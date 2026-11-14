import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { useContext } from "react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";

import { App } from "../App";
import { AuthProvider } from "../auth/AuthProvider";
import { PasswordChangeContext, useAuth } from "../auth/context";

const session = {
  user_id: "01900000-0000-7000-8000-000000000001",
  login_name: "owner",
  owner: true,
  display_name: "Owner",
  canonical_origin: "https://florabase.example",
};

function json(body: unknown, status = 200, headers?: HeadersInit) {
  return new Response(JSON.stringify(body), { status, headers });
}

function pathname(input: RequestInfo | URL) {
  return typeof input === "string"
    ? input
    : input instanceof URL
      ? input.pathname
      : input.url;
}

afterEach(() => {
  cleanup();
  window.history.replaceState(null, "", "/");
  vi.restoreAllMocks();
});

test("Account validates, clears submitted fields, updates CSRF, and releases the departure guard", async () => {
  window.history.replaceState(null, "", "#/account");
  let complete!: (response: Response) => void;
  const request = new Promise<Response>((resolve) => {
    complete = resolve;
  });
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const path = pathname(input);
    if (path.endsWith("/password")) return request;
    if (path.endsWith("/session")) return Promise.resolve(json(session));
    if (path.endsWith("/csrf"))
      return Promise.resolve(json({ csrf_token: "old-token" }));
    if (path.endsWith("/logout"))
      return Promise.resolve(json({ status: "ok" }));
    return Promise.resolve(json([]));
  });
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  const user = userEvent.setup();
  render(<App />);
  const current = await screen.findByLabelText("Current password");
  const next = screen.getByLabelText("New password", { exact: true });
  const repeat = screen.getByLabelText("Confirm new password");
  expect(current).toHaveAttribute("autocomplete", "current-password");
  expect(next).toHaveAttribute("autocomplete", "new-password");
  await user.type(current, "synthetic current");
  await user.type(next, "synthetic replacement");
  const theme = screen.getByRole("link", { name: "Theme" });
  await user.click(theme);
  expect(confirm).toHaveBeenCalledTimes(1);
  expect(window.location.hash).toBe("#/account");
  await user.click(screen.getByRole("button", { name: "Change password" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("do not match");
  expect(repeat).toHaveFocus();
  await user.type(repeat, "synthetic replacement");
  await user.click(screen.getByRole("button", { name: "Change password" }));
  expect(screen.getByRole("button", { name: "Sign out" })).toBeDisabled();
  expect(current).toHaveValue("");
  expect(next).toHaveValue("");
  expect(repeat).toHaveValue("");
  const call = fetch.mock.calls.find(([input]) =>
    pathname(input).endsWith("/password"),
  );
  expect(new Headers(call?.[1]?.headers).get("X-CSRF-Token")).toBe("old-token");
  expect(call?.[1]?.body).toBe(
    JSON.stringify({
      current_password: "synthetic current",
      new_password: "synthetic replacement",
    }),
  );
  complete(json({ csrf_token: "new-token" }));
  expect(await screen.findByText("Password changed.")).toBeVisible();
  await user.click(theme);
  await screen.findByRole("heading", { name: "Theme", level: 2 });
  expect(confirm).toHaveBeenCalledTimes(1);
  await user.click(screen.getByRole("button", { name: "Sign out" }));
  const logout = fetch.mock.calls.find(([input]) =>
    pathname(input).endsWith("/logout"),
  );
  expect(new Headers(logout?.[1]?.headers).get("X-CSRF-Token")).toBe(
    "new-token",
  );
});

function AuthProbe() {
  const auth = useAuth();
  return (
    <>
      <output>{auth.state.status}</output>
      <button onClick={() => void auth.logOut()}>Test sign out</button>
    </>
  );
}

test.each([401, 403])(
  "logout %s retries once using the same owner's replacement CSRF",
  async (first) => {
    const logoutTokens: (string | null)[] = [];
    let recoveries = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
      const path = pathname(input);
      if (path.endsWith("/session")) return Promise.resolve(json(session));
      if (path.endsWith("/csrf"))
        return Promise.resolve(
          json({ csrf_token: `csrf-${String(++recoveries)}` }),
        );
      if (path.endsWith("/logout")) {
        logoutTokens.push(new Headers(init?.headers).get("X-CSRF-Token"));
        return Promise.resolve(
          json({}, logoutTokens.length === 1 ? first : 200),
        );
      }
      throw new Error("Unexpected request");
    });
    const user = userEvent.setup();
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );
    await screen.findByText("authenticated");
    await user.click(screen.getByRole("button", { name: "Test sign out" }));
    await screen.findByText("unauthenticated");
    expect(logoutTokens).toEqual(["csrf-1", "csrf-2"]);
  },
);

test("logout with no current cookie ends locally without recovery or a retry", async () => {
  let sessions = 0;
  let logouts = 0;
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const path = pathname(input);
    if (path.endsWith("/session"))
      return Promise.resolve(++sessions === 1 ? json(session) : json({}, 401));
    if (path.endsWith("/csrf"))
      return Promise.resolve(json({ csrf_token: "old" }));
    if (path.endsWith("/logout")) {
      logouts++;
      return Promise.resolve(json({}, 401));
    }
    throw new Error("Unexpected request");
  });
  const user = userEvent.setup();
  render(
    <AuthProvider>
      <AuthProbe />
    </AuthProvider>,
  );
  await screen.findByText("authenticated");
  await user.click(screen.getByRole("button", { name: "Test sign out" }));
  await screen.findByText("unauthenticated");
  expect(logouts).toBe(1);
});

test("a password response cannot restore an expired provider generation", async () => {
  let complete!: (response: Response) => void;
  const pending = new Promise<Response>((resolve) => {
    complete = resolve;
  });
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const path = pathname(input);
    if (path.endsWith("/password")) return pending;
    if (path.endsWith("/session")) return Promise.resolve(json(session));
    if (path.endsWith("/csrf"))
      return Promise.resolve(json({ csrf_token: "old" }));
    throw new Error("Unexpected request");
  });

  function Probe() {
    const auth = useAuth();
    const change = useContext(PasswordChangeContext);
    return (
      <>
        <output>{auth.state.status}</output>
        <button
          disabled={!change || change.pending}
          onClick={() => {
            void change?.submit({
              current_password: "synthetic current",
              new_password: "synthetic replacement",
            });
          }}
        >
          Submit change
        </button>
        <button onClick={auth.sessionExpired}>Expire session</button>
      </>
    );
  }

  render(
    <AuthProvider>
      <Probe />
    </AuthProvider>,
  );
  const user = userEvent.setup();
  await screen.findByText("authenticated");
  await user.click(screen.getByRole("button", { name: "Submit change" }));
  await user.click(screen.getByRole("button", { name: "Expire session" }));
  complete(json({ csrf_token: "late" }));
  await waitFor(() => {
    expect(screen.getByRole("button", { name: "Submit change" })).toBeEnabled();
  });
  expect(screen.getByText("unauthenticated")).toBeVisible();
  expect(
    fetch.mock.calls.filter(([input]) => pathname(input).endsWith("/password")),
  ).toHaveLength(1);
});
