# UI-POLISH-006 Evidence — Collection UI Consistency Round + Detail Back/New Bar Removal

- **Feature ID:** `UI-POLISH-006` (proposed release class: `best-effort` in `docs/release/scope-v1.json`)
- **Branch:** `fix/ui-polish-006-collection`
- **Base:** `origin/main` `c83d8163` (fast-forwarded cleanly from Batch 14b `7b667a47` over `v0.1.0-beta.10` release commits)
- **Scope:** Frontend only (no DB migration, no backend/API changes). Part B2 remained `Approval pending` and was intentionally not implemented.

## Part A: Remove Back/New Bar from Plant & Sowing Details (in code, not CSS)

1. Removed `contextActions` ("← Back to Plants" / "← Back to Sowings") and detail-only `actions` ("New plant or group" / "New sowing") from `WorkspaceIntro` in `frontend/src/plants/PlantScreen.tsx` and `frontend/src/sowings/SowingScreen.tsx`, and removed the now-unused `contextActions` prop from `WorkspaceIntro` in `frontend/src/components/CollectionUI.tsx`.
2. Deleted the CSS hiding rule (`.app-content :is(.sowings-workspace, .plants-workspace):has(.collection-detail) .workspace-context-actions { display: none }`) from `frontend/src/components/detail-page.css`, the dead mobile `.collection-context-page > .workspace-context-actions` rules from `frontend/src/components/specimen.css`, and the dead `.sowing-master-detail.is-detail-view .sowing-back`, `.plant-master-detail.is-detail-view .plant-back`, and `.operational-layout.is-detail-view .sowing-back/.plant-back` rules from `frontend/src/styles.css`. `grep -rn ":has(.collection-detail)" frontend/src/` reports zero matches.
3. Loading-state back links at `PlantScreen.tsx` (~line 1588) and `SowingScreen.tsx` (~line 1115) remain intact and reachable while references/collection load; their base `.workspace-context-actions` rules in `styles.css` are preserved.
4. `creationTriggerRef` and `data-collection-return="create"` remain exclusively on the list-level toolbar buttons (`New plant or group`, `New sowing`). Wired `returnToList` onto the `Plants` / `Sowings` breadcrumb links via optional `BreadcrumbItem.onClick` so clicking the breadcrumb returns to the list and focuses the list/trigger.
5. Audited all other Collection details (`SeedLotScreen`, `HarvestScreen`, `CuttingDetails`, `LocationScreen`, `OrderScreen`, `SupplierScreen`): **none** rendered a Back/New bar hidden by CSS.
6. Updated `PlantScreen.test.tsx`, `SowingScreen.test.tsx`, and `test/directoryFilters.ts` to navigate back via the Breadcrumb link, assert focus returns to the collection list, and assert detail views render no `← Back to …` or `New …` buttons.

## Part B1: One Record Page for Every Collection Type (All 19 Items)

### Lineage Strip (`LineageStrip.tsx`, `lineage-strip.css`, `useRecordedLineage.ts`)
- **Item 1:** Dedicated `.lineage-strip__header` row pins `RECORDED LINEAGE` left and `Full lineage` right at constant height on every tab (including the Lineage tab, where `aria-current="page"` is set). Added `Full lineage` to Harvest as well.
- **Item 2:** `.lineage-strip__path` wraps cleanly with connectors inside each step's inline-start padding and generous row gap, so long Cuttings chains never clip.
- **Item 3:** Added `"plant>harvest": "harvested as"`, `"plant_group>harvest": "harvested as"`, and `"harvest>seed_lot": "converted to"` to `lineageVerbs` and passed `currentKind="harvest"` on Harvest.
- **Item 4:** Added compact descendants summary at the end of the strip (`→ 3 sowings`, `→ 1 plant`, `→ 2 attempts`, etc.) linking to the Lineage tab, both when ancestors exist and when a record starts its line.

### Lineage Tab (`LineagePanel.tsx`, `PropagationPath.tsx`)
- **Item 5:** Unified `LineagePanel` across all record types (including Seed lot, Sowing, and Harvest): `Explore material ancestry` link → **Ancestors** horizontal chain ending in `This <Record>` (empty stages filtered out in `PropagationPath`) → **Recorded from this record** elbow tree, with uniform empty-state wording (`No recorded lineage.` / `No recorded source: this record starts its line.` / `Nothing recorded from it yet.`). Removed Sowing's bespoke `PropagationPath`/`extractedStages` code and Cuttings' extra `Maternal lineage` heading.

### Tabs & Active Style (`DetailTabs`, `detail-page.css`)
- **Item 6:** Standardized tab sets and order: `Overview · <work tab(s)> · Photos · Lineage` (Harvest adds `Lineage`; Location adds `Overview · Contents` since location photos do not exist on `main`).
- **Item 7:** Unified `.ui-detail-page .detail-tabs .detail-tab` active/hover/focus styling in `detail-page.css` and removed conflicting `:hover` pale-green fill overrides from `collection-visual.css`, `seed-refinement.css`, `orders.css`, and `supplier-refinement.css`.

### Overview Grid, Almanac, Filler Text & Descendants (`RecordOverview`, `RecordAlmanac`, `RecordDescendants`)
- **Items 8 & 9:** Extracted `frontend/src/timeline/RecordAlmanac.tsx` (wrapping `RecordTimeline` for Schedule-enabled targets and providing the identical Planned/Recorded/History layout for Harvest) and shared `RecordOverview` two-column container-query layout (left = facts sections, right = Almanac, collapsing to one column below `44rem`) across Seed lot, Sowing, Vegetative lot, Rooting attempt, Plant, Plant group, Harvest, and Location.
- **Item 10:** Replaced Sowing's filler Germination section with live germination metrics from `getSowingGermination` (germinated total, last observation date, days to first germination, link to Germination tab) and replaced Seed lot's `"Seed lots have no Journal…"` filler with live sowing counts and link to Sowings.
- **Item 11:** Standardized descendants in Overview via shared `RecordDescendants` one-line count with links (Seed lot sowings, Sowing plants/plant groups, Plant/Plant group extracted plants + cuttings + harvests, Cuttings attempts/offspring, Harvest converted seed lots).

### Header, Specimen Label, Tab Bodies
- **Item 12:** Added `LifecycleStatus` status chip to Harvest header (`Active` / `Depleted` / `Recorded` derived from stored material state).
- **Item 13:** Enforced the `DetailHeader` action-bar rule (≤ 1 primary first + ≤ 2 secondary + Edit + `⋯ More`) across all types: Sowing puts `Create Plant` primary, `Record germination` and `Pot on seedlings…` secondary, `Edit Sowing`, and `Create Plant group` inside `⋯ More`; Plant group moves `Take cuttings` into `⋯ More`; Harvest surfaces `Record disposition` as primary when stored material is held; Location puts primary `Create child` before secondary `Log care for everything here…`.
- **Item 14:** Location omits `secondary` when `display_path === name` (root locations no longer repeat their title) and removes duplicate scope chips from the header status bar (keeping the `Enabled scopes` section in Overview).
- **Item 15:** Updated `SpecimenLabel` + `specimen.css` so plain UI text is the default, monospace (`--font-data`, `tabular-nums`) applies only to dates/quantities/codes, missing values share one plain muted style (`.specimen-label__unknown`), and Seed lot `quantityLabel` trims whitespace.
- **Item 16:** Scoped `.harvest-detail section` in `styles.css` to `.harvest-detail .detail-tab-panel > section` so Harvest's photo-to-label gap matches every other record, and fixed mobile `@media (max-width: 40rem)` `.specimen-label` to span `grid-column: 1 / -1`.
- **Item 17:** Removed the 2-column split on `.collection-detail .germination-section` in `styles.css` so Sowing's Germination tab shows metrics in a horizontal row and `Observation history` full width below.
- **Item 18:** Added shared `RecordChildCard` (matching `LineagePanel`'s compact card + `LifecycleStatus` chip grammar) and adopted it in Seed lot's Sowings tab and Cuttings' Rooting attempts and Offspring tabs.
- **Item 19:** Replaced Harvest's separate "Materials collected" and "Stored material" lists with one compact table (`Material · Quantity · Remaining · State · Storage · Actions` with one `⋯` menu per row) and compact inline link triggers (`Show Seed lot conversions`, `Show disposition history`) opening the existing panels.

## Part C: UI-POLISH-005 Review Leftovers

1. Updated `useRecordTab` in `frontend/src/ui-pages/Cuttings/CuttingDetails.tsx` to follow later `?tab=` route changes via both render-phase route tracking and `hashchange`/`popstate` listeners; covered by a regression test in `Cuttings.test.tsx`.
2. Removed duplicate represented/occurrence-ready counts from the `Species` chooser heading in `frontend/src/species-distribution/SpeciesDistributionScreen.tsx` (kept once in `.distribution-overview`); covered in `SpeciesDistributionScreen.test.tsx`.
3. Removed dead `.app-content .media-workspace > .page-header:not(.page-header--directory)` rules from `frontend/src/media/media.css`.

## Verification & Visual Evidence

- **UAT dataset:** Golden `COMPREHENSIVE` dataset via `make uat-instance-up PROFILE=comprehensive && make uat-instance-seed` (disposable UAT instance retired via `make uat-instance-remove` after verification).
- **Before/after screenshots (untracked, stored outside git per `AGENTS.md`):** Captured at both `1440×900` and `390×844` across Seed lot (`overview`, `sowings`, `lineage`), Sowing (`overview`, `germination`, `lineage`), Cuttings Vegetative lot (`overview`, `lineage`), Rooting attempt (`overview`), Plant (`overview`, `lineage`, cuttings mother), Plant group (`overview`), Harvest (`overview`, `lineage`), and Location (`bench overview`, `bench contents`, `empty root overview`).
- **Focused checks:**
  - `python3 scripts/check-features.py` — 205 features valid
  - `python3 scripts/check-doc-links.py` — 398 documents passed
  - `pnpm exec tsc -b` — 0 errors
  - `pnpm exec eslint` on all changed files — 0 errors, 0 warnings
  - `pnpm exec prettier --check` on all changed files — clean
  - `pnpm exec vitest run src/plants/ src/sowings/ src/seed-lots/ src/harvests/ src/ui-pages/Cuttings/ src/species-distribution/ src/media/ src/components/ src/lineage/ src/timeline/ src/bulk/` — **42 test files passed, 518 tests passed**
- **Canonical gate:** `make feature-verify AGENT_ID=antigravity-neon` run on the frozen tree (see `docs/progress.md`).
