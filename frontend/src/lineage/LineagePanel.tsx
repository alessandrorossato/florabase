import { DetailEmptyState } from "../components/DetailEmptyState";
import { PropagationPath } from "../propagation/PropagationPath";
import { InfoDisclosure } from "../components/ContextualHelp";
import {
  ancestryHref,
  lineageFallbackLabels as fallbackLabels,
  lineageHref as href,
  lineageKindLabels as labels,
  upstreamPath,
  useRecordedLineage,
  type LineageEndpoint,
} from "./useRecordedLineage";

const ancestryKinds = {
  "seed-lots": "seed_lot",
  plants: "plant",
  "plant-groups": "plant_group",
} as const;

/** The record's Lineage tab: the explorer entry point, then its recorded upstream path. */
export function LineagePanel({
  kind,
  id,
}: {
  kind: LineageEndpoint;
  id: string;
}) {
  return (
    <>
      <p className="lineage-explore">
        <a href={ancestryHref(ancestryKinds[kind], id)}>
          Explore material ancestry
        </a>
      </p>
      <RecordedUpstream kind={kind} id={id} />
    </>
  );
}

function RecordedUpstream({ kind, id }: { kind: LineageEndpoint; id: string }) {
  const [state, retry] = useRecordedLineage(kind, id);
  if (state.status === "loading")
    return <p role="status">Loading recorded lineage…</p>;
  if (state.status === "error")
    return (
      <div className="notice notice--error" role="alert">
        <p>Florabase could not load recorded lineage.</p>
        <button type="button" onClick={retry}>
          Retry lineage
        </button>
      </div>
    );
  if (state.value.ancestors.length === 0)
    return <DetailEmptyState>No recorded lineage.</DetailEmptyState>;
  if (kind !== "seed-lots") {
    // The API walks nearest-first. Reverse only that explicit path for material flow.
    const nodes = upstreamPath(state.value);
    const subject = state.value.subject;
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
        {state.value.ancestors.map((node) => (
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
