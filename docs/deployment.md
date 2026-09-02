# Deployment and upgrades

This is the canonical self-hosting guide. Florabase is pre-release software: review changes and keep
a tested backup before every upgrade.

## Prerequisites and deployment model

Install Docker Engine with Docker Compose v2, GNU Make, and `curl`. Clone the repository on a host
where an operator-managed HTTPS reverse proxy can forward to the frontend port.

`compose.yaml` builds the production targets. PostgreSQL and FastAPI remain on the internal Compose
network; only the nginx frontend proxy publishes `${APP_BIND_ADDRESS}:${APP_PORT}`. The frontend
serves the React application and forwards `/api/` to FastAPI.

## Configure the installation

```bash
git clone https://github.com/alessandrorossato/florabase.git
cd florabase
make setup
```

`make setup` creates `.env` from `.env.example` only when `.env` does not exist. The file is ignored
by Git. Replace the example database password in both `POSTGRES_PASSWORD` and
`FLORABASE_DATABASE_URL`; use a URL-safe password or percent-encode it in the URL. Do not commit the
file.

Set `FLORABASE_CANONICAL_ORIGIN` to the browser origin exactly:

```text
https://florabase.example.com
```

An origin contains only scheme and authority (host plus optional port), with no path, query, or
fragment. Production requires HTTPS. It rejects a missing or HTTP origin, insecure cookies, wildcard
CORS, and every non-empty CORS list because the current browser/API design is same-origin. The
development override instead fixes the canonical origin at `http://localhost:5173` and uses a
loopback-only development cookie; those settings cannot be used in production.

Keep `APP_BIND_ADDRESS=127.0.0.1` when the HTTPS proxy is on the same host. If the proxy is elsewhere,
expose the frontend deliberately and protect the network path. Do not publish PostgreSQL or FastAPI.

## First installation

Build the images, start PostgreSQL, apply all reviewed migrations, and start the application:

```bash
make build
docker compose up --detach db
make migrate
make up
```

Application startup never runs migrations. Create the first and only initial owner after migration:

```bash
docker compose run --rm backend python -m florabase.auth.bootstrap owner
```

The password is prompted without echo. Automation may use `--password-stdin` with a secret provider
that writes one line to standard input. Never put the password in a command argument, Compose file,
image layer, or source-controlled environment file.

Check the internal published endpoint and container state:

```bash
make health
docker compose ps
docker compose logs --tail=100
```

`make health` checks the frontend, API liveness, and PostgreSQL-backed readiness through the frontend
proxy. Also verify login and a read-only application view through the public HTTPS origin.

## HTTPS reverse proxy

Terminate TLS at an operator-managed proxy and forward to the frontend published port. The proxy
owns certificate renewal, HSTS after validation, request/body limits, relevant security headers,
replacement of untrusted forwarding headers, and source-address login rate limiting. Florabase does
not infer its security origin or user identity from forwarded headers.

## Persistence

The `postgres_data` named volume is the only application-managed durable data store today. It
survives `docker compose down` and container replacement. Attachment/upload storage is not
implemented. Deployment configuration, TLS material, and secrets live outside the application data
volume and need a separate protected backup.

## Safe upgrade

1. Read the incoming changes and migration notes.
2. While the existing installation is healthy, run `make backup` and copy the dump off-host.
3. Update the checked-out branch with the operator's reviewed Git workflow, for example
   `git pull --ff-only` on a release branch.
4. Run `make build`.
5. Ensure PostgreSQL is running with `docker compose up --detach db`.
6. Run `make migrate` to apply Alembic migrations to head.
7. Run `make up`, `make health`, inspect logs, and verify login through HTTPS.

Never use `docker compose down --volumes` or `docker compose down -v` as an upgrade step; either can
delete the database volume. A code rollback may not be compatible with a migrated database. Plan a
reviewed downgrade or restore, and use PostgreSQL's supported `pg_upgrade` or dump/restore procedure
for major PostgreSQL version changes.

See [backup and restore](backup-restore.md) and the [security architecture](security.md).
