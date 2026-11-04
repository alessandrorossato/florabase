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
 * The record header's compact upstream path: only explicitly recorded sources, oldest
 * first, ending at this record. A shared Botanical identity never implies lineage, and
 * descendants are not shown here (they are summarised by their own records).
 */
export function LineageStrip({
  kind,
  id,
  current,
  includeSubject = false,
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
  fullHref?: string;
  onFull?: MouseEventHandler<HTMLAnchorElement>;
}) {
  const [state, retry] = useRecordedLineage(kind, id);
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
    body = nodes.length ? (
      <ol className="lineage-strip__path">
        {nodes.map((node) => (
          <li key={`${node.kind}:${node.id}`}>
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
          <span className="lineage-strip__kind">{current}</span>
        </li>
      </ol>
    ) : (
      <p className="lineage-strip__note">No recorded source material.</p>
    );
  }
  return (
    <nav className="lineage-strip" aria-label="Recorded lineage">
      <p className="lineage-strip__label" aria-hidden="true">
        Recorded lineage
      </p>
      {body}
      {fullHref && (
        <a className="lineage-strip__full" href={fullHref} onClick={onFull}>
          Full lineage
        </a>
      )}
    </nav>
  );
}
