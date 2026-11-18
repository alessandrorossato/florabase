import type { components } from "../api/schema";
import type { AuthState, RetainedOwnerIdentity } from "./context";

export type LoginRequest = components["schemas"]["LoginRequest"];
export type LoginResponse = components["schemas"]["LoginResponse"];
export type SessionResponse = components["schemas"]["SessionResponse"];
export type CsrfResponse = components["schemas"]["CsrfResponse"];

export type ReauthenticationAuthState = Extract<
  AuthState,
  { status: "unauthenticated" | "submitting-login" }
> & { retainedIdentity: RetainedOwnerIdentity };

export type PresentationRetainedAuthState =
  | Extract<
      AuthState,
      { status: "authenticated" | "logging-out" | "logout-failed" }
    >
  | ReauthenticationAuthState;

/** Returns true only when an expired session retains an owner identity for modal recovery. */
export function isReauthenticationState(
  state: AuthState,
): state is ReauthenticationAuthState {
  return (
    (state.status === "unauthenticated" ||
      state.status === "submitting-login") &&
    state.retainedIdentity !== undefined
  );
}

/**
 * Presentation-only check for retaining a hidden, inert workspace DOM subtree
 * across reauthentication. Never use this to authorize requests or mutations.
 */
export function isPresentationRetainedState(
  state: AuthState,
): state is PresentationRetainedAuthState {
  return (
    state.status === "authenticated" ||
    state.status === "logging-out" ||
    state.status === "logout-failed" ||
    isReauthenticationState(state)
  );
}

/** Returns the active CSRF token only when the session is authenticated. */
export function activeCsrfToken(state: AuthState): string {
  return state.status === "authenticated" ? state.csrfToken : "";
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly retryAfter: string | null = null,
    readonly body?: unknown,
  ) {
    super(`API request failed with HTTP ${String(status)}`);
  }
}

export class AuthRequestLockedError extends Error {
  constructor() {
    super("Protected API request blocked while authentication is locked");
    this.name = "AuthRequestLockedError";
  }
}

export class StaleAuthEpochError extends Error {
  constructor() {
    super(
      "Protected API response discarded after authentication epoch changed",
    );
    this.name = "StaleAuthEpochError";
  }
}

export function isExpectedAuthCancellation(error: unknown): boolean {
  return (
    error instanceof AuthRequestLockedError ||
    error instanceof StaleAuthEpochError ||
    (error instanceof DOMException && error.name === "AbortError")
  );
}

interface AuthRequestGate {
  managed: boolean;
  locked: boolean;
  epoch: number;
  workspaceGeneration: number;
  ownerId: string | null;
  onUnauthorized?: (originatingEpoch: number) => void;
}

const gate: AuthRequestGate = {
  managed: false,
  locked: false,
  epoch: 0,
  workspaceGeneration: 0,
  ownerId: null,
};

const inFlightProtectedControllers = new Map<AbortController, number>();
const invalidationListeners = new Set<() => void>();
const activeCapabilities = new Set<{ revoke: () => void }>();

export interface ProtectedRequestCapability {
  readonly workspaceGeneration: number;
  readonly ownerId: string | null;
  isAuthorized: () => boolean;
  getEpoch: () => number;
  isRevoked: () => boolean;
  revoke: () => void;
  notifyUnauthorized: (originatingEpoch: number) => boolean;
  subscribeInvalidation: (listener: () => void) => () => void;
}

function revokeAllCapabilities(): void {
  for (const capability of [...activeCapabilities]) {
    capability.revoke();
  }
  activeCapabilities.clear();
}

function notifyInvalidation(): void {
  for (const [controller, controllerEpoch] of inFlightProtectedControllers) {
    if (gate.locked || controllerEpoch !== gate.epoch) {
      controller.abort(new StaleAuthEpochError());
    }
  }
  for (const listener of [...invalidationListeners]) listener();
}

export function attachAuthRequestGate(
  onUnauthorized: (originatingEpoch: number) => void,
  initialLocked = true,
): () => void {
  gate.managed = true;
  gate.locked = initialLocked;
  gate.epoch += 1;
  gate.workspaceGeneration += 1;
  gate.ownerId = null;
  gate.onUnauthorized = onUnauthorized;
  revokeAllCapabilities();
  notifyInvalidation();
  return () => {
    gate.managed = false;
    gate.locked = false;
    gate.epoch += 1;
    gate.workspaceGeneration += 1;
    gate.ownerId = null;
    gate.onUnauthorized = undefined;
    revokeAllCapabilities();
    notifyInvalidation();
  };
}

/**
 * Synchronously invalidates the active owner's workspace generation and revokes
 * every owner-bound request capability before any replacement owner session can unlock.
 */
export function invalidateProtectedWorkspace(): number {
  gate.locked = true;
  gate.epoch += 1;
  gate.workspaceGeneration += 1;
  gate.ownerId = null;
  revokeAllCapabilities();
  notifyInvalidation();
  return gate.epoch;
}

export function syncAuthRequestGate({
  locked,
  advanceEpoch = false,
  ownerId,
  invalidateWorkspace = false,
}: {
  locked: boolean;
  advanceEpoch?: boolean;
  ownerId?: string | null;
  invalidateWorkspace?: boolean;
}): number {
  if (invalidateWorkspace) {
    invalidateProtectedWorkspace();
  }
  const nextOwnerId = ownerId !== undefined ? ownerId : gate.ownerId;
  const changed =
    locked !== gate.locked ||
    advanceEpoch ||
    nextOwnerId !== gate.ownerId ||
    invalidateWorkspace;
  gate.locked = locked;
  gate.ownerId = nextOwnerId;
  if (advanceEpoch && !invalidateWorkspace) gate.epoch += 1;
  if (changed && (gate.locked || advanceEpoch || invalidateWorkspace)) {
    notifyInvalidation();
  }
  return gate.epoch;
}

export function isProtectedRequestAuthorized(): boolean {
  return !gate.managed || !gate.locked;
}

export function getProtectedAuthEpoch(): number {
  return gate.epoch;
}

export function getProtectedWorkspaceGeneration(): number {
  return gate.workspaceGeneration;
}

export function subscribeAuthInvalidation(listener: () => void): () => void {
  invalidationListeners.add(listener);
  return () => {
    invalidationListeners.delete(listener);
  };
}

/**
 * Acquires a fail-closed capability bound to the current owner and workspace generation.
 * Same-owner session recovery preserves the binding across temporary locks; any workspace
 * retirement (different-owner authentication, logout, discard) revokes it permanently.
 */
export function acquireProtectedRequestCapability(): ProtectedRequestCapability {
  const managedAtAcquire = gate.managed;
  const boundGeneration = gate.workspaceGeneration;
  const boundOwnerId = gate.ownerId;
  let revoked = managedAtAcquire && gate.locked && boundOwnerId === null;
  const unsubs = new Set<() => void>();
  const callbacks = new Set<() => void>();

  const isAuthorized = (): boolean => {
    if (revoked) return false;
    if (!gate.managed) return !managedAtAcquire;
    return (
      !gate.locked &&
      boundGeneration === gate.workspaceGeneration &&
      boundOwnerId === gate.ownerId
    );
  };

  const entry = {
    revoke: () => {
      if (revoked) return;
      revoked = true;
      activeCapabilities.delete(entry);
      for (const unsub of [...unsubs]) unsub();
      unsubs.clear();
      for (const listener of [...callbacks]) listener();
      callbacks.clear();
    },
  };
  if (!revoked) {
    activeCapabilities.add(entry);
  }

  return {
    workspaceGeneration: boundGeneration,
    ownerId: boundOwnerId,
    isAuthorized,
    getEpoch: () => (isAuthorized() ? gate.epoch : -1),
    isRevoked: () => revoked,
    revoke: entry.revoke,
    notifyUnauthorized: (originatingEpoch: number) => {
      if (!isAuthorized()) return false;
      return notifyProtectedUnauthorized(originatingEpoch);
    },
    subscribeInvalidation: (listener: () => void) => {
      if (revoked) return () => undefined;
      callbacks.add(listener);
      const unsub = subscribeAuthInvalidation(listener);
      unsubs.add(unsub);
      return () => {
        callbacks.delete(listener);
        unsubs.delete(unsub);
        unsub();
      };
    },
  };
}

/**
 * Centrally notifies the managed authentication gate of an HTTP 401 from
 * a protected endpoint when the response belongs to the current unlocked epoch.
 */
export function notifyProtectedUnauthorized(originatingEpoch: number): boolean {
  if (!gate.managed || gate.locked || gate.epoch !== originatingEpoch) {
    return false;
  }
  gate.onUnauthorized?.(originatingEpoch);
  return true;
}

async function fetchJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  const response = await fetch(path, {
    ...init,
    credentials: "same-origin",
    headers,
  });
  if (!response.ok) {
    let body: unknown;
    try {
      body = await response.json();
    } catch {
      body = undefined;
    }
    throw new ApiError(
      response.status,
      response.headers.get("Retry-After"),
      body,
    );
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function staleForEpoch(originatingEpoch: number): boolean {
  return gate.managed && (gate.locked || gate.epoch !== originatingEpoch);
}

export async function requestJson<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const managed = gate.managed;
  if (managed && gate.locked) throw new AuthRequestLockedError();

  const originatingEpoch = gate.epoch;
  const externalSignal = init.signal;
  const epochController = managed ? new AbortController() : undefined;
  const onExternalAbort = () => {
    epochController?.abort(externalSignal?.reason);
  };
  if (epochController) {
    if (externalSignal) {
      if (externalSignal.aborted) epochController.abort(externalSignal.reason);
      else
        externalSignal.addEventListener("abort", onExternalAbort, {
          once: true,
        });
    }
    inFlightProtectedControllers.set(epochController, originatingEpoch);
  }

  try {
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    const response = await fetch(path, {
      ...init,
      credentials: "same-origin",
      headers,
      signal: epochController ? epochController.signal : externalSignal,
    });
    if (staleForEpoch(originatingEpoch)) throw new StaleAuthEpochError();
    if (!response.ok) {
      let body: unknown;
      try {
        body = await response.json();
      } catch {
        body = undefined;
      }
      if (staleForEpoch(originatingEpoch)) throw new StaleAuthEpochError();
      if (response.status === 401) {
        notifyProtectedUnauthorized(originatingEpoch);
      }
      throw new ApiError(
        response.status,
        response.headers.get("Retry-After"),
        body,
      );
    }
    if (response.status === 204) {
      if (staleForEpoch(originatingEpoch)) throw new StaleAuthEpochError();
      return undefined as T;
    }
    const data = (await response.json()) as T;
    if (staleForEpoch(originatingEpoch)) throw new StaleAuthEpochError();
    return data;
  } catch (error: unknown) {
    if (
      epochController &&
      !externalSignal?.aborted &&
      epochController.signal.aborted &&
      !(error instanceof ApiError) &&
      !(error instanceof AuthRequestLockedError)
    ) {
      throw new StaleAuthEpochError();
    }
    throw error;
  } finally {
    if (epochController) {
      inFlightProtectedControllers.delete(epochController);
      externalSignal?.removeEventListener("abort", onExternalAbort);
    }
  }
}

export function getSession(signal?: AbortSignal): Promise<SessionResponse> {
  return fetchJson("/api/v1/auth/session", { signal });
}

export function recoverCsrf(signal?: AbortSignal): Promise<CsrfResponse> {
  return fetchJson("/api/v1/auth/csrf", { method: "POST", signal });
}

export function login(
  payload: LoginRequest,
  signal?: AbortSignal,
): Promise<LoginResponse> {
  return fetchJson("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
}

export async function logout(csrfToken: string): Promise<void> {
  await fetchJson("/api/v1/auth/logout", {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
  });
}

export type ChangePasswordRequest =
  components["schemas"]["ChangePasswordRequest"];

export function changePassword(
  payload: ChangePasswordRequest,
  csrfToken: string,
): Promise<LoginResponse> {
  return fetchJson("/api/v1/auth/password", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify(payload),
  });
}
