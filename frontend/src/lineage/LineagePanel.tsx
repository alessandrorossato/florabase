import { useCallback, useEffect, useId, useState } from "react";

import type { components } from "../api/schema";
import { ApiError, isExpectedAuthCancellation, requestJson } from "../auth/api";
import { useAuth } from "../auth/context";
import { DetailEmptyState } from "../components/DetailEmptyState";
import { LifecycleStatus } from "../components/WorkspaceUI";
import { PropagationPath } from "../propagation/PropagationPath";
import { InfoDisclosure } from "../components/ContextualHelp";
import {
  ancestryHref,
  lineageFallbackLabels as fallbackLabels,
  lineageHref as href,
  lineageKindLabels as labels,
  lineageVerbs,
  upstreamPath,
  useRecordedLineage,
  type LineageEndpoint,
  type LineageResponse,
} from "./useRecordedLineage";
import "./lineage-panel.css";

type AncestryChildren = components["schemas"]["AncestryChildren"];
type Descendants =
  | { status: "loading" }
  | { status: "ready"; value: AncestryChildren }
  | { status: "error" };
const DESCENDANT_PAGE = 25;

const ancestryKinds = {
  "seed-lots": "seed_lot",
  plants: "plant",
  "plant-groups": "plant_group",
  "vegetative-lots": "vegetative_lot",
  "propagation-attempts": "propagation_attempt",
} as const;

/**
 * Direct recorded descendants of one record (first page), read from the ancestry explorer's
 * children endpoint (no upstream walk); stale responses for another record are ignored.
 */
function useDirectDescendants(
  kind: LineageEndpoint,
  id: string,
): [Descendants, () => void] {
  const auth = useAuth();
  const { capability, sessionExpired } = auth;
  const authorized =
    auth.state.status === "authenticated" && capability.isAuthorized();
  const key = `${kind}:${id}`;
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<
    { key: string; attempt: number } & Descendants
  >({ status: "loading", key, attempt });
  useEffect(() => {
    if (!authorized) return;
    const controller = new AbortController();
    void requestJson<AncestryChildren>(
      `/api/v1/lineage/${ancestryKinds[kind]}/${id}/children?offset=0&limit=${String(DESCENDANT_PAGE)}`,
      { capability, signal: controller.signal },
    )
      .then((value) => {
        if (!controller.signal.aborted)
          setState({ status: "ready", key, attempt, value });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || isExpectedAuthCancellation(error))
          return;
        if (error instanceof ApiError && error.status === 401) {
          sessionExpired();
          return;
        }
        setState({ status: "error", key, attempt });
      });
    return () => {
      controller.abort();
    };
  }, [attempt, authorized, capability, id, key, kind, sessionExpired]);
  const retry = useCallback(() => {
    setAttempt((value) => value + 1);
  }, []);
  if (state.key !== key || state.attempt !== attempt)
    return [{ status: "loading" }, retry];
  return [state, retry];
}

/**
 * The record's Lineage tab: the explorer entry point, its recorded upstream path, then what
 * was recorded from it. A record that starts a line (a purchased Seed lot) has no upstream
 * path but can still have recorded descendants.
 */
export function LineagePanel({
  kind,
  id,
}: {
  kind: LineageEndpoint;
  id: string;
}) {
  const [upstream, retryUpstream] = useRecordedLineage(kind, id);
  const [descendants, retryDescendants] = useDirectDescendants(kind, id);
  const explorer = ancestryHref(ancestryKinds[kind], id);
  let body;
  if (upstream.status === "loading" || descendants.status === "loading")
    body = <p role="status">Loading recorded lineage…</p>;
  else if (
    upstream.status === "ready" &&
    descendants.status === "ready" &&
    upstream.value.ancestors.length === 0 &&
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
        ) : upstream.value.ancestors.length > 0 ? (
          <RecordedUpstream kind={kind} value={upstream.value} />
        ) : (
          <p className="lineage-panel__start">
            No recorded source: this record starts its line.
          </p>
        )}
        {descendants.status === "error" ? (
          <div className="notice notice--error" role="alert">
            <p>Florabase could not load what was recorded from this record.</p>
            <button type="button" onClick={retryDescendants}>
              Retry recorded descendants
            </button>
          </div>
        ) : (
          <RecordedDescendants
            parentKind={ancestryKinds[kind]}
            value={descendants.value}
            explorer={explorer}
          />
        )}
      </>
    );
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
  parentKind: (typeof ancestryKinds)[LineageEndpoint];
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
  kind,
  value,
}: {
  kind: LineageEndpoint;
  value: LineageResponse;
}) {
  if (kind !== "seed-lots") {
    // The API walks nearest-first. Reverse only that explicit path for material flow.
    const nodes = upstreamPath(value);
    const subject = value.subject;
    return (
      <PropagationPath
        title="Recorded lineage"
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
              type: `This ${labels[subject.kind]}`,
              label: subject.label ?? fallbackLabels[subject.kind],
              href: href(subject.kind, subject.id),
              state: subject.lifecycle,
              current: true,
            },
          ],
        ]}
      />
    );
  }
  return (
    <div>
      <InfoDisclosure label="How this path is recorded">
        <p>
          Only explicit collection relationships are shown. A shared Botanical
          identity does not imply lineage.
        </p>
      </InfoDisclosure>
      <ol className="lineage-list" aria-label="Recorded upstream path">
        {value.ancestors.map((node) => (
          <li key={`${node.kind}:${node.id}`}>
            <span className="record-state">{labels[node.kind]}</span>{" "}
            <a href={href(node.kind, node.id)}>
              {node.label ?? fallbackLabels[node.kind]}
            </a>{" "}
            <span className="record-state">{node.lifecycle}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
