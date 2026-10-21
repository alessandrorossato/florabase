import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, expect, test } from "vitest";
import { MapWorkspace } from "./MapWorkspace";

afterEach(cleanup);
function LocalChoice() {
  const [checked, setChecked] = useState(false);
  return (
    <label>
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => {
          setChecked(event.target.checked);
        }}
      />
      Example selection
    </label>
  );
}
test("pane switching preserves mounted selection and focus without changing location", async () => {
  const user = userEvent.setup();
  const before = window.location.href;
  const { container } = render(
    <MapWorkspace browserLabel="Species list" browser={<LocalChoice />}>
      <p>Map evidence</p>
    </MapWorkspace>,
  );
  const browser = screen.getByRole("button", { name: "Species list" });
  await user.click(browser);
  expect(browser).toHaveFocus();
  expect(container.firstChild).toHaveAttribute("data-pane", "browser");
  await user.click(screen.getByRole("checkbox"));
  const map = screen.getByRole("button", { name: "Map & evidence" });
  await user.click(map);
  expect(map).toHaveFocus();
  expect(container.firstChild).toHaveAttribute("data-pane", "map");
  await user.click(browser);
  expect(screen.getByRole("checkbox")).toBeChecked();
  expect(window.location.href).toBe(before);
});

test("canvas-only composition leaves the full map available without an empty side panel", () => {
  const { container } = render(
    <MapWorkspace>
      <p>Map evidence</p>
    </MapWorkspace>,
  );
  expect(screen.getByText("Map evidence")).toBeVisible();
  expect(
    screen.queryByRole("group", { name: "Map workspace view" }),
  ).not.toBeInTheDocument();
  expect(
    container.querySelector(".maps-workspace__browser"),
  ).not.toBeInTheDocument();
});
