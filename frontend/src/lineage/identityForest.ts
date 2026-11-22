import type { components } from "../api/schema";

export type IdentityLineageGraph =
  components["schemas"]["IdentityLineageGraph"];
export type GraphNode = IdentityLineageGraph["nodes"][number];

const keyOf = (kind: string, id: string) => `${kind}:${id}`;
export const nodeKey = (node: GraphNode) =>
  keyOf(node.record.kind, node.record.id);

export interface LineageForest {
  /** Records that start a recorded chain, in response order (identity records first). */
  roots: GraphNode[];
  /** Identity records with no recorded relationship at all. */
  independent: GraphNode[];
  children: Map<string, GraphNode[]>;
  /** Number of recorded parents per record; more than one is shown once, then referenced. */
  parents: Map<string, number>;
}

/**
 * Arranges the graph as a forest using only its explicit edges. Records that share the
 * identity but have no edge stay apart: shared identity is never lineage.
 */
export function buildForest(graph: IdentityLineageGraph): LineageForest {
  const byKey = new Map(graph.nodes.map((node) => [nodeKey(node), node]));
  const children = new Map<string, GraphNode[]>();
  const parents = new Map<string, number>();
  for (const edge of graph.edges) {
    const parent = keyOf(edge.parent_kind, edge.parent_id);
    const child = byKey.get(keyOf(edge.child_kind, edge.child_id));
    if (!child || !byKey.has(parent)) continue;
    children.set(parent, [...(children.get(parent) ?? []), child]);
    parents.set(nodeKey(child), (parents.get(nodeKey(child)) ?? 0) + 1);
  }
  const ordered = [...graph.nodes].sort(
    (a, b) => Number(b.in_identity) - Number(a.in_identity),
  );
  const linked = (node: GraphNode) =>
    children.has(nodeKey(node)) || parents.has(nodeKey(node));
  const independent = graph.nodes.filter(
    (node) => node.in_identity && !linked(node),
  );
  const roots = ordered.filter(
    (node) => linked(node) && !parents.has(nodeKey(node)),
  );
  // Persisted lineage is acyclic; if a cycle ever appears, its records still get shown.
  const reached = new Set<string>();
  const visit = (node: GraphNode) => {
    if (reached.has(nodeKey(node))) return;
    reached.add(nodeKey(node));
    for (const child of children.get(nodeKey(node)) ?? []) visit(child);
  };
  roots.forEach(visit);
  for (const node of ordered)
    if (linked(node) && !reached.has(nodeKey(node))) {
      roots.push(node);
      visit(node);
    }
  return { roots, independent, children, parents };
}

export interface LineItem {
  node: GraphNode;
  parentKind?: GraphNode["record"]["kind"];
  /** Already drawn under an earlier parent: shown as a reference, not again. */
  reference: boolean;
  children: LineItem[];
}

/**
 * The drawn lines, computed fresh from the forest so rendering stays pure: each record is
 * drawn once, at its first recorded parent in reading order, and referenced afterwards.
 */
export function forestLines(forest: LineageForest): LineItem[] {
  const drawn = new Set<string>();
  const item = (
    node: GraphNode,
    parentKind?: GraphNode["record"]["kind"],
  ): LineItem => {
    const key = nodeKey(node);
    if (drawn.has(key))
      return { node, parentKind, reference: true, children: [] };
    drawn.add(key);
    return {
      node,
      parentKind,
      reference: false,
      children: (forest.children.get(key) ?? []).map((child) =>
        item(child, node.record.kind),
      ),
    };
  };
  return forest.roots.map((root) => item(root));
}
