## 2026-11-08 — beta publication preflight recovery

- Protected beta.4 run `42508727559` passed exhaustive verification and reached `smoke_passed`.
  Its retained artifact contains `postgres-reproducibility/` alongside the flat release files.
  The actual beta.4 preparation and inventory functions reproduced the failure on that directory.
- Shared the staged publisher with local and hosted rehearsal. Publication validates an explicit
  asset set and recorded digests, retains diagnostic evidence separately, and requires exact-main
  CI, the forced migration cycle and hosted rehearsal before proceeding.
- [Preflight, coverage matrix, checkpoint and retry policy](security/beta-distribution-001/release-publication-preflight.md).
  The beta.4-layout preflight at `75d38c7` passed every local stage, including pinned PostgreSQL
  reproduction, Trivy, artifact-only smoke, validation of seven assets and three local promotions.
  Independent QA reproduced the old failure and recomputed all seven asset hashes. Its findings
  led to the previous-main migration base and stricter finalization guards. Beta.5 is the next
  candidate. The beta.4 tag still peels to `ea4f3ad3`. Read-only checks found no beta.5 Git tag,
  release or application image tags. Focused release 56, tool lock 4 and verification impact 30
  passed. Release-script Ruff and mypy, workflow actionlint, feature graph and API generation
  passed. API declarations remained byte-identical. Final exact-tree evidence is separate.

## 2026-11-08 — BETA4-PREP-001 release candidate preparation

- Prepared the current release, backend, frontend and installation identities for `0.1.0-beta.4`;
  preserved prior release evidence and the pinned PostgreSQL image. Publication remains separately
  authorized and has not occurred.
- Read-only preflight at base `bb6de646` found no beta.4 Git tag, GitHub Release or application
  image manifests. The hash-locked release regression suite passed 55 tests before and after the
  identity update; `python3 scripts/beta_release.py check --publication` passed.
- Canonical FULL verification and independent QA are required before delivery; the hosted rehearsal
  and protected PR checks must pass for the final candidate. No deployment or publication is implied.

## 2026-10-29 — WCVP-VERSION-001 explicit v15/v16 implementation for review

- Added immutable two-release definitions, separate optional v16 path and explicit provisioning;
  v15 stays default. Wrong archive/version/schema and cross-version destination replacement refuse.
  Atomic publication rechecks destination ownership under a per-file lock.
- Search, exact-taxon confirmation and proposals use an explicit selected release. Native range UI
  names both selected and confirmed versions. Frozen Apply dispatches from original release/hash
  and matching approved crosswalk without reading an optional index. Reconfirmation rotates the
  existing link UUID; no automatic migration, identity rename, text overwrite or range deletion.
- Preserved all twelve geographic equivalences and existing v15 evidence formats/constraints.
  Refreshed locked geography rows before Apply validation to detect another transaction's changes.
  No Alembic migration or protected dataset/environment change was necessary.
- Focused backend60/PostgreSQL38/frontend8 tests passed, strict backend/frontend typing passed;
  Review adapter4, four live foreign-runtime refusals, repeated seed IDs, graph117 and whitespace
  checks passed. The planner selects FULL for configuration impact; canonical exact-tree results
  are retained in the final feature-verification receipt rather than inferred from focused checks.
- Separate Review http://localhost:15281 uses six synthetic scenarios and real independent v15/v16
  indices. Browser inspection confirmed explicit v16 browsing preserves a v15 link and inspectable
  frozen v15 proposal, with add/keep-only geography. Operator acceptance remains pending.
- Production-format v16 index:952,799,232bytes; build208.48s; Python peak RSS44,872KiB. Temporary
  disk/cgroup peaks, physical mobile/AT/real zoom and large-collection performance remain unmeasured.
  Docker default subnet pools were exhausted; only this task's isolated networks use checked-free
  explicit subnets. Existing resources were preserved; disposable ownership/cleanup guards retained.
- [Contract, compatibility and provisioning](wcvp-version-001.md),
  [Review/checklist](review/wcvp-version-001/README.md). Feature is implemented, awaiting operator
  review; all changes unstaged/uncommitted. No push, merge or delivery.

# Engineering progress

## 2026-11-08 — beta-postgres-repro-001 implementation candidate

- Branch `fix/beta-postgres-repro-001` starts from verified `933b6984`; writer claim is held by
  `codex-beta-postgres-repro-001`. beta.1–beta.3 tags and their PostgreSQL identity are untouched.
- Failed run `42421453830` passed authorization and stopped at the exact PostgreSQL identity gate,
  before candidate image copy. Its retained artifact has no OCI layer descriptors or raw manifest/config
  bytes. The failure reports index `e514d64b…` vs pinned `4edc0790…`, platform manifest `72cb11d5…`
  vs `55b1969a…`, and config `e01ce338…` vs `ef74e207…`. The CI builder was BuildKit 0.33.1; the
  existing successful local evidence names 0.34.2. This is a testable leading cause; the first old
  layer byte and a causal CI result are pending hosted reproduction.
- Restored the exact immutable BuildKit 0.34.2 input without changing PostgreSQL version, source,
  base, apk pin, expected digests, root hardening or `require_pinned_postgres`. Added an ubuntu-24.04
  non-publishing rehearsal with pull-only GHCR preflight and a labeled local registry. Publication
  shares application-build, manifest, scan, SBOM, smoke, assets and digest promotion helpers. The
  rehearsal keeps two independent pinned-toolchain builds plus a diagnostic build using the prior
  0.33.1 image, and saves hash-checked raw index/platform/config bytes and layer descriptors.
- Two independent clean local PostgreSQL identity builds both matched index
  `sha256:4edc079088c3f78b69fc8f9473e33881ebabea7fea2d82b3227b70a69ae3b7de` and platform manifest
  `sha256:55b1969a7fddad118ca07a15058a43a5916dec3e4dbab38029e671225b392b91`; their owned builders
  were removed. Focused checks: release suite **48 passed**, runtime contract **62 passed on Python
  3.14** and **50 passed on Python 3.8**, repository `workflow-check` passed Ruff, formatting and
  strict mypy. `beta_release.py check --publication`, feature graph, `py_compile` and whitespace
  checks passed. `beta-release-checks.py` did not run to completion here because the installed `gh`
  CLI lacks `gh attestation verify`; the GitHub-hosted rehearsal and its runner-native check remain
  pending. No beta.4 version update, tag, publication dispatch or remote package/release mutation.
- [Failure analysis and rehearsal contract](security/beta-distribution-001/beta-release-rehearsal.md).
  Read-only GHCR findings, real GitHub attestations and Release API finalization are intentionally
  distinct: only the first is checked in rehearsal; the latter two remain protected-live-only.

## 2026-11-02 — BETA-FOUNDATION-001 B1–B4 QA corrections ready for delta review

- Continued clean authoritative `3553a9c` / tree `9d986e4`, confirming the existing
  `codex-beta-foundation-001` writer. Independent CONDITIONAL PASS required B1–B4; no delivery.
- B1 now checks sticky ownership for every direct child. Exact original-helper reproduction returned
  Git EPERM after losing registration; corrected real root-owned mode-1777 file and FIFO fixtures
  each refuse before unregistering and retain source/content. Empty-root-owned positive smoke passes.
- B2 now inspects all running container mounts regardless of labels, resolves binds and refuses
  candidate/descendant/ancestor overlaps, incomplete/changing metadata and unknown volume backing.
  Original helper retired a live unlabelled parent-bind/hidden-tmpfs fixture; corrected helper retains
  registration, source, running container and nested data. Host mountinfo/resource guards remain.
- Reproduced the throwaway-patch workflow failure: the old read-only assertion rejected the new
  `ps --quiet --no-trunc` query. Its exact read-only allowlist now includes required inventory/inspect
  commands, still rejects mutations, and passes. Original QA patch/log not retained; reproduced cause
  and bounded evidence are recorded without treating a stale assertion as a product regression.
- B3 makes architecture/runtime screening a pre-publication BETA-IMAGE-001 input; runtime capacity
  remains unmeasured. B4 requires immutable PostgreSQL identity, separate major/minor/image maintenance
  and explicit frontend/backend/DB Dockhand labels plus selected environment policy. Updated audit
  IDs/statuses and pending COLLECTION-VISUAL-002 acceptance/RELEASE-001; separate planned
  WORKFLOW-RETIRE-AUTH-001 records the agent-identity restriction discrepancy without implementing it.
- Checks: narrow baseline 2 passed; targeted 7 passed; smoke-enabled agent suite **60 passed/no skips**;
  adjacent lifecycle 46, resources 14 and environment 35 passed; shell helpers all passed;
  workflow Ruff/format/mypy passed; graph **132 valid**, links/status preservation/whitespace passed.
  Docker before/after identities: **6 containers / 8 networks / 17 volumes** unchanged, including
  existing container state/mount fingerprints; no retirement smoke containers remain.
- [Correction evidence and limitations](beta-foundation-001-qa-corrections.md). Independent delta QA
  must pass before canonical FULL, explicitly not run here. No receipt/verified promotion, production
  deployment, pipeline/backups implementation, push, PR, delivery, merge or real feature-finish.

## 2026-11-02 — BETA-FOUNDATION-001 implementation ready for independent QA

- Claimed linked `beta-foundation-001`, branch `feat/beta-foundation-001`, as
  `codex-beta-foundation-001` from clean cached main `af2372c`. No real production environment change.
- [Evidence audit and beta contract](beta-foundation-001.md) distinguishes delivered collection
  workflows from implemented/real-world acceptance, missing operational prerequisites and deferred
  work. Existing Harvest inventory/conversion, Orders, CSV, Taxonomy and Schedule are present; stale
  roadmap snapshots do not establish missing features. Existing statuses are preserved.
- Proposed private single-owner `v0.1.0-beta.1`: paired immutable GHCR images, versioned Dockhand
  image-only stack, stable PostgreSQL/media, Tailscale HTTPS plus owner authentication, explicit
  migration, paired off-host recovery and guarded upgrades. Evaluated NAS/VPS/dedicated host against
  capacity/uptime/recovery needs; no host selected without actual specifications. Added five scoped
  graph entries for foundation, images, runtime/recovery, actual-data rehearsal and beta admission.
- Retirement now permits readable empty directories through a removable parent, retains nonempty
  write requirements and refuses symlinks/mounts or unavailable traversal evidence before unforced Git
  removal. No permission rewrites/deletion fallback. Real disposable Docker nested-mount smoke
  reproduced root-owned empty `frontend/node_modules`; original helper fails both new positive cases,
  corrected helper passes. Historical reported directories are no longer available for inspection.
- Checks: initial narrow baseline 2 passed; existing workflow suite 50 passed; final expanded suite
  54 passed / 1 opt-in smoke skipped (55 total), final focused retirement 4 passed and separate real
  Docker smoke 1 passed; adjacent feature suite 46 passed and shell helpers all passed;
  `make workflow-check AGENT_ID=codex-beta-foundation-001` passed Ruff/format and strict mypy;
  feature graph 131 valid; whitespace checks passed. Iteration fixture/format/type failures resolved.
- [QA handoff and exact check scope](beta-foundation-001-qa.md): planner selects FULL, reserved for
  the different independent QA session under canonical policy; no receipt or `verified` promotion.
  Product suites/builds/API drift/migration cycle, real HTTPS deployment, full restore and real-data
  UAT not run by this implementation. Host/data/backup/RPO/RTO/maintenance choices remain open.
  Local commit only; no push, delivery, merge or real feature-finish.

## 2026-11-02 — UX004-FLAKE-001 lazy-workspace test correction

- Freshly fetched verified main `e5e6b4f` (#134); attached the clean existing `2185` worktree with
  `make feature-init BRANCH=fix/ux004-flaky-test`. Primary main and Claude's workflow worktree remain
  untouched.
- Reproduced the current Add plant test flake: unchanged UX004 passed 19/20 fresh-process runs
  (259/260 cases), with one timeout finding the Botanical identity combobox. Ten instrumented runs
  showed import settlement returning while React still displayed Loading workspace and before Plant
  reference requests. A promise-gated immediate-readiness probe failed 5/5 without async `act` and
  passed 5/5 with it; those diagnostic failures are distinct from the original intermittent test.
- Wrapped only the existing import-settlement wait in async `act` to flush the real lazy workspace
  commit/effects. All original assertions/timeouts remain; no product, fixture, dependency, API or
  workflow change. Corrected UX004 passed 30/30 fresh-process runs (390/390 cases).
- Related frontend regression passed 259/259 cases in nine suites; strict TypeScript, zero-warning
  ESLint, whole-frontend Prettier and production frontend build (274 modules) passed.
- [Investigation and exact focused checks](ux004-flake-001.md) distinguish this proven current-main
  scheduling weakness from the historical TX-001 failure, whose exact failed assertion is unavailable.
  Canonical verification and protected delivery await explicit coordination. No FULL, Feature Review,
  UAT, push, PR, merge or feature-finish; no feature status is promoted to verified.

## 2026-11-01 — TX-001 independent QA corrections (CONDITIONAL GO, nonblocking)

- Guard now walks each route's effective dependency tree (application, router, route and nested
  authentication/CSRF dependencies), requires every Session node to be function-scoped and cached,
  and proves completeness against all 203 OpenAPI operations. Negative probes reject nested
  `use_cache=False` and request-scoped declarations and show both really open a second Session.
  Mutating only `require_authenticated_actor` is reported on 200 of 203 routes for either case.
- Regression documentation now distinguishes three deterministic base failures from the
  timing-dependent rollback-after-flush failure caused by fixture login committing after its
  response (passes on base with a pause after login); no fourth defect is claimed.
- Architecture documents Session lifetime rules for streaming responses, background tasks and
  shared transaction identity. Runtime source is unchanged from `560d51e`.

## 2026-10-31 — TX-001 commit before HTTP success (candidate for independent QA)

- Root cause: every route declared `Depends(get_database_session)` with FastAPI 0.143.0's default
  request scope, whose exit stack closes only after `await response(...)`; its `session.commit()`
  therefore ran after the full 2xx was sent. Exceptions were already rolled back in both scopes.
- Reproduced on unmodified `fbce3c4` over real uvicorn HTTP: with a 2 s commit delay the client
  received 201 before COMMIT began and a separate connection could not see the row; an injected
  commit failure still returned 201 with the new id while persisting nothing. Login's AuthSession
  commit likewise landed after the client held the cookie.
- Fix: all 132 declarations use `scope="function"` (commit after endpoint and serialization, before
  send). No endpoint, service, schema, migration or OpenAPI change; generated OpenAPI is identical.
  A route-tree test requires one function-scoped session per request; ASGI probes check ordering.
- Nine real-commit PostgreSQL HTTP regressions cover visibility, commit failure → 500, rollback
  after flush, Schedule/SeedLot, explicit-commit Harvest and failed login, login/CSRF/logout. On the
  original source three fail deterministically for the ordering defect (visibility, commit
  failure, login cookie). Rollback-after-flush can also fail there (timing-dependent) only because
  fixture login commits after its response; it passes on the base once that commit is allowed to
  finish, and base rollback was already correct. Each restores all 38 ORM table counts.
- Focused evidence used PostgreSQL 16.15 (no Docker/PostgreSQL 18 available): backend unit
  981 passed/1 skipped (90.07%); integration 771 passed/1 skipped, the only failure the
  PostgreSQL-18 version assertion; Ruff, strict mypy and OpenAPI drift passed. The impact plan
  selects FULL; canonical FULL and independent QA are pending. No push, PR or merge.

## 2026-10-30 — SCHEDULE-UX-001 operator UAT and independent QA

- Operator reports all six Schedule UX UAT scenarios passed and explicitly authorizes independent
  QA, necessary blocking fixes, canonical FULL verification, protected PR delivery, merge and
  feature-finish. Approved design scope remains frozen.
- Fetched `origin/main`; latest remains `76c0911dbf7ca5dc5f64b1a8d1de8c57c676c70e`, an ancestor
  of candidate `5b7d9f4eafbe5ed6cd1a79e51d332aebc6b2ee6c`; no reconciliation or design change is
  needed. Independent code/evidence review found no blocking defect and required no source fix.
- Schedule Review `florabase-uat-preview-smoke-28ce00000001` at `http://localhost:25288/#/schedule`
  is healthy and owned by this worktree: frontend/backend/PostgreSQL healthy, code/database revision
  `20261013_0042`, fixture v4 ready with 66 references. Existing UAT data and resources are retained.
- Canonical `make feature-verify` selected FULL and passed on `89fe6fd` (tree receipt recorded):
  workflow suites passed; backend 978 passed / 1 skipped (90.06% coverage); frontend 1,077 passed
  across 100 files; all 766 PostgreSQL integration tests passed; Ruff/Prettier/ESLint/mypy/TypeScript,
  generated API drift, both production builds and full migration cycle passed. The migration verified
  `20261013_0042 -> 20261013_0042 -> 20261013_0042 -> 20261013_0042`; disposable integration,
  migration and selected-build resources reported successful cleanup. No API/schema migration was
  introduced by Schedule UX.
- The subsequent feature-status/evidence documentation update requires a second exact-tree FULL
  before delivery; its result is not presumed here. Protected PR delivery, merge, post-merge checks
  and feature-finish are authorized but pending. Physical device, AT, actual zoom, exhaustive
  dialog/theme, injected outage, midnight rollover and scale testing remain limitations.

## 2026-10-27 — UI-SYSTEM-001 Gate B review candidate, Proposal B refined

- Operator selected B and authorized bounded React implementation in the existing `bc88` worktree,
  branch `feat/ui-system-v1`, base `ee34874`. Preserved Gate A research, alternatives and all prior
  evidence. [Gate B package](design/ui-system-v1/gate-b/README.md),
  [before/after](http://localhost:15283/gate-b/index.html) and
  [working lab](http://localhost:15284/ui-lab/#/dashboard) are available locally.
- Implemented DirectoryPage, controlled List/Gallery, reusable row/card, responsive optional inspector,
  ActivityPage, safe `make ui-page` with two actual archetypes and dev-only `make ui-lab`. Reused
  PageHeader/DirectoryTools, canonical filter adapters, house dialogs, photo semantics and tokens.
  Presentation has a view-only URL/browser preference contract; Saved Views v1 is unchanged.
- Semantic typed icons preserve all navigation labels/groups/routes. Corrected the shared header's
  legacy flex-axis/basis collision. Optional TaskDialog fallback handles disappearing/remounted
  triggers; filtering does not pull focus from search. Production directories/Dashboard are not migrated.
- Refined Dashboard uses factual 17 individual Plants / 7 groups / 40 SeedLots / 12 active Sowings,
  eight distinct licensed reference photos without ownership/cover assignment, and Next work.
  At measured 1440×844, all eight photos load; last complete card ends at 730.453125px and the full
  Next work panel at 787.171875px; document extent is 1440×844. Smaller viewports scroll naturally.
- Focused frontend: 203 unique tests in 9 files passed; final overlapping 16-case shared/navigation
  rerun and subsequent 4-case Lab rerun passed. Scaffold 3/3, strict TypeScript, targeted zero-warning
  ESLint, formatting, Ruff, default production build and lab/fixture exclusion, graph 117 valid,
  whitespace and evidence validation passed. 72 JPEGs cover 27 primary, 36 six-theme and 9 contextual
  states. No horizontal overflow in primary/theme captures. Exact commands/limits are in the package.
- Initial worker-startup and browser/service failures were corrected and are not counted as passes;
  final artifacts were reacquired with all eight photos loaded. Actual zoom, physical-device, AT and
  live scale checks remain unperformed. The laboratory cannot mutate records and is not a live API pilot.
- Fresh main check found independently delivered Media #127 (`69814bba`), with a clean Media worktree
  and no shared-file overlap. No Media code/environment was replaced. Main alignment and CI-004
  canonical verification remain for the separately authorized delivery phase. UI-SYSTEM-001 stays
  `in_progress`; changes remain unstaged/uncommitted, with no FULL, push, PR or merge.
- Operator review of working templates and final Dashboard precedes production migration.
  Stop marker: `FLORABASE_UI_SYSTEM_V1_GATE_B_READY_FOR_REVIEW`.

## 2026-10-26 — RELEASE-VISUAL-AUDIT-001 audit/design review candidate

- Audited delivered main `ee3487412fe458cbdf7145154c54a58b66132cae` (#126) in existing
  Codex worktree `bc88`, branch `docs/release-visual-audit-001`. Source-derived inventory covers
  27 primary states and their contextual/direct routes. Existing UI Foundation remains authoritative;
  no production UI, API/schema/domain change or broad refactor.
- New independently owned Review `florabase-ui-audit-bc88` at `http://localhost:15279` retains
  exact source/resource guards and approved synthetic v4/80 + v5/252 fixture references. Existing
  c902 Review, Media, DEV/UAT/Preview/Sourcing/production and primary main were preserved.
  Media coordination was explicitly operator-authorized; localhost cookie collisions required
  sequential login-dependent capture batches, with invalid acquisitions excluded and repeated.
- [Review package](review/release-visual-audit-001/README.md) and
  [live gallery](http://localhost:15282/gallery.html): **270 selected screenshots**, including
  **162/162** primary combinations (27 states × three measured CSS viewports × Botanical Light/Dark),
  six-theme shared/difficult-workspace samples, real forms/inspectors/menus/filters/validation,
  contextual/direct editors, long content and truthful unavailable states. Raster sizes are recorded
  separately because the browser API scales its JPEG output. Large binaries remain outside Git.
- Nine findings include two reproduced P1s: Media permanent-delete initial focus is destructive;
  shared tablet header has an axis/basis CSS collision (880 px header, Media gallery starts at 1102.8 px,
  Seeds inventory at 1031 px). Eight static before/after proposals, existing component ownership and
  scoped implementation waves prioritize these corrections without implementing them. Media owns
  photography/preview workflows; delivered Taxonomy keeps its accepted graph model.
- Focused audit verification: source feature graph baseline **115 valid**; final graph **116 valid**;
  **270/270** screenshot digests/files/DOM sidecars, complete primary coverage, **863** local HTML
  references, gallery script syntax, browser filter/comparison and eight-proposal render checks pass.
  Audit-only formatting and whitespace checks recorded in package validation; no canonical FULL gate,
  application suites/build, staging, commit, push, PR or merge.
- Explicit acceptance gaps: absent WFO means graph/fullscreen not captured; QR base URL unset means
  native print/QR/printer checks pending; actual 125%/150% zoom was unavailable (Ctrl+Plus did not change
  layout/DPR/scale); AT, physical touch, soft keyboard, forced colors/reduced motion and 320px remain
  manual. Coverage matrix lists additional missing states. No application records were saved or
  deleted after isolated fixture initialization. Audit feature is `implemented`, not `verified`.
- Operator decision pending; exact stop marker: `FLORABASE_GLOBAL_UI_AUDIT_READY_FOR_REVIEW`.

## 2026-10-27 — MEDIA-VISUAL-001 approved Quick Preview enhancement and QA

- Added an explicit **Save local copy** action only for external MediaAssets without a snapshot.
  Reused the existing authenticated CSRF API; pending, duplicate-submit protection, retryable failure,
  protected-original transition, success focus, and gallery refresh retain current selection and
  filter/page URL. Local and already-saved assets do not expose the action; detail Refresh/Remove
  remain unchanged. No backend, API, schema or shared UI code changed.
- Focused regressions: **42/42** passed across MediaScreen, MediaNavigation and URL navigation.
  Affected-file ESLint, Prettier, TypeScript and production frontend build passed. Tests cover saved,
  unsaved and local assets, no remote request on render, CSRF, success/failure, pending/double click,
  protected image refresh, selected preview, preserved filters/page and success focus.
- Reconciled against fetched `origin/main` `ee3487412fe458cbdf7145154c54a58b66132cae`; it is already
  an ancestor of the complete candidate, so no merge/reset was required. Independently reviewed the
  Media-only change; global PageHeader/dialog/filter ownership remains with the UI System audit.
- Rebuilt only the guarded `florabase-media-review-1d44` project through its owner adapter. Existing
  DB/media volumes and schema `20261013_0042` were retained. Actual Quick Preview confirmed external
  consent and actionable failure after two explicit Wikimedia fetch attempts. The source host did not
  yield a copy; the UI/API test success path is not represented as live success. Fixture check passed;
  no seed/reset, association mutation, copy write, primary/cover change or foreign environment change.
- The authenticated live failure state was visually inspected. Existing 1440/1024/880/390 captures,
  six-theme grid, and P1 acceptance records remain available. No new live success screenshot exists;
  external-fetch success, physical mobile/touch, assistive technology, real zoom and large-library
  performance remain limitations.
- Candidate remains unstaged/uncommitted pending exact-tree canonical verification and protected
  delivery. The feature remains `implemented` until all acceptance and receipt evidence is complete.

## 2026-10-26 — MEDIA-VISUAL-001 implementation ready for operator review

- Implemented full-width responsive4:3 photographic cards, deliberate contained PhotoDialog preview
  with actual record/cover context, prominent contained detail originals and shared-vs-link metadata.
  Protected lazy thumbnails, external opt-in and all existing mutation/retention contracts remain.
- Fixed the three P1 causes locally: Media wrapping header (98px desktop;186px at1024/880), Cancel-first
  destructive focus/safe detail title, and filter/offset/browser-history/card-focus restoration.
  Live URL-removal testing found and fixed an inherited-facet fallback; Back restores the prior state.
- origin/main remains ee348741; all earlier audit/evidence preserved. Global UI audit/UI System v1
  coordination confirms no shared primitive conflict. No shared UI, backend/schema/API or sidebar move.
- Regression122 tests/nine files passed; final affected40 tests/three files passed. Full/final ESLint,
  Media Prettier, TypeScript/build,116-feature graph and diff whitespace passed. No canonical FULL.
- Live Review15280:1440/1024/880/390, expanded/collapsed navigation, all six themes, preview/detail,
  record Photos, cover blocking, filters/pagination, safe cancellation and navigation inspected.
  31 inspected implementation captures added to the before/after gallery; historical proposal retained.
- Operator explicitly approved recovery of the existing synthetic media-review owner's lost password;
  same ID/data retained, four old sessions revoked. Private access file stays outside served evidence.
  Final read-only comparison confirms every detail on35 assets/20 links/two covers unchanged; no seed,
  domain deletion/primary/link mutation, or foreign environment change occurred.
- Physical touch/AT/real zoom and live storage-failure/race/high-resolution performance remain limits.
  MEDIA-VISUAL-001 implemented, not verified. All work unstaged/uncommitted; no PR/merge/delivery.
  Handoff: `MEDIA_VISUAL_001_IMPLEMENTATION_READY_FOR_REVIEW`.

## 2026-10-26 — MEDIA-VISUAL-001 populated live review ready for approval

- Established independently owned actual Review at **http://localhost:15280/#/media** using the
  existing Environment guards, a distinct project/database and project-owned network/media/dependency
  volumes. Standard Review volumes, DEV, UAT, Taxonomy, CI, global audit and production were preserved.
  Product code/API/schema/navigation remain unchanged; feature remains **planned** pending approval.
- Reused unchanged v4/80 and v5/252 fixtures; added a separate guarded Media ledger: **35 assets,
  27 stored locally, 20 record links, 11 primary uses and 2 Identity covers**. There are eight distinct
  licensed photographs, two explicit cover-upload reuse cases and 17 generated drawings, not 35 photos.
  Repeat seed preserved IDs/relationships; exact original hashes and six foreign-runtime refusals passed.
- Actual browser evidence covers requested 1440/1024/390×844 viewports in Botanical Light/Dark,
  representative Herbarium/Mineral appearances, 24/11 pagination, real photo/record/primary/cover
  relationships, contextual Photos, mobile filtering/Back, contained originals, linker Escape/focus,
  blocked deletion and explicit controlled external-preview failure. No browser domain write/delete.
- Confirmed **P1** shared tablet header at **880px** after clean reload (grid top 1102.8px), independently
  coordinated as global audit F09/Wave A0; **P1** destructive initial focus in Media confirmation;
  **P1** breadcrumb filter loss and missing invoking-card focus on mobile Back. No production fix yet.
  [Updated audit/plan](media-visual-001-design-review.md) defines shared/component ownership and risks.
- [Updated comparison gallery](review/media-visual-001/gallery.html): **42 new captures** (30 owned
  actual-application, 8 current-data proposal, 4 attributed audit supplements) plus the original 30
  historical captures. Current/proposed are explicitly distinguished; same eight photographs, current
  order/counts/association labels are used. Long metadata prompted reachable preview-header actions.
- Focused checks: **4 adapter tests**, 3 host-identity refusals, 6 runtime-identity refusals, repeat-seed
  equality, protected original/thumbnail HTTP401, Ruff, Python syntax, proposal JavaScript syntax,
  feature graph, artifact links and whitespace. Canonical FULL, staging, commit, push, PR and merge
  remain unstarted. Physical touch/AT/actual zoom, saved external-copy and cleanup/race cases, and
  high-volume/high-resolution photographic performance remain explicit limitations.
- Handoff: `MEDIA_VISUAL_001_LIVE_REVIEW_READY_FOR_APPROVAL`.

## 2026-10-26 — MEDIA-VISUAL-001 design review packet

- Audited delivered MediaAsset, RecordMediaLink, contextual Photos and separate Identity cover/
  primary contracts on verified main `ee348741`; attached `docs/media-visual-001` through feature-init.
  [Audit and prioritized plan](media-visual-001-design-review.md) separates current capability,
  source findings, real browser evidence and proposals. Feature remains **planned**.
- Read-only retained v5 DB snapshot: 17 assets (9 local/8 external-only), 18 record links, 37 identities,
  zero covers/saved external copies. All eight packaged photograph sizes/SHA-256 match manifest and
  retained attachments. No fixture, record, media or environment lifecycle writes occurred.
- Captured limited actual desktop gallery/preview/detail/blocked cover deletion/linker and Escape
  focus return in the existing two-photo Taxonomy Review. c902 Review ownership refused correctly;
  its frontend/backend were absent. Available runtimes became unavailable during inspection; no
  populated Media-owned Review URL, live mobile or complete product theme acceptance is claimed.
- [Visual study and evidence gallery](review/media-visual-001/gallery.html) proposes a full-width 4:3
  photo grid, on-demand uncropped preview and larger detail image using actual v5 data. Study-only
  checks: 18 captures across 1440/1024/390×844 and six token themes, 4/3/2 columns, eight loaded photos,
  no horizontal overflow; filters, keyboard activation/Escape/focus and detail return exercised.
- Documentation graph, packaged image integrity, study artifact/link checks and whitespace were
  checked. Broad product implementation, canonical verification, staging, commit and protected
  delivery remain unstarted. Handoff: `MEDIA_VISUAL_001_DESIGN_READY_FOR_REVIEW`.

## 2026-10-26 — TAXONOMY-VISUAL-001 final operator UX refinement

- Moved search and List/Tree explorer selection beside Filters in the page header.
  Kept source/version evidence and contextual search help, with bounded desktop
  panes and responsive controls. Replaced the permanent inspector identity list
  with exact Identities/Living/Current/Historical KPI popovers using shared control
  layering, protected covers, attribution and explicit 24-row progressive reveal.
- Unified hierarchy focus, placement status, stored-thumbnail availability and
  display preferences in Filters. Collection representation/category/query remain
  authoritative API inputs; local facets reaggregate the bounded projection using
  global record evidence. Tree depth/photos are display preferences. Remote-only
  cover absence is not inferred from missing stored thumbnails.
- Added native fullscreen with a shared TaskDialog full-viewport fallback. The same
  graph remains mounted; camera, selection and expansions survive transitions.
  Native external exit, Escape, focus return, nested filters/popovers and navigation
  cleanup are handled. Source fallback retained all 12 synthetic identities and was
  restored. No collection/confirmation/media records or protected environments changed.
- Focused frontend: **42 unique cases in nine files passed**, including shared
  control regressions; final fullscreen rerun **2 passed**. Targeted zero-warning
  ESLint, formatting, TypeScript/production build passed. Backend/API contracts did
  not change in this refinement, so prior backend evidence was not repeated.
- Updated handoff and final-UX gallery with measured normal/fullscreen viewport fit,
  all six themes at 1440/1024/390×844, KPI navigation and combined-filter Back/Forward.
  Canonical plan remains FULL; it was not executed. Candidate is implemented on
  `feat/taxonomy-visual-001`; main `3902b92` reconciliation and independent acceptance/
  final verification remain Luna's next phase. Geography PR #122 is
  merged into `origin/main` at `3902b92146f3afc21184e658dae64385e33f4926`; the
  candidate remains unreconciled. CI-004 remains a separate delivery.

## 2026-10-25 — TAXONOMY-VISUAL-001 implementation for operator review

- Implemented the approved compact Taxonomy workspace on delivered main `5778da7`:
  shared search/Filters, hierarchy/inspector, contextual Needs review, exact identity
  return navigation, source evidence and useful missing-source fallback. Reused
  delivered APIs, projections and the canonical confirmation/unlink panel; local
  names, scope/category semantics and security/version guards remain authoritative.
- Corrected trim-before-length source prefix validation and stale identity 409
  recovery. Refresh reads the authoritative identity, discards candidate review and
  requires renewed explicit confirmation. Source rechecks refresh the selected
  editor; successful writes refresh counts without losing the inspected identity.
- Independently owned synthetic full-stack Review: `http://localhost:15278`, own
  PostgreSQL/media/source fixture, eight identities/six placed/two unresolved; no
  WFO archive download or protected environment changes. Real HTTP and browser
  confirm/conflict/refresh/unlink scenarios passed. Browser evidence includes 32
  native captures, all six themes at 1440/1024/390×844, missing-source evidence,
  mobile/filter/identity navigation, source restoration and explicit matching.
- Focused verification: **48 backend**, **5 PostgreSQL integration**, **177 affected
  frontend** passed, followed by **15 Taxonomy tests** after the final source-retry
  correction (178 unique affected cases overall). Strict typing, zero-warning
  frontend lint, backend Ruff/mypy, formatting, both API drift checks, production
  builds, Review guard checks, feature graph (113) and whitespace passed. Disposable
  integration/build cleanup verified. Existing Starlette deprecation warning noted.
- [Handoff and exact limitations](taxonomy-visual-001-handoff.md),
  [gallery](review/taxonomy-visual-001/gallery.html). Geography remains independently
  owned/unmerged; shared documentation/App test additions need normal integration
  QA. AT, physical touch, zoom and full-dataset performance remain pending. Feature
  is implemented, not verified. No canonical FULL gate, staging, commit, push, PR,
  delivery, protected upgrade or primary/audit/foreign worktree mutation.

## 2026-10-26 — CI-004 verification efficiency ready for operator review

- Implemented on attached worktree `a4b0`, branch `ci/ci-004-verification-efficiency`, base
  `3902b921` (merged Geography #122). Audited local feedback/QA/gate, PR/main checks, delivery and
  finish using actual workflow code and GitHub job/step logs. See the
  [handoff](ci-004-verification-efficiency-handoff.md) and
  [timing/plan evidence](ci-004-verification-efficiency-evidence.json).
- Required `quality`/`integration`/`build` jobs stay unconditional and independent. Exact platform SHA
  mismatch refuses; validated merge parents drive CI-003 classification. Docs-only PRs run graph/
  whitespace checks; affected product PRs omit only workflow helpers. Product suites, API/static,
  integration and both production builds remain complete. Main/high-risk/unknown verification stays
  exhaustive; invalid policy fails. Added stage timing/exit/recovery diagnostics and retained full logs.
- Repaired 16 missing explicit frontend test entries and conservative shared-map/style/PartialDate
  FULL boundaries. Independent QA found and corrected the PartialDate consumer gap and an unsafe
  wrong-checkout FULL fallback; re-review reported no remaining actionable defect. Depth-two shallow
  Git/event smoke proves exact merge-parent selection; current-SHA recovery never automatically
  retries failed assertions. Local receipt/freeze, protected delivery and ownership guards remain.
- Focused checks passed: selector/receipt/remote **24**, resource **14**, feature/delivery **42**,
  Preview **19**, environment **35**, UAT Preview **19**, UAT source **15**; shell helper suite;
  `make workflow-check` Ruff/format/strict mypy and parsed CI/Dependabot policy; feature graph
  **114 valid**; tracked/staged/untracked whitespace. Real `make smoke-workflow-resources` retired
  all synthetic owned resources while actual operator environment identities remained unchanged.
  Exact-SHA remote build smoke built both production images and retired both owned outputs.
- Measured historical helper steps **71–90s**; full-repository always-FULL planning before/after
  **17.859s → 0.008s**, with exactly equal job command lists. Tiny docs-fixture CLI **0.645/0.611/0.605s**
  excludes hosted checkout/runner/artifact costs; selective planning over the actual worktree took
  **18.345s**. No hosted end-to-end percentage improvement is claimed. Remote product sectorization,
  cross-job caches and skipping main remain deferred. Open dependency #124's lint failure remains
  separate and cannot be exempted by these changes.
- CI-004 is `implemented`, not `verified`. Operator review, the final frozen-tree **FULL** canonical
  gate (including real migration cycle), receipt and hosted execution remain pending before delivery.
  Changes are unstaged/uncommitted; no push, PR, branch-protection change, real delivery/finish,
  DEV upgrade or persistent UAT operation occurred.

## 2026-10-26 — CI-004 final canonical verification blocked

- User authorized final FULL verification and protected delivery. One `make verify-full` ran
  **1352.50s**, then failed during frontend tests: **968/975 passed**; seven failures in
  `src/App.test.tsx` (Location deep links, Sourcing/Explore destinations, sidebar disclosures,
  Plants filters, identity Harvests, identity Events, and narrow identity selection). Workflow
  safety/checks, backend typing and backend unit tests passed. No receipt was issued.
- Isolated `App.test.tsx`: **114/115 passed** in **75.96s**; the identity section keyboard
  Back/Forward test reproducibly fails after `history.back()`. The six other failures did not recur
  in isolation; resource contention is possible but unproven. No test assertions or product code
  were changed.
- Candidate remains unstaged/uncommitted; no PR, hosted checks, merge, finish, DEV upgrade or
  persistent-data operation occurred. CI-004 remains `implemented`, not `verified`. Fix or resolve
  the app-test blocker, diagnose the suite-only failures and rerun FULL before staging/delivery.
  `CI004_DELIVERY_BLOCKED`

## 2026-10-26 — CI-004 navigation failure diagnosis

- Corrected the Botanical Identity keyboard-history test to wait for its lazy route import and
  exact URL state across keyboard selection, browser Back and Forward. Assertions still cover the
  real jsdom history behavior and selected tabs; no production route behavior or expectations were
  weakened.
- Focused validation passed: identity history test **1/1**, full `App.test.tsx` **115/115** in
  **84.34s**, and related Plant/Saved View/Dashboard Search browser-history checks **4/4** across
  three files. This accounts for the six other reported App failures as non-reproducing in the
  complete App file run; their original causes cannot be established because the failed FULL log
  was not retained. No resource-contention cause is claimed.
- The App failure behavior predates CI-004 and no production navigation regression was demonstrated.
  The candidate is ready for its one final FULL gate; the CI-004 handoff records a bounded proposal
  for a small diagnostic App-navigation preflight, without implementing another gate.
  `CI004_FINAL_FULL_PENDING`
- The first FULL attempt after these diagnostics stopped during frontend lint at **201.59s** before
  app tests: ESLint rejected a void-returning shorthand in the new `waitFor` callback. Changed it to
  a block; focused ESLint and the exact navigation test pass. No receipt was issued. The final FULL
  run must cover this frozen correction.

## 2026-10-23 — Themes/Controls integration with delivered Collection origins

- Merged main `46ade479` (MAPS-ORIGINS-001, PR #119) into `feat/themes-001` after reviewed combined
  implementation `564f479`, original base `b3f1de4`. Manually resolved renderer, workspace, test and
  graph conflicts. Delivered renderer/workspace match main; shared Manage provenance site action
  now lives in its new inspector. Native fallback, precision, consent/failure latch, counts,
  filters/Saved Views, mounted responsive panes and all main graph entries are retained.
- Added theme-switch regressions to main's richer Leaflet fixture; no delivered tests removed.
  The six-theme renderer checks cover preserved selection/camera/accuracy and unchanged local or
  explicitly consented online layer behavior. Leaflet site Tooltip uses semantic colors and borders.
  Fixed an asynchronous Settings test focus race using the existing wait timeout and exact assertion.
- Full frontend: **872/872 passed in 75 files**, including 19 Origins checks and 82 App cases.
  Final TypeScript, full zero-warning ESLint, formatting and production build passed; graph 111 valid,
  no conflict markers/unmerged index entries or whitespace errors. The first focused run was 132/133;
  isolated Settings retry and the corrected full suite passed. No canonical FULL gate or receipt.
- Actual authenticated browser: six palettes/modes retain 12 markers, selected origin 02, identical
  camera transform and zero online tile elements. Drawer/Tooltip layered Escape, focus return,
  Saved Views and phone/tablet inspector behavior checked. Existing split runtime preserved; no
  DEV/Review/UAT data or foreign source mutation. See [integration handoff and evidence](review/controls-001/origins-integration/README.md).
- Themes and Controls remain implemented, pending independent QA/canonical verification and delivery.
  Actual AT/zoom/touch, provider raster, first-paint filmstrip and physical print acceptance remain
  explicitly pending. Integration is committed locally; no push, PR, delivery or finish.

## 2026-10-23 — Independent Themes/Controls QA review

- Reconfirmed integration commit `1a712ca7d01ee7705433f98622ae625cd228be82` includes original
  implementation `564f479` and current fetched `origin/main` `46ade479`; no newer main changes.
  Independently reviewed conflict resolutions, feature graph, themes, shared actions, map renderers,
  tooltips, accessibility tests and print/raster invariants. No confirmed defect found.
- Confirmed exact split runtime ownership: current candidate Quality frontend on port 15174; Review
  backend, database and media remain owned by older `c902` at `b3f1de4`, and Review's own frontend is
  stopped. The supported ownership guard refused reuse. No environment or other worktree was changed;
  live browser observations are not treated as full-stack acceptance.
- Browser keyboard check verified Settings System mode and synchronized footer announcement, then
  restored the pre-check Mineral/Dark preference. Accessible names for Origins filters, Saved Views,
  inspector and its Manage action were present. Pointer dispatch timed out; automated tests cover it.
  Independent real AT, physical touch, forced-colors/reduced-motion emulation, browser zoom, downloaded
  GBIF raster, throttled cold first paint and physical print/QR checks remain deferred.
- The integrated 872-test frontend run plus TypeScript, ESLint, formatting, production build and
  feature-graph checks remain passing evidence. The canonical FULL gate and exact-tree receipt are
  pending and must cover the final committed handoff.

## 2026-10-23 — THEMES-001 + CONTROLS-001 combined visual-review candidate

- Implemented one local semantic SVG vocabulary, native action/link adapters, three action patterns,
  and accessible Tooltip with hover/focus, descriptions, collision handling, native modal/fallback
  overlays and ordered Escape. Settings now uses labelled horizontal sliders; functional theme state
  is retained. Shared directories, search, Saved Views, menus, details, forms, shell/mobile and
  representative capability actions reuse the same system; essential/domain actions keep text.
- Preserved the six approved THEMES palettes and original 143 PNGs. Added
  [Controls handoff](controls-001-handoff.md) and [gallery](review/controls-001/gallery.html):
  **113 product captures + 3 component-fixture images**, six variants, real desktop/tablet/phone
  layout sizes, separate export dimensions, no measured root overflow, 44px action targets and
  30 passing Tooltip contrast/hit measurements. Browser System/reload behavior and labelled
  creation-menu keyboard behavior were checked. Pending AT/zoom/raster/printing are explicit.
- Combined frontend run passed **859/859 in 75 files**. After the final navigation/chevron refinements,
  all 82 App cases passed and a fresh focused run passed **63/63 in 10 files**, including 9 Controls
  cases. Final TypeScript, full ESLint (zero warnings), formatting and production build passed
  (**219 Vite modules**); graph **110 valid** and whitespace checks passed. The full suite predates
  the two final visual refinements; no exact-tree canonical receipt is claimed.
- Restored the authorized split review after its runtime stopped: exact current Quality frontend on
  loopback 15174, retained matching backend and database/media. Ownership was inspected; helper source
  mismatch still prevents supported complete handover. No reset/reseed/migration/credential change,
  no primary/foreign branch edit and no DEV/UAT/Stable Preview/production mutation.
- Both features are **implemented**, not verified. Operator approval supersedes the historical
  separate-PR plan with one branch, combined visual review and later protected PR. No canonical FULL
  gate, staging, commit, push, PR or delivery. Stop at `READY_FOR_THEMES_CONTROLS_VISUAL_REVIEW`.

## 2026-10-22 — THEMES-001 implementation candidate

- Implemented the exact six approved Botanical/Herbarium/Mineral Light/Dark token sets, semantic
  capability colors, native controls, map chrome/comparison slots and print-safe overrides without
  changing application routes, type, spacing, domain state or image/raster pixels.
- Added one blocking same-origin browser-local preference store: independent palette and
  System/Light/Dark, validation, denied-storage fallback, first-paint attributes, live OS updates,
  cross-tab synchronization and authentication persistence. Settings native radios and both existing
  footer controls apply immediately; footer cycles System → Light → Dark → System. Settings gear and
  CONTROLS-001 implementation remain untouched.
- Prepared [handoff](themes-001-handoff.md) and [actual browser gallery](review/themes-001/gallery.html):
  126 six-theme captures at approved real viewport sizes where recorded, 16 supplementary page-family
  checks and one Dark label preview. All 2,520 measured root colors match approved values; no captured
  root horizontal overflow. Plants/group evidence was recaptured populated. No actual zoom claim.
- Retained Review database/media/session under the explicitly authorized split runtime: current Quality
  frontend on loopback 15174, retained owner backend. Helper ownership mismatch remains documented;
  no reset, deletion, copy or reseed. DEV/UAT/Stable Preview/production unchanged.
- Validation: final frontend **850/850 tests in 74 files passed**; focused 45/45 and targeted
  UX004/theme retry 27/27 passed. Repaired a partial browser API test-stub leak without changing
  assertions/timeouts. Final `pnpm typecheck`, `pnpm lint` (zero warnings), `pnpm format:check` and
  `pnpm build` (214 modules) passed. Built bootstrap exists before the module bundle. Approved contrast
  calculator: 72 cases, zero failures. Feature graph: 110 valid; whitespace clean.
- Limits: independent visual/AT/forced-colors/zoom and physical print acceptance remain; synthetic GBIF
  fixture has no downloaded raster, and unmerged MAPS-ORIGINS-001 needs later integration review.
  THEMES is **implemented**, not verified; CONTROLS remains **planned**, scheduled before remaining-page
  normalization. No canonical gate, staging, commit, push or delivery in this phase.

## 2026-10-22 — THEMES-001 and CONTROLS-001 design contracts

- Audited the accepted UI Foundation, semantic/legacy color rules, shared controls, Theme preview,
  Settings, auth/media/print and the three map renderers at `b3f1de4`. Added the
  [theme proposal](themes-001-design-proposal.md), [six-variant token matrix](themes-001-token-matrix.md),
  [controls contract](controls-001-design-contract.md) and [implementation plan](themes-001-implementation-plan.md).
  The controls contract specifies one local SVG vocabulary, three action patterns, accessible
  Tooltip/overlay behavior, labelled essential actions and responsive migration/testing boundaries.
- Proposed THEMES delivery first, CONTROLS second, then remaining-page normalization and final
  application-wide visual review. Both remain independently deliverable and `planned`; neither is
  claimed implemented/verified. No production component, CSS, dependency, API or migration change.
- Added [design specimens](design/themes-controls/review.html) covering six variants and three
  widths, the six requested toolbar contexts, and form/modal/map/Settings structures. Source Sans/
  Serif families and existing type scale use local fallback fonts when unavailable. These are design
  excerpts, not production screenshots or actual browser-zoom proof.
- Checks: baseline feature graph **108 valid** and whitespace clean; final graph **110 valid**.
  Reproducible sRGB contrast calculator **72/72 pass**; source-relative design links, JSON/Python/HTML
  structure and documentation whitespace checked. Browser DOM geometry for **18/18 specimen
  palette/width combinations** had no sheet/control overflow; Botanical Dark phone inspected visually.
  Runtime, screen-reader, true viewport/zoom, tooltip interaction and physical print validation remain
  Phase 2 work. Canonical verification was deliberately not run.
- Existing managed worktree attached to `feat/themes-001` with `make feature-init`; no second
  worktree, protected-environment change, staging, commit, push or delivery. Design review boundary:
  `THEMES_AND_CONTROLS_DESIGN_REVIEW_READY`.

## 2026-10-21 — SOURCING-VISUAL-001 synchronization and review

- Synchronized the existing Sourcing worktree without rewriting history: preserved the reviewed
  candidate in `f9eef43`, merged `origin/main` (`9275947`, Maps `#116`) in normal merge `c946acb`,
  and kept both the Sourcing and Maps milestones. No conflict was reported; `docs/features.json`
  remains main's version with `MAPS-FOUNDATION-001`, and `SUPPLIER-003` / `ORDER-001` stay the
  domain sources of truth for this presentation increment. No backend contract or migration change
  was introduced.
- Post-merge review fixed real regressions: Orders search no longer disables itself while a filtered
  page is in flight, so multi-character queries keep focus; a missing Supplier UUID is visible in
  both the filter label and active filter; Supplier Quick-Preview Edit returns to the preview and
  restores its remounted Edit trigger; Back out of a direct edit URL closes the inline editor and
  restores the heading in Suppliers and Orders; Supplier creation focuses its loaded detail heading;
  and `ReferencePicker` preserves typed queries when a parent rebuilds `choices`.
- Verification: focused frontend **157 tests / 7 files**; post-merge full frontend regression
  **820 tests / 70 files**; strict TypeScript, zero-warning ESLint, Prettier and `make api-check`
  pass. Workflow helpers **34/34** and Review fixture **24 passed / 1 live-only skipped**.
  `make sourcing-preview-status` is healthy at `15175` (DB `20261013_0042`, fixture v4/ready/79,
  9 Suppliers, 4 Orders, 11 SeedLots). The live UAT smoke was not run; UAT volumes were verified
  untouched. `make verify-full`, delivery and finish remain the exact-tree final gate/operator steps.
- Deferred: direct-edit browser Back discards an unsaved draft without a custom prompt (in-app dirty
  dismissal still confirms); dead `.orders-page` / `.order-list li` CSS; Orders Edit remains
  available when the Supplier list failed to load, with server validation still authoritative.
- Preview, Feature Review (`15174`), Maps, UAT, DEV, Stable Preview and production were not restarted,
  reseeded, reset or removed; no volume deletion or prune occurred.

## 2026-10-21 — SOURCING-VISUAL-001 Orders normalization

- Reused the accepted Collection directory/detail architecture for Orders: hidden search caption with
  accessible name, one-line toolbar, compact rows with amount fallback below identity at narrower
  widths, Quick Preview, route-driven New Order, contextual/direct Edit and a full-width dashboard
  with Overview and linked SeedLot tabs. The Supplier filter uses the shared ReferencePicker inside
  the drawer; long names wrap, the popup stays within the control width, and Escape closes the picker
  before the drawer. Create/Edit preserve optional Supplier, independent partial Order dates,
  optional exact amount/currency pair, total-not-per-lot semantics, explicit unlink/delete rules and
  no fabricated provenance or inventory.
- Normalized dismissal and geometry: pristine backdrop closes; dirty backdrop/Cancel/Escape protect
  changes; inside/dropdown clicks stay inside; opener focus is restored, including the remounted
  Quick Preview trigger and the refreshed detail heading after direct Edit cancel/save. The desktop
  New Order modal now hugs its compact two-column form (measured about 533px at 1440×844) and keeps
  its footer visible; mobile keeps the shared full-screen scrollable canvas.
- Verification: focused Orders/ReferencePicker/navigation/App **122 tests / 4 files**; full frontend
  **790 tests / 68 files**; strict TypeScript, zero-warning ESLint, Prettier, production build and
  `git diff --check` pass. Workflow helper **33/33**, Review fixture **22 passed / 1 live-only
  skipped** and UAT guard subset **12 passed** remain prior candidate evidence. Canonical
  `make feature-verify`, Python Ruff/mypy, full backend/integration/migration/API gates and the live
  UAT smoke were not run.
- Visual review used exact-size same-origin iframe proxies at 1440×844, 1024×844 and 390×844, not
  native window resizing. Confirmed the 1440 New Order/Edit footer fit, 1024 compact PageHeader and
  row fallback, 390 one-column modal/directory, 448px filter drawer with a 398px menu wrapping the
  long Supplier name, and the linked-SeedLot detail tab. Pristine/dirty dismissal, direct-link
  fallback and every 1024 modal state retain focused-test coverage rather than live capture claims.
- Review follow-up: `Link existing seed lot` now uses a centered 46rem maximum dialog with an
  internally scrolling `min(22rem, 42dvh)` list, row-style selectable lot cards with source/Supplier
  metadata and an explicit linked status, and a footer that keeps pagination and Cancel reachable.
  A true backdrop click and Escape both dismiss the link dialog; the Review purchase context step
  shares the backdrop behavior while retaining its pending guard. The Edit Order form grid now
  reserves six pixels of inline focus-ring clearance plus scroll padding, so the 3px outline/2px
  offset on edge fields is no longer clipped by the scroll box. Live geometry at 1440×900 measured
  a 736×684 link dialog with a 352px list; at 390×844 it measured 339×690 with the footer visible.
  Focused `PurchaseContext`/`OrderScreen` tests **22 passed**.
- Sourcing Preview remains isolated and healthy at `15175`: frontend/backend/database healthy,
  backend health `ok`, DB `20261013_0042 (head)`, fixture **v4/ready/79**, coverage 9 Suppliers (1
  retired), 4 Orders, 11 SeedLots (6 with Supplier, 5 with Order). A review-created blank 0-lot
  synthetic Order was deleted through the UI, restoring the four fixture Orders; no other record or
  volume changed. `sourcing_preview.py status` currently refuses its ancestry guard because the
  branch is **0 ahead / 1 behind** `origin/main`; read-only Docker/API queries were used instead.
  No Feature Review, UAT, DEV, production or Maps operation occurred.
- Git remains unsynchronized: HEAD `9a73d3f`, `origin/main` `9275947`, merge base `9a73d3f`. The Maps
  commit adds no migration and does not overlap local backend contracts; `docs/progress.md` is the
  likely merge-only overlap. Proposed synchronization is a normal merge followed by both milestone
  preservation, `make api-check` only, and the focused/full verification set — not rebase/reset/stash
  or force-push. All changes remain unstaged/untracked; no canonical gate, commit, push or delivery.
  Candidate is **READY_FOR_SOURCING_REVIEW**.

## 2026-10-21 — SUPPLIERS-VISUAL-001 and dedicated Sourcing Preview

- Added a first-class `sourcing` workflow role and thin `scripts/sourcing_preview.py` CLI. Sourcing
  Preview runs project `florabase-sourcing-preview` on loopback `15175` with its own database,
  network, images, owner and retained volumes, composed from `compose.yaml`, `compose.dev.yaml`,
  `compose.review.yaml` and the new `compose.sourcing.yaml`. Existing fixtures seed the isolated
  dataset; Feature Review, UAT, DEV and Stable Preview remain untouched. Commands and safety
  boundaries are documented in `docs/development-workflow.md` and exposed as `sourcing-preview-*`
  Make targets.
- Rebuilt the Suppliers workspace against the accepted Collection language: directory search/Saved
  views/`+ New supplier` toolbar, compact botanical rows with neutral visual fallback, Quick Preview,
  full-width create panel, contextual Edit modal with dirty dismissal/focus restore, and full-width
  dashboard-style Details. Supplier rules and markup stay in the supplier feature; supplier-only CSS
  lives in `supplier-refinement.css`. Orders work was not started in that increment.
- Found and fixed a real route race while triaging the full suite: the deferred detail reset could
  clobber an already-loaded supplier after direct creation or directory navigation. The reset now
  preserves ready detail for the current route id; regression coverage remains in the supplier and
  App integration tests.
- Verification: **106 focused tests / three files**, full frontend **780 tests / 68 files**, strict
  TypeScript, zero-warning ESLint, Prettier, and production build pass. Workflow/environment tests
  **33 OK**; Review fixture tests **22 passed / 1 live-only skipped**; UAT fixture guard subset
  **12 passed** under a simulated UAT identity. The UAT live dataset suite still requires the
  disposable guarded UAT smoke and was not run against Sourcing Preview. No API contract or backend
  schema change, so API drift/migration gates are unchanged.
- Live Sourcing Preview checks at `15175` confirmed nine seeded suppliers, detail loading, contextual
  Edit modal open/Cancel/focus restore, and zero horizontal overflow. Responsive 1024×844 and 390×844
  checks used same-origin iframes because native viewport resizing was unavailable; 1440-width
  evidence came from the live desktop window. Native 1440×844/1024×844/390×844 window resizing and a
  simultaneous Feature Review comparison remain operator checks. All changes are unstaged and
  uncommitted; candidate is **SUPPLIERS_READY_FOR_VISUAL_REVIEW**.

## 2026-10-18 — COLLECTION-VISUAL-002 operator screenshot follow-up

- Matched Harvest/Stored material typography and empty preview to Plants; rounded Location row/toggle
  controls and spaced/rounded stored-material actions. New Harvest's Material/Source controls now
  align vertically, and its right-hand fields have consistent edges, with mobile stacking preserved.
- Added explicit Location Active/Retired/All filtering, Active by default, with matching counts,
  ancestor context, preserved expansion, URL/Saved Views and no stale preview. Backend scope is the
  strict Saved Views state allowlist only; no new hierarchy query, schema or migration.
- Contextual Edit Location uses the shared field-width searchable parent picker. Full paths wrap;
  explicit root choice, cycle exclusions and guarded dismissal remain. An unselected search cannot
  silently reparent to root. Live menu widths equal inputs: 558px desktop and 320px mobile.
- Focused results: **186 frontend tests / seven files**, **85 backend contract/service tests**, plus
  final Location/StrictMode subset, targeted ESLint/Prettier, strict production build, scoped Ruff/mypy,
  feature graph and whitespace checks. Nine new captures are indexed in the updated handoff. No domain
  write, Review reset/reseed, UAT operation, canonical feature-verify, staging, commit, push or delivery.
  Candidate remains available for acceptance: **READY_FOR_VISUAL_REVIEW**.

## 2026-10-17 — COLLECTION-VISUAL-002 second visual refinement

- Continued the same dirty candidate and running Feature Review; no reset/reseed or UAT operation.
  Fixed Stored material's collapsed three-column row, grouped search/filter/Saved views, and added
  compact stock facts with primary conversion, secondary disposition and per-item More actions.
- Shared leading-edge selection now covers Harvests and Locations. Harvest rows omit source prose;
  Details ends its high-value Notes/History grid near 766px at 1440×844. Contextual correction uses
  Details/Materials/Notes tabs; one-line edit and ordinary conversion have no inner desktop scrolling.
  Root Location Details fits fully, ending near 803px, with direct/inclusive and active/total truth intact.
- Audited filter contracts: Seeds/Sowings/Plants APIs do not support typed identity/Location parameters;
  these remain documented gaps. Existing Harvest and stored-material filters use shared drawer/chips.
  No speculative API or domain change. Focused results: **316 distinct tests / 15 files**; the combined
  shared run exited 143 after three successful family suites, and the remaining eight passed separately.
  TypeScript/production build passed; final lint/format/feature-graph/whitespace evidence is in the handoff.
- Saved 31 second-pass captures at real desktop/tablet/mobile sizes plus explicitly labelled zoom
  proxies. Live dirty-Escape encountered a CDP input stall; automated dismissal/Back/Save-focus checks
  pass, while native confirmation and true zoom remain operator checks. Review remains running in a
  fresh view; no canonical gate, staging, commit, push or delivery. **READY_FOR_VISUAL_REVIEW**.

## 2026-10-17 — COLLECTION-VISUAL-002 implementation and visual-review handoff

- Started the supported feature branch at requested PR #112 base `a36c6cf`. Harvests now use minimal
  Collection rows/Quick Preview, full-canvas creation with source/category Back and Cancel, guarded
  contextual aggregate correction and a direct full-page Edit fallback. Full-width one-page Details
  separates Materials collected from managed Stored material and retains explicit conversion,
  history, deletion guards and shared Photos. No domain/API/schema/dependency change.
- Locations retain their nested/capped tree, search ancestors and nonzero occupied rows. Quick
  Preview adds complete contextual Edit; compact create/edit keeps explicit required scope-group
  semantics. Full-width Details labels direct/inclusive active/total record counts, enabled scopes,
  navigable hierarchy and quiet retirement, preserving every existing lifecycle/deletion guard.
- Replaced only the delivered candidate's disposable Review through its guarded old-owner workflow.
  Known Review owner credentials were set interactively and supplied in chat, never in repository
  files. Review is healthy at `20261013_0042`, fixture v4/80. Its deterministic Review-only extension
  supplies mixed PlantGroup materials, primary media, deep hierarchy and a retired empty Location.
  Repeat seed and 23 fixture guard/live-preservation tests pass. Persistent UAT and other operator
  environments were not changed; a session restart retained this candidate's Review DB/media/owner.
- Focused/shared frontend checks passed **409 distinct tests / 17 files** (overlapping reruns counted
  once), plus strict TypeScript, targeted zero-warning ESLint, production frontend build, touched
  formatting, scoped fixture Ruff, **106-feature** graph and whitespace checks. The live pass fixed
  inherited panel ordering/columns and modal footer specificity; **66 responsive observations** and
  **23 screenshots** record the final surfaces. No measured document/control horizontal overflow;
  125%/150% remain honest viewport proxies. Large aggregates scroll and a first hidden-browser native
  confirmation attempt stalled; component dirty-dismissal evidence and later live pristine navigation
  are distinguished. See the [handoff](collection-visual-002-handoff.md) and
  [evidence](review/collection-visual-002/README.md).
- `COLLECTION-VISUAL-002` remains `implemented`, pending operator acceptance and independent canonical
  verification. Canonical feature-verify, staging, commit, push and delivery were not run. Candidate
  remains dirty, unstaged and uncommitted, with Feature Review running: `READY_FOR_VISUAL_REVIEW`.

## 2026-10-17 — COLLECTION-VISUAL-001 independent review and canonical verification

- Operator accepted the fourth visual pass. Independent review confirmed scope is Collection UI,
  supporting docs and evidence only; no backend/API/schema/migration/dependency changes. Replaced
  stale test presentation expectations with current all-visible section roles, accessible quantity
  labels, the explicit View lineage route, and the shared Photos empty-state copy. Domain assertions
  remain intact. Focused Sowing/Supplier regressions: **19 passed / 2 files**.
- Canonical `make feature-verify` selected **FULL** against
  `1e3df6adf9afdfd4a213396666b336f6d1b5136c` and passed with a working-tree receipt: feature graph
  **105 valid**; workflow/environment suites; repository formatting, frontend lint, strict mypy
  (**346 source files**), TypeScript and API drift; backend **939 passed / 90.22% coverage**;
  frontend **755 passed / 68 files**; PostgreSQL integration **735 passed**; backend/frontend
  production builds; full migration cycle at existing revision **20261013_0042**; exact-tree receipt.
  No migration was added. All disposable integration/migration resources were cleaned by exact owner.
- Feature status is now `verified`. Responsive evidence remains precise: true browser zoom was not
  tested; 125%/150% were viewport proxies, guided-group measured 2px beyond the 844px viewport, and
  the live Back observation stalled after reaching its source. Feature Review is healthy at revision
  `0042`, fixture v4/66. The read-only inventory identifies persistent UAT as owned by worktree
  `4ff7`; the guarded UAT status command refused this checkout, and no UAT operation was made. Its
  volumes remain retained. The final canonical rerun follows this documentation/status change so its
  receipt matches the complete tree; commit, protected delivery and finish remain next.

## 2026-10-10 — frontend low-risk dependency batch (implementation handoff)

- From merged PR #85 main `aebe471`, updated only `@types/leaflet` **1.9.21 → 1.9.22** and
  `@testing-library/user-event` **14.6.6 → 14.6.7**, with pnpm-generated lockfile and no transitive
  churn. Node, React, Vite, jsdom, lint/format tools and backend dependencies are unchanged.
- Baseline App **73 passed**; updated focused App/form/map selection **104 passed / 7 files**,
  strict TypeScript/Leaflet declarations, frontend lint, dependency formatting and production
  frontend build passed. Bounded synthetic browser smoke covered auth, normal form creation,
  partial/final profile clearing and real Leaflet marker/popup behavior; exact owned cleanup passed.
- CI-003 selects **FULL** including migration cycle. Changes remain unstaged/uncommitted;
  canonical gate, independent review and delivery belong to Luna. See the
  [handoff](dependency-maintenance-frontend-low-risk-handoff.md), including cold-test readiness
  evidence. Independent review found the clear-flow test acted on a hidden Uses field; the test now
  activates its tab before clearing, without weakening assertions or changing production behavior.
  No roadmap status changed.

## 2026-10-10 — frontend low-risk dependency batch (Luna independent verification)

- Independent review accepted the two-package dependency scope and pnpm lockfile delta. The only
  test repair follows the real UI by activating “Uses & warnings” before accessing Uses; production
  behavior and all save/clear assertions remain unchanged.
- Canonical `make feature-verify` selected **FULL** and passed: **910 backend tests, 90.32% coverage;
  557 frontend tests across 57 files; 711 PostgreSQL integration tests; eight workflow checks;
  static/format/lint/type/API checks; backend/frontend production builds; full migration cycle at
  `20261009_0041`; exact-tree receipt. Node 24.19.0 and pnpm 11.19.0 were used by Quality.
- Independent synthetic browser smoke confirmed authenticated Dashboard boot, identity creation,
  profile save, partial/final clearing, and Leaflet marker popup. Exact fixture and Quality cleanup
  passed; protected project identities remained. No database migration or DEV upgrade is needed.

## 2026-10-10 — CI-003 independent verification and protected delivery preparation

- Independently reviewed the implementation, complete feature graph, CI ownership, resource
  registration/cleanup paths, failure/signal handling, verification selectors/receipts, delivery and
  finish guards, and real Compose evidence. No workflow defect or `NEEDS_SOL` blocker was found.
- `make smoke-workflow-resources` passed against isolated synthetic projects: exact target cleanup
  was idempotent, dirty-primary finish refusal preserved Quality, proven fixture finish retired only
  its own Quality resources, and DEV/Review/UAT/Stable Preview/production, another Quality owner,
  unrelated projects, and shared BuildKit cache remained unchanged.
- Explicit `make verify-full` passed. After final status and roadmap updates, `make feature-verify`
  independently selected **FULL** and passed with a final-tree receipt: feature graph **99 valid**;
  workflow/helper suites, repository format/lint/strict typing and API drift; backend **910 passed**
  at **90.32%** coverage; frontend **557 passed across 57 files**; PostgreSQL integration **711
  passed**; backend/frontend production builds; and migration **base → head → base → head** through
  `20261009_0041`. Every disposable run reported zero owned container/network/volume residuals.
- The first final-gate attempt had one transient frontend lazy-load timeout under exhausted host
  swap. The unchanged test passed three isolated repetitions and the complete frontend suite passed
  on the fresh full-gate retry; no test or timeout was altered. Final canonical rerun follows this
  progress-log update so the receipt matches the complete final tree.
- CI-003 is `verified`; no schema changes mean no DEV upgrade is needed. After protected delivery
  and `make feature-finish`, sweep open bot dependency-update PRs before DASHBOARD-001. No staging,
  commit, push, PR, delivery, or feature finish has yet occurred.

## 2026-10-10 — CI-003 scoped Docker retirement and impact-aware local verification implemented

- Audited the complete **99-feature** graph and existing workflow/build/environment ownership at
  SCHEDULE-001 merge `3592593`; extended existing **CI-003** rather than create a duplicate ID.
  Attached `c122` through `make feature-init`, branch `ci/workflow-resource-impact-verification`.
- Added a versioned explicit impact map over complete committed/index/dirty/untracked inventories,
  rename/deletion/mode/symlink changes and bounded transitive regression consumers. Unknown,
  foundational/security/dependency/migration/workflow paths escalate **FULL**. Canonical local gate
  derives affected/full automatically; explicit `verify-full` remains available. Docs-only skips all
  Docker/product/static runtime stages; ordinary product changes skip workflow suites. Remote
  protected quality/integration/build remain exhaustive and retain coverage policy.
- Version **2** receipts preserve exact tree/base/branch/HEAD integrity and additionally record map
  digest, scopes/reasons, selected suites, actual commands/results, migration/build outcomes and UTC
  completion. Write/read independently rederive selection; stale, unsupported, incomplete or
  differently mapped evidence refuses delivery. Focused iteration writes no feature receipt.
- Registered exact positive ownership retirement for integration, migration, selected production
  builds and existing unique smoke fixtures, including caught INT/TERM, partial creation and cleanup
  failure. Exact IDs/names, foreign-user preflight/recheck and residual verification replace silent
  migration cleanup. Quality status/cleanup is worktree-scoped; proven finish retires it only after
  all existing Git/PR/primary checks. DEV/Review/UAT/Stable/production persistence is preserved.
  Ambiguous images, legacy unknowns and shared default BuildKit cache are retained/reported;
  no global prune or retroactive other-worktree cleanup was introduced.
- Focused offline tests: selector/inventory/receipt **15**, resource/runner/signals **13**, feature/
  delivery **37**, environment **29**, Preview **19**, UAT **19**; shell/Git helper fixtures pass.
  Workflow Ruff format/lint (**19 files**) and strict mypy (**13 runtime files + 1 UAT fixture**) pass.
  Whole product format/lint/type/API drift checks pass, measured serially at **55.61 / 118.19 /
  91.24 / 22.54 s** including Quality startup. They remain global for product safety, with their
  material cost documented. Graph remains **99 valid**; shell syntax and whitespace pass.
- Real disposable Schedule PostgreSQL **12 passed** in **35.18 s**; forced migration cycle passes in
  **30.04 s** (this source has no new revision: base/feature head both **0041**). Each retires its
  project/image with **zero** owned containers/networks/volumes. Derived Taxonomy frontend selection
  **29 passed across 4 files** in **35.40 s** including startup. Separate backend/frontend production
  builds pass in **6.64 / 3.05 s**, each exclusively owned image retired without deployment.
- Real synthetic isolation smoke passes exact target cleanup, stale network/volume, idempotence,
  preservation of nine non-target projects including two independently derived Quality owners, and
  actual linked-fixture finish safety/retirement. All **11 containers / 12 networks / 12 volumes**
  retire; real DEV/Review/UAT/Stable/production identities and final reports match their snapshots.
  Initial smoke reproduced exhausted default IPv4 pools and still cleaned all partial fixtures;
  synthetic isolation uses explicit unique IPv6 subnets, without changing product networking.
- [Handoff](ci-003-resource-impact-handoff.md) and [machine evidence](ci-003-resource-impact-evidence.json)
  distinguish real substage timings from four deterministic before/after selection/resource plans.
  Focused docs-plan commands took **0.346 s**, creating no Docker resources; no old/new end-to-end
  canonical timing or percentage is invented. Current Quality intentionally stays reusable;
  legacy/other-worktree resources and shared cache stay intact. Existing full product smoke scripts
  were adapted/statically checked, not claimed executed. Luna owns independent review and the final
  **FULL** canonical gate. CI-003 remains `implemented`; next product increment is **DASHBOARD-001**.
  Primary source/main unchanged; no staging, commit, push, delivery, attached-feature finish, DEV
  upgrade, product visual UAT or canonical verification occurred. **READY_FOR_VISUAL_REVIEW**.

## 2026-10-10 — SCHEDULE-001 independent final verification

- Independently reviewed the Schedule domain boundary, authenticated API and generated contract,
  target lifecycle/deletion behavior, Event transaction/idempotency, bounded queries, migration 0041,
  and focused frontend/context integrations. No product-policy blocker or functional/accessibility/
  responsive defect remains. Broad cross-application visual redesign remains deferred.
- Reproduced and fixed four stale pre-existing integration expectations exposed by revision 0041:
  the exact schema table set now includes `scheduled_activities`, and populated older-migration refusal
  assertions retain the actual Alembic head `20261009_0041`. All four focused PostgreSQL regressions
  pass; the complete isolated PostgreSQL integration suite passes **711 tests**.
- Live Schedule Preview review at 1440×844, 1024×844 and 390×844 verified filters, explicit create,
  completion with and without an Event, cancellation with retained terminal evidence, browser Back,
  keyboard focus and no horizontal overflow. A synthetic review-only activity was created then
  cancelled; seeded examples were left intact. No DEV, Stable Preview or production resources changed.
- Canonical `make feature-verify` passed: feature graph/workflow checks, repository formatting/lint/
  strict typing, backend tests and coverage policy, frontend strict typecheck and **557 tests across 57
  files**, generated OpenAPI/TypeScript drift, isolated PostgreSQL integration, production backend/
  frontend builds, migration 0041 downgrade/re-upgrade verification, whitespace and a per-worktree
  receipt for this final reviewed tree.
- SCHEDULE-001 is `verified` in `docs/features.json`. Delivery, `make feature-finish` and
  `make dev-upgrade` remain the next authorized lifecycle steps; migration 0041 requires the DEV
  upgrade after successful delivery. See [handoff](schedule-001-handoff.md).

## 2026-10-10 — SCHEDULE-001 scheduled collection activities implemented

- Initialized attached `dcdf` through guarded `make feature-init`, branch
  `feat/schedule-001-collection-activities`, from `8eece520408679579114677b3e2537e23f357b4b`.
  The roadmap named SCHEDULE-001 but the base 98-entry feature graph omitted it; exactly one
  canonical entry reconciles the omission. No existing feature record/status changed.
- Added retained future intentions with complete date-only due days, eight narrow activity kinds,
  optional exact BotanicalIdentity/SeedLot/Sowing/Plant/PlantGroup/Location targets, explicit
  planned/completed/cancelled states and derived overdue. Timestamp/epoch coercion is rejected;
  browser grouping and displayed day share the returned device-day projection across midnight.
- Owner/Origin/CSRF-protected APIs use row locks and versions. Completion without Event creates no
  occurrence or History item. Explicit compatible Plant/PlantGroup Event recording invokes the normal
  service atomically, with independently entered occurrence day/notes, durable restrictive linkage
  and exact retry idempotence. Inactive references remain understandable; no lifecycle cascade or
  target inference. Migration `20261009_0041` adds only Schedule; populated downgrade refuses and
  empty downgrade/re-upgrade preserves unrelated records.
- Added Activity → Schedule with active date groups, canonical URL filters, bounded Dashboard
  counts/upcoming records and Plant/PlantGroup/SeedLot/Sowing detail context/preselection. Existing
  TaskDialog/ReferencePicker patterns retain accessible confirmations, focus, retry and stale-form
  recovery. Filters are initially collapsed for mobile access. Calendar, Schedule Saved Views,
  recurrence, notifications, attachments and generic task-management capabilities remain deferred.
- Focused checks: backend **93 passed**, `--no-cov`, Schedule/Event/Event schemas/History/Saved Views/
  Location/BotanicalIdentity service/API; real PostgreSQL **52 passed** (Schedule **12**, Event API,
  History and Saved Views), including actual two-session races, target lifecycle/deletion races,
  atomic rollback, API security/filters and migration preservation. Backend Ruff format/lint and strict
  mypy (**336 files**) pass; UAT fixture scoped Ruff and strict mypy (**1 file**) pass.
- Frontend **197 passed across 9 files** (Schedule/App/lazy App/Plant/Sowing/SeedLot/Journal/History/
  Saved Views), full strict TypeScript/ESLint, affected Prettier and asset build. Final inactive-label
  correction additionally passes **20 tests** (Schedule **16**, ReferencePicker **4**), strict
  typing, focused lint/format and asset build. The shared picker keeps its original default wording;
  Schedule preserves transferred/converted/exhausted labels. Fixed duplicate initial reads that
  could mask a load error; retry and session-expiry regressions pass. Existing navigation expectations
  include Schedule and await Journal readiness. No assertions/timeouts were weakened.
- Workflow regressions: `scripts/test-uat-preview.py` **19 passed** and
  `scripts/test-environment-workflow.py` **29 passed**. Guarded UAT up/seed/status and repeated seed
  succeed. `make api-generate` and `make api-check` pass; final backend OpenAPI export check confirms
  no drift after date validation. Structural API audit finds only six new paths/ten new schemas,
  with all existing contracts unchanged. Feature graph **99 valid**; final docs formatting and
  `git diff --check` pass. Final production backend/frontend image builds pass (`make build`), without deployment.
- Retired the prior `748b` Preview through its exact owning guarded remove command, as authorized;
  `dcdf` Preview remains healthy at <http://localhost:15174>, schema **0041**, with **53** manifest
  records and additive synthetic Schedule examples. Repeated seed preserves edits. Browser review
  covered 1440×844, 1024×844 and 390×844 without horizontal overflow, native keyboard date reschedule,
  create/context across all four detail types, no-Event completion, independent November due/October
  linked occurrence, cancellation, terminal evidence, Back, focus containment/Escape and mobile More.
  Synthetic operator review records remain explicit; no personal collection data was used.
- [Schedule contract](schedule.md) and [implementation handoff](schedule-001-handoff.md) record scope,
  date/target/completion policy, checks and UAT readiness. SCHEDULE-001 is **implemented**, pending
  Luna visual review/canonical verification. PHYLOGENY-001 remains planned/SOURCE_BLOCKED,
  TAXONOMY-003 verified, BOTANY-003/004 and ENRICHMENT-002 planned. Primary remains clean; no DEV,
  Stable Preview or production services/data were changed. No `make feature-verify`, staging,
  commit, push, delivery, finish or DEV upgrade occurred. **READY_FOR_VISUAL_REVIEW**.

## 2026-10-09 — PHYLOGENY-001 source audit blocked before implementation

- Initialized attached `4aaf` through `make feature-init`, branch
  `feat/phylogeny-001-collection-tree`, from clean current origin/main `33f5592`.
  Audited all 98 feature owners/dependencies; existing PHYLOGENY-001 remains planned.
- Securely inspected actual Open Tree archive/current API: **opentree16.1**, **OTT 3.7draft3**,
  December 2025 completion rather than the release page's inconsistent June text. Archive
  **41,608,973 bytes**, SHA-256
  `c447c83e49f0cf61fa96d9a02c6135b809abf315ad384fdb26b88359a28da12c`.
  Verified induced-subtree capability, actual public-name candidates, mixed/taxonomy support,
  conflicts and long unary/ancestral paths; no inferred WFO↔OTT mapping or branch dating.
- Exact data-rights gate **SOURCE_BLOCKED**: current conditional CC0 terms plus mixed/unlicensed
  source repository, nine pinned input snapshots (three CC0, one empty, five missing license fields)
  and no release-specific license did not establish current redistribution scope for the exact
  synthetic result with required annotations. The producer's positive **2017 synthetic/OTT CC0
  declaration** is explicitly retained, not ignored; no prohibition on synthetic reuse is claimed.
  Recorded a precise reopening criterion and minimal derived-content boundary in the
  [source decision](phylogeny-001-source.md), [planned contract](collection-phylogeny.md) and
  [blocked handoff](phylogeny-001-handoff.md). No product implementation follows a failed source GO.
- Focused existing offline baseline: **54 passed**, `--no-cov`, taxonomy source/service/API and
  Species distribution/Native ranges Explore. Reused installed UAT development image with current
  source read-only, network disabled and no application/database volumes; no new build under host
  disk/swap pressure. Feature graph **98 valid**. Pinned Prettier passes all seven changed documents;
  `git diff --check`, local documentation links and final scope audits pass.
- Canonical `make feature-verify` passed: repository lint/format/type checks, backend **895 passed**
  (90.03% coverage), frontend **541 passed**, PostgreSQL integration **699 passed**, generated API
  drift check, production backend/frontend builds, and migration cycle (**no Alembic revisions
  added**). It recorded the verified working-tree receipt. Verification reran after this progress
  correction; no migration or DEV upgrade is applicable.
- Read-only UAT status confirms actual `748b` owner, frontend/backend/db healthy and migration
  **0040**; source mismatch correctly refuses takeover from `4aaf`. Existing Taxonomy UAT preserved.
  No UI, API generation, migration, index, confirmed OTT fixture, PostgreSQL implementation suite,
  frontend phylogeny tests, performance/render benchmark or visual review claimed. Primary was clean
  at source-gate stop; no DEV/Stable Preview/production changes or migration step is applicable.
- TAXONOMY-003 stays verified. TAXONOMY-001/002, BOTANY-003/004 and ENRICHMENT-002 stay planned;
  SCHEDULE-001 and broad cross-application visual review remain deferred. **SOURCE_BLOCKED**,
  not READY_FOR_VISUAL_REVIEW. This is audit documentation only; no visual product review applies.

## 2026-10-09 — TAXONOMY-003 collection-aware classification implemented

- Initialized attached `748b` through `make feature-init`, branch
  `feat/taxonomy-003-collection-tree`, from verified cached origin/main `a8ae74a`.
  Securely audited the complete official WFO Plant List 2026-06 ColDP archive and publisher
  exporters before implementation. Classification-only CC0 source GO pins checksum, release,
  exact parent/synonym semantics and the biological Plantae boundary; no TLS bypass or HTML scraping.
- Added optional ignored 394 MiB local SQLite hierarchy index and one canonical operator-confirmed
  WFO relationship per BotanicalIdentity. Explicit local search → inspect → Confirm, stale/version
  revalidation and unlink preserve local names/profiles/other providers and material Lineage.
  Migration `20261009_0040` adds only links and refuses populated downgrade.
- Reused shared EXPLORE-001/002 representation/category projection for collection-pruned paths,
  distinct identity counts, literal local search, family/genus details, unresolved knowledge,
  full identity breadcrumbs and taxonomy-only Related in my collection. Responsive keyboard tree,
  stable URL filter/selected-node state; Saved Views deliberately deferred.
- Implementation-focused suites passed: **96 offline backend tests**, **58 PostgreSQL tests**
  (including concurrent confirmation, migration preservation and Explore/provider regressions),
  **19 UAT workflow tests**, and **104 distinct frontend tests**. Final independent gate results are
  recorded below and in the [handoff](taxonomy-003-handoff.md).
- Initial implementation measurements under concurrent image/build load included a 34.48 s first
  UAT projection and a 6.93 s checksum-only run. Independent post-restart review with no image/build
  process running rendered the six-identity UAT Taxonomy view in 8.84 s and an immediate page reload
  in 1.07 s. The host still had load 3.78, 1.9/2 GiB swap used, and 1.1 GB free disk. A separate
  same-UAT-database measurement returned 6 identities, 23 required nodes, one unresolved identity,
  13,226 UTF-8 serialized-model bytes, and constant 2 PostgreSQL SELECTs + 3 SQLite statements;
  first/warm same-process projections took 1.84 s / 22 ms with the index already OS-cached. The
  34.48 s many-tens-of-seconds delay did not recur, though this was not an unpressured host baseline.
  A 500-identity synthetic test returns five nodes in 299 ms.
- Retired old Preview only through actual owner `16cc` guarded remove; current `748b` UAT seeded
  with 44 manifest records, five exact real WFO links, same-genus/family coverage and unresolved
  lavender. Repeat seed preserves edits. Initial frontend health deadline during initialization
  recovered without timeout changes: status reports correct source, 0040, healthy app/db, proxy 200.
  Functional browser review covered 1440×844, 1024×844 and 390×844, keyboard focus/expansion,
  node detail, related peers, breadcrumb and advisory source-synonym inspection without overflow.
- TAXONOMY-003 is **verified**. TAXONOMY-001/002, PHYLOGENY-001, BOTANY-003/004 and ENRICHMENT-002
  remain planned; broad cross-application visual review stays deferred.

## 2026-10-09 — BOTANY-003 source re-audit; narrow description source approved

- Initialized the attached `857e` worktree through `make feature-init`, branch
  `feat/botany-003-profile-enrichment`, from clean current cached origin/main `345e9f2`.
  Audited the complete two-field approved contract and delivered ENRICHMENT-001 implementation.
  Fresh host curl, existing development/runtime HTTPX and newly built worktree HTTPX rejected the
  exact official Flora of China archive before HTTP bytes; verified OpenSSL still shows the missing
  issuing intermediate and fatal error 20. Official static WFO Plant List release 2026-06 is a
  taxonomy source candidate, not proof of a replacement descriptive-content artifact.
- Independently retrieved WCVP v15 securely: **89,508,082 bytes**, SHA-256
  `693e05b31ea6ce724c88ccf38bb964db2f22424b396f7ed1fd04fdb203af7e81`, actual retrieval
  **2026-10-09T12:32:17.250119Z**. Complete **1,441,152** names-row scan confirms distinct
  geographic_area prose; source-field GO remains separate from structured ranges. No invented
  description, range-derived prose, provider ID crosswalk, TLS exception or page scraping.
- Separate source discovery securely inspected three complete official SEPASAL CSVs: taxa,
  major-use references and note references. Dataset-specific CC BY 4.0, TaxKey, cultivation/use/
  toxicity categories and bibliographic joins make this a concrete future candidate for those fields;
  exact cultivation/use/warning field imports remain unapproved. A later bounded description review
  approved only three exact SEPASAL / Flora Zambesiaca records under the dataset's CC BY 4.0 license.
  This does not approve the remaining records or provide broad coverage.
- Preserved existing TAXONOMY-001 reconciliation and TAXONOMY-002 name-history owners. Added
  **planned TAXONOMY-003** collection taxonomy browsing, **planned PHYLOGENY-001** separate
  evolutionary-tree discovery and **planned BOTANY-004** other profile-field source review.
  Updated roadmap, approved/deferred domain requirements, source decisions and blocked handoff.
- Focused current baseline passed **72 backend unit tests**, `--no-cov`. Feature graph **98 valid**
  and `git diff --check` passed. Pinned Prettier 3.9.6 passed for all ten changed documents. No text implementation,
  migration, generated API, PostgreSQL text/concurrency checks, new frontend tests or visual QA is
  claimed; these remain pending at the source prerequisite. The quality baseline built its current
  development image. No canonical `make feature-verify`, staging, commit or delivery.
- Read-only UAT status confirmed healthy prior owner `16cc` and schema **0039**; source mismatch
  correctly refuses this worktree's takeover. Preserved that Preview and its review evidence because
  no BOTANY-003 UI exists. Primary source and DEV/Stable Preview/production state were not changed.
  BOTANY-003 remains **planned**. Its exact Flora of China source is **SOURCE_BLOCKED**; the three
  reviewed SEPASAL records are a narrow `DESCRIPTION_SOURCE_GO`, insufficient for general
  BOTANY-003 implementation. This is not READY_FOR_VISUAL_REVIEW.
  [Current sources](botanical-profile-enrichment-sources.md), [separate discovery](botanical-knowledge-source-audit.md),
  [future taxonomy](collection-taxonomy-plan.md), [blocked handoff](botany-003-handoff.md).

## 2026-10-09 — ENRICHMENT-001 independent verification

- Operator UAT and independent domain/UI review passed. The independent final gate initially found
  one stale integration assertion: a populated downgrade from the new `20261009_0039` head
  correctly rolls back transactionally at `0039`, but the prior test expected `0038`. Updated the
  expected current revision; the focused reproduction passed and the full canonical gate then
  passed on the final tree.
- `make feature-verify` passed: **95 feature records valid**, **856 backend unit tests** with
  **90.04% coverage**, **534 frontend tests**, **693 PostgreSQL integration tests**, strict mypy
  (**317 files**), Ruff/format, Prettier/ESLint, strict TypeScript, OpenAPI drift, production build,
  migration verification and whitespace checks. A tree-specific verification receipt was recorded.
- Integration first could not allocate a Docker bridge because 14 unattached
  `florabase-quality-*` networks had exhausted the default pools. After inspecting their exact
  Compose labels, IDs, subnets and zero endpoints, only those verified quality orphans were removed
  explicitly. DEV, UAT Preview, Feature Review, Stable Preview, production and all running-container
  network assignments were preserved. The fresh integration project allocated and cleaned up its
  network successfully; the full gate passed without a Docker-pool or memory-pressure failure.
- ENRICHMENT-001 is **verified** and ready for reviewed local commit and protected delivery. Delivery,
  conservative finish and the required DEV upgrade for migration `20261009_0039` remain pending.
  Broad cross-application visual/product review, ENRICHMENT-002 and SCHEDULE-001 remain future work.

## 2026-10-09 — ENRICHMENT-001 structured native-range implementation

- Source GO preceded implementation: exact official **Kew WCVP v15** plain archive, README,
  complete schemas/rows and release-specific CC BY 3.0/citation were inspected. Retained SHA-256
  `693e05b31ea6ce724c88ccf38bb964db2f22424b396f7ed1fd04fdb203af7e81` and actual UTC retrieval.
  Explicit optional provisioning built the complete local **1,441,152-taxon / 1,986,879-assertion**
  SQLite index. It is ignored/excluded from Git/images; ordinary startup/API/Apply use no provider
  network. Missing source data preserves canonical ranges, profile editing and durable evidence.
- Added explicit WCVP taxon review/confirmation, frozen current-versus-proposed range evidence,
  a versioned twelve-unit literal TDWG/canonical crosswalk, visible excluded partial/split/unresolved
  units and original Native/Introduced/extinction/doubtful flags. Only explicit selected unqualified
  Native Apply adds existing `BotanicalProfileNativeRange` links; every current range is kept and
  no profile text or material origin changes. Removal/replacement is unsupported.
- Migration **20261009_0039** adds separate source links, monotonic destination revisions, frozen
  proposals and immutable applications. Locked source/link/identity/geography/destination/crosswalk
  checks reject stale/repeated Apply atomically, including edit-and-restore. Frozen v15 proposals
  can apply without the source index. Applied provenance survives manual edits/link changes and
  blocks identity deletion; deletion serializes with Apply. Empty downgrade preserves canonical
  ranges/text; any source link/proposal/application refuses populated downgrade.
- Source review is inside the existing BotanicalIdentity Reference → Native range module, with
  literal prefix search, exact IDs/accepted context, selective checkboxes, Add/Keep confirmation,
  immutable history/outcomes, source attribution, explicit retry and focused feedback. Corrected
  schema-name collisions with Media during generated-type verification and made source reprovision
  stale state/deletion feedback explicit. Updated the exact database table inventory and mock
  reference counts for the four intentional new tables; existing assertions remain strict.
- Final focused checks passed: **75 backend unit**, **81 disposable PostgreSQL integration**,
  **38 distinct frontend**, **19 host UAT guards**; Ruff/format, strict mypy (**315 files**),
  Prettier/ESLint/strict TypeScript, OpenAPI generation/drift, Vite production bundle, both production
  Docker runtime builds, **95-feature graph**, whitespace. Real PostgreSQL covers migration cycle,
  populated refusal, immutable evidence, stale state, concurrent Apply and Apply/deletion races.
  Production startup/health also passed with no source index, network disabled and read-only root
  plus ephemeral attachment tmpfs. Existing six Alembic path-separator deprecation warnings remain.
  Initial disposable subnet overlap was resolved using a free scoped subnet, with no product change.
- Guardedly retired the previous UAT through its owner `258f`, then started and explicitly seeded
  this worktree's **http://localhost:15174**, **preview / preview**, schema **0039**, fixture
  **v4 / 42 baseline records**. Startup's first health window expired during frontend dependency
  installation; frontend subsequently became healthy. Exact Aloe smoke added Oman, kept manual
  Thailand/Italy, refreshed canonical ranges and retrieved a fresh KEEP proposal; its source link
  and immutable application are retained for operator review. DOM/accessibility checks at
  **390×844, 1024×844 and 1440×844** showed no horizontal overflow and focused success feedback.
  No operator acceptance is claimed. No personal collection data or DEV/Stable Preview/production
  state was changed; primary checkout remains clean.
- At implementation handoff ENRICHMENT-001 was **implemented**, pending operator product UAT and
  Luna independent review; the later verification milestone above records its completed status.
  BOTANY-003's blocked text contract is unchanged; ENRICHMENT-002 automation, SCHEDULE-001 and broad
  cross-application product/visual review remain future. Tree stays **unstaged/uncommitted**;
  no canonical feature gate/receipt, commit, push, delivery, merge or finish was performed.
  [Source audit](native-range-enrichment-source-v15.md), [contract](native-range-enrichment.md)
  and [handoff](enrichment-001-handoff.md) retain exact evidence and review scenarios.

## 2026-10-08 — EXPLORE-002 independent final verification

- Independent review found the implementation aligned with the accepted collection-aware Native
  ranges contract and operator UAT. No production behavior defect was found. Three integration tests
  had stale hard-coded expectations for migration `0037`; those test assertions now read Alembic's
  current head, and their focused rerun passed.
- Canonical `make feature-verify` passed on the reviewed tree: **804 backend unit tests** at **90.06%
  coverage**, **528 frontend tests**, **673 PostgreSQL integration tests**, feature graph (**95 valid**),
  Ruff/Prettier/ESLint, strict mypy (**303 files**), strict
  TypeScript, API drift, both production image builds, migration cycle `0037 → 0038 → 0037 → 0038`,
  whitespace checks and a working-tree verification receipt.
- Migration `0038` is additive and passed its populate/refuse-downgrade and empty-cycle checks.
  Existing Alembic path-separator deprecation warnings remain. The operator accepted functional UAT;
  the broad cross-application visual/product review remains deferred before release hardening.
- EXPLORE-002 is `verified` and ready for its reviewed local commit and protected delivery. Delivery
  and `feature-finish` are still pending. Because this feature adds migration `0038`, successful
  delivery must be followed by `make dev-upgrade` on DEV. No production or Stable Preview state was
  modified.

## 2026-10-08 — EXPLORE-002 bounded operator UAT refinement

- The operator has now **accepted the current functionality for delivery**; broad visual/product
  review remains explicitly deferred across the application. Added explicit
  checkbox selection up to **20** identities, Selected species (N), deselection/Remove/View only/Clear,
  exact one-species detail and multiple-species distinct territory coverage with contributor lists.
  Per-identity broad/precise overlap counts once. Missing/filter-excluded IDs remain explicit and
  contribute no coverage; no query-wide selection or arbitrary replacement.
- Added OR **Collection records** filters for Seeds/Sowings/Plants/Plant groups/Stored material.
  Status remains single-select; Current qualifies active selected-category records, Living qualifies
  selected Plant/PlantGroup records, Historical requires retained selected-category evidence and
  globally no Current representation. Directory/overview/selection share all eligibility filters.
  New bounded comparison endpoint uses **2 SELECTs**, including twenty-ID requests; existing 2/4/4
  directory/overview/exact-detail query bounds remain. No domain/provider writes.
- Canonical repeated-ID/category URL and Saved View v1 sets restore deterministically; singular v1
  UUID state remains readable. No additional migration beyond **0038**. Desktop Explore now places
  Botanical identities/Media/Geography before non-actionable **Maps** text and the three unchanged
  map destinations; mobile remains flat with every destination.
- Audited official Kew WCVP/POWO sources and the complete **95-feature** graph. Refined existing
  **planned ENRICHMENT-001** for a separately reviewed structured-native-range candidate immediately
  after EXPLORE-002 delivery, before SCHEDULE-001 unless reprioritised. Exact reviewed taxon matching,
  TDWG crosswalk, provenance and operator-reviewed replacement remain future decisions. BOTANY-003
  stays unchanged. Recorded the later broad cross-application review checkpoint before release hardening.
- Final focused checks: **97 backend unit**, **39 disposable PostgreSQL**, **152 distinct frontend**
  tests (151 main-run passes plus corrected route-order test rerun), **23 read-only UAT runtime/fixture**,
  **19 host guard**; Ruff/format, strict mypy on 6 changed source files, CLI import lint,
  frontend Prettier/ESLint/strict TypeScript, Vite production build, API generation/drift, feature graph
  and whitespace passed. Existing 18 Alembic warnings remain. No full canonical gate/receipt is claimed.
- Task-owned UAT stays healthy at **http://localhost:15174/#/native-ranges**, **preview / preview**,
  schema **0038**, fixture **v4 / 42**. The explicit additive stored-material extension and repeated
  seed preserve existing operator edits/inventory; no reset. DOM/accessibility checks at
  **1440×844, 1024×844, 390×844** confirmed comparison, filter exclusion, one-species links,
  refresh and mobile IA without horizontal overflow. No screenshots.
- At this handoff the feature tree remained **unstaged/uncommitted**. The operator has authorized
  independent review, canonical verification, commit and protected delivery; the final verification
  evidence is recorded above.
  See [updated handoff](explore-002-handoff.md) and [source audit](native-range-enrichment-audit.md).

## 2026-10-08 — EXPLORE-002 implementation and UAT handoff

- Added the separate Native ranges Explore workspace with Collection overview and Selected species.
  Reused GEOGRAPHY-002's exact profile-owned range relationships and EXPLORE-001's representation,
  lifecycle/inventory scopes and literal search. No occurrence, prose or material-provenance inference.
  Broad/precise overlaps count distinct identities once per map territory; exact relationship lists
  retain broad, disjoint, custom and unavailable places without rewriting stored knowledge.
- Reviewed and pinned Natural Earth 1:110m Admin 0 map units (dataset 5.1.1, repository v5.1.2,
  public domain). Bundled 179 SVG paths in a separate lazy geometry chunk, **150.83 kB / 60.46 kB
  gzip**, with exact ISO mapping and canonical M49 descendant drawing primitives. Missing/custom
  boundaries stay explicit. Raw JSON parse median/p95 **0.56/0.99 ms** in local Node; this does not
  measure device paint. No runtime geometry/provider fetch or GIS persistence/library was added.
- Added authenticated bounded directory/overview/selection endpoints with constant **2/4/4 SELECTs**,
  summary totals independent of pagination and HTML map/count/precision companions. Canonical URL
  and private v1 Native ranges Saved Views persist stable scope/search/mode/identity/filter only.
  Migration **0038** solely extends the surface constraint and locks/refuses incompatible downgrade.
- Focused checks passed: **93 backend unit**, **38 isolated PostgreSQL** and **147 frontend** tests;
  Ruff/backend formatting (**344 files**), strict mypy (**303 files**), CLI syntax/import checks,
  geometry reproducibility, frontend Prettier/ESLint/strict TypeScript, `make api-generate`,
  `make api-check`, feature graph (**95 valid**), both final production image builds and
  `git diff --check`. After lint corrections, the **60 affected frontend tests** and Vite build
  passed again; see [handoff](explore-002-handoff.md). Existing 18 Alembic
  path-separator warnings remain; exhausted default Docker address pools were handled with an
  isolated subnet in the disposable final PostgreSQL project, which cleaned its own resources.
- Retired previous `c6cd` UAT through its owning guarded command, started this worktree, corrected
  an initial malformed fixture call and recovered only the incomplete synthetic preview through
  guarded reset. UAT is healthy/current at **0038**, fixture **v4 / 41 records**; repeated seed and
  **21 read-only runtime/fixture checks** plus **19 host guard tests** passed. All 5 / Living 2 /
  Current 4 / Historical 1, broad+Brazil overlap, disjoint Italy/Thailand, custom and no-range examples
  are ready at **http://localhost:15174/#/native-ranges**, **preview / preview**.
- DOM/accessibility inspection covered overview/selection at **1440×844, 1024×844 and 390×844**,
  wrapping, mobile navigation, native manager link, Saved View dialog and clear-selection focus;
  no horizontal overflow or screenshot artifacts. Operator visual/product UAT remains pending.
  EXPLORE-002 is **implemented**, all changes unstaged/uncommitted. Canonical `make feature-verify`,
  independent review, commit and delivery remain Luna's responsibility. Primary, DEV, Stable Preview
  and production runtime state were not modified. SCHEDULE-001 remains future; biological daily-use
  candidates remain next choices and BOTANY-003 stays blocked/unchanged.

## 2026-10-08 — EXPLORE-001 independent verification

- Independent final review found no production behavior defect. Collection projections, exact provider
  link use, query/paging bounds, Saved View/URL restore behavior, migration downgrade protection and
  the no-inference/no-persistence boundaries matched the accepted contract and passed operator UAT.
- Canonical `make feature-verify` passed on the reviewed tree: **797 backend unit tests** at **90.06%
  coverage**, **508 frontend tests**, **662 isolated PostgreSQL integration tests**, feature graph
  (**94 valid**), workflow helpers and static policy, Ruff/Prettier/ESLint, strict mypy (**299 files**),
  strict TypeScript, API drift, both production image builds, migration cycle
  `0036 → 0037 → 0036 → 0037`, whitespace checks and a working-tree verification receipt.
- Disposable PostgreSQL integration and migration-cycle resources were cleaned by their workflows.
  Existing Alembic path-separator deprecation warnings remain. Operator UAT had already passed; no
  product code changed after acceptance.
- EXPLORE-001 is `verified`; this tree is ready for its reviewed local commit, protected delivery and
  `feature-finish`. Migration `0037` means successful delivery must be followed by `make dev-upgrade`.
  Next after delivery: separate **EXPLORE-002 — Native ranges**; SCHEDULE-001 remains future and
  BOTANY-003 remains blocked/unchanged.

## 2026-10-08 — EXPLORE-001 implementation and UAT handoff

- Added authenticated bounded collection-aware identity discovery and Species distribution under
  Explore. Exact SeedLot/Plant/PlantGroup, Sowing → SeedLot and managed inventory → Harvest → source
  relationships define All represented, Living, Current and Historical. Historical excludes identities
  with any current representation; terminal/reversed/reintegrated evidence is retained. Grouped SQL
  yields unique identities and two SELECTs for totals/page, with literal search and deterministic paging.
- Reused MAP-002 unchanged for deliberate one-identity occurrence loading, quality policy, density,
  attribution and privacy. Discovery/selection/Saved Views perform no provider requests. No occurrence
  persistence, scientific-name rematching, native-range inference or Collection origins change.
- Added canonical local URL/v1 Saved View state with explicit stale/missing selection and same-view
  page-one/unloaded-map reset. Migration `20261008_0037` extends only the surface constraint and
  safely refuses populated downgrade under a writer lock; compatible cycles preserve existing views.
- Initial focused verification: **115 backend unit**, **35 isolated PostgreSQL**, **130 frontend** tests and
  **20 guarded fixture** tests passed. Ruff/backend formatting (**339 files**), strict mypy (**299
  files**), focused workflow-script policy/typing, frontend Prettier/ESLint/strict TypeScript,
  `make api-generate`, `make api-check`, feature graph (**94 valid**), both production runtime image
  builds, frontend Vite build and `git diff --check` passed. Existing Alembic path-separator warnings
  remain. Canonical `make feature-verify` was deliberately not run.
- After explicit operator approval, retired the old owning UAT with its guarded command and started
  this worktree's preview. Healthy source/schema `0037`, fixture v3 (**38 records**), repeated seed
  idempotence and baseline guards verified. Living basil/aloe, Current non-living lavender, Historical
  long-cultivar radish and excluded reference-only Viola support UAT; basil has the reviewed real
  CoL XR `48GBK` link, seeded offline through existing confirmation with no fabricated occurrences.
- Operator UAT passed. Independent route inspection confirmed the four expected identities, one locally
  occurrence-ready link and reference-only exclusion. A narrow viewport inspection showed vertical flow
  and wrapping of the long cultivar; automated tests cover explicit map load and error/zero states. No
  screenshot files saved. Preview:
  **http://localhost:15174/#/species-distribution**, **preview / preview**.
- EXPLORE-001 was `implemented` pending the independent review recorded above. EXPLORE-002 Native ranges is the preferred next separate increment;
  SCHEDULE-001 remains future and BOTANY-003 blocked/unchanged. See [handoff](explore-001-handoff.md)
  and [contract/lifecycle matrix](species-distribution.md). Primary checkout is clean at the base SHA.

## 2026-10-08 — ORDER-001 independent final verification

- Independent review found no Order, acquisition reconciliation, migration, security, or navigation
  behavior defect. The full canonical `make feature-verify` passed on the reviewed tree: feature graph
  (93 valid), workflow guards, Ruff/Prettier/lint/strict typing, **787 backend unit tests** (90.01%
  coverage), **503 frontend tests**, generated API drift, **645 PostgreSQL integration tests**,
  production backend/frontend builds, migration cycle `0035 → 0036 → 0035 → 0036`, whitespace checks
  and a working-tree verification receipt.
- The first frontend run exposed an obsolete UX-001 test expectation for the navigation group formerly
  called “Reference.” Production navigation correctly uses the approved “Explore” and “Sourcing” groups;
  only the stale test assertion was updated. The full gate passed after that test-only correction.
- ORDER-001 is now `verified` after operator UAT and independent review. Changes remain unstaged and
  uncommitted; protected delivery and local finish are the next authorized steps.

## 2026-10-08 — ORDER-001 purchase-context UAT refinement

- Replaced isolated Order selection with one authoritative purchase-context preview/resolve service
  used by SeedLot → Order, Order → existing lot and Order → new lot. Selection is read-only;
  existing Apply atomically saves reviewed acquisition fields/link while preserving independent
  material fields and other form drafts. Both Order/SeedLot versions are checked under consistent
  locks; stale refusal applies nothing. Creation revalidates confirmed fields and Order version.
- Purchased kinds stay exact; Unknown proposes Purchased. Incompatible known sources require a valid
  explicit saved correction. Blank Supplier proposes fill; known mismatch requires confirmation,
  including conflicts hidden by an unsaved Supplier draft. Unknown Order Supplier preserves known
  lot Supplier. Order Supplier edit refuses linked-lot contradictions without automatic synchronization.
- Acquisition is vertical with exact read-only Order/transaction information and Supplier-aware bounded
  search plus explicit Show all. Origin stays separate; Order total is never a lot price. Optional
  Order-date copy is unchecked by default, preserves PartialDate precision and never overwrites a
  differing receipt date silently. Unlink retains confirmed Source/Supplier/date values.
- Final backend regressions: **52 passed**; whole Ruff/format and strict mypy (**292 files**) pass.
  Real disposable PostgreSQL: **645 passed**, including **27 new reconciliation tests**; its helper
  cleaned only its own resources. OpenAPI drift and both production runtime image builds pass.
  Frontend: **50 passed across 4 focused files**; whole ESLint, strict TypeScript, Prettier and
  generated API drift pass. Feature graph: **93 valid**; no additional migration.
- Guardedly resumed owned UAT without resetting data. Fixture v2's **34 baseline records** and operator
  edits remain intact; four labelled synthetic extra lots support blank/Unknown, matching Supplier,
  conflicting Supplier/differing year and confirmed month-only date-copy scenarios. Browser checks at
  **1440×844, 1024×844 and 390×844** verified proposals, Cancel/Escape, reverse Apply and refresh,
  transaction price distinction, new-lot precision, unlink retention and no horizontal overflow.
  No screenshots were taken and viewport was reset. Preview: **http://localhost:15174/#/orders**,
  credentials **preview / preview**; see [handoff](order-001-handoff.md) for exact examples/evidence.
- At this historical UAT handoff, ORDER-001 remained `implemented`; its independent review and
  canonical verification were still pending.

## 2026-10-08 — ORDER-001 implementation and visual handoff

- Implemented explicit purchase transactions with optional Supplier, precision-preserving Order
  date, normalized non-unique reference, exact non-negative decimal total/paired currency and notes.
  Purchased/purchased-fruit SeedLots may explicitly link/unlink/relink one Order; known Suppliers
  must agree on both edit paths. Order row locks serialize these checks. Referenced deletion is
  refused; no backfill, automatic lots, quantity/lifecycle/date/origin/Location or lineage effects.
- Added bounded authenticated REST/directory/detail and compact create/edit dialogs, authoritative
  counts, exact Supplier/SeedLot navigation and normal SeedLot creation with only purchase context
  prefilled. Orders Saved Views restore canonical filters at page one. Direct Order Global Search
  joins Suppliers under Sourcing without linked-botany matching or expanding History.
- Applied the approved IA: Collection includes Locations; Explore contains Botanical identities,
  Media, Geography and Collection origins; Sourcing contains Suppliers/Orders. Page eyebrows,
  keyboard disclosures, active-group expansion and mobile reachability follow that mapping.
  Collection origins retains `#/map` and internal `provenance_map`; its copy describes recorded
  collection material origins. EXPLORE-001 Species distribution and EXPLORE-002 Native ranges remain
  roadmap-only candidates; SCHEDULE-001 stays future Activity work and BOTANY-003 is unchanged.
- Migration `20261008_0036` adds Orders, restrictive nullable SeedLot links, money/date/source checks,
  justified indexes and the Saved View surface. It preserves old lots and refuses downgrade with
  Orders or Orders Saved Views. Real PostgreSQL: **618 passed**, including **21 Order integration
  tests**; standalone disposable migration cycle **0035 → 0036 → 0035 → 0036 passed**. Six old
  schema/head expectations were corrected after the initial integration run; the fresh full run passed.
- Focused backend regressions: **178 passed**. Whole backend Ruff/format and strict mypy (**288
  files**), generated OpenAPI/TypeScript drift, feature graph (**93 valid**) and production backend
  runtime build passed. Focused frontend regressions: **187 passed across 11 files** (182 in the ten
  unaffected final-run files, then all five in the corrected Supplier suite). Whole-frontend ESLint,
  strict TypeScript and Prettier plus targeted lint on final edits passed. SeedLot tests now preload
  their screen; Supplier photo actions await their own controls. Existing assertions/timeouts and
  dedicated lazy-loading tests remain intact. Frontend production build evidence is in the handoff.
  Changed UAT scripts pass canonical workflow Ruff/format and strict fixture mypy;
  `make test-uat-preview` and real read-only fixture/guard tests each passed **19 tests**. No policy or
  timeout was weakened.
- Guardedly retired the prior ed24-owned UAT through its supported remove command, then started,
  explicitly seeded twice and checked this worktree's UAT. Services are healthy at revision 0036;
  fixture v2 has **34 baseline synthetic records**, including two independent Basil packets in one
  EUR purchase and a month-only purchase with unknown Supplier/price. Operator edits and extras are
  retained on re-seed. DEV, Stable Preview, Feature Review and production were not operated.
- Browser interaction/DOM/layout checks at **1440×844, 1024×844 and 390×844** covered Orders, forms,
  exact money/date/unknown knowledge, long references, linked lots, Supplier/SeedLot context, Add seed
  lot prefill, Saved Views, Global Search, sidebar keyboard/active expansion, mobile More and Collection
  origins vocabulary. Inspected views had no horizontal overflow. A development reference-load
  interruption recovered through Retry. No screenshots were taken; temporary viewport was reset.
  UAT is ready at **http://localhost:15174/#/orders**, credentials **preview / preview**. Operator
  visual/product acceptance remains pending.
- ORDER-001 is `implemented`. All work remains unstaged/uncommitted; no canonical feature gate,
  push, delivery, merge or finish. Luna owns independent review, verification and reviewed commit
  after operator UAT. See [implementation handoff](order-001-handoff.md) and [Order contract](orders.md).

## 2026-10-08 — HISTORY-001 independently verified

- Operator UAT passed, including the accepted Activity/navigation refinement. The independent review
  found no product or workflow defect. It corrected three pre-existing SeedLot test selectors that
  became ambiguous with the new History destination, and updated two migration-test head assertions
  for revision `20261007_0035`; the affected focused suite and final complete suites passed.
- `make feature-verify` passed on this tree: feature graph (93 valid), workflow helper/static checks,
  formatting, lint and typing, backend tests (**749 passed**), frontend Vitest (**474 passed across
  48 files**), isolated PostgreSQL integration (**597 passed**), OpenAPI drift, production image
  builds, migration cycle through `20261007_0035`, whitespace, and a working-tree verification receipt.
- HISTORY-001 is now `verified` in `docs/features.json`. Collection productivity v2 is complete on
  protected delivery; Orders / Purchases follows. SCHEDULE-001 remains future work and BOTANY-003 is
  unchanged. Commit, delivery and finish remain the authorized next steps for this review.

## 2026-10-07 — HISTORY-001 operator-UAT Activity refinement

- Added accessible desktop disclosures for all six sidebar groups, expanded on first use, with
  browser-only collapsed-group persistence and active-route auto-expansion. Mobile retains its
  existing compact navigation/More pattern and every destination.
- Renamed the global Event destination/title and Saved View display label to **Journal**, retaining
  `#/events`, the `events` surface, Event model/API/kinds and all existing category membership.
  Permanent Journal/History purpose copy links the two roles; correction/history help stays secondary.
  Journal rows prioritize date, kind, Plant/Group target, bounded notes and secondary related links.
- Refined History into a compact chronological rail/list with explicit pressed **All activity** and
  multi-category chips, compact record/year controls and Clear year. PartialDate/Recorded labels,
  canonical URLs, page-one Saved Views, projection/dedup/date/query semantics and migration 0035
  remain unchanged. No scheduling or domain persistence is added; roadmap sequencing stays intact.
- Checks: **88 backend unit** tests and **123 isolated PostgreSQL** tests passed; **181 frontend**
  tests across 12 files passed (172 in ten files, final corrected two-file rerun: nine). Whole-frontend
  zero-warning ESLint, strict TypeScript and Prettier passed; final test edits also passed targeted
  lint/format and strict type checking. Both API drift checks, backend/frontend production image
  builds, feature graph (**93 valid**) and `git diff --check` passed. No policy or timeout was weakened.
- Browser: Journal/History reviewed at **1440×844 and 1024×844**; sidebar keyboard/focus,
  collapse/refresh persistence and active-group expansion, Saved Views and multi-category/year
  Apply/Clear URLs checked. At **390×844**, History orientation/filter wrapping, semantic states,
  timeline DOM and all More destinations had no horizontal overflow. Browser control then became
  unavailable (empty browser inventory); mobile Journal and scrolled timeline/long-label visual
  review remain operator items, and the temporary viewport could not be reset. See the handoff.
- Read-only UAT status confirms live ed24 source, healthy services, revision `20261007_0035`,
  fixture v1 / 31 baseline records and existing edits preserved. This pass did not reset/reseed UAT
  or mutate operator records. Everything remains unstaged/uncommitted; no push/delivery or canonical
  `make feature-verify`. Operator UAT has passed; HISTORY-001 remains `implemented` pending this
  independent canonical verification and delivery.

## 2026-10-07 — HISTORY-001 implementation and visual handoff

- Implemented the read-only Activity → History projection over existing Events, propagation receipts,
  germination observations, structured Harvests, material dispositions and seed conversions. Owned
  backing Events/receipts/dispositions collapse to one operation; corrections retain typed keys.
  PartialDate precision, explicit Recorded fallback, persisted reversal status/instants and current-state
  exclusions remain truthful. No History table, audit log, mutation or scheduling capability is added.
- Added globally ordered SQL pagination/filtered totals in one joined query, typed authoritative links,
  canonical URL filters and History Saved Views. Migration `20261007_0035` extends only the SavedView
  surface check and refuses downgrade while History views exist. History uses the established
  workspace/navigation vocabulary and exact retained inventory focus within Harvest detail.
- Focused backend unit regressions: **230 passed**; real PostgreSQL regressions: **123 passed**,
  including source/dedup/date/query bounds and downgrade/re-upgrade safety. Frontend regressions:
  **161 passed across 9 files** (160 in the main run plus the separate transition test), including
  complete App navigation. Ruff formatting/lint, strict mypy (**281 files**), whole-frontend
  zero-warning ESLint, strict TypeScript, Prettier, generated API drift, feature graph (**93 valid**),
  production backend/frontend image builds and whitespace passed.
- Browser review covers **1440×844, 1024×844 and 390×844**, keyboard filters, canonical URL,
  browser Back restoration, separate mobile Events/History navigation and Harvest deep links without
  horizontal overflow. Supported guarded UAT replacement, startup and fixture-v1 seed succeeded from
  ed24; DEV, Stable Preview, Feature Review, production and primary checkout were not modified.
- HISTORY-001 is `implemented`; operator visual UAT has passed and independent review/canonical gate
  remain for this delivery phase. Collection productivity v2 remains open; Orders/Purchases follows verified delivery.
  SCHEDULE-001 remains future work and BOTANY-003 is unchanged. No canonical gate, staging, commit,
  push, delivery, merge or finish was run. See [HISTORY-001 handoff](history-001-handoff.md).

## 2026-10-07 — BULK-001 independent final verification

- Operator UAT passed for the scoped multi-select and atomic Location moves. The reviewed scope
  includes five typed active collection kinds, transient selection, authoritative per-kind domain
  effects, current server preview, stale-state refusal, keyboard-accessible controls, responsive
  navigation and truthful directory counts. No schema migration is part of the increment.
- Independent review found no production or workflow defect across the full diff, domain effects,
  selection/Saved Views boundaries, API/auth/CSRF, concurrency and atomicity, query bounds,
  accessibility, navigation, result counts, generated contracts and documentation.
- `make feature-verify` passed: backend **735 passed** at **90.54%** coverage; frontend **462 passed
  across 46 files**; PostgreSQL integration **582 passed**; strict mypy (**274 files**), strict
  TypeScript, Ruff, Prettier, zero-warning ESLint, generated API drift, production builds, no-migration
  cycle, whitespace and working-tree receipt all passed. The feature graph validates **92 features**.
- The gate's initial run found a stale Sowing test stub returning `None` after the reference helper
  gained a tuple return for Location assignment. Only that test double was corrected; the focused
  lineage suite passed (**4 tests**) and the full gate then passed. BULK-001 is now `verified` in the
  graph. Documentation changes require a final receipt refresh before commit.

## 2026-10-07 — BULK-001 operator UAT refinements

- Moved Select into the Saved Views utility row and made active selection compact, with one primary
  Move action and lightweight Select visible / Clear selection / Done controls. Enlarged the typed
  Location chooser/dialog; safe opt-in backdrop/Escape dismissal restores Move focus, while pending
  Apply remains guarded. Target changes still invalidate preview and disable Apply.
- Added Botanical Identity Add plant shortcuts in Quick Preview and detail, reusing normal identity-
  prefilled Plant creation. Added shared quiet result metadata across Collection, Places and Reference
  lists using existing filtered responses and authoritative Media totals; no count queries/domain
  changes/migration. Existing map companion lists count matching sites; bare maps/details/forms do not.
- Focused frontend checks: **266 tests in 17 files passed**. Whole-frontend Prettier, zero-warning
  ESLint, strict TypeScript and production Vite build passed; `git diff --check` clean. Backend
  semantics are unchanged from the implementation evidence; no canonical gate was run.
- Browser review covered **1440×844, 1024×844 and 390×844**: utility/selection controls, searchable
  chooser, preview invalidation, backdrop/inside clicks, keyboard focus/trap/return, truthful list
  counts and Identity action/navigation/prefill. No horizontal overflow or new persistent UAT record
  edits. Supported UAT restart preserved fixture v1, 31 baseline records and prior operator edits.
- Operator visual acceptance passed; Luna is now performing independent final review and canonical
  verification. Everything remains unstaged and uncommitted until the verified-tree delivery phase.
  Details and count-source audit: [BULK-001 handoff](bulk-001-handoff.md).

## 2026-10-06 — BULK-001 implementation and UAT handoff

- Added bounded explicit typed selection and server Preview → Apply Location moves for active
  SeedLots, Sowings, Plants, PlantGroups and managed Stored material. Reuses owning assignment
  primitives and per-record Movement Events; revalidates all record/target versions under locks,
  including no-ops, and rolls back the entire batch on conflict. No migration, selection persistence,
  query expansion, generic bulk framework or additional bulk action.
- Selection clears on filter/search, directory/task navigation and identical Saved View reopening.
  Accessible toolbar/dialog supports keyboard focus, no-op/conflict feedback, directory refresh and
  filter retention. Historical Harvest remains excluded. Approved macroareas and page eyebrows
  preserve routes, titles, descriptions and mobile destination access.
- Focused checks: **172 backend unit/domain tests**, **195 real PostgreSQL integration tests**,
  **242 frontend tests in 10 files**. Ruff, strict mypy (**274 files**), Prettier, zero-warning ESLint,
  strict TypeScript, both generated API drift checks, frontend/backend production builds and the
  **92-feature graph** and `git diff --check` passed. PostgreSQL tests cover atomic rollback, stale record/target changes,
  all five kinds and 100-row query bounds. No verification threshold was weakened.
- UAT Preview ownership moved from c5e8 through the supported guarded retirement and b647 startup,
  seed/status workflow. Fixture v1/code and 31 baseline records are preserved. Normal synthetic UAT
  exercises added moves, one explicitly unknown-quantity tracked inventory and a filtered Saved View;
  DEV/Stable Preview/Feature Review/production are untouched. Services are healthy at
  `http://localhost:15174` with `preview / preview`.
- Browser review covered **1440×844, 1024×844 and 390×844**, supported selection/preview surfaces,
  keyboard focus/trap/Escape, no-op handling, wrapping/bounds, Saved View reset and Movement history.
  Two-tab stale testing encountered a CSRF refusal before mutation; domain stale/atomic safety is
  proven in PostgreSQL, while that browser scenario remains for operator review. Automatic approval
  review rejected an extra direct fixture mutation; it was not executed or bypassed.
- At the time of this implementation handoff, BULK-001 remained `implemented` pending operator UAT
  and independent review/canonical gate.
  Unified operational history remains next, Orders/Purchases later, BOTANY-003 unchanged and blocked;
  SCHEDULE-001 is only a later candidate. Source is unstaged/uncommitted; no `feature-verify`, delivery,
  merge, finish or DEV upgrade. See [the handoff](bulk-001-handoff.md).

## 2026-10-06 — VIEW-001 independent review and final verification

- Independent review covered owner isolation, typed/canonical state contracts, stale references and
  future-version management, Origin/CSRF/session boundaries, single-query bounded listings, migration
  safety, all thirteen frontend adapters, ordinary URL/history behavior and accessible directory chrome.
  No production behavior defect was found. Operator UAT had passed at 1440×844, 1024×844 and
  390×844, including keyboard order, visible focus, named controls/groups and overflow checks.
- The first canonical run exposed 89.88% backend coverage versus the existing 90% policy. Added
  focused Saved View service/API unit tests; the complete backend unit suite then passed **690 tests at
  90.36%**. Its PostgreSQL run passed **562 tests** and exposed one stale pre-VIEW-001 schema inventory
  assertion; updated that table inventory to include the new `saved_views` migration table.
- Complete frontend Vitest passed **436 tests in 43 files**; Prettier, zero-warning ESLint, strict
  TypeScript, Ruff and strict mypy passed. The final canonical gate is rerunning the corrected frozen
  tree, including full isolated PostgreSQL integration/migration, API drift and production builds.
- VIEW-001 is marked **verified** on the basis of accepted operator scenarios and independent review;
  the final tree-specific canonical receipt is produced by the in-progress gate. No implementation
  semantics or verification thresholds were weakened.

## 2026-10-06 — VIEW-001 final operator UAT directory chrome polish

- Visually hid redundant peer directory headings, search captions and operational lifecycle captions
  with the existing `sr-only` convention. Explicit search labels, named directory regions and native
  fieldset legends remain accessible. Meaningful section/filter headings and detail/form hierarchy
  are preserved; DirectorySearch opt-in leaves picker/linker/contextual searches unchanged.
- Kept heading/subtitle → Saved Views → search → filters → results. Plants' desktop lifecycle
  buttons align with Record type without stretching. This follow-up changes no routes, search/filter
  behavior, Saved View state, API or domain semantics.
- Fresh review covered twelve supported directories plus the Provenance sites variant at
  **1440×844, 1024×844 and 390×844**: **78 collapsed/expanded bounds checks** found no horizontal
  overflow; **39 keyboard checks** retained named search/first-filter order and visible focus.
  Search-to-Active and Save dialog focus/trap/Escape passed at each size; mobile management-dialog
  cancellation returned focus to each exact trigger. Accessibility snapshots preserve label/group names.
- Focused frontend regressions: **225 passed in 13 files** after an **11-test baseline**. Final
  whole-frontend Prettier, zero-warning ESLint, strict TypeScript and production Vite build passed.
  Evidence and retained headings are recorded in [the updated handoff](view-001-handoff.md).
- UAT services remain healthy with existing operator data preserved. The source is unstaged and
  uncommitted; VIEW-001 remains **implemented**, awaiting visual review and Luna's canonical gate.

## 2026-10-06 — VIEW-001 operator UAT placement correction

- Moved Saved Views out of the Plants search/filter grid into its own row below the directory
  heading and above search. Applied the same placement to SeedLots and Sowings; Stored material
  now places the row below its explanatory subtitle. Other supported directories already use this
  arrangement. Saved Views does not shrink as a child of bounded directory flex layouts.
- Cross-surface review also caught the Saved Stored material route using an incorrect tab value.
  Its adapter and history guard now use the existing `tab=stored-material`; normal UI Save/Open and
  refresh retained the exact query/state. Added an App-level regression against the actual peer view.
- Browser review covered all 13 supported surfaces at **1440×844, 1024×844 and 390×844**:
  39 document/panel bounds checks found no horizontal overflow, with directory controls separated
  from ordinary filters. Checked empty lists, expanded long names, wrapped actions, keyboard
  Save/Saved views/search order, modal focus trap, Escape return, and Rename/Update/Delete cancellation.
  Screenshots and measurements stay outside Git in `/tmp/florabase-view001-layout-review`.
- Focused post-layout directory/UI tests: **90 passed**. Saved View adapter/UI and Stored material
  tests after the route correction: **67 passed**. Targeted App open/refresh and keyboard peer-view
  checks: **3 passed** (the Saved Views UI cases overlap between focused runs).
- Final affected-file Prettier and zero-warning ESLint, strict TypeScript and production Vite build
  passed. UAT status reports this worktree, healthy frontend/backend/DB, revision 0034 and fixture v1
  with existing edits preserved. `git diff --check` passed; the index remains empty and primary clean.
- VIEW-001 remains **implemented**, with no staging, commit, canonical gate or delivery in this phase.

## 2026-10-06 — VIEW-001 Saved operator views implementation

- Implemented owner-private PostgreSQL SavedView persistence, revision `20261006_0034`, typed v1
  state for all thirteen audited existing search/directory surfaces, canonical ordinary URLs and
  compact Save/Open/Rename/Update-current/Delete controls with Dashboard access.
- State excludes pagination and transient interaction state. Exact stale UUIDs remain filters;
  incompatible stored versions remain manageable without silent interpretation. Existing search
  matching and default directory predicates are preserved. Lists use one bounded owner-scoped
  query per page, without executing views or materializing results.
- Focused backend/state/search checks: **84 passed**. Real isolated PostgreSQL checks: **61 passed**,
  covering JSONB/UUIDv7/UTC, naming, second-user isolation, mutation protections, bounded listing,
  stale/future state, populated downgrade refusal and empty downgrade/re-upgrade, plus SEARCH-002
  and current-head migration regressions. Ruff format/lint and strict mypy passed; production
  backend runtime build passed. Final frozen frontend suite: **435 passed in 43 files**;
  zero-warning ESLint, strict TypeScript, production frontend build and Prettier passed.
  Generated API drift, feature graph (91 features) and `git diff --check` passed. Complete browser evidence is in
  [the implementation handoff](view-001-handoff.md).
- Supported guarded retirement proved prior UAT owner `9f48` before retiring only its resources;
  this branch prepares fresh synthetic UAT through normal up/seed/status. Fixture v1 is unchanged.
- Initial browser flows passed at 1440×844 before the browser connection disappeared. The operator
  UAT correction above completes the reference and responsive visual/overflow review; UAT remains healthy.
- VIEW-001 is **implemented**, awaiting operator visual/product UAT and independent architecture/QA
  and canonical verification. No feature-verify, staging, commit or delivery in this phase.
  Collection productivity v2 remains open: bulk operations next, then justified unified history,
  then Orders/Purchases. BOTANY-003's existing blocker is unchanged.

## 2026-10-06 — PREVIEW-001 ownership retirement regression required by SEARCH-002 UAT

- Delivered UAT lacked retirement: stop kept ownership and reset recreated it under the old owner.
  Added guarded `make uat-preview-remove CONFIRM_REMOVE_UAT_PREVIEW=florabase-uat-preview`, isolated
  from SEARCH-002 application code. It requires the owning linked source, including a delivered
  detached owner, and performs only read-only Git validation. Missing/wrong token, non-owner,
  ambiguous container/volume/network identity and foreign volume writers/network endpoints refuse.
- Removal proves exact resource/source identity, stops UAT writers, rechecks identities, then removes
  only scoped UAT containers/internal network and the individually named postgres/media/dependency
  volumes. No generic `down -v`, rebuild, reseed, Git/source edit or other environment operation.
  Stop/reset semantics remain distinct; workflow and PREVIEW-001 handoff now document old-owner
  removal followed by next-feature up/seed/status, including invocation from a pre-command owner.
- Regression checks: **19 UAT helper tests**, **29 environment helper tests**, workflow Ruff
  format/lint and strict mypy passed. Real disposable Compose smoke
  `florabase-uat-preview-smoke-2e4782f118e6` passed **18 PostgreSQL fixture tests**, its established
  seed/auth/persistence/reset/ahead-refusal checks and old-owner remove → new linked fixture source
  up → empty auth → fresh seed/IDs/media/ownership → real login. Supported removal cleaned fixture
  resources; operator environment/data and primary snapshots remained unchanged.
- With explicit operator authorization, ran the corrected Makefile's removal target from owning
  `80b3`: four containers, one network and exactly the three allowed volumes were proved and retired.
  No manual Docker deletion or relabeling. Live missing-confirmation/non-owner checks refused.
  Standard `9f48` up, seed and status then passed. DEV/Stable Preview/Feature Review/production
  resource/data digests and old/primary Git identities matched before/after. Operator acceptance has
  passed; independent QA and the canonical gate are underway.

## 2026-10-06 — SEARCH-002 global Harvest and Media coverage

- Implemented only in attached `9f48` worktree on `feat/search-002-global-coverage`, PREVIEW-001
  base/unchanged HEAD `0c36a404eedb89531447581d3769867e44d35490`. Added typed Harvest/Media kinds,
  exact authenticated routes, generated contracts, Collection → Media → Botany → Reference groups,
  existing kind controls and Harvest occurrence-year filtering.
- Harvest uses its current authoritative title/source/identity, notes and material text; only exact
  source identity and true occurrence year apply. No Location/Supplier/provenance/lifecycle/Event-kind
  inference. Media shares Library title/original-filename/attribution matching and title fallback,
  with safe context and UUID/missing-target handling on the existing exact detail route. Search
  loads no images and contacts no external host. EXISTS/grouped materials and unique Attachment
  joins preserve one result per record and fixed query bounds: six SELECTs for mixed new-kind text
  search at three or 51 matches; 28 for all 13 kinds. Independent final review added saved external-
  copy filename coverage; the full supported integration wrapper then passed **550 tests**, including
  40 SEARCH-002 cases.
- Focused backend **100 passed**; the earlier focused disposable PostgreSQL matrix **69 passed**, including all
  eleven old kinds, partial dates, forbidden filters, deduplication, auth, paging and query bounds;
  frontend DashboardSearch/MediaScreen/HarvestScreen/lazy routing **36 passed**. Ruff/mypy (257 files),
  generated API preparation, zero-warning ESLint, strict TypeScript, 90-feature graph, production
  frontend Vite/backend runtime builds, changed-file Prettier checks and `make api-check` passed.
  Ordinary test fixtures/readiness/lint issues were corrected without weakening tests, rules or
  thresholds. Disposable integration resources were cleaned without operator deletion.
- SEARCH-002 operator acceptance and independent verification have passed. Canonical `make feature-verify`
  passed on this tree: graph (90 valid), UAT/environment/workflow helpers (19/29/37 passed), Ruff,
  Prettier, strict mypy (257 files), strict TypeScript and ESLint, backend unit tests (613 passed,
  90.13% coverage), frontend tests (382 passed across 41 files), API drift, PostgreSQL integration
  (550 passed, 160 warnings), production images, migration-cycle check (no new revisions), whitespace
  and tree receipt. The cold lazy Botanical Identity route test now waits 3 seconds for its unchanged
  result assertion; an isolated diagnostic showed the cold Vite import resolves in about 2 seconds,
  while all 11 UX-004 tests pass in the full suite. No UX-004 production behavior changed.
  SEARCH-002 is **verified**. Saved filters/views
  are next; bulk operations and justified history remain deferred. Orders and the BOTANY-003 WFO TLS
  blocker are unchanged. No migration/index/search infrastructure or later productivity work added.
- The PREVIEW-001 retirement correction above enabled supported `80b3` → `9f48` UAT. Up/seed/status
  passed; DB/backend/frontend are healthy at `localhost:15174`, code/DB head `20261005_0033`, fixture
  v1 initialized (31 baseline records), and real `preview / preview` browser login succeeded.
- Independent `make smoke-uat-preview` passed on unique disposable project
  `florabase-uat-preview-smoke-e92b8aceebfa`, including 18 fixture tests and old-owner retirement →
  new linked source up → fresh seed/login → guarded cleanup. The operator UAT remains healthy.
- Actual browser review at 1440×844, 1024×844 and 390×844 passed result/filter fit with no horizontal
  overflow, exact Harvest/Media navigation, Media refresh/back/forward/missing-target state, external
  opt-in remaining unloaded, source/filename/year searches, empty/clear and Escape focus restoration.
  Final diff review reproduced an uppercase UUID Media link stuck in Loading; case normalization,
  a dedicated regression and repeated real UAT/frontend checks resolved it. Search results contain
  no images. Review artifacts are outside Git. Implementation is
  operator acceptance passed; independent final review and canonical verification passed. See
  [handoff](search-002-handoff.md) for exact semantics, checks, regression isolation and searches.
  At independent-review handoff, primary was clean on `main` and the index was empty; the reviewed
  branch then proceeds through the repository's single-commit protected delivery and conservative
  finish workflow.

## 2026-10-05 — PREVIEW-001 persistent dirty-feature operator UAT

- Implemented only in the attached 80b3 Codex worktree, `feat/preview-001-uat`, at SUPPLIER-003
  base/HEAD `bd7904316445f41570aadb827d680c24ba082900` (#70). UAT reuses Feature Review's source,
  build, non-root initializer, migration and persistence helpers with independent `florabase-uat-preview`
  DB/media/dependency volumes and network. It uses current tracked/untracked dirty source at loopback
  15174; Stable Preview's ref/worktree commands, DEV/primary source and production remain distinct.
- Added five `uat-preview-*` operator commands. Up never seeds; explicit guarded seed creates the
  UAT-only public `preview / preview` owner through normal owner/Argon2 machinery and a bounded
  version-1 basil/lavender/aloe collection. Normal password validation, login, sessions, Origin and
  CSRF remain unchanged. The fixture CLI is mounted explicitly, absent from production images.
  Host project/source/network/actual mount/volume/container checks and runtime origin/cookie/resource
  marker/current-database/user checks fail closed before seed/reset can target another environment.
- A media-volume manifest records 31 service-created UUIDv7 identities without production domain
  fields. Repeated seed preserves ordinary operator edits and adds no duplicate owner/media/link.
  Interrupted, missing or incompatible baselines require guarded reset rather than guessed repair.
  The synthetic collection covers Supplier media/absence, Location hierarchy, geography/provenance,
  varied SeedLots, active/historical Sowings, direct/derived Plants/group, explicit lineage,
  observations, Harvest, generated local PNG and offline external metadata. Reset requires
  `CONFIRM_RESET_UAT_PREVIEW=florabase-uat-preview`, validates exact resources, deletes DB/media/
  dependencies individually (never `down -v`), then rebuilds health and explicitly seeds.
- Focused checks: Stable Preview **19**, environment **29**, feature workflow **37**, UAT helper **9**
  tests passed. Real disposable UAT pytest **18 passed** covers runtime/DB/environment guard refusal,
  unchanged normal bootstrap password validation, interrupted/version/missing records and media.
  `make workflow-check` passed Ruff, formatting and strict helper/fixture mypy; final harness/test
  formatting/lint and strict three-module harness typing passed after the diagnostic/CI portability
  corrections. `bash -n` for the changed
  verification script, feature graph (**89 valid**), Make help and `git diff --check` passed.
- Full real Compose smoke passed on UUID-scoped `florabase-uat-preview-smoke-d84c2ca17471`: empty
  startup/auth; untracked current-source migration; real Argon2/session login/private collection;
  fixture lineage/Harvest/shared-media/primary relationships; triple seed preserving operator text
  and an operator-only record; DB/owner/media/dependency stop/start persistence; DB-ahead refusal
  without downgrade; rejected reset confirmations; complete reset/removal of operator data and
  recreated owner/media; repeat seed after reset. Before/after primary Git, operator container/volume
  metadata and running DB data checksums matched for DEV, Feature Review, Stable Preview, production
  and operator UAT. Only proven disposable resources were cleaned. DEV has no `preview` account.
  One fresh attempt failed frontend startup health with host load 25.98 and full swap; the final
  serial rerun passed unchanged health deadlines. No tests or timeouts were weakened.
- PREVIEW-001 remains **implemented** pending its canonical verification receipt;
  next product milestone remains **Collection productivity v2**. BOTANY-003's blocker and historical
  RELEASE-001 planning remain unchanged. No schema/domain/API or graphical shell change was made.
  Primary is clean on main; this feature stays unstaged/uncommitted. `make feature-verify`, staging,
  commit, push, delivery, merge and finish were not run. See [handoff](preview-001-handoff.md).
- Operator UAT passed; the healthy environment remains running at `http://localhost:15174`, seeded explicitly with
  `preview / preview`; DB current/code head are `20261005_0033`. Browser login and seeded Seeds,
  Suppliers, Sowings and Plants were inspected at 1440×844, 1024×844 and 390×844 without horizontal
  overflow. Mobile Dashboard, Supplier Photos and keyboard activation of Supplier detail also passed
  spot checks. To free the existing Review port,
  Feature Review was stopped from its owning 73d8 source after the isolated smoke; all three Review
  volumes were retained. DEV, Stable Preview, production and primary remain unchanged.

## 2026-10-05 — PREVIEW-001 independent review

- Operator reported product UAT passed. Independently reviewed the complete tracked and untracked
  PREVIEW-001 diff, host/runtime guards, normal authentication boundaries, fixture service invariants,
  persistence/reset scope, migration refusal, CI wiring, feature graph and operator documentation.
  No production/workflow defect or out-of-scope domain change was found; no tests were added because
  the existing independent runtime tests and real disposable smoke cover the reviewed contracts.
- Independently reran `make smoke-uat-preview` on fresh disposable project
  `florabase-uat-preview-smoke-901ac5363b53`. Eighteen PostgreSQL fixture/guard tests passed; the
  smoke confirmed dirty/untracked source, normal Argon2/session login, runtime refusals, triple seed,
  edit preservation, stop/start DB/media/dependency persistence, ahead-of-code refusal, guarded reset
  and recreation, and unchanged DEV/Feature Review/Stable Preview/production/operator UAT snapshots.
  Exact disposable resources were cleaned; operator UAT remains running. `git diff --check`, feature
  graph (89 valid), and `make help` passed. Canonical verification is the next step.

## 2026-10-05 — SUPPLIER-003 shared Supplier imagery and Reference completion

- Implemented only in the current 73d8 Codex worktree, attached through `make feature-init` as
  `feat/supplier-003-media` at merged HARVEST-003 base `4dbf6cf` (#69). Supplier is an ordinary
  typed shared-media target with multiple reusable local/external assets and one optional explicit
  primary. Concrete restrictive FKs, exact-target/duplicate/primary constraints and the existing
  immutable-link guard protect membership. Revision `20261005_0033` follows `20261004_0032`,
  has no backfill or binary mutation, cycles empty state and refuses populated downgrade before DDL.
- Supplier directory, Quick Preview and detail reuse protected thumbnails/neutral placeholders;
  the new Photos tab reuses shared upload/reference/link/caption/order/primary/unlink controls.
  Fixed direct-detail editing to use its loaded Supplier. Media Library Target now offers All,
  Collection media, Suppliers and every existing collection target. EXISTS filtering composes with
  search/kind/association and deterministic pagination, returns unique assets and uses two SELECTs.
  Collection media is exactly an explicit SeedLot/Sowing/Plant/PlantGroup/Event/Harvest link;
  Supplier-only assets are excluded and Supplier + Plant assets appear in both. Supplier choices
  use two SELECTs; mixed directory primary summaries use at most four, exercised with 30 Suppliers.
- Shared assets and each exact primary remain independent. Unlink clears the exact primary and
  retains assets/other links/covers; zero record links plus zero identity covers still gates deletion.
  Acquisition/lineage never inherits imagery. External disclosure/copy safety and protected reads,
  owner mutations, CSRF and exact Origin remain shared. No logo role/category, second media system,
  Orders, global Search v2 or botanical work was added.
- QUALITY focused backend Supplier/media/primary/copy pytest `--no-cov`: **59 passed**. The final
  disposable tmpfs PostgreSQL matrix passed **42 tests** across Supplier media/migration, shared
  media/races/primary races, Supplier API, external copies and shared-media migration preservation.
  Eighteen existing Alembic path_separator deprecation warnings remain. Cleaned only task-owned
  project `florabase-supplier003-20261005` without volume deletion; retained Feature Review.
- Focused SupplierScreen/MediaScreen/PhotosSection Vitest: **27 passed across 3 files**; existing App
  Supplier/UX-005 regressions passed **8 tests** (59 unrelated cases skipped) after actual lazy-render readiness and
  representative-image accessible-name selector corrections. Ruff format,
  Ruff check, strict mypy (**256 files**), zero-warning ESLint, strict TypeScript, generated contracts
  from `make api-generate`, `make api-check`, **89-feature** graph and both production image builds
  passed. Final diff audit and `git diff --check` passed. The independent canonical gate is pending.
- Corrected ordinary new-test selectors/types/lint. Existing full-row migration preservation now
  includes the new null Supplier column; retention assertions use the truthful Record links wording.
  An initial frontend command accidentally launched the full suite, exhausted host RAM/swap and was
  interrupted by stopping only its own test container. It is not passing evidence. Focused reruns
  used direct Vitest path selection; no validation, thresholds, timeouts or assertions were weakened.
- With explicit operator authorization, removed the prior fbb6-owned Review only through its supported
  helper and created current Review. `make feature-review-up` and `make feature-review-status` show
  healthy isolated services, 73d8 live source binds and code/database revision 0033 at localhost:15174.
  Synthetic A–G Supplier/media examples and screenshots stay outside repository source. Actual browser
  checks cover Supplier directory/Quick Preview/Photos and primary replacement at 1440×844, detail at
  1024×844, and directory/detail/external dialog focus/escape at 390×844 with no horizontal overflow.
  Reference-only external primary stays unloaded. The browser later disconnected and reported no
  available browser despite healthy Review; this agent did not complete the full Media Library matrix
  or a successful external fetch from example.test.
- The operator subsequently reported manual product UAT passed on 2026-10-05. Independent review
  found no production defect; focused tests above independently cover the acceptance criteria.
  SUPPLIER-003 is P1 **verified**. The canonical frozen-tree gate supplies its final delivery receipt.
  The new operator-approved next step is **PREVIEW-001**, added as planned P1 infrastructure;
  Collection productivity v2 follows it. BOTANY-003's approved WFO TLS blocker and historical
  RELEASE-001 planning remain unchanged. See [full handoff](supplier-003-handoff.md) for the
  contract and evidence. Primary checkout is untouched.

## 2026-10-04 — HARVEST-003 explicit SeedLot conversion and guarded reversal

- Continued only in the existing fbb6 Codex worktree, attached through `make feature-init` as
  `feat/harvest-003-seedlot-conversion` at merged HARVEST-002 base `c351971` (#67). The original
  product gate was resolved by the operator's approved B guarded-reversal contract. Added narrow
  typed conversion persistence, explicit active tracked seed-only creation, atomic stock/disposition/
  SeedLot accounting, canonical exact producer lineage and on-demand cross-links. Source identity
  defaults independently correctable target identity; PartialDate occurrence and explicit target
  Location preserve known facts without acquisition/provenance/Event/media/Sowing inference.
- Undo retains the original immutable disposition, conversion and resulting SeedLot as `reversed`,
  restoring typed source before quantity/state only under captured after-state/correction-version
  compatibility and resolved dependency rules. Converted producer/source and Harvest source are
  protected; later standalone dispositions still have no generic reversal. Reversed lots remain in
  history/totals/Location evidence and cannot reactivate or supply new Sowings. Safe descriptive,
  identity and Location corrections remain possible. Revision `20261004_0032` installs restrictive
  FKs, unique result/disposition links, typed quantity/coherence/origin guards and guarded downgrade.
- Added HARVEST-003 and promoted it to `verified` after accepted UAT and independent review, without
  changing other feature contracts/statuses.
  Reconciled the roadmap's current direction and actual landed graph statuses, retaining historical
  0.1.0/RELEASE-001 planning. Recorded the approved forward sequence through 1.0.0 and BOTANY-003's
  parallel approved-WFO incomplete-TLS-chain blocker without workaround or reselection. See
  [contract](harvest-seed-conversion.md) and [full Sol handoff](harvest-003-handoff.md).
- Focused QUALITY backend pytest `--no-cov`: **129 passed** across Harvest, inventory, conversion,
  SeedLot model/schema, lineage and import/export service files; SeedLot service/API **6 passed**;
  ordinary Sowing service **4 passed**. Focused Vitest Conversion/SeedLotScreen/SowingScreen:
  **48 passed**; the added identity/target-Location choice brought Conversion to **8 passed**,
  and final eligibility-request failure coverage brought it to **9 passed**, for **50 unique focused
  cases**. Final audit fixed an eligibility error appearing behind Undo: the dialog now shows the
  failure and keeps confirmation disabled. Final focused Conversion rerun: **9 passed**.
- Task-owned disposable PostgreSQL tmpfs project `florabase-harvest003-20261004` ran the current
  backend through `compose.integration.yaml` plus an untracked `/tmp` source override. Fresh focused
  matrix: **160 passed** across CSV API, conversion/migration, inventory/migration, SeedLot API,
  lineage API/integrity and propagation reversal. Final conversion/migration rerun after boundary/
  correction tests and SQL readability cleanup: **42 passed**. Twelve deterministic transaction/
  observed-lock-wait race cases cover overuse, duplicate use-all, source correction/Harvest/real
  lineage mutation and Undo vs disposition/conversion/use/duplicate Undo/correction, without sleeps.
  Migration cycles preserve a pre-existing ordinary lot/inventory without conversion backfill and
  reject populated downgrade. Existing Alembic path_separator deprecation warnings remain unchanged.
- An early reused test DB retained pre-cleanup race reference fixtures and caused four existing
  empty-DB CSV assertions to fail. Added complete fixture-reference cleanup and reran on fresh tmpfs:
  all passed. New-test enum fixture/selector/type/lint failures were fixed without weakening existing
  assertions, validation, configuration or timeouts.
- Ruff, Python format check, strict mypy (**254 source files**), Prettier, zero-warning ESLint,
  strict TypeScript, `make api-check`, the **87-feature** graph, production backend/frontend image
  builds and `git diff --check` passed. Generated contracts came from `make api-generate`.
  After resumption, final production builds, mypy over **132 application source files**, Python
  formatting (**289 files**) and Prettier passed again on the current tree.
  The final modal error-state fix passed strict TypeScript, zero-warning ESLint, Prettier and
  both production image builds on October 5.
- Feature Review was initially blocked by 8dfa ownership. With explicit operator approval, removed
  only that prior Review through its owning `feature-review-remove`; current `feature-review-up`
  and `feature-review-status` report fbb6 live binds, isolated DB/media/dependencies, healthy services
  and revision 0032 at localhost:15174. Actual browser smoke completed exact Plant partial transfer,
  changed target Location, dates, cross-links and lineage at **1440×844**, then a second exact use-all
  packet, depleted source and retained two conversions at **1024×844**. Browser reconnection resolved
  the interrupted mobile smoke: **390×844** blocked older Undo with useful reasons and disabled
  confirmation, restored focus on Cancel, then safely reversed the newest packet and restored exactly
  20 items. The reversed lot retained Harvest links and Plant lineage with no Start sowing action.
  PlantGroup approximate stock produced an exact 35 g packet with explicitly confirmed approximate
  65 g remainder; unknown group stock produced a measured 20 g packet while remainder stayed unknown.
  Non-seed/depleted rows had no conversion action. Mobile dialogs had no horizontal overflow and
  native quantity controls passed keyboard selection. All representative A–L cases are covered
  across the three requested sizes. Operator acceptance is accepted. Review synthetic data,
  credentials and screenshots are outside the diff; viewport override reset; DEV was unused.
  On October 5 the retained Review frontend/backend were found stopped; `make feature-review-up`
  restarted the isolated services without state removal and confirmed all healthy at revision 0032.
  - All changes remain unstaged/uncommitted. No extra worktree, primary checkout source change,
    commit, push, PR, delivery, merge or feature-finish. Operator UAT/visual acceptance and Luna's
    independent review/matrix are complete. The first canonical attempt stopped after 588 passing unit
    tests because coverage was 88.78% against the unchanged 90% threshold. Added independent unit
    coverage for creation, exact use-all conflict and kg guard, reversal eligibility/restoration,
    conversion history projection and API paths. Final canonical `make feature-verify` passed on
    October 5: backend 595 passed at 90.00%, frontend 368 passed across 40 files, PostgreSQL
    integration 500 passed, API drift and workflow checks passed, and production images built. The
    disposable migration cycle passed from 20261003_0031 through 20261004_0032, back and forward again.
    The gate exposed a migration-cycle helper that missed normal unannotated Alembic assignments; it
    now supports both forms and all 37 workflow-helper tests pass. The per-worktree verified receipt
    matches this tree. The reviewed local commit remains pending.

## 2026-10-04 — HARVEST-002 independent QA and canonical verification

- Independently reviewed the complete feature diff, including migration/model constraints, service
  locking and inventory transitions, Harvest/Location retention integration, APIs, tests, generated
  OpenAPI/TypeScript declarations and documentation. No material contract gap, production defect or
  unresolved product decision was found. Inventory remains independent of collected quantity and
  biological lifecycle; immutable disposition history and tracked source context remain protected.
- Verified Sol's PlantScreen/App edits synchronize against the real lazy workspace import using
  `vi.dynamicImportSettled()` inside React `act`. Existing detail/form assertions and API fixtures are
  preserved, with no mocks, sleeps, retries or timeout increases. The original Plant and PlantGroup
  deep links, Events preservation, hash switching, Back/Forward and return to the directory passed;
  PlantGroup also passed alone as a cold first import. The two full affected suites passed **107 tests**.
- First canonical gate passed: feature graph, workflow checks, Ruff, mypy across **247** backend source
  files, strict TypeScript, zero-warning ESLint, Prettier, API drift, **578** backend unit tests at
  **90.14%** coverage, **359** frontend tests across **39** files, **458** PostgreSQL integration tests,
  production builds and migration upgrade/downgrade/re-upgrade cycle. Final gate is being repeated on
  this documentation-complete tree so its receipt matches the committed source digest.
- Browser smoke remained unavailable because the Review frontend/backend were stopped; no browser
  result is claimed. No production correction was needed.

## 2026-10-04 — Plant route test synchronization

- Investigated Luna's preserved Plant/PlantGroup deep-link blocker before changing any implementation.
  Reproduced `#/plants/01900000-0000-7000-8000-000000000701` and
  `#/plant-groups/01900000-0000-7000-8000-000000000702`. Temporary tracing showed correct route parsing
  (`plants`, requested record ID, `plant`/`group`) and correct PlantScreen props. The real cold lazy
  PlantScreen import resolved after **1,147 ms**, just after the original **1,000 ms** detail-query
  deadline; the requested detail and Print label link then appeared and the workspace placeholder
  disappeared. The next warm case passed. This clarifies the earlier blocker record: the observed
  failure was test synchronization, not an indefinitely suspended production workspace. All tracing
  was removed and the instrumented production files restored byte-for-byte.
- With explicit operator approval, wrapped mocked session restoration and the real dynamic-import
  completion in React `act` in the two existing Plant deep-link cases. Applied the same synchronization
  to App's parameterized direct-creation routes after its first cold identity case failed in the
  combined focused run but resolved correctly in isolation. Existing detail/form assertions, real
  lazy imports, API fixtures, query/test timeouts and error boundaries remain unchanged. No production
  file was changed for this handoff, and HARVEST-002 semantics and Luna's existing changes are retained.
- Added a real hash/history regression covering Plant → PlantGroup switching, `?tab=events`, native
  Back/Forward events and return to `#/plants`. The test awaits actual hash/history events inside
  `act`, without sleeps, retries, global test configuration or mocked workspaces.
- Focused container validation: **126 passed across six files** (`App`, `PlantScreen`,
  `Propagation002`, App lazy/transition and WorkspaceBoundary). After callback lint corrections,
  App/PlantScreen again passed **107 tests**; the final event-synchronization adjustment passed both
  original deep-link regressions plus the history case (**3 passed**), and PlantGroup passed as a
  separate cold first import (**1 passed**). `pnpm format:check`, strict `pnpm typecheck`,
  `pnpm lint` with zero warnings and `git diff --check` passed.
- Optional browser smoke was unavailable: localhost:15174 refused the connection; read-only
  `make feature-review-status` confirmed Review frontend/backend exited, with the database healthy
  at revision `20261003_0031`. No Review volumes or credentials changed. No backend suite, canonical
  `make feature-verify`, staging, commit, push, delivery, merge or primary checkout modification was
  performed in this handoff. Independent review and final verification remain with Luna.

## 2026-10-03 — HARVEST-002 independent final-review verification

- Completed an independent review of the current feature tree, including the inventory ownership,
  quantity/state rules, serialized writes, source-context restrictions, Harvest/Event separation,
  Location projections, authenticated API boundary, generated contracts and operator-reviewed UI.
  No HARVEST-002 defect or unresolved domain decision was found. Final verification is blocked by
  an unrelated existing Plant/PlantGroup deep-link test that leaves the workspace on its loading
  placeholder.
- Extended the disposable PostgreSQL concurrency matrix to cover simultaneous tracking of the same
  HarvestItem and competing use-all dispositions. Both serialize on the owner-first locks; duplicate
  tracking conflicts without a second inventory and the losing use-all conflicts after seeing the
  depleted balance. Updated existing full-schema integration expectations for the two new inventory
  tables and the Harvest inventory Location scope.
- Added unit coverage for inventory API filter forwarding, error translation/rollback and write-route
  commit/refresh behavior to keep the required backend coverage threshold. Updated older Location UI
  expectations for the additional storage scope and fifth usage-count row.
- `make test-integration`: **458 passed, 571 deselected** against a unique disposable PostgreSQL
  Compose project, including HARVEST inventory and migration tests. The initial run exposed only the
  stale schema expectations above; the corrected full rerun passed. `git diff --check` and Python
  compile checks passed. The full frontend suite passed **358 tests across 39 files** after updating
  the two stale Location assertions. `make feature-verify` passed workflow and quality checks,
  including backend unit coverage at 90.14%, then failed in the unrelated Plants deep-link frontend
  test. The test also fails in isolation against the `origin/main` App.tsx and its regression test is
  preserved. No HARVEST-002 implementation files changed during the final gate attempt. Verification
  remains incomplete; no commit, push, delivery, merge or primary checkout changes were made.

## 2026-10-03 — HARVEST-002 operator UAT filter and peer-view corrections

- Continued only in `feat/harvest-002-inventory` in the existing `8dfa` Codex worktree.
  Reused Geography's peer-view button styling with `aria-pressed` and native Tab/Enter/Space
  behavior; no DetailTabs or dangling tabpanel relationships. `#/harvests` and
  `#/harvests?tab=stored-material` retain selected view across Back/Forward and refresh.
- Added the shared searchable ReferencePicker to both directories, default All botanical
  identities, with an accessible clear action and restored input focus. Choices are exact,
  deduplicated source identity references. Harvests reuse the existing `botanical_identity_id`
  API query and preserve the unfiltered choices while narrowed; Stored material filters its
  existing source projection locally. Identity composes with text/material/source type for
  Harvests and text/state/material/Location for Stored material. Misleading titles cannot
  establish membership. Global-empty and filtered-empty messages remain distinct. This UAT
  correction changed no backend, schema, generated contract or domain relationship.
- Aligned labels and 44px controls in compact desktop grids, two-column tablet grids and
  mobile full-width search/identity plus paired small selectors. Browser review of both URLs
  at **1440×844**, **1024×844** and **390×844** confirmed selected state, keyboard selection and
  clearing, exact identity/material/source composition, filtered-empty results and no page-wide
  horizontal overflow. Review initially showed no Harvests; three explicitly labelled synthetic
  UAT Harvests and tracked lines across two identities were added through existing services,
  including Plant/PlantGroup sources and an intentionally misleading cross-identity title.
  No existing Review records or volumes were removed or credentials changed.
- `make feature-review-up` and `make feature-review-status` passed: frontend/backend/DB healthy,
  source is this worktree, unchanged HEAD `519b9f0887b445fee84b19ea3ff96023a8573fac`, migration
  head/current `20261003_0031`, same `florabase-feature-review` DB/media/dependency volume names.
- Focused baseline **26 passed**. Final frontend **32 passed**: Harvest 9, Stored material 14,
  API query serialization 1, ReferencePicker 4, native reference interactions 2, plus the two
  targeted App route/keyboard cases (65 unrelated App cases intentionally skipped). Strict
  TypeScript, zero-warning ESLint, Prettier and `git diff --check` passed. Initial lint/import
  cleanup findings were corrected and the affected checks rerun successfully. No backend checks
  or API generation were needed for this frontend-only correction. Updated only the current UI
  contract and this milestone; prior implementation evidence remains intact.
- Operator visual acceptance remains pending. Work remains unstaged and uncommitted; no push,
  delivery, `make feature-verify`, new feature/worktree or primary checkout changes occurred.
  Review remains available at `http://localhost:15174`; screenshots remain outside the repository.

## 2026-10-03 — HARVEST-002 implemented for visual review

- Worked only in `/home/alessandro/.codex/worktrees/8dfa/florabase` on
  `feat/harvest-002-inventory`, attached with `make feature-init` from clean detached
  `origin/main`/HEAD `519b9f0887b445fee84b19ea3ff96023a8573fac`. HEAD remains unchanged.
  Primary `main` remains clean. No additional worktree, staging, commit, push, delivery,
  merge, feature-finish or canonical `make feature-verify` occurred.
- Added explicit zero/one inventory per historical HarvestItem and owned disposition facts.
  Positive finite NUMERIC exact/approximate count or mg/g/kg weight and unknown quantity stay
  independent of collected quantity. Active/depleted, storage Location, current correction,
  controlled consumed/processed/discarded/gifted/used_for_propagation, partial/use-all and typed
  immutable before/after snapshots follow [the inventory contract](harvest-inventory.md).
  Exact partial arithmetic preserves precision beyond 28 digits; approximate remainder requires
  confirmation; unknown stays unknown; use-all preserves precision and depletes.
- Harvest → inventory → Location locks refresh current state and serialize competing requests.
  Restrictive source-context FKs, item-kind/source triggers, unique item ownership, quantity/date/
  transition/snapshot checks and immutable disposition updates supplement service guards. Harvest
  correction retains item IDs and stock/history; deletion or tracked-line removal/kind changes
  conflict. History prevents tracking removal. No biological lifecycle/quantity/Location mutation,
  source Event, SeedLot conversion, propagation receipt, lineage edge, new media target or global
  search expansion was added.
- Inventory reads batch source/identity/Harvest context and storage paths with a history-existence
  flag; history loads on demand. The existing single recursive Location aggregate includes the
  fifth canonical inventory assignment type, active excluding depleted and total retaining it.
  Query evidence covers twelve rows and a deep tree within ten combined statements; the existing
  Location directory still proves two domain queries. Existing Locations migrate with storage
  eligibility disabled; scope removal/deletion guards retain assigned depleted material.
- Revision `20261003_0031` follows `20261002_0030`: no inventory backfill, historical quantity and
  owned Event retained across upgrade, empty downgrade/re-upgrade passes, populated downgrade
  refuses before destructive operations. Harvest-only Location scope is also guarded on downgrade.
  Review database reports the same head. Generated OpenAPI and TypeScript declarations match source.
- Focused checks: initial Harvest/Location unit baseline **56 passed**; final focused backend
  **77 passed** (Harvest 44, inventory 21, Location 12); disposable PostgreSQL **47 passed**
  (inventory 18, migration 1, existing Harvest/Location coverage 28). Real transactions verify
  7-vs-7 consumption at balance 10, disposition-vs-correction, tracking-vs-Harvest deletion and
  tracking-vs-material-kind correction. Tests retain genuinely preloaded ORM state, observe a real
  PostgreSQL lock wait and verify a valid refreshed outcome without arbitrary sleeps. Source and
  collected-quantity correction preserve stock/history; direct SQL cannot edit disposition facts.
  Hostile Origin, missing CSRF and unauthenticated access are rejected. Six pre-existing Alembic
  configuration deprecation warnings remain; no tests/checks/timeouts were weakened.
- Frontend focused **22 passed** (Stored material 13, Harvest 7, native Reference interactions 2).
  Backend Ruff and formatting, strict mypy (247 source files), frontend Prettier, zero-warning ESLint,
  strict TypeScript, `make api-check`, feature graph (86 valid features), production backend runtime
  image and frontend production build passed. `git diff --check` passed. Focused integration fixtures
  use unique tmpfs PostgreSQL Compose projects and scoped container/network cleanup without volume
  deletion. Initial import/fixture-cleanup/test-selector/lint failures were corrected and rerun.
- Feature Review is healthy at `http://localhost:15174`, project `florabase-feature-review`, with live
  source from this worktree and isolated review DB/media/dependency volumes. Owner was created through
  the supported password-stdin bootstrap; credentials/fixture scripts/screenshots stayed outside the
  repository. Synthetic examples cover untracked Harvests, exact seeds, approximate weight, unknown
  quantity, retained/depleted material, mixed tracked/untracked lines, dead Plant and completed
  PlantGroup, long botanical/source names and a five-level storage path.
- Browser implementation review at **1440×844**, **1024×844** and **390×844** checked directory/detail,
  tracking below collected amount, Location keyboard selection, each of the five categories, exact
  partial consumed (8→5 while Collected stays 10), approximate processed (confirmed About 60 g),
  unknown gifted partial, propagation use-all, discarded use-all, depletion, independent correction
  after history, never-used removal and retained mobile history. Filter-empty and depleted directory
  states work. No page-wide horizontal overflow was observed. Named dialogs, labelled quantity
  controls, visible focus, focus trapping, Escape/launcher restoration and focused server conflicts
  worked. Active/depleted and quantity precision use text. Mobile dialogs scroll within the viewport.
- HARVEST-002 is `implemented`, not `verified`. No unresolved implementation defect or new product
  ambiguity was found. Operator visual acceptance and independent Luna review/final canonical gate
  remain outstanding by the requested phase boundary. Work is intentionally unstaged/uncommitted:
  `READY_FOR_VISUAL_REVIEW`.

## 2026-10-02 — BOTANY-003 TLS diagnosis: missing provider intermediate

- Preserved all approved source/replacement findings on the current branch at `cd29de9`. Inspected
  the pinned Python 3.14.7 slim-bookworm Dockerfile and the unchanged development/runtime images
  using isolated read-only, non-root, no-mount diagnostic containers. Both already contain Debian
  `ca-certificates` `20250419~deb12u1`, populated system stores (150 roots) and certifi 2026.07.22
  (121 roots). Python 3.14.7/OpenSSL 3.0.20 default paths resolve to the system bundle/directory;
  SSL_CERT_FILE/SSL_CERT_DIR and conventional proxy variables are unset. Host has a newer public
  system CA package. Full image identities, bundle inventory and trust paths are in audit section 33.
- Direct SNI/verified OpenSSL diagnostics on host/development/runtime all receive exactly one
  identical certificate from the exact approved archive host: leaf `*.worldfloraonline.org`, issued
  by `GeoTrust TLS RSA CA G1`, valid 2026-07-14 through 2027-01-28, SAN matching the archive host.
  All fail with error 20 at depth 0. DigiCert's official metadata identifies the issuing intermediate's
  root as DigiCert Global Root G2, already present and valid in all tested system/certifi bundles.
  The issuing intermediate is omitted from the served chain; no issuer certificate was fetched,
  installed, embedded or trusted as a workaround.
- Host Python/system curl and both images' Python system/certifi plus HTTPX default/system probes
  all reject the chain with verification/hostname checks enabled. Evidence supports case C (observed
  remote incomplete chain), not a missing CA package, wrong effective CA path or hostname mismatch.
  No proxy/interception evidence was observed; no independent off-site network audit is claimed.
- `SOURCE_TLS_PROVIDER_BLOCKED`: WFO must serve its issuing intermediate to restore normal public
  chain validation. Provider-specific trust augmentation is an option requiring separate explicit
  approval, not implemented. No standard Florabase trust fix was justified; no rebuild, unrelated
  dependency change, insecure fallback, alternate source or application implementation occurred.
  BOTANY-003 remains `planned`; its source/product decision remains APPROVED. GBIF/CoL TLS behavior,
  operator services/data, branch and source research remain intact.
- Updated audit, domain-model blocker note, roadmap blocker note and progress. Pinned Prettier,
  feature graph (85 valid features) and diff checks cover documentation only. No provider-dependent
  CI check, application/migration/browser checks, canonical gate, staging, commit, push or delivery.

## 2026-10-02 — BOTANY-003 source/replacement approval and implementation access blocker

- Preserved the existing worktree/branch at `cd29de9` and all source-capability research. Recorded
  the operator's APPROVED decision C: WFO / Flora of China description → `description`; Kew WCVP
  `geographic_area` → `origin_distribution`; replacement policy 3 requires explicit Apply/confirmed
  Replace, typed immutable history and field-specific current attribution. Manual edits clear only
  the edited field's association while retaining history; source confirmation and stale-review
  checks are mandatory. No additional source/capability or provider-selection reconsideration.
- Tested the exact reviewed WFO archive securely before adding application code. Isolated read-only,
  non-root, no-mount containers from the existing QUALITY development and production backend images
  both used HTTPX 0.28.1/certifi 2026.07.22 with default TLS validation, fixed URL, no redirects and
  bounded streamed range retrieval. Both exited 1 before an HTTP response with
  `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate`. Host curl independently
  exited 60 for the same issuer-chain validation failure. Ephemeral probe containers were removed;
  operator environments/data and trust configuration were not changed.
- `SOURCE_IMPLEMENTATION_BLOCKED`: the operator required stopping if this exact approved access
  mechanism cannot be used safely. No TLS bypass, custom trust exception, alternate API/source,
  browser-download runtime mechanism or partial WCVP-only feature was substituted. Secure backend
  retrieval of this exact archive must succeed with a validated certificate chain before resuming.
  Root cause beyond the observed validation error has not been established; the earlier successful
  browser research and approved content/licensing findings remain intact.
- Updated audit, feature acceptance criteria, domain-model approved/deferred note, roadmap and
  progress. BOTANY-003 remains `planned`; no persistence model, route, parser, UI, migration or API
  artifact was implemented. Pinned Prettier, feature graph and diff checks cover documentation only.
  Implementation tests/build/browser checks did not run; the prior unrelated baseline failure was
  not investigated. No canonical gate, staging, commit, push, delivery, merge or finish.

## 2026-10-02 — BOTANY-003 bounded source-capability investigation

- Continued the existing `feat/botany-003-controlled-enrichment` worktree at `cd29de9`, under
  explicit research-only authorization. Extended `docs/botany-003-audit.md` with the full capability
  matrix, two actual taxa per source (Acer palmatum and Annona cherimola), access/license evidence,
  geography feasibility, provenance assessment and exact proposed responsibility boundaries.
- Retrieved WFO's publicly identified Flora of China Darwin Core Archive and verified exact WFO-ID
  description/reference joins, English general descriptions, CC BY 4.0/MBG effective metadata and
  original bibliography/URLs for both taxa. Classified this publication as public structured but
  weakly documented for consumers; no current supported live content API was established.
  Normal browser download succeeded; local curl reported issuer-chain validation failure. No TLS
  bypass or private harvester access occurred. Kept only minimal description excerpts in the report.
- Retrieved the officially supported Kew WCVP v16 download (extracted 2026-06-04), verified its
  README CC BY 3.0/citation, generalized distribution strings, native/introduced/extinct/doubtful
  flags and TDWG level-3 rows for both taxa. Inspected POWO's element-specific contributors/licenses;
  Annona UPFC uses carry CC BY-NC-SA 3.0, and poison-use/conservation categories are not warnings.
  The published historical pykew API hostname returned 403; no narrative API contract was inferred.
- Recommend source option C with non-overlapping fields: WFO's inspected licensed description
  subset → `description`; WCVP `geographic_area` → `origin_distribution`. Eligibility is conditional
  on explicit source choice, exact confirmed source IDs, approved snapshot access and durable
  per-value attribution. Existing GBIF/CoL remains taxonomy/match only. No third provider surveyed.
- Native ranges remain informational/unmapped: the official TDWG tables demonstrate KOR vs KP/KR,
  JAP vs political JP, and ECU vs GAL within EC. Florabase's CLDR places have no reviewed crosswalk;
  do not guess from labels or erase native/introduced distinctions. Cultivation, uses, warnings and
  uninspected contributors remain deferred. Mutable links/cache alone cannot retain applied-value
  license/reference/history; a small source-attribution extension is needed, not implemented.
- `SOURCE_CAPABILITY_DECISION_REQUIRED`. BOTANY-003 remains `planned`. Only the audit/progress
  documents changed. Pinned Prettier checks, `python3 scripts/check-features.py` (85 valid features)
  and `git diff --check` passed. No application tests or canonical gate were rerun, and the earlier
  unchanged frontend baseline failure was not investigated. No code/API/schema/UI/migration changes,
  staging, commit, push, delivery, merge or finish.

## 2026-10-02 — BOTANY-003 controlled enrichment audit

- Initialized the existing Codex worktree at `cd29de9` through `make feature-init` on
  `feat/botany-003-controlled-enrichment`. Audited the identity/profile, external adapter/cache,
  geographic hierarchy/native-range implementation, migrations, APIs, frontend modules, tests and
  current domain/architecture/roadmap contracts. The primary checkout and DEV were not modified.
- Recorded the full field matrix and requested handoff topics in `docs/botany-003-audit.md`.
  The implemented GBIF/CoL XR matcher supplies taxonomy and diagnostics, while BotanicalProfile
  owns five narrative sections and exact structured native ranges. There are no safe direct or
  deterministically normalized writable mappings. Taxonomy remains informational; narratives and
  native-status geography lack an eligible content contract. Official GBIF taxonomy documentation
  was checked; no new source capability was probed live.
- `NEEDS_PRODUCT_DECISION`: choose an approved profile-content source with an example linked taxon,
  retrieval/attribution/licensing contract and field mapping, or explicitly authorize bounded
  source-capability investigation. No placeholder proposal/apply API, synthetic taxonomy narrative,
  additional local fields, receipt or migration was added. BOTANY-003 remains `planned`.
- Baseline checks passed: 45 backend unit tests (`pytest --no-cov` over
  `test_external_botany_provider.py`, `test_external_botany_service.py`,
  `test_external_botany_api.py`, `test_botanical_profile_schemas.py`,
  `test_botanical_profile_service.py` and `test_botanical_native_range.py`); 15 PostgreSQL tests
  over external-botany API/migration and botanical-profile API/native-range migration suites;
  and 3 `ExternalBotanicalDataPanel.test.tsx` tests. PostgreSQL ran in isolated
  `florabase-integration-botany003-b4a3` with tmpfs storage, upgraded to actual code head
  `20261002_0030`, then its containers/network were removed without deleting volumes.
  Integration emitted 12 existing Alembic `path_separator` deprecation warnings.
- The additional unchanged `App.test.tsx --testNamePattern='profile|native.range'` baseline
  passed 10 cases and failed the directory/profile case at line 816 while locating the
  `Annona cherimola.*Cherimoya` button. The failure precedes profile interaction; it is not an
  enrichment regression. The exact case also failed in isolation. No test expectations, timeouts
  or unrelated UI were changed. Pinned Prettier checks over both changed documents,
  `python3 scripts/check-features.py` (85 valid features) and `git diff --check` passed.
- No application code or API artifacts changed, so application lint/typechecking/API drift and
  production builds were not run. No Feature Review launch, independent implementation review,
  operator acceptance, canonical `make feature-verify`, staging, commit, push, delivery, merge
  or finish was performed.

## 2026-10-02 — DEV upgrade initializer image portability fix

- Confirmed PR #64's upgrade path built only `backend`, then migrated before invoking
  `dev-state-init` from a potentially historical frontend development image. DEV upgrade now
  builds `backend` and `dev-state-init` together from the selected primary source and checks the
  initializer executable in the rendered image through a read-only, network-disabled Docker run
  without mounting DEV volumes, before starting the DB or applying migrations. Migration compatibility,
  revision confirmation and migration-before-initialization order retain their existing semantics.
- QUALITY frontend commands had the same initializer freshness assumption and now share this
  preparation helper. DEV up and Feature Review already build all services before initialization;
  Stable Preview/production/integration do not invoke this development initializer.
- Regressions failed against the old implementation and pass after the fix: stale/absent images,
  pending migration, already-at-head retry, build/executable failure before any DB operation,
  explicit current-source build ordering and QUALITY initialization. Focused checks passed
  29 environment tests, 37 feature-workflow tests, 19 Preview tests and shell helper fixtures;
  `make workflow-check` passed Ruff lint/format and strict mypy, plus `git diff --check`.
- `make smoke-dev-upgrade` passed on UUID project
  `florabase-dev-upgrade-smoke-51021aa5ae37`: the deliberately old image lacked the initializer;
  failed initializer build preserved revision 0029 and DB rows; rebuilding applied 0029 → 0030,
  initialized ownership, retried successfully at head and rebuilt again with the image absent.
  DB rows, media/dependency markers, all three volume identities and the DB container survived.
  Only fixture containers/network/volumes/image tags were removed. Before/after operator
  DEV/Review/Preview/production container+volume and primary Git snapshots match.
- Updated the canonical runtime freshness/retry invariant and added the repeatable isolated smoke
  target to script static checks. This worktree is attached through `make feature-init` to
  `fix/dev-upgrade-initializer-image` at main base `31209b2`. No primary checkout changes, operator
  DEV mutation, staging, commit, push, delivery, merge or finish. Ready for independent infrastructure
  review; the final canonical `make feature-verify` gate remains after that review. No graphical
  product review or feature-status promotion was performed.

## 2026-10-02 — CI-003 portable development and quality identity

- PR #64's GitHub `quality` failure reached frontend `pnpm format:check` but could not create
  `/app/_tmp_*`: Compose's 1000:1000 defaults did not match the invoking checkout owner. Both
  development application services shared this bind-mount assumption.
- DEV, Review and QUALITY now explicitly use the invoking POSIX UID/GID for both runtimes and
  project-local dependency/media initialization, overriding stale shell and `.env` defaults. Root
  invocation refuses; platforms without UID/GID APIs require an explicit numeric non-root identity
  in the process environment. Production and Stable Preview retain their image users and topology.
- Focused checks passed 26 environment tests and 37 feature-workflow tests, plus workflow Ruff
  lint/format and strict mypy. New linked-worktree cases cover UID 1000, UID 20023/GID 20024, stale
  settings, root refusal, missing/invalid host identity and production isolation.
- A separate synthetic `/tmp` checkout owned by 20023:20024 reproduced the exact frontend EACCES
  at UID 1000, then passed the same `pnpm format:check` with the corrected identity. Real non-root
  frontend/backend bind writes, backend media writes, fresh noninteractive dependency bootstrap,
  root-owned `.bin` repair, backend formatting/API drift and production configuration checks passed.
  Only the proven-new fixture resources were removed; the real checkout was never ownership-modified.
- Reviewed the correction and froze the tree before fresh `make feature-verify`; the canonical result
  and exact-worktree receipt are reported in the handoff. Correction remains uncommitted for operator
  review/redelivery on the existing branch and PR; no push, delivery, merge or finish was performed.

## 2026-10-02 — CI-003 safe foreign-source DEV recovery

- Fixed the independent review's recovery dead end: `dev-stop` no longer needs the primary or old
  Compose files to operate an existing DEV stack. Exact project/service/role (including recognized
  legacy metadata), source-mount and volume ownership checks identify DEV and fail closed on ambiguous
  resources. Stop retains its containers, network, DB/media/dependency volumes and all persistent data.
- Legacy media really uses Docker tmpfs, which disappears on stop. An initial isolated smoke caught
  Docker `cp`'s unsupported tmpfs view before any operator use. The final fixed helper reads the frozen
  backend's live filesystem through its PID namespace, exclusively copies missing regular files into
  the validated DEV attachment volume, verifies preservation and kills the frozen writer without a
  new-write window. Conflicts/copy errors leave the original backend alive; no media or volume is deleted.
- Primary startup accepts only a validated stopped stack, starts the retained DB without rebinding it,
  and refuses ahead/incompatible revisions before dependency initialization or application recreation.
  Explicit upgrade keeps the same revision guard; no automatic downgrade or implicit migration occurs.
  Stopped status reports retained source and exited state rather than cached healthy/running claims.
- Focused checks: 23 environment tests and 37 feature-workflow tests; workflow Ruff lint/format and
  strict mypy. Recovery coverage includes primary/foreign stop, old source absent, media conflicts,
  non-root ownership restoration, idempotence, ambiguous identity, destructive refusal, primary reuse
  and ahead-of-code state. Existing Review/Preview contracts and their isolation guards remain intact.
- `make smoke-dev-recovery` passed on a UUID-scoped real Compose fixture: vanished old source,
  tmpfs+durable media, DB rows and dependency state survive stop/recreation; services become healthy
  from primary; repeated stop is safe; ahead startup/upgrade refuse without downgrade. Operator DEV,
  Review, Preview, production and primary Git snapshots match before/after, including fixture cleanup.
- The prior receipt's digest `233acab3...` matched the dirty worktree. Its reported mismatch came from
  using the delivery check against uncommitted `HEAD`, not from stale source evidence. Added explicit
  `verify --worktree` for pre-commit review; default verification still requires both HEAD and working
  source for delivery. This fix changes the tree and requires fresh evidence. The final frozen-tree
  `make feature-verify` result and new exact-worktree receipt are reported in the handoff.
- Updated the canonical operator recovery flow and added the isolated smoke target. The live `8a70`
  DEV remains running and healthy; only read-only identity/status checks were performed on it. Primary
  is clean `main` at `4e90cce`; no real worktree creation, commit, push, delivery, merge or finish.

## 2026-10-02 — CI-003 environment/worktree workflow consolidation

- Discovered this Codex worktree clean/detached at `4e90cce`, identical to `origin/main` and primary
  `main`; attached `ci/development-environment-workflow` only here. No additional real worktree,
  commit, push, delivery, merge or finish was performed. Primary source/index remains untouched.
- Added idempotent existing-worktree initialization, isolated dirty-source Feature Review commands,
  primary-sourced DEV status/up/upgrade/stop, explicit production and worktree-quality projects,
  per-run disposable integration identity, automatic `.env` discovery and source/health/revision
  observability. DEV deliberately retains `florabase` to preserve existing operator volumes.
- Fresh named dependency/media volumes are initialized automatically; frontend stays non-root,
  bootstraps frozen dependencies without TTY and uses the pinned Corepack cache. DEV media is now
  persistent; legacy temporary media prevents unsafe recreation/stop. Revision compatibility guards
  distinguish code head from DB current and refuse ahead/incompatible state without downgrading.
- Stable Preview keeps clean `origin/main` source and immutable dependencies, uses its own stable
  overlay, rejects primary/other-branch paths and reports current/head. Its incomplete database-only
  import now refuses before mutation; coordinated DEV DB+media cloning is explicitly deferred.
- Delivery errors now print missing-CLI/auth/API/precondition evidence. Linked finish fast-forwards
  only clean primary `main`, retains the detached Codex checkout and atomically deletes only the
  proven merged branch. Receipt tests cover dirty/untracked migrations, symlinks, post-commit validity,
  later edits, per-worktree metadata, stale-evidence invalidation and edits during verification.
- Focused gates passed shell helper fixtures, 37 feature-workflow tests, 19 Preview tests, 13 environment
  tests, workflow Ruff lint/format and strict mypy for the new operational helpers, shell syntax,
  85-feature graph validation and whitespace checks. Early `make check` passed formatting/lint/types,
  550 backend unit tests, 339 frontend tests and API drift before final verification.
- Real `make smoke-environment-workflow` passed on this dirty linked source: untracked no-op migration
  applied only to Review, all three services healthy, frontend UID 1000, fresh noninteractive install,
  automated root-owned `.bin` repair, changed dependency/lockfile fixture, DB/media/dependency
  stop/restart persistence, Review-only destruction and independently healthy stable archive Preview.
  Production/integration configurations validate; smoke resource cleanup and DEV before/after
  container/mount/Git/revision snapshots match. No operator data was destroyed.
- Read-only `make dev-status` reveals the existing operator `florabase` project is still bound to the
  previous `8a70` worktree, with healthy services, temporary media root and DB revision 0030; selected
  primary code is also 0030. The command reports that source mismatch and refuses takeover. This
  legacy environment is deliberately left running and unchanged for operator reconciliation.
- [Canonical workflow](development-workflow.md), AGENTS, CONTRIBUTING, development/deployment guidance
  and the CI-003 graph entry are updated. CI-003 remains `implemented` pending independent infrastructure
  review. The frozen-tree canonical `make feature-verify` result and matching per-worktree receipt are
  reported in the handoff; no product graphical review is required. Public images/GHCR, release
  packaging, unrelated roadmap features and full DEV data cloning remain outside this increment.

## 2026-10-02 — lineage integrity audit for independent logical review

- Audited `320865b` / `fix/lineage-integrity-audit`, including HARVEST-001. Canonical ancestry uses
  explicit SeedLot/Sowing/Plant/PlantGroup foreign keys, including collection-produced SeedLot
  producers and immutable immediate extraction origins. Receipts, Events, Harvest, shared media,
  Location, geographic provenance/native ranges and botanical identity remain distinct. The
  [audit and invariant matrix](lineage-integrity.md) records corrections, historical retention,
  end-to-end representations, concurrency, query evidence and deferred capabilities.
- Reproduced three correction API cycles returning 200. All mutable source corrections now use
  the existing typed walker. Revision `20261002_0030` adds serialized acyclic graph writes and
  insertion-time source/result/Event correlation for all six receipt kinds. Existing cycles block
  upgrade without data repair; populated guard-only downgrade/reupgrade preserves all facts.
  READ COMMITTED graph-write isolation is enforced to avoid stale-snapshot lock races.
- Reproduced cached-ORM failures after competing commits in extraction, reintegration eligibility
  and SeedLot consumption. Locked reads now refresh current state before quantity/snapshot guards.
  Two further interleavings reproduced stale Plant/PlantGroup origin comparisons bypassing the
  reversed-Sowing guard; compare persisted origins before source-first row locking.
  Added complete exact/approximate/unknown extraction/reintegration/reversal histories, sibling and
  transfer isolation, five production generations, reference/Harvest/media separation, direct SQL
  corruption guards, stale-receipt correction, migration preservation and real lock contention.
- Semantic UI changes display ancestor lifecycle, prevent stale cross-record paths, and separate
  extracted Plants from direct Sowing results using an additive exact source-group API field.
  Both generated API artifacts are updated. No graphical polish, new lineage capability, feature ID
  or feature-status change is introduced; stale Event/reintegration documentation is corrected.
- Focused checks passed Ruff, strict mypy (240 source/test files), 83 backend unit tests, 72
  PostgreSQL tests, frontend lint/types and 68 affected frontend tests. The long-chain read returns
  22 ancestors in five statements. The main baseline test stages passed 546 backend / 336 frontend;
  its API-drift stage overlapped the contract edit and is superseded by final verification.
- The first full gate passed 550 backend unit and 339 frontend tests, then reached 434 successful
  PostgreSQL tests and failed the old expected migration-head assertion. Updated that assertion
  for revision 0030; the final gate is rerun after the confirmed origin-race fix.
- The next gate passed 550 backend unit tests (91.25% coverage), 339 frontend tests and 437
  PostgreSQL tests, production builds and the migration cycle, then failed receipt storage because
  `.git` is a file in this linked worktree. The helper now resolves its actual per-worktree Git
  metadata directory for write/read. A real linked-worktree regression and all 35 feature-workflow
  helper tests pass. Rerun the unchanged complete canonical gate on the final tree.
- Final full suites, API drift, feature graph/workflow helpers, production builds, migration cycle,
  whitespace and verification receipt run through `make feature-verify`; its exact completed result
  is reported in the handoff. No thresholds or runner settings are relaxed. The operator database
  is not upgraded; all work remains unstaged and uncommitted, with no push, delivery, merge or finish.

## 2026-10-01 — HARVEST-001 structured Harvest review handoff

- Continued `feat/structured-harvests` at `6a44a18`. Harvest records one Plant XOR PlantGroup,
  existing partial date, optional label/notes and 1–100 ordered material lines. Controlled material
  kinds, exact/approximate count or weight and unknown quantities retain explicit precision.
  Identity is derived from the source; lifecycle, group quantity, Location and seed inventory stay
  unchanged, including root, whole-plant and seed collection.
- Atomic aggregate writes own one protected harvest Event. Corrections update source/date/notes
  coherently; deletion removes Harvest and owned Event while retaining shared assets. Existing
  free-form harvest Events are preserved. Retained historical sources are selectable; concrete
  restrictive foreign keys protect their history. No source hard-delete API is introduced.
- Revision `20261001_0029` follows 0028. Concrete media/primary relationships extend the shared
  library. Immediate constraints and deferred aggregate/Event checks enforce final validity;
  populated downgrade refuses history loss and empty downgrade/reupgrade is supported.
- Added Collection navigation, directory/filters, compact desktop preview, detail, accessible
  multi-line forms, contextual source actions, identity Harvest history, Dashboard Quick action
  and structured Event links/images. Central image fallback preserves external-image privacy.
  Directory projection batches source/identity/material/image reads; 16 mixed-source records stay
  within eight statements.
- Baseline `make check` passed (502 backend unit tests, 90.89% coverage; 327 frontend tests).
  Development checks passed Ruff, backend/frontend typing and focused suites; 16 PostgreSQL tests
  cover rollback, coherence, source retention, media/primary membership and migration preservation.
  The complete canonical `make feature-verify` result and receipt are reported in the handoff;
  no thresholds, timeouts or runner settings are weakened.
- Browser review uses isolated synthetic data at 1440 × 844, 1024 × 844 and 390 × 844, covering
  directory/preview, one/multiple-item creation, correction, detail/media, Plant/PlantGroup contextual
  creation, activity/journal links, long names and partial/unknown dates/quantities. Keyboard material
  add/remove focus and dialog focus restoration were checked; no horizontal overflow was found.
  The [Harvest handoff](harvests.md) records the contract, review matrix and exact changed files.
- HARVEST-001 remains `implemented` pending operator acceptance. The tree stays unstaged and
  uncommitted on the same branch. Harvested-material inventory/disposition and explicit SeedLot
  conversion remain separate pre-1.0 candidates; all established roadmap milestones are preserved.

## 2026-10-01 — ATTACHMENT-005 persistent external copies

- Continued the same unstaged `feat/shared-media-library` tree. External assets keep their kind,
  canonical URL, attribution, UUID, links, primary selections and covers while optionally referencing
  one protected Attachment snapshot with UTC fetched-at metadata. Explicit Save/Refresh/Remove copy
  routes reuse original storage and shared derivatives; reads prefer saved content across views.
- Bounded fetches validate every DNS result and redirect, pin public IP connections, verify TLS
  hostnames, reject unsafe destinations/credentials, cap timeout/bytes, and reuse strict still-image
  decoding and pixel-bomb checks. Failed refresh retains the valid copy. Asset-row locks and a
  durable pending-cleanup pointer serialize copy/deletion actions and support explicit retry.
- Revision 0028 follows 0027, initializes old external copies as absent, performs no network access,
  and guards downgrade while copies/cleanup remain. Both migration contracts and the full empty
  cycle are covered. Persistent snapshots are included in paired original/database backups.
- Focused checks passed: Ruff, strict backend typing (229 files), 85 backend security/storage/media
  unit tests, 42 frontend media/photo/activity tests, frontend lint/types, and 19 PostgreSQL lifecycle,
  rollback, migration and real lock-race tests. The final canonical gate covers the complete tree;
  its result is reported in the handoff. No runner settings or thresholds are relaxed.
- Browser review at 1440 × 844, 1024 × 844 and 390 × 844 exercised real Save/Refresh, concise Gallery
  states, saved metadata, protected record/Photos/activity imagery, and removal confirmation with
  Escape focus restoration. No horizontal overflow was found. The tree remains unstaged and
  uncommitted; operator visual acceptance remains pending.

## 2026-10-01 — ATTACHMENT-005 shared media review handoff

- Continued the clean `feat/shared-media-library` branch at `1c4fbf1`, implementing the approved
  unlinked-media policy. MediaAsset owns one local original or attributed external reference;
  exact RecordMediaLinks retain the five established targets and independent caption/order.
  Explicit SeedLot/Plant/PlantGroup primary designations remain per target. Identity covers remain
  separate active references. Unlink and cover replacement retain assets; deletion requires zero
  collection links and zero covers, with no automatic cleanup or destructive cascade.
- Revision `20261001_0027` preserves existing IDs, files, technical/source metadata, targets,
  captions, chronological order, primary and cover references. Representative pre-upgrade data
  and guarded populated downgrade are tested. Empty downgrade/reupgrade is supported; populated
  rollback requires the coordinated pre-upgrade database/content backup.
- Added the paginated Media directory, compact preview, dedicated detail, shared metadata editor,
  record picker and record Photos link-existing workflow. External references stay unloaded in
  Gallery/Quick Preview and require explicit detail/Photos opt-in. Original storage/security and
  central record-image fallback remain. One locked, cached 320px WebP derivative serves every link.
- Baseline `make check` passed (433 backend / 310 frontend). Final focused checks passed Ruff,
  backend typing, 45 media/cover/API unit tests, frontend format/lint/typing and 81 Media/Photos/App
  tests. PostgreSQL migration, reference constraints, bounded queries, duplicate-link and
  link/delete races, primary serialization and HTTP auth/CSRF checks passed. The canonical
  `make feature-verify` runs the complete final suites, API drift, builds and migration cycle;
  its completed outcome and tree receipt are reported in the handoff. No thresholds or runner
  settings were weakened.
- Rendered review used disposable synthetic fixtures at 1440 × 844, 1024 × 844 and 390 × 844:
  Gallery/pagination/filters, landscape/portrait/square previews, detail, record Photos and both
  pickers; primary set/clear, link reuse, last-unlink retention, cover-only deletion guard, external
  opt-in/failure, empty search and keyboard Escape/focus restoration. Reviewed views have no
  horizontal overflow. The [media handoff](media-library.md) records contracts, resource/query
  evidence, migration/compatibility notes, review matrix and exact changed files.
- ATTACHMENT-005 is `implemented`, awaiting operator visual acceptance. Architecture/domain/storage/
  backup/deployment docs were updated, and the requested eight pre-1.0 roadmap milestones remain
  future work. No stage, commit, push, delivery, merge, branch switch or feature-finish is performed.

## 2026-10-01 — LOCATION-003 hierarchical usage final review

- Continued `feat/location-descendant-aggregation` at `c1fc7c5`. LOCATION-003 adds derived
  direct and arbitrary-depth inclusive usage for SeedLot, Sowing, Plant and PlantGroup. Legacy
  `usage` remains direct (including combined Plants/groups); additive `direct_usage` and
  `usage_including_descendants` expose the four types separately. Total/all-lifecycle and
  active-only semantics, assignment eligibility and child/direct/history deletion guards remain.
- The directory uses one hierarchy read plus one batched recursive PostgreSQL aggregate;
  distinct containment pairs terminate even for malformed cycles. No N+1 record queries,
  persisted counters, new indexes or migration are introduced. A representative planner check
  on 206 Locations/4,015 assignments reported 6.107 ms execution with one scan/aggregate per
  record type. Reparent tests verify both roots change without any record Location update.
- Directory and desktop Quick Preview show inclusive content with an explicit direct count when
  different, equal leaf counts once, and one empty message. Detail compares both scopes with
  per-type total/active counts. Existing general collection links are preserved: Location has
  no associated-record list, so no listing scope/default was introduced. Deep rows retain parent
  context and full paths while indentation stops growing after three levels.
- Focused checks passed 12 backend unit tests, 16 PostgreSQL Location/migration tests and
  66 frontend App/Location tests. Added coverage includes twelve-level trees, siblings, roots,
  empty branches, every lifecycle/type, source non-inference, cycle termination, two-query batching,
  additive API semantics, keyboard selection and deep-tree collapse/path context. Final complete
  suites and quality/API/build checks run through the canonical local gate; the completed result
  and tree receipt are reported with the handoff. No test settings or thresholds were weakened.
- Rendered review in the in-app browser covered 1440 × 844, 1024 × 844 and 390 × 844,
  including parent-only descendant content, mixed and leaf counts, empty Quick Preview, long paths
  and the expanded twelve-level mobile tree. Review found and fixed indentation collapse from
  26 px to a readable 211 px row. Final reviewed frames have no horizontal overflow; compact
  counts are included in the accessible row names. The [audit](location-descendant-aggregation.md)
  records contracts, query-plan evidence, visual matrix, screenshots and changed files.
- Operator visual acceptance and independent final review are complete. The review confirmed the
  direct/inclusive contract, all four canonical assignment types, unchanged legacy usage, recursive
  cycle-safe aggregation, dynamic reparenting, lifecycle semantics, API drift, existing deletion
  guards, and UI scope labels. No implementation defect or product ambiguity was found. The prior
  canonical verification receipt matches this tree; `git diff --check` passes. LOCATION-003 remains
  `implemented` pending final commit and delivery. All edits remain unstaged and uncommitted; no
  commit, push, merge, delivery or feature-finish ran.

## 2026-09-30 — Final operator pass 33–47 ready for visual acceptance

- Continued `feat/ui-consistency-polish` at `cd5bf70`, preserving prior work. Guided
  Sowing and Plant/PlantGroup forms now reuse normal field groups/section navigation,
  retain source/lineage, atomic quantity/result semantics and receipts, and use the
  existing display-name resolver. Nested native/server validation reveals and focuses
  the owning section without discarding state.
- Added accessible desktop sidebar resizing (248px default, 220px minimum, up to
  400px/35% of viewport), live route-preserving width and 32px collapsed inset. World
  initially expands to continents; user interaction remains. Shared More menus use
  anchored viewport-bounded portals with outside/Escape/focus behavior. Geography
  Sites/Map creation uses the existing page-header action pattern.
- BotanicalIdentity Edit groups existing Identity/Reference/Native range/Media owners;
  normal desktop sections fit, with independent detail navigation retained. Provenance
  Sites accept validated decimal or DMS inputs through unchanged decimal payloads.
  Labels adopts controls/preview composition and compact expandable print guidance,
  preserving dimensions, 4 × 9 print sheet and configured-origin QR semantics.
- Rendered review succeeded in the Codex in-app browser at 1440 × 844, 1024 × 844 and
  390 × 844 for every requested surface. The [audit](ui-consistency-polish.md) records
  the exact matrix, item 33–47 statuses, 108 chronological review captures and exact
  final-pass/complete branch manifests. Final frames replace QA-found quantity overflow,
  DMS label collisions, Botany spacing and tall Labels guidance. Operator acceptance
  remains pending. The synthetic tmpfs project was removed and browser overrides reset;
  no normal operator data or volumes were deleted.
- Affected checks passed 174 tests/10 files, compatibility checks 58/5 and final
  Seed/Labels checks 51/2. The final full frontend suite passed **304 tests/33 files**
  (19:57:22, 124.57s); formatting, zero-warning lint, strict TypeScript/production build,
  exporter/generator API drift, feature graph (81), Markdown formatting and diff checks
  passed. Intermediate interrupted execution is excluded from verification evidence.
- No backend/API/generated-contract/migration change was added by this final pass;
  earlier branch changes remain preserved. Supplier imagery/logo is explicitly post-0.1.0;
  Location `Direct here` / `Including descendants` remains a functional follow-up.
  UX-006 stays `implemented`. No canonical gate, staging, commit, push, merge, delivery
  or feature-finish ran. All work remains unstaged/uncommitted for visual acceptance.

## 2026-09-30 — Sectioned forms and shared record presentation ready for visual review

- Continued `feat/ui-consistency-polish` with the requested A–T refinement. Shared
  left-aligned workspaces begin 24px from the desktop sidebar, with surplus width
  on the right. A small shared form-section primitive keeps one mounted form/state,
  direct keyboard-accessible tabs, Back/Next, final-only submission and invalid-field
  reveal/focus. SeedLot, Sowing, Plant/PlantGroup, BotanicalProfile and ProvenanceSite
  editors use it; compact identity names and independent reference actions remain
  reachable. Existing payloads, partial dates, quantities and lineage are preserved.
- Centralized record imagery resolves local designated primary, eligible botanical
  cover, then type placeholder, including exact Event targets. Display names resolve
  explicit label, common name, useful cultivar, scientific name, then generic fallback
  without stored-name changes or numbering. Bounded photo cards and contained Botany
  preview images preserve aspect ratio. Sowing preview groups primary, maintenance
  and descendant actions. Reference shares shell, search and inset focus geometry.
- Rendered review completed at 1440 × 844, 1024 × 844 and 390 × 844 across all
  eleven requested routes and every required editor/photo/preview surface. The
  [audit](ui-consistency-polish.md) records the exact matrix, 117 final captures,
  image-shape checks, retained values and hidden native/server validation focus.
  QA-found small Seed rows, Sowing action sizing, mobile focus and activity badges
  were corrected. No page-wide horizontal overflow was found. Existing tablet/mobile
  selection opens detail directly where Quick Preview is desktop-only. The earlier
  browser limitation is resolved; final operator acceptance remains pending.
- Affected frontend checks passed 108 tests across 10 files; the complete final
  suite passed 281 tests across 30 files. Formatting, lint, TypeScript, production
  build, API exporter/generator drift, feature graph (81 features) and diff checks
  passed. No canonical gate or unrelated backend suite ran during this refinement;
  initial-phase backend/generated changes remain preserved.
- Shared media (`MediaAsset` ↔ `RecordMediaLink` ↔ records) and Location counts
  (`Direct here: 2` / `Including sublocations: 7`) remain documented follow-ups.
  UX-006 remains `implemented`; HEAD remains `cd5bf70`, all changes unstaged and
  uncommitted. No push, delivery, merge or finish ran. The synthetic review project
  and browser tab were removed without deleting operator data or volumes.

## 2026-09-30 — Final operator UI pass, rendered confirmation pending

- Continued `feat/ui-consistency-polish` for items 16–32. Shared desktop inset,
  compact Seed/Plant edit disclosures, Sowing action groups/facts/path, compact
  creation dependency panels, Plant origin/operations, neutral local-only directory
  photo slots, viewport-sized map, and scoped Botany cover/actions/edit/search fixes
  are implemented. The [audit](ui-consistency-polish.md) records the exact final-pass
  and 31-file branch manifests, each requested status and remaining visual checks.
  Shared media and Location subtree aggregation are documented follow-ups only;
  current direct usage and descendant-aware Dashboard filtering are unchanged.
- Focused checks passed 114 tests across eight files; the final complete frontend
  suite passed 268 tests across 27 files. An added note-retention assertion was
  corrected to retain original text; an intervening host-memory timeout run recovered
  with unchanged tests after stopping only the disposable review web services.
  Formatting, lint, TypeScript, production build, exporter/generator API drift,
  feature graph validation (81 features), Markdown formatting and diff checks passed.
- Rendered desktop checks confirmed compact Seed/Plant/Botany editors, keyboard
  access to Botany fields/actions, two-observation Germination, landscape cover and
  map composition. Final overview refinements, directory thumbnails/focus, actual
  Botany overflow scroll and the full 1024 × 844 / 390 × 844 matrix remain
  VISUAL_CONFIRMATION_PENDING: the browser connection disappeared under exhausted
  host memory and did not recover after tests recovered. Saved `final-` desktop
  screenshots remain available. Earlier 1–15 behavior passes regression checks;
  final responsive visual reconfirmation is pending, not claimed.
- Frontend/tests/docs only in this pass; earlier backend/generated changes are
  preserved. UX-006 remains `implemented`; HEAD is `cd5bf70`, with all changes
  unstaged/uncommitted. No gate, commit, push, delivery, merge or finish ran.
  The disposable review project was removed without operator volume/data changes.

## 2026-09-30 — Fifteen-item UI corrective pass for visual review

- Continued on `feat/ui-consistency-polish` with the focused Dashboard, Seeds,
  Sowings, Plants, Events and Provenance map corrections. The updated
  [audit](ui-consistency-polish.md) records one PASS receipt for each requested item,
  the exact 16 corrective-pass files and the full 26-file branch manifest. UX-006
  remains `implemented`; no feature graph status changed.
- Shared labelled record relationships clarify headers. Seed Remaining aligns in
  directory rows; grouped Seed/Sowing/Plant editors use desktop width. Sowing preview
  actions are grouped, Germination uses paired metrics/history, and propagation paths
  respond to their own available width. Plant group origin/history share a desktop row.
  Dashboard filter scroll controls reserve an inner gutter. Global Events and record
  journals reuse local-only target thumbnails without external/absent/broken placeholders.
  Map reuses the page intro and keeps its layers below mobile navigation. Existing
  values, validation, disclosures, operation guards, privacy and payloads are preserved.
- Corrective affected tests passed 113 cases across nine files; final full frontend
  tests passed 265 cases across 27 files. Frontend formatting, lint, TypeScript and
  production build passed. Existing API exporter/generator drift checks passed in the
  disposable review environment, feature graph validation passed (81 features), and
  Markdown formatting plus `git diff --check` passed. No backend/schema/generated
  contract edits were made during this corrective pass; initial-phase changes remain.
- Browser access recovered. Representative rendered checks covered 1440 × 844,
  1024 × 844, 1024 × 600 and 390 × 844, with the exact surface matrix in the audit.
  Long-label Seed edit height decreased approximately 39%; expanded individual Plant
  edit decreased 30% during review. The PlantGroup essentials editor fit 844px height.
  Measured views had no page-wide horizontal overflow; inset selected keyboard focus
  remained visible. Screenshots are saved in this task's visualization folder.
  Expanded editors, populated galleries/long history and operation receipts retain
  natural scrolling; exhaustive content/viewport combinations and operator visual
  acceptance remain pending. The disposable project was removed without deleting
  operator data or volumes.
- All changes remain unstaged and uncommitted at `cd5bf70`. No feature gate, delivery,
  push, merge or finish was run. Suppliers and deeper Reference work remain deferred.

## 2026-09-30 — Scoped UI consistency polish for visual review

- Implemented the reported Dashboard, Seeds, Sowings and Plants polish on
  `feat/ui-consistency-polish`. The [implementation audit](ui-consistency-polish.md) records the
  shared header/form/highlight rules, root causes, exact changed files and visual-review limits.
  UX-006 remains `implemented`; the feature graph is unchanged.
- Reused `WorkspaceIntro`, `Breadcrumbs`, `DetailHeader` and `PrimaryPhotoVisual`. Record/task
  headers reduce repeated context, forms use aligned responsive grids, fact values align and detail
  sections use desktop width. Sowing preview gives Open details primary emphasis. Inset result
  focus/selection and symmetric scrolling clearance resolve the identified clipping cause.
- Dashboard Events expose only the explicit Plant/PlantGroup target's designated primary photo,
  through the existing batched summary helper and protected local thumbnails. External designations
  remain neutral. No inheritance rule, migration, attachment/privacy change or unresolved domain
  decision was introduced. Existing disclosure, validation and payload contracts remain intact.
- Final affected frontend checks passed 87 tests across five files; the complete suite passed
  264 tests across 27 files. Frontend lint, formatting, TypeScript and production build passed.
  Backend focused tests passed 42 cases; Ruff formatting/lint and Event mypy checks passed. The
  affected PostgreSQL suites passed 17 tests, including Dashboard photo designation/clearing and
  thumbnail authorization. The first full integration run passed 357 tests and failed one exact
  response expectation; adding the new nullable target field to that expectation resolved it.
  No test timeout, sleep, retry, skip or runner change was introduced.
- API drift (`make api-check`), feature graph validation (81 valid features), Markdown formatting
  and `git diff --check` passed. Interim rendered review at 1440 × 844 covered Dashboard imagery and
  filters plus Seeds directory/preview/overview/detail with long context; no horizontal overflow was
  visible there. Browser access then became unavailable during host memory pressure. Final desktop,
  tablet and mobile layouts, affected editors and selected/focused result geometry remain pending
  operator visual review; responsive rendering is not claimed as verified. The disposable
  `florabase-ui-review` project was removed without deleting operator data or volumes.
- Work remains unstaged and uncommitted. No canonical feature gate, delivery, merge or finish
  workflow was run. Suppliers and the deeper Reference redesign remain intentionally deferred.

## 2026-09-30 — Plants and Plant groups UX consistency for visual review

- Refined the Plants-specific UX-006 implementation on `feat/plants-plantgroups-ux`; the feature
  graph remains unchanged and UX-006 remains `implemented`. The
  [audit and review notes](plants-plantgroups-ux.md) record findings, decisions, domain boundaries,
  rendered coverage and scoped follow-ups.
- Directory rows now prioritize identity, lifecycle and tracking type, with group-only exact,
  approximate or unknown quantity and wrapping recorded context. Designated collection photos also
  appear in the established desktop Quick Preview. Open details leads inspection; Edit leads normal
  correction, while extraction and whole-record transfer are secondary collection operations.
- Detail separates record summary, managed group, origin/provenance, notes and explicit extracted-Plant
  history. History uses only stored group origin and retains Reintegrated Plants without inferring
  current membership. Historical location/quantity labels describe retained facts; historical records
  do not show empty current-operation sections. Existing Events, Photos, Lineage, receipt reintegration
  and creation-reversal contracts remain intact.
- Both entry types put identity, label, group-only quantity and location in Essentials. Additional
  details retains mounted values, editing starts expanded, validation exposes corrective fields and
  focuses visible feedback, and final submit/Cancel actions follow the fields. Creation and structural
  dialog focus return behavior is covered. No shared component, backend, API, migration, dependency
  or persistence contract changed; the added styles are scoped to Plants.
- Live production-runtime review used only a separate disposable `florabase-ux-review` Compose
  project. Inspected 1440 × 844, 1024 × 844, 390 × 844 and 1024 × 600: populated and single-record
  directories, no-match/empty states, long botanical names/location paths, sparse records, landscape
  and portrait primary photos, disclosure, detail and dialogs. No horizontal overflow was observed.
  Exercised Plant creation/edit/location correction, movement Event and protected Photos; group
  creation with unknown quantity, approximate/exact edits, extraction and receipt reintegration,
  retained relationship history and authoritative Events. The review project was removed without
  volume-deletion commands; operator projects and data were preserved.
- The affected suite (`pnpm exec vitest run --configLoader runner src/plants/PlantScreen.test.tsx`)
  passed 38 tests; `pnpm test` passed 260 tests across 26 files using the repository's existing runner
  configuration. Thirteen behavioral cases were added
  for disclosure/value retention, quantities, sparse identity, stored extraction links, primary-photo
  privacy, historical facts and focus/validation. An overlapping test/lint attempt failed under host
  memory pressure; final tests passed with checks separated. Timeouts, runner settings, retries and
  skip behavior were not changed.
- Frontend `pnpm lint`, `pnpm format:check`, `pnpm typecheck` and `pnpm build` passed, as did
  Prettier checks for both changed Markdown documents. API drift (`make api-check`),
  `python3 scripts/check-features.py` (81 valid features) and `git diff --check` passed. The
  implementation is unstaged and uncommitted for independent visual review; no `feature-deliver` or
  `feature-finish` workflow was run. Suppliers and Reference remain candidates for their separate
  consistency passes.

## 2026-09-29 — independent shell and propagation UX QA

- Independently swept Dashboard, Seeds, Sowings, Plants and Plant groups, Suppliers, Botanical
  identities, Locations, Geography and provenance sites, Provenance map, Events, Labels, and Import /
  Export. Rendered checks covered 1440 × 844, 1024 × 844, 390 × 844, and 1024 × 600. Sidebar hide
  and reopen preserved the mounted workspace; hidden navigation had no focusable descendants, and
  state reset on reload. No shared-shell overflow, clipping, or route-width regression was found.
- Review corrected exact-zero Sowing copy and guarded observed percentages and T50 against zero-count
  denominators even if a response supplies derived values. Added boundary coverage for exact positive,
  approximate, weight, unknown, absent and zero quantities in list/detail paths. Test helpers now wait
  for the route or collection state the test needs; the session-expiry Plant test keeps its login-path
  assertion without waiting for an authenticated page title.
- The full frontend suite passed (247 / 247 tests, 26 files). `make check` and `make feature-verify`
  returned successfully; the latter recorded the final tree, ran disposable integration tests and
  production builds, and confirmed no Alembic revisions were added. `git diff --check` passed.
  No files were staged or committed.
- Follow-up gate review found that pytest-cov's `--cov-fail-under=90` was active, while
  coverage.py's default zero-decimal precision rounded 89.82% to 90 for its exit-status comparison.
  The raw pytest process therefore returned status 0; Make, the feature gate, and CI did not swallow
  an upstream failure. Coverage reports now use two-decimal precision, and a policy regression test
  locks both the 90% threshold and precise comparison. Focused germination-service tests cover
  validation and mutation paths; the direct backend run now passes 431 tests at 90.52% with status 0.

This log preserves meaningful verified milestones and current repository state. Exact acceptance
criteria and current status live in [`features.json`](features.json); Git history retains line-level
implementation detail.

## 2026-09-29 — shell and Sowings pre-release polish for operator review

- The desktop sidebar now hides and reopens with labeled keyboard controls while keeping the same
  workspace mounted. At 1440 × 844 and 1024 × 844 in the disposable preview, all groups and the
  account footer fitted without sidebar scrolling; hiding reclaimed the full workspace width.
  Navigation is Overview, Collection, Reference and Tools, with Botanical identities under Reference.
  The shared shell no longer adds an outer page-like background, shadow or clipping edge; it keeps
  readable maximum width and responsive gutters. Mobile retains its existing navigation behavior.
- New Seed lot is a single task without a duplicate top action. Essentials and Inventory stay in the
  fast-entry flow; Acquisition, Storage, Provenance, Seed details and Notes use a labeled disclosure
  that retains entered values. Quantity, source and partial-date controls are grouped with their
  related fields; final Add to collection and Cancel actions follow the form. Existing exact,
  approximate, unknown, supplier, storage and geographic-origin meanings remain unchanged.
- Sowings now uses a compact scrolling directory and persistent Quick Preview on desktop, with
  explicit identity, source, context, lifecycle and germination row information. Percentages use only
  a positive exact Sowing seed count as denominator; approximate, mass and unknown quantities keep
  text-only germination totals. Overview separates Source, Sowing, Germination, Results, Cultivation
  and Notes. Direct creation and editing use grouped fields and additional details; the Seed lot
  guided task remains distinct. Germination observations remain evidence, with derived values shown
  only when available. Descendant tasks distinguish the result and resulting Sowing state.
- The full frontend suite passed with one worker (247 tests across 26 files) before the final mobile
  row and descendant-copy corrections. After those edits, formatting, lint, TypeScript, production
  build, the exact affected descendant test and whitespace checks passed. API drift passed earlier;
  neither final edit touched the API. A broader
  focused rerun on the loaded host missed several lazy-screen waits; that run is not counted as a
  pass. `make check` passed formatting, lint, typing and all 425 backend unit tests, but its two
  Docker frontend runs exited with different slow-test failures (246/247 and 242/247). The
  originally timed-out Geography case then passed unchanged in the same Docker image; the two
  variable Plants/Seeds files passed unchanged with one worker (48/48). No test timeout, assertion
  or implementation was weakened for the loaded
  host. The disposable browser pass checked shell fit, hide/show, workspace width, Seeds creation,
  and Sowings directory, preview and detail at 1440 × 844 and 1024 × 844. A reopened 390 × 844
  preview exposed cramped Sowing row wrapping; a mobile-only grid correction was rebuilt and visually
  rechecked. Mobile Seed lot
  create, additional details, Sowing detail, New Sowing, Germination and Sowing-to-Plant forms used
  natural page scrolling without horizontal overflow. A 1440 × 844 route sweep covered Dashboard,
  Plants, Events, Botanical identities, Suppliers, Locations, Geography, Labels, Import / Export
  and the provenance map for headings and shell width. At 1024 × 600 the sidebar navigation scrolls
  while its account footer stays visible. The disposable stack was removed. No backend, API, schema,
  migration, dependency, eager route import or per-row request changed. All work remains unstaged
  and uncommitted; `make feature-verify` is reserved for the authorized later phase.

## 2026-09-28 — Seeds vertical UI polish for operator review

- Dashboard Quick actions now contains four collection and four reference creation links, each using
  the existing route and creation form. The Tools shortcuts were removed from that panel; both tools
  remain in the sidebar. Clicking an active sidebar destination returns to its canonical root and
  resets transient workspace state without a document reload. An edited form asks before discarding
  changes. Plants retains `+ New plant or group` because that button still opens a choice between
  individual Plant and PlantGroup creation.
- Seeds now gives its inventory more desktop width, compact two-line rows, a bounded list scroll
  area, and a persistent inspector. Rows, preview and detail distinguish active remaining quantity
  from a historical recorded quantity and preserve exact, approximate and unknown wording. The
  inspector shows the available Start sowing action and concise status, storage and Supplier facts.
  Overview uses separate Inventory, Source & origin, Dates & condition and Notes groups, with
  consistent internal links. The editor groups every existing field by task and keeps advanced
  fields visible during correction.
- Guided sowing shows the source lot and its state before entry, then requires an explicit choice to
  keep inventory unchanged, use part or use the whole lot. Exact compatible partial use previews
  its remainder; approximate partial use asks for a confirmed estimate without arithmetic; unknown
  stays unknown. The final step states the resulting operation and retains cancel, validation and
  conflict recovery. No backend, API, schema, migration, dependency or per-row data request changed.
- An authoritative original denominator is not stored for SeedLots. Receipts and current Sowings do
  not establish an all-time total after corrections and reversals, so a numeric utilization bar or
  used percentage would imply unsupported precision. This remains a domain decision for a separate
  increment; this pass shows the stored quantity and lifecycle truthfully.
- The disposable populated preview was reviewed at 1440 × 844, 1024 × 844 and 390 × 844 for Seeds
  directory, selection, filters, search, preview, detail tabs, editor, guided sowing, validation and
  active-sidebar reset. Disposable approximate, unknown and exhausted lots confirmed truthful row,
  preview and guided-use states alongside the exact fixture. Desktop list scroll and mobile natural
  document scroll were confirmed with
  no horizontal overflow. The final mobile pass restored bottom clearance below the fixed navigation
  so the guided form's Cancel link and editor actions remain reachable. The preview was removed after
  review. Focused tests passed, the full
  frontend suite passed (245 tests across 26 files), and `make check` passed formatting, lint,
  backend and frontend type checks, backend and frontend tests, and API drift. Production build and
  whitespace checks also passed. Changes remain unstaged and uncommitted; independent Seeds visual
  review precedes `make feature-verify`.

## 2026-09-28 — cross-application UI consistency for review

- Completed the existing Dashboard launcher with compact Create, Reference workspaces and Tools
  groups. New seed lot, sowing, plant and plant group links open their existing creation flows; the
  sowing link still requires an explicit SeedLot choice. Botanical identities, Suppliers, Locations
  and Geography link to their workspaces because they have no canonical direct-create route. Events
  remain contextual to a Plant or PlantGroup, so there is no global Event shortcut.
- Aligned major workspace eyebrow, title and one-sentence subtitle copy with the reviewed product
  terminology. Plants now says `+ New plant or group` because its button offers both creation paths;
  Seed lots and Sowings use explicit sentence-case actions. Mobile Seeds, Sowings and Plants titles
  now use the same compact 32 px scale as the other workspaces. Existing detail headers were
  inspected without changing their record structure or content.
- The route title flash came from bare loading/error `<h2>` elements on Seeds, Sowings and Plants
  inheriting the global large heading style before each compact ready header appeared. These states
  now share one `WorkspaceIntro` structure and copy. The lazy-route Suspense fallback is a restrained,
  title-free skeleton; route-level lazy imports and the separate chunk-failure recovery boundary remain.
  A deferred-module test covers the unresolved-chunk transition without introducing a duplicate title.
- Live disposable populated-preview navigation covered Dashboard → Seeds → Sowings → Plants → Events
  → Botanical identities → Suppliers → Geography → Labels → Dashboard at 1440 × 844 and 1024 × 844;
  mobile navigation and the same major routes were reviewed at 390 × 844. Loading and ready headers,
  the mobile More menu, four creation links, Quick actions, detail header structure, sidebar stability
  and horizontal overflow were inspected. No oversized title, competing header, white flash or
  horizontal overflow was observed. The preview was removed after review.
- Focused frontend tests passed (64 in the final focused rerun), followed by the full frontend suite
  (235 tests across 26 files); lint, formatting, TypeScript, production build and `git diff --check`
  passed. The build retains 39 lazy JavaScript chunks, 761,743 raw JS bytes total (1,396 above the
  preceding Dashboard pass), largest chunk 208,532 bytes (298 above), and 114,488 raw CSS bytes
  (891 above), without a Vite size advisory. No dependency, eager route/map loading, backend, API,
  schema or migration changed. This review boundary remains unstaged and uncommitted; the canonical
  `make feature-verify` gate is reserved for the later authorized phase.

## 2026-09-28 — Dashboard and sidebar-brand review pass

- On `fix/release-ui-polish`, gave the existing serif sidebar wordmark a dedicated block with aligned
  left padding, a restrained divider and normal letter spacing. Live inspection caught inherited
  negative heading letter spacing that had visually compressed the brand; the corrected wordmark is
  fully readable without widening the sidebar. The account footer and compact shell remain in place.
- Dashboard keeps its existing search, filters, four holding counts, Event data and four actions.
  Below the compact snapshot, Recent activity occupies the primary desktop column and Quick actions
  sits in a compact secondary panel. The activity list alone scrolls beneath its persistent heading
  and View all Events link. Compact Event rows align kind/date, record/badge and botanical context;
  internal links use the Florabase green for normal and visited states, with visible keyboard focus.
  Count links now announce their label and value clearly to assistive technology.
- The populated disposable preview was inspected at 1440 × 844, 1024 × 844 and 390 × 844. Both
  desktop widths had no document or horizontal overflow; activity scrolls within its column. At
  1024, search moves below the heading to preserve a usable width while the two columns remain.
  Mobile presents header, search, 2 × 2 snapshot, actions and activity in order, with natural page
  scrolling and no nested activity scroll pane. The preview was removed after review.
- Focused Dashboard/shell tests passed (58), full frontend tests passed (233), and frontend lint,
  formatting, TypeScript and final production build passed. The build retains 39 lazy JavaScript
  chunks, totaling 760,347 raw bytes (156 above the previous polish receipt); largest is 208,234
  bytes (26 above). CSS totals 113,597 raw bytes including the existing Labels stylesheet, with no
  Vite size advisory. No dependency, API, backend, schema or migration changed. The Dashboard visual
  direction awaits operator review; this pass remains unstaged and uncommitted.

## 2026-09-28 — final pre-release UI polish for visual review

- Kept the frozen 0.1.0 product scope and current `fix/release-ui-polish` branch. The full-height
  sidebar now carries brand, account and Sign out; the main masthead is gone. Shared compact headers
  and flex/grid workspace sizing replace viewport subtraction heights on desktop. Seeds, Sowings,
  Plants, Events, Botanical identities, Suppliers, Locations, Geography hierarchy and provenance
  sites use their result region as the principal scroll surface. Dashboard's activity list takes
  the remaining space. Mobile retains its navigation and natural document scrolling.
- Suppliers use compact list rows with direct-record context. Geography now exposes Places,
  Provenance sites and Map as peer views, retaining the stored-coordinate map and accessible
  companion list. Labels retain the approved A4 print geometry and temporary state while showing
  remaining sheet capacity and keeping the record picker visible during desktop composition.
- No domain, API, schema, migration, authentication, photo, map-provider or persistence contract
  changed. PERF-001 route and optional-map lazy loading remains in place. Browser review used the
  guarded disposable populated fixture at 1440 × 844, 1024 × 844 and 390 × 844; directory, timeline,
  hierarchy, selection, search and mobile scroll ownership were inspected without changing operator
  data. The fixture was removed after review. Empty and loading states, long botanical names, label
  copies and removal remain covered by focused component tests; physical label geometry was unchanged.
- Focused frontend checks passed: 81 App/Labels cases on the final code. `make check` passed backend and
  frontend formatting, lint and type checks, 425 backend unit tests, 232 frontend tests, and API
  drift. The existing pytest-cov 89.82% warning still prints against a whole-percent 90% setting,
  while pytest and the canonical `make check` exit successfully as explained in PERF-001.
  `pnpm build`, feature graph validation (81 features), and whitespace checks passed. The production build
  retains 39 JavaScript chunks: 760,191 raw bytes total versus PERF-001's 759,387; largest chunk
  208,208 versus 207,746 bytes, with no Vite size advisory. CSS grows to 110,231 raw bytes from the
  documented 100,981 because the shared viewport layouts are new. No dependency or eager route/map
  loading was added. Independent visual review remains before any release-hardening work.

## 2026-09-27 — PERF-001 implemented for independent review

- Preserved the untouched `d5a9da5` baseline, frozen protocol and comparison evidence in
  [PERF-001 report](performance/PERF-001.md), `baseline.json` and `after.json`. The guarded disposable
  `florabase-perf` project reuses production runtime images/topology with tmpfs PostgreSQL/media,
  loopback preview-style cookies and deterministic personal-collection data. Operator stacks/data
  were preserved; measurements ran separately from checks/builds. Maps use explicit deterministic
  browser responses; three separate live summary probes returned 200 with no eligible fixture data.
- Measured hotspots justified response-local geography maps, distinct-site serialization and reused
  loaded geography in SeedLot/Plant/PlantGroup responses, native lazy workspaces/wizards with loading
  and download-failure recovery, and public-static nginx gzip. API/schema/security/privacy/domain
  contracts and Vite advisory threshold remain unchanged; no index, migration, broad cache or pool
  tuning was justified. Alembic remains `20260925_0026`.
- Identical 28-read workloads retain seven repetitions, median/range, first-call timing, payload
  sizes and SQL counts; first comparison, warmed repeat and final repeat are all retained. Initial
  browser JS/CSS is 691,307→117,364 bytes (~83% less); initial requests 9→18; largest chunk 207,746
  bytes with no large-chunk advisory. Total all-workspace JS grows ~1.6% raw/~13% independently gzipped.
  Final SeedLot/Geography/Plant medians are 46.0/15.4/47.2ms versus 122.3/64.2/82.8ms baseline, but
  unchanged controls also become faster, so not all timing improvement is attributed to the fixes.
  SeedLot/Plant query counts drop 11→10; exact captured EXPLAIN plans did not justify new indexes.
- Final browser run has no errors, six cycles of 53 requests, stable DOM/listeners, no Dashboard maps
  or timers, and 122s idle with zero requests, unchanged session timestamps and five idle database
  connections. Runtime container memory settles around 298MiB with this tmpfs fixture; the report
  records health-check CPU, image/process/startup costs and no unsupported hardware guarantee.
  Thumbnail/original transfers, local Photos laziness and external opt-in remain intact. Larger full
  directories, provider/network latency and all-workspace chunk overhead remain documented costs.
- Regression coverage adds hierarchy reuse/integrity tests, three PostgreSQL query-count tests at
  1/20 records, workspace deferral/module reuse and failed-chunk recovery, and four benchmark safety
  guards. Focused runs: 36 backend, 54 frontend and 3 PostgreSQL cases passed. Existing UI assertions
  now await lazy-route readiness without weakening their assertions or timeouts.
- Final serial `make check` exits 0: formatting, Ruff, zero-warning ESLint, strict mypy (215 files),
  TypeScript, 425 backend unit tests, 230 frontend tests (25 files), and API drift check. **Coverage
  caveat:** pytest reports 89.82% against the configured 90% and prints a failure message while the
  command continues successfully. Independent review confirmed coverage.py defaults to 0-digit
  precision, so `round(89.82, 0)` meets the configured whole-percent 90% gate; pytest-cov separately
  prints a red unrounded warning without changing pytest's exit status. The message is misleading;
  threshold and precision remain unchanged.
  `make test-integration`: 357 passed/425 deselected/118 warnings in 132.97s. Production runtime build,
  actual static gzip/protected-response integrity, helper safety/lint/format/syntax checks and feature
  graph validation pass. Host Python 3.12 lacks existing `uuid7`; successful checks use Docker 3.14.7.
  An interrupted high-memory-pressure run was replaced with complete serial runs, not counted as proof.
- Independent final review found and corrected two narrow defects: a workspace error boundary that
  could mask unrelated lazy-module failures, and duplicate `/healthz` Content-Type headers. Recovery
  now recognizes only dynamic-import fetch/MIME `TypeError`s; a rebuilt Chromium run against the real
  hidden Seeds chunk showed the SPA fallback, recovery UI and retained authenticated shell without a
  document reload. Fresh production responses reproduced 10 SeedLot/Plant and 6 PlantGroup query
  counts; gzip/Vary, identity fallback, no-store runtime config, uncompressed protected API and the
  corrected plain-text health response all passed. The reviewed source/image identities and measured
  response details are in `after.json` and this report.
- Independent final `make feature-verify` passed all stages: quality, 425 backend unit tests, 232
  frontend tests, 357 PostgreSQL integration tests, generated API drift, production build, feature
  graph and migration checks. The 89.82% coverage line still prints pytest-cov's misleading warning,
  but the configured zero-precision 90% gate passes and the canonical command exits 0. PERF-001 is
  now `verified`; no staging, commit, push, delivery, merge, branch switch or finish was performed.
  RELEASE-001 should repeat the documented sanity workload on the exact candidate, real target
  hardware/persistent storage and HTTPS, alongside security/mobile/keyboard/installation/recovery.

## 2026-09-27 — LABEL-001 implemented for operator physical/visual review

- Added a temporary authenticated Labels workspace and secondary Print label detail actions for
  SeedLot, Plant, and PlantGroup. Reused the searchable ReferencePicker and existing protected record
  APIs; add/remove, copy counts, empty/retry/error states, keyboard operation, and responsive preview
  prepare one fresh A4 sheet of up to 36 labels. No persistence, migration, API change, numbering,
  photo loading, public record page, or server PDF service was introduced.
- Labels show the existing BotanicalIdentity display name, record type, optional existing record
  label, Florabase, and locally generated SVG QR. QR payloads contain only existing detail routes
  and validated UUIDs; login and authorization remain unchanged. Pinned the small
  dependency-free MIT `qrcode-generator` 2.0.4 and distributed its license notice with frontend assets.
- Fixed physical border-box cells are 50 × 30 mm, with a 22 mm QR and four-module quiet zone.
  Named A4 print CSS gives 4 × 9 cells, a 200 × 270 mm grid, 5 mm horizontal/13.5 mm vertical margins,
  no gutters, no scaling, no split labels, and only sheet output. Operator instructions require
  100% / Actual size and no Fit to page.
- Chromium fixture review covered empty/one/mixed/duplicate/long/cultivar/partial-name states at
  1440 × 844, 1024 × 844, and 390 × 844 with no page overflow or external requests. Print media
  measured all 36 cells at 188.96875 × 113.375 CSS px with no transform/zoom; ordinary print-to-PDF
  produced one A4 page. An independent decoder recovered all distinct exact record URLs from SVG
  rasterization and from 300 dpi crops of the actual printed PDF. Physical printer/system-dialog
  validation remains with the operator.

## 2026-09-27 — LABEL-001 independent final review

- Review found that the QR origin was browser-derived. QR generation now uses the existing
  `FLORABASE_CANONICAL_ORIGIN`, returned by the authenticated session API, so proxy/browser aliases
  cannot change a durable printed URL. Development produces the configured `http://localhost:5173`
  origin and production uses its configured HTTPS domain. Credential-bearing canonical origins are
  rejected. The additive authenticated-session response field is reflected in generated OpenAPI and
  frontend types; no endpoint, setting, migration, or public lookup behavior was added.
- Added regression coverage for canonical development and production URLs, browser-origin
  independence, invalid origins, and configured session output. The independent browser reached the
  sign-in screen; authenticated UI and print media were not visually re-reviewed without credentials.
  Operator reports functional UAT complete. Physical printer/system-dialog validation remains open.
- `make feature-verify` passed on the final LABEL-001 review tree: feature graph, formatting, lint,
  mypy, TypeScript, 423 backend unit tests, 228 frontend tests, API drift, 354 PostgreSQL integration
  tests, production builds, migration cycle (no new revision), whitespace check, and verification
  receipt. Backend coverage reported 89.77% against the nominal 90% threshold while the canonical
  gate succeeded, consistent with the existing rounding behavior. LABEL-001 is now `verified` in
  `features.json`; all changes remain unstaged and uncommitted. Physical printer/system-dialog checks
  remain open.
- Checks passed: 20 focused label cases; broad `make check` (422 backend unit and 220 frontend tests,
  Ruff, strict mypy, Prettier, ESLint, TypeScript, generated API drift); 354 isolated PostgreSQL tests
  including three new protected lookup/error cases; production frontend image; feature graph (81),
  diff whitespace, and same-origin health/readiness. The unchanged 89.75% coverage summary/rounded
  exit-status discrepancy documented for ATTACHMENT-004, Alembic warnings, and Vite chunk advisory
  remain. See [implementation review](label-001-review.md) and [operator guide](labels.md).
- LABEL-001 is `implemented`, not `verified`. All changes remain unstaged and uncommitted;
  independent `make feature-verify`, final commit, and delivery were intentionally reserved.

## 2026-09-26 — ATTACHMENT-004 implemented; operator visual review passed

- Added Alembic revision `20260925_0026` and a separate UUIDv7 `CollectionPrimaryPhoto` table with
  exactly one supported target/source and unique target/source constraints. No primary is inferred
  on migration, upload, or deletion. Selection locks the concrete target, existing photo, and local
  Attachment, validates exact ownership and active/presentable content, and changes designation only.
  Supported targets are SeedLot, Plant, and PlantGroup; Sowing and Event Photos and BotanicalIdentity
  reference covers remain separate.
- Added protected typed primary read/set/clear operations and a fixed authenticated local-photo
  WebP thumbnail using the existing safe decode/orientation mechanics, trusted storage resolver,
  320px maximum edge, no upscale, private digest/version ETag, and no persisted derivative. Directory
  response builders batch only compact primary summaries, without per-row metadata/gallery requests.
  External primaries render a neutral indicator and retain the gallery's explicit remote-load choice.
- Local deletion clears designation in the first pending-delete transaction, including failed-unlink
  retry behavior. External deletion clears it in the same metadata transaction; defensive source FK
  cascades guard final cleanup. Primary changes and metadata edits preserve gallery history/order.
  Photos actions update the mounted detail and directory state coherently.
- Browser review used an isolated disposable fixture for A–J: absent photos, one unselected photo,
  selected local primary, change, clear, selected-local deletion, Plant, PlantGroup, external primary,
  and excluded Sowing Photos. Reviewed representative directory/detail/gallery layouts at 1440px,
  1024px, and 390×844, including mobile action reachability and no page overflow. External views had
  no remote image element before explicit loading; a full Network-panel capture was not available.
  Selected-local browser deletion used the protected API followed by a browser refresh; focused UI
  tests cover authoritative designation refresh after photo removal. This is implementation fixture
  review, not operator UAT.
- Focused checks passed: 13 collection-photo backend unit tests; 19 PostgreSQL attachment/photo/API
  and migration integration tests, including upgrade/downgrade/re-upgrade preserving all existing
  Attachment, local/external photo, and BotanicalIdentity-cover metadata; 50 SeedLot/Plant unit and
  88 directory/detail API integration tests; 39 existing SeedLot/Plant screen tests and 11
  photo/primary frontend tests; Ruff formatting/lint and strict mypy; frontend
  Prettier/ESLint/TypeScript; backend production image and frontend production build; generated
  OpenAPI and frontend schema drift. Alembic emits its existing `path_separator` deprecation warning;
  Vite retains its existing large-chunk warning. Feature graph and final diff checks complete the
  handoff. See [implementation handoff](attachment-004-review.md) for exact commands and boundaries.
- ATTACHMENT-004 is `implemented`, not `verified`. Independent QA, `make feature-verify`, and the
  final local commit remain for Luna. No staging, commit, delivery, or production database migration
  was performed.

## 2026-09-27 — ATTACHMENT-004 independent QA

- Fixed the designation deletion/replacement race by locking the designation row during replacement;
  added a PostgreSQL concurrency regression test. Updated the integration assertions for migration
  head `20260925_0026` and the new table.
- Added focused unit coverage for selection and thumbnail route contracts. The canonical
  `make feature-verify` passed: 422 backend unit tests, 197 frontend tests, 351 PostgreSQL tests,
  production builds, generated API drift, and migration cycle `0025 → 0026 → 0025 → 0026`.
- The independent QA browser tool could not access the local review app. The operator subsequently
  completed the manual viewport and lifecycle review and reported a pass. Final review found the
  coverage display inconsistency documented in `attachment-004-review.md`; no coverage policy was
  changed.

## 2026-09-25 — GERMINATION-001 implemented for operator visual review

- Added Alembic revision `20260925_0025` for exact-day, non-negative incremental germination
  observations, with one row per Sowing/date and a restrictive Sowing foreign key. Observation
  mutations and Sowing edits lock the Sowing row before validating the independent cumulative total
  against an exact seed count. Exact date edits cannot move sowing after an observation. The existing
  operator-maintained `germinated_count` remains independent; corrections do not change lifecycle,
  Events, propagation, or descendants.
- Added protected typed germination detail and observation CRUD APIs. The backend derives chronological
  cumulative counts, first positive observation, elapsed days where the Sowing date is exact,
  exact-seed percentage, and decimal T50 from half the exact seeds sown using linear interpolation.
  Missing date/denominator/threshold inputs return absent values rather than fabricated metrics.
  Generated OpenAPI and frontend declarations are updated.
- Added a read-first Sowing Germination tab with concise separate totals, missing-data explanations,
  focused add/edit/delete dialogs, and a chronological table that stacks on mobile. A disposable
  browser fixture covered no observations, zero-only and populated history, full metrics,
  approximate quantity, partial date, threshold not reached, edit, delete, and mobile rows at
  1440px, 1024px, and 390×844. This was implementation-level fixture review, not operator UAT.
- Focused checks: 14 backend unit tests; 3 PostgreSQL migration, service and API integration tests;
  Python 3.14 Ruff and mypy; Sowing frontend component tests, Prettier, ESLint, TypeScript, and
  production build; generated OpenAPI drift, feature graph, and diff whitespace checks. The
  independent review, canonical `make feature-verify`, and commit remain for Luna.

## 2026-09-25 — GERMINATION-001 independent QA complete

- Added regression coverage for odd-count T50, baseline and multi-zero interpolation, exact inputs,
  endpoint authentication/CSRF/Origin, chronological insertion order, zero and exact-bound counts,
  CRUD corrections, and Sowing date/quantity edits. A two-session PostgreSQL test confirms one of
  two concurrent writes that exceed the exact seed total is rejected. Updated stale repository
  integration assertions for the new table and Alembic head.
- Independent checks passed: 11 germination unit cases, the Sowing frontend suite (15 tests), and
  the targeted PostgreSQL checks. The full frontend suite passed (190 tests across 21 files).
  Canonical `make feature-verify` passed with 414 backend unit tests and 348 PostgreSQL integration
  tests, including the migration upgrade/downgrade/re-upgrade cycle, generated API drift, frontend
  checks, production builds, and workflow helpers.
- GERMINATION-001 remains `implemented`; the exact verified tree is ready for the requested local
  commit. No production-code correction was required.

## 2026-09-25 — SEARCH-001 independent QA correction

- Corrected Event search context projection to select the BotanicalIdentity belonging to the
  Event's actual Plant or PlantGroup target. Regression coverage confirms both targets, readable
  context when optional labels are absent, unique Event hits, and existing result routes.
- Extended Dashboard QA for actual browser Back/Forward transitions, structured-filter restoration
  after remount, and out-of-order search responses. Search integration coverage also checks
  authentication, record domains, explicit relationships, combined filters, deterministic ordering,
  bounded pages, response privacy, and typed API validation.
- Focused checks passed: 5 PostgreSQL search integration tests, 403 backend unit tests at 90.60%
  coverage (including search API/service and Event tests), 189 frontend tests, 4 focused Dashboard
  search tests, backend Ruff/mypy, frontend Prettier/ESLint/strict TypeScript/build, API drift,
  feature graph, and `git diff --check`. Canonical verification follows on the final reviewed tree.

## 2026-09-25 — SEARCH-001 operator visual correction

- Styled the four existing Dashboard Quick-action links as compact secondary buttons. Their routes,
  normal-state placement, keyboard semantics, and search prominence remain unchanged.
- Tightened grouped search results into a consistent full-width row pattern. Type headings now keep
  counts beside their labels, bounded groups state the loaded and total counts, and repeated title
  context is suppressed. The total sits by the results heading; one lightweight Back to Dashboard
  control also serves the empty state. Collection, Botany, and Reference remain separate.
- Disposable browser fixture review covered normal Dashboard, one and many results, Event, Botany,
  Reference, and empty states at 1440px, 1024px, and 390×844. Quick actions wrapped on mobile; no
  whole-page horizontal overflow appeared. Event kind and target remain visible. Event dates are
  absent from the existing search-result payload and were left unchanged in this presentation-only
  pass.
- Focused frontend Prettier, ESLint, strict TypeScript, 21 component tests, production build, and
  `git diff --check` passed. No backend files changed; the canonical gate remains for later review.

## 2026-09-25 — SEARCH-001 implemented for operator visual review

- Made the authenticated Dashboard the global collection-search entry point without adding a
  navigation destination. Search-active state replaces the snapshot, Quick actions, and activity
  feed; clearing it restores them. Hash query parameters retain text and structured filters across
  refresh and browser history. Normal Dashboard Quick actions now open Add seed lot, Add plant, Add
  plant group, and Import / Export before recent activity. Sowing creation stays on its SeedLot's
  authoritative propagation workflow.
- Added a typed, server-side `/api/v1/search` contract for Collection records (SeedLot, Sowing,
  Plant, PlantGroup, Event), Botany (BotanicalIdentity and separate BotanicalProfile reference
  knowledge), and Reference (Supplier, Location, GeographicPlace, ProvenanceSite). Literal,
  case-insensitive text matching uses persisted labels, notes, identities, and explicit current
  relationships. Filters cover record kind, identity, applicable lifecycle or Event kind, current
  Location and descendants, direct Supplier/place/site, and type-specific recorded year. Results
  sort deterministically and page per kind with exact counts. No schema, index, or migration changed.
- Documented exact search semantics in `docs/search.md`; generated OpenAPI and frontend types; set
  SEARCH-001 to `implemented` pending operator visual review and independent final verification.
  Earlier disposable browser fixture review covered the Dashboard, filters, grouped results, and
  1440px, 1024px, and 390×844 layouts without whole-page horizontal overflow. The fixture was
  presentation-only; focused PostgreSQL tests exercised the live query behavior.
- Focused verification: 15 adjacent backend unit tests, 3 PostgreSQL search integration tests,
  21 Dashboard search and adjacent UX component tests, backend Ruff/mypy, frontend
  Prettier/ESLint/strict TypeScript, generated API drift, production builds, feature graph,
  documentation formatting, and `git diff --check` passed.
  `make feature-verify` remains reserved for the authorized later phase.

## 2026-09-24 — IMPORT-001 independent final review

- Independently reviewed the import contract, signed preview/apply flow, ordinary domain-service
  writes, CSV safety, frontend states, and feature graph. Added database-independent coverage for
  remaining format, reference-choice, export, and API token cases. No implementation defects were
  found; IMPORT-001 remains `implemented` pending delivery.
- `make feature-verify` passed: 393 backend unit tests at 90.41% coverage, all 337 PostgreSQL
  integration tests, 185 frontend tests, generated API drift, production builds, migration checks
  (no revision added), and the feature verification receipt. The final review reruns this gate on
  the complete tree before the local commit.

## 2026-09-24 — IMPORT-001 visual and information hierarchy correction

- Made Import the dominant desktop task with a compact secondary Export panel, a four-step
  Template → Upload → Preview → Import indicator, a grouped template/example/guide tool set, and
  clearer record-type, file, and validation controls. The recommended import order remains visible
  as supporting information. No CSV, API, domain, or preview/apply semantics changed.
- Moved the field guide below the top Import/Export row. A semantic, scroll-contained table keeps
  every field's meaning, requirement, accepted format, example, and notes scannable on wider
  screens; compact separator rows show the same information on mobile. Preview now uses quieter
  filters and row dividers, with Supplier changes compared in Field / Existing / CSV columns.
- Browser fixture review at 1440px, 1024px, and 390x844 covered the initial workspace, Supplier
  guide and update choice, long Seed lot guide, valid Seed lot preview, and invalid Supplier preview.
  No whole-page horizontal overflow appeared. The fixture mocked API responses; prior PostgreSQL
  integration checks covered actual backend behavior. Focused frontend component tests, Prettier,
  ESLint, strict TypeScript, production build, and `git diff --check` passed. No backend checks or
  `make feature-verify` ran in this presentation-only pass.

## 2026-09-24 — IMPORT-001 operator-UAT corrections

- Removed `record_ref` from all six normal import templates. Advanced CSVs may still supply an
  existing UUID explicitly, and exports retain UUID relationships. Preview now shows exact existing
  BotanicalIdentity, Supplier, and Location candidates with explicit Use existing, Update existing
  (current Supplier only), or Create separate choices where the domain permits them. Ambiguous
  relationship names and paths show actual candidate choices. A same-tuple BotanicalIdentity cannot
  be created separately; SeedLot, Plant, and PlantGroup imports remain create-only.
- Supplier Update existing shows a field-level diff and uses the ordinary update service. Blank CSV
  cells retain existing values. Preview stays read-only; signed choices bind to the reviewed bytes,
  session, candidate state, and confirmation time. Apply revalidates, locks Supplier updates, and
  rolls the entire file back on a later failure or stale choice.
- Added shared narrow enum/whitespace normalization with canonical values shown in Preview, clearer
  invalid-value messages, six downloadable valid examples, and a responsive in-app field guide.
  Template headers, examples, and field descriptions come from the same backend CSV contract.
  Updated `docs/import-export.md`; no schema or migration changed. The pre-0.1.0 roadmap selection
  remains unchanged.
- Browser review against a disposable fixture using realistic CSV files covered a new and existing
  identity, a new and existing Supplier, `Nursery` normalization, an invalid Supplier kind, a
  Location, and a Seed lot with readable relationships. At 1440px, 1024px, and 390x844 there was no
  whole-page horizontal overflow. The review corrected the cramped 1024px card layout and radio
  controls that stretched away from their labels. The guide and choice controls remained readable
  on mobile; the example link was visible for every selected type. The fixture mocked API responses;
  the separate PostgreSQL integration tests exercised actual backend Preview and Apply behavior.
- Focused checks: 17 backend unit tests, 13 PostgreSQL integration tests, 3 frontend component
  tests, Ruff formatting/lint, mypy, Prettier/ESLint/TypeScript, generated API drift, production
  frontend and backend image builds, feature graph, and `git diff --check` passed. The canonical
  `make feature-verify` gate remains with the independent final reviewer.

## 2026-09-24 — IMPORT-001 implemented for operator visual review

- Added separate bounded CSV imports for BotanicalIdentity, Supplier, Location, SeedLot, direct-origin
  Plant, and direct-origin PlantGroup. Exact headers, UTF-8/BOM handling, 2 MiB/2,000-row limits,
  schema and reference validation, row-level outcomes, and in-file Location parent keys are
  documented in `docs/import-export.md`. Preview only reads domain records. A 15-minute,
  session-bound confirmation token binds apply to the exact reviewed bytes; apply revalidates and
  commits one file atomically through existing create services. Existing collection records are not
  merged or silently skipped.
- Added authenticated, deterministic CSV export for these types with UUID relationships, readable
  companion labels/paths, partial dates, quantity certainty, lifecycle, and spreadsheet formula
  protection. Export is neither backup nor full-fidelity transfer. Sowing, sowing-origin descendants,
  Events, operation receipts, photos, and direct lineage import remain outside this contract; no
  historical operation receipts are fabricated. No schema or migration changed.
- Added one Import / Export workspace with type selection, template downloads, format help, file
  validation, filtered row-level preview, explicit confirmation, and result/retry states. A
  disposable browser fixture showed the preview and unresolved/invalid rows at 1440px, 1024px, and
  390×844 with no page horizontal overflow. This was UI layout review against a fixture; operator
  UAT on real collection data and the independent canonical gate remain outstanding.
- Recorded the operator's pre-0.1.0 selection of IMPORT-001, SEARCH-001, GERMINATION-001, LABEL-001,
  and planned ATTACHMENT-004. PWA-001, LINEAGE-003, ORDER-001, and DASHBOARD-001 remain post-0.1.0
  by default. IMPORT-001 is `implemented`, not `verified`; ATTACHMENT-004 is `planned` and not built.
- Focused checks passed: 10 backend unit tests, 7 PostgreSQL integration tests, 2 frontend Vitest
  flow, backend Ruff formatting/lint and mypy, frontend Prettier/lint/typecheck and production
  build, generated API drift, feature graph (81 valid features), documentation formatting, and
  `git diff --check`. The existing Vite chunk-size advisory remains. `make feature-verify` was
  intentionally reserved for independent final review after operator UAT.

## 2026-09-24 — approved 0.1.0 release boundary and resource phase recorded for review

- Added planned P0 `PERF-001` with dependencies on UX-006 and MAP-002. It requires a reproducible
  production-like resource baseline over idle and representative collection workflows, focused
  optimization of demonstrated backend, database, frontend, media, map, Docker, and long-running
  hotspots, then repeat measurement and documented modest self-hosting expectations. UX-006 supplies
  the redesigned collection and provenance-map path; MAP-002 directly supplies the occurrence-map
  path outside UX-006's dependency closure. No resource target is invented before measurement.
- Added planned P0 `RELEASE-001` with focused dependencies on UX-006, ATTACHMENT-002, CI-002, and
  PERF-001. Its acceptance contract covers production installation and upgrade, complete
  database-plus-media recovery, end-to-end collection UAT, security and failure review,
  responsive/accessibility review, final release-candidate resource sanity against PERF-001 results,
  accurate operator documentation, version policy, and first changelog entry. No optional product
  candidate became a dependency of either required increment; `BOTANY-003` remains planned and is
  explicitly post-0.1.0 under the current provider-content constraint.
- Replaced stale roadmap release sequencing with required, optional, and post-release boundaries.
  Corrected current-state UX review prose and the README/deployment claims that collection photos,
  contextual help, and attachment storage were absent or that a database-only backup was sufficient.
  No application behavior, schema, API, or release tooling changed. The operator still needs to
  select any optional pre-release work and, during `RELEASE-001`, settle supported upgrade/version
  expectations, licensing, and the first changelog entry.
- Focused checks: `python3 -m json.tool docs/features.json`, `python3 scripts/check-features.py`
  (80 valid features), priority/category and required-dependency assertions, changed-document
  internal-link checks, Prettier on changed Markdown/JSON, and `git diff --check` passed. The
  canonical application gate is reserved for independent review of this documentation-only graph
  change.

## 2026-09-24 — UX-006 independently reviewed and ready for delivery

- Audited the merged UX-004/UX-005 directory, preview, detail, task, help and responsive patterns against SeedLot, Sowing, Plant/PlantGroup, propagation, Events, Photos, Lineage and Dashboard. The operational directories mixed selection with nearly full detail, large editors competed with browsing, and repeated borders and permanent explanations obscured the record and next action.
- Seed lots, Sowings and Plants/Groups now share polished search, compact record-first rows, lifecycle/type filters, selected and focus states, a compact Quick Preview and dedicated read-first detail. Large create/edit forms open as explicit tasks with grouped core and optional fields; desktop and mobile use the same record routes, including Back/Forward and direct links. Existing quantity certainty, partial dates, source, provenance, lifecycle and explicit lineage rules remain intact.
- Dashboard now shows linked collection holdings, recent recorded Events and valid quick actions. Global Events uses a chronological activity view with compact category filters and contextual non-replay guidance. Propagation and Plant operation surfaces clarify next actions, source/result/quantity effects, receipt-dependent reversal and reintegration, while Photos and Lineage use the shared restrained presentation and retain their existing privacy and relationship boundaries.
- Browser inspection with existing representative records covered populated Dashboard, SeedLot/Sowing/Plant/Group browsing and detail, Events, Photos, Lineage, creation and extraction at 1440px, 1024px and 390×844. Review corrected extraction Cancel focus restoration, type-specific unlabelled-record fallbacks, a repeat-selection loading defect, narrow Plant-detail overflow, raw origin ID and compact desktop header wrap. No operator records were changed. The operator has accepted the general design direction; minor polish in historical and receipt-edge presentation is deferred to final cross-app UAT.
- Added UX-006 as `implemented` in the feature graph and aligned the roadmap. No backend, API, generated declaration, schema, migration, dependency or persistence change was made. Focused verification passed: 78 tests across six Vitest files, with all 23 Plant cases rerun after the final focus and label corrections; `pnpm format:check`, `pnpm lint`, `pnpm typecheck`, `pnpm build`, `python3 scripts/check-features.py` (78 valid features), and `git diff --check`. `make feature-verify` passed: 358 backend tests, 182 frontend tests, integration suite, generated API drift, type/lint/format checks, production builds, migration cycle, whitespace checks and verification receipt. Vite retained its chunk-size advisory. UX-006 remains `implemented` pending delivery workflow.

## 2026-09-23 — UX-005 independent review

- The operator accepted the general design direction and deferred minor visual refinements. Independent review confirmed the UX-005-only frontend/documentation scope, preserved explicit provenance and hierarchy semantics, lazy maps, and no backend, generated API, schema, migration, or dependency changes. UX-005 remains `implemented`; no UX-006 record was added.
- Corrected two data/error edge cases in the site and place inspectors: zero accuracy now displays, local places with a null type are not labeled canonical, and non-conflict delete failures no longer claim a relationship conflict. Pending site/place saves now disable their form controls. Shared dialog and menu focus-return regressions were strengthened.

## 2026-09-23 — UX-005 operator UAT corrections ready for visual review

- Fixed the shared dialog flash-close defect: React StrictMode effect replay closed the native dialog during cleanup, and its queued `close` event dismissed the newly reopened state. TaskDialog now handles intentional native cancellation without treating programmatic cleanup as user dismissal. The shared OverflowMenu now dismisses on outside pointer/focus, Escape, action selection and opening a peer, with listener cleanup and focus return. Focused StrictMode and menu regressions cover repeated open/close, focus trapping and outside interaction.
- Location filtering auto-reveals matching descendants and ancestors while preserving manual collapse/reopen for the current filter; a changed filter recomputes the initial expansion, and clearing it restores the unfiltered tree. Location, Supplier, Geographic Place and Provenance Site details now use compact read-first headers, structured relationships, usage figures and record lists; rare actions remain in More. A shared directory search and selected-row treatment bring Supplier, Location and Geography closer to BotanicalIdentity, whose selected card is now visibly distinct from focus and hover.
- Browser UAT with representative data inspected Supplier, Location, Geography, Provenance sites and BotanicalIdentity across 1440px, 1024px and 390×844: dialogs remained open until dismissed, menu outside-click worked, filtered branches stayed manually collapsed, linked material remained readable, mobile action rows aligned, and no horizontal overflow was found. The temporary browser fixture was removed. Focused verification: 63 tests across four Vitest files, followed by 53 App tests on the final handler edit; `pnpm lint`, `pnpm typecheck`, `pnpm format:check`, `pnpm build`, and `git diff --check` passed. Vite retained its chunk-size advisory. The operator has accepted the general design direction; minor visual refinements are deferred. The independent review and canonical verification follow this UAT milestone.

## 2026-09-23 — UX-005 implemented for operator visual review

- Audited UX-004's merged BotanicalIdentity patterns and the existing Supplier, Location, Geography, Provenance-site and collection-map workflows. The old surfaces mixed selection with full editing, showed permanent forms and repeated bordered panels, while the map competed with its list. Kept their recorded relationships, hierarchy, route meanings and loading/error behavior.
- Separated Supplier directory, compact list-backed Quick Preview and hash-routed detail. Detail reads contact, notes, recent acquisitions and directly linked material before editing; create and edit use a shared accessible dialog, and retirement stays in More.
- Recast Location as a hierarchy browser with search over names and paths, explicit usage-scope filtering, ancestor context, compact preview and dedicated read-first detail. Multiple roots, arbitrary depth, child creation, lifecycle and guarded edits/deletion keep the existing backend semantics.
- Organized Geography into Browse (Places and Provenance sites) and Map. The place browser distinguishes immutable canonical nodes from editable local nodes. Site browse keeps coordinate-less records visible; map mode lazily loads Leaflet for stored coordinate pairs only, with synchronized marker, list and site inspector. Place and site forms open on explicit create/edit intent.
- Made the separate collection provenance map the main surface with a companion site list and selected direct-record inspector. Its filters, direct-only record associations, markers, attribution and backend contract remain unchanged. Shared UX-004 PageHeader, QuickPreview, DetailHeader, StatStrip, Breadcrumbs and OverflowMenu vocabulary was reused; the small TaskDialog primitive supplies modal focus, Escape, Cancel and focus return.
- Reviewed representative data in the browser at 1440px, 1024px and 390×844 across directory, detail, hierarchy, browse/map, selected records and dialogs. Corrected row density, mobile tree alignment, page chrome and map layout; checked that no horizontal overflow remained. The temporary fixture was removed. The operator's final visual acceptance remains outstanding.
- Added UX-005 as `implemented` in `features.json`, updated the roadmap's scoped handoff, and corrected stale `docs/progress.md` current-state statuses against the feature registry. No backend, API, schema or migration change was made. Focused verification: `pnpm exec vitest run --configLoader runner src/App.test.tsx src/provenance-sites/ProvenanceSiteManager.test.tsx src/provenance-map/ProvenanceMapScreen.test.tsx` (60 passed); `pnpm lint`, `pnpm typecheck`, `pnpm format:check`, `pnpm build`, `git diff --check`, and feature-registry JSON validation passed. The production build retained Vite's chunk-size advisory; the map remains a separate lazy chunk. `make feature-verify` is reserved for independent final review after operator acceptance.

## 2026-09-22 — UX-004 operator-accepted reference ready for delivery

- Tightened the BotanicalIdentity directory into catalog rows with a polished search control and
  small collection context. The directory itself is the bounded scrolling region beside a compact,
  non-sticky Quick Preview; the page heading remains in a stable catalog frame. The navigation sits
  within a continuous full-height green column. Creation now uses a focused modal with trapped
  keyboard focus, Escape, validation retention and trigger restoration instead of expanding the page.
- Limited the rich cover-and-summary row to Overview and contained its representative image at the
  requested compact scale. Collection, Reference and Events use a shorter work header containing the
  identity context and the same Add/Edit/More hierarchy, so task content starts sooner at desktop,
  compact desktop and mobile widths.
- Simplified Overview to record dates and recent activity without repeating summary counts or names.
  Collection now distinguishes its segmented inner navigation from the main tabs and separates next
  actions from records, especially a source-seed-lot sowing launcher followed by a separate Recorded
  sowings section. Human-facing Seed lot, Sowing, Plant and Plant group wording replaces backend-style
  labels on the touched reference surfaces.
- Made Reference read-first and split it into Profile, Native range, Botanical source and Occurrences
  modules, with only the chosen module mounted. Profile fields render as a dossier until Add/Edit;
  Save and Cancel return to read mode. Native-range controls appear only after Manage, provider
  change/unlink actions live in anchored, Escape-closing More menus, and occurrence evidence remains
  an explicit load with its semantics and privacy detail behind accessible disclosures. Raw cover
  URLs and routine successful backend status no longer appear in the botanical UI. Trigger focus is
  restored across profile and native-range mode changes.
- Corrected the visible GBIF taxon action to `/taxon/{opaqueId}` without changing provider APIs,
  tightened cover credit to Photo / Source / Licence, and recorded possible occurrence caching plus
  post-0.1.0 operator-triggered botanical retrieval as contract-dependent future work only.
- Added the nullable stored external cover URL to the existing single-query directory projection.
  Configured external covers now render immediately in cards and Quick Preview without selection or
  per-record requests, using lazy loading, asynchronous decoding and no-referrer browser requests.
  Visible cards can contact their configured external hosts; Florabase still does not proxy, cache,
  discover or choose an external image. Local cards retain the authenticated thumbnail route and all
  broken or missing images retain the botanical fallback.
- Browser inspection used a temporary local representative-data fixture, removed afterward. It
  covered the 21-record bounded directory, creation dialog and focus restoration, local/external/
  no-cover states, long names, Quick Preview, Overview density, compact work headers, Collection
  subsections, all four Reference modules, native-range form, exact GBIF link and provider menu at
  1440px, 1024px and 390×844. The mobile image stays within 256px, fixed navigation leaves enough
  scroll clearance for provider actions, the continuous shell holds, and no horizontal overflow or
  browser console warning/error appeared.
- The independent review aligned the roadmap and reference guide with accepted operator behavior,
  narrowed mobile scroll spacing to BotanicalIdentity detail, and corrected the remaining user-facing
  Plant group and transfer terminology. No persistence, migration, dependency, unrelated screen redesign,
  occurrence cache, or botanical enrichment was added. UX-004 remains `implemented`; minor aesthetic
  refinements are deferred to later increments.
- Final `make feature-verify` passed on the reviewed tree: 358 backend unit tests at 90.18% coverage,
  171 frontend tests, 324 disposable PostgreSQL integration tests, workflow/feature helpers, format,
  lint, typing, generated API drift, production build, migration-cycle check (no Alembic revisions),
  whitespace validation and a recorded verification receipt. No unresolved technical or product
  contract issues remain; minor visual refinements stay deferred to later scoped increments.

## 2026-09-19 — UX-004 implemented; operator visual review required

- Audited global styling and the BotanicalIdentity directory/detail mixture. Added a restrained
  paper/green/sage vocabulary, spacing and radius tokens, editorial names, integrated image cards,
  a small shared PageHeader/QuickPreview/StatStrip/FormSection/FormActions set, and limited shell
  polish. Other entity screens and maps keep their structure; visible Transfer, GBIF taxon and
  Provenance site terminology is corrected without domain changes.
- Separated searchable directory, compact desktop preview and dedicated hash-routed detail. Preview
  uses only list metadata. Below 68rem cards open details directly; existing deep links select the
  new Overview / Collection / Reference / Events navigation and Seeds / Sowings / Plants subviews.
  Cover management is secondary within the hero. Existing profile/native-range/provider, cover,
  collection creation, history, guarded delete and contextual-help behaviors remain available.
- Added active record counts to the existing directory response through one grouped SQL query;
  independent aggregates prevent multiplication and per-record fetches. Generated OpenAPI and
  TypeScript declarations are updated. Directory/preview retain bounded local thumbnails and
  external-cover placeholders; Reference and occurrence-map lazy boundaries remain intact. No
  migration, domain model, framework, telemetry or remote visual dependency was added.
- Focused verification covers directory image privacy, selection versus keyboard focus, compact
  preview requests, detail routes and back/forward, legacy subsections, lazy Reference, mobile
  navigation, form grouping/help/validation, cover and guarded edit/delete behavior. Added a
  PostgreSQL regression for exact active counts, empty identities and a single directory query.
  Final canonical gate: `make feature-verify`; its working-tree receipt records successful checks.
- Browser layout checks used the actual application components with temporary mocked data at
  1440px, 1024px and 390×844, including mobile detail/Reference forms and a long unbroken scientific
  name. No horizontal overflow was observed. Temporary fixture files were removed; the real app
  remains behind owner login. These checks do not replace operator review of actual collection data.
- At that milestone, the next checkpoint was `OPERATOR_VISUAL_REVIEW` on desktop and mobile. The
  operator accepted the direction on 2026-09-22; remaining entity redesign and release hardening stay
  deferred to their own increments. UX-004 remains `implemented`.

## 2026-09-19 — UX-002 implemented

- Audited current create/edit forms and guided propagation, Event, transfer, extraction,
  reintegration, reversal, reference-selection, profile, provenance, and cover-image workflows after
  UX-003. Kept self-explanatory names, labels, contact fields, Notes, and ordinary actions free of
  extra help chrome while targeting domain boundaries that can change an operator's answer.
- Added one local layered-help system: concise inline text uses `aria-describedby`; expandable
  examples use named keyboard/touch buttons and semantic regions with Escape focus restoration; and
  focused modal help traps focus, closes with Escape, and returns focus for genuinely complex
  creation reversal semantics. The layout remains inline and full-width on narrow screens rather
  than using hover bubbles.
- Covered exact/approximate/unknown quantity, count-versus-weight, partial-date precision, current
  collection Location versus biological provenance, Supplier versus origin, shared botanical
  identity versus lineage, one-packet-per-SeedLot identity, Plant versus PlantGroup tracking, Event
  journal versus state-changing creation behavior, native range versus material provenance,
  external-image credit/licence metadata, and reversible-operation consequences.
- Added focused interaction and integration coverage for help/error description composition,
  keyboard activation, screen-reader names and regions, Escape/focus behavior, deliberate absence
  of help on Notes, existing form submission, and the affected SeedLot, Sowing, Plant/Event, and
  reversal workflows. Frontend type checking and linting pass; 60 focused tests pass. Canonical
  `make feature-verify` passes all 357 backend tests at 90.09% coverage, 159 frontend tests, and 323
  disposable PostgreSQL integration tests, plus feature/workflow checks, formatting, linting, strict
  typing, generated API drift, production builds, and whitespace checks. It detects no added Alembic
  revision. No API, generated contract, backend, persistence, or telemetry changed; UX-002 remains
  `implemented` pending independent review and release UAT.

## 2026-09-14 — UX-003 implemented

- Audited the complete collection workflow after maps, photos, transfer, propagation, and reversal
  work. Standardized desktop navigation in `Seeds → Sowings → Plants → Events` lifecycle order and
  kept the five-item mobile bar focused on Home, Seeds, Sowings, Plants, and an accessible More menu
  that leads with Events and preserves the secondary identity, map, and reference destinations.
- Made major collection lists lead with each record's own label and use BotanicalIdentity as
  supporting context. Detail headers now surface the natural next operation—add a SeedLot, start a
  Sowing, create a Plant/PlantGroup, extract, or transfer—before correction controls, while rare
  reversal and destructive actions remain separated. Stored BotanicalIdentity, source SeedLot or
  Sowing, original PlantGroup, Location, Supplier, provenance, and Event relationships gained direct
  navigation without inferring lineage from shared identity.
- Restructured BotanicalIdentity into Overview, Reference, Seeds, Sowings, Plants, and Events. Cover
  and collection summaries remain in Overview; profile, structured native range, and advisory
  external occurrence evidence share a distinct Reference surface. Hidden reference/collection
  panels no longer cause unnecessary eager requests, occurrence maps remain explicit-load, and
  external covers are not requested by compact directory views.
- Added a fixed-purpose authenticated local-cover thumbnail endpoint. It decodes the validated local
  cover under Pillow's bounds, applies orientation, preserves aspect ratio, never upscales, and emits
  WebP with a maximum 320-pixel edge. Private caching uses an ETag derived from attachment SHA-256
  and the transform version; conditional requests can return 304 before decoding. The endpoint does
  not expose storage paths, persist derivatives, proxy external images, or provide generic resize
  controls. Directory rows use this endpoint for local covers, a neutral external-cover indicator,
  and a clean no-cover fallback.
- Completed consistent tab-to-panel ARIA relationships, semantic panels, record-first headings,
  linked status/context fields, wrapping action groups, and deep-linkable Location selection.
  Collection-wide Events explicitly remain journal history whose ordinary edits/deletes do not
  recompute current state.
- Focused verification covers thumbnail dimensions, format, authentication, ownership behavior,
  private validators and 304 handling, external/missing cover behavior, absence of a generic resize
  route, navigation/action hierarchy, lifecycle cross-links, mobile structure, tab semantics, lazy
  reference loading, and existing Plant/Sowing flows. Canonical verification evidence is recorded by
  `make feature-verify`; UX-003 remains `implemented` pending independent review and final browser
  UAT.

## 2026-09-14 — ATTACHMENT-003 implemented

- Added revision `20260913_0024` with separate `LocalCollectionPhoto`, `ExternalImageReference`, and
  `BotanicalIdentityCoverImage` tables. Collection photos retain exactly one explicit target among
  SeedLot, Sowing, Plant, PlantGroup, and Event. The separate cover row has one unique
  BotanicalIdentity, exactly one local/external source mode, unique local Attachment ownership, and
  HTTPS/attribution constraints. A transaction-locked database guard prevents one Attachment from
  being a collection photo and identity cover simultaneously; populated photo or cover metadata
  blocks downgrade.
- Added authenticated target-scoped listing and owner/CSRF-protected upload, create, metadata-edit,
  and remove APIs. Local upload reuses ATTACHMENT-002 validation/storage and coordinates Attachment
  plus relationship persistence with cleanup on relation failure. Local removal preserves
  `active → pending_delete → unlink → relationship/Attachment deletion`, leaving failed or missing
  content as a hidden retry-only relationship. Direct Attachment deletion and Event hard deletion
  are blocked while a photo owns or references them; historical targets still accept photos.
- Added a reusable responsive Photos section to SeedLot, Sowing, Plant, and PlantGroup details and a
  focused Event-history dialog. Galleries distinguish uploaded content from external references,
  order by creation time then ID, cover empty/loading/broken/mutation states, and use caption-based
  or record-context alt text. External images show attribution and source host without loading,
  require an explicit privacy-disclosed browser action, send no referrer, and are never fetched by
  the backend.
- Added a conservative current cover to BotanicalIdentity details with local upload or attributed
  external HTTPS metadata, explicit external-host privacy acknowledgement, automatic no-referrer
  rendering after opt-in, and accessible replace/remove flows. Local replacement/removal composes
  with ATTACHMENT-002 pending-delete retries; external changes are metadata-only. Cover ownership
  blocks direct Attachment deletion, and an identity with a cover receives a meaningful deletion
  conflict. No automatic discovery, provider search, cover history, album or reordering, EXIF
  inspection, thumbnail, derivative, background media worker, list-card rendering, or
  BotanicalIdentity gallery was introduced; compact imagery remains for `UX-003` with a justified
  thumbnail strategy.
- Verification: focused affected backend tests (`35 passed`) and focused photo/cover component tests
  (`7 passed`); the backend suite (`354 passed`, 90.21% coverage), frontend suite (`150 passed`),
  and disposable PostgreSQL integration suite (`323 passed`) pass. The canonical
  `make feature-verify` gate covers those suites plus feature/workflow checks, API drift, production
  builds, the `0023 ↔ 0024` migration cycle with populated-data guard, whitespace, and the
  working-tree receipt.

## 2026-09-13 — ATTACHMENT-002 verified

- Added a narrow Attachment aggregate and Alembic revision `20260913_0023`: application-generated
  UUIDv7 metadata identifies active or retryable `pending_delete` still-image content while a
  separate opaque UUIDv7-derived key selects a backend-owned local path. No collection-record,
  Event, external-image, gallery, caption, attribution, or cover-image relationship was introduced.
- Added owner/CSRF-protected streaming upload and deletion plus owner-protected metadata/content
  retrieval. Uploads are limited to exactly 25 MiB and fully decode as one still JPEG, PNG, or WebP;
  normalized filenames remain display-only, SHA-256 and size are stored, permanent placement uses
  an atomic same-filesystem rename, storage keys resolve beneath one trusted root, and responses do
  not expose paths. Two-phase pending deletion makes unlink and metadata failures retryable.
- Added the backend-only `attachment_data` volume, non-root UID/GID 10001 ownership, 0700 directory
  permissions, isolated development/integration tmpfs roots, and a 32 MiB API proxy ceiling for
  multipart overhead. Backup and restore now quiesce writes, require a same-timestamp PostgreSQL
  dump/attachment tar pair, reject unsafe archive members, and verify stored sizes and SHA-256.
- Independent review confirmed the streaming size, full-decode, opaque-path, deletion-state, volume,
  migration, and archive boundaries. It tightened metadata/content retrieval to the owner session
  with `private, no-store` responses, rejects restore artifact filename/timestamp mismatches before
  Docker operations, adds exact-limit-minus-one and decompression-warning regression coverage, and
  removes redundant builder-stage filesystem setup.
- The final canonical `make feature-verify` covers the feature graph, workflow helpers, formatting,
  linting, strict typing, backend/frontend tests, API drift, disposable PostgreSQL integration,
  production image builds, the `0022 → 0023 → 0022 → 0023` migration cycle, whitespace, and a
  working-tree verification receipt. ATTACHMENT-002 is verified; ATTACHMENT-003 remains planned.

## 2026-09-12 — MAP-002 implemented

- Proved the current production GBIF path before implementation with documented Catalogue of Life
  XR fixture `Q2M4` and checklist `7ddf754f-d193-4cc9-b351-99906754a03b`. Exact occurrence search
  returned 437,168 PRESENT records and 431,970 coordinate-bearing PRESENT records without flagged
  geospatial issues; the same opaque ID, checklist, status, and quality filters returned a valid
  256-pixel PNG from the Maps v2 ad-hoc hex-density route. Runtime uses only the confirmed stored
  link ID and never performs scientific-name rematching or numeric-backbone translation.
- Added authenticated normalized occurrence-summary and fixed-purpose raster tile endpoints. The
  backend constructs only allowlisted GBIF requests with bounded time and response sizes, validates
  zoom/coordinates and PNG content, forwards no browser headers or collection metadata, and exposes
  no arbitrary proxy URL. Counts and tiles stay live; no occurrence, viewport, tile, native-range,
  GeographicPlace, BotanicalProfile, or collection persistence and no migration were introduced.
- Added an explicit-load BotanicalIdentity occurrence panel and lazy-loaded direct Leaflet layer.
  Zoom-appropriate hexagons show record density with a qualitative GBIF-style legend and an exact
  independently queried eligible total. The desktop/mobile textual companion covers taxon, source,
  checklist, retrieval time, quality policy, privacy, uncertainty, sampling bias, non-native and
  non-abundance semantics, dataset-specific licensing, attribution, empty and provider-error states.
  MAP-001 collection provenance and GEOGRAPHY-002 operator-managed native ranges remain separate.
- Canonical `make feature-verify` passed after independent review: the 75-entry feature graph and workflow
  helper suites passed; Ruff, Prettier, ESLint, strict mypy (169 source files), and strict TypeScript
  passed; 299 backend unit tests passed at 90.76% coverage, 143 frontend tests passed, and 305
  PostgreSQL integration tests passed; generated API declarations had no drift; backend and frontend
  production images built successfully (the lazy occurrence-map chunk is 0.90 kB / 0.54 kB gzip);
  the migration cycle correctly reported that no Alembic revision was added, and the final whitespace
  check passed.

## 2026-09-12 — PROPAGATION-002 frontend loading test stabilized

- Diagnosed the first guided-sowing component test's deterministic failure as an invalid test-timing
  assumption. Its in-memory session, CSRF, SeedLot, Location, and health mocks all resolved and the
  production workflow had no missing request or state race, but the test delegated the complete
  multi-effect React bootstrap to Testing Library's one-second polling deadline. On slower runs that
  deadline expired while the correct `Loading guided sowing…` state was still rendered.
- Kept the production UI and PROPAGATION-002 semantics unchanged. The affected test now explicitly
  flushes the immediate mocked request/update lifecycle inside an asynchronous React `act` boundary,
  then asserts the ready heading synchronously. No sleep, retry, timeout increase, weakened
  assertion, suite serialization, mock bypass, or global test-setting change was introduced.
- The exact affected test passed 10 consecutive fresh-process runs, and the complete 14-test
  PROPAGATION-002 file passed five consecutive runs (70 test executions) with normal timeouts. The
  complete 134-test frontend suite, Prettier, ESLint, strict TypeScript, the production Vite build,
  generated API drift, and diff whitespace checks pass.

## 2026-09-10 — contextual reference-picker race fixed

- Diagnosed the intermittent SeedLot contextual-creator failures as a stale delayed blur callback in
  the shared reference picker. Moving from the initially focused identity picker to the lot label
  scheduled a menu close; quickly returning to the picker reopened it, but the old callback could
  then close it again before the contextual-create action. CI's failed DOM captured that exact
  closed-combobox state.
- Replaced the input timer with focus-within handling at the picker boundary. The menu now closes
  synchronously only when focus leaves the complete picker, so pointer actions remain available and
  keyboard focus can move into its controls without an unowned timer. Added fake-timer regressions
  that deterministically reproduce blur and immediate refocus and protect internal focus movement.
- The stale-callback regression failed against the original implementation and all four focused
  picker regressions pass with the fix. A fresh container passed three consecutive complete SeedLot
  test-file runs (42 executions), including both affected contextual workflows on every run. The
  exact final code passes frontend Prettier, ESLint, strict TypeScript, the production Vite build,
  generated API drift, all 75 feature-graph entries, and diff whitespace checks.
- The unrelated `PROPAGATION-002` readiness-test timing assumption was subsequently corrected on
  `main` in `2caef9f`; it no longer blocks final verification of this focused picker change.

## 2026-09-10 — repository consistency and delivery reliability implemented

- Reconciled the public current-state summary and architecture overview with the verified Events,
  propagation lineage and reversal, geographic provenance, collection map, structured native-range,
  and external botanical-reference surfaces. Attachments/photos, richer germination and Event data,
  advanced search/analytics, import/export, contextual help, and PWA installability remain explicit
  deferrals; the V1 sequence and domain contracts are unchanged.
- Recorded the open-source-readiness follow-up already present on `main`: commit `a9c4391` adopted
  AGPL-3.0-or-later across the root license and package metadata, removed React Leaflet and its core
  package from the frontend manifest and lockfile, and retained Leaflet 1.9.4 directly for MAP-001.
  This pass reconfirmed those manifests, the lockfile, direct dependency tree, and direct Leaflet map
  implementation without adding dependency-audit infrastructure or changing runtime behavior.
- Corrected the delivery rerun gap after protected squash merge. Once `origin/main` advances, the
  reviewed feature SHA is no longer its ancestor; delivery now checks that SHA's associated
  same-repository PR before pushing and accepts the terminal state only when the exact branch/SHA was
  merged into `main`, every required current-SHA check passed, the reported merge SHA is on fetched
  `origin/main`, and the remote feature branch is deleted. Closed-unmerged, mismatched, ambiguous,
  missing-check, and unproven-divergence states remain blocked.
- Added deterministic no-network regression coverage for the merged-and-deleted rerun and retained
  exact-SHA failure cases. All 34 delivery/workflow helper tests pass. The complete SeedLot component
  file also passed nine consecutive focused runs (126 test executions); the reported contextual
  `Create identity` CI flake was not reproduced, its existing route/storage/dialog isolation remains
  sound, and no frontend code was changed.

## 2026-09-09 — GEOGRAPHY-002 implemented

- Added exact, many-valued BotanicalProfile native-range relationships to the shared
  GeographicPlace hierarchy. Broad and precise places can coexist without inferred ancestor or
  descendant links, and reparenting a custom place changes its derived display path without changing
  the stable relationship.
- Generalized the BotanicalProfile lifecycle: a profile exists while it owns any populated text
  section or structured native range. Adding the first range creates the profile atomically; clearing
  final text preserves range-only profiles; removing the final range deletes the profile only when
  no other meaningful profile-owned data remains. A deferred database constraint prevents persistent
  completely empty profiles.
- Added protected focused list/add/remove APIs, generated contracts, responsive identity-detail
  controls with path-disambiguated choices and accessible mutation feedback, and Geography usage
  visibility/deletion guards. Material provenance, ProvenanceSites, collection Locations, Suppliers,
  BotanicalIdentity fields, GBIF linking, and occurrence/distribution maps remain separate.
- Verification passed Ruff and Prettier formatting, Ruff and ESLint linting, strict mypy over 169
  source files, strict TypeScript, 286 backend unit tests at 90.78% coverage, 134 frontend tests, and
  304 disposable PostgreSQL integration tests. Revision `20260909_0022` was exercised through
  upgrade, populated-data downgrade refusal, cleanup, downgrade to `20260909_0021`, re-upgrade,
  deferred empty-profile rejection, and concurrent duplicate-add convergence. Generated API drift,
  both production image builds, all 75 feature-graph entries, and diff whitespace checks pass.
  `GEOGRAPHY-002` is implemented pending independent review.

## 2026-09-09 — BOTANY-002 verified

- Added the canonical BOTANY-002 external-data foundation and aligned separate planned
  GEOGRAPHY-002 native ranges, BOTANY-003 profile enrichment, MAP-002 botanical distribution,
  existing ATTACHMENT-002/003 photo work, later UX stabilization/help, and prose-only release
  hardening. V1 now denotes product scope while `0.1.0` is the intended first distributable release.
- Added a narrow backend-only GBIF adapter using the documented v2 matching service and Catalogue of
  Life eXtended Release checklist selection. Bounded requests normalize names, authorship, rank,
  status, accepted-name context, classification, match diagnostics, and alternatives while
  translating network, rate-limit, not-found, server, and malformed-response failures.
- Added one explicit current provider link per BotanicalIdentity/provider and a deterministic
  PostgreSQL JSONB response cache with a configurable one-day default freshness period. Link,
  replacement, stale-preserving refresh, and unlink operations never modify Florabase identity or
  profile facts; cache entries remain independent of links.
- Added protected focused APIs and a responsive BotanicalIdentity panel for editable search,
  ambiguous candidates, explicit confirmation, linked provenance, trusted GBIF navigation,
  refresh/failure freshness, replacement, and unlinking. The UI discloses that only botanical search
  terms leave Florabase and keeps enrichment, native ranges, occurrences, and MAP-001 out of scope.
- Independent verification passed 281 backend unit tests at 90.59% coverage, 132 frontend tests,
  298 disposable PostgreSQL integration tests, Ruff and Prettier formatting, Ruff and ESLint
  linting, strict mypy over 167 source files, strict TypeScript, and the migration cycle
  `20260908_0020 → 20260909_0021 → 20260908_0020 → 20260909_0021`, including populated-data
  downgrade refusal and concurrent link/cache convergence. Generated API drift, backend and
  frontend production image builds, validation of all 75 feature-graph entries, and final diff
  hygiene also pass. Canonical `make feature-verify` passed, including workflow helper coverage,
  production builds, the disposable migration cycle, and final whitespace and working-tree checks.

## 2026-09-09 — isolated stable-preview workflow implemented

- Added an operator-only stable-preview lifecycle around a detached adjacent Git worktree, with
  `origin/main` as the fetched default and an explicit-ref override. Existing clean previews move
  through safe detached switches; dirty previews and malformed worktree registrations fail closed,
  while targeted Git worktree repair covers a safely moved linked checkout without changing the
  primary branch, HEAD, index, or files; concurrent primary edits do not block preview preparation.
- Added a production-runtime Compose override and guarded orchestration for the explicit
  `florabase-preview` project. Rendered configuration validation pins build contexts to the preview
  worktree, publishes only `127.0.0.1:15173`, uses the matching loopback development origin/cookie
  policy, and requires isolated `florabase-preview_internal` and
  `florabase-preview_postgres_data` resources.
- Added explicit forward-only preview migration handling, interactive reuse of the existing owner
  bootstrap CLI, guarded development-to-preview custom-format dump/restore, bounded readiness,
  concise status, and stop/remove behavior that never deletes the preview volume. Development is
  hard-coded as import source and preflighted for migration compatibility before preview data is
  replaced; ordinary preview startup never imports data or runs a downgrade.
- Added 17 no-network workflow tests covering Git safety, fetched detached explicit-ref selection,
  invalid-ref and dirty-preview refusal, Compose paths/projects/resources/ports/configuration,
  persistent stop/remove semantics, preview-only migration/bootstrap targeting, guarded import
  direction and revision checks, readiness failures, status output, and unchanged disposable
  integration isolation. The new Python
  helpers pass Ruff formatting and lint; existing workflow and delivery helper suites, the 72-entry
  feature graph, Python compilation, and `git diff --check` pass.
- Real Docker verification created the clean sibling preview at
  `073ebf97c88e3a876280cfebfc23980b1048e4d2`, built from `origin/main`, migrated its new isolated
  volume to `20260908_0020`, reached both health endpoints through `http://localhost:15173`, and
  created an owner through the interactive preview bootstrap. Repeated startup was idempotent;
  stop and remove each preserved the volume; recreating the worktree retained both schema and owner;
  status accurately reported all three healthy services, exact SHA/ref, URL, volume, and revision.
  The exact temporary bootstrap test owner was removed afterward, leaving the running preview ready
  for the operator to create their own credentials.
  The persistent development stack was not running, so a real data import was deliberately not
  attempted. No product feature entry or Alembic revision was added for this developer workflow.

## 2026-09-09 — MAP-001 implemented

- Added the first-class authenticated collection provenance map using one Leaflet marker per
  coordinate-bearing ProvenanceSite. The initial viewport fits the available sites; accuracy is
  shown as an optional metre-radius circle, and explicit no-site, no-coordinate, and filter-empty
  states avoid inventing positions from broader geography or any other record.
- Added a deterministic bulk API projection for directly associated SeedLots, Plants, and
  PlantGroups with BotanicalIdentity and lifecycle context. Historical records remain visible,
  while Sowing-derived and PlantGroup-extracted descendants are deliberately excluded rather than
  inheriting an ancestor's provenance.
- Added record-type and BotanicalIdentity filtering with marker counts derived from the visible
  records, synchronized marker/list/detail selection, keyboard-operable companion navigation, and
  links to each collection record, BotanicalIdentity, and ProvenanceSite management route. The
  responsive layout preserves those non-map representations on narrow screens.
- Added pinned Leaflet 1.9.4, React Leaflet 5.0.0, and Leaflet type declarations. Operators can
  replace the OpenStreetMap-compatible tile URL and required attribution through an uncached runtime
  configuration asset; documentation calls out third-party tile-request privacy and self-hosting.
  The browser sends no Florabase record metadata, and no geocoding, geolocation, analytics,
  backend tile proxy, PostGIS, native-range data, or database migration was introduced.
- Implementation verification passed 265 backend unit tests at 90.45% coverage, 129 frontend tests,
  294 disposable PostgreSQL integration tests, Ruff and Prettier formatting, Ruff and ESLint
  linting, strict mypy over 156 source files, strict TypeScript, generated API drift, production
  backend and frontend image builds, validation of all 72 feature-graph entries, and
  `git diff --check`. The production frontend build retains Vite's non-failing warning for a
  roughly 601 kB main chunk. Canonical `make feature-verify` remains reserved for independent
  review.

## 2026-09-08 — SUPPLIER-002 verified

- Promoted Supplier from CRUD reference data to a focused detail hub while preserving its precise
  meaning: the direct acquisition source for a SeedLot, directly acquired Plant, or directly
  acquired PlantGroup. Sowing-derived and extracted descendants are not attributed to an ancestor's
  Supplier; GeographicPlace, ProvenanceSite, and physical collection Location remain independent.
- Added one-query Supplier-directory summaries and a focused detail projection with direct
  active/total counts, BotanicalIdentity-aware linked records, and deterministic recent acquisitions.
  SeedLots use their acquisition date, while directly acquired Plants and PlantGroups use their
  collection-entry date; unknown dates remain visible on linked records but are not presented as
  recent activity.
- Added responsive Overview and Linked material sections, useful empty states, direct navigation
  between Supplier and collection-record details, identity links, and historical lifecycle labels.
  Existing optional metadata and retirement/reactivation remain unchanged; retirement preserves all
  retained references, and no delete, order, purchase, price, or financial-analytics model was added.
- Focused implementation verification passed 263 backend unit tests at 90.41% coverage, 124 frontend
  tests, 293 disposable PostgreSQL integration tests, Ruff and Prettier formatting, Ruff and ESLint
  linting, strict mypy over 156 source files, strict TypeScript, generated API drift, production
  image builds, validation of all 71 feature-graph entries, and `git diff --check`. Alembic remains at
  `20260908_0020`; the feature required no schema change. Independent canonical verification is
  recorded with the reviewed feature branch.

## 2026-09-08 — GEOGRAPHY-003 implemented

- Superseded the stale evaluation-only planning contract and removed planned GEOGRAPHY-002 as a
  prerequisite. GEOGRAPHY-003 now depends on verified GEOGRAPHY-001 and UX-001; GEOGRAPHY-002
  remains planned for separate structured botanical native distribution.
- Preserved the immutable canonical World-rooted CLDR hierarchy and extended editable custom
  descendants with descriptive city/town, locality, and other named-area types. Added collapsed
  browsing, derived paths, bulk usage summaries, safe leaf deletion, and existing locked cycle-safe
  reparenting without inferred parents or a bundled city catalogue.
- Added relational ProvenanceSite records with optional GeographicPlace, coherent optional WGS84
  coordinates, optional non-negative metre accuracy, notes, timestamps, focused CRUD, usage-aware
  deletion, and reference support for SeedLots and directly entered Plants/PlantGroups. Location,
  Supplier, and planned botanical native distribution remain separate.
- Added an accessible responsive ProvenanceSite manager and path-aware selectors. The API exposes
  labels, coordinates, parent place paths, and supported collection usage for future MAP-001 without
  adding a map, geocoding, external requests, or botanical occurrence data.
- Focused verification passed 262 backend unit tests at 90.27% coverage, 123 frontend tests, 292
  disposable PostgreSQL integration tests, Ruff and Prettier formatting, Ruff and ESLint linting,
  strict mypy over 156 source files, strict TypeScript, generated API drift, feature-graph
  validation, and `git diff --check`. The disposable migration coverage exercises
  `20260907_0019 → 20260908_0020 → 20260907_0019 → 20260908_0020` and explicit downgrade refusal
  when ProvenanceSite data would be lost. Canonical `make feature-verify` remains reserved for
  independent review.

## 2026-09-07 — LOCATION-002 implemented

- Corrected the feature graph so global `UX-003` stabilization follows, rather than blocks, the
  remaining V1 feature surfaces. `LOCATION-002` now retains only its verified Location and UX
  foundations; the same stale prerequisite was removed from later `SUPPLIER-002`. `UX-003` remains
  planned and untouched.
- Added explicit Plants, Sowings, and Seed Lots scopes to the one shared hierarchical Location
  model, including safe migration defaults, API validation, backend-enforced assignments and moves,
  scope-aware selectors, and current-path preservation.
- Added an accessible collapsed-by-default Location tree with scope badges, usage summaries and
  directory links, child creation, reparenting, retirement/reactivation, and guarded leaf deletion.
  Active counts exclude historical records while totals retain them; used scopes cannot be removed,
  and referenced or parent Locations cannot be deleted.
- Implementation verification passed Ruff and formatting checks, ESLint, strict mypy over 148 source
  files, strict TypeScript, 251 backend unit tests at 90.13% coverage, 121 frontend tests, 282
  disposable PostgreSQL integration tests, generated API drift, feature-graph validation, and
  `git diff --check`. Canonical `make feature-verify` was intentionally not run; `LOCATION-002`
  remains implemented pending independent review.

## 2026-09-07 — PROPAGATION-003 verified

- Added receipt-proven reversal for SeedLot-to-Sowing, Sowing-to-Plant, and
  Sowing-to-PlantGroup. New forward operations atomically capture a versioned typed result
  expected-after snapshot with the receipt; historical receipts remain unchanged and report
  `legacy_receipt_missing_result_snapshot` instead of reconstructing past state from current data.
- Reversal restores the source's immutable BEFORE lifecycle and quantity representation without
  inverse arithmetic, marks the created result `reversed`, retains lineage and informational
  history, and marks only the receipt status reversed. Deterministic eligibility covers safe,
  retained-observation confirmation, structural correction, downstream-first ordering, transfer,
  extraction/reintegration, produced SeedLots, and other active-operation blockers.
- Added purpose-specific authenticated eligibility and CSRF-protected mutation APIs, plus responsive
  detail-page actions, typed blocker links, confirmation, authoritative refresh, historical badges,
  active-filter exclusions, and forward-workflow guards for reversed records.
- Independent review confirmed snapshot completeness and immutability, source restoration from the
  receipt BEFORE state, expected-result guards, downstream-first and cross-operation dependencies,
  global lock ordering, and the safe upgrade and guarded downgrade of Alembic revision
  `20260907_0018`. It corrected the historical-lifecycle validation message and made reversal
  eligibility refresh after Event creation, editing, or deletion so retained-history confirmation
  never presents stale same-screen state.
- Verification passed Ruff, strict mypy over 148 source files, 248 backend unit tests at 90.49%
  coverage, 278 disposable PostgreSQL integration tests, generated API drift, ESLint, strict
  TypeScript, all 119 frontend tests, and `git diff --check`. Manual QA in a disposable migrated
  stack covered safe, confirmation-required, and blocked reversal; retained observations; linked
  source, result, and dependent navigation; distinct repeated creation; active/history filters;
  accessible status and controls; and responsive behavior at desktop and 390×844.

## 2026-09-06 — PLANT-006 delivery CI follow-up

- Investigated a reported contextual SeedLot-creation test failure across isolated, in-file, and
  Plant-before-SeedLot runs. The route-hash changes did not leak state; the affected test had an
  ambiguous asynchronous modal lookup and did not reset browser storage during its own lifecycle.
  It now identifies each intended contextual dialog by accessible name and resets hash plus browser
  storage before and after every SeedLot screen test, while retaining the entered seed-lot details
  assertion after duplicate identity and failed supplier creation.

## 2026-09-06 — PLANT-006 verified

- Independent review confirmed the receipt-snapshot restoration, dependency guards, migration safety,
  and desktop/mobile reintegration workflow. It corrected two ordinary defects: operation-owned
  extraction and reintegration Events can no longer be edited through the ordinary Event API or UI,
  and successful extraction/reintegration now updates the Plant route hash to the authoritative
  target.
- Canonical `make feature-verify` passed: feature graph and workflow helpers; quality checks
  (including 209 backend tests at 90.05% coverage and 111 frontend tests); 247 disposable
  PostgreSQL integration tests; production builds; the `20260905_0016 → 0017 → 0016 → 0017`
  migration cycle; whitespace validation; and the local verification receipt.

## 2026-09-05 — PLANT-006 implemented

- Added receipt-proven reintegration of an extracted Plant into only its original PlantGroup. The
  locked atomic operation restores the immutable before-snapshot without inverse arithmetic, marks
  the Plant `reintegrated`, retains its lineage and Events, records one group-targeted reintegration
  Event, preserves the extraction Event, and changes only the receipt status to reversed.
- Added focused eligibility and mutation APIs with safe, confirmation-required retained-observation,
  and typed blocked outcomes. Guards cover receipt/result mismatch, lifecycle and structural Plant
  changes, transfer or other active receipts, produced SeedLots and downstream lineage, later group
  operations, group lifecycle/quantity correction, already-reversed receipts, and missing historical
  receipts. Concurrent mutation serializes on the receipt and affected rows.
- Added the responsive Plant and Event-journal experience: original-group context, retained-history
  confirmation, actionable blocker explanations, authoritative post-success refresh, Reintegrated
  historical state, lifecycle summaries, linked reintegration history, and operation-owned
  extraction actions that no longer resemble ordinary Event deletion.
- Added Alembic revision `20260905_0017`, generated API declarations, focused backend/frontend and
  PostgreSQL coverage including migration cycle, snapshot variants, history, blockers, rollback,
  repeat use, and concurrent requests. Implementation checks passed: Ruff and ESLint; strict mypy
  over 141 source files and strict TypeScript; 209 backend unit tests at 90.08% coverage; 111
  frontend tests; generated API drift; 247 disposable PostgreSQL integration tests; and
  `git diff --check`. Final canonical `make feature-verify` is intentionally left to the independent
  reviewer; `PROPAGATION-003` remains unimplemented.

## 2026-09-05 — CI-002 auto-merge delivery fix

- Corrected `make feature-deliver` to recognize GitHub REST's `closed` plus `merged: true` response
  after successful squash auto-merge, retain the resulting merge SHA, and continue blocking closed
  unmerged pull requests. Focused no-network coverage includes open polling, both closed outcomes,
  an auto-merge between polling reads, and resulting main-SHA reporting. Workflow tests, helper
  compilation, and `git diff --check` passed.

## 2026-09-05 — CI-002 verified

- Added `make feature-verify` as the final local feature gate. It validates the feature graph and
  repository workflow helpers, runs the quality, disposable PostgreSQL integration, and production
  build gates exactly once, checks both staged and unstaged whitespace errors, and stores an ignored
  local tree receipt rather than changing application files or requiring a clean working tree.
- Added conditional Alembic detection against the `origin/main` merge base. A branch with revision
  files receives `previous main head → feature head → previous main head → feature head` in a uniquely
  named Compose project backed by tmpfs PostgreSQL; non-migration branches skip that extra cycle.
- Added fail-closed `make feature-deliver`: it requires a clean reviewed commit and expected Florabase
  origin, refuses unsafe branch/history states, verifies the receipt, makes only a normal push, reuses
  one open PR or creates one deterministic PR, enables exact-SHA squash auto-merge, polls current-SHA
  `quality`, `integration`, and `build` checks with bounded startup/completion waits, and confirms the
  merge and remote-head deletion. Failed terminal checks leave the branch and PR untouched with
  `DELIVERY_BLOCKED`; a migration is reported only as a later `make dev-upgrade` reminder after
  `make feature-finish`.
- Focused no-network helper tests exercise verification success/failure and migration paths, clean
  delivery preconditions, normal non-force push, PR creation/reuse, exact SHA auto-merge/checks,
  action registration delay, failure/cancel/timeout handling, and remote-branch deletion. Canonical
  `make feature-verify`, `make check`, `make ci`, and `git diff --check` passed; delivery was not run
  against GitHub.
- The first real delivery created PR #19 but then rejected GitHub REST's lowercase `open` state.
  Delivery now normalizes REST state on parsing and validates the returned open PR's head branch,
  base branch, and exact delivery SHA for both reuse and creation. Regression fixtures cover lowercase
  and mixed-case state, historical closed/merged entries, mismatched branch/base data, and follow-up
  reuse without a duplicate PR.
- A second real delivery confirmed GitHub's normal post-push REST propagation window: PR #19 initially
  returned its prior head SHA before later reflecting the pushed SHA and registering new-SHA checks.
  Delivery now validates the open PR target immediately, then waits at a bounded two-second/sixty-second
  cadence only for a prior same-lineage head to advance to the delivery SHA. It rejects mismatched
  branch, base, state, or unrelated SHA without waiting, and begins the separate current-SHA check
  registration wait only after the PR head matches. No-network regression coverage includes delayed,
  immediate, timeout, wrong-target, no-duplicate, and check-sequencing paths.

## 2026-09-05 — REVERSAL-001 verified

- Added one closed relational `operation_receipts` representation for the six supported forward
  operation kinds. Explicit source/result/Event foreign keys and per-kind database checks replace a
  generic JSON payload; UUIDv7 identity, UTC creation time, applied/reversed status, adjustment mode,
  lifecycle, and exact/approximate/unknown quantity state are retained.
- Wired receipt creation into the existing locked SeedLot-to-Sowing, Sowing-to-Plant,
  Sowing-to-PlantGroup, PlantGroup extraction, Plant transfer, and PlantGroup transfer transactions.
  Exact and unit-bearing values are copied directly, estimates retain both recorded values, unknown
  remains all-null, group extraction records actual stored before/after state, and later aggregate
  correction does not rewrite the receipt.
- Added a unique operation-owned Event relationship for extraction and transfer. Ordinary Events
  retain non-replay edit/delete behavior; ordinary deletion of an operation-owned Event is rejected
  until a future purpose-specific undo exists. No historical receipts are fabricated, no receipt
  CRUD API is exposed, and no undo, reintegration, reverse mutation, or UI was added.
- Added migration `20260905_0016`, immutable-original-facts enforcement with a separately mutable
  future status, kind/payload constraints, focused unit/integration coverage, rollback injection,
  losing-concurrency receipt counts, and the disposable downgrade/re-upgrade cycle.
- Verification passed: canonical `make check` and `make ci`; workflow-helper checks; backend and
  frontend formatting, lint, strict typing, unit and frontend suites; API/generated-contract drift;
  all 238 disposable PostgreSQL integration tests including concurrency coverage; production backend
  and frontend builds; and `git diff --check`. The migration cycle passed after widening the stored
  transfer predecessor lifecycle constraint so the receipt schema never assumes that the captured
  prior lifecycle is always `active`.

## 2026-09-05 — reversible domain-operation planning refinement

- Audited the verified forward operations without changing application behavior. Exact SeedLot
  partial use and exact PlantGroup extraction have reversible numerical invariants (`100 → 80 → 100`
  and `10 → 9 → 10`); approximate values must restore their recorded estimate rather than use
  inverse arithmetic, unknown remains unknown, and quantity dimensions/units cannot be crossed.
- Recorded the current gap: forward transactions and extraction-result links exist, but no persisted
  operation identity, adjustment mode, before-state snapshot, complete created-record set, or prior
  transfer lifecycle exists. Current persistence is therefore insufficient for generally reliable
  undo despite the deliberate non-replay Event contract.
- Added planned `REVERSAL-001` for a narrow immutable authoritative-operation receipt,
  `PLANT-006` for recorded extracted-Plant reinsertion, and `PROPAGATION-003` for guarded
  propagation reversal. The plan keeps ordinary Event deletion separate from validated Undo action,
  records deterministic dependency blocks, and preserves history rather than assuming destructive
  cleanup. These increments are sequenced before later Location/geography selection, without adding
  artificial Location or geography feature dependencies.

## 2026-09-05 — PLANT-005 verified

- Added an explicit `transferred` lifecycle for Plant and PlantGroup plus owner-authorized,
  CSRF-protected transfer operations. Each operation locks the active target and atomically creates
  a transfer Event with an optional precision-preserved date, free-text recipient, and notes; the
  target remains editable as historical correction data, while later Event edits or deletion never
  replay lifecycle effects.
- Whole-group transfer preserves the stored group quantity and offers no partial quantity control.
  The existing extraction operation is now the required partial-transfer path: it atomically creates
  the resulting Plant, updates only an exact source count when applicable, and records a cultivation
  extraction Event on the source group with a navigable resulting-Plant relationship. Generic Event
  creation cannot manufacture extraction Events.
- Updated the responsive Plants experience with explicit bilingual transfer actions, accessible
  dialogs, active/history filtering, historical styling, transfer and extraction Event rendering,
  corrected routed-result navigation, and active-versus-transferred BotanicalIdentity summaries.
  Dashboard active totals continue to count only lifecycle `active` records.
- Added Alembic revision `20260904_0015`, regenerated OpenAPI and TypeScript declarations, and
  documented lifecycle, Event categories, quantity, correction, and relationship semantics.
- Independent release review added a database-enforced source-group/result-Plant relation and
  matching service validation, preventing an extraction Event from being reassigned to a Plant from
  a different PlantGroup. It also corrected the integration migration-head expectation.
- Canonical verification passed: `make check` (Ruff, Prettier, ESLint, strict mypy over 134 source
  files, strict TypeScript, API drift, 203 backend tests at 90.02% coverage, and 110 frontend
  tests) and `make ci` (workflow helpers, the same checks, 235 fresh PostgreSQL integration and
  migration tests, and production image builds). Authenticated browser QA covered desktop
  individual transfer and extraction journals plus the 390 × 844 responsive PlantGroup Events view
  and mobile navigation. `PLANT-005` is `verified`.

## 2026-09-04 — PROPAGATION-002 verified

- Added contextual BotanicalIdentity actions for preselected SeedLot creation, explicit source
  SeedLot selection before Sowing, and explicit Sowing-versus-direct paths for Plants and PlantGroups.
  Successful guided creation opens the new record while preserving visible links to its source and
  identity context.
- Added a two-stage SeedLot-to-Sowing workflow over the verified atomic API. It previews exact
  subtraction, requires confirmation before mutation, keeps approximate remainders visibly editable,
  preserves unknown quantities, suppresses incompatible arithmetic, offers no adjustment and valid
  use-all choices, prevents duplicate submission, and retains entered data on API failure.
- Added Sowing source and descendant summaries, explicit Plant/PlantGroup actions, operator-selected
  resulting Sowing lifecycle defaulting to active, deliberate completion summaries, and derived
  exact non-germinated counts only when the exact seed-count denominator permits them. Completed
  Sowings remain available under Completed and All; failed and abandoned records remain under All.
- Added a responsive, textual, clickable propagation-path component for stored lineage on Sowing and
  propagated Plant/PlantGroup overviews. Identity aggregation is still labeled as non-lineage;
  direct creation, retroactive entry, correction, and no-replay semantics remain unchanged. No
  backend, schema, migration, OpenAPI, or generated declaration change was needed.
- Focused verification: baseline 93 frontend tests passed before changes; Prettier and ESLint passed
  across the frontend; strict TypeScript passed; and 63 focused frontend tests passed across the new
  PROPAGATION-002 coverage and the affected identity, SeedLot, Sowing, and Plant screens. Generated
  API drift and `git diff --check` passed. An isolated migrated Compose stack verified contextual
  identity-to-SeedLot entry, exact SeedLot subtraction, atomic Sowing and Plant creation, returned
  record navigation, stored propagation links and summaries, and the compact responsive layout in a
  real browser. A one-shot full frontend run reached 96/98 before two existing SeedLot tests hit the
  15-second limit under host contention; the complete SeedLot file then passed 14/14 in isolation and
  again within the 63-test focused regression run.
- Independent verification passed `make check` and `make ci`: workflow-helper checks;
  backend/frontend formatting, lint, and strict type checks; 192 backend unit tests at 90.20%
  coverage; 108 frontend tests; API declaration drift; 229 disposable PostgreSQL integration tests;
  and production image builds. Browser QA at desktop and 390 × 844 verified the responsive,
  authenticated BotanicalIdentity → SeedLot → Sowing → Plant workflow, exact partial-use preview,
  explicit Sowing completion, source and descendant summaries, and clickable stored-lineage links.

## 2026-09-04 — PROPAGATION-001 verified

- Added explicit atomic SeedLot-to-Sowing and Sowing-to-Plant/PlantGroup backend operations while
  preserving every ordinary create and correction path. Exact compatible source quantities are
  locked and subtracted without allowing a negative remainder; approximate partial use requires an
  explicitly confirmed editable approximate remainder; unknown partial use remains unknown; and
  explicit use-all exhausts the source without manufacturing exact zero for approximate or unknown
  material.
- Added explicit post-transition Sowing lifecycle selection and a strongly typed propagation
  summary derived only from stored Sowing lineage. Each Plant contributes one exact tracked
  individual, exact PlantGroup counts contribute their quantities, and approximate or unknown
  groups remain separately visible without becoming exact counts. Germination observations are not
  rewritten, Sowing completion is never inferred, later edits do not replay transition effects, and
  no propagation log, redundant counter, automatic Event, frontend workflow, or migration was
  introduced.
- Independent review found the transition contract, explicit uncertainty handling, locking,
  correction boundaries, derived summary, and deferred Event/UI boundaries aligned with the
  acceptance criteria. Canonical `make ci` passed: workflow-helper tests; backend/frontend format,
  lint, and strict type checks; 192 backend unit tests at 90.20% coverage; 93 frontend tests; API
  generation drift check; 229 isolated PostgreSQL integration tests; and production image builds.
  The OpenAPI and TypeScript declarations are regenerated and current. No migration was needed.

## 2026-09-03 — post-UX-001 UAT roadmap refinement

- Recorded the intended collection lifecycle narrative from BotanicalIdentity through SeedLot,
  Sowing, Plant/PlantGroup, and Events or terminal state while preserving the distinction between
  identity aggregation, explicit lineage, quantities, and lifecycle state.
- Added planned `PROPAGATION-001` and `PROPAGATION-002` increments so quantity accounting,
  total/partial-use choices, source lifecycle decisions, contextual creation entry points, and
  cross-linking are decided and delivered in that order. `PROPAGATION-001` is the recommended next
  increment; no application behavior is included in this planning pass.
- Added later planned increments for transferred/ceded Plant lifecycle (`PLANT-005`), observed-use
  navigation refinement (`UX-003`), scope-aware hierarchical Location browsing (`LOCATION-002`),
  deliberately scoped finer-grained geography (`GEOGRAPHY-003`), and connected Supplier summaries
  (`SUPPLIER-002`). PlantGroup transfer remains an evaluation, global city reference data is not a
  first-release requirement, and Supplier financial totals remain gated by `ORDER-001`.
- Preserved every existing verified status and acceptance criterion. Validation parsed all 67
  feature records; checked required fields, allowed statuses and priorities, unique IDs, dependency
  references, self-dependencies, DAG cycles, and verified prerequisites; structurally compared all
  35 pre-existing verified records with `origin/main`; checked changed files with Prettier; and ran
  `git diff --check`.

## 2026-09-03 — UX-001

- Reframed Florabase around a collection Dashboard; persistent grouped desktop navigation; a fixed
  five-destination mobile bar with a secondary More tray; unified Plants browsing for distinct Plant
  and PlantGroup records; and a complete global Events journal. The focused Dashboard endpoint
  supplies authoritative collection counts and six recent Events, while the global endpoint keeps
  EVENT-001 ordering and EVENT-002's All, Observations, Cultivation, and Status vocabulary.
- Added shared breadcrumb, detail-header, accessible routed-tab, card, Event-feed, and explicit
  lineage primitives across Plant, PlantGroup, SeedLot, Sowing, and BotanicalIdentity details.
  BotanicalIdentity is now an identity-based collection hub with Overview, Seeds, Sowings, combined
  Plants and Plant groups, and Events tabs; textual record types, concrete cross-links, and explicit
  copy keep identity aggregation separate from recorded lineage.
- Completed the editability audit: Plant, PlantGroup, SeedLot, and Sowing retain their lifecycle-aware
  editors; Location, Supplier, and user-created GeographicPlace now share visible Edit and overflow
  action placement; canonical geography remains immutable. BotanicalIdentity gained focused update
  and guarded deletion: unused identities can be removed, while SeedLot, Plant, or PlantGroup
  references produce a clear conflict and never cascade. Contextual form guidance remains UX-002.
- Verification passed formatting, Ruff, ESLint, strict mypy, strict TypeScript, 176 backend unit
  tests, 93 frontend tests, all 224 disposable PostgreSQL integration tests, generated API drift,
  workflow-helper checks, production backend/frontend builds, and `git diff --check` through the
  canonical `make ci` path. Browser QA on an isolated tmpfs PostgreSQL stack covered every required
  detail, dashboard, global Events, menu, desktop sidebar, and 390×844 bottom-navigation flow with no
  console errors or horizontal page overflow. No migration was required and no operator database or
  persistent volume was modified. `UX-001` is verified.

## 2026-09-02 — EVENT-002

- Added one protected Event journal to both Plant and PlantGroup detail pages. The complete
  EVENT-001 vocabulary has human-readable labels; API order and unknown, year, month, or complete
  occurrence-date precision remain faithful. Desktop uses a vertical chronological timeline, while
  narrow screens use compact wrapping cards with touch-sized actions and no horizontal scrolling.
- Added predictable All, Observations, Cultivation, and Status filters plus useful loading, error,
  retry, empty, and mutation states. The accessible create flow conditionally requires a movement
  destination and explains movement or lifecycle side effects. Every Event can be edited or deleted;
  both flows explain that historical correction/deletion neither replays nor rolls back current
  Location or lifecycle. Successful creation refetches both Event history and the authoritative
  Plant/PlantGroup state; update and deletion refresh history only.
- Component coverage now exercises Plant and PlantGroup journals, every kind and partial-date
  precision, deterministic ordering, all filters, desktop/mobile structure, empty/loading/error
  states, creation and validation, state-changing refresh, edit/delete semantics, mutation failure,
  warnings, and accessible labels/actions. Verification passed Prettier, ESLint, strict TypeScript,
  Ruff, strict mypy over 122 source files, 169 backend unit tests at 90.72% coverage, 89 frontend
  tests, generated API drift, workflow-helper tests, all 222 disposable PostgreSQL integration tests,
  and production backend/frontend image builds through `make ci`; `git diff --check` also passed.
- Browser QA against an isolated tmpfs PostgreSQL stack confirmed the desktop timeline and the
  responsive 390×844 card layout, including faithful dates, wrapping long notes, visible destination,
  44-pixel action targets, zero horizontal overflow, side-effect warnings, non-rollback dialogs, and
  authoritative Location refresh after movement. No migration or generated API change was needed,
  and no operator database or volume was modified.
- A collection-wide Event timeline remains deferred. `UX-001` now explicitly retains the future
  cross-application review of primary/mobile and detail navigation, tabs/sections, action placement,
  cross-domain hierarchy, visual/interaction coherence, and possible global Event activity. That UX
  work remains planned. `EVENT-002` is verified.

## 2026-09-02 — EVENT-001

- Added first-class UUIDv7 Events for exactly one Plant or PlantGroup, with the controlled initial
  vocabulary, optional precision-preserved occurrence date and notes, exact UTC audit timestamps,
  restrictive relational references, and deterministic target timeline ordering. Alembic revision
  `20260902_0014` enforces target, kind, partial-date, notes, and movement-destination invariants and
  adds target timeline indexes.
- Added authenticated target-aware list/create APIs and Event read/update/delete APIs. Creation
  locks the target and atomically applies movement Location or death/loss/discarded lifecycle
  effects. Event correction and hard deletion intentionally change history only and never replay or
  roll back current target state; ordinary Plant/PlantGroup edits still do not create Events.
- Verified with Ruff and Prettier formatting, Ruff and ESLint, strict mypy over 122 source files,
  strict TypeScript, 169 backend unit tests at 90.72% coverage, 84 frontend tests, generated OpenAPI
  and TypeScript drift checks, workflow-helper tests, production backend/frontend image builds, and
  all 222 disposable PostgreSQL integration tests. Integration coverage includes the
  upgrade/downgrade/re-upgrade cycle, restrictive constraints, authorization and CSRF/Origin,
  transactional rollback, and concurrent movement serialization. The canonical integration wrapper
  was not invoked because its `down --volumes` cleanup was rejected by the execution safety layer;
  the same Compose test service ran in a unique project with tmpfs PostgreSQL and no Docker volumes,
  followed by non-volume container/network cleanup.
- Structured Event payloads beyond movement destination, Event attachments, and the timeline UI
  remain deferred to later increments. `EVENT-001` is verified.

## 2026-09-02 — CI-001 repository automation implemented

- Added stable `quality`, `integration`, and `build` pull-request checks using the repository's
  existing verification, disposable PostgreSQL, and production Compose build paths. The workflow
  has read-only permissions, per-PR stale-run cancellation, explicit timeouts, and unconditional
  integration cleanup.
- Added isolated-tested `feature-start` and `feature-finish` helpers, explicit development database
  upgrade wiring, and `make ci`; centralized the squash auto-merge workflow in contributor guidance.
- Local verification passed Bash syntax checks; isolated workflow-helper tests; pinned Prettier over
  changed Markdown, JSON, and YAML; 209 PostgreSQL integration tests; production backend/frontend
  image builds; `git diff --check`; and a final `make check` (Ruff, ESLint, strict mypy over 112
  source files, strict TypeScript, 141 backend unit tests at 90.17% coverage, 84 frontend tests, and
  generated API drift). One earlier `make check` attempt hit a host load average of 9.49 and 14
  unchanged frontend tests exceeded their five-second timeout; the focused retry and final complete
  run passed without weakening the tests.
- GitHub-side verification is complete: implementation was squash-merged as `a746e4f`, Actions run
  `33605345339` passed `quality`, `integration`, and `build`, and the repository permits squash
  auto-merge while disabling merge commits and rebases. The active `Protect main` ruleset targets
  only `refs/heads/main`, requires pull requests plus strict `quality`, `integration`, and `build`
  checks, and protects against deletion and non-fast-forward updates. The first `make feature-finish`
  execution verified the merged PR, fast-forwarded local `main`, removed local `ci/ci-001`, and left
  the repository clean; automatic remote head-branch deletion was also confirmed after merge.
  `CI-001` is now `verified`.
- The first pull-request run exposed a GitHub checkout ownership difference: Vitest's default
  bundled config loader tried to write a timestamped module under `/app/node_modules/.vite-temp`
  while loading `vite.config.ts`. The frontend test script now uses Vitest's supported runner config
  loader, which evaluates the existing config without writing beside the read-only checkout and
  preserves non-root container execution. Once the frontend suite could complete, the same run
  revealed that API drift verification also regenerated tracked artifacts before comparing and
  restoring them. Both generators now use read-only check modes during verification; the explicit
  artifact-writing path remains `make api-generate`.

## 2026-09-02 — DOCS-001 repository audit

- Reconciled public and engineering documentation with the implemented application through
  `PLANT-004`; rewrote the README, architecture, domain model, roadmap, deployment/development guides,
  and this milestone log around current behavior.
- Added concise contributor and security policies plus a pull-request template. Audited configuration,
  backup/restore, package metadata, GitHub configuration, links, licensing, CI, screenshots, and
  release gaps without adding product behavior.
- Corrected `GEOGRAPHY-002` from `verified` to `planned`: GeographicPlace exists and is used for
  material provenance, but no BotanicalIdentity/Profile native-range relationship is implemented.
- Added planned `CI-001` because Dependabot exists but no GitHub Actions verification workflow does.
  License selection, private vulnerability reporting, screenshots, version/release policy, and the
  first changelog entry remain operator/release decisions.
- Verification passed: Prettier over all changed Markdown/JSON/YAML; JSON/schema, unique-ID,
  dependency-reference, self-dependency, DAG, verified-prerequisite, internal-link,
  `.env.example`/Compose-key, and single-Alembic-head checks; repository stale-state greps;
  `git diff --check`; full `make check` (Ruff, ESLint, strict mypy over 112 source files, strict
  TypeScript, 141 backend unit tests at 90.17% coverage, 84 frontend tests, and generated API drift);
  and all 209 disposable PostgreSQL 18.6 integration tests. `DOCS-001` is verified.

## 2026-09-02 — PLANT-004

- Alembic revision `20260901_0013` added restrictive PlantGroup origin for extracted Plants and
  preserved the mutually exclusive Sowing, direct, or group-origin modes.
- Added an owner-authorized, CSRF-protected atomic extraction operation. It creates one Plant,
  decrements exact group quantity, completes the final exact member, and leaves approximate/unknown
  quantities unchanged. The accessible Plants UI exposes the focused workflow and keeps extraction
  origin read-only during ordinary editing.
- Verified with Ruff, strict mypy, 141 backend unit tests, 209 PostgreSQL integration tests, Prettier,
  ESLint, strict TypeScript, 84 frontend tests, generated API drift, production image builds, and
  responsive browser checks. `PLANT-004` is verified.

## 2026-09-01 — LINEAGE-002

- Alembic revision `20260901_0012` added mutually exclusive Plant/PlantGroup producers for
  collection-produced SeedLots, with restrictive references and cycle validation.
- Added typed authenticated lineage routes for SeedLots, Sowings, Plants, and PlantGroups. A focused
  recursive PostgreSQL traversal follows only supported direct workflow relationships and retains
  inactive history.
- Verified with 139 backend unit tests, 192 PostgreSQL integration tests, 80 frontend tests, static
  checks, generated contracts, production builds, and `make check`. `LINEAGE-002` is verified.

## 2026-09-01 — PLANT-003

- Added the accessible responsive Plants navigation section for Plant and PlantGroup list, search,
  lifecycle/type filtering, detail, creation, and full editing.
- Verified with 80 frontend tests, 138 backend unit tests, 184 PostgreSQL integration tests, static
  checks, generated-contract drift, production builds, responsive browser checks, and `make check`.
  `PLANT-003` is verified.

## 2026-08-31 — PLANT-001 and PLANT-002

- Defined Plant as one specimen with no quantity and PlantGroup as one managed group of one botanical
  identity. Both support incomplete data, Sowing or direct origin, provenance, Location, lifecycle,
  and historical retention.
- Alembic revision `20260831_0011` and protected APIs implemented those contracts without mutating
  SeedLot or Sowing accounting. Migration, invariant, authorization, generated-contract, unit, and
  integration checks passed. Both features are verified.

## 2026-08-31 — SOWING-001 through SOWING-003

- Defined and implemented Sowings as managed attempts from exactly one SeedLot, with optional
  precision-preserved date, quantity, simple germinated total, Location, cultivation details, and
  retained lifecycle.
- Alembic revision `20260831_0010`, protected APIs, and the responsive Sowing UI were verified across
  database invariants, authorization, unit/integration/component tests, generated contracts,
  production builds, and browser layouts. The three Sowing features are verified; PWA installability
  remains planned.

## 2026-08-30 — SeedLot and geography

- `SEED-001` through `SEED-004` defined and delivered the SeedLot schema, protected API, and
  accessible inventory UI. Revisions `20260830_0008` and `20260830_0009` preserve partial dates,
  source/provenance distinctions, optional exact/approximate count or weight, safe zero/exhausted
  semantics, storage Location, and lifecycle without implicit Sowing deduction.
- `GEOGRAPHY-001` installed a reproducible 287-row Unicode CLDR 48.2.1-derived canonical
  GeographicPlace hierarchy and protected custom extensions. `GEOGRAPHY-002` native-range
  relationships were only planned and remain unimplemented.
- Supplier and collection Location vertical slices were delivered in revisions `0005` and `0006`.
  Their protected directories, lifecycle/hierarchy behavior, tests, and generated contracts are
  verified.

## 2026-08-28 to 2026-08-30 — authenticated reference application

- `DOMAIN-001`, `DATABASE-001`, and `BACKEND-001` established the BotanicalIdentity contract,
  revision `0002`, protected REST slice, deterministic directory, validation, and generated types.
- `SECURITY-001` accepted the backend-owned session design. `SECURITY-002` implemented revision
  `0003`, owner bootstrap, Argon2id login, opaque PostgreSQL sessions, secure/loopback cookie modes,
  Origin and CSRF checks, expiry/revocation, and throttling. `FRONTEND-002` delivered browser session
  restoration and logout.
- `FRONTEND-001`, `PROFILE-001`, `PROFILE-002`, and `IDENTITY-001` delivered the accessible botanical
  identity/profile workflows and revision `0004`. All are verified.

## 2026-08-27 to 2026-08-28 — repository foundation

- `FOUNDATION-001` established production-oriented and development Compose stacks, non-root runtime
  images, health/readiness, explicit Alembic migrations, typed FastAPI/React scaffolding, generated
  contracts, and quality tooling.
- `OPS-001` added guarded PostgreSQL custom-format backup/restore and an isolated restore drill.
  `TESTING-001` added disposable PostgreSQL integration testing. All three are verified.

## Current state

As of 2026-10-13, delivered main is `f54648f` (PR #106); Alembic head is
`20261009_0041`. Historical handoff entries below and above describe their own candidate phase,
not the current delivery state.

- The [canonical product/release roadmap](product-roadmap.md) owns the agreed v0.1.0 → v1.0.0
  sequence. Immediate work: Journal/History product pass → Labels audit → functional/IA freeze →
  page-by-page visual review → UI Foundation normalization → release-readiness audit → public
  documentation/presentation → v0.1.0. No public release or release-gate completion is claimed.
- Dashboard/UI Foundation (PR #101) and Schedule Calendar (PR #105) are delivered and `verified`.
  Schedule remains future intention, Journal human-recorded observations/occurrences/notes and
  History a read-only factual projection. Existing LABEL-001 already includes authenticated QR lookup;
  mobile quick capture remains later work.
- The roadmap's delivered baseline and `docs/features.json` distinguish landed capabilities from
  implementation/verification status. Older landed increments recorded as `implemented` remain so;
  this planning work promotes none to `verified`. INFRA-MAINT-001 landed in PR #106 and retains its
  graph status `implemented`. Detailed delivery and verification evidence stays in the handoffs.
- PERF-001's verified measurements remain historical evidence; the expanded release candidate
  requires measured resource review. RELEASE-001 remains `planned`; install/upgrade, paired DB/media
  recovery, security, responsive/accessibility, public documentation and versioned distribution
  acceptance are outstanding. GHCR is preferred; no publishing is performed here.
- POST-0.1 priorities begin with material lineage, accepted-name reconciliation, name history,
  measurements, phenology and vegetative propagation/cuttings. Existing IDs are reused; unscheduled
  themes receive no speculative IDs. Vegetative propagation requires a domain decision before v1.0.
- PHYLOGENY-001 remains SOURCE_BLOCKED (`planned` in JSON) and blocks neither v0.1 freeze/release
  nor v1.0 core collection management. BOTANY-003's general-description path remains source-blocked;
  BOTANY-004 and ENRICHMENT-002 remain deferred. Source prerequisites are not implementation failures.
  Generic task management, multi-user collaboration and full offline writes/sync remain outside the
  agreed core scope.

## 2026-10-05 — PREVIEW-001 independent final verification

- `make feature-verify` passed on the complete reviewed tree: feature graph and workflow guards, Ruff,
  Prettier, strict mypy (256 application files), TypeScript, backend tests (600 passed, 90.01%
  coverage), frontend tests (375 passed across 41 files), API drift, PostgreSQL integration, production
  backend/frontend image builds, migration-cycle checks (no new Alembic revisions), whitespace and
  verification receipt.
- PREVIEW-001 is **verified** in `docs/features.json`; roadmap and handoff reflect operator UAT and
  independent verification complete. The receipt was recorded for this exact working tree.
- Commit, protected delivery, merge and conservative worktree finish remain the authorized next steps.

## 2026-10-09 — TAXONOMY-003 independent verification

- Independent product/source review accepted the collection-aware classification tree and its WFO
  2026-06 CC0 source contract. Browser review covered desktop, tablet and 390×844 mobile, keyboard
  navigation, filters, linked/unresolved identities and related classification peers; no fixture link
  was confirmed or changed. Broad cross-application visual review remains deferred.
- Canonical `make feature-verify` passed on the final reviewed tree: **895 backend tests, 90.03%
  coverage; 541 frontend tests across 56 files; 699 PostgreSQL integration tests; 329 strict-mypy
  files; API drift clean; production backend/frontend builds passed; migration cycle
  `0039 → 0040 → 0039 → 0040`; whitespace and worktree receipt passed.** Ruff, Prettier, ESLint,
  TypeScript, feature/workflow helpers and environment checks passed as part of the gate.
- TAXONOMY-003 is marked **verified** in `docs/features.json`. Source-index checksum and footprint,
  query counts, cold/warm measurements, UAT evidence and known host-load limits are documented in
  [the handoff](taxonomy-003-handoff.md). Protected delivery and DEV upgrade are the remaining
  lifecycle steps; migration 0040 requires the upgrade after merge.

## 2026-10-10 — CI-003 FULL migration-cycle repair (review handoff)

- Independently reproduced the dependency-only defect on exact base `d86c488`: FULL selected,
  migration command lacked `--force-cycle`, and the actual runner returned “no Alembic revisions
  added” without PostgreSQL. Initialized `fix/ci-003-full-migration-cycle` in the attached worktree;
  prior dependency-audit files remain preserved and are separate from this repair.
- Replaced the competing migration booleans with explicit `skip` / `affected-cycle` / `full-cycle`
  decisions. Every selected cycle uses the existing force mechanism. Automatic and explicit FULL
  execute identical exhaustive migration semantics; affected docs/frontend/domain skips remain safe.
- Corrected v2 receipts require four verified PostgreSQL revision states and successful exact
  disposable cleanup, distinguish required/executed/result from `skipped_by_impact`, and reject
  incomplete or historical v2 evidence through the existing delivery preflight validator.
- Focused selector/execution, fixture receipt/delivery, migration/resource and workflow helper checks
  pass, as do workflow Ruff formatting/lint and strict mypy, backend cycle-helper static checks,
  shell syntax, feature graph and whitespace checks. Real PostgreSQL smoke covers automatic and
  explicit FULL without migration differences, nontrivial synthetic downgrade/re-upgrade, and a
  broken existing migration chain with only a lockfile feature diff. All run-owned resources retire;
  separate real resource smoke proves volume cleanup and unchanged persistent resource identities.
- CI-003 remains `verified`; no new feature, product behavior, dependency baseline or remote CI change.
  Primary main remains clean at `d86c488`. No files staged, no commit/push/delivery; final canonical
  `make feature-verify` / `make verify-full` deliberately reserved for Luna. Dependency maintenance
  remains paused until this repair is delivered. See the
  [repair handoff](ci-003-full-migration-cycle-repair-handoff.md) and its focused evidence.

## 2026-10-11 — dependency-maintenance sweep closure

- Sequential maintenance delivered frontend lint/format (#88), Vite (#90), backend tooling (#92),
  psycopg (#94), FastAPI/Uvicorn (#96), and compatible SQLAlchemy 2.0/Alembic maintenance (#98), each
  with canonical FULL verification, protected quality/integration/build checks and workflow finish.
- The final isolated increment refreshes only pip-tools 7.6.1 → 7.6.2. Python 3.14.7/Click 8.5.0
  compatibility and clean installed requirements were confirmed. Both backend locks reproduce
  byte-for-byte; runtime pins are unchanged and generated headers remove the erroneous `--no-index`.
  CI-003 selects FULL for the actual manifest/lock diff, including forced complete migration cycle;
  exact-tree canonical verification and protected CI are required before delivering this closure.
- SQLAlchemy 2.1 remains deferred for substantive typing migration; jsdom for the Node contract;
  React 19.3 for missing reproducible browser coverage of the required complex forms/map flows.
  Only the uncommitted React dependency candidate was discarded; React stays 19.2.8.
- Old grouped bot proposals were re-read for compatible, superseded or deferred decisions, never
  merged. Node/Python/PostgreSQL contracts, protected environments and product scope are preserved.
  The [consolidated baseline](dependency-maintenance-baseline.md) records versions, prior delivery
  identities, focused evidence and reconsideration conditions without reopening completed groups.
- No schema migration or Dashboard work is included. DASHBOARD-001 is the next product increment.

## 2026-10-12 — UI Foundation v0.1 and DASHBOARD-001 implementation handoff

- Established semantic tokens, self-hosted Source Sans 3 / Source Serif 4, shared workspace
  primitives, safe base/shell styling and authoritative [UI contract](ui-contract.md).
- Dashboard now provides explicit active-record metrics, current identity coverage, planned
  attention, distinguishable Journal/History rows, propagation counts and optional sourcing review
  through one bounded authenticated aggregate. No schema migration or inferred rates.
- Added idempotent synthetic sourcing/propagation fixtures; authorized UAT replacement is healthy
  at localhost:15174. Visual self-review covered Dashboard, Seeds, Botanical identities and Schedule
  at 1440/1024/390; keyboard focus and navigation checked.
- Focused evidence: 3 backend unit, 21 PostgreSQL integration, 93 frontend and 1 fixture test pass;
  Ruff/script lint, mypy, ESLint, TypeScript/Vite build, generated API drift and formatting pass.
  Host-side lazy-loading timeouts resolved in the unchanged Quality runtime tests.
- [Handoff](dashboard-001-handoff.md) records definitions, evidence, screenshots and deferred global
  migration. Status implemented; independent QA owns canonical verification and final visual review.
  No staging, commit, push, delivery, main modification or canonical feature-verify performed.

## 2026-10-12 — DASHBOARD-001 visual-review refinement handoff

- Consolidated Search, Filters, Saved views and Quick add into a compact toolbar. Quick add uses
  the existing menu and nine creation routes; shared SavedViews supports optional dialog access.
  Advanced filters now use a compact right-side TaskDialog drawer with immediate URL state,
  query-preserving reset, keyboard dismissal and focus return.
- Scoped Dashboard width/overflow corrections enable document scrolling and full content width.
  Operational sections use approximately 7:5 desktop columns, equal tablet columns and mobile
  stacking; supporting sections retain light dividers. Existing domain/API/dependency semantics
  are unchanged by this refinement.
- Browser review at 1440×844, 1024×844 and 390×844 confirms toolbar/menu/drawer usability, reachable
  mobile footer controls and no horizontal overflow. Seeds and Botanical identities retain their
  existing layouts and inline SavedViews. Current screenshots and a synthetic Saved View review
  are recorded in the [handoff](dashboard-001-handoff.md).
- Focused evidence: 105 frontend tests across five files, 3 collection-view unit tests and
  4 Dashboard PostgreSQL tests pass; TypeScript, ESLint, Prettier, production Vite build and
  whitespace checks pass. Quality's configured `pnpm test` runner reports all 105 passes; its
  wrapper termination status and a concurrent host run's three App timing failures are documented
  in the handoff. Those three pass in isolation on the host; assertions/timeouts remain unchanged.
- Candidate stays implemented, unstaged and uncommitted for Luna. Canonical feature-verify,
  staging, commit, push and delivery remain reserved for the next owner.

## 2026-10-12 — DASHBOARD-001 independent verification

- Independent review corrected one strict-mypy issue in the new integration test's empty-state
  assertion by checking upcoming and recent-history lists separately; no test was weakened.
- Canonical FULL `make feature-verify` passed on the exact candidate tree: backend unit **910
  passed**, PostgreSQL integration **717 passed**, frontend **564 passed / 58 files**, strict lint,
  typing, format and API drift checks, production backend/frontend builds, migration full-cycle at
  existing head `20261009_0041`, health checks and whitespace checks. Exact-tree receipt recorded.
- Prior Quality Vitest wrapper exit 143 did not recur in the canonical run; its 564-test report
  completed, followed by the remaining integration/build/migration stages. No assertions or
  timeouts were weakened. Dashboard acceptance criteria are now evidenced; status is `verified`.

## 2026-10-12 — SCHEDULE-002 Calendar implementation handoff

- Added Month Calendar within Schedule, sharing ScheduledActivity, filters, URL navigation and
  versioned mutations. Inclusive API due-date bounds restrict loading to the visible month;
  scientific target fields support exact botanical typography. No migration or dependency.
- Bounded summaries reveal complete day work in the existing TaskDialog drawer. Mobile uses
  compact date/count navigation and the selected-day list; creation prefills its date.
  Synthetic fixtures add same-day density, month-end and next-month examples without overwrite.
- Focused checks pass: 17 backend unit, 15 PostgreSQL integration, 28 Schedule frontend and
  1 fixture test; date tests in three timezones, Ruff/format, strict mypy (339 files), ESLint,
  TypeScript, OpenAPI/client drift, backend production image and frontend production build.
  Feature schema validation and whitespace checks pass. Existing Alembic deprecations remain.
- Browser self-review at 1440×844, 1024×844 and 390×844 covered populated/empty states, shared
  filters/history, overflow/detail, keyboard focus/Escape, mobile transformation, selected-date
  creation, native reschedule and completion without Event. No horizontal overflow found.
  [Handoff and screenshots](schedule-002-handoff.md) record precise evidence and limitations.
- Exact owned disposable previews were cleaned after review, preserving operator environments.
  Candidate remains implemented, unstaged and uncommitted on `feat/schedule-002` at base
  `8ed57d63b45286cb2509e9eeca9c2a84ad5b14eb`. No canonical feature-verify, staging, commit,
  push, delivery, merge, feature-finish or primary-main change; independent QA owns the gate.

## 2026-10-12 — SCHEDULE-002 focused UX refinement

- Kept Calendar within Schedule as the same ScheduledActivity presentation, across shared filters,
  kinds and targets; Journal and History remain separate. Refined only Schedule's compact
  List/Calendar toolbar, creation action, subordinate guidance and truthful compact empty List.
  Empty/single-page pagination is suppressed; a concurrently emptied later page returns to page one.
- Create/edit reuses TaskDialog and FormActions with a viewport-bounded form, one scrolling
  content region and reachable Cancel/Save footer. Pristine dismissal returns focus; dirty
  Escape/backdrop/Cancel requires explicit discard and preserves entries when dismissed.
- Current checks pass: **45 Schedule frontend**, **17 backend unit** and **15 PostgreSQL** tests;
  focused ESLint, strict TypeScript, production Vite build and Schedule formatting. No assertions
  or timeouts weakened. Guarded integration cleanup reports zero residual resources.
- Current synthetic browser evidence covers Calendar, create/edit and compact empty List at
  1440×844, 1024×844 and 390×844, with same-day overflow, overdue/today/future and six target types.
  Browser access returned and all interrupted checks completed in a fresh isolated preview.
  Mobile content scrolls independently while the footer stays visible; pristine dismissal returns
  focus and dirty dismissal retains entries until explicit discard. Real synthetic create/edit
  saves persist. No horizontal overflow. The [handoff](schedule-002-handoff.md) records screenshots
  and precise evidence; independent QA still owns acceptance and canonical verification.
- No domain/API/Calendar-placement or global UI changes in this refinement. Candidate remains
  implemented, unstaged and uncommitted; no canonical feature-verify, commit, push or delivery.
  Exact-owner recovery cleaned the disposable synthetic preview with zero residual resources,
  preserving persistent environments and shared cache. Handoff/progress formatting, feature
  schema validation (100 features) and whitespace checks pass; HEAD and empty index are unchanged.

## 2026-10-12 — SCHEDULE-002 compact controls and persistent manual-review UAT

- Grouped target search/results/count and compact page controls; suppressed zero/single-page
  pagers. Reset now sits beside Filters only for active filters, preserving view/month/day while
  restoring defaults. Period navigation is compact `‹ Today ›` with accessible/disabled semantics.
  Shared bounded editor, footer, dirty protection and focus behavior remain intact.
- Audited the existing v4 fixture and added only its missing Genovese profile/packet and
  collection-wide activity through `manual_review_extension=1`. Recognized upgrades are additive;
  repeat seed preserves operator edits/IDs/dates, and interrupted work requires explicit reset.
  Provisioned the existing checksum-pinned WFO index for meaningful Taxonomy; cache remains ignored.
- Authorized guarded retirement of old synthetic UAT from its 51ba owner; stopped this candidate's
  Feature Review with volumes preserved to release the shared port. Established persistent UAT
  from 6147 at **http://localhost:15174**, UAT-only **preview / preview**, schema `20261009_0041`,
  v4/68 manifest records. Two repeat seeds and fixed-UAT stop/up preserved full row/media/manifest
  digests. UAT remains running; DEV/Stable Preview/production and unknown resources were preserved.
- Manual browser inspection covered Dashboard, Seeds, Sowings (active/completed), Plants,
  Harvests/stored material, Locations, Journal, History, Schedule List/Calendar, identities/profile,
  Taxonomy and Suppliers/Orders. Persistent Schedule review at 1440×844, 1024×844 and 390×844
  confirms controls, overflow detail, target variety, intended-date semantics, editor dismissal/
  scrolling/reachable footer and no horizontal overflow. Unrelated legacy UI polish is deferred.
- Focused evidence: 51 frontend, 17 Schedule unit, 15 Schedule PostgreSQL, 5 fixture-extension unit,
  25 real fixture/guard and 19 UAT workflow tests; guarded UAT Compose smoke and fixed persistence
  pass. Ruff/format, strict helper mypy (six files), ESLint, TypeScript and Vite build pass; no
  assertion or timeout was weakened. Disposable resources cleaned with zero residuals.
  Both Schedule extensions also retain a building marker across simulated post-commit write
  interruption, preventing silent duplicate reseeding. Current generated API drift check passes.
- [Handoff](schedule-002-handoff.md) records exact fixture/source/credentials/operator workflow,
  checks, screenshots and global-review deferrals. Candidate remains implemented, unstaged and
  uncommitted. No canonical feature-verify, commit, push or delivery.

## 2026-10-12 — SCHEDULE-002 independent verification

- Independent review of the full candidate diff confirmed Calendar remains a presentation of the
  shared `ScheduledActivity` workspace and filters, with no Journal/History mixing, preserved
  versioned actions, bounded inclusive month loading, local date semantics, responsive layouts,
  accessible controls, dialog dirty protection, and additive synthetic fixture ownership. No
  production/domain/workflow defect was found; two Schedule List density/desktop-width polish items
  remain deferred to the global page review.
- Canonical `make feature-verify` selected **FULL** and passed on the exact candidate tree: feature
  graph **100 valid**; backend **912 passed at 90.25% coverage**; frontend **599 passed across 60
  files**; PostgreSQL integration **720 passed**; all eight workflow suites; repository format,
  lint, strict typing and API drift checks; backend/frontend production builds; whitespace and exact
  working-tree receipt.
- Forced migration cycle passed through existing head `20261009_0041` (base → head → base → head);
  SCHEDULE-002 adds no migration. Exact disposable integration/build/migration resources were
  cleaned, while shared cache and unknown/legacy resources were retained. Persistent UAT remains
  healthy at `http://localhost:15174` with its v4/68-record synthetic fixture. DEV, Stable Preview,
  production and unrelated environments remain preserved. See the [handoff](schedule-002-handoff.md).
- SCHEDULE-002 is now `verified`. Protected delivery and `make feature-finish` follow the repository
  lifecycle after the exact verified candidate is committed.

## 2026-10-13 — INFRA-MAINT-001 implementation and preserved real UAT recovery

- From authoritative main `ec992440cba2681ca6e5327ec613a25f88183c3d`, initialized existing `947e`
  worktree through `make feature-init`, branch `ci/infra-maint-001`. Added exactly this consolidated
  infrastructure increment as implemented; SCHEDULE-002 and all existing statuses remain unchanged.
- Existing UAT guards now accept a proven clean delivered detached owner, including exact
  squash-merged PR heads with concurrent main changes. Stop preserves containers/network/volumes.
  Explicit same-path `uat-preview-sync` fetches delivered main, checks DB identity/target migration
  ancestry before source/migration mutation, journals intent, quiesces writers, switches normally,
  migrates only forward and recreates healthy applications. Interrupted sync resumes its pinned
  target; ordinary up/seed refuse it. Ownership/foreign-user/source/port/fixture guards stay closed.
  Feature finish is unchanged; detached reset refuses before mutation, preserving its attached-only contract.
- Encoded SQLAlchemy 2.1, React/DOM/types 19.3+, jsdom 30.1+ and Node declarations >24 deferrals
  in Dependabot per-package version rules. Compatible maintenance and unrelated weekly groups
  remain enabled. No dependency/pin/lock/runtime/product/UI change. QA closes open #102/#103/#104
  only after this policy merges; current bot proposals remain untouched.
- Focused checks pass: UAT **19 + 15**, environment **29**, feature helpers **41**, resource **14**,
  Stable Preview **19**, impact **19** and shell helper suite. Disposable real Compose smoke
  `florabase-uat-preview-smoke-c7fa48e9e127` passes **25** fixture tests, real finish/detach and
  repeated management, newer-main forward migration, interruption/refusal/resume, full domain/
  fixture/media/credential hash and dependency sentinel preservation, exact zero-residual cleanup
  and unchanged protected environments. Workflow lint/format (**22** files), strict typing
  (**15 + 2**), YAML/group/native-range validation, affected Prettier, graph **101**, syntax and
  whitespace checks pass. Initial smoke fixture faults were fixed; no check/assertion was weakened.
- Recovered real UAT using only the new Makefile sync command from owning `6147`: clean detached
  `ff6ab788` → delivered `ec99244`, schema/code **0041**, frontend/backend/db healthy at
  **http://localhost:15174**, normal **preview / preview** login/private collection/readiness 200.
  Exact full DB data digest, **68** fixture IDs/extensions, all **5** media-volume file hashes,
  original volume identities and ignored WFO index/seal hashes match before/after. No real seed,
  reset or removal. DEV/Review/Stable Preview/production and primary snapshots remain identical.
- [Handoff](infra-maint-001-handoff.md) and [machine evidence](infra-maint-001-evidence.json)
  include the interim reviewed-Makefile invocation, provenance, safety, checks and post-delivery bot
  cleanup. Candidate is unstaged/uncommitted at unchanged base HEAD; independent QA owns canonical
  verification and delivery. No canonical feature-verify, feature commit/push/delivery or real
  feature-finish/DEV upgrade occurred. **READY_FOR_REVIEW**.

## 2026-10-13 — canonical v0.1.0 to v1.0.0 roadmap (planning review handoff)

- Audited existing roadmap, feature graph, progress, workflow/UI contracts and relevant delivered
  feature/source handoffs from clean fetched main `f54648f`; initialized the existing Codex worktree
  with `make feature-init BRANCH=docs/product-release-roadmap`. No second worktree or primary change.
- Consolidated superseded roadmap sequences into the existing `docs/product-roadmap.md`: explicit
  DELIVERED / PLANNED / DEFERRED / SOURCE_BLOCKED / RELEASE_GATE vocabulary, PRE-0.1 freeze path,
  measurable release evidence, versioned GHCR distribution direction and stable-core v1.0 criteria.
- Recorded all fourteen post-0.1 priorities, including material ancestry distinct from taxonomy/
  phylogeny, historical botanical names, structured observations, care recurrence and vegetative
  propagation. CUTTING-001 retains its ID/dependencies/status but requires an explicit domain-model
  decision and honest starting/outcome quantities; TAXONOMY-001/002 now explicitly preserve names
  under which material was acquired or recorded. No implementation status is promoted or ID added.
- Corrected README/current-state planning prose against delivered capabilities without rewriting
  historical milestones. Journal/History and Labels remain the next product passes; physical print/
  scan evidence is outstanding. Source-blocked phylogeny and profile text do not block core releases.
- Validation passed: feature graph (101 records), JSON parse, pinned Prettier for all four changed
  files, 58 local Markdown links/anchors and 55 fully spelled roadmap feature IDs, unchanged graph
  IDs/statuses/priorities/dependencies and schema, unchanged RELEASE-001 contract, documentation-only
  scope, empty index, unchanged base HEAD and `git diff --check`. No application tests or operational
  release drills are claimed by this planning handoff.
- No application/UI/dependency/migration/publishing changes. No canonical `make feature-verify`,
  staging, commit, push, delivery, finish or environment mutation. Candidate remains available for
  independent planning review; next product increment is the Journal/History pass. **READY_FOR_REVIEW**.

## 2026-10-13 — ACTIVITY-001 Journal / History product pass (implementation handoff)

- Audited existing Event/Journal, History authority/deduplication, Schedule completion, entity
  activity contexts, Dashboard/search/navigation and synthetic UAT before implementation. Initialized
  existing `a165` worktree through `make feature-init` from requested main `b99bb4a` on
  `feat/journal-history-product-pass`; no new worktree or primary change.
- Product contract is visible in the pages: Journal = operator-recorded, History = authoritative
  past facts, Schedule = future intended work. Journal adds a target chooser and compact source-aware
  entries; contextual editor uses shared modal dismissal, dirty protection and focus return.
  History keeps read-only source navigation, precision, bounded SQL and existing backing-row suppression.
- Added one terminal History fact per completed ScheduledActivity, with persisted UTC completion
  time explicitly distinguished from actual occurrence/due date. Planned/overdue/cancelled work is
  excluded; explicit linked Events remain atomic/idempotent and retain their chosen actual date.
  Dashboard shares source/date presentation. No migration, new Event domain or universal timeline.
- Focused checks: backend **71**, PostgreSQL **56**, final affected frontend **81** plus contextual
  Plant **42**, real fixture/guard **25** tests. Repository Ruff lint/format, mypy **339** files,
  ESLint, TypeScript, scoped Prettier, frontend production build, `make api-check`, graph **102**,
  JSON and whitespace checks pass. PostgreSQL suites ran via guarded `scripts/test-integration.sh`;
  existing Harvest/receipt/conversion deduplication, uncertainty and query bounds are retained.
- Browser evidence at **1440×844 / 1024×844 / 390×844** covers pages, populated target chooser,
  editor and discard confirmation: no horizontal overflow, reachable controls, pristine/dirty
  dismissal and focus return. Real mobile Journal create/edit/month precision/filter/navigation/delete
  passes. In-app controller timed out; isolated Chromium supplied scoped checks, not global acceptance.
- Existing additive UAT fixture is sufficient; no fixture or real UAT data/ownership changes.
  Unique disposable candidate preview proved repeated-seed preservation and normal synthetic login.
  Temporary QA note was removed through its supported workflow. Protected environments were preserved.
- [Handoff](journal-history-product-pass-handoff.md) records the audit, correction/duplication/date
  rules, filters/navigation, checks, screenshots and exclusions. ACTIVITY-001 is **implemented**;
  independent QA owns visual acceptance and canonical verification. All changes remain unstaged and
  uncommitted at unchanged base HEAD. No `make feature-verify`, staging, commit, push or delivery.
  **READY_FOR_VISUAL_REVIEW**.

## 2026-10-13 — ACTIVITY-001 recording hub and Dashboard grammar refinement

- Same `a165` candidate and unchanged base `b99bb4a`. Journal is now a recording hub plus notebook
  fallback. Shared Record menu opens delivered Harvest/Sowing forms, atomic bulk Location moves,
  Schedule completion and contextual germination; notes retain the existing target chooser/editor.
  No copied structured forms or future domains. Global notebook excludes owned backing records and
  bare movement/lifecycle facts without notes; contextual source records remain available.
- Journal/History share Dashboard's flexible Search / Filters drawer / Saved views grammar, active
  summaries, query-preserving reset and compact ruled chronology. History stays read-only with source
  labels/links and PartialDate/UTC completion semantics. Bounded literal History search runs before
  SQL count/page; optional version-1 Saved View `q` preserves old states and URL navigation.
- Restored concise Journal/History subtitles at the operator's final request. Header/toolbar/date
  columns use available width and intrinsic wrapping; legacy Journal pane/header selectors no longer
  override document flow. Dashboard shares source/date semantics without a layout redesign.
- Focused verification: backend **147** (History/Saved Views/Schedule/Event/schema), PostgreSQL **57**
  (History/History Saved Views/Schedule/Dashboard/Event API); guarded integration cleanup passed.
  Frontend affected selection covers **194** tests; final contextual Plant/Journal rerun **42/42**
  passed after the last error-copy assertion update. Ruff lint/format, mypy **339** files, ESLint,
  strict TypeScript, scoped Prettier, production build and API drift pass; feature graph **102** valid.
  Commands used the Quality environment, `pytest --no-cov`, guarded `scripts/test-integration.sh`
  exact suite selections and `pnpm test` for `src/events`, `src/history`, contextual Plant,
  DashboardSearch, Saved Views, Schedule and UX001. No canonical `make feature-verify`.
- Real Chrome browser zoom: **1440×844 at 80/100/125/150%**, **1024×844 at 100/125%**,
  **390×844 at 100%**. All **21** Dashboard/Journal/History measurements show no horizontal
  document/main overflow and visible document flow; **71** screenshots include filters, Saved Views,
  Record, chooser and editor. Native checks pass for canonical routes, menu keyboard/outside/Escape/
  focus, chooser, pristine/dirty editor dismissal and mobile note create/edit/month/search/delete.
- Existing synthetic v4 fixture suffices; repeat seed preserves state. Final disposable preview
  `florabase-uat-preview-smoke-6f992cfb07eb` retired with zero residual owned resources; protected
  operator Git/container/volume/database snapshots unchanged. Temporary QA note removed via UI.
  Earlier interrupted/EOF-ended disposable previews retired by exact positive ownership.
- [Refined handoff](journal-history-product-pass-handoff.md) records the full product/routing contract,
  source/duplication/search/date rules, actual zoom evidence, checks and deferred sidebar IA questions.
  ACTIVITY-001 remains **implemented**, pending independent visual acceptance and canonical QA.
  Candidate remains unstaged/uncommitted; no commit, stage, push, delivery, Labels, sidebar restructuring
  or global visual review. **READY_FOR_VISUAL_REVIEW**.

## 2026-10-13 — ACTIVITY-001 consolidated Activity family refinement

- Same `a165` candidate on `feat/journal-history-product-pass`, unchanged base `b99bb4a`; no new
  feature/worktree or promotion of delivered features. Journal/History/Schedule semantics, canonical
  Record routing, duplicate suppression, completion evidence and Dashboard aggregates are preserved.
- `ActivityPageHeader` composes PageHeader's PageIdentity/PageTools with the existing Dashboard search,
  filter drawer and supported Saved Views grammar. Wide layouts share identity/tools horizontally;
  intrinsic wrapping and a stable search basis handle zoom/intermediate widths, with full-width mobile
  search. Concise subtitles remain. Schedule List/Calendar is a separate local control; no Schedule
  Saved Views contract is invented. CSS specificity removes an import-order wrapping conflict.
- Journal/History use grouped white chronologies with subtle dividers. Schedule retains its actual
  Overdue/Today/Next 7 days/Later buckets as white grouped surfaces, quieter counts/notes and Complete
  plus overflow actions. Terminal/non-owner rows remain inspectable without writes. Native-modal row
  menus stay inside their dialog; Escape closes the menu first, then returns focus. Versioned forms,
  conflicts/reload, confirmation, dirty safety and selected-date prefill remain canonical.
- Schedule exposes its existing bounded server-side title/notes `q`, shared by List and visible-month
  Calendar. Clear filters preserves query/view/month/day; exact-target and other URL dimensions remain.
  No new API, schema, runtime dependency, future domain or migration is introduced by this refinement.
  UI contract and [consolidated handoff](activity-family-refinement-handoff.md) record the demonstrated
  header/list pattern; sidebar membership/order and global visual migration remain deferred.
- Checks: baseline **68** frontend; final **147** focused backend tests, **197** affected frontend tests
  plus **2** shared interaction tests, **58** distinct PostgreSQL regressions (original selection **57**;
  final Schedule rerun **16**, including notes/literal search before count/page). Ruff lint/format,
  mypy **339** files, ESLint, strict TypeScript, scoped Prettier, final frontend build, `make api-check`,
  feature graph **102** and `git diff --check` pass. No weakened assertions or canonical verification.
- Actual Chrome zoom: all **35** Dashboard/Journal/History/Schedule List/Calendar page measurements
  pass at **1440×844 80/100/125/150%**, **1024×844 100/125%**, **390×844 100%**. Scoped graphical
  comparison confirms one Activity UI foundation. Native Record/Journal workflows and Schedule
  search/reset/view/menu, reschedule/completion/cancellation, Calendar drawer/month/mobile agenda pass.
  Browser evidence is in `docs/review/activity-family/`; global acceptance remains independent QA.
- Existing synthetic v4 fixture and repeated-seed preservation suffice. All temporary previews use
  positive ownership and retire with zero residual resources. Final preview
  `florabase-uat-preview-smoke-932dcdd1a4bd` preserves protected Git/container/volume metadata, raw
  database checksums and all **39** persistent UAT table counts/contents. Intermediate raw-dump
  comparisons varied in the persistent UAT database digest; no metadata difference was found in the
  retained diagnostic, and the earlier cause remains undetermined. Follow-up/final stable audits pass.
  No persistent UAT reset/reseed/repair or ownership change; temporary plans only persist until exact
  disposable retirement, and notebook test notes are deleted through their normal source workflow.
- Empty index and unchanged HEAD; all work remains unstaged/uncommitted. No stage, commit, push,
  delivery, `make feature-verify`, Labels, sidebar restructuring or global visual review.
  **READY_FOR_VISUAL_REVIEW**.

## 2026-10-13 — ACTIVITY-001 filter grammar and local Schedule heading correction

- Same unstaged/uncommitted `a165` candidate on `feat/journal-history-product-pass`; base HEAD
  remains `b99bb4a`. Concise subtitles remain restored. Dashboard behavior, domain ownership,
  notebook exclusions, History dedup/dates and Schedule versioned mutation contracts are preserved.
- Shared native checkbox fieldsets use two-column wide / one-column narrow grids. Journal Entry
  type, History Fact/Primary record type and Schedule Status/Activity kind/Target type support real
  combinations. History/Schedule enum queries are repeated, bounded, union within each dimension
  and intersect across search/date/other filters before count/page. Stable SQL ordering remains.
  Legacy v1 scalar Saved Views normalize without changing persisted rows; old URLs remain readable.
- Dashboard's live model now applies to every Activity drawer, including valid Timeline year:
  one conditional Reset filters / Done footer, no Apply year. Filters count restricting dimensions;
  compact dimension chips clear one restriction, while reset preserves query and Schedule view/month/
  day. Omitted legacy Status remains planned; unrestricted Status repeats all three real values.
  Journal's named groups still exclude Other, and all typed Schedule targets still exclude untargeted
  plans, so both remain counted restrictions. Overdue is still derived from planned due dates.
- Schedule List/Calendar moves into the local count/month heading. Calendar shares that region
  with Previous/Today/Next; List has no date navigation. Repeated filters, search and explicit
  month/day survive switching/refresh/browser history. Existing list surfaces and row menus remain.
- Content-sized 34rem Activity drawers cap at the viewport, scroll fields and keep the footer
  reachable. Scoped selectors fix Dashboard import-order precedence; native inset anchoring removes
  the remaining full-height blank Journal sheet. UI contract and the [consolidated handoff](activity-family-refinement-handoff.md)
  document the grammar, encoding, counts, accessibility and exact review evidence.
- Checks: baseline 129 frontend; 148 focused backend tests; Ruff lint/format (384 files), mypy (339),
  ESLint and strict TypeScript pass. 204 affected frontend tests pass, followed by all 56 Schedule
  tests and the final production build after the target-count/CSS corrections. 60 distinct focused
  PostgreSQL tests pass across History/Saved Views/Schedule/Dashboard/Event API: initial 59/60,
  corrected History fixture rerun 22/22 and final Schedule 17/17. API artifacts regenerated;
  `make api-check`, feature graph 102 and `git diff --check` pass. No canonical gate ran.
- Final actual zoom matrix passes all 35 page and 28 drawer measurements, with 168 captures in
  `docs/review/activity-family/filter-consistency/`. All four native/browser checks pass, including
  checkboxes/Space, combinations/count/reset, refresh/Back, local headings, period and mobile footer.
  Existing synthetic v4/repeated seed suffices. Final exact-owned disposable preview
  `florabase-uat-preview-smoke-c50bf9eb3778` retires with zero residual resources.
- Final preservation audit matches protected Git/container/volume metadata, non-UAT raw digests and
  all 38 UAT tables other than auth_sessions. That table keeps one row but its digest changes;
  exact fields/cause remain unproven, and full 39-table/raw-UAT preservation is not claimed for this
  interval. The preceding browser run matched all 39 tables. No persistent reset/reseed/repair or
  session rewrite; task browser actions target disposable URLs only, with no secret contents emitted.
- Empty index and unchanged HEAD. ACTIVITY-001 remains implemented for independent QA. No stage,
  commit, push, delivery, `make feature-verify`, Labels, sidebar restructuring or global visual review.
  **READY_FOR_VISUAL_REVIEW**.

## 2026-10-13 — ACTIVITY-001 independent review and verification

- Independent implementation and live product review found no material Journal, History, Schedule,
  filter, responsive, accessibility or domain-model defect. Persistent UAT inspection covered
  Dashboard, Journal, History, Schedule List/Calendar, filters, source navigation, linked completion
  context and URL-preserving view switching. No UAT business or fixture records were changed;
  authenticated sign-in exercised the expected session touch (`last_seen_at` / `idle_expires_at`).
- The first canonical full run exposed three load-sensitive 15-second timeouts in unchanged Sowing
  tests; all 19 tests passed both in isolation and in the subsequent full canonical run. No timeout
  threshold or test behavior was changed.
- Final `git diff --check` and `make feature-verify` pass on the review tree. Full evidence: feature
  graph 102 valid; 916 backend tests; 618 frontend tests; 731 PostgreSQL integration tests; lint,
  formatting, strict typing, API drift, backend/frontend production builds, complete migration cycle
  at `20261009_0041`, workflow/resource guards, and exact disposable-resource cleanup all pass.
  No application migration was added. Protected UAT/DEV/Feature Review resources and unknown
  Docker resources remain preserved.
- ACTIVITY-001 is verified against its acceptance criteria. The candidate is ready for staged-diff
  review and local commit; delivery and finish remain the requested next lifecycle steps.

## 2026-10-13 — IA-FREEZE-001 Labels and navigation candidate

- Clean current main `3fbf0ca` → `feat/ia-freeze-001` in the provided `4ff7` Codex worktree.
  One shared contextual/central Labels composer supports Seed lot, Plant, Plant group and managed
  Stored material. Mixed temporary batches expose typed sources, exact UUIDs/routes, per-record
  copies, totals, up to ten A4 sheets and final empty cells. No new API, persistence or migration.
- Record-specific real fields retain structured scientific/cultivar typography, PartialDate,
  approximation and unknown versus zero quantity. Stored material uses current managed inventory,
  not collected quantity. QR generation and canonical-origin creation gating are removed from this
  frozen print workflow; exact source associations and existing future-QR safeguards remain.
- One A4 / 50 × 30 mm / 4 × 9 preset, zero gutters, 5 mm horizontal / 13.5 mm vertical margins.
  Proportional full-paper preview remains responsive. Print isolates the sheet portal and uses exact
  mm offsets to avoid Chromium’s cumulative print-grid rounding. Long physical text gets explicit
  capacity feedback and readable full Label content; acquisition/quantity retain their priority line.
- Final IA remains Overview → Collection → Activity → Explore → Sourcing → Tools. Labels stays in
  Tools with everyday contextual entry; groups/material remain local Plants/Harvests modes. Maps
  stays non-actionable with its three indented children, Geography outside. URLs/search/deep links
  remain. Real navigation links, scrollable visible active destination, collapsed desktop and grouped
  native mobile navigation retain keyboard focus/return and account access.
- Baseline **101** tests. Final focused run **235 tests / eleven files**; final print-position,
  breadcrumb and shared-dialog rerun **107 / three files**, final fixed-header sidebar pass
  **85 / five files**. ESLint, strict TypeScript, production
  frontend build, graph **103 valid** and whitespace checks pass. No weakened checks or timeouts.
  Backend/API/schema are unchanged; no canonical `make feature-verify` was run.
- Final browser matrix covers 1440×844 **80/100/125/150%**, 1024×844 **100/125%**, 390×844 **100%**.
  No horizontal overflow or trapped Labels list; all four native contextual entries/source returns,
  mobile links/focus/Escape, active/expanded/collapsed sidebar and synthetic long-name stress pass.
  Four zoom levels produce identical A4 output geometry, two sheets, ~50 × 30 mm measured pitch;
  actual printer/stock alignment and system print dialog remain operator acceptance.
- Host interruption cleared initial temporary logs. Guarded exact recovery retired the old disposable
  preview with zero residual owned resources; the fresh preview proved repeat-seed preservation.
  Final cleanup/preservation evidence is in the [handoff](labels-navigation-ia-handoff.md) alongside
  screenshot/print measurements. Persistent UAT and other protected environments were preserved.
- IA-FREEZE-001 is **implemented**. **FUNCTIONAL_IA_FREEZE_READY** records no unresolved major v0.1
  workflow/IA decision; independent visual acceptance, canonical QA and release gates remain.
  No stage, commit, push, delivery, dependency updates, Location labels, QR/scanning, PDF feature,
  future domains, global visual normalization or release benchmarking. **READY_FOR_VISUAL_REVIEW**.

## 2026-10-13 — IA-FREEZE-001 operator corrections: QR, presets and Settings

- Continued the same `4ff7` / `feat/ia-freeze-001` candidate. Restored exact-source QR for all four
  material types using a persisted validated public origin, H correction, protected quiet/pattern
  regions, inset category vectors and an immediately adjacent Small fallback. Unconfigured or
  overly dense destinations block both Print and browser-menu label output. Picker/normal selected
  rows omit UUIDs and use human/domain context; exact links and advanced content retain IDs.
- Three direct physical A4 presets: **40 × 20 / 5 × 13**, **50 × 30 / 4 × 9**,
  **70 × 40 / 2 × 7 mm**. Each defines margins, QR size, typography and metadata density.
  Preset selection stays above composition; metadata gets a full-width band below the QR.
  Temporary size overrides do not alter the saved default. Stored-material QR hash changes focus
  the exact retained item even on an already-open Harvest.
- Small full-page **Settings** holds public QR origin, default preset and Tools links. Migration
  **20261013_0042** adds only typed singleton application preferences, default Medium/unconfigured;
  reads require authentication and writes CSRF. Security/login origin remains independent.
  Tools leaves primary navigation; five groups and Maps remain. Compact Settings / Theme / Sign out
  controls stay reachable. Theme presents planned modes truthfully and changes/persists no theme.
- **244 affected frontend tests / 13 files**, then final **81 / six** after corrections pass;
  **33 backend unit tests** and **seven PostgreSQL settings/migration regression tests** pass.
  Historical migration head checks now resolve code head without weakening retention assertions.
  Formatting, frontend/backend lint, strict typing, production frontend build, both API drift checks,
  graph **103** and whitespace pass. Broad pre-existing Alembic autogenerate differences are recorded
  honestly in the [handoff](labels-navigation-ia-handoff.md); the new table/cycle checks pass.
- Final actual zoom matrix **1440×844 80/100/125/150%; 1024×844 100/125%; 390×844 100%** has no
  document horizontal overflow. Each preset covers one/full/partial/multi-page output and exact
  source context; 21 zoomed print probes preserve physical dimensions. **48 independent decoder
  checks** pass across all categories/sizes, inset/adjacent glyphs and complete printed-size labels.
  Physical printer/stock/system-dialog acceptance remains with the operator.
- Disposable preview uses existing fixtures, preserving repeat seed state, and was retired with
  zero owned residual resources. This task did not reset/reseed/sync/migrate persistent UAT or write
  its settings. Protected runtime/Git identities and other database digests match; the live UAT
  digest differs, with authentication activity observed and full data equivalence unproven.
  Final read-only UAT status reported healthy services, revision **0042**, ready fixture **v4/66**,
  configured QR and Medium default. See the handoff for the comparison limits.
  The **2026-10-14** read-only recheck after host interruption finds frontend/backend stopped,
  database healthy, revision **0042** and fixture **v4/66** unchanged; no restart was performed.
- **FUNCTIONAL_IA_FREEZE_READY**, feature still **implemented**. No canonical `make feature-verify`,
  stage, commit, push or delivery; no dark mode, theme persistence, PDF feature, mobile QR capture,
  Location labels, dependency updates or global visual review. **READY_FOR_VISUAL_REVIEW**.

## 2026-10-14 — IA-FREEZE-001 final Settings / Labels information cleanup

- Continued `4ff7` / `feat/ia-freeze-001` without lifecycle advancement. Settings now shows General
  and compact Tools links on one page; no tab strip or duplicate label-size configuration.
  QR General Save retains validation/normalization/persistence and focuses via the existing direct
  QR Settings link. Labels → Print format keeps temporary size changes and adds explicit persisted
  **Set as default** / **Default**, saving/error/retry states. Each preference save preserves the
  latest other field in the existing API contract.
- Signed-in identity precedes labelled gear Settings and quiet Theme utilities, with Sign out as a
  separate account action. Expanded/sidebar reopen, narrow/zoomed desktop and mobile More remain
  accessible. Theme switching remains deferred. Physical labels retain scientific-name/cultivar
  typography, separate material type and record identity; classification hierarchy is excluded.
- Baseline **49 / three files** and final **136 focused frontend tests / five files** pass. Scoped
  formatting/lint, strict TypeScript and production build pass; feature graph/whitespace are checked
  at handoff. No backend/API/migration/dependency changes in this cleanup.
- All **seven** requested actual-zoom boundaries pass; **21** screen/print preset geometry probes
  retain physical width/height within **0.02 mm**. No horizontal page overflow. Short visible content
  with omitted optional metadata gives no Small warning; a long visible stock name still warns.
  Connected-browser clicks verify normalized General save, explicit defaults and bidirectional links.
- Current `cleanup-*` evidence and the updated [handoff](labels-navigation-ia-handoff.md) supersede
  preceding Settings/footer screenshots; the unchanged QR implementation retains prior decoder proof.
  The exactly owned disposable review preview is retired after review; protected-environment and
  fixture/media retention results are recorded separately in its preservation evidence. The complete
  protected snapshot for this cleanup matches; prior checksum uncertainty is not retroactively resolved.
  Final read-only persistent UAT status reports all three services healthy at **0042**, fixture
  **v4/66** ready. No UAT restart or mutation was performed by this task.
- **FUNCTIONAL_IA_FREEZE_READY** is reconfirmed; IA-FREEZE-001 remains **implemented**. Physical
  printer/system-dialog acceptance and independent visual/canonical QA remain subsequent phases.
  No UAT reset, stage, commit, push, delivery, dark mode or global visual review.
  **READY_FOR_VISUAL_REVIEW**.

## 2026-10-14 — IA-FREEZE-001 final Theme / QR editor / physical content correction

- Continued the same candidate. Theme is now one truthful SVG monitor → sun → moon icon cycler,
  with shared ephemeral footer state and keyboard/title/accessibility labels. No popover, visible
  prose, applied colors/tokens, backend write or theme persistence. Settings/Theme utilities remain
  separate from quiet Sign out.
- Labels QR destination now opens a small TaskDialog for the same persisted General setting.
  Shared save logic preserves the latest default; normalized Save regenerates QR in place without
  losing sources, copies or temporary preset. Cancel/pristine dismissal, guarded dirty dismissal,
  pending-save protection, validation/retry and Edit focus restoration retain the UI contract.
- Physical sheets now contain only scientific botanical name, optional roman cultivar/common name,
  exact-source QR and tiny category glyph. Existing BotanicalIdentity `common_name` is used without
  inventing names. Stock names, type text, UUIDs, Location/source/quantity/acquisition and taxonomy
  hierarchy do not print. Application chooser/details retain rich non-printing context. Overflow
  measures only rendered names. QR sizes are **16/24/32 mm**; scientific type **8/10/12 pt**.
- Baseline **53 / three files** and final serial **147 focused frontend tests / six files** pass.
  Scoped formatting/lint, strict typing and production frontend build pass. Initial unchanged-test
  timeouts under full swap disappear in the final serial run; no assertions/timeouts were weakened.
  No backend/API/schema/dependency change or canonical verification in this correction.
- All **seven** actual-zoom boundaries and **21** screen/print preset geometry probes pass within
  **0.02 mm**; 12 optional-name/preset combinations fit, and 12 long-name/preset cases warn on real
  clipping. Native browser interaction confirms cycling, dirty Escape, normalized Save and return
  focus. **48 ZXing checks** pass on 12 actual print-media A4 samples, including full labels and blur.
  The initial screen-media PDF probe was replaced before acceptance; all accepted samples are A4.
- Exactly owned review project `florabase-uat-preview-smoke-bff8e2a5be73` is retired with zero residual
  resources. Domain/fixture/media retention matches. Protected runtime/Git identity and non-UAT
  digests match; live UAT raw digest differs with authentication activity observed, but exact cause
  and full data equivalence remain unproven. No protected UAT reset/reseed/sync/migration/settings
  write; no live-state rollback. Current `final-*` evidence supersedes previous UI/print screenshots.
- [Handoff](labels-navigation-ia-handoff.md) reconfirms **FUNCTIONAL_IA_FREEZE_READY**; status remains
  **implemented**. Actual themes, physical printer/system-dialog acceptance, independent visual/
  canonical QA and future capabilities stay deferred. No stage, commit, push, delivery or global
  visual review. **READY_FOR_VISUAL_REVIEW**.

## 2026-10-14 — IA-FREEZE-001 independent delivery review in progress

- Independent review confirmed the v0.1 four-source label contract, exact-route QR content, Settings /
  Labels shared destination, three physical presets, botanical-only label output, stored-material
  identity, route/navigation grouping and the truthful icon-only Theme preview. Live persistent UAT
  is owned by this feature worktree, healthy at revision **0042** with fixture **v4/66** ready. A
  normal synthetic login, General settings read and temporary SeedLot composition succeeded; no
  settings or collection records were written.
- Independent settings unit tests: **23 passed**. Isolated PostgreSQL settings API, migration and
  schema-table regression tests: **26 passed**. The first broad integration attempt found one stale
  expected-table assertion; it was corrected to include `application_settings`, and the exact focused
  suites passed. The stale Settings navigation test was corrected to follow the Settings → Tools links.
- The first authorized canonical run reached workflow safeguards and stopped because the new backend
  settings package was not classified by the verification-impact map. The package is now explicitly
  marked FULL, satisfying the repository's production-module coverage rule while retaining the most
  conservative verification path. The canonical gate must be rerun on this updated tree.
- Isolated serial Labels/frontend lazy-navigation suites passed **54 + 1**. A broader selected frontend
  run passed **246/249**, with three Label cases timing out while host swap was full and unrelated
  Docker workloads were consuming CPU; the affected complete Labels suite and lazy-navigation case
  passed separately without changing timeouts. Independent ZXing-C++ rerun passed **48/48** actual
  print-sample checks. Canonical verification is now authorized and pending; IA-FREEZE-001 remains
  **implemented** until its exact-tree gate passes.
- Historical live-UAT raw-database checksum variance remains unresolved: prior snapshots lack a
  per-table baseline, so its exact cause and complete data equivalence cannot be reconstructed.
  Runtime/container identity, fixture integrity and available domain/media checks show no evidence of
  loss. No state was rolled back to force digest equality. The required login refreshed normal
  authentication-session activity during this review.
- [Updated independent-review handoff](labels-navigation-ia-handoff.md). **FUNCTIONAL_IA_FREEZE_READY**
  remains the product/architecture assessment. Physical printer acceptance remains deferred.

## 2026-10-14 — IA-FREEZE-001 independent verification passed

- Independently reviewed the complete candidate and final IA evidence. Confirmed the four supported
  source types, shared contextual/central label composer, botanical-only physical content, exact
  record QR routes, shared persisted QR origin, Settings → Tools routes, five primary navigation
  groups, Maps subgroup, utility footer and truthful theme icon cycler. Reviewed uncertainty and
  Stored material identity semantics; no major v0.1 workflow or architecture blocker remains.
- Canonical `make feature-verify` passed on the final candidate: backend **939/939**, PostgreSQL
  integration **734/734**, frontend **664/664**. Workflow/resource safeguards, format, lint, strict
  typing, generated API drift, both production builds, feature graph and whitespace checks passed.
  Full migration cycle **0041 → 0042 → 0041 → 0042** passed; its disposable resources were retired
  with zero container/network/volume residuals. Exact-tree receipt recorded.
- QR decoder rerun passed **48/48** checks over 12 actual print-media A4 samples. The seven viewport /
  zoom boundaries, 21 preset geometry probes, optional-name fit cases and clipping stress evidence
  are retained in `docs/review/labels-navigation/`. Real printer/stock alignment remains deferred.
- QA-only corrections updated the schema expectation for `application_settings`, routed legacy
  Import / Export test navigation through Settings → Tools, and allowed five seconds for lazy-route
  assertions under full-suite load. The Quality-only Compose profile runs Vitest with one worker so
  the complete jsdom suite avoids host contention; no test files, product behavior or assertions
  were removed or weakened.
- Persistent UAT remains owned by this feature tree, healthy at revision **0042**, fixture **v4/66**.
  The reviewer performed only login, settings read and temporary browser composition. Historical raw
  database checksum variance remains unresolved without a per-table baseline; no evidence of loss or
  corruption was found and no live UAT data was changed or reverted.
- IA-FREEZE-001 is **verified** and **FUNCTIONAL_IA_FREEZE_READY**. Commit, protected delivery and
  conservative finish are the remaining lifecycle steps. See
  [the verified handoff](labels-navigation-ia-handoff.md).

## 2026-10-14 — GLOBAL-VISUAL-001 normalization candidate

- Audited all **22 primary route states** on the preserved delivered UAT before production edits;
  inspected important Collection detail/edit flows and creation forms. Classified blockers,
  normalization and polish in [the visual inventory](review/global-visual/audit.md).
- Shared PageHeader/DirectoryTools align search, supported Saved Views, live filter drawers, native
  single-select choices and removable summaries. Collection, Explore and Sourcing now use grouped
  operational rows, bounded forms, consistent controls, action hierarchy and botanical typography.
  Taxonomy heading hierarchy and native-dialog focus containment were corrected. Dashboard, Activity,
  Settings, Labels, domains, routes and frozen navigation remain regression references.
- Frontend **666/666 across 64 files** passed with unchanged repository Vitest configuration, one
  file per process to bound host memory. After the final Taxonomy heading/surface correction, its
  focused suite passed **7/7**. Final labelled touch-target CSS is covered by subsequent strict
  TypeScript, zero-warning ESLint, Prettier and Vite production build checks, all passed. Feature graph
  **104 valid** and `git diff --check` passed. Exact scopes are recorded in the evidence JSON.
- Baseline `make check` passed backend formatting (**392 files**) then stopped at exact-lockfile
  frontend dependency installation due npm registry timeout. Existing locked UAT dependencies were
  copied read-only; no manifest/lock changes. Backend, integration and API drift stages were not run
  for this frontend-only change. Canonical `make feature-verify` was explicitly prohibited and not run.
- Baseline/final bundle comparison: initial JS **+107 gzip bytes**, all JS **+2,530 gzip bytes**,
  CSS **+2019 gzip bytes**, font assets unchanged. No runtime resource benchmark is claimed.
- Evidence includes 16 before screenshots, real candidate sign-in, isolated test-layout screenshots,
  **15** width probes with no horizontal overflow and **9** passing semantic contrast pairs. Isolated
  fixtures differ from UAT and do not prove authenticated candidate behavior; exact capture dimensions
  and scope are documented. True browser zoom was unavailable in the enabled browser surface.
- Feature Review resources belong to `a165`; preserved UAT belongs to `4ff7` (revision **0042**,
  fixture **v4/66**). Automatic approval review rejected fabricated CSRF success and temporary
  replacement of the other owner's frontend. Neither rejected command ran. The user explicitly authorized authenticated candidate review, but the supported UAT helper has no
  frontend-only replacement command: `make uat-preview-up` rebuilds and starts both backend and frontend.
  The exact original frontend image/container/source mount, backend/database container images, volume
  creation identities and network ID are recorded in `review/global-visual/uat-frontend-restoration-baseline.json`.
  No replacement ran because it would violate the requirement to keep backend unchanged and use only
  repository-supported scoped actions. UAT remains stopped with DB/media/dependencies preserved; no
  seed/reset/source sync, volume deletion or operator-record edit occurred. Temporary previews/tabs were closed.
- GLOBAL-VISUAL-001 remains **in_progress**, with a concrete unstaged/uncommitted candidate and
  [implementation handoff](global-visual-001-handoff.md). No stage, commit, push, delivery, dependency
  update, actual theming or domain/IA redesign occurred. Full visual acceptance remains outstanding.

## 2026-10-14 — GLOBAL-VISUAL-001 supported Feature Review fixture path

- The operator authorized removal of stopped, obsolete `a165` Review state through guarded
  `feature-review-remove`, after exact ownership/foreign-user and primary-Git checks. Candidate `996d`
  now owns healthy Feature Review at localhost:15174, schema **0042**, with its existing `owner`.
- Added `make feature-review-seed`, reusing the v4/manual-review fixture/domain services. Exact role,
  project, worktree, volume/network ownership/users, live DB/media mounts, health and migration-head
  checks precede writes. Runtime checks independently restrict it to `florabase_review` and Review
  bookkeeping. Existing owner credentials/sessions remain intact; no UAT data/media is copied or read.
- Review persists separate `.review-*` identity/ledger/lock files. Managed IDs/media are validated on
  repeat seed; edits survive, additive extensions run once, and ambiguous/interrupted or missing state
  refuses. The expected shared coverage is **v4/66**, or **68** with the optional approved WFO snapshot.
- Focused checks pass: environment **33**, UAT workflow/source **19 + 15**, Review fixture **21**
  (20 guards and live persistence), existing additive fixture **5**, Ruff lint/format and strict typing
  for five related helper files. The live read-only current-Review preflight passes. Canonical
  verification and real disposable Compose smoke were not run.
- After initial automatic approval rejection of the attached authorization, the operator directly
  authorized the scoped seed in chat. The first permitted run refused Alembic's canonical geographic
  references before collection writes; corrected/tested the guard to allow canonical references and
  still reject custom/operator data. Supported seed and repeat seed now pass at **v4/66**, ready.
  Live tests verify managed IDs/counts/media and rollback-only operator edit preservation; the owner
  identity/credential hash matches before seeding. Normal browser sign-in with `owner` succeeds.
- Browser inspection confirms populated Dashboard, Seeds, Journal, botanical identities and Orders;
  Settings/Labels/tools remain reachable. Authenticated screenshots and preservation evidence are in
  `docs/review/global-visual/`. The optional WFO snapshot is absent and the QR base URL remains blank;
  source setup and printing configuration retain their normal operator requirements.
- Review remains healthy/running for manual inspection. Protected UAT/DEV/Stable Preview/production
  resource metadata and primary Git match the pre-seed snapshot; no UAT records/media were accessed.
  Updated workflow documentation and [handoff](global-visual-001-handoff.md). All candidate changes remain
  unstaged/uncommitted; no canonical gate, delivery or product/visual edits occurred in this addition.

## 2026-10-14 — GLOBAL-VISUAL-001 first operator page-family refinement

- Dashboard search/tools now occupy the shared PageHeader row and wrap responsively. Compacted
  metrics/activity/spacing preserve readable type and 44px controls. Default desktop filters use a
  wider responsive drawer and compact related grids, fitting 1440×844 without vertical scrolling.
- Seeds uses explicit Select records/Exit selection, count/Select visible/Clear and an Actions menu
  containing only Move to location. Existing eligibility, scope resets, atomic move and 100-record
  bound remain. The shared pattern propagates to existing Sowings/Plants/groups/Stored material only.
- Shared FormSections distinguishes create progression from direct edit/save on every section;
  equivalent Sowing, Plant/group, site and profile edits opt in. SeedLot alone gains a comfortable
  60rem workspace, restrained height-dependent sticky actions and focus scroll clearance.
- SeedLot breadcrumb/identity/actions are unified; creation remains in the directory. Overview uses
  a main content column and grouped facts surface, compact empty Upcoming and existing tabs/media.
  Other detail families retain their different content hierarchy; no mechanical grid propagation.
- Authenticated Review browser checks cover the requested first-family states, normal desktop/mobile
  dimensions and explicit effective-space proxies. A normal Acquisition save of unchanged fixture
  values succeeded. Sibling edits were cancelled and accepted Journal/Settings/Labels checked read-only.
  Actual 125%/150% browser zoom remains unverified after unavailable/stalled shortcuts.
- Focused tests pass: first family/primitives **65**, current consumers **118**, Activity/Settings/Labels
  **129**; final SeedLot/form/bulk rerun **48** and bulk focus assertion rerun **12** overlap those counts.
  Final TypeScript, targeted ESLint, formatting, Vite build and diff whitespace checks pass; staged
  diff is empty. Final mobile inspection resolved footer overlap with fixed navigation by limiting
  sticky actions to taller desktop viewports; normal mobile actions are fully reachable by scrolling.
- Following an interruption, Review frontend/backend were stopped with its DB healthy. Supported
  `feature-review-up` recovered candidate-owned Review, preserving owner/session, DB **0042** and
  fixture **v4/66 ready**. No seed/reset/remove or UAT operation ran in this refinement.
  [Handoff](global-visual-001-handoff.md) and [evidence index](review/global-visual/first-family/README.md)
  distinguish initial normalization evidence from this refinement. Feature remains **in_progress**;
  no canonical gate, stage, commit or delivery.

## 2026-10-14 — GLOBAL-VISUAL-001 second refinement acquisition decision boundary

- Inspected the operator's requested Dashboard/SeedLot continuation and ORDER-001 contracts,
  backend services/integration assertions, Supplier consumers, existing routing/dialog and form paths.
  **NEEDS_PRODUCT_DECISION**: Order-derived commercial Supplier requires an explicit preservation
  policy for existing purchased lots without Orders, known lot Suppliers on unknown/unlinked Orders,
  and Order Supplier corrections currently blocked by linked independent Supplier knowledge.
- Unknown Order date/Supplier/reference/total already fit the existing nullable/PartialDate model;
  no invented date, automatic Order or placeholder domain is needed. No application or schema
  implementation began at the requested ambiguity boundary.
- Recorded the unscheduled post-v0.1/v1.0 Dashboard review in the roadmap. The requested v0.1 module
  removal, modal edit and detail/media refinement await the decision; no placeholder UI was added.
- Read-only Review status confirms candidate-owned healthy frontend/backend/DB, revision **0042**,
  fixture **v4/66 ready**. No Review reset/remove/reseed/restart, UAT action, stage, commit, delivery or
  canonical gate. [Handoff](global-visual-001-handoff.md) records evidence and exact pending decisions;
  this inspection claims no new runtime test or visual acceptance.

## 2026-10-14 — GLOBAL-VISUAL-001 second refinement after Supplier decision

- The operator resolved the boundary: Order Supplier is contextual UI authority only when known and
  linked. SeedLot Supplier remains independent persisted knowledge/fallback. No ORDER-001 persistence,
  reconciliation, acquisition-date, unlink or conflicting-Order-correction rule changes; no migration.
- Removed only Dashboard's Propagation/Sourcing/Botanical coverage rendering and unused CSS. The
  existing services/data remain, with a later configurable-module review recorded in the roadmap.
- SeedLot Edit now uses a native contextual workspace above the mounted Details tab or directory
  inspector/search/filter state, with bounded desktop geometry, internal panel scrolling and actions.
  Dirty Escape/Cancel/Back and pending/subtask dismissal are guarded; focus returns to Edit. Direct
  edit URLs/reload use the same full-page fallback; no other entity editor is migrated.
- Acquisition shows known linked Supplier read-only, retains independent editing for no/unknown
  Order Supplier and exposes existing explicit Order creation in a new tab plus choice refresh.
  Unknown date/price/Supplier facts are preserved and nothing is silently created or copied.
- Overview groups Inventory/Acquisition/Origin/Dates under At a glance; Purchase Order belongs inside
  Acquisition. SeedLot opts into compact attached Photos with explicit details link and overflow
  management; uploads, protected copies, external privacy and unlink confirmation remain supported.
- Focused tests pass **73** across SeedLot, Dashboard, Photos, purchase-context UI and Orders. Coverage
  includes backgrounds/tabs, route fallback, every-section Save, dirty history refusal without added
  entries, focus, Supplier adaptation/unlink/date retention and an explicitly created unknown Order.
  Serial reruns resolved transient loading timeouts during exhausted host swap without weaker checks.
- Review recovery uses only supported `feature-review-up` after services stopped; existing DB remains
  at **0042**. No reset/remove/reseed, UAT action, stage/commit/push/delivery or canonical gate. The
  [handoff](global-visual-001-handoff.md) records the resolved product decision and this pass's scope.

## 2026-10-15 — GLOBAL-VISUAL-001 second refinement review handoff

- Final focused validation: **107 tests** across nine suites (73 core and 34 shared regressions),
  strict TypeScript, targeted zero-warning ESLint, Prettier, production Vite build and diff whitespace
  pass. DashboardSearch's recurring first-load module-transformation timeout is resolved by awaiting
  the real lazy-module import in suite setup; assertions/timeouts and production routing are unchanged.
- Second-family evidence covers seven states at six viewports, native modal focus/scroll, authenticated
  Save to retained Photos, browser Back and directory-context return. Actual browser zoom remains an
  operator check. Acquisition screenshots precede the final checkbox alignment rule; a browser URL
  policy rejection prevented refresh. These limits are explicit, with no claim of visual acceptance.
- Supported Review recovery after interruption preserved the existing owner/session, revision **0042**
  and synthetic **v4/66 ready** data. Final status is healthy at localhost:15174. No reset/remove/reseed,
  UAT/DEV/Stable/production change, canonical gate, staging, commit, push or delivery. Candidate remains
  **in_progress**, unstaged/uncommitted, ready for operator inspection. Updated handoff and evidence.

## 2026-10-15 — GLOBAL-VISUAL-001 consolidated SeedLot family refinement

- Shared the existing Sowings directory split with Seeds, removing the local narrow preview cap;
  SeedLot Details now uses the available workspace width while prose remains bounded. No Sowing or
  Plant visual review/redesign began. Dashboard's final four-section scope and wide drawer remain.
- Added guarded native backdrop dismissal and explicit subtle tab hover/selection. Navigation reserves
  intrinsic wrapped height and focus clearance; the scrolling panel now has focus padding on all sides.
- Acquisition conditionally shows independent Supplier/PartialDate inputs only without an Order.
  Linked transaction facts are read-only, with independent lot knowledge retained and visible. Existing
  reconciliation, explicit date copy, unlink retention and stale/version safeguards remain unchanged.
- SeedLot Photos is now an image-first 4:3 mini-gallery with asset details links, named always-reachable
  overflow, hover/focus Open hint, concise metadata and a compact opt-in external privacy placeholder.
  Default Photos consumers retain their existing presentation. Lineage capability/semantics remain.
- Initial focused tests pass 64 and shared regressions 138. Fresh live visual acceptance is pending a
  new authenticated HTTP browser tab because retained error-page tabs are refused by browser policy;
  no workaround or new screenshot claims. Handoff records the full remaining responsive/zoom checklist.
- Review status remains healthy, candidate-owned, revision 0042 and v4/66 ready. No reset/remove/reseed,
  UAT/DEV/Stable/production action, canonical gate, stage/commit/push/delivery. All work stays dirty.

- Final code validation passes **202 tests in 14 suites**, TypeScript, zero-warning targeted ESLint,
  formatting, production build and whitespace. [Third-family evidence index](review/global-visual/third-family/README.md)
  records exact scopes and pending fresh browser review; no new visual acceptance is claimed.

## 2026-10-15 — GLOBAL-VISUAL-001 consolidated live review completion

- Fresh authenticated HTTP Review access resolved the retained error-tab block. Captured ten states
  at six viewport sizes (60 probes/screenshots), plus native focus, gallery/menu/direct-route and
  read-only Sowings/History/Settings/Labels evidence. Saved probes show no horizontal overflow.
- Live Acquisition inspection found inherited fieldset/legend/action spacing. Scoped spacing and
  transaction/fallback-facts grouping now fit both ordinary states at 1440x844 with no panel scroll
  (414px client/scroll height). Shorter viewports retain safe internal scrolling and visible actions.
- First/last editor tab focus rings and mobile controls remain intact. Gallery first row fits with
  header/tabs/tools; keyboard/touch overflow, cancelled metadata edit and exact media navigation work.
  Clean Back and a normal unchanged save restore Photos and the Edit trigger. Native dirty backdrop
  prompt was observed; live refusal and actual browser zoom remain operator acceptance.
- Strengthened the missing-history-event regression and fixed a close/fallback timing race: a
  contextual edit entry cannot reopen as a direct editor while browser Back is processing. Concise
  date/Supplier help retains explicit no-invented-date/origin semantics. No persistence/API change.
- No new fixtures or links were added. The reviewed SeedLot lacks external gallery/producer states;
  these have focused tests, with live fixture limits recorded. Normal CSRF refresh after the temporary
  direct-link tab used page reload; no session fabrication. One unchanged save may update metadata.
- Review stays running, revision 0042 and managed fixture v4/66 ready. All candidate work remains
  unstaged/uncommitted; no canonical verification, delivery or protected-environment operation.

- Final serial SeedLot rerun passes 45, including the strengthened fallback/focus regression. Across
  the current focused reports, **202 unique tests in 14 suites pass**. Source typing, zero-warning
  targeted ESLint, production build and whitespace pass. Host swap pressure caused intermediate
  unrelated timeouts; the serial rerun passed without weaker assertions/timeouts. Evidence is ready
  for operator inspection, with actual zoom and unavailable fixture states explicitly unclaimed.

## 2026-10-16 — GLOBAL-VISUAL-001 final SeedLot-family refinement

- Create SeedLot is one full-width ordered page with shared fields/validation, optional secondary lot
  label, visible section errors and final Cancel / Add seed lot. Edit retains its contextual modal,
  guarded dismissal, quiet tabs and direct-URL fallback. No broad Sowing/Plant redesign began.
- Shared PartialDate precision now stacks above fixed calendar-part slots. Independent Acquisition
  controls align horizontally; normal Unknown/linked states fit the desktop panel, and known parts
  scroll safely within it. Order, collection, Journal, Harvest and native Schedule dates retain their
  semantics. Sowing interaction tests preload their component; separate lazy-loading coverage remains.
- SeedLot Overview is a compact current-state dashboard: lifecycle/quantity/storage, readable
  Acquisition/Origin and inline date facts, beside natural-height Upcoming/Notes. Removed the duplicate
  Sowings-tab action, aligned compact empty Lineage, and emphasized exact/approximate/unknown remaining
  quantity. No persisted baseline exists, so no ratio/progress denominator was invented.
- New Photos/Media external images default to the existing guarded local-copy operation, with explicit
  reference-only opt-out and retained-reference retry after failure. Protected thumbnail/content paths,
  explicit primary selection and all fetch-safety rules remain. Controlled HTTP/PostgreSQL proof covers
  save/reload/refresh/remove without read-time remote fetches; no live arbitrary host was contacted.
- Focused/shared frontend checks pass **270 unique tests in 17 suites**; media backend checks pass
  **69 unit + 15 PostgreSQL tests**, with disposable cleanup verified. Intermediate cold Sowing import
  timeouts were resolved in interaction setup without weaker assertions/timeouts; the loading test passes.
- [Final SeedLot evidence](review/global-visual/final-seedlot/README.md) retains 57 responsive observations
  without horizontal overflow, additional Order Day evidence and exact validation summaries. Reduced
  viewport zoom proxies are labelled; actual zoom and native dirty-prompt handling remain operator checks.
  Browser automation stalled during an unsaved Order cancellation; it is not claimed as a passed check.
- Review stopped during the pause and was restarted only through its supported guarded workflow. The
  same owner/password, volumes and v4/66 dataset remain; schema is 20261013_0042. No reset/remove/reseed,
  UAT/DEV/Stable/production action, canonical gate, stage, commit, push or delivery. Candidate stays dirty
  and GLOBAL-VISUAL-001 remains in_progress for operator visual review.

- Final source checks pass strict TypeScript, zero-warning targeted ESLint, Prettier, production build
  and diff whitespace; staged diff is empty. SeedLot bundle is 45.60 kB / 12.39 kB gzip, main
  227.89 kB / 70.84 kB gzip. Supported Review status confirms frontend/backend/DB healthy and v4/66
  ready. Viewport overrides are reset and authenticated Overview remains available for manual review.

### 2026-10-16 — GLOBAL-VISUAL-001 detail empties and form labels (candidate)

- Informational Details empties now use the normal tab gutter and natural message height without
  borders; SeedLot Sowings and root Lineage establish the grammar, with safe related-record reuse.
  Photos retains its restrained gallery placeholder and all media actions.
- Added a small caption-only FieldLabel with a muted semantic-token asterisk. Removed optional-label
  suffixes while preserving explanatory prose. Audited actual schemas: SeedLot identity is required;
  defaulted Source/Lifecycle and nullable Supplier remain unmarked, including Purchased.
- Native/ARIA semantics follow existing requirements, including selected date parts, explicit quantity
  modes, Order price/currency pairing, media attribution and movement destinations. Location's Used for
  legend exposes its existing at-least-one rule through the group description; individual checkboxes
  remain independently optional. All 54 existing native/reference required expressions are unchanged.
- Focused/shared/sibling frontend validation passes **448 unique tests across 27 files**. The final
  Location group-caption change additionally passes **15 focused Location tests**. Five intermediate
  Notes query ambiguities were resolved by selecting the intended textarea/region, without weaker
  product assertions. Coverage includes conditional states, unchanged payloads, accessible names,
  keyboard/focus behavior, lightweight empties and the Photos exception.
- [Labels/empty-state evidence](review/global-visual/labels-empty/README.md) records **29 observations**
  across 1440x844, 1024x844 and 390x844 at 100%, with no horizontal document overflow: empty Details
  tabs, full-page Create, Edit Essentials/Acquisition and selected Month precision. No product records
  were saved. The operator resolved one browser stall while discarding an unsaved inspection draft;
  automated native-prompt handling is not certified. Viewport override is reset.
- Supported Review status confirms the same candidate owner, healthy frontend/backend/DB, schema
  20261013_0042 and existing managed v4/66 ready dataset. No reset/remove/reseed or UAT/DEV/Stable/
  production operation. GLOBAL-VISUAL-001 stays in_progress and all candidate edits remain unstaged/
  uncommitted; canonical verification, stage, commit, push and delivery remain unperformed.
- Final strict TypeScript and production build pass. SeedLot JS is 45.14 kB / 12.40 kB gzip; main
  is 228.15 kB / 70.92 kB gzip. New evidence and validation summaries are retained with the handoff.
- Final targeted ESLint passes with zero warnings, all 47 touched frontend files pass Prettier,
  whitespace checks pass and the staged diff is empty. Canonical feature-verify remains unrun.

## 2026-10-16 — GLOBAL-VISUAL-001 SeedLot dashboard / Photos / picker reference

- SeedLot Overview now has one subtle three-column current-state band, stronger values above quieter
  labels, then Acquisition/Origin and Dates/Upcoming in a semantic desktop grid. Restrained dividers
  separate groups; notes occupy the final row at natural reading width. Narrow/mobile layouts collapse
  without tiny columns. Existing facts, links, PartialDate/unknown/quantity semantics and conversion
  context remain; no other entity Overview was migrated.
- Compact Photos removes the repeated visible heading and global helper, retaining an accessible
  section name. Right-aligned actions precede the accepted gallery/empty placeholder. Live existing
  external media retains tile-specific host/privacy/Preview once; no remote image was fetched.
- Shared ReferencePicker now anchors to the control alone: the original 45.984px field/help gap becomes
  4px at matched width. Bounded menus fit viewport/clipping panels and can open above; keyboard active
  options scroll internally, selection restores focus and Escape first dismisses an open picker.
  Native Order/Plant/Sowing selects remain native, with no form redesign.
- Focused baseline passes 21 tests; final SeedLot, Photos/Media, shared picker and representative
  Order/Plant/Sowing/Bulk/Labels coverage passes **247 unique tests across 13 files**. Updated date
  assertions check semantic terms/values rather than layout whitespace. Strict TypeScript,
  zero-warning targeted ESLint, eight-file Prettier, production build and whitespace checks pass.
  SeedLot JS: 45.38 kB / 12.42 kB gzip; main: 228.15 kB / 70.91 kB gzip.
- [Dashboard/picker evidence](review/global-visual/seed-dashboard/README.md) retains **30 observations**:
  all requested views at 1440x844, 1024x844 and 390x844 at 100%, representative shared/native consumers
  and one additional short-viewport menu fit. No horizontal overflow; all measured menus match input
  width and 4px separation. No records/media were saved, linked, removed or fetched remotely.
- Existing Review stays running/authenticated on the same candidate: frontend/backend/DB healthy,
  schema 20261013_0042, managed v4/66 ready data preserved. Viewport override reset; normal-size
  operator-ready capture retained. No reset/remove/reseed, UAT/DEV/Stable/production operation,
  canonical feature-verify, stage, commit, push or delivery. Candidate remains dirty and in_progress.

## 2026-10-16 — GLOBAL-VISUAL-001 operator acceptance and independent QA checkpoint

- The operator completed the authenticated Feature Review walkthrough and accepted the reviewed
  scope, with SeedLot as the Collection-family reference. Independent review inspected the complete
  candidate diff by feature area and representative Dashboard, Seeds, mobile, SeedLot Overview and
  external-image privacy captures. No material production, domain, navigation, accessibility or
  workflow defect was found.
- Independent focused Quality frontend validation passes **378 tests across 23 files**, including
  App/navigation, Dashboard, SeedLot and Order reconciliation, Plant/Sowing, media/Photos, Lineage,
  Labels, shared forms, pickers and filters. The new Review fixture guard suite passes **20 tests**;
  its one live Review preservation probe is intentionally skipped in this offline focused run. The
  existing environment ownership suite passes **33 tests**. The direct host invocation of the Review
  fixture tests was not counted because system Python 3.12 lacks the repository's UUIDv7 API; the
  valid project Python 3.14 container run passed.
- `make workflow-resources` reports Feature Review running on this candidate with its three own
  volumes; UAT containers are stopped with their three persistent volumes retained. DEV's database
  is running from its primary source; its application containers are stopped. Unknown legacy
  resources and shared BuildKit cache are retained. The repository verification plan selects FULL
  backend, frontend, integration and build scopes.
- 125%/150% evidence remains labelled viewport proxies. Actual tab zoom was not automatable through
  the available browser surface; the operator's completed visual review is the acceptance evidence
  for the reviewed scope, and this tooling limitation remains explicit.
- Canonical `make feature-verify` passed on the corrected candidate tree. The first attempt caught one
  Prettier-only issue in `PlantScreen.tsx`; the repository Quality formatter corrected that file, and
  the complete gate was rerun. FULL results: backend **939 passed** (735 integration deselected in
  unit run), frontend **707 passed across 66 files**, PostgreSQL integration **735 passed** (939
  unit tests deselected), environment workflow **33 passed**, Review fixture guards **20 passed / 1
  expected live-probe skip**, migration cycle passed at `20261013_0042`, generated API check clean,
  Ruff/ESLint/Prettier/mypy/TypeScript clean, production backend and frontend images built, whitespace
  checks clean, and the verified-tree receipt recorded. Disposable verification resources were
  cleaned by their registered owners; persistent Feature Review remains running. Staging, commit,
  delivery and finish are the next authorized steps.

## 2026-10-16 — COLLECTION-VISUAL-001 implementation for visual review

- From clean PR #111 main `1e3df6a`, initialized the existing `ef73` worktree as
  `feat/collection-visual-001`. Sowings and Plants reuse the accepted Collection directory,
  coherent create form, contextual edit, full-width detail/Overview and compact Photos grammar.
  PlantGroup changes stay within existing shared workflows. Client validation, payloads, quantities,
  germination uncertainty, explicit lineage, lifecycle and server-authoritative operations remain.
- Added guarded contextual dismissal/focus/Back and direct edit aliases/fallbacks, including correct
  cross-record draft initialization. Shared gallery CSS now belongs to PhotosSection. Mobile record
  tabs wrap and Schedule links retain separation. No backend/API/schema/migration/dependency or
  global navigation change; no persistent UAT access or canonical gate.
- Focused tests: Sowing/Plant **76**, SeedLot **48**, shared
  Photos/Media/forms/picker/date/BULK **64**, Journal/History/Schedule/Settings **75**, and isolated
  full Labels **54**, plus propagation/reversal **14**: **331 distinct cases / 16 files passed**.
  Labels and five Plant timeouts under host pressure
  passed on unchanged isolated full-file repeats; the earlier terminated combined run is not
  counted. Strict TypeScript, targeted ESLint/Prettier, production frontend build, feature graph
  **105 valid** and whitespace checks pass. No assertions, test timeouts or validation were weakened.
- Live authenticated Feature Review records **72** state/viewport checks with no final horizontal
  overflow, plus **12** contextual-create checks and representative desktop/mobile evidence. The
  meaningful seed-usage review remains separate while its entry fields and descendant creation use
  coherent page forms. 125%/150% measurements are explicitly
  viewport proxies; actual browser zoom remains an operator check. Existing fixture **v4/66** covers
  recorded/unknown/zero germination, Plants/groups, locations, relationships, Journal and media;
  no fixture-code extension was needed.
- The operator approved replacement of obsolete `996d` Review; supported exact-owner stop/remove
  preceded candidate up/bootstrap/seed. After interruption, supported up restored the same candidate
  DB/media. Review stays healthy at `http://localhost:15174`, login `owner`, DB/code **0042**, source
  `ef73` + live unstaged changes. See [handoff](collection-visual-001-handoff.md) and
  [evidence](review/collection-visual/sowings-plants/README.md). Feature is **implemented**, awaiting
  operator visual acceptance and later independent canonical QA. No staging, commit, push or delivery.

## 2026-10-16 — COLLECTION-VISUAL-001 second operator pass

- Continued the same dirty `ef73` / `feat/collection-visual-001` candidate after the operator's
  second-pass decisions. Minimal Seed/Sowing/Plant rows now use Botanical Identity media geometry;
  source/date/location stay in Quick Preview and Details. Paired preview actions align; Plant/group
  preview adds the existing Harvest route and a meaningful media area without upscaling small images.
- CreationReversal access moved into Details headers with on-demand eligibility in a native dialog,
  real blockers/links, required observation confirmation, pending/409 guards and focus return.
  Overview uses compact relationship recaps; detailed paths use canonical Lineage, with Sowing's old
  propagation alias preserved. Full-workspace create and compact contextual Edit retain validation,
  payloads and dirty-state behavior. Shared detail empties replace large absence panels.
- Final focused tests: **223 / 13 files passed** (SeedLot 49, Plant 52, Sowing/reversal/guided 44,
  shared media/Photos/Lineage/forms/picker/date/BULK 78). Obsolete presentation expectations were
  updated while preserving business assertions; no timeout, backend test or validation was weakened.
  Strict TypeScript/production build, targeted ESLint/Prettier, feature graph **105 valid** and
  whitespace checks pass. Payload/validation/germination/reversal-submit helpers match HEAD.
- Current [second-pass evidence](review/collection-visual/sowings-plants/second-pass/README.md) records
  **90 unique state/viewport checks** without measured horizontal overflow. Representative desktop
  Origin editors fit without internal scrolling; Sowing/Plant Overviews fit, PlantGroup nearly fits.
  Actual browser zoom remains outstanding: 125%/150% checks are clearly labelled viewport proxies.
  Live fixtures expose blocked reversal; eligible/confirmation paths have behavioral test evidence.
- The existing candidate Review remains healthy at `http://localhost:15174`, DB/code **0042**, fixture
  **v4/66**. No reset, removal, reseed, collection mutation or persistent UAT/DEV/Preview/production
  operation. No backend/API/schema/dependency changes, staging, commit, push, canonical gate or
  delivery. **Implemented**, pending operator acceptance; the current handoff supersedes the first.

## 2026-10-16 — COLLECTION-VISUAL-001 third operator pass

- Continued the same dirty `ef73` candidate. Collection rows use quiet botanical serif identity and
  italic scientific names with sans operational metadata. Plant/group Lineage reverses explicit API
  traversal into ancestor-to-descendant order and appends the current subject, retaining the recorded
  extracted-group step. Shared paths turn downward at narrower widths; no inferred relationships.
- Details have at most one primary daily action, visible secondary/Edit actions and the established
  More menu for Print label/Undo creation. The existing guarded reversal dialog returns focus to More.
  Create/operation forms use the delivered SeedLot full canvas; extraction adds compact source/result/
  quantity context and plain inherited Origin. In-app history establishes category/source parents;
  Back and Cancel preserve those parents, including the source Details tab, without a global Back hook.
- Final focused checks: **318 distinct tests / 18 files passed** (core 49, App/navigation/guided 89,
  eight clean regression files 124, final complete Plant file 56). Fixed a duplicate extraction conflict
  warning; focus tests wait for required heading focus before interaction. Earlier failed/terminated
  attempts are accounted for in the evidence index. No timeout, domain assertion or validation weakened.
  Targeted Prettier/zero-warning ESLint, strict TypeScript/production build, **105-feature** graph and
  whitespace checks pass. Nine domain/payload/reversal-submit helpers match HEAD after whitespace
  normalization; backend/API/schema/migration/dependencies remain unchanged.
- Current [third-pass evidence](review/collection-visual/sowings-plants/third-pass/README.md) records
  **67 unique state/viewport checks** without measured horizontal overflow, navigation/focus observations
  and desktop/mobile captures. Actual browser zoom remains outstanding; enlarged-view checks are
  labelled viewport proxies. The preserved fixture has no extracted individual, so that four-node path
  has unit evidence rather than a claimed live capture. Prior pass evidence is marked historical.
- Read-only Review status confirms healthy current ownership, DB/code **0042**, existing **v4/66**.
  No reset/removal/reseed or collection mutation; no persistent environment touched. Left running at
  `http://localhost:15174`. All work remains unstaged/uncommitted; no canonical gate or delivery.
  Feature remains **implemented**, pending third-pass operator visual acceptance and later QA.

## 2026-10-17 — COLLECTION-VISUAL-001 fourth operator pass

- Continued the same dirty `ef73` candidate. Consolidated page form/grid/footer rules, removing
  detached footer surfaces and duplicate CSS. Full-page footers share SeedLot gutters/border/padding
  and a transparent canvas; contextual Edit keeps its bounded footer. Hidden redundant captions retain
  meaningful accessible names for PartialDate, quantities and Origin. Sowing columns/control rows and
  textarea heights now align deliberately. Domain rules, payloads, atomic writes and reversals remain.
- Guided Plant/group creation uses one page identity, compact linked source context, two semantic
  columns and four native Sowing-state radios with one selected consequence. Conditional completion
  facts remain. Transfer moves into existing More with stable dialog focus return; daily actions/Edit
  remain visible. Guided parent history preserves the exact source Details tab.
- Final focused evidence: **178 tests / 11 files passed** (120 in ten clean combined files, 58 in the
  final complete Plant repeat). Corrected an unrelated Journal date query changed too broadly during
  test cleanup and waited for required scheduled menu focus. An interrupted repeat is not counted;
  no timeout, domain assertion or validation weakened. Strict TypeScript/production build, targeted
  zero-warning ESLint/Prettier, **105-feature** graph and whitespace checks pass. Nine domain/payload/
  reversal-submit helpers match HEAD. No backend/API/schema/migration/dependency edits or full gates.
- [Fourth-pass evidence](review/collection-visual/sowings-plants/fourth-pass/README.md) records **30**
  form/viewport checks with continuous static footers, matching edges and no horizontal overflow;
  mobile footers clear navigation. At real 1440×844, New Plant/group/Sowing and guided Plant fit; guided
  group is 846px high with its footer visible. Three desktop Origin editors have no internal scroll.
  Live More/Transfer/Undo and both guided Cancel returns were checked without mutation. Actual browser
  zoom remains untested; enlarged-view checks are labelled viewport proxies. Real-history unit tests
  cover Back; a live Back tool wait stalled after reaching the source, so no full live matrix is claimed.
- On resumption Review frontend/backend were stopped; supported exact-owner `feature-review-up`
  restored them while preserving existing DB/media, owner and **v4/66**, revision **0042**. Final status
  is healthy and Review stays running. No reset/removal/reseed or persistent environment operation.
  All work remains unstaged/uncommitted, no canonical gate or delivery. Feature remains implemented,
  awaiting fourth-pass operator acceptance and later independent QA.

## 2026-10-17 — COLLECTION-VISUAL-001 independent review and canonical verification

- Independently reviewed the accepted candidate and its stale-test corrections. One initial full-gate
  frontend attempt failed a timing-sensitive Stored Material focus assertion; the focused test passed
  in isolation, and the unchanged candidate's final complete frontend suite passed **755 tests / 68
  files**. No product behavior or test assertion was weakened.
- Final `make feature-verify` selected FULL against `1e3df6adf9afdfd4a213396666b336f6d1b5136c` and
  passed: feature graph **105 valid**, workflow/environment checks, formatting, lint, strict mypy
  (**346 files**), TypeScript/API drift, backend **939 passed / 90.22%**, PostgreSQL integration
  **735 passed**, production builds, full migration cycle and exact working-tree receipt. No migration
  was added; all cycle points remain at `20261013_0042`.
- Exact-owner Review status initially showed stopped app services with the database retained; supported
  `make feature-review-up` restored health using the same candidate source and preserved database/media,
  owner and fixture **v4/66**. Persistent UAT belongs to worktree `4ff7`; its guarded status command
  refused this checkout. No UAT mutation occurred and its volumes remain retained. Candidate is ready
  for commit and protected delivery.
- Initial protected delivery created PR **#112**. Required `integration` and `build` passed, while
  `quality` found one focus regression in guided Sowing local validation. That path now supplies its
  field error to the existing accessible focus mapping, and the regression awaits the animation-frame
  focus rather than asserting synchronously. The correction is bounded to accessibility; final
  verification and protected delivery must be rerun for the follow-up commit.

## 2026-10-18 — MAPS-FOUNDATION-001 architecture and Native ranges slice

- Audited all three Maps workspaces before implementation; [design](maps-foundation-001-design.md)
  records distinct occurrence/native-range/material-origin contracts, existing SVG/Leaflet renderers,
  geometry/provider boundaries, URL/Saved Views, accessibility and reuse order. Retained the current
  engines, APIs and geometry; Species distribution and Collection origins reuse is planning only.
- Native ranges proves a compact map-first shell, explicit narrow-screen pane switching, precise
  discrete legends, keyboard polygon/HTML territory inspection and synchronized selected state.
  Comparison map precedes the selected-species list; exact broad/precise/custom places and unavailable
  boundaries remain explicit. Existing scientific-name formatting, compact Saved Views and filters
  preserve domain meaning, bounded selection, URL restoration, authentication and retry behavior.
- Final focused checks: **120 frontend tests / 13 files passed** across Maps, Provenance sites and
  Saved Views; scoped zero-warning ESLint/Prettier, strict TypeScript/Vite production build,
  **106-feature** graph and `git diff --check` pass. Baseline was 17 tests; final new behaviors include
  actual jsdom Back/Forward, reset preservation, polygon keyboard/clear, map/list inspection and bins.
  Native ranges JS **24.27/7.15 kB gzip**, CSS **7.67/1.60 kB gzip**; lazy geometry remains
  **150.83/60.46 kB gzip**. No backend, schema, API, dependencies or shared UI implementation changed.
- [Seven synthetic offline snapshots](review/maps-foundation-001/README.md) cover 1440×844, 1024×844,
  390×844 and tall content inspection without measured horizontal page overflow. They use real
  components/CSS/geometry with mocked local responses and a labelled static shell; they are not live
  Review evidence. Real browser zoom, screen reader, device touch and mobile navigation clearance
  remain pending. Initial offline rendering/approval-service limits were resolved without bypass.
- Reused the isolated Codex worktree `c606`; supported initialization attached `feat/maps-foundation-001`
  to freshly fetched `origin/main` at `a36c6cf`. COLLECTION-VISUAL-002 retains its Review resources;
  no environment start/stop/seed/adoption or persistent service change. No canonical feature-verify,
  staging, commit, push or delivery. Feature is **implemented**, pending operator acceptance and
  independent verification; full [handoff](maps-foundation-001-handoff.md) defines the next review.

## 2026-10-19 — MAPS-FOUNDATION-001 authenticated operator review

- With explicit operator approval, preserved all candidate files, fast-forwarded the existing branch
  to main `9a73d3f` (PR #113), and reconciled backlog/progress while retaining both increments.
  Non-overlapping candidate files were restored byte-for-byte; primary main was untouched.
- Removed the old `fb05` Review through its guarded owning-worktree workflow, then started Maps
  Review from `c606`. Interactive owner bootstrap and guarded synthetic seed completed. Final
  status is healthy, fixture **v4/80**, code/DB **20261013_0042**. Credential supplied only in chat.
  Review remains running at localhost:15174; UAT, DEV, Stable Preview and production untouched.
- Real authenticated overview, one/two/three-species selection, territory polygon/text/keyboard
  inspection, exact/broad/custom/unavailable/no-range evidence, empty/invalid state, Saved Views,
  URL reload and actual Back/Forward were inspected. Mobile pane switching preserves species,
  territory inspection and focus. A comparison Saved View remains for the operator.
- Live mobile evidence justified local control compaction and moving supporting explanation/metadata
  below the map. Final overview/comparison/single maps fit usefully in the first mobile viewport,
  with no measured horizontal overflow. [Live evidence](review/maps-foundation-001/live/README.md)
  distinguishes actual viewports from zoom proxies; no real zoom, screen-reader, physical touch or
  live API/asset failure injection certification is claimed.
- Final **121 tests / 13 files**, scoped zero-warning ESLint/Prettier, strict TypeScript/Vite build,
  **107-feature** graph, whitespace and healthy exact-source Review checks pass. Interrupted local
  runs (exit 143) were superseded by completed validation; no test or guard was weakened. No canonical
  gate, staging, feature commit, push or delivery. Changes remain unstaged/uncommitted; operator
  acceptance and the future map phases are detailed in the [handoff](maps-foundation-001-handoff.md).
- Final continuation found stopped app services with the database retained. Supported Review startup
  restored healthy frontend/backend/database from the same `c606` candidate, preserving owner login,
  fixture v4/80 and revision `20261013_0042`. Review remains running for the operator.

## 2026-10-19 — MAPS-FOUNDATION-001 overview and interaction refinement

- Refined the existing dirty `c606` candidate at `9a73d3f` without branch changes. The accepted
  PageHeader/DirectoryTools pattern puts Filters, Saved Views and Choose species on the right.
  Five grounded KPIs lead into a full-width map; species selection uses an explicit searchable,
  paged TaskDialog instead of a permanent rail. Selected count and compact names remain visible.
- KPI actions open the chooser or reveal/focus textual coverage and exact places. With-range
  browsing uses the existing durable filter; no inverse/no-range API or invented metric was added.
  Coverage, unsupported boundaries, methodology and detailed selection/places are progressive disclosures.
- Added hover/focus territory preview independent of committed inspection. Separated fills, fixed
  boundaries and inward-clipped emphasis; neighboring paths can no longer erase a selected edge
  or receive its overpaint. Selection, focus and hover keep distinct geometry; static layers are inert.
- Authenticated desktop/tablet/mobile review confirms map prominence, no horizontal overflow,
  modal focus/persistence, scientific/common/cultivar search, one/two/three species, exact/broad/custom/
  no-range evidence, Saved View restoration, URL reload and actual Back/Forward.
  [Refinement evidence](review/maps-foundation-001/refinement/README.md) supersedes the first live layout.
- Baseline **25 tests / 4 files**; affected regressions **131 / 15**; final Native/maps rerun **30 / 4**
  after correcting the mapped-KPI asset-failure state. Scoped zero-warning ESLint/Prettier, strict
  TypeScript/Vite build, **107-feature** graph and whitespace pass. Final JS **29.61/8.44 kB gzip**,
  CSS **10.34/2.13 kB gzip**; geometry remains **150.83/60.46 kB gzip**. No tests or safeguards weakened.
- Supported Review rebuild resolved development-session module errors and retained owner/credentials,
  v4/80 fixture, saved preset and revision `20261013_0042`. Review remains running. No seed/reset/removal,
  UAT/DEV/Preview/production change, canonical gate, staging, commit or delivery in this pass.
  Real zoom, screen-reader and physical-touch acceptance remain pending in the [handoff](maps-foundation-001-handoff.md).

## 2026-10-20 — MAPS-FOUNDATION-001 geographic exploration refinement

- Continued the same dirty `c606` / `feat/maps-foundation-001` candidate at `9a73d3f`; all work remains
  unstaged and uncommitted. No new branch, reconciliation, canonical gate, commit, PR or delivery.
- Adopted Collection PageHeader search beside Filters/Saved Views/Choose species. Explore all uses
  the complete filtered collection; Compare uses explicit choices with up to five stable labelled
  colors. SVG stripes encode all overlapping contributors while fixed boundaries and inward-clipped
  selected/hover/focus layers remain intact. Restored 6–20-ID views retain all IDs in count mode.
- Added independent multi-territory toggles, chips/removal/clear and a scoped union/intersection
  inspector with exact-versus-broad evidence. A concrete overview-contract gap required one bounded
  authenticated read API, reusing canonical ancestry and existing representation filters. Generated
  OpenAPI/TypeScript updated; no migration, geometry, provider or dependency change.
- Wide layout is about 70/30 map/inspector. Five names follow the canvas; mounted Map/Inspector panels
  give direct small-screen access. About/Places replaces duplicate bottom menus; exact-place paging
  retains the map. Native ranges remains isolated from occurrence density and collection provenance.
- Final checks: **39 Native/maps + 101 related frontend tests = 140 / 15 files**, **6 backend unit**,
  **10 isolated PostgreSQL integration**, scoped zero-warning lint/format, strict TypeScript/Vite,
  Ruff/mypy, API drift, **107-feature** graph and whitespace/empty-index checks pass. An earlier host
  combined test run ended 143 without a result; completed scoped container runs supersede it.
- [Spatial evidence](review/maps-foundation-001/spatial/README.md) distinguishes authenticated five-ID
  and real two-way overlap from labelled renderer-only 1/2/3/5-way polygon fixtures. No fixture rows
  were changed. True browser zoom, actual screen reader, physical touch and operator product acceptance
  remain pending in the [handoff](maps-foundation-001-handoff.md).
- Supported Review startup resumed services stopped between continuations, preserving owner credential,
  database/media/dependencies, v4/80 fixture and revision `20261013_0042`. Review remains available for
  inspection; no reseed/removal or UAT/DEV/Stable Preview/production operation was performed.

## 2026-10-21 — MAPS-FOUNDATION-001 independent review and operator acceptance

- Independently reviewed the existing Native ranges implementation, API, data semantics, shared map
  shell, renderer, Saved Views, URL/history, keyboard/focus behavior and spatial evidence. No material
  blocker or production correction was found. Authenticated Review showed one-, two- and three-species
  selection, union/intersection, broad versus exact evidence, and transient territory selection; the
  selected set remained independent. Review data and saved state were preserved.
- Operator accepted the map-first hierarchy, five-layer comparison, inspector/search density and
  responsive map/list behavior. Existing 1440×844, 1024×844 and 390×844 captures are viewport evidence;
  true browser zoom, actual screen-reader use and physical-device touch inspection remain open follow-up
  checks and are not claimed complete.
- Focused verification passed: **140 frontend tests / 15 files**, **10 backend unit tests** and
  **10 PostgreSQL Native ranges integration tests**. During the full gate, one test-only enum typing
  issue was fixed and the focused integration suite passed again. The subsequent full gate passed
  strict typing, backend tests, and **797 frontend tests / 70 files**, then was interrupted while the
  736-test PostgreSQL integration run was at 44%. It did not return a success result or receipt.
- The final candidate remains on `feat/maps-foundation-001` at main baseline `9a73d3f`, with changes
  unstaged and uncommitted. The canonical full gate is being rerun on the documented, accepted tree
  before authorized commit and protected delivery. Review remains running with its v4/80 fixture at
  `20261013_0042`; UAT, DEV, Stable Preview and production remain untouched.

## 2026-10-21 — MAPS-FOUNDATION-001 canonical verification

- Final canonical `make feature-verify` passed on the accepted candidate. Results: **943 backend unit
  tests, 797 frontend tests / 70 files and 736 PostgreSQL integration tests**; workflow guards,
  formatting, lint, strict typing, OpenAPI/TypeScript drift, backend/frontend production builds,
  feature graph, whitespace and complete migration cycle passed. The migration cycle verified
  `20261013_0042` at all four checkpoints; this feature adds no migration. The working-tree receipt
  records the verified candidate against base `9a73d3f`.
- Updated `MAPS-FOUNDATION-001` to `verified` and synchronized this handoff with the acceptance and
  gate results. The result-only documentation change requires one more canonical gate before staging.
  Candidate changes remain unstaged and uncommitted; protected delivery and `make feature-finish`
  remain outstanding. Maps Review remains running; protected environments remain untouched.

## 2026-10-21 — MAPS-DISTRIBUTION-001 visual-review candidate

- New independent `b139` / `feat/maps-distribution-001` candidate from fetched clean main
  `9275947` includes PR #116. Reused PageHeader/DirectoryTools, TaskDialog, compact Saved Views,
  BotanicalName and MapWorkspace for a map-first single-identity occurrence workspace.
- Added grounded local readiness actions, searchable chooser with transient hover/focus previews,
  contextual evidence inspector, compact qualitative legend, progressive quality/licensing details,
  explicit partial-tile failure/retry and Leaflet resize handling for mounted responsive panes.
  Preserved exact GBIF links, explicit Load, representation/search, URL/history and v1 Saved Views.
  No native/abundance/absence inference, bin locations/counts, comparison or backend/API changes.
- Completed regressions: **116 tests / 10 files** across occurrence, shared maps, Native ranges,
  Saved Views and identity-detail consumers. After the final invoking-control focus fix, the
  final Species distribution file passed **9 tests**. A later broad run ended 143 without a result;
  it is not claimed passed. Affected-file zero-warning ESLint, full frontend Prettier,
  strict TypeScript/production Vite build, **108-feature** graph and whitespace checks passed.
- Authenticated 1440×844, 1024×844 and 390×844 review covered layout, pane persistence, cultivar
  search, keyboard previews/focus, actual Back/Forward and Saved View save/reopen with evidence
  unloaded. Fixed reproduced tablet header gaps. [Browser evidence](review/maps-distribution-001/README.md)
  records live partial-tile failures and positive aggregate counts, not fabricated occurrence data.
- Operator explicitly approved guarded replacement of the delivered Maps Review. The fresh
  candidate-owned `florabase-feature-review` at <http://localhost:15174/#/species-distribution>
  is healthy with its own v4/80 fixture and database head `20261013_0042`. Sourcing at 15175,
  UAT, DEV, Stable Preview and production remain untouched. Host RAM/swap pressure and browser
  input/capture timeouts are documented honestly; completed scoped runs supersede timed-out attempts.
- Graph status is `implemented`. [Handoff](maps-distribution-001-handoff.md) records architecture,
  scientific/privacy boundaries, exact checks, ownership and pending operator product, actual zoom,
  screen-reader and touch acceptance. No canonical gate, staging, commit, push or delivery.

## 2026-10-21 — MAPS-DISTRIBUTION-001 durable evidence refinement

- Operator-requested refinement supersedes the initial no-persistence/unloaded-restoration rule.
  Audited ExternalProviderCache, fixed GBIF summary/tile adapter, media volume/backup behavior and
  primary GBIF rights/HTTP guidance before implementing bounded summary and viewed-raster reuse.
  No raw occurrence ingestion, migration, new dependency or changes to Native ranges semantics.
- Chooser uses established backdrop dismissal and invoker focus; internal interactions and Escape
  preserve selected identity. One Data details disclosure and bounded desktop inspector keep primary
  counts/date/Refresh compact. Responsive map/inspector switching keeps Leaflet mounted.
- Actual incomplete-tile cause: provider 503 plus valid empty 204 decoded as an image failure and
  latched frontend errors. Added transparent 204 success, bounded failed-visible-tile retries,
  cancellation cleanup and separate optional online basemap errors. Local Natural Earth context
  permits external-request-free cache playback. Existing proxy limits remain.
- PostgreSQL summaries and durable bounded PNG/204 files share exact taxon/contract/generation keys.
  Cache-only GET never refreshes; owner/CSRF POST and DELETE are explicit. Failed refresh retains good
  cached evidence; successful refresh isolates a new generation; old summaries are dated/stale.
  Storage quotas/eviction, policy exclusions, backup limits and future raw-record decision are in
  [the audit](maps-distribution-001-cache-design.md) and [handoff](maps-distribution-001-handoff.md).
- Focused backend suite: **33 passed**; final API transport regression rerun: **6 passed**. Ruff clean;
  strict external_botany mypy: **8 sources clean**. PostgreSQL API integration: **3 passed**;
  exact owned project `florabase-integration-1f2164f94bb1` cleaned with zero residual resources.
  Generated OpenAPI and TypeScript drift check passed. Cache/chooser/renderer frontend: **21 passed
  across 4 files**. Completed scoped frontend checks total **123 tests / 11 files** (21 occurrence/
  distribution, 22 NativeRangesScreen, 77 shared-map/geometry/Saved Views, 3 identity consumer).
  Zero-warning changed-file ESLint/Prettier and strict TypeScript/production build pass. Resource-
  constrained broad attempts are explicitly not counted; completed isolated runs supersede them.
  Feature graph **108 valid** and whitespace check pass; exact evidence is in the handoff.
- Live existing Review HTTP verification returned Ocimum basilicum **3,783 eligible / 9,775 total**,
  PNG 200/14,610 bytes and empty 204; each tile replayed identically cache-only and summary reopen
  retained generation. Fixture v4/80 was preserved. Error/offline behavior uses injected tests.
  Initial responsive captures are explicitly historical; browser transport/timeouts prevented fresh
  expanded-details/cache navigation screenshots. Current visual acceptance remains with operator.
- Candidate remains implemented, unstaged/uncommitted, with no canonical feature-verify or delivery.
  Candidate Review 15174 preserved; Sourcing 15175 and all protected environments untouched.

## 2026-10-21 — MAPS-DISTRIBUTION-001 source navigation and main synchronization

- Fetched and inspected current `origin/main` at `4a657d8` (Sourcing PR #117), preserved the full
  dirty/untracked Maps candidate in a Git stash, fast-forwarded only `feat/maps-distribution-001`,
  and restored the candidate. `docs/progress.md` and `frontend/src/App.test.tsx` merged cleanly;
  the final branch is based on the Sourcing merge and retains both feature sets.
- Added **Link botanical source** to selected identities with missing or incompatible GBIF links.
  `#/identities/<id>?tab=source` now opens that exact identity's Reference → Botanical source,
  including direct load and refresh. Focused App tests assert the local route and no GBIF search;
  species-distribution tests assert the exact selected identity URL. Native anchor behavior keeps
  keyboard focus visible and browser Back history native.
- Independent regression suites passed: **106 frontend Maps/App tests**, **58 frontend Sourcing,
  order, selector, dialog and record-visual tests**, and **33 backend provider/service/API/cache
  unit tests**. The Sourcing-preview, persistent UAT, DEV, Stable Preview and production resources
  remain untouched; candidate-owned Feature Review is healthy at 15174 with its v4/80 fixture.
- Corrected an existing invalid multi-exception clause in
  `backend/tests/integration/test_harvest_seed_conversion.py`; it predates this feature and the
  Sourcing merge. This syntax-only test correction is required for Python 3.12 to collect the full
  suite and changes no runtime behavior.
- The graph remains `implemented` pending the required full canonical gate, final exact-tree
  receipt, protected delivery and post-merge DEV smoke. No stage/commit/push/delivery yet.

## 2026-10-21 — MAPS-DISTRIBUTION-001 full verification

- `make verify-full` passed on the candidate tree: backend **953 passed** (90.03% coverage), frontend
  **832 passed across 71 files**, PostgreSQL integration **737 passed**, API drift, formatting,
  lint, strict typing, migration upgrade/downgrade cycle, and backend/frontend production builds.
  Workflow checks, feature graph (**108 valid**) and whitespace checks passed; the exact-tree
  verification receipt was recorded. The test-only Python 3.12 syntax correction was included.
- Candidate Feature Review at <http://localhost:15174/#/species-distribution> was restarted from
  the guarded, worktree-owned lifecycle and is healthy on current code. Its v4/80 fixture and
  database revision `20261013_0042` were preserved. Local reopen displayed saved occurrence counts
  and tiles without provider traffic, identified two missing areas, and exposed explicit refresh.
  Expanded Data details separated **3,783 eligible mapped records** from **9,775 matching present
  records** and disclosed the data-quality, uncertainty, attribution and privacy contracts.
- `MAPS-DISTRIBUTION-001` is `verified`. Sourcing Preview at 15175, UAT, DEV, Stable Preview, and
  production remain untouched. Staging, commit, protected delivery, finish and post-merge DEV smoke
  remain pending. The required final `make feature-verify` rerun passed in full mode after these
  documentation/status edits and recorded the exact-tree receipt.
- A later gate rerun reproduced a cold-start failure in the unrelated Dashboard default-route test:
  the lazy workspace was still loading at the one-second query timeout. Raised that assertion's
  wait to ten seconds (matching the route-transition regression), then the isolated UX001 suite
  passed **7/7**. The final full gate is being rerun after this test-only reliability adjustment.

## 2026-10-22 — MAPS-ORIGINS-001 visual-review candidate

- Fetched main `b3f1de4` includes delivered PR #118. Canonical initialization attached
  new supplied Codex `c902` to `feat/maps-origins-001-candidate` because the suggested
  branch was already attached elsewhere. Primary and other worktrees were preserved.
- Audited and documented reuse before implementation. Collection origins now uses
  the accepted header search/Filters/Saved Views, functional mapped-site/direct-record/
  identity counts, approximately 70/30 Leaflet/inspector layout, bounded site browsing
  and identity-grouped exact record/lifecycle links. Missing coordinates retain the
  Geography path; default mapped sites with no direct records remain inspectable.
- Preserved `#/map`, `provenance_map` v1, identity-only `q`, `seed_lots` and Plants plus
  PlantGroups `plants`. Exclusion permanently clears selection; ordinary inspection
  preserves viewport. Exact markers/accuracy circles, safe hover/focus text, explicit
  Enter/Space, 44px hit areas, mounted responsive panes/resize and reduced motion are
  covered. No descendant, Supplier, Location, native-range or GBIF origin inference.
- Retained configured online tiles/attribution with explicit offline switch, local
  bundled Natural Earth context, tile-failure Retry and visible privacy distinction.
  Final synthetic browser audit intercepted 36 tile-coordinate-only URLs with no
  referrer. No remote geocoding/provider/dependency/API/schema changes were needed.
- Completed **270 frontend tests / 19 files**, **94 backend unit tests**, **4 PostgreSQL
  provenance API integration tests**; exact disposable integration cleanup passed.
  ESLint, full frontend formatting, strict TypeScript/production build, API drift,
  **109-feature** graph and whitespace/index checks pass. A broad run exited 143 and
  an initial unchanged lazy Geography timeout are not claimed passed; completed
  scoped reruns supersede them without weakening checks.
- [Handoff](maps-origins-001-handoff.md) and labelled
  [synthetic evidence](review/maps-origins-001/README.md) record 1440×844, 1024×844,
  390×844 measurements, real Leaflet keyboard, pane retention, Back/Forward, Saved
  View reopening, API Retry and provider-failure fallback. No horizontal overflow.
  Headless zoom did not change viewport/ratio; true zoom, actual screen reader,
  physical touch and live authenticated candidate acceptance remain operator work.
- Feature Review 15174 still belongs to delivered `b139` and was not acquired,
  started, removed or reseeded. DEV, UAT, Stable Preview, production and Sourcing
  remain untouched. Status is `implemented`; all changes remain unstaged/uncommitted.
  No canonical `make feature-verify`, commit, push, PR or delivery. Candidate boundary:
  **READY_FOR_ORIGINS_VISUAL_REVIEW**.

## 2026-10-22 — MAPS-ORIGINS-001 authenticated Feature Review

- Verified old Review ownership/resources with guarded inventory/status, then obtained
  explicit operator deletion approval. Stopped/removed only `b139`'s exact Review
  environment through its owning guarded commands; all other environments/worktrees
  were preserved. Started replacement from `c902` using `make feature-review-up`.
- Bootstrapped new enabled `owner` securely via password stdin; random password stays
  in a user-owned mode-0600 file outside the repository. Guarded seeding initialized
  **v4 / ready / 80 records**. Frontend, backend and database are healthy, owned by
  `c902`, at revision `20261013_0042`; launched HEAD is `b3f1de4` plus the dirty candidate.
- Authenticated real-browser checks verify exact marker/list/inspector selection,
  KPI counts/dialogs, search, record filters, exclusion clearing and retained panes
  at 1440×844, 1024×844 and 390×844, with no horizontal overflow or runtime errors.
  Actual online check loaded **12 tiles**, none failed/pending. Standard live fixture
  has one mapped site/direct SeedLot/identity and unknown accuracy; richer states
  retain the earlier labelled synthetic and test evidence, without collection edits.
- Review remains running at <http://localhost:15174/#/map>.
  [Live evidence/status](review/maps-origins-001/live/README.md) supersede the previous
  slot limitation. True zoom, screen reader, physical touch, independent QA and
  operator visual acceptance remain pending. No canonical verification, staging,
  commit, delivery or DEV upgrade. **ORIGINS_LIVE_REVIEW_READY**.

## 2026-10-22 — Origins operator corrections and Extended Botanical Review Dataset v5

- Continued dirty c902 candidate without new branch, staging, commit, delivery or canonical gate.
  Audited outgoing OSM requests and official policy: prior no-referrer tiles violated its Referer
  requirement. Collection origins now starts with local Natural Earth context; permitted online
  detail requires configuration plus explicit enablement, uses origin-only cross-origin Referer and
  hides the complete layer on first error without retry. Exact WGS84 markers/accuracy remain local.
  HTTP-200 policy artwork remains a documented browser-image limitation; no bypass/prefetch added.
- Corrected Filters into compact full-row Seed lots / Plants and plant groups controls, retaining
  existing keys and shared apply-as-chosen Done/Close/Escape/backdrop semantics. Real 1440/1024/390
  screenshots/checks pass with no horizontal overflow. Long site labels exposed a collapsing Leaflet
  tooltip; explicit bounded width fixes it without moving coordinates or changing the mapping stack.
- Added separately versioned Review-only dataset/manifest and guarded extended seed/status commands.
  Existing v4, owner credentials, edits and UAT semantics remain unchanged. New data uses domain
  services with transactional graph creation, explicit failure diagnostics, stable logical references
  and retained service-generated UUIDv7 IDs. No network acquisition; licensed photos total 508,755 bytes
  outside production build contexts. External references remain private until explicit Preview once.
- Positively verified exact c902 project/source/DB/media/network/revision ownership before mutation.
  Additive live seed twice returned ready/252 references and identical IDs/counts; v4 retains its
  byte-identical ledger/80 references and unchanged owner credential fingerprint. All 14 pre-existing
  foreign project inventories compare unchanged. No Review reset/removal/recreation.
- Live totals: 37 identities, 43 SeedLots, 19 Plants, 7 PlantGroups, 16 Sowings, 12 Orders, 10 Suppliers,
  14 provenance sites, 18 Locations, 25 profiles, 24 identities with structured ranges, 5 Harvests,
  8 items, 4 inventories, 13 Journal/operation events, 2 germination observations, 27 scheduled
  activities, 17 media assets (9 local/8 external), 18 media links and 9 protected attachments.
  Origins projects 12 mapped / 2 no-coordinate sites, 42 direct records and 22 distinct identities.
- Authenticated browser acceptance verifies marker/inspector navigation, KPIs, filters, responsive
  panes, five-species BR5/TH4/IT3/US2/AU1 overlap, broad/exact/custom/unmapped range records, collection
  directories and Stored material, protected photo decode/401, attribution, explicit no-referrer
  external preview and isolated online-provider refusal without retry. No real remote provider
  outage/download is claimed. Evidence: `docs/review/maps-origins-001/refinement-v5/`.
- Completed checks: frontend 130/15 files; full ESLint, TypeScript/build and scoped formatting; backend
  109 passed/1 optional live skip; PostgreSQL affected suites 38 passed and final strengthened fixture
  3 passed; workflow/environment 35 passed; operational lint/format/strict typing; backend and generated
  TypeScript API drift; 109-feature graph; diff whitespace and empty staged diff. Disposable test
  cleanup succeeded. No schema/API/dependency changes. Intermediate harness/static-invocation errors
  were corrected; only successful final checks are counted.
- Updated design/handoff and dedicated `docs/review/extended-botanical-dataset-v5.md` with matrices,
  licensing, exact counts, failure/recovery and disk footprint. Live Review stays healthy at 15174,
  owner password retained outside repository. True browser zoom, physical touch, screen-reader and
  independent/operator acceptance remain pending. `READY_FOR_ORIGINS_VISUAL_REVIEW`.

## 2026-10-22 — MAPS-ORIGINS-001 independent review

- Re-fetched `origin/main`: `b3f1de4693f50a12396344d251a16a0b4ded4b92`, exactly the candidate base;
  merge-base matches and branch divergence is zero. Guarded Review status confirms the healthy
  c902-owned `florabase-feature-review`, both database revisions `20261013_0042`, v4 ready/80 and
  v5 ready/252 references with operator edits preserved.
- Rechecked the authenticated live map, KPIs, mapped marker and inspector, exact WGS84/recorded
  accuracy, grouped material links, category filters and responsive pane controls. Live totals are
  12 mapped sites, 42 distinct direct records, 22 identities and 2 sites without coordinates.
  Enter on a textual site row selected it; Escape cleared inspection. No live data was changed.
- Reviewed source, workflow ownership, domain relationships, synthetic fixture idempotence/failure
  tests, no-network guarantees, local/external media split and v4/UAT isolation. All eight local
  image sources/licences were checked against individual Wikimedia Commons pages; the 508,755-byte
  derivatives match manifest size/hash and contain no EXIF. Natural Earth is public-domain 1:110m
  context. Current OSM guidance requires an accurate Referer and attribution and prohibits scraping
  and offline tile prefetch; online detail remains disabled by default and the tested failure path
  retains local geography without automatic retry.
- `origin/main` compatibility is clean; targeted backend Ruff passes after correcting import order.
  Focused browser, backend, PostgreSQL, workflow, type, build and API checks remain documented above.
  Canonical verification and operator acceptance were pending at that review checkpoint; both are
  recorded as complete in the following milestone. No staging, commit or delivery had occurred.

## 2026-10-22 — MAPS-ORIGINS-001 canonical verification

- The final independent review rechecked authenticated c902 Review ownership, healthy services,
  revision `20261013_0042`, v4/v5 fixture status, exact map evidence and operator-preserved edits.
  The authenticated map interaction suite covered marker/list/inspector synchronization, keyboard
  selection, record filters and KPIs. No live collection data was changed.
- `make verify-full` passed on the implementation and review-evidence tree and recorded its
  per-worktree verification receipt. Backend unit tests: **953 passed, 1 skipped**; frontend:
  **844 passed across 72 files**; PostgreSQL integration: **740 passed, 953 deselected**. Ruff,
  ESLint, formatting, mypy/TypeScript, backend/frontend production builds, API drift, workflow and
  resource guards, migration cycle and whitespace/index checks passed. The verified schema is
  `20261013_0042`; this increment adds no API, schema or dependency change.
- The exact disposable integration project and migration cycle cleaned up successfully with no
  residual containers, networks or volumes. Review, DEV, UAT, Stable Preview, Sourcing, production,
  and all other worktrees remain preserved. Feature status is now `verified`; changes are still
  unstaged/uncommitted. The documentation update requires one final receipt refresh before guarded
  delivery via `make feature-deliver`.

## 2026-10-23 — BOTANICAL-IDENTITIES-VISUAL-001 implementation and visual handoff

- Implemented balanced Quick Preview actions and explicit active-SeedLot Sowing / actual Plant or
  PlantGroup Harvest source choosers, including loading, retry, cancellation and prerequisite links.
  Tablet/phone selection now exposes the same Preview actions in the shared native TaskDialog.
- Reworked the compact identity header, Overview facts/links, all four Collection modes, all five
  Reference modes and source-labelled Events. Preserved botanical names, counts, provenance,
  Journal/History boundaries, direct URLs and existing provider-loading behavior.
- Reused contextual EditWorkspace with all four edit sections, mounted drafts, section-specific
  saves, normalized saved names, unsaved/pending guards and focus/context return. Moved deletion
  to the Overview Danger zone; confirmation starts on Cancel and retains server integrity rules.
- Focused frontend: **134 passed / 8 files**; strict TypeScript and production build (**225 modules**),
  ESLint on all ten changed TS/TSX files, scoped formatting, **112-feature graph** and whitespace
  checks pass. Repository-wide lint/full frontend attempts were interrupted (143); the full attempt
  also reported ImportExport readiness failures. No full-suite or canonical verification is claimed.
- Positively owned isolated review runs at **http://localhost:15176/#/identities**, synthetic data only;
  retained Review port 15174 and foreign worktrees/data were preserved. Handoff and **71 screenshots**
  with measured desktop/tablet/phone states and all six theme variants are in
  `docs/botanical-identities-visual-001-handoff.md` and its linked gallery; zero measured horizontal
  overflow. Approved provider-backed imagery, real AT/touch/zoom and independent/operator acceptance
  remain pending. Feature is `implemented`; no FULL gate, staging, commit, push, PR, merge or delivery.
  `BOTANICAL_IDENTITIES_VISUAL_REVIEW_READY`.

## 2026-10-23 — BOTANICAL-IDENTITIES-VISUAL-001 operator refinement

- Replaced nested Collection/Reference read navigation with flat bounded sections; Overview now
  combines a local botanical excerpt/status, distinct truthful record/active counts, one relevant
  next action and four recent events. Added all five canonical collection operations, including
  PlantGroup creation; genuine SeedLot/Plant/group source eligibility remains authoritative.
- Added exact identity-ID URL/Saved View scope to Seeds, Sowings and Plants, composing with search,
  lifecycle and kind, with visible clear controls and return links. Reused existing Harvest/map
  contracts; unsupported Journal/History filters are explicitly deferred in the handoff.
- Normalized identity row dimensions and shared thin preview-selection accents across comparable
  lists while preserving focus/bulk states. Extracted shared Journal timeline styles for identity
  Events, retaining partial dates, source ownership and existing global Journal behavior.
- Final affected frontend **374 passed / 18 files**; backend **88 unit + 15 PostgreSQL integration
  passed**, exact disposable cleanup verified. Strict TypeScript/build (**230 modules**), targeted
  ESLint (**30 files**), frontend/backend formatting, Ruff, changed-module mypy, both API artifact
  checks, **112-feature graph** and whitespace pass. No canonical FULL or full-suite claim.
- Current gallery adds **66 screenshots / 63 measured states**, all six theme variants and three
  viewport sizes, with zero measured horizontal overflow; original 71 retained. Native discard
  confirmation blocked final browser recaptures; older phone-header screenshots and manual
  discard/deletion review limits are labelled honestly. No editor save/deletion was submitted.
- The exact owned port-15176 review services remain running; original synthetic data preserved,
  six labelled packets and one Saved View added. Handoff records routes, checks and limitations in
  `docs/botanical-identities-visual-001-handoff.md`. Operator acceptance remains pending. Changes
  remain unstaged/uncommitted; no push, PR or delivery.
  `BOTANICAL_IDENTITIES_REFINED_REVIEW_READY`.

## 2026-10-24 — BOTANICAL-IDENTITIES-VISUAL-001 cross-functional IA review

- Final operator pass now has exactly Overview, Reference, Taxonomy, Maps, Media and History.
  Overview combines a compact semantic surface band, five exact filtered footprint links, local
  botanical/taxonomy summary, four recent authoritative facts including Harvests and one valid next
  action. Legacy Collection/Events and previous sub-section routes retain useful destinations.
- Reference is textual only. Taxonomy reuses existing source workflows. Maps explicitly loads one
  of three distinct evidence types using existing engines; native inspector is identity scoped and
  direct provenance membership/counts exclude unrelated records. Media shows actual cover rights
  and bounded owner links with honest gallery limits. History retains the actual event provider;
  unsupported sowing/germination/global identity history projections are documented.
- Preserved exact URL/Saved View filters, all five creation actions and real source choosers,
  mounted editor drafts, independent saves, dirty/pending guards and Cancel-first deletion.
  Uniform Add entries measure 44px in all six themes. Editor context and adjacent navigation are
  compact; the six main tabs use a narrow-screen scroll strip without page overflow.
- On operator request, added a clearly fictional populated identity through authenticated review
  APIs: 3 SeedLots, 1 Sowing, 2 Plants, 1 PlantGroup, 1 Harvest and 4 recorded facts, complete profile,
  illustrative manual range/direct provenance and an attributed existing offline image. The manifest
  verifies both original identities' counts are unchanged; no existing record was deleted or reset.
- Final affected frontend **458 passed / 28 files**; strict TypeScript/build (**236 modules**),
  ESLint (**45 TS/TSX files**, zero warnings), scoped frontend formatting (**49 source files**),
  **112-feature graph** and whitespace passed. No third-pass API/schema change or backend rerun;
  historical **88 unit + 15 integration** evidence remains in the archived refinement handoff.
- Current gallery contains **72 screenshots / 72 measured states**, all six themes and three
  viewports (1440×844, 1024×844, 390×844), with zero root/body horizontal overflow. All prior
  handoffs/galleries remain. Native discard confirmation was reproduced safely with a temporary
  unsaved draft; the browser exposed no dialog handle, so operator Cancel was requested and no
  bypass/save/deletion was attempted. Interactive discard acceptance, approved provider imagery,
  physical touch/AT/zoom and independent operator acceptance remain pending.
- Only positively owned review services were reconnected after restart, retaining DB/media and
  network. The populated review is at port 15176; no foreign/DEV/UAT/Preview/production resource was
  changed. Final handoff: `docs/botanical-identities-visual-001-handoff.md`. Status `implemented`;
  changes unstaged/uncommitted; no canonical FULL, push, PR or delivery.
  `BOTANICAL_IDENTITY_CROSS_FUNCTIONAL_REVIEW_READY`.

## 2026-10-24 — BOTANICAL-IDENTITIES-VISUAL-001 final visual composition

- Preserved the accepted Overview/Reference/Taxonomy/Maps/Media/History architecture and all prior
  candidate work. Applied one semantic primary section surface, aligned spacing/borders/radii and
  quieter internal dividers. Compacted breadcrumb/header/tab spacing; actions stay together below
  the name at intermediate widths. Fixed and recaptured the long-name Overview squeeze at 860px.
- Maps now compares three distinct evidence types in three/two/one columns, showing actual entry,
  saved-cache and direct provenance counts through existing local reads. One explicitly activated
  full-width inspection reuses existing engines; it focuses/scrolls to the map and Close inspection
  returns focus to its trigger. Dedicated origins workspace remains honestly labelled all identities;
  no unsupported filter, provider acquisition or inferred geographic evidence was introduced.
- Media features the actual cover and its rights with restrained existing management controls.
  A separate responsive gallery queries existing exact owner photo lists in six-record batches,
  preserves captions/owner links/rights and uses shared protected thumbnails/viewer. Remote assets
  without saved copies stay placeholders. Older entries without asset IDs remain source links.
  Two credited offline illustrations were added only to the existing fictional review Plant;
  readonly audit confirms original and fictional collection counts, image rights and ownership.
- Reference now exposes textual content directly under the tabs, with heading-row Edit profile,
  two-column short fields and readable full-width long fields. Taxonomy uses the same surface;
  History retains its operational timeline and Harvest facts without a redundant feed container.
- Final affected frontend **501 passed / 31 files**, clean exit 0; final focused inspection/keyboard
  follow-up **22 passed / 3 files**, clean exit 0 (overlapping selection). Initial composition run's
  unhandled old App provenance mock shape was fixed explicitly; its attempt evidence is retained.
  Strict TypeScript/build (**237 modules**), ESLint (**11 affected TS/TSX files**, zero warnings),
  scoped formatting (**51 source/CSS files**), **112-feature graph**, whitespace and gallery links
  pass. No API/schema/migration change or backend rerun in this pass.
- Updated handoff and gallery contain **63 captures / 63 measured states**, six themes, 1440×844,
  1024×844, 390×844 and intermediate 860×844; zero page-level horizontal overflow. Pristine editor
  opens/closes at desktop/phone and returns to Media; the retained editor tab was untouched.
  Provider imagery, physical touch/AT/zoom, earlier native-confirm manual acceptance and operator
  composition acceptance remain pending. Inspection preferences restored to Botanical Light and
  temporary viewport reset. Only the positively owned port-15176 review runtime was used.
- Operator accepts the current excess card/elevated-surface nesting as non-blocking. Track a separate
  cross-application visual-normalization follow-up: reduce unnecessary card/background nesting,
  reuse established page surfaces and separators, preserve useful grouping, and align with the
  eventual global IA. No broad styling redesign is part of this delivery.
- Status remains `implemented`; all changes unstaged/uncommitted. No canonical FULL gate, push,
  PR, delivery or global IA-NAV-001 redesign. `BOTANICAL_IDENTITY_VISUAL_COMPOSITION_READY`.

## 2026-10-24 — GEOGRAPHY-VISUAL-001 exploration review candidate

- Initialized `feat/geography-visual-001` in the provided clean Codex worktree from freshly fetched
  `origin/main` `e7ade78559803a35b738a669085799f55eb76258`. Kept the implementation unstaged and
  uncommitted; feature status is `implemented`, with operator acceptance and canonical verification
  explicitly pending.
- Added `#/geography/overview`: four local authenticated reads, independent loading/empty/error/retry
  summaries and exact identity/site/material links keep structured native ranges, observed occurrence
  density and recorded provenance distinct. No map engines, provider loading or inference on the hub.
  Reused all three delivered map destinations through grouped internal navigation; global sidebar,
  Settings, tokens, APIs/schema and dependencies are unchanged.
- Normalized Geography row/preview typography, density, metadata, actions and visible focus using
  existing primitives. Retained the Places hierarchy and canonical/local restrictions. Exact
  place-to-site filtering reuses existing site identities; source records reuse the origins projection.
  Coordinate-less sites explicitly retain the missing exact-record-link limitation. Legacy `mode=map`
  is labelled Site map and remains distinct from Collection origins.
- Browser review reproduced and fixed lost Geography query transitions by stabilizing view-hook
  arguments, a tablet header flex-direction defect, and the native species deep-link mode. Added no
  shared router mechanism or shared directory primitive. The App change reserves one lazy internal
  overview route; IA-NAV integration remains documented.
- Focused baseline: 47 tests/4 files. Final affected frontend suite: **148 passed/7 files**. Strict
  TypeScript, full zero-warning ESLint, frontend formatting and production Vite build passed.
  Feature graph: **112 valid**; whitespace/index checks passed. One earlier host-pressure timeout
  was superseded by the unchanged passing full affected selection; no tests/timeouts were weakened.
- Authenticated isolated `florabase-geography-5430` review runs at `http://localhost:15276`, backend
  loopback 18276, database revision `20261013_0042`, with a small API-created synthetic fixture and
  separate volumes/network. Existing Review/UAT/DEV/Sourcing/Preview and other worktrees were not
  taken over, reset or reseeded.
- Evidence: **67** captures at 1440×844, 1024×844 and 390×844 across Botanical Light/Dark, Herbarium
  Light and Mineral Dark; **9** browser interaction groups include keyboard/focus, hierarchy,
  exact source records, Back/Forward, real Saved View restoration and labelled empty/error/1000-site
  renderer doubles. Zero page errors, attempted third-party requests or horizontal overflow.
  Handoff and evidence: `docs/geography-visual-001-handoff.md`, `docs/review/geography-visual-001/`.
- Backend/integration/API regeneration and canonical FULL verification were not run because this
  phase changes no backend/API/schema and reserves the final gate for acceptance. True zoom,
  screen-reader/physical-device use, real-large-collection performance and live-provider checks remain
  explicit limits. No staging, commit, push, PR or delivery. `GEOGRAPHY_EXPLORATION_REVIEW_READY`.

## 2026-10-24 — Geography review runtime persistence

- Replaced the stopped session-bound frontend with detached candidate-owned container
  `florabase-geography-5430-frontend`, restart policy `unless-stopped`, on the existing Geography
  network and loopback port 15276. Reused this worktree and its locked dependencies; backend, DB,
  credentials and collection data remain intact. No other environment was changed.
- Frontend startup and proxied `/api/v1/ready` passed. Application suites were not rerun for this
  runtime-only repair; source remains unstaged and uncommitted.

## 2026-10-24 — GEOGRAPHY-VISUAL-001 unified navigation refinement

- Continued the existing `feat/geography-visual-001` candidate at `e7ade78`; no branch reset,
  additional worktree, staging or commit. Feature remains `implemented`, pending operator acceptance
  and canonical verification. This operator-approved refinement supersedes the initial grouped
  navigation and sidebar-preservation scope above.
- Removed only the global Maps subgroup and its three children from Explore/mobile More; Geography
  is the single geographic entry. One six-link internal navigation mounts the complete existing
  Native ranges, Species distribution and Collection origins screens through a shared Geography
  header. Places/Sites stay first-class; Site map remains a local Sites List/Map mode. No renderer,
  provider, dependency, backend/API/schema or shared token changes.
- Canonical `#/geography/*` views coexist with unchanged old map URLs, exact identity/query state,
  management and site deep links. A small directory-state path adapter retains v1 Saved View schemas
  and stored paths. Native anchors preserve normal keyboard/history behavior and modified clicks.
  Stabilized Origins' reset callback after reproducing stale visible search on same-view navigation.
- Reworked Overview into three balanced evidence summaries with explicit unknown occurrence totals,
  direct-record counts qualified to mapped sites and compact Places/Sites access. Existing independent
  load/error/retry behavior, canonical/local restrictions, coordinates and source semantics remain.
- Read-only audited botanical-identity branch `859028a`: its exact legacy map links remain supported.
  Documented the localized Maps removal and shared App/state integration points for IA-NAV-001;
  no other workstream or environment was edited. Fetched main remains `e7ade78`.
- Baseline: **51 passed/2 files**. Final affected frontend selection: **225 passed/15 files**,
  including route/alias/navigation, all map screens, App/lazy/transition, Overview, Saved Views,
  Site management and provider/cache/privacy/tile regressions. TypeScript, zero-warning ESLint,
  formatting and production build passed (refinement verification record). Feature graph:
  **112 valid**; whitespace and empty-index checks passed. Canonical FULL was not run.
- Browser matrix: **126 checks** across seven presentations, 1440×844/1024×844/390×844 and all three
  palettes in Light/Dark. **57** curated exact-dimension captures; active navigation visible, no
  checked horizontal overflow, page errors or third-party requests. Regional Origins/Site map
  captures use existing zoom controls, preserving automatic fitting. Interaction evidence covers
  legacy/canonical reload, exact Native identity selection, filters, Back/Forward, record cross-links,
  local Site map, existing Saved View restoration and mobile keyboard/More navigation. Headless
  Ctrl-click remains unprevented; native tab creation is explicitly unclaimed.
- Preserved the original handoff/gallery and added current evidence under
  `docs/review/geography-visual-001/refinement/`. The isolated persistent review remains on loopback
  15276/18276 with its existing synthetic data. No live provider, actual screen-reader/physical-device,
  true zoom or real-large-collection claim. Coordinate-less exact source-record linking remains an
  explicit API limitation. No push, PR, delivery or final verification receipt.
  `GEOGRAPHY_UNIFIED_NAVIGATION_REVIEW_READY`.

## 2026-10-24 — GEOGRAPHY-VISUAL-001 final UX refinement

- Preserved the accepted six-view IA, global Geography entry and supported canonical/legacy routes.
  Shared Florabase Breadcrumbs now precede every Geography header; Explore is the existing group
  label, Geography links through the canonical route helper to Overview and the active view is named.
  No unsupported Explore landing route or extra navigation strip was introduced.
- Replaced Overview cards with compact divider-led evidence rows and simple geographic-record links.
  Existing local coverage, independent loading/error/retry/empty states and exact links remain;
  occurrence totals stay explicitly unknown and mapped-site record counts remain distinct from quantities.
- Normalized Places density and indentation, reusing the shared selection accent and keeping expand
  separate from select. Preview status, ancestry, parent navigation, child creation, authoritative
  counts, associated-site links and canonical/local restrictions remain. Capped deep indentation
  preserves space for real long names on mobile.
- Fixed New local place backdrop dismissal through existing TaskDialog behavior. Backdrop, native
  Escape and Cancel share pending/dirty checks and the established discard confirmation. A preset
  child parent is a clean baseline; declined discard retains all fields. Focus trapping and return
  to the actual initiating control passed real-browser checks. Five focused clean/dirty/pending
  regressions pass; no global modal or dirty-state mechanism was added.
- Unified Provenance sites into one selected-ID list/map/inspector. Desktop shows all panes; tablet
  places the inspector below list/map; mobile presentation preserves the same DOM and selection.
  Coordinate-less rows remain searchable/selectable/editable in both presentations, with explicit
  missing-coordinate state and no invented marker. Existing map engine, decimal coordinates,
  accuracy, usage, source semantics, local context and provider privacy are preserved. No site
  subtype exists in the API, so no classification was invented.
- Baseline: **17 passed/3 files**. Final retained passing results cover **231 unique tests/15 files**
  across focused runs, including App/lazy/transition, all map screens, breadcrumbs/aliases/state,
  Overview, Place workflows, new dialog safety, site synchronization, coordinate-less records,
  Saved Views and occurrence/cache/privacy/tile behavior. A stale eyebrow assertion now checks the
  actual breadcrumb, and StrictMode waits for the real cold view import; assertions and global
  timeouts were not weakened. Interrupted workers under host memory pressure are not passing evidence.
- Browser evidence: **162 presentation checks**, nine presentations × three viewports × Botanical,
  Herbarium and Mineral Light/Dark; **71** independently size-checked captures (69 ordinary plus two
  labelled browser-only 1000-site renderer doubles). Seven real interaction groups cover hierarchy,
  clean/dirty dialog focus/dismissal, synchronized markers/list/inspector, coordinate-less mobile
  presentation and breadcrumb history/reload. No completed-run page errors, external requests or
  checked horizontal overflow. The large-data doubles are not persisted data or a backend benchmark.
- Fetched latest `origin/main` again before finalizing: still `e7ade78`; no reconciliation/reset or
  other-worktree edit. The candidate-owned persistent review retains its data; protected DEV/Review/
  UAT and other agent environments were not modified. Earlier handoffs and galleries are preserved;
  current evidence is `docs/review/geography-visual-001/final-ux/`.
- Feature remains `implemented`, unstaged and uncommitted. Operator acceptance and canonical FULL
  remain separate; no push, PR, merge, feature-finish, receipt or live-provider/physical-device claim.

## 2026-10-25 — Geography final UX handoff completion

- Completed strict TypeScript, full zero-warning ESLint, full frontend formatting and production build.
  Feature graph: **112 valid**; whitespace and empty-index checks pass. Retained focused evidence:
  **231 unique tests/15 files passed**, plus **16 repeated final-source confirmation tests/2 files**.
  Current reports, **162** presentation checks, **7** interaction groups and **71** size-checked
  screenshots are indexed in `docs/review/geography-visual-001/final-ux/README.md`.
- Latest fetched main remains `e7ade78`. Ownership inventory confirmed only the existing
  `florabase-geography-5430` containers mount this worktree. Started those retained DB/backend/frontend
  containers after they were stopped; existing volumes, records and account are preserved. Review
  readiness and the existing synthetic login passed. No other environment or database was changed.
- Final handoff: `docs/geography-visual-001-handoff.md`. Feature stays `implemented`; everything
  remains unstaged/uncommitted. Canonical FULL, delivery, live-provider, real-device/screen-reader
  and true-zoom checks remain explicitly deferred. No push, PR, merge, receipt or feature-finish.
  `GEOGRAPHY_FINAL_UX_REVIEW_READY`.

## 2026-10-25 — GEOGRAPHY-VISUAL-001 operator corrections

- Restored the accepted balanced three-card Overview with current factual metrics, unknown occurrence
  counts and compact record access. Removed the six-view tab component entirely from every Geography
  view; the hub, canonical breadcrumbs and contextual links now provide geographic navigation.
- Reorganized sites as a LEFT list/inspector rail and RIGHT prominent existing map (37/63). Selection,
  accuracy, edit/detail/source links and coordinate-less discovery remain synchronized. Mobile
  List/Map retains the same record. Measured map/rail bounds fit 1440×844 (y=233–837) and 1024×844
  (y=273–829). Long lists and keyboard-focusable inspectors use intentional panel scrolling;
  mobile keeps complete details in document flow. No map engine or provider behavior changed.
- Places now have moderately rounded shared rows, spacing/borders, selected inset accent, separate
  visible focus and restrained ARIA-expanded chevrons instead of boxed +/−. Leaves have no disclosure.
  Hierarchy, canonical/local rules, create-child behavior and dirty/pending dialog protection remain.
- Extracted the existing Breadcrumbs renderer without changing callers; PageHeader applies one common
  convention to straightforward roots. Unsupported group links to Dashboard are plain labels; exact
  existing parent URLs remain. Named Collection details and missing Explore/Collection prefixes were
  corrected without workflow refactoring. Contextual-task/module exceptions and main reconciliation
  are documented in `docs/geography-breadcrumb-audit.md` as a bounded follow-up.
- Baseline **17 tests/3 files**. Final full frontend: **919 passed/79 files**, plus **47 repeated
  focused confirmations** after lint-only cleanup. Strict TypeScript, zero-warning ESLint, frontend
  formatting, production build, **112-feature** graph, whitespace and empty-index checks passed.
  No tests/assertions or validation were weakened; edit-invalidated attempts are superseded.
- Evidence: **162 Geography +56 global breadcrumb checks**, **6 interaction groups**, **89 current
  size-verified PNGs** (84 matrix +3 selection/focus +2 labelled renderer doubles), and a separate
  provenance-labelled before JPEG from main. Before/after links prove cards, no tabs, rounded rows,
  chevrons, right-edge map, mobile selection and breadcrumbs. Zero completed matrix/interaction page
  errors or attempted external requests. Existing data and previous galleries/handoffs are preserved.
- Fetched `origin/main` at **5778da7 (#121)** and merged it into the feature branch without resetting
  or rebasing either history. Resolved conflicts by retaining both `BOTANICAL-IDENTITIES-VISUAL-001`
  and `GEOGRAPHY-VISUAL-001`, both progress histories, and both App regression sets. Identity-scoped
  SeedLot/Sowing/Plant Saved Views and backend canonicalization coexist with the Geography legacy-route
  adapter; all three IdentityMaps legacy map URLs remain supported. Plant, SeedLot and Sowing
  breadcrumb additions were preserved. IA-NAV's worktree and protected DEV/Review/UAT datasets were
  not modified.
- Current handoff/gallery: `docs/geography-visual-001-handoff.md`,
  `docs/review/geography-visual-001/operator-corrections/README.md`. Feature remains `implemented`;
  operator visual review is complete. Integrated regressions passed **356 tests/12 files** and the
  feature graph validates **113** entries. Canonical FULL, protected delivery and feature-finish remain
  pending. Live-provider, true-zoom, physical-device/screen-reader and contextual breadcrumb checks
  remain deferred. No push, PR or merge.
  `GEOGRAPHY_COMMITTED_READY_FOR_QA`.

## 2026-10-25 — GEOGRAPHY-VISUAL-001 independent QA follow-up

- Reconciliation merge `e501d7c2f068451e11808731e1bb87aa05e03a23` retains the approved Geography
  commit and Botanical Identities #121. Independent cross-feature regression passed **356 tests / 12
  files**; feature graph validates **113** entries.
- First canonical `make verify-full` passed workflow safety, formatting/lint/type checks and backend
  unit tests, then reported **972/975 frontend tests**. Geography, breadcrumb, Places, map and
  Provenance suites passed. Schedule passed **51/51** in isolation; its one full-suite focus failure
  was transient. Import/Export exposed asynchronous test waits around lazy route loading; the tests
  now wait for the loaded links and controls and passed **3/3**.
- The exact-tree canonical gate must be rerun after these reviewed test and handoff updates. No
  product behavior changed during independent QA. Protected delivery, feature-finish and DEV smoke
  have not run. Live-provider, physical-device/screen-reader, true-zoom and contextual breadcrumb
  improvements remain accepted follow-ups.
  `GEOGRAPHY_INDEPENDENT_QA_IN_PROGRESS`.

- Follow-up FULL run passed **974/975 frontend tests**; one `App.test.tsx` geography-create case
  timed out while the lazy route still displayed its loading state. Extended that dialog wait to five
  seconds. Import/Export now passes **3/3**, Schedule passed **51/51**, and the Geography-specific
  workspace, Overview, Places, breadcrumbs, and Provenance tests passed. Canonical FULL must be
  repeated on this final test/documentation tree; no product behavior changed.

- Final canonical `make verify-full` passed on the reconciled final QA tree: **956 backend tests**,
  **975 frontend tests**, and **743 PostgreSQL integration tests**; workflow and feature graph checks,
  formatting, lint, typing, API drift, production builds, migration cycle, whitespace and exact-tree
  receipt passed. The receipt is for branch `feat/geography-visual-001` against
  `5778da7be03bc6030cb0ab3af03b9631bf4fa209`. No product behavior changed during QA. Protected
  delivery, feature-finish and guarded DEV smoke remain pending. Live-provider, physical-device/screen
  reader, true-zoom and contextual breadcrumb improvements remain accepted follow-ups.
  `GEOGRAPHY_QA_VERIFIED_READY_FOR_DELIVERY`.

### TAXONOMY-VISUAL-001 — interactive Tree Explorer extension (2026-10-25)

Added the operator-approved horizontal source-backed graph within the existing
Taxonomy view: independent selection/disclosure, full ranks, source ancestry,
URL-backed branch/rank focus, pan/pinch/zoom/fit/reset, keyboard navigation,
responsive inspector and bounded protected identity thumbnails. Reused Classification,
collection eligibility and explicit matching/409 recovery. No graph dependency,
migration, worldwide source request or inferred taxonomy. Default progressive
expansion, 240 layout nodes, viewport culling and 48 graph thumbnail bounds retain
the 5,000-identity API boundary. The owned synthetic Review was extended additively
to 12 identities/three Basil identities/three cover references without undoing
operator confirmations; source fallback was exercised and restored.

Focused evidence: 28 frontend tests, 49 backend tests, six PostgreSQL integration
cases with disposable cleanup, strict typing, zero-warning ESLint, Ruff, API drift
and production build passed. The 5,000-identity/5,183-node benchmark and six-theme
three-width gallery are linked from `docs/taxonomy-visual-001-handoff.md`.
Latest origin/main is Geography PR #122 (`3902b921`); reconciliation merge `ccd8014`
preserves both route/test and progress histories. The merged App navigation suite
passed 116/116. Impact plan selects FULL; canonical FULL and protected delivery are
pending. CI-004 remains a separate delivery and was not cherry-picked.
Status remains implemented pending canonical verification.

### TAXONOMY-VISUAL-001 — independent QA and delivery (2026-10-26)

- Reconciled approved Taxonomy commit `fee51be` with Geography PR #122 (`3902b921`)
  through `ccd8014`. CI-004 PR #125 (`c570d0a`) later merged independently and was
  integrated from latest `origin/main` with `e2fff88`, not cherry-picked.
- Independent regression evidence: merged `App.test.tsx` **116/116**; Taxonomy
  unit tests **25/25**; CI-004 scope inventory **24/24**. The missing typed fake
  search fixture, backend coverage gap and delivered test inventory were corrected
  without weakening checks.
- Canonical `make feature-verify` against `c570d0a` passed: feature graph **115
  valid**, backend **969 passed / 1 skipped at 90.04% coverage**, frontend **1,007
  passed across 94 files**, PostgreSQL integration **744 passed**, static/style/type
  checks, API drift, production builds, migration cycle and exact-tree receipt.
  Physical-device and screen-reader certification, live-provider validation and
  performance beyond the documented synthetic large-tree benchmark remain unverified.
- Taxonomy status is `verified`. Documentation and registry status were updated after
  that receipt; a final canonical receipt is required for this exact tracked tree
  before protected delivery. No protected environment or unrelated worktree changed.
  `TAXONOMY_QA_VERIFIED_DELIVERY_PENDING`.

## 2026-10-27 — CI Media frontend test inventory hotfix

- On clean `ci/media-test-inventory-hotfix` from `origin/main` `69814bba`, added the two omitted
  Media navigation tests to the `media` frontend impact inventory. The existing drift regression
  already asserts every `.test.` file under classified frontend prefixes is listed, so no duplicate
  assertion was needed. `make test-verification-impact` passed all 24 cases. No production Media
  behavior changed. FULL canonical verification and protected delivery remain pending.

### UI-SYSTEM-001 — Gate A product direction candidate (2026-10-26)

- Fetched delivered `origin/main ee3487412fe458cbdf7145154c54a58b66132cae`
  and inspected parallel Media ownership before creating `docs/ui-system-v1-design`
  in the existing bc88 managed worktree. Preserved the preceding unstaged audit.
- Added `docs/design/ui-system-v1/`: critical KEEP/REFINE/REDESIGN review of 28
  families including shell (13 KEEP, 8 REFINE, 7 REDESIGN), five structural A/B
  comparisons, 25 main design variants, seven proposed archetypes and 22 component
  contracts. Reused actual Foundation tokens and v5 data; no production UI edits.
- Read/hash-checked 270 audit images and paired DOM evidence; reviewed 17 baseline
  contact sheets and 15 design sheets. Corrected the interpretation of Location 297
  as transient/unselected. Identity covers, specimen photos, recorded provenance,
  native ranges and observed occurrences remain distinct.
- Working read-only review: `http://localhost:15283/`. Captured 75 desktop/tablet/
  mobile renders, 12 six-theme examples and 8 contextual Group/Edit states. No
  document horizontal overflow or broken images in this matrix; 22 bounded local
  interaction assertions and 30 sampled semantic-role contrast checks passed.
  Tablet Seeds header is 132.5px in the proposed layout. These are design renders,
  not production regression certification or real browser-zoom evidence.
- Checks: `python3 docs/design/ui-system-v1/validate.py` passed 221 local HTML
  references, 124 fixture records, 8 photo hashes, 28 decisions and capture/focus
  assertions; `node --check` passed; Python compilation passed; feature graph
  **117 valid**. Package formatting and final diff hygiene are checked separately.
- Documented Media's independently reported scoped F01/F09 corrections and
  integration requirements without copying code or taking over its environment.
  Maps/Taxonomy retain accepted specialist architecture and evidence contracts.
- Gate B remains pending operator direction acceptance: actual React templates,
  safe scaffold, dev-only living React lab, two real integrations and policy-selected
  canonical verification. `UI-SYSTEM-001` remains `in_progress`. No canonical FULL,
  staging, commit, push, PR, application mutation or protected environment change.
  Physical devices, assistive technology, actual zoom and print/provider acceptance
  remain unverified. `FLORABASE_UI_SYSTEM_V1_DESIGN_READY_FOR_REVIEW`.

### UI-SYSTEM-001 — approved Gate B, production Wave 1 review (2026-10-27)

- Preserved the complete dirty candidate and normally fast-forwarded this managed feature branch to
  delivered Media #127 and its separate CI inventory hotfix #128, `c77a1c5`; a fresh fetch confirmed
  the same main. No unrelated CI implementation, new worktree, history rewrite or primary change.
- Migrated actual Dashboard, Seeds and Plants through composed Directory primitives, optional native/
  inline inspectors, truthful image-source fallbacks and typed semantic icons. Existing domain APIs,
  quantities/precision, Active/History, groups/lineage/transfers, editing, Saved Views, bulk moves and
  navigation remain owned by their capabilities. View-only Back/Forward retains safe bulk choices.
- Dashboard's existing endpoint gains one bounded read-only photo projection, deduplicated by stored
  content before its limit; generated OpenAPI/TypeScript artifacts are checked. No schema migration,
  provider fetch or fabricated specimen association. Eight protected images and all five Next work
  entries fit the measured 1440×844 Light/Dark viewport; all recent facts remain in a native disclosure.
- Actual Review `localhost:15279` preserves its v4/v5 data. Explicit operator approval initialized a
  separate two-image/zero-collection Review at `127.0.0.1:15285`; cookie hosts stay separate. No foreign
  Review, DEV/UAT/stable/production reset. Read-only comparison portal: `localhost:15283/wave1/`.
- Final scoped frontend evidence: **402 distinct tests / 20 files** across passing screen/shared runs,
  including the final **134/134** App/Dashboard/Directory rerun. Backend contract **3/3**, PostgreSQL
  Dashboard **5/5** with zero residual disposable resources, scaffold generator **3/3**, impact policy
  **24/24**, strict typing/lint/format, API drift, feature graph **118 valid**, production build and lab/
  generated-example exclusion. No assertion weakening or timeout increase. App interaction fixtures
  preload their lazy identity module; dedicated lazy-loading acceptance remains separate and passing.
- `docs/design/ui-system-v1/wave1/` contains architecture/source inventory, generated scaffold demo,
  before/after gallery, 58 real/context/developer captures (40-case production matrix), Dashboard
  geometry, exact evidence limits and a recommended unimplemented Wave 2. All prior evidence retained.
- UI-SYSTEM-001 remains `in_progress`. Canonical FULL, coverage/full integration/migration cycle,
  physical devices, assistive technology and actual browser zoom remain pending. No staging, commit,
  push, PR or merge. `FLORABASE_UI_SYSTEM_V1_WAVE1_READY_FOR_REVIEW`.

### UI-SYSTEM-001 — Wave 1 final UX refinements (2026-10-29)

- Retained the approved architecture and unstaged candidate. Refined Seeds/Plants List/Gallery
  hierarchy, bounded names, exact/approximate/unknown quantities and distinct always-visible
  Preview/Details/Edit controls. Native TaskDialog now provides desktop/mobile overlays without
  reducing directory width; source/location and domain operations remain accessible.
- Extended existing bulk selection with Ctrl/Cmd entry, visible checkboxes, explicit exit and safe
  representation/history retention. Preserved the 100-record cap and existing atomic server preview/
  Apply contract. A focus race on extraction Cancel was corrected without weakening its assertion.
- Dashboard now samples up to eight actual active individual Plants across the full relation,
  retains a visit's sample, links to Plant details and separates protected primary/reference/missing
  imagery. Nine existing Quick add destinations retain labels and gain distinct typed icons.
- Final report/comparison gallery: `docs/design/ui-system-v1/wave1/refinements/`, 80 real JPEGs,
  complete 40-case responsive Light/Dark matrix, 32 overlay/selection captures and contextual proof.
  Both 1440x844 Dashboard extents fit all eight Plant cards, KPIs and five Next work entries.
- Focused frontend evidence totals 317 distinct cases/13 files across scoped runs, backend contract
  3/3; scoped typing/lint/format/API/build and production lab exclusion pass. Final isolated PostgreSQL
  result and exact limits are recorded in the refinement verification report. Earlier raw /tmp logs
  were lost on host restart; passing tool outputs remain in the chat. Review DB/media were preserved;
  only its verified stopped application containers were restarted.
- Audited cross-domain bulk recommendations remain proposals. DASHBOARD-CUSTOMIZATION-001 is planned
  only. UI-SYSTEM-001 remains in_progress. No canonical FULL, staging, commit, push, PR or merge.
  Final production UI approval precedes independent QA and delivery.

### UI-SYSTEM-001 — final Plants Gallery and QA handoff (2026-10-29)

- Operator approved the Wave 1 framework subject to the Gallery correction. Only Plants/PlantGroups
  opt into photographic titles: 4:3 cover images, dark title gradient, two-line names clear of
  selection, compact honest placeholders and a light shared 44px three-action toolbar.
- Preserved primary/reference labels and all existing selection, Preview, navigation and Edit
  callbacks. Independent source review corrected checkbox/title overlap and found no further
  concrete blocker. No fixture or collection writes.
- Final Gallery evidence contains 36 six-theme/three-size/context captures plus one mobile body
  capture, source/hash/geometry checks and a disclosed historical comparison. Unaffected evidence
  is retained. Final focused checks and environmental limits are in gallery-final.md.
- Operator now authorizes a reviewed implementation commit and independent QA handoff. Feature
  remains in_progress until acceptance and the policy-selected FULL gate succeed. Independent QA
  owns canonical verification and protected delivery; no push, PR or merge in implementation.
  FLORABASE_UI_SYSTEM_V1_WAVE1_READY_FOR_INDEPENDENT_QA.

### UI-SYSTEM-001 — independent QA corrections (2026-10-29)

- Corrected the UI Lab fixture boundary by keeping the already approved, attributed botanical images
  beside the frontend module that uses them; the canonical Docker context can now resolve them.
- Kept Dashboard recent activity visible on entry, preserving its existing content and native
  disclosure behavior. Updated only accessible-name assertions to match the approved
  `Individual Plants` metric label; counts and destinations are unchanged.
- Gave the lazy SeedLot creation assertion enough time for its route chunk to load, without changing
  the expected form or identity assertion. Reused stable button nodes in the 100-record selection
  boundary test to avoid repeating expensive accessible-name queries.
- Focused checks passed: Propagation/UX/Dashboard **34/34**, bulk cap **1/1**, media return focus
  **1/1**, and UI Lab **4/4**. Canonical FULL verification passed on the final reconciled tree.

### UI-SYSTEM-001 — Wave 3 Batch 1 safety handoff (2026-10-29)

- Dedicated isolated `548f` checkout attached through `make feature-init` to
  `feat/ui-system-v1-wave3`, base `5b2e2a1`. Wave 1 #129 is merged; Wave 2 is
  still unmerged. Batches 2–4 deliberately remain unstarted.
- Page-owned Cancel-first/danger confirmations correct Harvest deletion and Stored
  material tracking removal. Existing pending locks, error retention and stable
  More-trigger focus return remain. Location creation and inventory/disposition/
  conversion tasks protect changed drafts while pristine dismissal remains immediate.
  Shared TaskDialog/EditWorkspace, APIs, schema and domain rules are unchanged.
- Focused baseline: 44 domain tests passed. Changed-tree checks cover 16 Harvest,
  24 Stored material, 10 Conversion and 19 selected Location tests (69 distinct
  cases; 99 unrelated App cases excluded). Final static results and exact limits
  are in the Batch 1 handoff. Test-only lint corrections preserved all assertions.
- One worktree-owned Quality project was used serially; Wave 2 and all Review,
  DEV/UAT environments were preserved. No canonical gate, production build, live
  browser/theme/viewport/zoom/device/AT acceptance, commit, push, PR or merge.
  UI-SYSTEM-001 remains in_progress. See
  [Batch 1 handoff and UAT checklist](design/ui-system-v1/wave3/README.md).

## 2026-10-29 — UI System v1 Wave 2 ready for operator UAT

- Verified clean primary `main` and freshly fetched `origin/main` at `afcfbab` (Wave 1 PR #129).
  Canonical `make feature-start BRANCH=feat/ui-system-v1-wave2` attached the existing isolated
  Codex `bf7a` worktree. [Compliance matrix and handoff](design/ui-system-v1/wave2/README.md)
  distinguish shared adaptations, existing compliant editors and genuine Calendar/domain exceptions.
- Journal, History and Schedule now compose through ActivityPage and shared DirectoryTools, replacing
  the duplicated Activity drawer/chips. Suppliers/Orders adopt shared full-width List/Gallery,
  explicit Preview/Details/Edit, close-first overlay previews and reconnected focus return.
  Domain chronology, APIs, canonical filters/Saved Views, pagination, calendar controls, transaction/
  packet relationships and existing create/detail/edit behavior remain capability-owned.
- Independently owned populated canonical Review at **http://localhost:15174** is healthy, on code/DB
  `20261013_0042`, with guarded v4/80 and v5/252 synthetic fixture references. Evidence gallery at
  **http://localhost:15285** contains **154 settled captures**: all 144 primary combinations across
  eight presentation states, measured 1440/1024/390×844 CSS and all six themes, plus ten contextual
  samples. Actual JPEG raster dimensions/digests are recorded separately. No horizontal overflow.
  Invalid resize/stale and failed acquisitions are excluded. DEV, existing data, foreign Docker
  resources and WCVP implementation worktrees were preserved.
- Untouched-main archive baseline **97/97**; final focused boundary **144/144 in 12 files** passed,
  including four new Sourcing navigation/pagination/focus cases. Complete frontend ESLint,
  TypeScript, Prettier, production build, API drift, 120-feature graph and whitespace pass.
  Initial broad `make check` stopped at transient-source formatting during dependency bootstrap;
  it is not counted as a baseline or FULL pass. Earlier test/static failures were corrected.
- Live mobile Preview/Escape/Edit/Cancel focus and exact return URLs, Journal immediate filters/
  reset/empty results and Calendar overflow/period/Today were checked without browser domain writes.
  Physical devices, AT, actual browser zoom, forced colors, injected live failures and scale remain
  explicit limits. The handoff lists operator UAT scenarios and existing genuine exceptions.
- CI-004 plans **FULL** for shared Activity composition/styling. Per canonical UI review order,
  operator acceptance and independent correctness review precede the one final `make feature-verify`;
  canonical FULL/integration/migration cycling are still pending. `UI-SYSTEM-WAVE2-001` is
  `implemented`, not `verified`. Source remains unstaged/uncommitted; no push, PR or merge.
  Stop marker: `FLORABASE_UI_SYSTEM_V1_WAVE2_READY_FOR_OPERATOR_UAT`.

## 2026-10-29 — Wave 2 operator approved; local commit for independent QA

- Operator reports **all six UAT scenarios PASSED**, freezes the approved UI/UX scope and authorizes
  the local implementation commit before independent QA and canonical FULL. No new UAT or design
  cycle is requested. [Independent QA handoff](design/ui-system-v1/wave2/independent-qa.md).
- Audited the complete candidate diff and both untracked additions. Before these documentation-only
  status updates, the exact source fingerprint matched the approved evidence:
  `dc0c69259ad891bdf536cf82c5960e3f1726f4b5d61b6baf22e7b4ed533fd6b9`.
  Activity/Sourcing implementation and tests remain unchanged. Only Wave 2 source, regression tests,
  CSS and documentation are included; no credentials, screenshots, fixtures, build output or caches.
- Fresh `origin/main` is `5b2e2a1fadffa30de4e9129fe01750c71efb6d6c` (WCVP-VERSION-001 #130),
  one commit beyond this candidate's base `afcfbab334622d64cca2cdb2ea4c8f6a51ad957f`.
  Implementation paths do not overlap; only `docs/features.json` and `docs/progress.md` overlap.
  Reconciliation is required before canonical verification; it is deliberately left to QA rather
  than importing unrelated WCVP changes into the approved implementation commit. Primary main,
  other worktrees and existing Review/DEV/UAT environments are unchanged.
- Retained evidence revalidated: **154/154** screenshot digests and **144 passed tests in 12 files**;
  prior lint/typing/format/build/API drift evidence remains attached to the unchanged implementation.
  Current feature graph **120 valid** and diff whitespace pass. No canonical gate was run or duplicated.
- `UI-SYSTEM-WAVE2-001` remains `implemented`; independent QA reconciles current main, reviews/fixes
  objective defects, freezes source/index and runs one CI-004-selected canonical **FULL** gate.
  No push, PR, merge or feature-finish in this local-commit task.

### UI-SYSTEM-001 — Wave 3 reconciliation and adaptation in progress (2026-10-29)

- Normal merge `13c3233` reconciles delivered Wave 2 #131 (`76c0911`) while
  preserving Batch 1 checkpoint `3669869`. The progress-only conflict retained
  both milestones. Shared Directory/dialog/Saved Views/navigation contracts were
  inspected; only ActivityPage/shared Sourcing CSS changed in the delivered wave.
- Initial page adaptations add shared Sowing records/presentation/actions/overlay,
  Harvest explicit actions and overlay, exact stored inventory links and Location
  loading/error/missing states. Shared components and SeedLots/Plants/PlantGroups
  remain unchanged.
- The original 10 failing cases were diagnosed and resolved. Three Sowing tests
  queried rows by partial names that also matched newly explicit Preview/Details/Edit
  actions; one additionally expected the former inline preview, while the approved
  overlay contract now presents a modal. Six Harvest tests had the same action-name
  ambiguity; retry itself succeeded. The Stored Material test expected the old
  Harvest-only URL; the intended exact inventory URL is now asserted. Location's
  deep-link test also now asserts its explicit missing-record state and return link.
- Focused Wave 3 suites passed **83/83** (Sowing 33, Harvest 16, Stored Material 24,
  Conversion 10). The preserved Batch 1 safety baseline passed **69/69** (50
  Harvest/Stored Material/Conversion and 19 selected Location App cases).
  `pnpm typecheck`, affected-file ESLint with zero warnings, Prettier write/check,
  `python3 scripts/check-features.py` (121 valid) and `git diff --check` passed.
- The prior Feature Review owner safely retired its project. Read-only status
  showed no foreign owner, and Docker reported no remaining project containers,
  volumes or networks. `make feature-review-up` provisioned the canonical Review
  for this worktree; current health, ownership and migration head are verified at
  `13c3233`. The Review database is clean and its v4 synthetic fixture and owner
  are not yet provisioned. Owner password entry is handed off to the operator.
- No FULL gate, push, PR, delivery, shared component change or resource cleanup.
  Responsive/theme visual evidence and operator UAT remain pending.

### UI-SYSTEM-001 — Wave 3 Review and visual handoff (2026-10-29)

- The operator completed the canonical Review-only owner bootstrap interactively.
  The UI showed `Signed in as owner`; no password was read, copied or recorded.
  The canonical v4 Review seeder reported ready, 80 baseline records, and preserved
  the owner and existing edits. The post-seed lifecycle check showed this worktree
  as the Review source, healthy frontend/backend/database, and migration head
  `20261013_0042`. An initial status refresh was blocked by Docker socket
  permission; a read-only retry then confirmed source, health and fixture state.
- Browser screenshots covered Harvests, Stored material and Locations in all six
  themes at 1440×900, with all three surfaces also inspected at 1024×900 and
  390×844. Sowings Gallery covered all six themes at 1440×900 and Botanical Light
  at 1024×900 and 390×844; List and Gallery were both inspected in Botanical Light.
  Captures show the populated pages and the in-flight loading states. Location's
  missing-record state and return link were checked. The inline screenshots are
  visible in the review conversation; no image archive or separate gallery URL
  was created. All 12 surface/viewport combinations (four routes × three widths)
  reported no horizontal page overflow.
- Verified Harvest Preview Escape returns focus to its trigger; Delete opens with
  Cancel focused, and Escape cancels without mutation. Location dirty Cancel opens
  the discard prompt; rejecting preserves the entered text and accepting discards
  the temporary draft. Stored Material opens the exact inventory query and scrolls
  the target into view. Existing affected tests cover retryable Location errors,
  pending operations and save failures; no live service outage was injected.
- Review URL: `http://localhost:15174`. Viewports are browser-emulated CSS sizes;
  physical devices, actual browser zoom and screen-reader/assistive-technology
  checks remain unverified. The UAT checklist and current evidence notes are in
  [Wave 3 progress and compliance matrix](design/ui-system-v1/wave3/README.md).
- Preserved regression evidence remains Wave 3 focused **83/83** and Batch 1 safety
  baseline **69/69**, with the previously passing strict TypeScript, affected ESLint,
  Prettier and feature-registry checks. No application source changed during this
  review; only documentation is being updated. No FULL gate, push, PR, merge,
  feature-finish, additional Docker mutation beyond the authorized Review setup and
  fixture seed, or resource cleanup was performed.

### UI-SYSTEM-001 — Wave 3 final operator refinement candidate (2026-10-30)

- Operator has **not accepted** Wave 3 and requested card/photo/preview/hierarchy
  refinements. The operator clarified that the photo concerns affect **all**
  galleries. This candidate supersedes the previous operator-UAT-ready handoff.
- DirectoryInspector now defaults to an accessible nonmodal side panel across
  Collection/Sourcing consumers. Desktop/tablet use separate columns; mobile
  stacks a bounded inspector above results. No backdrop, inert list or Tab trap;
  other records stay interactive. Close/Escape restore the latest connected
  trigger/fallback; task dialogs and existing control layers retain priority.
  Domain API/URL/Saved Views/selection/editor/deletion ownership is unchanged.
- Reproduced an empty Harvest photo preview at 840px: the legacy <=1024px
  QuickPreview hide rule suppressed nested content. The <=768px detail-pane hide
  rule was also overridden for active nonmodal previews. Source captions lacked
  an image-positioned containing block; side-panel visuals now anchor them.
  Gallery source badges no longer form a dark strip; source text/alt/native titles
  remain available. Mixed photo/placeholder card rows stretch to equal bottoms,
  with existing bottom actions and compact placeholders retained.
- Locations adopts Geography management's chevrons, branch-row presentation,
  focusable hierarchy root and matching compact-depth threshold. Location-specific
  usage counts, explicit scopes, ancestor retention/filter expansion overrides,
  retired states, parent protection, actions and Batch 1 guards are preserved.
- **377/377 tests in 11 files passed**, including the full 118-case App suite,
  Seeds, Plants, Suppliers, Orders, shared directory/RecordVisual and the complete
  Wave 3 domain regression set (33 Sowings, 17 Harvests, 24 Stored Material,
  10 Conversion). All original **69 Batch 1 safety cases** pass within this run;
  the additional Harvest photo/switching case expands that boundary to 70.
  New assertions cover nonmodal interaction/free Tab/latest-trigger Escape,
  photo-source switching/fallback and Location chevron/root semantics. An initial
  82/83 run exposed one stale Harvest dialog-role expectation; it was corrected
  for the requested nonmodal contract. Test callbacks were adjusted for lint
  without changing assertions.
- Strict TypeScript, affected-file ESLint (zero warnings), Prettier, 121-feature
  validation and whitespace checks passed. Only focused checks ran; canonical
  QA/FULL/feature-verify was not started. The existing local Batch 1 checkpoint
  3669869 and reconciliation merge 13c3233 remain intact; source is uncommitted.
- Canonical `make feature-review-extended-seed` added the standard v5 synthetic
  dataset: **252 managed references**, ready, preserving v4/80, owner and existing
  edits. Final owned Review status confirms healthy frontend/backend/database and
  code/database head **20261013_0042** at http://localhost:15174. No DEV/UAT or
  foreign Review worktree/resources were changed; no cleanup was performed.
- Inline browser evidence includes the before blank photo dialog, fixed photo
  side panel, record switching/Escape focus, mixed Plants cards and Sowing preview,
  plus expanded Location hierarchy. Six settled 1440px mixed-card/side-preview
  captures cover all six themes: loaded photos, no modal and no horizontal
  overflow. Three mixed cards shared bottom 580.015625px/action baseline
  579.015625px. Also checked 1024px columns and 390px stacked preview/hierarchy.
  Screenshot binaries were emitted inline; no standalone archive is claimed.
  Physical devices, actual browser zoom, AT and live outage injection remain limits.
- Updated [operator checklist and refinement handoff](design/ui-system-v1/wave3/README.md),
  UI contract and Gate B preview guidance. Operator review/acceptance is pending.
  No commit, push, PR, merge or feature-finish in this refinement pass.

### 2026-10-30 — UI System v1 global directory refinement (operator review pending)

- Shared native record-surface Preview replaces the eye action; explicit Details/Edit,
  bulk/modifier precedence and native modified Sourcing links remain. Compact status
  indicators reuse StatusBadge/Icon without collapsing richer lifecycle states.
- Eligible Collection/Sourcing directories now bound results scrolling separately
  from identity/tools/chips. Compact nonmodal inspector has a stable reserved column,
  independent body and footer; mobile stacks short identity/actions above results.
  Short viewports deliberately fall back to flow. Specialized workspaces stay distinct.
- Corrected real Sourcing trigger-focus reconnection, preview remount during refresh,
  escaped accessibility labels inflating outer scroll, and compressed gallery rows.
- Final focused combined run **381/381 across 11 files** includes all original
  **69 Batch 1 safety cases**, full App118 and Wave 3 domain regressions. TypeScript,
  zero-warning affected ESLint, formatting, API drift, 121-feature graph and diff
  whitespace pass. Updated intentional click-to-Details expectations retain domain
  assertions. Impact planner requires eventual **FULL**, deferred until acceptance.
- Healthy owned Review at http://localhost:15174 uses this worktree and migration
  20261013_0042; baseline fixture v4/80 ready and prior extended v5/252 preserved.
  Measured long-list scroll keeps header/inspector and outer shell stationary.
  Six-theme 1440px photo checks and 1024/390/320 layouts have no horizontal overflow;
  final 320px screenshot shows visible results and accessible compact footer.
- Updated UI contract, framework guidance, feature criterion and Wave 3 matrix,
  evidence index and operator checklist. Browser evidence is inline, no standalone
  image archive. Real browser zoom, physical devices, screen readers and live outage
  injection remain unverified. Source remains uncommitted; no FULL, push, PR, merge,
  feature-finish or foreign environment changes. Operator acceptance is pending.
- The browser session expired during an extra final Supplier spot-check after
  completed visual evidence and Seeds Escape/reopen scroll retention. Live UAT
  requires operator sign-in; no credentials were accessed or recorded.
- Final Supplier Active/Retired trigger description: TypeScript, affected lint/
  formatting and 13/13 Supplier tests passed again; final responsive CSS format
  check passed. No implementation commit was created.

### 2026-10-30 — Operator browser annotations corrected

- Themed thin native results/Preview scrollbars; whole-row/card hover, preview/bulk
  highlight and keyboard focus now include Details/Edit. Native trigger and action
  children remain transparent; accounted for Tooltip's intervening wrapper.
- Restored existing idle inspector guidance in Seeds, Plants/groups and Sowings
  (hidden on mobile). Seeds Gallery uses Plants' quiet right-aligned actions.
  Corrected discarded Sowing selected prop and bulk visual precedence, retaining
  actual selection membership, routes and domain operations.
- **382/382 tests across 11 files pass**, including the original 69 Batch 1 cases;
  added/extended placeholder, whole-record highlight and bulk deselection coverage.
  Strict TypeScript, affected zero-warning lint, formatting, graph121 and whitespace
  pass. Prior API drift evidence retained; no API/backend change.
- Inline 1317px Seeds List/Gallery/idle and Plants selected screenshots plus six-theme
  computed-style checks verify continuous highlight and themed scrollbars. 390px idle
  pane hidden, 320px open Preview leaves ~149px of results, 1024px no horizontal
  overflow. Keyboard Escape restores the whole-record focus outline without selection.
  Owned Review remains healthy; operator signed in interactively, no credential access.
- Updated Wave 3 evidence/UAT and UI contract. No FULL, commit, push, PR, merge or
  environment cleanup. Operator acceptance remains pending; previous physical-device,
  actual zoom and screen-reader limitations still apply.

### 2026-10-30 — Text lifecycle and stable directory header follow-up

- Restored Active text in compatible Collection/Supplier rows. Sowing Failed and
  Abandoned now use danger colors; Completed remains distinct.
- Moved Seeds/Plants/Sowings count and Select records into toolbar actions, removing
  the separate line above results. Opt-in stable filter-summary lane preserves
  header height whether filters exist or not; many chips scroll horizontally.
- Final combined focused run: 382/382 across 11 files, including original Batch 1
  cases. Strict TypeScript, affected zero-warning ESLint, Prettier, graph121 and
  whitespace pass. First static attempt needed a formatting refresh after edits;
  final run passed. Prior API evidence retained; no backend/API changes.
- Browser control unavailable for this pass; fresh visual alignment evidence remains
  pending and prior screenshots are historical. No FULL, commit, push, PR or merge.

### 2026-10-30 — Collection pagination and photographic overlap correction

- Seeds/Plants/Sowings count and Select records restored above results, with 20
  default records/page, 50/100/All options, bounded navigation and explicit matching,
  global and displayed-range counts. Filters/size reset pagination; bulk remains
  displayed-page-only and retains the 100-record limit. Saved Views/API unchanged.
- Shortened Collection subtitles. Removed absolute photo-title positioning causing
  Plants title/Active/scientific-name collision; browser geometry confirms separation.
- 383/383 combined focused tests pass, including Batch 1. Final mobile arrow/layout
  refinement: shared16/16, strict typing, affected lint/formatting pass. Graph121 and
  whitespace pass. Existing API no-drift evidence retained.
- Real Review checks show Seeds pages 1–20/21–40, truthful 40 matching/43 total,
  Plants 24 matching/26 total, All option and list/pane tops exactly aligned.
  At <=400px, page-flow fallback avoids an unusably short list; measured422px list
  at320x844 with Preview. Inline screenshots updated. Physical devices/AT/zoom remain
  unverified. Owned Review healthy at migration20261013_0042. No FULL, commit,
  push, PR, merge or cleanup; operator acceptance pending.

### 2026-10-30 — Compact pagination composition

- Replaced widely spaced full-size primary Previous/Next controls with one compact
  cluster using existing IconButton chevrons, tooltips, page position and native
  Per page select. Left range/count summary remains factual; Select records is
  visually separate from navigation. Carbon pagination guidelines informed grouping.
- Desktop first/second page and bulk mode verified in Review; mobile two-row grid
  checked at320px with no horizontal overflow or exposed arrow labels. Existing
  pagination/All/bulk safety semantics preserved. Browser viewport restored.
- Combined383/383 focused tests pass, including Batch 1. TypeScript, affected ESLint,
  formatting, graph121 and whitespace pass. Final stylesheet/shared16-case rerun
  supplements that result; no backend/API change. Updated evidence/UAT notes.
- No FULL, commit, push, PR, merge or cleanup. Operator acceptance remains pending;
  actual device, zoom and screen-reader limits remain as previously documented.

### 2026-10-30 — Directory quick actions and Carbon pagination follow-up

- Added an explicit Preview icon beside Details/Edit in shared Collection/Sourcing
  directory actions while retaining row/card Quick Preview. Stored Material now has
  a nonmodal inspector with Escape/Close focus return and an exact Harvest inventory
  destination. Preview action names are distinct from record-surface names for assistive
  technology. Sowings gallery actions use the existing shared bottom-aligned layout.
- Adopted shared compact Carbon pagination for Harvests, Stored Material, Suppliers,
  Orders and Botanical identities: 20 by default, 50/100/All, matching/total/range,
  and filter/size page reset. Orders keep server pagination, with All loading all API
  pages; bulk semantics remain displayed-page-only. Saved Views, domain filters and
  navigation contracts remain unchanged.
- Focused regressions: **257/257** across 10 suites, including Seeds/Plants/Sowings
  shared-action coverage and Stored Material preview dismissal/focus. Strict TypeScript
  and zero-warning affected ESLint passed; Prettier, the 123-feature graph and
  `git diff --check` pass. No canonical FULL or Review environment change was made.
- Live browser capture was unavailable in the current session, so the annotated
  1317×900 screenshots remain the visual reference, not new before/after evidence.
  Responsive browser/device, actual zoom and screen-reader checks remain for operator
  review. No push, PR, merge or feature-finish.

## 2026-10-30 — Activity concept and isolated Schedule UX review

- Freshly fetched `origin/main` / primary `main` at `76c0911` (PR #131); initialized the existing
  clean Codex `28ce` worktree as `feat/activity-concept-schedule-prototype` with `make feature-init`.
  [Study and handoff](design/activity-concept/handoff.md) audit actual Event/Journal/History/Schedule
  and media contracts, distinguish new Journal storage/API requirements, provide recording-first
  journeys/wireframes, compact read-only History guidance and an official-source Schedule matrix.
- Added a separate development-only frontend Schedule prototype at loopback **15286/activity-lab/**,
  with Agenda, compact date rail, optional date-only Week, reused Month and responsive inspection.
  Actual Schedule rows, target pickers and guarded ActivityDialog are reused; the sole production
  source edit exports that dialog without behavioral changes. Synthetic fetch never forwards requests;
  changes and explicit Event receipts remain in memory. No Journal persistence/API, generated contract,
  shared primitive, Wave 3 worktree, Docker or Review resource changed.
- Baseline **75/75**; final **86/86** tests in six suites, including **11** new prototype cases.
  Complete frontend ESLint/Prettier, strict TypeScript, production build, existing UI Lab exclusion,
  Activity prototype exclusion across **125** emitted text assets, **122-feature** graph, local links,
  capture integrity and diff whitespace pass. Node 24.22.1 / available pnpm 11.25.0 differs from the
  declared pnpm 11.19.0; lockfile and dependencies are unchanged.
- **54** primary settled captures cover three views × desktop/tablet/mobile × six themes; all have
  measured 844px-high viewports and no horizontal document overflow. **Six** contextual captures and
  native synthetic completion/filter/inspection/discard smoke supplement them. Raster sizes/digests,
  source manifest and explicit manual/AT/zoom/backend limits are recorded. Week dense-day columns,
  mobile header density, selected-day paging at scale and cross-period overdue attention remain
  operator decisions before production integration; no usability or independent acceptance is claimed.
- `ACTIVITY-CONCEPT-001` is `implemented` for the study only, not `verified`. A reviewed local study
  commit follows focused checks and final diff review. Per task scope no canonical FULL/feature-verify,
  PostgreSQL/migration/API gate,
  protected delivery, push, PR, merge or feature-finish ran. Operator decisions and phased production
  work are in the handoff. **FLORABASE_ACTIVITY_CONCEPT_AND_SCHEDULE_UX_REVIEW_READY**.

### Activity prototype — annotated Month navigation refinement (2026-10-30)

- Applied the operator's two browser annotations only: Month now uses the same separate navigation
  row as Agenda/Week, with Previous month, Today, Next month and Jump to date. Month retains its grid;
  the existing embedded compact navigation is hidden only inside this prototype. Shared components
  and production Schedule behavior are unchanged.
- Strict frontend TypeScript, scoped ESLint, 11 prototype tests and diff whitespace pass. Existing
  Month screenshots are historical and the evidence source manifest records the refinement.
  Browser reinspection was unavailable after the session reported an unavailable browser handle;
  no fresh graphical acceptance is claimed. No canonical FULL or delivery was run.

### Activity prototype — final visual closure (2026-10-30)

- Recovered the browser session and verified the annotated Month navigation at the operator's
  840px viewport: Month uses the common period toolbar, Next month navigates forward and Today
  restores October 2026. No horizontal overflow (825px document width / 840px viewport).
  `docs/design/activity-concept/evidence/month-navigation-final.jpg` records the final result.
  This resolves the preceding browser-inspection limitation. Scope remains concept/prototype review;
  no canonical FULL, protected delivery or feature-finish is authorized or performed.

## 2026-10-30 — Schedule production UX ready for operator UAT

- Fetched main remains `76c0911`; `feat/schedule-ux` retains approved prototype through `b8d066f`.
  Audited active dirty Wave 3 at `548f` and avoided all shared primitive/environment modifications.
- Production Agenda/Month reuse authenticated Schedule services and actual dialogs; common period,
  Today and date-jump controls preserve canonical URLs/filters and browser state. Exact selected-day
  Agenda bounds run server-side before pagination; continuous Agenda remains default. Week stays in
  the laboratory. Journal persistence, source-derived History and all backend contracts are unchanged.
- [UAT handoff](design/schedule-ux/README.md): isolated guarded UAT Review at **localhost:25288**,
  project `florabase-uat-preview-smoke-28ce00000001`, v4/66 baseline, existing code/DB `20261013_0042`.
  Wave 3 Review at 15174 and DEV remain untouched. Synthetic `preview / preview` access is UAT-only.
- Baseline **75/75**; final **76/76** in five Schedule/Activity suites, complete ESLint/Prettier,
  strict TypeScript and production build pass. Real authenticated server smoke covers persistence,
  reschedule, stale 409, no-Event completion, terminal guards, cancellation and date validation.
  Native UI save/reload persistence, Month Next/Back/Today and selected-day reload pass.
- **36** primary responsive/six-theme captures have no horizontal document overflow; two supplemental
  captures and both reviewed contact sheets accompany raster/digest evidence. Physical devices, AT,
  actual zoom, live network-failure injection, rollover and scale remain explicit limits.
- Policy selects FULL, including inherited unclassified laboratory paths; no policy exception was
  introduced. Per operator direction, canonical FULL and delivery await UAT. `SCHEDULE-UX-001` is
  implemented, not verified. No PR, push, merge or feature-finish performed.
  **FLORABASE_SCHEDULE_UX_READY_FOR_OPERATOR_UAT**.

## 2026-10-30 — Wave 3 isolated cross-application QA

- Created isolated branch `qa/wave3-independent` from the unchanged Wave 3 checkpoint
  `81962b2407e3ff1187753b1eabcffe3b9dfefae0` (tree `9fee87874fd67af7bc6c359d8e38724948ea4f10`).
  Confirmed local `origin/main` is `fbce3c4cfad26bdfa3297d53a1e65a7ec6a0ad65` and merged it
  without rewriting history. The only conflict was the append-only progress log; both prior
  milestones were retained. Integration commit: `2be886a1cfc997365e1cfe2ba7ab4bbe58079471`.
- Cross-application review found the shared DirectoryPage, DirectoryTools, DirectoryResults,
  DirectoryInspector, Saved Views, and status patterns consistently used by Collection and
  Sourcing. Media and botanical identities use directory tools with their own content previews;
  Taxonomy, Geography, Locations hierarchy, Journal, History, Schedule, labels/import-export,
  and Settings retain justified specialized interactions. No bounded corrective code change
  was supported by evidence; domain semantics and specialized navigation remain intact.
- **557/557** focused tests pass across **32** suites covering Collection, Sourcing, shared
  directory/visuals, Schedule, Reference, Explore, History, and Location routing. Strict
  TypeScript, affected-file ESLint, Prettier, 123-feature validation, and staged/working diff
  whitespace checks pass. One initial filtered run skipped 525 cases and lint initially included
  an ignored CSS file; both commands were corrected and the full selected suites rerun cleanly.
- Existing evidence records Wave 3 responsive widths 1440/1024/390 and all six themes, and
  Schedule responsive/six-theme captures are checked in under `docs/design/schedule-ux/evidence/`.
  An attempted read-only browser inspection could not attach because the in-app browser reported
  its user handle unavailable; no new live visual, zoom, device, screen-reader, or operator UAT
  evidence is claimed. No FULL, push, PR, main merge, feature-finish, Review reassignment, or
  resource cleanup was performed. Additional short visual/UAT review remains appropriate before
  operator acceptance.

## 2026-10-30 — Wave 3 final UAT corrections: Suppliers and Sowings

- Confirmed clean original feature and independent-QA worktrees, then fast-forwarded only
  `feat/ui-system-v1-wave3` to the approved QA checkpoint `d09fd86118ecc9a17a9aef27e099d8a182ae073d`.
  The QA branch remains unchanged. Suppliers and Orders shared a confirmed compact-row regression:
  title links sat apart from preview triggers, thumbnails were oversized, and flexible fact columns
  widened rows. Both now use a shared-trigger composition, bounded metadata and direct Details/Edit.
  Active Suppliers use the existing compact accessible status indicator. No shared primitive changed.
- Independently inspected Sowings List and Gallery; found no missing propagation. Toolbar, internal
  scrolling, persistent nonmodal preview, explicit Details/Edit, lifecycle, selection, pagination,
  germination and lineage behavior remain in place; no Sowings source changes were made.
- Focused regression: **145/145** in 7 test files (Suppliers 13, Orders 20, Sowings 34, Seeds 56,
  DirectoryPage 16, DirectoryResults 5, DirectoryTools 1). Strict TypeScript, affected-file ESLint,
  Prettier, `python3 scripts/check-features.py` (123 valid), and `git diff --check` pass.
- Refreshed only the owner-bound Feature Review using `make feature-review-up`; status reports healthy
  frontend/backend/database, expected source worktree, code/DB head `20261013_0042`, and fixture v4
  ready (80 records). Live visual comparison captured inline at 1320x900 in Mineral Dark and Light:
  Suppliers List, Orders List/Gallery, Sowings List/Gallery. Preview opened a side inspector; direct
  Supplier Details navigated to its record route. Theme restored to Dark, Mineral.
- The connected browser offers no viewport override; exact 1440/1024/390 CSS-pixel captures were not
  possible for this correction. Screen reader, physical device and actual browser zoom remain UAT.
  Operator checklist: compare Supplier/Order List rows with Seeds; click titles/rows for Preview;
  verify Details/Edit bypass preview; switch Orders and Sowings List/Gallery; scroll with Preview open;
  verify pagination and multi-select; verify Sowings lifecycle and germination semantics; repeat at
  1440/1024/390 and supported themes on operator's responsive test setup. No FULL, push, PR, merge or
  feature-finish was run. Acceptance remains pending.

### 2026-10-30 — Directory annotation follow-up

- Removed redundant eye Preview controls from directory action groups while preserving
  record-surface Quick Preview and direct Details/Edit. Kept domain operations visible
  in their place: Start sowing for eligible SeedLots and Create Plant/Germination for
  eligible Sowings, without duplicating operations already shown in the open inspector.
- Added idle inspector guidance for Suppliers, Orders and Harvests; adjusted desktop
  inspector alignment below pagination and the Stored Material/Harvest workspace height
  so the results area can scroll instead of clipping lower content. Supplier status now
  uses a text label. Botanical Identity Quick Preview retains its common name in the
  accessible name.
- Focused Collection regression: **180/180** across 7 files. Expanded integration
  regression: **316/316** across 10 files, including App, UI Lab and Propagation. The
  complete frontend suite then passed **1095/1095** across **100** files. Strict
  TypeScript, full frontend ESLint, changed-file Prettier, 123-feature validation and
  `git diff --check` pass.
- No live browser comparison, updated visual evidence, Review refresh, FULL, commit,
  push, PR or merge was performed. Operator visual review remains necessary for row
  action balance, inspector sizing and the annotated Stored Material viewport; device,
  zoom and assistive-technology verification remain open.

### 2026-10-30 — Directory annotation corrections

- Restored SeedLot Start sowing on selected and unselected active rows as a stylized,
  labelled icon action. Sowings Create Plant and Germination use the same icon-only
  treatment and remain directly operable alongside Details/Edit.
- Put Seeds, Sowings and Harvests pagination in a full-width directory grid row above
  both the results and inspector. Added an idle Harvest inspector, kept preview aligned
  with the first row, and corrected Stored Material toolbar sizing and stable filter-chip
  space. Botanical Identity now pages consistently, aligns its Quick Preview with the
  list and provides contextual row actions for Add seed lot, Add plant, Start sowing and
  Record harvest.
- Fixed selected-filter chip dimensions to prevent clipped borders. The first targeted
  run found tests querying identity cards by a partial species name also matched the new
  contextual action names; updated those selectors to target Quick Preview explicitly.
- Regression passed: **389/389** tests across 13 files, including App, UX-001/004,
  Seeds, Sowings, Plants, Harvests, Stored Material, Botanical Identity actions, shared
  DirectoryPage, Suppliers, Orders and UI Lab. The formerly failing App/UX-004 pair now
  passes **130/130**. Affected-file ESLint, TypeScript, changed-source Prettier,
  123-feature validation and `git diff --check` pass.
- The existing Review tab was read only; it still shows the pre-refresh Harvest screen.
  No Review refresh, responsive screenshot set, FULL, commit, push, PR or merge was
  performed. Live visual confirmation of these corrections at 1440/1024/390 and across
  themes remains outstanding; operator acceptance is pending.

### 2026-10-31 — UI System v1 same-family consolidation candidate

- Preserved feature HEAD `4b8c038f2373c37c5645125b22c06f019698b66b`, Batch 1 and the clean
  independent-QA checkpoint `d09fd86118ecc9a17a9aef27e099d8a182ae073d` (already an ancestor).
  Local and remotely checked main remain `fbce3c4cfad26bdfa3297d53a1e65a7ec6a0ad65`.
- Documented four page families and moved eight record directories onto shared
  `DirectoryWorkspace`, typed `DirectoryRecordContent` slots, status/actions and nonmodal
  inspector geometry. Shared pagination replaces four local copies; Orders retains server
  pagination. Removed parallel Sourcing/Sowings directory styles and obsolete geometry rules.
  Domain/API/save/filter ownership, exact inventory routes, quantities and safety guards remain
  with their existing pages. Locations/Geography share recursive presentation; Location selection
  now retains the tree at tablet/mobile widths, with explicit Details navigation.
- Corrected one real creation-focus regression; changed other test expectations only for the
  documented compact states, idle inspectors, exact Details links and retired layout classes.
  Complete frontend regression passed **1097/1097 in 100 files**. Later peer-tool changes passed
  **171/171**, identity styling passed **145/145**. Final mobile comparison found Stored preview
  content could collapse to zero height; shared minimum sizing/narrow-page flow and scrollable
  metadata fix this. Stored Active now uses the same accessible check, retaining Depleted text.
  Final affected cross-consumer regression passed **397/397 in 13 files**; strict TypeScript,
  full frontend ESLint, Prettier and production build pass. Feature validation: **123 valid**;
  `git diff --check` passes. Full results and limits: `design/ui-system-v1/consolidation/verification.txt`.
- Captured **95 unique states**, including eight directories in six themes at 1440px, all eight
  at 1024/390 in Mineral Dark, five galleries at three widths, two hierarchies at three widths,
  photos, long names, rich lifecycle, pagination/All/selection, inspector persistence and 720×450
  stress. Measurements report no horizontal overflow; all 79 list/inspector bounds checks report
  no overlap. Comparison sheets, checksummed manifest and dirty-source fingerprint accompany
  the gallery in `design/ui-system-v1/consolidation/evidence/`.
- Browser smoke verifies Preview/Escape/focus return and direct Details for eight directories;
  exact inventory destination and scroll persistence remain intact. Harvest confirmation focuses
  Cancel; Escape returns to More actions without deletion. Unsaved Seed label was not persisted.
  Native dirty-confirm rejection was not controllable through this browser and remains manual
  UAT alongside physical devices, screen readers, actual zoom and full theme/width/state coverage.
- Existing Review remains healthy and owned by `548f`, code/DB `20261013_0042`, fixture v4 ready
  (80 managed baseline records), extended fixture retained; live source binds include these dirty
  changes. No credentials recorded. No environment reprovisioning, foreign-worktree changes or
  resource cleanup. Verification-impact planning selects FULL; it was deliberately not run.
  Candidate awaits operator UAT and independent final review. No delivery commit, push, PR,
  main merge or feature-finish.

### 2026-11-01 — Shared directory interaction cleanup (operator review pending)

- Followed checkpoint `db1e71fb85f1396408ed6f07800d4992dea0233d` with textual lifecycle
  chips and one More actions menu per record across eight consolidated directories. Existing
  Details/Edit, domain actions, exact inventory destinations and guards retain their owners.
  Selected fill loses the inset stripe; hover, keyboard focus and bordered triggers stay distinct.
- Reused OverflowMenu with opt-in mounted domain content. Fixed portal click propagation into
  row Preview and nested Escape closing both association dialog and menu. A new regression
  proves dialog Escape returns to its command, then menu Escape returns to More actions.
  Existing tests now exercise the menu path and textual states. Hierarchies and specialists
  are unchanged.
- Final checks: **412/412 tests in 16 suites**, strict TypeScript, full frontend ESLint and
  Prettier, production build, **123 valid features**, and `git diff --check` pass. Existing
  JSDOM native confirm() warning remains; guard assertions pass. No canonical FULL was run.
- Browser smoke verifies Preview/Escape/focus and Details across eight directories, Edit for
  seven existing editor owners, exact Stored inventory URL, association dialog focus, and fill
  without a stripe. At 1024/390, three representative stacked inspectors retain 147px of
  scrollable content with no horizontal document overflow. Review is healthy and owned by this
  worktree; code/DB `20261013_0042`, fixture v4 ready. No record was saved or deleted.
- Results, screenshots, source fingerprint and exact file list:
  `design/ui-system-v1/consolidation/interaction-cleanup/`. Focused Mineral Dark checks do not
  replace the historical six-theme audit. Physical devices, screen readers, actual zoom and
  native dirty-confirm rejection remain manual UAT. Final operator UAT remains pending.
  No commit, push, PR, merge, feature-finish or resource cleanup.

### 2026-11-01 — Final directory interaction contract correction (operator UAT pending)

- Implemented the explicitly confirmed replacement of the earlier cleanup contract: direct
  bordered Details/Edit, eligible creation-only overflow, textual semantic lifecycle chips,
  and removal of Quick Preview/idle inspector columns from eight directories and both
  hierarchy explorers. Full record Overview/tabs and domain workflow owners remain intact.
- Fixed the actual appended-Details defect with exclusive directory/detail rendering in
  Seeds/Sowings/Plants and Geography Places. Direct Sowings/Plants Edit now initializes its
  record without Preview. Identity Edit reopens on browser history; duplicate selection and
  connected focus targets remain available. Exact Stored inventory Edit enters its existing
  guarded correction dialog. Shared hierarchy tracks align direct actions and wrap status/name;
  compact gallery placeholders no longer show a clipped source banner over their icon.
  Geography dedicated records now distinguish loading, retryable error and missing records.
- Focused regression: **441/441 in 17 suites** on the final candidate, including RecordVisual
  and the new Geography loading/error/retry/missing-record regression. The owning domain/App
  suites include the original Batch 1 safeguards; earlier 69-case evidence is preserved.
  Strict TypeScript, whole frontend ESLint, affected Prettier, production build, **123 valid
  features** and `git diff --check` pass. One interrupted repeat produced no result and is
  excluded from passing evidence. No canonical FULL was run.
- Live Review verifies dedicated navigation, correct editors, source-prefilled creation,
  exact inventory destinations, Escape/focus and bulk-mode selection without row navigation.
  Evidence covers eight directories at 1024/390, five desktop galleries, desktop records,
  both hierarchies at 1440/1024/390 and all six themes for status presentation. Semantic
  status text/surface contrast is **5.90:1–9.08:1**. No Preview nodes or document horizontal
  overflow were observed in the recorded directory/hierarchy states.
- Current contract, matrix, exact file list, source fingerprint, 50 captures and UAT checklist:
  `design/ui-system-v1/consolidation/final-interaction-correction/`. Prior Preview galleries
  are explicitly historical. Physical devices, screen readers, actual zoom and native dirty-
  confirm rejection remain operator checks; this is representative browser coverage.
- Existing Review remains owned by `548f` at `http://localhost:15174`, code/DB
  `20261013_0042`, fixture v4 ready with 80 managed baseline records; extended synthetic
  records retained. No record was saved/deleted during live smoke. No foreign worktree,
  DEV/UAT/Review provisioning, Docker cleanup, commit, push, PR, merge or feature-finish.
  Checkpoint `db1e71f`, Batch 1 `3669869` and QA/Schedule ancestry remain preserved.

### 2026-11-01 — Details and hierarchy consolidation, Part A (UAT pending)

- Preserved the completed interaction correction in checkpoint `107f719273085ec7c2c51a3bb5ed720e31a245ba`.
  Reconciled TX-001 `4ca5fe0ae85da0f48e3f4df4f370f98c3747a311` through normal merge
  `31ef765f19d414a00a350167f08b3887898f7195`; both progress histories retained.
  Scoped TX-001 infrastructure baseline: 13 passed with `--no-cov`; the initial scoped
  default-coverage invocation passed its tests but failed the whole-application threshold.
- Shared HierarchyRow now contains record and trailing Details/Edit in one bordered surface;
  chevrons remain siblings. Locations and Geography reuse the same grid, wrapping and connectors.
  Shared DetailPage extends existing CollectionUI/DetailHeader, Breadcrumbs and DetailTabs;
  Locations, identities, places, Suppliers and Orders retain domain-owned sections and guards.
  Identity formatted heading, focus target and actions remain stable across tabs. Place Details
  no longer repeat the directory search/header. Canonical places still have no Edit.
- Focused Part A regressions: 170/170 in six suites (App, UX004, Suppliers, Orders,
  CollectionUI, HierarchyRow). Two initial UX004 findings were corrected: restored the named
  identity detail region and replaced the superseded split-header assertion with stable-header
  behavior coverage. Strict TypeScript, full frontend ESLint, production build, feature graph
  (123) and diff checks pass. No FULL. Expanded browser/evidence checks continue with Part B.
- Reproduced the reported Harvests blank page: Vite served an empty transformed StoredMaterial
  module while the source export existed. Invalidating that module restored directory and Details
  without source changes or environment restart. Production build includes both exports.
- Review remains owner 548f; no foreign resources changed. No protected delivery; final UAT pending.

### 2026-11-01 — Botanical cover fallback and final Details evidence, Part B (UAT pending)

- Part A checkpoint `83e1c3bad6c4977bdf2a82f2fb3cc2b000f93add` remains standalone.
  Collection fallback now follows own designated photo → exact eligible botanical cover → placeholder.
  Removed the own-photo-only Details gates in Seeds/Plants/groups, added the Sowings Details visual,
  and fixed summary enrichment based on cover metadata rather than the presence of a scientific name.
  Harvest/Stored no longer substitute a physical source-record photo. Activity's explicit source-photo
  compatibility is retained. No per-row request, API/schema change, media write or primary change.
- Final affected run: **458/458 tests in 20 suites**, strict TypeScript, whole frontend ESLint,
  affected Prettier, production build, **123 valid features**, and diff checks pass. Original Batch 1
  safety coverage is included; historical 69-case evidence remains intact. No canonical FULL.
  The earlier 449-case run passed tests but typing exposed the retained Activity caller; its optional
  contract was restored and a regression added before the final run. Obsolete UX001/UX004 split-header
  assertions were updated to the intentionally shared header; deferred reads and named regions remain.
- Browser evidence: five Details families at 1440/1024/390 (15 layout checks), five families in all six
  themes (30), both hierarchies at all three widths (6), and five 320px narrow-stress checks. Keyboard
  expansion keeps its route; actions remain inside row boundaries. Location Edit/Escape restores focus.
  Captures include long paths/cultivar, partial-date/unknown-price Order, missing images, own protected
  photo, Gallery alignment, restored Harvests loading and exact Stored inventory navigation.
- Current Review directory has 37/37 identities explicitly showing No cover image. Positive inherited
  cover, external suppression, image-error and later-own-photo transitions are automated evidence only;
  no Media/identity association was created for a screenshot. These cases, physical devices, screen
  readers and actual browser zoom remain operator UAT. 320px stress is not browser zoom.
- Review owner/source 548f, frontend/backend/db healthy, code/DB `20261013_0042`, fixture v4 ready with
  80 managed baseline records and extended data retained. Reported Harvests blank page was an empty
  Vite transformed module; invalidation restored access, including fresh reload/Details/Stored checks.
  No record saved/deleted, foreign worktree/environment touched, push, PR, protected merge, FULL or cleanup.
- Current compliance matrix, source fingerprint, exact file list, verification and visual gallery:
  `design/ui-system-v1/consolidation/details-cover/`. Final operator UAT remains pending.

### UI-FLICKER-001 C1/C3 stable headings — 1 November 2026

- Directory pages declare `page-header--directory` from first render (Seeds, Sowings, Plants, Harvests,
  Stored material, Suppliers, Orders, Botanical identities, Locations). Shared `DetailLoading` covers
  Harvest, Supplier, Order, Location, Sowing, Plant, identity and direct Seed/Sowing/Plant loading.
  The directory breadcrumb gap is fixed, removing the proven 8px movement; Suppliers, Orders, identities
  and Locations settle 8px higher than before and Locations now uses the shared directory heading size.
- Checks: 1125/1125 frontend tests in 101 files, strict TypeScript, ESLint and Prettier on changed files,
  production build. Live delayed-network comparison against the checkpoint at 1440; patched build also
  at 1024/390. Direct URL, record switching, and Back/Forward on Suppliers only. Sowings was re-traced
  on the integrated Review (22px y63, stable). No canonical FULL, push, PR or merge.
- Unresolved: 390 px shell movement of 4-12px, legacy Seeds/Sowings/Plants Details position after direct
  loading, brief first-render gap on Supplier Details, operator UAT. UI-DETAIL-001 remains open.

### UI System v1 Gate B canonical Details — 1 November 2026

- Seeds, Sowings, Plants/PlantGroups, Harvests, Locations, identities, Suppliers, Orders and Geography
  Places use one `DetailPage` contract: 32px title, 22px below 48rem, shared breadcrumb gap and flat
  shell. `DetailSummary` replaces the Details metric patterns and omits absent values while keeping zero.
- Mobile gutter no longer depends on loaded records. Nested workspaces no longer add a margin, so Plants,
  Suppliers and Orders directories settle with Seeds. `DetailLoading` now matches the final title.
- Checks: all 101 frontend test files, strict TypeScript, ESLint and Prettier on changed files, production
  build, `check-features.py` and diff check. Geometry at 1440/1024/390 and gutter at 600/768/769 in one
  browser. Real click Back/Forward on Orders; 500 responses reach real error states on Supplier, Harvest, Order.
- Unresolved: UI-DETAIL-001 awaits operator acceptance; UI-FLICKER-001 stays partially resolved. See
  `design/ui-system-v1/consolidation/details-cover/README.md`. No FULL, push, PR, merge or origin/main.

### UI System v1 Wave 3 closure disposition — 1 November 2026

- Operator reports the six Gate B UAT checks complete. UI-DETAIL-001 closed for Wave 3 with classified
  exceptions; UI-FLICKER-001 stays partially resolved with three P3 observations. No application code changed.
- `origin/main` is `4ca5fe0` (TX-001, #133) and already an ancestor through `31ef765`; no new merge was needed.
- Migration head is `20261013_0042` on both. QA and canonical verification evidence follow this entry.
- Independent QA in an isolated clone: PASS WITH FINDINGS, no P0/P1. Three P2 defects (blank unknown Seed id,
  Plant Forward keeping the directory, focus on `body` after Details/Back) and P3s are deferred in the Details
  closure matrix. Operator rule: only P0/P1 are corrected before closure.

### AGENT-WORKFLOW-001 provider-neutral multi-agent workflow — 2 November 2026

- `AGENTS.md` is the one contract. Vendor documentation shows native reading by Claude Code (2.1.309 installed
  under the desktop app), Codex and OpenCode, so no `CLAUDE.md` or OpenCode configuration was added.
- Added `scripts/feature_worktree.py` and `make feature-worktree/attach/context/claim/handoff/retire`,
  plus `FileLock` in `workflow_resources.py` for Review/Sourcing/UAT lifecycle, canonical FULL and per-worktree gates.
  Verify and Review gate on the writer; deliver and finish refuse agent identities and pending handoffs.
- Independent read-only QA: 1 P1, 2 P2, 8 P3, no P0; all fixed with regressions, not re-reviewed by a second QA pass.
- Focused checks with `AGENT_ID` set: test-agent-workflow 30, test-feature-workflow 46, test-environment-workflow 35,
  test-verification-impact 24, test-workflow-resources 14, test-preview-workflow 19, test-uat-preview 19 + 15,
  test-workflow-helpers, workflow-check. Real smoke on this repository: claim and refusal, Review ownership refusal
  against the protected owner, create/attach/collision, refused retire of `548f`. Final gate: canonical FULL, by receipt.
- Second independent QA (Codex): FAIL, P1 Review Compose denylist omitted `cp` and `watch`. Corrected with a fail-closed
  allowlist across Review, Sourcing, DEV, Quality and production routes; pending re-review, then a new canonical FULL.
- Third independent QA: FAIL, P1 production `down -v`, P2 `cp -L`. Corrected with parser-accurate flag matching on all
  roles, also refusing `up -V` and `cp -` tar streams; pending re-review, then a new canonical FULL.
- Not exercised: real Claude Code, Codex or OpenCode sessions (provider identities are simulated) and real delivery.
- See [handoff](agent-workflow-001-handoff.md) for design and tradeoffs. Status stays `implemented`;
  no push, PR, merge, finish, old clone/worktree removal or Docker/Git prune.

### UI-POLISH-001 — focused Wave 3 review candidate, 2 November 2026

- Validated clean `feat/ui-polish-001` at cached main `9ac7b6c` in the operator-selected worktree;
  confirmed writer `codex-ui-polish-001` through feature-context/claim. No takeover or branch change.
- Checked the historical three P2 findings against source and reproduced missing-Seed, Plant Forward
  and Seed focus failures. Seeds now show an explicit unavailable state; Plant/Group Forward reopens
  retained Details while preserving creation/extraction success feedback. Six record owners share
  bounded title/browser-Back focus restoration with row, list and existing Search fallbacks. Plant
  and Sowing heading refs target the record title. Existing editors retain focus ownership.
- Baseline Seed/Plant suites: **120/120**. Final focused run: **396/396 in 13 suites** (six owning
  screens, focus hook, CollectionUI, DirectoryPage, recordNavigation, App, App.transition, App.lazy).
  `pnpm typecheck`, `pnpm lint`, `pnpm format:check`, `pnpm build`, feature graph **125**, and diff
  whitespace checks pass. Independent read-only review found the empty-directory fallback hole;
  it was fixed with a zero-row regression and re-reviewed without unresolved correctness findings.
- [Audit, exact checks, decision options and limits](ui-polish-001-review.md). C5 contextual-action
  placement and repeated metrics remain separate design decisions; the operator removed the mistaken
  C6 reference. Stored material's lack of an independent Details route remains an accepted exception.
  Broader QA-3, historical P3s and live responsive/theme/zoom/assistive/device review are not closed.
- Status `implemented`; implementation committed as `22ab055` after explicit operator authorization.
  Independently reviewed, with canonical verification still pending. No canonical FULL/receipt, push, PR,
  merge, delivery, finish or shared DEV/Review/UAT operation. Only this worktree's Quality resources
  were used; TEST-DATA-001 and its fixture infrastructure were not changed.


### UI-POLISH-001 — final independent-QA corrections, 2 November 2026

- Implementation `22ab055` / tree `f994e66f04772ee630c70dc8320577c9715ffc79` is committed.
  Operator-supplied Claude QA returned CONDITIONAL PASS: 396/396 documented tests, 10/10
  adversarial probes and 6/6 mutation checks detecting regressions; no confirmed functional blocker.
  Corrected historical staged/uncommitted wording. Status stays `implemented`: independently
  reviewed does not mean canonically verified, delivered or merged.
- B1/N3/N4 correction changes only tests and documentation: Forward feedback assertions for Plant
  creation, Group creation and extraction; unavailable Seed title focus; Supplier real-history
  Back/Forward and owner-level empty-directory Search fallback. No production change was needed.
- Checks: targeted **7/7**; affected **398/398 in 13 suites**; `pnpm typecheck`, `pnpm lint`,
  `pnpm format:check`, `pnpm build`, feature graph **125** and diff whitespace checks passed.
  [Audit and exact evidence](ui-polish-001-review.md#independent-claude-qa-and-final-corrections--2-november-2026).
- N1/N2/N5/N6 remain nonblocking and deferred. C5, repeated metrics, broader QA-3/P3 and live
  visual acceptance remain outside this correction. Stored Material's accepted behavior is preserved.
  No canonical FULL, push, PR, merge, feature-finish, shared environment or TEST-DATA-001 changes.

### TEST-DATA-001 golden dataset vertical slice — 2 November 2026

- Added a manifest-driven SMOKE golden dataset (`scripts/golden_plan.py`, `scripts/golden_dataset.py`,
  `scripts/fixtures/golden/`) generating through owning services into isolated `golden_*` databases and
  media roots. `review_dataset_v5.apply_node` was extracted for reuse without behavior change. Design and
  operator decisions: [design](test-data-001-design.md); coverage: `scripts/fixtures/golden/COVERAGE.md`.
- Evidence: identical canonical digest across hash seeds, timezones and two separate disposable stacks;
  idempotent repeat; atomic failure with retry; post-commit failure never ready; damage detected only in the
  damaged copy; persistent targets refused; zero residual resources after each run.
- Checks: `test_golden_dataset.py` and `test_review_dataset_v5.py` integration, `make workflow-check`,
  `test-uat-preview`, `test-verification-impact`, `test-environment-workflow`, `check-features`.
- Unresolved: COMPREHENSIVE and STRESS, ten planned scenarios, Review/UAT/performance adoption (needs operator
  lifecycle review), independent QA. Status `in_progress`. No canonical FULL, push, PR or merge.

### TEST-DATA-001 independent QA corrections — 2 November 2026

- Added one exclusive, non-blocking per-copy lifecycle lock under `/tmp/florabase-golden/.locks`, covering create,
  generate, validate, verify-baseline, digest and retire; a loser exits 75 and changes nothing.
- Added `verify-baseline`, comparing a copy with a reviewed digest pinned in the manifest, separate from domain
  validation. `digest` is now a diagnostic that also works on damaged copies.
- Narrowed digest normalization after a column-by-column comparison of two copies: free text that looks like a
  timestamp, canonical geography, the provider cache, media bytes and scenario keys are now content.
- The coverage matrix now separates runnable from planned profiles; only SMOKE is executable.
- Removed the `--copy` re-exec (about 1.1 s per CLI call) and parallelized losing contenders and teardown.
- Checks: `make golden-dataset-check` (25 passed, 260 s; 172 s and 17 tests before),
  `test_review_dataset_v5.py`, `make workflow-check`, `scripts/check-features.py`, `test-uat-preview`,
  `test-verification-impact`, `test-environment-workflow`, backend `mypy` and ruff on the test module.
- Not run: canonical FULL, the complete integration and unit suites, frontend checks, `smoke-uat-preview`.
- Unresolved: every migration needs a reviewed manifest pin update; the digest has been observed on one calendar
  date only; the application import still costs about 1.8 s per CLI process.

### TEST-DATA-001 timestamp baseline correction — 2 November 2026

- Fixed a false `baseline-verified`: every timestamp was reduced to present or absent, so moving
  `external_taxon_links.last_refreshed_at` by 30 days changed stale/fresh behaviour but not the digest.
- Generation now runs on a plan-derived clock (anchor date 12:00 UTC plus one second per node), and the digest
  retains every timestamp. Only `app_metadata.created_at` and the empty session tables stay outside it.
- Reviewed SMOKE baseline is now `70a1b1ae037cdfce7fa494096bbb557e266cfe7df5780183acda2c7d8dbef967`.
- Added timestamp negatives through the CLI, an exhaustive per-column digest check, and `verify-baseline` to the
  lock contention tests.
- Checks: `test_golden_dataset.py` (29) and `test_review_dataset_v5.py` (3) in fresh disposable stacks,
  `make workflow-check`, `test-uat-preview`, `test-verification-impact`, `test-environment-workflow`,
  `scripts/check-features.py`, backend `mypy`, ruff on the test module.
- Not run: canonical FULL, the complete integration and unit suites, frontend checks, `smoke-uat-preview`.
- Unresolved: anchored timestamps read as stale on the real clock; the module takes about 5 minutes.

### BETA-IMAGE-001 — image pipeline candidate for independent QA, 3 November 2026

- Claimed authoritative `feat/beta-image-001` from main `f637539` as `codex-beta-image-001`.
  Added paired production image hardening, pinned compiler/base/build/security inputs, hash-enforced
  unchanged production dependencies, coherent beta versions/OCI traceability, embedded healthchecks,
  minimal non-root runtimes, frontend release metadata/Docker DNS and licenses/notices.
- Added protected manual-main GHCR workflow with exact source/tag/check/environment approval,
  provenance/SBOM, immutable candidate digests, security and artifact-only smoke before version
  promotion, manifest schema, source/attestation retention and new-prerelease-only publication.
  Existing delivery protections and TEST-DATA-002 are untouched; no persistent deployment mechanism.
- Focused checks: workflow-check (Ruff/format/strict mypy), 9 release-contract tests, actionlint 1.7.12,
  both API generators/api-check, production builds, complete native amd64 image-only smoke,
  132-feature graph and whitespace pass. Smoke verified migrations, auth/CSRF/cookies, private original
  media and application recreation; exact owned resources/images retired with zero residual state.
- Initial make check: backend 985 passed/2 skipped (90.06%); frontend 1144 passed/1 Sowing URL assertion
  failed. That single test and all 35 Sowing tests pass on focused repeats; broad run is not a PASS.
- **Publication blocked:** intended-host evidence/operator selection is absent; final raw security scans
  report backend 11 CRITICAL/66 HIGH, frontend 3/61 and PostgreSQL 2/26, with zero secret findings.
  Gates remain fail-closed, without suppression. Registry publication/pulls, hosted protection checks,
  independent QA and canonical FULL are unexecuted. Status stays `in_progress`; this is not beta admission.
- [Implementation/runbook](beta-image-001.md), [QA checks/blockers](beta-image-001-qa.md),
  [local evidence/report hashes](beta-image-001-local-evidence.json). No push, PR, merge or feature-finish.
### TEST-DATA-002 comprehensive golden dataset — 2 November 2026

- COMPREHENSIVE is executable: 3,183 plan nodes, 3,973 domain records, 34 media files, generated through owning
  services with 18 exercised refusals and 140 invariants. SMOKE's plan pin and baseline `70a1b1ae…f967` are unchanged.
  Design, coverage gaps and CI proposal: [design](test-data-002-design.md).
- Digest addition: link `version` UUIDs get ordinals.
- Domain observations, unchanged and for review: the owning service accepts a new record at a retired Location,
  and a movement Event on a dead Plant.
- Checks: `make golden-dataset-comprehensive-check` in two separate stacks (22 passed each; a third produced the pin),
  `make golden-dataset-check` (31 passed), `test_review_dataset_v5.py` (3 passed), `make workflow-check`,
  `check-features`, `test-verification-impact`, `test-uat-preview`, `test-environment-workflow`, ruff and mypy on
  the plan, runtime and test modules. Zero residual resources after each stack.
- Not run: canonical `make feature-verify`, the complete integration and unit suites, frontend checks.
- Unresolved: independent QA; `import-export-roundtrip`; update-service edit paths; real image cost; approval of any
  CI schedule; Review and UAT adoption. Status `implemented`. No push, PR or merge.

### TEST-DATA-002 fingerprint integrity correction — 2 November 2026

- Independent QA failed `ba4deac` (P1): the digest replaced the stored completion hash of movement completions with a
  constant, so a corrupted value still verified, though `Schedule.complete` uses it to tell a retry from a conflict.
- Every stored hash, in both profiles, is now proven against the request rebuilt from the plan and the copy's ids. Only a
  proven value whose request holds a per-copy id is replaced, by that canonical request. Anything else stays raw and is a
  domain problem, so the digest changes and `verify-baseline` refuses. No Schedule service changed.
- Reviewed baseline moved from `d2db9e9b…98c7` to `cf423707…3a11`. Against the old pin, only `scheduled_activities` and the
  combined digest changed; plan, counts, projections, media and scenario keys did not. SMOKE's pin is byte-identical.
- P2: published totals corrected to 287 canonical + 7 custom = 294 geographic rows; 3,982 and 4,269 modeled rows.
- Checks: `make golden-dataset-comprehensive-check` in two stacks separate from the pin's (29 passed each),
  `make golden-dataset-check` (32 passed), `test_review_dataset_v5.py` (3 passed), `make workflow-check`, `check-features`,
  ruff and mypy on the plan and runtime, ruff on the test modules.
- Not run: canonical `make feature-verify`, the complete integration and unit suites, frontend checks. Delta QA pending.

### BETA-IMAGE-001 — independent QA corrections, 3 November 2026

- D1 fixes disappearing-container cleanup with fresh inventory proof and exact-label missing-source recovery. 17 resource regressions pass; real race/repeat and supported recovery CLI (forged-source refusal) pass with zero owned residuals.
- D2 requires exact signer workflow, main source ref, authorized commit and hosted runners; checksum-verified gh 2.103.3 supports the required flags; 2.46.0 does not. D3 enforces the published JSON schema plus cross-field checks, with pinned host-only tooling and 11 passing release tests.
- Reviewed Pillow/certifi batch: 13.0.0/2026.10.18, unchanged verification policy, application setuid/setgid removed. Compatibility 102/102 tests; batch-A artifact smoke passes, scans remain blocked at backend 5 CRITICAL/43 HIGH, frontend 3/61, PostgreSQL 2/26, zero secrets. Original 11/66 backend evidence preserved. Advisory-specific VEX is a conditional unapproved draft only.
- D4 locally merged origin/main 1e44c3f without rewriting; progress entries from both branches retained. Main contributes TEST-DATA-002 fixtures/planner/tests, not runtime app/Docker/release changes. No foreign environment changed.
- New maintained Python/nginx base digest batch builds, but PostgreSQL registry inspection hits Docker Hub HTTP 429 unauthenticated pull limit before runtime smoke/scanning. Current-pin runtime/security verdict is unknown; previous-batch scan counts do not certify it. All exact owned resources retired.
- DS224+ Linux/amd64 selected by operator; measured runtime/capacity acceptance pending. Compose portability to PCs/VPSs retained; no Dockhand dependency added. No canonical FULL, push, PR, remote merge, publication or persistent deployment. [Delta handoff](beta-image-001-qa-corrections.md) records tests, original/new report hashes and blockers.

### BETA-IMAGE-001 — final reliability correction, 3 November 2026

- Full container IDs and conservative legacy-prefix existence checks prevent false cleanup success on inspect failure; realistic regression detects the old defect. Release Compose process groups quiesce before cleanup, with bounded timeout/refusal/recovery. Real timed SIGTERM plus late owned creation removes 2 containers/network/media, verifies zero residuals and unchanged foreign inventory. Resource suites 19/19.
- Project-managed no-ensurepip venv, verified pip bootstrap and hash-locked transitive tools replace system pip/PYTHONPATH requirements. make test-beta-images 12/12 passes, including fresh offline cache use; absent offline cache refuses. make workflow-check and actionlint pass. D3 rejects equal index/platform digests and untrusted build inputs.
- Official smoke passes on current pins without pull shim; scans measure backend 2 CRITICAL/36 HIGH, frontend 1/4, PostgreSQL 2/26, zero secrets. Raw reports, exact index/native/config identities, advisory-by-package inventory and unapproved expiring VEX drafts preserved. Security gate remains blocking. Patched Python/media compatibility 102/102.
- [Final reliability handoff](beta-image-001-final-reliability.md). DS224+ amd64 runtime/capacity and publication approvals remain pending; no canonical FULL before delta QA, push, PR, merge, GHCR publication, deployment or feature-finish.

### BETA-SECURITY-001 — candidate for independent QA, 3 November 2026

- Claimed authoritative feat/beta-security-001 at f0d2422 as codex-beta-security-001. Evaluated trixie,
  selected digest-pinned Python 3.14 Alpine and stable unprivileged nginx Alpine slim; preserved Debian
  DEV and every PostgreSQL identity field. No application dependency or PostgreSQL major changed.
- Exact final runtime scans: backend **0 CRITICAL / 0 HIGH**, frontend **0/0**, PostgreSQL unchanged
  **2/26**, zero secrets. Full original/new reports, base trials, advisory/package/fix inventories,
  hash-checked native/index/config identities and 26 unapproved expiring gosu VEX drafts are retained.
  Optional libpq OAuth actually links flagged curl/Brotli; no waiver proposed for those libraries.
- Hardened private executable cache/isolated imports, canonical CI producer and exact protected source
  checks, complete unsuppressed scan inventories, application descriptor comparisons, read-only/cap-drop
  artifact smoke, individual image attestations, publication checkpoints and draft asset digest checks.
  Public manifest v1 unchanged; BETA-RUNTIME-001 Compose/storage/controller/backups untouched.
- Focused: baseline release tests 12/12; updated 21/21; workflow-check Ruff/format/strict mypy; actionlint
  1.7.12; resource regressions 19/19; official artifact-only smoke and 103 exact musl runtime media/
  provider/cache/SQLite tests; fresh online scans and expected PostgreSQL gate refusal; offline tool tests, api-check, 35 environment
  regressions and real Compose SIGTERM/late-create/repeated-cleanup/foreign-inventory proof.
  All disposable owned resources/images retired; shared upstream/build cache retained.
- Supplied DS224+ Engine 24.0.2 / Compose 2.20.1 and capacity measurements recorded without fabricated
  screening/runtime/security acceptance. PostgreSQL maintenance or individually accepted/reviewed VEX,
  explicit host approval, protected environment/package configuration and publication authorization remain.
- No canonical FULL before independent QA authorization, no delivery receipt, push, PR, merge, registry
  publication or deployment. [Runbook/QA handoff](beta-security-001.md),
  [retained evidence](security/beta-security-001/README.md). Feature remains in_progress.

### BETA-SECURITY-001 — draft lookup P1 correction, 3 November 2026

- Independent Claude QA conditionally passed 34cebbe / tree 8653d1a4; P1 published-tag lookup could
  not discover the unpublished draft. Replaced it with authenticated paginated listing, unique draft
  selection, numeric-ID re-fetch, source/tag/ID/URL/state and asset checks, then numeric-ID PATCH.
- Local asset checks now precede version-tag promotion; draft upload/validation still follows security,
  smoke and attestations. Permissions unchanged. No PostgreSQL digest/VEX/runtime contract change.
- Baseline 21/21; old implementation fails two new regressions, and actual old snippet reproduces
  tag-404 against mocked GitHub behavior. Corrected suite 25/25; workflow-check and actionlint pass.
- PostgreSQL 2 CRITICAL/26 HIGH still blocks publication. Separate maintenance proposal requires
  explicit operator approval and BETA-RUNTIME-001 coordination. [Delta QA handoff](beta-security-001-lookup-correction.md).
  No canonical FULL, push, PR, merge or publication. Targeted independent delta QA is next.

### BETA-RUNTIME-001 — image-only beta runtime candidate for independent QA, 3 November 2026

- Resumed in the authoritative worktree at `f0d2422` under the existing writer claim. The saved plan and Compose draft were validated against the repository, and two draft defects were corrected. An empty `FLORABASE_WFO_SNAPSHOT_PATH=` parses as `Path('.')`, so optional datasets now live in a rendered `reference.env`. CPU limits now default to unlimited, because Synology kernels may refuse CFS quotas.
- Added `deploy/beta/compose.yaml` and the stdlib-only, Python 3.8-compatible `deploy/beta/florabasectl.py`. The stack is image-only, digest-pinned, with bind-backed stable volumes mounted `nocopy`, a schema-gate (startup never migrates), maintenance-only migrate/tools, a loopback-only frontend, hardened read-only containers, bounded logs and `dockhand.update=false` everywhere.
- The controller covers preflight evidence, init, install, owner bootstrap and acceptance (local and HTTPS, with owner login). Recovery sets carry checksums, metadata and exact table counts; it also does verify, retention, encrypted restic export/import, isolated and replacement restore, and a serialized journaled promote/resume/abort with forward fix. Plus drift and volume-adoption refusal, reference datasets, status alerting and check-release.
- Smoke-found controller defects were fixed: Compose's unbounded dependency wait would hang on a crash-looping backend; child processes consumed a stdin password; Docker copy-up made the host `postgres/` directory 1777; plain or foreign `florabase-prod_*` volumes from the source-build stack were not refused; an interrupted replacement restore did not block other mutations.
- Checks: `make test-beta-runtime` (34 tests under Python 3.14.4 with host Compose, 26 controller tests under Python 3.8.20). The offline suite also passed with checksum-verified Compose 2.20.1. ruff (py38 target), ruff format and mypy --strict are clean on all new files. `make smoke-beta-runtime` passed on docker:24.0.2-dind with Compose 2.20.1 and the controller under Python 3.8.20 from a copied bundle. It covered install, persistence across recreation and daemon restart, backup/tamper detection, isolated restore (33.5 s), restic export/import, a compatible upgrade with unchanged PostgreSQL container/image/volumes, refusal of an ahead schema, the failed-migration abort, the failed-application refused abort plus forward fix, replacement restore (41.8 s) with sessions invalidated and failed data preserved, SIGKILL-after-migrate resume, and WFO dataset provisioning (read-only, cleared). Owned resources were retired with zero residuals; the unrelated workload and host `florabase-prod` resources were unchanged.
- Not done: no real-host access, deployment, Dockhand pin or Tailscale Serve verification, real reboot, off-host destination or RPO/RTO acceptance; no independent QA, canonical FULL, push or PR. The restic image is a new runtime-owned pin for BETA-SECURITY-001 scanning. [Runbook](beta-runtime-001.md).

### BETA-RUNTIME-001 — independent QA corrections R1–R4, 3 November 2026

- Codex infrastructure QA failed `e1a708f` (tree `25e01a8c…`).
  - R1 P0: the reusable one-shot schema gate is replaced by a backend entrypoint guard that runs on every start. It requires image head = `.env` release head = database revision and fails closed. The schema-aware healthcheck stops a running backend whose revision changes.
  - R2 P0: retention now proves set identity from the directory (syntax, real non-symlink ownership/mode, containment, exact artifacts, checksums, metadata identity) and re-proves it before deletion; the policy is range-checked.
  - R3 P1: IPv4 loopback-only binding.
  - R4 P1: the disclosure scan is derived from the Git feature diff plus untracked files.
- Against the reviewed controller, every new R2/R3 regression fails; its retention deleted `../../victim` and an absolute path, in disposable temp directories. The reviewed Compose fails the new guard contract test.
- `make test-beta-runtime`: 50 tests pass under Python 3.14.4 with host Compose (also with Compose 2.20.1); 39 under Python 3.8.20, where the Git-based disclosure scan is skipped (no Git in the image). `make workflow-check` and `check-features` pass.
- Official `make smoke-beta-runtime` from clean commit `ec02359` (tree `aa774b3f…`) on docker:24.0.2-dind with Compose 2.20.1 and Python 3.8.20 took 703.5 s. In the schema-guard drill, after a recorded guard success the revision was forged; the backend never became healthy or ready while running, under plain `up -d` (exit 1), `docker restart` or recreation, and recovered with a plain `up -d` once the revision was restored. Also covered: bind refusals; retention with a planted `../postgres` entry kept untouched, newest set kept, idempotent; and all earlier drills. Owned resources were removed with zero residuals; host `florabase-prod` and the unrelated nested workload were unchanged.
- Two smoke-harness defects were fixed: early `docker exec` raced the DinD cgroup v2 setup (`sed: write error`, intermittent daemon exit), and recovery now uses plain `up -d`. Concurrent unrelated containers from another worktree's integration run appeared during the run and are not owned by it.
- Open: real-host evidence (OS/Python, pinned Dockhand, Tailscale Serve, reboot, off-host destination, RPO/RTO); restic pin security review (BETA-SECURITY-001); independent re-QA; canonical FULL. No push, PR, deployment or `release/inputs.json` change.

### BETA-RUNTIME-001 — second independent QA corrections R2–R4, 3 November 2026

- Codex QA failed `fcd25bc` (tree `c838427…`).
  - R3: ambient `FLORABASE_BIND_ADDRESS=0.0.0.0` rendered `host_ip 0.0.0.0`. The frontend now publishes on a literal `127.0.0.1` (only the port is variable); the bind-address option is removed; acceptance requires 127.0.0.1.
  - R4: the staged-only bypass. The scanner now reads Git objects (`base..HEAD`, staged index, unstaged worktree, untracked files) with rename detection, fails closed on Git errors and has no exemption.
  - R2 TOCTOU: removal now goes through a no-follow root descriptor (controller-owned 0700), set identity checks, an in-root tombstone rename and fd-based `rmtree`. The residual trust boundary is documented.
- Against `fcd25bc`: the hostile ambient variable still renders 0.0.0.0 (now 127.0.0.1), the reviewed scanner returns `[]` for the staged leak (now `staged notes.md:1`), and the directory-substitution, unprotected-root and bind regressions fail. R1 is unchanged and its drills still pass.
- `make test-beta-runtime`: 57 tests pass under Python 3.14.4 with host Compose and with Compose 2.20.1; 45 under Python 3.8.20 (Git-based disclosure tests skipped there, no Git in the image). `make workflow-check` and `check-features` pass.
- Official `make smoke-beta-runtime` from clean `b53da44` (tree `e25855ce…`) on docker:24.0.2-dind / Compose 2.20.1 / Python 3.8.20 passed every step, including the new live hostile-bind recreation (db/backend unpublished, frontend 127.0.0.1 only). Zero owned residuals; host containers and volumes identical before and after.
- New real-host blocker: Docker Engine < 28 (DSM ships 24.0.2) may expose loopback-published ports to same-L2 peers, so independent LAN reachability testing and DSM protections are required before deployment. No firewall, daemon or Tailscale changes were made. Remaining: other real-host evidence, the restic pin security review, origin/main reconciliation before final FULL (main is unchanged at `f0d2422` today), re-QA and canonical FULL.

### BETA-RUNTIME-001 — main reconciliation with BETA-SECURITY-001, 3 November 2026

- Fetched `origin/main` `52dc414` (PR #143, BETA-SECURITY-001) and merged it non-rewritingly as `0b53893`. The only conflict was the append-only progress log; both sections were kept, Security's first. `release/`, both Dockerfiles, workflows and the beta release/publication scripts are byte-identical to main. The PostgreSQL identity, manifest schema and publication restrictions are unchanged; the restic pin remains subject to separate security review.
- Main changes executable image contracts: the backend runtime is now `python:3.14-alpine` and the frontend `nginx-unprivileged:stable-alpine-slim`. Runtime assumptions were checked (frontend `wget` healthcheck, BusyBox `sh`/`rm`/`touch`/`env`, Python entrypoint guard and healthcheck, uid 10001/101); no runtime code change was needed.
- Checks: `make workflow-check` (Security's beta image suite 25/25 included), `make test-beta-runtime` (57 tests under Python 3.14.4, also with Compose 2.20.1; 45 under Python 3.8.20), `check-features` (134 valid).
- Official smoke rerun from clean `0b53893` (tree `914989a0…`): all 18 steps passed on the Alpine images in 776.7 s. Steps included hostile bind, schema guard, isolated (36.6 s) and replacement (46.2 s) restore, failed/interrupted upgrades and the retention boundary. Zero owned residuals; host containers, volumes and networks unchanged.
- Remaining: real-host acceptance (LAN reachability on Engine 24.0.2 with DSM protections, OS/Python, pinned Dockhand, Tailscale Serve, reboot, off-host destination, RPO/RTO), Security's own PostgreSQL 2 CRITICAL/26 HIGH publication blocker, the restic pin review, final QA and canonical FULL.

### UI-DESIGN-001 — consistency review package, PROPOSED / AWAITING DESIGN APPROVAL, 4 November 2026

- Documentation only, on `docs/ui-design-001` from `61fefbb` (#144), writer `claude-ui-design-001`. Package: `docs/review/ui-design-001/` (audit, findings F-01–F-17, decisions D1–D6 all pending, proposed token/component changes, phased Claude Code plan with independent review, acceptance and public screenshot checklist, evidence index, seven labelled design mockups). Interactive source: the private Claude Design artifact linked from the package README.
- Re-checked on main: RELEASE-VISUAL-AUDIT F09 resolved; F01 resolved at callers but still order-dependent in `TaskDialog`; F02 partial; UI-DETAIL-001 residue (C5 row, repeated lifecycle) still in source; UI-FLICKER-001 still partial and not re-measured.
- Limits: no authenticated live session on main (owner sign-in); captures are from 1 November; no physical device, screen reader, real zoom or forced-colors checks; contrast computed from `tokens.css`. Mockups are hand-built recreations with synthetic data, rasterized with html2canvas, and are not product screenshots.
- No frontend, token, backend, schema, fixture or environment change. Checks: `check-features` (135 valid), docs-only `make feature-verify`. No push, PR, merge or delivery. Codex is not assigned implementation work.

### UI-DESIGN-001 — closed as a documented design review, 4 November 2026

- The operator closed UI-DESIGN-001 as a documentation-only baseline. **No implementation was approved.** D1–D6 stay open and deferred without decision. The operator will explore a more radical redesign in a separate feature, Florabase Next, which is not started on this branch.
- The package status changed to COMPLETE — DOCUMENTED DESIGN REVIEW · NO IMPLEMENTATION APPROVED. The audit, findings, mockups, evidence index and design artifact are kept unchanged as reference. The README gained a Closure section; the implementation plan is reference only. The feature is `verified` against its revised closure criteria.
- Checks: `check-features` (135 valid) and docs-only `make feature-verify` on the final committed HEAD. No frontend, token, backend, schema, fixture or environment change. No push, PR or merge; the branch is ready for operator `make feature-deliver`.

### UI-REDESIGN-EXPLORATION-001 — M0 worktree and authenticated baseline, 4 November 2026

- Operator approved experimentation with decisions D1–D4: Workbench direction enriched with Herbarium and Living Lineage, Field Ledger light and dark without removing the six themes, 40px pointer and 44px touch controls, and M0 first. Experimental only. No FULL, delivery or merge before operator review of the running alternative.
- Agent-provided worktree at `origin/main` `d94f275`: session branch renamed to `feat/ui-redesign-exploration-001`, `make feature-init`, `make feature-claim AGENT_ID=claude-next`. Primary checkout and main unchanged.
- Baseline: UAT Preview (`florabase-uat-preview`, loopback 15174) built from this worktree at `d94f275`, migrations at head `20261013_0042`, fixture v4 with 66 synthetic records, UAT-only fixture owner. No personal credentials. DEV untouched.
- `docs/design/florabase-next/capture.py` in the pinned Playwright image (`v1.48.0-noble`, playwright installed into scratch, nothing added to the repository's dependencies): 149 images over 37 routes at 1440/1024/390. None skipped, no console errors, no external requests. Manifest with hashes committed; images kept outside Git in the locally excluded `.florabase-next-evidence/`.
- Registered `UI-REDESIGN-EXPLORATION-001` (`in_progress`). Limits: small fixture, no screen reader, forced colours, real zoom or device. No frontend code change yet; M1 (Field Ledger palette and primitives) is next.

### UI-REDESIGN-EXPLORATION-001 — M1 Field Ledger foundation, 4 November 2026

- Commits `8ce52fa`, `b39fa50` and `ecadaf3`, frontend only. Field Ledger joins the existing palette × appearance matrix as a system: Instrument Sans UI, Newsreader italic scientific names, IBM Plex Mono data, 14/20 body, 8/12/14 radii, 2px focus offset, and 40px pointer controls with 44px under compact or coarse pointers. Complete light and dark sets are included. It is the branch default only; saved Botanical, Herbarium or Mineral choices are honoured, and a test pins those six blocks to main's bytes.
- New system tokens default to UI Foundation values; shared rules read them, with no page-local overrides. Fonts are exact-pinned Fontsource 5.3.0 (OFL-1.1), same-origin, with licences under `/licenses/`, no CDN.
- Checks: typecheck, lint, Prettier, production build. The full frontend suite passed 1153/1153 in three serial runs; main `d94f275` passed 1145/1145 three times. Three earlier branch runs under concurrent capture load each showed one different focus/timing intermittent (UX004, StoredMaterial, Schedule); none reproduced in isolation or serially. Recorded for independent review.
- Evidence: 70 images at `ecadaf3` (manifests in `docs/design/florabase-next/m1/`). Field Ledger light, dark and tablet show no control below 40px desktop or 44px touch and no console errors. Botanical preservation is 33/37 pixel-identical to the baseline; Settings differs as intended, dashboard and Geography are capture noise, and the Collection origins zoom glyph difference (131 px) is unexplained. Baseline 149/149 hashes intact.
- Pre-existing findings on main, not changed: Leaflet zoom buttons are 30px, and lazy `geography.css` changes directory breadcrumb spacing after a Geography visit. Canonical FULL not run; no push, PR or merge. Stopped at the M1 checkpoint.

### UI-REDESIGN-EXPLORATION-001 — M2 Workbench shell and navigation, 4 November 2026

- Commit `307611b`, frontend only. New `frontend/src/shell/`: the navigation model (six workspaces, every section once, existing sub-views as deep links, shared creation actions), `WorkbenchShell`, `CommandPalette` and scoped `workbench.css`.
  - **Rail:** a workspace tablist that previews sections without navigating.
  - **Context panel:** Search, New, sections and sub-views, account, and a hide option.
  - **Palette:** Ctrl/⌘K or `/`, over sections, creation routes and records from the existing `/api/v1/search`, with loading, empty and error states.
  - **Mobile:** a header section strip, a workspace bottom bar with section sheets, and an account sheet.
- Routes, deep links, history, auth and the unsaved-changes guard are kept. `App.tsx` routes all shell navigation through one guarded `navigateTo`, and the shell keeps the existing page layout contract.
- Fixed from M1: the lazily loaded duplicate breadcrumb rules in `geography.css`, and the 30px Leaflet zoom buttons. Removed about 620 lines of dead sidebar CSS, the resize handle and the collapsed-groups preference.
- Tests: the shared `test/navigation.ts` helper; old sidebar tests replaced with Workbench equivalents (destinations, panel preview/hide/reopen, tablist keyboard, malformed preference); 10 new shell tests.
- Checks: typecheck, ESLint, Prettier and production build pass. The full frontend suite passed 1164/1164 on the committed tree three times (one in-session run and two serial runs). No intermittent failure was observed in M2; the earlier M1 focus/timing intermittents stay tracked and unclassified.
- Evidence (UAT Preview, synthetic fixture), manifests in `docs/design/florabase-next/m2/`:
  - Field Ledger light: 43 captures over 12 routes at 1440/1024/390 plus palette, preview, New menu, sheets and keyboard focus. No control under 40px pointer or 44px touch, no console errors.
  - Dark: 10 captures, same result.
  - Botanical inside the shell: 7 captures; one 40px mobile filter chip, as on main.
  - Six before/after composites are in `.florabase-next-evidence/m2-before-after/`.
- Deviations from the concept are documented: the rail previews rather than navigates; no global top bar; no counts or saved views in the panel; Settings as a sixth workspace; Dashboard is unchanged until M3. The Collection origins glyph variance is superseded by the zoom resize and remains unexplained. Canonical FULL not run; no push, PR or merge. Stopped at the M2 checkpoint.

### UI-REDESIGN-EXPLORATION-001 — M3 Today and directories, 4 November 2026

- Commit `b59a21c`, frontend only. Today replaces the Dashboard presentation on the same route and endpoint:
  - A lede composed only from returned counts.
  - The holdings ledger.
  - Next work labelled "Planned in Schedule", with the Overdue caveat.
  - Specimen plates.
  - Recent activity with Journal and History origins kept.
  - A compact Record keeping panel of the existing derived counts, with their definitions. This reverses the v0.1 decision to hide those modules and is flagged for review.
- The page-level Quick add is consolidated into the shell New menu. Shell creation routes now use `openCollectionPage`, so Back semantics match content links.
- Directories adopt the Ledger grammar through edits to their owning rules (`directory-system.css`, `directory.css`, `status.css`): hairline rows, Newsreader scientific names, end-aligned summaries, quiet row actions, 4:3 specimen plates, phone rows with actions on their own line, and dot-and-word status. Field Ledger titles use Newsreader via `--type-h1` and `--type-h2`. The six themes stay pinned.
- Saved Views are discoverable in the owning workspace panel, Today, mobile sheets and the palette, via the existing list endpoint and `savedViewHash`; incompatible views are omitted. There's also a session-only Recent group. No new API or route.
- The Journal record launcher no longer depends on the lazily loaded Dashboard stylesheet; about 600 lines of dead dashboard CSS are removed.
- Checks: typecheck, ESLint, Prettier and build pass. The full frontend suite passed 1169/1169 on the committed tree three times (one in-session run and two serial). No intermittent observed. Main JS is 11 kB larger (3.4 kB gzipped).
- Evidence: 61 captures at `b59a21c` (manifests in `docs/design/florabase-next/m3/`), plus six before/after composites. Field Ledger shows no control under 40px pointer or 44px touch and no console errors.
  - A temporary Saved View was created via the API for the captures, then deleted; UAT is back to zero Saved Views.
- Preview-model evaluation (analytical, not user testing): keep the model, with Recent, Saved views and the palette offsetting cross-workspace trips.
- Known regressions and limits: no in-page Quick add; the visible title is now Today; Record keeping reverses the v0.1 decision; a small band above gallery photos; stacked directory tools on phones.
- Canonical FULL not run; no push, PR or merge. Stopped at the M3 checkpoint.

### UI-REDESIGN-EXPLORATION-001 — M4 record detail and lineage, 4 November 2026

- Commits `94a1675` (implementation and tests), `bfb23b4` (Order detail target size) and `380e6f4` (Harvest states Source and date once). Frontend only: no backend, API, schema, route or auth change.
- M3 decisions:
  - Today's record-keeping counts are now a collapsed, neutral "Data quality" disclosure that keeps its definitions and source line.
  - Saved views show five, then an accessible "Show all N saved views" disclosure; the eight-item cap is removed.
  - Mobile directory header density is carried as a required item before final visual acceptance.
- Shared `DetailHeader` across all ten record types:
  - 6rem specimen plate.
  - Field Ledger `--type-record-title`; the six themes fall back to `--type-h1`.
  - Botanical-face scientific names, a lifecycle line and an optional lineage slot.
  - Lifecycle is stated once (removed from At a glance on Plant, group, Seed lot and Sowing). Sowing's Seed lot moves to the strip. Harvest states Source in the header and the date in the summary.
- `LineageStrip` shows only the explicitly recorded upstream path from the existing lineage endpoints, oldest first. Sowings read their recorded Seed lot's path. There are no descendants and no identity-based inference. It has an empty wording and a retryable failure. `LineagePanel` shares the new `useRecordedLineage` hook.
- `RecordTimeline` replaces `UpcomingActivities`:
  - A Planned lane from Schedule; overdue reads "not recorded as done".
  - A Recorded lane from the Journal, with partial-date precision kept and undated entries stated.
  - Seed lots and Sowings point to where their records live.
  - System history links History by kind. A per-record History filter is recorded as a separate proposal.
- Checks:
  - Typecheck, ESLint, Prettier and build pass. Main JS is 263.1 kB (gzip 81.6 kB).
  - Full frontend suite 1177/1177 at `94a1675` and twice at `380e6f4`, plus one serial rerun with 1 failure: `StoredMaterial.test.tsx` "a QR inventory hash change focuses the retained record on an already-open Harvest".
  - That test then failed 2 of 30 times in isolation at `380e6f4` (and 0 of 20 times with the pre-`380e6f4` Harvest screen, which the test does not load).
  - The branch has not changed `StoredMaterial.tsx`, its test or its API, and they import no M4 module. This is the StoredMaterial intermittent tracked since M1. It is still not classified as pre-existing, because it has not been reproduced on main.
- Evidence: 108 captures at `380e6f4` (nine detail routes at 1440 full and viewport, 1024 and 390, in Field Ledger light and dark and in Botanical). Manifests are in `docs/design/florabase-next/m4/`. There are 16 before/after composites against the main baseline.
  - Field Ledger: 0 console errors and 0 controls below target.
  - Botanical: 0 console errors. Order detail's inline action is 40px at touch widths, because the six themes keep their pointer geometry.
- Open for review:
  - Mobile directory header density (required).
  - The prominent programmatic focus outline on record titles.
  - One extra Journal request on Plant details.
  - Plant Origin and provenance partly repeats the strip.
  - Non-lineage record types only get the shared header.
- Canonical FULL not run; no push, PR or merge. Stopped at the M4 checkpoint.

### UI-REDESIGN-EXPLORATION-001 — M5 advanced interactions and mobile workflows, 4 November 2026

- Commit `e593c50`, frontend only.
- Record sheet (rail accent; first item of the phone bottom bar) contains:
  - the open record's own actions;
  - a Plant / Plant group / Sowing chooser into the record's real form via a one-time `?entry=new`;
  - label links (typed, pasted or USB-scanner);
  - camera scanning only with `BarcodeDetector` in a secure context;
  - the existing recording routes.
- No form copies and no new API.
- Label links accept only the shapes labels encode and use only the in-app route.
- Palette leads with "This <record>" actions. Fixed broken palette group `aria-labelledby` (ids contained spaces).
- Programmatically focused headings show the focus ring only after keyboard use (verified in UAT).
- StoredMaterial QR focus test: diagnosed as a passive-effect race in the test (the component also focuses when its effect registers). It now waits for focus: 2/30 failures before, 40/40 after. Not classified as pre-existing.
- MediaScreen "detail return preserves filters…" failed once in one full run; 0/30 isolated; media untouched on the branch. Tracked.
- Checks: typecheck, ESLint, Prettier and build pass; 1203/1203; main JS 269.9 kB (gzip 83.4 kB).
- Evidence: 10 interaction captures plus 24 route captures at `e593c50` (manifests in `docs/design/florabase-next/m5/`). 0 console errors; 0 below target; keyboard-only Record → Journal entry verified.
- Open for M6 and release acceptance:
  - Record-detail distinctiveness.
  - A three-step UAT lineage chain.
  - Overview consistency for non-lineage details.
  - Journal double load (investigated; design options recorded).
  - Provenance/lineage duplication.
  - Mobile directory header density (required).
  - Camera scanning untested on real devices.
- Canonical FULL not run; no push, PR or merge. Stopped at the M5 checkpoint.

### UI-REDESIGN-EXPLORATION-001 — M6A creative design review, 4 November 2026

- Design only; no frontend, backend, API, schema or auth change.
- New Claude Design canvas: https://claude.ai/artifact/B3TWNaSJvnjxUz2GmdXRCx. The Phase B artifact is preserved unchanged. The canvas has ten artboards over four pages:
  - three record-detail directions (A Specimen Sheet, B Research Workspace, C Ledger Folio);
  - A on phone and tablet, with sparse data, unknowns, partial dates, and loading/error states;
  - Today grouped by record, a compact phone Seeds header, Record sheet v2, and the palette and confirm dialog;
  - before/after with real M5 captures.
- Grounded in UAT fixture v4 data; one three-step lineage record is marked illustrative.
- Audit, tradeoffs, recommendation, M6B component plan and the release-issue register (R1–R13) are in `docs/design/florabase-next/m6a-design-review.md`.
- Recommendation: direction A (Specimen Sheet) for all ten record types, with C's precision grouping in the Journal tab.
- M6B not started; awaiting operator direction approval. No FULL, push, PR or merge.

### UI-REDESIGN-EXPLORATION-001 — M6B Specimen Sheet implementation, 4 November 2026

- Direction A (Specimen Sheet) with Direction C's precision grouping, as approved.
- Commits `81ba6b9`, `85b726a`, `659e053`, `70810bb`, `353ea39`, plus the checkpoint commit. Frontend only.
- Specimen Sheet: `DetailHeader` specimen mode, `SpecimenPlate`, `SpecimenLabel`.
  - Applied to Plant, Plant group, Seed lot, Sowing, Harvest (including Stored material inside it), Order, Supplier and Location (label only).
  - Botanical identity keeps its reference-hub layout (deviation).
- Lineage sequence with relationships written as text. Almanac axis with precision groups.
- `JournalScope`: one Journal request per record view (R2).
- Compact phone directory header (R4): first record 580px → 264–296px; no header control under 44px.
- Today groups Next work by record. Record sheet v2: tiles plus one record search through the existing search endpoint.
- R5: a real three-step lineage was created in isolated UAT through the existing extraction API (Plant `01a1a834-…`). UAT Preview now differs from fixture v4 by that Plant, and the Basil seedlings group is now 5 plants.
- Tests changed only where the design moved a fact:
  - Plant "Managed group" and "At a glance" regions → "Plant group facts";
  - the extracted Plant's group link is asserted in the facts;
  - Seed lot "At a glance" heading → facts region;
  - Timeline → Almanac;
  - Record sheet chooser → search;
  - one Journal call-signature assertion.
- New tests: Almanac geometry and grouping, the shared Journal request, and lineage relationship text.
- MediaScreen (R6): final focus assertion hardened for the passive-effect race (not reproduced: 0 of 32 stressed isolated runs).
- New intermittent: SowingScreen "old Sowing propagation URL opens the canonical Lineage tab and empty summary" failed once in one full run and 0 of 15 isolated; tracked, details in the M6B README section.
- Checks:
  - Format, typecheck and lint pass; build passes. Main JS 269.9 → 285.0 kB (gzip 83.4 → 87.8 kB).
  - Full suite on the final tree: 4 runs. 3 passed 1207/1207; 1 had the single SowingScreen failure (0 of 15 isolated, 0 in the 2 later full runs; message not captured).
- Evidence: 144 captures at `353ea39`, plus 6 interaction captures. Manifests are in `docs/design/florabase-next/m6b/`.
  - 0 console errors.
  - Field Ledger light and dark: 0 below target.
  - Botanical: 40px controls at touch widths, from the original themes' pointer geometry (as since M1).
- Open: R7 real-device QR, R10 measured contrast pass for new tint pairs, R11 manual screen reader/zoom/forced colours, the Journal tab's own precision grouping, the phone action dock.
- Canonical FULL not run; no push, PR or merge. Stopped at the M6B checkpoint.

### UI-REDESIGN-EXPLORATION-001 — M6 final refinement and visual review, 4 November 2026

- Frontend only, on M6B.
- Botanical identity reference sheet: framed 4:5 plate, record-title serif, ruled foot. Its hub layout is kept.
- Journal tab precision periods (shared `precisionGroups`; one list item per entry, API order).
- Specimen label: links and paths use the UI face; recorded values keep the data face.
- Evaluated and declined, with reasons:
  - phone action dock (duplicates the Record button);
  - Today thumbnails (schedule targets carry no image);
  - Record sheet recent chips (the shell's Recent holds sections, not records).
- Accessibility (automated):
  - every new text pair ≥ 5.58:1 and non-text marks ≥ 4.08:1, in light and dark;
  - 45 Tab stops on a record, all with a visible focus indicator;
  - 200% zoom: no horizontal overflow; 400% zoom: no element beyond the viewport (the 16 px reported on Seeds is the test browser's scrollbar);
  - forced colours: no console errors.
- Manual screen reader, real zoom, real high contrast and physical-device checks remain owed.
- SowingScreen intermittent: mechanism proven (2 of 150 probe renders showed the tab selected before the address was canonical). Fixed in the app with `useLayoutEffect` (0 of 300 after). Not classified as pre-existing.
- Four full runs before the fix: 1207/1207 each. Final tree: one run 1207/1207; one run had a new single failure in App "identity section keyboard navigation retains browser Back and Forward boundaries" (truncated hash mismatch; 20 of 20 isolated passes; not diagnosed; tracked).
- Larger specimen images: an additive `display_url` rendition with `srcset` is recorded as a backend proposal; not implemented.
- QR camera on Android: pending the operator.
- Review: live UAT at http://localhost:15174 (`preview` / `preview`, synthetic). 16 numbered screenshots are in `.florabase-next-evidence/m6-final-review/` (manifest in `docs/design/florabase-next/m6-final/`).
- Canonical FULL not run; no push, PR or merge. M7 not started.

### UI-REDESIGN-EXPLORATION-001 — M7 side-by-side evaluation and recommendation, 4 November 2026

- Commits `2d95552` (lineage, tablet, phone and sparse-Almanac refinements) and `4571f03` (fixes), plus the checkpoint commit (docs). Main `d94f275` is unchanged and is the merge base.
- Regressions found and fixed:
  - phone DirectoryPage directories were 16 px too wide since M6B (hidden title), hiding part of the bottom bar;
  - a pre-existing 32 px Taxonomy disclosure.
- Correction: the M6 note attributing 16 px at 400% zoom to a scrollbar was wrong; it was the overflow.
- Functional comparison:
  - test inventory: 894 → 937 names; 8 absent, all replaced or renamed;
  - route sweep: all 37 main routes, 0 console errors, 0 below target in Field Ledger light and dark;
  - workflow smoke 10/10 on synthetic UAT, including Journal create and delete with the data restored.
- Identity intermittent:
  - not reproduced in 4 instrumented full runs (step latencies 1–13 ms against a 1000 ms wait, refuting the timeout hypothesis) or 20 isolated runs;
  - tracked and unclassified.
- Checks:
  - format, typecheck, lint and build pass; full suite 1207/1207 on the final tree, and 4/4 instrumented runs;
  - backend diff against main is empty.
- Evidence: 236 captures at `4571f03` in Field Ledger light and dark, plus 10 main-vs-Next composites. The independent review package is `docs/design/florabase-next/INDEPENDENT-REVIEW.md`.
- Recommendation: adopt with specific blocking corrections (independent review, a manual screen reader pass, identity intermittent classification, operator acceptance of the habit changes, then FULL and delivery only on approval).
- QR camera on Android: pending the operator. Canonical FULL not run; no push, PR or merge.

### UI-REDESIGN-EXPLORATION-001 — M8 design refinement (Stage A and Stage B), 5–6 November 2026

- Input: independent audit of `35f9eb2` (functional QA pass with findings; design and UX acceptance fail) and operator findings A–C.
- Stage A: Claude Design canvas https://claude.ai/artifact/EZkPPeaXAXm151sJmbUPCq (record detail, Today, phone, missing photos and palette, directories) and `docs/design/florabase-next/m8a-design-refinement.md`.
- Stage B commits `42929cf`, `e5e7abe`, `edc25b8`, `0495b81`, `a94d02f`, `b92e6ca`; record in `docs/design/florabase-next/m8b-implementation.md`.
- Defects fixed with cause and failing-first regression tests:
  - Workbench panel collapse: the collapsed rule preceded an equal-specificity base rule;
  - detail tabs ignored later `?tab=` routes on an open record (the cause of the identical M7 plant-lineage capture); captures now assert address and selected tab.
- Built: specimen sheet, 2× image-enlargement cap, quiet missing-photo mat, lineage stem and phone disclosure, panel collapsed on record pages, Today bench, shared ledger directory language, phone directory spacing (first record 236–247 px), identity tab grid, palette record glyphs.
- Not built: sparse-Almanac season strip, palette group totals, Locations/Journal/History/Taxonomy list restyle, phone context bar replacing the workspace strip.
- Extended Review + WFO: investigated only (`docs/design/florabase-next/m8-extended-review-environment.md`); no supported environment combines v5 and WFO; nothing activated.
- Tests: identity intermittent not reproduced in 33 further runs (21 orders, 12 under contention). New: `location hierarchy … keyboard selection` fails deterministically with shuffle seed 3; Geography and a Schedule test failed once each, unclassified.
- Checks on `b92e6ca`: format, typecheck, lint, build pass; full suite 1209/1210, then 1210/1210 twice; backend diff empty.
- Manual screen reader, physical zoom, high contrast and touch passes and Android QR remain open. Canonical FULL not run; no push, PR or merge.

### UI-REDESIGN-EXPLORATION-001 — M8 final UX (Activity identities and Settings), 6 November 2026

- Approved design: canvas page 6 with D1 (History chips share the Filters state) and D2 (Month day inspector on selection).
- Commits `15dc04f`, `c1146b4`, `7f4a222`, `5eb5691`, `0127aa0`, `784c975`; record in `docs/design/florabase-next/m8-final-ux-implementation.md`.
- Built: Settings as Theme · Labels · Import / Export, with the QR destination in Labels and a compatible `#/settings?tab=general` redirect; the Journal as a field journal; History as an audit table with fact type chips; the Schedule's Agenda lanes, Month cells and day inspector.
- Found and fixed during verification:
  - History chips were 36 px, below target (caught by the capture probe);
  - the legacy QR redirect was lost under React development double-invocation.
- Checks on `784c975`: format, typecheck, lint and build pass; full suite 1211/1211 in three consecutive runs; 236 captures with 0 errors, 0 below target and 0 state failures; backend diff empty.
- Manual accessibility passes and Android QR remain open. Canonical FULL not run; no push, PR or merge.

### UI-REDESIGN-EXPLORATION-001 — M8 independent QA remediation, 6 November 2026

- Input: Codex Luna's final M8 QA (PASS WITH FINDINGS; FULL not authorised). Record:
  `docs/design/florabase-next/m8-qa-remediation.md`.
- Commits `a9bf9e5` (F2 test sync), `33f427b` (F3 TaskDialog focus gap), `9744409` (F1 phone
  day panel and shell scroll-padding), `b164650` (F4 History chip row), `61867c0` (F7
  identity title focus).
- Reproduced and root-caused F2 (lazy chunk plus synchronous query), F3 (focus on `<body>`
  between dialog removal and passive cleanup; no duplicate mutation or lost work) and F7
  (late title focus taking focus from the tabs). F6 not reproduced and not claimed fixed.
- Checks on `61867c0`: format, typecheck, lint and build pass; 1217/1217 in three
  consecutive full runs; 40/40 shuffled App seeds and 40/40 shuffled Schedule runs under
  contention; 155 light and 155 dark captures with 0 errors, 0 below target and 0 state
  failures; backend diff empty.
- Open: manual screen-reader, zoom, high-contrast and touch passes; Android QR; F6 watch.
  Canonical FULL not run; no push, PR or merge.

### UI-REDESIGN-EXPLORATION-001 — M8 final responsive QA remediation, 6 November 2026

- Input: Codex Luna's second M8 review (FULL NO-GO); scope limited to two responsive
  corrections. Record: `docs/design/florabase-next/m8-responsive-remediation.md`.
- `177a01e` (P1): the pinned phone header is detected against the layout viewport
  (`clientWidth`), not `window.innerWidth`, so classic scrollbars no longer zero the top
  scroll-padding; measured bar geometry is published rounded up.
- `41a5c35` (P2): `body` min-width subtracts a classic scrollbar's width, removing the
  15px page overflow at 320px without hiding overflow.
- `e5a430a`: real-browser geometry regression under classic and overlay scrollbars;
  74/96 on `61baa3f`, 96/96 light and dark on `e5a430a`.
- Checks on `e5a430a`: format, typecheck, lint and build pass; 1220/1220 in three
  consecutive full runs; 155 light and 155 dark captures with 0 errors, 0 below target
  and 0 state failures; backend diff empty.
- F6 stays on the watch list. Canonical FULL not run; no push, PR or merge.

## 2026-11-06 — VERIFICATION-FAST-001 cheap-first canonical gate (Phase 1)

- Root causes:
  - Whitespace checks ran after every expensive stage, so a FULL that passed all Docker suites
    failed on two Markdown EOF blank lines and had to repeat everything.
  - `test-agent-workflow.py` `helper()` inherited the runner's stdin. Under a terminal,
    `TAKEOVER=` refusals became operator takeovers. This was reproduced with a PTY: 2 failures on
    `fec0398`, passing with `/dev/null`.
- The gate now runs graph, then the three whitespace checks, then offline workflow suites,
  workflow-check, quality, builds, the migration cycle and integration. The stage set and commands
  are unchanged.
- Every stage gets `/dev/null` stdin. The gate prints the stage order, a per-stage summary and a
  diagnostics-only last-run journal. The frozen-state check now covers the working tree, index and
  HEAD.
- `make check` runs `api-check` before `test`.
- Measured: a real `make verify-full` with a bad untracked Markdown EOF fails in 10.5 s wall time
  (stages 0.12 s, no Docker resources); before, it would have failed only after the whole FULL.
- Offline suites under a PTY stdin all pass (138 s), the same as the base under `/dev/null`.
- Checks:
  - `test-verification-impact`: 28 passed.
  - `test-feature-workflow`: 49 passed.
  - All eight offline workflow suites pass under a PTY stdin.
  - The workflow-check Ruff, format and strict mypy lines pass.
  - The new tests fail against the base scripts.
- Phase 2 reusable stage evidence is a proposal only. It is documented with its enforced-boundary
  safety analysis in [the handoff](verification-fast-001-handoff.md) and recommended as a separate
  feature. Independent infrastructure QA is pending.

### BETA-DISTRIBUTION-001 — installable beta distribution candidate for independent QA, 6 November 2026

- Worktree `feat/beta-distribution-001` from `fec0398`, writer `claude-beta`; `origin/main` `da80dc6`
  (#149, verification-workflow files only) merged without rewriting. Operator decisions: keep the
  image pair, explicit one-shot migrations, `0.1.0-beta.1`.
- Releases now attach `compose.yaml`, `florabasectl.py` and `florabase.env.example`; no `latest`.
  The backend guard reports invalid configuration (field names only), unavailable database and
  empty/pending/newer schemas with the exact action and still never migrates. Acceptance checks the
  application shell, its scripts and JSON 404 for unknown API paths. New
  [installation guide](installation.md) with Dockhand workflow; record in
  [beta-distribution-001.md](beta-distribution-001.md).
- Security: PostgreSQL pin moved to the upstream same-version `18.6-alpine` rebuild `123b1799…`
  (brotli/libcurl fixed; data-directory compatibility checked) — **needs operator approval**. Frontend
  base newly showed 3 HIGH (musl, zlib) with no upstream rebuild; exact Alpine pins restore 0/0;
  backend 0/0. **Blocker:** 1 CRITICAL / 25 HIGH remain in PostgreSQL's gosu (not executed by the
  stack; gate stays fail-closed). Reduced reports in `docs/security/beta-distribution-001/`.
- Checks: `make workflow-check` (incl. `test-beta-runtime` 60 + 48 under Python 3.8.20,
  `test-beta-images` 26); `check-features` 138 valid; guard refusals in the real backend image;
  `scripts/smoke-beta-runtime.py` 21/21 from clean `872f076` (830.6 s) and `fd4fc76` (841.4 s),
  adding pending-migration, missing-secret, stopped-database, HTTP-origin and TLS reverse-proxy
  drills; zero owned residuals, DEV/UAT/host `florabase-prod` untouched.
- Not run: independent QA, canonical `make feature-verify` (FULL), frontend/backend unit suites
  (no application code changed), registry publication, real-host or real Dockhand checks.
  Observation: readiness has no DB connect timeout. No push, PR, tag or release.

### BETA-DISTRIBUTION-001 — PostgreSQL gosu evaluation and readiness bound, 6 November 2026

- Operator approved the rebuilt `postgres:18.6-alpine@sha256:123b1799…5395` pin for development and
  isolated verification only; full digest, provenance, compatibility and recovery evidence recorded in
  [postgresql-gosu-remediation.md](security/beta-distribution-001/postgresql-gosu-remediation.md).
- No official fix exists: docker-library still pins gosu 1.19 for every PostgreSQL 18 variant and gosu
  1.20 is built on the same Go 1.24.6. A gosu-free derived prototype (upstream digest, `rm` gosu,
  `USER 70:70`) builds reproducibly (`b242b556…` twice), scans 0 CRITICAL / 0 HIGH / 0 secrets, and passes
  hardened 70:70 init, restart/recreation, dump, `pg_restore --list`, restore, old-pin data directory and
  default-user checks; a root start exits 127 before `initdb` without changing existing data.
  Recommended; integration into the protected publication workflow awaits operator approval.
- `985437f`: readiness hung without an answer for 60 s on a paused database; an unpooled engine with
  `connect_timeout=3` and `statement_timeout=2000` now answers 503 in 3.0 s (stopped database 503 in
  about 5 s, healthy 200 in 0.1 s).
- Checks: backend Ruff, format, strict mypy; backend unit suite 986 passed / 3 skipped (90.06%);
  readiness integration 2 passed; `beta_release.py check` passed; local artifact-only image smoke
  `LOCAL_BETA_CANDIDATE_PASSED` at `985437f` (docs edited during the run, image contexts unchanged).
- Runtime smoke 21/21 from clean `3123acf` (819.9 s, evidence refreshed); the drill's 5 s probe still
  meets the nested daemon's 5 s resolver timeout for a stopped `db`.
- Still BETA-BLOCKED. Not run: independent QA, canonical FULL, protected
  publication. No push, PR, tag, GHCR package or release.

### BETA-DISTRIBUTION-001 — Florabase PostgreSQL image integrated, 7 November 2026

- Operator approved integrating the gosu-free image (not publication). `postgres/` builds
  `florabase-postgres:18.6-alpine-florabase.1` from the approved `postgres:18.6-alpine@sha256:123b1799…`:
  gosu removed, zlib 1.4-r0, `USER 70:70`, a root guard (exit 64 before any initialization or data
  change). Deterministic with the pinned BuildKit (fixed epoch, no in-index attestations, apk.log
  removed); pins index `e5855f0c…` / platform `e625e587…` reproduced from fresh builders.
- Integrated into release inputs, manifest schema v2 (derived identity plus `upstream`), the protected
  publisher (refuses unreproducible builds; scan, SBOM, smoke, attestation, promotion with the pair),
  the controller, artifact, candidate and runtime smokes. Record:
  [postgresql-image.md](security/beta-distribution-001/postgresql-image.md).
- Registry-level check on a disposable registry: identity equal to the pins, release gate PASSED on
  the pulled bytes, Grype squashed and all-layers 0 Critical / 0 High, SBOM without gosu. gosu's
  original bytes remain in upstream layer 2 (runtime removal, not physical elimination).
- Grype also found zlib CVE-2026-4738 (Critical) that Trivy misses: fixed in the backend and
  PostgreSQL images. Backend `sqlite-libs` 3.53.4-r0 keeps 4 High with no Alpine fix, assessed not
  reachable; whether a second scanner gates releases is an operator decision.
- Checks: `make workflow-check`; `beta_release.py check`; local candidate passed; runtime smoke 22/22
  from clean `0d074e7` (858.2 s). Not run: actionlint (declined download), independent QA, canonical
  FULL, GHCR publication. Still BETA-BLOCKED. No push, PR, tag or release.

### BETA-DISTRIBUTION-001 — independent QA corrections, 7 November 2026

- Independent read-only QA of `794fdfc`: PASS WITH FINDINGS (1 P1, 3 P2, 5 P3); FULL not authorized
  until P1. All nine addressed in `8ce70c6`:
  - P1: the manifest binds the install bundle by SHA-256, each bundle file is attested, the controller
    refuses a differing `compose.yaml`/`florabasectl.py`, and attestation checks are mandatory in the guide;
  - P2-1/P3-2: an unpublished PostgreSQL identity is built and verified in a loopback registry before
    any byte reaches GHCR; a published tag must equal the pin (lookup errors fail closed) and is
    re-verified, not rebuilt;
  - P2-2: buildx client pinned (v0.38.1) and `postgres-identity --check` in the read-only verify job;
  - P2-3: release notes name the single-scanner gate; P3-1: upstream `docker-entrypoint.sh` refuses root,
    covering overridden entry points; P3-3: controller mirrors the identity rules and version label;
    P3-4: readiness caches a success for 1 s; P3-5: stale text corrected.
- New pins: index `4edc0790…`, platform `55b1969a…`, reproduced twice and through the verified-copy path.
- Checks: `make workflow-check` (release 30, runtime 61 + 49 on Python 3.8.20); backend unit 987 passed
  (90.07%); registry verification (gate PASSED, Grype 0 Critical/High both modes); local candidate passed;
  runtime smoke 22/22 from clean `52648b5` (857.9 s). Not run: actionlint, canonical FULL, publication.
  Delta QA requested. No push, PR, tag or release.

### BETA-DISTRIBUTION-001 — delta QA corrections, 7 November 2026

- Delta QA of `c88ea79`: PASS WITH FINDINGS (D-P2-1, D-P3-1, D-P3-2), all fixed: the verify-job identity
  rebuild is removed (it reintroduced the Alpine-pin release block), `check-release` reads newer manifests
  without the bundle check, and the guide's attestation loop fails visibly. QA accepted the absent
  `ci.yml` reproducibility job as a CI-FAST follow-up. Canonical FULL follows on the corrected tree.

### BETA-DISTRIBUTION-001 — SQLite reference-index hardening, 7 November 2026

- Final QA of `4329381` agreed with all four Grype `sqlite-libs` dispositions and demonstrated that a
  crafted index (a `taxa` view over FTS5) reaches CVE-2026-119373's code path through the WCVP search.
  The operator approved hardening before public publication.
- `core/reference_index.py` is now the only WFO/WCVP opener. It enables defensive mode, turns off
  views, triggers, extension loading, writable schema and trusted schema, sets `query_only` and
  `cell_size_check`, and holds one read transaction. It then requires the exact builder schema
  before any query, fails closed with a generic error and an operator log line, and writes nothing.
  Builders refuse to publish an index that fails the check. Builder DDL is unchanged, so every index
  from a supported builder stays accepted.
- Docs: the guide's reference-dataset section requires indexes built by Florabase's builders and
  separates integrity (SHA-256, seal) from provenance; security record
  `docs/security/beta-distribution-001/sqlite-reference-indexes.md`.
- Checks: `test_reference_index.py` (24 tests) and the existing WFO/WCVP suites (90 in total) pass
  on SQLite 3.40.1 (dev) and 3.53.4 (runtime image). Lint, format and strict mypy pass. Benchmark
  on 1.4M taxa: plus 0.07 ms per connection, identical results.
- Not run: indexes from the full official archives (not on this host). Canonical FULL and
  independent QA follow on the committed tree.

### BETA-DISTRIBUTION-001 — QA of the SQLite hardening, 7 November 2026

- Independent QA of `40200e0`: PASS WITH FINDINGS (3 × P3), all fixed. P3-1: duplicated
  `sqlite_schema` rows collapsed into the set comparison (a second `sqlite_autoindex_taxa_1`
  pointing at another b-tree passed and returned wrong data); duplicates are now refused and logged.
  P3-2: the test count in the security record. P3-3: the guide's `reference set --sha256` now uses
  the digest from the build output (the WFO seal, or the WCVP digest recorded after the build), not
  one computed from the copy. QA's informational note: `ATTACH` is now refused (attached-database
  limit 0). `test_reference_index.py` has 25 tests.
- Delta QA of `8ef70ec`: PASS WITH FINDINGS (2 × P3), both fixed. P3-4: the duplicate check was
  quadratic in the schema size (about 32 s of CPU for a crafted 30,000-object schema); it now
  compares the row count with the contract, and only counts duplicates for the refusal log. P3-5:
  the security record's suite total is 91.

### CI-RELEASE-PLATFORM — publication decoupled from host acceptance, 7 November 2026

- Release sequence clarified by the operator: publish verified linux/amd64 images and prerelease through the
  protected workflow; then deploy the published images to a chosen host; accept the host separately.
- `release/platform.json` now records the supported platform, `publication.host_approval_required=false` and a
  `deployment_acceptance` block that stays `pending`. Synology DS224+ is only a candidate target. `check_platform`
  no longer requires an approved host, operator or screening date; it fails closed unless the platform is
  linux/amd64, host approval is not required, and the deployment-acceptance block exists. All other
  publication protections are untouched.
- Docs: `beta-image-001.md`, `beta-security-001.md`, BETA-IMAGE-001 acceptance wording in `features.json`.
  Real-host acceptance (capacity, Docker/Compose, HTTPS, persistence, backup/restore, recovery) has NOT occurred.
- Checks: `make test-beta-images` (29 tests) and `beta_release.py check --publication` pass. Other publication
  blockers (QA/FULL, `RELEASE_APPROVED_SHA`, protections, manual authorization) are unchanged. Nothing published or tagged.

### RELEASE-TOOLS-LOCK-BETA2 — release-tool lock fix and v0.1.0-beta.2, 7 November 2026

- First protected run (`actions/runs/42395852280`) failed in the verify job: on Python 3.12 `referencing==0.37.0`
  requires `typing-extensions>=4.4.0` (marker `python_version < "3.13"`), which was absent from the hashed lock,
  so `--require-hashes` refused it. The publish job was skipped and no Release or package was created. It was
  invisible on the Python 3.14 development host, where the marker is false. Reproduced in `python:3.12`.
- `release/requirements.txt` now pins `typing-extensions==4.16.0` with wheel and sdist SHA-256 hashes verified by
  downloading both files. Hash checking, `--only-binary` and the bootstrap pip hash are unchanged.
- New `scripts/test-release-tools-lock.py` (run by `make test-beta-images`): prepares the tools from an empty cache,
  asserts pinned-and-hashed entries and no `--no-deps`/index overrides, and walks every locked wheel's `Requires-Dist`
  with markers evaluated for Python 3.11, 3.12 (GitHub runner), 3.13 and 3.14. It fails on the previous lock.
- Bootstrap audit: the clean bootstrap and the import check pass on Python 3.11–3.14 containers; Python 3.10 is
  unsupported by the repository and unchanged. No other bootstrap defect was found.
- Version bumped to `0.1.0-beta.2` (backend/frontend packages, Dockerfile defaults, OpenAPI, `release/inputs.json`,
  installation guide). The existing `v0.1.0-beta.1` tag is untouched; the operator creates `v0.1.0-beta.2` after
  delivery. Nothing published, tagged or configured.

### GHCR-PREFLIGHT-BETA3 — registry-manifest preflight and v0.1.0-beta.3, 7 November 2026

- Protected `v0.1.0-beta.2` run `42407235373`: verify passed; publish failed in the preflight with
  `gh: Invalid argument. (HTTP 400)` from `GET /users/alessandrorossato/packages?package_type=container`.
  The GitHub Packages REST API does not accept the workflow's `GITHUB_TOKEN` (it requires a classic
  personal access token with `read:packages`), so the listing could never succeed in CI. The fixture
  test mocked `gh` and hid it. Nothing was built, pushed or released.
- `publish-beta-images.py` now asks the GHCR registry API directly: a `pull,push`-scoped token from
  `ghcr.io/token` (the scope a push requests, so a not-yet-created package is still authorized), then
  `GET /v2/<repo>/manifests/<tag>`. A 200 must carry a manifest/index media type, `schemaVersion` 2 and a
  `Docker-Content-Digest` equal to the SHA-256 of the body. Only a 404 whose errors are all
  `MANIFEST_UNKNOWN`/`NAME_UNKNOWN` is absent; 401/403/429/5xx, network errors, timeouts and malformed
  bodies refuse. An existing backend/frontend version refuses; an existing PostgreSQL tag must equal the
  pinned index digest. No new token or permission. The cleanup no longer removes a builder that was never
  created (the secondary `no builder` error); logout still always runs.
- The repository formatter (target py314) rewrites `except (A, B):` into 3.14-only syntax, while the
  runner uses Python 3.12; a new test parses every release script with the 3.12 grammar.
- Tests: `RegistryPreflightTests` (12) for existing/absent/unauthorized/unavailable/malformed lookups,
  PostgreSQL tag with pinned and other digests, absent PostgreSQL rebuild and early-error cleanup; also
  run on `python:3.12-slim`. Live read-only GHCR probe: existing public tag returned its verified digest,
  an absent tag returned absent, invalid credentials refused.
- Not verifiable before the protected run: GHCR's answer to `GITHUB_TOKEN` for a never-published package
  (expected `NAME_UNKNOWN`/`MANIFEST_UNKNOWN` 404; any other answer fails closed).
- Version bumped to `0.1.0-beta.3`; `v0.1.0-beta.1` and `v0.1.0-beta.2` tags are untouched.

### BETA-RELEASE-REHEARSAL — reproducibility hotfix candidate, 8 November 2026

- The beta.3 publication run `42421453830` passed verification, protected authorization and GHCR
  preflight, then stopped at `require_pinned_postgres`: CI index `e514d64b...` and platform
  `72cb11d5...` differed from pins `4edc0790...` and `55b1969a...`. No app candidate push occurred.
  The retained state has no historical raw OCI documents or layer descriptors, so a byte-level
  first difference cannot be recovered from that run.
- A non-publishing rehearsal and shared publisher helpers were added. The exact prior BuildKit image
  and pinned 0.34.2 image both reproduced the pinned index, platform, config and all 13 layer
  descriptors on the TUXEDO. Thus BuildKit version alone is not the local cause; the GitHub-hosted
  comparison remains required before claiming root cause or accepting the candidate fix.
- Full local rehearsal on committed `f719785ba819ecf3bf0dc8ef5b0dc10f9b3f0604` passed all disposable
  registry stages: two independent PostgreSQL builds, backend/frontend production builds, manifest and
  digest checks, Trivy 0.69.3 scans (zero reported vulnerabilities/secrets), PostgreSQL SBOM,
  image-only migration/login/media smoke, install bundle inventory, local tag promotion and release /
  attestation input validation. First attempt caught and fixed a PostgreSQL repository namespace
  mismatch before the final run. Local GHCR authentication/absence, GitHub attestation creation and
  Release API finalization were not exercised.
- The local rehearsal report and full output are retained at
  `/tmp/florabase-beta-release-rehearsal-local-final` on the development host. They are not hosted
  workflow artifacts. `make feature-verify AGENT_ID=codex-beta-postgres-repro-001` passed FULL on
  commit `6dce05f`: workflow checks, static/type/API checks, 1,221 frontend tests, both production
  builds, full migration cycle and 836 selected PostgreSQL integration tests (29 skipped). The
  canonical gate reported zero residual owned containers, networks or volumes and wrote a valid
  receipt. GitHub-hosted rehearsal remains pending; do not mark the feature verified or prepare
  beta.4 until hosted evidence establishes the failed-run cause and the rehearsal passes there.
- Before hosted delivery, the diagnostic path was corrected so the previous BuildKit build records
  its OCI evidence even when it differs from the pin; that build is diagnostic and does not weaken
  the exact acceptance check on the two pinned-toolchain rebuilds. A regression test guards this
  distinction. Focused `workflow-check` passes; final FULL is rerun on the resulting commit.
- PR #155's first GitHub-hosted rehearsal (`42474189742`, artifact ID `13614289125`) ran on
  `ubuntu-24.04` with Docker 28.0.4, Buildx 0.38.1 and the pinned BuildKit 0.34.2, and reproduced
  the beta.3 mismatch. Its retained OCI evidence shows layers 1–11 and 13 match the pinned local
  reproduction; layer 12 (`COPY LICENSE`) differs, as does `rootfs.diff_ids[11]`. The local checkout
  presented `postgres/LICENSE` as 0664; forcing 0644 reproduced the hosted mismatch, while forcing
  0664 reproduced the pinned platform, config and index. The build helper now normalizes this
  context file to 0664 without changing Dockerfile history. A regression test checks normalization
  from a 0644 checkout and evidence collection before the unchanged exact digest gate.
- PR #155 hosted rehearsal run `42482904548` on `ubuntu-24.04` confirms the PostgreSQL correction:
  both independent pinned-toolchain builds and the previous-BuildKit diagnostic matched platform
  `sha256:55b1969a...` and index `sha256:4edc0790...`; all 13 layer digests matched. Backend and
  frontend production builds plus release-manifest validation passed. The run then exposed a
  separate registry evidence bug before Trivy: the classic `docker save` fallback indexed the
  `imagetools inspect --raw` response as an OCI index although it had no `manifests` member. The
  fallback now resolves and checks the root/native descriptors through the same immutable
  registry identity path used by manifest construction and retains the raw response for review.
- PR #155 hosted run `42485751305` again matched both PostgreSQL index and platform pins on two
  independent builds and the previous-BuildKit diagnostic; all 13 layers matched. Backend and
  frontend builds and manifest validation passed. Trivy setup then found another valid Docker
  export shape: `docker save` emitted an OCI `index.json` whose sole root points directly to the
  native platform manifest. `saved_descriptors()` treated that root manifest as an index and
  failed before scans. The follow-up fix verifies the exported uncompressed layer digests against the config and
  binds that config to the selected immutable registry index and adds regression coverage. Focused release tests passed
  (55 unit and 4 Python 3.12 compatibility tests). The next hosted rehearsal is still required;
  security scans and downstream stages have not yet passed on GitHub Actions.

### CI-HYGIENE-001 — verification impact for executable documentation, 7 November 2026

- Replaced the blanket `docs/` exemption with an allowlist of static documentation suffixes.
  Review Compose overlays, Python and browser tooling, the Dockerfile prototype, and unknown formats
  select FULL. Git mode evidence across the base, HEAD, index and working tree protects executable
  files and symlinks even when they use a documentation suffix.
- The baseline impact suite passed 28 tests. The updated suite passed 30 tests, including real Git
  modifications, additions, deletions, renames in both directions, masked modes and a synthetic
  PR merge smoke. Independent QA confirmed the suite, the 139-entry feature graph, and the current
  documentation inventory (65 FULL paths and 3,207 lightweight paths). It also checked unusual Git
  filenames and masked executable modes. QA reproduced an unmerged Markdown path whose executable
  stage-3 mode was absent from the raw diff. The planner now refuses unmerged paths, and the
  regression failed before this correction and passed afterward. Canonical FULL evidence belongs
  to the exact-tree receipt.
- The first FULL stopped at the disclosure check, which flagged a synthetic Git fixture address.
  The fixture now uses a local-only identity. The disclosure check remains in place.
- Focused Ruff lint, format and strict mypy passed after separating raw and decoded Git paths.

### DOCS-CORRECTNESS-001 — development, source upgrades and beta installation, 8 November 2026

- README uses the DEV targets in order and guards `make setup`. A disposable Makefile check
  reproduced that the standalone recipe still overwrites an existing `.env` despite its message.
  The documented guard preserved the existing fixture and created the file in the fresh case.
- Source-build upgrade instructions keep application writers stopped through the final paired
  backup and migration, with a maintenance-mode failure and recovery path. Routine `make backup`
  restarts the backend. Image-only installation checks all four release attestations and the
  bundle's manifest digests before controller preflight, install or promotion.
- Checked Make targets and documented commands against the helpers, Compose and protected
  workflow. Independent shell QA passed the two new snippets with disposable stubs, including
  backup, download, attestation, version and digest failures. The environment workflow suite
  passed 35 tests. The beta runtime offline suite passed 62 tests each with Compose 5.7.0 and
  checksum-verified 2.20.1. With the source DEV overlay, 2.20.1 rendered both frontend ports
  (5173 and 8080), while 5.7.0 rendered only 5173. The canonical docs-only gate is
  `make feature-verify` on the final commit.
- No live attestation verification, real-host beta acceptance or end-to-end source-build
  upgrade/restore drill was performed in this increment. Earlier disposable runtime evidence
  remains scoped to its recorded environment.

### RELEASE-READINESS-001 — consolidation, installation and setup safety, 8 November 2026

- Cherry-picked CI-HYGIENE-001 and DOCS-CORRECTNESS-001 in order. Both progress conflicts were
  resolved by retaining the main release history and appending each workstream's evidence.
- INSTALL-GUIDE-001 makes verified published images the primary operator path. It binds the four
  asset attestations to the approved source commit, separates Linux, Synology, Dockhand and Tailscale
  instructions, and covers explicit upgrades, interrupted operations and fresh-host recovery.
- SETUP-SAFETY-001 keeps the guard and no-clobber copy in one recipe shell. The disposable
  `make test-workflow-helpers` fixture passed for creation, mode preservation, repeated invocations
  and a dangling symlink. `make test-verification-impact` passed all 30 tests, and the feature graph
  validated 141 entries.
- Independent QA matched both picked patches outside progress and checked shell syntax, controller
  arguments and Markdown links. Delta QA passed after fixing the approved-commit attestation check,
  the nginx and standalone Compose notes, restart ordering, and setup file permissions. The release
  block succeeded with disposable stubs and rejected source, attestation and bundle digest errors.
- The consolidated plan requires FULL. `make feature-verify` records the current result and receipt
  in the worktree metadata. The first run's disclosure check rejected a realistic-looking
  Tailscale example. The guide now uses explicit device and tailnet placeholders. Prior receipts
  remain historical evidence. Published-image acceptance and Synology, Dockhand, Tailscale and
  off-host recovery on a real host remain pending.

- Resume audit: PR #155's passing stage journal totals 1,094.02 s, including 572.50 s for
  integration and 364.12 s for quality. Pytest itself took 558.81 s in integration. The
  [verification handoff](verification-fast-001-handoff.md#consolidation-audit-8-november-2026)
  records the breakdown and follow-ups. Integration now logs its 20 slowest phases at or above
  0.1 s using the existing pytest runner. The selected taxonomy migration file passed, printed
  its slow test call and verified disposable cleanup. The planner suite passed 30 tests, and the
  workflow helper suite and 141-feature graph passed. The plan still selects FULL. The final
  consolidation gate and receipt remain pending.
