import { mkdirSync, writeFileSync } from "node:fs";
import { expect, test } from "vitest";
import { graphIndex, layoutGraph, GRAPH_LIMIT } from "./graph";
import { largeGraph } from "./graph.fixture";

test("record reproducible 5000-identity graph transformation/layout cost", () => {
  const nodes = largeGraph(5000),
    times: number[] = [];
  let displayed = 0;
  for (let i = 0; i < 15; i++) {
    const start = performance.now(),
      index = graphIndex(nodes);
    const layout = layoutGraph(index, new Set(index.nodes.keys()));
    displayed = layout.nodes.length;
    times.push(performance.now() - start);
  }
  times.sort((a, b) => a - b);
  const report = {
    fixtureIdentities: 5000,
    sourceNodes: nodes.length,
    displayedNodes: displayed,
    renderLimit: GRAPH_LIMIT,
    iterations: 15,
    medianMs: times[7],
    p95Ms: times[14],
    targetMs: 100,
    environment:
      "Vitest Node 24; pure source indexing and bounded layout, not GPU/frame timing",
  };
  mkdirSync("node_modules/.tmp", { recursive: true });
  writeFileSync(
    "node_modules/.tmp/taxonomy-graph-performance.json",
    JSON.stringify(report, null, 2) + "\n",
  );
  expect(displayed).toBe(GRAPH_LIMIT);
  expect(times[14]).toBeLessThan(1000);
});
