# INFRA-MAINT-001 — persistent UAT lifecycle and Dependabot defer policy

Implementation candidate from authoritative main `ec992440cba2681ca6e5327ec613a25f88183c3d`,
branch `ci/infra-maint-001`. Infrastructure only; SCHEDULE-002 remains delivered and verified.
Independent QA owns the canonical gate and delivery. Changes remain unstaged/uncommitted.

## UAT ROOT CAUSE

Ordinary UAT commands delegated feature context to `Repository.initialize()`, which requires an
attached feature branch based on cached origin/main. Finish deliberately retains the linked source
at the original feature commit and deletes its branch. With squash delivery this HEAD is usually
not an ancestor of main. Only destructive retirement understood detached owners. Persistent
volumes remained owned, but ordinary management refused them.

Initial live inspection also found stopped backend/frontend with previous Docker source-file mount
errors; the PostgreSQL service remained healthy. This is recorded separately from the Git guard.

## UAT DESIGN

Extend the existing UAT helper and resource contract. Keep the exact owning linked source path,
fixed project, DB identity, loopback URL, three named volumes and fixture marker. Add
`make uat-preview-sync` as an explicit forward transition. No environment is adopted by another
worktree and ordinary up/status/seed never fetch or change Git.

Status reports actual service running/stopped health, source path/current HEAD, launch HEAD,
attached/detached context, cached delivered-main relationship, DB/code revisions, fixture
version/state/count, interrupted intent, URL and next commands. Invalid/foreign identity and
incompatible schema return failure with diagnostics; status never starts the DB. Stopped DB
revision is explicitly unavailable.

## DETACHED OWNER

Require a clean linked source, expected GitHub origin, all three existing volumes with exact source
labels, exact container project/role/source/mount/DB/port identities, recognized launch Git
identity, no unexpected mounts or foreign resource users, and the ready fixture/identity marker.
A detached source with no established UAT cannot create a fresh environment.

Delivery proof accepts a source commit contained in cached origin/main. For a squash head, query
GitHub's commit-associated PRs read-only: exactly one closed/merged PR must have this exact head,
Florabase/main base, a merge commit contained in cached origin/main. Concurrent main changes may make the merge
tree differ from the reviewed head; exact PR delivery is still valid, and sync advances to the
complete delivered main tree.
Missing authentication/network/proof fails closed. No inference from matching files alone.

## STALE OWNER / SYNC

Run commands from the existing owning checkout. An older owner can use the implementation's
Makefile without copying code or changing the invoking source:

```bash
cd /path/to/established/uat/owner
make -f /path/to/reviewed/implementation/Makefile uat-preview-status
make -f /path/to/reviewed/implementation/Makefile uat-preview-sync
```

Sync requires clean detached delivered ownership, then normal `git fetch --prune origin`, pins
origin/main, checks delivered-history ancestry and target migration metadata before changing
source. It starts only the validated existing DB if stopped, checks actual database identity and
forward compatibility, writes atomic durable intent in this worktree's Git metadata, stops all
UAT application writers, and uses normal `git switch --detach <pinned-main>` in the same owner.
It builds that code, upgrades forward, initializes permissions/dependencies, recreates services,
waits for health and rechecks volumes/markers/revisions. It never seeds automatically.

The journal pins before/target/source/project and original volume creation identities/labels.
Interruption retains volumes, stopped writers and the journal. Repeated sync resumes that exact
pinned target, even if main has advanced further; invoke sync again afterward for the later main.
Up/seed refuse pending intent; status/stop remain available. Failures never automatically roll
back code or downgrade a migrated DB. Inspect ambiguous metadata instead of deleting it.
CLI mutations use a nonblocking per-owner lock. External Docker/Git operations can still race;
identity and source/volume checks detect changes at transition boundaries.

## DATABASE SAFETY

Use the existing literal Alembic graph and forward-upgrade guard. Target metadata is inspected
before source switch or migration; unknown/ahead revisions refuse. Runtime queries verify actual
`florabase_uat` database/user and resulting code head. Applications stop before schema upgrades.
Ordinary up starts the existing DB without rebinding it for this preflight. Seed requires DB at
code head. No automatic downgrade, data copy, startup migration or new application migration.

## RESOURCE SAFETY

Every ordinary lifecycle operation now checks foreign volume users and network endpoints as well
as the existing ownership checks. Stop retains containers/network and all volumes, allowing
stopped-owner inspection and restart without losing proof. Sync preserves their creation
identities and source labels; the source path is stable, so no volume or marker relabel is needed.
Only containers refresh their Git launch identity after the validated transition.

Remove/reset remain explicitly destructive commands with existing exact confirmation tokens.
Reset retains its attached-feature-only contract and now refuses a detached owner before stopping
anything; guarded remove still supports delivered detached retirement.
The real UAT is never passed to them. Disposable smoke cleanup remains positively owned and
registered before creation; no global cleanup or unrelated environment mutation.

## FEATURE-FINISH RELATIONSHIP

`feature-finish` is unchanged. It proves delivery, retires only its Quality environment, detaches
and removes its feature ref. It does not stop/sync/seed or retire UAT. The retained source must stay
on disk while UAT binds it; do not archive an active UAT owner. Legacy squash owners use exact
read-only PR proof, so no new finish metadata is required.

## REAL UAT PRESERVATION

Recovered only through the new supported command:

```bash
make -C /home/alessandro/.codex/worktrees/6147/florabase \
  -f /home/alessandro/.codex/worktrees/947e/florabase/Makefile uat-preview-sync
```

The same source `/home/alessandro/.codex/worktrees/6147/florabase` advanced from clean detached
`ff6ab788980845cfd1d5c3a985acb808983c2e80` (exact merged PR #105 head) to clean detached delivered
main `ec992440cba2681ca6e5327ec613a25f88183c3d`. Source/container Git labels now agree. All three
application/DB services are running and healthy; the one-shot initializer exited normally.
DB/code remain `20261009_0041`; the journal is complete/removed. No new migration was needed.

[Before/after machine evidence](infra-maint-001-evidence.json) proves identical:

- Full normalized DB data SHA-256 `0d4bc56614ecfea61bb67cbb9603dab23b257591e286c735f6ed71b1a5450155`,
  including all persisted operator records and owner credentials before the subsequent login check.
- Original volume names, creation times and labels for DB, media and dependencies.
- Complete v4 ready fixture, all **68** manifest IDs and extension metadata; representative Suppliers
  and counts (**1** owner, **2** Plants, **9** SeedLots, **19** ScheduledActivity, **2** media assets).
- All **5** files in the media volume, including workflow/fixture markers, lock and binary evidence.
- The ignored WFO index and seal hashes, retaining meaningful collection Taxonomy.

Normal authentication then returned **200** for `preview / preview`, authenticated SeedLots and
readiness through the real loopback frontend. This normal login creates an auth session **after**
the exact DB preservation snapshot; credentials were not reset. No real seed/reset/remove occurred.
DEV/Feature Review/Stable Preview/production container identities/start times/mounts, volumes,
running DB digests and primary Git identity match their before-recovery snapshots exactly.

Until this increment is delivered, the owner's historical Makefile still has its historical guard.
Manage it through the reviewed candidate Makefile above, substituting `uat-preview-status`,
`uat-preview-stop` or `uat-preview-up` as needed. After this candidate merges, explicit sync from
that same owner loads the newly delivered helper; ordinary owner-local Make targets then work.
Keep the candidate and UAT owner on disk while this interim helper path is in use.

## DEPENDABOT ROOT CAUSE

The delivered maintenance baseline intentionally rejected SQLAlchemy 2.1, React 19.3, jsdom 30.1
and Node declarations beyond 24. Closed PRs had no source-controlled ignore policy, so weekly
version automation generated equivalent proposals again.

## DEPENDABOT POLICY / DEFERRED VERSIONS

| Dependency                                       | Ignored range      | Maintained proposals | Remove ignore when                                                                                                                         |
| ------------------------------------------------ | ------------------ | -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| sqlalchemy                                       | `>=2.1,<2.2`       | 2.0.x                | Dedicated ORM typing/application, autoflush/transaction and PostgreSQL concurrency migration review                                        |
| react, react-dom, @types/react, @types/react-dom | `>=19.3.0 <20.0.0` | Matching 19.2.x      | Repository-supported reproducible real-browser acceptance covers create/edit, profile clearing/focus, Schedule, Leaflet and runtime errors |
| jsdom                                            | `>=30.1.0`         | 30.0.x               | Explicit Node-support decision or a supported release resolves compatibility with the complete declared range                              |
| @types/node                                      | `>=25.0.0`         | 24.x                 | Runtime/support contract deliberately moves beyond Node 24                                                                                 |

No dependencies, manifest pins, lockfiles, runtime contract or Docker image versions change.
React's remaining 19.x minors share the browser gate; future major React/SQLAlchemy proposals
remain separate review candidates, never automatic acceptance. The existing jsdom 30.0.1 engine
floor mismatch with part of `>=24 <25` remains documented, not hidden or resolved here.

## GROUP BEHAVIOR

Both existing minor/patch groups and all three weekly ecosystems remain unchanged. Dependabot
filters ignored versions per dependency; unaffected packages remain eligible for the group.
No wildcard ignore, global minor suppression, group exclusion or disabled automation.
GitHub's [official options reference](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference#ignore)
specifies native package-manager range syntax and filtering before update selection.

## OPEN BOT PR CLEANUP PLAN

After this infrastructure candidate passes QA and merges to main, QA must re-read and close:

- [#102](https://github.com/alessandrorossato/florabase/pull/102): deliberately deferred SQLAlchemy 2.1.
- [#103](https://github.com/alessandrorossato/florabase/pull/103): deliberately deferred React 19.3/types and jsdom.
- [#104](https://github.com/alessandrorossato/florabase/pull/104): incompatible Node 26 declarations for Node 24.

Then list all open Dependabot PRs and verify no equivalent proposal remains; inspect the next weekly
run to confirm compatible group updates continue. All three were confirmed open read-only during
implementation. No bot PR was merged, closed, commented on or otherwise mutated here.

## TESTS

Focused validation passed; canonical `make feature-verify` was not invoked:

- `make test-uat-preview`: **19** existing UAT guards plus **15** delivered-source/resource/sync
  tests. Temporary Git fixtures cover attached, clean/dirty/unestablished detached, current/behind/
  ahead/unrelated, exact squash proof with a concurrent main tree, wrong labels/mounts/markers,
  foreign volume/network users, stopped/current/incompatible status, forward sync, unknown/ahead/
  unversioned DB, replaced volumes, interrupted/pinned-target recovery, pending up/seed refusal,
  detached reset refusal and seed compatibility.
- Environment workflow **29**, feature verification/delivery helpers **41**, resource helpers **14**,
  Stable Preview **19**, impact/receipt **19**, and shell workflow helper suite all pass. These are
  focused offline fixture checks, not execution of the canonical feature gate.
- `make smoke-uat-preview`: unique disposable project
  `florabase-uat-preview-smoke-c7fa48e9e127`; **25** real PostgreSQL fixture/guard tests; startup,
  real login, operator edits/new record, repeated seed, stop/up, ahead refusal, confirmed disposable
  reset/removal, wrong-owner refusal, real fixture `feature-finish` and repeated detached status/
  stop/up/seed; newer locally delivered main with forward migration; injected interruption after
  source switch; status/stop and ordinary-action refusal; explicit sync resume. Full domain row
  hashes, credential row, fixture/media hashes and dependency-volume sentinel remain identical.
  Registered exact owned cleanup reports **zero** residual containers/networks/volumes; protected
  real environments and primary match their snapshots. Only synthetic Git fixtures were staged,
  committed/pushed to temporary local bare repositories or finished; the real candidate was not.
- `make workflow-check`: policy validation, Ruff lint and format-check (**22** helper files), strict
  mypy (**15** runtime files plus **2** fixture/migration helper files). Known native npm ranges are
  exercised using the already pinned SemVer tool; no new parser/emulator/dependency is installed.
- Affected Markdown/JSON/YAML/JavaScript Prettier check, Node syntax check, feature graph (**101**
  valid), shell syntax and `git diff --check` pass. Product implementation/manifest/lock/generated
  API diffs are empty. No whole-product unit/integration/build or browser visual gate is claimed.

Earlier smoke attempts exposed test setup faults (embedded program indentation, finish working
directory and local fixture fetch selection); each cleaned its registered resources. They were
corrected, and the final complete run above passes. PostgreSQL's circular-FK data-dump warnings
were emitted during read-only digest snapshots; no restore was attempted and preservation matches.

## DOCUMENTATION

Canonical development workflow and dependency-maintenance baseline describe persistence,
delivered/stale owners, explicit same-path sync, interruption recovery, destructive commands,
version deferrals/reopening events and post-delivery PR cleanup. The feature graph records this
consolidated increment as implemented, leaving all existing feature statuses unchanged.

## DEFERRED

Canonical `make feature-verify`, independent QA, staging, commit, push, PR creation, delivery and
post-merge bot cleanup belong to the next phase. No product/domain/UI change or deferred upgrade.
General browser acceptance infrastructure and the Node-contract decision remain separate work.
