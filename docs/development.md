# Development

The [development workflow](development-workflow.md) is canonical for DEV, existing Codex worktrees,
Feature Review, Stable Preview, integration/CI, production, review order and verification receipts.

For a new primary checkout, run `make setup`, `make dev-up`, then `make dev-upgrade` and
`make dev-bootstrap-owner LOGIN=owner`. DEV always selects the primary checkout. Use `make feature-init`
and `make feature-review-up` inside a Codex-managed feature worktree to inspect dirty source at
`http://localhost:15174`; stable `origin/main` remains independently available through `make preview`
at `http://localhost:15173`. No copied or symlinked `.env` is required.

## Resource measurements

The [PERF-001 protocol/report](performance/PERF-001.md) documents the guarded `florabase-perf`
project, production runtime builds, deterministic disposable dataset, API/SQL/browser collectors,
comparison evidence and serial reproduction commands. It reuses the production topology with tmpfs
PostgreSQL/media and a single loopback frontend port; it never imports operator data or loads the
normal `.env`. Benchmark independently of quality/build jobs, and retain baseline evidence before
changing code. Normal CI has deterministic query/loading regressions, not CPU/RAM/latency thresholds.

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
`florabase-integration-<run-id>` Compose project, verifies disposable-database markers, migrates to head, and
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
make feature-review-up
make migration MESSAGE="describe schema change"
make feature-review-up
```

Inspect generated SQL, constraints, data safety, and downgrade behavior. Add PostgreSQL migration and
invariant coverage proportional to risk. Never use application startup or `create_all()` to mutate
the schema, and never rewrite a migration that may have been deployed.

The current Alembic head is discovered from the migration chain rather than duplicated here; use
`make feature-review-status` when needed.

To upgrade the existing development database explicitly, use `make dev-upgrade`. It uses
`compose.yaml` plus `compose.dev.yaml`, displays the current revision, applies `alembic upgrade head`,
and displays the resulting revision without deleting volumes. Back up meaningful production data
before production upgrades; this development helper is not a production deployment command.

## Git and backlog workflow

Read `AGENTS.md`, `docs/progress.md`, and `docs/features.json`. Choose a scoped increment and use
`make feature-init` in an existing Codex worktree or `make feature-start BRANCH=feat/example` for
manual development. Follow the [canonical review profiles and verification timing](development-workflow.md#review-profiles-and-verification-timing).
Update tests/documentation and review the final tree before the canonical `make feature-verify`.
Commit only when authorized; the operator runs protected delivery separately.

`make feature-deliver` checks the exact reviewed tree, authenticated GitHub CLI, repository identity,
current-SHA protected checks and exact PR identity. It pushes normally, reuses/creates one PR and waits
for protected squash auto-merge. Reruns can recognize a proven completed delivery without another push.
After merge, `make feature-finish` updates clean primary `main` and retains a Codex feature worktree
as detached; it refuses staged/dirty primary state. If delivery reports a migration, run
`make dev-upgrade` only after finish. See [CONTRIBUTING.md](../CONTRIBUTING.md).
