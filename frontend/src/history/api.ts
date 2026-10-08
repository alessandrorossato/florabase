import type { components } from "../api/schema";
import { requestJson } from "../auth/api";
import { historyParams, type HistoryState } from "./state";
export type HistoryEntry = components["schemas"]["HistoryEntry"];
export type HistoryResponse = components["schemas"]["HistoryResponse"];
export type HistoryReference = components["schemas"]["HistoryReference"];
export function getHistory(
  state: HistoryState,
  offset: number,
  signal?: AbortSignal,
): Promise<HistoryResponse> {
  const params = historyParams(state);
  params.set("offset", String(offset));
  return requestJson(`/api/v1/history?${params}`, { signal });
}
export function historyHref(
  ref: HistoryReference,
  source?: HistoryEntry["source_kind"],
): string {
  switch (ref.kind) {
    case "plant":
      return `#/plants/${ref.id}${source === "event" ? "?tab=events" : ""}`;
    case "plant_group":
      return `#/plant-groups/${ref.id}${source === "event" ? "?tab=events" : ""}`;
    case "sowing":
      return `#/sowings/${ref.id}${source === "germination" ? "?tab=germination" : ""}`;
    case "harvest":
      return `#/harvests/${ref.id}`;
    case "seed_lot":
      return `#/seeds/${ref.id}`;
    case "location":
      return `#/locations/${ref.id}`;
    case "harvest_inventory":
      return ref.harvest_id
        ? `#/harvests/${ref.harvest_id}?inventory=${ref.id}`
        : "#/harvests?tab=stored-material";
  }
}
