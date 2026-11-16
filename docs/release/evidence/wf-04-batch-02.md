# WF-04 Batch 02 integration evidence

The Batch 02 integration branch is `ci/batch-02`, based on `origin/main` at
`554d74de88a278e2b9a392de9d105d3d62c35f91`. The bootstrap commit
`5a7f78ff4156a2d13ca605dfd6e1005a2e2459f7` registers `CI-005` (`implemented`, `tooling`) in
[`docs/features.json`](../../features.json) and [`docs/release/scope-v1.json`](../scope-v1.json)
and permits `scripts/*.py` paths in batch manifest reconciliation.
The [batch manifest](batches/batch-02.json) records the bootstrap commit, the five exact source
tips, merge commits, additive `docs/progress.md` resolutions, and post-merge reconciliations.

## Source provenance and exact-tip readiness

Each source was verified at its frozen tip in a clean, claimed worktree with no pending handoff
and committed repository evidence:

| ID | Branch | Frozen tip | Writer | Source QA | Committed evidence |
| --- | --- | --- | --- | --- | --- |
| FN-05 | `feat/fn-05-journal-today` | `a470811742e694c1df579b65ad13f586e73a5864` | `hydrogen-fn-05` | `argon-qa` | [`fn-05.md`](fn-05.md), [`progress.md`](../../progress.md) |
| FN-06 | `feat/fn-06-journal-navigation` | `e6f85c9865d7e8eabe7a6876d7754f5905eb74aa` | `hydrogen-fn-06-journal-nav` | `argon-qa` | [`fn-06.md`](fn-06.md), [`progress.md`](../../progress.md) |
| DOC-05 | `docs/doc-05-audit` | `fad0e06232d8131ae5614be2cc146f6fb1f832d1` | `terra-doc05` | `source-qa` | [`versioning.md`](../../versioning.md), [`progress.md`](../../progress.md) |
| WF-06 | `feat/wf-06` | `e538874e61b5107d98cf9a27a1963ba2e8f43254` | `terra-wf06` | `source-qa` | [`wf-06.md`](wf-06.md), [`progress.md`](../../progress.md) |
| CI-005 | `docs/g-docs-links` | `a97b870a19733609679af009a2f947e5e480cf7c` | `terra-gdocs` | `source-qa` | [`g-docs-links.md`](g-docs-links.md), [`progress.md`](../../progress.md) |

## Preflight and scope consistency

- **CI-005 registration:** `G-DOCS` remains a release gate in [`scope-v1.md`](../scope-v1.md);
  the offline Markdown link checker (`scripts/check-doc-links.py` and `scripts/test-doc-links.py`)
  is registered as `CI-005` (`implemented` in `docs/features.json`, `tooling` in
  `docs/release/scope-v1.json`) so it satisfies the WF-04 feature identifier contract without
  adding a mandatory v1.0 certification blocker.
- **DOC-05 status:** `DOC-05` is `implemented` (not `verified`), supported by
  [`CHANGELOG.md`](../../../CHANGELOG.md), [`docs/versioning.md`](../../versioning.md) and
  [`SECURITY.md`](../../../SECURITY.md). With `DOC-05` at `implemented`,
  `python3 scripts/check-features.py --release-candidate` reports the eight remaining open
  `certify` and `release-work` blockers (`RELEASE-001`, `CUTTING-001`, `UI-SYSTEM-001`,
  `BETA-IMAGE-001`, `beta-postgres-repro-001`, `BETA-SECURITY-001`, `BETA-DATA-001`,
  `BETA-ACCEPTANCE-001`).
- **WF-03 test ownership:** `scripts/test-doc-links.py` and `scripts/test-workflow-cleanup.py`
  reside under `scripts/` (`full_prefixes`), and `make verification-plan` validates the test
  inventory before any Docker stage starts.
- **Simulated GitHub Actions CI preflight:** Offline workflow and impact suites passed under
  `GITHUB_ACTIONS=true`, covering `GITHUB_HEAD_REF`, `GITHUB_EVENT_NAME`, `GITHUB_EVENT_PATH`,
  `GITHUB_SHA`, synthetic PR merge and branch mismatch refusal, nested local receipt fixture
  isolation, and fail-closed remote stage-evidence refusal.
- **Disclosure scanner reconciliation:** `make test-beta-runtime` (`Disclosure` suite) caught
  host-home paths in `docs/release/evidence/fn-05.md` and `docs/search-002-handoff.md` and a
  synthetic `.invalid` email literal in `scripts/test-workflow-cleanup.py`; these were sanitized
  in the final batch reconciliation commit on `ci/batch-02` while preserving the five frozen source
  worktrees and their original commit ancestry.
