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

  it("checks /api/v1/health, persists URL, displays version and MOBILE-002 placeholder", async () => {
    const user = userEvent.setup();
    const store = createMemoryStore();
    const httpGet = vi.fn<HttpGetFn>((url) => {
      if (url === "http://10.0.2.2:5173/api/v1/health") {
        return Promise.resolve({ status: 200, data: { status: "ok" } });
      }
      if (url === "http://10.0.2.2:5173/release.json") {
        return Promise.resolve({
          status: 200,
          data: { version: "0.1.0-beta.7", revision: "d7e056b" },
        });
      }
      return Promise.resolve({ status: 404, data: "" });
    });

    render(
      <NativeServerOnboarding
        allowDebugHttp={true}
        store={store}
        httpGet={httpGet}
      />,
    );

    const input = await screen.findByLabelText(/server url/i);
    await user.type(input, "http://10.0.2.2:5173/");
    await user.click(screen.getByRole("button", { name: /check server/i }));

    expect(await screen.findByText(/server reachable/i)).toBeInTheDocument();
    expect(screen.getByText(/ok \(HTTP 200\)/i)).toBeInTheDocument();
    expect(screen.getByText("0.1.0-beta.7 (d7e056b)")).toBeInTheDocument();
    expect(
      screen.getByText("Sign-in for the app arrives in MOBILE-002."),
    ).toBeInTheDocument();
    expect(store.current()).toBe("http://10.0.2.2:5173");
  });

  it("handles dev servers where /api/v1/health has no version and /release.json is absent", async () => {
    const user = userEvent.setup();
    const store = createMemoryStore();
    const httpGet = vi.fn<HttpGetFn>((url) => {
      if (url.endsWith("/api/v1/health")) {
        return Promise.resolve({ status: 200, data: { status: "ok" } });
      }
      return Promise.resolve({
        status: 200,
        data: "<!doctype html><html></html>",
      });
    });

    render(
      <NativeServerOnboarding
        allowDebugHttp={true}
        store={store}
        httpGet={httpGet}
      />,
    );

    const input = await screen.findByLabelText(/server url/i);
    await user.type(input, "http://10.0.2.2:5173");
    await user.click(screen.getByRole("button", { name: /check server/i }));

    expect(
      await screen.findByText(/not reported by \/api\/v1\/health/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Sign-in for the app arrives in MOBILE-002."),
    ).toBeInTheDocument();
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
      />,
    );

    const input = await screen.findByLabelText(/server url/i);
    const submit = screen.getByRole("button", { name: /check server/i });

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
