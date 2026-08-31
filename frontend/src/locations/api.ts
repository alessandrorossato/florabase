import type { components } from "../api/schema";
import { ApiError, requestJson } from "../auth/api";

export type LocationCreate = components["schemas"]["LocationCreate"];
export type LocationUpdate = components["schemas"]["LocationUpdate"];
export type LocationResponse = components["schemas"]["LocationResponse"];
type HTTPValidationError = components["schemas"]["HTTPValidationError"];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function locationValidationMessages(error: ApiError): string[] {
  if (!isRecord(error.body) || !Array.isArray(error.body.detail))
    return ["Check the location details and try again."];
  const detail = error.body as HTTPValidationError;
  return Array.from(
    new Set(
      (detail.detail ?? []).map((item) => {
        const field = item.loc.at(-1);
        if (field === "name" && item.msg.toLowerCase().includes("blank"))
          return "Name cannot be blank.";
        if (
          field === "name" &&
          item.msg.toLowerCase().includes("control character")
        )
          return "Name contains an unsupported character.";
        if (field === "name" && item.type === "string_too_long")
          return "Name is too long.";
        return "Check the location details and try again.";
      }),
    ),
  );
}

export function locationConflictMessage(error: ApiError): string | null {
  if (!isRecord(error.body) || !isRecord(error.body.detail)) return null;
  const code = error.body.detail.code;
  if (code === "location_cycle")
    return "That parent would create a hierarchy cycle. Choose another location.";
  if (code === "location_active_descendants")
    return "Retire active descendants before retiring this location.";
  if (code === "location_retired_ancestor")
    return "Reactivate retired ancestors before making this location active.";
  if (code === "location_parent_not_found")
    return "The selected parent no longer exists. Refresh the directory and choose again.";
  return null;
}

export function listLocations(
  signal?: AbortSignal,
): Promise<LocationResponse[]> {
  return requestJson("/api/v1/locations", { signal });
}

export function createLocation(
  payload: LocationCreate,
  csrfToken: string,
): Promise<LocationResponse> {
  return requestJson("/api/v1/locations", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify(payload),
  });
}

export function updateLocation(
  id: string,
  payload: LocationUpdate,
  csrfToken: string,
): Promise<LocationResponse> {
  return requestJson(`/api/v1/locations/${encodeURIComponent(id)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify(payload),
  });
}

export function setLocationRetired(
  id: string,
  retired: boolean,
  csrfToken: string,
): Promise<LocationResponse> {
  const action = retired ? "retire" : "reactivate";
  return requestJson(`/api/v1/locations/${encodeURIComponent(id)}/${action}`, {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
  });
}
