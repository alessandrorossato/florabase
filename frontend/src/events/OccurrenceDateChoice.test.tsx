import { useState } from "react";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import { OccurrenceDateChoice, type DateChoice } from "./OccurrenceDateChoice";
import { invalidDateControls } from "../seed-lots/dateControls";
import type { PartialDate } from "../seed-lots/api";

const zone = process.env.TZ;
afterEach(() => {
  cleanup();
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
  "Today records the device-local day in %s",
  async (timeZone, instant, day) => {
    process.env.TZ = timeZone;
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(instant));
    const user = userEvent.setup();
    const changes: (PartialDate | null)[] = [];
    render(<Example changes={changes} />);
    const label = `Today, 2026-11-${String(day)}`;
    await user.click(screen.getByRole("radio", { name: label }));
    expect(changes).toEqual([{ precision: "day", year: 2026, month: 11, day }]);
    expect(invalidDateControls(form())).toEqual([]);
  },
);

test("nothing is preselected and an unanswered choice is invalid", async () => {
  const user = userEvent.setup();
  const changes: (PartialDate | null)[] = [];
  render(<Example changes={changes} />);
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
  expect(screen.getByLabelText("Precision")).toHaveValue("day");
  for (const part of ["Year", "Month", "Day"])
    expect(screen.getByLabelText(part)).toHaveValue(null);
  expect(screen.queryByRole("option", { name: "Unknown" })).toBeNull();
  await user.type(screen.getByLabelText("Year"), "2025");
  await user.type(screen.getByLabelText("Month"), "4");
  expect(invalidDateControls(form())[0]).toBe(screen.getByLabelText("Day"));
  expect(changes.every((value) => value === null)).toBe(true);
  await user.selectOptions(screen.getByLabelText("Precision"), "month");
  expect(changes.at(-1)).toEqual({ precision: "month", year: 2025, month: 4 });
  expect(invalidDateControls(form())).toEqual([]);
});

test("Date unknown records null; it is unavailable with a reason where a date is required", async () => {
  const user = userEvent.setup();
  const changes: (PartialDate | null)[] = [];
  const { unmount } = render(<Example changes={changes} />);
  await user.click(screen.getByRole("radio", { name: "Date unknown" }));
  expect(changes).toEqual([null]);
  expect(invalidDateControls(form())).toEqual([]);
  unmount();

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
