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
builds the production backend and frontend images. `make ci` runs all three gates locally in
sequence; it is deliberately comprehensive, while focused commands remain the normal development
loop.

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
branch and document explicit exclusions. Before review, run focused tests and `make check` (plus the
relevant integration/build gates), inspect `git diff` and `git diff --check`, update progress
honestly, and stage only intentional files.

Push normally and open a pull request into `main`. Required GitHub checks are `quality`,
`integration`, and `build`; the normal merge method is squash auto-merge, never bypassing a pending
or failed check. GitHub should remove the merged remote head branch. From the clean local feature
branch, finish with:

```bash
make feature-finish
```

This helper requires authenticated GitHub CLI evidence that the exact branch head was merged into
`main`, verifies that merge on `origin/main`, fast-forwards local `main`, and only then removes the
unchanged local branch. It stops without deletion when merge state cannot be established.

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the concise contributor checklist.
