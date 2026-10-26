import { useEffect, useMemo, useRef, useState } from "react";
import { ActionButton, IconButton } from "../components/Action";
import type { Identity, Tree } from "./api";
import type { TaxonomyState } from "./state";
import { TaxonomyCover } from "./TaxonomyCover";
import {
  ancestry,
  edgePath,
  fitCamera,
  graphIndex,
  initialExpansion,
  layoutGraph,
  NODE_HEIGHT,
  NODE_WIDTH,
  zoomCamera,
  type Camera,
  type GraphIndex,
  type GraphLayout,
} from "./graph";
import "./tree-explorer.css";

export function TreeExplorer({
  data,
  state,
  update,
  select,
  detailsOpen,
  toggleDetails,
  fullscreen = false,
  toggleFullscreen,
}: {
  data: Tree;
  state: TaxonomyState;
  update: (state: TaxonomyState) => void;
  select: (id: string) => void;
  detailsOpen: boolean;
  toggleDetails: () => void;
  fullscreen?: boolean;
  toggleFullscreen?: () => void;
}) {
  const index = useMemo(() => graphIndex(data.nodes), [data.nodes]);
  const [opened, setOpened] = useState<Set<string>>(() => new Set());
  const [closed, setClosed] = useState<Set<string>>(() => new Set());
  const [reset, setReset] = useState(0);
  const path = ancestry(index, state.taxon);
  const expanded = initialExpansion(index);
  for (const id of [
    ...opened,
    ...path.slice(0, -1),
    ...ancestry(index, state.branch ?? ""),
    ...(index.children.get(state.branch ?? "") ?? []),
  ])
    expanded.add(id);
  for (const id of closed) expanded.delete(id);
  const expansionKey = [...expanded].sort().join(",");
  const layout = useMemo(
    () =>
      layoutGraph(
        index,
        new Set(expansionKey.split(",")),
        state.branch,
        state.through,
      ),
    [index, expansionKey, state.branch, state.through],
  );
  const identities = useMemo(
    () => new Map(data.identities.map((identity) => [identity.id, identity])),
    [data.identities],
  );
  const covers = useMemo(() => {
    const result = new Map<string, Identity>();
    for (const node of data.nodes) {
      const representative = node.identity_ids
        .filter((id) => identities.get(id)?.cover)
        .sort()[0];
      if (representative) {
        const identity = identities.get(representative);
        if (identity) result.set(node.taxon.source_taxon_id, identity);
      }
    }
    return result;
  }, [data.nodes, identities]);
  function toggle(id: string) {
    if (expanded.has(id)) {
      setClosed(new Set(closed).add(id));
      setOpened(new Set([...opened].filter((item) => item !== id)));
    } else {
      setOpened(new Set(opened).add(id));
      setClosed(new Set([...closed].filter((item) => item !== id)));
    }
  }
  function focus(id: string) {
    update({
      ...state,
      branch: id || undefined,
      through: undefined,
      taxon: id || state.taxon,
    });
    setOpened(
      new Set([
        ...opened,
        ...ancestry(index, id),
        id,
        ...(index.children.get(id) ?? []),
      ]),
    );
    setClosed(new Set());
  }
  return (
    <div className="tree-explorer">
      <div className="tree-explorer-tools">
        {toggleFullscreen && (
          <ActionButton
            icon="maximize"
            variant="secondary"
            onClick={toggleFullscreen}
          >
            {fullscreen ? "Exit fullscreen" : "Fullscreen"}
          </ActionButton>
        )}
        <details className="tree-branch-controls">
          <summary>Branches</summary>
          <div>
            <ActionButton
              variant="quiet"
              onClick={() => {
                setOpened(new Set(layout.nodes.map((node) => node.id)));
                setClosed(new Set());
              }}
            >
              Expand displayed
            </ActionButton>
            <ActionButton
              variant="quiet"
              onClick={() => {
                setOpened(new Set());
                setClosed(new Set(index.nodes.keys()));
              }}
            >
              Collapse all
            </ActionButton>
            <p>
              Expand progressively within the 240-node display bound. Hierarchy
              and rank controls are in Filters.
            </p>
          </div>
        </details>
        <ActionButton
          variant="quiet"
          disabled={!state.taxon || !index.nodes.has(state.taxon)}
          onClick={() => {
            focus(state.taxon);
          }}
        >
          Focus selected branch
        </ActionButton>
        <ActionButton
          variant="quiet"
          onClick={() => {
            setClosed(new Set());
            setOpened(new Set());
            setReset((n) => n + 1);
            update({ ...state, branch: undefined, through: undefined });
          }}
        >
          Reset view
        </ActionButton>
        <ActionButton variant="secondary" onClick={toggleDetails}>
          {detailsOpen ? "Hide details" : "Show details"}
        </ActionButton>
      </div>
      {state.branch && (
        <p className="tree-focus-note">
          Focused branch:{" "}
          {index.nodes.get(state.branch)?.taxon.scientific_name ??
            "No longer eligible"}
          .{" "}
          <button
            className="button--quiet"
            onClick={() => {
              focus("");
            }}
          >
            Clear branch focus
          </button>
        </p>
      )}
      {state.taxon &&
        !layout.nodes.some((node) => node.id === state.taxon) &&
        index.nodes.has(state.taxon) && (
          <p role="status" className="tree-focus-note">
            Selection is outside displayed branches or ranks. Its details are
            retained.{" "}
            <button
              className="button--quiet"
              onClick={() => {
                focus(state.taxon);
              }}
            >
              Reveal selection
            </button>
          </p>
        )}
      <TreeDiagram
        key={`${state.branch ?? ""}:${state.through ?? ""}:${String(reset)}`}
        layout={layout}
        index={index}
        expanded={expanded}
        selected={state.taxon}
        focus={state.branch}
        through={state.through}
        covers={covers}
        photos={state.photos !== "hide"}
        toggle={toggle}
        select={select}
      />
      <p className="tree-explorer-caption">
        {layout.nodes.length} displayed taxa · {data.counts.represented}{" "}
        eligible identities · represented branches only · accepted concepts;
        linked synonyms remain in identity details.
        {layout.limited
          ? " Display limit reached (240 nodes). Collapse branches or focus a family/genus before expanding further."
          : ""}{" "}
        Taxonomic classification, without evolutionary distance.
      </p>
    </div>
  );
}

function TreeDiagram({
  layout,
  index,
  expanded,
  selected,
  focus,
  through,
  covers,
  photos,
  toggle,
  select,
}: {
  layout: GraphLayout;
  index: GraphIndex;
  expanded: Set<string>;
  selected: string;
  focus?: string;
  through?: string;
  covers: Map<string, Identity>;
  photos: boolean;
  toggle: (id: string) => void;
  select: (id: string) => void;
}) {
  const viewport = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 800, height: 480 });
  const [camera, setCamera] = useState<Camera | null>(null);
  const [roving, setRoving] = useState(selected || layout.nodes[0]?.id || "");
  const pendingFocus = useRef<string | null>(null);
  const points = useRef(new Map<number, { x: number; y: number }>());
  const dragged = useRef(false);
  const dragOrigin = useRef<{ x: number; y: number } | null>(null);
  const base = useMemo(() => {
    const target =
      layout.nodes.find((node) => node.id === (focus ?? selected)) ??
      layout.nodes[0];
    const fit = fitCamera(layout, size);
    if (
      layout.nodes.length > 0 &&
      (focus || size.width < 600 || fit.zoom < 0.55)
    ) {
      const zoom = 0.85;
      return {
        zoom,
        x: size.width / 2 - (target.x + NODE_WIDTH / 2) * zoom,
        y: size.height / 2 - (target.y + NODE_HEIGHT / 2) * zoom,
      };
    }
    return fit;
  }, [layout, size, focus, selected]);
  const active = camera ?? base;
  const path = new Set(ancestry(index, selected));
  const positions = useMemo(
    () => new Map(layout.nodes.map((node) => [node.id, node])),
    [layout],
  );
  useEffect(() => {
    const element = viewport.current;
    if (!element || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver((entries) => {
      const rect = entries.at(0)?.contentRect;
      if (rect?.width && rect.height)
        setSize({ width: rect.width, height: rect.height });
    });
    observer.observe(element);
    return () => {
      observer.disconnect();
    };
  }, []);
  useEffect(() => {
    const element = viewport.current;
    if (!element) return;
    const wheel = (event: WheelEvent) => {
      event.preventDefault();
      if (event.ctrlKey || event.metaKey) {
        const rect = element.getBoundingClientRect();
        setCamera((previous) =>
          zoomCamera(previous ?? base, Math.exp(-event.deltaY * 0.003), {
            x: event.clientX - rect.left,
            y: event.clientY - rect.top,
          }),
        );
      } else
        setCamera((previous) => {
          const c = previous ?? base;
          return {
            ...c,
            x: c.x - (event.shiftKey ? event.deltaY : event.deltaX),
            y: c.y - (event.shiftKey ? 0 : event.deltaY),
          };
        });
    };
    element.addEventListener("wheel", wheel, { passive: false });
    return () => {
      element.removeEventListener("wheel", wheel);
    };
  }, [base]);
  function zoom(factor: number) {
    setCamera((previous) =>
      zoomCamera(previous ?? base, factor, {
        x: size.width / 2,
        y: size.height / 2,
      }),
    );
  }
  function moveFocus(id: string) {
    const node = positions.get(id);
    if (!node) return;
    setRoving(id);
    pendingFocus.current = id;
    setCamera({
      ...active,
      x: size.width / 2 - (node.x + NODE_WIDTH / 2) * active.zoom,
      y: size.height / 2 - (node.y + NODE_HEIGHT / 2) * active.zoom,
    });
  }
  const displayed = layout.nodes.filter((node) => {
    const x = node.x * active.zoom + active.x,
      y = node.y * active.zoom + active.y;
    return (
      x + NODE_WIDTH * active.zoom > -160 &&
      x < size.width + 160 &&
      y + NODE_HEIGHT * active.zoom > -120 &&
      y < size.height + 120
    );
  });
  return (
    <>
      <div
        className="tree-camera-controls"
        role="group"
        aria-label="Diagram camera"
      >
        <ActionButton
          variant="secondary"
          onClick={() => {
            setCamera(fitCamera(layout, size));
          }}
        >
          Fit to view
        </ActionButton>
        <IconButton
          icon="add"
          label="Zoom in"
          tooltip="Zoom into the taxonomy diagram"
          onClick={() => {
            zoom(1.35);
          }}
        />
        <output aria-label="Diagram zoom">
          {Math.round(active.zoom * 100)}%
        </output>
        <ActionButton
          variant="secondary"
          aria-label="Zoom out"
          onClick={() => {
            zoom(1 / 1.35);
          }}
        >
          −
        </ActionButton>
        <span className="tree-camera-help" id="tree-camera-help">
          Drag / scroll to pan · Ctrl+scroll or pinch to zoom · arrow keys
          browse nodes
        </span>
      </div>
      <div
        className="tree-canvas"
        ref={viewport}
        tabIndex={0}
        role="region"
        aria-label="Interactive taxonomy diagram"
        aria-describedby="tree-camera-help"
        onKeyDown={(event) => {
          if (event.target !== event.currentTarget) return;
          const deltas: Partial<Record<string, [number, number]>> = {
            ArrowLeft: [60, 0],
            ArrowRight: [-60, 0],
            ArrowUp: [0, 60],
            ArrowDown: [0, -60],
          };
          const delta = deltas[event.key];
          if (delta) {
            event.preventDefault();
            const [dx, dy] = delta;
            setCamera({ ...active, x: active.x + dx, y: active.y + dy });
          } else if (event.key === "+" || event.key === "=") {
            event.preventDefault();
            zoom(1.35);
          } else if (event.key === "-") {
            event.preventDefault();
            zoom(1 / 1.35);
          } else if (event.key === "Home" || event.key === "0") {
            event.preventDefault();
            setCamera(fitCamera(layout, size));
          }
        }}
        onPointerDown={(event) => {
          if (event.button !== 0) return;
          points.current.set(event.pointerId, {
            x: event.clientX,
            y: event.clientY,
          });
          dragOrigin.current = { x: event.clientX, y: event.clientY };
          dragged.current = false;
        }}
        onPointerMove={(event) => {
          const old = points.current.get(event.pointerId);
          if (!old) return;
          const before = [...points.current.values()];
          points.current.set(event.pointerId, {
            x: event.clientX,
            y: event.clientY,
          });
          const origin = dragOrigin.current;
          if (
            !dragged.current &&
            origin &&
            Math.hypot(event.clientX - origin.x, event.clientY - origin.y) < 5
          )
            return;
          dragged.current = true;
          event.currentTarget.setPointerCapture(event.pointerId);
          if (points.current.size === 2) {
            const after = [...points.current.values()];
            const distance = (p: { x: number; y: number }[]) =>
              Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y);
            const previous = distance(before);
            const rect = event.currentTarget.getBoundingClientRect();
            const center = {
              x: (after[0].x + after[1].x) / 2 - rect.left,
              y: (after[0].y + after[1].y) / 2 - rect.top,
            };
            if (previous > 0)
              setCamera((c) =>
                zoomCamera(
                  {
                    ...(c ?? base),
                    x: (c ?? base).x + (event.clientX - old.x) / 2,
                    y: (c ?? base).y + (event.clientY - old.y) / 2,
                  },
                  distance(after) / previous,
                  center,
                ),
              );
          } else
            setCamera((c) => ({
              ...(c ?? base),
              x: (c ?? base).x + event.clientX - old.x,
              y: (c ?? base).y + event.clientY - old.y,
            }));
        }}
        onPointerUp={(event) => {
          points.current.delete(event.pointerId);
          if (event.currentTarget.hasPointerCapture(event.pointerId))
            event.currentTarget.releasePointerCapture(event.pointerId);
        }}
        onPointerCancel={() => {
          points.current.clear();
          dragOrigin.current = null;
        }}
        onClickCapture={(event) => {
          if (dragged.current) {
            event.preventDefault();
            event.stopPropagation();
            dragged.current = false;
          }
        }}
      >
        {!layout.nodes.length ? (
          <p className="taxonomy-empty">
            No classified taxa match these filters. Unresolved identities remain
            available in Needs review.
          </p>
        ) : (
          <div
            className="tree-world"
            style={{
              width: layout.width,
              height: layout.height,
              transform: `translate(${String(active.x)}px, ${String(active.y)}px) scale(${String(active.zoom)})`,
            }}
          >
            <svg
              className="tree-edges"
              width={layout.width}
              height={layout.height}
              aria-hidden="true"
            >
              {layout.nodes.map((node) => {
                const parent = node.parent
                  ? positions.get(node.parent)
                  : undefined;
                return parent ? (
                  <path
                    key={node.id}
                    d={edgePath(parent, node)}
                    className={
                      path.has(node.id) ? "tree-edge--selected" : undefined
                    }
                  />
                ) : null;
              })}
            </svg>
            {displayed.map((placed, i) => {
              const id = placed.id,
                node = placed.node,
                children = index.children.get(id) ?? [],
                representative = covers.get(id);
              return (
                <div
                  key={id}
                  className={`tree-node${id === selected ? " tree-node--selected" : path.has(id) ? " tree-node--ancestor" : ""}`}
                  style={{
                    left: placed.x,
                    top: placed.y,
                    width: NODE_WIDTH,
                    minHeight: NODE_HEIGHT,
                  }}
                >
                  <button
                    className="tree-node-select"
                    type="button"
                    aria-label={`${node.taxon.scientific_name}, ${node.taxon.rank}, ${String(node.counts.represented)} identities`}
                    aria-pressed={id === selected}
                    tabIndex={
                      roving === id || (!positions.has(roving) && i === 0)
                        ? 0
                        : -1
                    }
                    ref={(element) => {
                      if (element && pendingFocus.current === id) {
                        element.focus({ preventScroll: true });
                        pendingFocus.current = null;
                      }
                    }}
                    onFocus={() => {
                      setRoving(id);
                    }}
                    onClick={() => {
                      setRoving(id);
                      select(id);
                    }}
                    onKeyDown={(event) => {
                      const at = layout.nodes.findIndex(
                        (item) => item.id === id,
                      );
                      let next: string | undefined;
                      if (event.key === "ArrowRight") {
                        if (
                          children.length &&
                          node.taxon.rank !== through &&
                          !expanded.has(id)
                        ) {
                          event.preventDefault();
                          event.stopPropagation();
                          toggle(id);
                          return;
                        }
                        next = layout.nodes.find(
                          (item) => item.parent === id,
                        )?.id;
                      } else if (event.key === "ArrowLeft")
                        next = placed.parent ?? undefined;
                      else if (event.key === "ArrowDown")
                        next = layout.nodes[at + 1]?.id;
                      else if (event.key === "ArrowUp")
                        next = layout.nodes[at - 1]?.id;
                      else if (event.key === "Home") next = layout.nodes[0]?.id;
                      else if (event.key === "End")
                        next = layout.nodes.at(-1)?.id;
                      if (next) {
                        event.preventDefault();
                        event.stopPropagation();
                        moveFocus(next);
                      }
                    }}
                  >
                    <TaxonomyCover
                      identity={representative}
                      representative
                      load={photos && active.zoom >= 0.18 && i < 48}
                    />
                    <span className="tree-node-copy">
                      <strong
                        className={
                          [
                            "genus",
                            "species",
                            "subspecies",
                            "variety",
                            "form",
                          ].includes(node.taxon.rank)
                            ? "taxonomy-scientific"
                            : undefined
                        }
                      >
                        {node.taxon.scientific_name}
                      </strong>
                      <small>{node.taxon.rank}</small>
                    </span>
                    <span className="taxonomy-count">
                      {node.counts.represented}
                    </span>
                  </button>
                  {children.length > 0 && node.taxon.rank !== through && (
                    <button
                      type="button"
                      className="tree-node-expand"
                      aria-label={`${expanded.has(id) ? "Collapse" : "Expand"} ${node.taxon.scientific_name} branch`}
                      aria-expanded={expanded.has(id)}
                      onClick={() => {
                        toggle(id);
                      }}
                    >
                      {expanded.has(id) ? "−" : "+"}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </>
  );
}
