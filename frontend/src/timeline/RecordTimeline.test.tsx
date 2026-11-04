import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../auth/context";
import * as events from "../events/api";
import * as schedule from "../schedule/api";
import { localDay } from "../schedule/state";
import { JournalScope } from "../events/JournalScope";
import { useJournalReader } from "../events/journalReader";
import { RecordTimeline } from "./RecordTimeline";

vi.mock("../events/api", () => ({ listEvents: vi.fn() }));
vi.mock("../schedule/api", () => ({ listSchedule: vi.fn() }));
const auth = { sessionExpired: vi.fn() } as unknown as AuthContextValue;
type Item = schedule.SchedulePage["items"][number];
type Event = events.EventResponse;

function planned(overrides: Partial<Item>): Item {
  return {
    id: "a1",
    activity_kind: "repot",
    title: "Repot basil",
    due_on: "2026-10-01",
    notes: null,
    status: "planned",
    version: 1,
    overdue: false,
    target: { kind: "plant", id: "p", label: "Basil", lifecycle: "active" },
    linked_event_id: null,
    created_at: "2026-09-30T12:00:00Z",
    updated_at: "2026-09-30T12:00:00Z",
    completed_at: null,
    cancelled_at: null,
    ...overrides,
  };
}
function event(overrides: Partial<Event>): Event {
  return {
    id: "e1",
    kind: "flowering",
    occurred_on: { precision: "day", year: 2026, month: 6, day: 3 },
    notes: "First flowers",
    target: { kind: "plant", id: "p" },
    harvest_id: null,
    created_at: "2026-06-03T12:00:00Z",
    updated_at: "2026-06-03T12:00:00Z",
    ...overrides,
  } as Event;
}
function mount(element: React.ReactElement) {
  return render(
    <AuthContext.Provider value={auth}>{element}</AuthContext.Provider>,
  );
}

beforeEach(() => {
  vi.mocked(schedule.listSchedule).mockResolvedValue({
    items: [
      planned({
        id: "late",
        title: "Repot basil",
        due_on: "2026-01-01",
        overdue: true,
      }),
      planned({ id: "next", title: "Pinch tips", due_on: "2099-01-01" }),
    ],
    total: 5,
    offset: 0,
    limit: 3,
    today: localDay(),
    overdue_count: 1,
    today_count: 0,
  });
});
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

test("planned work stays planned, overdue is not shown as done, and Journal dates keep their precision", async () => {
  vi.mocked(events.listEvents).mockResolvedValue([
    event({ id: "day" }),
    event({
      id: "month",
      kind: "repotting",
      notes: null,
      occurred_on: { precision: "month", year: 2025, month: 4, day: null },
    }),
    event({
      id: "year",
      kind: "observation",
      notes: null,
      occurred_on: { precision: "year", year: 2024, month: null, day: null },
    }),
    event({ id: "undated", occurred_on: null }),
  ]);
  const onOpen = vi.fn();
  mount(
    <RecordTimeline
      kind="plant"
      id="p"
      journal={{ target: "plant", href: "#/plants/p?tab=events", onOpen }}
    />,
  );
  const timeline = screen.getByRole("region", { name: "Almanac" });
  const plannedLane = within(timeline).getByRole("region", { name: "Planned" });
  const late = (
    await within(plannedLane).findByRole("link", { name: "Repot basil" })
  ).closest("li");
  expect(late).toHaveTextContent("Overdue · not recorded as done");
  expect(
    within(plannedLane).getByRole("link", { name: "Pinch tips" }).closest("li"),
  ).toHaveTextContent("Planned");
  expect(
    within(plannedLane).getByRole("link", { name: "View all 5 in Schedule" }),
  ).toHaveAttribute("href", "#/schedule?target_kind=plant&target_id=p");
  expect(
    within(plannedLane).getByRole("link", { name: "Schedule activity" }),
  ).toHaveAttribute(
    "href",
    "#/schedule?target_kind=plant&target_id=p&action=create",
  );
  expect(schedule.listSchedule).toHaveBeenCalledWith(
    expect.objectContaining({
      target_kind: ["plant"],
      target_id: "p",
      status: ["planned"],
    }),
    0,
    3,
    expect.any(AbortSignal),
  );

  const recordedLane = within(timeline).getByRole("region", {
    name: "Recorded",
  });
  const entries = await within(recordedLane).findAllByRole("listitem");
  expect(
    entries.map((entry) => entry.querySelector("time")?.textContent),
  ).toEqual(["2026-06-03", "2025-04", "2024"]);
  expect(entries[0]).toHaveTextContent("Flowering");
  expect(entries[0]).toHaveTextContent("Journal · First flowers");
  const open = within(recordedLane).getByRole("link", {
    name: "Open Journal (4 entries)",
  });
  await userEvent.click(open);
  expect(onOpen).toHaveBeenCalledOnce();
  expect(
    within(timeline).getByRole("link", { name: "History" }),
  ).toHaveAttribute("href", "#/history?subject_kind=plant");
});

test("records without a Journal point to where observations are kept; inactive records cannot gain plans", async () => {
  mount(
    <RecordTimeline
      kind="seed_lot"
      id="lot"
      current={false}
      recordedElsewhere="Seed lots have no Journal."
    />,
  );
  const recorded = screen.getByRole("region", { name: "Recorded" });
  expect(recorded).toHaveTextContent("Seed lots have no Journal.");
  expect(events.listEvents).not.toHaveBeenCalled();
  await screen.findByRole("link", { name: "Repot basil" });
  expect(screen.queryByRole("link", { name: "Schedule activity" })).toBeNull();
});

test("empty and failed lanes are explicit and retryable", async () => {
  vi.mocked(schedule.listSchedule).mockReset();
  vi.mocked(schedule.listSchedule)
    .mockRejectedValueOnce(new Error("down"))
    .mockResolvedValueOnce({
      items: [],
      total: 0,
      offset: 0,
      limit: 3,
      today: localDay(),
      overdue_count: 0,
      today_count: 0,
    });
  vi.mocked(events.listEvents)
    .mockRejectedValueOnce(new Error("down"))
    .mockResolvedValueOnce([]);
  mount(
    <RecordTimeline
      kind="plant_group"
      id="g"
      journal={{ target: "group", href: "#/plant-groups/g?tab=events" }}
    />,
  );
  await userEvent.click(
    await screen.findByRole("button", { name: "Retry activities" }),
  );
  expect(await screen.findByText("No planned activities.")).toBeVisible();
  await userEvent.click(screen.getByRole("button", { name: "Retry Journal" }));
  expect(await screen.findByText("No Journal entries yet.")).toBeVisible();
  expect(events.listEvents).toHaveBeenLastCalledWith("group", "g");
});

test("inside a record view the Almanac and the Journal share one Journal request", async () => {
  vi.mocked(events.listEvents).mockResolvedValue([event({ id: "one" })]);
  let reader: ReturnType<typeof useJournalReader> | undefined;
  function Probe() {
    reader = useJournalReader();
    return null;
  }
  mount(
    <JournalScope version="v1">
      <RecordTimeline
        kind="plant"
        id="p"
        journal={{ target: "plant", href: "#/plants/p?tab=events" }}
      />
      <Probe />
    </JournalScope>,
  );
  await screen.findByText("Flowering");
  // A second reader (the Journal tab) reuses the response.
  await reader?.read("plant", "p");
  expect(events.listEvents).toHaveBeenCalledTimes(1);
  // A Journal mutation invalidates; the next read asks again.
  reader?.invalidate("plant", "p");
  await reader?.read("plant", "p");
  expect(events.listEvents).toHaveBeenCalledTimes(2);
});
