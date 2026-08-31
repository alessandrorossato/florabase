# Development

## Reproducible container workflow

Run `make setup` once, inspect `.env`, then use `make dev` for hot reload. The development override mounts source into development image targets and binds every published dependency to loopback. It replaces the production frontend port and healthcheck with Vite on port 5173. The base stack remains the source of service topology and production defaults.

Development explicitly sets `http://localhost:5173` as the canonical origin and uses the
loopback-only `florabase-session-dev` cookie without `Secure`. Open Vite through that exact URL for
login-origin checks. Production cannot select this cookie mode.

After migrations, create the local owner using the bootstrap command in `docs/security.md`, then
open `http://localhost:5173`. The browser restores an existing HttpOnly-cookie session after a
reload and obtains a fresh in-memory CSRF token automatically; it does not ask for the password
again while the backend session remains valid. Sign out revokes the backend session and returns to
the owner login form.

Normal checks use containers:

```bash
make format-check
make lint
make typecheck
make test
make test-integration
make api-check
make check
```

`make format` is the only command above that intentionally modifies source. Do not run destructive database tests against a valuable database.

`make test` keeps the normal backend unit tests and frontend tests fast by excluding the
`integration` marker. `make test-integration` creates the separate `florabase-integration`
Compose project, waits for PostgreSQL 18, checks two explicit disposable-test configuration
markers, applies the real Alembic chain, runs integration tests, and removes its containers and
tmpfs-backed database even when tests fail. Tests share one PostgreSQL instance for the run and
use a rolled-back transaction per test. The integration database has no published port and does
not reuse the normal `florabase` Compose project or its `postgres_data` volume.

## Optional host workflow

Host tools are not required. If used, install Python 3.12–3.14 and Node 24, then:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements-dev.lock
cd frontend && corepack enable && pnpm install --frozen-lockfile
```

Run backend commands from `backend/` and frontend commands from `frontend/`. Lockfiles contain exact direct and transitive versions. Review release notes and run the full suite when updating them. `make dependency-update` refreshes locks after direct pins in `pyproject.toml` or `package.json` have been deliberately reviewed.

## Database changes

Start PostgreSQL, create a revision with `make migration MESSAGE="..."`, inspect it, and apply with `make migrate`. Autogeneration is assistance, not proof of correctness. Never edit an already-deployed migration to disguise a new change.

## Generated API contract

FastAPI generates `backend/openapi.json`; `openapi-typescript` generates `frontend/src/api/schema.d.ts`. Generated files are committed. `make api-check` regenerates temporary comparisons and restores the working files before returning.
