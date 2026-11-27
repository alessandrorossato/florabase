import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { createPortal } from "react-dom";
import { afterEach, expect, test, vi } from "vitest";
import { TaskDialog } from "./TaskDialog";

afterEach(cleanup);

function Nested({ outer, inner }: { outer: () => void; inner: () => void }) {
  const [open, setOpen] = useState(true);
  return (
    <TaskDialog title="Outer" onClose={outer}>
      <p>Outer draft</p>
      {open &&
        createPortal(
          <TaskDialog
            title="Inner"
            onClose={() => {
              inner();
              setOpen(false);
            }}
          >
            <button type="button">Inner action</button>
          </TaskDialog>,
          document.body,
        )}
    </TaskDialog>
  );
}

test("a nested dialog's cancel (Android back) closes only that dialog", () => {
  const outer = vi.fn();
  const inner = vi.fn();
  render(<Nested outer={outer} inner={inner} />);
  fireEvent(
    screen.getByRole("dialog", { name: "Inner" }),
    new Event("cancel", { cancelable: true }),
  );
  expect(inner).toHaveBeenCalledTimes(1);
  expect(outer).not.toHaveBeenCalled();
  expect(screen.getByRole("dialog", { name: "Outer" })).toBeInTheDocument();
});

test("Escape in a nested dialog closes only that dialog", () => {
  const outer = vi.fn();
  const inner = vi.fn();
  render(<Nested outer={outer} inner={inner} />);
  fireEvent.keyDown(screen.getByRole("button", { name: "Inner action" }), {
    key: "Escape",
  });
  expect(inner).toHaveBeenCalledTimes(1);
  expect(outer).not.toHaveBeenCalled();
});
