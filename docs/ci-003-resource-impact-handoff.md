# CI-003 Docker lifecycle and impact-aware local verification

## Worktree and feature ownership

Implementation uses only the attached Codex-managed worktree, branch
`ci/workflow-resource-impact-verification`, base `3592593f8ef78549ae2ba5b00c43b66930dcfd42`
(SCHEDULE-001, PR #83). The primary checkout remains on `main`.
`make feature-init` attached the clean detached worktree through the repository helper.

The complete **99-feature** graph was audited, including all dependencies and statuses. CI-001 owns
remote CI; CI-002 owns original feature gate/delivery; **CI-003** already owns environment contracts,
Quality/integration resource isolation, per-worktree receipts, linked finish and canonical workflow
orchestration. Its existing acceptance criteria cover both requested concerns. Extend CI-003 rather
than duplicate these owners or invent CI-004. CI-003 is `verified` after independent review and the
full canonical gates. Other feature statuses/priorities are unchanged. After CI-003 delivery, a
dedicated sweep of open bot dependency-update PRs precedes
product successor **DASHBOARD-001**, then the agreed functional/IA completion wave before broad visual
redesign.

## Current workflow audit

Audited AGENTS, CONTRIBUTING, Makefile, CI, development/workflow/architecture/roadmap/progress and the
complete feature graph; verification/fingerprint/delivery/finish, environment, integration, migration,
Preview/UAT, smoke/helper tooling; Compose files, Dockerfiles and build contexts.

| Before this increment          | Behavior and resource consequence                                                                                                                                         |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Canonical feature gate         | Always runs five workflow suites + workflow static + whole quality + all integration + both production builds + conditional migration, even for docs                      |
| Quality commands               | Exact metadata-hashed project; `run --rm` reuses three named volumes and one network; development images and BuildKit cache persist; no supported retirement/finish hook  |
| Integration                    | UUID project; tmpfs PostgreSQL/media; EXIT/INT/TERM cleanup uses scoped Compose down with volumes/orphans; no residual check; project-built tests image remains           |
| Migration cycle                | PID project; base → head → base → head; down omits volumes, suppresses errors, and signal trap can return to the workflow; project image remains                          |
| DEV                            | Primary source; persistent DB/media/dependencies; guarded stop retains state and legacy tmpfs preservation                                                                |
| Review/UAT                     | Current dirty source; intentional persistent DB/media/dependencies with exact source ownership; stop preserves; removal/reset explicit and guarded                        |
| Stable Preview/production      | Separate persistent source/project/database/media; production image tags intentionally reusable                                                                           |
| Existing unique smoke fixtures | `finally` cleanup but no consistent caught-TERM registration/residual verification; some image removal relies on fixture tags; environment smoke uses real Review project |
| PERF fixture                   | Fixed operator-managed `florabase-perf`, explicit start/measure/stop, tmpfs DB/media; reusable benchmark session rather than a unique gate run; preserved                 |
| Build cache                    | Actual daemon uses shared **default/docker** Buildx builder, BuildKit v0.34.0; initial aggregate cache 73 records/1.24 GB; no provable project-exclusive boundary         |

The resource diagnostic also finds legacy labelled integration/migration image outputs, stale Quality
and ad-hoc networks, and unknown source identities. These are reported, not retroactively deleted.
The first synthetic safety smoke actually reproduced Docker's exhausted default address pools;
registered cleanup successfully retired all partially created fixtures. Subsequent synthetic
isolation fixtures use unique explicit IPv6 ULA subnets with IPv4 disabled, so they do not consume
shared IPv4 pools. Product integration networking remains normal.

## Environment lifecycle matrix

| Environment                    | Lifecycle                                   | Retirement                                                                                       |
| ------------------------------ | ------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| DEV                            | Persistent                                  | Existing guarded stop; never temporary cleanup                                                   |
| Quality                        | Exact worktree, reusable during active work | Explicit `quality-clean`; automatic only after proven finish safeguards                          |
| Integration                    | Unique disposable run                       | Registered cleanup on success/failure/partial creation/caught INT/TERM; residual verification    |
| Migration verification         | Unique disposable run                       | Same; complete appropriate cycle preserved                                                       |
| Verification production builds | Unique disposable outputs                   | Remove exclusive positively labelled images; no deployment                                       |
| Feature Review                 | Intentionally persistent                    | Stop preserves all volumes; exact-owner remove remains explicit                                  |
| UAT Preview                    | Intentionally persistent                    | Stop preserves; reset/remove remain explicit exact-owner actions                                 |
| Stable Preview                 | Persistent                                  | Existing explicit stop/remove semantics; never temporary cleanup                                 |
| Production                     | Persistent                                  | Existing deployment commands; never temporary cleanup                                            |
| Unique real smoke fixtures     | Disposable, labelled before creation        | Same context/signal/ownership cleanup; fixed Review smoke replaced by a unique synthetic project |
| Fixed PERF benchmark           | Explicit reusable operator fixture          | Existing manual lifecycle; no automatic gate cleanup                                             |

## Resource ownership, disposable cleanup and failure behavior

`workflow_resources.py` is a bounded Florabase helper. New disposable resources carry exact Compose
project plus `io.florabase.workflow.lifecycle`, `.owner` (UUID run token), and `.source` labels.
Quality owner is the **exact Git metadata path**, with the existing deterministic hashed project.
Services/networks/volumes and terminal built images receive ownership before creation. Compose-owned
labels are generated by Compose; build outputs explicitly retain project ownership.

`Disposable` registers signal handlers before creating resources and refuses pre-existing resources
for a new run. The runner uses fixed disposable configuration and ignores implicit Compose project/
file overrides and workstation `.env`. Integration accepts only explicit existing integration `.py`
files under the correct directory, deduplicated and passed as arguments. No query/test expansion or
shell interpolation of user test paths occurs. Full integration remains the default without selections.

Cleanup discovers only exact project/owner-labelled resources, proves all identities **before** any
mutation, and refuses foreign users of volumes/networks. It removes individually re-inspected exact
container IDs (including orphans), network IDs and volume names, with another user/owner check, then
verifies zero owned container/network/volume residuals. Already-clean retirement is idempotent.
Cleanup errors fail the runner/gate, even after passing tests. No generic daemon prune or name-only/
blacklist deletion is used. The project cannot be a persistent lifecycle.

Real command errors retain their underlying Docker diagnostics and print the failed stage/command,
impact scopes, cleanup result, residuals and `make workflow-resources`. Disposable failures also print
an exact recovery command with project, role and owner token; invoke it from the same source after
restoring Docker capacity/access. Recovery cannot target Quality/persistent roles. SIGKILL or daemon
loss cannot execute process cleanup; recovery remains exact-owner/fail-closed.

## Quality cleanup, finish and Review/UAT preservation

`make quality-status` identifies the exact current metadata/project/source and counts. `make
quality-clean` retires only that worktree. Recognized legacy Quality containers additionally prove
source/Quality role; legacy network and three known volume keys prove exact deterministic project
and Compose metadata. Any other legacy ownership fails closed. Other Quality projects are not selected.

Finish retains **all** existing clean-branch/PR/merge/exact-OID/main-ancestry/primary-index safeguards.
Only after those checks pass does it retire current Quality, before primary fast-forward/detach/ref
removal. A cleanup failure retains the branch and gives diagnostics. This hook was exercised only in
fresh isolated Git/Docker fixtures; the attached feature was not finished.

Review/UAT stop/reset/remove implementations and ownership/takeover semantics are unchanged. They
are never automatic gate cleanup targets. Existing smoke wrappers alone add temporary ownership;
UAT transition fixtures share a run label while their explicit UAT source ownership changes through
the existing guarded remove/new-owner procedure. DEV/Stable/production are never selected.

## Images, build cache and observability

Verification uses independent backend/frontend contexts in unique labelled build projects. Only an
exactly owned output without foreign tags/container users is removed, without force. Multiple tags,
foreign users or ambiguous legacy images are retained and counted; shared base images remain.
Normal `make build` still means persistent production builds. No release/distribution changes occur.

Shared default BuildKit cache is deliberately retained: image/project names cannot prove exclusive
cache ownership. A new dedicated builder would introduce a new cache/dependency boundary and duplicate
cold setup; no evidence warrants forcing that migration in this increment. No automatic builder/
buildx/system/container/image/network/volume prune is introduced. The report explicitly states the
remaining shared cache policy.

`make workflow-resources` reports known DEV/Quality/Review/UAT/Stable/production projects, registered
disposable lifecycles, legacy project images and unknown Florabase-labelled resources with bounded
IDs/names/status/source. It reads labels first and inspects only Florabase candidates; no environment
secrets, collection data or unrelated workload inspection/deletion is involved. Unknowns are report-only.

## Impact model, map and transitive dependencies

`scripts/verification-impact.json` version 1 explicitly owns current source modules and exact test
files. Scopes include identity, profile/botany/enrichment, seeds/sowings/plants, harvest, events,
history, schedule, media/attachments, geography/provenance, explore/taxonomy, suppliers/orders,
locations/lineage/propagation, bulk, saved views, import/export, search/labels/dashboard/maps,
Activity navigation, collection projections and security regressions. Shared backend/frontend,
database/migrations and infrastructure are explicit full-escalation boundaries. Docs are separate.

A regression consumer references its owning suite group without duplicating its list or implying its
source changed. Real transitive relationships stay bounded: Taxonomy → provider/source links and
collection views → Explore/Taxonomy regression boundaries; Schedule → Event/Activity/target/security
regressions; Activity → write-security regressions. ReferencePicker and broadly shared UI primitives
escalate full rather than rely on an incomplete consumer graph. Taxonomy does not select Orders/Labels.

Complete inventory compares modes/blobs with the resolved exact base, includes untracked source and
both rename sides/deletions, then unions committed/index/working differences. A staged or committed
production edit cannot be hidden by an unstaged base-content revert. Rule overlap unions ownership
conservatively, with sorted/deduplicated deterministic output. New tests in a classified frontend module run as exact changed paths. Missing selected tests fail rather than
silently disappear. Invalid policy fails closed. No runtime-history learning, fuzzy classification,
telemetry, external changed-file upload or automatic test generation is added.

## Escalation rules and verification modes

Unknown paths, policy/verification/workflow scripts, Makefile/CI/Compose/Docker files, dependency and
lock/config changes, auth/core/DB/API foundations, widely shared frontend primitives, migration
revisions and unowned generated contracts select **FULL**. This increment therefore selects full.
Migration revisions currently escalate conservatively; bounded migration plans are not guessed.
Generated artifacts accompanied by classified production ownership expand the frontend/backend layers.

- Focused: existing explicit developer checks; no delivery receipt.
- Affected: canonical `make feature-verify`/`verify-affected` derives safe selection automatically.
- Full: `make verify-full` forces the complete gate; only stricter override is supported.
- `make verification-plan [FORMAT=json] [REF=<exact-base>]` exposes the same human/machine decision.

## Static checks, test/integration selection, migration and builds

Docs-only runs feature graph plus tracked/staged/untracked whitespace checks with no Docker. Product
plans retain global format/lint/strict typing/API drift; their measured cost is explicitly recorded
below. Global typing/contracts preserve cross-scope safety. No claim that these checks are free is made.
Backend affected suites use exact files and `--no-cov`; full quality/remote CI still enforce the existing
90% coverage policy. Frontend selection passes exact test files to Vitest. Workflow suites run for
full/workflow impact, not ordinary domain/UI changes. PostgreSQL selects only explicit mapped files
through the same disposable runner; zero selection never silently invokes an empty test command.

Migration changes/infrastructure/DB foundations enable appropriate complete cycling. The cycle still
uses the literal previous-base single Alembic head and real PostgreSQL. Infrastructure can force it
without a new revision. Docs-only does not invoke it. Independent frontend-only builds frontend;
backend-only builds backend; both layers/generated frontend contracts and full plans build both.

## Receipt format, delivery validation and remote CI policy

Version **2** retains branch/base/exact working-tree digest and committed-HEAD delivery validation.
It adds the complete versioned plan/map digest, changed paths/scopes and transitive scopes, reasons,
selected backend/integration/frontend/workflow/static suites, exact completed command/result list,
migration/build decision/result and UTC timestamp. The gate freezes content and rejects concurrent
source changes; successful focused commands cannot write a final receipt.

Receipt write and delivery read independently recompute current selection and require **every**
selected check to have passed in the exact expected order. Unsupported versions, missing completion,
failed/missing/extra checks, other base/branch, stale tree/HEAD or different map/plan are rejected.
Normal commit of the reviewed tree preserves receipt validity. Unusual masked staged/committed edits
participate conservatively; removing that transient impact requires a new plan/receipt.

Protected GitHub **quality / integration / build remain exhaustive**, with existing required names,
full application tests/coverage and both production builds. CI adds the new deterministic helper
suites; no protected check is sectorized, weakened or bypassed. `make ci` remains exhaustive.

## Checks and real Docker evidence

Evidence is consolidated in [the machine report](ci-003-resource-impact-evidence.json). Implementation
checks cover selector/inventory/receipt/delivery, ownership/retirement/runner failure/signals,
environment/Preview/UAT and finish safeguards. Original application tests were not deleted, weakened
or regenerated. Formatting, strict typing, shell syntax, graph and whitespace checks are recorded.

The real isolation smoke creates ten fresh synthetic project/resource sets: target integration,
another disposable, two independently metadata-derived Quality projects, DEV-like, Review-like,
UAT-like, Stable-like, production-like and unrelated-like. Only the exact target retires; all nine
non-target sets survive. Stale target network/volume and repeated cleanup are covered. Every synthetic
set subsequently retires through its own registered cleanup. A real linked Git fixture verifies dirty
primary refusal preserves Quality; successful proven finish retires its exact Quality and preserves
all other fixtures. Real operator resource identities are snapshotted unchanged.

Actual selected Schedule PostgreSQL integration passes **12 tests**, with one project/2 containers/
1 network/no persistent volume/1 test image; retirement verifies zero owned residuals. Forced real
base → head → base → head also passes and retires its project/image. This branch adds no migration,
so base and feature heads both equal 0041; existing migration invariants are not bypassed. Separate
backend/frontend production-build probes validate selective image retirement without deployment.

## Before/after resources and timing: limits and reproduction

The old canonical behavior is read directly from base scripts; representative new decisions are
measured with synthetic changed-path inputs against current source. The docs-plan commands really
execute as focused checks without writing a feature receipt. Integration, migration, selected
frontend and builds are separately measured real invocations. Whole old/new canonical runtime is
**not measured or estimated**: the user reserves final full verification for Luna, and host/bootstrap
costs make invented percentage claims misleading. The comparison table records selected suite/build
counts and resource contracts; actual substage results/residuals are separate in the machine report.

Reproduce implementation evidence (serially, outside concurrent heavy builds):

```bash
make test-verification-impact test-workflow-resources test-feature-workflow
make test-environment-workflow test-preview-workflow test-uat-preview test-workflow-helpers
make workflow-check
make smoke-workflow-resources
./scripts/test-integration.sh backend/tests/integration/test_schedule.py
./scripts/verify-migration-cycle.sh origin/main --force-cycle
make verify-build SERVICES=backend
make verify-build SERVICES=frontend
make quality-status
make workflow-resources
make verification-plan FORMAT=json
```

The independent review and full canonical gates are recorded in the final verification milestone in
`docs/progress.md`. No product visual UAT is required. The active Quality environment intentionally
remains reusable; disposable runs must show zero required residuals. Legacy images/cache/other Quality
and unknown resources remain untouched and visible. Delivery uses the protected repository workflow;
after merge, `make feature-finish` performs conservative local cleanup. No DEV upgrade is needed because
this increment adds no database migration.

## Documentation and roadmap

AGENTS conventions and the existing phase split apply. Updated CONTRIBUTING, development/workflow,
architecture, CI-003 feature criteria, roadmap and progress explain the automatic safe gate, explicit
full override, receipt, exact resource diagnostics/cleanup, preserved persistent state and cache
residuals. After CI-003 delivery, sweep open bot dependency-update PRs before **DASHBOARD-001**. No
product implementation/API/schema changes.

Implementation handoff: **READY_FOR_VISUAL_REVIEW** (infrastructure review; no graphical UAT).
