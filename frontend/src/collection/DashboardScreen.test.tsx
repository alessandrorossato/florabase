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
  await userEvent.click(screen.getByText("Recent activity · 0 latest entries"));
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
  await screen.findByRole("heading", { name: "Collection snapshot" });
  await userEvent.click(screen.getByText(/Recent activity ·/));
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

test("authoritative KPI units and eight distinct protected photographs retain Plant destinations and attribution", async () => {
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
  expect(images).toHaveLength(8);
  expect(new Set(images.map((image) => image.getAttribute("src"))).size).toBe(
    8,
  );
  for (const photo of photos) {
    expect(
      within(grid).getByRole("link", { name: photo.title }),
    ).toHaveAttribute("href", `#/plants/${photo.id}`);
    expect(
      within(grid).getByRole("img", { name: photo.title }),
    ).toHaveAttribute("loading", "eager");
  }
  await userEvent.click(screen.getByText("Image attribution"));
  expect(screen.getByText(/Creator 0/)).toBeVisible();
  expect(screen.getAllByRole("link", { name: "CC BY 4.0" })).toHaveLength(8);
});

test("fewer images are not duplicated and unavailable images retain a useful destination without remote loading", async () => {
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
  expect(screen.getAllByText("No photograph").length).toBeGreaterThan(0);
  fireEvent.error(image);
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: photo.title })).toHaveAttribute(
    "href",
    `#/plants/${photo.id}`,
  );
  expect(screen.getAllByText("No photograph")).toHaveLength(4);
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
  expect(screen.getByRole("link", { name: plant.title })).toBeVisible();
});
