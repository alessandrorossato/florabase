import type { components } from "../api/schema";
import { requestJson } from "../auth/api";

export type EventCreate = components["schemas"]["EventCreate"];
export type EventKind = components["schemas"]["EventKind"];
export type EventResponse = components["schemas"]["EventResponse"];
export type EventUpdate = components["schemas"]["EventUpdate"];

export type EventTargetKind = "plant" | "group";

function targetPath(kind: EventTargetKind, id: string): string {
  const collection = kind === "plant" ? "plants" : "plant-groups";
  return `/api/v1/${collection}/${encodeURIComponent(id)}/events`;
}

export function listEvents(
  kind: EventTargetKind,
  id: string,
  signal?: AbortSignal,
): Promise<EventResponse[]> {
  return requestJson(targetPath(kind, id), { signal });
}

export function createEvent(
  kind: EventTargetKind,
  id: string,
  payload: EventCreate,
  csrfToken: string,
): Promise<EventResponse> {
  return requestJson(
    targetPath(kind, id),
    mutation("POST", payload, csrfToken),
  );
}

export function updateEvent(
  id: string,
  payload: EventUpdate,
  csrfToken: string,
): Promise<EventResponse> {
  return requestJson(
    `/api/v1/events/${encodeURIComponent(id)}`,
    mutation("PUT", payload, csrfToken),
  );
}

export function deleteEvent(id: string, csrfToken: string): Promise<void> {
  return requestJson(`/api/v1/events/${encodeURIComponent(id)}`, {
    method: "DELETE",
    headers: { "X-CSRF-Token": csrfToken },
  });
}

function mutation(
  method: "POST" | "PUT",
  payload: EventCreate | EventUpdate,
  csrfToken: string,
) {
  return {
    method,
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify(payload),
  };
}
