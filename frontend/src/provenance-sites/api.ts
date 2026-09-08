import type { components } from "../api/schema";
import { requestJson } from "../auth/api";

export type ProvenanceSiteCreate =
  components["schemas"]["ProvenanceSiteCreate"];
export type ProvenanceSiteUpdate =
  components["schemas"]["ProvenanceSiteUpdate"];
export type ProvenanceSiteResponse =
  components["schemas"]["ProvenanceSiteResponse"];

export function listProvenanceSites(
  signal?: AbortSignal,
): Promise<ProvenanceSiteResponse[]> {
  return requestJson("/api/v1/provenance-sites", { signal });
}

export function createProvenanceSite(
  payload: ProvenanceSiteCreate,
  csrfToken: string,
): Promise<ProvenanceSiteResponse> {
  return requestJson("/api/v1/provenance-sites", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify(payload),
  });
}

export function updateProvenanceSite(
  id: string,
  payload: ProvenanceSiteUpdate,
  csrfToken: string,
): Promise<ProvenanceSiteResponse> {
  return requestJson(`/api/v1/provenance-sites/${encodeURIComponent(id)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify(payload),
  });
}

export function deleteProvenanceSite(
  id: string,
  csrfToken: string,
): Promise<void> {
  return requestJson(`/api/v1/provenance-sites/${encodeURIComponent(id)}`, {
    method: "DELETE",
    headers: { "X-CSRF-Token": csrfToken },
  });
}
