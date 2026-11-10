import { useCallback, useEffect, useState } from "react";

import type { components } from "../api/schema";
import { requestJson } from "../auth/api";

export type LineageResponse = components["schemas"]["LineageResponse"];
export type LineageNode = LineageResponse["subject"];
/** Collection resources with a recorded-lineage endpoint. */
export type LineageEndpoint =
  | "seed-lots"
  | "plants"
  | "plant-groups"
  | "vegetative-lots"
  | "propagation-attempts";

export type RecordedLineage =
  | { status: "loading" }
  | { status: "ready"; value: LineageResponse }
  | { status: "error" };

export const lineageKindLabels: Record<LineageNode["kind"], string> = {
  seed_lot: "Seed lot",
  sowing: "Sowing",
  plant: "Plant",
  plant_group: "Plant group",
  vegetative_lot: "Vegetative lot",
  propagation_attempt: "Rooting attempt",
};
export const lineageFallbackLabels: Record<LineageNode["kind"], string> = {
  seed_lot: "Unlabelled seed lot",
  sowing: "Unlabelled sowing",
  plant: "Unlabelled plant",
  plant_group: "Unlabelled plant group",
  vegetative_lot: "Unlabelled vegetative lot",
  propagation_attempt: "Unlabelled rooting attempt",
};

/** The record's own detail page. */
export function recordHref(kind: LineageNode["kind"], id: string) {
  if (kind === "vegetative_lot") return `#/cuttings/lots/${id}`;
  if (kind === "propagation_attempt") return `#/cuttings/attempts/${id}`;
  const route =
    kind === "seed_lot"
      ? "seeds"
      : kind === "plant_group"
        ? "plant-groups"
        : `${kind}s`;
  return `#/${route}/${id}`;
}

export function lineageHref(kind: LineageNode["kind"], id: string) {
  return `${recordHref(kind, id)}?tab=lineage`;
}

/** The Material ancestry explorer centred on one record. */
export function ancestryHref(kind: LineageNode["kind"], id: string) {
  return `#/lineage/${kind}/${id}`;
}

/**
 * The recorded relationship between two adjacent steps, named only from their kinds (every
 * step is an explicitly recorded source, so the pair determines the relationship).
 */
export const lineageVerbs: Partial<Record<string, string>> = {
  "seed_lot>sowing": "sown as",
  "sowing>plant": "grown into",
  "sowing>plant_group": "grown into",
  "plant_group>plant": "extracted",
  "plant>seed_lot": "produced",
  "plant_group>seed_lot": "produced",
};

/**
 * Explicit upstream path, oldest first. The API walks one recorded source per record,
 * nearest-first; only that path is reversed and de-duplicated. Nothing is inferred.
 */
export function upstreamPath(value: LineageResponse): LineageNode[] {
  const seen = new Set<string>();
  return [...value.ancestors].reverse().filter((node) => {
    const key = `${node.kind}:${node.id}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

/** Loads one record's recorded lineage; stale responses for another record are ignored. */
export function useRecordedLineage(
  kind: LineageEndpoint,
  id: string,
): [RecordedLineage, () => void] {
  const key = `${kind}:${id}`;
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<
    { key: string; attempt: number } & RecordedLineage
  >({ status: "loading", key, attempt });
  useEffect(() => {
    const controller = new AbortController();
    void requestJson<LineageResponse>(`/api/v1/${kind}/${id}/lineage`, {
      signal: controller.signal,
    })
      .then((value) => {
        if (!controller.signal.aborted)
          setState({ status: "ready", key, attempt, value });
      })
      .catch(() => {
        if (!controller.signal.aborted)
          setState({ status: "error", key, attempt });
      });
    return () => {
      controller.abort();
    };
  }, [id, kind, key, attempt]);
  const retry = useCallback(() => {
    setAttempt((value) => value + 1);
  }, []);
  if (state.key !== key || state.attempt !== attempt)
    return [{ status: "loading" }, retry];
  return [state, retry];
}
