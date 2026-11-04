import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../auth/context";
import { RecordSheet } from "./RecordSheet";

const plantId = "0190d2a8-0000-7000-8000-000000000002";
const sowingId = "0190d2a8-0000-7000-8000-000000000003";
const auth = {
  state: {
    status: "authenticated",
    session: {
      user_id: "u",
      login_name: "owner",
      display_name: null,
      owner: true,
      canonical_origin: "https://florabase.example",
    },
    csrfToken: "csrf",
  },
  logIn: vi.fn(),
  logOut: vi.fn(),
  sessionExpired: vi.fn(),
  retryRestoration: vi.fn(),
  cancelLogout: vi.fn(),
} as AuthContextValue;

const fetch = vi.fn((path: string) => {
  const kind = /targets\/(\w+)/.exec(path)?.[1] ?? "plant";
  const id = kind === "sowing" ? sowingId : plantId;
  const label = kind === "sowing" ? "Spring tray" : "Basil mother";
  return Promise.resolve(
    new Response(
      JSON.stringify({
        items: [{ kind, id, label, lifecycle: "active" }],
        total: 1,
      }),
      { headers: { "Content-Type": "application/json" } },
    ),
  );
});
beforeEach(() => {
  vi.stubGlobal("fetch", fetch);
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  fetch.mockClear();
});

/** A navigator that keeps its prototype and adds a stub camera API. */
function withMedia(mediaDevices: object): Navigator {
  return Object.create(navigator, {
    mediaDevices: { value: mediaDevices },
  }) as Navigator;
}

function mount(hash = "#/dashboard") {
  const follow = vi.fn((event: { preventDefault: () => void }) => {
    event.preventDefault();
  });
  const onNavigate = vi.fn();
  const onClose = vi.fn();
  render(
    <AuthContext.Provider value={auth}>
      <RecordSheet
        hash={hash}
        follow={follow}
        onNavigate={onNavigate}
        onClose={onClose}
      />
    </AuthContext.Provider>,
  );
  return { follow, onNavigate, onClose };
}

test("on a Plant, the sheet leads with that Plant's own actions", async () => {
  const { follow, onClose } = mount(`#/plants/${plantId}?tab=overview`);
  const sheet = screen.getByRole("dialog", { name: "Record" });
  const here = within(sheet).getByRole("navigation", { name: "This Plant" });
  const entry = within(here).getByRole("link", { name: "Add Journal entry" });
  expect(entry).toHaveAttribute(
    "href",
    `#/plants/${plantId}?tab=events&entry=new`,
  );
  await userEvent.click(entry);
  expect(follow).toHaveBeenCalledWith(
    expect.anything(),
    `#/plants/${plantId}?tab=events&entry=new`,
  );
  expect(onClose).toHaveBeenCalled();
  await screen.findByRole("combobox", { name: "Target record" });
});

test("away from a record, choosing a Sowing opens its germination form", async () => {
  mount();
  expect(screen.queryByRole("navigation", { name: /^This / })).toBeNull();
  await userEvent.click(screen.getByRole("radio", { name: "Sowing" }));
  await userEvent.click(
    await screen.findByRole("combobox", { name: "Target record" }),
  );
  const option = await screen.findByRole("option", { name: /Spring tray/ });
  await userEvent.click(within(option).getByRole("button"));
  expect(
    screen.getByRole("link", { name: "Open germination entry" }),
  ).toHaveAttribute("href", `#/sowings/${sowingId}?tab=germination&entry=new`);
  expect(
    fetch.mock.calls.some(([path]) =>
      path.includes("/schedule/targets/sowing"),
    ),
  ).toBe(true);
});

test("a typed or scanner-typed label link opens only a Florabase label route", async () => {
  const { onNavigate, onClose } = mount();
  const field = screen.getByLabelText("Label link");
  await userEvent.type(field, "https://evil.example/#/plants?action=create");
  await userEvent.click(screen.getByRole("button", { name: "Open" }));
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Not a Florabase label link",
  );
  expect(field).toHaveAttribute("aria-invalid", "true");
  expect(onNavigate).not.toHaveBeenCalled();
  await userEvent.clear(field);
  // USB scanners type the code and press Enter.
  await userEvent.type(
    field,
    `https://florabase.example/#/plants/${plantId}{Enter}`,
  );
  expect(onClose).toHaveBeenCalled();
  expect(onNavigate).toHaveBeenCalledWith(`#/plants/${plantId}`);
});

test("camera scanning is offered only where the browser can read QR codes", () => {
  mount();
  expect(screen.queryByRole("button", { name: "Scan with camera" })).toBeNull();
  cleanup();
  vi.stubGlobal(
    "BarcodeDetector",
    class {
      detect() {
        return Promise.resolve([]);
      }
    },
  );
  vi.stubGlobal("navigator", withMedia({ getUserMedia: vi.fn() }));
  mount();
  expect(
    screen.getByRole("button", { name: "Scan with camera" }),
  ).toBeVisible();
});

test("a scanned label navigates and releases the camera; a foreign code is refused", async () => {
  const stop = vi.fn();
  const stream = { active: true, getTracks: () => [{ stop }] };
  const values = [
    ["not a label"],
    [`https://florabase.example/#/seeds/${plantId}`],
  ];
  vi.stubGlobal(
    "BarcodeDetector",
    class {
      detect() {
        return Promise.resolve(
          (values.shift() ?? []).map((rawValue) => ({ rawValue })),
        );
      }
    },
  );
  vi.stubGlobal(
    "navigator",
    withMedia({ getUserMedia: vi.fn(() => Promise.resolve(stream)) }),
  );
  vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
  const { onNavigate } = mount();
  await userEvent.click(
    screen.getByRole("button", { name: "Scan with camera" }),
  );
  expect(
    await screen.findByText(
      "That code is not a Florabase label. Try another label.",
    ),
  ).toBeVisible();
  await vi.waitFor(() => {
    expect(onNavigate).toHaveBeenCalledWith(`#/seeds/${plantId}`);
  });
  expect(stop).toHaveBeenCalled();
});
