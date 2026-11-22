import { render, screen, within } from "@testing-library/react";
import { expect, test } from "vitest";

import { DataSourcesScreen } from "./DataSourcesScreen";
import { HelpScreen } from "./HelpScreen";

test("Help explains key ideas and links every workspace destination", () => {
  render(<HelpScreen />);
  expect(screen.getByRole("heading", { name: "Help", level: 2 })).toBeVisible();
  const explore = screen.getByRole("region", { name: "Explore" });
  expect(
    within(explore).getByRole("link", { name: "Lineage" }),
  ).toHaveAttribute("href", "#/lineage");
  expect(screen.getByText("Botanical identity")).toBeInTheDocument();
});

test("Data sources lists each external reference with its access rule and the planned standard", () => {
  render(<DataSourcesScreen />);
  const table = screen.getByRole("table");
  expect(
    within(table).getByRole("link", { name: "World Flora Online (WFO)" }),
  ).toHaveAttribute("href", "#/taxonomy");
  expect(within(table).getAllByRole("row")).toHaveLength(7);
  expect(
    screen.getByRole("heading", { name: "Integration standard (planned)" }),
  ).toBeVisible();
});
