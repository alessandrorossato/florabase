import { useState } from "react";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test } from "vitest";
import { PartialDateField } from "./PartialDateField";
import type { PartialDate } from "./api";
afterEach(cleanup);
function Example({
  hidePrecisionLabel = false,
}: {
  hidePrecisionLabel?: boolean;
}) {
  const [value, setValue] = useState<PartialDate | null>(null);
  return (
    <>
      <PartialDateField
        id="date"
        label="Acquired"
        hidePrecisionLabel={hidePrecisionLabel}
        value={value}
        onChange={setValue}
        disabled={false}
      />
      <output aria-label="Recorded date">{JSON.stringify(value)}</output>
      <label>
        Adjacent supplier
        <input defaultValue="Retained Supplier" />
      </label>
    </>
  );
}
test.each([false, true])(
  "precision keeps known components and adjacent values with hidden caption %s",
  async (hidePrecisionLabel) => {
    const user = userEvent.setup();
    render(<Example hidePrecisionLabel={hidePrecisionLabel} />);
    const group = screen.getByRole("group", { name: "Acquired" });
    const precision = within(group).getByLabelText<HTMLSelectElement>(
      hidePrecisionLabel ? "Acquired precision" : "Precision",
    );
    expect(precision.labels[0].classList.contains("sr-only")).toBe(
      hidePrecisionLabel,
    );
    expect(screen.getByLabelText("Recorded date")).toHaveTextContent("null");
    expect(precision).not.toBeRequired();
    await user.selectOptions(precision, "day");
    for (const part of ["Year", "Month", "Day"])
      expect(screen.getByLabelText(part)).toBeRequired();
    await user.clear(screen.getByLabelText("Year"));
    await user.type(screen.getByLabelText("Year"), "2024");
    await user.clear(screen.getByLabelText("Month"));
    await user.type(screen.getByLabelText("Month"), "9");
    await user.selectOptions(precision, "month");
    expect(screen.queryByLabelText("Day")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Recorded date")).toHaveTextContent(
      '{"precision":"month","year":2024,"month":9}',
    );
    await user.selectOptions(precision, "year");
    expect(screen.queryByLabelText("Month")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Year")).toHaveValue(2024);
    await user.selectOptions(precision, "");
    expect(screen.getByLabelText("Recorded date")).toHaveTextContent("null");
    expect(screen.queryByLabelText("Year")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Adjacent supplier")).toHaveValue(
      "Retained Supplier",
    );
  },
);

function Spied({
  initial,
  onChange,
}: {
  initial: PartialDate | null;
  onChange: (value: PartialDate | null) => void;
}) {
  const [value, setValue] = useState(initial);
  return (
    <form aria-label="Date form">
      <PartialDateField
        id="when"
        label="Acquired"
        value={value}
        onChange={(next) => {
          onChange(next);
          setValue(next);
        }}
        disabled={false}
      />
    </form>
  );
}
const isValidPayload = (value: PartialDate | null) =>
  value === null ||
  (value.precision === "year"
    ? value.month === undefined && value.day === undefined
    : value.precision === "month"
      ? Number.isInteger(value.month) && value.day === undefined
      : Number.isInteger(value.month) && Number.isInteger(value.day));

test("no part is invented: precision changes keep typed parts, drop unneeded ones and leave new ones empty", async () => {
  const user = userEvent.setup();
  const changes: (PartialDate | null)[] = [];
  render(<Spied initial={null} onChange={(value) => changes.push(value)} />);
  const precision = screen.getByLabelText("Precision");
  await user.selectOptions(precision, "month");
  expect(screen.getByLabelText("Year")).toHaveValue(null);
  expect(screen.getByLabelText("Month")).toHaveValue(null);
  expect(screen.getByLabelText("Year")).toBeInvalid();
  await user.type(screen.getByLabelText("Year"), "2024");
  // Year typed, month still empty: incomplete, never a payload.
  expect(changes).toEqual([]);
  expect(screen.getByLabelText("Month")).toBeInvalid();
  expect(screen.getByLabelText("Month")).toHaveAccessibleDescription(
    /Enter a valid month/,
  );
  await user.type(screen.getByLabelText("Month"), "9");
  expect(changes.at(-1)).toEqual({ precision: "month", year: 2024, month: 9 });

  // Up: the new day stays empty and the value becomes incomplete again.
  await user.selectOptions(precision, "day");
  expect(screen.getByLabelText("Day")).toHaveValue(null);
  expect(screen.getByLabelText("Month")).toHaveValue(9);
  expect(changes.at(-1)).toBeNull();
  await user.type(screen.getByLabelText("Day"), "31");
  // 31 September does not exist.
  expect(changes.at(-1)).toBeNull();
  expect(screen.getByLabelText("Day")).toBeInvalid();
  await user.clear(screen.getByLabelText("Day"));
  await user.type(screen.getByLabelText("Day"), "30");
  expect(changes.at(-1)).toEqual({
    precision: "day",
    year: 2024,
    month: 9,
    day: 30,
  });

  // Down: day and then month are dropped, never displayed again.
  await user.selectOptions(precision, "month");
  expect(changes.at(-1)).toEqual({ precision: "month", year: 2024, month: 9 });
  expect(screen.queryByLabelText("Day")).not.toBeInTheDocument();
  await user.selectOptions(precision, "year");
  expect(changes.at(-1)).toEqual({ precision: "year", year: 2024 });
  await user.selectOptions(precision, "day");
  expect(screen.getByLabelText("Month")).toHaveValue(null);
  expect(screen.getByLabelText("Day")).toHaveValue(null);
  expect(changes.at(-1)).toBeNull();
  expect(changes.every(isValidPayload)).toBe(true);
});

test("year precision alone emits only a year", async () => {
  const user = userEvent.setup();
  const changes: (PartialDate | null)[] = [];
  render(<Spied initial={null} onChange={(value) => changes.push(value)} />);
  await user.selectOptions(screen.getByLabelText("Precision"), "year");
  expect(screen.queryByLabelText("Month")).not.toBeInTheDocument();
  await user.type(screen.getByLabelText("Year"), "1987");
  expect(changes.at(-1)).toEqual({ precision: "year", year: 1987 });
  expect(changes.every(isValidPayload)).toBe(true);
});

test.each([
  [{ precision: "day", year: 2019, month: 2, day: 28 }, ["2019", "2", "28"]],
  [{ precision: "month", year: 2019, month: 7, day: null }, ["2019", "7"]],
  [{ precision: "year", year: 1999, month: null, day: null }, ["1999"]],
  [null, []],
] as const)(
  "stored %j opens unchanged without rewriting it",
  (stored, shown) => {
    const changes: (PartialDate | null)[] = [];
    render(
      <Spied initial={stored} onChange={(value) => changes.push(value)} />,
    );
    expect(screen.getByLabelText("Precision")).toHaveValue(
      stored?.precision ?? "",
    );
    const inputs = screen.queryAllByRole("spinbutton");
    expect(inputs.map((input) => (input as HTMLInputElement).value)).toEqual(
      shown,
    );
    for (const input of inputs) expect(input).toBeValid();
    expect(changes).toEqual([]);
  },
);

test("an incomplete draft blocks native submission; noValidate forms find it", async () => {
  const user = userEvent.setup();
  const { invalidDateControls } = await import("./dateControls");
  render(<Spied initial={null} onChange={() => undefined} />);
  const form = screen.getByRole("form", { name: "Date form" });
  expect(form).toBeValid();
  expect(invalidDateControls(form as HTMLFormElement)).toEqual([]);
  await user.selectOptions(screen.getByLabelText("Precision"), "day");
  await user.type(screen.getByLabelText("Year"), "2024");
  expect(form).toBeInvalid();
  const [control] = invalidDateControls(form as HTMLFormElement);
  expect(control).toBe(screen.getByLabelText("Month"));
  expect(control.validationMessage).toBe(
    "Acquired is incomplete: enter a valid month (1–12), or change its precision.",
  );
  await user.selectOptions(screen.getByLabelText("Precision"), "");
  expect(form).toBeValid();
});
