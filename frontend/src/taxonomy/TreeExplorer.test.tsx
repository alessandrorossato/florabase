import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterAll, beforeAll, afterEach, expect, test, vi } from "vitest";
import * as graph from "./graph";
import { TaxonomyFilters } from "./TaxonomyFilters";
import { TreeExplorer } from "./TreeExplorer";
import { TaxonomyCover } from "./TaxonomyCover";
import { ids, largeGraph, sample } from "./graph.fixture";
import { readState, taxonomyHash } from "./state";
afterEach(cleanup);
beforeAll(() => {
  Object.defineProperties(HTMLElement.prototype, {
    setPointerCapture: { configurable: true, value: vi.fn() },
    hasPointerCapture: { configurable: true, value: () => false },
    releasePointerCapture: { configurable: true, value: vi.fn() },
  });
});
afterAll(() => {
  delete (HTMLElement.prototype as Partial<HTMLElement>).setPointerCapture;
  delete (HTMLElement.prototype as Partial<HTMLElement>).hasPointerCapture;
  delete (HTMLElement.prototype as Partial<HTMLElement>).releasePointerCapture;
});
function setup() {
  const update = vi.fn(),
    select = vi.fn();
  const view = render(
    <TreeExplorer
      data={sample}
      state={{
        scope: "all",
        record: [],
        q: "",
        taxon: ids.species,
        view: "tree",
      }}
      update={update}
      select={select}
      detailsOpen
      toggleDetails={vi.fn()}
    />,
  );
  return { ...view, update, select };
}
test("select and disclosure are separate, with keyboard parent/child traversal", async () => {
  const user = userEvent.setup(),
    { select } = setup();
  const species = screen.getByRole("button", {
    name: "Ocimum basilicum, species, 2 identities",
  });
  await user.click(species);
  expect(select).toHaveBeenCalledWith(ids.species);
  select.mockClear();
  await user.click(
    screen.getByRole("button", { name: "Collapse Ocimum branch" }),
  );
  expect(select).not.toHaveBeenCalled();
  expect(
    screen.queryByRole("button", {
      name: "Ocimum basilicum, species, 2 identities",
    }),
  ).toBeNull();
  await user.click(
    screen.getByRole("button", { name: "Expand Ocimum branch" }),
  );
  const genus = screen.getByRole("button", {
    name: "Ocimum, genus, 2 identities",
  });
  genus.focus();
  await user.keyboard("{ArrowRight}");
  expect(
    screen.getByRole("button", {
      name: "Ocimum basilicum, species, 2 identities",
    }),
  ).toHaveFocus();
  await user.keyboard("{Enter}");
  expect(select).toHaveBeenCalledWith(ids.species);
});
test("zoom and pan do not recompute layout or refetch images", async () => {
  const layout = vi.spyOn(graph, "layoutGraph"),
    user = userEvent.setup();
  setup();
  const before = layout.mock.calls.length;
  const images = screen
    .getAllByRole("img")
    .map((img) => img.getAttribute("src"));
  await user.click(screen.getByRole("button", { name: "Zoom in" }));
  await user.click(screen.getByRole("button", { name: "Zoom out" }));
  const diagram = screen.getByRole("region", {
    name: "Interactive taxonomy diagram",
  });
  diagram.focus();
  await user.keyboard("{ArrowLeft}{ArrowDown}");
  expect(layout).toHaveBeenCalledTimes(before);
  expect(
    new Set(screen.getAllByRole("img").map((img) => img.getAttribute("src"))),
  ).toEqual(new Set(images));
  expect([...new Set(images)]).toEqual([
    "/api/v1/media-assets/asset-a/thumbnail?v=abc",
  ]);
  layout.mockRestore();
});
test("branch/rank controls serialize source IDs and never change collection scope", async () => {
  const user = userEvent.setup(),
    update = vi.fn();
  render(
    <TaxonomyFilters
      data={sample}
      state={{
        scope: "all",
        record: [],
        q: "",
        taxon: ids.species,
        view: "tree",
      }}
      update={update}
    />,
  );
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Family" }),
    ids.family,
  );
  expect(update).toHaveBeenLastCalledWith(
    expect.objectContaining({
      scope: "all",
      record: [],
      branch: ids.family,
      taxon: ids.family,
    }),
  );
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Show ranks through" }),
    "family",
  );
  expect(update).toHaveBeenLastCalledWith(
    expect.objectContaining({ through: "family" }),
  );
  const restored = readState(
    taxonomyHash({
      scope: "historical",
      record: ["seed_lot"],
      q: "Basil",
      taxon: ids.species,
      view: "tree",
      branch: ids.family,
      through: "genus",
    }),
  );
  expect(restored).toMatchObject({
    scope: "historical",
    record: ["seed_lot"],
    q: "Basil",
    view: "tree",
    branch: ids.family,
    through: "genus",
  });
});
test("protected covers fall back on errors and never use a remote/full-size image", () => {
  const { rerender } = render(
    <TaxonomyCover identity={sample.identities[0]} representative />,
  );
  const image = screen.getByRole("img");
  expect(image).toHaveAttribute("loading", "lazy");
  expect(image).toHaveAttribute(
    "src",
    sample.identities[0].cover?.thumbnail_url,
  );
  expect(image).toHaveAccessibleName(/representative descendant/);
  fireEvent.error(image);
  expect(screen.queryByRole("img")).toBeNull();
  rerender(<TaxonomyCover identity={sample.identities[1]} />);
  expect(screen.queryByRole("img")).toBeNull();
});
test("large graph DOM and thumbnail work are bounded", async () => {
  const nodes = largeGraph();
  const data = {
    ...sample,
    nodes,
    identities: Array.from({ length: 5000 }, (_, i) => ({
      ...sample.identities[0],
      id: "identity-" + String(i),
    })),
    counts: { represented: 5000, living: 5000, current: 5000, historical: 0 },
  };
  render(
    <TreeExplorer
      data={data}
      state={{ scope: "all", record: [], q: "", taxon: "", view: "tree" }}
      update={vi.fn()}
      select={vi.fn()}
      detailsOpen
      toggleDetails={vi.fn()}
    />,
  );
  const diagram = screen.getByRole("region", {
    name: "Interactive taxonomy diagram",
  });
  expect(within(diagram).getAllByRole("button").length).toBeLessThanOrEqual(
    480,
  );
  expect(within(diagram).queryAllByRole("img").length).toBeLessThanOrEqual(48);
  const user = userEvent.setup();
  expect(within(diagram).getAllByRole("img").length).toBeGreaterThan(0);
  await user.click(screen.getByText("Branches"));
  for (let i = 0; i < 4; i++)
    await user.click(screen.getByRole("button", { name: "Expand displayed" }));
  expect(screen.getByText(/Display limit reached/)).toBeInTheDocument();
  expect(diagram.querySelectorAll(".tree-node").length).toBeLessThanOrEqual(
    240,
  );
  expect(diagram.querySelectorAll(".tree-edges path").length).toBeLessThan(240);
  expect(within(diagram).queryAllByRole("img").length).toBeLessThanOrEqual(48);
  expect(
    new Set(
      within(diagram)
        .queryAllByRole("img")
        .map((image) => image.getAttribute("src")),
    ).size,
  ).toBeLessThanOrEqual(1);
});

test("pointer drag, pinch, wheel and fit use the camera without selecting a node", async () => {
  const { select } = setup();
  const diagram = screen.getByRole("region", {
    name: "Interactive taxonomy diagram",
  });
  const world = diagram.querySelector(".tree-world");
  const before = world?.getAttribute("style");
  function pointer(type: string, id: number, x: number, y: number) {
    const event = new Event(type, { bubbles: true });
    Object.defineProperties(event, {
      pointerId: { value: id },
      button: { value: 0 },
      clientX: { value: x },
      clientY: { value: y },
    });
    fireEvent(diagram, event);
  }
  pointer("pointerdown", 1, 100, 100);
  pointer("pointermove", 1, 140, 130);
  expect(world?.getAttribute("style")).not.toBe(before);
  pointer("pointerdown", 2, 200, 130);
  const zoom = screen.getByLabelText("Diagram zoom").textContent;
  pointer("pointermove", 2, 260, 130);
  expect(screen.getByLabelText("Diagram zoom").textContent).not.toBe(zoom);
  pointer("pointerup", 1, 140, 130);
  pointer("pointercancel", 2, 260, 130);
  const after = world?.getAttribute("style");
  fireEvent.wheel(diagram, { deltaX: 40, deltaY: 20 });
  expect(world?.getAttribute("style")).not.toBe(after);
  fireEvent.wheel(diagram, {
    deltaY: -100,
    ctrlKey: true,
    clientX: 100,
    clientY: 100,
  });
  expect(select).not.toHaveBeenCalled();
  await userEvent
    .setup()
    .click(screen.getByRole("button", { name: "Fit to view" }));
  expect(world?.getAttribute("style")).toBe(before);
});
