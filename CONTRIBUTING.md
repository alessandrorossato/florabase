# Contributing to Florabase

Florabase is developed as small, dependency-aware increments. Start with the
[development guide](docs/development.md), then choose or discuss one item from
[`docs/features.json`](docs/features.json).

## Workflow

1. Choose the roadmap increment, then run `make feature-start BRANCH=feat/event-001`. The helper
   accepts focused `feat/`, `fix/`, `docs/`, and `ci/` names and creates the branch only from a clean,
   fast-forwarded `main`; it never chooses product scope for you.
2. Keep the change within one backlog increment and state what is intentionally out of scope.
3. Run focused checks while working. Independently review the implementation and ordinary fixes, then
   run `make feature-verify` as the one canonical final local gate. It covers the complete local
   pull-request equivalent without duplicating expensive suites.
4. Inspect the final diff, update tests and documentation, and create a reviewed local commit. Only
   mark a feature `verified` when every listed acceptance criterion was actually exercised.
5. The operator runs `make feature-deliver`. It performs a normal push, reuses or creates one pull
   request into `main`, enables squash auto-merge with the exact delivery SHA, and waits for the
   required `quality`, `integration`, and `build` checks. It never bypasses protections. After it
   reports success, run `make feature-finish` from the clean local feature branch. If delivery reports
   a migration, then run `make dev-upgrade` after finishing the branch.

Database changes must use a new reviewed Alembic migration; never rewrite a deployed revision.
FastAPI owns the OpenAPI contract. Run `make api-generate` after API changes and commit both
`backend/openapi.json` and `frontend/src/api/schema.d.ts`; `make api-check` must pass.

Pull requests should identify the feature ID, summarize scope and exclusions, list exact checks,
call out migrations and generated-contract changes, and include required documentation updates.
Review the diff for secrets, generated junk, and unrelated files before pushing. Squash merge is the
normal policy: one backlog increment becomes one pull request and one coherent commit on `main`,
while the development branch may contain multiple commits.
