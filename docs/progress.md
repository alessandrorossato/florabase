# Engineering progress

This log preserves meaningful verified milestones and current repository state. Exact acceptance
criteria and current status live in [`features.json`](features.json); Git history retains line-level
implementation detail.

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

- Alembic head: `20260909_0021` on the BOTANY-002 implementation branch.
- Verified product boundary: local owner authentication; botanical identities/profiles; suppliers;
  collection locations; geographic places/material provenance; seed lots; sowings and simple
  germination totals; Plants/PlantGroups; explicit producer/Sowing/extraction lineage; and the
  protected Plant/PlantGroup Event journal and timeline UI; atomic extraction history; retained
  transferred Plant/PlantGroup history; scope-aware hierarchical collection Locations; and direct,
  connected-record Supplier summaries.
- `PROPAGATION-001` through `PROPAGATION-003`, `SUPPLIER-002`, `LOCATION-002`, `GEOGRAPHY-003`, and
  `MAP-001` are verified; `BOTANY-002` is implemented pending independent verification. The next
  increment remains decided by the machine-readable dependency graph;
  licensing/version policy and release readiness remain explicit later operator/product decisions.
- `CI-001` repository automation is verified through the merged pull-request workflow and protected
  `main` checks.
  Other unblocked P2 product items are listed by the machine-readable dependency graph rather than
  prioritized here.
- Deliberately absent: Event attachments/photos, advanced search, import/export, PWA behavior,
  offline/synchronization behavior, generic graphs, and multi-user collaboration.
