# Review profiles, verification gates and Quality resources

> Summary: Domain/UI/infrastructure review profiles, docs placement and progress rotation rules, affected vs FULL gates, and Quality Docker resources.

## Review profiles and verification timing

Choose the order appropriate to the change:

- **Domain / integrity / security:** implementation → focused tests → adversarial logical review →
  fixes → operator functional/visual acceptance → final canonical verification → commit/delivery.
- **UI / UX:** implementation → focused tests → Feature Review → operator visual acceptance →
  independent correctness review → fixes → final canonical verification → commit/delivery.
- **Infrastructure / CI:** implementation → real workflow smoke → independent infrastructure review
  → fixes → final canonical verification → commit/delivery. No product graphical review is required.

Independent review seeks objective correctness defects. It does not reopen operator-accepted cosmetic
choices without a correctness/accessibility reason. Visual acceptance does not redefine established
domain contracts.

### Documentation and review-artifact placement

- **Living guides in topic subfolders under `docs/`:** place new living guides in the matching
  subfolder (`operate/`, `develop/`, `architecture/`, `product/`, or `features/<workspace>/`), add
  a one-line `> Summary: ...` after the `# Title`, and link them from that folder's `README.md`.
  Do not add new `.md` files at the top level of `docs/` (`make doc-links` enforces the allowed
  top-level list).
- **Per-increment artefacts in `docs/archive/<FEATURE-ID>/`:** place per-increment handoffs, design
  notes, audits, reviews and evidence JSON directly in `docs/archive/<FEATURE-ID>/` from the start.
- **No committed review screenshots:** review screenshots and visual-audit captures are **not
  committed** to Git; attach them to the pull request or keep them in the local project folder. Only
  curated public images under `docs/assets/` are committed. Existing directories under
  `docs/archive/review/` and `docs/release/evidence/` are preserved as historical evidence.
- **Progress log rotation (`docs/progress.md`):** at each beta release-prep commit (which lands on
  `main` alone, outside batch merges), move milestones older than the previous published beta's
  release-prep entry verbatim to `docs/archive/progress/<beta>.md` and link it from the archive
  header line at the top of `docs/progress.md` alongside `docs/archive/progress-until-beta-7.md`.

Local verification distinguishes five policy tiers (`docs`, `affected`, `product-frontend`,
`product`, and `full`), grouped across developer iteration and canonical gating:

- **Focused:** developer-selected existing test/check commands for iteration. These do not write a
  delivery receipt. Integration accepts explicit existing files, for example
  `./scripts/test-integration.sh backend/tests/integration/test_schedule.py`.
- **Canonical (`make feature-verify` / `make verify-affected`):** derives the safe tier automatically
  from the exact base and complete committed/index/dirty/untracked feature tree, then writes the
  exact completed-plan receipt:
  - **`docs`:** docs-only static changes (including `docs/` static files and root `README.md`,
    `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`, `THIRD-PARTY-NOTICES.md`, and `LICENSE`)
    run `feature-graph`, `doc-links`, `test-doc-links`, and the three whitespace checks with no
    Docker/product suites or image builds. (Container image licences live in `backend/LICENSE`,
    `frontend/LICENSE`, and `postgres/LICENSE`, not root `LICENSE`.)
  - **`affected`:** module-scoped product changes run explicit affected suites, global product
    static checks, selected independent production builds, and skip workflow suites and migration
    cycling.
  - **`product-frontend`:** shared frontend changes (`product_frontend_prefixes` such as
    `frontend/src/components/`, `frontend/src/styles/`, `frontend/src/maps/`, `frontend/src/shell/`,
    and `product_frontend_tests`) without backend-layer changes run global static/API-drift checks,
    all frontend tests (`make test-frontend`), and the `frontend` production build, with no backend
    unit tests, no integration tests, no workflow suites, and no migration cycling. Combining a
    shared frontend path with any backend-layer change promotes to `product`.
  - **`product`:** shared backend product changes (`product_backend_prefixes` such as shared
    `backend/src/florabase/` infrastructure other than `__init__.py`, and `product_backend_tests`),
    or mixed shared-frontend + backend changes, run the full product baseline (`make check` for all
    backend and frontend unit/component tests and static/API-drift checks, both `backend` and
    `frontend` production builds, and `make test-integration` on disposable PostgreSQL), while
    omitting workflow/release suites and forced migration cycling.
  - **`full` (`make verify-full`):** runs everything in `product` plus all ten workflow/release
    suites (`WORKFLOW`) and the four-transition PostgreSQL migration cycle (`--force-cycle`). Full
    remains mandatory for infrastructure/scripts/Makefile/Compose/CI/Dockerfile/lockfile/Alembic/release
    changes, `LICENSE`, `backend/src/florabase/__init__.py`, unknown or unclassified paths
    (fail-closed), releases, and operator-requested exhaustive checks. Every selected FULL stage
    executes exhaustively; there is no force-narrow override.

Preview the human plan with `make verification-plan`; use `make verification-plan FORMAT=json`
for the same machine-readable decision. `REF=<exact-base>` selects a diagnostic base; canonical
verification still fetches main and requires that exact base to be an ancestor. The versioned
[scripts/verification-impact.json](../../../scripts/verification-impact.json) (schema v2) contains explicit
source/test ownership (`backend_dirs`, `integration_dirs`, `frontend_dirs`, legacy flat test lists,
`product_backend_tests`, `product_frontend_tests`, and `full_tests`), consumer regression boundaries
and transitive relationships. A new test file placed in a directory owned by a scope (or under a
`product_backend_prefixes` / `product_frontend_prefixes` / `full_prefixes` directory) is discovered
and selected automatically with that scope without editing the map; any test file on disk under
`backend/tests/` or `frontend/` that is owned by no scope or tier causes the pre-gate inventory check
(`make verification-plan`, `make feature-verify`, and `scripts/ci-verify.py`) to exit non-zero and
name the file before starting Docker. Any unknown non-test path escalates full. Editing the map or
verification infrastructure also escalates full. Migration revisions conservatively escalate full.
Every full plan requires the complete base → head → base → head cycle on disposable PostgreSQL; no
changed-file shortcut may suppress it. Affected plans may skip migration cycling only when impact
analysis proves it unnecessary. Generated contracts require an owning classified production scope.

True docs-only plans run feature graph and complete whitespace checks with no Docker/product
suites or image builds. Under `docs/`, the impact map allows only known static documentation
suffixes. Compose overlays, review scripts, browser review HTML and unrecognized formats require
FULL. Executable modes and symlinks require FULL even with a documentation suffix. The planner
checks modes across the base, HEAD, index and worktree and considers both sides of a move.
An unmerged path prevents the planner from safely classifying the tree.
Product plans retain whole-repository Ruff, Prettier, ESLint, mypy, TypeScript
and generated API drift checks. Affected unit tests use explicit files and `--no-cov`; exhaustive
local/remote quality still enforces the existing whole-application coverage threshold. Frontend-only
changes build frontend; backend-only changes build backend; generated frontend contract changes
build both. The contexts are independent. Pure product changes skip workflow-specific suites.

Stages run cheapest-first and independently of the launching terminal:
1. Feature graph and the three whitespace checks.
2. Offline workflow suites, then the Docker `workflow-check`.
3. Global static checks, then unit suites (`make check` runs `api-check` before `test`).
4. Production builds, then the migration cycle, then integration (and `golden-dataset` when changed
   paths intersect the Golden closure or fail-closed classification).

Every stage gets `/dev/null` as stdin. The gate prints the stage order up front and a per-stage
summary (passed, failed, interrupted or not run, with elapsed time) at the end or on failure. It
keeps the latest run's timings in `<git-dir>/info/florabase-verification-last-run.json`, which is
diagnostics only and never evidence. Because source-state checks run first, the closing
frozen-state comparison covers the working tree, the index and HEAD. See
[VERIFICATION-FAST-001](../../archive/VERIFICATION-FAST-001/verification-fast-001-handoff.md).

Stage evidence is opt-in and local
([VERIFICATION-EVIDENCE-001](../../archive/VERIFICATION-EVIDENCE-001/verification-evidence-001-handoff.md)).

- `make feature-verify REUSE=1` may skip **only** Quality and integration. It skips them when a
  record in this worktree's Git metadata proves that their complete input closure is unchanged.
  The closure covers rendered Compose models, every bind source and build context (including
  untracked and ignored files), scripts and top-level files, environment, tools and exact image
  identity.
- `REUSE=dry-run` runs everything and reports what would be reused.
- `FRESH=1` ignores records and takes precedence over the reuse controls.
- `make verification-evidence` previews the decision without running stages.
- Every other stage, including the real migration cycle, always runs.
- Unknown, corrupt or stale evidence runs the stage fresh, and the log states why. Local records
  expire 24 hours after completion in UTC. Missing, malformed, timezone-naive, future-dated or
  out-of-order timestamps refuse reuse.
- BuildKit and dependency caches are never evidence.
- Receipts are version 3 and name every reused stage. Version 2 receipts remain valid.
- Delivery always refuses a receipt containing reused stages. For consolidated integration,
  commit and freeze the tree, then run `env -u REUSE FRESH=1 make verify-full AGENT_ID=<writer>`.
  Require a version 3 FULL receipt with an empty reused-stage list and validate it against HEAD
  using `feature-tree-fingerprint.py verify`.

Freeze source before the final gate. It invalidates old evidence at startup and rejects source edits
while stages run. Receipts cover file content, modes and symlinks, exact base/branch, tier/mode,
impact-map version/digest, changed/affected scopes, product/escalation reasons, selected suites,
completed commands, static checks, migration/build decisions and results, and a UTC completion
timestamp.
Migration evidence distinguishes the decision, cycle requirement, actual execution and result. Required
cycles verify the database revision after all four transitions and record successful disposable cleanup;
affected skips record `skipped_by_impact`. Older v2 receipts lacking this evidence are incompatible and
require a new canonical gate.
Delivery recomputes the policy, rejects receipts below the recomputed required tier (such as `docs`,
`affected`, `product-frontend`, or `product` when `full` is required, or `docs`/`affected`/
`product-frontend` when `product` is required), and rejects incomplete, obsolete, mismatched or stale
evidence. The normal same reviewed tree can be committed without a ceremonial rerun. Transient
staged/committed changes masked by unstaged reverts are classified conservatively; freeze the index
too when using such unusual combinations, since removing transient impact invalidates the stored
plan.

Protected GitHub `quality`, `integration`, `build`, and `rehearse` remain stable, independent jobs
with no job-level conditions or workflow path filters. Each independently validates the platform PR
merge SHA and both exact parents, then recomputes the complete-tree impact plan:

- **Docs-only PRs:** `quality`, `integration`, and `build` run graph/link/whitespace checks only;
  `rehearse` runs `python3 scripts/ci-verify.py rehearse-scope`, prints the reason and exits early
  with green status.
- **`affected` and `product-frontend` PRs:** `quality` runs graph/link checks, global static/API
  checks and only the selected backend/frontend suites (`make test-frontend` for `product-frontend`);
  `integration` runs only selected integration files (or docs checks when empty); `build` builds only
  selected production services (`SERVICES=frontend` or `SERVICES=backend`); `rehearse` runs the full
  release rehearsal.
- **`product`, `full`, pushes to `main`, `workflow_dispatch`, and any fallback:** retain exhaustive
  remote checks (`make check`, `make test-integration`, both builds, full `rehearse`, and
  `release-migration` on `main`).

Missing/invalid platform SHA or a checkout at another SHA refuses before `quality`/`integration`/
`build` checks (and falls back to running full `rehearse` in `rehearse-scope`, catching any error
including import errors). Once checkout identity is proven, missing/inconsistent impact event
metadata falls back to full (while `ci/batch-*` still requires exact parent proof and platform-tree
validation before using `make_plan(base)`). Depth-two checkout retains the merge and both exact
parents. No local receipt or client impact metadata is trusted. Missing/invalid policy fails
`quality`/`integration`/`build` and falls back to full in `rehearse`. `make ci` remains exhaustive.
See the [CI-004 handoff/evidence](../../archive/CI-004/ci-004-verification-efficiency-handoff.md).

The implementing agent runs focused tests, relevant static/build checks and records uncovered risks.
A different agent or session performs independent QA: it reviews behavior/code, runs focused regressions for uncovered risks, fixes
ordinary defects, then freezes source **and index** and runs **one** `make feature-verify`. That
entry point selects FULL automatically when required; do not routinely chain `verify-full` after it.
CI-004 itself requires independent infrastructure QA and the complete FULL gate before delivery.
Only a post-gate change to verified content or the recomputed plan (including transient index impact),
a failed/interrupted gate, established release policy or explicit operator request warrants new
canonical execution. Commit the same verified tree without
a ceremonial rerun; validate its receipt after committing. Finish confirms merge/repository/resource
safety without rerunning comprehensive suites. Review handoffs may leave the final gate pending when
the operator owns the next acceptance phase; never label that state `verified`.

Remote stages retain their original output and 14-day full-log artifacts, add durations and report
failure exit status, command, prior passed stages and recovery guidance. Diagnose a failed test using
its exact file/case before repeating expensive suites. For an evidenced transient GitHub environment
failure on an unchanged SHA, rerun only failed jobs (`gh run rerun RUN_ID --failed`) or one job
(`gh run rerun --job JOB_ID`); do not automatically retry assertion failures. Existing successful
independent jobs can remain evidence for that same run/SHA. Code or dependency changes require a
new commit/run and a new local receipt. Local gate startup invalidates its previous receipt; a
failed/partial gate never leaves new delivery evidence. Remote failures do not alter the local
receipt, but delivery continues to require successful current-SHA remote checks.

### Quality and Docker resources

```bash
make quality-status       # Exact invoking worktree metadata/project and resource counts
make workflow-resources   # Known Florabase environments, legacy/unknown resources, image/cache policy
make quality-clean        # Explicit destructive retirement of ONLY this worktree's Quality state
```

To inspect and retire finished-work leftovers one project at a time:

```bash
make workflow-cleanup-report
python3 scripts/workflow_cleanup.py --project <exact-project> --confirm <reported-token>
```

The first command is read-only for Docker resources. It reports unproved resources without an
available action. Confirmation is operator-only and binds the exact project, eligible action and
inventory identity; re-run the report if anything changes. It removes positively owned Quality
and disposable resources or stops an eligible UAT instance while retaining its volumes. Protected
persistent projects are never targets. Missing sources are considered only on the default local
Docker socket, with no explicit Docker host/context; registered missing worktrees and surviving
Quality metadata refuse. Existing sources require a clean, unclaimed worktree with validated finish
proof. Ambiguous and legacy resources remain report-only. For a disposable run, a durable marker
is written only after its body completes normally; a crash, interruption or failed body has no such
proof and requires the exact recovery procedure printed by the run. This intentionally does not
infer that an unlocked crashed run has finished. The marker and project locks coordinate supported
local helpers; direct Docker, Git and non-cooperating processes can still race the checks. Stop
external writers before confirmation. No global Docker prune or cache removal is performed.

Quality remains reusable during feature work; individual test/lint/type commands do not retire it.
Quality services run under the generated `quality` override with `network_mode: none` (and no
project networks), while `make dependency-update` and `make dev-references-setup` opt into Docker's
shared `bridge` network via `--quality-network` (the `quality-network` override). `make dependency-update`
refreshes `frontend/pnpm-lock.yaml` through the dedicated `frontend-lockfile` (`toolchain`) service
without building or mounting `frontend_node_modules`; any non-offline `frontend` run clears its
Quality offline provenance marker so subsequent offline Quality refuses mixed state until
`make quality-clean` restores a clean volume. Ordinary Quality runs
therefore allocate zero Docker bridge subnets. Its project derives from the exact Git metadata path. New resources carry workflow lifecycle, owner
metadata and source labels as well as Compose project identity. Legacy Quality containers require
exact source/role; legacy networks and the three known volume keys require exact deterministic
project/Compose metadata. Unknown ownership refuses before mutation. Another worktree's resources
are never selected. `feature-finish` retires the current Quality project only after all existing
PR/merge/branch/primary Git safety checks pass, before detaching or switching source. Failure retains
the branch and reports diagnostics. It does not retire Review/UAT state.

Cleanup validates ownership and foreign resource users, removes exact container IDs (including
orphans), network IDs and volume names, then verifies retirement. No name-substring/blacklist cleanup
or shared-daemon prune is used. Cleanup cannot adopt persistent projects. SIGKILL/daemon loss cannot
run a process's cleanup; the failed-run log provides an exact owner/project/source recovery command.
Use that command from the owning source after restoring Docker access; never substitute global prune.
Status does not inspect collection data, environment secrets or unrelated workloads.

Verification image builds use unique labelled projects and retire exclusive image outputs. Normal
`make build` still builds the persistent production tags. Legacy or multiply tagged/shared images
are retained. Current builds use the daemon's shared default BuildKit builder; cache lacks a safe
project ownership boundary, so automatic cache deletion is deliberately absent. A dedicated builder
would require a separately evaluated dependency/cache migration and is not required here. The
resource report states this residual. Do not run global Docker system/container/image/volume/network/
builder/buildx prune as normal automation. For address-pool, disk/cache or volume failures, inspect
`make workflow-resources` and use only exact owning-worktree/run retirement; unknowns remain intact.

For a review before committing, check the dirty/untracked worktree explicitly:

```bash
python3 scripts/feature-tree-fingerprint.py verify --worktree \
  --branch "$(git branch --show-current)" --base "$(git merge-base origin/main HEAD)"
```

Delivery uses the default stricter receipt check: both committed `HEAD` and the working tree must
match. A valid uncommitted verified tree therefore passes `--worktree` and correctly fails the
delivery check until committed; this alone does not mean verification is stale.

The operator runs `make feature-deliver` only after review and commit. Delivery requires a clean exact
verified tree, expected origin, authenticated `gh`, correct PR/branch identity and current-SHA protected
checks; it never moves a checkout or upgrades databases. Missing `gh`, authentication, origin, receipt,
API and PR identity failures have explicit diagnostics. Protected squash auto-merge is unchanged.

After a proven merge, `make feature-finish` from a linked feature worktree requires a clean primary
checkout on `main`, fast-forwards it through Git's normal index/worktree update, detaches the
feature worktree at its reviewed SHA, records its finish proof, deletes only the proven merged
feature branch, fetches and prints primary status, and then runs best-effort retirement from the
primary checkout using the primary's helper. Managed worktrees under `florabase-worktrees/` are
retired automatically when every retirement guard passes (`FEATURE WORKTREE RETIRED: <path>`,
`Your shell is in a removed directory: cd <primary>`, `WORKTREE: RETIRED <path>`). If any guard
refuses (including owned Review/UAT/Preview resources or Docker unavailable), finish still exits 0
and retains the worktree with the exact refusal reason, follow-up command, and final
`WORKTREE: RETAINED <path> (<reason>)` line. Pass `KEEP_WORKTREE=1` to keep the detached worktree
without attempting retirement; provider-managed worktrees are always retained for the tool that
created them. A dirty/staged primary or unexpected primary branch receives an actionable refusal
with feature source retained. Single-checkout manual finish still switches to updated `main`.

