# Florabase documentation

Living guides and reference documents live at the top level of `docs/`. Finished per-increment
handoffs, design notes, reviews and evidence are archived under [`archive/`](archive/).

## Install & operate

- [Install Florabase](installation.md) — self-hosting with the single `compose.yaml`, upgrades,
  reverse proxy, backup and restore
- [Backup and restore](backup-restore.md) — paired PostgreSQL and attachment-volume backup/restore
- [Security baseline](security.md) — authentication, sessions, CSRF, network isolation and optional
  hardened container override
- [Public read-only demo mode](demo-mode.md) — opt-in `FLORABASE_DEMO_READONLY` showcase mode,
  `FLORABASE_WORKERS`, and interactive guided tour
- [Versioning and compatibility](versioning.md) — beta, release-candidate and v1.x support policy
- [Portable installation (v0.1.0-beta.6 tombstone)](portable-installation.md) — redirect from the
  retired `v0.1.0-beta.6` portable procedure to `installation.md`
- [Third-party notices and data sources](../THIRD-PARTY-NOTICES.md) — bundled assets, operator
  reference snapshots and optional runtime providers

## Develop

- [Development guide](development.md) — local setup, focused checks, migrations, OpenAPI generation
  and Git practices
- [Development, review, preview and production workflow](development-workflow.md) — worktrees,
  writer claims, Review/UAT/Preview environments, canonical verification and delivery
- [Source-build deployment and upgrades](deployment.md) — development-only source builds
- [Persistent Golden DEV](dev-golden.md) — deterministic Golden dataset management for DEV
- [DEV reference indexes](dev-references.md) — provisioning local WFO and WCVP snapshots for DEV
- [Dependency maintenance baseline](dependency-maintenance-baseline.md) — dependency deferral and
  reopening policy referenced by `.github/dependabot.yml`
- [UI Foundation v0.1 contract](ui-contract.md) and [six-variant token matrix](themes-001-token-matrix.md)
- [Engineering progress](progress.md) — recent milestones (`v0.1.0-beta.7` onward)
- [Feature backlog](features.json) — machine-readable feature graph and statuses
- [Contributing](../CONTRIBUTING.md), [Agent guide](../AGENTS.md), and
  [Agent prompt template](agent-prompt-template.md)

## Architecture & domain

- [Architecture](architecture.md) — modular monolith structure, API and infrastructure boundaries
- [Domain model](domain-model.md) — entities, invariants and botanical vs collection separation
- [Lineage integrity](lineage-integrity.md) — canonical concrete-edge contract and reversal
  invariants
- [Canonical geography data](geography-data.md) — Unicode CLDR territory seed data and licensing
- [Botanical reference matching](botanical-matching.md) — matching and normalization foundation
- [Product roadmap](product-roadmap.md) — post-v1.0.0 themes and scope boundaries

## Feature guides

- **Collection**: [Cuttings](cuttings.md), [Harvests](harvests.md),
  [Stored harvested material](harvest-inventory.md),
  [Harvest-to-seed-lot conversion](harvest-seed-conversion.md),
  [Location descendant aggregation](location-descendant-aggregation.md),
  [Bulk operations](bulk-operations.md)
- **Activity**: [Measurements](measurements.md), [Phenology](phenology.md),
  [Operational history](operational-history.md), [Schedule & Calendar](schedule.md)
- **Explore**: [Collection taxonomy](collection-taxonomy.md),
  [Lineage explorer](lineage-explorer.md), [Shared media library](media-library.md),
  [Species distribution](species-distribution.md), [Native ranges](native-ranges-explore.md),
  [Native-range enrichment](native-range-enrichment.md)
- **Sourcing**: [Purchase orders](orders.md)
- **Tools & Settings**: [Global search](search.md), [Saved views](saved-views.md),
  [Physical labels & QR lookup](labels.md), [Guided CSV import / export](import-export.md),
  [Installable web app (PWA)](pwa.md)

## Release

- [v1.0.0 release scope](release/scope-v1.md) and [scope manifest](release/scope-v1.json)
- [Feature reconciliation against v1.0.0](release/feature-reconciliation-v1.md)
- [Release acceptance checklist](release/acceptance-v1.md) and
  [page inventory](release/page-inventory-v1.md)
- [Release target schema follow-up](release/release-target-schema-followup.md),
  [restatements](release/restatements-v1.md), [REL-01 tooling](release/rel-01-tooling.md), and
  [scope handoff](release/scope-v1-handoff.md)
- Active `in_progress` beta-release and golden-dataset working documents remain at the top level of
  `docs/` until their features finish (`beta-data-001*`, `beta-distribution-001*`,
  `beta-image-001*`, `beta-runtime-001*`, `beta-security-001*`, `test-data-001-design.md`), along
  with `planned` source-audit documents (`botany-003*`, `botanical-profile-enrichment*`,
  `botanical-knowledge-source-audit.md`, `collection-phylogeny.md`, `phylogeny-001*`).
- `docs/security/` holds security workbooks and prototypes for active beta security tracks.
- `docs/performance/` holds `PERF-001` benchmark methodology and measurements.

## Decisions (ADRs)

- [0001 — Modular monolith](decisions/0001-modular-monolith.md)
- [0002 — PostgreSQL](decisions/0002-postgresql.md)
- [0003 — REST and OpenAPI](decisions/0003-rest-openapi.md)
- [0004 — Identifier strategy](decisions/0004-identifier-strategy.md)
- [0005 — Authentication and sessions](decisions/0005-authentication-and-sessions.md)
- [0006 — Local attachment storage](decisions/0006-local-attachment-storage.md)
- [0007 — Accepted-name reconciliation](decisions/0007-accepted-name-reconciliation.md)
- [0008 — Self-initializing single Compose](decisions/0008-self-initializing-single-compose.md)
- [0009 — Minimal production Compose](decisions/0009-minimal-production-compose.md)
- [0010 — Deployable `:latest` Compose](decisions/0010-deployable-latest-compose.md)

## Archive & historical evidence

- [`archive/`](archive/) — per-increment handoffs, design notes, audits, reviews and evidence JSON
  for `implemented` and `verified` features (`docs/archive/<FEATURE-ID>/`).
- [Engineering progress until v0.1.0-beta.7](archive/progress-until-beta-7.md) — verbatim historical
  milestones prior to `v0.1.0-beta.7`.
- `docs/review/` — **historical evidence**: visual-review captures, audit notes and review fixtures
  from completed increments. Going forward, review screenshots and visual-audit captures are not
  committed to the repository; only curated images under `docs/assets/` are committed.
- `docs/release/evidence/` — **historical evidence**: batch integration manifests, certification
  dossiers and beta publication records.
- `docs/design/` — historical UI design explorations and Gate A/B design-system records.
