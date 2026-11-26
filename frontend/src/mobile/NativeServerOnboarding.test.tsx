import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { NativeServerOnboarding } from "./NativeServerOnboarding";
import type { HttpGetFn } from "./healthProbe";
import type { ServerUrlStore } from "./preferences";

function createMemoryStore(initial: string | null = null): ServerUrlStore & {
  current: () => string | null;
} {
  let value = initial;
  return {
    current: () => value,
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

describe("NativeServerOnboarding", () => {
  afterEach(() => {
    cleanup();
  });

  it("checks /api/v1/health and /api/v1/system/info, persists URL, and calls onConnected", async () => {
    const user = userEvent.setup();
    const store = createMemoryStore();
    const onConnected = vi.fn();
    const httpGet = vi.fn<HttpGetFn>((url) => {
      if (url === "http://10.0.2.2:5173/api/v1/health") {
        return Promise.resolve({ status: 200, data: { status: "ok" } });
      }
      if (url === "http://10.0.2.2:5173/api/v1/system/info") {
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

    render(
      <NativeServerOnboarding
        allowDebugHttp={true}
        store={store}
        httpGet={httpGet}
        appVersion="0.1.0-beta.8"
        onConnected={onConnected}
      />,
    );

    const input = await screen.findByLabelText(/server url/i);
    await user.type(input, "http://10.0.2.2:5173/");
    await user.click(screen.getByRole("button", { name: /^connect$/i }));

    await waitFor(() => {
      expect(onConnected).toHaveBeenCalledWith("http://10.0.2.2:5173", {
        serverVersion: "0.1.0-beta.8",
        apiVersion: 1,
        minClientVersion: "0.1.0-beta.8",
        capabilities: ["device-auth"],
        runtimeConfig: {
          mapOnlineEnabled: false,
          mapTileUrl: undefined,
          mapAttribution: undefined,
        },
      });
    });
    expect(store.current()).toBe("http://10.0.2.2:5173");
  });

  it("refuses sign-in when server lacks /api/v1/system/info or app version is below min_client_version", async () => {
    const user = userEvent.setup();
    const store = createMemoryStore();
    const onConnected = vi.fn();
    const httpGet = vi.fn<HttpGetFn>((url) => {
      if (url.endsWith("/api/v1/health")) {
        return Promise.resolve({ status: 200, data: { status: "ok" } });
      }
      if (url.endsWith("/api/v1/system/info")) {
        return Promise.resolve({ status: 404, data: { detail: "Not Found" } });
      }
      return Promise.resolve({ status: 404, data: "" });
    });

    render(
      <NativeServerOnboarding
        allowDebugHttp={true}
        store={store}
        httpGet={httpGet}
        appVersion="0.1.0-beta.8"
        onConnected={onConnected}
      />,
    );

    const input = await screen.findByLabelText(/server url/i);
    await user.type(input, "http://10.0.2.2:5173");
    await user.click(screen.getByRole("button", { name: /^connect$/i }));

    let alert = await screen.findByRole("alert");
    expect(alert).toHaveAttribute("data-error-category", "incompatible-server");
    expect(alert).toHaveTextContent(/does not support mobile device sign-in/i);
    expect(onConnected).not.toHaveBeenCalled();
    expect(store.current()).toBeNull();

    // Now return a server requiring beta.10 while app is beta.8
    httpGet.mockImplementation((url) => {
      if (url.endsWith("/api/v1/health")) {
        return Promise.resolve({ status: 200, data: { status: "ok" } });
      }
      if (url.endsWith("/api/v1/system/info")) {
        return Promise.resolve({
          status: 200,
          data: {
            server_version: "0.1.0-beta.10",
            api_version: 1,
            min_client_version: "0.1.0-beta.10",
            capabilities: ["device-auth"],
          },
        });
      }
      return Promise.resolve({ status: 404, data: "" });
    });

    await user.click(screen.getByRole("button", { name: /^connect$/i }));
    alert = await screen.findByRole("alert");
    expect(alert).toHaveAttribute("data-error-category", "incompatible-client");
    expect(alert).toHaveTextContent(/0\.1\.0-beta\.8.*0\.1\.0-beta\.10/i);
    expect(onConnected).not.toHaveBeenCalled();
    expect(store.current()).toBeNull();
  });

  it("shows distinct errors for invalid URL, unreachable host, TLS error, and non-Florabase response", async () => {
    const user = userEvent.setup();
    const store = createMemoryStore();
    const httpGet = vi.fn<HttpGetFn>();

    render(
      <NativeServerOnboarding
        allowDebugHttp={false}
        store={store}
        httpGet={httpGet}
        appVersion="0.1.0-beta.8"
      />,
    );

    const input = await screen.findByLabelText(/server url/i);
    const submit = screen.getByRole("button", { name: /^connect$/i });

    // 1. Invalid URL (HTTP rejected in release build)
    await user.type(input, "http://10.0.2.2:5173");
    await user.click(submit);
    let alert = await screen.findByRole("alert");
    expect(alert).toHaveAttribute("data-error-category", "invalid-url");
    expect(alert).toHaveTextContent(/HTTPS is required/i);
    expect(httpGet).not.toHaveBeenCalled();

    // 2. Unreachable host
    httpGet.mockRejectedValueOnce(new Error("Failed to connect to host"));
    await user.clear(input);
    await user.type(input, "https://unreachable.example.com");
    await user.click(submit);
    alert = await screen.findByRole("alert");
    expect(alert).toHaveAttribute("data-error-category", "unreachable");
    expect(alert).toHaveTextContent(/Server unreachable/i);

    // 3. Untrusted TLS CA
    httpGet.mockRejectedValueOnce(
      new Error("CertPathValidatorException: Trust anchor not found"),
    );
    await user.click(submit);
    alert = await screen.findByRole("alert");
    expect(alert).toHaveAttribute("data-error-category", "tls");
    expect(alert).toHaveTextContent(/Certificate not trusted/i);

    // 4. Non-Florabase server (HTML response or wrong JSON)
    httpGet.mockResolvedValueOnce({
      status: 200,
      data: "<html><body>Not Florabase</body></html>",
    });
    await user.click(submit);
    alert = await screen.findByRole("alert");
    expect(alert).toHaveAttribute("data-error-category", "non-florabase");
    expect(alert).toHaveTextContent(/Not a Florabase server/i);
    expect(store.current()).toBeNull();
  });

  it("loads and forgets a previously saved server URL", async () => {
    const user = userEvent.setup();
    const store = createMemoryStore("https://nas.example.com");

    render(
      <NativeServerOnboarding
        allowDebugHttp={false}
        store={store}
        httpGet={vi.fn()}
        appVersion="0.1.0-beta.8"
      />,
    );

    const input = await screen.findByLabelText(/server url/i);
    await waitFor(() => {
      expect(input).toHaveValue("https://nas.example.com");
    });

    await user.click(screen.getByRole("button", { name: /forget saved url/i }));
    await waitFor(() => {
      expect(input).toHaveValue("");
    });
    expect(store.current()).toBeNull();
  });
});
