import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test } from "vitest";
import { Lab } from "./Lab";

afterEach(cleanup);

test("the active Sowing specimen excludes completed, failed and abandoned fixture records", () => {
  window.history.replaceState(null, "", "#/sowings?view=list");
  render(<Lab />);
  expect(
    screen.getByRole("link", { name: "Ficus carica" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("link", { name: "Daucus carota" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("link", { name: "Phaseolus vulgaris" }),
  ).not.toBeInTheDocument();
});

test("Dashboard links count records and uses eight distinct attributed reference photographs", () => {
  window.history.replaceState(null, "", "#/dashboard");
  render(<Lab />);
  const overview = screen.getByRole("region", { name: "Botanical overview" });
  const images = within(overview).getAllByRole("img");
  expect(images).toHaveLength(8);
  expect(new Set(images.map((image) => image.getAttribute("src"))).size).toBe(
    8,
  );
  for (const image of images) {
    expect(image).toHaveAttribute(
      "alt",
      expect.stringContaining("not an assigned specimen photo"),
    );
  }
  expect(
    screen.getByRole("link", { name: "Individual Plants: 17" }),
  ).toHaveAttribute("href", "#/plants?type=plant");
  expect(screen.getByRole("link", { name: "Plant groups: 7" })).toHaveAttribute(
    "href",
    "#/plants?type=group",
  );
  expect(screen.getByRole("region", { name: "Next work" })).toHaveTextContent(
    "Repot nursery aloe",
  );
});

test("directory search reaches identities beyond the bounded initial excerpt and retains records across modes", async () => {
  window.history.replaceState(
    null,
    "",
    "#/identities?q=Aloe%20vera&view=gallery",
  );
  render(<Lab />);
  expect(screen.getByRole("link", { name: "Aloe vera" })).toBeInTheDocument();
  const user = userEvent.setup();
  await user.click(screen.getByRole("checkbox", { name: /Select Aloe vera/ }));
  await user.click(screen.getByRole("button", { name: "List" }));
  expect(
    screen.getByRole("checkbox", { name: /Select Aloe vera/ }),
  ).toBeChecked();
  expect(
    screen.getByRole("searchbox", { name: "Search Botanical identities" }),
  ).toHaveValue("Aloe vera");
  expect(window.location.hash).toContain("view=list");
});

test("Plant group scope counts groups and exposes group size without adding a sidebar destination", async () => {
  window.history.replaceState(null, "", "#/plants?type=group&view=list");
  render(<Lab />);
  expect(screen.getByText("7")).toBeInTheDocument();
  expect(screen.getAllByText("Group size (plants)").length).toBeGreaterThan(0);
  expect(
    within(
      screen.getByRole("navigation", { name: "Primary navigation" }),
    ).queryByRole("link", { name: "Plant groups" }),
  ).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Filters" }));
  await userEvent.selectOptions(
    screen.getByRole("combobox", { name: "Record type" }),
    "all",
  );
  await userEvent.click(screen.getByRole("button", { name: "Done" }));
  expect(screen.getByText("24")).toBeInTheDocument();
  expect(window.location.hash).toContain("view=list");
});
