import { useState } from "react";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test } from "vitest";
import { PartialDateField } from "./PartialDateField";
import type { PartialDate } from "./api";
afterEach(cleanup);
function Example() {
  const [value, setValue] = useState<PartialDate | null>(null);
  return (
    <>
      <PartialDateField
        id="date"
        label="Acquired"
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
test("precision keeps only known components, preserves parts and leaves adjacent fields intact", async () => {
  const user = userEvent.setup();
  render(<Example />);
  const group = screen.getByRole("group", { name: "Acquired" });
  const precision = within(group).getByLabelText("Precision");
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
});
