# Feature Review and UAT environments

> Summary: UAT Preview, parallel per-worktree UAT instances, and Feature Review browser acceptance workflows.

## UAT Preview and operator acceptance

```bash
make uat-preview-up
make uat-preview-seed          # Explicit first-use seed; UAT-only preview / preview
make uat-preview-status
# Open http://localhost:15174
make uat-preview-stop
make uat-preview-up            # Same owner, collection, operator edits and media
make uat-preview-sync          # Explicit forward update after delivery/finish; preserves state
# Destructive return to the canonical synthetic baseline:
make uat-preview-reset CONFIRM_RESET_UAT_PREVIEW=florabase-uat-preview
```

UAT extends Feature Review's existing dirty-source runtime, migration checks and persistence helpers.
It has its own project, `florabase_uat` database, DB/media/dependency volumes and network, and resolves
no `.env` secrets. It uses the same established loopback port 15174: Feature Review and UAT Preview
are alternative consumers of that port. Stop an existing Feature Review **from its owning worktree**
before starting UAT; stop retains its independent data. Stable Preview remains at 15173 and DEV at 5173. No automatic takeover, reset or copy of another environment occurs.

Startup builds the current worktree including untracked source, upgrades forward only and waits for
health. Source bindings remain live. Startup never creates an owner or synthetic records. Seeding is
explicit and provider independent; detached delivery proof may need GitHub access as described below. UAT's public `preview / preview` credential is synthetic fixture
state, **UAT PREVIEW ONLY**; production defaults and normal owner password validation are unchanged.
The seed helper is mounted explicitly by the host workflow and is absent from production images.
Before seeding, host guards check source/context, project, containers, origin, network, actual volume
mounts and Docker ownership. Runtime guards also check development cookie policy, UAT mode,
DB URL/user, a validated resource marker and `current_database()/current_user`.

Fixture version 4 is a small basil/lavender/aloe collection with Suppliers, a Location hierarchy,
synthetic provenance, varied SeedLots, active/historical Sowings, direct/derived Plants, a PlantGroup,
observations, a Harvest and shared local/primary/external media. ORDER-001 adds an exact-date EUR
purchase with two separate basil packets and a month-only purchase with unknown Supplier/price. Local PNG content is generated through
the normal upload service. External `example.invalid` metadata requires no fetch and deliberately
exercises the remote-image failure state. EXPLORE-001 adds a Historical-only exhausted radish packet,
a reference-only Viola identity, and an offline-confirmed basil taxon link (`48GBK`) verified through
the existing CoL XR provider on 2026-10-08. Lavender is Current non-living; basil/aloe are Living.
The snapshot is taxonomy metadata only: seeding makes no provider request and never fabricates
occurrence evidence or profile enrichment. EXPLORE-002 adds a Current sage packet without
structured range, synthetic broad+Brazil overlap, disjoint Italy/Thailand, a Historical broad range,
and a separate custom native area. These are explicitly labelled synthetic reference assertions
for UAT, not botanical evidence; provenance remains separate. Repeated seed preserves range edits. Its additive v4 refinement extension tracks managed basil
stored material (42 manifest records). A recognised original v4 manifest is validated before the
extension; existing operator inventory is adopted without changing its state. No reset is needed.
The fixture supports multi-species overlap/disjoint comparison and Seeds/Sowings/Plants/Plant groups/
Stored material category combinations. Native ranges uses explicit selection up to 20 and a separate
OR category filter; Explore groups its three map destinations under a non-actionable Maps label,
with Geography outside that subgroup. TAXONOMY-003 adds Taxonomy (`#/taxonomy`) outside Maps,
with the optional pinned WFO 2026-06 index/seal in ignored `backend/src/.source-cache/`.
Its explicit additive fixture extension confirms five real source IDs and adds a Holy basil identity/
packet (44 manifest records): basil/Holy basil share genus, basil/sage share family, Aloe and radish
exercise distinct families/higher ancestors; lavender remains unlinked. Repeat seeding preserves
operator link edits. Interrupted extensions remain `building` and require the guarded reset.
Mobile retains all destinations. See [taxonomy UAT handoff](../../archive/TAXONOMY-003/taxonomy-003-handoff.md).

The current manual-review fixture keeps version 4 and evolves through validated additive markers.
`dashboard_extension=1` adds a purchased packet without an Order link and unknown/zero germination
examples. `schedule_extension=1` and `schedule_calendar_extension=1` provide overdue/today/future,
completed/cancelled work, all six target types and same-day overflow. `manual_review_extension=1`
adds an `Ocimum basilicum` ‘Genovese’ identity with explicitly synthetic profile text, an unknown
quantity packet linked to the month-only Order, and whole-collection scheduled work. There are
66 manifest records, or 68 with the optional pinned WFO index and its Holy basil extension.
These are small interconnected review examples, not source-backed botanical assertions.

Persistent UAT at **http://localhost:15174** is the normal manual product-review dataset. Start it
with `make uat-preview-up`, inspect `make uat-preview-status`, and sign in with the UAT-only
**preview / preview** fixture owner. Explicit `make uat-preview-seed` initializes a fresh UAT or
applies missing recognized additive extensions; ordinary up never seeds or resets. Same-owner
stop/up preserves DB, media, operator edits and dependencies. Feature Review remains separate.
Schedule due dates are anchored to the UTC day of each explicit extension's first seed, following
the existing fixture convention. Repeat seed never rolls dates forward or reschedules edits.
To refresh overdue/today/future examples for a later review day, deliberately use the guarded
`make uat-preview-reset CONFIRM_RESET_UAT_PREVIEW=florabase-uat-preview`; that discards all UAT
operator edits. An incompatible/interrupted fixture still refuses ordinary seed and requires
this explicit reset. Keep the optional WFO index/seal in the owning worktree's ignored cache for
Taxonomy review; no reference-source download occurs during startup or seed.

The seed manifest lives outside production domain models in the UAT media volume and records service
created UUIDv7 identities. Repeating seed validates existing identities and binary integrity, leaves
all operator text/quantity/primary edits alone, and creates no duplicates. It does not recreate a
baseline object intentionally deleted by an operator: missing/partial/version-incompatible baseline
state refuses with an explicit reset instruction. Interrupted initial seeding remains marked
`building`; normal seed never guesses which unrecorded rows belong to fixtures. Reset is the sole
workflow for returning to a canonical baseline.

Reset requires an attached feature owner and the exact project token, and validates every target resource before stopping writers,
then removes only the individually identified `florabase-uat-preview_postgres_data`,
`florabase-uat-preview_attachment_data` and `florabase-uat-preview_frontend_node_modules` volumes.
It recreates health, owner and fixtures in one command. It never uses `down -v`, deletes a source
worktree or touches DEV/Stable Preview/production. A failed rebuild is actionable and may leave UAT
stopped or unseeded; rerun `up` and explicit `seed` after resolving the failure. Never delete a volume
manually to bypass identity refusal. A different worktree cannot adopt persisted UAT resources.

Persistent UAT survives feature delivery and `feature-finish`. Finish leaves the owning linked
source detached and removes its feature branch; it does not change the operator environment.
Do not archive that source while UAT uses its bind mounts. Ordinary status/stop/up/seed remain
supported for an established clean delivered detached owner. Delivery proof requires either HEAD
contained in cached origin/main or an exact squash-merged PR head with Florabase/main
base and merge commit contained in cached origin/main. Concurrent main changes can make its merge
tree differ from the reviewed head; the exact PR proof still permits management, and explicit sync
advances to the complete delivered main tree. The latter uses an authenticated read-only
GitHub query and fails closed when unavailable. Arbitrary/dirty/unmerged detached sources refuse.
Existing exact source/resource/DB/port/fixture guards still apply, including foreign volume users
and network endpoints. Stop retains containers, network and all three volumes.

Status distinguishes attached valid owner, detached delivered owner current with cached main,
stale delivered owner, missing UAT and invalid/foreign ownership. It reports current/launch HEAD,
service running/stopped health, fixture version/count, DB/code revisions and recovery guidance.
An incompatible DB returns a diagnostic failure; stop remains available. Status never starts a
stopped DB, so its revision is then explicitly unavailable. Ordinary commands never fetch or sync.

From the existing owning checkout, explicitly advance persistent UAT after delivery:

```bash
make uat-preview-status
make uat-preview-sync
make uat-preview-status
# Optional explicit additive extensions, after checking the upgraded fixture contract:
make uat-preview-seed
```

Sync requires a clean detached delivered owner. It validates existing ownership, fetches normally,
pins newer origin/main, inspects its migration graph, checks the actual preserved DB's identity and
forward compatibility, then stops application writers. A normal detached switch advances only the
owning source; primary main and other worktrees are unchanged. Code builds, forward migrations and
healthy container recreation reuse the same DB/media/dependency volumes and source labels. No
automatic seed, reset, downgrade or transfer to another source path occurs. Ahead/unknown DB
revisions refuse before the source changes or migrations run.

An atomic per-owner journal in Git metadata retains before/target/source/project and exact original
volume creation identities/labels. If interrupted, preserve it and rerun `make uat-preview-sync`:
recovery resumes the pinned target, even if origin/main has advanced again. Up/seed refuse incomplete
sync; status/stop remain supported. Failed transitions leave the volumes intact and writers stopped
when already quiesced. There is no automatic code rollback after a migration. Inspect ambiguous
metadata rather than deleting it or manually rewriting labels. CLI mutations hold a nonblocking
per-owner lock; direct external Docker/Git operations still require operator coordination.

An older delivered owner can invoke a reviewed/newer helper through its Makefile without copying
source files. Working directory continues to select the established owner:

```bash
cd /path/to/established/uat/owner
make -f /path/to/reviewed/implementation/Makefile uat-preview-status
make -f /path/to/reviewed/implementation/Makefile uat-preview-sync
```

Preservation is the normal lifecycle. `uat-preview-remove` and `uat-preview-reset` remain deliberately
destructive, with exact project confirmation and individually proved resource identities. Use them
only when intentionally discarding the synthetic collection, edits and media; they are unnecessary
for finish or later delivered-main updates. A different feature worktree cannot adopt persisted UAT.
See the [INFRA-MAINT-001 handoff](../../archive/INFRA-MAINT-001/infra-maint-001-handoff.md) for proof, smoke and recovery evidence.

## UAT instances (parallel, per worktree)

UAT Preview remains the one manual-review environment with the v4 fixture. When several features
need acceptance at the same time, each linked feature worktree can instead own one **UAT instance**
(MULTIBRANCH-UAT-001):

```bash
make uat-instance-up [PROFILE=smoke|comprehensive]   # First use allocates a port; default smoke
make uat-instance-seed                               # Explicit golden dataset generation
make uat-instance-status                             # Source/SHA, port, migrations, dataset manifest
make uat-instance-validate                           # Exit 0 verified, 1 invalid/refused, 3 changed, 4 unavailable
make uat-instance-stop                               # Preserve DB, media and dependencies
make uat-instance-list                               # Read-only: every slot, owner and state
make uat-instance-reset CONFIRM_RESET_UAT_INSTANCE=florabase-uat-branch-<branch> [PROFILE=...]
make uat-instance-remove CONFIRM_REMOVE_UAT_INSTANCE=florabase-uat-branch-<branch>
```

The project is `florabase-uat-branch-` plus the branch with `/` replaced by `-` (for example
`florabase-uat-branch-feat-example-001`); branches with `.` or `_` or longer than 40 characters are
refused. It reuses every UAT Preview guard (linked source, origin, exact container labels, mounts,
networks, internal DB/backend, loopback-only frontend, foreign volume users) with its own role label
`uat-instance`, `golden_uat` database and the additional generated `uat-instance` override. It
resolves no `.env` secrets and never reads, copies or mounts another environment's data.

**Allocation.** Four slots, ports 15180–15183, bound networks, image tags and memory. The record is
the labels of the instance's own volumes (`io.florabase.uat.instance`, `.port`, `.profile`), which
Docker cannot change, so a finished detached owner still finds its instance and the port and profile
stay fixed until reset or removal. First `up` takes the lowest slot that no other instance records,
no container (running or stopped) publishes and no other listener holds; it refuses another source's
instance name, a full pool and, by creating and removing one uniquely named probe network, Docker
address-pool exhaustion, all before building anything. Later starts re-prove the recorded port.

**Dataset.** Startup never seeds. `seed` runs the existing TEST-DATA-001/002 golden runtime
(`scripts/golden_dataset.py generate --profile <profile>`) in a one-off backend container with the
scripts mounted read-only. Its target guard accepts one persistent target only: workflow mode
`uat-instance`, a `florabase-uat-branch-*` project, development (never disposable) settings, the
instance's own `db:5432/golden_uat` and the standard media root; the disposable copy lifecycle
(`create-copy`, `retire-copy`) stays test-only. The golden ledger in the instance's media volume is the
dataset manifest that status prints (profile, seed, anchor date, plan digest, schema revision, state,
record count). Repeat seed is idempotent; a failed seed requires reset. `validate` runs
`verify-baseline`: an operator edit reports `invariant-valid-baseline-modified` (3), or `domain-invalid` (1)
when it moves a pinned read projection such as search counts; neither is an environment failure. Sign
in with the synthetic **golden-owner / disposable-golden-owner-password**, UAT INSTANCE ONLY.
Golden timestamps are anchored to the plan's fixed date, so schedules can read as past due.

**Capacity and locks.** Every mutating command holds a nonblocking per-instance lock. `up`, `seed`
and `reset` also hold the machine-wide `verification-full` capacity lock, so at most one heavy
instance build or seed runs and never beside a canonical FULL gate; the loser is refused with the
holder's purpose. `stop`, `remove` and `status` are never blocked by another instance. Only claims inside the pool count
against its four slots; `make smoke-uat-instance` uses ephemeral ports and also takes the capacity lock.

**Retirement.** Reset and remove refuse anything but the instance's exact project before any Docker
mutation, remove one-off seed/validate containers an interrupted run left (all proven to be this
project's backend from this source before any is removed), then use the UAT Preview retirement path: stop proven writers, remove only the proven
containers, network and three volumes, never `down -v`. Remove also deletes the two exact
`<project>-backend/frontend-development` tags unless still in use. `feature-retire` refuses a
worktree whose source still owns instance volumes, so remove the instance first.

**Rebuilt branch / stale launch.** Rebuilding an attached feature or batch branch from scratch (for
example with `git reset --hard` or `make feature-batch-prepare`) leaves existing instance
containers carrying a launched `io.florabase.sha` that is no longer an ancestor of `HEAD`
(UAT-INSTANCE-002). Attached `UATInstance` commands never call `gh api` to check delivered PR proof.
When every container, volume, network, mount, port, environment and volume-user check passes and the
40-hex commit still exists in this worktree's `HEAD` or branch reflog, `make uat-instance-status`
marks it `launched HEAD: <sha> (stale: not in current history)` and prints the next step,
`make uat-instance-stop` stops the proven containers, `make uat-instance-up` rebuilds and relabels
them from `HEAD` (keeping `require_upgradeable` migration safety and pointing to guarded reset if
the DB is incompatible, never auto-resetting), and guarded `make uat-instance-reset` /
`make uat-instance-remove` work without manual `docker rm`. `seed` and `validate` refuse until
`make uat-instance-up` rebuilds from `HEAD`. An unknown SHA not in the local reflog is still refused
by `status`, `stop`, `up`, `seed` and `validate`; if Git reflog expiry / `git gc` has pruned an old
commit, confirmed `make uat-instance-reset CONFIRM_RESET_UAT_INSTANCE=<project>` or
`make uat-instance-remove CONFIRM_REMOVE_UAT_INSTANCE=<project>` recovers once all other identity
checks pass. Singleton UAT Preview and detached owners keep the unchanged `delivered()` path.

Limits: synthetic WFO/WCVP indexes built during generation are not provisioned for the running app (see the [TEST-DATA-002 decisions](../../archive/TEST-DATA-002/test-data-002-design.md#next-step-separately-review-and-uat)). Browsers share `localhost` cookies across ports, so signing in to a second instance in the
same browser profile signs out the first (use separate profiles). An instance whose source worktree
was deleted cannot be retired by these commands; `make uat-instance-list` marks it as MISSING SOURCE
for operator cleanup. A leftover `dev-state-init` one-off is refused, not removed; inspect it manually. The workstation golden reference running production images is a separate
planned increment (GOLDEN-REFERENCE-001). Proof: `make test-uat-preview` (offline) and
`make smoke-uat-instance` (real disposable Docker).

## Feature Review and browser acceptance

```bash
make feature-review-up
make feature-review-bootstrap-owner LOGIN=owner    # first use only; choose your Review password
make feature-review-seed                           # representative synthetic data
make feature-review-status
# Open http://localhost:15174 and perform the relevant acceptance workflow.
make feature-review-stop
make feature-review-up       # Rebuild source; preserve and reuse Review state
```

`up` validates feature context and rendered isolation, builds the exact current source, initializes
volume ownership, starts PostgreSQL, checks migration compatibility, upgrades only Review to that
worktree's Alembic head, and waits for database/backend/frontend health. Dirty and untracked migrations
are included. Bind-mounted application source is live; backend reload and Vite reflect edits after
launch. Lockfile or image/dependency changes require another `up` so bootstrap runs again.

Status answers "what exact code am I looking at?": source, current branch/full SHA/dirty state,
launch SHA, health, DB current, code head, URL, project, network and all persistent volume identities.
One Review environment is supported. Containers and volumes carry source ownership; another worktree
cannot take over those resources, even after a normal stop. Remove from the owning worktree first.

`feature-review-seed` explicitly reuses the UAT v4/manual-review fixture **code**, never UAT data or
volumes. It requires healthy, exactly owned `florabase-feature-review` resources and a DB at code head;
runtime guards also verify `florabase_review`, loopback development authentication, and Review's own
media root. It refuses every other project, foreign ownership, shared resources and ambiguous state.
One enabled Review owner must already exist; its login, password, sessions and settings are retained.
Collection records use the application's existing single-owner collection model and domain services.
Review-only additive `lineage_explorer_extension=1` adds 47 [LINEAGE-003 ancestry](../../features/explore/lineage-explorer.md)
records (branching, conversions, unknown origins, reversals and a paged flat) through owning services.

`make feature-review-extended-seed` adds the separately versioned
[Extended Botanical Review Dataset v5](../../archive/review/extended-botanical-dataset-v5.md) to a ready v4 Review.
`make feature-review-extended-status` validates its ledger and reports counts. Both repeat exact
host/resource/runtime ownership checks and refuse DEV, UAT, Sourcing, Stable Preview and production.
The extension never resets the database/media, changes credentials, overwrites operator edits or
changes UAT's baseline semantics. It uses a separate `.review-dataset-v5.json` ledger and the same
Review lock. Packaged licensed photographs are mounted read-only; seeding makes no external requests.

The dataset has **66 managed records**, or **68** when the configured approved WFO snapshot is available:
identities, Seeds, Sowings, Plants/PlantGroups, Locations, geography/native ranges, Stored material,
Harvests, Suppliers/Orders, Journal/History facts, Schedule examples and generated local/shared media.
External media uses an intentionally offline reference; occurrence evidence is not fabricated. Missing
optional taxonomy source data remains a truthful limitation. Seed never downloads a new reference source.
The ledger, identity and lock are `.review-fixture.json`, `.review-identity.json` and `.review-fixture.lock`
inside Review media storage; UAT bookkeeping is separate. Status reports fixture version/state/count.
Rerunning validates its managed IDs/media and preserves operator edits; known additive extensions run
once. A nonempty unrecognized collection, missing managed record/media, incompatible version or
interrupted `building` ledger refuses instead of repairing, resetting or duplicating state. Inspect such
state before explicitly deciding whether to retain it or authorize guarded Review removal.

Stop removes containers/network but **preserves DB, media and dependencies**. Destruction is separate:

```bash
make feature-review-remove CONFIRM_REMOVE_REVIEW=florabase-feature-review
```

This explicitly deletes only that project's DB/media/dependency volumes and prints their names.
It cannot target DEV, Preview or production. It does not remove the feature worktree. There is no
automatic DEV data reuse and no Review import helper. Synthetic data is supported; realistic cloning
requires a coordinated DB-and-media snapshot, a destination replacement confirmation and revision
compatibility checks. That complete clone is deferred. The old database-only Preview import now
refuses before reading or replacing data because it could create dangling media references.
