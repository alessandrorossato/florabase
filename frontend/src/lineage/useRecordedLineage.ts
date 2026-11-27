import { useCallback, useEffect, useState } from "react";

import type { components } from "../api/schema";
import { ApiError, isExpectedAuthCancellation, requestJson } from "../auth/api";
import { useAuth } from "../auth/context";

export type LineageResponse = components["schemas"]["LineageResponse"];
export type LineageNode = LineageResponse["subject"];
export type AncestryChildren = components["schemas"]["AncestryChildren"];
export type AncestryKind = LineageNode["kind"];
/** Collection resources with a recorded-lineage endpoint. */
export type LineageEndpoint =
  | "seed-lots"
  | "plants"
  | "plant-groups"
  | "vegetative-lots"
  | "propagation-attempts";

export const ancestryKinds: Record<LineageEndpoint, AncestryKind> = {
  "seed-lots": "seed_lot",
  plants: "plant",
  "plant-groups": "plant_group",
  "vegetative-lots": "vegetative_lot",
  "propagation-attempts": "propagation_attempt",
};

export type DirectDescendants =
  | { status: "loading" }
  | { status: "ready"; value: AncestryChildren }
  | { status: "error" };

export const DESCENDANT_PAGE = 25;

export type RecordedLineage =
  | { status: "loading" }
  | { status: "ready"; value: LineageResponse }
  | { status: "error" };

export const lineageKindLabels: Record<
  LineageNode["kind"] | "harvest",
  string
> = {
  seed_lot: "Seed lot",
  sowing: "Sowing",
  plant: "Plant",
  plant_group: "Plant group",
  vegetative_lot: "Vegetative lot",
  propagation_attempt: "Rooting attempt",
  harvest: "Harvest",
};
export const lineageFallbackLabels: Record<
  LineageNode["kind"] | "harvest",
  string
> = {
  seed_lot: "Unlabelled seed lot",
  sowing: "Unlabelled sowing",
  plant: "Unlabelled plant",
  plant_group: "Unlabelled plant group",
  vegetative_lot: "Unlabelled vegetative lot",
  propagation_attempt: "Unlabelled rooting attempt",
  harvest: "Unlabelled harvest",
};

const pluralKindLabels: Record<LineageNode["kind"], [string, string]> = {
  seed_lot: ["seed lot", "seed lots"],
  sowing: ["sowing", "sowings"],
  plant: ["plant", "plants"],
  plant_group: ["plant group", "plant groups"],
  vegetative_lot: ["vegetative lot", "vegetative lots"],
  propagation_attempt: ["attempt", "attempts"],
};

/** Direct recorded descendants grouped by kind, in first-seen order: "2 sowings". */
export function descendantCounts(
  children: AncestryChildren,
): { kind: LineageNode["kind"]; count: number; label: string }[] {
  const counts = new Map<LineageNode["kind"], number>();
  for (const item of children.items) {
    counts.set(item.record.kind, (counts.get(item.record.kind) ?? 0) + 1);
  }
  return [...counts].map(([kind, count]) => {
    const [singular, plural] = pluralKindLabels[kind];
    return {
      kind,
      count,
      label: `${String(count)} ${count === 1 ? singular : plural}`,
    };
  });
}

/** Compact summary for LineageStrip, e.g. "2 sowings" or "1 plant, 1 plant group". */
export function descendantSummaryLabel(
  children: AncestryChildren,
): string | null {
  if (!children.total) return null;
  if (children.items.length < children.total) {
    return `${String(children.total)} recorded from this`;
  }
  const parts = descendantCounts(children).map(({ label }) => label);
  return parts.length ? parts.join(", ") : null;
}

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
  const href = recordHref(kind, id);
  return kind === "vegetative_lot" || kind === "propagation_attempt"
    ? href
    : `${href}?tab=lineage`;
}

/** The Material ancestry explorer centred on one record. */
export function ancestryHref(kind: LineageNode["kind"], id: string) {
  return `#/lineage/${kind}/${id}`;
}

/** Recorded lineage across every record of one Botanical identity. */
export function identityLineageHref(identityId: string) {
  return `#/lineage/identity/${identityId}`;
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
  "plant>harvest": "harvested as",
  "plant_group>harvest": "harvested as",
  "harvest>seed_lot": "converted to",
  "plant>vegetative_lot": "provided cuttings for",
  "plant_group>vegetative_lot": "provided cuttings for",
  "vegetative_lot>propagation_attempt": "struck in",
  "propagation_attempt>plant": "rooted into",
  "propagation_attempt>plant_group": "rooted into",
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
  const auth = useAuth();
  const { capability, sessionExpired } = auth;
  const authorized =
    auth.state.status === "authenticated" && capability.isAuthorized();
  const key = `${kind}:${id}`;
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<
    { key: string; attempt: number } & RecordedLineage
  >({ status: "loading", key, attempt });
  useEffect(() => {
    if (!authorized) return;
    const controller = new AbortController();
    void requestJson<LineageResponse>(`/api/v1/${kind}/${id}/lineage`, {
      capability,
      signal: controller.signal,
    })
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
 * Direct recorded descendants of one record (first page), read from the ancestry explorer's
 * children endpoint (no upstream walk); stale responses for another record are ignored.
 */
export function useDirectDescendants(
  kind: AncestryKind | null,
  id: string | null,
): [DirectDescendants, () => void] {
  const auth = useAuth();
  const { capability, sessionExpired } = auth;
  const authorized =
    auth.state.status === "authenticated" && capability.isAuthorized();
  const enabled = Boolean(kind && id);
  const key = enabled ? `${String(kind)}:${String(id)}` : "disabled";
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<
    { key: string; attempt: number } & DirectDescendants
  >({ status: "loading", key, attempt });
  useEffect(() => {
    if (!authorized || !kind || !id) return;
    const controller = new AbortController();
    void requestJson<AncestryChildren>(
      `/api/v1/lineage/${kind}/${id}/children?offset=0&limit=${String(DESCENDANT_PAGE)}`,
      { capability, signal: controller.signal },
    )
      .then((value) => {
        if (!controller.signal.aborted) {
          if (
            typeof value === "object" &&
            // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
            value !== null &&
            Array.isArray(value.items) &&
            typeof value.total === "number"
          )
            setState({ status: "ready", key, attempt, value });
          else
            setState({
              status: "ready",
              key,
              attempt,
              value: { items: [], total: 0, offset: 0, limit: DESCENDANT_PAGE },
            });
        }
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
  if (!enabled)
    return [
      {
        status: "ready",
        value: { items: [], total: 0, offset: 0, limit: DESCENDANT_PAGE },
      },
      retry,
    ];
  if (state.key !== key || state.attempt !== attempt)
    return [{ status: "loading" }, retry];
  return [state, retry];
}
