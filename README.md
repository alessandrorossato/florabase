# Florabase

Florabase is a self-hosted botanical collection manager. This repository currently contains only its production-oriented foundation: PostgreSQL, a typed FastAPI REST API, a React frontend, explicit migrations, quality tooling, and operational documentation. Botanical features are intentionally not implemented yet.

## Prerequisites

- Docker Engine 29 or newer with Docker Compose v2 (`docker compose`)
- GNU Make 4 or newer
- `curl` for `make health`
- Linux amd64 or arm64

Host Python and Node are optional because normal commands run in containers.

## Initial setup

```bash
make setup
```

Review `.env`. Its checked-in example values are only for localhost development. Set a unique URL-safe database password and keep `POSTGRES_PASSWORD` and the password inside `FLORABASE_DATABASE_URL` identical. Never deploy the example credentials.

For production, also set `FLORABASE_CANONICAL_ORIGIN` to the exact public HTTPS origin and keep
`FLORABASE_CORS_ORIGINS=[]` for the same-origin browser/API architecture.

## Start, inspect, and stop

Production-oriented local stack:

```bash
make up
make migrate
make health
make logs
make down
```

The UI is available at <http://127.0.0.1:8080>. PostgreSQL and the backend are not published by the base stack.

After the first migration of a new installation, create the one local owner interactively:

```bash
docker compose run --rm backend python -m florabase.auth.bootstrap owner
```

The password is prompted securely and never accepted as a command argument. See
[security.md](docs/security.md) for the stdin automation option and authentication policy.

Hot-reloading development stack:

```bash
make dev
```

This publishes Vite at <http://localhost:5173>, FastAPI at <http://localhost:8000>, and PostgreSQL
at `127.0.0.1:5432`. Use the `localhost` Vite URL because it is the explicit development canonical
origin. Development behavior comes from `compose.dev.yaml`; production never enables reload,
debug mode, or the loopback cookie policy.

## Development commands

```bash
make build
make test
make test-integration
make lint
make format
make format-check
make typecheck
make check
```

`make check` is the main non-destructive suite. It checks formatting, lint, Python/TypeScript typing, backend/frontend tests, and generated API drift. See [development.md](docs/development.md).

## Database migrations

Apply reviewed migrations explicitly; application startup never migrates automatically:

```bash
make migrate
make migration MESSAGE="describe schema change"
```

Inspect every generated migration and add downgrade behavior where practical before applying it.

## API contract generation

```bash
make api-generate
make api-check
```

`backend/openapi.json` is generated from FastAPI. `frontend/src/api/schema.d.ts` is generated from it. Both are committed so frontend builds do not require a running backend.

## Backup and restore

```bash
make backup
make restore FILE=backups/florabase-YYYYMMDDTHHMMSSZ.dump CONFIRM_REPLACE=yes CONFIRM_DATABASE=florabase
```

Restore replaces the target database. Read [backup-restore.md](docs/backup-restore.md) before using it. Database dumps do not include future uploaded attachments, `.env`, or reverse-proxy secrets.

## Production deployment

The base Compose stack is production-oriented but assumes an operator-managed HTTPS reverse
proxy. At minimum, replace example secrets, set the exact HTTPS canonical origin, leave CORS
disabled, set `APP_BIND_ADDRESS` deliberately, run a backup, build reviewed images, apply
migrations explicitly, bootstrap the first owner on new installations, start the stack, and run
`make health`. See [deployment.md](docs/deployment.md) and [security.md](docs/security.md).

## Documentation

- [Architecture](docs/architecture.md)
- [Preliminary domain model](docs/domain-model.md)
- [Product roadmap](docs/product-roadmap.md)
- [Development](docs/development.md)
- [Deployment](docs/deployment.md)
- [Backup and restore](docs/backup-restore.md)
- [Security](docs/security.md)
- [Backlog](docs/features.json)
- [Progress](docs/progress.md)
