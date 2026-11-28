# Batch integration (WF-04)

> Summary: Multi-branch batch preparation, additive progress merge, verification, delivery, and batch finish.

## Batch integration (WF-04)

Use a dedicated `ci/batch-<id>` worktree (or `ci/wf-04-batch-01` for the bootstrap) with one
claimed writer. Source writers can continue their independent focused QA. Select only source
tips whose owners have frozen them for integration and whose independent evidence names the
tested revision. A clean worktree alone is insufficient. Keep each owner's original receipt
and QA. Ready sources enter the reviewed batch without separate canonical runs.

```bash
make feature-batch-plan
make feature-batch-plan REQUEST=/path/to/request.json > /path/to/plan.json
make feature-batch-prepare PLAN=/path/to/plan.json AGENT_ID=<integration-writer>
```

A request is a JSON object with `branch`, `summary`, `base`, and `sources`. The `summary` is
one reviewed plain line of 10 to 72 characters, without commit IDs, backticks or a type
prefix. Preparation refuses a plan without it and records it in the manifest, so it cannot
change afterwards. Delivery titles the PR `chore(release): <summary> (batch <id>)`, and the PR
body keeps every source ID, branch and commit. A manifest without a summary predates this
rule and keeps its original title. Each source specifies
`id`, `branch`, full `tip`, `reviewer` and `evidence` (committed Markdown paths at its tip).
List sources in the intended merge order. The planner checks the pinned base, exact clean
tips, writer claims, gates and evidence paths. The writer compares the regenerated plan again
before and after preparation. The manifest under `docs/release/evidence/batches/` records
the source commits and the original tips remain ancestors of the integration head.

Preparation refuses conflicts outside an additive `docs/progress.md` merge. When a source
has a conflict, fix or review it deliberately before starting a new candidate. Record any
post-merge documentation reconciliations as a path-to-reason mapping in the manifest's
`reconciliation` object. Stage those files and the manifest together and commit them as the
single commit following the final source merge. A reviewer in a detached checkout verifies
this exact commit, the merge replay, and the evidence. Give the writer a JSON review containing
`reviewer`, `head`, `base`, `tree`, `result` (equal to `pass`) and `evidence`.

```bash
make feature-batch-review REVIEW=/path/to/exact-review.json AGENT_ID=<integration-writer>
env -u REUSE FRESH=1 make verify-full AGENT_ID=<integration-writer>
```

For a batch, the operator runs `make feature-deliver AGENT_ID=operator` from the integration
worktree. Delivery revalidates the source tips, no-reuse FULL receipt, exact commit approval,
and strict up-to-date GitHub Actions checks. The protected jobs verify the platform merge tree
against the manifest's pinned base and exact head. After protected squash, delivery confirms
the squash parent and tree and archives proof and a private local ref under shared Git
metadata. A changed base or tree requires a new reviewed candidate and a fresh receipt.

For a same-base correction to an open batch PR, add a single fast-forward commit. Its manifest
`correction` records the direct parent in `supersedes`, the workflow and documentation
`paths` changed, and the `reason`. Keep the original provenance. After exact-head QA and a
fresh FULL, supply `EXPECTED_PR=<number>` and `EXPECTED_HEAD=<corrected-sha>` to
`feature-deliver`. It verifies and reuses that PR, preserving the original title and body.


After the operator authorizes finish, run the usual `make feature-finish` from the integration
branch for that branch's own merged PR. This fast-forwards clean primary `main`, installs the
updated helpers, and auto-retires the managed integration worktree when safe. Then run
`make feature-batch-finish PR=<number> AGENT_ID=operator` from clean primary `main`.
It verifies the PR again and processes only its listed source tips;
`SOURCE=feat/example` limits finish to one. Moved tips, missing proof and protected resources
refuse, and the output identifies any unfinished source. For each finished source, batch finish
applies the same best-effort managed-only retirement (`FINISHED <branch> at <tip>; RETIRED <path>`
or `FINISHED <branch> at <tip>; RETAINED <path> (<reason>)`); retention does not fail the command,
and `KEEP_WORKTREE=1` opts out. Retained managed worktrees can still use the explicit
`make feature-retire` confirmation later. Provider-managed worktrees remain with their provider and
any Preview/UAT owner remains subject to its existing lifecycle rules.
