# Engineering progress

> Earlier milestones through `v0.1.0-beta.6` are archived in [archive/progress-until-beta-7.md](archive/progress-until-beta-7.md). Milestones before the `v0.1.0-beta.10` release preparation are in [archive/progress/v0.1.0-beta.10.md](archive/progress/v0.1.0-beta.10.md). Per-beta rotation started at `v0.1.0-beta.11` release prep (see [workflow/verification-and-gates.md](develop/workflow/verification-and-gates.md#documentation-and-review-artifact-placement)).

## 2026-11-28 — Full data export ZIP (`DATA-EXPORT-001`, batch 16a)

- On `claude/project-thread-d7pp0a` (to be integrated as `feat/data-export-001`) from `origin/main`
  `524da27`, writer Claude thread; no migration. Design:
  [archive/DATA-EXPORT-001/design.md](archive/DATA-EXPORT-001/design.md).
- New `backend/src/florabase/data_export/` (registry, streaming service, API) included from
  `import_export/api.py`: `GET /api/v1/exports/full.zip?include_files=` and
  `GET /api/v1/exports/full/summary`; regenerated `openapi.json` and `schema.d.ts`. New
  `FullExportCard` in Tools → Import / Export. Docs: feature guide section, backup and user-guide
  "not a backup" lines, `DATA-EXPORT-001` in `features.json` (`implemented`) and `scope-v1.json`
  (`best-effort`), verification-impact scope.
- Checks run in the cloud thread (PostgreSQL 16, Node 22): `tests/test_data_export.py` (7) and
  `tests/integration/test_data_export.py` (8, golden smoke copy) pass; ruff, mypy, eslint, tsc,
  prettier clean; `FullExportCard.test.tsx` (3) pass; LibreOffice opens `plants.csv` with readable
  columns. The remaining backend (12) and frontend (60) failures are identical on unchanged `main`
  in that environment. Canonical FULL not yet run.
- Integration note: IDENTIFICATION-001's `identifications` table must be added to
  `data_export/registry.py` and `reviewed_columns.json`; the contract test fails until it is.

## 2026-11-28 — v0.1.0-beta.11 release preparation

- On `docs/release-beta-11` from `origin/main` `46dbb72`, realigned on `af7a96c` after `DOCS-005`
  (writer `claude-release-beta11`). Version
  surfaces move to `0.1.0-beta.11` (`release/inputs.json`, backend package and module, frontend and
  mobile packages, both Dockerfiles, OpenAPI `info.version`). A new `v0.1.0-beta.11` CHANGELOG entry
  covers Batch 15b (`QUICK-ADD-001`, `UX-ENTRY-002`, `BULK-002`, `UI-POLISH-006`, `MOBILE-004`,
  `DEMO-001`; `UAT-INSTANCE-002` is development tooling only) and `DOCS-005`, with beta.10 upgrade
  notes: no migration (head `20261125_0050`), PostgreSQL `18.6-alpine-florabase.6` and
  `compose.yaml` unchanged. `docs/archive/BETA-DATA-001/beta-data-001.md` names beta.11.
- `docs/release/scope-v1.md` names beta.10 as the current upgrade baseline. Records the missing
  beta.10 publication evidence in
  [beta-10-publication.md](release/evidence/beta-10-publication.md) (Release API, GHCR tags,
  attestation statements, signed APK attached by the re-dispatched Android workflow).
- First per-beta progress rotation: milestones older than the `v0.1.0-beta.10` release-prep entry
  move verbatim to [archive/progress/v0.1.0-beta.10.md](archive/progress/v0.1.0-beta.10.md),
  linked from the archive header line.
- No feature status changes. Tag, protected publication and beta.11 publication evidence remain
  operator actions.

## 2026-11-27 — Docs subfolder reorganization, agent reading path, and drift checks (`DOCS-005`)

- Reorganized `docs/` on `docs/docs-005-structure` (base `c83d816`, writer `antigravity-docs-005`) with a pure `git mv` first commit (`0390c760`) moving 67 top-level files into `operate/`, `develop/`, `architecture/`, `product/`, `features/{collection,activity,explore,sourcing,tools}/`, and `archive/<FEATURE-ID>/` (plus `git mv docs/review docs/archive/review`). Kept 7 top-level tombstones (`installation.md`, `security.md`, `backup-restore.md`, `deployment.md`, `mobile.md`, `versioning.md`, and existing `portable-installation.md`) preserving released `CHANGELOG.md` anchors and leaving `compose.yaml` and `postgres/florabase-postgres-entrypoint.sh` untouched.
- Split `development-workflow.md` (80.8 KB) into `develop/workflow/` (6 files) + anchor-preserving index, and `domain-model.md` (75.6 KB) into `architecture/domain-model/` (4 files) + index; kept `develop/ui-contract.md` (48.2 KB) whole per Phase 1 ruling. Added `> Summary:` lines and folder `README.md` indexes, `docs/agent-map.md`, `make feature-show` / `make feature-list` (`scripts/feature-show.py`), updated `AGENTS.md` step 4, and extended `scripts/check-doc-links.py` + `scripts/test-doc-links.py` with structure drift checks.
- Updated hard-coded `docs/` paths across backend (`release_schema.py`, `events/{model,schemas}.py` + regenerated `openapi.json`/`schema.d.ts`), frontend, scripts, tests, CI, `Makefile`, `release/platform.json`, and `docs/design/ui-system-v1/*.py`. Registered `DOCS-005` next to `DOCS-001` (`best-effort`). Evidence: [docs/archive/DOCS-005/evidence.md](archive/DOCS-005/evidence.md).
- Fix round: generalized `scripts/feature_batch.py` `_additive_progress()` symmetrically so a pure top-prepend integration branch merges cleanly with an incoming branch that also rewrites deep links in `docs/progress.md` (keeping refusal when both sides edit deep text; tests in `scripts/test-agent-workflow.py`), and made `scripts/feature-show.py` match IDs/prefixes case-insensitively (`scripts/test-check-features.py`).

## 2026-11-27 — Batch 15 integration (UAT-INSTANCE-002, MOBILE-004, UI-POLISH-006, QUICK-ADD-001/UX-ENTRY-002/BULK-002, DEMO-001)

- `ci/batch-15b` from `origin/main` `c83d816` (writer `claude-batch-15`) merges, in order,
  `ci/uat-instance-002` `bd890ee`, `feat/mobile-004-notifications` `707a833` (it already contains
  `bd890ee`, merged at the source to resolve the shared `make mobile-sync` line in `docs/mobile.md`),
  `fix/ui-polish-006-collection` `a5f43a9`, `feat/market-phase1` `7e3937b` (QUICK-ADD-001,
  UX-ENTRY-002, BULK-002) and `feat/demo-001-readonly-tour` `ffb4cea` (DEMO-001, realigned on
  `c83d816`, registry entries moved off the tail of `docs/features.json` and
  `docs/release/scope-v1.json`; it also merges `707a833` and adds `demo_readonly: false` to the
  MOBILE-004 session fixture so `tsc -b` passes). Only `docs/progress.md` conflicted and was
  resolved additively; the UAT-INSTANCE-002 milestone is moved back above MOBILE-004 into merge
  order. No migration (Alembic head unchanged). The first candidate `ci/batch-15` (`070463f`) was
  abandoned after its integration review found that `tsc -b` error. DOCS-005 is delivered
  separately after this batch (operator decision 27/11).
  Evidence: [wf-04-batch-15b.md](release/evidence/wf-04-batch-15b.md).
- Checks on the integrated tree before review: OpenAPI export `--check` (no drift) and
  `openapi-typescript` regeneration (no `schema.d.ts` change), `tsc -b` (exit 0), full Vitest,
  backend unit tests outside `tests/integration` (only the known environment failures that also
  fail on `main`), `check-features.py`, `check-doc-links.py` and `test-beta-runtime.py`.
  Canonical FULL follows the recorded exact-head review.

## 2026-11-27 — UAT-INSTANCE-002 stale launch handling on rebuilt branches (also: mobile-sync pnpm fix, follow-up of #231)

- On `ci/uat-instance-002` from `origin/main` `c83d8163` (writer `antigravity-neon-uat-instance-002`;
  registered right after `MULTIBRANCH-UAT-001` in `docs/features.json` as `implemented` and in
  `docs/release/scope-v1.json` as `best-effort`). Tooling only: no product code, no migration.
- Added local reflog proof `in_worktree_reflog()` and hardened `delivered()` error handling in
  `scripts/uat_source.py`; extracted `verify_launched_sha()` and `check_upgradeable()` hooks in
  `scripts/uat_preview.py` (deferring launched-SHA checks until after all container/volume/network/
  mount/port/env/foreign-user checks pass, while keeping singleton UAT Preview and detached-owner
  `delivered()` unchanged); overrode them in `scripts/uat_instance.py` so attached UAT instances
  never call `gh api`, report stale launches in `status`, allow `stop`/`up`/guarded `reset`/guarded
  `remove` without manual `docker rm`, keep `require_upgradeable` safety with a guarded reset hint
  on `up`, refuse `seed`/`validate` while stale, and accept expired 40-hex SHAs only in
  confirm-guarded `reset`/`remove` when all other identity checks pass. Added a one-line stale-launch
  hint in `scripts/feature_batch.py` `prepare()` when the batch worktree owns a UAT instance.
- Documented the rebuilt-branch / stale-launch contract in `docs/development-workflow.md` and
  archived reproduction, open-check answers and smoke evidence in
  [uat-instance-002-handoff.md](archive/UAT-INSTANCE-002/uat-instance-002-handoff.md).
- Checks: `make test-uat-preview` (60 passed: preview 20, source 18, instance 22),
  `make workflow-check`, `make test-agent-workflow` (81 passed, 3 skipped),
  `make test-feature-workflow`, `make test-environment-workflow` (51 passed), `make doc-links`
  (398 docs), `scripts/check-features.py` (205 features valid), real disposable Docker
  `make smoke-uat-instance` (including branch-rewrite stale launch through `status`/`stop`/`up`/
  guarded `reset` and before/after `io.florabase.sha` labels) and `make smoke-uat-preview`.
  Canonical FULL via `make feature-verify` follows tree freeze.

## 2026-11-27 — MOBILE-004 Android local Schedule reminders (PWA preserved)

- On `feat/mobile-004-notifications` from `origin/main` `c83d8163` (`v0.1.0-beta.10`, writer
  `neon-mobile-004`). Zero database migrations, zero backend changes, zero OpenAPI drift, and zero
  `@capacitor/*` packages in `frontend/package.json`.
- Pinned `@capacitor/local-notifications@8.3.1` in `mobile/package.json` (`mobile/pnpm-lock.yaml`),
  verified zero Google Play Services / Firebase / FCM / ML Kit in the resolved Gradle
  `releaseRuntimeClasspath`, stripped `SCHEDULE_EXACT_ALARM` (`tools:node="remove"`), and added
  `MY_PACKAGE_REPLACED` (`android:exported="false"`) on `LocalNotificationRestoreReceiver` in
  `mobile/android/app/src/main/AndroidManifest.xml` so pending alarms survive both reboots and
  Obtainium/APK updates. Extended `scripts/generate-mobile-assets.py` to generate deterministic
  monochrome status-bar icons (`drawable-{mdpi..xxxhdpi}/ic_stat_florabase.png`, wired in
  `mobile/capacitor.config.ts` with `iconColor: "#153A2C"`).
- Added pure DST/time-zone-aware reminder plan builder (`frontend/src/mobile/remindersPlan.ts`),
  serialized coalescing coordinator and Preferences/bridge adapters
  (`frontend/src/mobile/reminders.ts`), and lazy native-only `NativeRemindersSettings` panel
  (`frontend/src/mobile/NativeRemindersSettings.tsx`) mounted in `Settings → Account` below
  **Connected devices** strictly behind `isNativeShell()` (`frontend/src/settings/AccountScreen.tsx`).
  Schedules at most one inexact `allowWhileIdle` daily digest over the next 14 local calendar days
  (`GET /api/v1/schedule?status=planned&due_from=<today>&due_to=<today+13>&today=<today>&limit=100`,
  owned IDs `41000..41099`), uses `VISIBILITY_PRIVATE` channel `schedule-reminders` with count-only
  collapsed text and ≤5 sanitized ≤60-char titles in expanded `inboxList` only, persists only
  `updatedAt`/`timeZone`/per-day counts in `florabase.reminders.plan`, deep-links cold/warm/expired-session
  taps into Schedule (`#/schedule?window=today|overdue` or `#/schedule/<id>`), recomputes serially on
  auth start, foreground resume (incl. time-zone change), Schedule mutations (`changes.ts`), and
  settings edits, and cancels pending + delivered owned notifications on switch-off, logout, 401,
  server change/forget, and `min_client_version` failure.
- Web bundle delta vs `origin/main`: `index-*.js` `+109 B` raw / `+63 B` gzip (`300,950 B ->
  301,059 B`, `91,662 B -> 91,725 B`), `index-*.css` `+0 B`.
- Extended `MobileReleaseContract` (`scripts/test-beta-runtime.py`) for manifest permission
  allowlist, `MY_PACKAGE_REPLACED` receiver, `ic_stat_florabase` assets, and zero Google/Firebase
  dependencies; updated `docs/mobile.md` ("Reminders"), registered `MOBILE-004` (`implemented`,
  `post-1.0`) in `docs/features.json` and `docs/release/scope-v1.json`, and recorded full emulator
  and test evidence in [docs/archive/MOBILE-004/evidence.md](archive/MOBILE-004/evidence.md).
- Verified `make mobile-android-debug` and signed `make mobile-android-release` (throwaway keystore,
  `v0.1.0-beta.10` / `versionCode 100310`), focused Vitest (17 files, 127 tests), `make workflow-check`,
  and live Android 16 AOSP emulator E2E (startup isolation, permission-denied recovery, inexact
  delivery latency +55 s to +90 s, lock-screen `VISIBILITY_PRIVATE`, warm tap, completion recompute,
  cold-start tap, expired-session 401 cleanup + post-login deep link, APK update survival, reboot
  survival, and logout cleanup). Canonical FULL `make feature-verify AGENT_ID=neon-mobile-004` runs
  on the frozen committed HEAD.

## 2026-11-27 — Collection detail consistency round & Back/New bar removal (`UI-POLISH-006`)

- On `fix/ui-polish-006-collection` from `origin/main` `c83d8163` (writer `antigravity-neon`); frontend-only (no migrations, no API changes). Part B2 (approved by Alessandro on 26/11) was added on top by Claude after the independent review of the B1 commit.
- **Part A (Back/New bar removal):** Removed `contextActions` and detail-only `actions` from `WorkspaceIntro` on Plant and Sowing details (`PlantScreen.tsx`, `SowingScreen.tsx`, `CollectionUI.tsx`), deleted the CSS hiding rule in `detail-page.css` and dead `.workspace-context-actions`/`.plant-back`/`.sowing-back` detail rules in `specimen.css` and `styles.css` (keeping reachable loading-state back links), wired breadcrumb focus-return to the list via `BreadcrumbItem.onClick`, confirmed no other Collection details hid a Back/New bar, and updated Plant/Sowing tests.
- **Part B1 (items 1–19):** Built shared `RecordAlmanac`, `RecordOverview` (two-column facts-left / Almanac-right), `RecordDescendants` (one-line counts), and `RecordChildCard`, then migrated Seed lot, Sowing, Vegetative lot, Rooting attempt, Plant, Plant group, Harvest, and Location details:
  - `LineageStrip`: pinned `Full lineage` right at constant height across all tabs, wrapped long Cuttings chains without clipping, added `harvested as` verb for Harvest, and appended compact descendants summaries linking to the Lineage tab.
  - `LineagePanel`: unified across every record type (including Sowing and Harvest) with `Ancestors` horizontal cards and `Recorded from this record` elbow tree plus consistent empty-state wording.
  - `DetailTabs` & `DetailHeader`: unified tab skeleton (`Overview · <work tab(s)> · Photos · Lineage`; Location `Overview · Contents`) with one underline active tab style, enforced ≤ 1 primary + ≤ 2 secondary + Edit + `⋯ More` (Sowing `Create Plant group` and Plant group `Take cuttings` in `More`; Harvest status chip + `Record disposition` primary when held; Location `Create child` primary before `Log care…`, no repeated root subtitle, no duplicate header scope chips).
  - `SpecimenLabel` & tab bodies: monospace only for dates/quantities/codes with one muted `Not recorded` style, fixed Harvest photo-label spacing and mobile 390px label width, stacked Sowing Germination `Observation history` full-width below the metrics row, replaced Sowing/Seed lot filler text with real data, adopted `RecordChildCard` on Seed lot Sowings and Cuttings child tabs, and consolidated Harvest's collected/stored inventory into one compact table with inline conversion/disposition links.
- **Part C (UI-POLISH-005 leftovers):** Synced Cuttings `useRecordTab` to later `?tab=` route changes, removed duplicate counts from the Species distribution `Species` chooser heading, and removed dead `:not(.page-header--directory)` rules in `media.css`.
- **Part B2 (approved 26/11):** `DetailHeader` gained a shared key facts strip under the action bar (Seed lot remaining · sowings · viable until; Sowing sown · germinated · days since sowing; Plant days in collection · journal entries · harvests; Plant group plants · extracted · journal entries · harvests; Harvest held · materials · seed lots converted; Vegetative lot taken · remaining · attempts; Rooting attempt struck · rooted · established; Location active plants · active sowings · child locations). `SpecimenPlate` shrinks to a short placeholder with an `Add photo` link to the Photos tab when the record has no image (`RecordVisual` marks itself `data-empty`). The Almanac opens with a `Next up` line (first planned activity and when it is due, or `Nothing planned · Schedule activity`). `DetailTabs` shows count badges (Photos, Sowings, Germination, Journal, Rooting attempts, Observations, Offspring, Contents); the badge is `aria-hidden` so tab names stay stable.
- Review fixes on top of B1: Plant/Plant group Overview descendants now read the same lineage children as the strip (one vocabulary, no capped Vegetative-lot query); a Plant with no harvests no longer links to the species' harvest list; Harvest descendants count excludes reversed Seed lot conversions.
- Registered `UI-POLISH-006` (`implemented`, `best-effort`) in `docs/features.json` and `docs/release/scope-v1.json`. Evidence: [evidence.md](archive/UI-POLISH-006/evidence.md).
- Checks: `check-features.py` (205 valid), `check-doc-links.py` (399 docs), `tsc -b`, ESLint, Prettier, focused Vitest across 11 affected directories (42 files / 518 passed), before/after visual verification at `1440×900` and `390×844` on a disposable golden `COMPREHENSIVE` UAT instance (retired afterward), and canonical `make feature-verify AGENT_ID=antigravity-neon`.

## 2026-11-27 — Market Phase 1: QUICK-ADD-001, UX-ENTRY-002, BULK-002

- On `claude/project-thread-sg3uco` from `origin/main` `c83d816`. Audit of roadmap Phase 1 against
  main: O-08/O-09/O-10 and default WFO provisioning already shipped in beta.10, so this slice adds
  only the missing quick-add path and dated bulk moves; arm64 images and QR quick actions are
  deferred. No migration. Evidence: [`market-phase1.md`](release/evidence/market-phase1.md).
- `QUICK-ADD-001`: `POST /api/v1/quick-add/plant` creates or reuses the identity, confirms a picked
  WFO taxon through the TAXONOMY-001 link only while the name matches, and creates a Plant or
  PlantGroup in one transaction; `#/quick-add` page linked from Today, **+ New** and **Record**.
- `UX-ENTRY-002`: Create identity from the Plant form, Sowing descendant wizard and pot-on pickers
  through a shared portalled dialog that reuses an exact duplicate.
- `BULK-002`: optional `occurred_on` on bulk location apply dates Plant/PlantGroup Movement Events;
  the Move dialog asks the date (Today by default) only for Plant/PlantGroup selections.
- Registered all three in `docs/features.json` (`implemented`) and `docs/release/scope-v1.json`
  (`best-effort`). Checks: backend ruff/format/mypy, focused pytest on PostgreSQL, frontend tsc,
  eslint and full vitest (1535 tests) pass; canonical `make feature-verify` pending.

## 2026-11-27 — Opt-in public read-only demo mode & guided tour (`DEMO-001`, realigned on `7b667a4` + review fixes)

- On `feat/demo-001-readonly-tour` realigned on `origin/main` `7b667a4` (post Batch 14b, writer
  `antigravity-demo-001`). No database migration and zero impact on standard production
  authentication (`FLORABASE_DEMO_READONLY` defaults to `false`, `G-SEC`/`ENG-03` public allowlist
  and `MOBILE-003` `runtime_config` preserved).
- Backend: added `demo_readonly: bool = False` (`FLORABASE_DEMO_READONLY`) in `core/config.py` and
  single-source `uvicorn_workers_from_environment` (`FLORABASE_WORKERS` `1..8`, default `1`) in
  `db/release_schema.py`; added `auth/demo_readonly.py` with explicit non-symlink startup marker
  verification (`verify_demo_marker` requiring `.florabase-demo-readonly.marker` in both
  `release_schema serve` and FastAPI `lifespan`, logging `PUBLIC READ-ONLY DEMO: no login required`),
  `DemoReadOnlyMiddleware` rejecting all non-`GET`/`HEAD`/`OPTIONS` HTTP requests with `403`
  `demo_read_only` (`Cache-Control: no-store`), transient in-memory `resolve_demo_actor` (zero
  `auth_sessions` DB writes), neutral `Demo visitor` session response (`owner: false`,
  `login_name: ""`), empty `GET /api/v1/auth/device-sessions`, cache-only `external_botany` GETs
  (`external-taxa/search`, `occurrence-map/summary`, `occurrence-map/tiles` making zero outbound
  GBIF calls and zero cache writes on miss), public demo thumbnail cache headers without
  `Vary: Cookie`, and `"demo-readonly"` capability in `GET /api/v1/system/info`. Regenerated
  `backend/openapi.json` and `frontend/src/api/schema.d.ts`.
- Frontend: skipped `POST /api/v1/auth/csrf` in `auth/AuthProvider.tsx` when `session.demo_readonly`
  is `true` and surfaced `403` `demo_read_only` responses via `shell/demo/readonlyNotice.ts`; updated
  `shell/WorkbenchShell.tsx` to display `Demo visitor (read-only)` and hide Sign out, `Record`,
  `+ New`, saved-view removal and owner-only Settings links (`Account`, `Media`, `Import / Export`);
  lazy-loaded `shell/demo/DemoExperience.tsx` in `App.tsx` only in demo mode, rendering the
  semantic-token `Read-only demo` banner, polite read-only mutation notices, and a 7-step interactive
  guided tour (`shell/demo/tourSteps.ts`, `shell/demo/demo.css`) linking to GitHub
  `docs/installation.md` with `Escape`/Skip/Restart, `?tour=1`, and resilient `sessionStorage`.
- Docs & manifests: added [docs/operate/demo-mode.md](operate/demo-mode.md) (with full GET route side-effect audit
  and caching/rate-limit notes), documented `FLORABASE_WORKERS` in [docs/operate/installation.md](operate/installation.md),
  linked in `docs/README.md`, registered `DEMO-001` (`implemented`, proposed class `best-effort`) in
  `docs/features.json` and `docs/release/scope-v1.json`, and recorded evidence in
  [evidence.md](archive/DEMO-001/evidence.md).
- Checks: `make api-generate` / `make api-check`, `scripts/check-features.py`, `scripts/check-doc-links.py`,
  focused unit & PostgreSQL integration suites (`test_demo_readonly.py`, `test_demo_readonly_api.py`,
  `DemoExperience.test.tsx`), and canonical FULL gate (`make verify-full AGENT_ID=antigravity-demo-001`).

## 2026-11-27 — Android release APK: apksigner output format (MOBILE-003)

- Second `v0.1.0-beta.10` APK run (45981312380) built and signed the APK but
  `scripts/mobile-android-release.sh` picked the runner's preinstalled build-tools 37.0.0 apksigner,
  which prints `V2 Signer: certificate SHA-256 digest:` instead of `Signer #1 certificate ...`, so the
  certificate check aborted. The workflow now removes build-tools newer than the declared 36.0.0 on
  the ephemeral runner before running the tag's script, and the script parses both formats for future
  tags. Contract tests cover both.

## 2026-11-27 — Android release APK: Corepack pnpm version (MOBILE-003)

- `mobile-android-release.yml` failed for `v0.1.0-beta.10` (run 45965802666) with
  `ERR_PNPM_BAD_PM_VERSION`: `corepack enable` plus `pnpm --dir frontend` from the repository root
  (no root `package.json`) made Corepack fetch its default pnpm 12 instead of the pinned
  `pnpm@11.19.0`. The build step now runs pnpm from `frontend/` and `mobile/`; the workflow contract
  test rejects `pnpm --dir`. Re-dispatch with `tag=v0.1.0-beta.10` attaches the APK to the existing
  release; images and the release itself are unchanged.

## 2026-11-27 — v0.1.0-beta.10 release preparation

- On `docs/release-beta-10` from `origin/main` `7b667a4` (writer `claude-release-beta10`). Version
  surfaces move to `0.1.0-beta.10` (`release/inputs.json`, backend package and module, frontend and
  mobile packages, both Dockerfiles, OpenAPI `info.version`). The Unreleased CHANGELOG section
  becomes the `v0.1.0-beta.10` entry covering Batch 13 (`PROPAGATION-BATCH-001`, `CARE-BULK-001`,
  `FN-03`, `UX-SORT-001`, `MEDIA-FETCH-001`, `DOCS-004`), `MOBILE-002` and Batch 14b (`IMPORT-002`,
  `REF-SETUP-001`, `ABOUT-001`, `UX-SORT-002`, `MEDIA-SETTINGS-001`, `MOBILE-003`, `DOC-04`,
  `UI-POLISH-002`–`005`, `BETA-SECURITY-001`), with beta.9 upgrade notes: three migrations since
  beta.9 (head `20261125_0050`), PostgreSQL `18.6-alpine-florabase.6`, and `compose.yaml` enabling
  `FLORABASE_REFERENCES_SETUP=auto`. `docs/beta-data-001.md` names beta.10. Test fixtures that use
  beta.9 as sample data are unchanged.
- No feature status changes. Tag, protected publication and publication evidence remain operator
  actions.
