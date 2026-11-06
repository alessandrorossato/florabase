import { useId, useState } from "react";
import type { MouseEventHandler } from "react";

import {
  lineageFallbackLabels,
  lineageHref,
  lineageKindLabels,
  upstreamPath,
  useRecordedLineage,
  type LineageEndpoint,
  type LineageNode,
} from "./useRecordedLineage";
import "./lineage-strip.css";

/**
 * The recorded relationship between two adjacent steps, named only from their kinds (every
 * step is an explicitly recorded source, so the pair determines the relationship).
 */
const verbs: Partial<Record<string, string>> = {
  "seed_lot>sowing": "sown as",
  "sowing>plant": "grown into",
  "sowing>plant_group": "grown into",
  "plant_group>plant": "extracted",
  "plant>seed_lot": "produced",
  "plant_group>seed_lot": "produced",
};
function Verb({
  from,
  to,
}: {
  from?: LineageNode["kind"];
  to?: LineageNode["kind"];
}) {
  const verb = from && to ? verbs[`${from}>${to}`] : undefined;
  return verb ? <span className="lineage-strip__verb">{verb}</span> : null;
}

/**
 * The record header's compact upstream path: only explicitly recorded sources, oldest
 * first, ending at this record. A shared Botanical identity never implies lineage, and
 * descendants are not shown here (they are summarised by their own records).
 */
export function LineageStrip({
  kind,
  id,
  current,
  includeSubject = false,
  currentKind,
  fullHref,
  onFull,
}: {
  /** The endpoint whose recorded path is read. */
  kind: LineageEndpoint;
  id: string;
  /** How this record is named at the end of the path, e.g. "This Plant". */
  current: string;
  /**
   * The endpoint record is itself this record's recorded source (a Sowing reads its
   * Seed lot's path, then the Seed lot is appended before this record).
   */
  includeSubject?: boolean;
  /** This record's kind, so the last step can name its recorded relationship. */
  currentKind?: LineageNode["kind"];
  fullHref?: string;
  onFull?: MouseEventHandler<HTMLAnchorElement>;
}) {
  const [state, retry] = useRecordedLineage(kind, id);
  // Phones fold the path into one row (M8); wider layouts hide the toggle and always show it.
  const [expanded, setExpanded] = useState(false);
  const pathId = useId();
  let toggle = null;
  let body;
  if (state.status === "loading")
    body = <p className="lineage-strip__note">Loading recorded lineage…</p>;
  else if (state.status === "error")
    body = (
      // Visible, not announced (nor is loading): the strip is secondary to its record.
      <p className="lineage-strip__note">
        Recorded lineage could not be loaded.{" "}
        <button type="button" className="button--quiet" onClick={retry}>
          Retry lineage
        </button>
      </p>
    );
  else {
    const nodes: LineageNode[] = [
      ...upstreamPath(state.value),
      ...(includeSubject ? [state.value.subject] : []),
    ];
    if (nodes.length)
      toggle = (
        <button
          type="button"
          className="lineage-strip__toggle"
          aria-expanded={expanded}
          aria-controls={pathId}
          onClick={() => {
            setExpanded(!expanded);
          }}
        >
          <span className="lineage-strip__toggle-label">
            Recorded lineage · {nodes.length}{" "}
            {nodes.length === 1 ? "step" : "steps"}
          </span>
          <span className="lineage-strip__toggle-summary">
            {[
              ...nodes.map((node) => lineageKindLabels[node.kind]),
              current,
            ].join(" → ")}
          </span>
        </button>
      );
    body = nodes.length ? (
      <ol id={pathId} className="lineage-strip__path">
        {nodes.map((node, index) => (
          <li key={`${node.kind}:${node.id}`}>
            <Verb from={nodes[index - 1]?.kind} to={node.kind} />
            <span className="lineage-strip__kind">
              {lineageKindLabels[node.kind]}
            </span>
            <a href={lineageHref(node.kind, node.id)}>
              {node.label ?? lineageFallbackLabels[node.kind]}
            </a>
            {node.lifecycle !== "active" && (
              <span className="lineage-strip__state">{node.lifecycle}</span>
            )}
          </li>
        ))}
        <li aria-current="true" className="lineage-strip__current">
          <Verb from={nodes.at(-1)?.kind} to={currentKind} />
          <span className="lineage-strip__kind">{current}</span>
        </li>
      </ol>
    ) : (
      <p className="lineage-strip__note">No recorded source material.</p>
    );
  }
  return (
    <nav
      className="lineage-strip"
      aria-label="Recorded lineage"
      data-expanded={expanded || undefined}
    >
      <p className="lineage-strip__label" aria-hidden="true">
        Recorded lineage
      </p>
      {toggle}
      {body}
      {fullHref && (
        <a className="lineage-strip__full" href={fullHref} onClick={onFull}>
          Full lineage
        </a>
      )}
    </nav>
  );
}
