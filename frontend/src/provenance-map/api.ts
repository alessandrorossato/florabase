import type { components } from "../api/schema";
import { requestJson } from "../auth/api";

export type ProvenanceMapResponse =
  components["schemas"]["ProvenanceMapResponse"];
export type ProvenanceMapSite = components["schemas"]["ProvenanceMapSite"];
export type ProvenanceMapRecord = components["schemas"]["ProvenanceMapRecord"];

export function getCollectionProvenanceMap(
  signal?: AbortSignal,
): Promise<ProvenanceMapResponse> {
  return requestJson("/api/v1/provenance-sites/map", { signal });
}
