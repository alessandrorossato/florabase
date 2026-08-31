import type { components } from "../api/schema";

export type LoginRequest = components["schemas"]["LoginRequest"];
export type LoginResponse = components["schemas"]["LoginResponse"];
export type SessionResponse = components["schemas"]["SessionResponse"];
export type CsrfResponse = components["schemas"]["CsrfResponse"];

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly retryAfter: string | null = null,
    readonly body?: unknown,
  ) {
    super(`API request failed with HTTP ${String(status)}`);
  }
}

export async function requestJson<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
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

export function getSession(signal?: AbortSignal): Promise<SessionResponse> {
  return requestJson("/api/v1/auth/session", { signal });
}

export function recoverCsrf(signal?: AbortSignal): Promise<CsrfResponse> {
  return requestJson("/api/v1/auth/csrf", { method: "POST", signal });
}

export function login(
  payload: LoginRequest,
  signal?: AbortSignal,
): Promise<LoginResponse> {
  return requestJson("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
}

export async function logout(csrfToken: string): Promise<void> {
  await requestJson("/api/v1/auth/logout", {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
  });
}
