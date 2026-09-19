import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import { ContextHelpDialog, FieldHelp, InfoDisclosure } from "./ContextualHelp";
import { describedBy } from "./aria";

function DescribedField() {
  const [invalid, setInvalid] = useState(false);
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        setInvalid(true);
      }}
    >
      <label htmlFor="quantity">Quantity</label>
      <input
        aria-describedby={describedBy(
          "quantity-help",
          invalid && "quantity-error",
        )}
        aria-invalid={invalid || undefined}
        id="quantity"
      />
      <FieldHelp id="quantity-help">
        Leave the quantity unknown rather than guessing.
      </FieldHelp>
      {invalid && <p id="quantity-error">Enter a positive quantity.</p>}
      <button type="submit">Save</button>
    </form>
  );
}

describe("contextual help", () => {
  it("associates inline help and composes it with validation", async () => {
    const user = userEvent.setup();
    render(<DescribedField />);
    const input = screen.getByLabelText("Quantity");

    expect(input).toHaveAccessibleDescription(
      "Leave the quantity unknown rather than guessing.",
    );
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(input).toHaveAccessibleDescription(
      "Leave the quantity unknown rather than guessing. Enter a positive quantity.",
    );
  });

  it("opens expandable help from a named button and closes it with Escape", async () => {
    const user = userEvent.setup();
    render(
      <InfoDisclosure label="More information about quantity">
        <p>Exact means actually known.</p>
      </InfoDisclosure>,
    );
    const trigger = screen.getByRole("button", {
      name: "More information about quantity",
    });

    await user.tab();
    expect(trigger).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(
      screen.getByRole("region", {
        name: "More information about quantity",
      }),
    ).toBeVisible();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("region")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("manages focus and Escape for deep contextual help", async () => {
    const user = userEvent.setup();
    render(
      <ContextHelpDialog
        buttonLabel="Understand creation reversal"
        title="How creation reversal works"
      >
        <p>The result remains in history.</p>
        <button type="button">Read reversal policy</button>
      </ContextHelpDialog>,
    );
    const trigger = screen.getByRole("button", {
      name: "Understand creation reversal",
    });

    await user.click(trigger);
    const dialog = screen.getByRole("dialog", {
      name: "How creation reversal works",
    });
    expect(dialog).toBeVisible();
    expect(dialog).toHaveAttribute("aria-modal", "true");
    const close = screen.getByRole("button", { name: "Close" });
    const policy = screen.getByRole("button", { name: "Read reversal policy" });
    expect(close).toHaveFocus();
    await user.keyboard("{Tab}");
    expect(policy).toHaveFocus();
    await user.keyboard("{Shift>}{Tab}{/Shift}");
    expect(close).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });
});
