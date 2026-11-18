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

interface AuthRequestGate {
  managed: boolean;
  locked: boolean;
  epoch: number;
  onUnauthorized?: (originatingEpoch: number) => void;
}

const gate: AuthRequestGate = {
  managed: false,
  locked: false,
  epoch: 0,
};

const inFlightProtectedControllers = new Map<AbortController, number>();
const invalidationListeners = new Set<() => void>();

function notifyInvalidation(): void {
  for (const [controller, controllerEpoch] of inFlightProtectedControllers) {
    if (gate.locked || controllerEpoch !== gate.epoch) {
      controller.abort(new StaleAuthEpochError());
    }
  }
  for (const listener of invalidationListeners) listener();
}

export function attachAuthRequestGate(
  onUnauthorized: (originatingEpoch: number) => void,
  initialLocked = true,
): () => void {
  gate.managed = true;
  gate.locked = initialLocked;
  gate.epoch += 1;
  gate.onUnauthorized = onUnauthorized;
  notifyInvalidation();
  return () => {
    gate.managed = false;
    gate.locked = false;
    gate.epoch += 1;
    gate.onUnauthorized = undefined;
    notifyInvalidation();
  };
}

export function syncAuthRequestGate({
  locked,
  advanceEpoch = false,
}: {
  locked: boolean;
  advanceEpoch?: boolean;
}): number {
  const changed = locked !== gate.locked || advanceEpoch;
  gate.locked = locked;
  if (advanceEpoch) gate.epoch += 1;
  if (changed && (gate.locked || advanceEpoch)) {
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

export function subscribeAuthInvalidation(listener: () => void): () => void {
  invalidationListeners.add(listener);
  return () => {
    invalidationListeners.delete(listener);
  };
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
      if (response.status === 401 && managed) {
        gate.onUnauthorized?.(originatingEpoch);
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
