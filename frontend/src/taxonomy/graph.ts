import type { Node } from "./api";

export const NODE_WIDTH = 176;
export const NODE_HEIGHT = 80;
export const GRAPH_LIMIT = 240;
export interface GraphIndex {
  nodes: Map<string, Node>;
  children: Map<string | null, string[]>;
  roots: string[];
}
export function graphIndex(nodes: Node[]): GraphIndex {
  const byId = new Map(nodes.map((node) => [node.taxon.source_taxon_id, node]));
  const children = new Map<string | null, string[]>();
  for (const node of nodes) {
    const parent =
      node.parent_id && byId.has(node.parent_id) ? node.parent_id : null;
    const siblings = children.get(parent) ?? [];
    siblings.push(node.taxon.source_taxon_id);
    children.set(parent, siblings);
  }
  for (const ids of children.values())
    ids.sort(
      (a, b) =>
        (byId.get(a)?.taxon.scientific_name ?? "").localeCompare(
          byId.get(b)?.taxon.scientific_name ?? "",
        ) || a.localeCompare(b),
    );
  return { nodes: byId, children, roots: children.get(null) ?? [] };
}
export function ancestry(index: GraphIndex, id: string): string[] {
  const result: string[] = [],
    seen = new Set<string>();
  let current: string | null = id;
  while (current && index.nodes.has(current) && !seen.has(current)) {
    seen.add(current);
    result.unshift(current);
    current = index.nodes.get(current)?.parent_id ?? null;
  }
  return result;
}
export function initialExpansion(index: GraphIndex): Set<string> {
  const open = new Set<string>();
  const queue = index.roots.map((id) => ({ id, depth: 0 }));
  for (const item of queue) {
    if (item.depth >= 3) continue;
    open.add(item.id);
    for (const id of index.children.get(item.id) ?? [])
      queue.push({ id, depth: item.depth + 1 });
  }
  return open;
}
export interface PlacedNode {
  node: Node;
  id: string;
  parent: string | null;
  x: number;
  y: number;
  depth: number;
}
export interface GraphLayout {
  nodes: PlacedNode[];
  width: number;
  height: number;
  limited: boolean;
}

/** Source edges only. Rank limits stop at an actual source rank, never invent a missing rank. */
export function layoutGraph(
  index: GraphIndex,
  expanded: Set<string>,
  branch = "",
  through = "",
  limit = GRAPH_LIMIT,
): GraphLayout {
  const spine = new Set(ancestry(index, branch));
  const allowed = new Set<string>();
  if (branch && index.nodes.has(branch)) {
    const pending = [branch];
    while (pending.length) {
      const id = pending.pop();
      if (!id || allowed.has(id)) continue;
      allowed.add(id);
      pending.push(...(index.children.get(id) ?? []));
    }
    for (const id of spine) allowed.add(id);
  }
  const stack = [...index.roots]
    .reverse()
    .map((id) => ({ id, parent: null as string | null, depth: 0 }));
  const rows: PlacedNode[] = [],
    seen = new Set<string>();
  let limited = false;
  while (stack.length) {
    const item = stack.pop();
    if (!item || seen.has(item.id) || (allowed.size && !allowed.has(item.id)))
      continue;
    seen.add(item.id);
    const node = index.nodes.get(item.id);
    if (!node) continue;
    if (rows.length >= limit) {
      limited = true;
      break;
    }
    rows.push({ ...item, node, x: 28 + item.depth * (NODE_WIDTH + 42), y: 0 });
    if (expanded.has(item.id) && node.taxon.rank !== through) {
      for (const id of [...(index.children.get(item.id) ?? [])].reverse())
        stack.push({ id, parent: item.id, depth: item.depth + 1 });
    }
  }
  const positions = new Map(rows.map((row) => [row.id, row]));
  const childPositions = new Map<string, PlacedNode[]>();
  for (const row of rows)
    if (row.parent)
      childPositions.set(row.parent, [
        ...(childPositions.get(row.parent) ?? []),
        row,
      ]);
  let leaf = 0;
  for (const row of [...rows].reverse()) {
    const kids = childPositions.get(row.id) ?? [];
    row.y = kids.length
      ? (kids[0].y + kids[kids.length - 1].y) / 2
      : 24 + leaf++ * (NODE_HEIGHT + 20);
  }
  // Reverse postorder gives sibling subtrees stable, non-overlapping vertical bands.
  const maxY = Math.max(0, ...rows.map((row) => row.y));
  for (const row of positions.values()) row.y = maxY - row.y + 24;
  return {
    nodes: rows,
    width: Math.max(380, ...rows.map((row) => row.x + NODE_WIDTH + 28)),
    height: Math.max(240, maxY + NODE_HEIGHT + 48),
    limited,
  };
}
export interface Camera {
  x: number;
  y: number;
  zoom: number;
}
export function fitCamera(
  layout: Pick<GraphLayout, "width" | "height">,
  size: { width: number; height: number },
): Camera {
  const zoom = Math.max(
    0.03,
    Math.min(1, size.width / layout.width, size.height / layout.height) * 0.94,
  );
  return {
    zoom,
    x: (size.width - layout.width * zoom) / 2,
    y: (size.height - layout.height * zoom) / 2,
  };
}
export function zoomCamera(
  camera: Camera,
  factor: number,
  point: { x: number; y: number },
): Camera {
  const zoom = Math.max(0.03, Math.min(2.5, camera.zoom * factor)),
    ratio = zoom / camera.zoom;
  return {
    zoom,
    x: point.x - (point.x - camera.x) * ratio,
    y: point.y - (point.y - camera.y) * ratio,
  };
}
export function edgePath(parent: PlacedNode, child: PlacedNode): string {
  const x = parent.x + NODE_WIDTH,
    y = parent.y + NODE_HEIGHT / 2,
    endY = child.y + NODE_HEIGHT / 2,
    middle = (x + child.x) / 2;
  return `M${String(x)},${String(y)} C${String(middle)},${String(y)} ${String(middle)},${String(endY)} ${String(child.x)},${String(endY)}`;
}
