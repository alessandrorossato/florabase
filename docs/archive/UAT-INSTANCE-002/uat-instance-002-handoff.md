# UAT-INSTANCE-002 handoff — stale launch handling on rebuilt branches

27 November 2026 · `ci/uat-instance-002` · writer `antigravity-neon-uat-instance-002` · base `c83d8163` (fast-forwarded from batch 14b `7b667a47` after `v0.1.0-beta.10` landed on `origin/main`).
Operator contract: [development workflow](../../development-workflow.md#uat-instances-parallel-per-worktree).
Proposed release class in `docs/release/scope-v1.json`: **`best-effort`** (registered right after `MULTIBRANCH-UAT-001` in both `docs/features.json` and `docs/release/scope-v1.json`).

## Problem reproduction (before vs after)

When `make feature-batch-prepare` (or `git reset --hard`) rebuilds an attached branch from scratch, existing `florabase-uat-branch-*` containers still carry `io.florabase.sha=<old_tip>`, which is no longer an ancestor of `HEAD`.

**Before the fix (on unmodified base `7b667a47`):**

Rebuilding a linked `ci/batch-14` worktree (`old_tip=4e4fea8e...`, `new_tip=9b87b036...`) made every `uat-instance-*` lifecycle command call `UATPreview.require_identity()` → `delivered()` → `gh api repos/alessandrorossato/florabase/commits/<old_tip>/pulls`, failing with HTTP 422:

```text
gh: No commit found for SHA: 4e4fea8ec410efcd016fed3c1de5b6a68dc97b62 (HTTP 422)
[status] FAILED (WorkflowError): command failed: gh api repos/alessandrorossato/florabase/commits/4e4fea8ec410efcd016fed3c1de5b6a68dc97b62/pulls
[stop] FAILED (WorkflowError): command failed: gh api repos/alessandrorossato/florabase/commits/4e4fea8ec410efcd016fed3c1de5b6a68dc97b62/pulls
[reset] FAILED (WorkflowError): command failed: gh api repos/alessandrorossato/florabase/commits/4e4fea8ec410efcd016fed3c1de5b6a68dc97b62/pulls
[remove] FAILED (WorkflowError): command failed: gh api repos/alessandrorossato/florabase/commits/4e4fea8ec410efcd016fed3c1de5b6a68dc97b62/pulls
```

**After the fix:**

With zero `gh` calls (`uat_source.run` never invoked):

```text
db: stopped; source: /tmp/repro-after-.../batch-14; launched HEAD: d6a96a5f... (stale: not in current history)
Owner: valid (stale launch)
Next: make uat-instance-up to rebuild from HEAD, or make uat-instance-reset CONFIRM_RESET_UAT_INSTANCE=florabase-uat-branch-ci-batch-14
```

`status`, `stop`, `up`, guarded `reset`, and guarded `remove` succeed without manual `docker rm`; `seed` and `validate` refuse with `run make uat-instance-up first`.

## Design summary

- **`scripts/uat_source.py`**:
  - Added `in_worktree_reflog(repo, sha, branch)`: validates `sha` matches `[0-9a-f]{40}`, confirms `git cat-file -e <sha>^{commit}` succeeds in the local repository, and checks that `sha` appears in this worktree's `HEAD` reflog or its current branch's `refs/heads/<branch>` reflog (`git reflog show --format=%H`). Commits from other branches/worktrees or unknown SHAs fail. Note on reflog scope: `refs/heads/<branch>` reflog is shared across worktrees in the common `.git` directory and a worktree's `HEAD` reflog includes other branches that worktree previously had checked out; this is acceptable because all container and volume `io.florabase.source` and `com.docker.compose.project.working_dir` labels (plus project, role, mounts, network, ports and foreign volume users) must still match this exact worktree before `verify_launched_sha()` is evaluated.
  - Hardened `delivered(repo, sha=None, *, make_prefix="uat-preview")`: catches `(WorkflowError, json.JSONDecodeError)` and non-list responses from `gh api ...`, raising a single clear `WorkflowError` with the 12-char SHA and caller-scoped next command (`uat-preview` vs `uat-instance`) instead of a raw `command failed: gh api ...` / 422 error.
- **`scripts/uat_preview.py`**:
  - Extracted `verify_launched_sha(launched, *, stale_ok=False, allow_expired_sha=False)` and `check_upgradeable(current, graph)` hooks. `UATPreview` keeps the exact existing `ancestor()` / `delivered()` rule regardless of `stale_ok` or `allow_expired_sha`, preserving singleton UAT Preview and detached-owner semantics unchanged.
  - Deferred `verify_launched_sha` in `require_identity()` until after every volume, container, state, network, port, mount, environment, and `require_resource_users()` check passes (while keeping the 40-hex format check in the container loop), so foreign containers are always refused first.
- **`scripts/uat_instance.py`**:
  - Overrides `verify_launched_sha`: detached worktrees delegate straight to `super()` (`delivered()`); attached worktrees never call `gh api`, accept ancestor SHAs normally, accept reflog-proved non-ancestor SHAs when `stale_ok=True` (and refuse with `run make uat-instance-up first` otherwise), and accept expired 40-hex SHAs only when `allow_expired_sha=True` (confirm-guarded `reset`/`remove` after all other checks pass).
  - Overrides `check_upgradeable`: keeps `require_upgradeable` intact and appends the exact guarded `make uat-instance-reset CONFIRM_RESET_UAT_INSTANCE=<project>` command on incompatibility, without auto-resetting or deleting data.
  - Updates `status()` to mark non-ancestor launched SHAs as `launched HEAD: <sha> (stale: not in current history)` and print the rebuild/reset next step.
- **`scripts/feature_batch.py`**:
  - Prints a one-line note at the end of `prepare()` when `owned_resources(repo)` reports a `florabase-uat-branch-*` instance on the batch worktree (`its running launch predates these merges; run make uat-instance-up to rebuild from HEAD`), catching `WorkflowError` and `ResourceError` in separate clauses so `ruff format` (targeting Python 3.14) cannot strip parentheses into PEP 758 syntax incompatible with CI's Python 3.12 runner. The Python 3.12 AST parse regression in `scripts/test-uat-instance.py` now covers `feature_batch.py` and the `scripts/ci-verify.py` host-run import graph. Known pre-existing follow-up (left untouched, as both run inside Python 3.14 containers): `scripts/license_check.py:96` and `scripts/golden_dataset.py:1151` carry the same parentheseless PEP 758 `except` form.

## Open checks answered

1. **`require_identity()` callers (`uat_preview.py` / `uat_instance.py`)**:

   | Caller | Flags passed | Attached `UATInstance` stale launch | Singleton `UATPreview` / detached owner |
   | --- | --- | --- | --- |
   | `UATInstance.status` | `stale_ok=True` | Allowed; reports stale + next step | Unchanged (`delivered()`) |
   | `UATPreview.stop` (x2) | `stale_ok=True` | Allowed (stops proved containers) | Unchanged (`delivered()`) |
   | `UATPreview.up` (pre-build) & `stop_writers(stale_ok=True)` | `stale_ok=True` | Allowed (rebuilds & relabels from HEAD) | Unchanged (`delivered()`) |
   | `UATPreview.up` (post-`compose up`) | `running=True` (`stale_ok=False`) | Must match HEAD (refuses if still stale) | Unchanged |
   | `UATPreview.reset` (x2, after `confirm == project` & attached check) | `stale_ok=True, allow_expired_sha=True` | Allowed (also reflog-expiry fallback) | Refused (detached) / Unchanged (preview) |
   | `UATPreview.retirement_resources` (from `remove` after `confirm == project`) | `retiring=True, stale_ok=True, allow_expired_sha=True` | Allowed (also reflog-expiry fallback) | Unchanged (`delivered()`) |
   | `UATInstance.seed`, `validate_dataset`, `golden` | `running=True` (`stale_ok=False`) | Refused (`run make uat-instance-up first`) | Unchanged |
   | `UATPreview.sync` (x5) & `stop_writers()`, `fixture`, `seed`, `status` | default (`stale_ok=False`) | N/A | Unchanged (`delivered()`) |

2. **`feature-batch-prepare` hint**: Implemented in `scripts/feature_batch.py` (13 lines, reusing already-imported `owned_resources(repo)` inside `try/except WorkflowError` so offline/no-Docker invocations remain unaffected; covered by unit test).
3. **Reflog expiry (`git gc` / 30-day unreachable expiry)**: Yes, `git reflog expire` / `git gc` removes unreachable commits from the reflog, after which `in_worktree_reflog` returns `False`. Implemented the confirm-guarded fallback: `status`, `stop`, `up`, `seed`, and `validate` still refuse any unknown/expired SHA, while `make uat-instance-reset CONFIRM_RESET_UAT_INSTANCE=<project>` and `make uat-instance-remove CONFIRM_REMOVE_UAT_INSTANCE=<project>` pass `allow_expired_sha=True` on an attached `UATInstance` **only** after `confirm == self.project` and after every other container, volume, network, mount, port, environment, 40-hex SHA format, and foreign-volume-user check passes.

## Checks and real Docker smoke evidence

| Check | Result |
| --- | --- |
| `make test-uat-preview` (`test-uat-preview.py` 20, `test-uat-source.py` 18, `test-uat-instance.py` 22) | 60 passed |
| `make workflow-check` (ruff check/format, strict mypy 44 + 2 + 6 files, `test-beta-images` 86, `test-beta-runtime` 20 / 0 disclosures, mobile asset determinism) | Pass |
| `make test-agent-workflow` | 81 passed (3 skipped) |
| `make test-feature-workflow`, `make test-environment-workflow` (44 + 7), `make doc-links` (398 docs), `scripts/check-features.py` (205 features) | Pass |
| `make smoke-uat-instance` (disposable Docker, incl. Step 6 branch-rewrite stale launch) | **Pass**, 0 residual state |
| `make smoke-uat-preview` (disposable Docker, singleton + delivered owner sync) | **Pass**, 0 residual state |
| Canonical `make feature-verify AGENT_ID=antigravity-neon-uat-instance-002` (FULL) | Run after tree freeze (recorded in receipt) |

**Real Docker smoke (`make smoke-uat-instance`) before/after `io.florabase.sha` labels:**

- Before rewrite (`old_tip`): `{"backend": "2e3ace714c712ec01571dd4bd5d8a92c5fa6c0dc", "db": "2e3ace714c712ec01571dd4bd5d8a92c5fa6c0dc", "dev-state-init": "2e3ace714c712ec01571dd4bd5d8a92c5fa6c0dc", "frontend": "2e3ace714c712ec01571dd4bd5d8a92c5fa6c0dc"}`
- After `git reset --hard` + sibling commit (`20843084...`): `status` reported `launched HEAD: 2e3ace714c712ec01571dd4bd5d8a92c5fa6c0dc (stale: not in current history)` and `Owner: valid (stale launch)`; `seed` and `validate` refused (`run make uat-instance-up first`); `stop` succeeded; `up` preserved the database digest and relabeled all four containers to `20843084bcc3c393fc05be5774982b132cac9596`.
- After second rewrite (`9fef3b66...`): guarded `reset` recreated and reseeded cleanly without manual `docker rm`, relabeling all four containers to `9fef3b66ff82731a204b8975b98580a02e35c893`; `validate_dataset() == 0`; cleanup removed all disposable containers/networks/volumes/images with `residual_containers_networks_volumes=0`.
