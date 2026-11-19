import { useState } from "react";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "../auth/context";
import { acquireTestAuth } from "../test/auth";
import * as eventsApi from "./api";
import type { EventCreate, EventResponse, EventUpdate } from "./api";
import { EventJournal } from "./EventJournal";
import { OccurrenceDateChoice, type DateChoice } from "./OccurrenceDateChoice";
import { invalidDateControls } from "../seed-lots/dateControls";
import type { PartialDate } from "../seed-lots/api";

let auth: AuthContextValue;
beforeEach(async () => {
  auth = (await acquireTestAuth({ csrfToken: "csrf" })).auth;
});

function storedEvent(
  id: string,
  occurred_on: PartialDate | null,
  notes = `Entry ${id}`,
): EventResponse {
  return {
    id,
    kind: "observation",
    occurred_on,
    created_at: "2026-10-07T12:00:00Z",
    updated_at: "2026-10-07T12:00:00Z",
    notes,
    target: {
      id: "plant-1",
      type: "plant",
      label: "Specimen #1",
      lifecycle: "active",
      botanical_identity: { id: "id-1", display_label: "Monstera deliciosa" },
    },
    destination_location_id: null,
    destination_location: null,
    recipient: null,
    resulting_plant_id: null,
    resulting_plant: null,
    measurement_corrections: [],
    harvest_id: null,
    harvest_title: null,
  };
}

const zone = process.env.TZ;
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.useRealTimers();
  // Assigning undefined would store the string "undefined".
  if (zone === undefined) delete process.env.TZ;
  else process.env.TZ = zone;
});

function Example({
  initial = null,
  initialChoice,
  unknownUnavailable,
  changes,
}: {
  initial?: PartialDate | null;
  initialChoice?: DateChoice;
  unknownUnavailable?: string;
  changes: (PartialDate | null)[];
}) {
  const [value, setValue] = useState(initial);
  return (
    <form aria-label="Entry">
      <OccurrenceDateChoice
        id="when"
        value={value}
        initialChoice={initialChoice}
        unknownUnavailable={unknownUnavailable}
        disabled={false}
        onChange={(next) => {
          changes.push(next);
          setValue(next);
        }}
      />
    </form>
  );
}
const form = () => screen.getByRole<HTMLFormElement>("form", { name: "Entry" });

test.each([
  // 23:30 on 12 November in New York is already 13 November in UTC.
  ["America/New_York", "2026-11-13T04:30:00Z", 12],
  // 00:30 on 13 November in Auckland is still 12 November in UTC.
  ["Pacific/Auckland", "2026-11-12T11:30:00Z", 13],
  ["UTC", "2026-11-12T12:00:00Z", 12],
])(
  "Today is preselected by default (D1) and records the device-local day in %s",
  async (timeZone, instant, day) => {
    process.env.TZ = timeZone;
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(instant));
    const user = userEvent.setup();
    const changes: (PartialDate | null)[] = [];
    render(<Example changes={changes} />);
    const label = `Today, 2026-11-${String(day)}`;
    expect(screen.getByRole("radio", { name: label })).toBeChecked();
    expect(changes).toEqual([{ precision: "day", year: 2026, month: 11, day }]);
    expect(invalidDateControls(form())).toEqual([]);
    await user.click(screen.getByRole("radio", { name: "Date unknown" }));
    expect(changes.at(-1)).toBeNull();
    await user.click(screen.getByRole("radio", { name: label }));
    expect(changes.at(-1)).toEqual({
      precision: "day",
      year: 2026,
      month: 11,
      day,
    });
  },
);

test("when initialChoice is unset, nothing is preselected and an unanswered choice is invalid", async () => {
  const user = userEvent.setup();
  const changes: (PartialDate | null)[] = [];
  render(<Example initialChoice="unset" changes={changes} />);
  for (const radio of screen.getAllByRole("radio"))
    expect(radio).not.toBeChecked();
  expect(screen.getByRole("group", { name: /When did it happen/ })).toBe(
    screen.getAllByRole("radio")[0].closest("fieldset"),
  );
  expect(invalidDateControls(form()).map((c) => c.validationMessage)).toEqual([
    "Choose when this happened: Today, Another date or Date unknown.",
  ]);
  // Arrow keys move within the native radio group.
  screen.getAllByRole("radio")[0].focus();
  await user.keyboard("{ArrowDown}");
  expect(screen.getByRole("radio", { name: "Another date" })).toBeChecked();
  expect(changes).toEqual([null]);
});

test("Another date starts empty and stays invalid until complete", async () => {
  const user = userEvent.setup();
  const changes: (PartialDate | null)[] = [];
  render(<Example changes={changes} />);
  await user.click(screen.getByRole("radio", { name: "Another date" }));
  expect(changes.at(-1)).toBeNull();
  expect(screen.getByLabelText("Precision")).toHaveValue("day");
  for (const part of ["Year", "Month", "Day"])
    expect(screen.getByLabelText(part)).toHaveValue(null);
  expect(screen.queryByRole("option", { name: "Unknown" })).toBeNull();
  await user.type(screen.getByLabelText("Year"), "2025");
  await user.type(screen.getByLabelText("Month"), "4");
  expect(invalidDateControls(form())[0]).toBe(screen.getByLabelText("Day"));
  expect(changes.slice(1).every((value) => value === null)).toBe(true);
  await user.selectOptions(screen.getByLabelText("Precision"), "month");
  expect(changes.at(-1)).toEqual({ precision: "month", year: 2025, month: 4 });
  expect(invalidDateControls(form())).toEqual([]);
});

test("Date unknown records null; it is unavailable with a reason where a date is required", async () => {
  const user = userEvent.setup();
  const changes: (PartialDate | null)[] = [];
  const { unmount } = render(<Example changes={changes} />);
  await user.click(screen.getByRole("radio", { name: "Date unknown" }));
  expect(changes.at(-1)).toBeNull();
  expect(invalidDateControls(form())).toEqual([]);
  unmount();

  changes.length = 0;
  render(
    <Example
      changes={changes}
      unknownUnavailable="A height needs a date."
      initialChoice="unknown"
    />,
  );
  const unknown = screen.getByRole("radio", { name: "Date unknown" });
  expect(unknown).toBeDisabled();
  expect(unknown).not.toBeChecked();
  expect(unknown).toHaveAccessibleDescription("A height needs a date.");
  expect(invalidDateControls(form())[0].validationMessage).toBe(
    "Choose when this happened: Today or Another date.",
  );
  // Any precision satisfies a required date.
  await user.click(screen.getByRole("radio", { name: "Another date" }));
  await user.selectOptions(screen.getByLabelText("Precision"), "year");
  await user.type(screen.getByLabelText("Year"), "2023");
  expect(changes.at(-1)).toEqual({ precision: "year", year: 2023 });
  expect(invalidDateControls(form())).toEqual([]);
});

test.each([
  [{ precision: "day", year: 2019, month: 2, day: 28 }, ["2019", "2", "28"]],
  [{ precision: "month", year: 2019, month: 7, day: null }, ["2019", "7"]],
  [{ precision: "year", year: 1999, month: null, day: null }, ["1999"]],
] as const)("stored %j opens as Another date, unchanged", (stored, shown) => {
  const changes: (PartialDate | null)[] = [];
  render(<Example initial={stored} changes={changes} />);
  expect(screen.getByRole("radio", { name: "Another date" })).toBeChecked();
  expect(screen.getByLabelText("Precision")).toHaveValue(stored.precision);
  expect(
    screen
      .getAllByRole("spinbutton")
      .map((input) => (input as HTMLInputElement).value),
  ).toEqual(shown);
  expect(changes).toEqual([]);
  expect(invalidDateControls(form())).toEqual([]);
});

test("a stored unknown date opens as Date unknown when editing", () => {
  const changes: (PartialDate | null)[] = [];
  render(<Example initialChoice="unknown" changes={changes} />);
  expect(screen.getByRole("radio", { name: "Date unknown" })).toBeChecked();
  expect(changes).toEqual([]);
});

test("initialChoice Today (D1 option b) records the local day once", () => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(2026, 10, 12, 9));
  const changes: (PartialDate | null)[] = [];
  render(<Example initialChoice="today" changes={changes} />);
  expect(
    screen.getByRole("radio", { name: "Today, 2026-11-12" }),
  ).toBeChecked();
  expect(changes).toEqual([
    { precision: "day", year: 2026, month: 11, day: 12 },
  ]);
});

test("EventJournal preselects Today for new entries and saves Today, Another date and Date unknown as chosen", async () => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(2026, 10, 16, 10));
  const created: EventCreate[] = [];
  let entries: EventResponse[] = [];
  vi.spyOn(eventsApi, "listEvents").mockImplementation(() =>
    Promise.resolve(entries),
  );
  vi.spyOn(eventsApi, "createEvent").mockImplementation(
    (_kind, _id, payload) => {
      created.push(payload);
      const item = storedEvent(
        `created-${String(created.length)}`,
        payload.occurred_on ?? null,
        payload.notes ?? "",
      );
      entries = [item, ...entries];
      return Promise.resolve(item);
    },
  );
  const user = userEvent.setup();
  render(
    <AuthContext.Provider value={auth}>
      <EventJournal
        targetKind="plant"
        targetId="plant-1"
        targetLabel="Specimen #1"
        locations={[]}
        onTargetRefresh={() => Promise.resolve()}
      />
    </AuthContext.Provider>,
  );

  // (1) New entry opens with Today selected and saves without another date action.
  await user.click(await screen.findByRole("button", { name: "Add entry" }));
  expect(
    screen.getByRole("radio", { name: "Today, 2026-11-16" }),
  ).toBeChecked();
  await user.type(screen.getByLabelText("Notes"), "Saved with Today");
  await user.click(
    within(screen.getByRole("dialog")).getByRole("button", {
      name: "Add entry",
    }),
  );
  expect(created[0]).toMatchObject({
    kind: "observation",
    occurred_on: { precision: "day", year: 2026, month: 11, day: 16 },
    notes: "Saved with Today",
  });

  // (2a) Another date can be chosen explicitly and saved as chosen.
  await user.click(await screen.findByRole("button", { name: "Add entry" }));
  await user.click(screen.getByRole("radio", { name: "Another date" }));
  await user.selectOptions(screen.getByLabelText("Precision"), "month");
  await user.type(screen.getByLabelText("Year"), "2024");
  await user.type(screen.getByLabelText("Month"), "5");
  await user.type(screen.getByLabelText("Notes"), "Saved with Another date");
  await user.click(
    within(screen.getByRole("dialog")).getByRole("button", {
      name: "Add entry",
    }),
  );
  expect(created[1]).toMatchObject({
    kind: "observation",
    occurred_on: { precision: "month", year: 2024, month: 5 },
    notes: "Saved with Another date",
  });

  // (2b) Date unknown can be chosen explicitly and saved as chosen.
  await user.click(await screen.findByRole("button", { name: "Add entry" }));
  await user.click(screen.getByRole("radio", { name: "Date unknown" }));
  await user.type(screen.getByLabelText("Notes"), "Saved with Date unknown");
  await user.click(
    within(screen.getByRole("dialog")).getByRole("button", {
      name: "Add entry",
    }),
  );
  expect(created[2]).toMatchObject({
    kind: "observation",
    occurred_on: null,
    notes: "Saved with Date unknown",
  });
});

test("EventJournal preserves stored full, year-month, year-only and unknown dates on untouched save", async () => {
  const cases: {
    id: string;
    stored: PartialDate | null;
    shown: string[];
  }[] = [
    {
      id: "full",
      stored: { precision: "day", year: 2021, month: 8, day: 19 },
      shown: ["2021", "8", "19"],
    },
    {
      id: "month",
      stored: { precision: "month", year: 2020, month: 4 },
      shown: ["2020", "4"],
    },
    {
      id: "year",
      stored: { precision: "year", year: 2018 },
      shown: ["2018"],
    },
    {
      id: "unknown",
      stored: null,
      shown: [],
    },
  ];
  const entries = cases.map((c) => storedEvent(c.id, c.stored, `Note ${c.id}`));
  const updates: { id: string; payload: EventUpdate }[] = [];
  vi.spyOn(eventsApi, "listEvents").mockResolvedValue(entries);
  vi.spyOn(eventsApi, "updateEvent").mockImplementation((id, payload) => {
    updates.push({ id, payload });
    const existing = entries.find((e) => e.id === id) ?? entries[0];
    return Promise.resolve({
      ...existing,
      occurred_on: payload.occurred_on ?? null,
      notes: payload.notes ?? null,
    });
  });

  const user = userEvent.setup();
  render(
    <AuthContext.Provider value={auth}>
      <EventJournal
        targetKind="plant"
        targetId="plant-1"
        targetLabel="Specimen #1"
        locations={[]}
        onTargetRefresh={() => Promise.resolve()}
      />
    </AuthContext.Provider>,
  );

  for (const item of cases) {
    const card = (await screen.findByText(`Note ${item.id}`)).closest(
      "article",
    );
    if (!card) throw new Error(`Missing card ${item.id}`);
    await user.click(within(card).getByRole("button", { name: "Edit" }));
    const dialog = screen.getByRole("dialog", { name: "Edit entry" });
    if (item.stored) {
      expect(
        within(dialog).getByRole("radio", { name: "Another date" }),
      ).toBeChecked();
      expect(within(dialog).getByLabelText("Precision")).toHaveValue(
        item.stored.precision,
      );
      expect(
        within(dialog)
          .getAllByRole("spinbutton")
          .map((input) => (input as HTMLInputElement).value),
      ).toEqual(item.shown);
    } else {
      expect(
        within(dialog).getByRole("radio", { name: "Date unknown" }),
      ).toBeChecked();
    }
    await user.clear(within(dialog).getByLabelText("Notes"));
    await user.type(
      within(dialog).getByLabelText("Notes"),
      `Updated ${item.id}`,
    );
    await user.click(
      within(dialog).getByRole("button", { name: "Save changes" }),
    );
    expect(updates.at(-1)?.id).toBe(item.id);
    expect(updates.at(-1)?.payload).toMatchObject({
      occurred_on: item.stored,
      notes: `Updated ${item.id}`,
    });
  }
});

test("EventJournal keeps stored and drafted dates stable across kind switches, cancel/restore, record navigation, and height validation", async () => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(2026, 10, 16, 10));
  const firstEvents = [
    storedEvent(
      "e-1",
      { precision: "month", year: 2022, month: 9 },
      "Sept note",
    ),
  ];
  const secondEvents = [storedEvent("e-2", null, "Undated second")];
  const created: EventCreate[] = [];
  vi.spyOn(eventsApi, "listEvents").mockImplementation((_kind, id) =>
    Promise.resolve(id === "plant-1" ? firstEvents : secondEvents),
  );
  vi.spyOn(eventsApi, "createEvent").mockImplementation(
    (_kind, _id, payload) => {
      created.push(payload);
      return Promise.resolve(
        storedEvent(
          "created",
          payload.occurred_on ?? null,
          payload.notes ?? "",
        ),
      );
    },
  );

  const user = userEvent.setup();
  const { rerender } = render(
    <AuthContext.Provider value={auth}>
      <EventJournal
        key="plant:plant-1"
        targetKind="plant"
        targetId="plant-1"
        targetLabel="Specimen #1"
        locations={[]}
        onTargetRefresh={() => Promise.resolve()}
      />
    </AuthContext.Provider>,
  );

  // Pristine new entry (Today preselected) closes on Cancel without a discard prompt.
  await user.click(await screen.findByRole("button", { name: "Add entry" }));
  expect(
    screen.getByRole("radio", { name: "Today, 2026-11-16" }),
  ).toBeChecked();
  await user.click(screen.getByRole("button", { name: "Cancel" }));
  expect(
    screen.queryByRole("dialog", { name: "Discard unsaved Journal changes?" }),
  ).not.toBeInTheDocument();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

  // Drafted date survives kind switches and cancel -> Continue editing restoration; Height requires a date.
  await user.click(screen.getByRole("button", { name: "Add entry" }));
  await user.click(screen.getByRole("radio", { name: "Another date" }));
  await user.selectOptions(screen.getByLabelText("Precision"), "year");
  await user.type(screen.getByLabelText("Year"), "2023");
  await user.selectOptions(screen.getByLabelText("Entry type"), "pruning");
  expect(screen.getByRole("radio", { name: "Another date" })).toBeChecked();
  expect(screen.getByLabelText("Precision")).toHaveValue("year");
  expect(screen.getByLabelText("Year")).toHaveValue(2023);

  // Cancel -> Continue editing restores the drafted date intact.
  await user.click(screen.getByRole("button", { name: "Cancel" }));
  const discard = screen.getByRole("dialog", {
    name: "Discard unsaved Journal changes?",
  });
  await user.click(
    within(discard).getByRole("button", { name: "Continue editing" }),
  );
  expect(screen.getByRole("radio", { name: "Another date" })).toBeChecked();
  expect(screen.getByLabelText("Precision")).toHaveValue("year");
  expect(screen.getByLabelText("Year")).toHaveValue(2023);

  // Switching to Date unknown then to Measurement disables Date unknown and blocks saving until dated.
  await user.click(screen.getByRole("radio", { name: "Date unknown" }));
  await user.selectOptions(screen.getByLabelText("Entry type"), "measurement");
  const unknownRadio = screen.getByRole("radio", { name: "Date unknown" });
  expect(unknownRadio).toBeDisabled();
  expect(unknownRadio).not.toBeChecked();
  await user.type(screen.getByLabelText(/^Value/), "18.5");
  await user.click(
    within(screen.getByRole("dialog")).getByRole("button", {
      name: "Add entry",
    }),
  );
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Choose when this happened: Today or Another date.",
  );
  expect(created).toHaveLength(0);

  // Navigating between records resets the composer and does not leak the previous draft.
  rerender(
    <AuthContext.Provider value={auth}>
      <EventJournal
        key="plant:plant-2"
        targetKind="plant"
        targetId="plant-2"
        targetLabel="Specimen #2"
        locations={[]}
        onTargetRefresh={() => Promise.resolve()}
      />
    </AuthContext.Provider>,
  );
  await screen.findByText("Undated second");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Edit" }));
  expect(screen.getByRole("radio", { name: "Date unknown" })).toBeChecked();
  await user.selectOptions(screen.getByLabelText("Entry type"), "repotting");
  expect(screen.getByRole("radio", { name: "Date unknown" })).toBeChecked();
});
