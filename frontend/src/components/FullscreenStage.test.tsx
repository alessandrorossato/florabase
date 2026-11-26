import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test } from "vitest";

import { FullscreenStage } from "./FullscreenStage";

afterEach(cleanup);

test("full screen enlarges the stage and Escape or the toggle leaves it", async () => {
  const user = userEvent.setup();
  render(
    <>
      <button type="button">Outside</button>
      <FullscreenStage
        className="lineage-stage"
        title="Recorded lines"
        titleId="lines"
        label="recorded lines"
      >
        <p>Diagram</p>
      </FullscreenStage>
    </>,
  );
  const stage = screen.getByRole("region", { name: "Recorded lines" });
  expect(stage).not.toHaveClass("is-fullscreen");
  await user.click(
    screen.getByRole("button", { name: "Full screen recorded lines" }),
  );
  expect(stage).toHaveClass("is-fullscreen");
  expect(document.documentElement).toHaveClass("has-fullscreen-frame");
  // The rest of the page is inert while the stage covers it.
  expect(screen.getByText("Outside")).toHaveAttribute("inert");
  await user.keyboard("{Escape}");
  expect(stage).not.toHaveClass("is-fullscreen");
  expect(document.documentElement).not.toHaveClass("has-fullscreen-frame");
  expect(screen.getByText("Outside")).not.toHaveAttribute("inert");
  await user.click(
    screen.getByRole("button", { name: "Full screen recorded lines" }),
  );
  await user.click(
    screen.getByRole("button", { name: "Exit full screen recorded lines" }),
  );
  expect(stage).not.toHaveClass("is-fullscreen");
});
