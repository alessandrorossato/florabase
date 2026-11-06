import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, expect, test } from "vitest";

import { TaskDialog } from "./TaskDialog";

afterEach(() => {
  cleanup();
});

/** Closes its dialog from a resolved promise, like a save completing. */
function AsyncCloseHarness({ done }: { done: Promise<void> }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        type="button"
        onClick={() => {
          setOpen(true);
          void done.then(() => {
            setOpen(false);
          });
        }}
      >
        Open task
      </button>
      {open && (
        <TaskDialog title="Task" onClose={() => undefined}>
          <button type="button">Inside</button>
        </TaskDialog>
      )}
    </>
  );
}

test("focus is back on the invoking control when an asynchronous update removes the dialog", async () => {
  const user = userEvent.setup();
  let finish: () => void = () => undefined;
  const done = new Promise<void>((resolve) => {
    finish = resolve;
  });
  render(<AsyncCloseHarness done={done} />);
  const trigger = screen.getByRole("button", { name: "Open task" });
  await user.click(trigger);
  expect(screen.getByRole("button", { name: "Inside" })).toHaveFocus();

  // Record where focus is at the moment the dialog leaves the document, before any
  // later scheduler work: there must be no gap where focus sits on <body>.
  let focusAtRemoval: Element | null | undefined;
  const observer = new MutationObserver(() => {
    if (focusAtRemoval === undefined && !screen.queryByRole("dialog"))
      focusAtRemoval = document.activeElement;
  });
  observer.observe(document.body, { childList: true, subtree: true });
  finish();
  await waitFor(() => {
    expect(focusAtRemoval).not.toBeUndefined();
  });
  observer.disconnect();
  expect(focusAtRemoval).toBe(trigger);
  expect(trigger).toHaveFocus();
});
