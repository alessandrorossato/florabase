import type { components } from "../api/schema";
import { requestJson, type ProtectedRequestCapability } from "../auth/api";

export type ProvenanceSiteCreate =
  components["schemas"]["ProvenanceSiteCreate"];
export type ProvenanceSiteUpdate =
  components["schemas"]["ProvenanceSiteUpdate"];
export type ProvenanceSiteResponse =
  components["schemas"]["ProvenanceSiteResponse"];

export function listProvenanceSites(
  capability: ProtectedRequestCapability,
  signal?: AbortSignal,
): Promise<ProvenanceSiteResponse[]> {
  return requestJson("/api/v1/provenance-sites", { capability, signal });
}

export function createProvenanceSite(
  payload: ProvenanceSiteCreate,
  csrfToken: string,
  capability: ProtectedRequestCapability,
): Promise<ProvenanceSiteResponse> {
  return requestJson("/api/v1/provenance-sites", {
    capability,
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify(payload),
  });
}

export function updateProvenanceSite(
  id: string,
  payload: ProvenanceSiteUpdate,
  csrfToken: string,
  capability: ProtectedRequestCapability,
): Promise<ProvenanceSiteResponse> {
  return requestJson(`/api/v1/provenance-sites/${encodeURIComponent(id)}`, {
    capability,
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify(payload),
  });
}

export function deleteProvenanceSite(
  id: string,
  csrfToken: string,
  capability: ProtectedRequestCapability,
): Promise<void> {
  return requestJson(`/api/v1/provenance-sites/${encodeURIComponent(id)}`, {
    capability,
    method: "DELETE",
    headers: { "X-CSRF-Token": csrfToken },
  });
}
