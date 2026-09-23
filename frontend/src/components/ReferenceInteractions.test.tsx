import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StrictMode, useState } from "react";
import { afterEach, expect, test, vi } from "vitest";

import { OverflowMenu } from "./ReferenceUI";
import { TaskDialog } from "./TaskDialog";

afterEach(() => {
  vi.restoreAllMocks();
  delete (HTMLDialogElement.prototype as Partial<HTMLDialogElement>).showModal;
  delete (HTMLDialogElement.prototype as Partial<HTMLDialogElement>).close;
});

function DialogHarness() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        type="button"
        onClick={() => {
          setOpen(true);
        }}
      >
        New record
      </button>
      {open && (
        <TaskDialog
          title="New record"
          onClose={() => {
            setOpen(false);
          }}
        >
          <label htmlFor="record-name">Name</label>
          <input id="record-name" />
          <button
            type="button"
            onClick={() => {
              setOpen(false);
            }}
          >
            Save
          </button>
          <button
            type="button"
            onClick={() => {
              setOpen(false);
            }}
          >
            Cancel
          </button>
        </TaskDialog>
      )}
    </>
  );
}

test("native dialog survives StrictMode close replay, traps focus, and restores its launcher", async () => {
  Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
    configurable: true,
    value(this: HTMLDialogElement) {
      this.setAttribute("open", "");
    },
  });
  Object.defineProperty(HTMLDialogElement.prototype, "close", {
    configurable: true,
    value(this: HTMLDialogElement) {
      this.removeAttribute("open");
      queueMicrotask(() => {
        this.dispatchEvent(new Event("close"));
      });
    },
  });
  const user = userEvent.setup();
  render(
    <StrictMode>
      <DialogHarness />
    </StrictMode>,
  );
  const launcher = screen.getByRole("button", { name: "New record" });

  await user.click(launcher);
  await waitFor(() => {
    expect(screen.getByRole("dialog", { name: "New record" })).toHaveAttribute(
      "open",
    );
  });
  expect(screen.getByLabelText("Name")).toHaveFocus();
  await user.keyboard("{Shift>}{Tab}{/Shift}");
  expect(screen.getByRole("button", { name: "Cancel" })).toHaveFocus();
  await user.keyboard("{Tab}");
  expect(screen.getByLabelText("Name")).toHaveFocus();
  fireEvent.pointerDown(document.body);
  expect(
    screen.getByRole("dialog", { name: "New record" }),
  ).toBeInTheDocument();
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(launcher).toHaveFocus();

  await user.click(launcher);
  expect(screen.getByLabelText("Name")).toHaveFocus();
  await user.click(screen.getByRole("button", { name: "Cancel" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(launcher).toHaveFocus();
  await user.click(launcher);
  await user.click(screen.getByRole("button", { name: "Save" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(launcher).toHaveFocus();
});

test("overflow menus dismiss outside and on action, Escape, or another menu", async () => {
  const user = userEvent.setup();
  const action = vi.fn();
  render(
    <>
      <OverflowMenu ariaLabel="First actions">
        <button type="button" onClick={action}>
          Retire
        </button>
      </OverflowMenu>
      <OverflowMenu ariaLabel="Second actions">
        <button type="button">Delete</button>
      </OverflowMenu>
      <button type="button">Outside</button>
    </>,
  );
  const first = screen.getByLabelText("First actions").closest("details");
  const second = screen.getByLabelText("Second actions").closest("details");
  expect(first).not.toBeNull();
  expect(second).not.toBeNull();
  await user.click(screen.getByLabelText("First actions"));
  expect(first).toHaveAttribute("open");
  fireEvent.pointerDown(screen.getByRole("button", { name: "Retire" }));
  expect(first).toHaveAttribute("open");
  await user.click(screen.getByRole("button", { name: "Retire" }));
  expect(action).toHaveBeenCalledOnce();
  expect(first).not.toHaveAttribute("open");
  expect(screen.getByLabelText("First actions")).toHaveFocus();
  await user.click(screen.getByLabelText("First actions"));
  fireEvent.pointerDown(screen.getByRole("button", { name: "Outside" }));
  expect(first).not.toHaveAttribute("open");
  await user.click(screen.getByLabelText("First actions"));
  await user.keyboard("{Escape}");
  expect(first).not.toHaveAttribute("open");
  expect(screen.getByLabelText("First actions")).toHaveFocus();
  await user.click(screen.getByLabelText("First actions"));
  await user.click(screen.getByLabelText("Second actions"));
  await waitFor(() => {
    expect(first).not.toHaveAttribute("open");
    expect(second).toHaveAttribute("open");
  });
});
