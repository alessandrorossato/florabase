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
  window.history.replaceState(null, "", "/#/schedule");
  vi.mocked(api.listSchedule).mockResolvedValue(page());
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
  expect(
    await screen.findByText("No activities match this view."),
  ).toBeVisible();
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
  expect(screen.getByText(/calendar day \(2026-01-02\)/)).toBeVisible();
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
