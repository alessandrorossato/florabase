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
import { ScheduleScreen } from "./ScheduleScreen";
import { UpcomingActivities } from "./UpcomingActivities";
import {
  defaultState,
  localDay,
  readScheduleState,
  scheduleHash,
} from "./state";
vi.mock("./api", () => ({
  listSchedule: vi.fn(),
  listCalendar: vi.fn(),
  getActivity: vi.fn(),
  getTarget: vi.fn(),
  listTargets: vi.fn(),
  writeActivity: vi.fn(),
  transitionActivity: vi.fn(),
}));
const id = "01900000-0000-7000-8000-000000000001";
const target: api.Target = {
  kind: "plant",
  id,
  label: "Basil",
  lifecycle: "active",
};
const expireSession = vi.fn();
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
  sessionExpired: expireSession,
  retryRestoration: vi.fn(),
  cancelLogout: vi.fn(),
};
function item(overrides: Partial<api.Activity> = {}): api.Activity {
  return {
    id,
    activity_kind: "repot",
    title: "Repot basil",
    due_on: "2026-10-01",
    notes: "Future intention",
    status: "planned",
    version: 1,
    overdue: true,
    target: { kind: "plant", id, label: "Basil", lifecycle: "active" },
    linked_event_id: null,
    created_at: "2026-09-30T12:00:00Z",
    updated_at: "2026-09-30T12:00:00Z",
    completed_at: null,
    cancelled_at: null,
    ...overrides,
  };
}
function page(items = [item()]): api.SchedulePage {
  return {
    items,
    total: items.length,
    offset: 0,
    limit: 50,
    today: localDay(),
    overdue_count: 1,
    today_count: 0,
  };
}
function mount(content = <ScheduleScreen />) {
  return render(
    <AuthContext.Provider value={auth}>{content}</AuthContext.Provider>,
  );
}
beforeEach(() => {
  vi.spyOn(window, "matchMedia").mockReturnValue({
    matches: false,
  } as MediaQueryList);
  window.history.replaceState(null, "", "/#/schedule");
  vi.mocked(api.listSchedule).mockResolvedValue(page());
  vi.mocked(api.listCalendar).mockResolvedValue(page());
  vi.mocked(api.listTargets).mockResolvedValue({ items: [target], total: 1 });
  vi.mocked(api.getTarget).mockResolvedValue(target);
  vi.mocked(api.writeActivity).mockResolvedValue(item());
  vi.mocked(api.transitionActivity).mockResolvedValue(
    item({ status: "completed", version: 2 }),
  );
  vi.mocked(api.getActivity).mockResolvedValue(item());
});
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

test("active intentions show explicit due day, overdue and Activity purpose", async () => {
  mount();
  expect(
    await screen.findByRole("button", { name: "Repot basil" }),
  ).toBeVisible();
  expect(api.listSchedule).toHaveBeenCalledTimes(1);
  expect(screen.getByText("Planned · Overdue")).toBeVisible();
  expect(screen.getByRole("heading", { name: "Overdue" })).toBeVisible();
  expect(screen.getByText(/Journal records occurrences/)).toBeVisible();
  expect(screen.getByRole("link", { name: "Basil" })).toHaveAttribute(
    "href",
    `#/plants/${id}`,
  );
});
test("create a concrete future intention without any Event", async () => {
  const u = userEvent.setup();
  mount();
  await u.click(screen.getByRole("button", { name: "Schedule activity" }));
  const d = screen.getByRole("dialog", { name: "Schedule activity" });
  await u.type(within(d).getByLabelText("Title"), "Check greenhouse");
  fireEvent.change(within(d).getByLabelText("Due date"), {
    target: { value: "2026-11-02" },
  });
  await u.click(within(d).getByRole("button", { name: "Save activity" }));
  await waitFor(() => {
    expect(api.writeActivity).toHaveBeenCalledWith(
      null,
      expect.objectContaining({
        title: "Check greenhouse",
        due_on: "2026-11-02",
        target: null,
      }),
      "csrf",
    );
  });
  expect(api.transitionActivity).not.toHaveBeenCalled();
});
test("reschedule uses current version and preserved typed target", async () => {
  const u = userEvent.setup();
  mount();
  await u.click(
    await screen.findByRole("button", { name: "Edit / reschedule" }),
  );
  const d = screen.getByRole("dialog");
  fireEvent.change(within(d).getByLabelText("Due date"), {
    target: { value: "2026-11-09" },
  });
  await screen.findByRole("combobox", { name: "Target record" });
  await u.click(within(d).getByRole("button", { name: "Save activity" }));
  await waitFor(() => {
    expect(api.writeActivity).toHaveBeenCalledWith(
      id,
      expect.objectContaining({
        expected_version: 1,
        due_on: "2026-11-09",
        target: { kind: "plant", id },
      }),
      "csrf",
    );
  });
});
test("completion defaults to no Event; explicit recording asks actual date and notes", async () => {
  const u = userEvent.setup();
  mount();
  await u.click(await screen.findByRole("button", { name: "Complete" }));
  expect(
    screen.getByLabelText("Complete without a Journal Event"),
  ).toBeChecked();
  await u.click(screen.getByRole("button", { name: "Complete without Event" }));
  await waitFor(() => {
    expect(api.transitionActivity).toHaveBeenCalledWith(
      expect.objectContaining({ id, version: 1 }),
      "complete",
      "csrf",
      null,
    );
  });
  await u.click(await screen.findByRole("button", { name: "Complete" }));
  await u.click(screen.getByLabelText("Record what happened in Journal"));
  expect(screen.getByLabelText("Actual occurrence date")).toHaveValue(
    localDay(),
  );
  fireEvent.change(screen.getByLabelText("Actual occurrence date"), {
    target: { value: "2026-10-08" },
  });
  await u.type(
    screen.getByLabelText("Event notes"),
    "Repotted into larger pot",
  );
  await u.click(
    screen.getByRole("button", { name: "Complete and record Event" }),
  );
  await waitFor(() => {
    expect(api.transitionActivity).toHaveBeenLastCalledWith(
      expect.objectContaining({ id }),
      "complete",
      "csrf",
      {
        kind: "repotting",
        occurred_on: "2026-10-08",
        notes: "Repotted into larger pot",
        destination_location_id: null,
      },
    );
  });
});
test("cancel confirmation retains planning evidence and sends version", async () => {
  const u = userEvent.setup();
  mount();
  await u.click(await screen.findByRole("button", { name: "Cancel activity" }));
  expect(screen.getByText(/planning record will remain/)).toBeVisible();
  await u.click(screen.getByRole("button", { name: "Confirm cancellation" }));
  await waitFor(() => {
    expect(api.transitionActivity).toHaveBeenCalledWith(
      expect.objectContaining({ version: 1 }),
      "cancel",
      "csrf",
      null,
    );
  });
});
test("stale save preserves entries and offers current server reload", async () => {
  vi.mocked(api.writeActivity).mockRejectedValueOnce(new ApiError(409));
  const u = userEvent.setup();
  mount();
  await u.click(
    await screen.findByRole("button", { name: "Edit / reschedule" }),
  );
  await screen.findByRole("combobox", { name: "Target record" });
  await u.clear(screen.getByLabelText("Title"));
  await u.type(screen.getByLabelText("Title"), "My correction");
  await u.click(screen.getByRole("button", { name: "Save activity" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("changed");
  expect(screen.getByLabelText("Title")).toHaveValue("My correction");
  vi.mocked(api.getActivity).mockResolvedValueOnce(
    item({ version: 2, title: "Another operator's correction" }),
  );
  await u.click(
    screen.getByRole("button", { name: "Reload current activity" }),
  );
  await waitFor(() => {
    expect(screen.getByLabelText("Title")).toHaveValue(
      "Another operator's correction",
    );
  });
});
test("contextual create resolves exact selected target", async () => {
  window.history.replaceState(
    null,
    "",
    `/#/schedule?target_kind=plant&target_id=${id}&action=create`,
  );
  mount();
  const d = await screen.findByRole("dialog", { name: "Schedule activity" });
  expect(within(d).getByLabelText("Target type")).toHaveValue("plant");
  expect(
    await screen.findByRole("combobox", { name: "Target record" }),
  ).toHaveValue("Basil");
  expect(api.getTarget).toHaveBeenCalledWith(
    "plant",
    id,
    expect.any(AbortSignal),
  );
});
test("filters have deterministic URLs and Back/Forward restores query", async () => {
  const u = userEvent.setup();
  mount();
  await u.click(screen.getByRole("button", { name: "Filters" }));
  await u.selectOptions(screen.getByLabelText("Date window"), "overdue");
  expect(window.location.hash).toBe("#/schedule?window=overdue");
  await u.selectOptions(screen.getByLabelText("Status"), "completed");
  expect(window.location.hash).toBe("#/schedule?status=completed");
  window.history.replaceState(null, "", "/#/schedule?window=today");
  fireEvent(window, new PopStateEvent("popstate"));
  expect(screen.getByLabelText("Date window")).toHaveValue("today");
});
test("completed and cancelled evidence remains inspectable with no write actions", async () => {
  vi.mocked(api.listSchedule).mockResolvedValue(
    page([item({ status: "completed", overdue: false })]),
  );
  window.history.replaceState(null, "", "/#/schedule?status=completed");
  mount();
  await screen.findByRole("button", { name: "Repot basil" });
  expect(
    screen.queryByRole("button", { name: "Complete" }),
  ).not.toBeInTheDocument();
  expect(screen.getByText("Completed without a Journal Event")).toBeVisible();
});
test("keyboard modal closes with Escape and returns focus", async () => {
  const u = userEvent.setup();
  mount();
  const button = screen.getByRole("button", { name: "Schedule activity" });
  button.focus();
  await u.keyboard("{Enter}");
  expect(screen.getByRole("dialog")).toBeVisible();
  expect(screen.getByLabelText("Title")).toHaveFocus();
  await u.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(button).toHaveFocus();
});
test("errors, retry and empty state remain usable", async () => {
  vi.mocked(api.listSchedule).mockRejectedValueOnce(new ApiError(500));
  mount();
  await screen.findByRole("alert");
  vi.mocked(api.listSchedule).mockResolvedValueOnce(page([]));
  fireEvent.click(screen.getByRole("button", { name: "Retry Schedule" }));
  expect(await screen.findByText("No planned activities yet.")).toBeVisible();
});
test("bounded entity and Dashboard summaries link to canonical Schedule filters", async () => {
  mount(<UpcomingActivities kind="plant" id={id} />);
  await screen.findByRole("link", { name: "Repot basil" });
  expect(api.listSchedule).toHaveBeenCalledWith(
    expect.objectContaining({ target_kind: "plant", target_id: id }),
    0,
    3,
    expect.any(AbortSignal),
  );
  expect(
    screen.getByRole("link", { name: "Schedule activity" }),
  ).toHaveAttribute(
    "href",
    `#/schedule?target_kind=plant&target_id=${id}&action=create`,
  );
});
test("URL parser rejects unsupported manager dimensions and invalid targets", () => {
  expect(
    readScheduleState(
      "#/schedule?status=overdue&target_id=broken&priority=high",
    ),
  ).toEqual(defaultState);
  expect(
    scheduleHash({
      ...defaultState,
      activity_kind: "repot",
      target_kind: "plant",
      q: " basil ",
    }),
  ).toBe("#/schedule?activity_kind=repot&target_kind=plant&q=basil");
});

test("date groups and displayed day use the same returned projection across midnight", async () => {
  const response = page([item({ due_on: "2026-01-02", overdue: false })]);
  response.today = "2026-01-02";
  vi.mocked(api.listSchedule).mockResolvedValue(response);
  mount();
  expect(
    await screen.findByRole("heading", { name: "Today", level: 3 }),
  ).toBeVisible();
  expect(screen.getByText(/Local day: 2026-01-02/)).toBeVisible();
  expect(
    screen.queryByRole("heading", { name: "Overdue", level: 3 }),
  ).not.toBeInTheDocument();
});

test("expired read session invokes the established authentication recovery once", async () => {
  vi.mocked(api.listSchedule).mockRejectedValueOnce(new ApiError(401));
  mount();
  await waitFor(() => {
    expect(expireSession).toHaveBeenCalledTimes(1);
  });
  expect(
    screen.queryByText("Florabase could not load Schedule."),
  ).not.toBeInTheDocument();
});

test("editing a retained inactive target keeps its actual lifecycle label", async () => {
  const inactive = { ...target, lifecycle: "transferred" };
  vi.mocked(api.listSchedule).mockResolvedValue(
    page([item({ target: inactive })]),
  );
  vi.mocked(api.listTargets).mockResolvedValue({ items: [inactive], total: 1 });
  const user = userEvent.setup();
  mount();
  await user.click(
    await screen.findByRole("button", { name: "Edit / reschedule" }),
  );
  expect(
    await screen.findByText("Current selection is transferred."),
  ).toBeVisible();
  expect(
    screen.queryByText("Current selection is retired."),
  ).not.toBeInTheDocument();
  expect(
    within(screen.getByRole("dialog")).getByRole("combobox", {
      name: "Target record",
    }),
  ).toHaveValue("Basil");
});

function calendarRoute(extra = "") {
  window.history.replaceState(
    null,
    "",
    `/#/schedule?view=calendar&month=2026-10${extra}`,
  );
}

test("List and Calendar share filters, link URLs and restore browser state", async () => {
  window.history.replaceState(
    null,
    "",
    "/#/schedule?window=overdue&activity_kind=repot&q=basil",
  );
  const user = userEvent.setup();
  mount();
  await user.click(screen.getByRole("link", { name: "Calendar" }));
  expect(screen.getByRole("link", { name: "Calendar" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  expect(window.location.hash).toContain(
    "window=overdue&activity_kind=repot&q=basil&view=calendar",
  );
  await waitFor(() => {
    expect(api.listCalendar).toHaveBeenCalledWith(
      expect.objectContaining({
        window: "overdue",
        activity_kind: "repot",
        q: "basil",
      }),
      expect.any(AbortSignal),
    );
  });
  await user.click(screen.getByRole("link", { name: "List" }));
  expect(window.location.hash).toBe(
    "#/schedule?window=overdue&activity_kind=repot&q=basil",
  );
  calendarRoute("&status=cancelled&date=2026-10-15");
  fireEvent(window, new PopStateEvent("popstate"));
  expect(screen.getByRole("link", { name: "Calendar" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  expect(
    screen.getByRole("button", { name: /Thursday, 15 October 2026/ }),
  ).toHaveAttribute("aria-pressed", "true");
});

test("month navigation crosses year boundary and Today returns to local month/day", async () => {
  calendarRoute();
  const user = userEvent.setup();
  mount();
  await user.click(screen.getByRole("button", { name: "Next month" }));
  expect(screen.getByRole("heading", { name: "November 2026" })).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Next month" }));
  await user.click(screen.getByRole("button", { name: "Next month" }));
  expect(screen.getByRole("heading", { name: "January 2027" })).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Previous month" }));
  expect(screen.getByRole("heading", { name: "December 2026" })).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Today" }));
  expect(window.location.hash).toContain(
    `month=${localDay().slice(0, 7)}&date=${localDay()}`,
  );
  expect(screen.getByRole("button", { name: /, today,/ })).toHaveAttribute(
    "aria-current",
    "date",
  );
});

test("overflow is bounded, day drawer reveals every item and keyboard returns focus", async () => {
  calendarRoute();
  vi.mocked(api.listCalendar).mockResolvedValue(
    page(
      Array.from({ length: 6 }, (_, i) =>
        item({
          id: `${id}-${String(i)}`,
          title: `Work ${String(i)}`,
          due_on: "2026-10-01",
        }),
      ),
    ),
  );
  const user = userEvent.setup();
  mount();
  const more = await screen.findByRole("button", {
    name: "4 more activities on Thursday, 1 October 2026",
  });
  expect(
    within(screen.getByRole("table")).getAllByRole("button", { name: /^Work/ }),
  ).toHaveLength(2);
  more.focus();
  await user.keyboard("{Enter}");
  const drawer = screen.getByRole("dialog", {
    name: "Scheduled work · Thursday, 1 October 2026",
  });
  expect(
    within(drawer).getByRole("button", { name: "Close day" }),
  ).toHaveFocus();
  expect(within(drawer).getAllByRole("button", { name: /^Work/ })).toHaveLength(
    6,
  );
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(more).toHaveFocus();
  expect(api.listCalendar).toHaveBeenCalledTimes(1);
});

test("selected-date create and day actions reuse versioned Schedule dialogs including conflicts", async () => {
  calendarRoute();
  const user = userEvent.setup();
  mount();
  const day = await screen.findByRole("button", {
    name: /Thursday, 1 October 2026,/,
  });
  await user.click(day);
  let drawer = screen.getByRole("dialog");
  await user.click(
    within(drawer).getByRole("button", { name: "Add activity" }),
  );
  let form = screen.getByRole("dialog", { name: "Schedule activity" });
  expect(within(form).getByLabelText("Due date")).toHaveValue("2026-10-01");
  await user.type(within(form).getByLabelText("Title"), "Day planning");
  await user.click(within(form).getByRole("button", { name: "Save activity" }));
  await waitFor(() => {
    expect(api.writeActivity).toHaveBeenCalledWith(
      null,
      expect.objectContaining({ due_on: "2026-10-01", title: "Day planning" }),
      "csrf",
    );
  });
  drawer = screen.getByRole("dialog", { name: /Scheduled work/ });
  await within(drawer).findByRole("button", { name: "Edit / reschedule" });
  await user.click(
    within(drawer).getByRole("button", { name: "Edit / reschedule" }),
  );
  form = screen.getByRole("dialog", { name: "Edit / reschedule activity" });
  await within(form).findByRole("combobox", { name: "Target record" });
  fireEvent.change(within(form).getByLabelText("Due date"), {
    target: { value: "2026-11-01" },
  });
  vi.mocked(api.writeActivity).mockRejectedValueOnce(new ApiError(409));
  await user.click(within(form).getByRole("button", { name: "Save activity" }));
  expect(await within(form).findByRole("alert")).toHaveTextContent("changed");
  expect(within(form).getByLabelText("Due date")).toHaveValue("2026-11-01");
  expect(api.writeActivity).toHaveBeenLastCalledWith(
    id,
    expect.objectContaining({ expected_version: 1, due_on: "2026-11-01" }),
    "csrf",
  );
  await user.keyboard("{Escape}");
  await user.click(screen.getByRole("button", { name: "Discard changes" }));
  expect(
    within(drawer).getByRole("button", { name: "Edit / reschedule" }),
  ).toHaveFocus();
  await user.click(within(drawer).getByRole("button", { name: "Complete" }));
  await user.click(
    screen.getByRole("button", { name: "Complete without Event" }),
  );
  await waitFor(() => {
    expect(api.transitionActivity).toHaveBeenCalledWith(
      expect.objectContaining({ version: 1 }),
      "complete",
      "csrf",
      null,
    );
  });
  await within(drawer).findByRole("button", { name: "Cancel activity" });
  await user.click(
    within(drawer).getByRole("button", { name: "Cancel activity" }),
  );
  await user.click(
    screen.getByRole("button", { name: "Confirm cancellation" }),
  );
  await waitFor(() => {
    expect(api.transitionActivity).toHaveBeenLastCalledWith(
      expect.objectContaining({ version: 1 }),
      "cancel",
      "csrf",
      null,
    );
  });
});

test("terminal calendar evidence uses explicit state and no completion actions", async () => {
  calendarRoute("&status=cancelled");
  vi.mocked(api.listCalendar).mockResolvedValue(
    page([item({ status: "cancelled", overdue: false })]),
  );
  const user = userEvent.setup();
  mount();
  await user.click(
    await screen.findByRole("button", { name: /Thursday, 1 October 2026,/ }),
  );
  const drawer = screen.getByRole("dialog");
  expect(
    within(drawer).getByText("Cancelled", { selector: "strong" }),
  ).toBeVisible();
  expect(
    within(drawer).queryByRole("button", { name: "Complete" }),
  ).not.toBeInTheDocument();
});

test("mobile day selection exposes inline work and date prefill without a modal", async () => {
  vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({ matches: true }));
  try {
    calendarRoute();
    const user = userEvent.setup();
    mount();
    await user.click(
      await screen.findByRole("button", { name: /Thursday, 1 October 2026,/ }),
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    const agenda = screen.getByRole("region", {
      name: "Thursday, 1 October 2026",
    });
    expect(
      within(agenda).getByRole("button", { name: "Repot basil" }),
    ).toBeVisible();
    await user.click(
      within(agenda).getByRole("button", { name: "Add activity" }),
    );
    expect(screen.getByLabelText("Due date")).toHaveValue("2026-10-01");
  } finally {
    vi.unstubAllGlobals();
  }
});

test("Calendar loading, retry, empty filtered period and reset preserve presentation", async () => {
  calendarRoute("&activity_kind=water");
  vi.mocked(api.listCalendar).mockRejectedValueOnce(new ApiError(500));
  mount();
  expect(
    screen.getAllByText("Loading scheduled activities…").length,
  ).toBeGreaterThan(0);
  await screen.findByRole("alert");
  vi.mocked(api.listCalendar).mockResolvedValue(page([]));
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(
    await screen.findByText("No activities match this month and its filters."),
  ).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Reset filters" }));
  expect(window.location.hash).toBe("#/schedule?view=calendar&month=2026-10");
});

test("calendar target uses scientific typography only on exact scientific fields", async () => {
  calendarRoute();
  vi.mocked(api.listCalendar).mockResolvedValue(
    page([
      item({
        target: {
          kind: "botanical_identity",
          id,
          label: "Ocimum basilicum ‘Genovese’",
          lifecycle: null,
          scientific_name: "Ocimum basilicum",
          cultivar_name: "Genovese",
        },
      }),
    ]),
  );
  const user = userEvent.setup();
  mount();
  await user.click(
    await screen.findByRole("button", { name: /Thursday, 1 October 2026,/ }),
  );
  const drawer = screen.getByRole("dialog");
  const name = within(drawer).getByText("Ocimum basilicum");
  expect(name.tagName).toBe("I");
  expect(name).toHaveClass("scientific-name");
  expect(name).not.toHaveTextContent("Genovese");
  expect(
    within(drawer).getByRole("link", { name: "Ocimum basilicum ‘Genovese’" }),
  ).toBeVisible();
});

test.each([0, 1, 50])(
  "target results with %i records suppress pagination",
  async (total) => {
    vi.mocked(api.listTargets).mockResolvedValue({
      items: total ? [target] : [],
      total,
    });
    mount();
    await userEvent.click(
      screen.getByRole("button", { name: "Schedule activity" }),
    );
    fireEvent.change(
      within(screen.getByRole("dialog")).getByLabelText("Target type"),
      {
        target: { value: "plant" },
      },
    );
    const group = await screen.findByRole("group", { name: "Target record" });
    expect(
      await within(group).findByText(
        `${String(total)} matching ${total === 1 ? "record" : "records"}`,
      ),
    ).toBeVisible();
    expect(
      within(group).getByRole("searchbox", { name: "Find collection record" }),
    ).toBeVisible();
    expect(
      within(group).getByRole("combobox", { name: "Target record" }),
    ).toBeVisible();
    expect(
      within(group).queryByRole("navigation", { name: "Target record pages" }),
    ).not.toBeInTheDocument();
    expect(
      within(group).queryByRole("button", { name: "Next records" }),
    ).not.toBeInTheDocument();
  },
);

test("target pages remain bounded and preserve selection while server search resets offset", async () => {
  const other = {
    ...target,
    id: "01900000-0000-7000-8000-000000000002",
    label: "Aloe",
  };
  vi.mocked(api.listTargets)
    .mockResolvedValueOnce({ items: [target], total: 51 })
    .mockResolvedValueOnce({ items: [other], total: 51 })
    .mockResolvedValue({ items: [target], total: 1 });
  const user = userEvent.setup();
  mount();
  await user.click(screen.getByRole("button", { name: "Schedule activity" }));
  fireEvent.change(
    within(screen.getByRole("dialog")).getByLabelText("Target type"),
    {
      target: { value: "plant" },
    },
  );
  const group = await screen.findByRole("group", { name: "Target record" });
  await within(group).findByText("51 matching records");
  const picker = within(group).getByRole("combobox", { name: "Target record" });
  await user.click(picker);
  await user.click(within(group).getByRole("button", { name: "Basil" }));
  const nav = within(group).getByRole("navigation", {
    name: "Target record pages",
  });
  expect(
    within(nav).getByRole("button", { name: "Previous records" }),
  ).toBeDisabled();
  await user.click(within(nav).getByRole("button", { name: "Next records" }));
  await within(group).findByText("Page 2");
  const secondNav = within(group).getByRole("navigation", {
    name: "Target record pages",
  });
  expect(
    within(secondNav).getByRole("button", { name: "Next records" }),
  ).toBeDisabled();
  expect(
    within(secondNav).getByRole("button", { name: "Previous records" }),
  ).toBeEnabled();
  expect(
    within(group).getByRole("combobox", { name: "Target record" }),
  ).toHaveValue("Basil");
  expect(api.listTargets).toHaveBeenLastCalledWith(
    "plant",
    "",
    50,
    expect.any(AbortSignal),
  );
  await user.type(
    within(group).getByRole("searchbox", { name: "Find collection record" }),
    "b",
  );
  await waitFor(() => {
    expect(api.listTargets).toHaveBeenLastCalledWith(
      "plant",
      "b",
      0,
      expect.any(AbortSignal),
    );
  });
  await within(group).findByText("1 matching record");
  expect(
    within(group).getByRole("combobox", { name: "Target record" }),
  ).toHaveValue("Basil");
});

test("Calendar reset stays in the toolbar and preserves its month/day and browser history", async () => {
  calendarRoute(
    "&status=completed&window=later&activity_kind=repot&target_kind=plant&q=missing&date=2026-10-14",
  );
  vi.mocked(api.listCalendar).mockResolvedValue(page([]));
  mount();
  await screen.findByText("No activities match this month and its filters.");
  const controls = screen.getByRole("group", { name: "Schedule controls" });
  const reset = within(controls).getByRole("button", { name: "Reset filters" });
  expect(screen.getAllByRole("button", { name: "Reset filters" })).toHaveLength(
    1,
  );
  const push = vi.spyOn(window.history, "pushState");
  await userEvent.click(reset);
  expect(window.location.hash).toBe(
    "#/schedule?view=calendar&month=2026-10&date=2026-10-14",
  );
  expect(push).toHaveBeenCalledWith(null, "", window.location.hash);
  expect(
    screen.queryByRole("button", { name: "Reset filters" }),
  ).not.toBeInTheDocument();
  push.mockRestore();
});

test("Calendar period changes alone never expose filter Reset", async () => {
  calendarRoute();
  mount();
  await userEvent.click(screen.getByRole("button", { name: "Next month" }));
  expect(window.location.hash).toBe("#/schedule?view=calendar&month=2026-11");
  expect(
    screen.queryByRole("button", { name: "Reset filters" }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByRole("navigation", { name: "Calendar period" }),
  ).toContainElement(screen.getByRole("button", { name: "Today" }));
});

test("empty default List is compact, truthful and has no pagination or reset", async () => {
  vi.mocked(api.listSchedule).mockResolvedValue(page([]));
  mount();
  expect(await screen.findByText("No planned activities yet.")).toBeVisible();
  expect(
    screen.queryByRole("navigation", { name: "Schedule pages" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Reset filters" }),
  ).not.toBeInTheDocument();
  expect(screen.queryByText("Page 1")).not.toBeInTheDocument();
  expect(api.listSchedule).toHaveBeenCalledTimes(1);
});

test("empty filtered List resets all filters from the shared toolbar", async () => {
  window.history.replaceState(
    null,
    "",
    "/#/schedule?status=completed&q=missing",
  );
  vi.mocked(api.listSchedule)
    .mockResolvedValueOnce(page([]))
    .mockResolvedValueOnce(page([item({ status: "completed" })]))
    .mockResolvedValueOnce(page([item({ status: "completed" })]));
  mount();
  expect(
    await screen.findByText("No activities match these filters."),
  ).toBeVisible();
  expect(
    screen.queryByRole("navigation", { name: "Schedule pages" }),
  ).not.toBeInTheDocument();
  await userEvent.click(
    await screen.findByRole("button", { name: "Reset filters" }),
  );
  expect(window.location.hash).toBe("#/schedule");
  expect(api.listSchedule).toHaveBeenCalledWith(
    expect.objectContaining({ status: "completed", q: "", window: "all" }),
    0,
    1,
    expect.any(AbortSignal),
  );
});

test("empty underlying List stays truthful while toolbar offers active-filter reset", async () => {
  window.history.replaceState(null, "", "/#/schedule?q=missing");
  vi.mocked(api.listSchedule).mockResolvedValue(page([]));
  mount();
  expect(await screen.findByText("No planned activities yet.")).toBeVisible();
  expect(api.listSchedule).toHaveBeenCalledTimes(2);
  expect(
    within(screen.getByRole("group", { name: "Schedule controls" })).getByRole(
      "button",
      { name: "Reset filters" },
    ),
  ).toBeVisible();
  expect(
    within(screen.getByRole("status")).queryByRole("button", {
      name: "Reset filters",
    }),
  ).not.toBeInTheDocument();
});

test.each(["completed", "cancelled"] as const)(
  "empty %s status does not claim there are no ScheduledActivity records",
  async (status) => {
    window.history.replaceState(null, "", `/#/schedule?status=${status}`);
    vi.mocked(api.listSchedule).mockResolvedValue(page([]));
    mount();
    expect(await screen.findByText(`No ${status} activities.`)).toBeVisible();
    expect(
      within(
        screen.getByRole("group", { name: "Schedule controls" }),
      ).getByRole("button", { name: "Reset filters" }),
    ).toBeVisible();
  },
);

test("List pagination is retained only for multiple populated pages", async () => {
  vi.mocked(api.listSchedule).mockResolvedValue({ ...page(), total: 51 });
  mount();
  expect(
    await screen.findByRole("navigation", { name: "Schedule pages" }),
  ).toBeVisible();
  expect(screen.getByRole("button", { name: "Next" })).toBeEnabled();
});

test("a concurrently emptied last List page returns to existing activities", async () => {
  vi.mocked(api.listSchedule)
    .mockResolvedValueOnce({ ...page(), total: 51 })
    .mockResolvedValueOnce({ ...page([]), total: 50 })
    .mockResolvedValueOnce({ ...page(), total: 50 });
  mount();
  await userEvent.click(await screen.findByRole("button", { name: "Next" }));
  expect(await screen.findByText("50 active activities")).toBeVisible();
  expect(api.listSchedule).toHaveBeenLastCalledWith(
    expect.anything(),
    0,
    50,
    expect.any(AbortSignal),
  );
  expect(
    screen.queryByText("No planned activities yet."),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("navigation", { name: "Schedule pages" }),
  ).not.toBeInTheDocument();
});

test.each(["Escape", "backdrop", "Cancel"])(
  "pristine create closes via %s and returns focus",
  async (via) => {
    const user = userEvent.setup();
    mount();
    const trigger = screen.getByRole("button", { name: "Schedule activity" });
    await user.click(trigger);
    const dialog = screen.getByRole("dialog", { name: "Schedule activity" });
    // Interior clicks must not count as backdrop dismissal.
    fireEvent.click(dialog, { clientX: 0, clientY: 0 });
    expect(dialog).toBeVisible();
    if (via === "Escape") await user.keyboard("{Escape}");
    else if (via === "backdrop")
      fireEvent.click(dialog, { clientX: -1, clientY: -1 });
    else
      await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
    expect(
      screen.queryByRole("dialog", {
        name: "Discard unsaved activity changes?",
      }),
    ).not.toBeInTheDocument();
  },
);

test.each(["Escape", "backdrop", "Cancel"])(
  "dirty create protects entries via %s until explicit discard",
  async (via) => {
    const user = userEvent.setup();
    mount();
    const trigger = screen.getByRole("button", { name: "Schedule activity" });
    await user.click(trigger);
    const dialog = screen.getByRole("dialog", { name: "Schedule activity" });
    await user.type(
      within(dialog).getByLabelText("Title"),
      "Keep this intention",
    );
    async function dismiss() {
      if (via === "Escape") await user.keyboard("{Escape}");
      else if (via === "backdrop")
        fireEvent.click(dialog, { clientX: -1, clientY: -1 });
      else
        await user.click(
          within(dialog).getByRole("button", { name: "Cancel" }),
        );
    }
    await dismiss();
    expect(
      screen.getByRole("dialog", { name: "Discard unsaved activity changes?" }),
    ).toBeVisible();
    expect(dialog).toBeVisible();
    expect(within(dialog).getByLabelText("Title")).toHaveValue(
      "Keep this intention",
    );
    expect(api.writeActivity).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Continue editing" }));
    expect(within(dialog).getByLabelText("Title")).toHaveValue(
      "Keep this intention",
    );
    await dismiss();
    await user.click(screen.getByRole("button", { name: "Discard changes" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  },
);

test("edit date changes are protected and reverting them restores pristine dismissal", async () => {
  const user = userEvent.setup();
  mount();
  const trigger = await screen.findByRole("button", {
    name: "Edit / reschedule",
  });
  await user.click(trigger);
  const dialog = screen.getByRole("dialog");
  fireEvent.change(within(dialog).getByLabelText("Due date"), {
    target: { value: "2026-11-05" },
  });
  await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
  expect(dialog).toBeVisible();
  expect(within(dialog).getByLabelText("Due date")).toHaveValue("2026-11-05");
  await user.click(screen.getByRole("button", { name: "Continue editing" }));
  fireEvent.change(within(dialog).getByLabelText("Due date"), {
    target: { value: "2026-10-01" },
  });
  await user.keyboard("{Escape}");
  expect(
    screen.queryByRole("dialog", { name: "Discard unsaved activity changes?" }),
  ).not.toBeInTheDocument();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(trigger).toHaveFocus();
});

test("pending save cannot dismiss or submit twice and successful save returns focus", async () => {
  const user = userEvent.setup();
  let resolve: (activity: api.Activity) => void = () => {
    throw new Error("save not started");
  };
  vi.mocked(api.writeActivity).mockReturnValueOnce(
    new Promise((r) => {
      resolve = r;
    }),
  );
  mount();
  const trigger = screen.getByRole("button", { name: "Schedule activity" });
  await user.click(trigger);
  const dialog = screen.getByRole("dialog");
  await user.type(within(dialog).getByLabelText("Title"), "Save one intention");
  await user.click(
    within(dialog).getByRole("button", { name: "Save activity" }),
  );
  expect(within(dialog).getByRole("button", { name: "Cancel" })).toBeDisabled();
  await user.keyboard("{Escape}");
  fireEvent.click(dialog, { clientX: -1, clientY: -1 });
  const form = dialog.querySelector("form");
  if (!form) throw new Error("Activity form is missing");
  fireEvent.submit(form);
  expect(dialog).toBeVisible();
  expect(api.writeActivity).toHaveBeenCalledTimes(1);
  expect(
    screen.queryByRole("dialog", { name: "Discard unsaved activity changes?" }),
  ).not.toBeInTheDocument();
  resolve(item());
  await waitFor(() => {
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
  expect(trigger).toHaveFocus();
});

test.each(["Escape", "backdrop"])(
  "dismiss discard confirmation with %s keeps the draft and its focus",
  async (via) => {
    const user = userEvent.setup();
    mount();
    await user.click(screen.getByRole("button", { name: "Schedule activity" }));
    const title = screen.getByLabelText("Title");
    await user.type(title, "Do not discard");
    await user.keyboard("{Escape}");
    const confirmation = screen.getByRole("dialog", {
      name: "Discard unsaved activity changes?",
    });
    expect(
      screen.getByRole("button", { name: "Continue editing" }),
    ).toHaveFocus();
    if (via === "Escape") await user.keyboard("{Escape}");
    else fireEvent.click(confirmation, { clientX: -1, clientY: -1 });
    expect(confirmation).not.toBeInTheDocument();
    expect(title).toHaveValue("Do not discard");
    expect(title).toHaveFocus();
    expect(api.writeActivity).not.toHaveBeenCalled();
  },
);
