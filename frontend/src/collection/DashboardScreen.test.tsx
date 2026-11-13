import {
  cleanup,
  fireEvent,
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
import { recordWorkflows } from "../events/recordWorkflows";
import type { Activity } from "../schedule/api";
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
  for (const name of ["Next work", "Recent activity"])
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
    screen.queryByRole("link", { name: "Individual Plants: 0" }),
  ).not.toBeInTheDocument();
  reject(new Error("Offline"));
  expect(await screen.findByRole("alert")).toHaveTextContent("could not load");
  await user.click(screen.getByRole("button", { name: "Retry" }));
  expect(
    await screen.findByRole("link", { name: "Individual Plants: 0" }),
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
  const plan = {
    id: "plan",
    title: "Inspect leaves",
    due_on: "2026-10-10",
    status: "planned",
    overdue: true,
    target: null,
  };
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
      upcoming: [plan],
      overdue_items: [plan],
    },
  });
  render(<DashboardOverview />);
  await screen.findByRole("heading", { name: "Collection snapshot" });
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

function storedPhoto(index: number) {
  return {
    id: `plant-${String(index)}`,
    title: `Botanical photograph ${String(index)}`,
    scientific_name: "Aloe vera",
    image: {
      thumbnail_url: `/api/v1/media-assets/media-${String(index)}/thumbnail`,
      attribution: `Creator ${String(index)}`,
      licence_label: "CC BY 4.0",
      licence_url: "https://creativecommons.org/licenses/by/4.0/",
      source_url: null,
    },
    reference_image: null,
  } satisfies NonNullable<DashboardResponse["photos"]>[number];
}

test("authoritative KPI units and at most four distinct protected photographs retain Plant destinations and attribution", async () => {
  const photos = Array.from({ length: 8 }, (_, index) => storedPhoto(index));
  get.mockResolvedValue({
    ...empty,
    counts: {
      ...empty.counts,
      active_plants: 17,
      active_plant_groups: 7,
      active_seed_lots: 40,
      active_sowings: 12,
    },
    photos,
  });
  render(<DashboardOverview />);
  expect(
    await screen.findByRole("link", { name: "Individual Plants: 17" }),
  ).toHaveAttribute("href", "#/plants?type=plant");
  expect(screen.getByRole("link", { name: "Plant groups: 7" })).toHaveAttribute(
    "href",
    "#/plants?type=group",
  );
  expect(screen.getByRole("link", { name: "Seed lots: 40" })).toHaveAttribute(
    "href",
    "#/seeds",
  );
  const grid = screen.getByRole("list", { name: "Selected individual Plants" });
  const images = within(grid).getAllByRole("img");
  expect(images).toHaveLength(4);
  expect(new Set(images.map((image) => image.getAttribute("src"))).size).toBe(
    4,
  );
  for (const photo of photos.slice(0, 4)) {
    expect(
      within(grid).getByRole("link", { name: photo.title }),
    ).toHaveAttribute("href", `#/plants/${photo.id}`);
    expect(
      within(grid).getByRole("img", { name: photo.title }),
    ).toHaveAttribute("loading", "eager");
  }
  await userEvent.click(screen.getByText("Image attribution"));
  expect(screen.getByText(/Creator 0/)).toBeVisible();
  expect(screen.getAllByRole("link", { name: "CC BY 4.0" })).toHaveLength(4);
  expect(screen.queryByText(/Creator 4/)).not.toBeInTheDocument();
});

test("fewer images are not duplicated, and unavailable images are never drawn as placeholders or loaded remotely", async () => {
  const photo = storedPhoto(1);
  get.mockResolvedValue({
    ...empty,
    photos: [
      photo,
      {
        ...storedPhoto(2),
        image: null,
        reference_image: {
          ...storedPhoto(2).image,
          thumbnail_url: "https://external.invalid/do-not-load.jpg",
        },
      },
    ],
  });
  render(<DashboardOverview />);
  const image = await screen.findByRole("img", { name: photo.title });
  expect(screen.getAllByRole("img")).toHaveLength(1);
  expect(image).toHaveAttribute("src", photo.image.thumbnail_url);
  expect(
    within(
      screen.getByRole("list", { name: "Selected individual Plants" }),
    ).getAllByRole("listitem"),
  ).toHaveLength(1);
  expect(screen.queryByText("No photograph")).not.toBeInTheDocument();
  fireEvent.error(image);
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
  expect(
    screen.queryByRole("list", { name: "Selected individual Plants" }),
  ).not.toBeInTheDocument();
  expect(screen.queryByText("No photograph")).not.toBeInTheDocument();
  expect(
    screen.getByText(
      /None of the sampled Plants has a photo that can be shown yet/,
    ),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "Add photos in Plants" }),
  ).toHaveAttribute("href", "#/plants");
});

test("Plant visit sample stays stable through rerenders, and broken primary falls back to a labelled identity reference", async () => {
  const original = storedPhoto(1);
  const plant: NonNullable<DashboardResponse["photos"]>[number] = {
    ...original,
    reference_image: {
      ...original.image,
      thumbnail_url: "/api/v1/media-assets/reference/thumbnail",
      attribution: "Reference creator",
    },
  };
  get.mockResolvedValue({ ...empty, photos: [plant] });
  const rendered = render(<DashboardOverview />);
  const image = await screen.findByRole("img", { name: plant.title });
  expect(image).toHaveAttribute("src", original.image.thumbnail_url);
  rendered.rerender(<DashboardOverview />);
  expect(get).toHaveBeenCalledTimes(1);
  expect(screen.getByRole("link", { name: plant.title })).toHaveAttribute(
    "href",
    `#/plants/${plant.id}`,
  );
  fireEvent.error(image);
  expect(screen.getByRole("img", { name: plant.title })).toHaveAttribute(
    "src",
    "/api/v1/media-assets/reference/thumbnail",
  );
  expect(screen.getByText("Identity reference", { exact: true })).toBeVisible();
  fireEvent.error(screen.getByRole("img", { name: plant.title }));
  expect(screen.queryByRole("img")).toBeNull();
  expect(screen.queryByRole("link", { name: plant.title })).toBeNull();
  expect(
    screen.getByRole("link", { name: "Add photos in Plants" }),
  ).toBeVisible();
});

test("Today composes its summary only from returned counts and states every source", async () => {
  get.mockResolvedValue({
    ...empty,
    counts: { ...empty.counts, active_plants: 1, active_seed_lots: 7 },
    overview: {
      ...emptyOverview,
      overdue: 1,
      due_today: 2,
      current_identities: 5,
      identities_with_profile: 4,
      identities_with_wfo: 0,
      sowings_unknown_germination: 3,
      sowings_zero_germination: 1,
      sowings_with_germination: 2,
      purchase_packets_without_order: 6,
    },
  });
  render(<DashboardOverview />);
  expect(
    await screen.findByText(
      "1 overdue and 2 due today in the Schedule. You hold 1 active Plant, 0 Plant groups, 7 seed lots and 0 active sowings.",
    ),
  ).toBeInTheDocument();
  expect(screen.getByText("Planned in Schedule")).toBeInTheDocument();
  expect(
    screen.getByText(
      "Recorded in the Journal and derived History, latest first",
    ),
  ).toBeInTheDocument();
  // Always visible (UX-TODAY-001): the former Data quality disclosure is gone.
  const records = screen.getByRole("region", { name: "To review" });
  expect(records.querySelector("details")).toBeNull();
  expect(records).toHaveTextContent(
    "Derived counts of current records. Prompts to review, not tasks or conclusions.",
  );
  for (const [term, value] of [
    ["Active sowings without a germination count", "3"],
    ["Active sowings with zero germinated recorded", "1"],
    ["Active sowings with germination recorded", "2"],
    ["Purchased seed lots without an Order link", "6"],
    ["Current identities with reference knowledge", "4 of 5"],
    ["Current identities with a confirmed WFO link", "0 of 5"],
  ]) {
    const row = within(records).getByText(term).closest("div");
    expect(row).toHaveTextContent(`${term}${value}`);
  }
  expect(records).toHaveTextContent("A zero count is recorded, not a failure.");
  expect(
    screen.getByText(/Overdue is derived from the due date/),
  ).toBeInTheDocument();
});

test("an empty Schedule says so instead of manufacturing work", async () => {
  get.mockResolvedValue(empty);
  render(<DashboardOverview />);
  expect(
    await screen.findByText(
      "Nothing is overdue or due today in the Schedule. You hold 0 active Plants, 0 Plant groups, 0 seed lots and 0 active sowings.",
    ),
  ).toBeInTheDocument();
});

function activity(id: string, due_on: string, extra: Partial<Activity> = {}) {
  return {
    id,
    activity_kind: "inspect",
    title: `Work ${id}`,
    due_on,
    target: null,
    notes: null,
    status: "planned",
    version: 1,
    overdue: due_on < emptyOverview.today,
    linked_event_id: null,
    created_at: "2026-09-01T00:00:00Z",
    updated_at: "2026-09-01T00:00:00Z",
    completed_at: null,
    cancelled_at: null,
    ...extra,
  } satisfies Activity;
}

test("sections follow the work-first order in the DOM, which is also the visual order", async () => {
  get.mockResolvedValue({ ...empty, photos: [storedPhoto(1)] });
  const { container } = render(<DashboardOverview />);
  await screen.findByRole("heading", { name: "Next work" });
  expect(
    screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent),
  ).toEqual([
    "Next work",
    "Recent activity",
    "Record",
    "Collection snapshot",
    "To review",
    "Plants in your collection",
  ]);
  expect(container.querySelector(".today")?.firstElementChild).toHaveClass(
    "today-lede",
  );
});

test("planned work is grouped by window with calendar-day ages, caps and links to the full list", async () => {
  const target = {
    kind: "plant",
    id: "p1",
    label: "Bench lemon",
    lifecycle: "active",
    scientific_name: "Citrus limon",
    cultivar_name: null,
  } as const;
  get.mockResolvedValue({
    ...empty,
    overview: {
      ...emptyOverview,
      overdue: 30,
      due_today: 2,
      next_seven_days: 1,
      upcoming: [activity("old", "2026-10-01")],
      overdue_items: [
        activity("old", "2026-10-01", { target }),
        activity("yesterday", "2026-10-10"),
      ],
      due_today_items: [
        activity("now-1", "2026-10-11"),
        activity("now-2", "2026-10-11"),
      ],
      next_seven_days_items: [activity("soon", "2026-10-14")],
    },
  });
  render(<DashboardOverview />);
  const overdue = await screen.findByRole("region", {
    name: "Overdue 2 earliest of 30",
  });
  const rows = within(overdue).getAllByRole("listitem");
  expect(rows).toHaveLength(2);
  expect(rows[0]).toHaveTextContent("10 days overdue");
  expect(rows[1]).toHaveTextContent("1 day overdue");
  expect(within(rows[0]).getByText("2026-10-01")).toHaveAttribute(
    "datetime",
    "2026-10-01",
  );
  expect(
    within(rows[0]).getByRole("link", { name: "Work old" }),
  ).toHaveAttribute("href", "#/schedule/old");
  expect(
    within(rows[0]).getByRole("link", { name: "Bench lemon" }),
  ).toHaveAttribute("href", "#/plants/p1");
  expect(rows[0]).toHaveTextContent("Bench lemon · Plant · Citrus limon");
  expect(rows[1]).toHaveTextContent("Collection-wide · not tied to a record");
  expect(
    within(overdue).getByRole("link", {
      name: "Overdue: all 30 in Schedule",
    }),
  ).toHaveAttribute("href", "#/schedule?window=overdue");
  const today = screen.getByRole("region", { name: "Due today 2" });
  const due = within(today).getAllByRole("listitem");
  expect(due).toHaveLength(2);
  for (const row of due) expect(row).toHaveTextContent("Due today");
  expect(within(today).queryByRole("link", { name: /all/ })).toBeNull();
  const next = screen.getByRole("region", { name: "Next 7 days 1" });
  expect(within(next).getByRole("listitem")).toHaveTextContent("In 3 days");
  expect(within(next).queryByText("Work old")).toBeNull();
});

test("planned work beyond the three windows is acknowledged, not shown as an empty Schedule", async () => {
  get.mockResolvedValue({
    ...empty,
    overview: { ...emptyOverview, upcoming: [activity("far", "2026-12-01")] },
  });
  render(<DashboardOverview />);
  expect(
    await screen.findByText(/Later planned work is in Schedule/),
  ).toBeInTheDocument();
  expect(screen.queryByText("Work far")).toBeNull();
});

test("no usable image means one line and no photo strip; one image means a one-item strip", async () => {
  get.mockResolvedValue({
    ...empty,
    photos: [{ ...storedPhoto(1), image: null }],
  });
  const first = render(<DashboardOverview />);
  expect(
    await screen.findByText(
      /None of the sampled Plants has a photo that can be shown yet/,
    ),
  ).toBeInTheDocument();
  expect(screen.queryByRole("img")).toBeNull();
  expect(
    screen.queryByRole("heading", { name: "Plants in your collection" }),
  ).toBeNull();
  first.unmount();
  get.mockResolvedValue({
    ...empty,
    photos: [{ ...storedPhoto(1), image: null }, storedPhoto(2)],
  });
  render(<DashboardOverview />);
  expect(await screen.findAllByRole("img")).toHaveLength(1);
  expect(
    within(
      screen.getByRole("list", { name: "Selected individual Plants" }),
    ).getAllByRole("listitem"),
  ).toHaveLength(1);
  expect(screen.queryByText(/photo that can be shown yet/)).toBeNull();
});

test("Record reuses the launcher's workflow links and adds Journal and Schedule entry points", async () => {
  get.mockResolvedValue(empty);
  render(<DashboardOverview />);
  const record = within(
    await screen.findByRole("navigation", { name: "Record choices" }),
  );
  for (const { label, href } of recordWorkflows)
    expect(record.getByRole("link", { name: label })).toHaveAttribute(
      "href",
      href,
    );
  expect(
    record.getByRole("link", { name: "Add Journal entry" }),
  ).toHaveAttribute("href", "#/events");
  expect(
    record.getByRole("link", { name: "Schedule activity" }),
  ).toHaveAttribute("href", "#/schedule?action=create");
  expect(
    screen.getByRole("link", { name: "Botanical identities: 0" }),
  ).toHaveAttribute("href", "#/species-distribution?scope=current");
});
