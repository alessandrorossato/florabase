# Development

## Container workflow

Docker Compose is the canonical toolchain. Install Docker Engine with Compose v2, GNU Make, Git, and
`curl`, then run:

```bash
make setup
make dev
```

The development override mounts source, enables backend and frontend hot reload, and publishes only
loopback ports: Vite at `http://localhost:5173`, FastAPI at `http://localhost:8000`, and PostgreSQL at
`127.0.0.1:5432`. Use the exact `localhost` Vite URL so Origin and development-cookie checks match.
Run `make migrate`, bootstrap a local owner as documented in [deployment.md](deployment.md), and do
not use valuable data for development tests.

## Isolated stable preview

`make dev` runs the current worktree with hot reload, the normal `florabase` Compose project,
development ports, and the persistent development database. For stable manual browser QA while that
worktree remains on a feature branch or has local changes, use:

```bash
make preview
```

The preview helper fetches `origin`, resolves `origin/main` to an exact commit, and creates or safely
updates a detached Git worktree at `../florabase-preview`. It then builds production runtime targets
from that preview worktree, explicitly starts the `florabase-preview` Compose project, upgrades only
its database to the selected code's Alembic head, waits for service health and host reachability, and
prints the resolved ref, SHA, and canonical URL: `http://localhost:15173`.

Select another reviewed commit or ref explicitly when needed:

```bash
make preview REF=<commit-or-ref>
```

The helper never checks out, resets, stashes, cleans, rebases, or otherwise changes the primary
worktree, and does not require it to remain idle while preview preparation runs. An existing preview
worktree must be clean before its detached revision can move. The
Compose project directory and build contexts are validated against the preview worktree, so preview
images cannot accidentally be built from the active feature worktree. If that linked worktree was
safely moved on disk, startup uses Git's targeted worktree-repair primitive and then verifies the
exact registered path; malformed or ambiguous worktree metadata is rejected.

Preview uses production/static backend and frontend image targets without development bind mounts.
Only `127.0.0.1:15173` is published; FastAPI and PostgreSQL remain internal. The backend retains the
unchanged production security validation, while this loopback-only environment explicitly uses
`FLORABASE_ENVIRONMENT=development`, canonical origin `http://localhost:15173`, and
`loopback-development` cookies. Its fixed internal-only database credentials are local non-secret
defaults; no primary `.env` is copied into the preview worktree.

The `florabase-preview_postgres_data` volume is distinct from the normal development and disposable
integration databases. It survives container recreation, `make preview-stop`, and
`make preview-remove`. On an empty database, `make preview` applies migrations but does not invent an
owner password. When startup reports that no owner exists, create one through the existing secure,
interactive bootstrap implementation:

```bash
make preview-bootstrap-owner LOGIN=owner
```

To explicitly replace preview data with a snapshot of the currently running persistent development
database, use both target guards:

```bash
make preview-import-dev CONFIRM_REPLACE_PREVIEW=yes CONFIRM_DATABASE=florabase_preview
```

The command hard-codes the normal `florabase` development project as source and
`florabase-preview` as target, creates and validates a temporary custom-format dump, preflights its
Alembic revision against the selected preview code, coordinates preview application containers,
restores only the preview database, upgrades it forward when necessary, and removes the temporary
dump. It never runs during ordinary preview startup and never modifies development data. Treat all
database copies as sensitive even though the temporary artifact is deleted.

Preview migration handling is forward-only. If the persistent preview database—or the development
snapshot selected for import—has a revision that the selected code cannot safely upgrade, the helper
fails without downgrading or deleting the preview volume. Choose a compatible ref; for an import,
the compatibility check happens before preview data is replaced.

Lifecycle and troubleshooting commands are:

```bash
make preview-status
make preview-stop
make preview-remove
```

Status reports the worktree path and exact SHA, clean/dirty state, known requested ref, Compose
project, container state/health text, URL, persistent volume presence, and the Alembic revision when
the preview database is running. Stop removes preview containers but preserves its worktree and
database. Remove first performs that same non-volume stop, then removes only a clean preview Git
worktree; it refuses local preview changes and still preserves the database volume.

For logs, use the exact isolated project and both configuration files (paths shown here assume the
default adjacent worktree):

```bash
docker compose --project-name florabase-preview \
  --project-directory ../florabase-preview \
  --file ../florabase-preview/compose.yaml \
  --file compose.preview.yaml logs --tail=100
```

The persistent preview database is not a test fixture. `make test-integration` remains a separate
tmpfs-backed `florabase-integration` project, and feature verification never targets preview data.

## Checks

Use the narrowest relevant command while working:

```bash
make format
make format-check
make lint
make typecheck
make test-backend
make test-frontend
make test-integration
make api-check
make build
make check
make ci
make test-feature-workflow
make feature-verify
```

`make format` modifies Python and frontend-supported text; the other check commands are intended to
be non-destructive. `make test` combines backend unit and frontend tests. `make check` combines
format checks, lint, strict typing, unit/component tests, and generated API drift. Run
`make test-integration` separately for PostgreSQL-backed behavior; it creates the isolated
`florabase-integration` Compose project, verifies disposable-database markers, migrates to head, and
removes its tmpfs-backed database even on failure.

Run production image builds when Dockerfiles, dependencies, build configuration, or release-facing
code changes. Run migration and integration checks for schema or persistence changes.

GitHub runs three stable checks for pull requests into `main`: `quality` runs `make check`,
`integration` exercises the same disposable PostgreSQL suite as `make test-integration`, and `build`
builds the production backend and frontend images. `make ci` remains the direct local equivalent of
those three jobs. `make feature-verify` is the canonical feature-level final gate: it runs the
workflow-helper and feature-graph checks, the same quality, integration, and build stages once,
`git diff --check`, and records a local receipt for the verified working tree. It does not require a
clean tree and never modifies application files. When the branch adds Alembic revisions, it also runs
the previous-main-head → feature-head → previous-main-head → feature-head cycle in a uniquely named,
tmpfs-backed disposable Compose project; it never touches the development database or its volume.

## Optional host tools

Containers are preferred. For focused host work, the declared ranges are Python 3.12–3.14 and Node
24 with pnpm 11:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements-dev.lock
cd frontend
corepack enable
pnpm install --frozen-lockfile
```

Run backend tools from `backend/` and frontend tools from `frontend/`. Exact dependencies are in the
committed lockfiles. Change direct pins deliberately, review release notes, refresh locks with
`make dependency-update`, and run the full relevant suite.

## API contracts

FastAPI is authoritative. `backend/openapi.json` is generated from the application, and
`frontend/src/api/schema.d.ts` is generated from that artifact. After an API contract change:

```bash
make api-generate
make api-check
```

Commit both generated files. Do not hand-edit generated TypeScript declarations or accept drift.

## Database migrations

Alembic is the only schema-management path. Start PostgreSQL, then create and apply a revision:

```bash
make migration MESSAGE="describe schema change"
make migrate
```

Inspect generated SQL, constraints, data safety, and downgrade behavior. Add PostgreSQL migration and
invariant coverage proportional to risk. Never use application startup or `create_all()` to mutate
the schema, and never rewrite a migration that may have been deployed.

The current Alembic head is discovered from the migration chain rather than duplicated here; use
`docker compose run --rm backend alembic heads` when needed.

To upgrade the existing development database explicitly, use `make dev-upgrade`. It uses
`compose.yaml` plus `compose.dev.yaml`, displays the current revision, applies `alembic upgrade head`,
and displays the resulting revision without deleting volumes. Back up meaningful production data
before production upgrades; this development helper is not a production deployment command.

## Git and backlog workflow

Read `AGENTS.md`, `docs/progress.md`, and `docs/features.json`, decide the backlog increment, then use:

```bash
make feature-start BRANCH=feat/example
```

The helper requires a clean tree and an `origin`, fetches and prunes, fast-forwards local `main`, and
refuses unsafe or existing branches. It does not infer the next feature. Keep one increment per
branch and document explicit exclusions. Independently review the implementation and fixes, then run
`make feature-verify`. Inspect the final diff, update progress honestly, stage only intentional files,
and create the reviewed local commit. The verification receipt proves only that the final committed
tree matches the locally verified tree; it is a machine-local guard, not a substitute for review.

The operator then runs:

```bash
make feature-deliver
```

This requires a clean, committed non-`main` feature branch and authenticated GitHub CLI access to the
Florabase repository. It never rebases, merges, stashes, amends, force-pushes, or changes repository
settings. It pushes normally, reuses an existing open PR for the branch or creates one deterministic
PR, enables exact-SHA squash auto-merge, and waits with bounded polling for current-SHA `quality`,
`integration`, and `build` checks. Failed, cancelled, skipped, or timed-out checks leave the PR open
and end with `DELIVERY_BLOCKED`; fix, recommit, re-verify, and rerun delivery on the same PR. On
success it confirms the merge and remote branch deletion. GitHub should remove the merged remote head
branch. From the clean local feature branch, finish separately with:

```bash
make feature-finish
```

This helper requires authenticated GitHub CLI evidence that the exact branch head was merged into
`main`, verifies that merge on `origin/main`, fast-forwards local `main`, and only then removes the
unchanged local branch. It stops without deletion when merge state cannot be established.

If `make feature-deliver` reports a database migration, run `make dev-upgrade` only after
`make feature-finish`; delivery never upgrades any database.

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the concise contributor checklist.
