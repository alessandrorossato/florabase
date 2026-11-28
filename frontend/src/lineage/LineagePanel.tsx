import { useId } from "react";

import { DetailEmptyState } from "../components/DetailEmptyState";
import { LifecycleStatus } from "../components/WorkspaceUI";
import { PropagationPath } from "../propagation/PropagationPath";
import {
  ancestryHref,
  ancestryKinds,
  lineageFallbackLabels as fallbackLabels,
  lineageHref as href,
  lineageKindLabels as labels,
  lineageVerbs,
  upstreamPath,
  useDirectDescendants,
  useRecordedLineage,
  type AncestryChildren,
  type AncestryKind,
  type LineageEndpoint,
  type LineageNode,
} from "./useRecordedLineage";
import "./lineage-panel.css";

export interface LineagePanelSubject {
  kind: LineageNode["kind"] | "harvest";
  id: string;
  label: string | null;
  lifecycle: string;
}

/**
 * The record's Lineage tab, uniform across every Collection record type (Seed lot, Sowing,
 * Plant, Plant group, Vegetative lot, Rooting attempt, Harvest):
 *   1. Explore material ancestry link
 *   2. Ancestors (horizontal chain ending in "This record", or empty wording)
 *   3. Recorded from this record (elbow-connector tree, or empty wording)
 */
export function LineagePanel({
  kind,
  id,
  includeSubject = false,
  subject,
  descendantsKind,
  descendantsId,
  descendantsOverride,
  explorerHref,
}: {
  kind: LineageEndpoint;
  id: string;
  /** True when `kind`/`id` is the parent record (Sowing reads its Seed lot, Harvest its source). */
  includeSubject?: boolean;
  /** The current record when `includeSubject` is true (Sowing or Harvest). */
  subject?: LineagePanelSubject;
  /** Explicit kind/id for direct descendants (used by Sowing). */
  descendantsKind?: AncestryKind;
  descendantsId?: string;
  /** Pre-loaded direct descendants (used by Harvest seed-lot conversions). */
  descendantsOverride?: AncestryChildren;
  /** Override for the Material ancestry explorer link. */
  explorerHref?: string;
}) {
  const [upstream, retryUpstream] = useRecordedLineage(kind, id);
  const resolvedDescKind: AncestryKind | null =
    descendantsOverride !== undefined
      ? null
      : (descendantsKind ?? (!includeSubject ? ancestryKinds[kind] : null));
  const resolvedDescId =
    descendantsOverride !== undefined
      ? null
      : (descendantsId ?? (!includeSubject ? id : null));
  const [loadedDescendants, retryDescendants] = useDirectDescendants(
    resolvedDescKind,
    resolvedDescId,
  );
  const descendants =
    descendantsOverride !== undefined
      ? ({ status: "ready", value: descendantsOverride } as const)
      : loadedDescendants;

  const explorer =
    explorerHref ??
    (descendantsKind && descendantsId
      ? ancestryHref(descendantsKind, descendantsId)
      : ancestryHref(ancestryKinds[kind], id));
  const parentKind: LineageNode["kind"] | "harvest" =
    subject?.kind ?? descendantsKind ?? ancestryKinds[kind];

  let body;
  if (upstream.status === "loading" || descendants.status === "loading")
    body = <p role="status">Loading recorded lineage…</p>;
  else {
    const responseSubject =
      upstream.status === "ready"
        ? (upstream.value as { subject?: LineageNode }).subject
        : undefined;
    const ancestorNodes: LineageNode[] =
      upstream.status === "ready"
        ? [
            ...upstreamPath(upstream.value),
            ...(includeSubject && responseSubject ? [responseSubject] : []),
          ]
        : [];
    const currentRecord: LineagePanelSubject | null =
      subject ??
      (responseSubject
        ? {
            kind: responseSubject.kind,
            id: responseSubject.id,
            label: responseSubject.label ?? null,
            lifecycle: responseSubject.lifecycle,
          }
        : null);

    if (
      upstream.status === "ready" &&
      descendants.status === "ready" &&
      ancestorNodes.length === 0 &&
      descendants.value.total === 0
    )
      body = <DetailEmptyState>No recorded lineage.</DetailEmptyState>;
    else
      // Each half fails on its own, so a loaded upstream path is never hidden by the other.
      body = (
        <>
          {upstream.status === "error" ? (
            <div className="notice notice--error" role="alert">
              <p>Florabase could not load the recorded upstream path.</p>
              <button type="button" onClick={retryUpstream}>
                Retry lineage
              </button>
            </div>
          ) : ancestorNodes.length > 0 && currentRecord ? (
            <RecordedUpstream nodes={ancestorNodes} current={currentRecord} />
          ) : (
            <p className="lineage-panel__start">
              No recorded source: this record starts its line.
            </p>
          )}
          {descendants.status === "error" ? (
            <div className="notice notice--error" role="alert">
              <p>
                Florabase could not load what was recorded from this record.
              </p>
              <button type="button" onClick={retryDescendants}>
                Retry recorded descendants
              </button>
            </div>
          ) : (
            <RecordedDescendants
              parentKind={parentKind}
              value={descendants.value}
              explorer={explorer}
            />
          )}
        </>
      );
  }
  return (
    <>
      <p className="lineage-explore">
        <a href={explorer}>Explore material ancestry</a>
      </p>
      {body}
    </>
  );
}

function RecordedDescendants({
  parentKind,
  value,
  explorer,
}: {
  parentKind: LineageNode["kind"] | "harvest";
  value: AncestryChildren;
  explorer: string;
}) {
  const headingId = useId();
  if (value.total === 0)
    return (
      <p className="lineage-panel__start">Nothing recorded from it yet.</p>
    );
  return (
    <section className="lineage-panel__next" aria-labelledby={headingId}>
      <h4 id={headingId}>Recorded from this record</h4>
      <ul className="lineage-panel__children">
        {value.items.map(({ record, descendant_count }) => (
          <li key={`${record.kind}:${record.id}`}>
            <span className="lineage-panel__verb">
              {lineageVerbs[`${parentKind}>${record.kind}`] ?? "recorded as"}
            </span>
            <article className="lineage-panel__card" data-kind={record.kind}>
              <span className="lineage-panel__kind">{labels[record.kind]}</span>
              <a href={href(record.kind, record.id)}>
                {record.label ?? fallbackLabels[record.kind]}
              </a>
              <span className="lineage-panel__facts">
                <LifecycleStatus state={record.lifecycle} />
                {descendant_count > 0 && (
                  <a href={ancestryHref(record.kind, record.id)}>
                    {`${String(descendant_count)} recorded from it`}
                  </a>
                )}
              </span>
            </article>
          </li>
        ))}
      </ul>
      {value.total > value.items.length && (
        <p className="lineage-panel__more">
          Showing {value.items.length} of {value.total}.{" "}
          <a href={explorer}>Explore material ancestry</a> for the rest.
        </p>
      )}
    </section>
  );
}

function RecordedUpstream({
  nodes,
  current,
}: {
  nodes: LineageNode[];
  current: LineagePanelSubject;
}) {
  const currentHref =
    current.kind === "harvest"
      ? `#/harvests/${current.id}?tab=lineage`
      : href(current.kind, current.id);
  return (
    <PropagationPath
      title="Ancestors"
      listLabel="Recorded upstream path"
      stages={[
        ...nodes.map((node) => [
          {
            type: labels[node.kind],
            label: node.label ?? fallbackLabels[node.kind],
            href: href(node.kind, node.id),
            state: node.lifecycle,
          },
        ]),
        [
          {
            type: `This ${labels[current.kind]}`,
            label: current.label ?? fallbackLabels[current.kind],
            href: currentHref,
            state: current.lifecycle,
            current: true,
          },
        ],
      ]}
    />
  );
}
