# BETA-FOUNDATION-001 — implementation handoff for independent QA

Status: **READY_FOR_QA**, feature `implemented`, not `verified` and not beta GO.
Branch: `feat/beta-foundation-001`; baseline: `af2372c7e20468376b3d12904c83dee18133da84`.
Worktree: `/home/alessandro/Desktop/github/florabase-worktrees/beta-foundation-001`.
Writer: `codex-beta-foundation-001`; claim retained pending an explicit recipient handoff.
The final local commit/HEAD and tree are reported in the chat; they are not self-embedded in this file.

## Scope and review

[Audit, architecture and beta acceptance contract](beta-foundation-001.md) includes the source-backed
functional inventory, missing prerequisites/deferred features, host evaluation, image/runtime scope,
prioritized dependencies and acceptance criteria. Five corresponding entries were added to
`features.json`; no existing feature status or stable-release acceptance was changed. Deployment,
backup and roadmap documents point to the beta proposal without presenting it as implemented.

Retirement correction is confined to `scripts/feature_worktree.py` and its existing regression suite.
The original blanket per-directory write test was too strict for an empty child removable through
its parent. New preflight checks removal/traversal, refuses symlinks and mounted descendants and
fails closed without Linux mountinfo. Git removal remains unforced; existing finish/resource/writer/
dirty/ignored-file guards retain their ordering. No permission repair or deletion fallback exists.
The historical directories are gone; real Docker smoke reproduced the documented mountpoint cause.

Implementer self-review covered the complete diff, refusal before Git unregisters, ignored-cache
scope, linked worktree boundaries, parent/sticky permissions, no-follow traversal and same-device
mount evidence. This is not independent QA. No UI code/schema/dependency/runtime Compose changed;
no graphical product review is required for this infrastructure increment.

## Executed evidence

Commands ran from the linked worktree unless noted. Docker/GitHub in offline suites are PATH mocks;
Git repositories and kernel locks are real disposable fixtures.

| Check | Result |
| --- | --- |
| Initial narrow baseline: `python3 scripts/test-agent-workflow.py AgentWorkflowTests.test_regenerable_caches_do_not_block_retirement AgentWorkflowTests.test_retirement_refuses_every_unsafe_state` | 2 passed on unchanged source |
| Existing workflow suite during implementation | 50 passed |
| Final complete `python3 scripts/test-agent-workflow.py` | 55 discovered: 54 passed, 1 opt-in Docker smoke skipped |
| Final four new offline retirement cases (empty, nonempty, links/mounts, traversal/parents) | 4 passed after formatting/type correction |
| `FLORABASE_RETIRE_DOCKER_SMOKE=1 python3 scripts/test-agent-workflow.py AgentWorkflowTests.test_real_docker_root_owned_empty_mountpoint_retirement` | 1 passed; cached `node:24.19.0-bookworm-slim`, no network/persistent volume; root-owned empty host directory removed by ordinary fixture retirement |
| Red regression against original `af2372c` helper | Both positive cases fail with the original ownership refusal, including real Docker-created root-owned directory; expected failures, not unresolved defects |
| `make test-feature-workflow test-workflow-helpers` | 46 feature/delivery fixture tests passed; shell helper checks all passed |
| `make workflow-check AGENT_ID=codex-beta-foundation-001` | Passed: dependency policy, Ruff lint/format (30 files), strict mypy (19 + 5 files) |
| `python3 scripts/check-features.py` | 131 valid features, no dependency cycle |
| `git diff --check`, staged and untracked whitespace checks | Passed before local commit |
| `make verification-plan FORMAT=json` | Selects FULL: both workflow files are high-risk; both builds, all product/workflow suites and full migration cycle required |

Iteration failures were resolved: two early negative fixtures collapsed an entirely untracked
frontend directory in Git's ignored status; fixtures now include tracked frontend source. A direct
formatter invocation initially used the wrong configuration; unrelated formatting was restored and
the repository's explicit config applied. Strict typing caught a mixed stat tuple element in the
sticky-parent fixture; assignment now uses typed `st_mode`. No checks were weakened.

Non-secret local logs (ephemeral, not committed): `/tmp/beta-foundation-agent-tests.log`,
`/tmp/beta-foundation-adjacent-tests.log`, `/tmp/beta-foundation-workflow-check.log`,
`/tmp/beta-foundation-red.log`. Focused and Docker-smoke results were also returned directly in chat.
The red probe used the original Git object in disposable copied scripts, not a changed branch.

## Pending independent acceptance

The [canonical workflow](development-workflow.md#review-profiles-and-verification-timing) explicitly
assigns the frozen-tree canonical gate to a different QA agent/session. Therefore no canonical
`make feature-verify` or delivery receipt was produced in this implementation handoff. Full application
unit/integration tests, API drift, production builds and Alembic cycle were **not run** here; neither
were actual Dockhand/Tailscale deployment, backup restore, host soak or real-data onboarding. Those
future beta-runtime acceptance tasks are not foundation implementation evidence.

1. Use the writer handoff protocol to an identified QA recipient (no takeover by an agent), or review
   read-only in an isolated detached checkout. Treat this report as a claim, not verification proof.
2. Review inventory against source/feature statuses, deployment failure cases and narrowed code change.
   Challenge Linux-only retirement behavior and symlink refusal, evidence failures, same-device bind
   mounts, root-owned empty directories, dirty trees and owned Docker resources. Mount guards have
   deterministic mountinfo simulation; the real Docker smoke proves leftover host mountpoint behavior,
   not a privileged host bind-mount attack. Unavailable source directories correctly fail closed.
3. Run focused regressions for uncovered risks and the opt-in Docker smoke; fix ordinary defects.
4. Freeze source **and index**, then run once:

   ```bash
   make feature-verify AGENT_ID=<qa-recipient>
   ```

   It selects FULL automatically. Do not substitute an affected gate or manually repeat its covered
   stages. Record any environmental limit exactly. Update feature status only after every criterion
   has evidence; a documentation change after a gate invalidates exact-tree verification.
5. Stop for the operator. This request does not authorize push, delivery, merge or feature-finish.

Quality project `florabase-quality-ae6f77a16b92` contains only this worktree's quality resources and is
retained by normal workflow policy. Disposable smoke containers used `--rm`; no real finished worktree
was retired. Existing DEV, Review, UAT, production data and source were not intentionally modified.
The quality mount can leave an ignored empty host `frontend/node_modules`; it is not source/delivery
content. Do not delete shared volumes or run broad Docker cleanup for this handoff.

Open decisions before beta runtime: actual NAS/DSM or VPS specifications/capacity and chosen architecture;
collection/input/media scale; stable tailnet hostname/users/devices; independent encrypted backup target,
key custody and accepted RPO/RTO/retention; maintenance outage; day-one optional WFO/WCVP requirements.
These do not block independent QA of the foundation increment.
