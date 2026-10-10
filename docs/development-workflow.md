# Development, review, preview and production workflow

This is the canonical environment and feature lifecycle contract. Codex manages its own worktrees;
Florabase validates feature context and runs environments from explicit source trees. It does not
create a second feature worktree or move the primary checkout off `main`.

| Environment      | Source                                                      | Compose files                                | Project                                  | Browser                    | State                                                         |
| ---------------- | ----------------------------------------------------------- | -------------------------------------------- | ---------------------------------------- | -------------------------- | ------------------------------------------------------------- |
| DEV              | Primary checkout discovered through Git                     | `compose.yaml` + `compose.dev.yaml`          | `florabase`                              | `http://localhost:5173`    | Persistent DB, media, dependencies                            |
| Feature Review   | Current feature worktree, including dirty/untracked files   | baseline + DEV + `compose.review.yaml`       | `florabase-feature-review`               | `http://localhost:15174`   | Persistent, isolated DB/media/dependencies                    |
| UAT Preview      | Current feature worktree, including dirty/untracked files   | baseline + DEV + Review + `compose.uat.yaml` | `florabase-uat-preview`                  | `http://localhost:15174`   | Persistent isolated synthetic DB/media/dependencies           |
| Stable Preview   | Clean detached checkout of fetched `origin/main` by default | baseline + `compose.preview.yaml`            | `florabase-preview`                      | `http://localhost:15173`   | Persistent isolated DB/media, immutable frontend dependencies |
| Quality checks   | Current feature worktree                                    | baseline + DEV                               | `florabase-quality-<metadata-path-hash>` | None started               | Isolated dependency/media volumes, no live DB required        |
| Integration / CI | Current source / CI checkout                                | `compose.integration.yaml`                   | `florabase-integration-<random-run-id>`  | None                       | Disposable PostgreSQL tmpfs and test state                    |
| Production       | Selected deployable source/artifact                         | `compose.yaml`                               | `florabase-prod`                         | Proxy port 8080 by default | Persistent DB/media                                           |

Migration verification (`florabase-feature-migration-<run-id>`), selected production verification
builds (`florabase-verification-build-<run-id>`) and unique smoke fixtures are also disposable.
Integration, migration and smoke register retirement before creating resources and verify zero owned
containers/networks/volumes after success, failure, partial creation and caught INT/TERM. A cleanup
failure fails the workflow. Images with exact ownership and no foreign tags/users retire; ambiguous
images and shared BuildKit cache remain and are reported. DEV, Review, UAT, Stable Preview and
production never use this automatic retirement. The fixed `florabase-perf` benchmark is explicitly
operator-managed reusable test state, not a unique per-gate fixture; its manual stop contract remains.

DEV deliberately retains the legacy explicit project name `florabase`. Renaming it to
`florabase-dev` would silently select an empty database instead of the operator's existing data.
Every helper passes an explicit project and project directory; none rely on the directory basename.
Compose prefixes DB, media, dependencies, networks, containers and development image tags with that
project. Review does not publish PostgreSQL/backend ports. Production has no Vite, source binds,
development port exposure or mutable dependency volume. Preview uses production builds and the
same-origin proxy with loopback cookie policy, not a Vite server.

## Existing Codex worktree

The primary checkout remains on `main`. Open the Codex-provided worktree and run:

```bash
make feature-init
# Only when Codex left a clean detached HEAD at origin/main:
make feature-init BRANCH=ci/example
```

Initialization validates repository identity, branch naming, source path and the cached `origin/main`
base. It prints branch, SHA, dirty state, primary path and common metadata without revealing secrets.
It is idempotent on an existing compatible feature branch, including dirty source. It never fetches
implicitly or discards changes. Fetch `origin/main` deliberately before initial setup when needed.
Detached attachment requires a clean tree exactly at `origin/main`; an existing branch must contain
that base. Unsupported states receive a refusal rather than a reset, stash or branch rewrite.

Manual development can still use `make feature-start BRANCH=feat/example`. In a primary checkout it
fetches, fast-forwards clean `main`, then creates the branch as before. In a linked worktree it fetches
and delegates to initialization in that worktree, without attempting to switch shared `main`.

## Configuration

Runtime helpers resolve configuration in this order: explicit `FLORABASE_ENV_FILE`, the selected
source's `.env`, then the primary checkout's `.env`; absent configuration uses `/dev/null` and Compose
reports required values for DEV/production. Git discovery supports a linked-worktree `.git` pointer
and paths containing spaces. No `.env` copy or symlink is required. Commands report only the file
path, never its contents or interpolated database URLs.

Review uses fixed local-only database credentials and port overrides regardless of the resolved
configuration. Stable Preview ignores `.env` entirely and uses its existing local-only settings.
Quality checks also override database identity and do not access DEV's database. The environment
resolver is local configuration reuse, not a secret-management framework.

## DEV

```bash
make dev-up        # `make dev` remains an alias
make dev-status
make dev-upgrade
make dev-bootstrap-owner LOGIN=owner
make dev-stop
```

These commands select the primary checkout even when invoked in a Codex feature worktree. Status
prints that source's current branch/SHA/dirty state, URL, project, network, volume names, service
health, code head and DB revision. Existing containers bound to another source cause an explicit
refusal instead of silently acquiring new source mounts. `dev-up` does not migrate the database;
`dev-upgrade` builds the current primary backend and `dev-state-init` images and checks that the
initializer is executable in the rendered image before starting the DB or applying migrations.
The read-only, network-disabled preflight runs directly from that exact image without mounting DEV
volumes. The initializer shares the frontend development image; an existing local image is never treated as proof of freshness. Upgrade
checks migration compatibility, applies `upgrade head`, confirms the revision, then initializes DEV
volume ownership. Retrying when the DB is already at code head is safe: images are still prepared,
Alembic performs no pending migration, and ownership initialization repeats without replacing data
or volumes. No command automatically downgrades.

### Returning old-worktree DEV to primary

Use the supported commands from the current feature worktree or the updated primary checkout:

```bash
make dev-status    # Shows expected primary source, actual old source and recovery action
make dev-stop      # Identifies and stops existing DEV through Docker metadata
make dev-up        # Recreates application containers from primary after the DB compatibility check
```

`dev-stop` works even if the old checkout was moved or deleted. It validates the exact `florabase`
project, recognized services, development role (or the established legacy Compose metadata), source
mounts and project-owned DB/media/dependency volumes. Ambiguous identities, one-off containers or
another environment's metadata cause refusal before stopping anything. It retains the containers,
network and **all volumes and persistent data**; it does not run Compose `down`, remove containers,
delete volumes, alter Git or migrate the DB. Repeated stop is safe. Review stop/remove and Preview
cleanup retain their own separate semantics.

Docker tmpfs disappears on container stop. For the older `/tmp/florabase-attachments` media root,
`dev-stop` first freezes the backend, copies missing regular files into its already-mounted
`florabase_attachment_data` volume, and verifies both the copied files and pre-existing durable files.
The fixed Python helper reads the live tmpfs through the paused backend's PID namespace; Docker
`cp` does not support this source. It has no network or source binds, a read-only root filesystem,
only the validated media volume writable, and only the `SYS_PTRACE`/`DAC_OVERRIDE` capabilities
needed to read that non-root process's filesystem and preserve its files. It uses the pinned
`python:3.14.7-slim-bookworm` image (pulled if absent); unavailable runtime leaves the backend running.
It never overwrites conflicting content or deletes media. A copy failure, conflict or unsupported
entry leaves the legacy backend running with its original tmpfs intact. After successful preservation,
the frozen backend is killed without reopening a write window; PostgreSQL is stopped normally after
the application containers. In-flight backend requests are interrupted. No operator `chown`, manual
Docker recovery or separate media migration is required for the recognized legacy layout.

`dev-up` still refuses running foreign-source application containers. After `dev-stop`, it validates
the retained stack, starts the existing DB without rebinding it, and compares DB current with primary
code head before dependency initialization or application recreation. Ahead/unknown revisions refuse
startup or upgrade with `DB CURRENT IS AHEAD OF OR INCOMPATIBLE WITH CODE`; no downgrade occurs. DEV
does not migrate implicitly. If an upgrade is needed, explicitly run `make dev-upgrade` using primary
code. Stop again before retrying startup after an ahead refusal, and first update primary `main` to
code that knows the preserved revision. When compatible, startup recreates the containers using
primary source and the same DB/media/dependency volumes, repairing ownership through the normal
initializer. Primary must contain this workflow and its durable media configuration before recovery
startup; attempting startup against the older tmpfs override is refused.

This recovery preserves state in place. It is not a backup: retain coordinated DB/media snapshots
before production-like upgrades, and do not treat a database-only dump as complete recovery.

## Operator environments

Use **DEV** for coding/debugging with developer data, **UAT Preview** for accepting the current
feature with synthetic data, and **production** for real collection data. **Stable Preview** is the
engineering snapshot of an explicit stable Git ref; its `preview*` commands are unchanged.

## UAT Preview and operator acceptance

```bash
make uat-preview-up
make uat-preview-seed          # Explicit first-use seed; UAT-only preview / preview
make uat-preview-status
# Open http://localhost:15174
make uat-preview-stop
make uat-preview-up            # Same owner, collection, operator edits and media
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
explicit and network independent. UAT's public `preview / preview` credential is synthetic fixture
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
Mobile retains all destinations. See [taxonomy UAT handoff](taxonomy-003-handoff.md).

The seed manifest lives outside production domain models in the UAT media volume and records service
created UUIDv7 identities. Repeating seed validates existing identities and binary integrity, leaves
all operator text/quantity/primary edits alone, and creates no duplicates. It does not recreate a
baseline object intentionally deleted by an operator: missing/partial/version-incompatible baseline
state refuses with an explicit reset instruction. Interrupted initial seeding remains marked
`building`; normal seed never guesses which unrecorded rows belong to fixtures. Reset is the sole
workflow for returning to a canonical baseline.

Reset requires the exact project token, validates every target resource before stopping writers,
then removes only the individually identified `florabase-uat-preview_postgres_data`,
`florabase-uat-preview_attachment_data` and `florabase-uat-preview_frontend_node_modules` volumes.
It recreates health, owner and fixtures in one command. It never uses `down -v`, deletes a source
worktree or touches DEV/Stable Preview/production. A failed rebuild is actionable and may leave UAT
stopped or unseeded; rerun `up` and explicit `seed` after resolving the failure. Never delete a volume
manually to bypass identity refusal. A different worktree cannot adopt persisted UAT resources.

Before moving UAT to the next feature, deliberately retire the old synthetic state from its owning
linked worktree (including a delivered, detached owner):

```bash
# In the old owning worktree: discards its UAT collection, edits, media and dependencies.
make uat-preview-remove CONFIRM_REMOVE_UAT_PREVIEW=florabase-uat-preview
# In the next active feature worktree:
make uat-preview-up
make uat-preview-seed
make uat-preview-status
```

Removal validates the exact project, source labels, source mounts, service settings, all three
named volumes and the scoped internal network. Foreign container users of a volume or network,
missing/wrong confirmation and non-owning sources refuse before stopping anything. It stops UAT
writers, rechecks identities, removes only proved UAT containers/network and individually removes
the three volumes above. It never uses `down -v`, rebuilds, seeds, edits Git/source or changes
DEV/Stable Preview/Feature Review/production. A partial failure reports an error; resolve it and
rerun removal from the same owner. Stop preserves ownership; reset rebuilds under the same owner;
remove releases ownership for a fresh baseline. Cross-worktree state transfer is still excluded.

If an old owner predates this command, invoke the corrected Makefile **while keeping that old
worktree as the current directory**. The removal target resolves its helper from that Makefile,
while ownership and Compose sources resolve from the invoking checkout:

```bash
# Example: run from /home/alessandro/.codex/worktrees/80b3/florabase
make -f /home/alessandro/.codex/worktrees/9f48/florabase/Makefile uat-preview-remove \
  CONFIRM_REMOVE_UAT_PREVIEW=florabase-uat-preview
```

No source copying, branch switching, ownership-label changes or manual Docker deletion is needed.

The browser has no additional environment badge; CLI/status identity and Preview-prefixed fixture
labels provide the distinction without changing the application shell.
See [PREVIEW-001 handoff](preview-001-handoff.md) for checks and operator scenarios.

## Feature Review and browser acceptance

```bash
make feature-review-up
make feature-review-status
make feature-review-bootstrap-owner LOGIN=owner
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

Stop removes containers/network but **preserves DB, media and dependencies**. Destruction is separate:

```bash
make feature-review-remove CONFIRM_REMOVE_REVIEW=florabase-feature-review
```

This explicitly deletes only that project's DB/media/dependency volumes and prints their names.
It cannot target DEV, Preview or production. It does not remove the Codex worktree. There is no
automatic DEV data reuse and no Review import helper. Synthetic data is supported; realistic cloning
requires a coordinated DB-and-media snapshot, a destination replacement confirmation and revision
compatibility checks. That complete clone is deferred. The old database-only Preview import now
refuses before reading or replacing data because it could create dangling media references.

## Development runtime identity and dependencies

DEV, Feature Review and QUALITY helpers explicitly supply the invoking POSIX user's UID/GID as
`LOCAL_UID:LOCAL_GID` to both frontend and backend. These values override stale shell or `.env`
defaults, so bind-mounted source remains writable by its owner in local and CI checkouts, including
linked worktrees. Run as the user who owns the selected source; root invocation refuses before
Compose runs. On platforms without host UID/GID APIs, explicitly export numeric `LOCAL_UID` and
`LOCAL_GID` for a non-root Docker identity that can write the bind mounts; missing/invalid values or
UID zero refuse. Production and Stable Preview retain their image-defined users.

The development image seeds `node_modules` with non-root ownership. A short-lived root initializer
mounts only the project's dependency and media volumes, fixes ownership to that same UID/GID and
exits. It never mounts or changes source files. The non-root frontend installs with `CI=true`,
`--frozen-lockfile` and `--prefer-offline` before executing pnpm. Corepack uses the image's read-only
pinned package cache; its temporary home supports non-default host UIDs.
QUALITY frontend commands also build and validate that shared image before initialization.
Fresh volumes, root-owned historical `.bin` files and changed lockfiles need no interactive TTY,
manual `chown`, world-writable permissions or populated host dependency directory.

## Stable Preview

```bash
make preview                 # Fetched origin/main, separate clean detached worktree
make preview-status
make preview-bootstrap-owner LOGIN=owner
make preview-stop
make preview-remove          # Clean preview worktree removed; DB/media preserved
```

The default path is `florabase-preview` beside the primary checkout, regardless of the invoking
feature worktree. `PREVIEW_PATH` selects another explicit path. Existing safe `REF=` support remains
available for deliberate stable tag/SHA comparisons; output identifies the selected ref and SHA.
Preview never consumes dirty feature source. Its frontend dependencies live inside immutable image
builds rather than a shared `node_modules` volume. Status identifies ref/SHA, source path, health,
DB current/code head, DB/media volumes and network. A newer or incompatible persistent preview DB
blocks migration; no automatic downgrade or destructive ref-switch recovery occurs.

## Integration and production

`make test-integration` creates a fresh uniquely named project per invocation, with PostgreSQL tmpfs
and fixed disposable credentials. An EXIT trap removes only that run's containers and resources.
No DEV or Review volumes are mounted. Feature migration-cycle testing uses another isolated project
and applies previous-main head → feature head → previous-main head → feature head when required.

`make up`, `build`, `migrate`, `down`, `backup`, and `restore` use the explicit `florabase-prod` project.
`compose.yaml` remains the production distribution topology: immutable non-root backend/frontend
images, same-origin nginx proxy, internal PostgreSQL/backend, health/readiness, persistent DB/media,
secure cookies and explicit HTTPS origin. Application startup never migrates. Back up coordinated
DB/media artifacts before `make migrate`; follow [backup and restore](backup-restore.md).
Production overrides belong in explicit deployment configuration, not the DEV/Review overlays.
Existing installations previously using the baseline's legacy `florabase` name must inventory and
migrate their paired data deliberately before adopting `florabase-prod`; this helper does not silently
attach production to DEV volumes. Public images/GHCR, release packaging and the end-user installer
remain release/distribution work, not part of this consolidation. The expected future end-user path
uses immutable published images with this same production topology and explicit upgrade policy.

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

Local verification has three layers:

- **Focused:** developer-selected existing test/check commands for iteration. These do not write a
  delivery receipt. Integration accepts explicit existing files, for example
  `./scripts/test-integration.sh backend/tests/integration/test_schedule.py`.
- **Affected:** `make feature-verify` (or `make verify-affected`) derives the safe plan automatically
  from the exact base and complete committed/index/dirty/untracked feature tree. It runs explicit
  affected suites, global product static checks, selected independent production builds and required
  migration cycling, then writes the exact completed-plan receipt. It can escalate to full.
- **Full:** `make verify-full` explicitly forces the complete original application and workflow gate.
  Full remains mandatory for infrastructure/security/foundational/dependency/unknown changes,
  releases and operator-requested exhaustive checks. Every selected FULL stage executes exhaustively;
  migration verification always performs the real PostgreSQL cycle even without a migration diff.
  There is no force-narrow override.

Preview the human plan with `make verification-plan`; use `make verification-plan FORMAT=json`
for the same machine-readable decision. `REF=<exact-base>` selects a diagnostic base; canonical
verification still fetches main and requires that exact base to be an ancestor. The versioned
[scripts/verification-impact.json](../scripts/verification-impact.json) contains explicit source/test
ownership, consumer regression boundaries and transitive relationships. Any unknown path escalates
full. Editing the map or verification infrastructure also escalates full. Migration revisions
conservatively escalate full. Every full plan requires the complete base → head → base → head cycle
on disposable PostgreSQL; no changed-file shortcut may suppress it. Affected plans may skip migration
cycling only when impact analysis proves it unnecessary. Generated contracts require an owning
classified production scope.

True docs-only plans run feature graph and complete whitespace checks with no Docker/product
suites or image builds. Product plans retain whole-repository Ruff, Prettier, ESLint, mypy, TypeScript
and generated API drift checks. Affected unit tests use explicit files and `--no-cov`; exhaustive
local/remote quality still enforces the existing whole-application coverage threshold. Frontend-only
changes build frontend; backend-only changes build backend; generated frontend contract changes
build both. The contexts are independent. Pure product changes skip workflow-specific suites.

Freeze source before the final gate. It invalidates old evidence at startup and rejects source edits
while stages run. Version 2 receipts cover file content, modes and symlinks, exact base/branch, mode,
impact-map version/digest, changed/affected scopes, escalation reasons, selected suites, completed
commands, static checks, migration/build decisions and results, and a UTC completion timestamp.
Migration evidence distinguishes the decision, cycle requirement, actual execution and result. Required
cycles verify the database revision after all four transitions and record successful disposable cleanup;
affected skips record `skipped_by_impact`. Older v2 receipts lacking this evidence are incompatible and
require a new canonical gate.
Delivery recomputes the policy and rejects incomplete, obsolete, mismatched or stale evidence. The
normal same reviewed tree can be committed without a ceremonial rerun. Transient staged/committed
changes masked by unstaged reverts are classified conservatively; freeze the index too when using
such unusual combinations, since removing transient impact invalidates the stored plan.

Protected GitHub `quality`, `integration`, and `build` still run **complete** suites and both builds.
`make ci` also remains exhaustive; remote CI is not sectorized. This CI-003 increment itself requires
Luna's independent **full** canonical gate before commit/delivery. See the
[handoff/evidence](ci-003-resource-impact-handoff.md).

### Quality and Docker resources

```bash
make quality-status       # Exact invoking worktree metadata/project and resource counts
make workflow-resources   # Known Florabase environments, legacy/unknown resources, image/cache policy
make quality-clean        # Explicit destructive retirement of ONLY this worktree's Quality state
```

Quality remains reusable during feature work; individual test/lint/type commands do not retire it.
Its project derives from the exact Git metadata path. New resources carry workflow lifecycle, owner
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
checkout on `main`, fast-forwards it through Git's normal index/worktree update, detaches the retained
feature worktree at its reviewed SHA and deletes only the proven merged feature branch. Codex owns
archiving that worktree. A dirty/staged primary or unexpected primary branch receives an actionable
refusal with feature source retained. Single-checkout manual finish still switches to updated `main`.

## Troubleshooting and acceptance evidence

- `DB CURRENT IS AHEAD OF OR INCOMPATIBLE WITH CODE`: use the checkout containing that revision or
  update primary `main` after delivery. Never force a downgrade to make the old code fit.
- DEV `belongs to <source>`: use `make dev-stop`, then `make dev-up` after primary is updated and
  DB/code compatible. No old source files or volume deletion are required.
- Review `belongs to <source>`: run stop/remove from its owning source before starting another Review.
- `GitHub CLI gh ... not found in PATH`: install `gh` on the operator host; authenticate with
  `gh auth login` before delivery. Verification does not require GitHub authentication.
- Primary staged changes during finish: preserve/resolve the operator changes deliberately; do not
  reset the index or check out the feature into primary.
- Migration or startup failure: use the environment's status command. Preserve its volumes while
  resolving code/revision compatibility; stop is not remove.

`make test-environment-workflow` models primary 0029 and a dirty untracked linked-worktree 0030,
configuration fallback, project boundaries, ahead-of-code refusal and destructive scope.
`make smoke-environment-workflow` requires an already linked worktree and fresh unique synthetic Review/Preview projects; existing operator Review is preserved.
It creates an untracked no-op migration, starts real Review, proves non-root/noninteractive fresh
bootstrap, repairs an intentionally root-owned `.bin` fixture through normal startup, checks
changed dependency/lockfile bootstrap and DB/media/dependency stop/restart persistence, builds a separate `origin/main` archive Preview and
validates production/integration topology. DEV container/mount/Git/revision snapshots are compared
before and after. Only fresh resources bearing exact registered-run labels are retired and verified; no operator data is deleted
and no additional real Git worktree is created.

`make smoke-dev-recovery` uses a unique disposable DEV fixture with a vanished old source. It proves
legacy tmpfs and durable media, DB rows and dependency files survive stop and primary recreation,
repeated stop is safe, and ahead-of-code state refuses application startup/upgrade without downgrade.
Before/after snapshots verify operator DEV, Review, Preview, production and primary Git are unchanged.
