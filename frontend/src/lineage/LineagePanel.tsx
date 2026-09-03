import { useEffect, useState } from "react";

import type { components } from "../api/schema";
import { requestJson } from "../auth/api";

type LineageResponse = components["schemas"]["LineageResponse"];
type Kind = "seed-lots" | "sowings" | "plants" | "plant-groups";

const labels: Record<string, string> = {
  seed_lot: "Seed lot",
  sowing: "Sowing",
  plant: "Plant",
  plant_group: "Plant group",
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
  }, [id, kind]);

  if (state.status === "loading")
    return <p role="status">Loading recorded lineage…</p>;
  if (state.status === "error")
    return (
      <div className="notice notice--error" role="alert">
        Florabase could not load recorded lineage.
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
      <p className="field-help">
        Only explicit collection provenance is shown. A shared Botanical
        identity does not imply lineage.
      </p>
      <ol className="lineage-list">
        {state.value.ancestors.map((node) => (
          <li key={`${node.kind}:${node.id}`}>
            <span className="record-state">{labels[node.kind]}</span>{" "}
            <a href={href(node.kind, node.id)}>
              {node.label ??
                ("botanical_identity" in node
                  ? node.botanical_identity.display_label
                  : `Unlabelled ${labels[node.kind]}`)}
            </a>
          </li>
        ))}
      </ol>
    </div>
  );
}
