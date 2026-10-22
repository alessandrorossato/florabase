# MAPS-ORIGINS-001 design

Recorded before implementation, 2026-10-22. Fetched `origin/main` is
`b3f1de4693f50a12396344d251a16a0b4ded4b92` (PR #118). The new supplied Codex
worktree `c902` uses `feat/maps-origins-001-candidate`: the suggested branch is
already attached elsewhere. No other checkout is changed.

The original plan below is historical. The operator-correction section supersedes its online-default,
retry and unavailable-Review-slot assumptions; current behavior/evidence is in the handoff.

## Audit and reuse

The existing `provenance-map` screen is a directory beside Leaflet, with duplicated
controls, an unbounded list above selected details, and selection-triggered flyTo.
`provenance-sites` owns coordinates and management; Geography actually lives in
`geographic-places`, not `geography`. The existing authenticated map projection
already returns coordinate-bearing sites, direct records, lifecycle, exact identity
IDs, accuracy, total sites and sites without coordinates. No API or migration is
needed. Server qualification excludes Sowing-origin Plants/PlantGroups and
extracted Plants; historical direct records remain eligible.

Reuse PageHeader, DirectorySearch, DirectoryTools/TaskDialog, compact SavedViews,
useDirectoryView and the mounted MapWorkspace pane switch. Keep `#/map`,
`provenance_map` v1 and `q` identity-only literal search, `seed_lots`, `plants`
(Plants AND PlantGroups). Ordinary selection remains transient. Exclusion clears
selection permanently; clearing filters never resurrects stale selection. Native
ranges and Species distribution keep their separate evidence and state contracts.

## Provenance-specific presentation

Use compact functional KPIs for visible/total mapped sites, distinct direct record
keys, distinct identity IDs, and all sites missing coordinates. KPI dialogs provide
bounded searchable site/record/identity breakdowns; missing coordinates links to
Geography's sites view, the existing non-map path (no invented missing-only filter).
Default filters expose mapped sites with zero direct records, explicitly labelled;
identity/category exclusions hide sites with no matching records.

Desktop is approximately 70/30 map/inspector with a bounded scrolling inspector.
Default inspector browses sites; selection replaces it with coordinates, accuracy,
filtered direct-record totals and expandable identity groups with record links and
actual lifecycle. Record counts never represent material quantity. Both panes
remain mounted on tablet/mobile. Escape and explicit All sites clear inspection
without clearing filters.

Retain one marker per exact coordinate pair/site and recorded accuracy circles.
Use safe DOM text tooltips, selected icon/z-order and the textual list for coincident
sites, with no jitter or invented geometry. Selection never moves the viewport.
Fit only when visible site IDs/coordinates change, plus an explicit Fit sites action.
ResizeObserver invalidates a revealed map without recreation or animated panning.

## Basemap and privacy

Audit found direct configured OSM tile requests containing only z/x/y plus provider
subdomain; record names/IDs/metadata enter DOM only. Ordinary tile requests disclose
the viewport and client network information. Preserve the default configured online
basemap and attribution, offer an explicit offline switch, and reuse the existing
lazy Natural Earth asset as local generalized context below exact markers. Reproject
its vertices through Leaflet, never use country centroids. Failed tiles have a retry;
local map/list/record information remains available. No new provider/dependency,
geocoding, occurrence request, native-range assertion or persistent cache is added.

## Verification and environment boundary

Focused tests cover counts/deduplication, category meanings, unlinked sites,
selection/filter/history restoration, grouped records, mounted panes, Leaflet
resize/viewport/accuracy, safe tooltips, tile recovery and coordinate fidelity.
Run affected map, Saved Views, Geography, SeedLot and Plants regressions plus static,
build and API drift checks. Existing backend direct-origin tests remain authoritative.

Feature Review 15174 remains owned by delivered `b139`, including its volumes, even
though its frontend/backend are stopped. Do not start, adopt, remove or reseed it.
Use labelled synthetic, frontend-only browser evidence without changing collection
data. Record viewport measurements and distinguish fixture evidence from authenticated
Review, actual zoom, screen-reader and touch acceptance. No canonical feature-verify,
staging, commit, push, PR or delivery in this phase.

## Operator corrections and Extended Botanical Review Dataset v5 — 2026-10-22

Audit confirms the prior renderer explicitly suppressed Referer, violating the
[official OSM tile policy](https://operations.osmfoundation.org/policies/tiles/).
The earlier successful-image count did not certify provider policy compliance.
Use bundled local geometry by default, require explicit operator online enablement,
use the canonical OSM hostname and browser identification/referrer/caching, and
remove the entire online layer on the first failure. No automated OSM viewport
sweeps, header spoofing, automatic policy-block retries or proxy is introduced.
The map's exact markers/accuracy and inspector remain independent from tile access.
The category fieldset gets scoped compact checkbox rows, preserving shared drawer
apply-as-you-choose, Done/Close, Escape/backdrop and invoking-focus behavior.

v5 is a separate additive Review-only dataset, not a replacement/version change of
`uat_fixture.py` v4. A dedicated guarded seed/status entry point repeats the current
host ownership/mount/network/DB/media checks and runtime exact marker/owner checks,
requires a ready valid v4 baseline, and serializes against its fixture lock. A
separate manifest records deterministic logical keys and service-generated UUIDv7
IDs, relationships, source plan fingerprint, counts and completion state. Reopening
a ready extension validates presence and protected media but never overwrites operator
edits or replays creation/operations. A building/failed ledger is explicit, never
reported ready; transaction failures roll back new database rows. Interrupted committed
creation can be recognized from the complete manifest references, not recreated.

All domain objects use existing services and schemas. Curated species names carry no
new authority/taxon-ID claims; synthetic range scenarios are explicitly labelled in
profiles and evidence. New owned material/site/location/order/supplier labels and notes
say Review v5. Existing verified GBIF links remain unchanged; no provider data is
fetched by the seeder. Curated licensed small photos are packaged as bounded assets
with source/author/license/digest metadata, ingested through protected media services;
external references remain metadata until explicit Preview once. No runtime acquisition
or mass media/tile download is part of seeding.

Integration tests use disposable PostgreSQL, not a test mutation of the live Review.
Live acceptance follows only after fixture tests and exact ownership verification;
seed twice to prove retained IDs/counts/owner/baseline, without reset/removal/recreation.
