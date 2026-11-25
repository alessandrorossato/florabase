import type { components } from "../api/schema";
import { requestJson, type ProtectedRequestCapability } from "../auth/api";
export type ApplicationSettings =
  components["schemas"]["ApplicationSettingsValue"];
export type SystemReferences =
  components["schemas"]["SystemReferencesResponse"];
export type ReferenceSetupIndexStatus =
  components["schemas"]["ReferenceSetupIndexStatus"];

export function getSystemReferences(
  capability: ProtectedRequestCapability,
  signal?: AbortSignal,
): Promise<SystemReferences> {
  return requestJson("/api/v1/system/references", { capability, signal });
}

export function getApplicationSettings(
  capability: ProtectedRequestCapability,
  signal?: AbortSignal,
): Promise<ApplicationSettings> {
  return requestJson("/api/v1/application-settings", { capability, signal });
}
export function saveApplicationSettings(
  value: ApplicationSettings,
  token: string,
  capability: ProtectedRequestCapability,
): Promise<ApplicationSettings> {
  return requestJson("/api/v1/application-settings", {
    capability,
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": token },
    body: JSON.stringify(value),
  });
}

// Both General and the contextual Labels dialog edit the same persisted preference.
export async function savePublicQrBaseUrl(
  value: string,
  token: string,
  capability: ProtectedRequestCapability,
): Promise<ApplicationSettings> {
  const latest = await getApplicationSettings(capability);
  return saveApplicationSettings(
    { ...latest, public_qr_base_url: value.trim() || null },
    token,
    capability,
  );
}
export const publicQrValidationMessage =
  "Use an HTTP(S) scheme and authority only, with no credentials, path, query or fragment (maximum 200 characters).";
