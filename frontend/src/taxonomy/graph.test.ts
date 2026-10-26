import { expect, test } from "vitest";
import {
  ancestry,
  edgePath,
  fitCamera,
  graphIndex,
  GRAPH_LIMIT,
  initialExpansion,
  layoutGraph,
  NODE_HEIGHT,
  NODE_WIDTH,
  zoomCamera,
} from "./graph";
import { ids, largeGraph, node, sample } from "./graph.fixture";

test("source parentage, intermediate ranks and identity counts remain authoritative", () => {
  const index = graphIndex(sample.nodes),
    layout = layoutGraph(index, new Set(index.nodes.keys()));
  expect(ancestry(index, ids.species)).toEqual([
    ids.root,
    ids.family,
    ids.subfamily,
    ids.genus,
    ids.species,
  ]);
  expect(layout.nodes).toHaveLength(sample.nodes.length);
  const positions = new Map(layout.nodes.map((n) => [n.id, n]));
  for (const n of layout.nodes) {
    expect(n.parent).toBe(n.node.parent_id);
    if (n.parent) {
      const parent = positions.get(n.parent);
      expect(parent).toBeDefined();
      expect(n.x).toBeGreaterThan(parent?.x ?? 0);
      if (!parent) throw new Error("Missing source parent");
      expect(edgePath(parent, n)).toMatch(/^M.* C/);
    }
  }
  expect(positions.get(ids.species)?.node.counts.represented).toBe(2);
  expect(positions.get(ids.species)?.node.counts.represented).not.toBe(40);
  expect(
    new Set(
      layout.nodes
        .filter((n) => ![...positions.values()].some((c) => c.parent === n.id))
        .map((n) => n.y),
    ).size,
  ).toBe(2);
});
test("collapse preserves the source index; focus retains ancestry and excludes unrelated branches", () => {
  const index = graphIndex(sample.nodes),
    expanded = new Set(index.nodes.keys());
  expanded.delete(ids.family);
  expect(
    layoutGraph(index, expanded).nodes.some((n) => n.id === ids.species),
  ).toBe(false);
  expect(index.nodes.has(ids.species)).toBe(true);
  expect(
    layoutGraph(index, expanded, ids.family).nodes.some(
      (n) => n.id === ids.species,
    ),
  ).toBe(false);
  const focused = layoutGraph(index, new Set(index.nodes.keys()), ids.genus);
  expect(focused.nodes.map((n) => n.id)).toEqual([
    ids.root,
    ids.family,
    ids.subfamily,
    ids.genus,
    ids.species,
  ]);
  expect(
    layoutGraph(index, new Set(index.nodes.keys()), "", "family").nodes.some(
      (n) => n.id === ids.subfamily,
    ),
  ).toBe(false);
});
test("missing ranks do not create inferred nodes or edges; broken ancestry terminates safely", () => {
  const index = graphIndex([
    node(ids.root, "Plantae", "kingdom", null),
    node(ids.species, "Not inferred from name", "variety", ids.root),
  ]);
  const layout = layoutGraph(index, new Set([ids.root]), "", "family");
  expect(layout.nodes).toHaveLength(2);
  expect(layout.nodes[1].parent).toBe(ids.root);
  expect(ancestry(index, "missing")).toEqual([]);
  const cyclic = graphIndex([
    node(ids.root, "A", "clade", ids.genus),
    node(ids.genus, "B", "genus", ids.root),
  ]);
  expect(ancestry(cyclic, ids.root)).toHaveLength(2);
});
test("large expansion is bounded and initial expansion stays progressive", () => {
  const nodes = largeGraph(),
    index = graphIndex(nodes);
  expect(nodes.length).toBeGreaterThan(5000);
  expect(layoutGraph(index, initialExpansion(index)).nodes.length).toBeLessThan(
    20,
  );
  const expanded = layoutGraph(index, new Set(index.nodes.keys()));
  expect(expanded.nodes).toHaveLength(GRAPH_LIMIT);
  expect(expanded.limited).toBe(true);
  expect(new Set(expanded.nodes.map((n) => n.id)).size).toBe(GRAPH_LIMIT);
});
test("fit and zoom keep a stable world anchor with explicit zoom limits", () => {
  const layout = layoutGraph(
    graphIndex(sample.nodes),
    new Set(sample.nodes.map((n) => n.taxon.source_taxon_id)),
  );
  const c = fitCamera(layout, { width: 800, height: 480 });
  expect(c.x + layout.width * c.zoom).toBeLessThanOrEqual(800);
  expect(c.y + layout.height * c.zoom).toBeLessThanOrEqual(480);
  const point = { x: 300, y: 200 },
    zoomed = zoomCamera(c, 1.5, point);
  expect((point.x - c.x) / c.zoom).toBeCloseTo(
    (point.x - zoomed.x) / zoomed.zoom,
  );
  expect(zoomCamera(c, 1e9, point).zoom).toBe(2.5);
  expect(zoomCamera(c, 1e-9, point).zoom).toBe(0.03);
  expect(NODE_WIDTH).toBeGreaterThan(100);
  expect(NODE_HEIGHT).toBeGreaterThan(44);
});
