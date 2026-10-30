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
import { AuthContext } from "../../auth/context";
import {
  FixtureSchedule,
  fixtureAuth,
  fixtureId,
  fixtureTargets,
  fixtureToday,
} from "./fixtures";
import { ScheduleUxPrototype } from "./ScheduleUxPrototype";
import { prototypeHash, readPrototype, weekDays } from "./model";
import { localDay, readScheduleState } from "../../schedule/state";

let fixture: FixtureSchedule;
beforeEach(() => {
  fixture = new FixtureSchedule();
  vi.stubGlobal("fetch", fixture.fetch);
  window.history.replaceState(
    null,
    "",
    "#/schedule?month=2026-10&date=2026-10-30",
  );
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
function mount() {
  return render(
    <AuthContext.Provider value={fixtureAuth}>
      <ScheduleUxPrototype fixture={fixture} />
    </AuthContext.Provider>,
  );
}
async function inspect(title = "Repot nursery aloe") {
  await userEvent.click(await screen.findByRole("button", { name: title }));
  return screen.findByLabelText("Activity inspection");
}
async function request(path: string, payload: unknown, method = "POST") {
  return fixture.fetch(`/api/v1/schedule${path}`, {
    method,
    body: JSON.stringify(payload),
  });
}

test("Agenda retains exact targets, due days and current versus historical targets", async () => {
  mount();
  expect(
    await screen.findByRole("button", { name: "Repot nursery aloe" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "Salvia · tray 12" }),
  ).toHaveAttribute("href", `#/sowings/${fixtureId(103)}`);
  const panel = await inspect("Review transferred plant follow-up");
  expect(panel).toHaveTextContent("Historical target retained");
  await userEvent.click(
    within(panel).getByRole("button", { name: "Complete" }),
  );
  expect(
    screen.queryByRole("radio", { name: /Record what happened/ }),
  ).not.toBeInTheDocument();
  await userEvent.click(
    screen.getByRole("button", { name: "Complete without Event" }),
  );
  await waitFor(() => {
    expect(fixture.items[1].status).toBe("completed");
  });
  expect(fixture.events).toHaveLength(0);
});

test("canonical complete dialog defaults to no occurrence and exposes explicit supported Event recording", async () => {
  mount();
  const panel = await inspect();
  await userEvent.click(
    within(panel).getByRole("button", { name: "Complete" }),
  );
  const dialog = screen.getByRole("dialog", { name: "Complete activity" });
  expect(
    within(dialog).getByRole("button", { name: "Complete without Event" }),
  ).toBeInTheDocument();
  const choice = within(dialog).getByRole("radio", {
    name: "Record what happened in Journal",
  });
  expect(choice).not.toBeChecked();
  await userEvent.click(choice);
  expect(within(dialog).getByLabelText(/Actual occurrence date/)).toHaveValue(
    localDay(),
  );
  await userEvent.click(
    within(dialog).getByRole("radio", {
      name: "Complete without a Journal Event",
    }),
  );
  await userEvent.click(
    within(dialog).getByRole("button", { name: "Complete without Event" }),
  );
  await waitFor(() => {
    expect(fixture.items[0].status).toBe("completed");
  });
  expect(fixture.events).toHaveLength(0);
});

test("reschedule conflict retains the draft until explicit reload, then saves with the current version", async () => {
  mount();
  const panel = await inspect();
  await userEvent.click(
    within(panel).getByRole("button", { name: "Edit / reschedule" }),
  );
  const due = screen.getByLabelText(/Due date/);
  fireEvent.change(due, { target: { value: "2026-11-03" } });
  fixture.injectConflict();
  await userEvent.click(screen.getByRole("button", { name: "Save activity" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Reload the current activity",
  );
  expect(due).toHaveValue("2026-11-03");
  await userEvent.click(
    screen.getByRole("button", { name: "Reload current activity" }),
  );
  await waitFor(() => {
    expect(screen.getByLabelText(/Due date/)).toHaveValue("2026-10-28");
  });
  fireEvent.change(screen.getByLabelText(/Due date/), {
    target: { value: "2026-11-03" },
  });
  await userEvent.click(screen.getByRole("button", { name: "Save activity" }));
  await waitFor(() => {
    expect(fixture.items[0].due_on).toBe("2026-11-03");
  });
  expect(fixture.items[0].version).toBe(3);
});

test("failed save retains entered fields and canonical dirty dismissal protects the draft", async () => {
  mount();
  await userEvent.click(
    screen.getByRole("button", { name: "+ Schedule activity" }),
  );
  await userEvent.type(screen.getByLabelText(/Title/), "Inspect trial bench");
  fixture.injectFailure();
  await userEvent.click(screen.getByRole("button", { name: "Save activity" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "entries are still here",
  );
  await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
  expect(
    screen.getByRole("dialog", { name: "Discard unsaved activity changes?" }),
  ).toBeInTheDocument();
  await userEvent.click(
    screen.getByRole("button", { name: "Continue editing" }),
  );
  expect(screen.getByLabelText(/Title/)).toHaveValue("Inspect trial bench");
});

test("date-only week crosses a month and canonical filters and inspection survive serialization", () => {
  expect(weekDays("2026-11-01")).toEqual([
    "2026-10-26",
    "2026-10-27",
    "2026-10-28",
    "2026-10-29",
    "2026-10-30",
    "2026-10-31",
    "2026-11-01",
  ]);
  const state = readScheduleState(
    "#/schedule?status=completed&status=cancelled&target_kind=plant&q=notes&month=2026-11&date=2026-11-01",
  );
  const hash = prototypeHash(state, "week", fixtureId(1));
  window.history.replaceState(null, "", hash);
  expect(readPrototype()).toMatchObject({
    ux: "week",
    selected: fixtureId(1),
    state,
  });
});

test("browser history closes inspection and restores query/date/week without clearing filters", async () => {
  mount();
  await inspect();
  window.history.replaceState(
    null,
    "",
    "#/schedule?ux=week&month=2026-11&date=2026-11-01&q=Water",
  );
  fireEvent(window, new PopStateEvent("popstate"));
  await waitFor(() => {
    expect(
      screen.queryByLabelText("Activity inspection"),
    ).not.toBeInTheDocument();
  });
  expect(
    screen.getByRole("searchbox", { name: "Search Schedule" }),
  ).toHaveValue("Water");
  expect(screen.getByRole("link", { name: "Week" })).toHaveAttribute(
    "aria-current",
    "page",
  );
});

test("terminal cancellation, idempotent completion, target eligibility and explicit Event date stay separate", async () => {
  const item = fixture.items[0];
  const payload = {
    expected_version: 1,
    event: {
      kind: "repotting",
      occurred_on: "2026-10-29",
      notes: "Actual observation",
    },
  };
  expect((await request(`/${item.id}/complete`, payload)).status).toBe(200);
  expect((await request(`/${item.id}/complete`, payload)).status).toBe(200);
  expect(fixture.events).toHaveLength(1);
  expect(fixture.events[0].event.occurred_on).toBe("2026-10-29");
  expect(item.due_on).toBe("2026-10-28");
  expect(
    (await request(`/${item.id}/cancel`, { expected_version: item.version }))
      .status,
  ).toBe(409);
  expect(
    (
      await request(`/${fixtureId(3)}/complete`, {
        expected_version: 1,
        event: { kind: "observation", occurred_on: fixtureToday },
      })
    ).status,
  ).toBe(409);
  expect(
    (
      await request(`/${fixtureId(2)}/complete`, {
        expected_version: 1,
        event: { kind: "observation", occurred_on: fixtureToday },
      })
    ).status,
  ).toBe(409);
  expect(
    (
      await request("", {
        title: "New",
        activity_kind: "inspect",
        due_on: fixtureToday,
        target: fixtureTargets[6],
      })
    ).status,
  ).toBe(409);
  expect(
    (await request(`/${fixtureId(5)}/cancel`, { expected_version: 1 })).status,
  ).toBe(200);
  expect(fixture.items[4].cancelled_at).toBeTruthy();
});

test("fixture transport fails closed and bounds/filter/counts list requests", async () => {
  expect((await fixture.fetch("/api/v1/plants")).status).toBe(503);
  const response = await fixture.fetch(
    "/api/v1/schedule?status=planned&q=Water&limit=1&offset=1",
  );
  expect(await response.json()).toMatchObject({
    items: [],
    total: 1,
    offset: 1,
    limit: 1,
  });
});

test("load failure offers retry and empty search has no fabricated activities", async () => {
  fixture.injectFailure();
  mount();
  expect(await screen.findByRole("alert")).toHaveTextContent("Could not load");
  await userEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(
    await screen.findByRole("button", { name: "Repot nursery aloe" }),
  ).toBeInTheDocument();
  await userEvent.type(
    screen.getByRole("searchbox", { name: "Search Schedule" }),
    "unmatched",
  );
  await waitFor(() => {
    expect(
      screen.queryByRole("button", { name: "Repot nursery aloe" }),
    ).not.toBeInTheDocument();
  });
  expect(screen.getByText(/0 matching activities/)).toBeInTheDocument();
});

test("week loads only the inclusive period through the existing list contract across a month boundary", async () => {
  const { loadWeek } = await import("./model");
  const state = readScheduleState("#/schedule?month=2026-11&date=2026-11-01");
  const page = await loadWeek(state, new AbortController().signal);
  expect(page.total).toBe(9);
  expect(
    page.items.every(
      (row) => row.due_on >= "2026-10-26" && row.due_on <= "2026-11-01",
    ),
  ).toBe(true);
  expect(
    page.items.some((row) => row.title === "Review basil harvest readiness"),
  ).toBe(false);
});

test("closing the inline inspector restores focus to its exact title trigger", async () => {
  mount();
  const title = await screen.findByRole("button", {
    name: "Repot nursery aloe",
  });
  await userEvent.click(title);
  const panel = await screen.findByLabelText("Activity inspection");
  expect(panel).toHaveFocus();
  fireEvent.keyDown(panel, { key: "Escape" });
  expect(title).toHaveFocus();
  expect(
    screen.queryByLabelText("Activity inspection"),
  ).not.toBeInTheDocument();
});
