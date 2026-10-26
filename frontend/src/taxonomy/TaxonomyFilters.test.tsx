import { useState } from "react";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test } from "vitest";
import { TaxonomyFilters } from "./TaxonomyFilters";
import { sample, ids, node } from "./graph.fixture";
import { taxonomyHash, type TaxonomyState } from "./state";
afterEach(cleanup);
function Filters() {
  const [state, setState] = useState<TaxonomyState>({
    scope: "all",
    record: [],
    q: "Basil",
    taxon: ids.species,
    view: "tree",
  });
  const data = {
    ...sample,
    nodes: [
      ...sample.nodes,
      node("wfo-9999999901", "Other family", "family", ids.root),
      node("wfo-9999999902", "Other genus", "genus", "wfo-9999999901"),
      node("wfo-9999999903", "Other species", "species", "wfo-9999999902"),
    ],
  };
  return (
    <>
      <TaxonomyFilters data={data} state={state} update={setState} />
      <output aria-label="Filter URL">{taxonomyHash(state)}</output>
    </>
  );
}
test("hierarchy choices depend on actual ancestry and parent changes clear downstream focus", async () => {
  const user = userEvent.setup();
  render(<Filters />);
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Family" }),
    ids.family,
  );
  expect(screen.getByRole("combobox", { name: "Genus" })).toHaveTextContent(
    "Ocimum",
  );
  expect(screen.getByRole("combobox", { name: "Genus" })).not.toHaveTextContent(
    "Other genus",
  );
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Genus" }),
    ids.genus,
  );
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Species" }),
    ids.species,
  );
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Family" }),
    "wfo-9999999901",
  );
  expect(screen.getByRole("combobox", { name: "Genus" })).toHaveValue("");
  expect(screen.getByRole("combobox", { name: "Species" })).toHaveValue("");
  expect(screen.getByRole("combobox", { name: "Species" })).toHaveTextContent(
    "Other species",
  );
  expect(
    screen.getByRole("combobox", { name: "Species" }),
  ).not.toHaveTextContent("Ocimum basilicum");
  expect(screen.getByLabelText("Filter URL")).toHaveTextContent("q=Basil");
});
test("media/status and display controls retain URL evidence without changing category semantics", async () => {
  const user = userEvent.setup();
  render(<Filters />);
  await user.click(screen.getByRole("checkbox", { name: "Seeds" }));
  await user.click(screen.getByRole("checkbox", { name: "Plants" }));
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Source placement" }),
    "synonym",
  );
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Stored cover thumbnail" }),
    "with",
  );
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Show ranks through" }),
    "family",
  );
  await user.click(
    screen.getByRole("checkbox", {
      name: "Show representative node thumbnails",
    }),
  );
  const url = screen.getByLabelText("Filter URL");
  for (const value of [
    "record=seed_lot",
    "record=plant",
    "status=synonym",
    "media=with",
    "photos=hide",
    "through=family",
    "q=Basil",
  ])
    expect(url).toHaveTextContent(value);
  expect(
    screen.getByRole("checkbox", { name: "Represented branches only" }),
  ).toBeDisabled();
});
