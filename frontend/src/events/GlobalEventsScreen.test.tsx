import {
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "../auth/context";
import { listGlobalEvents, type EventResponse } from "../collection/api";
import * as saved from "../saved-views/api";
import { GlobalEventsScreen } from "./GlobalEventsScreen";
import { filteredEvents } from "./eventData";

vi.mock("../collection/api", () => ({ listGlobalEvents: vi.fn() }));
vi.mock("../saved-views/api", () => ({ listSavedViews: vi.fn() }));
const auth: AuthContextValue = {
  state: {
    status: "authenticated",
    csrfToken: "csrf",
    session: {
      user_id: "owner",
      login_name: "owner",
      display_name: null,
      owner: true,
      canonical_origin: "http://localhost",
    },
  },
  logIn: vi.fn(),
  logOut: vi.fn(),
  sessionExpired: vi.fn(),
  retryRestoration: vi.fn(),
  cancelLogout: vi.fn(),
};
const event: EventResponse = {
  id: "event",
  kind: "harvest",
  occurred_on: null,
  created_at: "2026-10-07T12:00:00Z",
  updated_at: "2026-10-07T12:00:00Z",
  notes: "Collected dry seed. ".repeat(30),
  target: {
    id: "plant",
    type: "plant",
    label: "Basil mother plant",
    lifecycle: "active",
    botanical_identity: { id: "identity", display_label: "Ocimum basilicum" },
  },
  destination_location_id: null,
  destination_location: null,
  recipient: null,
  resulting_plant_id: null,
  resulting_plant: null,
  harvest_id: "harvest",
  harvest_title: "Basil seeds",
};
function mount() {
  return render(
    <AuthContext.Provider value={auth}>
      <GlobalEventsScreen />
    </AuthContext.Provider>,
  );
}
beforeEach(() => {
  window.history.replaceState(null, "", "#/events");
  vi.mocked(listGlobalEvents).mockResolvedValue([
    event,
    { ...event, id: "death", kind: "death", notes: null, harvest_id: null },
  ]);
  vi.mocked(saved.listSavedViews).mockResolvedValue([]);
});
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

test("Journal explains its focused role and keeps secondary help and relationships", async () => {
  mount();
  expect(
    screen.getByRole("heading", { name: "Journal", level: 2 }),
  ).toBeVisible();
  expect(
    screen.getByText(
      /Observations and actions recorded for Plants and Plant groups/,
    ),
  ).toBeVisible();
  expect(screen.getByRole("link", { name: "History" })).toHaveAttribute(
    "href",
    "#/history",
  );
  await screen.findByText("Harvest");
  const row = screen
    .getByRole("link", { name: "Harvest: Basil seeds" })
    .closest("article");
  expect(row).not.toBeNull();
  if (!row) throw new Error("Journal row missing");
  expect(within(row).getByText("Recorded 7 Oct 2026")).toBeVisible();
  expect(
    within(row).getByRole("link", { name: "Basil mother plant" }),
  ).toHaveAttribute("href", "#/plants/plant?tab=events");
  expect(
    row.querySelector(".journal-related a[href='#/harvests/harvest']"),
  ).toHaveTextContent("Harvest: Basil seeds");
  expect(
    row.querySelector(".journal-excerpt")?.textContent.length,
  ).toBeLessThanOrEqual(241);
  const children = Array.from(row.children);
  expect(
    children.findIndex((child) => child.classList.contains("event-target")),
  ).toBeLessThan(
    children.findIndex((child) => child.classList.contains("journal-related")),
  );
  const user = userEvent.setup();
  await user.click(
    screen.getByText("How Event corrections affect current state"),
  );
  expect(screen.getByText(/does not recompute a Plant/)).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Lifecycle" }));
  expect(window.location.hash).toBe("#/events?category=status");
  expect(screen.getByText("Death")).toBeVisible();
  expect(screen.queryByText("Harvest")).not.toBeInTheDocument();
});

test("Journal keeps Event grouping and existing Saved View routes and identifiers", async () => {
  const kinds: EventResponse["kind"][] = [
    "observation",
    "flowering",
    "fruiting",
    "movement",
    "repotting",
    "pruning",
    "treatment",
    "harvest",
    "extraction",
    "reintegration",
    "transfer",
    "death",
    "loss",
    "discarded",
    "other",
  ];
  const rows = kinds.map((kind) => ({ ...event, kind }));
  expect(filteredEvents(rows, "observations").map((row) => row.kind)).toEqual(
    kinds.slice(0, 3),
  );
  expect(filteredEvents(rows, "cultivation").map((row) => row.kind)).toEqual(
    kinds.slice(3, 10),
  );
  expect(filteredEvents(rows, "status").map((row) => row.kind)).toEqual(
    kinds.slice(10, 14),
  );
  expect(filteredEvents(rows, "all")).toEqual(rows);
  vi.mocked(saved.listSavedViews).mockResolvedValue([
    {
      id: "view",
      name: "Lifecycle journal",
      surface: "events",
      state_version: 1,
      state: { category: "status" },
      created_at: event.created_at,
      updated_at: event.created_at,
      compatibility: "supported",
    },
  ]);
  mount();
  await screen.findByText("Harvest");
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Saved views" }));
  await screen.findByRole("button", { name: "Open Lifecycle journal" });
  expect(
    screen.getByRole("region", { name: "Journal Saved Views" }),
  ).toBeVisible();
  await user.click(
    screen.getByRole("button", { name: "Open Lifecycle journal" }),
  );
  await waitFor(() => {
    expect(
      screen.getByRole("button", { name: "Lifecycle", pressed: true }),
    ).toBeVisible();
  });
  expect(window.location.hash).toBe("#/events?category=status");
  expect(saved.listSavedViews).toHaveBeenCalledWith(
    "events",
    expect.any(AbortSignal),
    0,
  );
});
