# WF-04 Batch 11 integration evidence

The Batch 11 integration branch is `ci/batch-11`, based on pinned `origin/main` at
`ef5451f782d8ef9c44d3a7f0d28394bcf1a5a8ea` (PR #215). The integration writer is `neon` with claim
`9e49bc34819b`. The [manifest](batches/batch-11.json) records the zero-bootstrap linear base, exact
source tips, merge commits, additive `docs/progress.md` resolution, and post-merge reconciliations.

## Source provenance and exact-tip readiness

Each source was frozen in its own clean, claimed worktree with no pending handoff and reviewed
before preparation (source branches were not rewritten):

| ID | Branch | Frozen tip | Writer | Source QA | Committed evidence |
| --- | --- | --- | --- | --- | --- |
| INSTALL-003 | `feat/install-003-latest-compose` | `ac93677107886284a91c9b36e2bdb751a2cf458f` | `antigravity-install-003` | `independent-source-qa` | [`0010-deployable-latest-compose.md`](../../decisions/0010-deployable-latest-compose.md), [`installation.md`](../../installation.md), [`progress.md`](../../progress.md) |
| UI-REVIEW-001 (with LINEAGE-004 merged) | `fix/ui-ux-review` | `27ece94337fff7ba40951ee9194e1eb707b2e51e` | `claude-ui-review` | `independent-source-qa` | [`lineage-explorer.md`](../../lineage-explorer.md), [`page-inventory-v1.md`](../page-inventory-v1.md), [`progress.md`](../../progress.md) |

## Integration conflict and cross-branch checks

- **Conflict resolution:** `INSTALL-003` (`ac93677`, merge `fae46af`) auto-merged
  `docs/features.json` and `docs/release/scope-v1.json` and conflicted only in `docs/progress.md`,
  resolved additively by `feature-batch-prepare`. `UI-REVIEW-001` (`27ece94`, which already merged
  `origin/main` `ef5451f` and `LINEAGE-004` `77b8b54`, merge `76b0479`) merged cleanly onto
  `fae46af` with zero conflicts (`README.md`, `docs/features.json`, `docs/release/scope-v1.json`,
  and `docs/progress.md` all merged cleanly).
- **Cross-branch compatibility:**
  - `README.md` retains both the `UI-REVIEW-001` showcase/screenshots update and the `INSTALL-003`
    Architecture/Requirements `:latest` Compose instructions.
  - `docs/features.json` retains all 176 features (`VERIFY-SPEED-001`, `INSTALL-002`,
    `INSTALL-003`, `LINEAGE-004`, `UI-REVIEW-001`) and passes `scripts/check-features.py`.
  - All new tests introduced by `fix/ui-ux-review` (`frontend/src/settings/HelpAndSources.test.tsx`,
    `frontend/src/lineage/IdentityLineage.test.tsx`) and modified tests in both branches are owned
    by `scripts/verification-impact.json` v2 (`product_frontend_prefixes`, `scopes.lineage`, and
    `full_tests`).
- **Reconciliation:** Reordered the newly merged `INSTALL-003`, `UI-REVIEW-001`, and `LINEAGE-004`
  milestones in [`docs/progress.md`](../../progress.md) newest-first above `VERIFY-SPEED-001`
  without dropping any entry (retaining `main`'s tail UAT smoke milestone), prepended the Batch 11
  integration milestone, and recorded this provenance document.
- **Proposed release classes (for operator confirmation):** `INSTALL-003` (`release-work`,
  `implemented`), `UI-REVIEW-001` (`best-effort`, `verified`), and `LINEAGE-004` (`best-effort`,
  `verified`) in [`docs/release/scope-v1.json`](../scope-v1.json). No checks were weakened.

Exact-commit independent batch QA (`make feature-batch-review`) and one fresh canonical FULL gate
(`env -u REUSE FRESH=1 make feature-verify AGENT_ID=neon`) validate the frozen committed head
before operator delivery.
