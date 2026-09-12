import type { components } from "../api/schema";
import { requestJson } from "../auth/api";

export type OccurrenceMapSummary =
  components["schemas"]["OccurrenceMapSummary"];

export function getOccurrenceMapSummary(
  identityId: string,
  signal?: AbortSignal,
): Promise<OccurrenceMapSummary> {
  return requestJson(
    `/api/v1/botanical-identities/${encodeURIComponent(identityId)}/occurrence-map/summary`,
    { signal },
  );
}

export function occurrenceTileUrl(identityId: string): string {
  return `/api/v1/botanical-identities/${encodeURIComponent(identityId)}/occurrence-map/tiles/{z}/{x}/{y}.png`;
}
