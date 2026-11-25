/* eslint-disable react-refresh/only-export-components -- AuthProvider co-locates lexically private gate attachment with public auth request APIs; Vite HMR falls back to full reload */
import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import type { components } from "../api/schema";
import {
  AuthContext,
  PasswordChangeContext,
  type AuthContextValue,
  type AuthState,
  type LoginSubmission,
  type RetainedOwnerIdentity,
} from "./context";
import {
  buildTransportFetchInit,
  clearNativeBearerToken,
  getConfiguredServerUrl,
  hasNativeBearerToken,
  isNativeBearerTransport,
  loadDefaultDeviceLabel,
  persistNativeBearerToken,
  resolveApiUrl,
} from "./transport";

export type LoginRequest = components["schemas"]["LoginRequest"];
export type LoginResponse = components["schemas"]["LoginResponse"];
export type SessionResponse = components["schemas"]["SessionResponse"];
export type CsrfResponse = components["schemas"]["CsrfResponse"];
export type DeviceSessionCreateRequest =
  components["schemas"]["DeviceSessionCreateRequest"];
export type DeviceSessionCreateResponse =
  components["schemas"]["DeviceSessionCreateResponse"];
export type DeviceSessionItem = components["schemas"]["DeviceSessionItem"];
export type DeviceSessionListResponse =
  components["schemas"]["DeviceSessionListResponse"];
export type DeviceSessionRevokeAllResponse =
  components["schemas"]["DeviceSessionRevokeAllResponse"];

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

export class NativeFileActionUnavailableError extends Error {
  constructor() {
    super(
      "Opening/downloading files is not yet available in the app — coming soon.",
    );
    this.name = "NativeFileActionUnavailableError";
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

interface ManagedWorkspaceCapabilityHandle {
  readonly capability: ProtectedRequestCapability;
  revoke: () => void;
}

interface AuthProviderGateController {
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
function enqueueAuthCookieOperation<T>(op: () => Promise<T>): Promise<T> {
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

function revokedAuthCapability(): ProtectedRequestCapability {
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
 * Lexically private gate attachment restricted to AuthProvider in this module.
 * Capability issuance and gate mutation authority are bound to the returned
 * opaque controller and permanently lost upon retirement.
 */
function attachAuthRequestGate(
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
  const configuredServerUrl = getConfiguredServerUrl();
  if (configuredServerUrl !== null) {
    try {
      const configuredOrigin = new URL(configuredServerUrl).origin;
      if (parsed.origin === configuredOrigin) {
        const relativePath = `${parsed.pathname}${parsed.search}${parsed.hash}`;
        if (parsed.pathname === "/api/v1/health") {
          return { kind: "public-local", url: relativePath };
        }
        return { kind: "protected-api", url: relativePath };
      }
    } catch {
      // Ignore malformed server URL configuration.
    }
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

async function fetchJson<T>(
  path: string,
  init: RequestInit = {},
  { includeBearer = true }: { includeBearer?: boolean } = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  const response = await fetch(
    resolveApiUrl(path),
    buildTransportFetchInit({ ...init, headers }, { includeBearer }),
  );
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
    const response = await fetch(
      resolveApiUrl(path),
      buildTransportFetchInit({
        ...requestInit,
        headers,
        signal: epochController.signal,
      }),
    );
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
  if (isNativeBearerTransport()) {
    throw new NativeFileActionUnavailableError();
  }
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
  if (isNativeBearerTransport()) {
    throw new NativeFileActionUnavailableError();
  }
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

export function createDeviceSession(
  payload: DeviceSessionCreateRequest,
  signal?: AbortSignal,
): Promise<DeviceSessionCreateResponse> {
  return fetchJson(
    "/api/v1/auth/device-sessions",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal,
    },
    { includeBearer: false },
  );
}

export async function revokeCurrentDeviceSession(): Promise<void> {
  await fetchJson("/api/v1/auth/device-sessions/current", {
    method: "DELETE",
  });
}

export function listDeviceSessions(
  capability: ProtectedRequestCapability,
  signal?: AbortSignal,
): Promise<DeviceSessionListResponse> {
  return requestJson<DeviceSessionListResponse>(
    "/api/v1/auth/device-sessions",
    {
      capability,
      signal,
    },
  );
}

export async function revokeDeviceSession(
  sessionId: string,
  csrfToken: string,
  capability: ProtectedRequestCapability,
): Promise<void> {
  await requestJson<undefined>(
    `/api/v1/auth/device-sessions/${encodeURIComponent(sessionId)}`,
    {
      method: "DELETE",
      headers: csrfToken ? { "X-CSRF-Token": csrfToken } : undefined,
      capability,
    },
  );
}

export function revokeAllDeviceSessions(
  csrfToken: string,
  capability: ProtectedRequestCapability,
): Promise<DeviceSessionRevokeAllResponse> {
  return requestJson<DeviceSessionRevokeAllResponse>(
    "/api/v1/auth/device-sessions",
    {
      method: "DELETE",
      headers: csrfToken ? { "X-CSRF-Token": csrfToken } : undefined,
      capability,
    },
  );
}

function serviceFailureMessage(): string {
  return "Florabase could not reach the authentication service. Please try again.";
}

function loginErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 401) {
    return "The login name or password was not accepted.";
  }
  if (error instanceof ApiError && error.status === 429) {
    const retry = error.retryAfter
      ? ` Try again in ${error.retryAfter} seconds.`
      : " Please wait before trying again.";
    return `Too many login attempts.${retry}`;
  }
  if (error instanceof ApiError && error.status === 422) {
    return "Check the login name and password, then try again.";
  }
  return serviceFailureMessage();
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: "restoring" });
  const [workspaceKey, setWorkspaceKey] = useState(0);
  const [restorationAttempt, setRestorationAttempt] = useState(0);

  const stateRef = useRef<AuthState>(state);
  const generation = useRef(0);
  const authEpochRef = useRef(0);
  const providerGateRef = useRef<AuthProviderGateController | null>(null);
  const mountedRef = useRef(true);
  const changingPassword = useRef(false);
  const [passwordChangePending, setPasswordChangePending] = useState(false);
  const workspaceCapRef = useRef<{
    ownerId: string;
    handle: ManagedWorkspaceCapabilityHandle;
  } | null>(null);
  const [capability, setCapability] = useState<ProtectedRequestCapability>(() =>
    revokedAuthCapability(),
  );

  const commitState = useCallback((next: AuthState) => {
    stateRef.current = next;
    setState(next);
  }, []);

  const isActiveProvider = useCallback(
    (expectedGate?: AuthProviderGateController | null) => {
      const activeGate =
        expectedGate !== undefined ? expectedGate : providerGateRef.current;
      return (
        mountedRef.current &&
        activeGate !== null &&
        activeGate === providerGateRef.current &&
        activeGate.isActive()
      );
    },
    [],
  );

  const retireWorkspaceCapability = useCallback(() => {
    workspaceCapRef.current?.handle.revoke();
    workspaceCapRef.current = null;
    setCapability(revokedAuthCapability());
  }, []);

  const ensureWorkspaceCapability = useCallback(
    (gateController: AuthProviderGateController | null, ownerId: string) => {
      if (
        !gateController ||
        gateController !== providerGateRef.current ||
        !gateController.isActive()
      ) {
        return;
      }
      if (workspaceCapRef.current?.ownerId === ownerId) {
        return;
      }
      workspaceCapRef.current?.handle.revoke();
      const handle = gateController.acquireWorkspaceCapability();
      workspaceCapRef.current = { ownerId, handle };
      setCapability(handle.capability);
    },
    [],
  );

  const expireAuthenticatedSession = useCallback(
    (expectedEpoch?: number) => {
      const gateController = providerGateRef.current;
      if (!isActiveProvider(gateController) || !gateController) return;
      if (
        expectedEpoch !== undefined &&
        expectedEpoch !== authEpochRef.current
      ) {
        return;
      }
      const current = stateRef.current;
      if (
        current.status !== "authenticated" &&
        current.status !== "logout-failed"
      ) {
        return;
      }
      generation.current += 1;
      if (isNativeBearerTransport()) {
        void clearNativeBearerToken();
      }
      authEpochRef.current = gateController.syncGate({
        locked: true,
        advanceEpoch: true,
        ownerId: current.session.user_id,
      });
      commitState({
        status: "unauthenticated",
        retainedIdentity: {
          user_id: current.session.user_id,
          login_name: current.session.login_name,
          display_name: current.session.display_name,
        },
        message: "Your session expired. Sign in again to continue.",
      });
    },
    [commitState, isActiveProvider],
  );

  useLayoutEffect(() => {
    mountedRef.current = true;
    const gateController = attachAuthRequestGate((originatingEpoch) => {
      if (providerGateRef.current !== gateController) return;
      expireAuthenticatedSession(originatingEpoch);
    }, true);
    providerGateRef.current = gateController;
    workspaceCapRef.current = null;
    const current = stateRef.current;
    const ownerId =
      current.status === "authenticated" || current.status === "logout-failed"
        ? current.session.user_id
        : isReauthenticationState(current)
          ? current.retainedIdentity.user_id
          : null;
    authEpochRef.current = gateController.syncGate({
      locked:
        current.status !== "authenticated" &&
        current.status !== "logout-failed",
      ownerId,
    });
    return () => {
      mountedRef.current = false;
      if (providerGateRef.current === gateController) {
        providerGateRef.current = null;
      }
      workspaceCapRef.current = null;
      generation.current += 1;
      gateController.detach();
    };
  }, [expireAuthenticatedSession]);

  useEffect(() => {
    const capturedGate = providerGateRef.current;
    if (!isActiveProvider(capturedGate) || !capturedGate) return;

    const controller = new AbortController();
    const attempt = ++generation.current;
    authEpochRef.current = capturedGate.invalidateWorkspace();
    retireWorkspaceCapability();
    commitState({ status: "restoring" });

    void enqueueAuthCookieOperation(async () => {
      if (attempt !== generation.current || !isActiveProvider(capturedGate)) {
        return;
      }

      try {
        if (isNativeBearerTransport() && !hasNativeBearerToken()) {
          authEpochRef.current = capturedGate.invalidateWorkspace();
          retireWorkspaceCapability();
          commitState({ status: "unauthenticated" });
          return;
        }
        const session = await getSession(controller.signal);
        if (attempt !== generation.current || !isActiveProvider(capturedGate)) {
          return;
        }
        let csrfToken = "";
        if (!isNativeBearerTransport()) {
          // CSRF recovery rotates server-side session CSRF state; once dispatched,
          // it must settle inside the lifecycle queue barrier even if this provider
          // unmounts so replacement restoration cannot race a late server rotation.
          const csrf = await recoverCsrf();
          if (
            attempt !== generation.current ||
            !isActiveProvider(capturedGate)
          ) {
            return;
          }
          csrfToken = csrf.csrf_token;
        }
        authEpochRef.current = capturedGate.syncGate({
          locked: false,
          advanceEpoch: true,
          ownerId: session.user_id,
        });
        ensureWorkspaceCapability(capturedGate, session.user_id);
        commitState({
          status: "authenticated",
          session,
          csrfToken,
        });
      } catch (error: unknown) {
        if (attempt !== generation.current || !isActiveProvider(capturedGate)) {
          return;
        }
        authEpochRef.current = capturedGate.invalidateWorkspace();
        retireWorkspaceCapability();
        if (error instanceof ApiError && error.status === 401) {
          if (isNativeBearerTransport()) {
            await clearNativeBearerToken();
          }
          commitState({ status: "unauthenticated" });
          return;
        }
        commitState({
          status: "recovery-failed",
          message: serviceFailureMessage(),
        });
      }
    });

    return () => {
      generation.current += 1;
      controller.abort();
    };
  }, [
    commitState,
    ensureWorkspaceCapability,
    isActiveProvider,
    restorationAttempt,
    retireWorkspaceCapability,
  ]);

  const logIn = useCallback(
    (payload: LoginSubmission) => {
      const capturedGate = providerGateRef.current;
      if (!isActiveProvider(capturedGate) || !capturedGate) {
        return Promise.resolve();
      }
      return enqueueAuthCookieOperation(async () => {
        if (!isActiveProvider(capturedGate)) return;
        const attempt = ++generation.current;
        authEpochRef.current = capturedGate.invalidateWorkspace();
        retireWorkspaceCapability();
        commitState({ status: "submitting-login" });
        let csrfToken = "";
        try {
          if (isNativeBearerTransport()) {
            const trimmedLabel = payload.device_label?.trim() ?? "";
            const rawLabel =
              trimmedLabel !== ""
                ? trimmedLabel
                : await loadDefaultDeviceLabel();
            const deviceLabel = rawLabel.slice(0, 120) || "Android device";
            const created = await createDeviceSession({
              login_name: payload.login_name,
              password: payload.password,
              device_label: deviceLabel,
            });
            await persistNativeBearerToken(created.token);
            if (
              attempt !== generation.current ||
              !isActiveProvider(capturedGate)
            ) {
              return;
            }
          } else {
            const csrf = await login({
              login_name: payload.login_name,
              password: payload.password,
            });
            if (
              attempt !== generation.current ||
              !isActiveProvider(capturedGate)
            ) {
              return;
            }
            csrfToken = csrf.csrf_token;
          }
        } catch (error: unknown) {
          if (
            attempt !== generation.current ||
            !isActiveProvider(capturedGate)
          ) {
            return;
          }
          commitState({
            status: "unauthenticated",
            message: loginErrorMessage(error),
          });
          return;
        }

        try {
          const session = await getSession();
          if (
            attempt !== generation.current ||
            !isActiveProvider(capturedGate)
          ) {
            return;
          }
          authEpochRef.current = capturedGate.invalidateWorkspace();
          retireWorkspaceCapability();
          setWorkspaceKey((value) => value + 1);
          authEpochRef.current = capturedGate.syncGate({
            locked: false,
            advanceEpoch: true,
            ownerId: session.user_id,
          });
          ensureWorkspaceCapability(capturedGate, session.user_id);
          commitState({
            status: "authenticated",
            session,
            csrfToken,
          });
        } catch {
          if (
            attempt !== generation.current ||
            !isActiveProvider(capturedGate)
          ) {
            return;
          }
          commitState({
            status: "recovery-failed",
            message: serviceFailureMessage(),
          });
        }
      });
    },
    [
      commitState,
      ensureWorkspaceCapability,
      isActiveProvider,
      retireWorkspaceCapability,
    ],
  );

  const reauthenticate = useCallback(
    (payload: LoginSubmission) => {
      const capturedGate = providerGateRef.current;
      if (!isActiveProvider(capturedGate) || !capturedGate) {
        return Promise.resolve();
      }
      const capturedWorkspace = getProtectedWorkspaceGeneration();
      return enqueueAuthCookieOperation(async () => {
        if (!isActiveProvider(capturedGate)) return;
        if (getProtectedWorkspaceGeneration() !== capturedWorkspace) return;
        const current = stateRef.current;
        if (current.status !== "unauthenticated" || !current.retainedIdentity)
          return;
        const { retainedIdentity } = current;
        const attempt = ++generation.current;
        authEpochRef.current = capturedGate.syncGate({
          locked: true,
          advanceEpoch: true,
          ownerId: retainedIdentity.user_id,
        });
        commitState({
          status: "submitting-login",
          retainedIdentity,
        });

        let csrfToken = "";
        try {
          if (isNativeBearerTransport()) {
            const trimmedLabel = payload.device_label?.trim() ?? "";
            const rawLabel =
              trimmedLabel !== ""
                ? trimmedLabel
                : await loadDefaultDeviceLabel();
            const deviceLabel = rawLabel.slice(0, 120) || "Android device";
            const created = await createDeviceSession({
              login_name: payload.login_name,
              password: payload.password,
              device_label: deviceLabel,
            });
            await persistNativeBearerToken(created.token);
            if (
              attempt !== generation.current ||
              !isActiveProvider(capturedGate)
            ) {
              return;
            }
          } else {
            const csrf = await login({
              login_name: payload.login_name,
              password: payload.password,
            });
            if (
              attempt !== generation.current ||
              !isActiveProvider(capturedGate)
            ) {
              return;
            }
            csrfToken = csrf.csrf_token;
          }
        } catch (error: unknown) {
          if (
            attempt !== generation.current ||
            !isActiveProvider(capturedGate)
          ) {
            return;
          }
          commitState({
            status: "unauthenticated",
            retainedIdentity,
            message: loginErrorMessage(error),
          });
          return;
        }

        try {
          const session = await getSession();
          if (
            attempt !== generation.current ||
            !isActiveProvider(capturedGate)
          ) {
            return;
          }
          const sameOwnerRecovery =
            session.user_id === retainedIdentity.user_id;
          if (!sameOwnerRecovery) {
            // Retire previous owner workspace & revoke all old-owner capabilities
            // synchronously before unlocking the gate for the replacement owner.
            authEpochRef.current = capturedGate.invalidateWorkspace();
            retireWorkspaceCapability();
            setWorkspaceKey((value) => value + 1);
          }
          authEpochRef.current = capturedGate.syncGate({
            locked: false,
            advanceEpoch: true,
            ownerId: session.user_id,
          });
          ensureWorkspaceCapability(capturedGate, session.user_id);
          commitState({
            status: "authenticated",
            session,
            csrfToken,
          });
        } catch {
          if (
            attempt !== generation.current ||
            !isActiveProvider(capturedGate)
          ) {
            return;
          }
          commitState({
            status: "unauthenticated",
            retainedIdentity,
            message: serviceFailureMessage(),
          });
        }
      });
    },
    [
      commitState,
      ensureWorkspaceCapability,
      isActiveProvider,
      retireWorkspaceCapability,
    ],
  );

  const discardRetainedSession = useCallback(() => {
    const capturedGate = providerGateRef.current;
    if (!isActiveProvider(capturedGate) || !capturedGate) {
      return Promise.resolve();
    }
    const capturedWorkspace = getProtectedWorkspaceGeneration();
    return enqueueAuthCookieOperation(() => {
      if (
        !isActiveProvider(capturedGate) ||
        getProtectedWorkspaceGeneration() !== capturedWorkspace
      ) {
        return Promise.resolve();
      }
      const current = stateRef.current;
      if (
        (current.status !== "unauthenticated" &&
          current.status !== "submitting-login") ||
        !current.retainedIdentity
      ) {
        return Promise.resolve();
      }
      generation.current += 1;
      authEpochRef.current = capturedGate.invalidateWorkspace();
      retireWorkspaceCapability();
      setWorkspaceKey((value) => value + 1);
      commitState({ status: "unauthenticated" });
      return Promise.resolve();
    });
  }, [commitState, isActiveProvider, retireWorkspaceCapability]);

  const logOut = useCallback(() => {
    const capturedGate = providerGateRef.current;
    const initialState = stateRef.current;
    if (
      changingPassword.current ||
      !isActiveProvider(capturedGate) ||
      !capturedGate ||
      (initialState.status !== "authenticated" &&
        initialState.status !== "logout-failed")
    ) {
      return Promise.resolve();
    }
    const originatingWorkspace = getProtectedWorkspaceGeneration();
    const originatingOwnerId = initialState.session.user_id;

    return enqueueAuthCookieOperation(async () => {
      const current = stateRef.current;
      if (
        changingPassword.current ||
        !isActiveProvider(capturedGate) ||
        getProtectedWorkspaceGeneration() !== originatingWorkspace ||
        (current.status !== "authenticated" &&
          current.status !== "logout-failed") ||
        current.session.user_id !== originatingOwnerId
      ) {
        return;
      }
      const attempt = ++generation.current;
      const { session } = current;
      let csrfToken = current.csrfToken;
      authEpochRef.current = capturedGate.syncGate({
        locked: true,
        advanceEpoch: true,
        ownerId: session.user_id,
      });
      commitState({ status: "logging-out", session, csrfToken });
      try {
        if (isNativeBearerTransport()) {
          try {
            await revokeCurrentDeviceSession();
          } catch (error: unknown) {
            if (
              attempt !== generation.current ||
              !isActiveProvider(capturedGate)
            ) {
              return;
            }
            if (!(error instanceof ApiError && error.status === 401)) {
              throw error;
            }
          }
          await clearNativeBearerToken();
        } else {
          try {
            await logout(csrfToken);
          } catch (error: unknown) {
            if (
              attempt !== generation.current ||
              !isActiveProvider(capturedGate)
            ) {
              return;
            }
            if (
              !(error instanceof ApiError) ||
              (error.status !== 401 && error.status !== 403)
            ) {
              throw error;
            }
            let live;
            try {
              live = await getSession();
            } catch (probeError: unknown) {
              if (
                attempt !== generation.current ||
                !isActiveProvider(capturedGate)
              ) {
                return;
              }
              if (probeError instanceof ApiError && probeError.status === 401) {
                authEpochRef.current = capturedGate.invalidateWorkspace();
                retireWorkspaceCapability();
                setWorkspaceKey((value) => value + 1);
                commitState({ status: "unauthenticated" });
                return;
              }
              throw probeError;
            }
            if (
              attempt !== generation.current ||
              !isActiveProvider(capturedGate)
            ) {
              return;
            }
            if (!live.owner || live.user_id !== session.user_id) {
              throw error;
            }
            csrfToken = (await recoverCsrf()).csrf_token;
            if (
              attempt !== generation.current ||
              !isActiveProvider(capturedGate)
            ) {
              return;
            }
            await logout(csrfToken);
          }
        }
        if (attempt === generation.current && isActiveProvider(capturedGate)) {
          authEpochRef.current = capturedGate.invalidateWorkspace();
          retireWorkspaceCapability();
          setWorkspaceKey((value) => value + 1);
          commitState({ status: "unauthenticated" });
        }
      } catch {
        if (attempt !== generation.current || !isActiveProvider(capturedGate)) {
          return;
        }
        commitState({
          status: "logout-failed",
          message:
            "Logout could not be confirmed. Your server session may still be active.",
          session,
          csrfToken,
        });
      }
    });
  }, [commitState, isActiveProvider, retireWorkspaceCapability]);

  const submitPassword = useCallback(
    (payload: ChangePasswordRequest) => {
      const capturedGate = providerGateRef.current;
      const initialState = stateRef.current;
      if (
        isNativeBearerTransport() ||
        !isActiveProvider(capturedGate) ||
        !capturedGate ||
        initialState.status !== "authenticated" ||
        !initialState.session.owner ||
        changingPassword.current
      ) {
        return Promise.resolve(false);
      }
      const originatingWorkspace = getProtectedWorkspaceGeneration();
      const originatingOwnerId = initialState.session.user_id;

      return enqueueAuthCookieOperation(async () => {
        const current = stateRef.current;
        if (
          !isActiveProvider(capturedGate) ||
          getProtectedWorkspaceGeneration() !== originatingWorkspace ||
          current.status !== "authenticated" ||
          !current.session.owner ||
          current.session.user_id !== originatingOwnerId ||
          changingPassword.current
        ) {
          return false;
        }
        const attempt = ++generation.current;
        changingPassword.current = true;
        setPasswordChangePending(true);
        try {
          const response = await changePassword(payload, current.csrfToken);
          if (
            attempt !== generation.current ||
            !isActiveProvider(capturedGate)
          ) {
            return false;
          }
          authEpochRef.current = capturedGate.syncGate({
            locked: false,
            advanceEpoch: true,
            ownerId: current.session.user_id,
          });
          commitState({ ...current, csrfToken: response.csrf_token });
          return true;
        } catch (error: unknown) {
          if (
            attempt !== generation.current ||
            !isActiveProvider(capturedGate)
          ) {
            return false;
          }
          if (error instanceof ApiError && error.status === 401) {
            expireAuthenticatedSession();
            return false;
          }
          throw error;
        } finally {
          changingPassword.current = false;
          setPasswordChangePending(false);
        }
      });
    },
    [commitState, expireAuthenticatedSession, isActiveProvider],
  );

  const passwordChange = useMemo(
    () => ({ pending: passwordChangePending, submit: submitPassword }),
    [passwordChangePending, submitPassword],
  );

  const sessionExpired = useCallback(() => {
    expireAuthenticatedSession();
  }, [expireAuthenticatedSession]);

  const retryRestoration = useCallback(() => {
    const capturedGate = providerGateRef.current;
    if (!isActiveProvider(capturedGate) || !capturedGate) return;
    generation.current += 1;
    authEpochRef.current = capturedGate.invalidateWorkspace();
    retireWorkspaceCapability();
    setRestorationAttempt((attempt) => attempt + 1);
  }, [isActiveProvider, retireWorkspaceCapability]);

  const cancelLogout = useCallback(() => {
    const capturedGate = providerGateRef.current;
    if (!isActiveProvider(capturedGate) || !capturedGate) return;
    const current = stateRef.current;
    if (current.status === "logout-failed") {
      generation.current += 1;
      authEpochRef.current = capturedGate.syncGate({
        locked: false,
        advanceEpoch: true,
        ownerId: current.session.user_id,
      });
      ensureWorkspaceCapability(capturedGate, current.session.user_id);
      commitState({
        status: "authenticated",
        session: current.session,
        csrfToken: current.csrfToken,
      });
    }
  }, [commitState, ensureWorkspaceCapability, isActiveProvider]);

  const value = useMemo<AuthContextValue>(
    () => ({
      state,
      capability,
      workspaceKey,
      logIn,
      reauthenticate,
      discardRetainedSession,
      logOut,
      sessionExpired,
      retryRestoration,
      cancelLogout,
    }),
    [
      cancelLogout,
      capability,
      discardRetainedSession,
      logIn,
      logOut,
      reauthenticate,
      retryRestoration,
      sessionExpired,
      state,
      workspaceKey,
    ],
  );

  return (
    <AuthContext.Provider value={value}>
      <PasswordChangeContext.Provider value={passwordChange}>
        {children}
      </PasswordChangeContext.Provider>
    </AuthContext.Provider>
  );
}
