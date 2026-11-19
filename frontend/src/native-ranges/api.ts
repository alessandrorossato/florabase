import type { components } from "../api/schema";
import { requestJson, type ProtectedRequestCapability } from "../auth/api";
import type { RecordCategory } from "../saved-views/state";
import type { Scope } from "../species-distribution/api";

export type RangeIdentity = components["schemas"]["NativeRangeIdentity"];
export type RangePage = components["schemas"]["NativeRangeIdentityPage"];
export type Overview = components["schemas"]["NativeRangeOverview"];
export type SelectedRanges = components["schemas"]["SelectedNativeRanges"];
export type Selection = components["schemas"]["NativeRangeSelection"];
export type RangePlace = components["schemas"]["RecordedRangePlace"];
export type PlaceCoverage = components["schemas"]["RecordedPlaceCoverage"];
export type Territory = components["schemas"]["TerritoryCoverage"];
export interface Filters {
  q: string;
  scope: Scope;
  withRange: boolean;
  record: RecordCategory[];
}
const endpoint = "/api/v1/explore/native-ranges";
function params(filters: Filters, offset: number) {
  const result = new URLSearchParams({
    q: filters.q.trim(),
    scope: filters.scope,
    with_range: String(filters.withRange),
    offset: String(offset),
  });
  for (const category of filters.record) result.append("record", category);
  return result;
}
export function listNativeIdentities(
  filters: Filters,
  offset: number,
  capability: ProtectedRequestCapability,
  signal: AbortSignal,
): Promise<RangePage> {
  return requestJson(`${endpoint}/identities?${params(filters, offset)}`, {
    capability,
    signal,
  });
}
export function getNativeOverview(
  filters: Filters,
  offset: number,
  capability: ProtectedRequestCapability,
  signal: AbortSignal,
): Promise<Overview> {
  return requestJson(`${endpoint}/overview?${params(filters, offset)}`, {
    capability,
    signal,
  });
}
export function getNativeSelection(
  id: string,
  filters: Filters,
  offset: number,
  capability: ProtectedRequestCapability,
  signal: AbortSignal,
): Promise<SelectedRanges> {
  return requestJson(
    `${endpoint}/identities/${encodeURIComponent(id)}?${params(filters, offset)}`,
    { capability, signal },
  );
}

export function getNativeComparison(
  ids: string[],
  filters: Filters,
  capability: ProtectedRequestCapability,
  signal: AbortSignal,
): Promise<Selection> {
  const query = params(filters, 0);
  query.delete("offset");
  for (const id of ids) query.append("identity", id);
  return requestJson(`${endpoint}/selection?${query}`, { capability, signal });
}

export type TerritoryIdentityPage =
  components["schemas"]["TerritoryRangeIdentityPage"];
export function listTerritoryIdentities(
  filters: Filters,
  codes: string[],
  match: "any" | "all",
  ids: string[] | undefined,
  offset: number,
  capability: ProtectedRequestCapability,
  signal: AbortSignal,
): Promise<TerritoryIdentityPage> {
  const query = params(filters, offset);
  codes.forEach((code) => {
    query.append("territory", code);
  });
  ids?.forEach((id) => {
    query.append("identity", id);
  });
  query.set("match", match);
  return requestJson(`${endpoint}/territories/identities?${query}`, {
    capability,
    signal,
  });
}
