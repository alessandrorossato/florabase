# Engineering progress

This log preserves meaningful verified milestones and current repository state. Exact acceptance
criteria and current status live in [`features.json`](features.json); Git history retains line-level
implementation detail.

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

- Alembic head: `20260902_0014`.
- Verified product boundary: local owner authentication; botanical identities/profiles; suppliers;
  collection locations; geographic places/material provenance; seed lots; sowings and simple
  germination totals; Plants/PlantGroups; explicit producer/Sowing/extraction lineage; and the
  protected Plant/PlantGroup Event backend journal and detail-page timeline UI.
- `PROPAGATION-001` and `PROPAGATION-002` are verified; the next recommended P1 product increment
  is decided by the machine-readable dependency graph;
  licensing/version policy and release readiness remain explicit later operator/product decisions.
- `CI-001` repository automation is verified through the merged pull-request workflow and protected
  `main` checks.
  Other unblocked P2 product items are listed by the machine-readable dependency graph rather than
  prioritized here.
- Deliberately absent: a collection-wide Event timeline, structured Event payloads beyond movement,
  Event attachments/photos, advanced search, dashboards, import/export, PWA behavior,
  offline/synchronization behavior, generic graphs, and multi-user collaboration.
