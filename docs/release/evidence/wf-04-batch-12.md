# WF-04 Batch 12 integration evidence

The Batch 12 integration branch is `ci/batch-12`, based on pinned `origin/main` at
`ddf5a1431453df6c6644fb1f2e9feeec6b120e16` (PR #223). The integration writer is `claude-batch-12`.
The [manifest](batches/batch-12.json) records the zero-bootstrap linear base, exact source tips,
merge commits, additive `docs/progress.md` resolutions and post-merge reconciliations.

## Source provenance and exact-tip readiness

Each source was frozen in its own clean, claimed worktree with no pending handoff:

| ID | Branch | Frozen tip | Writer | Source QA | Committed evidence |
| --- | --- | --- | --- | --- | --- |
| WF-BATCH-PROGRESS-001 | `ci/wf-batch-progress-001` | `ea607ee444d6f7add330164f38f7e839a0c55c0b` | `claude-batch-progress-header` | `claude-wf-batch-progress-qa` | [`wf-batch-progress-001.md`](wf-batch-progress-001.md) |
| DOCS-003 | `docs/docs-003-install-guide` | `a2b50350a5d718e9385cc251c7dcf2fcaa4d1ecb` | `antigravity-docs-003` | `claude-docs003-source-qa` | [`beta-8-publication.md`](beta-8-publication.md), [`handoff.md`](../../archive/DOCS-003/handoff.md) |
| FN-02 (with FN-04, UX-ENTRY-001) | `feat/fn-02-fn-04-list-ux` | `66fec2f9ae13c67a33090a18a38d5b334377762b` | `claude-pkg-b` | `claude-pkgb-source-qa` | [`fn-02-fn-04-ux-entry-001.md`](fn-02-fn-04-ux-entry-001.md) |
| UI-REVIEW-002 | `fix/plants-list-reference-mount` | `2c03a67c763b7f776767b8459c2743230d37f979` | `claude-batch13-impl` | `claude-batch13-source-qa` | [`ui-review-002.md`](ui-review-002.md) |

## Integration conflict and cross-branch checks

- **Why a third source:** the first preparation (DOCS-003 then FN-02) refused FN-02 with
  `progress conflict cannot be resolved by retaining both sets of additions` because both sources
  insert their milestone below the `# Engineering progress` heading added by DOCS-002.
  WF-BATCH-PROGRESS-001 fixes `additive_progress()` and merges first; preparation ran with that
  source's `scripts/feature_batch.py`, which is the script in the integrated tree.
- **Conflict resolution:** WF-BATCH-PROGRESS-001 merged cleanly. DOCS-003, FN-02 and UI-REVIEW-002
  auto-merged `docs/features.json`, `docs/release/scope-v1.json`, `docs/installation.md` and
  `compose.yaml` and conflicted only in `docs/progress.md`, resolved additively by
  `feature-batch-prepare`; source milestones stay in merge order below the heading.
- **Cross-branch compatibility:** FN-02 and UI-REVIEW-002 share no `frontend/` or `backend/` file;
  `compose.yaml` keeps the FN-02 one-time setup header and the UI-REVIEW-002 reference-index
  pointer. DOCS-003 deferred the `compose.yaml` header and `UpdateNotice.test.tsx` fixtures to
  FN-02, which carries them. UI-REVIEW-002 was added after Alessandro asked to fold the
  post-beta.8 review fixes into this batch so that one FULL covers all four sources.
- **Compose line budget:** the first four-source candidate (UI-REVIEW-002 at `cceaf3c`) produced a
  53-line `compose.yaml` and failed the 50-line limit in `scripts/test-beta-runtime.py`; UI-REVIEW-002
  was reduced to one comment line (snippet moved to `docs/installation.md`) at `2c03a67`, and the
  merged file is exactly 50 lines. At the operator's request the limit in
  `StackContract.test_minimal_shape_services_and_latest_images` was then raised from 50 to 60 lines
  to restore headroom; every other minimal-Compose assertion is unchanged.
- **Reconciliation:** prepended the Batch 12 integration milestone to
  [`docs/progress.md`](../../progress.md) and recorded this provenance document.
- **Proposed release classes (for operator confirmation):** `WF-BATCH-PROGRESS-001` (`tooling`),
  `DOCS-003` (`release-work`), `FN-02`, `FN-04`, `UX-ENTRY-001`, `UI-REVIEW-002` (`best-effort`), all
  `implemented`.
