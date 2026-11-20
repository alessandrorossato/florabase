import type { components } from "../api/schema";
import { requestJson, type ProtectedRequestCapability } from "../auth/api";

export type OccurrenceMapSummary =
  components["schemas"]["OccurrenceMapSummary"];

export function getOccurrenceMapSummary(
  identityId: string,
  capability: ProtectedRequestCapability,
  signal?: AbortSignal,
): Promise<OccurrenceMapSummary> {
  return requestJson(
    `/api/v1/botanical-identities/${encodeURIComponent(identityId)}/occurrence-map/summary`,
    { capability, signal },
  );
}

export function occurrenceTileUrl(identityId: string): string {
  return `/api/v1/botanical-identities/${encodeURIComponent(identityId)}/occurrence-map/tiles/{z}/{x}/{y}.png`;
}

export type OccurrenceEvidence = components["schemas"]["OccurrenceEvidence"];
export function getCachedOccurrenceEvidence(
  identityId: string,
  capability: ProtectedRequestCapability,
  signal?: AbortSignal,
): Promise<OccurrenceEvidence> {
  return requestJson(
    `/api/v1/botanical-identities/${encodeURIComponent(identityId)}/occurrence-map/cache`,
    { capability, signal },
  );
}
export function refreshOccurrenceEvidence(
  identityId: string,
  csrf: string,
  capability: ProtectedRequestCapability,
): Promise<OccurrenceEvidence> {
  return requestJson(
    `/api/v1/botanical-identities/${encodeURIComponent(identityId)}/occurrence-map/cache`,
    { capability, method: "POST", headers: { "X-CSRF-Token": csrf } },
  );
}
export function clearOccurrenceEvidence(
  identityId: string,
  csrf: string,
  capability: ProtectedRequestCapability,
): Promise<void> {
  return requestJson(
    `/api/v1/botanical-identities/${encodeURIComponent(identityId)}/occurrence-map/cache`,
    { capability, method: "DELETE", headers: { "X-CSRF-Token": csrf } },
  );
}
