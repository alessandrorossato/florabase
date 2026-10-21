# MAPS-DISTRIBUTION-001 — final refinement review

Candidate: `/home/alessandro/.codex/worktrees/b139/florabase`, branch
`feat/maps-distribution-001`, base `4a657d863af8c3e545f3a2bc9c1d3255344ef48a`
(Sourcing PR #117, following Maps PR #116). Updated 2026-10-21. The feature graph is `verified`
after the full gate; the final exact-tree receipt passed after the documentation/status edits.
Candidate files remain uncommitted. Protected delivery and post-merge DEV smoke remain pending.

This refinement supersedes the initial visual-only, always-unloaded/no-persistence contract.
The operator expressly requested durable reuse of explicitly loaded aggregate evidence and
viewed raster tiles. It does not introduce a local dataset of individual occurrence records.
The architecture audit preceded cache implementation; see
[cache design, rights and storage](maps-distribution-001-cache-design.md) and the updated
[workspace contract](species-distribution.md).

## Chooser and layout

PageHeader, DirectoryTools/Filters, compact Saved Views, BotanicalName, TaskDialog and
MapWorkspace retain the accepted presentation. Selection remains one exact represented
Botanical Identity; hover/focus previews are transient. The chooser opts into the established
TaskDialog backdrop contract. Backdrop and Escape close it, internal controls do not, and
focus returns to the actual Choose species/KPI invoker. Closing does not alter selection.

The desktop workspace remains approximately 70/30 map/inspector. Identity, linked taxon,
eligible and total PRESENT record counts, last checked and Refresh precede one Data details
disclosure. Long IDs, quality policy, uncertainty, privacy, licences and snapshot limitations
are secondary. Desktop inspector scrolling is bounded to viewport height; tablet/mobile
retain the mounted map/inspector switch. ResizeObserver invalidates Leaflet size without
resetting the map. Native ranges and shared map implementation are unchanged.

## Botanical source navigation

When no compatible GBIF link exists, Species distribution offers **Link botanical source** in
the unavailable map state. It preserves the selected identity ID in
`#/identities/<identity-id>?tab=source`. Identity detail maps this route to Reference and selects
the Botanical source module, while existing Overview, Reference, Native range, Taxonomy and
Occurrences routes retain their behavior. The URL works on direct load and refresh. The action is
a native keyboard-operable anchor with shared visible focus styling. The destination performs only
the local external-link read; it does not search GBIF or mutate identity state. Browser hash
navigation retains the normal Back path to the originating Species distribution view.

## Real tile diagnosis and recovery

Actual Review backend logs showed GBIF 503 responses at z=2/y=0/x=1 and x=2, successful
PNG tiles elsewhere, and valid HTTP 204 empty tiles including 2/0/0 and 2/3/0. There was no
authentication failure in those observed requests. The former Leaflet IMG layer decoded
204 as a broken image, latched any failure indefinitely and rebuilt layers/viewport on retry.

The density GridLayer now fetches authenticated same-origin tiles. A 204 completes as a
transparent successful tile. Real failures remain failures. Transient 502/503/504 and network
errors receive at most two retries with bounded delay (Retry-After capped at ten seconds).
401/429/404/409 do not auto-retry. Explicit retry targets failed/missing visible tiles;
successful tiles and viewport stay. Tile unload/unmount cancels clients and removes their
warnings. Warning state follows current incomplete coverage, rather than one historical error.
Basemap errors and retry are separate. Textual evidence remains available through failures.

The default geographic context comes from the existing bundled Natural Earth public-domain
asset, reprojected as vertices through Leaflet. Cache playback therefore needs no external
basemap. The configured online basemap requires a separate explicit checkbox and describes
its IP/visible-area disclosure. It is never archived in this cache.

## Durable local evidence

- Summaries reuse PostgreSQL ExternalProviderCache, in a separate occurrence-v1 namespace,
  at most 256 entries. The key hashes exact provider taxon, CoL XR checklist, fixed quality
  filters, projection, renderer/style/bin contract and version. Both counts must succeed
  before a new UUID generation is atomically published. Failed refresh returns the old
  summary/generation with the provider error; it does not erase good evidence.
- Validated PNG and 204 entries live in the existing durable attachment Docker volume,
  under `occurrence-cache-v1`, outside authoritative media `objects/`. Filenames add generation
  and z/x/y. Limits: 64 MiB per taxon contract, 512 MiB overall, 4096 files; writes evict
  90-day inactive entries and oldest access to meet quotas. Flat derived paths, no-follow
  reads/lock, flock, bounded PNG validation, temporary writes/fsync/atomic replacement and
  per-process identical-request deduplication protect the cache. Four active upstream tile
  requests per process; no whole-world/all-zoom background acquisition.
- Authenticated local GET restores summary automatically; owner/CSRF POST is explicit
  Load/Refresh; owner/CSRF DELETE clears the linked taxon's cache. Tiles accept `generation`
  and `local_only`; 404 cache miss or 409 obsolete generation never falls back to GBIF.
  Browser tile transport uses no-store, leaving authoritative link/generation checks on
  the server. Legacy explicit routes remain. OpenAPI/TypeScript declarations changed;
  no schema migration, dependency or raw-occurrence table was added.
- Navigation, reload and Saved View restoration reset external permission and read only
  local evidence. A cache miss stays Not downloaded. Cached summaries older than one day
  are labelled potentially outdated (Florabase policy). Provider failure/offline retains
  cached counts and available tiles. Changing the exact linked taxon segregates evidence.
- A successful refresh starts a new generation and keeps map viewport, replacing only the
  overlay. Old tiles are never silently substituted. Counts and viewed tiles are separate
  provider observations; a generation is a progressive visualization cache, not a frozen
  GBIF data transaction. Only visited/downloaded/retained tile areas and zooms work offline.
  Missing, evicted and unavailable areas remain explicitly incomplete.

Summaries survive restart and belong to ordinary DB backups. Tiles survive container restart,
but the standard attachment archive includes only `objects/` and intentionally excludes
raster caches. Preserving offline rasters through restore requires a coordinated optional
archive of the cache directory with the matching DB snapshot. Restoring only normal backups
leaves honest tile misses; it does not cause hidden network recovery. Clear affects all
identities with the same exact taxon contract; evidence is public provider-derived data,
accessible only behind Florabase authentication.

## Rights, privacy and scientific meaning

The audit links primary GBIF API, map-use, download-format and publisher-attribution guidance.
One observed successful tile explicitly allowed `public, max-age=1200`. This supports HTTP
cache reuse, not a blanket licence over underlying contributing datasets. Upstream no-store,
no-cache and must-revalidate responses are conservatively excluded from persistence. Such a
summary remains usable for that visit with a Not saved explanation. Provider/publisher
attribution, licence link and obtained date remain visible. The agreement page returned 403
to the documentation reader; official training supplies its attribution/licence obligations.
No private raster caching ban was found in the audited primary sources; this is the bounded
implementation decision, not a legal certification or a redistribution permission.

Only exact taxon, fixed filters and viewed tile coordinates go to GBIF after explicit action.
Search, selection, cache reads and Saved Views send no collection metadata or account data to
providers. No geolocation, name rematching, raw records or bulk downloads are introduced.
Full records would require the separate official asynchronous GBIF download/citation/licence
and bounded-ingestion design described in the audit.

Occurrence is not native range; recording density is not abundance. Eligible mapped records
are a subset of total matching PRESENT records. Blank/empty tiles do not establish absence.
Raster pixels provide neither precise occurrence coordinates nor exact bin counts. The
qualitative purple/yellow legend remains tied to the provider renderer and zoom. Coordinate
uncertainty, historical/cultivated/introduced records and sampling effort remain explained.

## Verification and Review evidence

- Focused backend cache/provider/API/service suite: **33 passed**. After the browser tile
  transport changed to no-store, final API handler regressions also passed **6 tests**.
- Focused PostgreSQL API integration: 3 tests passed. Tests exercise local miss, explicit
  first refresh, persisted PNG/204 replay without provider calls, stale read, offline
  refresh fallback, successful generation replacement, taxon isolation, authentication,
  CSRF and clearing. Owned project `florabase-integration-1f2164f94bb1` reported
  `RESOURCE_CLEANUP_PASSED`, zero residual containers/networks/volumes, shared cache retained.
- Ruff lint and formatting passed for the capability and focused tests (11 files). Strict
  mypy passed for all **8 external_botany source files**. Generated OpenAPI/TypeScript
  `make api-check` passed; no drift.
- Final completed scoped frontend runs: **123 tests / 11 files**: occurrence/Species
  distribution **21/4**, NativeRangesScreen **22/1**, shared NativeCoverageMap/geometry,
  MapWorkspace and Saved Views **77/5**, identity-detail consumer **3/1**. The consumer
  tests now supply the authenticated context and local cache miss expected by the panel.
  Details expansion preserves the mounted map and makes no provider call. Tile tests
  inject 204, transient failures, retry exhaustion/recovery, auth/rate limits and cancellation.
- Changed-file zero-warning ESLint and Prettier checks passed. Strict TypeScript and
  production Vite build passed. Final production chunks: Species distribution 10.61 kB,
  occurrence panel 8.84 kB and lazy density renderer 6.34 kB (uncompressed build output).
  Feature graph: **108 valid**; `git diff --check` passed.
- Broad runs under host memory/swap pressure had test/worker timeouts; they are **not**
  counted as passing. The isolated completed runs above supersede those failed attempts
  without changing test timeouts, assertions or Native ranges implementation.
- Final `make verify-full` passed: backend **953 passed** (90.03% coverage), frontend **832 passed
  across 71 files**, PostgreSQL integration **737 passed**, workflow/static checks, API drift,
  formatting, lint, strict typing, production builds, and the full migration cycle. The feature graph
  has **108 valid features**. After the final handoff/status edits, `make feature-verify` passed in
  full mode and recorded the exact-tree receipt.
- Live authenticated HTTP check against the existing Review loaded Ocimum basilicum:
  **3,783 eligible mapped / 9,775 total matching PRESENT records**. PNG 2/2/1 was 200,
  14,610 bytes; empty 2/0/0 was 204. Both replayed identically with local_only=true, and
  reopening the summary retained the same generation. This required two counts and only
  two actual upstream tiles. Provider-offline/error cases use injected tests, not a real
  provider outage or traffic storm.
- [Initial browser captures](review/maps-distribution-001/README.md) cover 1440×844,
  1024×844 and 390×844 before this functional refinement. A live 670×872 browser review of the
  current code verified the local-only saved summary/map, explicit missing-tile message, inspector
  counts and expanded Data details. No refresh or clear action was invoked. This is not a fresh
  1440/1024/390 responsive recapture; true browser zoom, screen-reader use and physical-device touch
  checks remain operator acceptance items. HTTP replay and automated remount/Saved View tests are
  separate evidence, not claims of those additional checks.

## Review environment and acceptance boundary

Existing candidate-owned `florabase-feature-review` remains at
<http://localhost:15174/#/species-distribution>, with its v4/80 fixture preserved. No reset,
reseed or replacement was done in this refinement. The guarded lifecycle reports frontend,
backend and database healthy on current code with schema `20261013_0042`. The prior replacement of delivered
Native ranges Review had explicit operator approval. Sourcing Preview 15175, UAT, DEV,
Stable Preview and production remain untouched. Existing database head is `20261013_0042`;
this increment needs no migration.

The operator accepted the current Species distribution experience and authorized final
verification and delivery. Current changed-route regression verifies `tab=source` on initial
load and reload, no GBIF search, exact identity, and the Species distribution action URL. Actual
browser Back behavior is supported by native hash navigation and remains part of the post-merge DEV
smoke. Fresh responsive browser captures for the latest cache refinement, true browser zoom,
screen-reader use and physical-device touch checks were not performed. External GBIF availability,
bounded cache eviction, incomplete offline coverage and standard-backup raster exclusion remain
documented limits.
