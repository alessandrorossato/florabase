# UX-SORT-001 evidence

- **Branch:** `feat/fn-05-directory-sort` from `origin/main`
  `b632c5c734fdab55e62230cdee99938ae34ece7e`
- **Writers:** `neon-fn-05` (implementation, commit `440c32899d744bab1ef0b2573e72072297e2622c`);
  `claude-batch13` after operator takeover (identifier rename and this record)
- **Feature:** `UX-SORT-001` (`implemented`; proposed release class `best-effort` in
  [`docs/release/scope-v1.json`](../scope-v1.json), registered next to `FN-02`/`FN-04`)
- **Identifier:** implemented as `FN-05`, renamed to `UX-SORT-001` because `FN-05` is already the
  release task for Journal Today preselection (`acceptance-v1.md`, `scope-v1.md`, G-CORE). Its own
  record, [`fn-05.md`](fn-05.md), is unchanged. The rename touches only `docs/features.json`,
  `docs/release/scope-v1.json`, `docs/progress.md`, one comment in
  `backend/src/florabase/saved_views/state.py` and six test titles; no behaviour changes. The
  branch name keeps `fn-05`.
- **Migrations / OpenAPI:** none; `backend/openapi.json` and `frontend/src/api/schema.d.ts` are
  unchanged.

## Scope

1. **Toolbar alignment.** `frontend/src/styles/normalization.css` and
   `frontend/src/styles/directory-system.css` clear the inherited `.field` `margin-bottom` on
   `.directory-tools .directory-sort`, size its `<select>` to `var(--control-height)` with
   `1px solid var(--border-strong)`, `var(--radius-small)`, `var(--type-body)` and a
   `var(--surface-hover)` hover in light and dark themes, and keep it non-full-width
   (`flex: 0 1 auto; max-width: 100%`) on the phone tools row (`@media (max-width: 40rem)`), wrapping
   without horizontal overflow when it does not fit.
2. **Directory rollout.** `sortDirectory` (`frontend/src/components/directorySort.ts`) and
   `DirectorySortSelect` (`frontend/src/components/DirectorySort.tsx`) gain a name-only mode
   (`DirectoryNameSort`: Default order, Name A–Z, Name Z–A; omitting `dateLabel` hides Newest/Oldest).
   Sorting is applied before pagination with canonical URL and Saved View state, validated in
   `backend/src/florabase/saved_views/state.py` (`HarvestState`, `StoredMaterialState`,
   `NameSortedTextState`) and `frontend/src/saved-views/state.ts`.

## Directory inventory

| Screen | Surface | Decision | Name / date key and reason |
| --- | --- | --- | --- |
| Seeds (`SeedLotScreen.tsx`) | `seed_lots` | Existing SORT (FN-02) | Unchanged (`acquisition_date ?? harvest_date`, "acquisition or harvest date") |
| Sowings (`SowingScreen.tsx`) | `sowings` | Existing SORT (FN-02) | Unchanged (`sowing_date`, "sowing date") |
| Plants and Plant groups (`PlantScreen.tsx`) | `plants` | Existing SORT (FN-02) | Unchanged (`collection_entry_date`, "collection-entry date") |
| Harvests (`HarvestScreen.tsx`) | `harvests` | SORT | Name `display_title`; date `occurred_on` ("harvest date"), undated last; before pagination |
| Botanical identities (`BotanicalIdentityScreen.tsx`) | `botanical_identities` | NAME-ONLY | `display_label`; no domain date on `BotanicalIdentityResponse` |
| Stored material (`StoredMaterial.tsx`) | `stored_material` | NAME-ONLY | Visible row title (material label · harvest title); no domain date on `InventoryResponse`; before pagination and bulk-selection mapping |
| Suppliers (`SupplierScreen.tsx`) | `suppliers` | NAME-ONLY | `name`; no domain date on `SupplierListResponse` |
| Cuttings, lots and attempts (`Cuttings.tsx`) | `cuttings` | SKIP | Server-side limit/offset pagination |
| Orders (`OrderScreen.tsx`) | `orders` | SKIP | Server-side limit/offset pagination |
| Media (`MediaScreen.tsx`) | `media` | SKIP | Server-side limit/offset pagination |
| Locations (`LocationScreen.tsx`) | `locations` | SKIP | Hierarchical location tree, not a flat list |
| Geography (`GeographyScreen.tsx`) | `geography` | SKIP | Place tree, map and site sub-view sharing one toolbar |
| Taxonomy (`TaxonomyScreen.tsx`) | none | SKIP | Classification tree and analysis explorer; no Saved View surface |
| Species distribution (`SpeciesDistributionScreen.tsx`) | `species_distribution` | SKIP | Distribution map/analysis with a server-paginated identity chooser |
| Native ranges (`NativeRangesScreen.tsx`) | `native_ranges` | SKIP | Native-range map and multi-species comparison |
| Collection origins (`ProvenanceMapScreen.tsx`) | `provenance_map` | SKIP | Geographic origin map |
| Activity, Journal (`GlobalEventsScreen.tsx`) | `events` | SKIP | Chronological event feed |
| Activity, History (`HistoryScreen.tsx`) | `history` | SKIP | Chronological audit feed with server-side offset pagination |
| Activity, Schedule (`ScheduleScreen.tsx`) | none | SKIP | Due-date agenda and calendar grouped by time window |

Non-production `<DirectoryTools>` demos (`ui-lab/Lab.tsx`, `ScaffoldDirectoryExample.tsx`) are
untouched.

## Computed-layout measurements

Measured in headless Chromium against the worktree's stylesheets (the repository has no Playwright
suite in `pnpm test`; the CSS contract is covered by `frontend/src/appearance/styles.test.ts`).

| Viewport | State | Sort select | Sibling toolbar controls |
| --- | --- | --- | --- |
| 1440×900, Seeds | Before | top 99.5, bottom 139.5, h 40.0, margin-bottom 16px | top 107.5, bottom 147.5, h 40.0 (select 8.0px higher) |
| 1440×900, Seeds | After | top 100.5, bottom 140.5, h 40.0, margin-bottom 0 | View, Filters, Saved, New: top 100.5, bottom 140.5, h 40.0, radius 8px, border 1px |
| Phone (≤ 40rem), Botanical identities | After | top 539.1, bottom 583.1, h 44.0, w 135.0, margin-bottom 0 | Saved and New 44px icon buttons at top 539.1 on the same row |
| Phone (≤ 40rem), Seeds | After | h 44.0, margin-bottom 0 | Wraps cleanly; not full-width, no horizontal overflow |

## Screenshots (not committed)

Before/after captures are kept outside the repository (Antigravity scratch folder of the
implementing session), per the repository rule that review screenshots are not committed:
`before-1440-light.png`, `after-1440-light.png`, `after-1440-dark.png`, `after-390-light.png`,
`after-390-dark.png`.

## Verification

Focused tests at `440c328`: `pytest --no-cov tests/test_saved_views.py` (107 passed, accepted and
rejected sort values for harvests, stored material, botanical identities and suppliers); frontend
Vitest `directorySort.test.ts`, `DirectoryTools.test.tsx`, `styles.test.ts`, `state.test.ts`,
`BotanicalIdentitySort.test.tsx`, `HarvestScreen.test.tsx`, `StoredMaterial.test.tsx`,
`SupplierScreen.test.tsx` and the existing Seeds, Sowings and Plants screen tests (all passed).

Canonical gate on tested commit `440c32899d744bab1ef0b2573e72072297e2622c`
(`make feature-verify AGENT_ID=neon-fn-05`, tier `product`): `FEATURE_VERIFICATION_PASSED`, total
964.35s.

| Stage | Result | Elapsed |
| --- | --- | --- |
| feature-graph (188 features) | passed | 0.02s |
| doc-links (370 documents) and test-doc-links | passed | 0.37s / 0.04s |
| whitespace, staged and untracked | passed | 0.06s |
| quality (`make check`) | passed | 232.68s |
| production-builds | passed | 19.60s |
| integration (PostgreSQL) | passed | 314.88s |
| golden-dataset (35 passed) | passed | 396.69s |

The identifier rename and this record change test titles, so the frozen tip is verified again by
canonical `make feature-verify AGENT_ID=claude-batch13`.

## Merge-tree notes

At `440c328`, `git merge-tree` against the other Batch 13 sources reported only `docs/progress.md`
conflicts for `feat/care-bulk-001` and `feat/propagation-batch-001` (`saved_views/state.py`,
`saved-views/state.ts`, `docs/features.json` and `docs/release/scope-v1.json` auto-merge). The
`docs/release/scope-v1.json` conflict then reported for `docs/docs-004-batch12-followups` came from
that branch predating `MOBILE-002` on `origin/main`; it is resolved on that branch by merging
`b632c5c`.
