import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test } from "vitest";

import { FullscreenStage } from "./FullscreenStage";

afterEach(cleanup);

test("full screen enlarges the stage and Escape or the toggle leaves it", async () => {
  const user = userEvent.setup();
  render(
    <FullscreenStage
      className="lineage-stage"
      title="Recorded lines"
      titleId="lines"
      label="recorded lines"
    >
      <p>Diagram</p>
    </FullscreenStage>,
  );
  const stage = screen.getByRole("region", { name: "Recorded lines" });
  expect(stage).not.toHaveClass("is-fullscreen");
  await user.click(
    screen.getByRole("button", { name: "Full screen recorded lines" }),
  );
  expect(stage).toHaveClass("is-fullscreen");
  expect(document.documentElement).toHaveClass("has-fullscreen-frame");
  await user.keyboard("{Escape}");
  expect(stage).not.toHaveClass("is-fullscreen");
  expect(document.documentElement).not.toHaveClass("has-fullscreen-frame");
  await user.click(
    screen.getByRole("button", { name: "Full screen recorded lines" }),
  );
  await user.click(
    screen.getByRole("button", { name: "Exit full screen recorded lines" }),
  );
  expect(stage).not.toHaveClass("is-fullscreen");
});
