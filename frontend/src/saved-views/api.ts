import type { components } from "../api/schema";
import {
  requestJson,
  type ProtectedRequestCapability,
  type ProtectedRequestInit,
} from "../auth/api";
import type { Surface } from "./state";

export type SavedView = components["schemas"]["SavedViewResponse"];
export type SavedViewCreate = components["schemas"]["SavedViewCreate"];
export type SavedViewUpdate = components["schemas"]["SavedViewUpdate"];
export function listSavedViews(
  surface: Surface | undefined,
  capability: ProtectedRequestCapability,
  signal?: AbortSignal,
  offset = 0,
): Promise<SavedView[]> {
  const params = new URLSearchParams();
  if (surface) params.set("surface", surface);
  if (offset) params.set("offset", String(offset));
  return requestJson(`/api/v1/saved-views${params.size ? `?${params}` : ""}`, {
    capability,
    signal,
  });
}
function mutation(
  method: string,
  token: string,
  capability: ProtectedRequestCapability,
  value?: SavedViewCreate | SavedViewUpdate,
): ProtectedRequestInit {
  return {
    capability,
    method,
    headers: {
      "X-CSRF-Token": token,
      ...(value ? { "Content-Type": "application/json" } : {}),
    },
    ...(value ? { body: JSON.stringify(value) } : {}),
  };
}
export function createSavedView(
  value: SavedViewCreate,
  token: string,
  capability: ProtectedRequestCapability,
): Promise<SavedView> {
  return requestJson(
    "/api/v1/saved-views",
    mutation("POST", token, capability, value),
  );
}
export function updateSavedView(
  id: string,
  value: SavedViewUpdate,
  token: string,
  capability: ProtectedRequestCapability,
): Promise<SavedView> {
  return requestJson(
    `/api/v1/saved-views/${encodeURIComponent(id)}`,
    mutation("PATCH", token, capability, value),
  );
}
export function deleteSavedView(
  id: string,
  token: string,
  capability: ProtectedRequestCapability,
): Promise<void> {
  return requestJson(
    `/api/v1/saved-views/${encodeURIComponent(id)}`,
    mutation("DELETE", token, capability),
  );
}
