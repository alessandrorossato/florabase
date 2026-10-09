import { recordCategories, type RecordCategory } from "../saved-views/state";
import type { Scope } from "../species-distribution/api";

export interface TaxonomyState {
  scope: Scope;
  record: RecordCategory[];
  q: string;
  taxon: string;
}
export function readState(hash = window.location.hash): TaxonomyState {
  const params = new URLSearchParams(hash.split("?", 2)[1] ?? "");
  const scope = params.get("scope");
  return {
    scope:
      scope === "living" || scope === "current" || scope === "historical"
        ? scope
        : "all",
    record: recordCategories.filter((category) =>
      params.getAll("record").includes(category),
    ),
    q: (params.get("q") ?? "").slice(0, 200),
    taxon: /^wfo-[0-9]{10}$/.test(params.get("taxon") ?? "")
      ? (params.get("taxon") ?? "")
      : "",
  };
}
export function taxonomyHash(state: TaxonomyState): string {
  const params = new URLSearchParams();
  if (state.scope !== "all") params.set("scope", state.scope);
  for (const category of recordCategories)
    if (state.record.includes(category)) params.append("record", category);
  if (state.q.trim()) params.set("q", state.q.trim());
  if (state.taxon) params.set("taxon", state.taxon);
  return `#/taxonomy${params.size ? `?${params}` : ""}`;
}
