# CI-003 FULL migration-cycle repair — 2026-10-10

## DEFECT

Dependency/shared changes correctly selected FULL, but migration verification could return success
without running PostgreSQL when there was no Alembic revision diff. CI-003 remains `verified`; this
is corrective maintenance, with no new feature or roadmap change.

## REPRODUCTION

Before edits, an independent disposable Git clone of exact main
`d86c488488575265330c4294d3d6f4bf4293174d` received only a newline in `frontend/pnpm-lock.yaml`.
The real complete-tree planner selected FULL, full quality/integration and both production builds,
but `migration=true`, `migration_cycle=false`. The selected command actually ran:

```text
./scripts/verify-migration-cycle.sh d86c488488575265330c4294d3d6f4bf4293174d
migration verification: no Alembic revisions added
exit: 0
```

No database cycle ran. The precise original plan, command and output are preserved in the
[repair evidence](ci-003-full-migration-cycle-repair-evidence.json).

## ROOT CAUSE

Stage inclusion and forcing were independent booleans: FULL enabled `migration`, while the narrower
changed-file heuristic controlled `migration_cycle`. A successful conditional runner exit then
became a passed completed check and `migration_result=passed`, even after a skip.

## CONTRACT

- FOCUSED: explicit developer iteration commands; no canonical delivery receipt.
- AFFECTED: execute impact-required checks; migration may skip only when impact safely permits it.
- FULL: execute every exhaustive local stage, including real migration cycling without a revision diff.

Automatic escalation and explicit force-FULL have identical migration semantics. Dependency/shared
selection and exhaustive protected remote quality/integration/build are unchanged.

## IMPLEMENTATION

The plan now carries `migration=skip|affected-cycle|full-cycle`. The executor rejects a FULL plan with
any weaker decision. Every required cycle passes the existing `--force-cycle` mechanism, so the
runner's legacy optional changed-file shortcut cannot suppress a selected stage. There is no second
force mechanism or force-narrow override.

## AFFECTED BEHAVIOR

| Input                                               | Actual mode                    | Migration    |
| --------------------------------------------------- | ------------------------------ | ------------ |
| Docs only                                           | AFFECTED                       | `skip`       |
| Scoped frontend only                                | AFFECTED                       | `skip`       |
| Scoped domain, no migration                         | AFFECTED                       | `skip`       |
| Alembic revision change                             | FULL, conservatively as before | `full-cycle` |
| Dependency/lockfile, no migration diff              | FULL                           | `full-cycle` |
| Explicit force-FULL, with or without migration diff | FULL                           | `full-cycle` |

Current rules escalate every Alembic change to FULL; no bounded affected migration policy was
invented. The supported `affected-cycle` executor decision is separately tested as unconditional
when required. Docs/frontend/domain skip tests exercise the executor, not just selector booleans.

## FULL BEHAVIOR

The dependency-only orchestration fixture proves selection and execution of full quality,
integration, both production builds and forced migration. Its product commands and Docker metadata
are simulated to keep it offline; this is executor regression coverage, not a claim of product-suite
acceptance. Real PostgreSQL migration and resource cleanup are independently exercised below.

## MIGRATION EXECUTION

The repository-authoritative sequence remains upgrade to the literal base commit's single revision,
upgrade to code head, downgrade to that base revision, then re-upgrade to head. A backend verification
helper uses the same Alembic operations on guarded disposable PostgreSQL and checks the database's
current revision after each operation. It emits schema evidence only after all four succeed.

The disposable runner checks that evidence against the exact base and current source head, then
emits cycle success only after its existing ownership cleanup succeeds. Failed Alembic operations,
missing/mismatched evidence, caught interruptions and failed cleanup cannot produce success evidence.
When base equals head, the middle transitions need no revision DDL, but all four operations and state
checks still execute on a fresh PostgreSQL database; the existing chain must actually upgrade.

## RECEIPT

Version 2 remains sufficient: `migration` now records `decision`, `cycle_required`, `cycle_executed`,
`result` and evidence. A required stage's completed check includes four verified revision states and
`cleanup_verified=true`; a legitimate affected skip records `skipped_by_impact`, both cycle flags
false and null evidence. Exit zero alone cannot establish completed migration verification.

Writer and reader independently rederive the exact plan and expected commands/evidence. Historical
v2 receipts with boolean decisions or only `migration_result=passed` are incompatible and require
fresh canonical verification; they are explicitly tested. No receipt was written for this repair.

## DELIVERY VALIDATION

Delivery already invokes the shared fingerprint validator in preflight before push. Its actual
validator is tested through delivery preflight against a committed synthetic fixture: valid FULL
execution is accepted; skipped/missing/tampered cycle evidence and historical v2 are rejected before
push. Existing branch/base/map/tree/HEAD/completion safeguards remain intact. Delivery itself was
not invoked against Florabase or GitHub.

## REGRESSION TESTS

Coverage includes the affected/FULL matrix, refusal of lighter FULL decisions, automatic dependency
escalation and explicit force-FULL, actual orchestration commands, failed/quietly skipped runners,
valid FULL and affected receipts, incompatible old v2 and tampered/stale evidence, delivery preflight,
linked-worktree receipts and failure/signal/resource ownership cleanup.

`make smoke-migration-cycle` is a focused, receipt-free real PostgreSQL probe with four disposable
Git/Docker cases: automatic FULL without migration changes; explicit FULL without migration changes;
a synthetic revision that actually creates, downgrades/drops and re-upgrades/recreates a table; and
a broken existing migration committed in the synthetic base, with only a lockfile feature diff. The
last case must fail and must emit no cycle-success evidence. It does not modify deployed revisions.

## DOCKER CLEANUP

Every migration run uses an exact unique `feature-migration` owner/project, registered before
creation, and independently verifies zero owned container/network/volume/image residuals after
success or the expected failure. The database uses tmpfs; no persistent migration volume is created.
The existing real resource smoke additionally proves exact orphan/network/project-volume removal,
idempotence, protected synthetic environments and real persistent resource identities unchanged.
Shared BuildKit cache remains retained according to CI-003 policy; no global prune ran.

## FOCUSED CHECKS

- Selector/execution tests: **19 passed**.
- Feature verification/receipt/delivery fixture tests: **41 passed**.
- Workflow resource/migration failure tests: **14 passed**.
- Existing workflow helper shell fixtures: **all passed**.
- `make workflow-check`: Ruff lint/format and strict mypy, **14 + 2 source files**, passed.
- Backend cycle helper: configured Ruff lint/format and strict mypy with local source path, passed.
- Real direct forced cycle and `make smoke-migration-cycle`: passed; expected broken-chain failure
  was detected and cleaned up.
- `make smoke-workflow-resources`: passed; persistent resource identities unchanged.
- Bash syntax, feature graph (**99 valid**) and tracked/staged/untracked whitespace: passed.

Final canonical `make feature-verify` / `make verify-full` deliberately did not run. Luna owns that
gate. No new product quality/integration/build acceptance is claimed in this repair.

## DEPENDENCY SWEEP FOLLOW-UP

Dependency maintenance remains paused until this repair is delivered. PRs #24, #46 and #68 and their
branches were not modified, merged, closed or rebased in this task. No dependency version, product
behavior, API, schema migration, feature registry or protected remote CI change was made.

All repair edits remain unstaged and uncommitted on `fix/ci-003-full-migration-cycle` in the attached
managed worktree. Primary main remains clean at `d86c488`; no push, delivery or feature-finish ran.
The pre-existing dependency audit JSON/handoff and its earlier progress milestone are preserved as
separate audit context, not repair files to stage automatically. The operator must resolve their
disposition before freezing a delivery tree: canonical receipts include untracked source too.

READY_FOR_VISUAL_REVIEW
