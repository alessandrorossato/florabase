# Engineering progress

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

- Alembic head: `20261001_0029`; ATTACHMENT-005 and HARVEST-001 are implemented pending visual acceptance.
- Verified product boundary: local owner authentication; botanical identities/profiles; suppliers;
  collection locations; geographic places/material provenance; seed lots; sowings and simple
  germination totals; Plants/PlantGroups; explicit producer/Sowing/extraction lineage; and the
  protected Plant/PlantGroup Event journal and timeline UI; atomic extraction history; retained
  transferred Plant/PlantGroup history; scope-aware hierarchical collection Locations; direct,
  connected-record Supplier summaries; and exact structured BotanicalProfile native ranges over the
  shared GeographicPlace hierarchy; and guarded local still-image attachment storage with
  authenticated retrieval and coordinated database/content backup.
- `PROPAGATION-001` through `PROPAGATION-003`, `SUPPLIER-002`, `BOTANY-002`, and
  `ATTACHMENT-002` are verified. `LOCATION-002`, `GEOGRAPHY-003`, `MAP-001`, `GEOGRAPHY-002`,
  `ATTACHMENT-003`, `IMPORT-001`, `SEARCH-001`, and `UX-002` through `UX-006` are implemented in the
  graph; UX-004, UX-005, and UX-006 have landed on `main`, but their graph status has not been
  promoted to `verified`.
  `PERF-001` is verified on the frozen 0.1.0 scope. The agreed blocking cross-application UI polish
  is awaiting operator visual review before `RELEASE-001` hardening and acceptance; PERF-001's
  measurement report records the remaining costs and review caveats.
  Optional product candidates are not dependencies of either required increment. Licensing,
  version/upgrade policy, and release readiness remain to be resolved in `RELEASE-001`.
- `CI-001` repository automation is verified through the merged pull-request workflow and protected
  `main` checks.
  Other unblocked P2 product items are listed by the machine-readable dependency graph rather than
  prioritized here.
- Deliberately absent: arbitrary derivative pipelines beyond the fixed cached local 320px WebP,
  identity-cover history, automatic or
  provider image discovery, PWA behavior,
  offline/synchronization behavior, generic graphs, and multi-user collaboration.
