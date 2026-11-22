# WF-04 Batch 10 integration evidence

The Batch 10 integration branch is `ci/batch-10`, based on pinned `origin/main` at
`1e985f106b6f34185a3724605ea1b47e44da79dd` (PR #213). The integration writer is `neon` with claim
`21d44024b6bf`. The [manifest](batches/batch-10.json) records the linear bootstrap commit, exact
source tips, merge commits, additive `docs/progress.md` resolution, and post-merge reconciliations.

## Bootstrap commit

`b51e2b31496df993d42a5f07b8ea448dadb56aad` updates `additive_progress` in `scripts/feature_batch.py`
and adds regression coverage in `scripts/test-agent-workflow.py`. Because PR #213 (`1e985f1`)
amended the final line of `docs/progress.md` after `c5f9cdf`, the previous exact-substring check
refused a pure top-of-file prepend from a second source branched from `c5f9cdf`. The updated helper
preserves fail-closed rejection whenever the incoming source modifies existing content or the
integration branch alters the top anchor, while retaining both top-of-file additions and `main`'s
non-conflicting tail update.

## Source provenance and exact-tip readiness

Each source was frozen in its own clean, claimed worktree with no pending handoff and independently
reviewed before preparation:

| ID | Branch | Frozen tip | Writer | Source QA | Committed evidence |
| --- | --- | --- | --- | --- | --- |
| INSTALL-002 | `feat/install-002-minimal-compose` | `a012f4360171b1a34ca5422d6487b811ba94fb98` | `neon` | `independent-source-qa` (PASS) | [`0009-minimal-production-compose.md`](../../decisions/0009-minimal-production-compose.md), [`installation.md`](../../installation.md), [`progress.md`](../../progress.md) |
| WF-SCOPE-001 | `feat/wf-scope-001-scoped-verification` | `1b78a0452031bd5ad0ebacc0515916037d7a2a28` | `neon-wf-scope-001` | `independent-source-qa` (PASS WITH NOTES) | [`development-workflow.md`](../../development-workflow.md), [`progress.md`](../../progress.md) |

## Integration conflict and cross-branch checks

- **Conflict resolution:** `INSTALL-002` (including `a012f43`, which restored `internal: true` and
  `app` network isolation in `compose.yaml`, `scripts/test-beta-runtime.py`,
  `scripts/test-beta-images.py`, `scripts/smoke-portable-compose.py`, ADR 0009 and
  `docs/security.md` while keeping `read_only`/`cap_drop` as the optional override snippet) merged
  cleanly onto `b51e2b3` (`b150388`). Merging `WF-SCOPE-001` (`b34ab43`) auto-merged
  `docs/features.json` and `docs/release/scope-v1.json` and conflicted only in `docs/progress.md`,
  resolved additively by `feature-batch-prepare` with all entries preserved newest-first
  (`INSTALL-002` above `WF-SCOPE-001` above `ENG-05`, retaining `1e985f1`'s tail UAT smoke
  milestone).
- **Cross-branch compatibility:** `backend/tests/test_release_schema.py` is owned by `full_tests`
  and `backend/tests/test_infrastructure.py` by `product_backend_tests` in `WF-SCOPE-001`'s v2
  impact map; `.github/workflows/beta-release-rehearsal.yml` satisfies all assertions in
  `INSTALL-002`'s `scripts/test-beta-images.py`.
- **Reconciliation:** Prepended the Batch 10 milestone in [`docs/progress.md`](../../progress.md)
  and recorded this provenance document.
- **Proposed release classes (for operator confirmation):** `WF-SCOPE-001` (`tooling`,
  `implemented`) and `INSTALL-002` (`release-work`, `implemented`) in
  [`docs/release/scope-v1.json`](../scope-v1.json). No checks were weakened.

Exact-commit independent batch review (`make feature-batch-review`) and one fresh canonical FULL
gate (`env -u REUSE FRESH=1 make feature-verify AGENT_ID=neon`) validate the frozen committed head
before operator delivery.
