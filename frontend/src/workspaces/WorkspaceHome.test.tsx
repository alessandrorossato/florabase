import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../auth/context";
import type { DashboardResponse } from "../collection/api";
import { emptyOverview } from "../collection/dashboardFixtures";
import { acquireTestAuth } from "../test/auth";
import { WorkspaceHome } from "./WorkspaceHome";

const get = vi.hoisted(() => vi.fn());
vi.mock("../collection/api", () => ({ getDashboard: get }));
let auth: AuthContextValue;
beforeEach(async () => {
  auth = (await acquireTestAuth()).auth;
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});
const summary: DashboardResponse = {
  counts: {
    active_plants: 17,
    active_plant_groups: 1,
    active_seed_lots: 40,
    active_sowings: 12,
    botanical_identities: 9,
    events: 230,
  },
  recent_events: [],
  overview: {
    ...emptyOverview,
    sowings_unknown_germination: 5,
    purchase_packets_without_order: 0,
    current_identities: 8,
    identities_with_wfo: 3,
    due_today: 2,
    overdue: 1,
    next_seven_days: 4,
  },
};
function show(id: Parameters<typeof WorkspaceHome>[0]["id"]) {
  return render(
    <AuthContext.Provider value={auth}>
      <WorkspaceHome id={id} />
    </AuthContext.Provider>,
  );
}
const tile = (name: string) =>
  screen.getByRole("link", { name }).closest("li") as HTMLElement;

test("Collection lists every sub-section once with grounded counts, views and first actions", async () => {
  get.mockResolvedValue(summary);
  show("collection");
  expect(
    screen.getByRole("heading", { level: 2, name: "Collection" }),
  ).toBeVisible();
  const list = screen.getByRole("list", { name: "Collection sections" });
  expect(
    within(list)
      .getAllByRole("heading", { level: 3 })
      .map((heading) => heading.textContent),
  ).toEqual([
    "Seeds",
    "Sowings",
    "Cuttings",
    "Plants",
    "Harvests",
    "Locations",
  ]);
  expect(await screen.findByText("40")).toBeVisible();
  expect(within(tile("Seeds")).getByText(/active seed lots/)).toBeVisible();
  // A zero derived count is not shown as a warning line.
  expect(within(tile("Seeds")).queryByText(/without an Order/)).toBeNull();
  expect(
    within(tile("Sowings")).getByText("5 sowings without a germination count"),
  ).toBeVisible();
  expect(within(tile("Plants")).getByText("1 Plant group")).toBeVisible();
  expect(
    within(tile("Plants")).getByRole("link", { name: "Plant groups" }),
  ).toHaveAttribute("href", "#/plants?type=group");
  expect(
    within(tile("Harvests")).getByRole("link", { name: "Stored material" }),
  ).toHaveAttribute("href", "#/harvests?tab=stored-material");
  expect(
    within(tile("Seeds")).getByRole("link", { name: "New seed lot" }),
  ).toHaveAttribute("href", "#/seeds?action=create");
  // Sections without a count in the summary never show an invented one.
  expect(within(tile("Cuttings")).queryByText(/\d/)).toBeNull();
  expect(screen.getByRole("link", { name: "Seeds" })).toHaveAttribute(
    "href",
    "#/seeds",
  );
});

test("Activity and Explore read their counts from the same summary", async () => {
  get.mockResolvedValue(summary);
  const view = show("activity");
  expect(await screen.findByText("230")).toBeVisible();
  expect(
    within(tile("Schedule")).getByText("1 overdue · 4 in the next 7 days"),
  ).toBeVisible();
  expect(within(tile("Schedule")).getByText(/due today/)).toBeVisible();
  view.unmount();
  show("explore");
  expect(
    await within(await screen.findByRole("list")).findByText(
      "3 with a confirmed WFO link",
    ),
  ).toBeVisible();
  expect(
    within(tile("Geography")).getByRole("link", { name: "Native ranges" }),
  ).toHaveAttribute("href", "#/native-ranges");
});

test("a failed summary keeps every section usable and can be retried", async () => {
  get.mockRejectedValueOnce(new Error("offline")).mockResolvedValue(summary);
  const user = userEvent.setup();
  show("sourcing");
  expect(await screen.findByText(/Counts could not be loaded/)).toBeVisible();
  expect(screen.getByRole("link", { name: "Suppliers" })).toBeVisible();
  expect(screen.getByRole("link", { name: "New order" })).toHaveAttribute(
    "href",
    "#/orders?action=create",
  );
  await user.click(screen.getByRole("button", { name: "Retry counts" }));
  expect(screen.queryByText(/Counts could not be loaded/)).toBeNull();
  expect(get).toHaveBeenCalledTimes(2);
});
