# Florabase agent reading map

Start every task with [`AGENTS.md`](../AGENTS.md), read **only the top milestone** of [`progress.md`](progress.md), inspect only the feature IDs you touch via `make feature-show ID=<ID>` (or `ID=<prefix>`), then open **only the one or two sections below** that match your task.

| If your task is … | Read these exact sections (not whole folders) |
| --- | --- |
| **New Alembic migration / DB schema change** | [development.md §Database migrations](develop/development.md#database-migrations), [architecture.md](architecture/architecture.md), [ADR 0002](decisions/0002-postgresql.md), [ADR 0004](decisions/0004-identifier-strategy.md), [ADR 0008](decisions/0008-self-initializing-single-compose.md) |
| **New API endpoint / OpenAPI contract change** | [ADR 0003](decisions/0003-rest-openapi.md), [development.md §API contracts](develop/development.md#api-contracts), [architecture.md](architecture/architecture.md) |
| **New UI page / Collection record page** | [ui-contract.md §Page archetypes](develop/ui-contract.md#page-archetypes), [ui-contract.md §UI System v1](develop/ui-contract.md#ui-system-v1--approved-gate-b-and-production-wave-1), [Gate B implementation](design/ui-system-v1/gate-b/implementation.md) |
| **UI theme / CSS tokens** | [themes-001-token-matrix.md](develop/themes-001-token-matrix.md), [ui-contract.md §Semantic colors](develop/ui-contract.md#semantic-colors) |
| **Worktree, writer claim, handoff, delivery, retirement** | [workflow/worktrees-and-agents.md §Feature worktrees and agents](develop/workflow/worktrees-and-agents.md#feature-worktrees-and-agents), [§Worktrees provided by an agent tool](develop/workflow/worktrees-and-agents.md#worktrees-provided-by-an-agent-tool), [agent-prompt-template.md](develop/agent-prompt-template.md) |
| **Verification tier, review profile, gates, Quality Docker** | [workflow/verification-and-gates.md §Review profiles and verification timing](develop/workflow/verification-and-gates.md#review-profiles-and-verification-timing), [§Quality and Docker resources](develop/workflow/verification-and-gates.md#quality-and-docker-resources) |
| **Batch integration (WF-04)** | [workflow/batches.md §Batch integration (WF-04)](develop/workflow/batches.md#batch-integration-wf-04) |
| **UAT instance / Feature Review / browser QA** | [workflow/review-and-uat.md §UAT instances (parallel, per worktree)](develop/workflow/review-and-uat.md#uat-instances-parallel-per-worktree), [§Feature Review and browser acceptance](develop/workflow/review-and-uat.md#feature-review-and-browser-acceptance) |
| **DEV / Golden DEV / Stable or Sourcing Preview** | [workflow/environments.md §DEV](develop/workflow/environments.md#dev), [dev-golden.md](develop/dev-golden.md), [workflow/environments.md §Sourcing Preview](develop/workflow/environments.md#sourcing-preview) |
| **Release / beta prep / versioning / production Compose** | [operate/versioning.md](operate/versioning.md), [operate/installation.md](operate/installation.md), [ADR 0009](decisions/0009-minimal-production-compose.md), [ADR 0010](decisions/0010-deployable-latest-compose.md), [release/scope-v1.md](release/scope-v1.md), [release/release-target-schema-followup.md](release/release-target-schema-followup.md) |
| **Backup, restore, or source-build deployment** | [operate/backup-restore.md](operate/backup-restore.md), [operate/deployment.md](operate/deployment.md) |
| **Mobile (Capacitor Android, APK signing, Obtainium)** | [operate/mobile.md](operate/mobile.md), [ADR 0011](decisions/0011-mobile-device-sessions.md), [operate/pwa.md](operate/pwa.md) |
| **Import / Export (CSV, XLSX wizard)** | [features/tools/import-export.md](features/tools/import-export.md) |
| **Reference data (WFO, WCVP, GBIF, CLDR, Natural Earth)** | [develop/dev-references.md](develop/dev-references.md), [architecture/botanical-matching.md](architecture/botanical-matching.md), [architecture/geography-data.md](architecture/geography-data.md), [ADR 0007](decisions/0007-accepted-name-reconciliation.md) |
| **Security-sensitive change (auth, sessions, CSRF, containers)** | [operate/security.md](operate/security.md), [ADR 0005](decisions/0005-authentication-and-sessions.md), [ADR 0011](decisions/0011-mobile-device-sessions.md), [ADR 0006](decisions/0006-local-attachment-storage.md) |
| **Domain model — Reference concepts (identities, locations, suppliers)** | [domain-model/reference-concepts.md](architecture/domain-model/reference-concepts.md) |
| **Domain model — Collection & propagation (SeedLot, Sowing, Plant, Event)** | [domain-model/collection-concepts.md](architecture/domain-model/collection-concepts.md), [architecture/lineage-integrity.md](architecture/lineage-integrity.md) |
| **Domain model — IA, lineage, attachments, ownership** | [domain-model/ia-lineage-and-attachments.md](architecture/domain-model/ia-lineage-and-attachments.md) |
| **Domain model — Operations (harvests, search, views, bulk, orders, schedule)** | [domain-model/operations-and-deferred.md](architecture/domain-model/operations-and-deferred.md) |
| **Collection features (cuttings, harvests, bulk moves, labels, locations)** | [features/collection/README.md](features/collection/README.md) |
| **Activity features (measurements, phenology, history, schedule)** | [features/activity/README.md](features/activity/README.md) |
| **Explore features (taxonomy, phylogeny, lineage, media, maps, ranges)** | [features/explore/README.md](features/explore/README.md) |
| **Sourcing & Tools features (orders, search, saved views, import/export)** | [features/sourcing/README.md](features/sourcing/README.md), [features/tools/README.md](features/tools/README.md) |
| **Dependencies / lockfiles / Dependabot** | [develop/dependency-maintenance-baseline.md](develop/dependency-maintenance-baseline.md) |
| **Docs-only change / adding a guide / archiving an increment** | [workflow/verification-and-gates.md §Documentation and review-artifact placement](develop/workflow/verification-and-gates.md#documentation-and-review-artifact-placement), [docs/README.md](README.md) |
| **Workflow troubleshooting** | [workflow/troubleshooting.md](develop/workflow/troubleshooting.md) |

## Quick lookup commands

- `make feature-show ID=MOBILE-004` — print one feature entry from `docs/features.json` plus its release class from `docs/release/scope-v1.json`.
- `make feature-show ID=MOBILE-` — print every feature matching a prefix.
- `make feature-list STATUS=in_progress` — list feature IDs, statuses, and release classes (omit `STATUS=` for all).
- `make doc-links` — verify all relative Markdown links, top-level `docs/` rules, folder index coverage, summaries, and tombstones.
