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

export type OccurrenceEvidence = components["schemas"]["OccurrenceEvidence"];
export function getCachedOccurrenceEvidence(
  identityId: string,
  signal?: AbortSignal,
): Promise<OccurrenceEvidence> {
  return requestJson(
    `/api/v1/botanical-identities/${encodeURIComponent(identityId)}/occurrence-map/cache`,
    { signal },
  );
}
export function refreshOccurrenceEvidence(
  identityId: string,
  csrf: string,
): Promise<OccurrenceEvidence> {
  return requestJson(
    `/api/v1/botanical-identities/${encodeURIComponent(identityId)}/occurrence-map/cache`,
    { method: "POST", headers: { "X-CSRF-Token": csrf } },
  );
}
export function clearOccurrenceEvidence(
  identityId: string,
  csrf: string,
): Promise<void> {
  return requestJson(
    `/api/v1/botanical-identities/${encodeURIComponent(identityId)}/occurrence-map/cache`,
    { method: "DELETE", headers: { "X-CSRF-Token": csrf } },
  );
}
