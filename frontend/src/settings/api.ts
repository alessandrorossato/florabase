import type { components } from "../api/schema";
import { requestJson } from "../auth/api";
export type ApplicationSettings =
  components["schemas"]["ApplicationSettingsValue"];
export function getApplicationSettings(
  signal?: AbortSignal,
): Promise<ApplicationSettings> {
  return requestJson("/api/v1/application-settings", { signal });
}
export function saveApplicationSettings(
  value: ApplicationSettings,
  token: string,
): Promise<ApplicationSettings> {
  return requestJson("/api/v1/application-settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": token },
    body: JSON.stringify(value),
  });
}

// Both General and the contextual Labels dialog edit the same persisted preference.
export async function savePublicQrBaseUrl(
  value: string,
  token: string,
): Promise<ApplicationSettings> {
  const latest = await getApplicationSettings();
  return saveApplicationSettings(
    { ...latest, public_qr_base_url: value.trim() || null },
    token,
  );
}
export const publicQrValidationMessage =
  "Use an HTTP(S) scheme and authority only, with no credentials, path, query or fragment (maximum 200 characters).";
