import {
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import { DashboardOverview } from "./DashboardScreen";
import { emptyOverview, journalFixture } from "./dashboardFixtures";
import type { DashboardResponse } from "./api";
import { ApiError } from "../auth/api";
import { localDay } from "../schedule/state";

const expired = vi.hoisted(() => vi.fn());
const auth = { sessionExpired: expired };
vi.mock("../auth/context", () => ({ useAuth: () => auth }));
const get = vi.hoisted(() => vi.fn());
vi.mock("./api", () => ({ getDashboard: get }));
const empty: DashboardResponse = {
  counts: {
    active_plants: 0,
    active_plant_groups: 0,
    active_seed_lots: 0,
    active_sowings: 0,
    botanical_identities: 0,
    events: 0,
  },
  recent_events: [],
  overview: emptyOverview,
};
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

test("empty collection preserves all operational areas and uses the local calendar day", async () => {
  get.mockResolvedValue(empty);
  render(<DashboardOverview />);
  expect(
    await screen.findByRole("heading", { name: "Collection snapshot" }),
  ).toBeInTheDocument();
  for (const name of ["Attention & upcoming", "Recent activity"])
    expect(screen.getByRole("heading", { name })).toBeInTheDocument();
  expect(screen.getByText(/No planned activities/)).toBeInTheDocument();
  expect(screen.getByText(/No recent activity/)).toBeInTheDocument();
  expect(get).toHaveBeenCalledWith(expect.any(AbortSignal), localDay());
  expect(get).toHaveBeenCalledTimes(1);
  for (const name of ["Propagation", "Sourcing", "Botanical coverage"])
    expect(screen.queryByRole("heading", { name })).not.toBeInTheDocument();
});

test("loading, recoverable failure and retry never manufacture zero metrics", async () => {
  let reject!: (e: Error) => void;
  get
    .mockImplementationOnce(
      () =>
        new Promise((_resolve, no) => {
          reject = no;
        }),
    )
    .mockResolvedValueOnce(empty);
  const user = userEvent.setup();
  render(<DashboardOverview />);
  expect(screen.getByRole("status")).toHaveTextContent("Loading");
  expect(
    screen.queryByRole("link", { name: "Plants: 0" }),
  ).not.toBeInTheDocument();
  reject(new Error("Offline"));
  expect(await screen.findByRole("alert")).toHaveTextContent("could not load");
  await user.click(screen.getByRole("button", { name: "Retry" }));
  expect(
    await screen.findByRole("link", { name: "Plants: 0" }),
  ).toBeInTheDocument();
});

test("auth failures expire the session", async () => {
  get.mockRejectedValue(new ApiError(401, "Expired"));
  render(<DashboardOverview />);
  await waitFor(() => {
    expect(expired).toHaveBeenCalledOnce();
  });
});

test("Journal, History, partial dates, reversal and planned work remain distinguishable", async () => {
  const journal = journalFixture(
    "01900000-0000-7000-8000-000000000101",
    "Observed growth",
  );
  get.mockResolvedValue({
    ...empty,
    overview: {
      ...emptyOverview,
      overdue: 1,
      due_today: 1,
      next_seven_days: 2,
      sowings_unknown_germination: 3,
      sowings_zero_germination: 1,
      recent_activity: [
        journal,
        {
          ...journal,
          key: "history:1",
          source_kind: "germination",
          title: "Germination",
          status: "reversed",
          occurred_on: null,
          date_basis: "recorded",
        },
      ],
      upcoming: [
        {
          id: "plan",
          title: "Inspect leaves",
          due_on: "2026-10-10",
          overdue: true,
          target: null,
        },
      ],
    },
  });
  render(<DashboardOverview />);
  const recent = await screen.findByRole("region", { name: "Recent activity" });
  expect(within(recent).getByText("Journal")).toBeInTheDocument();
  expect(within(recent).getByText("History")).toBeInTheDocument();
  expect(within(recent).getByText("2024")).toBeInTheDocument();
  expect(within(recent).getByText(/Recorded .*UTC/)).toBeInTheDocument();
  expect(within(recent).getByText("Reversed")).toBeInTheDocument();
  expect(within(recent).queryByText("Inspect leaves")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Inspect leaves" })).toHaveAttribute(
    "href",
    "#/schedule/plan",
  );
  expect(screen.getByRole("link", { name: "Overdue: 1" })).toHaveAttribute(
    "href",
    "#/schedule?window=overdue",
  );
  expect(
    screen.queryByRole("heading", { name: "Propagation" }),
  ).not.toBeInTheDocument();
});
