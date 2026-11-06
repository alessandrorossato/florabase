import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import { App } from "../App";
import { AuthContext, type AuthContextValue } from "../auth/context";
import { SettingsScreen } from "./SettingsScreen";

const expired = vi.fn();
const state: AuthContextValue = {
  state: {
    status: "authenticated",
    csrfToken: "csrf",
    session: {
      user_id: "01900000-0000-7000-8000-000000000001",
      login_name: "owner",
      display_name: "Owner",
      owner: true,
      canonical_origin: "https://security.example",
    },
  },
  logIn: vi.fn(),
  logOut: vi.fn(),
  sessionExpired: expired,
  retryRestoration: vi.fn(),
  cancelLogout: vi.fn(),
};
function json(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
function pathOf(input: RequestInfo | URL) {
  return typeof input === "string"
    ? input
    : input instanceof URL
      ? input.toString()
      : input.url;
}
function theme() {
  return render(
    <AuthContext.Provider value={state}>
      <SettingsScreen />
    </AuthContext.Provider>,
  );
}
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.clearAllMocks();
  window.history.replaceState(null, "", "/");
});

function appFetch(baseUrl: string | null = null) {
  return vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const path = pathOf(input);
    return Promise.resolve(
      json(
        path.endsWith("/session")
          ? (
              state.state as Extract<
                typeof state.state,
                { status: "authenticated" }
              >
            ).session
          : path.endsWith("/csrf")
            ? { csrf_token: "csrf" }
            : path.endsWith("application-settings")
              ? { public_qr_base_url: baseUrl, default_label_preset: "medium" }
              : path.includes("/api/v1/")
                ? []
                : { status: "ok" },
      ),
    );
  });
}

test("Theme holds only palette and appearance, needs no server settings and repeats no tools", async () => {
  const fetch = vi.spyOn(globalThis, "fetch");
  theme();
  expect(screen.getByRole("heading", { name: "Theme" })).toBeVisible();
  expect(
    screen.queryByRole("textbox", { name: "Public / QR base URL" }),
  ).not.toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "General" })).toBeNull();
  expect(screen.queryByRole("heading", { name: "Tools" })).toBeNull();
  expect(screen.queryByRole("link", { name: "Labels" })).toBeNull();
  expect(screen.queryByRole("link", { name: "Import / Export" })).toBeNull();
  const user = userEvent.setup();
  await user.click(screen.getByRole("radio", { name: "Herbarium" }));
  await user.click(screen.getByRole("radio", { name: "Dark" }));
  expect(document.documentElement).toHaveAttribute("data-palette", "herbarium");
  expect(document.documentElement).toHaveAttribute("data-appearance", "dark");
  expect(screen.getByRole("radio", { name: "Dark" })).toHaveFocus();
  expect(fetch).not.toHaveBeenCalled();
});

test("#/settings stays valid as Theme; the Settings workspace lists Theme, Labels and Import / Export once", async () => {
  window.history.replaceState(null, "", "#/settings");
  appFetch();
  render(<App />);
  await screen.findByRole(
    "heading",
    { name: "Theme", level: 2 },
    { timeout: 5000 },
  );
  expect(window.location.hash).toBe("#/settings");
  const nav = screen.getByRole("navigation", { name: "Primary navigation" });
  expect(within(nav).getByRole("link", { name: "Theme" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  expect(within(nav).getAllByRole("link", { name: "Labels" })).toHaveLength(1);
  expect(within(nav).getByRole("link", { name: "Labels" })).toHaveAttribute(
    "href",
    "#/labels",
  );
  expect(
    within(nav).getAllByRole("link", { name: "Import / Export" }),
  ).toHaveLength(1);
  expect(within(nav).queryByRole("link", { name: "Settings" })).toBeNull();
  const content = screen.getByRole("region", { name: "Workspace content" });
  expect(within(content).queryByRole("link", { name: "Labels" })).toBeNull();
  expect(
    within(content).queryByRole("textbox", { name: "Public / QR base URL" }),
  ).toBeNull();
});

test("the former Settings QR address opens the QR destination in Labels and replaces the address", async () => {
  window.history.replaceState(null, "", "#/settings?tab=general");
  appFetch("https://flora.example");
  render(<App />);
  const field = await screen.findByRole(
    "textbox",
    { name: "Public / QR base URL" },
    { timeout: 5000 },
  );
  expect(field).toHaveValue("https://flora.example");
  expect(screen.getByRole("dialog", { name: "QR destination" })).toBeVisible();
  expect(window.location.hash).toBe("#/labels");
  expect(
    screen.getByRole("heading", { name: "Labels", level: 2 }),
  ).toBeVisible();
  const nav = screen.getByRole("navigation", { name: "Primary navigation" });
  expect(within(nav).getByRole("link", { name: "Labels" })).toHaveAttribute(
    "aria-current",
    "page",
  );
});
