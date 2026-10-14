import {
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
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
function settings(focusQr = false) {
  return render(
    <AuthContext.Provider value={state}>
      <SettingsScreen focusQr={focusQr} />
    </AuthContext.Provider>,
  );
}
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.clearAllMocks();
  window.history.replaceState(null, "", "/");
});

test("read, save normalized QR destination with CSRF, remount persisted value and clear explicitly", async () => {
  let saved = {
    public_qr_base_url: null as string | null,
    default_label_preset: "medium",
  };
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation((_path, init) => {
      if (init?.method === "PUT") {
        const sent = JSON.parse(init.body as string) as typeof saved;
        saved = {
          ...sent,
          public_qr_base_url:
            sent.public_qr_base_url?.replace(/\/$/, "").toLowerCase() ?? null,
        };
      }
      return Promise.resolve(json(saved));
    });
  const user = userEvent.setup();
  const first = settings();
  const input = await screen.findByRole("textbox", {
    name: "Public / QR base URL",
  });
  expect(input).toHaveValue("");
  await user.type(input, "https://FLORA.example/");
  await user.click(screen.getByRole("button", { name: "Save settings" }));
  expect(await screen.findByRole("status")).toHaveTextContent(
    "Application settings saved",
  );
  expect(input).toHaveValue("https://flora.example");
  expect(
    new Headers(
      fetch.mock.calls.find(([, init]) => init?.method === "PUT")?.[1]?.headers,
    ).get("X-CSRF-Token"),
  ).toBe("csrf");
  first.unmount();
  settings();
  const again = await screen.findByRole("textbox", {
    name: "Public / QR base URL",
  });
  expect(again).toHaveValue("https://flora.example");
  await user.clear(again);
  await user.click(screen.getByRole("button", { name: "Save settings" }));
  await waitFor(() => {
    expect(saved.public_qr_base_url).toBeNull();
  });
});

test("one page contains General and Tools without tabs or a duplicate label preference", async () => {
  let saved = {
    public_qr_base_url: "https://flora.example",
    default_label_preset: "medium",
  };
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation((_path, init) => {
      if (init?.method === "PUT")
        saved = JSON.parse(init.body as string) as typeof saved;
      return Promise.resolve(json(saved));
    });
  settings();
  const user = userEvent.setup();
  const input = await screen.findByRole("textbox", {
    name: "Public / QR base URL",
  });
  expect(screen.getByRole("heading", { name: "General" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Tools" })).toBeVisible();
  expect(
    screen.queryByRole("navigation", { name: "Settings sections" }),
  ).not.toBeInTheDocument();
  expect(screen.queryByText("Labels & printing")).not.toBeInTheDocument();
  expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Labels" })).toHaveAttribute(
    "href",
    "#/labels",
  );
  expect(screen.getByRole("link", { name: "Import / Export" })).toHaveAttribute(
    "href",
    "#/import-export",
  );
  // A default saved in Labels after this page loaded must survive a QR URL save.
  saved.default_label_preset = "large";
  await user.clear(input);
  await user.type(input, "https://new.example");
  await user.click(screen.getByRole("button", { name: "Save settings" }));
  await screen.findByText("Application settings saved.");
  const body = fetch.mock.calls.find(([, init]) => init?.method === "PUT")?.[1]
    ?.body;
  expect(JSON.parse(body as string)).toEqual({
    public_qr_base_url: "https://new.example",
    default_label_preset: "large",
  });
});

test("invalid URL response and failed save retain edits; retry and auth failure are actionable", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation((_path, init) =>
      Promise.resolve(
        json(
          init?.method === "PUT"
            ? {}
            : { public_qr_base_url: null, default_label_preset: "medium" },
          init?.method === "PUT" ? 422 : 200,
        ),
      ),
    );
  settings();
  const user = userEvent.setup();
  const input = await screen.findByRole("textbox", {
    name: "Public / QR base URL",
  });
  await user.type(input, "https://flora.example/path");
  await user.click(screen.getByRole("button", { name: "Save settings" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "no credentials, path, query or fragment",
  );
  expect(input).toHaveValue("https://flora.example/path");
  fetch.mockImplementation(() => Promise.resolve(json({}, 500)));
  cleanup();
  settings();
  await screen.findByRole("alert");
  fetch.mockImplementation(() =>
    Promise.resolve(
      json({ public_qr_base_url: null, default_label_preset: "medium" }),
    ),
  );
  await user.click(screen.getByRole("button", { name: "Retry" }));
  await screen.findByRole("textbox");
  cleanup();
  fetch.mockImplementation(() => Promise.resolve(json({}, 401)));
  settings();
  await waitFor(() => {
    expect(expired).toHaveBeenCalled();
  });
});

test("Settings deep links and Tools replace the primary Tools macro-category, preserving routes", async () => {
  window.history.replaceState(null, "", "#/settings?tab=tools");
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
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
              ? { public_qr_base_url: null, default_label_preset: "medium" }
              : { status: "ok" },
      ),
    );
  });
  render(<App />);
  await screen.findByRole(
    "heading",
    { name: "Settings", level: 2 },
    { timeout: 5000 },
  );
  const nav = screen.getByRole("navigation", { name: "Primary navigation" });
  expect(
    within(nav).queryByRole("region", { name: "Tools" }),
  ).not.toBeInTheDocument();
  expect(
    within(nav).queryByRole("link", { name: "Labels" }),
  ).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Labels" })).toHaveAttribute(
    "href",
    "#/labels",
  );
  expect(screen.getByRole("link", { name: "Import / Export" })).toHaveAttribute(
    "href",
    "#/import-export",
  );
  expect(screen.getByRole("link", { name: "Settings" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  expect(
    screen.queryByRole("navigation", { name: "Settings sections" }),
  ).not.toBeInTheDocument();
  expect(
    await screen.findByRole("textbox", { name: "Public / QR base URL" }),
  ).toBeVisible();
  expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
});

test("direct QR Settings navigation focuses the General field and keeps Tools available", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    json({ public_qr_base_url: null, default_label_preset: "medium" }),
  );
  settings(true);
  expect(
    await screen.findByRole("textbox", { name: "Public / QR base URL" }),
  ).toHaveFocus();
  expect(screen.getByRole("link", { name: "Labels" })).toBeVisible();
});
