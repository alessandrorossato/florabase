# Deployment

## Model

`compose.yaml` builds and runs the production targets. PostgreSQL and the backend remain on the internal network; only the frontend proxy publishes a port. Images use upstream multi-architecture tags and no architecture-specific build steps.

## Release procedure

1. Install supported Docker/Compose and copy `.env.example` to `.env`.
2. Replace credentials with unique secrets. Keep the PostgreSQL password URL-safe or correctly percent-encode it in `FLORABASE_DATABASE_URL`.
3. Set `FLORABASE_CANONICAL_ORIGIN` to the exact public HTTPS origin, without a path, query, or
   fragment. Keep `FLORABASE_CORS_ORIGINS=[]`; the initial browser/API architecture is same-origin.
4. Set `APP_BIND_ADDRESS`; keep `127.0.0.1` when a host reverse proxy is used.
5. Run `make backup` before upgrading an existing installation.
6. Run `make build` and review image/build failures.
7. Start PostgreSQL as appropriate and run `make migrate` explicitly.
8. On a new installation, run the one-shot owner bootstrap documented below.
9. Run `make up`, `make health`, and inspect `docker compose ps` plus logs.

Application startup does not apply migrations. Rollback requires a reviewed application rollback and, when a migration is not safely reversible, a tested restore plan.

Production startup fails closed when the canonical origin is missing or uses HTTP, the cookie mode
is insecure, CORS is enabled, or wildcard CORS is configured.

## First owner

Create the only initial enabled owner after migration and before public exposure:

```bash
docker compose run --rm backend python -m florabase.auth.bootstrap owner
```

The password prompt is not echoed. Automation may use `--password-stdin` with a secret provider
that writes one line to standard input. Do not use a command-line password, environment variable,
Compose setting, setup endpoint, or image build argument. The command fails once any user exists
and concurrent invocations cannot create two owners.

## Reverse proxy

Terminate HTTPS at an operator-managed proxy and forward to the frontend published port. The
external proxy must replace untrusted forwarding headers and owns certificate renewal, HSTS,
request/body limits, applicable security headers, and source-address login rate limiting. The
frontend and backend do not use forwarded headers as an identity source, and the backend is not
directly exposed; security-sensitive public URL behavior uses `FLORABASE_CANONICAL_ORIGIN`, not
inferred headers.

## Persistence and upgrades

`postgres_data` is durable across `docker compose down` and container recreation; never use `docker compose down --volumes` during normal operations. Future uploads will use a separately backed-up persistent volume or bind mount. Major PostgreSQL upgrades require the PostgreSQL project's supported `pg_upgrade` or dump/restore process and a tested rollback window.
