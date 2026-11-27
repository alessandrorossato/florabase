# DOCS-005 Phase 1 — Move Map & Design Note

- **Branch**: `docs/docs-005-structure` (fast-forwarded from `7b667a4` to `origin/main` `c83d816` per Phase 1 ruling #0; writer `antigravity-docs-005`)
- **Phase 1 rulings applied (27/11)**: (1) 7 top-level tombstones kept incl. `docs/portable-installation.md` and preserved `CHANGELOG.md` anchors; (2) `mobile-001-adr.md` → `docs/archive/MOBILE-001/`; (3) `development-workflow.md` and `domain-model.md` split, `ui-contract.md` kept whole; (4) `progress.md` rotation rule documented only (no rotation in this diff, `additive_progress()` untouched); (5) `postgres/florabase-postgres-entrypoint.sh` untouched, `schemas.py` + `make api-generate` updated, `release/platform.json` + `.github/dependabot.yml` updated; (6) `docs/review/` → `docs/archive/review/` + 3 living docs + 3 `docs/design/ui-system-v1/` scripts updated.
- **Feature ID**: `DOCS-005` — verified unused across `docs/features.json`, `docs/release/scope-v1.json`, and repo. Register next to `DOCS-001` (line ~58 of `docs/features.json`, line ~9 of `docs/release/scope-v1.json`, class `"best-effort"`) to avoid tail conflicts with Batch 15 branches.
- **Baseline checks**: `check-doc-links.py` (398 docs), `test-doc-links.py` (4 OK), `check-features.py` (204 features valid).
- **Measured agent start-path savings**: Before = `AGENTS.md` (9.7 KB) + `docs/progress.md` (96.5 KB) + `docs/features.json` (252.5 KB) = **358.7 KB (367,342 B)**. Projected After = `AGENTS.md` (≤ 9.7 KB) + `docs/agent-map.md` (~6 KB) + latest milestone (~2 KB) + one `make feature-show` (~0.8 KB) = **~18.5 KB (~95% reduction)**.

## 1. Confirmed Target Tree (with Phase 1 amendments)

```
docs/
  README.md, agent-map.md (≤150 lines), progress.md, features.json
  <7 tombstones>: installation.md, mobile.md, deployment.md, backup-restore.md,
                  security.md, versioning.md, portable-installation.md (stays at root; see Q1)
  user-guide/          unchanged
  operate/             README.md + installation, backup-restore, security, versioning, deployment, mobile, pwa (future: demo-mode)
  develop/             README.md + development, development-workflow (index) + workflow/*, dev-golden, dev-references,
                       dependency-maintenance-baseline, agent-prompt-template, ui-contract (index + ui-contract/* if Q3=yes), themes-001-token-matrix
  architecture/        README.md + architecture, domain-model (index) + domain-model/*, lineage-integrity, geography-data, botanical-matching
  decisions/           ADRs 0001–0011, unchanged path
  features/            README.md + collection/, activity/, explore/, sourcing/, tools/ (each with README.md)
  product/             README.md + product-roadmap
  release/, security/, design/, performance/, assets/   unchanged paths
  archive/
    <FEATURE-ID>/      finished handoffs/designs/audits/evidence (+ MOBILE-001/mobile-001-adr.md; see Q2)
    progress/          rotated progress slices (beta-7-to-beta-9.md); progress-until-beta-7.md stays at existing path (see Q6)
    review/            git mv of docs/review/ (2,651 files / 167 MB; not deleted)
```

**Amendments to brief's proposed tree:** (1) Keep `docs/portable-installation.md` at `docs/` root (it is already a tombstone referenced by released `CHANGELOG.md` L220 & L275 incl. `#isolated-restore`, which must not be rewritten). (2) Place unlisted `docs/mobile-001-adr.md` (spike ADR superseded by ADR 0011) in `docs/archive/MOBILE-001/mobile-001-adr.md` (or `docs/decisions/`, see Q2).

## 2. Full Move Map (all 71 top-level files in `docs/` + `docs/review/`)

| Old path (`docs/...`) | New path (`docs/...`) | Stub | Referenced by (external / code / release-history / internal) |
| --- | --- | --- | --- |
| `README.md` | *(unchanged)* | — | `README.md`, `CHANGELOG.md`, `AGENTS.md`, `scripts/test-verification-impact.py` |
| `features.json` | *(unchanged)* | — | `AGENTS.md`, `CONTRIBUTING.md`, `README.md`, `.github/pull_request_template.md`, `scripts/check-features.py` & tests |
| `progress.md` | *(unchanged; rotated)* | — | `AGENTS.md`, `CHANGELOG.md`, `README.md`, `.github/pull_request_template.md`, `scripts/feature_batch.py` & tests |
| `portable-installation.md` | *(unchanged tombstone)* | kept | `CHANGELOG.md` (released L220, L275 `#isolated-restore`), `docs/README.md`, `docs/archive/DOCS-002/` |
| `installation.md` | `operate/installation.md` | **yes** | `compose.yaml` (L1, L9), `CHANGELOG.md` (released, 3 anchors), `README.md`, `SECURITY.md`, `release_schema.py`, `postgres/florabase-postgres-entrypoint.sh`, `beta_release.py`, `smoke-portable-compose.py`, `test_release_schema.py`, `test-beta-{images,runtime}.py`, 26 docs |
| `backup-restore.md` | `operate/backup-restore.md` | **yes** | `CHANGELOG.md` (released L79), `README.md`, `Makefile` L155, `release/history/`, 5 docs |
| `security.md` | `operate/security.md` | **yes** | `CHANGELOG.md` (released L154 `#optional-container-hardening`), `README.md`, `SECURITY.md`, `decisions/0010`, `release/history/`, 9 docs |
| `versioning.md` | `operate/versioning.md` | **yes** | `CHANGELOG.md` L4, `README.md`, `SECURITY.md`, 2 docs |
| `deployment.md` | `operate/deployment.md` | **yes** | `README.md`, `THIRD-PARTY-NOTICES.md`, `frontend/src/{occurrence,provenance}-map/*.tsx` comments, `release/history/`, 5 docs |
| `mobile.md` | `operate/mobile.md` | **yes** | `frontend/src/mobile/healthProbe.ts` (Android UI error), `Makefile` L634/642, `scripts/mobile-android-release.sh`, `.github/workflows/mobile-android-release.yml`, `scripts/test-beta-runtime.py`, 4 docs |
| `pwa.md` | `operate/pwa.md` | no | `README.md`, 4 docs |
| `development.md` | `develop/development.md` | no | `README.md`, 3 docs |
| `development-workflow.md` | `develop/development-workflow.md` + `develop/workflow/*` | no | `AGENTS.md`, `CONTRIBUTING.md`, `scripts/test-agent-workflow.py` L2785, `release/history/`, 16 docs |
| `dev-golden.md` | `develop/dev-golden.md` | no | `performance/PERF-001.md`, 6 docs |
| `dev-references.md` | `develop/dev-references.md` | no | 3 docs |
| `dependency-maintenance-baseline.md` | `develop/dependency-maintenance-baseline.md` | no | `.github/dependabot.yml` L18, 2 docs |
| `agent-prompt-template.md` | `develop/agent-prompt-template.md` | no | `AGENTS.md` L131, 2 docs |
| `ui-contract.md` | `develop/ui-contract.md` (+ `develop/ui-contract/*`, Q3) | no | `AGENTS.md` L65, `release/history/`, 7 docs |
| `themes-001-token-matrix.md` | `develop/themes-001-token-matrix.md` | no | `frontend/src/styles/tokens.css` L1, 5 docs |
| `architecture.md` | `architecture/architecture.md` | no | `README.md`, `scripts/test-verification-impact.py` (synthetic), 1 doc |
| `domain-model.md` | `architecture/domain-model.md` + `architecture/domain-model/*` | no | `README.md`, `release/history/`, 4 docs |
| `lineage-integrity.md` | `architecture/lineage-integrity.md` | no | `release/history/`, 5 docs |
| `geography-data.md` | `architecture/geography-data.md` | no | `THIRD-PARTY-NOTICES.md` L13, 3 docs |
| `botanical-matching.md` | `architecture/botanical-matching.md` | no | 1 doc |
| `product-roadmap.md` | `product/product-roadmap.md` | no | `README.md`, `release/history/`, 5 docs |
| `cuttings.md` | `features/collection/cuttings.md` | no | 7 docs |
| `harvests.md` | `features/collection/harvests.md` | no | `README.md`, `release/history/`, 5 docs |
| `harvest-inventory.md` | `features/collection/harvest-inventory.md` | no | `release/history/`, 5 docs |
| `harvest-seed-conversion.md` | `features/collection/harvest-seed-conversion.md` | no | `release/history/`, 5 docs |
| `location-descendant-aggregation.md` | `features/collection/location-descendant-aggregation.md` | no | `release/history/`, 3 docs |
| `bulk-operations.md` | `features/collection/bulk-operations.md` | no | 8 docs |
| `labels.md` | `features/collection/labels.md` | no | `release/history/`, 4 docs |
| `measurements.md` | `features/activity/measurements.md` | no | 5 docs |
| `phenology.md` | `features/activity/phenology.md` | no | `backend/src/florabase/events/{model,schemas}.py`, `backend/openapi.json`, `frontend/src/api/schema.d.ts`, `frontend/src/events/{PhenologyHistory.tsx,eventData.ts}`, `release/history/`, 4 docs |
| `operational-history.md` | `features/activity/operational-history.md` | no | `release/history/`, 7 docs |
| `schedule.md` | `features/activity/schedule.md` | no | `scripts/test-verification-impact.py` (synthetic), `release/history/`, 6 docs |
| `collection-taxonomy.md` | `features/explore/collection-taxonomy.md` | no | `THIRD-PARTY-NOTICES.md` L15, `release/history/`, 6 docs |
| `collection-phylogeny.md` | `features/explore/collection-phylogeny.md` | no | 4 docs |
| `lineage-explorer.md` | `features/explore/lineage-explorer.md` | no | `release/history/`, 5 docs |
| `media-library.md` | `features/explore/media-library.md` | no | `README.md`, `release/history/`, 8 docs |
| `species-distribution.md` | `features/explore/species-distribution.md` | no | `THIRD-PARTY-NOTICES.md` L17, 7 docs |
| `native-ranges-explore.md` | `features/explore/native-ranges-explore.md` | no | `THIRD-PARTY-NOTICES.md` L12, `frontend/src/native-ranges/data/NATURAL-EARTH-NOTICE.md`, `release/history/`, 8 docs |
| `native-range-enrichment.md` | `features/explore/native-range-enrichment.md` | no | `THIRD-PARTY-NOTICES.md` L16, 7 docs |
| `botanical-profile-enrichment.md` | `features/explore/botanical-profile-enrichment.md` | no | 2 docs |
| `botanical-profile-enrichment-sources.md` | `features/explore/botanical-profile-enrichment-sources.md` | no | `release/history/`, 6 docs |
| `botanical-knowledge-source-audit.md` | `features/explore/botanical-knowledge-source-audit.md` | no | 4 docs |
| `orders.md` | `features/sourcing/orders.md` | no | `release/history/`, 7 docs |
| `search.md` | `features/tools/search.md` | no | 3 docs |
| `saved-views.md` | `features/tools/saved-views.md` | no | `release/history/`, 5 docs |
| `import-export.md` | `features/tools/import-export.md` | no | `release/history/`, 6 docs |
| `beta-data-001.md` | `archive/BETA-DATA-001/beta-data-001.md` | no | 2 docs |
| `beta-data-001-templates.md` | `archive/BETA-DATA-001/beta-data-001-templates.md` | no | none |
| `beta-distribution-001.md` | `archive/BETA-DISTRIBUTION-001/beta-distribution-001.md` | no | 1 doc |
| `beta-distribution-001-evidence.json` | `archive/BETA-DISTRIBUTION-001/beta-distribution-001-evidence.json` | no | 3 docs |
| `beta-image-001.md` | `archive/BETA-IMAGE-001/beta-image-001.md` | no | `scripts/test-beta-images.py` L2118, 6 docs |
| `beta-image-001-final-reliability.md` | `archive/BETA-IMAGE-001/beta-image-001-final-reliability.md` | no | 5 docs |
| `beta-image-001-local-evidence.json` | `archive/BETA-IMAGE-001/beta-image-001-local-evidence.json` | no | 2 docs |
| `beta-image-001-qa.md` | `archive/BETA-IMAGE-001/beta-image-001-qa.md` | no | 2 docs |
| `beta-image-001-qa-corrections.md` | `archive/BETA-IMAGE-001/beta-image-001-qa-corrections.md` | no | 3 docs |
| `beta-image-001-qa-correction-evidence.json` | `archive/BETA-IMAGE-001/beta-image-001-qa-correction-evidence.json` | no | 1 doc |
| `beta-runtime-001.md` | `archive/BETA-RUNTIME-001/beta-runtime-001.md` | no | 4 docs |
| `beta-runtime-001-evidence.json` | `archive/BETA-RUNTIME-001/beta-runtime-001-evidence.json` | no | 2 docs |
| `beta-runtime-001-qa-handoff.md` | `archive/BETA-RUNTIME-001/beta-runtime-001-qa-handoff.md` | no | none |
| `beta-security-001.md` | `archive/BETA-SECURITY-001/beta-security-001.md` | no | `release/platform.json` L20, 3 docs |
| `beta-security-001-lookup-correction.md` | `archive/BETA-SECURITY-001/beta-security-001-lookup-correction.md` | no | 2 docs |
| `botany-003-audit.md` | `archive/BOTANY-003/botany-003-audit.md` | no | 3 docs (`botanical-profile-enrichment*`, `botany-003-handoff`) |
| `botany-003-handoff.md` | `archive/BOTANY-003/botany-003-handoff.md` | no | 3 docs |
| `mobile-001-adr.md` | `archive/MOBILE-001/mobile-001-adr.md` *(see Q2)* | no | `decisions/0011-mobile-device-sessions.md`, `mobile.md`, `progress.md` |
| `phylogeny-001-handoff.md` | `archive/PHYLOGENY-001/phylogeny-001-handoff.md` | no | `release/history/`, 3 docs |
| `phylogeny-001-source.md` | `archive/PHYLOGENY-001/phylogeny-001-source.md` | no | `release/history/`, 5 docs |
| `test-data-001-design.md` | `archive/TEST-DATA-001/test-data-001-design.md` | no | 3 docs |
| `review/` *(dir, 2,651 files)* | `archive/review/` *(via `git mv`)* | no | See §7 |

*(Note: `docs/release/history/product-roadmap-2026-11-11.md` is checked by `check-doc-links.py`; its relative links to moved docs will be updated link-only per Owner decision 4a so `make doc-links` stays green without adding 20+ tombstones.)*

## 3. Tombstone List (7 files at `docs/` root)

Because `check-doc-links.py` validates `#fragment` anchors in released `CHANGELOG.md` (which must not be rewritten), tombstones with released anchored links keep matching stub headings (same pattern as `portable-installation.md` today):

- `docs/installation.md` → `operate/installation.md` — **External refs**: `compose.yaml` L1/L9 (untouched), released `CHANGELOG.md` (L51, L75, L78, L137, L178, L208), published GitHub release notes (`beta_release.py`), shipped PG/backend images. **Stub headings required**: `## 1. Create the folders and set owners once`, `## Optional botanical reference datasets`, `## Isolated restore`.
- `docs/security.md` → `operate/security.md` — **External refs**: released `CHANGELOG.md` L154, `SECURITY.md`, `README.md`. **Stub heading required**: `## Optional container hardening`.
- `docs/portable-installation.md` → `operate/installation.md` — **Existing tombstone**; **External refs**: released `CHANGELOG.md` L220 & L275 (`#isolated-restore`). Keeps existing headings; links updated to `operate/installation.md`.
- `docs/mobile.md` → `operate/mobile.md` — **External refs**: shipped Android APK (`frontend/src/mobile/healthProbe.ts`), `Makefile`, `.github/workflows/mobile-android-release.yml`, `scripts/mobile-android-release.sh`.
- `docs/backup-restore.md` → `operate/backup-restore.md` — **External refs**: released `CHANGELOG.md` L79, `README.md`, `Makefile` L155.
- `docs/deployment.md` → `operate/deployment.md` — **External refs**: `README.md`, `THIRD-PARTY-NOTICES.md`, map component comments.
- `docs/versioning.md` → `operate/versioning.md` — **External refs**: `CHANGELOG.md` L4, `README.md`, `SECURITY.md`.

## 4. Non-`docs/` Files to Edit (full `git grep docs/` audit)

- **Root & CI**: `AGENTS.md` (step 4 + agent-map + moved paths, ≤ 135 lines), `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `THIRD-PARTY-NOTICES.md`, `CHANGELOG.md` (header L4 + Unreleased only; released sections untouched), `Makefile` (L155, L634, L642 + new `feature-show` / `feature-list` targets), `.github/dependabot.yml` L18, `.github/workflows/mobile-android-release.yml` L98. *(Untouched: `compose.yaml`, `.github/pull_request_template.md`.)*
- **Backend**: `backend/src/florabase/db/release_schema.py` (L215, 222, 326, 333), `backend/tests/test_release_schema.py` (L561, 672), `backend/src/florabase/events/model.py` (L68). *(Conditional on Q4: `backend/src/florabase/events/schemas.py` L79 → `make api-generate` updating `backend/openapi.json` & `frontend/src/api/schema.d.ts`.)*
- **Frontend**: `frontend/src/mobile/healthProbe.ts` L129, `frontend/src/events/{PhenologyHistory.tsx,eventData.ts}`, `frontend/src/{occurrence-map/OccurrenceDensityMap.tsx,provenance-map/ProvenanceMap.tsx}`, `frontend/src/native-ranges/data/NATURAL-EARTH-NOTICE.md` L9, `frontend/src/styles/tokens.css` L1.
- **Postgres & Release metadata**: `release/platform.json` L20 (`beta-security-001.md` → archive). *(Conditional on Q4: `postgres/florabase-postgres-entrypoint.sh` L32/41/48/52/54/78.)*
- **Scripts & Tests**: `scripts/check-doc-links.py` + `scripts/test-doc-links.py` (Part 3 drift checks + tests), `scripts/check-features.py` + `scripts/test-check-features.py` (`--show` / `--list` helpers + tests), `scripts/beta_release.py` L1150, `scripts/mobile-android-release.sh` L42/53/61, `scripts/smoke-portable-compose.py` L562/584/586/604/772, `scripts/test-agent-workflow.py` L2785 (read `docs/develop/development-workflow.md` + `workflow/*.md`), `scripts/test-beta-images.py` L1476 & L2118, `scripts/test-beta-runtime.py` L346/435/630, `scripts/test-verification-impact.py` (new subfolder + `docs/archive/review/` `.py`/`.cjs`/`compose.yaml` cases). *(`scripts/verification-impact.json` needs NO change: `documentation_prefixes: ["docs/"]` + `documentation_suffixes` already classifies new subfolders docs-only and keeps `.py`/`.cjs`/`.yaml` under `docs/archive/review/` at FULL.)*
- **Design helper scripts**: `docs/design/ui-system-v1/{build-data.py,serve.py,wave1/validate.py}` (5 path refs from `docs/review/` → `docs/archive/review/`, see Q7).

## 5. `docs/progress.md` Rotation & Affected Parsers

- **Cut point**: Last published tag is `v0.1.0-beta.9` (`docs/progress.md` L585 `## 2026-11-24 — v0.1.0-beta.9 release preparation`). Keep L1–597 (23 milestones, ~48 KB, from `v0.1.0-beta.9` onward) in `docs/progress.md`; move L598–1227 (25 milestones, Batch 12 back to `v0.1.0-beta.7`, ~50 KB) verbatim to `docs/archive/progress/beta-7-to-beta-9.md`. Link both `archive/progress/beta-7-to-beta-9.md` and existing `archive/progress-until-beta-7.md` from a one-line archive notice under `# Engineering progress` (and at the bottom). Document the per-beta rotation rule in `docs/develop/workflow/verification-and-gates.md`.
- **Parsers affected**: Only `scripts/feature_batch.py` (`additive_progress()`, L264–301) parses `docs/progress.md` (`check-features.py` does not). **Critical finding**: `additive_progress()` handles a tail-truncated `ours` when `theirs` is a pure top prepend (via 3-line `anchor` match), **but fails if `theirs` has the truncated tail**. Therefore in Batch 15, **`DOCS-005` must merge first** (or we generalize `additive_progress()` symmetrically — see Q5).

## 6. Giant-Guide Split Plans (all moved text verbatim)

**`development-workflow.md` (80.8 KB → `docs/develop/development-workflow.md` ~3 KB index keeping all `##` anchors + 6 files under `docs/develop/workflow/`):**

| New file (`docs/develop/workflow/...`) | Sections moved verbatim | Size |
| --- | --- | --- |
| `worktrees-and-agents.md` | Preamble (L1–41) + `## Feature worktrees and agents` (incl. `### Worktrees provided by an agent tool`, delivery & retirement, L42–224) | 18.7 KB |
| `environments.md` | `## Configuration`, `## DEV` (incl. Golden DEV), `## Operator environments`, `## Development runtime identity and dependencies`, `## Sourcing Preview`, `## Stable Preview`, `## Integration and production` | 12.6 KB |
| `review-and-uat.md` | `## UAT Preview and operator acceptance`, `## UAT instances (parallel, per worktree)`, `## Feature Review and browser acceptance` | 21.4 KB |
| `verification-and-gates.md` | `## Review profiles and verification timing` (incl. `### Documentation and review-artifact placement` + new progress rotation rule, `### Quality and Docker resources`) | 21.3 KB |
| `batches.md` | `## Batch integration (WF-04)` | 4.4 KB |
| `troubleshooting.md` | `## Troubleshooting and acceptance evidence` | 2.3 KB |

**`domain-model.md` (75.6 KB → YES, split into `docs/architecture/domain-model.md` index + 4 files under `docs/architecture/domain-model/`):**
- `reference-concepts.md` (24.4 KB): `## Reference concepts` (L10–350)
- `collection-concepts.md` (21.5 KB): `## Collection concepts` (L351–642; owns `#vegetative-propagation` & `#event`)
- `ia-lineage-and-attachments.md` (15.0 KB): `## Collection information architecture`, `## Explicit lineage`, `## Attachment storage contract`, `## Ownership and mutation boundary` (L643–855)
- `operations-and-deferred.md` (14.3 KB): `## Deferred capabilities`, `## Global search coverage`, `## Saved operator views`, `## Safe explicit bulk Location moves`, `## Scheduled collection activities` (L856–1047)

**`ui-contract.md` (48.1 KB → Recommend YES, split into `docs/develop/ui-contract.md` index + 3 files under `docs/develop/ui-contract/`, see Q3):**
- `foundation.md` (11.6 KB): `## Direction` through `## Do / don't` (L12–182)
- `page-normalization.md` (24.0 KB): `## Activity recording...` through `## Harvest and Location normalization candidate` (L183–493)
- `ui-system-v1-waves.md` (11.6 KB): `## UI System v1 — approved Gate B and production Wave 1` (L494–650)

## 7. `docs/review/` Live References (moving via `git mv` to `docs/archive/review/`)

- **Living Markdown links (3 files)**: `docs/development-workflow.md` L575 (`extended-botanical-dataset-v5.md`), `docs/native-ranges-explore.md` L206 (`maps-foundation-001/spatial/README.md`), `docs/design/ui-system-v1/component-contracts.md` (2 links to `release-visual-audit-001/component-inventory.md`).
- **Design Python scripts (3 files)**: `docs/design/ui-system-v1/{build-data.py,serve.py,wave1/validate.py}` read `docs/review/release-visual-audit-001/{capture-index,component-consumers}.json`.
- **Living prose mentions**: `docs/README.md` L106, `docs/development-workflow.md` L720, `docs/design/florabase-next/m8-extended-review-environment.md` L12; historical prose in `docs/decisions/0008` L30 and `docs/release/{evidence/certify/*,evidence/g-ux-pre-rc.md,evidence/ref-setup-001-design.md,restatements-v1.md}` (leave historical evidence prose verbatim).
- **Archive links**: 20 files under `docs/archive/` (142 links) — update relative `../../review/` → `../review/` (and `../review/` → `review/` in `progress-until-beta-7.md`).
- **Tests**: `scripts/test-verification-impact.py` (keep coverage for `docs/archive/review/` `.py`/`.cjs`/`compose.yaml`).

## 8. Batch-15 Parallel-Branch Conflict Map & Commit Strategy

Commit 1 = **pure `git mv` only** (zero content edits, maximizing Git rename detection). Subsequent commit(s) = splits, link/path updates, indexes, `agent-map.md`, `AGENTS.md`, `feature-show`, drift checks. Paths other Batch-15 branches (`UI-POLISH-006`, `UAT-INSTANCE-002`, `MOBILE-004`, `DEMO-001` realign) will touch:
- `docs/progress.md` (all 4 branches — merge `DOCS-005` first per §5!)
- `docs/features.json` & `docs/release/scope-v1.json` (all 4 branches — mitigated by inserting `DOCS-005` after `DOCS-001`, away from tail)
- `docs/README.md` (any branch adding a doc — e.g. `DEMO-001` adding `demo-mode.md` → should land in `docs/operate/demo-mode.md` + `docs/operate/README.md`)
- `docs/mobile.md` → `docs/operate/mobile.md` (`MOBILE-004`; `git mv` commit lets Git follow renames)
- `docs/development-workflow.md` → `docs/develop/workflow/review-and-uat.md` (`UAT-INSTANCE-002` edits `## UAT instances`)
- `docs/ui-contract.md` (if `UI-POLISH-006` updates it; see Q3)
- `backend/openapi.json` & `frontend/src/api/schema.d.ts` (only if Q4 updates `events/schemas.py` docstring)

## 9. Open Questions for Alessandro / Claude Rulings

1. **`docs/portable-installation.md`**: Keep at `docs/` root as one of the 7 allowed tombstones (recommended; preserves released `CHANGELOG.md` L220 & L275)?
2. **`docs/mobile-001-adr.md`**: Move to `docs/archive/MOBILE-001/mobile-001-adr.md` (recommended) or `docs/decisions/`?
3. **Giant-doc splits**: Confirm splitting `domain-model.md` (75.6 KB → 4 files) and `ui-contract.md` (48.1 KB → 3 files), or keep `ui-contract.md` single (48.1 KB, warning only) to reduce `UI-POLISH-006` friction?
4. **Shipped image & OpenAPI docstrings**: Update `postgres/florabase-postgres-entrypoint.sh` (`docs/installation.md` → `docs/operate/installation.md`) and `backend/src/florabase/events/schemas.py` (`docs/phenology.md` → `docs/features/activity/phenology.md` + `make api-generate`), or keep `postgres/` untouched (valid via tombstone) and defer `events/schemas.py` docstring to avoid OpenAPI diff in Batch 15? *(Recommended: update `release_schema.py` + scripts/frontend now; leave `postgres/` on the tombstone so the built PG `.6` image isn't invalidated, and confirm whether to update `events/schemas.py`.)*
5. **Batch-15 `progress.md` rotation**: Merge `DOCS-005` first in Batch 15 (keeps `feature_batch.py` untouched) or also make `additive_progress()` symmetric? And confirm cut point at L597 (keep `v0.1.0-beta.9` prep onward, 23 milestones) vs L584 (strictly post-beta.9, 22 milestones).
6. **`docs/archive/progress-until-beta-7.md`**: Keep at its existing path (recommended; preserves `DOCS-002` archive links) while placing new rotations in `docs/archive/progress/`?
7. **`docs/design/ui-system-v1/*.py`**: Update the 5 `docs/review/` paths in `build-data.py`, `serve.py`, `wave1/validate.py` to `docs/archive/review/`? *(Recommended: yes.)*
