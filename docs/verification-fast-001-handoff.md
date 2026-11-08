# VERIFICATION-FAST-001: fast, deterministic canonical verification

Status: Phase 1 implemented on `ci/verification-fast-001`; Phase 2 (reusable stage evidence) is a
**proposal only** and changes nothing in this branch.

## Root causes addressed

1. **Expensive work ran before trivial checks.** `checks_for()` appended `whitespace`,
   `staged-whitespace` and `untracked-whitespace` *after* every workflow, quality, integration,
   build and migration stage. A FULL that passed every costly stage failed at the very end on two
   trailing Markdown blank lines. The one-line fix then needed a complete new FULL.
2. **Test helpers inherited the runner's stdin.** `AgentWorkflowTests.helper()` in
   `scripts/test-agent-workflow.py` passed no `stdin`. `feature_worktree.py claim` treats
   `TAKEOVER=` as an operator action only when `sys.stdin.isatty()`. A gate launched from a real
   terminal therefore turned the two "agent cannot take over" assertions into operator takeovers.
   Reproduced on base `fec0398` with a PTY stdin. Both tests fail
   (`AssertionError: 0 != 1 : WRITER CLAIMED: codex`) and pass with `/dev/null`.
   - `test_receiver_detects_tree_or_commit_drift_after_handoff`
   - `test_interrupted_writer_requires_exact_takeover_and_corrupt_state_fails_closed`

## Phase 1 changes

- `scripts/verification_gate.py`
  - Reorders stages, cheapest deterministic checks first (below). Coverage is unchanged: the
    same stage set and commands, with no new skips.
  - Every stage runs with `stdin=/dev/null`, so launches from a terminal, a pipe and CI behave the
    same way.
  - Prints the planned `Stage order:` up front, plus a per-stage summary (passed, failed,
    interrupted or not run, with elapsed seconds and a total) on success, failure and Ctrl-C.
  - Writes `<git-dir>/info/florabase-verification-last-run.json` atomically after every stage.
    This file is diagnostics only: it is never read back and never counts as evidence.
- `scripts/feature-verify.sh` runs the gate with `</dev/null`. Its frozen-tree check now compares
  the **working tree, index and HEAD** (`feature-tree-fingerprint.py frozen-state`), not the
  working tree alone. Running whitespace and staged-whitespace checks early is valid only if
  nothing can change the index or HEAD later in the run.
- `Makefile` `check` now runs `api-check` (generated-contract drift, a few seconds) before the
  unit suites: `format-check lint typecheck api-check test`.
- `scripts/test-agent-workflow.py` `helper()` passes `stdin=subprocess.DEVNULL`. The PTY-based
  `terminal()` operator tests are unchanged.

### Stage order

| # | Before (FULL) | After (FULL) |
|---|---|---|
| 1 | feature-graph | feature-graph |
| 2–4 | 8 offline workflow suites + workflow-check | whitespace, staged-whitespace, untracked-whitespace |
| 5–12 | quality (`make check`) | 8 offline host workflow suites |
| 13 | integration | workflow-check (Docker Ruff/format/mypy and beta policy tests) |
| 14 | production-builds | quality (`format-check lint typecheck api-check test`) |
| 15 | migration-cycle | production-builds |
| 16 | — | migration-cycle |
| 17 | whitespace ×3 (last) | integration |

Affected plans follow the same pattern: graph, then whitespace, then global static checks, then
the selected backend/frontend tests, builds, migration (when selected) and integration. Docs-only
plans are unchanged (graph plus whitespace).

Dependency notes:

- No stage consumes another stage's output. Each disposable stage owns and retires its own
  project.
- Reordering is safe because the whole run is bracketed by the frozen-state comparison.
- Builds, migration and integration are ordered by observed cost: cached builds take 3–7 s, one
  migration cycle about 30 s, integration 35–200 s.

### Measurements

Run on this host on 2026-11-06, Docker 29 with the operator's DEV and UAT running.

- **Markdown-EOF FULL, real run.** `make verify-full` was run in this worktree with an untracked
  Markdown file ending in a blank line.
  - Before: the whitespace stages ran only after every other stage, so failure came after the
    complete FULL. Historical remote equivalents: quality 410 s, integration 197 s, builds 34 s,
    plus about 136 s of local workflow suites, workflow-check and the migration cycle.
  - After: failed in **10.5 s wall time**. Most of that is `git fetch` and plan computation; the
    four source-state stages took 0.12 s. Thirteen stages were reported `not run`, and no Docker
    resource was created.
- **Offline workflow suites, sequential.**
  - Base (stdin `/dev/null`): helpers 1 s, feature 19 s, agent 111 s, preview <1 s,
    environment 1 s, UAT 1 s, impact 2 s, resources <1 s. All passed.
  - After, with a **PTY stdin** (the operator-terminal case that failed before): helpers 1.45 s,
    feature 22.08 s, agent 107.42 s, preview 0.55 s, environment 1.77 s, UAT 1.38 s, impact
    3.08 s, resources 0.09 s. All passed, about 138 s in total, the same as base.
- Per-stage times are otherwise unchanged by reordering. The saving is time-to-failure for
  cheap-class defects, and no repeated expensive stages after their fix.

### Regression tests

`scripts/test-verification-impact.py`:

- Exact FULL stage order and set. Whitespace is first in every product plan, and affected cost
  order is preserved.
- `make check` prerequisite order.
- Stage stdin is not a TTY, and is empty, even when the gate runs under a PTY.
- The failure summary and diagnostics journal report failed and `not run` stages and leave no
  temporary files.

`scripts/test-feature-workflow.py` (real `feature-verify.sh` in a Git fixture):

- A FULL with a committed Markdown file ending in a blank line fails at `whitespace` before any
  make/Docker command. A second untracked one fails at `untracked-whitespace`. After both fixes,
  FULL passes and writes a fresh receipt.
- A stage that stages a file (`git add`) during verification is refused with no receipt.
- A gate launched with a PTY stdin gives every stage a noninteractive stdin and writes the stage
  summary and journal.

All new tests fail against the base scripts (verified by temporarily restoring them) and pass after
the change.

## Phase 2 proposal: reusable stage evidence (not implemented)

### Is it still needed after Phase 1?

The motivating scenario was a cheap-class failure after expensive stages. Phase 1 removes it, and
policy tests that read documentation now also run before Docker suites. The remaining real
benefit is a **post-gate edit outside the expensive stages' input closure**. The common case is a
docs-only wording or `docs/progress.md` change after a passing FULL. Today that requires a
complete new FULL, about 15 minutes. With reuse, only graph, whitespace, workflow suites,
workflow-check, builds and migration would rerun (about 4–5 minutes), while `quality` and
`integration` are reused.

That is a real but narrower saving. It needs a new receipt version and an operator policy
decision, so it belongs in a **separate feature/PR** (proposed id `VERIFICATION-EVIDENCE-001`).

### Two kinds of caching

- **Dependency/build caching** already exists and stays as it is: BuildKit layers, Quality images,
  the `frontend_node_modules` volume. It makes stages *faster*, but it is **never evidence**.
- **Stage evidence reuse** would skip a stage entirely because an equivalent execution already
  passed. Only this needs the safety proof below.

### Which stages could be reused

| Stage | Enforced input boundary | Proposal |
|---|---|---|
| feature-graph, whitespace ×3 | whole tree | always run (milliseconds) |
| offline workflow suites | **none**: host processes read anywhere. `test-agent-workflow.py` reads `docs/development-workflow.md`; `test-beta-images.py` reads `docs/beta-image-001.md` | always run |
| workflow-check | mounts the repository root | always run |
| quality (`make check`) | Compose bind mounts and build contexts: `backend/**`, `frontend/**`, plus host wrappers | reuse candidate |
| integration | backend build context plus `./scripts:/review:ro` | reuse candidate |
| production-builds | build contexts plus base images resolved by tag | always run; BuildKit makes them cheap |
| migration-cycle | mutable disposable PostgreSQL, base checkout, cleanup evidence | **always fresh** (the FULL contract requires a real cycle) |

Documentation is *not* inert in general, as the reads in the table show. Reuse is only proposed
where Docker mounts **enforce** the input boundary. A path list maintained by hand would not prove
it.

### Evidence record

- **Location:** `<absolute-git-dir>/florabase-stage-evidence/<key>.json`. That is per worktree,
  outside the source tree, and never shared across worktrees or trusted from clients or CI.
- **Writing:** a record is written only after the stage exits 0, under the existing per-worktree
  verification lock. It goes to a temporary file in the same directory, is fsynced, then moved into
  place with `os.replace`. A failed, interrupted or partial run therefore leaves no record for its
  stage, but records of earlier passed stages survive.
- **Fields:** schema version, stage id, exact argv, key, the full input manifest, result `passed`,
  exit 0, UTC start and end, run id, and a digest over the record body.

The **key** is a SHA-256 over:

1. Schema version, stage id and exact argv.
2. The gate implementation: `verification_gate.py`, `verification_impact.py`,
   `verification-impact.json`, `feature-verify.sh`, `feature-tree-fingerprint.py`,
   `workflow_environment.py` and its imports, `workflow_resources.py`, `disposable_workflow.py`,
   the `Makefile`, and the stage's helper scripts.
3. The **input closure**, derived from `docker compose config --format json` (bind sources plus
   build contexts filtered by `.dockerignore`), not listed by hand.
   - It covers the content, mode and symlink digests of every tracked and untracked file inside
     the closure, using the existing `working_entries()` semantics.
   - Any mount type or source it cannot classify means *no reuse*.
4. Compose files, the resolved env-file content digest and an allowlist of environment variables
   (`LOCAL_UID`, `LOCAL_GID`, `FLORABASE_*`).
5. Tool identity: Docker server and Compose versions, host Python and Git versions.
6. **Image identity after a fresh `compose build`** (cheap when cached), plus resolved digests of
   base images and the PostgreSQL image.
7. For quality: the digest of `node_modules/.modules.yaml` after `dev-state-init`
   reconciliation. The mutable volume itself is never trusted.

### Reuse rule

A stage is reused only if all of the following hold. Otherwise it runs normally, and the log says
why: `miss`, `invalidated: <input class changed>`, `corrupt`, `schema` or `fresh requested`.

- The record exists and parses.
- The schema matches and the body digest verifies.
- The result is `passed` with exit 0.
- The key recomputed from current state equals the stored key, *and* every manifest entry
  recomputes identically.
- The stage is not one of the always-run or always-fresh stages above.
- The run is local. Remote CI never reuses.

The record digest detects corruption and partial writes. It does not stop deliberate tampering by
the same OS user, which is consistent with the cooperative workflow protocol.

### Receipt

- The receipt becomes version 3. Each reused completed entry carries `reused_from` (run id, key,
  `finished_at`), so delivery policy can see exactly what was reused.
- The receipt is still written fresh for the exact working tree. It still requires the clean,
  committed HEAD tree at delivery, and the plan is still recomputed.
- An old receipt is never copied to a new HEAD. A new commit always gets its own receipt.
- Whether reused stages are acceptable for **FULL** delivery is an **operator policy decision**.

### Controls and rollout

- `make feature-verify FRESH=1` (and `--fresh`) ignores every record. Reuse starts **opt-in**
  (`REUSE=1`).
- Before reuse is enabled, a dry-run mode logs "would reuse / invalidated because …", to show the
  key is stable and conservative.
- Docker hygiene: a reused stage creates no resources and skips no cleanup. The gate should finish
  with a `workflow-resources` residual check either way.
- Tests required:
  - cache hit;
  - misses for each input class: application file, workflow script, lockfile, Dockerfile, Compose
    file, env file, image digest, tool version, policy map;
  - a migration file always runs fresh;
  - a tampered or truncated record;
  - a failed or interrupted stage leaves no record;
  - two concurrent gates;
  - `FRESH=1`;
  - the receipt for a new HEAD is never copied;
  - the docs-only post-gate edit reuses quality and integration and reruns the rest.

## Remaining risks and follow-ups

- Remote `ci-verify.py` quality jobs run whitespace checks only for docs-only PRs. Product PRs rely
  on the local gate for `git diff --check`. Adding the three cheap checks to the remote `quality`
  job is a separate CI change: it affects every open PR, including `feat/beta-distribution-001`,
  so it needs coordination.
- `make check` order is shared with remote CI and other branches. This branch changes only its
  prerequisite order, not its contents.

## Consolidation audit, 8 November 2026

The passing local FULL for PR #155 at `7e7376240fd047fd46e0e47063e5f73c2dabb605` recorded
1,094.02 seconds of stage execution (18m 14s). This excludes time waiting for the machine lock and
work outside the stage timer. The measured run does not account for a 25-minute elapsed estimate.

| Stage | Recorded time | Breakdown |
| --- | ---: | --- |
| PostgreSQL integration | 572.50 s | 558.81 s inside pytest, 807 passed and 29 skipped. About 14 s outside pytest for build/start/migration and cleanup combined |
| Quality | 364.12 s | Frontend Vitest took 254.80 s and backend pytest took 16.84 s |
| Workflow checks and source checks | 144.60 s | Agent workflow fixtures took 97.05 s |
| Production builds and migration cycle | 12.81 s | 3.20 s for builds and 9.61 s for the separate migration cycle |

The original integration log did not attribute time to individual tests. The integration Compose
service now reports the 20 slowest setup, call or teardown phases of at least 0.1 s. The same
report is available through selected-file runs. The test command, isolation and gate coverage are
unchanged.

- During iteration, use `make verification-plan` to inspect existing affected selection and use
  `./scripts/test-integration.sh backend/tests/integration/test_taxonomy_migration.py` when only that
  module needs feedback. Run focused workflow and disclosure checks before freezing CI or operator
  docs. Run canonical FULL once after review on the finalized tree.
- Use the timing table to target the most expensive fixture or test first. Compare identical
  selections on the same host. An integration sharding trial would need a fresh database per shard,
  equivalent collection and skips, and preserved migration/cleanup guarantees. Some tests change
  the schema and share a session database. Evaluate frontend worker isolation separately because
  the current Vitest config disables file parallelism.
- Retain existing dependency and BuildKit caches. For cold hosted runs, measure download and build
  costs before adding a cache. Key any new dependency cache by lockfile, toolchain and platform
  and continue validating locked installs. Keep PostgreSQL state, results and receipts out of caches.
- For a release failure, correlate the exact SHA, run and attempt with the first failing step,
  existing release checkpoints and retained artifacts. For a follow-up diagnostics change, surface
  that phase and link the artifacts in the job summary without including credentials or creating
  a retry path around an identity or publication check.
