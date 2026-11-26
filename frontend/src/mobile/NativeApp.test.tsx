import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  activeCsrfToken,
  downloadProtectedFile,
  openProtectedTab,
  type ProtectedRequestCapability,
} from "../auth/api";
import { resetAuthTransport } from "../auth/transport";
import {
  mapRuntimeConfig,
  resetMapRuntimeConfig,
} from "../provenance-map/config";
import type { HttpGetFn } from "./healthProbe";
import { NativeApp } from "./NativeApp";
import type { ServerUrlStore } from "./preferences";
import type { SecureTokenStore } from "./secureToken";

function createMemoryUrlStore(initial: string | null = null): ServerUrlStore {
  let value = initial;
  return {
    load: vi.fn(() => Promise.resolve(value)),
    save: vi.fn((next: string) => {
      value = next;
      return Promise.resolve();
    }),
    clear: vi.fn(() => {
      value = null;
      return Promise.resolve();
    }),
  };
}

function createMemoryTokenStore(
  initial: string | null = null,
  deviceLabel = "Pixel 9",
): SecureTokenStore & { current: () => string | null } {
  let token = initial;
  return {
    current: () => token,
    get: vi.fn(() => Promise.resolve(token)),
    set: vi.fn((next: string) => {
      token = next;
      return Promise.resolve();
    }),
    clear: vi.fn(() => {
      token = null;
      return Promise.resolve();
    }),
    getDeviceLabel: vi.fn(() => Promise.resolve(deviceLabel)),
  };
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function requestUrl(input: RequestInfo | URL): string {
  return typeof input === "string"
    ? input
    : input instanceof URL
      ? input.href
      : input.url;
}

const ownerSession = {
  user_id: "01900000-0000-7000-8000-000000000001",
  login_name: "owner",
  owner: true,
  display_name: "Owner",
  canonical_origin: "https://nas.example.com",
};

describe("NativeApp device sign-in and Keystore lifecycle", () => {
  afterEach(() => {
    cleanup();
    resetAuthTransport();
    resetMapRuntimeConfig();
    window.history.replaceState(null, "", "/");
    vi.restoreAllMocks();
  });

  it("signs in with prefilled Build.MODEL label, persists token only in Keystore, disables file actions, and hides password form", async () => {
    const user = userEvent.setup();
    const urlStore = createMemoryUrlStore("https://nas.example.com");
    const tokenStore = createMemoryTokenStore(null, "Pixel 9 Pro");
    const httpGet = vi.fn<HttpGetFn>((url) => {
      if (url === "https://nas.example.com/api/v1/health") {
        return Promise.resolve({ status: 200, data: { status: "ok" } });
      }
      if (url === "https://nas.example.com/api/v1/system/info") {
        return Promise.resolve({
          status: 200,
          data: {
            server_version: "0.1.0-beta.8",
            api_version: 1,
            min_client_version: "0.1.0-beta.8",
            capabilities: ["device-auth"],
          },
        });
      }
      return Promise.resolve({ status: 404, data: "" });
    });

    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation((input, init) => {
        const url =
          typeof input === "string"
            ? input
            : input instanceof URL
              ? input.href
              : input.url;
        const headers = new Headers(init?.headers);
        if (
          url === "https://nas.example.com/api/v1/auth/device-sessions" &&
          init?.method === "POST"
        ) {
          expect(init.credentials).toBe("omit");
          expect(headers.get("Authorization")).toBeNull();
          return Promise.resolve(
            jsonResponse(
              {
                session_id: "01900000-0000-7000-8000-000000000099",
                token: "opaque-device-token-secret",
                device_label: "Pixel 9 Pro",
                created_at: "2026-11-23T10:00:00Z",
                idle_expires_at: "2026-12-23T10:00:00Z",
                absolute_expires_at: "2027-05-22T10:00:00Z",
              },
              201,
            ),
          );
        }
        if (url === "https://nas.example.com/api/v1/auth/session") {
          expect(init?.credentials).toBe("omit");
          expect(headers.get("Authorization")).toBe(
            "Bearer opaque-device-token-secret",
          );
          return Promise.resolve(jsonResponse(ownerSession));
        }
        if (
          url === "https://nas.example.com/api/v1/auth/device-sessions" &&
          (!init?.method || init.method === "GET")
        ) {
          return Promise.resolve(
            jsonResponse({
              items: [
                {
                  id: "01900000-0000-7000-8000-000000000099",
                  device_label: "Pixel 9 Pro",
                  created_at: "2026-11-23T10:00:00Z",
                  last_seen_at: "2026-11-23T10:05:00Z",
                  idle_expires_at: "2026-12-23T10:00:00Z",
                  absolute_expires_at: "2027-05-22T10:00:00Z",
                  current: true,
                },
              ],
            }),
          );
        }
        if (url === "https://nas.example.com/api/v1/health") {
          return Promise.resolve(jsonResponse({ status: "ok" }));
        }
        return Promise.resolve(jsonResponse([]));
      });

    window.history.replaceState(null, "", "#/account");
    render(
      <NativeApp
        allowDebugHttp={false}
        urlStore={urlStore}
        tokenStore={tokenStore}
        httpGet={httpGet}
        appVersion="0.1.0-beta.8"
      />,
    );

    const deviceInput = await screen.findByLabelText(/device name/i);
    await waitFor(() => {
      expect(deviceInput).toHaveValue("Pixel 9 Pro");
    });

    await user.type(screen.getByLabelText(/login name/i), "owner");
    await user.type(screen.getByLabelText(/^password/i), "test-passphrase");
    await user.click(screen.getByRole("button", { name: /^sign in$/i }));

    expect(
      await screen.findByText("Change your password in the web app."),
    ).toBeVisible();
    expect(screen.queryByLabelText("Current password")).not.toBeInTheDocument();
    expect(await screen.findByText("Pixel 9 Pro")).toBeVisible();
    expect(screen.getByText("This device")).toBeVisible();

    // Token persisted only in Keystore plugin, never in localStorage or sessionStorage.
    expect(tokenStore.current()).toBe("opaque-device-token-secret");
    expect(JSON.stringify(window.localStorage)).not.toContain(
      "opaque-device-token-secret",
    );
    expect(JSON.stringify(window.sessionStorage)).not.toContain(
      "opaque-device-token-secret",
    );

    // No /api/v1/auth/csrf call should ever occur in Bearer mode.
    const csrfCalls = fetchSpy.mock.calls.filter(([req]) =>
      requestUrl(req).includes("/auth/csrf"),
    );
    expect(csrfCalls).toHaveLength(0);

    // In Bearer mode, authenticated state yields a non-empty token sentinel so
    // domain save handlers do not short-circuit on `if (!token) return;`, while
    // cookie mode keeps returning "" when csrfToken is empty.
    expect(
      activeCsrfToken({
        status: "authenticated",
        session: ownerSession,
        csrfToken: "",
      }),
    ).toBe("bearer");
    expect(activeCsrfToken({ status: "unauthenticated" })).toBe("");

    // Forged/unregistered capability is rejected before touching native file actions.
    const fakeCap = {} as ProtectedRequestCapability;
    await expect(
      downloadProtectedFile({
        path: "/api/v1/export/plants.csv",
        capability: fakeCap,
        fallbackFilename: "plants.csv",
      }),
    ).rejects.toThrow();
    await expect(
      openProtectedTab({
        path: "/api/v1/attachments/1/content",
        capability: fakeCap,
      }),
    ).rejects.toThrow();
  });

  it("shows native update banner when server_version is newer and applies sanitised runtime_config", async () => {
    const user = userEvent.setup();
    const urlStore = createMemoryUrlStore("https://nas.example.com");
    const tokenStore = createMemoryTokenStore("valid-token", "Pixel 9");
    const httpGet = vi.fn<HttpGetFn>((url) => {
      if (url.endsWith("/api/v1/health")) {
        return Promise.resolve({ status: 200, data: { status: "ok" } });
      }
      if (url.endsWith("/api/v1/system/info")) {
        return Promise.resolve({
          status: 200,
          data: {
            server_version: "0.1.0-beta.10",
            api_version: 1,
            min_client_version: "0.1.0-beta.8",
            capabilities: ["device-auth"],
            runtime_config: {
              map_online_enabled: true,
              map_tile_url: "https://tiles.example.org/{z}/{x}/{y}.png",
              map_attribution:
                '&copy; <a href="https://tiles.example.org">Tiles</a><script>evil()</script>',
            },
          },
        });
      }
      return Promise.resolve({ status: 404, data: "" });
    });

    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = requestUrl(input);
      if (url.endsWith("/api/v1/auth/session")) {
        return Promise.resolve(jsonResponse(ownerSession));
      }
      if (url.endsWith("/api/v1/health")) {
        return Promise.resolve(jsonResponse({ status: "ok" }));
      }
      return Promise.resolve(jsonResponse([]));
    });

    render(
      <NativeApp
        allowDebugHttp={false}
        urlStore={urlStore}
        tokenStore={tokenStore}
        httpGet={httpGet}
        appVersion="0.1.0-beta.9"
      />,
    );

    const banner = await screen.findByRole("complementary", {
      name: /florabase app update/i,
    });
    expect(banner).toBeVisible();
    expect(banner).toHaveTextContent(/0\.1\.0-beta\.10/);
    expect(banner).toHaveTextContent(/Obtainium/i);

    expect(mapRuntimeConfig).toEqual({
      onlineConfigured: true,
      tileUrl: "https://tiles.example.org/{z}/{x}/{y}.png",
      attribution:
        '© <a href="https://tiles.example.org/" rel="noopener noreferrer" target="_blank">Tiles</a>',
    });

    await user.click(screen.getByRole("button", { name: /^later$/i }));
    expect(
      screen.queryByRole("complementary", { name: /florabase app update/i }),
    ).not.toBeInTheDocument();
  });

  it("hides native update banner when app matches server_version and defaults maps offline", async () => {
    const urlStore = createMemoryUrlStore("https://nas.example.com");
    const tokenStore = createMemoryTokenStore("valid-token", "Pixel 9");
    const httpGet = vi.fn<HttpGetFn>((url) => {
      if (url.endsWith("/api/v1/health")) {
        return Promise.resolve({ status: 200, data: { status: "ok" } });
      }
      if (url.endsWith("/api/v1/system/info")) {
        return Promise.resolve({
          status: 200,
          data: {
            server_version: "0.1.0-beta.9",
            api_version: 1,
            min_client_version: "0.1.0-beta.8",
            capabilities: ["device-auth"],
          },
        });
      }
      return Promise.resolve({ status: 404, data: "" });
    });

    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = requestUrl(input);
      if (url.endsWith("/api/v1/auth/session")) {
        return Promise.resolve(jsonResponse(ownerSession));
      }
      if (url.endsWith("/api/v1/health")) {
        return Promise.resolve(jsonResponse({ status: "ok" }));
      }
      return Promise.resolve(jsonResponse([]));
    });

    render(
      <NativeApp
        allowDebugHttp={false}
        urlStore={urlStore}
        tokenStore={tokenStore}
        httpGet={httpGet}
        appVersion="0.1.0-beta.9"
      />,
    );

    await waitFor(() => {
      expect(mapRuntimeConfig.onlineConfigured).toBe(false);
    });
    expect(
      screen.queryByRole("complementary", { name: /florabase app update/i }),
    ).not.toBeInTheDocument();
  });

  it("clears Keystore token when a stored Bearer token receives 401 on boot", async () => {
    const urlStore = createMemoryUrlStore("https://nas.example.com");
    const tokenStore = createMemoryTokenStore("revoked-token", "Pixel 9");
    const httpGet = vi.fn<HttpGetFn>((url) => {
      if (url.endsWith("/api/v1/health")) {
        return Promise.resolve({ status: 200, data: { status: "ok" } });
      }
      if (url.endsWith("/api/v1/system/info")) {
        return Promise.resolve({
          status: 200,
          data: {
            server_version: "0.1.0-beta.8",
            api_version: 1,
            min_client_version: "0.1.0-beta.8",
            capabilities: ["device-auth"],
          },
        });
      }
      return Promise.resolve({ status: 404, data: "" });
    });

    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = requestUrl(input);
      if (url.endsWith("/api/v1/auth/session")) {
        return Promise.resolve(jsonResponse({ detail: "Unauthorized" }, 401));
      }
      return Promise.resolve(jsonResponse({ status: "ok" }));
    });

    render(
      <NativeApp
        allowDebugHttp={false}
        urlStore={urlStore}
        tokenStore={tokenStore}
        httpGet={httpGet}
        appVersion="0.1.0-beta.8"
      />,
    );

    expect(await screen.findByLabelText(/login name/i)).toBeVisible();
    await waitFor(() => {
      expect(tokenStore.current()).toBeNull();
    });
  });
});
