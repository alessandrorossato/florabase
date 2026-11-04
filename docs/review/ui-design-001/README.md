# UI-DESIGN-001 — visual and interaction consistency review

> **Status: COMPLETE — DOCUMENTED DESIGN REVIEW · NO IMPLEMENTATION APPROVED.** UI-DESIGN-001 is complete as a documented design review,
> closed on 4 November 2026. Its audit, findings, proposals, mockups and design artifact are retained as
> a reference baseline. **No implementation was approved.** Decisions D1–D6 remain open and were not
> decided. The operator chose to explore a more radical UI/UX redesign in a separate feature (Florabase
> Next) instead of implementing this plan. No frontend code, design token, API, schema or fixture was
> changed.

- **Main commit reviewed:** `61fefbbd026ae11fd84394acba698a84abc7f16d` (`61fefbb`, #144, 4 November 2026).
  The last frontend source change before it is `9ef2b63` (#138, 2 November, tests only).
- **Interactive design artifact:** [Florabase UI System (Claude Design)](https://claude.ai/artifact/T5A2PpURaCtwGxYTU6F8eN).
  It is private to its owner until shared from its Share menu. It holds the editable token set, 13
  component cards, the interactive Plants workspace and the before/after page. This folder is its
  retained Git export.
- **Implementation:** none approved. If any part of this plan is revived, it needs a new operator-approved
  increment, with Claude Code implementing and an independent session on a different model reviewing.
  **Codex is not assigned implementation work.**

## How to read this package

Every statement carries one of these labels.

| Label | Meaning |
| --- | --- |
| **EXISTING** | Current delivered behavior or contract, described as it is (source or documented contract). |
| **VERIFIED (source)** | Measured by a scan or a line reference in `frontend/src` at `61fefbb`. Reproducible with the cited file and line. |
| **EVIDENCE (1 Nov)** | Observed in a browser capture taken on 1 November 2026 (Wave 3 branch, same frontend source). Not re-observed live. |
| **PROPOSAL** | A design recommendation from this review. Not approved. |
| **DECISION PENDING** | Needs an operator decision before any implementation (D1–D6). |

## Contents

| Document | Purpose |
| --- | --- |
| [audit.md](audit.md) | Concise audit by criterion, plus earlier findings re-checked against main |
| [findings.md](findings.md) | Prioritized inconsistencies F-01 to F-17 with concrete evidence |
| [decisions.md](decisions.md) | D1–D6, the options and their consequences. None chosen |
| [proposed-changes.md](proposed-changes.md) | Ten visual rules, token additions and component changes |
| [implementation-plan.md](implementation-plan.md) | Phased plan for Claude Code, lowest regression risk first |
| [acceptance-checklist.md](acceptance-checklist.md) | Visual acceptance and public screenshot checklist |
| [evidence.md](evidence.md) | The existing captures used as "before" evidence (referenced in place, not copied) |
| [mockups/](mockups/README.md) | Seven static renderings of the proposal. **Design mockups, not production screenshots** |

## Relationship to existing documentation

This package extends the existing UI System v1 material; it does not restate it. The authoritative
sources stay where they are:

- [UI Foundation v0.1 contract](../../ui-contract.md): tokens, type, spacing, page grammar, interaction surfaces.
- [`frontend/src/styles/tokens.css`](../../../frontend/src/styles/tokens.css): the single token source (six themes).
- [UI System v1 overview](../../design/ui-system-v1/README.md) and the [Gate B composition contract](../../design/ui-system-v1/gate-b/implementation.md).
- [Wave 3 consolidation](../../design/ui-system-v1/consolidation/README.md), [final interaction correction](../../design/ui-system-v1/consolidation/final-interaction-correction/README.md) and [Details/cover closure matrix](../../design/ui-system-v1/consolidation/details-cover/README.md) (UI-DETAIL-001, UI-FLICKER-001, QA-1 to QA-10).
- [UI-POLISH-001 review](../../ui-polish-001-review.md) and [RELEASE-VISUAL-AUDIT-001](../release-visual-audit-001/README.md) (F01–F09).

The design artifact's token file mirrors `tokens.css` exactly for review purposes. It is not a second
token source, and the proposed tokens in it are not in the product.

## Limitations

- **No authenticated live session on current main.** The local development stack requires the owner's
  sign-in, which the reviewing agent may not enter. The live UI was not observed during this review.
- **Screenshots are from 1 November 2026.** They come from the Wave 3 evidence sets, whose frontend
  source matches `61fefbb`. One of them, the desktop Plants capture, shows a loading state instead of
  records (F-17).
- **No physical-device, screen-reader, real browser-zoom or forced-colors verification.** Contrast
  ratios are computed from `tokens.css` values, not measured on rendered pixels.
- The mockups are hand-built recreations rendered with synthetic data. They show intended structure
  and hierarchy, not pixel parity with the product. See [mockups/README.md](mockups/README.md) for the
  known raster artifacts.

## Closure

- **Complete:** the documented review (audit, findings F-01–F-17, proposed changes, plan, checklist,
  evidence index, mockups, and the interactive design artifact).
- **Not approved:** every PROPOSAL and every phase of the [implementation plan](implementation-plan.md).
- **Open:** D1–D6 ([decisions.md](decisions.md)), deferred without a decision.
- **Successor:** Florabase Next, a separate creative-exploration feature with a working alternative
  frontend. It may use this package as reference evidence. It is not bound by these proposals, and
  this package does not approve or start it.
- **Still valid as findings:** the VERIFIED (source) items describe `61fefbb` and remain true until the
  cited code changes. Re-check them before relying on them.

## Phase boundary

Documentation only, committed locally on `docs/ui-design-001`. No push, PR, merge, delivery or
feature-finish. No frontend, token, backend, migration, fixture or environment change. No Review, DEV
or UAT environment was started, modified or signed into.
