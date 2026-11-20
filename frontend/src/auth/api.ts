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
  constructor(
    message = "Protected API request blocked while authentication is locked",
  ) {
    super(message);
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

export class ProtectedTabBlockedError extends Error {
  constructor() {
    super(
      "Pop-up blocked by browser. Allow pop-ups for Florabase to open this file.",
    );
    this.name = "ProtectedTabBlockedError";
  }
}

export function isExpectedAuthCancellation(error: unknown): boolean {
  return (
    error instanceof AuthRequestLockedError ||
    error instanceof StaleAuthEpochError ||
    (error instanceof DOMException && error.name === "AbortError")
  );
}

declare const capabilityBrand: unique symbol;

/**
 * Opaque handle authorizing protected requests for a single owner workspace.
 * Never exposes internal generation/epoch mutators or public revocation methods.
 */
export interface ProtectedRequestCapability {
  readonly [capabilityBrand]: true;
  isAuthorized: () => boolean;
  subscribeInvalidation: (listener: () => void) => () => void;
  subscribePermanentRevocation: (listener: () => void) => () => void;
}

export interface ManagedWorkspaceCapabilityHandle {
  readonly capability: ProtectedRequestCapability;
  revoke: () => void;
}

export interface AuthProviderGateController {
  readonly isActive: () => boolean;
  readonly syncGate: (options: {
    locked: boolean;
    advanceEpoch?: boolean;
    ownerId?: string | null;
    invalidateWorkspace?: boolean;
  }) => number;
  readonly invalidateWorkspace: () => number;
  readonly acquireWorkspaceCapability: () => ManagedWorkspaceCapabilityHandle;
  readonly detach: () => void;
}

export interface ProtectedRequestInit extends RequestInit {
  capability: ProtectedRequestCapability;
}

export interface ProtectedBlobResult {
  status: number;
  blob: Blob;
  contentType: string | null;
  contentDisposition: string | null;
}

export type ClassifiedResourceUrl =
  | { kind: "protected-api"; url: string }
  | { kind: "public-local"; url: string }
  | { kind: "local-blob"; url: string }
  | { kind: "external-https"; url: string }
  | { kind: "invalid" };

interface CapabilityRecord {
  readonly providerId: number;
  readonly workspaceGeneration: number;
  readonly ownerId: string;
  revoked: boolean;
  revoke: () => void;
}

interface AuthRequestGate {
  activeProviderId: number;
  nextProviderId: number;
  locked: boolean;
  epoch: number;
  workspaceGeneration: number;
  ownerId: string | null;
  onUnauthorized?: (originatingEpoch: number, providerId: number) => void;
}

const gate: AuthRequestGate = {
  activeProviderId: 0,
  nextProviderId: 0,
  locked: true,
  epoch: 0,
  workspaceGeneration: 1,
  ownerId: null,
};

const inFlightProtectedControllers = new Map<
  AbortController,
  { providerId: number; epoch: number }
>();
const invalidationListeners = new Set<() => void>();
const capabilityRecords = new WeakMap<
  ProtectedRequestCapability,
  CapabilityRecord
>();
const activeCapabilityRecords = new Set<CapabilityRecord>();

let cookieOpQueue: Promise<void> = Promise.resolve();
let pendingCookieOpsCount = 0;

/**
 * Serializes cookie- and CSRF-mutating authentication lifecycle operations
 * across provider remounts so replacement providers observe settled server
 * session and CSRF state before probing or publishing tokens.
 */
export function enqueueAuthCookieOperation<T>(
  op: () => Promise<T>,
): Promise<T> {
  const run = (): Promise<T> => {
    try {
      return Promise.resolve(op());
    } catch (error: unknown) {
      return Promise.reject(
        error instanceof Error ? error : new Error(String(error)),
      );
    }
  };
  const nextRun =
    pendingCookieOpsCount === 0 ? run() : cookieOpQueue.then(run, run);
  pendingCookieOpsCount += 1;
  cookieOpQueue = nextRun.then(
    () => {
      pendingCookieOpsCount -= 1;
    },
    () => {
      pendingCookieOpsCount -= 1;
    },
  );
  return nextRun;
}

function revokeAllCapabilities(providerId?: number): void {
  for (const record of [...activeCapabilityRecords]) {
    if (providerId === undefined || record.providerId === providerId) {
      record.revoke();
    }
  }
  if (providerId === undefined) {
    activeCapabilityRecords.clear();
  }
}

function notifyInvalidation(): void {
  for (const [controller, info] of inFlightProtectedControllers) {
    if (
      gate.locked ||
      info.providerId !== gate.activeProviderId ||
      info.epoch !== gate.epoch
    ) {
      controller.abort(new StaleAuthEpochError());
    }
  }
  for (const listener of [...invalidationListeners]) listener();
}

export function revokedAuthCapability(): ProtectedRequestCapability {
  const capability = Object.freeze({
    isAuthorized: () => false,
    subscribeInvalidation: () => () => undefined,
    subscribePermanentRevocation: (listener: () => void) => {
      listener();
      return () => undefined;
    },
  }) as unknown as ProtectedRequestCapability;
  return capability;
}

function invalidateProtectedWorkspaceForProvider(providerId: number): number {
  if (providerId !== gate.activeProviderId) {
    revokeAllCapabilities(providerId);
    return -1;
  }
  gate.locked = true;
  gate.epoch += 1;
  gate.workspaceGeneration += 1;
  gate.ownerId = null;
  revokeAllCapabilities();
  notifyInvalidation();
  return gate.epoch;
}

function syncAuthRequestGateForProvider({
  providerId,
  locked,
  advanceEpoch = false,
  ownerId,
  invalidateWorkspace = false,
}: {
  providerId: number;
  locked: boolean;
  advanceEpoch?: boolean;
  ownerId?: string | null;
  invalidateWorkspace?: boolean;
}): number {
  if (providerId !== gate.activeProviderId) {
    return -1;
  }
  if (invalidateWorkspace) {
    invalidateProtectedWorkspaceForProvider(providerId);
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

function issueWorkspaceCapabilityForProvider(
  providerId: number,
): ManagedWorkspaceCapabilityHandle {
  if (
    providerId === 0 ||
    providerId !== gate.activeProviderId ||
    gate.ownerId === null
  ) {
    return { capability: revokedAuthCapability(), revoke: () => undefined };
  }

  const boundProviderId = providerId;
  const boundGeneration = gate.workspaceGeneration;
  const boundOwnerId = gate.ownerId;
  const unsubs = new Set<() => void>();
  const callbacks = new Set<() => void>();
  const revocationCallbacks = new Set<() => void>();

  const record: CapabilityRecord = {
    providerId: boundProviderId,
    workspaceGeneration: boundGeneration,
    ownerId: boundOwnerId,
    revoked: false,
    revoke: () => {
      if (record.revoked) return;
      record.revoked = true;
      activeCapabilityRecords.delete(record);
      for (const unsub of [...unsubs]) unsub();
      unsubs.clear();
      for (const listener of [...revocationCallbacks]) listener();
      revocationCallbacks.clear();
      for (const listener of [...callbacks]) listener();
      callbacks.clear();
    },
  };
  activeCapabilityRecords.add(record);

  const isAuthorized = (): boolean => {
    if (record.revoked) return false;
    return (
      !gate.locked &&
      gate.activeProviderId === boundProviderId &&
      gate.workspaceGeneration === boundGeneration &&
      gate.ownerId === boundOwnerId
    );
  };

  const capability = Object.freeze({
    isAuthorized,
    subscribeInvalidation: (listener: () => void) => {
      if (record.revoked) return () => undefined;
      callbacks.add(listener);
      const unsub = subscribeAuthInvalidation(listener);
      unsubs.add(unsub);
      return () => {
        callbacks.delete(listener);
        unsubs.delete(unsub);
        unsub();
      };
    },
    subscribePermanentRevocation: (listener: () => void) => {
      if (record.revoked) {
        listener();
        return () => undefined;
      }
      revocationCallbacks.add(listener);
      return () => {
        revocationCallbacks.delete(listener);
      };
    },
  }) as unknown as ProtectedRequestCapability;

  capabilityRecords.set(capability, record);
  return { capability, revoke: record.revoke };
}

/**
 * Attaches an AuthProvider instance to the shared request gate and returns a
 * provider-private controller. Capability issuance and gate mutation authority
 * are bound to this opaque controller and permanently lost upon retirement.
 */
export function attachAuthRequestGate(
  onUnauthorized: (originatingEpoch: number) => void,
  initialLocked = true,
): AuthProviderGateController {
  const providerId = ++gate.nextProviderId;
  let retired = false;
  gate.activeProviderId = providerId;
  gate.locked = initialLocked;
  gate.epoch += 1;
  gate.workspaceGeneration += 1;
  gate.ownerId = null;
  gate.onUnauthorized = (originatingEpoch, callbackProviderId) => {
    if (
      retired ||
      callbackProviderId !== providerId ||
      gate.activeProviderId !== providerId
    ) {
      return;
    }
    onUnauthorized(originatingEpoch);
  };
  revokeAllCapabilities();
  notifyInvalidation();

  const isActive = (): boolean =>
    !retired && gate.activeProviderId === providerId;

  return Object.freeze<AuthProviderGateController>({
    isActive,
    syncGate: (options) => {
      if (!isActive()) return -1;
      return syncAuthRequestGateForProvider({ providerId, ...options });
    },
    invalidateWorkspace: () => {
      if (!isActive()) {
        revokeAllCapabilities(providerId);
        return -1;
      }
      return invalidateProtectedWorkspaceForProvider(providerId);
    },
    acquireWorkspaceCapability: () => {
      if (!isActive()) {
        return { capability: revokedAuthCapability(), revoke: () => undefined };
      }
      return issueWorkspaceCapabilityForProvider(providerId);
    },
    detach: () => {
      if (retired) return;
      retired = true;
      if (gate.activeProviderId !== providerId) {
        revokeAllCapabilities(providerId);
        return;
      }
      gate.activeProviderId = 0;
      gate.locked = true;
      gate.epoch += 1;
      gate.workspaceGeneration += 1;
      gate.ownerId = null;
      gate.onUnauthorized = undefined;
      revokeAllCapabilities();
      notifyInvalidation();
    },
  });
}

export function isProtectedRequestAuthorized(): boolean {
  return gate.activeProviderId !== 0 && !gate.locked && gate.ownerId !== null;
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

function validateCapability(capability: ProtectedRequestCapability): {
  record: CapabilityRecord;
  originatingEpoch: number;
  originatingProviderId: number;
  originatingWorkspace: number;
  originatingOwner: string;
} {
  const record = capabilityRecords.get(capability);
  if (!record) {
    throw new AuthRequestLockedError(
      "Protected API request requires a valid active capability",
    );
  }
  if (
    record.revoked ||
    record.providerId !== gate.activeProviderId ||
    record.workspaceGeneration !== gate.workspaceGeneration ||
    record.ownerId !== gate.ownerId
  ) {
    throw new StaleAuthEpochError();
  }
  if (gate.locked) {
    throw new AuthRequestLockedError();
  }
  return {
    record,
    originatingEpoch: gate.epoch,
    originatingProviderId: gate.activeProviderId,
    originatingWorkspace: gate.workspaceGeneration,
    originatingOwner: gate.ownerId,
  };
}

/**
 * Classifies resource URLs before any raw `<img src>` or `<a href>` emission.
 * All same-origin URLs other than explicit public assets (`/api/v1/health`, `/icons/*`)
 * fail closed as `protected-api` and must be loaded with an active capability.
 */
export function classifyResourceUrl(
  rawUrl: string | null | undefined,
): ClassifiedResourceUrl {
  const trimmed = rawUrl?.trim() ?? "";
  if (!trimmed) return { kind: "invalid" };
  const originBase =
    typeof window !== "undefined" && window.location.origin
      ? window.location.origin
      : "http://localhost";
  let parsed: URL;
  try {
    parsed = new URL(trimmed, originBase);
  } catch {
    return { kind: "invalid" };
  }
  if (parsed.protocol === "blob:") {
    return { kind: "local-blob", url: parsed.href };
  }
  if (parsed.origin === originBase) {
    const sameOriginUrl = `${parsed.pathname}${parsed.search}${parsed.hash}`;
    if (
      parsed.pathname === "/api/v1/health" ||
      parsed.pathname === "/icons" ||
      parsed.pathname.startsWith("/icons/")
    ) {
      return { kind: "public-local", url: sameOriginUrl };
    }
    return { kind: "protected-api", url: sameOriginUrl };
  }
  if (parsed.protocol === "https:") {
    return { kind: "external-https", url: parsed.href };
  }
  return { kind: "invalid" };
}

export function parseContentDispositionFilename(
  header: string | null,
  fallback: string,
): string {
  const sanitize = (candidate: string): string => {
    let cleaned = "";
    for (const ch of candidate.trim()) {
      const code = ch.charCodeAt(0);
      if (code < 0x20 || code === 0x7f || ch === "/" || ch === "\\") {
        cleaned += "_";
      } else {
        cleaned += ch;
      }
    }
    cleaned = cleaned.replace(/^\.+/, "").trim();
    if (!cleaned || cleaned === "." || cleaned === "..") return fallback;
    return cleaned;
  };
  if (!header) return sanitize(fallback);

  const extMatch = /filename\*\s*=\s*(?:[^']*)'(?:[^']*)'([^;\r\n]+)/i.exec(
    header,
  );
  if (extMatch?.[1]) {
    try {
      return sanitize(decodeURIComponent(extMatch[1].trim()));
    } catch {
      // Fall through to quoted or plain filename parameter.
    }
  }
  const quotedMatch = /filename\s*=\s*"([^"\r\n]+)"/i.exec(header);
  if (quotedMatch?.[1]) return sanitize(quotedMatch[1]);
  const plainMatch = /filename\s*=\s*([^;\r\n]+)/i.exec(header);
  if (plainMatch?.[1]) return sanitize(plainMatch[1]);
  return sanitize(fallback);
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

async function executeProtectedFetch<T>(
  path: string,
  init: ProtectedRequestInit,
  defaultAccept: string,
  parseSuccess: (response: Response) => Promise<T>,
): Promise<T> {
  const { capability, ...requestInit } = init;
  const {
    record,
    originatingEpoch,
    originatingProviderId,
    originatingWorkspace,
    originatingOwner,
  } = validateCapability(capability);

  const isCurrentContext = (): boolean =>
    !record.revoked &&
    !gate.locked &&
    gate.activeProviderId === originatingProviderId &&
    gate.epoch === originatingEpoch &&
    gate.workspaceGeneration === originatingWorkspace &&
    gate.ownerId === originatingOwner;

  const externalSignal = requestInit.signal;
  const epochController = new AbortController();
  const onExternalAbort = () => {
    epochController.abort(externalSignal?.reason);
  };
  if (externalSignal) {
    if (externalSignal.aborted) epochController.abort(externalSignal.reason);
    else {
      externalSignal.addEventListener("abort", onExternalAbort, { once: true });
    }
  }
  inFlightProtectedControllers.set(epochController, {
    providerId: originatingProviderId,
    epoch: originatingEpoch,
  });

  try {
    const headers = new Headers(requestInit.headers);
    if (!headers.has("Accept")) {
      headers.set("Accept", defaultAccept);
    }
    const response = await fetch(path, {
      ...requestInit,
      credentials: "same-origin",
      headers,
      signal: epochController.signal,
    });
    if (externalSignal?.aborted) {
      throw new DOMException("The operation was aborted.", "AbortError");
    }
    if (!isCurrentContext()) throw new StaleAuthEpochError();
    if (!response.ok) {
      let body: unknown;
      try {
        body = await response.json();
      } catch {
        body = undefined;
      }
      if (!isCurrentContext()) throw new StaleAuthEpochError();
      if (response.status === 401) {
        gate.onUnauthorized?.(originatingEpoch, originatingProviderId);
      }
      throw new ApiError(
        response.status,
        response.headers.get("Retry-After"),
        body,
      );
    }
    const parsed = await parseSuccess(response);
    if (!isCurrentContext()) throw new StaleAuthEpochError();
    return parsed;
  } catch (error: unknown) {
    if (
      !externalSignal?.aborted &&
      epochController.signal.aborted &&
      !(error instanceof ApiError) &&
      !(error instanceof AuthRequestLockedError)
    ) {
      throw new StaleAuthEpochError();
    }
    throw error;
  } finally {
    inFlightProtectedControllers.delete(epochController);
    externalSignal?.removeEventListener("abort", onExternalAbort);
  }
}

export function requestJson<T>(
  path: string,
  init: ProtectedRequestInit,
): Promise<T> {
  return executeProtectedFetch<T>(
    path,
    init,
    "application/json",
    async (response) => {
      if (response.status === 204) return undefined as T;
      return (await response.json()) as T;
    },
  );
}

export function requestProtectedBlob(
  path: string,
  init: ProtectedRequestInit,
): Promise<ProtectedBlobResult> {
  return executeProtectedFetch<ProtectedBlobResult>(
    path,
    init,
    "*/*",
    async (response) => ({
      status: response.status,
      blob: response.status === 204 ? new Blob([]) : await response.blob(),
      contentType: response.headers.get("Content-Type"),
      contentDisposition: response.headers.get("Content-Disposition"),
    }),
  );
}

export async function downloadProtectedFile({
  path,
  capability,
  fallbackFilename,
  accept,
  signal,
}: {
  path: string;
  capability: ProtectedRequestCapability;
  fallbackFilename: string;
  accept?: string;
  signal?: AbortSignal;
}): Promise<string> {
  const { blob, contentDisposition } = await requestProtectedBlob(path, {
    capability,
    signal,
    headers: accept ? { Accept: accept } : undefined,
  });
  validateCapability(capability);

  const filename = parseContentDispositionFilename(
    contentDisposition,
    fallbackFilename,
  );
  const objectUrl = URL.createObjectURL(blob);
  let cleaned = false;
  let timerId: number | undefined;
  let unsub: () => void = () => undefined;

  const revokeObject = () => {
    if (cleaned) return;
    cleaned = true;
    unsub();
    if (timerId !== undefined) window.clearTimeout(timerId);
    URL.revokeObjectURL(objectUrl);
  };

  unsub = capability.subscribeInvalidation(() => {
    if (!capabilityRecords.get(capability) || !capability.isAuthorized()) {
      revokeObject();
    }
  });

  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  link.style.display = "none";
  document.body.append(link);
  try {
    link.click();
  } finally {
    link.remove();
    timerId = window.setTimeout(revokeObject, 1000);
  }
  return filename;
}

export async function openProtectedTab({
  path,
  capability,
  accept,
}: {
  path: string;
  capability: ProtectedRequestCapability;
  accept?: string;
}): Promise<void> {
  validateCapability(capability);
  // Open synchronously on user click without "noopener" feature token so we keep
  // a handle to close the popup on cancellation/failure; sever opener right away.
  const popup = window.open("", "_blank");
  if (!popup) {
    throw new ProtectedTabBlockedError();
  }
  try {
    popup.opener = null;
  } catch {
    // Ignore read-only opener implementations.
  }

  let objectUrl: string | null = null;
  let unsub: () => void = () => undefined;
  let timerId: number | undefined;

  const cleanupUrl = () => {
    unsub();
    if (timerId !== undefined) window.clearTimeout(timerId);
    if (objectUrl !== null) {
      URL.revokeObjectURL(objectUrl);
      objectUrl = null;
    }
  };

  const closePopupIfOpen = () => {
    try {
      if (!popup.closed) popup.close();
    } catch {
      // Ignore cross-origin / detached close errors.
    }
  };

  unsub = capability.subscribeInvalidation(() => {
    if (!capability.isAuthorized()) {
      closePopupIfOpen();
      cleanupUrl();
    }
  });

  try {
    const { blob } = await requestProtectedBlob(path, {
      capability,
      headers: accept ? { Accept: accept } : undefined,
    });
    validateCapability(capability);
    objectUrl = URL.createObjectURL(blob);
    popup.location.replace(objectUrl);
    timerId = window.setTimeout(cleanupUrl, 60_000);
  } catch (error) {
    closePopupIfOpen();
    cleanupUrl();
    throw error;
  }
}

export function getSession(signal?: AbortSignal): Promise<SessionResponse> {
  if (signal?.aborted) {
    return Promise.reject(
      new DOMException("The operation was aborted.", "AbortError"),
    );
  }
  const request = fetchJson<SessionResponse>("/api/v1/auth/session", {
    signal,
  });
  if (!signal) return request;
  return new Promise<SessionResponse>((resolve, reject) => {
    const onAbort = () => {
      reject(new DOMException("The operation was aborted.", "AbortError"));
    };
    signal.addEventListener("abort", onAbort, { once: true });
    request.then(
      (value) => {
        signal.removeEventListener("abort", onAbort);
        resolve(value);
      },
      (error: unknown) => {
        signal.removeEventListener("abort", onAbort);
        reject(error instanceof Error ? error : new Error(String(error)));
      },
    );
  });
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
