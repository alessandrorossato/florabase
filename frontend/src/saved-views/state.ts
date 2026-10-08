import {
  historyHash,
  parseHistoryState,
  saveHistoryState,
} from "../history/state";
import type { components } from "../api/schema";
import {
  eventKinds,
  lifecycles,
  readSearchState,
  searchHash,
  searchKinds,
  searchParams,
  type SearchState,
} from "../collection/searchApi";

export type Surface = components["schemas"]["SavedViewSurface"];
export type SavedState = components["schemas"]["SavedViewResponse"]["state"];
export type DirectorySurface = Exclude<Surface, "global_search" | "history">;
export interface DirectoryStates {
  seed_lots: { q: string; lifecycle: "active" | "history" | "all" };
  sowings: { q: string; lifecycle: "active" | "completed" | "all" };
  plants: {
    q: string;
    lifecycle: "active" | "history" | "all";
    type: "all" | "plant" | "group";
  };
  harvests: {
    q: string;
    material: string;
    source_type: string;
    identity_id: string;
  };
  stored_material: {
    q: string;
    state: string;
    material: string;
    identity_id: string;
    location_id: string;
  };
  events: { category: "all" | "observations" | "cultivation" | "status" };
  media: {
    q: string;
    kind: string;
    association: string;
    target:
      | ""
      | "collection"
      | "seed_lot"
      | "sowing"
      | "plant"
      | "plant_group"
      | "event"
      | "harvest"
      | "supplier";
  };
  botanical_identities: { q: string };
  suppliers: { q: string };
  orders: { q: string; supplier_id: string };
  locations: {
    q: string;
    scope: "all" | "plants" | "sowings" | "seed_lots" | "harvest_inventory";
  };
  geography: { q: string; mode: "places" | "sites" | "map" };
  provenance_map: { q: string; seed_lots: boolean; plants: boolean };
}

export const surfaceLabels: Record<Surface, string> = {
  global_search: "Global Search",
  seed_lots: "Seed lots",
  sowings: "Sowings",
  plants: "Plants and Plant groups",
  harvests: "Harvests",
  stored_material: "Stored material",
  events: "Journal",
  history: "History",
  media: "Media Library",
  botanical_identities: "Botanical identities",
  suppliers: "Suppliers",
  orders: "Orders",
  locations: "Locations",
  geography: "Geography",
  provenance_map: "Collection origins",
};
export const directoryRoutes: Record<DirectorySurface, string> = {
  seed_lots: "seeds",
  sowings: "sowings",
  plants: "plants",
  harvests: "harvests",
  stored_material: "harvests?tab=stored-material",
  events: "events",
  media: "media",
  botanical_identities: "identities",
  suppliers: "suppliers",
  orders: "orders",
  locations: "locations",
  geography: "geography",
  provenance_map: "map",
};
export const defaults: DirectoryStates = {
  seed_lots: { q: "", lifecycle: "active" },
  sowings: { q: "", lifecycle: "active" },
  plants: { q: "", lifecycle: "active", type: "all" },
  harvests: { q: "", material: "", source_type: "", identity_id: "" },
  stored_material: {
    q: "",
    state: "active",
    material: "",
    identity_id: "",
    location_id: "",
  },
  events: { category: "all" },
  media: { q: "", kind: "", association: "all", target: "" },
  botanical_identities: { q: "" },
  suppliers: { q: "" },
  orders: { q: "", supplier_id: "" },
  locations: { q: "", scope: "all" },
  geography: { q: "", mode: "places" },
  provenance_map: { q: "", seed_lots: true, plants: true },
};
const materials = [
  "fruit",
  "flower",
  "leaf",
  "root",
  "seed",
  "stem_or_shoot",
  "whole_plant",
  "other",
];
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const choices: Partial<
  Record<DirectorySurface, Record<string, readonly string[]>>
> = {
  seed_lots: { lifecycle: ["active", "history", "all"] },
  sowings: { lifecycle: ["active", "completed", "all"] },
  plants: {
    lifecycle: ["active", "history", "all"],
    type: ["all", "plant", "group"],
  },
  harvests: { material: materials, source_type: ["plant", "plant_group"] },
  stored_material: {
    state: ["active", "depleted", "all"],
    material: materials,
  },
  events: { category: ["all", "observations", "cultivation", "status"] },
  media: {
    kind: ["local", "external"],
    association: ["all", "linked", "unlinked"],
    target: [
      "collection",
      "seed_lot",
      "sowing",
      "plant",
      "plant_group",
      "event",
      "harvest",
      "supplier",
    ],
  },
  locations: {
    scope: ["all", "plants", "sowings", "seed_lots", "harvest_inventory"],
  },
  geography: { mode: ["places", "sites", "map"] },
};

function fieldValue(
  surface: DirectorySurface,
  key: string,
  value: unknown,
): string | boolean | null {
  if (key === "q")
    return typeof value === "string" && Array.from(value.trim()).length <= 200
      ? value.trim()
      : null;
  if (key.endsWith("_id"))
    return typeof value === "string" && (!value || uuid.test(value))
      ? value.toLowerCase()
      : null;
  if (surface === "provenance_map")
    return typeof value === "boolean" ? value : null;
  return typeof value === "string" &&
    ((value === "" &&
      defaults[surface][key as keyof DirectoryStates[typeof surface]] === "") ||
      choices[surface]?.[key]?.includes(value))
    ? value
    : null;
}

export function directoryState<S extends DirectorySurface>(
  surface: S,
  input: SavedState,
  strict = true,
): DirectoryStates[S] | null {
  const base = defaults[surface];
  const result: Record<string, string | boolean> = { ...base };
  for (const [key, value] of Object.entries(input)) {
    if (!(key in base)) {
      if (strict) return null;
      continue;
    }
    const normalized = fieldValue(surface, key, value);
    if (normalized === null) {
      if (strict) return null;
      continue;
    }
    // Empty UI selections use defaults, except explicit all-state storage choice.
    result[key] = normalized;
  }
  return result as DirectoryStates[S];
}

export function readDirectoryState<S extends DirectorySurface>(
  surface: S,
  hash = window.location.hash,
  fallback: Partial<DirectoryStates[S]> = {},
): DirectoryStates[S] {
  const [path, query = ""] = hash.split("?", 2);
  const params = new URLSearchParams(
    path === `#/${directoryRoutes[surface].split("?", 2)[0]}` ? query : "",
  );
  const input: SavedState = { ...fallback };
  for (const key of Object.keys(defaults[surface])) {
    const value = params.get(key);
    if (value !== null)
      input[key] =
        typeof defaults[surface][key as keyof DirectoryStates[S]] === "boolean"
          ? value === "false"
            ? false
            : value === "true"
              ? true
              : value
          : value;
  }
  return directoryState(surface, input, false) ?? defaults[surface];
}

export function saveDirectoryState<S extends DirectorySurface>(
  surface: S,
  state: DirectoryStates[S],
): SavedState | null {
  const parsed = directoryState(surface, { ...state });
  if (!parsed) return null;
  const result: SavedState = {};
  for (const [key, value] of Object.entries(parsed)) {
    if (
      value !== defaults[surface][key as keyof DirectoryStates[S]] &&
      value !== ""
    )
      result[key] = value;
  }
  return result;
}

export function saveSearchState(state: SearchState): SavedState | null {
  const params = searchParams(state);
  const parsed = readSearchState(searchHash(state));
  if (
    Array.from(parsed.q).length > 120 ||
    parsed.kinds.length !== new Set(parsed.kinds).size
  )
    return null;
  for (const key of [
    "identityId",
    "locationId",
    "supplierId",
    "provenancePlaceId",
    "provenanceSiteId",
  ] as const) {
    if (parsed[key] && !uuid.test(parsed[key])) return null;
  }
  const kind = parsed.kinds.length === 1 ? parsed.kinds[0] : undefined;
  if (
    parsed.lifecycle &&
    (!kind || !lifecycles[kind]?.includes(parsed.lifecycle))
  )
    return null;
  if (
    parsed.eventKind &&
    (kind !== "event" || !eventKinds.includes(parsed.eventKind))
  )
    return null;
  if (
    parsed.year &&
    (!kind ||
      ![
        "seed_lot",
        "sowing",
        "plant",
        "plant_group",
        "event",
        "harvest",
      ].includes(kind) ||
      !/^\d{1,4}$/.test(parsed.year) ||
      Number(parsed.year) < 1)
  )
    return null;
  if (state.kinds.some((item) => !searchKinds.includes(item))) return null;
  const result: SavedState = {};
  for (const [key, value] of params) {
    if (key === "kind") result.kind = parsed.kinds;
    else result[key] = key === "year" ? Number(value) : value;
  }
  return result;
}

export function savedViewHash(
  surface: Surface,
  version: number,
  state: SavedState,
): string | null {
  if (version !== 1) return null;
  if (surface === "history") {
    const parsed = parseHistoryState(state);
    return parsed && Object.keys(saveHistoryState(parsed)).length
      ? historyHash(parsed)
      : null;
  }
  if (surface === "global_search") {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(state)) {
      if (
        key === "kind" &&
        Array.isArray(value) &&
        value.every((kind) => typeof kind === "string")
      ) {
        for (const kind of value) params.append("kind", kind);
      } else if (
        (key !== "year" && key !== "kind" && typeof value === "string") ||
        (key === "year" && typeof value === "number")
      )
        params.set(key, String(value));
      else return null;
    }
    const search = readSearchState(`#/dashboard?${params}`);
    const canonical = saveSearchState(search);
    if (
      !canonical ||
      !Object.keys(canonical).length ||
      Object.keys(state).some((key) => !(key in canonical)) ||
      (Array.isArray(state.kind) &&
        state.kind.some(
          (kind) =>
            !searchKinds.includes(kind as components["schemas"]["SearchKind"]),
        ))
    )
      return null;
    return searchHash(search);
  }
  if (!(surface in defaults)) return null;
  const parsed = directoryState(surface, state);
  if (!parsed) return null;
  const canonical = saveDirectoryState(surface, parsed);
  if (!canonical || !Object.keys(canonical).length) return null;
  const [route, query = ""] = directoryRoutes[surface].split("?", 2);
  const params = new URLSearchParams(query);
  for (const [key, value] of Object.entries(canonical))
    params.set(key, String(value));
  return `#/${route}${params.size ? `?${params}` : ""}`;
}
