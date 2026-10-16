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
  const first = screen.getByRole("button", { name: "First actions" });
  const second = screen.getByRole("button", { name: "Second actions" });
  await user.click(first);
  expect(first).toHaveAttribute("aria-expanded", "true");
  const menu = screen.getByRole("group", { name: "First actions menu" });
  expect(menu.parentElement).toBe(document.body);
  fireEvent.pointerDown(screen.getByRole("button", { name: "Retire" }));
  expect(first).toHaveAttribute("aria-expanded", "true");
  await user.click(screen.getByRole("button", { name: "Retire" }));
  expect(action).toHaveBeenCalledOnce();
  expect(first).toHaveAttribute("aria-expanded", "false");
  expect(first).toHaveFocus();
  await user.click(first);
  fireEvent.pointerDown(screen.getByRole("button", { name: "Outside" }));
  expect(first).toHaveAttribute("aria-expanded", "false");
  await user.click(first);
  await user.keyboard("{Escape}");
  expect(first).toHaveAttribute("aria-expanded", "false");
  expect(first).toHaveFocus();
  await user.keyboard("{ArrowDown}");
  await waitFor(() => {
    expect(screen.getByRole("button", { name: "Retire" })).toHaveFocus();
  });
  await user.click(second);
  expect(first).toHaveAttribute("aria-expanded", "false");
  expect(second).toHaveAttribute("aria-expanded", "true");
});

test("navigation dialogs include links in focus containment", async () => {
  const user = userEvent.setup();
  render(
    <TaskDialog title="Navigation" onClose={vi.fn()}>
      <button type="button">Close navigation</button>
      <a href="#/labels">Labels</a>
    </TaskDialog>,
  );
  expect(
    screen.getByRole("button", { name: "Close navigation" }),
  ).toHaveFocus();
  await user.keyboard("{Shift>}{Tab}{/Shift}");
  expect(screen.getByRole("link", { name: "Labels" })).toHaveFocus();
  await user.keyboard("{Tab}");
  expect(
    screen.getByRole("button", { name: "Close navigation" }),
  ).toHaveFocus();
});

test("dialog focus skips inactive panels, disabled fieldsets, inert content and negative tab stops", async () => {
  const user = userEvent.setup();
  render(
    <TaskDialog title="Grouped editor" onClose={() => undefined}>
      <div hidden>
        <input aria-label="Inactive field" />
      </div>
      <fieldset disabled>
        <input aria-label="Disabled field" />
      </fieldset>
      <div inert>
        <button type="button">Inert action</button>
      </div>
      <input aria-label="Programmatic field" tabIndex={-1} />
      <input aria-label="Visible field" />
      <button type="button">Save visible panel</button>
      <div hidden>
        <button type="button">Hidden final action</button>
      </div>
    </TaskDialog>,
  );
  expect(screen.getByLabelText("Visible field")).toHaveFocus();
  await user.keyboard("{Shift>}{Tab}{/Shift}");
  expect(
    screen.getByRole("button", { name: "Save visible panel" }),
  ).toHaveFocus();
  await user.keyboard("{Tab}");
  expect(screen.getByLabelText("Visible field")).toHaveFocus();
});
