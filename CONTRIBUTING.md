# Contributing to Florabase

Florabase is developed as small, dependency-aware increments. Start with the
[development guide](docs/development.md), then choose or discuss one item from
[`docs/features.json`](docs/features.json).

## Workflow

1. Branch from the current verified `main`. Use a focused name such as `feat/event-001`,
   `fix/<topic>`, or `docs/<topic>`.
2. Keep the change within one backlog increment and state what is intentionally out of scope.
3. Run focused checks while working and `make check` before requesting review. Run
   `make test-integration` when persistence, API/database behavior, or migrations are affected.
4. Update tests and documentation with behavior. Only mark a feature `verified` when every listed
   acceptance criterion was actually exercised.
5. Use concise imperative commits, for example `docs: clarify deployment workflow`.

Database changes must use a new reviewed Alembic migration; never rewrite a deployed revision.
FastAPI owns the OpenAPI contract. Run `make api-generate` after API changes and commit both
`backend/openapi.json` and `frontend/src/api/schema.d.ts`; `make api-check` must pass.

Pull requests should identify the feature ID, summarize scope and exclusions, list exact checks,
call out migrations and generated-contract changes, and include required documentation updates.
Review the diff for secrets, generated junk, and unrelated files before pushing.
