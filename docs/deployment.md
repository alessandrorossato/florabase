# Deployment and upgrades

This is the canonical self-hosting guide. Florabase is pre-release software: review changes and keep
a tested backup before every upgrade.

## Prerequisites and deployment model

Install Docker Engine with Docker Compose v2, GNU Make, and `curl`. Clone the repository on a host
where an operator-managed HTTPS reverse proxy can forward to the frontend port.

`compose.yaml` builds the production targets in the explicit `florabase-prod` project. DEV retains
its separate legacy `florabase` project; Review and Preview use their own resources. Existing baseline
installations previously using `florabase` must preserve and deliberately migrate coordinated DB/media
before adopting the new production project name. No helper silently attaches those volumes.
See [environment boundaries](development-workflow.md).

`compose.yaml` builds the production targets. PostgreSQL and FastAPI remain on the internal Compose
network; only the nginx frontend proxy publishes `${APP_BIND_ADDRESS}:${APP_PORT}`. The frontend
serves the React application and forwards `/api/` to FastAPI.

## Resource expectations

See the [PERF-001 measured environment and resource report](performance/PERF-001.md) for the
representative personal-collection workload, production image sizes, runtime memory, known costs and
reproduction commands. Its measurements describe one host and a disposable tmpfs database, not a
minimum-hardware guarantee. Build/test memory differs from steady runtime use; run heavy verification
and image builds serially on a constrained host. Allow for the OS, Docker, HTTPS proxy, persistent
media/database growth and backups in addition to measured application containers.

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

### Provenance-map basemap

Collection origins starts with bundled Natural Earth 1:110m generalized geography. This is an
orientation overview, not street-level detail; markers retain their exact recorded WGS84 positions
and accuracy circles. Local geography, records and inspector do not require an external provider.

The frontend image includes `/usr/share/nginx/html/runtime-config.js`. An operator may replace or
bind-mount it, setting `mapOnlineEnabled: true`, `mapTileUrl` and `mapAttribution` only after verifying
that the selected provider permits this deployment. The visitor must then explicitly enable Online
basemap. The shipped flag is false. Preserve the provider's attribution; the canonical public OSM
endpoint is `https://tile.openstreetmap.org/{z}/{x}/{y}.png` and its
[tile usage policy](https://operations.osmfoundation.org/policies/tiles/) applies. No bulk acquisition,
prefetch, host rotation, custom User-Agent, proxy impersonation or cache bypass is implemented.

Tiles go directly from the browser to the provider, disclosing IP, viewed tile area and the app
origin. Cross-origin Referer uses `strict-origin-when-cross-origin`; record paths, hashes, queries,
identity names and notes are not sent. Suppressing Referer violates public OSM policy. Choose a
permitted self-hosted provider if this disclosure is undesirable. The first image/tile error removes
the whole online layer and disables further attempts until the next visit; local evidence remains.
Browser image errors cannot reliably distinguish HTTP status or detect policy artwork returned with
HTTP 200. A deployment must resolve provider access before enabling the optional layer. The app does
not geocode, request geolocation or infer provenance from basemap availability.

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

The `postgres_data` and backend attachment named volumes hold application-managed durable data. They
survive `docker compose down` and container replacement. A complete application backup includes the
paired PostgreSQL dump and attachment archive described in [backup and restore](backup-restore.md).
Deployment configuration, TLS material, and secrets need a separate protected backup.

## Safe upgrade

1. Read the incoming changes and migration notes.
2. While the existing installation is healthy, run `make backup` and copy both the database dump and
   matching attachment archive off-host.
3. Update the checked-out branch with the operator's reviewed Git workflow, for example
   `git pull --ff-only` on a release branch.
4. Run `make build`.
5. Ensure PostgreSQL is running with `docker compose up --detach db`.
6. Run `make migrate` to apply Alembic migrations to head.
7. Run `make up`, `make health`, inspect logs, and verify login through HTTPS.

Never use `docker compose down --volumes` or `docker compose down -v` as an upgrade step; either can
delete the database and attachment volumes. The dedicated attachment volume is initialized from the
backend image with UID/GID 10001 ownership and mode 0700. An operator replacing it with a host bind
mount must provide that runtime account compatible ownership and permissions; do not use 0777. A
code rollback may not be compatible with a migrated database. Plan a reviewed downgrade or restore,
and use PostgreSQL's supported `pg_upgrade` or dump/restore procedure for major PostgreSQL version
changes.

See [backup and restore](backup-restore.md) and the [security architecture](security.md).

### Shared media migration

ATTACHMENT-005 adds explicit revisions `20261001_0027` and `20261001_0028`; startup does not apply it. Back up the
database and original attachment volume before the operator upgrade. No file moves or re-uploads
are needed. Populated downgrade requires that paired backup. See [shared media](media-library.md)
for Gallery workflows, removal semantics and regenerable thumbnail storage.

Explicit external Save/Refresh needs outbound public HTTP/HTTPS and DNS access. The backend rejects
internal destinations and never fetches during migration, startup, restore or ordinary reads. Saved
external snapshots persist in the existing attachment volume and belong in paired backups.
