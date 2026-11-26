# Engineering progress

## 2026-11-25 — REF-SETUP-001 automatic background reference index provisioning

- On `feat/ref-setup-001` from `origin/main` `b632c5c` (writer `neon-ref-setup-001`), targeting
  Batch 14 alongside `IMPORT-002` with zero edits to `import_export/`, `import_wizard/`, or
  frontend import screens.
- Added `FLORABASE_REFERENCES_SETUP` (`off` default when unset | `auto`) and
  `FLORABASE_REFERENCES_STATE_DIR` (default `/var/lib/florabase/data/state/reference`) in
  `backend/src/florabase/core/config.py`, enabled `- FLORABASE_REFERENCES_SETUP=auto` in
  `compose.yaml` (50 lines, keeping ADR 0009/0010 contract), and updated
  `scripts/test-beta-runtime.py`.
- Centralized pinned archive streaming in `backend/src/florabase/core/reference_index.py`
  (`download_archive()` with configurable `max_seconds=1800`, `follow_redirects=False`,
  `Content-Length`/streaming byte bounds, and multi-header `content-type` validation for Zenodo's
  duplicate `application/octet-stream` headers), added `taxonomy/snapshot.py::download()`
  (`Accept: */*`, exact 132,643,291-byte check, checksum before ZIP parse), and reused it in
  `native_range_enrichment/snapshot.py::download()`.
- Added `backend/src/florabase/reference_setup/` (`state.py`, `lock.py`, `worker.py`, `runner.py`):
  FastAPI `lifespan()` starts a lightweight coordinator task only in `auto` mode (no I/O in
  start-up; every seal/readiness check runs in a worker thread), spawning sequential `os.nice(10)` worker subprocesses holding an inter-process
  `fcntl` lock in `state/reference/` (`0700`), cleaning stale `.staging-*` directories on start,
  running a `(archive + expected_index) * 1.2` free-space pre-check (`failed: disk`), staging
  with `TMPDIR`/`SQLITE_TMPDIR` inside `state/reference/`, atomically publishing sealed indexes,
  deleting downloaded archives, terminating cleanly on `SIGTERM` with zero partial publish,
  logging one sanitized warning line per failure (`network`/`checksum`/`size`/`build`/`disk`),
  retrying at most once every 6 hours while not ready, and exiting with zero idle work once ready.
  Managed WCVP v16 enforces `require_seal=True`; `off` mode keeps using existing valid sealed
  managed indexes (`ready (setup off)`) with zero outbound requests; manual paths are skipped,
  never written, and reported as `manual`.
- Kept unauthenticated `GET /api/v1/system/info` unchanged, added authenticated read-only
  `GET /api/v1/system/references` (`SystemReferencesResponse`, `ReferenceSetupIndexStatus`),
  regenerated `backend/openapi.json` and `frontend/src/api/schema.d.ts`, added a read-only
  **Reference index status** block in **Settings → Data sources**, and updated unavailable notices
  in Taxonomy and Native Range panels for background preparation.
- Updated `docs/installation.md`, `docs/dev-references.md`,
  `docs/security/beta-distribution-001/sqlite-reference-indexes.md`, `CHANGELOG.md` (`Unreleased`
  upgrade note), `docs/features.json` (`REF-SETUP-001`, `implemented`, next to WCVP/taxonomy),
  `docs/release/scope-v1.json` (`"best-effort"`), and recorded Phase 1 design and Phase 2 evidence
  (including live real-archive worker run: WFO `126.78 s` / `166.4 MiB` RSS / `413,069,312` B;
  WCVP v16 `87.90 s` / `67.2 MiB` RSS / `952,799,232` B) in
  [ref-setup-001-design.md](release/evidence/ref-setup-001-design.md) and
  [ref-setup-001.md](release/evidence/ref-setup-001.md).
- Verified focused backend unit tests (`test_reference_setup.py`, 17 passed), PostgreSQL
  integration tests (`tests/integration/test_reference_setup.py`, 3 passed), frontend checks
  (`HelpAndSources.test.tsx`, `TaxonomyScreen.test.tsx`, `NativeRangeEnrichmentPanel.test.tsx`,
  34 passed), `scripts/test-beta-runtime.py` (17 passed), `scripts/check-features.py`, `doc-links`,
  `api-check`, and `git merge-tree` against `feat/import-002-sheet-wizard` (`7dcbfd8`: clean
  auto-merge on all code, `openapi.json`, `schema.d.ts`, `features.json`, and `scope-v1.json`;
  expected additive-only conflict in `docs/progress.md`). Canonical FULL
  `make feature-verify AGENT_ID=neon-ref-setup-001` runs on the frozen committed tree.
- Review fixes (writer `claude-ref-setup`, takeover of `neon-ref-setup-001`): M1 coordinator
  `start()` only creates the task and all `is_index_ready()` calls run via `asyncio.to_thread`, so
  seal hashing (~1.37 GB) never blocks the lifespan or `/api/v1/health`; S1 the runner passes
  `TMPDIR`/`SQLITE_TMPDIR` in the worker environment pointing at a fixed per-index
  `.staging-<index>` directory created under the lock; S2 a `checksum` failure is not retried until
  restart (pinned release no longer served upstream, documented in `installation.md`); S3 the
  WCVP DEV CLI keeps its 240 s bound; S4/S5 wording on the seal (corruption, not tampering) and
  on manual paths; S6 structured `source_preparing` (`TaxonomyTree`, `IdentityTaxonomy`) and
  `preparing` (`SourceStatus`) flags replace frontend substring matching, without repeating the
  server sentence. Focused checks: `test_reference_setup.py` (19 passed), native range and
  taxonomy backend tests, integration `test_reference_setup.py` (3 passed), ruff, mypy, frontend
  typecheck/lint/prettier and taxonomy/botanical-profiles/settings vitest (64 passed),
  `api-generate` + `api-check`.
## 2026-11-25 — ABOUT-001 Settings → About page and official data-source links

- On `feat/about-001` from `origin/main` `b632c5c`, merged with `origin/main` `08ff2f9` (writer
  `claude-about-001`), targeting Batch 14.
  Frontend only: no backend, OpenAPI, migration or Compose change.
- Added Settings → About (`#/about`, `frontend/src/settings/AboutScreen.tsx`): version and short
  image revision from the image's `/release.json` (exported `fetchReleaseInfo`, now shared with the
  update watcher), project link, the tag's `CHANGELOG.md` and release notes, and the bundled
  `/LICENSE` and `/THIRD_PARTY_NOTICES.txt`.
- Settings → Data sources gains a "Links" column: official site and data-source page for WFO
  (2026-06 on Zenodo), Kew WCVP, GBIF (API docs), Natural Earth (download page) and OpenStreetMap
  (tile usage policy).
- Checks: Vitest `src/settings src/shell src/pwa src/App.test.tsx src/App.lazy.test.tsx` (251 tests),
  `pnpm typecheck`, `pnpm lint`, `prettier --check src`. Evidence:
  [docs/release/evidence/about-001.md](release/evidence/about-001.md).
- Unresolved: canonical `make feature-verify` not yet run; `docs/progress.md`, `docs/features.json`
  and `DataSourcesScreen.tsx` also change on `feat/ref-setup-001` (see evidence for merge check).

## 2026-11-25 — UX-SORT-002 server-side Sort by for Orders, Media and Cuttings

- On `feat/ux-sort-002` from `feat/fn-05-directory-sort` `760283a` (UX-SORT-001), realigned by
  merging `origin/main` `08ff2f9` (batch 13, #227). Writer `claude-ux-sort-002`.
- Added `backend/src/florabase/db/ordering.py` (`DirectorySort`, `directory_order()`) and an optional
  whitelisted `sort` (`name`, `name_desc`, `newest`, `oldest`; anything else 422) on
  `/api/v1/orders`, `/api/v1/media-assets`, `/api/v1/vegetative-lots` and
  `/api/v1/propagation-attempts`. Ordering runs in SQL before `limit`/`offset`, compares names
  case-insensitively on the displayed name, orders partial dates with missing month/day at the start
  of the period, keeps missing names/dates last and breaks ties by id. Defaults are unchanged.
- Orders, Media and Cuttings reuse `DirectorySortSelect` (dated options), reset to the first page on
  change and round-trip `sort` through URL and Saved View state (`OrderState`, `MediaState`,
  `CuttingsState`; `frontend/src/saved-views/state.ts`). No migration; OpenAPI regenerated.
- Registered `UX-SORT-002` (`implemented`, `best-effort`). Evidence:
  [ux-sort-002.md](release/evidence/ux-sort-002.md). Known limit: SQL `lower()` is not the browser's
  natural numeric compare (`Batch 10` before `Batch 9`).
- Focused checks: ruff/mypy, pnpm format/lint/typecheck, vitest (orders, media, cuttings, saved views,
  components), backend unit tests, `make api-check`, and PostgreSQL integration for
  `product/test_directory_sort.py` plus the orders, cuttings API, shared media and saved-view suites (68
  passed). The canonical `make feature-verify` is run by the operator.

## 2026-11-25 — Settings → Media defaults (`MEDIA-SETTINGS-001`)

- On `feat/media-settings-001` from `ci/batch-13` `756a3c8`, realigned by merging `origin/main`
  `08ff2f9` (Batch 13, #227) (writer `claude-media-settings`).
  Migration `20261125_0050` on `20261125_0049` adds four media-default columns to
  `application_settings`; single Alembic head `20261125_0050`.
- New Settings → Media page: the saved default only pre-selects "Save a local copy" (no automatic
  fetch, privacy contract unchanged); default attribution/licence prefill only the owner's own
  uploads. Local uploads now accept `licence_label`/`licence_url`. OpenAPI regenerated; golden
  smoke/comprehensive baselines updated for the new schema revision.
- Checks: `make test-backend`, focused integration (settings, settings migration, attachment API),
  `make golden-dataset-check`, `make golden-dataset-comprehensive-check`, `make test-frontend`,
  `make lint`, `make typecheck`, `check-features.py`. Evidence: [media-settings-001.md](release/evidence/media-settings-001.md).

## 2026-11-25 — Batch 13 integration (DOCS-004, PROPAGATION-BATCH-001, CARE-BULK-001/FN-03, UX-SORT-001, MEDIA-FETCH-001)

- `ci/batch-13` from `origin/main` `b632c5c` (writer `claude-batch-13`) merges, in order,
  `docs/docs-004-batch12-followups` `40e204b`, `feat/propagation-batch-001` `7022f8e`,
  `feat/care-bulk-001` `3490d18`, `feat/fn-05-directory-sort` `760283a` and
  `fix/media-fetch-001` `d2321c1`; only `docs/progress.md` conflicted and was resolved additively.
  The PROPAGATION-BATCH-001 milestone (source based on older `1a78476`) is moved back into merge
  order. Single Alembic head `20261125_0049` on `20261123_0048`. Evidence:
  [wf-04-batch-13.md](release/evidence/wf-04-batch-13.md).
- Checks on the integrated tree: `make api-generate` (no drift), `check-features.py` and
  `make check`. Canonical FULL follows the recorded exact-head review.

## 2026-11-24 — Batch 12 documentation follow-ups (`DOCS-004`)

- On `docs/docs-004-batch12-followups` from `origin/main` `1a78476` (writer `antigravity-neon`),
  docs-only third source for Batch 13.
- Updated [docs/features.json](features.json) entry `WF-BATCH-PROGRESS-001` so the first acceptance
  criterion states that entries inserted below `# Engineering progress` by two sources are both
  retained in merge order below the heading (matching `scripts/feature_batch.py`
  `additive_progress()`); checked `docs/development-workflow.md` and `docs/progress.md` (neither
  contained the wrong wording) and left historic manifests under `docs/release/evidence/batches/`
  untouched.
- Rewrote the optional botanical reference datasets snippet and intro sentence in
  [docs/installation.md](installation.md) so operators add the two `environment` list items and the
  `volumes` list item to the existing `backend` service lists without duplicating `environment:` or
  `volumes:` keys, keeping exact paths and environment variable names.
- Registered `DOCS-004` (`implemented`, proposed release class `best-effort`) next to `DOCS-003`
  (not at the tail) in `docs/features.json` and `docs/release/scope-v1.json`. Evidence:
  [docs-004.md](release/evidence/docs-004.md).
- Checks: `make doc-links`, `python3 ./scripts/check-features.py`, `make verification-plan FORMAT=json`
  (`tier: docs`), and canonical `make feature-verify AGENT_ID=antigravity-neon` (`docs` tier) on the
  frozen tip.

## 2026-11-24 — Batch pot-on and PlantGroup split (`PROPAGATION-BATCH-001`)

- On `feat/propagation-batch-001` from `origin/main` `1a78476` (writer `neon-propagation-batch-001`).
  No database migration, no new receipt kind or grouping ID, and `propagation/reversal.py` and
  `SowingDescendantWizard.tsx` remain untouched.
- Backend: added pure label-pattern module `backend/src/florabase/propagation/labels.py` (single-line
  normalization, `{n}` expansion with `counter_start`/`counter_padding`, 1–200 count limit, ≤255-char
  expanded-label validation); `POST /api/v1/sowings/{sowing_id}/pot-on` (`potOnSowing`) in
  `propagation/api.py` backed by `create_plants_from_sowing_batch` at the end of
  `propagation/service.py` (locks sowing once, checks `expected_sowing_updated_at` → 409
  `stale_preview`, rejects inactive/reversed sowings with 409, writes one existing `SOWING_TO_PLANT`
  receipt per created Plant in a single transaction, and applies `resulting_sowing_lifecycle` only on
  the Nth iteration so `REVERSAL-001` newest-first reversal restores Sowing and SeedLot);
  `POST /api/v1/plant-groups/{plant_group_id}/extract-batch` (`extractPlantsFromGroup`) in
  `plants/api.py` backed by `PlantGroupExtractBatchCreate`/`PlantGroupExtractBatchResponse` and
  `extract_plants_batch` appended at the end of `plants/schemas.py` and `plants/service.py` (loops
  existing `extract_plant`, caps exact-quantity groups at current quantity, allows approximate/unknown
  groups up to 200, preserves `PLANT-006` newest-first reintegration, rolls back atomically on
  mid-batch failure). Regenerated `backend/openapi.json` and `frontend/src/api/schema.d.ts`.
- Frontend: added `frontend/src/propagation/api.ts` and `frontend/src/propagation/PotOnDialog.tsx`
  with Sowing mode (N individual Plants via `potOnSowing` or one PlantGroup of N via existing
  `createPlantGroupFromSowing`), germinated hint, live `{n}` preview (first 3 + last), no-`{n}`
  warning, `ReferencePicker` identity/location selectors, smart Completed default when N ≥ germinated,
  explicit preview/confirm sentence, 409 `stale_preview` refresh, and links to created records;
  added minimal launchers in `sowings/SowingScreen.tsx` ("Pot on seedlings…") and
  `plants/PlantScreen.tsx` ("Split into plants…").
- Docs & manifests: updated `docs/domain-model.md`, registered `PROPAGATION-BATCH-001` (`implemented`,
  proposed class `best-effort`) right after `PROPAGATION-003` in `docs/features.json` and
  `docs/release/scope-v1.json`, and committed evidence in
  [propagation-batch-001.md](release/evidence/propagation-batch-001.md).
- Focused checks: `ruff format --check`, `ruff check`, `mypy` (0 issues), backend unit suite
  `backend/tests/propagation/test_propagation_batch.py` (8 passed) and `test_propagation.py` (16
  passed), `scripts/test_check_api_routes.py` (27 passed), PostgreSQL integration
  `backend/tests/integration/propagation/test_propagation_batch_api.py` (4 passed, incl. 12-plant
  pot-on + newest-first full reversal back to SeedLot, 5-plant exact split + newest-first
  reintegration, approximate split, mid-batch rollback, owner/CSRF), `make api-check` (no drift),
  frontend `pnpm typecheck`, `pnpm lint`, Prettier, Vitest (`PotOnDialog`, `GuidedForms`,
  `SowingScreen`, `PlantScreen` — 4 files, 135 passed), `scripts/check-features.py` (187 valid),
  `scripts/check-doc-links.py`, and headless Chromium visual checks at 1440×900 and 375×812 (zero
  overflow). Canonical `make feature-verify AGENT_ID=neon-propagation-batch-001` (`affected` tier)
  runs on the frozen committed tip.

## 2026-11-25 — CARE-BULK-001 + FN-03 bulk care logging, batch undo, and Watering/Feeding Journal kinds

- On `feat/care-bulk-001` from `origin/main` `b632c5c` (writer `neon`), scoped cleanly for Batch 13
  alongside `feat/propagation-batch-001` and `docs/docs-004-batch12-followups`.
- Added linear Alembic migration `20261125_0049_event_care_kinds.py` (`down_revision =
  "20261123_0048"`): acquires `LOCK TABLE events IN ACCESS EXCLUSIVE MODE`, recreates
  `ck_events_kind` with `watering` and `feeding` (`FN-03`), adds nullable `batch_id uuid`, and
  creates partial index `ix_events_batch_id WHERE batch_id IS NOT NULL`; downgrade refuses with an
  explicit error when watering or feeding events exist before removing the index/column and
  restoring the prior constraint.
- Extended `events/model.py` (`EventKind.WATERING`, `EventKind.FEEDING`, `batch_id`) and
  `events/service.py` (`create_event(..., batch_id: UUID | None = None)` with matching
  `created_at`/`updated_at` at creation and strictly advancing `updated_at` on edits). Marked
  `watering` and `feeding` as informational retainable observations for propagation creation
  reversal (`propagation/reversal.py`) and PlantGroup reintegration (`plants/service.py`,
  `plants/schemas.py`).
- Added bulk care backend modules `bulk/care_schemas.py`, `bulk/care_service.py`, and
  `bulk/care_api.py` (wired in `api/router.py` without touching BULK-001):
  `POST /api/v1/bulk/care/preview`, `POST /api/v1/bulk/care/apply`, and
  `DELETE /api/v1/bulk/care/batches/{batch_id}` (owner + CSRF, allowed kinds
  `watering`/`feeding`/`treatment`/`repotting`/`pruning`/`observation`/`other`, max 500 targets,
  selection or Location subtree CTE with ordered locking, SHA-256 `target_signature` → `409
  stale_preview`, empty/all-skipped → `422 nothing_to_log`, undo deleting only unedited events and
  returning kept edited ones). Regenerated `backend/openapi.json` and `frontend/src/api/schema.d.ts`
  (`make api-check` clean).
- Added frontend `bulk/careApi.ts` and `bulk/BulkCare.tsx` (`BulkCareDialog` with Today preselected
  via `OccurrenceDateChoice`, preview summary + skipped list, stale-preview refresh, and
  `BulkCareSuccessNotice` with **Undo**), wired `"Log care…"` in `BulkToolbar`
  (`bulk/BulkLocation.tsx`, shown only when every selected record is a Plant or PlantGroup), wired
  `"Log care for everything here…"` on active Locations (`locations/LocationScreen.tsx`), and added
  Watering/Feeding + the **Care** filter group to `events/eventData.ts` and
  `events/EventJournal.tsx`. With operator approval (2026-11-25), extended `events.category` in
  `frontend/src/saved-views/state.ts` and `backend/src/florabase/saved_views/state.py` to accept
  `"care"` (`max_length=4`) while preserving existing three-category Saved Views unchanged.
  Optional stretch (global Journal batch collapsing) was intentionally skipped to stay within the
  file boundary.
- Updated `docs/domain-model.md`, `docs/bulk-operations.md`, `docs/features.json` (`FN-03` and
  `CARE-BULK-001` placed right after `EVENT-002`, status `implemented`), `docs/release/scope-v1.json`
  (both `best-effort` right after `EVENT-002`), `docs/release/scope-v1.md`, and
  [`docs/release/evidence/care-bulk-001.md`](release/evidence/care-bulk-001.md). Verified desktop
  (`1280×800`) and phone (`390×844`) dialog captures with zero horizontal overflow; canonical FULL
  `make feature-verify AGENT_ID=neon` runs on the frozen committed tree.

## 2026-11-25 — UX-SORT-001 directory sort toolbar alignment and directory rollout

- On `feat/fn-05-directory-sort` from `origin/main` `b632c5c` (writer `neon-fn-05`).
- Fixed `.directory-tools .directory-sort` alignment in `frontend/src/styles/normalization.css` and
  `frontend/src/styles/directory-system.css`: cleared `.field`'s inherited `margin-bottom`, sized
  the `<select>` to `var(--control-height)` with matching `1px solid var(--border-strong)`,
  `var(--radius-small)`, `var(--type-body)`, and hover surface in light/dark themes, and kept it
  non-full-width (`flex: 0 1 auto; max-width: 100%`) on the phone tools row.
- Extended `sortDirectory` (`frontend/src/components/directorySort.ts`) and `DirectorySortSelect`
  (`frontend/src/components/DirectorySort.tsx`) with an optional name-only mode (`DirectoryNameSort`:
  `"" | "name" | "name_desc"`), preserving existing Seeds, Sowings and Plants behavior and labels.
- Rolled out `Sort by` before pagination with canonical URL and Saved View state (no migration, no
  OpenAPI change) to **Harvests** (dated by `occurred_on`, `dateLabel="harvest date"`), **Botanical
  identities** (name-only by `display_label`), **Stored material** (name-only by visible material +
  harvest title, keeping bulk selection aligned with sorted rows), and **Suppliers** (name-only by
  `name`), with matching `backend/src/florabase/saved_views/state.py` validation (`HarvestState`,
  `StoredMaterialState`, `NameSortedTextState`). Server-paginated directories (Cuttings, Orders,
  Media, History), trees/maps/analysis views (Locations, Geography, Taxonomy, Species distribution,
  Native ranges, Collection origins), and chronological feeds/agenda (Journal, Schedule) remain
  intentionally unsorted.
- Registered `UX-SORT-001` (`implemented`, `best-effort`) in `docs/features.json` and
  `docs/release/scope-v1.json`. Verified with unit, CSS regression, backend saved-view, and
  component tests plus canonical `make feature-verify AGENT_ID=neon-fn-05` at `440c328`.
- Renamed the identifier from `FN-05` to `UX-SORT-001` (writer `claude-batch13` after operator
  takeover) because `FN-05` is already the release task for Journal Today preselection with its own
  record in `docs/release/evidence/fn-05.md`; that record is unchanged. Evidence:
  [ux-sort-001.md](release/evidence/ux-sort-001.md).

## 2026-11-25 — MEDIA-FETCH-001 Wikipedia/Wikimedia local copies

- On `fix/media-fetch-001` from `origin/main` `b632c5c` (writer `claude-media-fetch`). No migration,
  no OpenAPI change.
- `media/fetch.py` now sends `Florabase/<__version__> media-copy (+https://github.com/alessandrorossato/florabase)`
  on every request and redirect, rewrites Wikipedia/Wikimedia `/wiki/File:` pages (canonical and
  localized namespaces) to `Special:FilePath` before fetching, and reports a 200 `text/html` page with
  a direct-address message. `ExternalAssetCreate`, record-photo `ExternalImageWrite` (create and
  update) and identity-cover `ExternalCoverWrite` store the rewritten `image_url` and keep the
  operator's `source_url`; Media metadata edits cannot change `image_url`.
- Focused: `tests/test_media_fetch.py`, `test_media.py`, `test_media_copies.py`,
  `test_collection_photos.py`, `test_identity_covers.py`, `test_primary_photo.py` (122 passed),
  ruff, ruff format, mypy. Evidence:
  `docs/release/evidence/media-fetch-001.md`.

## 2026-11-25 — IMPORT-002 spreadsheet wizard frontend pass

- On `feat/import-002-sheet-wizard` (writer `claude-import-002`), after merging `origin/main`
  `b632c5c` (MOBILE-002; only `docs/progress.md` conflicted). Review notes L1/L2 were already fixed
  in `7dcbfd8` (`neon`) and are covered by `test_xlsx_trailing_formula_only_row_detected_and_counted`.
- Added `frontend/src/import-export/SheetImportWizard.tsx` (six steps: upload with sheet and header
  row, row type, column mapping with browser-remembered mapping, grouped review of species,
  locations and suppliers with `WfoNameInput` reuse, rows with "Only problems", import result with
  links) and `sheetApi.ts`; launcher in `ImportExportScreen.tsx`, the per-type import marked
  Advanced and otherwise unchanged.
- Fixed a dead end found in the UI run: an empty first XLSX sheet made inspect fail before the sheet
  picker appeared; without an explicit sheet the parser now opens the first sheet with data.
- Checks: backend ruff, mypy, import unit suites (53 passed), IMPORT-001 + IMPORT-002 integration
  (20 passed); frontend Prettier, tsc, ESLint, Vitest `src/import-export` (8 passed); manual UI run of
  all seven samples on a UAT instance. Evidence: [import-002.md](release/evidence/import-002.md).
  Canonical FULL pending (operator).

## 2026-11-24 — IMPORT-002 single-sheet CSV/XLSX import wizard (backend pass)

- On `feat/import-002-sheet-wizard` from `origin/main` `ddf5a14` (writer `neon`); backend-only pass
  while waiting for `ci/batch-12` and `feat/mobile-002-device-auth` to land on `main` before the
  frontend wizard pass (which will reuse batch 12's `WfoNameInput`).
- Narrow refactor of `backend/src/florabase/import_export/service.py`: extracted
  `build_rows(kind, sources, refs)` from `preview(...)` and added optional `PendingReference`
  support (`pending=None` default) on `References` so preview can validate collection rows against
  not-yet-created identities, suppliers, and locations while keeping IMPORT-001 byte-identical.
- Added `backend/src/florabase/import_wizard/` (`sheet.py`, `mapping.py`, `schemas.py`,
  `service.py`, `api.py`), mounted from `import_export/api.py` under `/api/v1/sheet-imports/*`
  (`inspect`, `preview`, `apply`; `operation_id`s `inspectSheetImport`, `previewSheetImport`,
  `applySheetImport`) to avoid route collision with `/api/v1/imports/{kind}/*`.
  - Pinned `openpyxl==3.1.5` (MIT, pulls `et-xmlfile==2.0.0`, MIT) in `backend/pyproject.toml` and
    regenerated `backend/requirements.lock` and `backend/requirements-dev.lock`.
  - Enforced 2 MiB upload, 2,000 nonblank rows, 60 columns, one sheet, header row 1–10, 30 MiB
    uncompressed zip budget, 100:1 compression ratio, bounded `<!DOCTYPE`/`<!ENTITY` rejection,
    `read_only=True`/`data_only=True` cached-value-only parsing, and a bounded `data_only=False`
    second pass to flag uncached formulas as invalid if mapped and ignore them if unmapped.
  - Added EN/IT header auto-suggestions (`quantity_value` omitted for Plants), optional
    `append_unmapped_to_notes`, grouped identity/location/supplier review with near-match
    suggestions and explicit `skip` visibility ("will be left empty"), 15-minute session-bound
    HMAC-SHA256 confirmation, and single-transaction apply that creates identities → suppliers →
    locations, rebuilds `References` from the DB to re-run `build_rows`, and rolls back with `409`
    on any conflict or row-outcome drift.
- Copied synthetic fixtures from `import-samples.zip` as-is into `backend/tests/fixtures/sheet/`,
  added unit (`backend/tests/test_import_wizard.py`) and PostgreSQL integration tests
  (`backend/tests/integration/test_import_wizard_api.py`), regenerated `backend/openapi.json` and
  `frontend/src/api/schema.d.ts`, mapped `import_wizard/` and `fixtures/sheet/` in
  `scripts/verification-impact.json`, extended `docs/import-export.md`, and registered `IMPORT-002`
  (`in_progress` in `docs/features.json`, `best-effort` in `docs/release/scope-v1.json`, both right
  after `IMPORT-001`).
- Backend review fixes (`M1`, `M2`):
  - **M1 (confirmed preview state digest)**: added `preview_state_digest(plan)` over per-group
    `(key, action, matched_id)` for identities, locations, and suppliers plus `row_count` and
    per-row outcomes; bound it inside the HMAC confirmation token (`issued.preview_digest.sig`)
    and verified it inside `apply_sheet` before creating any entity (returning `409` `"validate
    again"` with zero writes when e.g. a Location with the same path is created between preview
    and apply).
  - **M2 (formatted blank XLSX rows)**: raised `MAX_SCANNED_ROWS` to `200_000`, enforced
    `MAX_ROWS` strictly on nonblank rows, stopped storing trailing/empty rows during CSV/XLSX
    scanning, and bounded the `data_only=False` formula pass by `last_nonblank_row` (verified on
    a 2-data-row XLSX with a formatted empty cell at `A50000`).
- Checks passed: `make check` (`doc-links` 364 docs, `format-check` 447 backend + Prettier, `lint`
  Ruff + ESLint, `typecheck` strict mypy 392 files + tsc, `api-check` zero drift, `test-backend`
  1356 passed / 3 skipped / 90.55% coverage, `test-frontend` 133 files / 1437 passed),
  re-verified after M1/M2 fixes with `ruff format --check`, `ruff check`, strict `mypy` (392
  files), `make api-check`, focused unit suite (`test_import_export.py`, `test_import_export_api.py`,
  `test_import_wizard.py`: 51 passed), and `./scripts/test-integration.sh` on
  `test_import_export_api.py` + `test_import_wizard_api.py` (20 passed), plus earlier
  `scripts/test_check_api_routes.py` (27 passed), `make license-check` (PyPI + 290 npm packages,
  0 forbidden), `scripts/check-features.py` (181 valid), and `scripts/test-verification-impact.py`
  (46 OK). Not yet run: frontend wizard UI (pending batch 12 + `MOBILE-002` merge into this branch)
  and final canonical FULL `make feature-verify`.

## 2026-11-23 — MOBILE-002 device sign-in, Keystore plugin, and compatibility contract (PWA preserved)

- On `feat/mobile-002-device-auth` from `origin/main` `ddf5a14` (writer `neon-mobile-002`).
- Added opaque 256-bit Bearer device sessions in PostgreSQL (`auth_sessions` extended via reversible
  Alembic migration `20261123_0048_device_sessions.py` with `transport`, `device_label`, nullable
  `csrf_digest`, and `ix_auth_sessions_user_transport`): `POST /api/v1/auth/device-sessions`
  (strict `application/json` 415 guard, shared Argon2id/`LoginThrottle`, 30d idle / 180d absolute,
  20 active session cap serialized under `_locked_user` `FOR NO KEY UPDATE` before `auth_sessions`
  `ORDER BY id FOR UPDATE` and evicting oldest-seen), `GET /api/v1/auth/device-sessions`,
  `DELETE /api/v1/auth/device-sessions/current` (Bearer-only),
  `DELETE /api/v1/auth/device-sessions/{session_id}`, and `DELETE /api/v1/auth/device-sessions`
  (available to any authenticated user for their own sessions, returning `404` cross-user).
  Enforced strict transport isolation (cookie+Bearer rejected `401` + `WWW-Authenticate: Bearer`;
  cookie-only `/auth/password`, `/auth/csrf`, `/auth/logout` reject Bearer `403`; password change
  revokes all browser + device sessions; browser cookie/CSRF/`require_origin` unchanged).
- Added automatic scoped native CORS (`NativeAppCorsMiddleware` in `backend/src/florabase/core/cors.py`):
  exact origins `https://localhost` and `capacitor://localhost` only, `allow_credentials=False`,
  active in `Environment.PRODUCTION` without relaxing the generic `FLORABASE_CORS_ORIGINS` guard.
- Added unauthenticated `GET /api/v1/system/info` (`server_version`, `api_version: 1`,
  `min_client_version: "0.1.0-beta.8"`, `capabilities: ["device-auth"]`) while keeping
  `GET /api/v1/health` untouched, and regenerated `backend/openapi.json` + `frontend/src/api/schema.d.ts`.
- Permanently renamed Android `applicationId`/namespace/package from `org.florabase.app` to
  `io.github.alessandrorossato.florabase`, removed Capacitor's `Example*Test.java`, set
  `loggingBehavior: "none"` in `mobile/capacitor.config.ts` so `SecureToken.set` never prints tokens
  to `logcat`, gated debug mixed-content strictly under `BuildConfig.DEBUG` in `MainActivity.java`,
  and added in-repo `SecureTokenPlugin.java` using direct `AndroidKeyStore` AES-256-GCM + app-private
  `SharedPreferences` (`allowBackup=false`, self-healing clear on decryption failure, `Build.MODEL`
  device-label prefill).
- Added frontend Bearer transport (`frontend/src/auth/transport.ts`), strict SemVer pre-release
  comparator (`frontend/src/mobile/semver.ts`), `NativeApp` compatibility + Keystore boot shell,
  `.catch` startup fallback in `frontend/src/main.tsx`, `NativeFileActionUnavailableError` for
  `downloadProtectedFile`/`openProtectedTab` (inline protected images via `useProtectedImage`
  working over Bearer), and **Connected devices** management in `Settings -> Account` (hiding the
  password form on native). Web bundle delta vs `ddf5a14`: `index-*.js` `+1,233 B` raw / `+339 B`
  gzip (`301,721 B -> 302,954 B`, `91,795 B -> 92,134 B`), `index-*.css` `+0 B`, zero `@capacitor/*`
  dependencies in `frontend/package.json`.
- Documented [ADR 0011](decisions/0011-mobile-device-sessions.md) (amending
  [ADR 0005](decisions/0005-authentication-and-sessions.md)), updated [docs/mobile.md](mobile.md),
  added `MobileReleaseContract` to `scripts/test-beta-runtime.py`, and registered `MOBILE-002`
  (`implemented`, proposed class `post-1.0`) in `docs/features.json` and `docs/release/scope-v1.json`.
- Verified `make mobile-android-debug` (`app-debug.apk`, 6.5 MB) and full 13-step live Android 16
  AOSP emulator (`florabase_api36`) end-to-end acceptance against an isolated worktree UAT instance
  (removed cleanly afterward): zero SW registrations, `/api/v1/system/info` check, `Build.MODEL`
  prefill, Keystore encrypted storage + zero token in WebView storage/Preferences/logcat, 3 inline
  protected blob images loaded, Bearer `POST`/`PUT` mutations, force-stop persistence, PWA device
  revocation, PWA password-change revocation, and explicit app sign-out. Canonical FULL
  `make feature-verify AGENT_ID=neon-mobile-002` runs on the frozen committed tree.

## 2026-11-24 — v0.1.0-beta.9 release preparation

- On `docs/release-beta-9` from `origin/main` `1a78476` (writer `claude-release-beta-9`). Version
  surfaces move to `0.1.0-beta.9` (`release/inputs.json`, backend package and module, frontend and
  mobile packages, both Dockerfiles, OpenAPI `info.version`). The Unreleased CHANGELOG section
  becomes the `v0.1.0-beta.9` entry: `FN-02`, `FN-04`, `UX-ENTRY-001`, `UI-REVIEW-002`,
  `RUNTIME-IDLE-001`, `DOCS-002` and `DOCS-003`, with beta.8 upgrade notes. PostgreSQL moves to
  `18.6-alpine-florabase.5` (same PostgreSQL 18.6 layout), no database migrations since beta.8, and
  `compose.yaml` changes are comments only. `docs/beta-data-001.md` names beta.9. `MOBILE-001` and
  workflow-only increments are not operator-facing and stay out of the CHANGELOG.
- No feature status changes. Tag, protected publication and publication evidence remain operator
  actions.

## 2026-11-23 — Batch 12 integration (WF-BATCH-PROGRESS-001, DOCS-003, FN-02/FN-04/UX-ENTRY-001, UI-REVIEW-002)

- `ci/batch-12` from `origin/main` `ddf5a14` (writer `claude-batch-12`) merges, in order,
  `ci/wf-batch-progress-001` `ea607ee`, `docs/docs-003-install-guide` `a2b5035`,
  `feat/fn-02-fn-04-list-ux` `66fec2f` and `fix/plants-list-reference-mount` `2c03a67`;
  `docs/progress.md` resolved additively; the `compose.yaml` line limit in
  `scripts/test-beta-runtime.py` is raised from 50 to 60 at the operator's request. Evidence:
  [wf-04-batch-12.md](release/evidence/wf-04-batch-12.md).
- Focused checks: `check-features.py`, `check-doc-links.py`, `test-doc-links.py`,
  `test-check-features.py`, `workflow-check` (incl. `test-beta-runtime`, 50-line `compose.yaml`) on
  the integrated tree; `test-agent-workflow` (81 OK, 3 skipped) and `workflow-check` on the
  WF-BATCH-PROGRESS-001 tip. Canonical FULL follows the recorded exact-head review.

## 2026-11-23 — Batch additive progress merge below the shared heading (`WF-BATCH-PROGRESS-001`)

- On `ci/wf-batch-progress-001` from `origin/main` `ddf5a14` (writer `claude-batch-progress-header`).
- `scripts/feature_batch.py` `additive_progress()` now sets aside the line prefix shared by the
  merge base and both sides (the `# Engineering progress` heading added by DOCS-002) before applying
  the unchanged additive rules, so two sources inserting milestones below the heading merge; edits to
  existing entries still refuse. Registered `WF-BATCH-PROGRESS-001` (`implemented`, proposed class
  `tooling`). Evidence: [wf-batch-progress-001.md](release/evidence/wf-batch-progress-001.md).
- Checks: the two additive progress tests in `scripts/test-agent-workflow.py`, a replay on the real
  Batch 12 revisions, `scripts/check-features.py`. Canonical FULL runs with Batch 12.

## 2026-11-23 — DOCS-003 installation guide accuracy fixes and v0.1.0-beta.8 publication record

- On `docs/docs-003-install-guide` from `origin/main` `ddf5a14` (writer `antigravity-docs-003`).
- Updated [docs/installation.md](installation.md), [docs/backup-restore.md](backup-restore.md),
  [README.md](../README.md) and [CHANGELOG.md](../CHANGELOG.md) (`Unreleased`) from the 2026-11-23
  operator rehearsal findings against the 40-line production `compose.yaml`:
  - Added a "Before you start" callout at the top of `docs/installation.md` and a bold sentence in
    `README.md`'s self-hosting paragraph pointing to the one-time folder setup block in § 1 before
    the first deploy.
  - Updated § Paired backup to state it runs over SSH in the folder holding the stack's
    `compose.yaml` (`docker compose ls`; Dockhand keeps its own copy), removed `.env`, and made
    archiving and checksumming `release-manifest.json` conditional on its presence while keeping
    `set -e`.
  - Replaced `FLORABASE_HTTP_PORT` with the host port of the `frontend` mapping (default `8080`),
    made editing the `frontend` port directly in the restore copy of `compose.yaml` the primary
    instruction when restoring on the same host (with `ports: !override` in `restore-override.yaml`
    noted as an option for Compose 2.24.4 or later), and noted that a restore drill on another Linux
    host needs `sudo` for `chown` and an `https://` `FLORABASE_CANONICAL_ORIGIN` (pointing to §
    Tailscale and HTTPS).
  - Replaced `<FLORABASE_DATA_DIR>` / `FLORABASE_BACKUP_DIR` placeholders with explicit mount-path
    descriptions (`your data folder (the left side of the /var/lib/florabase/data mount)` and `your
    backup folder (the left side of the /var/lib/florabase/backup mount)`), quoting only the exact
    `release_schema.py` mount-separation messages (`the data and backup folders are the same`,
    `the data folder is inside the backup folder`, `the backup folder is inside the data folder`).
  - Aligned § Synology NAS example paths with `compose.yaml` (`/volume1/docker/florabase/data` and
    `/volume1/docker/florabase/backup`) and noted that backups, restores and offline password
    resets need SSH access with the `docker compose` CLI on the NAS.
  - Stated in § Upgrade (and `docs/backup-restore.md`) that the automatic pre-upgrade dump is
    written only when the database Alembic revision changes (`release_schema.py` `upgrade`
    condition); image-only updates at the same head write none.
- Recorded [v0.1.0-beta.8 publication evidence](release/evidence/beta-8-publication.md) (workflow
  run `45124950700` attempt 1, annotated tag `3a6dc331ed0770cf24b171b4af650dbadda0585f` on commit
  `c4ffd63004bf4448af902ffb9a012f5d53f965bd`, Release asset SHA-256 digests, image index/platform
  digests from `release-manifest.json`, and verified `gh attestation verify` results for
  `release-manifest.json` and the three OCI images) and updated
  [docs/release/scope-v1.md](release/scope-v1.md) § Upgrade baseline.
- Registered `DOCS-003` (`implemented`, proposed release class `release-work`) in
  `docs/features.json` and `docs/release/scope-v1.json`, and wrote the handoff in
  [docs/archive/DOCS-003/handoff.md](archive/DOCS-003/handoff.md).
- Checks: `make verification-plan FORMAT=json` (`tier: docs`), `python3 scripts/check-features.py`,
  `python3 scripts/check-doc-links.py`, `python3 scripts/test-doc-links.py`, and canonical
  `make feature-verify AGENT_ID=antigravity-docs-003` (`docs` tier). Unresolved: none (`compose.yaml`
  header comment and `frontend/src/pwa/UpdateNotice.test.tsx` beta.7 fixture deferred to next
  product batch to keep `docs` tier).

## 2026-11-23 — Directory sort, searchable pickers and Save and add another (`FN-02`, `FN-04`, `UX-ENTRY-001`)

- On `feat/fn-02-fn-04-list-ux` from `origin/main` `ddf5a14` (writer `claude-pkg-b`). No migration,
  no OpenAPI drift, PWA behaviour unchanged; upgrade and backup paths untouched.
- FN-02: Seeds, Sowings and Plants gain a `Sort by` toolbar select (default, name A–Z/Z–A,
  newest/oldest by acquisition-or-harvest, sowing and collection-entry date; undated last). Sorting
  precedes browser pagination and `sort` is a canonical URL and Saved View field (frontend state
  and backend `saved_views/state.py`).
- FN-04: 13 reference selects over user data now use the shared keyboard-operable
  `ReferencePicker` (Plant, Sowing, Journal movement, descendant identity, Provenance site, native
  range, Geography parent, Location parent, Stored material location filter); the picker gains
  optional `id`, `name` and `describedBy`. Bounded enumerations stay native selects.
- UX-ENTRY-001: Save and add another in the Seeds, Sowings and Plants create forms keeps the form
  open with a fresh draft that retains only the identity (or SeedLot).
- `compose.yaml` header carries the one-time folder setup block; `UpdateNotice.test.tsx` fixtures
  moved to `0.1.0-beta.8`/`beta.9`. Registered FN-02, FN-04, UX-ENTRY-001 (`implemented`, proposed
  class `best-effort`). Evidence:
  [fn-02-fn-04-ux-entry-001.md](release/evidence/fn-02-fn-04-ux-entry-001.md).
- Focused checks in the Quality container: `pnpm typecheck`, `pnpm lint`, `pnpm format:check`,
  full `pnpm vitest run` (134 files, 1448 tests passed); backend `pytest tests/test_saved_views*.py`
  (94 passed), `ruff check`, `ruff format --check`, `mypy`; `export_openapi.py` without drift;
  `scripts/test-beta-runtime.py StackContract` (16 passed); `scripts/check-features.py`.
  Canonical FULL not yet run; independent review pending. Not checked: real-browser visual review
  of the new toolbar select and pickers.

## 2026-11-23 — Post-beta.8 review fixes: directory cards, WFO suggestions, reference mount, media layout (`UI-REVIEW-002`)

- On `fix/plants-list-reference-mount` from `origin/main` `ddf5a14` (writer `claude-batch13-impl`),
  a fourth Batch 12 source. Gallery directories keep card-sized tracks for one or two records; the
  identity create form suggests WFO names through read-only `GET /api/v1/explore/taxonomy/candidates`;
  `compose.yaml` points to the read-only WFO/WCVP v16 mount snippet in installation; the
  identity Media tab and media asset page are simplified and external covers save a local copy by
  default. Evidence: [ui-review-002.md](release/evidence/ui-review-002.md).
- Checks: focused backend taxonomy tests, ruff, mypy; frontend typecheck, ESLint, Prettier and Vitest
  on the touched areas. Canonical FULL runs with Batch 12; layout pending operator approval.

## 2026-11-23 — MOBILE-001 Capacitor Android shell spike (PWA preserved)

- On `feat/mobile-001-capacitor-spike` from `origin/main` `68e9449` (writer `neon-mobile-001`).
- Added Capacitor 8 Android shell under `mobile/` (`@capacitor/{core,android,cli}@8.6.2`,
  `@capacitor/preferences@8.0.1`, `@capacitor/app@8.1.2`, `pnpm@11.19.0`, Node `24.x`, Android
  platform only, `com.google.gms:google-services` removed for F-Droid cleanliness) consuming
  `../frontend/dist` with zero backend, auth, CORS, CSP, or PWA changes.
- Added runtime native detection (`frontend/src/mobile/runtime.ts`, reading Capacitor's injected
  `window.Capacitor.isNativePlatform()` with zero `@capacitor/*` imports in `frontend/package.json`
  or the web bundle) and gated `frontend/src/main.tsx` so native builds skip
  `registerServiceWorker()` and `<UpdateNotice />` and lazy-load `NativeServerOnboarding`
  (web entry delta: `+584 B` raw / `+194 B` gzip; `index-*.css` `+0 B`; `/sw.js` preserved).
- Added native Server URL onboarding (`frontend/src/mobile/`): `https://` required in release,
  `http://10.0.2.2` and private LAN allowed only in debug builds, `GET /api/v1/health` + optional
  `/release.json` probe via native `CapacitorHttp`, URL persistence via Capacitor Preferences,
  distinct error states (invalid URL, unreachable, TLS CA, cleartext, non-Florabase), and the
  `MOBILE-002` sign-in placeholder.
- Added `mobile/android/app/src/main/res/xml/network_security_config.xml` (release: no cleartext,
  trusts `system` + `user` CAs) and `src/debug/res/xml/network_security_config.xml` (debug local
  HTTP overlay), root and Android `.gitignore` rules for APKs/keystores/Gradle/`local.properties`,
  and `make mobile-sync` / `make mobile-android-debug` targets in `Makefile`.
- Classified `mobile/` and `frontend/src/mobile/` under non-FULL, non-golden `mobile` scope in
  `scripts/verification-impact.json` with regressions in `scripts/test-verification-impact.py`,
  permitted the standard `10.0.2.2` emulator loopback alias in `scripts/test-beta-runtime.py`,
  documented setup and architecture in [docs/mobile.md](mobile.md) and
  [docs/mobile-001-adr.md](mobile-001-adr.md), and registered `MOBILE-001` (`implemented`,
  proposed release class `post-1.0`) in `docs/features.json` and `docs/release/scope-v1.json`.
- Verified `make mobile-android-debug` (`app-debug.apk`, 6.5 MB) and live Android 16 AOSP emulator
  (`florabase_api36`): zero service-worker registrations, distinct invalid/unreachable/non-Florabase
  errors, `http://10.0.2.2:5173` `/api/v1/health` OK, Preferences persistence across force-stop
  restart, and observed WebView `fetch` / `Origin` / `SameSite=Strict` / CORS login blockers.
  Canonical `make feature-verify AGENT_ID=neon-mobile-001` runs on the frozen committed tree.

## 2026-11-23 — Lower idle container CPU, probe log filter, startup banner, and settings error diagnostics (`RUNTIME-IDLE-001`)

- On `feat/runtime-idle-001` (rebased onto `1d4e0ba`, writer `antigravity`).
- Replaced the Python `/api/v1/ready` backend image `HEALTHCHECK` with busybox `wget` against
  `/api/v1/health` (`--interval=30s --timeout=5s --start-period=60s --start-interval=2s --retries=3`),
  moved `postgres/Dockerfile` (`18.6-alpine-florabase.5`, reproducible index
  `sha256:8397c577...`, platform `sha256:8b9e1108...`) and `frontend/Dockerfile` to 30 s intervals
  with `--start-interval`, keeping `compose.yaml` and `compose.dev.yaml` untouched (ADR 0009) and
  `/api/v1/ready` unchanged. Verified `moby/moby` `v24.0.2` ignores unknown `StartInterval` in OCI
  image configs (`image.NewFromJSON` uses `encoding/json.Unmarshal`).
- Added `HealthProbeAccessFilter` on `uvicorn.access` (drops loopback 2xx `GET /api/v1/health` and
  `/api/v1/ready` only), plain-ASCII ≤ 72-column startup banner as the first stdout output of
  `release_schema wait-db` (`FLORABASE_REVISION` exposed from `ARG REVISION`), and
  `pydantic.ValidationError` field-name reporting across all `release_schema` actions without
  leaking input values, context, URLs, or secrets.
- Measured on disposable `compose.yaml` stack (120 s idle cgroup CPU delta, before vs after):
  `backend` 3,970.01 ms (3.31%) → 398.88 ms (0.33%, −90.0%), `db` 1,172.29 ms (0.98%) → 341.43 ms
  (0.28%, −70.9%), `frontend` 425.58 ms (0.35%) → 138.13 ms (0.12%, −67.5%); backend idle access
  logs 12 → 0; single backend probe wall time (10 runs) 340.70 ms → 63.11 ms median (−81.5%).
- Checks: `beta_release.py postgres-identity --check` (`POSTGRES_IDENTITY_REPRODUCED`),
  `make smoke-beta-images` (`LOCAL_BETA_CANDIDATE_PASSED`), `scripts/smoke-portable-compose.py`
  passed, `make feature-verify AGENT_ID=antigravity` (FULL). Unresolved: none.

## 2026-11-23 — WF-CLEANUP-001 finish auto-retirement, Golden closure and review residue

- On `ci/wf-cleanup-001` from `origin/main` `c4ffd63` (writer `neon`).
- **Auto-retirement on finish & batch finish:** Factored `retire_path()`, `is_managed_worktree()`,
  `retire_finished_worktree()` and `retire-finished --path <abs>` out of `retire()` in
  `scripts/feature_worktree.py` so `scripts/feature-finish.sh` (from the primary checkout via final
  `exec`) and `scripts/feature_batch.py finish()` reuse every retirement guard (operator identity,
  managed marker directly under `florabase-worktrees/`, locks, finish proof, clean/ignored checks,
  Docker resource and running-mount guards, mountinfo/symlink/permission preflight, non-forced
  `git worktree remove`). Managed worktrees auto-retire best-effort (`WORKTREE: RETIRED <path>` /
  `FINISHED <branch> at <tip>; RETIRED <path>`); any refusal or `KEEP_WORKTREE=1` retains the
  worktree with exit code 0, exact reason and follow-up command (`WORKTREE: RETAINED <path>
  (<reason>)`). Provider-managed worktrees are never touched. Updated `Makefile` (`KEEP_WORKTREE`
  export + help), `AGENTS.md`, `docs/development-workflow.md`, `scripts/test-agent-workflow.py`,
  and `scripts/test-workflow-helpers.sh`.
- **Agent post-delivery guidance:** Documented the 3-step post-delivery worktree removal rule for
  provider-managed worktrees in `AGENTS.md`, `docs/development-workflow.md`, and
  [agent-prompt-template.md](agent-prompt-template.md).
- **Verification impact & Golden closure:** Added `backend/alembic.ini`, `backend/scripts/` and
  `postgres/` to `golden_prefixes` and classified `backend/scripts/check_api_routes.py` and
  `backend/scripts/test_check_api_routes.py` under `product_backend_prefixes` (product tier backend
  ALL + `golden-dataset`, no FULL escalation) in `scripts/verification-impact.json`, with focused
  regressions in `scripts/test-verification-impact.py`.
- **No `assert` in container smoke snippets:** Replaced `assert` checks inside container Python
  snippets in `scripts/smoke-beta-images.py` (dev-tool check, now naming offending packages via
  `sys.exit`) and `scripts/smoke-uat-preview.py` (relationship/photo checks via `RuntimeError`) and
  in the `scripts/test-beta-images.py` fake-checker fixture, with an offline `python -O` regression
  in `scripts/test-beta-images.py`.
- **Batch 11 P3 notes, L5 closure & operator dispositions (2026-11-22):**
  - Promoted `INSTALL-003` to `verified` in `docs/features.json` (normalized multi-line
    `dependencies`, citing [wf-04-batch-11.md](release/evidence/wf-04-batch-11.md)) and updated the
    stale UI-REVIEW-001 gate-rerun pointer below.
  - Closed L5 review residue: verified `scripts/beta_release.py` `compose_template()` binds the
    tracked `compose.yaml` by SHA-256 in the `compose_template` field of the attested
    `release-manifest.json` (`release/manifest.schema.json`, `.github/workflows/beta-images.yml`),
    and appended the resolution note to the historical INSTALL-001 residual below.
  - Applied operator dispositions (option (a), 2026-11-22): `BETA-RUNTIME-001` moved to
    `implemented` / `record` (`docs/features.json`, `docs/release/scope-v1.json`,
    `docs/release/feature-reconciliation-v1.md`) with its real-host persistence, paired
    backup/restore, HTTPS/origin/CSRF and failure-recovery gates folded into `BETA-ACCEPTANCE-001`
    (retaining `BETA-RUNTIME-001` in `dependencies`); `ENG-03` confirmed `best-effort` across
    `docs/release/feature-reconciliation-v1.md`, `docs/release/scope-v1.md` and
    `docs/release/scope-v1-handoff.md`.
  - Registered `WF-CLEANUP-001` (`implemented`, proposed release class `tooling`) in
    `docs/features.json` and `docs/release/scope-v1.json`.
- Focused checks before canonical FULL: `test-agent-workflow.py` (80 OK, 3 skipped),
  `test-workflow-helpers.sh` (pass), `test-feature-workflow.py` (55 OK),
  `test-verification-impact.py` (45 OK), `test-stage-evidence.py` (22 OK),
  `test-check-features.py` (26 OK), `workflow-check` (82 `test-beta-images` + 4 lock + 16
  `test-beta-runtime` + Dependabot policy + Ruff + strict mypy across 49 scripts),
  `check-features.py` (177 valid; `--release-candidate` blockers unchanged: `RELEASE-001`,
  `BETA-IMAGE-001`, `beta-postgres-repro-001`, `BETA-SECURITY-001`, `BETA-DATA-001`,
  `BETA-ACCEPTANCE-001`), `check-doc-links.py` (357 docs), and `test-doc-links.py` (4 OK).
  Canonical FULL (`make feature-verify AGENT_ID=neon`) runs on this frozen committed head before
  operator delivery; no push, PR or merge.

## 2026-11-23 — DOCS-002 root community docs, licensing notices and docs/ tidy-up

- Implemented on `docs/docs-001` from `origin/main` `c4ffd63` (`v0.1.0-beta.8`, writer
  `neon-docs-001`). Note: `DOCS-001` already existed as a verified baseline entry in
  `docs/features.json`, so this increment uses the next free identifier `DOCS-002` (proposed
  release class `best-effort` in `docs/release/scope-v1.json`).
- **Part A (root community & licensing docs)**: rewrote `README.md` "What works today" around the
  UI navigation names from `frontend/src/shell/navigation.ts`, folded the Docker Compose merge
  rules link into Requirements, shortened self-hosting to point to `docs/installation.md`, updated
  visibility wording to "public pre-release (beta) series" (verified public repo and public GHCR
  manifests), and added copyright (`Alessandro Rossato`), `THIRD-PARTY-NOTICES.md` and
  `docs/README.md` links. Updated `CONTRIBUTING.md` with an external-contributor section
  (issue-first, focused PRs, AGPL-3.0-or-later inbound=outbound, DCO `git commit -s`, respectful
  conduct without a separate CoC, `SECURITY.md`) above the preserved maintainer/agent workflow,
  added a DCO checkbox to `.github/pull_request_template.md`, updated `SECURITY.md` supported
  versions for the latest published beta while retaining the 1.x row and GitHub private reporting,
  added `Alessandro Rossato` author metadata to `backend/pyproject.toml` and
  `frontend/package.json` without editing `LICENSE` or beta.8 version surfaces, and added root
  `THIRD-PARTY-NOTICES.md` from committed notices and `DataSourcesScreen.tsx`.
- **Part B (`docs/` structure & links)**: added [`docs/README.md`](README.md) indexing living
  guides and marking `docs/review/` and `docs/release/evidence/` as historical evidence; moved 72
  finished (`implemented`/`verified`) increment artefacts via `git mv` into
  `docs/archive/<FEATURE-ID>/` (preserving all living guides, `in_progress`/`planned` feature docs,
  and all script/code-referenced paths); updated 367 relative Markdown links plus
  `docs/features.json`; split `docs/progress.md` verbatim at `v0.1.0-beta.7` into
  [`docs/archive/progress-until-beta-7.md`](archive/progress-until-beta-7.md) (redacting one
  pre-existing personal home path flagged by `test-beta-runtime.py`); documented ongoing placement
  and no-committed-review-screenshot conventions in `AGENTS.md` and `docs/development-workflow.md`;
  wired `doc-links` (`scripts/check-doc-links.py`) into `make check`.
- **Part C (cheap doc-only verification & licence audit)**: moved `LICENSE` from `full_prefixes` to
  `documentation_paths` alongside `SECURITY.md`, `CHANGELOG.md`, and `THIRD-PARTY-NOTICES.md` in
  `scripts/verification-impact.json`, updated `scripts/test-verification-impact.py`, and added
  local `make license-check` (`scripts/license_check.py`, `scripts/license_check_npm.mjs`; no CI
  job). Full move inventory and operator TODOs are in
  [`docs/archive/DOCS-002/docs-002-handoff.md`](archive/DOCS-002/docs-002-handoff.md).
- Checks: `python3 scripts/check-doc-links.py` (360 documents), `python3 scripts/test-doc-links.py`
  (4 OK), `python3 scripts/check-features.py` (177 valid), `python3 scripts/test-check-features.py`
  (26 OK), `python3 scripts/test-verification-impact.py` (43 OK), `make test-agent-workflow` (76 OK,
  3 skipped), `make license-check` (PyPI 53 packages, npm 290 packages, 0 forbidden), followed by
  canonical `make feature-verify AGENT_ID=neon-docs-001` (FULL).

## 2026-11-22 — v0.1.0-beta.8 release preparation

- Version surfaces move to `0.1.0-beta.8` (`release/inputs.json`, backend package and module,
  frontend package, both Dockerfiles, OpenAPI `info.version`). The Unreleased CHANGELOG section
  becomes the `v0.1.0-beta.8` entry: minimal `:latest` three-service `compose.yaml` (#214, #216),
  `LINEAGE-004` and `UI-REVIEW-001`, and a note that a Compose-manager update pulls the current
  `:latest` images including rebuilt `florabase-postgres` images within PostgreSQL 18.
  PostgreSQL moves to `18.6-alpine-florabase.4`, published for the first time by this release.
  `docs/beta-data-001.md` names beta.8 and the backend deploy step instead of the removed
  `migrate` service.
- No feature status changes. Tag, protected publication and publication evidence remain operator
  actions.

## 2026-11-22 — WF-04 Batch 11 integration (`INSTALL-003` + `UI-REVIEW-001` / `LINEAGE-004`)

- Prepared `ci/batch-11` on top of pinned `origin/main` (`ef5451f`, includes #215) with writer
  `neon` via `make feature-batch-plan` and `make feature-batch-prepare`.
- Merged `INSTALL-003` (`feat/install-003-latest-compose` at `ac93677`, merge `fae46af`) and
  `UI-REVIEW-001` with `LINEAGE-004` (`fix/ui-ux-review` at `27ece94`, merge `76b0479`) without
  rewriting source branches. `README.md`, `docs/features.json` and `docs/release/scope-v1.json`
  merged cleanly keeping all 176 features; `docs/progress.md` resolved additively and was
  reconciled newest-first (`INSTALL-003`, `UI-REVIEW-001`, `LINEAGE-004` above `VERIFY-SPEED-001`,
  retaining `1e985f1`'s tail UAT smoke milestone).
- Recorded [Batch 11 provenance](release/evidence/wf-04-batch-11.md) and
  [batch-11.json](release/evidence/batches/batch-11.json). Proposed release classes in
  `docs/release/scope-v1.json`: `INSTALL-003` (`release-work`), `UI-REVIEW-001` (`best-effort`),
  `LINEAGE-004` (`best-effort`).
- Exact-head independent batch QA (`make feature-batch-review`) and one fresh canonical FULL gate
  (`env -u REUSE FRESH=1 make feature-verify AGENT_ID=neon`) run on this frozen committed head
  before operator delivery.

## 2026-11-22 — INSTALL-003 directly usable `:latest` `compose.yaml` (ADR 0010)

- On `feat/install-003-latest-compose` from `16ccf4b` (writer `antigravity-install-003`).
- Adopted [ADR 0010](decisions/0010-deployable-latest-compose.md) amending
  [ADR 0009](decisions/0009-minimal-production-compose.md): `compose.yaml` on `main` is now a
  directly usable 40-line file referencing `:latest` images
  (`ghcr.io/alessandrorossato/florabase-{postgres,backend,frontend}:latest`), plain short bind
  mounts with Synology-style absolute host path examples, plain environment literals (no `.env` or
  Compose interpolation), header folder-setup instructions, and no custom networks (`internal: true`
  and `app` moved to the optional hardened override in [docs/security.md](security.md)).
- Added `change-me` placeholder password refusal in both
  `postgres/florabase-postgres-entrypoint.sh` (reproduced `18.6-alpine-florabase.4` at
  `index_digest` `sha256:2d843bd2ac7e9cebc4b4aaed2d24bb6f7717261fa27e798fe1f28583e853d625`,
  `platform_digest` `sha256:c677e9e20e56d6c32c2d359f66b44b66e2ead27d51fcaa64528f78a88299589d`) and
  `backend/src/florabase/db/release_schema.py`.
- Removed `FLORABASE_DATA_DIR` / `FLORABASE_BACKUP_DIR` env vars from `compose.yaml`; added
  `/proc/self/mountinfo` identical/nested bind-mount detection in `release_schema.py` (including
  btrfs subvolumes, warning and continuing on indeterminate mountinfo and refusing on positive
  detection).
- Updated `scripts/beta_release.py`, `scripts/publish-beta-images.py` and
  `.github/workflows/beta-images.yml`: dropped `render_compose()` and the rendered `compose.yaml`
  release asset/attestation (keeping OCI image + `release-manifest.json` attestations), and added
  `:latest` promotion alongside versioned tags with a code-enforced PostgreSQL 18 major guard.
- Updated `docs/installation.md`, `docs/security.md`, `README.md`, `CHANGELOG.md`,
  `docs/security/beta-distribution-001/postgresql-image.md`, `docs/features.json` (`INSTALL-003`
  `implemented`) and `docs/release/scope-v1.json` (`INSTALL-003` proposed class `release-work`).
- Checks passed: `make format-check lint typecheck test-backend` (1300 passed, 90.18% coverage),
  `make workflow-check` (81+4 release tests, 16 beta-runtime tests, ruff/format/strict mypy),
  `python3 scripts/test-environment-workflow.py` (44 OK), `python3 scripts/check-features.py`,
  `python3 scripts/beta_release.py check --publication`,
  `python3 scripts/beta_release.py postgres-identity --check` (`POSTGRES_IDENTITY_REPRODUCED`), and
  live disposable `scripts/smoke-portable-compose.py` against `compose.yaml`. Not run: full
  `make feature-verify` (not yet committed/pushed per operator Phase 2 instructions).

## 2026-11-22 — UI-REVIEW-001 operator UI/UX review (with LINEAGE-004 merged)

- On `fix/ui-ux-review` from `1e985f1` (writer `claude-ui-review`); LINEAGE-004 (`77b8b54`) merged in
  at the operator's request so one FULL and one delivery cover both. Bugs and visual alignment only.
- Harvests/Stored material use the Cuttings record-type switch (`.directory-surfaces`) under the
  search in both views. One List/Gallery toggle and one Agenda/Calendar toggle name the view they open.
- Workbench: Saved views are sub-items of their owning section (five, then "Show all"), with a
  hover/focus remove control confirmed in a dialog (`DELETE /api/v1/saved-views/{id}`); the separate
  panel group and the Today "all views" list are gone. `sectionOfHash` is shared with `workspaceOfHash`.
- Journal/History/Schedule headers follow the directory grammar; Schedule month is one compact row of
  controls with viewport-sized cells and 24px pointer targets (44px kept for touch).
- Taxonomy: absolutely positioned sr-only text escaped the review list and grew the document by
  ~2,500px; the list now contains it. Gallery plates no longer centre inside stretched card buttons.
- Maps: Collection origins and Species distribution use the Native ranges metric cards; Online basemap
  is shown only when `mapOnlineEnabled` is set (Species distribution previously ignored the flag).
- Themes: the Field Ledger system (fonts, radii, controls) applies to every palette; Field Ledger is
  labelled Botanical, the old Botanical palette is retired (stored choice falls back), Herbarium and
  Mineral gain rail and lineage colours (contrast-tested). Settings and identity lineage gain breadcrumbs.
- Later rounds: Cuttings rows use the shared Details/Edit actions (`?action=edit` opens the edit
  dialog); Explore titles equal their menu entries (Taxonomy, Collection origins, Species
  distribution, Native ranges, Places); Taxonomy uses one List/Tree toggle with icons and an inline
  stage; Lineage home shows metric cards and an identity gallery on a dotted stage; record lineage
  cards share one grammar; Settings adds **Help** (built from the navigation) and a static **Data
  sources** page (current references, access rules, planned integration standard).
- README: `docs/assets/readme-showcase.png` mosaic (desktop and phone) from the Feature Review dataset with demo names and WFO links applied only to that disposable Review database.
- Record ancestry (`#/lineage/<kind>/<id>`) now belongs to Explore → Lineage with breadcrumbs; record pages keep their Lineage tab and link there. The record-type switch is a `DirectoryTools` `surfaces` slot directly under the toolbar.
- Checks: frontend typecheck, ESLint, Prettier and the full Vitest suite (128 files, 1419 tests) in the
  Review container; browser review on Feature Review at 1440×900, 768 and 375, light and dark.
  Canonical gate: `make feature-verify` (tier full, after merging `origin/main` at `16ccf4b`) passed
  all stages, including quality, production builds, migration cycle and integration (1324.6s).
  Two earlier attempts failed for environmental reasons: WCVP/WFO indexes copied into this
  worktree's ignored `backend/src/.source-cache/` for the Review screenshots made
  `test_missing_v16_keeps_v15_link_current_without_silent_fallback` see a real v16 index (cache
  removed), and `PlantScreen.test.tsx` "detail loading, detail failure, authorization, and session
  expiry" failed once under full-suite load but passes in isolation and on rerun (possible flake).
- Independent QA (read-only, detached `3c55bdc`): no P0/P1. Fixed every P2: focus returns to the
  owning section link after a saved-view removal and an expired session shows an error; Cuttings
  `?action=edit` no longer opens editing for reversed attempts and is cleared on close; the Taxonomy
  tree scroller also contains sr-only text; the Lineage gallery shows counts with " · " (no implied
  ancestry), uses `display_label` for cultivars and handles 401; Data sources describes all GBIF
  online requests and WCVP CC BY 3.0. P3: remove-button hover specificity, one `aria-current` per
  view, compact "+N more" in the Schedule month, occurrence tile guard and basemap copy, palette test
  names plus an explicit retired-Botanical fallback test, docs (lineage routes, page inventory nav),
  refreshed README showcase. Canonical gate rerun after these fixes was the Batch 11 FULL recorded
  in the Batch 11 milestone above and [wf-04-batch-11.md](release/evidence/wf-04-batch-11.md).
  UI-REVIEW-001 and LINEAGE-004 are marked verified. Release class proposed for the operator for
  UI-REVIEW-001: `best-effort`.

## 2026-11-22 — LINEAGE-004 identity lineage in Explore

- On `feat/lineage-004` from `1e985f1` (writer `claude-lineage004`). Reuses the LINEAGE-003 explorer.
- Backend: `GET /api/v1/lineage/identities/{identity_id}/graph` (`getIdentityLineageGraph`) returns
  one BotanicalIdentity's records (Sowings and rooting attempts through their own source lot) with
  only explicit edges from the explorer's source columns; linked records of other identities are
  flagged `in_identity=false`; bounded at 500 with `truncated`, never presenting a left-out member as
  foreign; 404 `botanical_identity_not_found`. No schema change.
- Frontend: Explore → **Lineage** (`#/lineage`) searches identities, Seed lots, Sowings, Plants and
  Plant groups via `/api/v1/search`; `#/lineage/identity/<id>` draws one stem per recorded line,
  with outside-identity cards, references for multi-parent records and a separate list of records
  without recorded relationships. The identity overview links to it. New `lineage` icon and section.
- Checks (cloud session, outside Docker: the quality images cannot fetch dependencies through the
  session proxy): ruff check/format and strict mypy clean; backend unit suite 1281 passed with
  coverage 90.15% (3 failures are root/host-path environment tests, unrelated); PostgreSQL 16
  integration `test_lineage_api.py` 14 passed; frontend tsc, ESLint and Prettier clean; lineage and
  navigation tests pass; the remaining 46 frontend failures are identical on `origin/main` under the
  session's Node 22 (the project pins Node 24). OpenAPI regenerated with the locked dependencies.
  Visual check of both pages at desktop and phone width, no horizontal overflow.
- Not run: FULL `make feature-verify`, `make api-check` (both need the Docker quality stack).
  Release class proposed for the operator: `best-effort`.

## 2026-11-22 — VERIFY-SPEED-001 canonical FULL wall-time optimization

- On `ci/verify-speed-001` from `origin/main` `16ccf4b` (writer `neon`).
- Split `backend/tests/integration/test_golden_dataset.py` out of the default integration run using
  the same explicit-selection fixture as `test_golden_comprehensive.py` (`SEARCH_PATH =
  "test_golden_dataset"`), preserving `test_the_full_suite_skips_the_comprehensive_module` and
  adding `test_the_full_suite_skips_the_golden_dataset_module` and updating the stale default-CI
  comment in `test_comprehensive_does_not_touch_the_smoke_plan`. Added validated `golden_prefixes`
  to `scripts/verification-impact.json` covering the full Golden import and runtime closure
  (`backend/src/florabase/`, `backend/alembic/`, `backend/pyproject.toml`, `backend/requirements`,
  `backend/uv.lock`, `backend/Dockerfile`, `compose.dev.yaml`, `Makefile`,
  `scripts/test-integration.sh`, Golden/fixture scripts, and integration test fixtures),
  `golden_dataset` selection (closure-triggered or fail-closed on unclassified paths) in
  `scripts/verification_impact.py`, the non-reusable `golden-dataset` stage
  (`make golden-dataset-check`) in `scripts/verification_gate.py`, and exhaustive `main` push CI
  coverage in `scripts/ci-verify.py`.
- Enabled Vitest file parallelism in `frontend/vite.config.ts` (`fileParallelism: true`,
  `pool: "forks"`, `maxWorkers` defaulting to `3` via `VITEST_MAX_WORKERS`, keeping `testTimeout:
  15_000`) and lifted the pinned `VITEST_MAX_WORKERS: "1"` in `scripts/compose_stacks.py` to
  `"${VITEST_MAX_WORKERS:-3}"`. Five consecutive `make test-frontend` runs passed (127 files,
  1,414 tests each, zero retries): `96.84 s`, `98.33 s`, `96.01 s`, `96.12 s`, `96.43 s` (down
  from `~258 s` serial locally).
- Consolidated `workflow-check` in `Makefile` from 7 separate backend container runs into one
  container invocation with shared file-list Make variables, run-all failure reporting, and a
  worktree-owned disposable mypy cache under `<git-dir>/florabase-mypy-workflow-cache` (verified
  host-UID owned, zero root-owned files; `33.06 s` before -> `27.16 s` cold / `23.73 s` warm).
- Hygiene: removed retired `deploy/` from `full_prefixes`, added manual `make smoke-beta-lifecycle`
  and documented `scripts/test-beta-lifecycle.py` in `docs/beta-image-001-final-reliability.md`,
  profiled all 22 tests in `scripts/test-stage-evidence.py` (`110.26 s` total; fixtures retained
  unchanged to preserve subprocess/Git coverage), and recorded the two-lane gate design note in
  [VERIFY-SPEED-001](archive/VERIFY-SPEED-001/verify-speed-001.md) without implementing parallel lanes.
- Registered `VERIFY-SPEED-001` (`implemented`, proposed release class `tooling`) in
  `docs/features.json` and `docs/release/scope-v1.json`.
- Focused checks before canonical FULL: `test-verification-impact.py` (43 OK),
  `test-stage-evidence.py` (22 OK, 110.26 s), `test-check-features.py` (26 OK),
  `test-feature-workflow.py` (55 OK), `test-environment-workflow.py` (44 OK),
  `make golden-dataset-check` (35 passed in 349.73 s), `make test-frontend` ×5 (5/5 passed),
  `make workflow-check` (cold + warm pass), `check-features.py`, `check-doc-links.py`, and
  `test-doc-links.py`. Canonical FULL (`env -u REUSE FRESH=1 make feature-verify AGENT_ID=neon`)
  runs on this frozen committed tree; no push, PR or merge.

## 2026-11-22 — WF-04 Batch 10 integration (`WF-SCOPE-001` + `INSTALL-002`)

- Prepared `ci/batch-10` on top of pinned `origin/main` (`1e985f1`) with writer `neon` via
  `make feature-batch-plan` and `make feature-batch-prepare`.
- Linear bootstrap commit `b51e2b3` updated `additive_progress` in `scripts/feature_batch.py` (with
  regression coverage in `scripts/test-agent-workflow.py`) so pure top-of-file progress prepends
  preserve non-conflicting tail edits on `main` (such as PR #213's `1e985f1` entry) while staying
  fail-closed on edits inside existing progress content.
- Merged `INSTALL-002` (`feat/install-002-minimal-compose` at `a012f43`, including `internal: true`
  and `app` network isolation in `compose.yaml`, `scripts/test-beta-runtime.py`,
  `scripts/test-beta-images.py`, `scripts/smoke-portable-compose.py`, ADR 0009 and
  `docs/security.md`, merge `b150388`) and `WF-SCOPE-001` (`feat/wf-scope-001-scoped-verification`
  at `1b78a04`, merge `b34ab43`) without rewriting source branches. `docs/features.json` and
  `docs/release/scope-v1.json` merged cleanly; `docs/progress.md` resolved additively keeping all
  entries newest-first alongside `1e985f1`'s tail milestone.
- Recorded [Batch 10 provenance](release/evidence/wf-04-batch-10.md) and
  [batch-10.json](release/evidence/batches/batch-10.json). Proposed release classes in
  `docs/release/scope-v1.json`: `WF-SCOPE-001` (`tooling`), `INSTALL-002` (`release-work`).
- Exact-head independent review (`make feature-batch-review`) and one fresh canonical FULL gate
  (`env -u REUSE FRESH=1 make feature-verify AGENT_ID=neon`) run on this frozen committed head
  before operator delivery.

## 2026-11-22 — INSTALL-002 minimal three-service production `compose.yaml` (ADR 0009)

- On `feat/install-002-minimal-compose` from `c5f9cdf` (writer `neon`).
- Adopted [ADR 0009](decisions/0009-minimal-production-compose.md) amending
  [ADR 0008](decisions/0008-self-initializing-single-compose.md), shrinking production
  `compose.yaml` from 188 lines to 49 lines with three non-root services (`db`, `backend`,
  `frontend`), fixed `container_name` (`florabase-db`, `florabase-backend`, `florabase-frontend`),
  `internal: true` (`db`/`backend`) and `app` (`backend`/`frontend`) network isolation, no YAML
  anchors, no inline shell scripts, no root containers, `create_host_path: false` on every bind
  mount, literal `127.0.0.1` frontend-only publication, single `FLORABASE_DB_PASSWORD`, and
  `TZ=${TZ:-Europe/Rome}` (logs only).
- Built and verified reproducible `florabase-postgres:18.6-alpine-florabase.4`
  (`index_digest` `sha256:93797c3941d06b3a8d591851df04605b5287ace2a11bb32421589ddff1a1782c`,
  `platform_digest` `sha256:7213d5bb35a00e1f80ca60193ad81a07c946e328ad4128a57e53e50fb47bb8b9`),
  adding `PGDATA`, `POSTGRES_DB`, `POSTGRES_USER`, image `HEALTHCHECK`, `-c timezone=UTC`,
  `FLORABASE_DB_PASSWORD` mapping, and pre-start ownership/mode/empty-folder/marker/`pg_controldata`
  guards with 70-owned `postgres/installation.pending` while preserving `gosu` removal, `USER 70:70`
  and exit 64 root refusal.
- Moved backend constant production `ENV` values into `backend/Dockerfile` (`runtime`), added
  `florabase-backend-entrypoint` (`PGPASSWORD` derivation) and `florabase-start` (`wait-db` →
  `release_schema deploy` → owner-env scrub → `exec release_schema serve`), pinned SQLAlchemy,
  Alembic and password-reset sessions to `-c timezone=UTC`, added host-path/non-nesting/same-folder
  and private `backup/pre-upgrade` permission guards, and added atomic `state/upgrade-failed.env`
  latching so restart loops never write repeated dumps.
- Registered `INSTALL-002` (`implemented`, `release-work`) in `docs/features.json` and
  `docs/release/scope-v1.json`; updated `scripts/beta_release.py` (`COMPOSE_SLOTS`),
  `scripts/test-beta-runtime.py`, `scripts/test-beta-images.py`, `scripts/smoke-beta-images.py`,
  `scripts/smoke-portable-compose.py` (ownership refusals, failed-upgrade single-dump latch, UTC
  check with `TZ=Europe/Rome`, beta.7 `0701`-folder upgrade, isolated restore via untracked
  `container_name` override), `docs/installation.md`, `docs/deployment.md`, `docs/security.md`
  (accepted trade-offs + optional hardened override), `docs/security/beta-distribution-001/postgresql-image.md`,
  `README.md`, `CHANGELOG.md`, and `AGENTS.md`.
- Checks: `beta_release.py postgres-identity --check` (`POSTGRES_IDENTITY_REPRODUCED`),
  `make test-beta-runtime` (17 OK), `make test-beta-images` (80 + 4 OK), `make smoke-beta-images`
  (`LOCAL_BETA_CANDIDATE_PASSED`), live `smoke-portable-compose.py` (all 3 stacks green with zero
  residual resources), `make workflow-check`, `pytest tests/test_release_schema.py
  tests/test_infrastructure.py` (68 OK), `check-features.py` (171 valid), `check-doc-links.py`
  (352 docs), independent infrastructure QA (all P0–P3 findings resolved), and canonical FULL
  `make feature-verify AGENT_ID=neon` plus `make release-preflight-local`.

## 2026-11-22 — WF-SCOPE-001 scoped verification by changed files

- On `feat/wf-scope-001-scoped-verification` from `c5f9cdf` (writer `neon-wf-scope-001`).
- Added the `product-frontend` tier (`TIER_ORDER`: `docs < affected < product-frontend < product <
  full`), bumped `scripts/verification-impact.json` to schema v2 (`product_backend_prefixes`,
  `product_frontend_prefixes`, `product_backend_tests`, `product_frontend_tests`), and moved
  `LICENSE` from `documentation_paths` into `full_prefixes` because all three Dockerfiles copy it.
- Scoped PR CI (`scripts/ci-verify.py`): `affected` and `product-frontend` plans run selected
  static/unit suites, selected integration files (or docs checks when empty) and selected builds,
  while `product`, `full`, pushes to `main` and fallbacks remain exhaustive and `ci/batch-*` keeps
  platform-tree validation plus `make_plan(base)`.
- Added `python3 scripts/ci-verify.py rehearse-scope` and PR-only `concurrency` to
  `.github/workflows/beta-release-rehearsal.yml` so docs-only PRs exit `rehearse` early with green
  status while non-docs PRs, pushes to `main`, `workflow_dispatch` and any planning or import error
  fail closed into the full rehearsal.
- Registered `WF-SCOPE-001` (`implemented`) in `docs/features.json` and proposed class `tooling` in
  `docs/release/scope-v1.json`; updated `docs/development-workflow.md`.
- Checks before final canonical gate: `test-verification-impact.py` (42 OK), `workflow-check`
  (Dependabot policy, 79 `test-beta-images`, 4 `test-release-tools-lock`, 18 `test-beta-runtime`,
  Ruff check/format, `mypy --strict` across 49 scripts), `test-feature-workflow` (55 OK),
  `test-agent-workflow` (75 OK, 3 skipped), `check-features.py`, `check-doc-links.py`,
  `test-doc-links.py`. Canonical `make verify-full` runs on this frozen tree before commit/delivery.
- Unresolved: none locally; PR description will link a real docs-only commit run showing `rehearse`
  exiting early after operator approves push/PR.

## 2026-11-22 — ENG-05 closed on branch (a)

- Documentation only, on `claude/project-thread-7djkvu` from `1126c03`. The operator chose
  branch (a) of the ENG-05 criterion: the two-session PostgreSQL regression delivered in #185.
- `./scripts/test-integration.sh backend/tests/integration/test_taxonomy_concurrency.py` passed
  13 tests on PostgreSQL 18.6 with clean disposable cleanup; recorded in
  [ENG-05 evidence](release/evidence/eng-05.md).
- Updated the TAXONOMY-001 lines of `feature-reconciliation-v1.md` and answered question 3 of
  `scope-v1-handoff.md`. The CERT-02 note of 2026-11-16 that calls both findings open predates
  this record and is superseded by it. TAXONOMY-001 status is unchanged.

## 2026-11-22 — UAT Preview smoke repaired on main

- On `fix/uat-fixture-activity-targets`, rebased on `e2db9f4` (writer `claude-uat-fixture`).
- `smoke-uat-preview` failed on `main` since PR #167: `test-uat-fixture.py` requires a Schedule
  activity for every `TARGETS` kind, but the fixture created no vegetative lot or propagation
  attempt. Added the additive `cutting_schedule_extension` (one basil stem-cutting lot and rooting
  attempt via `cuttings.fast_create`, plus two planned activities at today+5/+9) to both seed paths
  and `validate_manifest`; existing manifests gain it once and operator edits are never rescheduled.
- A second defect hidden behind the first: `UATPreview.marker_state` ran `docker run` on the
  retained backend container's image ID, which the containerd image store (Docker 29) drops after a
  rebuild (`No such image`). It now uses the project's own `-backend-development` tag, as
  `uat_instance.py` already does; regression test added to `test-uat-preview.py`.
- Checks: `make smoke-uat-preview` passed (fixture pytest 52 passed, 1 skipped; exact cleanup);
  `python3 scripts/test-uat-preview.py` 20 OK; ruff check/format and strict mypy on the touched
  scripts clean. Not run: FULL `make feature-verify`.

## 2026-11-21 — Batch 09: WF-09 two Compose files, rehearse in delivery, RC-SEQ-01 records

- WF-09 (ADR 0008): the repository tracks exactly `compose.yaml` and a standalone
  `compose.dev.yaml` (the former `compose.runtime.yaml` base merged with the development
  override). `scripts/compose_stacks.py` holds the workflow overrides (production, review, UAT,
  UAT instance, sourcing, quality, quality-network, preview, performance and the standalone
  integration stack) and writes them content-addressed under the checkout's untracked Git
  directory (`florabase-compose/<digest>/compose.<name>.yaml`). The eleven tracked overlays and the
  two historical `docs/review` stacks are removed. A revision from before WF-09 keeps its tracked
  overlays and the helpers still load them (DEV on an older primary, Stable Preview of an older
  ref). `docker compose config` of every stack (DEV, prod, review, sourcing, UAT, UAT instance,
  quality, quality-network, preview, perf, integration) was identical before and after, apart from
  top-level `x-` anchors that Compose ignores. Release artifact copies, lint/type lists and tests
  carry the new module.
- `feature-deliver` now also waits for the hosted `rehearse` job and fails loudly when it fails,
  after #207 merged with a failing rehearsal. On 2026-11-21 the operator also added `rehearse` to
  the `Protect main` ruleset, which now requires quality, integration, build and rehearse.
- RC-SEQ-01 operator decisions are recorded: CUTTING-001 and UI-SYSTEM-001 are `implemented`
  (verified only after RC-image G-CORE/G-UX and operator acceptance), U02 accepted for the
  non-Preview clauses, UI-FLICKER-001 option (a). The Codex CUTTING-001 claim was taken over on
  the operator's instruction; its uncommitted files are untouched.
- Batch 08 follow-ups: mypy includes `backend/scripts/check_api_routes.py`, and the production
  route inventory test no longer passes ambient `FLORABASE_*` variables. The impact classification
  of that script and the smoke `assert` statements remain open.
- The beta.7 publication record is part of this batch. Trivy keeps the floating vulnerability
  database (operator decision 2026-11-21): pinning would make scans reproducible but hide newly
  published CVEs. Instead every scan set records the database that judged it: `scan_images`
  (used by `publish-beta-images` and `rehearse`) writes `scanner-version.json` (`trivy version`
  with the DB `Version`, `UpdatedAt`, `NextUpdate`, `DownloadedAt`) next to the reports and blocks
  the security gate when that record is missing.
- Smoke fixtures follow WF-09: `smoke-dev-recovery` and `smoke-dev-upgrade` copy
  `scripts/compose_stacks.py` (without it the fixture read as a pre-WF-09 tree lacking a base
  `compose.yaml`), and the recovery smoke's modelled old source drops it again. `smoke-dev-golden`
  already copied `scripts/`. `smoke-migration-cycle` commits its baseline with `--allow-empty`,
  since a clean HEAD plus identical copied files left nothing to commit.
- The recovery smoke rendered its modelled pre-WF-09 baseline under the generator's
  `florabase-prod` name, which pinned `florabase-prod_*` network and volume names into the fixture;
  the baseline now drops those names so only the fixture project owns them.
- Checks: `make workflow-check` passed. Real smokes: `smoke-workflow-resources` (502 s) and
  `smoke-uat-instance` (203 s) passed on `73e5510`; after the fixes `smoke-environment-workflow`
  (114 s, Review and Stable Preview), `smoke-dev-recovery`, `smoke-dev-upgrade` (40 s) and
  `smoke-migration-cycle` (76 s) passed. `trivy version --format json` with a populated cache was
  run against the pinned 0.69.3 image and returns the DB `Version`/`UpdatedAt`; the full
  `scan_images` path runs first in hosted `rehearse`.
- Unresolved: `smoke-uat-preview` fails in `test-uat-fixture.py` because the UAT fixture creates no
  scheduled activity for the `vegetative_lot` and `propagation_attempt` targets added by #167. This
  predates Batch 09 and is not in the FULL gate; it needs its own fixture fix. Resolved by the milestone below.

## 2026-11-21 — v0.1.0-beta.7 published

- `1126c03` was tagged `v0.1.0-beta.7` and published through the protected release workflow
  (run `44949666442`, attempt 2, after the operator updated `RELEASE_APPROVED_SHA` from the beta.6
  commit). The [publication record](release/evidence/beta-7-publication.md) lists the five Release
  assets with matching SHA-256 digests and GHCR tags resolving to the manifest digests;
  `gh attestation verify` succeeded for the three images, `compose.yaml` and the manifest, bound
  to the commit and run.
- `docs/release/scope-v1.md` names beta.7 as the current G-MIGRATE and G-UPGRADE baseline. No
  feature status changed.

## 2026-11-21 — Release rehearsal upgrade smoke under umask 077

- The hosted `rehearse` job failed from #207 onward: the release pipeline runs under umask 077, so
  the derived test-only upgrade image copied its migration and previous-release declaration as
  0600 and `migrate` (uid 10001) stopped with `PermissionError` instead of the expected
  `SQLSTATE 42P07`. The derived Dockerfile now copies both with `--chmod=0644`; the production
  backend image is unaffected. A mismatched refusal now prints the `up` output, service states
  and the service log tail. The local checks did not catch it because they ran under umask 022.
- Checks: hosted `rehearse` on this branch (workflow dispatch) and the canonical gate.

## 2026-11-21 — v0.1.0-beta.7 release preparation

- Version surfaces move to `0.1.0-beta.7` (`release/inputs.json`, backend package and module,
  frontend package, both Dockerfiles, regenerated OpenAPI). The Unreleased CHANGELOG section
  becomes the `v0.1.0-beta.7` entry, the first release with the self-initializing `compose.yaml`
  (#205, #207). The installation guides name beta.7 as the first release of the new layout.
  PostgreSQL stays `18.6-alpine-florabase.3`; the backend declares beta.6 as its previous release.
- No feature status changes. Tag, protected publication and publication evidence remain operator
  actions.

---

Earlier milestones (through `v0.1.0-beta.6` / `INSTALL-001`) are archived verbatim, newest-first, in [archive/progress-until-beta-7.md](archive/progress-until-beta-7.md).
