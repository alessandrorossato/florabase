# DOCS-002 — Root community docs, licensing notices and `docs/` tidy-up handoff

- **Branch**: `docs/docs-001` (base `origin/main` `c4ffd63`, `v0.1.0-beta.8`)
- **Writer**: `neon-docs-001`
- **Feature ID note**: `DOCS-001` already exists in [`docs/features.json`](../../features.json) as
  a verified `baseline` entry (`Audit repository consistency and public-repository readiness`,
  depended on by `CI-001`). This increment therefore uses the next free identifier **`DOCS-002`**
  in [`docs/features.json`](../../features.json) and
  [`docs/release/scope-v1.json`](../../release/scope-v1.json) (proposed release class:
  `best-effort`).
- **Licence decision preserved**: `AGPL-3.0-or-later`; inbound contributions use DCO
  (`Signed-off-by` via `git commit -s`), no CLA, no separate `CODE_OF_CONDUCT.md`. Root `LICENSE`
  text is untouched. No beta.7/beta.8 version surfaces or CHANGELOG release headings were modified.

## Summary of changes

### Part A — Root community & licensing documents
- [`README.md`](../../../README.md): rewrote "What works today" in 15 bullets using UI navigation
  names from `frontend/src/shell/navigation.ts` (keeping every existing guide link), folded the
  Docker Compose merge rules link into Requirements, shortened self-hosting to 3 sentences pointing
  to `docs/installation.md`, updated visibility wording to "public pre-release (beta) series"
  (verified public GitHub repo and public anonymous GHCR manifest pull), added `Copyright (C) 2026
  Alessandro Rossato`, `THIRD-PARTY-NOTICES.md` and `docs/README.md` links.
- [`CONTRIBUTING.md`](../../../CONTRIBUTING.md): added "Contributing as an external contributor"
  above the preserved "Maintainer and agent workflow".
- [`.github/pull_request_template.md`](../../../.github/pull_request_template.md): added a DCO
  sign-off checkbox.
- [`SECURITY.md`](../../../SECURITY.md): updated Supported versions to state best-effort fixes on
  `main` for the latest published beta (older betas unsupported), retaining the 1.x row and GitHub
  private vulnerability reporting as the sole channel.
- [`backend/pyproject.toml`](../../../backend/pyproject.toml) and
  [`frontend/package.json`](../../../frontend/package.json): added `Alessandro Rossato` author
  metadata without changing dependency pins or lockfiles.
- [`THIRD-PARTY-NOTICES.md`](../../../THIRD-PARTY-NOTICES.md): new root notice table covering
  bundled fonts (OFL-1.1), `qrcode-generator` (MIT), Natural Earth (Public Domain), Unicode CLDR
  (Unicode-3.0), UI Lab/Review fixture photos (CC0/CC BY), operator-installed WFO (CC0) and Kew
  WCVP (CC BY 3.0), on-demand GBIF (per-dataset), optional OSM tiles (ODbL), and software
  dependency compatibility.

### Part B — `docs/` structure, links, `progress.md` split, and conventions
- [`docs/README.md`](../../README.md): new documentation index grouped into Install & operate,
  Develop, Architecture & domain, Feature guides, Release, Decisions (ADRs), and Archive &
  historical evidence (marking `docs/review/` and `docs/release/evidence/` as historical evidence).
- Archived **72** root-level increment artefacts of `implemented` / `verified` features via
  `git mv` into `docs/archive/<FEATURE-ID>/` (full table below). Living guides, `planned` /
  `in_progress` feature docs, and script/code-referenced paths (`docs/beta-image-001.md`,
  `docs/themes-001-token-matrix.md`, `docs/dependency-maintenance-baseline.md`) stayed in place.
- Updated **367** relative Markdown links across 95 Markdown files (362 via automated rename pass +
  5 backtick-label links + 1 `progress.md` anchor in `docs/phylogeny-001-handoff.md`) plus
  `docs/features.json` (`VERIFY-SPEED-001`).
- Split [`docs/progress.md`](../../progress.md) verbatim at `v0.1.0-beta.7`: kept the 15 milestones
  from `v0.1.0-beta.7` onward (plus this `DOCS-002` entry) newest-first in `docs/progress.md`, and
  moved the 293 earlier milestones verbatim, newest-first, to
  [`docs/archive/progress-until-beta-7.md`](../progress-until-beta-7.md) (updating 246 relative
  links for the `archive/` depth and redacting one legacy personal home path at line 7553 flagged by
  `scripts/test-beta-runtime.py`).
- Updated [`AGENTS.md`](../../../AGENTS.md) and
  [`docs/development-workflow.md`](../../develop/development-workflow.md) with ongoing documentation
  placement and no-committed-review-screenshot rules.
- Wired `doc-links` (`python3 ./scripts/check-doc-links.py`) into `make check` in
  [`Makefile`](../../../Makefile).

### Part C — Cheap doc-only verification & local licence check
- [`scripts/verification-impact.json`](../../../scripts/verification-impact.json): added
  `SECURITY.md`, `CHANGELOG.md`, `THIRD-PARTY-NOTICES.md`, and `LICENSE` to `documentation_paths`
  and removed `LICENSE` from `full_prefixes`.
- [`scripts/test-verification-impact.py`](../../../scripts/test-verification-impact.py): updated
  docs-only, full-escalation, `make check`, and release-rehearsal tests accordingly.
- Added local `make license-check` ([`scripts/license_check.py`](../../../scripts/license_check.py)
  and [`scripts/license_check_npm.mjs`](../../../scripts/license_check_npm.mjs); no CI job added).

## Complete list of moved files (72 files, `old → new`)

| Old path | New path |
| --- | --- |
| `docs/activity-family-refinement-handoff.md` | `docs/archive/ACTIVITY-001/activity-family-refinement-handoff.md` |
| `docs/journal-history-product-pass-handoff.md` | `docs/archive/ACTIVITY-001/journal-history-product-pass-handoff.md` |
| `docs/agent-workflow-001-handoff.md` | `docs/archive/AGENT-WORKFLOW-001/agent-workflow-001-handoff.md` |
| `docs/attachment-004-review.md` | `docs/archive/ATTACHMENT-004/attachment-004-review.md` |
| `docs/beta-foundation-001.md` | `docs/archive/BETA-FOUNDATION-001/beta-foundation-001.md` |
| `docs/beta-foundation-001-qa.md` | `docs/archive/BETA-FOUNDATION-001/beta-foundation-001-qa.md` |
| `docs/beta-foundation-001-qa-corrections.md` | `docs/archive/BETA-FOUNDATION-001/beta-foundation-001-qa-corrections.md` |
| `docs/botanical-identities-visual-001-handoff.md` | `docs/archive/BOTANICAL-IDENTITIES-VISUAL-001/botanical-identities-visual-001-handoff.md` |
| `docs/bulk-001-handoff.md` | `docs/archive/BULK-001/bulk-001-handoff.md` |
| `docs/ci-003-full-migration-cycle-repair-evidence.json` | `docs/archive/CI-003/ci-003-full-migration-cycle-repair-evidence.json` |
| `docs/ci-003-full-migration-cycle-repair-handoff.md` | `docs/archive/CI-003/ci-003-full-migration-cycle-repair-handoff.md` |
| `docs/ci-003-resource-impact-evidence.json` | `docs/archive/CI-003/ci-003-resource-impact-evidence.json` |
| `docs/ci-003-resource-impact-handoff.md` | `docs/archive/CI-003/ci-003-resource-impact-handoff.md` |
| `docs/ci-004-verification-efficiency-evidence.json` | `docs/archive/CI-004/ci-004-verification-efficiency-evidence.json` |
| `docs/ci-004-verification-efficiency-handoff.md` | `docs/archive/CI-004/ci-004-verification-efficiency-handoff.md` |
| `docs/collection-visual-001-handoff.md` | `docs/archive/COLLECTION-VISUAL-001/collection-visual-001-handoff.md` |
| `docs/collection-visual-002-handoff.md` | `docs/archive/COLLECTION-VISUAL-002/collection-visual-002-handoff.md` |
| `docs/controls-001-design-contract.md` | `docs/archive/CONTROLS-001/controls-001-design-contract.md` |
| `docs/controls-001-handoff.md` | `docs/archive/CONTROLS-001/controls-001-handoff.md` |
| `docs/cutting-001-design.md` | `docs/archive/CUTTING-001/cutting-001-design.md` |
| `docs/dashboard-001-audit.md` | `docs/archive/DASHBOARD-001/dashboard-001-audit.md` |
| `docs/dashboard-001-handoff.md` | `docs/archive/DASHBOARD-001/dashboard-001-handoff.md` |
| `docs/dependency-maintenance-frontend-lint-format-handoff.md` | `docs/archive/DEPENDENCY-MAINTENANCE/dependency-maintenance-frontend-lint-format-handoff.md` |
| `docs/dependency-maintenance-frontend-low-risk-handoff.md` | `docs/archive/DEPENDENCY-MAINTENANCE/dependency-maintenance-frontend-low-risk-handoff.md` |
| `docs/enrichment-001-handoff.md` | `docs/archive/ENRICHMENT-001/enrichment-001-handoff.md` |
| `docs/native-range-enrichment-audit.md` | `docs/archive/ENRICHMENT-001/native-range-enrichment-audit.md` |
| `docs/native-range-enrichment-source-v15.md` | `docs/archive/ENRICHMENT-001/native-range-enrichment-source-v15.md` |
| `docs/explore-001-handoff.md` | `docs/archive/EXPLORE-001/explore-001-handoff.md` |
| `docs/explore-002-handoff.md` | `docs/archive/EXPLORE-002/explore-002-handoff.md` |
| `docs/geography-breadcrumb-audit.md` | `docs/archive/GEOGRAPHY-VISUAL-001/geography-breadcrumb-audit.md` |
| `docs/geography-visual-001-handoff.md` | `docs/archive/GEOGRAPHY-VISUAL-001/geography-visual-001-handoff.md` |
| `docs/global-visual-001-handoff.md` | `docs/archive/GLOBAL-VISUAL-001/global-visual-001-handoff.md` |
| `docs/harvest-003-handoff.md` | `docs/archive/HARVEST-003/harvest-003-handoff.md` |
| `docs/history-001-handoff.md` | `docs/archive/HISTORY-001/history-001-handoff.md` |
| `docs/labels-navigation-ia-handoff.md` | `docs/archive/IA-FREEZE-001/labels-navigation-ia-handoff.md` |
| `docs/infra-maint-001-evidence.json` | `docs/archive/INFRA-MAINT-001/infra-maint-001-evidence.json` |
| `docs/infra-maint-001-handoff.md` | `docs/archive/INFRA-MAINT-001/infra-maint-001-handoff.md` |
| `docs/label-001-review.md` | `docs/archive/LABEL-001/label-001-review.md` |
| `docs/maps-distribution-001-cache-design.md` | `docs/archive/MAPS-DISTRIBUTION-001/maps-distribution-001-cache-design.md` |
| `docs/maps-distribution-001-handoff.md` | `docs/archive/MAPS-DISTRIBUTION-001/maps-distribution-001-handoff.md` |
| `docs/maps-foundation-001-design.md` | `docs/archive/MAPS-FOUNDATION-001/maps-foundation-001-design.md` |
| `docs/maps-foundation-001-handoff.md` | `docs/archive/MAPS-FOUNDATION-001/maps-foundation-001-handoff.md` |
| `docs/maps-origins-001-design.md` | `docs/archive/MAPS-ORIGINS-001/maps-origins-001-design.md` |
| `docs/maps-origins-001-handoff.md` | `docs/archive/MAPS-ORIGINS-001/maps-origins-001-handoff.md` |
| `docs/media-visual-001-design-review.md` | `docs/archive/MEDIA-VISUAL-001/media-visual-001-design-review.md` |
| `docs/multibranch-uat-001-handoff.md` | `docs/archive/MULTIBRANCH-UAT-001/multibranch-uat-001-handoff.md` |
| `docs/order-001-handoff.md` | `docs/archive/ORDER-001/order-001-handoff.md` |
| `docs/phenology-001-handoff.md` | `docs/archive/PHENOLOGY-001/phenology-001-handoff.md` |
| `docs/preview-001-handoff.md` | `docs/archive/PREVIEW-001/preview-001-handoff.md` |
| `docs/schedule-001-handoff.md` | `docs/archive/SCHEDULE-001/schedule-001-handoff.md` |
| `docs/schedule-002-handoff.md` | `docs/archive/SCHEDULE-002/schedule-002-handoff.md` |
| `docs/search-002-handoff.md` | `docs/archive/SEARCH-002/search-002-handoff.md` |
| `docs/sourcing-visual-001-handoff.md` | `docs/archive/SOURCING-VISUAL-001/sourcing-visual-001-handoff.md` |
| `docs/supplier-003-handoff.md` | `docs/archive/SUPPLIER-003/supplier-003-handoff.md` |
| `docs/collection-taxonomy-plan.md` | `docs/archive/TAXONOMY-003/collection-taxonomy-plan.md` |
| `docs/taxonomy-003-handoff.md` | `docs/archive/TAXONOMY-003/taxonomy-003-handoff.md` |
| `docs/taxonomy-003-source.md` | `docs/archive/TAXONOMY-003/taxonomy-003-source.md` |
| `docs/taxonomy-visual-001-handoff.md` | `docs/archive/TAXONOMY-VISUAL-001/taxonomy-visual-001-handoff.md` |
| `docs/test-data-002-design.md` | `docs/archive/TEST-DATA-002/test-data-002-design.md` |
| `docs/themes-001-design-proposal.md` | `docs/archive/THEMES-001/themes-001-design-proposal.md` |
| `docs/themes-001-handoff.md` | `docs/archive/THEMES-001/themes-001-handoff.md` |
| `docs/themes-001-implementation-plan.md` | `docs/archive/THEMES-001/themes-001-implementation-plan.md` |
| `docs/ui-polish-001-review.md` | `docs/archive/UI-POLISH-001/ui-polish-001-review.md` |
| `docs/ux-004-reference.md` | `docs/archive/UX-004/ux-004-reference.md` |
| `docs/ux004-flake-001.md` | `docs/archive/UX-004/ux004-flake-001.md` |
| `docs/plants-plantgroups-ux.md` | `docs/archive/UX-006/plants-plantgroups-ux.md` |
| `docs/ui-consistency-polish.md` | `docs/archive/UX-006/ui-consistency-polish.md` |
| `docs/verification-evidence-001-handoff.md` | `docs/archive/VERIFICATION-EVIDENCE-001/verification-evidence-001-handoff.md` |
| `docs/verification-fast-001-handoff.md` | `docs/archive/VERIFICATION-FAST-001/verification-fast-001-handoff.md` |
| `docs/verify-speed-001.md` | `docs/archive/VERIFY-SPEED-001/verify-speed-001.md` |
| `docs/view-001-handoff.md` | `docs/archive/VIEW-001/view-001-handoff.md` |
| `docs/wcvp-version-001.md` | `docs/archive/WCVP-VERSION-001/wcvp-version-001.md` |

## `make license-check` report

- **PyPI**: 53 installed packages audited, **0 forbidden** (MIT, BSD-2/3-Clause, Apache-2.0,
  MPL-2.0, LGPL-3.0-only, PSF-2.0, MIT-0, MIT-CMU, AGPL-3.0-or-later).
- **npm**: 290 installed packages audited, **0 forbidden** (MIT, ISC, BSD-2/3-Clause, Apache-2.0,
  MPL-2.0, CC0-1.0, CC-BY-4.0, BlueOak-1.0.0, MIT-0).

## Remaining operator TODOs

1. Confirm **GitHub private vulnerability reporting** is enabled in repository Settings → Code
   security and analysis (referenced in `SECURITY.md`).
2. Confirm the proposed `DOCS-002` release class (`best-effort` in `docs/release/scope-v1.json`)
   and feature ID choice (`DOCS-002` because `DOCS-001` is an existing verified baseline entry).
3. Deliver via `make feature-deliver AGENT_ID=operator` (or batch with other work).
