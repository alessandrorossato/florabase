import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import { HierarchyRow } from "./HierarchyRow";

afterEach(cleanup);

test("hierarchy surface contains record and direct actions while expansion stays independent", async () => {
  const expand = vi.fn();
  const details = vi.fn();
  const edit = vi.fn();
  render(
    <>
      <button onClick={expand} aria-expanded={false}>
        Expand parent
      </button>
      <HierarchyRow>
        <button onClick={details}>Very long location · 20 records</button>
        <div>
          <button onClick={details}>Details</button>
          <button onClick={edit}>Edit</button>
        </div>
      </HierarchyRow>
    </>,
  );
  const user = userEvent.setup();
  const record = screen.getByRole("button", { name: /Very long location/ });
  expect(record.closest(".ui-hierarchy-row")).toContainElement(
    screen.getByRole("button", { name: "Edit" }),
  );
  expect(record.closest(".ui-hierarchy-row")).not.toContainElement(
    screen.getByRole("button", { name: "Expand parent" }),
  );
  await user.click(screen.getByRole("button", { name: "Expand parent" }));
  expect(expand).toHaveBeenCalledTimes(1);
  expect(details).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Edit" }));
  expect(edit).toHaveBeenCalledTimes(1);
  expect(details).not.toHaveBeenCalled();
  record.focus();
  await user.keyboard("{Enter}");
  await user.keyboard(" ");
  expect(details).toHaveBeenCalledTimes(2);
});
