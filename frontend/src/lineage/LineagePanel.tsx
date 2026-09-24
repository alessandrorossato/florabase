import { useEffect, useState } from "react";

import type { components } from "../api/schema";
import { requestJson } from "../auth/api";
import { InfoDisclosure } from "../components/ContextualHelp";

type LineageResponse = components["schemas"]["LineageResponse"];
type Kind = "seed-lots" | "sowings" | "plants" | "plant-groups";

const labels: Record<string, string> = {
  seed_lot: "Seed lot",
  sowing: "Sowing",
  plant: "Plant",
  plant_group: "Plant group",
};
const fallbackLabels: Record<string, string> = {
  seed_lot: "Unlabelled seed lot",
  sowing: "Unlabelled sowing",
  plant: "Unlabelled plant",
  plant_group: "Unlabelled plant group",
};

function href(kind: string, id: string) {
  const route =
    kind === "seed_lot"
      ? "seeds"
      : kind === "plant_group"
        ? "plant-groups"
        : `${kind}s`;
  return `#/${route}/${id}?tab=lineage`;
}

export function LineagePanel({ kind, id }: { kind: Kind; id: string }) {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<
    | { status: "loading" }
    | { status: "ready"; value: LineageResponse }
    | { status: "error" }
  >({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    void requestJson<LineageResponse>(`/api/v1/${kind}/${id}/lineage`, {
      signal: controller.signal,
    })
      .then((value) => {
        setState({ status: "ready", value });
      })
      .catch(() => {
        if (!controller.signal.aborted) setState({ status: "error" });
      });
    return () => {
      controller.abort();
    };
  }, [id, kind, attempt]);

  if (state.status === "loading")
    return <p role="status">Loading recorded lineage…</p>;
  if (state.status === "error")
    return (
      <div className="notice notice--error" role="alert">
        <p>Florabase could not load recorded lineage.</p>
        <button
          type="button"
          onClick={() => {
            setState({ status: "loading" });
            setAttempt((value) => value + 1);
          }}
        >
          Retry lineage
        </button>
      </div>
    );
  if (state.value.ancestors.length === 0)
    return (
      <div className="empty-state">
        <p>No explicit upstream lineage is recorded.</p>
      </div>
    );
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
            </a>
          </li>
        ))}
      </ol>
    </div>
  );
}
