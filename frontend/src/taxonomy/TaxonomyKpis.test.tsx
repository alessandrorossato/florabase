import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test } from "vitest";
import { TaxonomyKpis } from "./TaxonomyKpis";
import { sample, ids } from "./graph.fixture";
const state = {
  scope: "all" as const,
  record: [],
  q: "Basil",
  taxon: ids.species,
};
afterEach(cleanup);
test("KPI popovers inspect exact subsets, toggle/outside/Escape dismiss and retain canonical links", async () => {
  const user = userEvent.setup();
  const rows = [
    sample.identities[0],
    {
      ...sample.identities[1],
      id: "current",
      display_label: "Current only",
      representation: "current" as const,
      current_records: 1,
      living_records: 0,
    },
    sample.identities[1],
  ];
  render(
    <>
      <TaxonomyKpis identities={rows} state={state} />
      <button>Outside</button>
    </>,
  );
  expect(screen.queryByRole("link")).toBeNull();
  const all = screen.getByRole("button", { name: "Identities: 3" });
  await user.click(all);
  expect(
    screen.getAllByRole("link", { name: /Basil|Current only/ }),
  ).toHaveLength(3);
  expect(screen.getByRole("link", { name: "Basil a" })).toHaveAttribute(
    "href",
    expect.stringContaining("taxonomy_return="),
  );
  expect(screen.getByRole("img", { name: "Cover of Basil a" })).toHaveAttribute(
    "src",
    sample.identities[0].cover?.thumbnail_url,
  );
  await user.click(all);
  expect(screen.queryByRole("link")).toBeNull();
  await user.click(screen.getByRole("button", { name: "Living: 1" }));
  expect(
    screen.getByRole("group", { name: "Living: 1 menu" }),
  ).toHaveTextContent("Basil a");
  expect(screen.queryByRole("link", { name: "Current only" })).toBeNull();
  await user.click(screen.getByRole("button", { name: "Current: 2" }));
  expect(
    screen.getByRole("group", { name: "Current: 2 menu" }),
  ).toHaveTextContent("Current only");
  expect(screen.queryByRole("group", { name: "Living: 1 menu" })).toBeNull();
  await user.keyboard("{Escape}");
  expect(screen.getByRole("button", { name: "Current: 2" })).toHaveFocus();
  await user.click(screen.getByRole("button", { name: "Historical: 1" }));
  expect(
    screen.getByRole("group", { name: "Historical: 1 menu" }),
  ).toHaveTextContent("Basil b");
  await user.click(screen.getByRole("button", { name: "Outside" }));
  expect(screen.queryByRole("link")).toBeNull();
});
test("empty KPI and bounded identity pagination remain explicit", async () => {
  const user = userEvent.setup();
  const { rerender } = render(
    <TaxonomyKpis identities={[sample.identities[0]]} state={state} />,
  );
  await user.click(screen.getByRole("button", { name: "Historical: 0" }));
  expect(screen.getByText(/No historical identities/)).toBeVisible();
  await user.keyboard("{Escape}");
  const rows = Array.from({ length: 60 }, (_, i) => ({
    ...sample.identities[0],
    id: "row-" + String(i),
    display_label: "Basil " + String(i),
  }));
  rerender(<TaxonomyKpis identities={rows} state={state} />);
  await user.click(screen.getByRole("button", { name: "Identities: 60" }));
  const panel = screen.getByRole("group", { name: "Identities: 60 menu" });
  expect(within(panel).getAllByRole("img")).toHaveLength(24);
  await user.click(
    screen.getByRole("button", { name: "Show more identities (24 of 60)" }),
  );
  expect(within(panel).getAllByRole("img")).toHaveLength(48);
  expect(
    screen.getByRole("group", { name: "Identities: 60 menu" }),
  ).toBeVisible();
  fireEvent.pointerDown(document.body);
  expect(
    screen.queryByRole("group", { name: "Identities: 60 menu" }),
  ).toBeNull();
});
