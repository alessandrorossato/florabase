# Agent guide

Florabase is a self-hosted modular monolith: React/TypeScript frontend, FastAPI/Python backend, and
PostgreSQL, deployed with Docker Compose. Work on one concrete backlog increment per feature branch;
do not pre-build later capabilities.

## Start every task

1. Read this file completely.
2. Run `git status --short --branch`; preserve unrelated work and never expose secrets.
3. Inspect `git log --oneline --decorate -10` and branch from the current verified `main`.
4. Read `docs/progress.md` and inspect `docs/features.json`.
5. Inspect the relevant implementation and documentation before designing another mechanism.
6. Run the narrowest meaningful baseline checks; use `make check` before risky or broad changes when
   the full stack is available.

Choose the roadmap increment before creating a branch. Use `make feature-start
BRANCH=feat/<feature-id>` (or a focused `fix/`, `docs/`, or `ci/` name) to create it from clean,
fast-forwarded `main`. Implement the smallest coherent change, run focused checks while developing,
then complete the relevant full verification before marking a feature `verified`.

## Repository boundaries

- `backend/src/florabase/`: FastAPI application, configuration, database infrastructure, and domain
  capabilities.
- `backend/alembic/`: the only database schema-change path; application startup never migrates.
- `backend/tests/`: unit tests and clearly isolated PostgreSQL integration tests.
- `frontend/src/`: accessible React UI and generated API declarations.
- `docs/`: architecture, operations, domain model, backlog, progress, and ADRs.
- `scripts/`: guarded operational and verification scripts.
- `compose.yaml`: production-oriented baseline; `compose.dev.yaml`: development override.

## Engineering conventions

- Use Python type hints and modern SQLAlchemy 2.x APIs. Ruff owns formatting/imports; mypy is strict.
- Keep TypeScript strict. ESLint and Prettier own lint and format. Use semantic HTML and cover
  loading, success, validation, and failure states.
- APIs live under `/api/v1`. Pydantic validates inputs and responses. Backend OpenAPI is
  authoritative; after contract changes run `make api-generate` and commit both generated artifacts.
  `make api-check` must report no drift.
- Keep business rules with their owning capability. Add abstractions or infrastructure only for a
  current requirement.
- Every schema change needs a reviewed Alembic migration with constraints, data safety, and downgrade
  behavior considered. Never use `create_all()` for schema management.
- Store timezone-aware boundary timestamps in UTC. New identifiers follow ADR 0004 unless superseded.
- Never weaken tests, type checking, validation, or error handling to hide failures.
- Never commit `.env`, secrets, backups, uploads, caches, build output, or virtual environments.
- Never use volume deletion such as `docker compose down --volumes` as a routine workflow.
- Production CORS must be explicit and never wildcard; do not directly publish PostgreSQL or the
  backend from production-oriented configuration.

## Backlog, documentation, and delivery

`docs/features.json` is the machine-readable source of truth. Preserve its schema and statuses:
`planned`, `in_progress`, `implemented`, and `verified`. Verification requires evidence for every
acceptance criterion, not merely satisfied dependencies.

After meaningful work, update affected documentation and append or consolidate a concise
`docs/progress.md` milestone with the exact checks and unresolved issues. Review the implementation
and diff independently, fix ordinary defects, then use `make feature-verify` as the canonical final
local gate; do not manually repeat its covered verification stages. Review the resulting final diff,
stage only intentional files, inspect the staged diff, and create the reviewed local commit. When a
task boundary is `READY_FOR_DELIVERY`, do not push or create a PR: the operator runs deterministic
`make feature-deliver`. It pushes normally, reuses or creates the PR, and waits for protected squash
auto-merge without bypassing checks. Never force-push, rewrite shared history, manually force a
merge, or commit feature work directly to `main`. After delivery reports a merged PR, use `make
feature-finish` for conservative local cleanup, then use `make dev-upgrade` only when delivery
reported a migration.

Before finishing, run relevant formatting, lint, typing, tests, integration, API drift, migration,
build, and health checks proportional to the change. Report environmental limits exactly and never
claim checks that did not run.
