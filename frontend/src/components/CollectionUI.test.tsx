import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import { DetailHeader } from "./CollectionUI";
import { OverflowMenu } from "./ReferenceUI";

afterEach(cleanup);

test("Details groups the primary, daily secondary, Edit and rare menu actions", async () => {
  const edit = vi.fn();
  render(
    <DetailHeader
      eyebrow="Plant"
      title="Specimen"
      primaryActions={<button>Record harvest</button>}
      secondaryActions={<button className="button--secondary">Transfer</button>}
      onEdit={edit}
      overflow={
        <OverflowMenu ariaLabel="More record actions">
          <a href="#/labels">Print label</a>
        </OverflowMenu>
      }
    />,
  );
  const bar = screen.getByRole("group", { name: "Record actions" });
  expect(
    within(bar)
      .getAllByRole("button")
      .map((button) => button.textContent),
  ).toEqual(["Record harvest", "Transfer", "Edit", "More"]);
  expect(within(bar).getByRole("button", { name: "Transfer" })).toHaveClass(
    "button--secondary",
  );
  const user = userEvent.setup();
  await user.click(within(bar).getByRole("button", { name: "Edit" }));
  expect(edit).toHaveBeenCalledTimes(1);
  expect(
    screen.queryByRole("link", { name: "Print label" }),
  ).not.toBeInTheDocument();
  await user.click(
    within(bar).getByRole("button", { name: "More record actions" }),
  );
  expect(screen.getByRole("link", { name: "Print label" })).toHaveAttribute(
    "href",
    "#/labels",
  );
});
