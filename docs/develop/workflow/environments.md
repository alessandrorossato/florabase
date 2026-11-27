# Development, Preview and production environments

> Summary: Configuration resolution, persistent DEV and Golden DEV, Sourcing Preview, Stable Preview, and production boundaries.

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

These commands select the primary checkout even when invoked in a linked feature worktree. Status
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

### Persistent Golden DEV

DEV can hold the reviewed COMPREHENSIVE synthetic collection. Start, stop, builds and forward
migrations preserve the PostgreSQL and attachment volumes. Golden initialization and replacement
are explicit operator actions. See [Golden DEV operations](../dev-golden.md) for target checks,
verification, backup locations, and interruption recovery.

See [DEV reference indexes](../dev-references.md) for the pinned WFO and WCVP cache and
the explicit setup and verification commands.

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
**Sourcing Preview** (`15175`) is a per-worktree visual-review environment for the Sourcing slice; it
is additive and never replaces Feature Review, UAT or Stable Preview.

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

## Sourcing Preview

A persistent, per-worktree preview for the Sourcing slice (Suppliers today, Orders next). It reuses
the Review runtime and fixture with an independent project, network, database (`florabase_sourcing`),
media volume and dependency volume, and publishes only `127.0.0.1:15175`. It can therefore run at the
same time as Feature Review/UAT (`15174`) and Stable Preview (`15173`) without sharing or stopping
them.

```bash
make sourcing-preview-up                      # Build if needed, migrate, wait for health
make sourcing-preview-bootstrap-owner LOGIN=owner
make sourcing-preview-seed                    # Synthetic Suppliers/Orders/linked SeedLots
make sourcing-preview-status
make sourcing-preview-stop                    # Preserve DB, media and dependencies
make sourcing-preview-remove CONFIRM_REMOVE_SOURCING=florabase-sourcing-preview
```

`up` builds only when the Sourcing images are missing (pass `--rebuild` via
`python3 scripts/sourcing_preview.py up --rebuild` to force one); the shared BuildKit cache is reused
otherwise. `bootstrap-owner` reads one password from the terminal, `--password-stdin`,
`--password-file` or `--password`. Seeding requires an already-bootstrapped single enabled owner and
an empty baseline; the fixture refuses any other source, project, database or marker and never
touches DEV, Feature Review, UAT, Stable Preview or production. Owned resources carry
`io.florabase.role=sourcing`, `io.florabase.source` and `io.florabase.sha` labels and the standard
`io.florabase.source` volume labels, so `remove` deletes only
`florabase-sourcing-preview_postgres_data`, `..._attachment_data`, `..._frontend_node_modules` and
its own containers/network.

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
`make golden-dataset-check` runs the [TEST-DATA-001 golden dataset](../../archive/TEST-DATA-001/test-data-001-design.md) inside that
same disposable workflow; its copies exist only beside disposable test PostgreSQL. The default
integration suite skips that module; the verification gate adds the `golden-dataset` stage only when
changed paths intersect `golden_prefixes` in `scripts/verification-impact.json` or cannot be
classified (fail-closed), while `main` push CI always runs it.
`make golden-dataset-comprehensive-check` runs the [TEST-DATA-002 profile](../../archive/TEST-DATA-002/test-data-002-design.md) the same
way. It is manual: the default integration suite skips that module, so CI and the canonical gate do not run it.

`make up`, `build`, `migrate`, `down`, `backup`, and `restore` use the explicit `florabase-prod` project.
The `prod` stack (DEV + production override) is the source-build production topology: immutable non-root backend/frontend
images, same-origin nginx proxy, internal PostgreSQL/backend, health/readiness, persistent DB/media,
secure cookies and explicit HTTPS origin. Application startup never migrates. For source-build upgrades, follow the
[maintenance procedure](../../operate/deployment.md#safe-upgrade) to keep writers stopped from backup through migration.
Production overrides belong in explicit deployment configuration, not the DEV/Review overlays.
Existing installations previously using the baseline's legacy `florabase` name must inventory and
migrate their paired data deliberately before adopting `florabase-prod`; this helper does not silently
attach production to DEV volumes. Published releases offer one self-initializing
[`compose.yaml`](../../operate/installation.md) with its own storage layout (ADR 0008).
