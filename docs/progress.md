# Engineering progress

This log preserves meaningful verified milestones and current repository state. Exact acceptance
criteria and current status live in [`features.json`](features.json); Git history retains line-level
implementation detail.

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

- Alembic head: `20260901_0013`.
- Verified product boundary: local owner authentication; botanical identities/profiles; suppliers;
  collection locations; geographic places/material provenance; seed lots; sowings and simple
  germination totals; Plants/PlantGroups; explicit producer/Sowing/extraction lineage.
- Next dependency-unblocked P1 product contract: `EVENT-001`.
- `CI-001` repository automation is verified through the merged pull-request workflow and protected
  `main` checks.
  Other unblocked P2 product items are listed by the machine-readable dependency graph rather than
  prioritized here.
- Deliberately absent: Plant events, attachments/photos, advanced search, dashboards, import/export,
  PWA behavior, offline/synchronization behavior, generic graphs, and multi-user collaboration.
