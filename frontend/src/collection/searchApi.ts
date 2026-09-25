import type { components } from "../api/schema";
import { requestJson } from "../auth/api";

export type SearchKind = components["schemas"]["SearchKind"];
export type SearchResponse = components["schemas"]["SearchResponse"];

export interface SearchState {
  q: string;
  kinds: SearchKind[];
  identityId: string;
  lifecycle: string;
  locationId: string;
  supplierId: string;
  provenancePlaceId: string;
  provenanceSiteId: string;
  eventKind: string;
  year: string;
}

const kinds: SearchKind[] = [
  "seed_lot",
  "sowing",
  "plant",
  "plant_group",
  "event",
  "botanical_identity",
  "botanical_profile",
  "supplier",
  "location",
  "geographic_place",
  "provenance_site",
];

export function readSearchState(): SearchState {
  const query = window.location.hash.split("?", 2)[1] ?? "";
  const params = new URLSearchParams(query);
  return {
    q: params.get("q") ?? "",
    kinds: params
      .getAll("kind")
      .filter((kind): kind is SearchKind => kinds.includes(kind as SearchKind)),
    identityId: params.get("identity_id") ?? "",
    lifecycle: params.get("lifecycle") ?? "",
    locationId: params.get("location_id") ?? "",
    supplierId: params.get("supplier_id") ?? "",
    provenancePlaceId: params.get("provenance_place_id") ?? "",
    provenanceSiteId: params.get("provenance_site_id") ?? "",
    eventKind: params.get("event_kind") ?? "",
    year: params.get("year") ?? "",
  };
}

export function activeSearch(state: SearchState): boolean {
  return Boolean(
    state.q.trim() ||
    state.kinds.length ||
    state.identityId ||
    state.lifecycle ||
    state.locationId ||
    state.supplierId ||
    state.provenancePlaceId ||
    state.provenanceSiteId ||
    state.eventKind ||
    state.year,
  );
}

export function searchParams(state: SearchState): URLSearchParams {
  const params = new URLSearchParams();
  if (state.q.trim()) params.set("q", state.q.trim());
  for (const kind of state.kinds) params.append("kind", kind);
  if (state.identityId) params.set("identity_id", state.identityId);
  if (state.lifecycle) params.set("lifecycle", state.lifecycle);
  if (state.locationId) params.set("location_id", state.locationId);
  if (state.supplierId) params.set("supplier_id", state.supplierId);
  if (state.provenancePlaceId)
    params.set("provenance_place_id", state.provenancePlaceId);
  if (state.provenanceSiteId)
    params.set("provenance_site_id", state.provenanceSiteId);
  if (state.eventKind) params.set("event_kind", state.eventKind);
  if (state.year) params.set("year", state.year);
  return params;
}

export function searchHash(state: SearchState): string {
  const query = searchParams(state).toString();
  return `#/dashboard${query ? `?${query}` : ""}`;
}

export function getSearch(
  state: SearchState,
  offset: number,
  signal?: AbortSignal,
): Promise<SearchResponse> {
  const params = searchParams(state);
  params.set("offset", String(offset));
  return requestJson<SearchResponse>(`/api/v1/search?${params.toString()}`, {
    signal,
  });
}
