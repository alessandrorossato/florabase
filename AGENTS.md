# Agent guide

Florabase is a self-hosted modular monolith: React/TypeScript frontend, FastAPI/Python backend, and PostgreSQL, deployed with Docker Compose. The repository is deliberately at foundation stage. Implement one concrete, small capability at a time; do not pre-build the full botanical model.

## Start every task

1. Read this file completely.
2. Run `git status` and preserve unrelated changes.
3. Inspect recent history with `git log --oneline --decorate -10`.
4. Read `docs/progress.md`.
5. Inspect `docs/features.json` and select one well-scoped item when the user has not specified one.
6. Inspect relevant existing code and documentation before designing a parallel mechanism.
7. Run appropriate baseline checks before risky changes; normally `make check`, or the narrowest meaningful subset when the full stack is unavailable.

Then implement the smallest coherent change, test it, update relevant docs/backlog/progress, inspect `git diff` and `git status`, and leave the repository runnable.

## Important directories

- `backend/src/florabase/`: FastAPI application, central configuration, database infrastructure, and future capability modules.
- `backend/alembic/`: the only database schema-change path.
- `backend/tests/`: backend tests; PostgreSQL-dependent tests must be clearly marked and isolated.
- `frontend/src/`: accessible React UI and generated API declarations.
- `docs/`: architecture, operations, domain discovery, backlog, progress, and ADRs.
- `scripts/`: guarded operational and verification scripts.
- `compose.yaml`: production-oriented baseline; `compose.dev.yaml`: development-only override.

## Workflow and conventions

- Use Python type hints everywhere and modern SQLAlchemy 2.x APIs. Ruff owns Python formatting/import ordering; mypy runs in strict mode.
- TypeScript must remain strict. ESLint and Prettier own frontend lint/format behavior. Use semantic HTML and test loading, success, and failure states.
- Backend APIs live under `/api/v1`. Pydantic models validate inputs and responses. Backend OpenAPI is authoritative; run `make api-generate` after contract changes and commit both generated artifacts.
- Keep business rules near the capability that owns them. Add service/repository abstractions only when a current use case needs a boundary.
- Every database schema change requires an Alembic migration. Never use `create_all()` as schema management. Review generated SQL, constraints, data migration safety, and downgrade behavior.
- Timestamps are timezone-aware at boundaries and stored in UTC. Future identifiers follow ADR 0004 unless superseded by another accepted ADR.
- Tests must cover success, validation, failure behavior, and database invariants proportional to risk. Run the narrow test during development and the full relevant suite before finishing.

## Non-negotiable safeguards

- Never modify or weaken tests merely to make failures disappear.
- Never delete or silently weaken requirements without explicit user instruction.
- Never bypass type checking to hide design errors or add blanket suppressions.
- Never suppress exceptions without a narrow, documented justification; do not silently catch failures.
- Inspect existing implementations before creating parallel abstractions.
- Do not introduce infrastructure without a concrete requirement.
- All database schema modifications require migrations, and application startup must not apply them implicitly.
- Never commit secrets, `.env`, backups, uploads, dependency caches, or virtual environments.
- Production CORS must be explicit and must never default to `*`.
- Do not publish PostgreSQL or the backend directly in production-oriented configuration.
- Containers must remain multi-architecture where upstream images allow, run non-root where practical, preserve SIGTERM behavior, and write durable state only to documented volumes.
- Never claim verification that was not actually performed.
- Leave the repository in a clean, runnable state and update documentation when behavior or architecture changes.

## Backlog and progress

`docs/features.json` is machine-readable. Preserve its schema and allowed statuses: `planned`, `in_progress`, `implemented`, `verified`. `verified` requires executing every listed acceptance criterion. Priority means P0 blocks safe foundational work, P1 is the next core increment, P2 is valuable after the core path, and P3 is optional/later.

After meaningful work, append a concise entry to `docs/progress.md` with date, feature IDs, summary, exact checks, decisions, and unresolved issues. Update a feature status only when evidence supports it. Do not turn progress into a diary.

## Completion checklist

1. Run relevant formatting, lint, typing, tests, build, migration, and health checks.
2. Update generated OpenAPI/types after API changes.
3. Update docs, ADRs only for consequential decisions, backlog status, and progress.
4. Inspect `git diff` for secrets, debug code, accidental artifacts, duplication, and false completion claims.
5. Run `git status`; report any environmental verification limits exactly.
