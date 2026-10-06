import type { components } from "../api/schema";
import { requestJson } from "../auth/api";
import type { Surface } from "./state";

export type SavedView = components["schemas"]["SavedViewResponse"];
export type SavedViewCreate = components["schemas"]["SavedViewCreate"];
export type SavedViewUpdate = components["schemas"]["SavedViewUpdate"];
export function listSavedViews(
  surface?: Surface,
  signal?: AbortSignal,
  offset = 0,
): Promise<SavedView[]> {
  const params = new URLSearchParams();
  if (surface) params.set("surface", surface);
  if (offset) params.set("offset", String(offset));
  return requestJson(`/api/v1/saved-views${params.size ? `?${params}` : ""}`, {
    signal,
  });
}
function mutation(
  method: string,
  token: string,
  value?: SavedViewCreate | SavedViewUpdate,
): RequestInit {
  return {
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
): Promise<SavedView> {
  return requestJson("/api/v1/saved-views", mutation("POST", token, value));
}
export function updateSavedView(
  id: string,
  value: SavedViewUpdate,
  token: string,
): Promise<SavedView> {
  return requestJson(
    `/api/v1/saved-views/${encodeURIComponent(id)}`,
    mutation("PATCH", token, value),
  );
}
export function deleteSavedView(id: string, token: string): Promise<void> {
  return requestJson(
    `/api/v1/saved-views/${encodeURIComponent(id)}`,
    mutation("DELETE", token),
  );
}
