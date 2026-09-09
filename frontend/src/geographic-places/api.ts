import type { components } from "../api/schema";
import { ApiError, requestJson } from "../auth/api";

export type GeographicPlaceCreate =
  components["schemas"]["GeographicPlaceCreate"];
export type GeographicPlaceUpdate =
  components["schemas"]["GeographicPlaceUpdate"];
export type GeographicPlaceResponse =
  components["schemas"]["GeographicPlaceResponse"];
type HTTPValidationError = components["schemas"]["HTTPValidationError"];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function geographyValidationMessages(error: ApiError): string[] {
  if (!isRecord(error.body) || !Array.isArray(error.body.detail))
    return ["Check the local place details and try again."];
  const detail = error.body as HTTPValidationError;
  return Array.from(
    new Set(
      (detail.detail ?? []).map((item) => {
        const field = item.loc.at(-1);
        if (field === "name" && item.msg.toLowerCase().includes("blank"))
          return "Name cannot be blank.";
        if (field === "name" && item.type === "string_too_long")
          return "Name is too long.";
        if (field === "parent_id") return "Choose a parent geographic place.";
        return "Check the local place details and try again.";
      }),
    ),
  );
}

export function geographyConflictMessage(error: ApiError): string | null {
  if (!isRecord(error.body) || !isRecord(error.body.detail)) return null;
  const code = error.body.detail.code;
  if (code === "geographic_place_cycle")
    return "That parent would create a hierarchy cycle. Choose another place.";
  if (code === "geographic_place_active_descendants")
    return "Retire active descendants before retiring this place.";
  if (code === "geographic_place_retired_ancestor")
    return "Reactivate retired ancestors before making this place active.";
  if (code === "geographic_place_parent_not_found")
    return "The selected parent no longer exists. Refresh and choose again.";
  if (code === "canonical_geographic_place_immutable")
    return "Canonical geographic places are maintained from CLDR and cannot be changed here.";
  if (code === "geographic_place_has_native_ranges")
    return "Remove botanical native-range references before deleting this place.";
  return null;
}

export function listGeographicPlaces(
  signal?: AbortSignal,
): Promise<GeographicPlaceResponse[]> {
  return requestJson("/api/v1/geographic-places", { signal });
}

export function createGeographicPlace(
  payload: GeographicPlaceCreate,
  csrfToken: string,
): Promise<GeographicPlaceResponse> {
  return requestJson("/api/v1/geographic-places", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify(payload),
  });
}

export function updateGeographicPlace(
  id: string,
  payload: GeographicPlaceUpdate,
  csrfToken: string,
): Promise<GeographicPlaceResponse> {
  return requestJson(`/api/v1/geographic-places/${encodeURIComponent(id)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify(payload),
  });
}

export function setGeographicPlaceRetired(
  id: string,
  retired: boolean,
  csrfToken: string,
): Promise<GeographicPlaceResponse> {
  const action = retired ? "retire" : "reactivate";
  return requestJson(
    `/api/v1/geographic-places/${encodeURIComponent(id)}/${action}`,
    { method: "POST", headers: { "X-CSRF-Token": csrfToken } },
  );
}

export function deleteGeographicPlace(
  id: string,
  csrfToken: string,
): Promise<void> {
  return requestJson(`/api/v1/geographic-places/${encodeURIComponent(id)}`, {
    method: "DELETE",
    headers: { "X-CSRF-Token": csrfToken },
  });
}
