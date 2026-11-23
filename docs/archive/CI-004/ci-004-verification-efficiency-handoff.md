# CI-004 — Verification efficiency handoff

## Initial audit and implementation plan

Base: `3902b92146f3afc21184e658dae64385e33f4926` (merged Geography #122).
Branch: `ci/ci-004-verification-efficiency`, attached worktree `a4b0`.
Initial review boundary: leave changes unstaged/uncommitted; no push, PR, delivery or finish.

The local CI-003 planner already selects affected checks and enforces FULL for infrastructure,
security, dependencies, migrations and unknown paths. The remote workflow runs three independent
jobs with exhaustive application checks on every PR and main push. Superseded runs already cancel.
Feature-finish checks merge/Git/resource safety and does not run application suites.

Measured GitHub runs #231/#232/#233 show workflow helpers taking 71/90/77 seconds before quality.
Successful #232/#233 quality took 508/494 seconds; integration 213/199; build 47/51.
The initial offline baseline passed 19 selector/receipt tests, 14 resource tests and 41 feature/
delivery tests. No expensive product suite was run for benchmarking.

Implement bounded changes:

1. Recompute impact independently inside each existing required job, against the validated PR
   merge parents; absent/inconsistent event metadata forces exhaustive verification. Main stays full.
2. Docs-only PRs execute graph/whitespace checks in all three jobs. Affected product PRs omit only
   workflow helpers. All product PRs retain complete application suites, API/static checks,
   PostgreSQL integration and both builds. Narrow remote product tests are deferred.
3. Preserve original output, add stage duration/exit/recovery information, retain full CI logs.
4. Repair explicit local test inventory drift and conservatively escalate shared map/style modules.
5. Exercise real synthetic Git/event/failure cases and existing helper safety suites. Independent
   QA and one policy-selected FULL canonical gate remain required before delivery.

The following sections record the implemented scope and review evidence.

## Implemented architecture and command matrix

`scripts/ci-verify.py` is a small adapter over CI-003's planner and stage executor, not a second
selector or receipt format. Every required job checks out the platform merge commit with depth-two Git
history (merge plus both parents) and credentials disabled. For a PR it checks that `HEAD` equals `GITHUB_SHA` and its exact
ordered parents equal the event's base and head SHAs. It compares the complete merge result to that
immutable base, including conflict-resolution content, modes, both rename sides, deletions and
unexpected dirty/index/untracked files. It does not compare to a later-moving `origin/main`.
Missing/invalid platform SHA or a checkout at another SHA refuses before running checks. Once the
checkout identity is proven, unsupported events, missing impact metadata and mismatched parents
force FULL. A head-only checkout matching the platform SHA cannot narrow without exact merge parents.
Unreadable/invalid policy fails the job. Main always runs exhaustive remote verification.

| Remote job / change | Before | Implemented |
| --- | --- | --- |
| `quality`, docs-only PR | All workflow helpers + `make check` | Feature graph + tracked/staged/untracked whitespace checks |
| `integration`, docs-only PR | `make test-integration` | Same real repository checks |
| `build`, docs-only PR | `make build` | Same real repository checks |
| `quality`, affected product PR | All helpers + complete `make check` | Graph + complete `make check`; omit only workflow helpers |
| `quality`, FULL or main | All helpers + complete `make check` | Same complete helpers/check + explicit feature graph |
| `integration`, every product PR/main | Complete PostgreSQL integration | Same complete suite, new disposable project per execution |
| `build`, every product PR/main | Both production images | Both via existing `make verify-build SERVICES="backend frontend"`, exact disposable retirement |
| Local final acceptance | `make feature-verify` auto-selects affected/FULL | Same; repaired explicit ownership and broader shared-module escalation |
| `make ci` | Exhaustive | Exhaustive, unchanged |
| Feature-finish | Protected-merge/Git/resource guards | Unchanged; no comprehensive suite rerun |

No required job is conditionally skipped, no path filter is added, and there is no dependency job
whose failure could accidentally skip required jobs. Only each job's commands vary. Job names,
timeouts, contents-read permissions and obsolete-run cancellation remain stable. Failure exits flow
through Python, Bash `pipefail` and `tee`; no `continue-on-error`, assertion retry or success wrapper
is introduced. Complete logs remain in Actions and are also retained as separate 14-day artifacts,
including on failure. Artifact upload does not turn a failed verification step green.

## Complete lifecycle and repeated-work audit

Counts below describe Geography's final historical tree, not tests executed by CI-004. Local final
acceptance recorded 956 backend, 975 frontend and 743 integration passes; GitHub #232 logs confirm
those counts (backend also reported one existing skip, unchanged by this work). Focused scope/count
varies by increment. Local phase wall times are not available as reliable historical measurements.

| Phase | Commands / scope | Cost, ownership and result reuse | New evidence / repetition |
| --- | --- | --- | --- |
| 1. Sol implementation | Edit one increment; inspect impact | No automatic suite or Docker startup | Source development |
| 2. Sol feedback | Exact Vitest files; pytest `--no-cov`; relevant lint/type/build; explicit integration files via existing wrapper | Reuse only own metadata-hashed Quality; disposable integration DB migrates fresh | Fast defect feedback; no receipt; avoid full-suite iteration |
| 3. Operator acceptance | Domain/UI acceptance as applicable | Infrastructure needs workflow smoke, no graphical product review | Acceptance evidence distinct from automated testing |
| 4. Luna independent QA | Review connected code/domain; adversarial focused regressions | Reuse focused results only when same source/environment and relevant; inspect uncovered risks | Independent reasoning; no ceremonial repetition of already-covered tests |
| 5. Frozen canonical acceptance | One `make feature-verify`; FULL for high risk, or explicit `make verify-full` when demanded | Own Quality; new integration, build and migration projects; frozen exact-tree receipt | Authoritative local acceptance. Historical FULL repeats all 956/975/743; full cycle even without migration diff |
| 6. Commit/delivery | Inspect diff/staged diff; commit same tree; receipt validation; operator `make feature-deliver` | No tests in commit/delivery. Receipt revalidated against exact source/index/base/policy/branch | Guards correspondence; cannot reuse a receipt after verified content/plan/base/policy changes |
| 7. Required PR jobs | Three `ci-verify.py` invocations in parallel | Separate hosted runners/dependencies/build caches; #232 quality 508s, integration 213s, build 47s | Independent delivered merge verification. Product tests remain deliberately repeated; docs/helper repetition bounded |
| 8. Protected merge | Current-SHA success + exact-SHA auto-merge | No suite; no branch-protection edits | Merge identity/protection |
| 9. Main workflow | Same three jobs, always exhaustive | Fresh runners; #233 quality 494s, integration 199s, build 51s | Post-merge branch evidence; overlaps PR suites but retained for reliability |
| 10. Finish | Operator `make feature-finish` after merge | GitHub merge/SHA/ancestry/primary-index checks; retire exact owned Quality; persistent environments preserved | No application suite, DB upgrade or receipt fabrication |

Quality commands reuse named dependency volumes and dev images but still validate dependency state.
Frontend invocations call `prepare_initializer`, which intentionally builds the selected source and
runs the owner initializer; cached build traversal and frozen-lock dependency checks repeat. These
protect root-owned/changed-lockfile cases and are unchanged. Each hosted job is a separate machine;
a successful build job does not populate quality/integration's image store. Production contexts are
independent backend/frontend builds. Integration creates tmpfs PostgreSQL, builds its test image,
waits for readiness and migrates before pytest; migration cycle has a separate DB/image and exact
base → head → base → head revision checks. No reliable per-substage PostgreSQL/build setup breakdown
was retained; the job/stage totals include these costs. Dependency/build caches are not test evidence.

## Baseline and before/after measurements

[Machine-readable evidence](ci-004-verification-efficiency-evidence.json) records exact job/step
metadata, representative before/after planner output and focused checks. Source runs:
[#231 failure](https://github.com/alessandrorossato/florabase/actions/runs/40226321036),
[#232 passing PR](https://github.com/alessandrorossato/florabase/actions/runs/40237067768),
[#233 passing main](https://github.com/alessandrorossato/florabase/actions/runs/40237825195).

| Run | Quality total / helper step / product step | Integration total / execution step | Build total / execution step |
| --- | --- | --- | --- |
| #231 | 337s / 71s / 257s, failed | 206s / 197s, passed | 42s / 34s, passed |
| #232 | 508s / 90s / 410s, passed | 213s / 205s, passed | 47s / 38s, passed |
| #233 | 494s / 77s / 407s, passed | 199s / 190s, passed | 51s / 41s, passed |

#232 backend pytest reported 18.83s and frontend 277.23s; integration pytest reported 157.84s.
These components are included in their larger stage/job times, not additional costs. The passing
#232 jobs used 768 aggregate runner-seconds and #233 744, excluding queueing. They overlap in wall
time because the three jobs already run independently. No new matrix/parallelism can reclaim that
existing parallelism. The skipped helper step is a measured 71–90s component on these runs, not a
promised future net saving: checkout depth, runner variance and artifact upload add different costs.

The optimized **real local synthetic docs CLI** ran all required repository checks in 0.645s quality,
0.611s integration and 0.605s build, with zero product tests, image builds or PostgreSQL starts. Before,
the remote commands always scheduled every product suite and both builds. This proves eliminated
work, not a hosted-CI percentage comparison. No optimized hosted workflow is run before review/push;
GitHub runner/checkout/artifact costs and net hosted duration remain unmeasured. The tiny fixture
contains only minimal scripts/graph/docs. Planning the full real worktree separately took **18.345s**
on this host; every selective PR job pays its own plan cost. Do not present the subsecond fixture as the
real repository or hosted duration. Checkout fetches depth two rather than all history: the synthetic
shallow-clone test proves both exact parent trees are available for classification.

Always-FULL remote events/fallbacks now validate exact checkout identity and the map, then construct
the exhaustive plan directly. They do not hash the full worktree just to discover that every check
must run; local receipt inventory/freeze is unchanged. On the same real repository, old unconditional
FULL planning took **17.859s**, direct FULL planning **0.008s**, and all three effective required-job
command lists were asserted exactly equal. This is measured planning overhead only. Selective PR
plans retain the complete inventory and its cost; no hosted end-to-end saving is claimed. No expensive complete
suite was executed merely to benchmark it.

| Representative change | Local checks before → after | Remote before → after | Risk / receipt |
| --- | --- | --- | --- |
| `taxonomy/taxonomy.css` | Global product static + 4 → 5 frontend files + frontend build; no DB/cycle | Complete product/helper suites + both builds → same product/build coverage, omit helpers | CSS can share selectors; unchanged static/consumer evidence plus one repaired mapped test; final receipt required |
| `taxonomy/IdentityTaxonomyPanel.tsx` | Same 4 → 5 frontend files and frontend build | Same affected-product policy | Test inventory explicit, no claim of complete inferred dependency graph |
| Shared `components/actions/OverflowMenu.tsx` | FULL → FULL | Full → full | All frontend consumers including BulkLocation; full receipt/cycle |
| Shared `styles/tokens.css` | FULL by unknown path → explicit FULL | Full → full | Whole application styles; no exemption for visually small diffs |
| Backend taxonomy service | Static + 12 backend/4 frontend/9 integration files + backend build → 12/5/9 | Complete product/helper suites + both builds → same product/build coverage, omit helpers | Frontend regressions retained for backend consumers; final affected receipt |
| Documentation only | Graph + whitespace → same | Complete suites/builds → graph/whitespace in all required jobs | No Docker; exact-tree receipt still required locally |
| Alembic revision | FULL → FULL | Full → full | Real complete local cycle remains mandatory |
| Dependencies / CI | FULL → FULL | Full → full | CI-004 cannot exempt itself; mandatory independent FULL before delivery |

## Impact-map audit

Sixteen existing frontend test files were absent from their declared owner lists: eight Identity
hub/media/geography files, PartialDateField, Schedule API/calendar, ProvenanceMap, NativeCoverageMap,
Labels QR, DashboardScreen and EvidenceTiles. They are now explicit entries. A guard checks existing
tests under every classified frontend prefix against the versioned lists, so future inventory drift
fails the helper suite. Runtime selection still uses explicit ownership, not glob-based guessing.
All currently mapped test files exist. Existing overlap/transitive selections deduplicate.

Shared `components/` and ReferencePicker already select FULL, so the BulkLocation consumer is
included even when its own file is untouched. Explicit shared styles, appearance and map workspace
prefixes now document existing unknown-path FULL behavior. Native ranges, provenance map, occurrence
map and species distribution now select FULL because their renderer/API/geometry consumers cross
Identity, Geography and multiple map screens. Narrowing them requires a separately proven graph.
Independent QA also identified PartialDateField and its CSS as shared by Journal, Plants and Harvest;
both now select FULL with regression cases. Unknown Geography/settings/new module paths continue to
select FULL rather than silently disappear. Backend ownership remains unchanged and inventory checks
continue to enforce classification or escalation. Generated API artifacts alone select FULL; with a
classified owner they retain both layers/builds locally. Remote product verification remains complete
in either case. Dependencies, security, infrastructure and migrations retain FULL.

This audit does not prove every frontend/backend transitive consumer. That is why affected **remote
test sectorization is deferred**. The expanded map invalidates older local receipts by digest as
designed. The receipt schema, complete source/index/untracked inventory, freeze, migration evidence,
delivery current-SHA checks and finish protections are otherwise unchanged.

## Historical failures and safe diagnosis

- **Geography #122, run #231:** quality failed with seven BulkLocation failures and 968 passes;
  build/integration passed. Six excerpts could not find `Move to location`; the menu was closed.
  The merged test change waits for the actual toolbar focus scheduled by `requestAnimationFrame`
  before continuing through the overflow menu. This is an evidenced interaction-order race and its
  correction is already in base `3902b92`. No production menu change, arbitrary sleep, quarantine,
  weakened assertion or silent skip is part of CI-004. #232 passed 975/975 frontend tests.
- **Identity run #228:** `App.test.tsx` expected a conflict draft but received the original name;
  927 tests passed and one failed. The log proves an editor-state assertion failure, not whether
  the cause was product logic, stale fixture or scheduling. Do not label it transient from timing
  alone. The later #229/#230 runs passed after intervening work; no causal diagnosis is invented.
- **Dependency PR #124, run #235:** quality fails eight `no-deprecated` lint diagnostics for
  MediaQueryList `addListener`/`removeListener` in App, Plant and SeedLot tests. Build/integration
  passed. This is concrete dependency/lint incompatibility, not a Docker or flaky-test failure.
  Do not suppress it or rerun to conceal it.
- **This audit:** initial read-only Docker inventory hit `no such object` when a concurrently
  retiring disposable container disappeared. The second inventory succeeded; no mutation/recovery
  was attempted. No historical claim of resource exhaustion or stale-receipt-caused reruns is made
  without available logs. Local static checks caught import ordering and a missing list annotation;
  corrected and rechecked, without weakening checks.

The new stage failure line identifies the stage, exact command, exit status, elapsed time and prior
passed stages. Original test output supplies file/case/stack trace; use the retained complete log.
No failure category is guessed by a string classifier. Example diagnosis:

```bash
# From the owning feature worktree, preserve existing Vitest configuration and assertions:
python3 scripts/workflow_environment.py quality compose -- run --rm --no-deps frontend \
  pnpm test src/bulk/BulkLocation.test.tsx
# Add -t '<exact case>' only after identifying the failing case.
# Existing safe focused PostgreSQL runner:
./scripts/test-integration.sh backend/tests/integration/test_schedule.py
# Read remote failures; only retry after diagnosis proves a transient environment failure:
gh run view RUN_ID --log-failed
gh run rerun RUN_ID --failed
gh run rerun --job JOB_ID
```

A local failed/interrupted canonical gate has invalidated its prior receipt and needs a complete
policy-selected rerun after diagnosis/fixes. A remote failure leaves the local receipt untouched but
blocks delivery. A same-SHA remote job rerun can preserve successful independent jobs; a changed
commit requires new remote verification and new local evidence. GitHub reruns retain the original
SHA/ref, so they cannot verify a later code fix. See
[GitHub job-rerun semantics](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs),
[checkout history/merge behavior](https://github.com/actions/checkout), and
[artifact retention](https://github.com/actions/upload-artifact).

## Tests, smoke and acceptance boundaries

- `make test-verification-impact`: 24 passed, including docs/product/full remote decisions,
  shared controls/CSS/map escalation, explicit inventory, real synthetic two-parent PR event,
  moving origin/main, wrong-checkout hard refusal, inconsistent/missing impact event fallback, real CLI docs commands, failure
  status/output propagation and no local receipt issuance. Existing inventory tests cover commits,
  index/dirty/untracked, rename/delete/mode/symlink changes and hidden staged changes; receipt tests
  reject policy/base/completion tampering and required migration evidence omissions.
- `make test-workflow-resources`: 14 passed; exact positive ownership, foreign users, partial
  creation, failure/signals, persistent roles, safe test selections and cleanup evidence.
- `make test-feature-workflow`: 42 passed; source mutation during gates, old receipt invalidation,
  linked receipt isolation, missing/failed/cancelled/timed-out required checks, manual same-SHA failed
  job recovery without automatically retrying assertions, stale/current SHA,
  exact-SHA merge, moving base and branch/primary safety. No real PR/delivery action occurs.
- `make test-workflow-helpers test-preview-workflow test-environment-workflow test-uat-preview`:
  shell suite plus 19/35/19/15 Python cases passed in isolated fixtures.
- `make workflow-check`: workflow Ruff lint/format and strict mypy plus parsed CI/Dependabot YAML
  policy assertions passed. The YAML regression requires all three unconditional jobs, original
  event triggers, sufficient parent history and pipefail; no job dependency or permissive error handling.
- `make smoke-workflow-resources`: **WORKFLOW_RESOURCE_SMOKE_PASSED**. Real synthetic containers,
  networks and volumes retired; nine protected/non-target simulations survived; actual operator
  DEV/Review/UAT/Stable/production resource identities unchanged. Synthetic finish is exercised only
  inside temporary Git/Docker fixtures; this feature's finish command was never run.

Independent infrastructure QA found and fixed a wrong-checkout FULL-fallback defect: a valid platform
SHA must now match actual HEAD before any impact fallback. Direct/CLI regression cases refuse wrong,
missing or invalid SHAs before commands or success markers. QA re-reviewed the correction, passed
the synthetic history/refusal test independently and reported no remaining actionable defect. It also
identified the repaired shared PartialDate boundary. QA also confirmed the depth-two history boundary and direct-FULL planning shortcut, with focused
regressions passing independently. Hosted Actions and the canonical FULL gate were not part of this
independent review.

The exact-SHA remote build entry point was also exercised locally: both production images built,
**RESOURCE_CLEANUP_PASSED** removed both owned images with zero residual containers/networks/volumes,
and **CI_JOB_PASSED: build** followed. The first build stage took 72.89s including cold dependency
downloads; the final corrected entry point took 4.62s for the stage using warm shared cache. These
are cache-condition observations, not a claimed CI-004 speedup or total planner-inclusive duration.
No application feature, migration, dependency pin, branch protection or persistent environment is
changed. CI-004 is `implemented`, not `verified`. At the initial review checkpoint there was no
staging, commit, push, PR, delivery/finish, DEV upgrade or persistent UAT authorization.

## Deferred work and exact integration dependencies

1. **Narrow remote product selection:** requires proof of complete transitive backend/frontend
   consumers and test inventory maintenance, especially shared CSS, renderers and interactions.
   Keep exhaustive product CI until a separate reviewed migration establishes that evidence.
2. **Shared remote Docker/dependency caches:** fresh hosted runners currently repeat cold setup.
   Cross-job image export or cache backends require authentication/poisoning/ownership/eviction
   analysis. Existing shared local BuildKit cache is retained, never globally pruned. No cache hit
   is reused as a verification result.
3. **Skipping main after PR / release evidence reuse:** deferred. Squash/main identity and branch
   movement mean PR and post-merge executions are not interchangeable. Main and exhaustive release
   policy remain intact. No results are trusted from client receipts or workflow artifacts.
4. **Further helper deduplication:** the existing selector receipt fixture invokes part of feature
   orchestration also exercised by the feature suite. Keep both: current review value outweighs the
   small synthetic-fixture cost; do not build another test framework to shave seconds.
5. **Initializer build/dependency bootstrap:** unchanged because source freshness, root-owned
   `.bin` repair and changed-lockfile correctness require an independently evaluated replacement.
6. **Integration state:** base includes #121 and fixed/merged #122. Open backend dependency #123
   (`974fb56cdbdefc87accb7b0b03a72751146570e4`) passed run #234; frontend dependency #124
   (`55a4ee03dc7f8815925dc01ca46fc609a2c7b3f9`) failed lint in #235. Neither is included or required
   by CI-004. The existing #124 failure is explicitly evaluated: manifests remain unchanged here,
   dependency changes still select FULL, and all remote product lint/tests remain mandatory, so
   CI-004 cannot make that red dependency commit mergeable. Do not merge/update those PRs as part
   of this task. Recheck live main/open PR state before eventual CI-004 delivery; integrate any
   intervening changes deliberately and rerun the frozen-tree FULL gate.
7. **Before delivery:** operator review, independent QA disposition, one final `make feature-verify`
   selecting FULL including real complete migration cycle, receipt check, intentional staging and
   commit, then authorized protected delivery. A final hosted workflow smoke remains necessary
   after authorized push. No local synthetic run claims to prove hosted permissions/artifact service.

## 2026-10-26 — Final canonical verification follow-up

The user authorized the final FULL gate and protected delivery. The previous `make verify-full`
attempt ran for **1352.50 seconds** and failed in `quality` during `make check`: **968/975 frontend
tests passed**. Seven failures were reported in `src/App.test.tsx`: Location detail deep links;
Sourcing/Explore destinations; sidebar disclosures; Plants filters; identity Harvests mode; identity
Events mode; and narrow identity selection. The complete Vitest stage took **932.64 seconds**. The
original full-run log was not retained in `/tmp`; its exact failed assertions therefore cannot be
recovered. No receipt was issued.

The independently reproducible Botanical Identity section Back/Forward test is a separate App test.
It could fail while the lazy workspace was still showing its loading placeholder, or before the
asynchronous history traversal and route state had synchronized. The test now waits for the lazy
route imports, the exact overview/history hashes after keyboard selection and Back/Forward, and the
selected tabs. It still exercises real jsdom history traversal and does not alter production routing.
The final focused test passed, the full App file passed **115/115** in **84.34 seconds**, and four
related Plant, Saved View, and Dashboard Search history tests passed. The six original full-suite
failures all passed in the App file run after this correction, but their individual original causes
remain unproven; they are not attributed to the history test or to resource contention.

CI-004 does not change frontend production code; the navigation test and behavior predate this
candidate. No application navigation defect was demonstrated. No test was skipped, quarantined, or
weakened. One bounded workflow follow-up is proposed: run a small existing App navigation regression
subset before expensive exhaustive FULL verification to expose known route regressions earlier. It
must remain a fast diagnostic, must not duplicate the frontend suite, and must not replace the
exhaustive gate for infrastructure changes. This follow-up is not implemented here.

**Focused gate is clean; the required one final FULL canonical run is pending.** No new receipt,
commit, PR, hosted checks, merge, finish, DEV upgrade, or persistent-data operation has occurred.

The first FULL attempt after this diagnostic stopped during frontend lint after **201.59 seconds**,
before application tests. ESLint found one `@typescript-eslint/no-confusing-void-expression` error in
the new `waitFor` callback. Braces corrected the callback; targeted ESLint and the exact navigation
test then passed. This failure issued no receipt and is corrected in the frozen candidate for the
next final FULL attempt.
