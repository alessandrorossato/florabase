import type { components } from "../api/schema";
import {
  requestJson,
  type ProtectedRequestCapability,
  type ProtectedRequestInit,
} from "../auth/api";

export type EventCreate = components["schemas"]["EventCreate"];
export type EventKind = components["schemas"]["EventKind"];
export type EventResponse = components["schemas"]["EventResponse"];
export type EventUpdate = components["schemas"]["EventUpdate"];

export type JournalRootingObservation =
  components["schemas"]["JournalRootingObservation"];

export function listJournalRootingObservations(
  capability: ProtectedRequestCapability,
  signal: AbortSignal,
) {
  return requestJson<JournalRootingObservation[]>(
    "/api/v1/events/rooting-observations",
    { capability, signal },
  );
}

export type EventTargetKind = "plant" | "group";

function targetPath(kind: EventTargetKind, id: string): string {
  const collection = kind === "plant" ? "plants" : "plant-groups";
  return `/api/v1/${collection}/${encodeURIComponent(id)}/events`;
}

export function listEvents(
  kind: EventTargetKind,
  id: string,
  capability: ProtectedRequestCapability,
  signal?: AbortSignal,
): Promise<EventResponse[]> {
  return requestJson(targetPath(kind, id), { capability, signal });
}

export function createEvent(
  kind: EventTargetKind,
  id: string,
  payload: EventCreate,
  csrfToken: string,
  capability: ProtectedRequestCapability,
): Promise<EventResponse> {
  return requestJson(
    targetPath(kind, id),
    mutation("POST", payload, csrfToken, capability),
  );
}

export function updateEvent(
  id: string,
  payload: EventUpdate,
  csrfToken: string,
  capability: ProtectedRequestCapability,
): Promise<EventResponse> {
  return requestJson(
    `/api/v1/events/${encodeURIComponent(id)}`,
    mutation("PUT", payload, csrfToken, capability),
  );
}

export function deleteEvent(
  id: string,
  csrfToken: string,
  capability: ProtectedRequestCapability,
): Promise<void> {
  return requestJson(`/api/v1/events/${encodeURIComponent(id)}`, {
    capability,
    method: "DELETE",
    headers: { "X-CSRF-Token": csrfToken },
  });
}

function mutation(
  method: "POST" | "PUT",
  payload: EventCreate | EventUpdate,
  csrfToken: string,
  capability: ProtectedRequestCapability,
): ProtectedRequestInit {
  return {
    capability,
    method,
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify(payload),
  };
}
