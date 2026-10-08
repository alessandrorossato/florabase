import { describe, expect, test } from "vitest";
import { readSearchState, searchHash } from "../collection/searchApi";
import {
  defaults,
  directoryState,
  readDirectoryState,
  saveDirectoryState,
  saveSearchState,
  savedViewHash,
  type DirectorySurface,
  type SavedState,
} from "./state";

const missing = "AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA";
test("directory URL state belongs only to its surface", () => {
  expect(readDirectoryState("suppliers", "#/plants?q=basil")).toEqual(
    defaults.suppliers,
  );
});

test("Unicode text limits match backend character counts and retain canonical state", () => {
  const directoryQuery = "🌱".repeat(200);
  expect(savedViewHash("suppliers", 1, { q: directoryQuery })).not.toBeNull();
  expect(directoryState("suppliers", { q: `${directoryQuery}🌱` })).toBeNull();
  const searchQuery = "🌱".repeat(120);
  expect(savedViewHash("global_search", 1, { q: searchQuery })).not.toBeNull();
  expect(
    savedViewHash("global_search", 1, { q: `${searchQuery}🌱` }),
  ).toBeNull();
});

const cases: [DirectorySurface, SavedState, string][] = [
  [
    "seed_lots",
    { q: "basil", lifecycle: "history" },
    "#/seeds?q=basil&lifecycle=history",
  ],
  ["sowings", { lifecycle: "completed" }, "#/sowings?lifecycle=completed"],
  [
    "plants",
    { q: "basil", lifecycle: "all", type: "group" },
    "#/plants?q=basil&lifecycle=all&type=group",
  ],
  [
    "harvests",
    { material: "seed", source_type: "plant", identity_id: missing },
    `#/harvests?material=seed&source_type=plant&identity_id=${missing.toLowerCase()}`,
  ],
  [
    "stored_material",
    { state: "all", location_id: missing },
    `#/harvests?tab=stored-material&state=all&location_id=${missing.toLowerCase()}`,
  ],
  ["events", { category: "cultivation" }, "#/events?category=cultivation"],
  [
    "media",
    { q: "leaf", kind: "external", association: "linked", target: "supplier" },
    "#/media?q=leaf&kind=external&association=linked&target=supplier",
  ],
  ["botanical_identities", { q: "Ocimum" }, "#/identities?q=Ocimum"],
  ["suppliers", { q: "店" }, "#/suppliers?q=%E5%BA%97"],
  [
    "orders",
    { q: "PO", supplier_id: missing },
    `#/orders?q=PO&supplier_id=${missing.toLowerCase()}`,
  ],
  [
    "locations",
    { q: "shelf", scope: "seed_lots" },
    "#/locations?q=shelf&scope=seed_lots",
  ],
  ["geography", { q: "Italy", mode: "map" }, "#/geography?q=Italy&mode=map"],
  [
    "provenance_map",
    { q: "basil", seed_lots: false },
    "#/map?q=basil&seed_lots=false",
  ],
];
describe.each(cases)("%s explicit adapter", (surface, state, hash) => {
  test("canonical route restores the same effective state from the beginning", () => {
    const parsed = directoryState(surface, state);
    expect(parsed).not.toBeNull();
    if (!parsed) throw new Error("Invalid fixture");
    const saved = saveDirectoryState(surface, parsed);
    expect(savedViewHash(surface, 1, saved ?? {})).toBe(hash);
    expect(
      saveDirectoryState(surface, readDirectoryState(surface, hash)),
    ).toEqual(saved);
    expect(
      saveDirectoryState(
        surface,
        readDirectoryState(
          surface,
          `${hash}&offset=80&page=4&selected_id=private&action=create`,
        ),
      ),
    ).toEqual(saved);
    expect(saved).not.toHaveProperty("offset");
    expect(savedViewHash(surface, 9, state)).toBeNull();
  });
  test("defaults omitted; arbitrary keys and invalid state refused", () => {
    expect(saveDirectoryState(surface, defaults[surface])).toEqual({});
    expect(savedViewHash(surface, 1, {})).toBeNull();
    expect(
      savedViewHash(surface, 1, { ...state, selected_id: missing }),
    ).toBeNull();
    expect(directoryState(surface, { q: ["bad"] })).toBeNull();
    expect(savedViewHash(surface, 1, { ...state, offset: 40 })).toBeNull();
  });
});

test("Global Search uses SEARCH-002 parser and serializer, with deterministic repeated kinds", () => {
  const search = readSearchState(
    `#/dashboard?q=+Basil+&kind=media_asset&kind=harvest&kind=media_asset&identity_id=${missing}&offset=80`,
  );
  const saved = saveSearchState(search);
  expect(saved).toEqual({
    q: "Basil",
    kind: ["harvest", "media_asset"],
    identity_id: missing.toLowerCase(),
  });
  expect(savedViewHash("global_search", 1, saved ?? {})).toBe(
    searchHash(search),
  );
  expect(saveSearchState(readSearchState(searchHash(search)))).toEqual(saved);
  expect(saved).not.toHaveProperty("offset");
});

test("Global Search retains every exact filter and numeric year without new semantics", () => {
  const state = readSearchState(
    `#/dashboard?kind=plant&lifecycle=active&year=2026&identity_id=${missing}&location_id=${missing}&supplier_id=${missing}&provenance_place_id=${missing}&provenance_site_id=${missing}`,
  );
  const saved = saveSearchState(state);
  expect(saved).toMatchObject({
    year: 2026,
    lifecycle: "active",
    provenance_site_id: missing.toLowerCase(),
    provenance_place_id: missing.toLowerCase(),
    supplier_id: missing.toLowerCase(),
    location_id: missing.toLowerCase(),
  });
  expect(savedViewHash("global_search", 1, saved ?? {})).toBe(
    searchHash(state),
  );
  expect(
    savedViewHash("global_search", 1, {
      kind: ["event"],
      event_kind: "flowering",
      year: 2026,
    }),
  ).toBe("#/dashboard?kind=event&event_kind=flowering&year=2026");
});

test.each([
  { q: "basil", route: "https://foreign.invalid" },
  { q: "basil", offset: 20 },
  { kind: ["bad"] },
  { kind: ["plant", "bad"] },
  { identity_id: "bad" },
  { kind: ["harvest"], lifecycle: "active" },
  { kind: ["media_asset"], year: 2026 },
  { kind: ["plant"], lifecycle: "completed" },
  { year: 2026 },
  { kind: ["event"], event_kind: "bad" },
  { q: "x".repeat(121) },
  { kind: ["plant"], year: 0 },
  { kind: ["plant"], year: 10000 },
  { q: ["bad"] },
  {},
])("bad saved Global Search state stays safely incompatible: %j", (state) => {
  expect(savedViewHash("global_search", 1, state)).toBeNull();
});

test("stale UUIDs stay exact, UI defaults do not store presentation noise", () => {
  expect(savedViewHash("harvests", 1, { identity_id: missing })).toBe(
    `#/harvests?identity_id=${missing.toLowerCase()}`,
  );
  expect(
    saveDirectoryState("plants", {
      q: "  basil  ",
      lifecycle: "active",
      type: "all",
    }),
  ).toEqual({ q: "basil" });
  expect(
    readDirectoryState("geography", "#/geography/site", { mode: "sites" }).mode,
  ).toBe("sites");
  expect(readDirectoryState("plants", "#/plants?type=group").type).toBe(
    "group",
  );
  expect(readDirectoryState("plants", "#/plants?type=bad").type).toBe("all");
});

test("Native ranges canonical URL and private state exclude geometry and transient pagination", () => {
  const state = {
    q: "  Synthetic  ",
    scope: "living",
    mode: "species",
    identity: missing,
    withRange: true,
  };
  const parsed = directoryState("native_ranges", state);
  expect(parsed).toEqual({
    ...state,
    q: "Synthetic",
    identity: [missing.toLowerCase()],
    record: [],
  });
  if (!parsed) throw new Error("Expected valid Native ranges state");
  const saved = saveDirectoryState("native_ranges", parsed);
  if (!saved) throw new Error("Expected saved Native ranges state");
  const hash = savedViewHash("native_ranges", 1, saved);
  expect(hash).toBe(
    `#/native-ranges?q=Synthetic&scope=living&mode=species&identity=${missing.toLowerCase()}&withRange=true`,
  );
  if (!hash) throw new Error("Expected Native ranges hash");
  expect(readDirectoryState("native_ranges", hash)).toEqual(parsed);
  for (const key of ["geometry", "hover", "offset", "zoom", "viewport"]) {
    expect(
      savedViewHash("native_ranges", 1, { ...state, [key]: 1 }),
    ).toBeNull();
  }
  for (const invalid of [
    { scope: "bad" },
    { mode: "map" },
    { identity: "bad" },
    { withRange: "true" },
  ]) {
    expect(savedViewHash("native_ranges", 1, invalid)).toBeNull();
  }
  expect(
    readDirectoryState(
      "native_ranges",
      "#/native-ranges?scope=bad&identity=bad&mode=bad&withRange=bad",
    ),
  ).toEqual(defaults.native_ranges);
});

test("Native selection and record categories are bounded canonical sets with legacy v1 support", () => {
  const ids = Array.from(
    { length: 21 },
    (_, i) => `01900000-0000-7000-8000-${String(i).padStart(12, "0")}`,
  );
  const input = {
    identity: [ids[1].toUpperCase(), ids[0], ids[1]],
    record: ["plant", "seed_lot", "plant"],
    mode: "species",
  };
  const hash = savedViewHash("native_ranges", 1, input);
  expect(hash).toBe(
    `#/native-ranges?mode=species&identity=${ids[0]}&identity=${ids[1]}&record=seed_lot&record=plant`,
  );
  expect(readDirectoryState("native_ranges", hash ?? "").identity).toEqual(
    ids.slice(0, 2),
  );
  expect(
    directoryState("native_ranges", { identity: ids.slice(0, 20) }),
  ).not.toBeNull();
  expect(directoryState("native_ranges", { identity: ids })).toBeNull();
  expect(
    directoryState("native_ranges", { identity: [ids[0], "bad"] }),
  ).toBeNull();
  expect(directoryState("native_ranges", { record: ["event"] })).toBeNull();
  expect(
    directoryState("native_ranges", { identity: ids[0] })?.identity,
  ).toEqual([ids[0]]);
});
