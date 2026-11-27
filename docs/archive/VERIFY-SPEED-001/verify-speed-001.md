# VERIFY-SPEED-001 — Canonical FULL Wall-Time Reduction and Two-Lane Gate Proposal

Date: 2026-11-22. Branch: `ci/verify-speed-001` (from `origin/main` `16ccf4b`).

## Implemented changes (Items 1–4)

1. **Golden dataset closure stage (`golden-dataset`)**
   - `backend/tests/integration/test_golden_dataset.py` now uses the same module-level
     `explicitly_selected` autouse fixture as `test_golden_comprehensive.py` (`SEARCH_PATH =
     "test_golden_dataset"`). The default `make test-integration` run collects and skips all Golden
     SMOKE cases with a clear reason, while `make golden-dataset-check` names the file explicitly
     and executes all 35 tests (including both `test_the_full_suite_skips_the_comprehensive_module`
     and the new `test_the_full_suite_skips_the_golden_dataset_module`).
   - `scripts/verification-impact.json` declares `golden_prefixes` (validated by `load_map()`),
     derived from imports and fixtures of the Golden tooling:
     - `scripts/golden_plan.py`
     - `scripts/golden_dataset.py`
     - `scripts/dev_golden` (`dev_golden.py`, `dev_golden_snapshot.py`, `dev_golden_payload.py`)
     - `scripts/test-dev-golden.py`
     - `scripts/smoke-dev-golden.py`
     - `scripts/uat_fixture.py` (imported by `golden_dataset.py`)
     - `scripts/review_dataset_v5.py` (imported by `golden_dataset.py`)
     - `scripts/attachment_artifacts.py` (imported by `dev_golden_payload.py`)
     - `scripts/test-integration.sh`
     - `scripts/fixtures/golden/`
     - `scripts/fixtures/botanical-v5/` (loaded by `review_dataset_v5.py`)
     - `backend/alembic/`
     - `backend/src/florabase/` (Golden tooling imports ~30 domain packages plus `florabase.main`)
     - `backend/pyproject.toml`
     - `backend/requirements` (`requirements.lock`, `requirements-dev.lock`)
     - `backend/uv.lock`
     - `backend/Dockerfile`
     - `compose.dev.yaml`
     - `Makefile`
     - `backend/tests/integration/test_golden_dataset.py`
     - `backend/tests/integration/test_golden_comprehensive.py`
     - `backend/tests/integration/conftest.py`
     - `backend/tests/conftest.py`
   - `scripts/verification_impact.py` sets `plan["golden_dataset"]` to `True` only when changed
     paths intersect `golden_prefixes`, when any path cannot be classified (fail-closed), or when
     `force_golden=True` (used by `scripts/ci-verify.py` on `main` push CI and fallback paths so
     `main` remains exhaustive). `scripts/verification_gate.py` appends `golden-dataset`
     (`make golden-dataset-check`) after `integration` when `plan["golden_dataset"]` is `True`;
     `REUSABLE_STAGES` remains `{"quality", "integration"}` (the Golden stage is never reused).
2. **Bounded Vitest file parallelism**
   - Git history showed `fileParallelism: false` was introduced in PR #12 (`76ec29f9`, 2026-09-03)
     when the suite had 93 tests; the later `UX004` flake was fixed independently in
     [`docs/archive/UX-004/ux004-flake-001.md`](../UX-004/ux004-flake-001.md) by wrapping `vi.dynamicImportSettled()` in
     async `act()`. In addition, `scripts/compose_stacks.py` pinned `VITEST_MAX_WORKERS: "1"` in
     the `quality` Compose override.
   - `frontend/vite.config.ts` now enables `fileParallelism: true`, `pool: "forks"`, and
     `maxWorkers` defaulting to `3` (overridable via `VITEST_MAX_WORKERS` for small hosts), while
     retaining `testTimeout: 15_000`. `scripts/compose_stacks.py` changes the `quality` default to
     `VITEST_MAX_WORKERS: "${VITEST_MAX_WORKERS:-3}"`.
   - Five consecutive local `make test-frontend` runs passed with zero flakes and zero retries
     (127 files, 1,414 tests each): `96.84 s`, `98.33 s`, `96.01 s`, `96.12 s`, `96.43 s` (down
     from `~258 s` serial on this host and `318 s` in CI).
3. **`workflow-check` consolidation**
   - `Makefile` replaces the seven separate backend `$(DEV_COMPOSE) run` invocations with one
     container run executing all seven steps (`ruff check`, `ruff format --check`, and `mypy
     --strict` for workflow scripts, runtime-client scripts, and app-context scripts) in sequence.
     File lists live in shared Make variables (`WORKFLOW_RUFF_FILES`, `WORKFLOW_MYPY_STRICT_FILES`,
     `WORKFLOW_RUNTIME_CLIENT_FILES`, `WORKFLOW_APP_MYPY_FILES`). Every step always runs; any
     failure prints the failing step names to stderr and exits `1`.
   - Mypy receives a disposable, worktree-owned cache directory under
     `$(git rev-parse --absolute-git-dir)/florabase-mypy-workflow-cache` (separate subdirs per
     invocation flags/`MYPYPATH`, never shared across worktrees, never a named Docker volume, and
     never touching the working tree). Verified host-UID ownership: `compose.dev.yaml` runs
     `backend` as `user: "${LOCAL_UID:-1000}:${LOCAL_GID:-1000}"` with the invoking host UID:GID
     propagated by `workflow_environment.py`, so all files under
     `.git/worktrees/<name>/florabase-mypy-workflow-cache` are host-owned (`0` root-owned files)
     and cleanly removable by `make feature-retire`.
   - Measured locally: `33.06 s` before -> `27.16 s` cold cache / `23.73 s` warm cache after (the
     backend container portion drops from `~14 s` to `~8 s` cold / `~4.5 s` warm; GitHub Actions
     runners avoid 6 container startups + BuildKit checks).
4. **Hygiene and `test-stage-evidence.py` profile**
   - Removed the retired `deploy/` entry from `full_prefixes` in
     `scripts/verification-impact.json` (any reintroduced `deploy/` path still escalates to FULL
     fail-closed as unclassified).
   - Added manual `make smoke-beta-lifecycle` for `scripts/test-beta-lifecycle.py` and documented it
     as a manual real-Docker probe in
     [`docs/beta-image-001-final-reliability.md`](../BETA-IMAGE-001/beta-image-001-final-reliability.md).
   - Profiled `scripts/test-stage-evidence.py` (22 tests, `110.26 s` total):

| Test | Elapsed | Notes |
| --- | ---: | --- |
| `GateEvidenceTests.test_failed_interrupted_and_self_mutating_stages_leave_no_record` | 14.81 s | 5 full gate runs + interrupted slow stage |
| `GateEvidenceTests.test_concurrent_gates_in_one_worktree_refuse_and_records_stay_intact` | 12.76 s | 2 full gate runs + `VERIFY_SLOW_SECONDS=6` |
| `InvalidationTests.test_application_sources_tests_contracts_and_migrations` | 10.95 s | `setUp` full gate + 14 `decisions()` subprocesses |
| `GateEvidenceTests.test_new_commit_and_index_or_head_drift_never_inherit_a_receipt` | 10.03 s | 3 full gate runs |
| `InvalidationTests.test_configuration_environment_tools_images_and_policy` | 9.20 s | `setUp` full gate + 11 `decisions()` subprocesses |
| `GateEvidenceTests.test_default_fresh_dry_run_and_invalid_controls` | 8.66 s | 3 full gate runs + 3 refusal checks |
| `GateEvidenceTests.test_receipt_version_3_and_version_2_compatibility` | 8.25 s | 3 full gate runs + 10 receipt verifications |
| `GateEvidenceTests.test_cache_hit_reuses_only_quality_and_integration_and_never_delivers` | 6.73 s | 3 full gate runs |
| `InvalidationTests.test_dry_run_requires_fresh_and_valid_timestamps` | 6.45 s | `setUp` full gate + 9 `decisions()` subprocesses |
| `InvalidationTests.test_corrupt_truncated_tampered_schema_and_foreign_records_run_fresh` | 6.44 s | `setUp` full gate + 9 `decisions()` subprocesses |
| `GateEvidenceTests.test_docs_only_edit_after_full_reuses_proven_stages_and_reruns_the_rest` | 4.73 s | 2 full gate runs |
| `InvalidationTests.test_documentation_and_volatile_labels_do_not_invalidate` | 4.20 s | `setUp` full gate + commit + `decisions()` |
| `InvalidationTests.test_distinct_worktrees_never_share_evidence` | 3.87 s | `setUp` full gate + linked worktree |
| `GateEvidenceTests.test_records_never_store_environment_or_env_file_values` | 3.18 s | 1 full gate run |
| `ClosureClassificationTests.*` (8 unit tests) | 0.00 s each | Pure in-process unit tests |

Because every fixture test exercises real `feature-verify.sh` -> `verification_gate.py` ->
`stage_evidence.py` subprocess flows against isolated bare/cloned Git repositories and `FAKE_DOCKER`,
shrinking them would reduce end-to-end subprocess/fixture coverage; they are left unchanged.

---

## Design Note Only (Not Implemented): Two Parallel Lanes in `run_checks()`

### Proposal

Keep the six fast source-state checks (`feature-graph`, `doc-links`, `test-doc-links`, `whitespace`,
`staged-whitespace`, `untracked-whitespace`; `~0.5 s` combined) strictly sequential at the start of
`verification_gate.run_checks()` so any metadata, link, or whitespace defect still fails before
launching workflow tests or Docker.

Once source checks pass under the existing `verification_lock(metadata)` and machine-wide
`machine_lock("verification-full", ...)`, split the remaining stages into two concurrent worker
lanes (`ThreadPoolExecutor(max_workers=2)`):

- **Lane A (host offline suites + worktree Quality project):**
  `test-workflow-helpers` -> `test-feature-workflow` -> `test-agent-workflow` ->
  `test-preview-workflow` -> `test-environment-workflow` -> `test-uat-preview` ->
  `test-verification-impact` -> `test-workflow-resources` -> `test-ui-page` ->
  `workflow-check` -> `quality` (`make check`).
- **Lane B (disposable Docker stages):**
  `production-builds` -> `migration-cycle` -> `integration` (-> `golden-dataset` when selected).

Single-lane mode remains the automatic default for `docs`, `affected`, and `product-frontend` tiers
(where one lane would be empty or trivial) and whenever only one lane has stages.

### Host capacity and CPU/RAM contention

Measured directly on the operator workstation (`2026-11-22`):

- **CPU:** AMD Ryzen AI 9 HX 370 — 12 physical cores / **24 logical CPUs** (`nproc` = `24`, Docker
  `NCPU=24`).
- **Memory:** **60 GiB RAM** (`65,407,602,688` bytes, `44 GiB` available, `8.0 GiB` swap).
- **Docker storage/network:** `overlayfs`, `DefaultAddressPools=[]` (default 29 bridge subnets).

Observed concurrency profile of Lane A + Lane B:

1. **First ~290 s (non-overlapping heavy work):** Lane A runs single-threaded Python/Git fixture
   tests (`test-agent-workflow`, `test-verification-impact`, `test-feature-workflow`; ~1–2 cores,
   `<1 GiB` RAM) while Lane B runs cached `production-builds` (~3 s), `migration-cycle` (~9 s), and
   single-process `pytest` + tmpfs PostgreSQL in `integration` (~1–2 cores, ~1.5–2 GiB RAM). Total
   utilization is ~2–4 cores and ~2–3 GiB RAM, comfortable even on a 4-core / 16 GiB host.
2. **Non-Golden FULL completion boundary:** Without `golden-dataset`, Lane B finishes around
   `t ≈ 307 s` — right around the time Lane A reaches `workflow-check` (`t ≈ 290 s`) and *before*
   Lane A starts Vitest (`t ≈ 350 s`). Thus 3-worker Vitest and PostgreSQL `integration` barely
   overlap at all on non-Golden FULL runs.
3. **Golden-closure FULL overlap:** When `golden-dataset` is also selected (+~350 s in Lane B),
   Lane A's `quality` (3 forked jsdom Vitest workers, ~3 cores, ~2–3 GiB RAM) overlaps Lane B's
   `golden-dataset` (~1–2 cores, ~1.5 GiB RAM). On the 24-CPU / 60 GiB workstation this stays under
   25% CPU and 10% RAM. On a **4-core / 8–16 GiB host**, simultaneous 3-worker Vitest +
   PostgreSQL/Golden subprocesses can oversubscribe CPU and risk jsdom timeouts (`15_000 ms`).
   **Recommended guard:** enable two lanes by default only when `os.cpu_count() >= 8` (or explicit
   `FLORABASE_VERIFY_LANES=2`), and cap `VITEST_MAX_WORKERS=2` if forced on `<= 6`-core hosts.

### Docker address-pool and BuildKit contention

- **Address pools:** Lane A's Quality stack (`compose_stacks.py`) sets `network_mode: none` and
  `networks: !reset []` on every service, allocating **0 Docker networks**. Lane B runs
  `production-builds` (0 networks), `migration-cycle` (1 disposable network, torn down before exit),
  `integration` (1 disposable network, torn down before exit), and `golden-dataset` (1 disposable
  network, torn down before exit) sequentially. Peak concurrent Docker bridge networks = **1**,
  identical to serial execution.
- **BuildKit contention:** Lane B invokes `production-builds` at `t = 0` (`backend` and `frontend`
  production targets) and the `integration` backend dev target shortly after (`t ≈ 12 s`), whereas
  Lane A does not touch Docker until `workflow-check` (`t ≈ 290 s`). On warm caches both builds take
  `<4 s` and never collide. On a completely cold cache (e.g., fresh runner after lockfile edits),
  BuildKit handles concurrent solves safely against the shared daemon cache, though concurrent cold
  `pnpm install` / `pip install` layers would double transient disk/RAM I/O; on cold-cache runs,
  either accepting BuildKit serialization or running `production-builds` before the fork avoids any
  memory spike.
- **Stage evidence (`REUSABLE_STAGES = {"quality", "integration"}`):** `stage_evidence.py` filters
  container events strictly by `com.docker.compose.project` (`florabase-quality-<hash>` vs
  `florabase-integration-*`) and writes atomically to distinct files (`quality.json` vs
  `integration.json`). Because neither lane mutates tracked/untracked worktree files, `Recording`
  remains isolated per stage; only `write_journal()` needs a `threading.Lock`.

### Output handling (per-lane logs + live summary)

- Inheriting stdout/stderr directly from two concurrent lanes would interleave pytest, Vitest, Ruff,
  and BuildKit progress bars unreadably.
- Instead, create an untracked per-run directory `<git-dir>/info/verification-logs/<run-id>/` with
  `lane-a.log` and `lane-b.log` (pruning older runs beyond e.g. the last 5).
- Each lane redirects stage stdout/stderr into its lane log (still capturing `migration-cycle`
  stdout cleanly to parse `MIGRATION_REPORT` verbatim).
- The main thread prints concise lock-serialized progress lines to stdout (`[lane-a] start quality`,
  `[lane-b] pass integration 285.40s`) and prints the full `Stage summary` at the end. On any stage
  failure, print the tail of the failing stage's lane log (e.g. last 120 lines) plus the exact path
  to the complete log file.

### Fail-fast across lanes

- Share a `threading.Event` (`abort_event`) and a lock-protected `active_procs: dict[str, Popen]`
  between both lanes.
- Launch every stage subprocess with `start_new_session=True` so each stage owns a dedicated process
  group.
- When either lane fails (non-zero exit or invalid `MIGRATION_REPORT`):
  1. Set `abort_event` so the sibling lane never starts another queued stage.
  2. Send `SIGTERM` to the sibling lane's active process group (`os.killpg(pgid, signal.SIGTERM)`),
     allowing disposable runners (`disposable_workflow.py`, `verify-migration-cycle.sh`,
     `test-integration.sh`) to execute their cleanup traps cleanly.
  3. Wait up to a bounded grace window (`30 s`, matching `Disposable.run`'s quiescence window) for
     the sibling to exit and emit `RESOURCE_CLEANUP_PASSED`; only escalate to `SIGKILL` on timeout
     with an explicit diagnostic instructing `make workflow-resources`.
  4. Abort any active `stage_evidence.Recording` in both lanes so interrupted or aborted stages
     never write evidence records.

### Receipt exactness (`validate_execution()`)

- `validate_execution()` compares `json.dumps(completed, sort_keys=True)` against `expected` built
  strictly in `checks_for(plan)` order.
- Under two lanes, `run_checks()` stores each passing stage dict in a map keyed by `check["id"]`
  (or original index in `checks`) and materializes the returned `completed` list strictly in
  `checks_for(plan)` order — **never** completion order.
- The receipt schema (`version: 3`), `validate_execution()`, frozen-tree comparison, and delivery
  preflight require **zero format changes**.
- The diagnostics journal (`florabase-verification-last-run.json`) records stages in plan order with
  an optional `lane` field and a top-level `wall_elapsed` so overlapping stage durations are never
  confused with total wall time.

### Interrupt (`SIGINT` / `SIGTERM`) and cleanup

- Catch `KeyboardInterrupt` (and handle `SIGTERM`) in the coordinator thread, set `abort_event`,
  send `SIGINT`/`SIGTERM` to **both** active process groups via `os.killpg`, wait up to `30 s` for
  both disposable runners to complete cleanup, abort active `stage_evidence.Recording` instances,
  record `"interrupted"` for active stages and `"not run"` for unstarted stages in the journal,
  print `Stage summary` and lane log paths to stderr, and exit `130` without writing a receipt.

### Estimated wall-time savings from measured stage times

Baseline local FULL measured on this workstation (`wf_scope_minimal_compose_batch`, 2026-11-22,
pre-`VERIFY-SPEED-001`): **`1,354.83 s` (`22m 35s`)** serial.

| Stage group | Pre-`VERIFY-SPEED-001` (Batch 10) | Post Items 1–3 (serial est.) | Lane |
| --- | ---: | ---: | --- |
| Source checks (6 stages) | 0.51 s | ~0.5 s | Serial prefix |
| Offline workflow suites (9 stages) | 289.20 s | ~289 s | Lane A |
| `workflow-check` | 33.26 s | ~24–27 s | Lane A |
| `quality` (`make check`) | 374.38 s | ~212 s (Vitest ~96 s vs ~258 s) | Lane A |
| `production-builds` (cached) | 3.29 s | ~3 s | Lane B |
| `migration-cycle` | 9.11 s | ~9 s | Lane B |
| `integration` (excl. Golden) | 645.10 s (incl. Golden) | ~295 s (645 s − 350 s) | Lane B |
| `golden-dataset` (only when closure touched) | *(included above)* | ~350 s | Lane B |

Projected wall time on this workstation:

- **Non-Golden FULL (typical workflow/infra/product-wide change):**
  - Serial after Items 1–3: `0.5 + 525 + 307` ≈ **`833 s` (`13.9 min`)** (already `~522 s` / `8.7 min`
    faster than the `1,355 s` Batch 10 baseline).
  - With two parallel lanes: `0.5 + max(525, 307)` ≈ **`526 s` (`8.8 min`)** — an additional
    **`~307 s` (`~5.1 min`, ~37%)** wall-time reduction.
  - Critical path shifts completely from `integration` to **Lane A** (`test-agent-workflow` 127 s +
    `test-verification-impact` 129 s + `quality` 212 s).
- **Golden-closure FULL (e.g. migration, `db/`, or Golden script change):**
  - Serial after Items 1–3: `0.5 + 525 + 657` ≈ **`1,183 s` (`19.7 min`)**.
  - With two parallel lanes: `0.5 + max(525, 657)` ≈ **`658 s` (`11.0 min`)** on a 24-CPU host —
    an additional **`~525 s` (`~8.8 min`, ~44%)** wall-time reduction.

No parallel-lane execution code is implemented in `VERIFY-SPEED-001`; operator decision is required
before scheduling a follow-up increment.
