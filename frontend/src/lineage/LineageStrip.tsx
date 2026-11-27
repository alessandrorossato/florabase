import { useId, useState } from "react";
import type { MouseEventHandler } from "react";

import {
  ancestryKinds,
  descendantSummaryLabel,
  lineageFallbackLabels,
  lineageHref,
  lineageKindLabels,
  lineageVerbs,
  upstreamPath,
  useDirectDescendants,
  useRecordedLineage,
  type AncestryKind,
  type LineageEndpoint,
  type LineageNode,
} from "./useRecordedLineage";
import "./lineage-strip.css";

function Verb({
  from,
  to,
}: {
  from?: LineageNode["kind"] | "harvest";
  to?: LineageNode["kind"] | "harvest";
}) {
  const verb = from && to ? lineageVerbs[`${from}>${to}`] : undefined;
  return verb ? <span className="lineage-strip__verb">{verb}</span> : null;
}

/**
 * The record header's compact lineage summary: explicitly recorded sources oldest first,
 * ending at this record, plus a compact descendants summary linking to the Lineage tab.
 * A shared Botanical identity never implies lineage.
 */
export function LineageStrip({
  kind,
  id,
  current,
  includeSubject = false,
  currentKind,
  fullHref,
  onFull,
  onLineageTab = false,
  descendantsKind,
  descendantsId,
  descendantsSummary,
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
  currentKind?: LineageNode["kind"] | "harvest";
  fullHref?: string;
  onFull?: MouseEventHandler<HTMLAnchorElement>;
  /** True when the Lineage tab is already active; keeps "Full lineage" in place without jump. */
  onLineageTab?: boolean;
  /** Optional explicit record kind/id for direct descendants (used by Sowing). */
  descendantsKind?: AncestryKind;
  descendantsId?: string;
  /** Optional pre-computed compact descendants text (used by Harvest conversions). */
  descendantsSummary?: string | null;
}) {
  const [state, retry] = useRecordedLineage(kind, id);
  const resolvedDescKind: AncestryKind | null =
    descendantsSummary !== undefined
      ? null
      : descendantsKind && descendantsId
        ? descendantsKind
        : fullHref && !includeSubject
          ? ancestryKinds[kind]
          : null;
  const resolvedDescId =
    resolvedDescKind === null
      ? null
      : (descendantsId ?? (!includeSubject ? id : null));
  const [descendants] = useDirectDescendants(resolvedDescKind, resolvedDescId);
  const descendantText =
    descendantsSummary !== undefined
      ? descendantsSummary
      : descendants.status === "ready"
        ? descendantSummaryLabel(descendants.value)
        : null;

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
              ...(descendantText ? [descendantText] : []),
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
        {descendantText && (
          <li className="lineage-strip__descendants">
            {fullHref ? (
              <a href={fullHref} onClick={onFull}>
                {descendantText}
              </a>
            ) : (
              <span>{descendantText}</span>
            )}
          </li>
        )}
      </ol>
    ) : (
      <p className="lineage-strip__note">
        No recorded source material.
        {descendantText && (
          <span className="lineage-strip__descendants-inline">
            {" "}
            <span aria-hidden="true">→</span>{" "}
            {fullHref ? (
              <a href={fullHref} onClick={onFull}>
                {descendantText}
              </a>
            ) : (
              descendantText
            )}
          </span>
        )}
      </p>
    );
  }
  return (
    <nav
      className="lineage-strip"
      aria-label="Recorded lineage"
      data-expanded={expanded || undefined}
    >
      <div className="lineage-strip__header">
        <p className="lineage-strip__label" aria-hidden="true">
          Recorded lineage
        </p>
        {fullHref && (
          <a
            className="lineage-strip__full"
            href={fullHref}
            aria-current={onLineageTab ? "page" : undefined}
            onClick={onFull}
          >
            Full lineage
          </a>
        )}
      </div>
      {toggle}
      {body}
    </nav>
  );
}
