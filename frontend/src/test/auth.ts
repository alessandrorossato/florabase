import { act, render, type RenderResult } from "@testing-library/react";
import { createElement, useEffect, type ReactElement } from "react";
import { createRoot } from "react-dom/client";
import { afterEach } from "vitest";
import type { ProtectedRequestCapability, SessionResponse } from "../auth/api";
import { AuthProvider } from "../auth/AuthProvider";
import { useAuth, type AuthContextValue } from "../auth/context";

export function defaultTestSession(
  overrides: Partial<SessionResponse> = {},
): SessionResponse {
  return {
    user_id: "00000000-0000-0000-0000-000000000001",
    login_name: "grower",
    display_name: "Test Grower",
    owner: true,
    canonical_origin: "http://localhost",
    ...overrides,
  };
}

const activeTeardowns = new Set<() => void>();

export function cleanupTestAuth(): void {
  for (const teardown of [...activeTeardowns]) {
    teardown();
  }
  activeTeardowns.clear();
}

afterEach(() => {
  cleanupTestAuth();
});

export interface AcquiredTestAuth {
  readonly capability: ProtectedRequestCapability;
  readonly auth: AuthContextValue;
  readonly session: SessionResponse;
  readonly csrfToken: string;
  unmount: () => void;
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function requestPathname(input: RequestInfo | URL): string {
  const raw =
    input instanceof Request
      ? input.url
      : input instanceof URL
        ? input.href
        : input;
  try {
    return new URL(raw, "http://localhost").pathname;
  } catch {
    return raw;
  }
}

/**
 * Mounts a real `<AuthProvider>` against mock session + CSRF transport so tests
 * receive a genuine module-tracked capability without exposing any production test issuer.
 */
export async function acquireTestAuth({
  session: sessionOverrides,
  csrfToken = "test-csrf",
}: {
  session?: Partial<SessionResponse>;
  csrfToken?: string;
} = {}): Promise<AcquiredTestAuth> {
  cleanupTestAuth();

  const session = defaultTestSession(sessionOverrides);
  const prevFetch = globalThis.fetch;
  globalThis.fetch = (input, init) => {
    const path = requestPathname(input);
    const method = (
      init?.method ?? (input instanceof Request ? input.method : "GET")
    ).toUpperCase();
    if (path === "/api/v1/auth/session" && method === "GET") {
      return Promise.resolve(jsonResponse(session));
    }
    if (path === "/api/v1/auth/csrf" && method === "POST") {
      return Promise.resolve(jsonResponse({ csrf_token: csrfToken }));
    }
    return Promise.resolve(jsonResponse({ detail: "Not found" }, 404));
  };

  const container = document.createElement("div");
  document.body.append(container);
  const root = createRoot(container);
  const captured: { auth: AuthContextValue | null } = { auth: null };

  function CaptureAuth() {
    const value = useAuth();
    useEffect(() => {
      captured.auth = value;
    }, [value]);
    return null;
  }

  let tornDown = false;
  const unmount = () => {
    if (tornDown) return;
    tornDown = true;
    activeTeardowns.delete(unmount);
    act(() => {
      root.unmount();
    });
    container.remove();
  };
  activeTeardowns.add(unmount);

  try {
    await act(async () => {
      root.render(
        createElement(AuthProvider, null, createElement(CaptureAuth)),
      );
      await Promise.resolve();
      await Promise.resolve();
      await Promise.resolve();
    });
  } finally {
    globalThis.fetch = prevFetch;
  }

  if (!captured.auth) {
    unmount();
    throw new Error("Failed to initialize test AuthProvider context");
  }
  const resolvedAuth: AuthContextValue = captured.auth;
  if (resolvedAuth.state.status !== "authenticated") {
    unmount();
    throw new Error(
      `Expected authenticated test AuthProvider state, got ${resolvedAuth.state.status}`,
    );
  }

  return {
    capability: resolvedAuth.capability,
    auth: resolvedAuth,
    session,
    csrfToken,
    unmount,
  };
}

/**
 * Renders UI inside a real `<AuthProvider>` that restores against mock `/auth/session`
 * and `/auth/csrf` endpoints and forwards remaining fetches to `prevFetch` (or `fetchHandler`).
 */
export async function renderWithTestAuth(
  ui: ReactElement,
  {
    session: sessionOverrides,
    csrfToken = "test-csrf",
    fetchHandler,
  }: {
    session?: Partial<SessionResponse>;
    csrfToken?: string;
    fetchHandler?: typeof fetch;
  } = {},
): Promise<RenderResult & { getAuth: () => AuthContextValue }> {
  cleanupTestAuth();

  const session = defaultTestSession(sessionOverrides);
  const prevFetch = globalThis.fetch;
  let restored = false;
  const restoreFetch = () => {
    if (restored || fetchHandler) return;
    restored = true;
    globalThis.fetch = prevFetch;
  };

  let latestAuth: AuthContextValue | null = null;
  function Bridge() {
    const value = useAuth();
    useEffect(() => {
      latestAuth = value;
    }, [value]);
    if (value.state.status !== "authenticated") return null;
    return ui;
  }

  globalThis.fetch = (input, init) => {
    const path = requestPathname(input);
    const method = (
      init?.method ?? (input instanceof Request ? input.method : "GET")
    ).toUpperCase();
    if (path === "/api/v1/auth/session" && method === "GET") {
      return Promise.resolve(jsonResponse(session));
    }
    if (path === "/api/v1/auth/csrf" && method === "POST") {
      return Promise.resolve(jsonResponse({ csrf_token: csrfToken }));
    }
    if (fetchHandler) {
      return fetchHandler(input, init);
    }
    return prevFetch(input, init);
  };

  const restoreCustomFetch = () => {
    if (fetchHandler) {
      globalThis.fetch = prevFetch;
    }
  };
  activeTeardowns.add(restoreCustomFetch);

  let rendered: RenderResult;
  try {
    rendered = render(createElement(AuthProvider, null, createElement(Bridge)));
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
      await Promise.resolve();
    });
  } finally {
    restoreFetch();
  }

  return {
    ...rendered,
    getAuth: () => {
      if (!latestAuth) throw new Error("AuthContext not initialized");
      return latestAuth;
    },
  };
}
