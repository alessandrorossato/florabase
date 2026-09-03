import type { components } from "../api/schema";
import { requestJson } from "../auth/api";

export type DashboardResponse = components["schemas"]["DashboardResponse"];
export type BotanicalIdentityCollectionResponse =
  components["schemas"]["BotanicalIdentityCollectionResponse"];
export type EventResponse = components["schemas"]["EventResponse"];

export function getDashboard(signal?: AbortSignal): Promise<DashboardResponse> {
  return requestJson<DashboardResponse>("/api/v1/dashboard", { signal });
}

export function listGlobalEvents(
  signal?: AbortSignal,
): Promise<EventResponse[]> {
  return requestJson<EventResponse[]>("/api/v1/events", { signal });
}

export function getIdentityCollection(
  id: string,
  signal?: AbortSignal,
): Promise<BotanicalIdentityCollectionResponse> {
  return requestJson<BotanicalIdentityCollectionResponse>(
    `/api/v1/botanical-identities/${id}/collection`,
    { signal },
  );
}
