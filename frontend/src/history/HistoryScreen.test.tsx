import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "../auth/context";
import { ApiError } from "../auth/api";
import * as api from "./api";
import * as saved from "../saved-views/api";
import { HistoryScreen } from "./HistoryScreen";
import { historyHash, parseHistoryState, readHistoryState } from "./state";
import { savedViewHash } from "../saved-views/state";
vi.mock("./api", async (original) => ({
  ...(await original<typeof import("./api")>()),
  getHistory: vi.fn(),
}));
vi.mock("../saved-views/api", () => ({
  listSavedViews: vi.fn(),
  createSavedView: vi.fn(),
  updateSavedView: vi.fn(),
  deleteSavedView: vi.fn(),
}));
const id = "01900000-0000-7000-8000-000000000001";
const other = "01900000-0000-7000-8000-000000000002";
const sessionExpired = vi.fn();
const auth: AuthContextValue = {
  state: {
    status: "authenticated",
    session: {
      user_id: id,
      login_name: "owner",
      display_name: null,
      owner: true,
      canonical_origin: "http://localhost",
    },
    csrfToken: "csrf",
  },
  logIn: vi.fn(),
  logOut: vi.fn(),
  sessionExpired,
  retryRestoration: vi.fn(),
  cancelLogout: vi.fn(),
};
function entry(overrides: Partial<api.HistoryEntry> = {}): api.HistoryEntry {
  return {
    key: `event:${id}`,
    category: "event",
    source_kind: "event",
    source_id: id,
    subtype: "movement",
    title: "Movement",
    context: "",
    primary: { kind: "plant", id, label: "Basil mother plant" },
    related: [{ kind: "location", id: other, label: "Greenhouse bench" }],
    occurred_on: { precision: "month", year: 2026, month: 10 },
    occurred_at: null,
    recorded_at: "2026-10-07T12:00:00Z",
    date_basis: "occurred",
    status: null,
    ...overrides,
  };
}
const response = (
  items = [entry()],
  total = items.length,
  offset = 0,
): api.HistoryResponse => ({ items, total, offset, limit: 50 });
function mount() {
  return render(
    <AuthContext.Provider value={auth}>
      <HistoryScreen />
    </AuthContext.Provider>,
  );
}
beforeEach(() => {
  window.history.replaceState(null, "", "/#/history");
  vi.mocked(api.getHistory).mockResolvedValue(response());
  vi.mocked(saved.listSavedViews).mockResolvedValue([]);
});
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

test("mixed timeline preserves precision, Recorded, reversed state and exact typed links without mutations", async () => {
  vi.mocked(api.getHistory).mockResolvedValue(
    response([
      entry(),
      entry({
        key: "harvest:h",
        category: "harvest",
        source_kind: "harvest",
        title: "Harvest recorded",
        primary: { kind: "harvest", id, label: "Seeds collected" },
        related: [],
        occurred_on: { precision: "year", year: 2025 },
      }),
      entry({
        key: "germination:g",
        category: "germination",
        source_kind: "germination",
        title: "Germination observed",
        primary: { kind: "sowing", id, label: "Spring tray" },
        related: [],
        occurred_on: { precision: "day", year: 2026, month: 10, day: 7 },
      }),
      entry({
        key: "conversion:c:applied",
        category: "material",
        source_kind: "conversion",
        title: "Seed lot created from stored seeds",
        primary: { kind: "seed_lot", id, label: "Collected seeds" },
        related: [
          {
            kind: "harvest_inventory",
            id: other,
            harvest_id: id,
            label: "Stored seeds",
          },
        ],
        date_basis: "recorded",
        occurred_on: null,
        status: "reversed",
      }),
      entry({
        key: "operation_receipt:r",
        category: "propagation",
        source_kind: "operation_receipt",
        title: "Plant group created from Sowing",
        primary: { kind: "plant_group", id, label: "Basil group" },
        related: [],
      }),
    ]),
  );
  mount();
  expect(screen.getByRole("heading", { name: "History" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Journal" })).toHaveAttribute(
    "href",
    "#/events",
  );
  expect(screen.getByRole("button", { name: "All activity" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await screen.findByText("Movement");
  expect(screen.getAllByText("2026-10")).toHaveLength(2);
  expect(screen.getByText("2025")).toBeInTheDocument();
  expect(screen.getByText("2026-10-07")).toBeInTheDocument();
  expect(
    screen.getByText("7 Oct 2026").closest(".history-date"),
  ).toHaveTextContent("Recorded 7 Oct 2026");
  expect(screen.getByText("Reversed")).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "Basil mother plant" }),
  ).toHaveAttribute("href", `#/plants/${id}?tab=events`);
  expect(screen.getByRole("link", { name: "Spring tray" })).toHaveAttribute(
    "href",
    `#/sowings/${id}?tab=germination`,
  );
  expect(screen.getByRole("link", { name: "Seeds collected" })).toHaveAttribute(
    "href",
    `#/harvests/${id}`,
  );
  expect(
    screen.getByRole("link", { name: "Related: Stored seeds" }),
  ).toHaveAttribute("href", `#/harvests/${id}?inventory=${other}`);
  expect(screen.getByRole("link", { name: "Basil group" })).toHaveAttribute(
    "href",
    `#/plant-groups/${id}`,
  );
  expect(screen.getByRole("link", { name: "Collected seeds" })).toHaveAttribute(
    "href",
    `#/seeds/${id}`,
  );
  for (const name of [/^Edit/, /^Delete/, /^Reverse/, /^Move/, /^Select/])
    expect(screen.queryByRole("button", { name })).not.toBeInTheDocument();
  expect(screen.getAllByRole("list").length).toBeGreaterThan(0);
});

test("loading, empty, failure, retry and session expiry", async () => {
  vi.mocked(api.getHistory)
    .mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValueOnce(response([]));
  mount();
  expect(screen.getByRole("status")).toHaveTextContent("Loading History");
  await screen.findByRole("alert");
  await userEvent.setup().click(screen.getByRole("button", { name: "Retry" }));
  await screen.findByText("No recorded activity matches these filters.");
  expect(screen.getByText("0 records")).toBeInTheDocument();
  vi.mocked(api.getHistory).mockRejectedValueOnce(new ApiError(401));
  fireEvent.popState(window);
  await waitFor(() => {
    expect(sessionExpired).toHaveBeenCalled();
  });
});

test("category, subject, timeline year and URL back/forward state reset pagination", async () => {
  vi.mocked(api.getHistory).mockImplementation((_filters, offset) =>
    Promise.resolve(response([entry()], 101, offset)),
  );
  const user = userEvent.setup();
  mount();
  await screen.findByText("Movement");
  await user.click(screen.getByRole("button", { name: "Next page" }));
  await waitFor(() => {
    expect(api.getHistory).toHaveBeenLastCalledWith(
      expect.anything(),
      50,
      expect.any(AbortSignal),
    );
  });
  await user.click(screen.getByRole("button", { name: "Harvests" }));
  expect(window.location.hash).toBe("#/history?category=harvest");
  expect(screen.getByRole("button", { name: "All activity" })).toHaveAttribute(
    "aria-pressed",
    "false",
  );
  await waitFor(() => {
    expect(api.getHistory).toHaveBeenLastCalledWith(
      expect.objectContaining({ category: ["harvest"] }),
      0,
      expect.any(AbortSignal),
    );
  });
  await user.click(screen.getByRole("button", { name: "Events" }));
  await user.selectOptions(
    screen.getByLabelText("Primary record type"),
    "plant",
  );
  await user.type(screen.getByLabelText("Timeline year"), "2026");
  await user.click(screen.getByRole("button", { name: "Apply year" }));
  expect(window.location.hash).toBe(
    "#/history?category=event&category=harvest&subject_kind=plant&year=2026",
  );
  window.history.replaceState(
    null,
    "",
    "/#/history?category=germination&year=2025",
  );
  fireEvent.popState(window);
  await waitFor(() => {
    expect(screen.getByRole("button", { name: "Germination" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
  expect(screen.getByLabelText("Timeline year")).toHaveValue("2025");
  expect(screen.getByLabelText("Primary record type")).toHaveValue("");
  window.history.replaceState(null, "", "/#/history?category=material");
  fireEvent(window, new HashChangeEvent("hashchange"));
  await waitFor(() => {
    expect(
      screen.getByRole("button", { name: "Stored material" }),
    ).toHaveAttribute("aria-pressed", "true");
  });
});

test("refresh restores filters, shows bounded page count and previous page", async () => {
  window.history.replaceState(
    null,
    "",
    "/#/history?category=material&year=2026",
  );
  vi.mocked(api.getHistory).mockImplementation((_filters, offset) =>
    Promise.resolve(response([entry()], 51, offset)),
  );
  const user = userEvent.setup();
  mount();
  await screen.findByText("Movement");
  expect(screen.getByText("1 of 51 records")).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Stored material" }),
  ).toHaveAttribute("aria-pressed", "true");
  await user.click(screen.getByRole("button", { name: "Next page" }));
  await screen.findByText("Page 2");
  await user.click(screen.getByRole("button", { name: "Previous page" }));
  await screen.findByText("Page 1");
  await user.clear(screen.getByLabelText("Timeline year"));
  await user.type(screen.getByLabelText("Timeline year"), "0");
  await user.click(screen.getByRole("button", { name: "Apply year" }));
  expect(screen.getByText("Enter a year from 1 to 9999.")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Clear year" }));
  expect(screen.getByLabelText("Timeline year")).toHaveValue("");
  expect(window.location.hash).toBe("#/history?category=material");
  await user.click(screen.getByRole("button", { name: "All activity" }));
  expect(window.location.hash).toBe("#/history");
  expect(screen.getByRole("button", { name: "All activity" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});

test("History Saved View saves filters, reopens canonical URL and resets identical-view pagination", async () => {
  const view: saved.SavedView = {
    id,
    name: "Material history",
    surface: "history",
    state_version: 1,
    state: { category: ["material"] },
    created_at: "2026-10-07T12:00:00Z",
    updated_at: "2026-10-07T12:00:00Z",
    compatibility: "supported",
  };
  vi.mocked(saved.createSavedView).mockResolvedValue(view);
  vi.mocked(saved.listSavedViews).mockResolvedValue([view]);
  vi.mocked(api.getHistory).mockImplementation((_filters, offset) =>
    Promise.resolve(response([entry()], 101, offset)),
  );
  const user = userEvent.setup();
  mount();
  await screen.findByText("Movement");
  await user.click(screen.getByRole("button", { name: "Stored material" }));
  await user.click(screen.getByRole("button", { name: "Save view" }));
  const dialog = screen.getByRole("dialog");
  await user.type(within(dialog).getByLabelText(/name/i), "Material history");
  await user.click(within(dialog).getByRole("button", { name: "Save view" }));
  await waitFor(() => {
    expect(saved.createSavedView).toHaveBeenCalledWith(
      expect.objectContaining({
        surface: "history",
        state: { category: ["material"] },
      }),
      "csrf",
    );
  });
  await user.click(screen.getByRole("button", { name: "Next page" }));
  await screen.findByText("Page 2");
  await user.click(
    await screen.findByRole("button", { name: "Open Material history" }),
  );
  await screen.findByText("Page 1");
  expect(window.location.hash).toBe("#/history?category=material");
  expect(api.getHistory).toHaveBeenLastCalledWith(
    expect.objectContaining({ category: ["material"] }),
    0,
    expect.any(AbortSignal),
  );
});

test("canonical History state ignores invalid URL values and rejects saved transient keys", () => {
  expect(
    readHistoryState(
      "#/history?category=bad&category=harvest&category=event&category=harvest&year=0&subject_kind=bad",
    ),
  ).toEqual({ category: ["event", "harvest"], year: "", subject_kind: "" });
  expect(
    historyHash(
      readHistoryState("#/history?year=0026&category=harvest&category=event"),
    ),
  ).toBe("#/history?category=event&category=harvest&year=26");
  expect(
    savedViewHash("history", 1, {
      year: 2026,
      category: ["harvest", "event", "harvest"],
    }),
  ).toBe("#/history?category=event&category=harvest&year=2026");
  expect(parseHistoryState({ year: 2026, offset: 50 })).toBeNull();
  expect(savedViewHash("history", 1, { category: ["bad"] })).toBeNull();
  expect(savedViewHash("history", 2, { year: 2026 })).toBeNull();
  expect(savedViewHash("history", 1, {})).toBeNull();
});
