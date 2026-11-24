# WF-BATCH-PROGRESS-001 evidence

- Branch `ci/wf-batch-progress-001` from `origin/main` `ddf5a14` (writer `claude-batch-progress-header`).
- Defect: since DOCS-002 added the `# Engineering progress` heading, two batch sources that each
  insert their milestone below it no longer match either additive rule in
  `scripts/feature_batch.py` `additive_progress()`, so `make feature-batch-prepare` refused Batch 12
  (DOCS-003 then FN-02) with `progress conflict cannot be resolved by retaining both sets of
  additions`.
- Fix: set aside the longest line prefix shared by the merge base, the integration side and the
  incoming source (keeping at least one base line in the remainder), apply the unchanged additive
  rules to the remainders, and restore the prefix. The base remainder must still appear intact in
  both sides, so an edit to existing entries still refuses.
- Checks:
  - `python3 scripts/test-agent-workflow.py AgentWorkflowTests.test_batch_additive_progress_keeps_shared_heading_above_both_sources AgentWorkflowTests.test_batch_additive_progress_preserves_main_tail_edit_and_fails_closed`
    passed; the new test fails with an error against the previous `feature_batch.py`.
  - Replayed on the real Batch 12 revisions (`6fe49ae` DOCS-003 merge, `66fec2f` FN-02 tip): the
    result keeps the heading, then the DOCS-003 and FN-02 milestones, then `main`'s entries
    unchanged.
  - `python3 scripts/check-features.py`.
