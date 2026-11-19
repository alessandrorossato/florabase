import type { components } from "../api/schema";
import { requestJson, type ProtectedRequestCapability } from "../auth/api";

export type DashboardResponse = components["schemas"]["DashboardResponse"];
export type BotanicalIdentityCollectionResponse =
  components["schemas"]["BotanicalIdentityCollectionResponse"];
export type EventResponse = components["schemas"]["EventResponse"];

export function getDashboard(
  capability: ProtectedRequestCapability,
  signal?: AbortSignal,
  today?: string,
): Promise<DashboardResponse> {
  return requestJson<DashboardResponse>(
    `/api/v1/dashboard${today ? `?today=${encodeURIComponent(today)}` : ""}`,
    { capability, signal },
  );
}

export function listGlobalEvents(
  capability: ProtectedRequestCapability,
  signal?: AbortSignal,
): Promise<EventResponse[]> {
  return requestJson<EventResponse[]>("/api/v1/events", { capability, signal });
}

export function getIdentityCollection(
  id: string,
  capability: ProtectedRequestCapability,
  signal?: AbortSignal,
): Promise<BotanicalIdentityCollectionResponse> {
  return requestJson<BotanicalIdentityCollectionResponse>(
    `/api/v1/botanical-identities/${id}/collection`,
    { capability, signal },
  );
}
