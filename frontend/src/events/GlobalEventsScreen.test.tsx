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
import * as schedule from "../schedule/api";
import { filteredEvents } from "./eventData";

vi.mock("../collection/api", () => ({ listGlobalEvents: vi.fn() }));
vi.mock("../schedule/api", () => ({ listTargets: vi.fn() }));
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
  kind: "observation",
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
  harvest_id: null,
  harvest_title: null,
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
    {
      ...event,
      id: "death",
      kind: "death",
      notes: "Roots damaged by frost.",
      harvest_id: null,
    },
  ]);
  vi.mocked(saved.listSavedViews).mockResolvedValue([]);
});
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

test("Journal uses compact header and toolbar with authored content and source links", async () => {
  mount();
  expect(
    screen.getByRole("heading", { name: "Journal", level: 2 }),
  ).toBeVisible();
  const toolbar = screen.getByRole("group", { name: "Journal toolbar" });
  expect(
    within(toolbar).getByRole("searchbox", { name: "Search Journal" }),
  ).toBeVisible();
  expect(
    within(toolbar).getByRole("button", { name: "Filters" }),
  ).toBeVisible();
  expect(
    within(toolbar).getByRole("button", { name: "Saved views" }),
  ).toBeVisible();
  expect(
    screen.getByRole("button", { name: "Record" }).closest("header"),
  ).not.toBeNull();
  expect(screen.queryByText(/How Event corrections/)).not.toBeInTheDocument();
  await screen.findByText("Observation");
  const row = screen
    .getAllByRole("link", { name: "Basil mother plant" })[0]
    .closest("article");
  if (!row) throw new Error("Notebook row missing");
  expect(within(row).getByText("Recorded 7 Oct 2026 (UTC)")).toBeVisible();
  expect(
    within(row).getByRole("link", { name: "Basil mother plant" }),
  ).toHaveAttribute("href", "#/plants/plant?tab=events");
  expect(
    row.querySelector(".journal-excerpt")?.textContent.length,
  ).toBeLessThanOrEqual(241);
});

test("Journal filters use the drawer, retain query on reset, and restore URL search", async () => {
  const user = userEvent.setup();
  mount();
  await screen.findByText("Observation");
  await user.type(
    screen.getByRole("searchbox", { name: "Search Journal" }),
    "basil",
  );
  await user.click(screen.getByRole("button", { name: "Filters" }));
  const drawer = screen.getByRole("dialog", { name: "Journal filters" });
  await user.click(within(drawer).getByRole("checkbox", { name: "Lifecycle" }));
  expect(window.location.hash).toBe("#/events?q=basil&category=status");
  await user.keyboard("{Escape}");
  expect(screen.getByRole("button", { name: "Filters (1)" })).toHaveFocus();
  expect(screen.getByText("Death")).toBeVisible();
  expect(screen.queryByText("Observation")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Clear filters" }));
  expect(window.location.hash).toBe("#/events?q=basil");
  await user.clear(screen.getByRole("searchbox", { name: "Search Journal" }));
  await user.type(
    screen.getByRole("searchbox", { name: "Search Journal" }),
    "collected dry",
  );
  expect(screen.getByText("Observation")).toBeVisible();
  expect(screen.queryByText("Death")).not.toBeInTheDocument();
  window.history.replaceState(null, "", "#/events?q=ocimum&category=status");
  window.dispatchEvent(new PopStateEvent("popstate"));
  await waitFor(() => {
    expect(
      screen.getByRole("searchbox", { name: "Search Journal" }),
    ).toHaveValue("ocimum");
  });
});

test("legacy Journal Saved Views and Event kind memberships stay valid", async () => {
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
  expect(filteredEvents(rows, "observations").map((r) => r.kind)).toEqual(
    kinds.slice(0, 3),
  );
  expect(filteredEvents(rows, "cultivation").map((r) => r.kind)).toEqual(
    kinds.slice(3, 10),
  );
  expect(filteredEvents(rows, "status").map((r) => r.kind)).toEqual(
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
  const user = userEvent.setup();
  mount();
  await screen.findByText("Observation");
  await user.click(screen.getByRole("button", { name: "Saved views" }));
  await user.click(
    await screen.findByRole("button", { name: "Open Lifecycle journal" }),
  );
  expect(window.location.hash).toBe("#/events?category=status");
  await waitFor(() => {
    expect(screen.getByText("Death")).toBeVisible();
  });
});

test("Record routes every delivered structured workflow and closes accessibly", async () => {
  const user = userEvent.setup();
  mount();
  const trigger = screen.getByRole("button", { name: "Record" });
  await user.click(trigger);
  const menu = screen.getByRole("navigation", { name: "Record choices" });
  for (const [label, href] of [
    ["Record harvest", "#/harvests?action=create"],
    ["Record sowing", "#/sowings?action=create"],
    ["Move plants / groups", "#/plants"],
    ["Complete scheduled work", "#/schedule"],
  ]) {
    expect(within(menu).getByRole("link", { name: label })).toHaveAttribute(
      "href",
      href,
    );
  }
  await user.keyboard("{Escape}");
  expect(trigger).toHaveFocus();
  expect(
    screen.queryByRole("navigation", { name: "Record choices" }),
  ).not.toBeInTheDocument();
  await user.click(trigger);
  await user.click(screen.getByRole("heading", { name: "Journal" }));
  expect(
    screen.queryByRole("navigation", { name: "Record choices" }),
  ).not.toBeInTheDocument();
  await waitFor(() => {
    expect(trigger).toHaveFocus();
  });
  await user.keyboard("{ArrowDown}");
  await waitFor(() => {
    expect(
      screen.getByRole("button", { name: "Add observation / note" }),
    ).toHaveFocus();
  });
  await user.keyboard("{ArrowDown}");
  expect(screen.getByRole("link", { name: "Record harvest" })).toHaveFocus();
  await user.keyboard("{Escape}");
  expect(trigger).toHaveFocus();
});

test.each([
  "Add observation / note",
  "Other journal entry",
  "Record germination",
])(
  "%s reuses the correct contextual workflow and preserves dialog focus",
  async (label) => {
    vi.mocked(schedule.listTargets).mockImplementation((kind) =>
      Promise.resolve({
        total: 1,
        items: [
          { id: "target", kind, label: "Review specimen", lifecycle: "dead" },
        ],
      }),
    );
    const user = userEvent.setup();
    mount();
    await user.click(screen.getByRole("button", { name: "Record" }));
    await user.click(screen.getByRole("button", { name: label }));
    const germination = label === "Record germination";
    const dialog = screen.getByRole("dialog", {
      name: germination ? "Record germination" : "Record a Journal entry",
    });
    if (!germination)
      await user.selectOptions(
        within(dialog).getByLabelText("Record type"),
        "plant_group",
      );
    const picker = await within(dialog).findByRole("combobox", {
      name: "Target record",
    });
    await user.click(picker);
    await user.click(
      within(
        await within(dialog).findByRole("option", { name: /Review specimen/ }),
      ).getByRole("button"),
    );
    expect(
      within(dialog).getByRole("link", {
        name: germination
          ? "Open germination observations"
          : "Continue to Journal",
      }),
    ).toHaveAttribute(
      "href",
      germination
        ? "#/sowings/target?tab=germination"
        : "#/plant-groups/target?tab=events",
    );
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Record" })).toHaveFocus();
  },
);

test("operation-owned backing records stay out of the global notebook without removing explanatory notes", async () => {
  vi.mocked(listGlobalEvents).mockResolvedValue([
    {
      ...event,
      id: "note",
      kind: "other",
      notes: "Moved because nights are warmer.",
    },
    { ...event, id: "owned-harvest", kind: "harvest", harvest_id: "harvest" },
    {
      ...event,
      id: "owned-operation",
      kind: "extraction",
      operation_kind: "plant_group_to_plant",
      operation_status: "applied",
    },
  ]);
  mount();
  expect(
    await screen.findByText("Moved because nights are warmer."),
  ).toBeVisible();
  expect(
    screen.queryByText("Harvest", { selector: "h3" }),
  ).not.toBeInTheDocument();
  expect(screen.queryByText("Extraction")).not.toBeInTheDocument();
});

test("unannotated movement facts remain in History while notebook context is retained", async () => {
  vi.mocked(listGlobalEvents).mockResolvedValue([
    { ...event, id: "bare-move", kind: "movement", notes: null },
    {
      ...event,
      id: "contextual-move",
      kind: "movement",
      notes: "Moved outside because nights are now stable.",
    },
  ]);
  mount();
  expect(
    await screen.findByText("Moved outside because nights are now stable."),
  ).toBeVisible();
  expect(screen.getAllByText("Movement", { selector: "h3" })).toHaveLength(1);
  expect(screen.getByText("1 record")).toBeVisible();
});

test("entry categories are a live union with one counted dimension and preserved search", async () => {
  vi.mocked(listGlobalEvents).mockResolvedValue([
    event,
    { ...event, id: "repot", kind: "repotting" },
    { ...event, id: "other", kind: "other" },
  ]);
  const user = userEvent.setup();
  mount();
  await screen.findByText("Observation");
  await user.type(
    screen.getByRole("searchbox", { name: "Search Journal" }),
    "Basil",
  );
  await user.click(screen.getByRole("button", { name: "Filters" }));
  const drawer = screen.getByRole("dialog", { name: "Journal filters" });
  await user.click(
    within(drawer).getByRole("checkbox", { name: "Cultivation" }),
  );
  await user.click(
    within(drawer).getByRole("checkbox", { name: "Observations" }),
  );
  expect(window.location.hash).toBe(
    "#/events?q=Basil&category=observations&category=cultivation",
  );
  expect(screen.getByText("Observation")).toBeVisible();
  expect(screen.getByText("Repotting")).toBeVisible();
  expect(screen.queryByText("Other")).not.toBeInTheDocument();
  await user.click(
    within(drawer).getByRole("checkbox", { name: "Cultivation" }),
  );
  expect(screen.queryByText("Repotting")).not.toBeInTheDocument();
  await user.click(
    within(drawer).getByRole("button", { name: "Reset filters" }),
  );
  expect(window.location.hash).toBe("#/events?q=Basil");
  expect(screen.getByText("Other")).toBeVisible();
  await user.click(within(drawer).getByRole("button", { name: "Done" }));
  expect(screen.getByRole("button", { name: "Filters" })).toHaveFocus();
});
