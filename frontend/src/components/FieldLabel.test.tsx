import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";
import { FieldLabel } from "./FieldLabel";
afterEach(cleanup);

test("required captions retain their control name and expose requirement independently of the visual mark", () => {
  render(
    <form>
      <FieldLabel htmlFor="name" required>
        Name
      </FieldLabel>
      <input id="name" required />
      <FieldLabel htmlFor="notes">Notes</FieldLabel>
      <textarea id="notes" />
    </form>,
  );
  expect(screen.getByRole("textbox", { name: "Name" })).toBeRequired();
  expect(screen.getByLabelText("Name")).toHaveAccessibleName("Name");
  expect(screen.getByLabelText("Notes")).not.toBeRequired();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  expect(
    screen.getByText("Name").querySelector(".required-mark"),
  ).toHaveAttribute("aria-hidden", "true");
  expect(screen.getByText("Notes").querySelector(".required-mark")).toBeNull();
});

test("wrapped captions follow conditional native requirement without changing the accessible name", () => {
  const view = (required: boolean) => (
    <label>
      <FieldLabel as="span" required={required}>
        Attribution
      </FieldLabel>
      <textarea required={required} />
    </label>
  );
  const { rerender } = render(view(false));
  expect(screen.getByLabelText("Attribution")).not.toBeRequired();
  rerender(view(true));
  expect(screen.getByLabelText("Attribution")).toBeRequired();
  expect(screen.getByRole("textbox", { name: "Attribution" })).toBeVisible();
});
