import { recordCategories, type RecordCategory } from "../saved-views/state";
import type { Scope } from "../species-distribution/api";

export interface TaxonomyState {
  scope: Scope;
  record: RecordCategory[];
  q: string;
  taxon: string;
  panel?: "unresolved";
  identity?: string;
  view?: "tree";
  branch?: string;
  status?: "accepted" | "synonym" | "unlinked";
  media?: "with" | "without";
  ranks?: "all";
  photos?: "hide";
  through?: "family" | "genus" | "species";
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
    ...(["accepted", "synonym", "unlinked"].includes(params.get("status") ?? "")
      ? { status: params.get("status") as TaxonomyState["status"] }
      : {}),
    ...(["with", "without"].includes(params.get("media") ?? "")
      ? { media: params.get("media") as TaxonomyState["media"] }
      : {}),
    ...(params.get("ranks") === "all" ? { ranks: "all" as const } : {}),
    ...(params.get("photos") === "hide" ? { photos: "hide" as const } : {}),
    ...(params.get("view") === "tree" ? { view: "tree" as const } : {}),
    ...(/^wfo-[0-9]{10}$/.test(params.get("branch") ?? "")
      ? { branch: params.get("branch") ?? "" }
      : {}),
    ...(["family", "genus", "species"].includes(params.get("through") ?? "")
      ? { through: params.get("through") as TaxonomyState["through"] }
      : {}),
    ...(params.get("panel") === "unresolved"
      ? { panel: "unresolved" as const }
      : {}),
    ...(params.get("panel") === "unresolved" &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
      params.get("identity") ?? "",
    )
      ? { identity: (params.get("identity") ?? "").toLowerCase() }
      : {}),
  };
}
export function taxonomyHash(state: TaxonomyState): string {
  const params = new URLSearchParams();
  if (state.scope !== "all") params.set("scope", state.scope);
  for (const category of recordCategories)
    if (state.record.includes(category)) params.append("record", category);
  if (state.q.trim()) params.set("q", state.q.trim());
  if (state.taxon) params.set("taxon", state.taxon);
  if (state.panel) params.set("panel", state.panel);
  if (state.panel && state.identity) params.set("identity", state.identity);
  if (state.status) params.set("status", state.status);
  if (state.media) params.set("media", state.media);
  if (state.ranks) params.set("ranks", state.ranks);
  if (state.photos) params.set("photos", state.photos);
  if (state.view) params.set("view", state.view);
  if (state.branch) params.set("branch", state.branch);
  if (state.through) params.set("through", state.through);
  return `#/taxonomy${params.size ? `?${params}` : ""}`;
}

export function taxonomyIdentityHash(
  id: string,
  state: TaxonomyState,
  matching = false,
): string {
  const params = new URLSearchParams();
  if (matching) params.set("tab", "taxonomy");
  params.set("taxonomy_return", taxonomyHash(state));
  return `#/identities/${encodeURIComponent(id)}?${params}`;
}

export function taxonomyReturnHash(hash = window.location.hash): string | null {
  const value = new URLSearchParams(hash.split("?", 2)[1] ?? "").get(
    "taxonomy_return",
  );
  return value && (value === "#/taxonomy" || value.startsWith("#/taxonomy?"))
    ? taxonomyHash(readState(value))
    : null;
}

export const representation = {
  living: "Living · Current",
  current: "Current",
  historical: "Historical",
};
export const scopes = [
  { value: "all", label: "All represented" },
  { value: "living", label: "Living" },
  { value: "current", label: "Current" },
  { value: "historical", label: "Historical" },
] as const;
export const recordLabels = {
  seed_lot: "Seeds",
  sowing: "Sowings",
  plant: "Plants",
  plant_group: "Plant groups",
  stored_material: "Stored material",
};
