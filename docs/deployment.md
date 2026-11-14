# Source-build deployment and upgrades

This guide builds Florabase from a repository checkout. For the linux/amd64 beta distributed as
digest-pinned container images, use the [image-only installation guide](installation.md) and
[beta runtime runbook](beta-runtime-001.md). The two paths both use the `florabase-prod` Compose
project name and have different storage layouts. Keep them on separate hosts. The beta controller
refuses to adopt source-build volumes.

Florabase is pre-release software. Review the incoming changes and keep a tested backup before
every upgrade.

## Prerequisites and deployment model

For the source checkout workflow, install Docker Engine with Compose **2.24.4 or newer**,
Python 3, GNU Make, Git and `curl`. Clone the repository on a host where an operator-managed
HTTPS reverse proxy can reach the frontend port.

The base source-build `compose.yaml` has no custom merge tags. Repository development and
verification overlays use `!override` and `!reset`, which is why the checkout workflow specifies
a newer Compose plugin. With 2.20.1,
the DEV overlay can render both frontend port mappings instead of replacing the production mapping.
The image-only beta uses a separate stack without those tags and its controller accepts Compose
**2.20 or newer**. The beta smoke results apply to that image-only stack.
[Docker Compose merge rules](https://docs.docker.com/reference/compose-file/merge/)

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

`make setup` creates `.env` from `.env.example` and preserves an existing configuration.
Replace the example database password in both `POSTGRES_PASSWORD` and `FLORABASE_DATABASE_URL`.
Use a URL-safe password or percent-encode it in the URL. Git ignores the file.

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

Run source-build commands from the deployment checkout. Define this shell function in each terminal
where you use the examples. It selects the same production project, Compose file and environment as
the Make targets.

```bash
prod() { python3 ./scripts/workflow_environment.py prod compose -- "$@"; }
```

Build the images, wait for PostgreSQL, apply all reviewed migrations, and start the application:

```bash
make build &&
prod up --detach --wait db &&
make migrate &&
make up
```

Application startup never runs migrations. Create the first and only initial owner after migration:

```bash
prod run --rm backend python -m florabase.auth.bootstrap owner
```

The password is prompted without echo. Automation may use `--password-stdin` with a secret provider
that writes one line to standard input. Never put the password in a command argument, Compose file,
image layer, or source-controlled environment file.

For an existing source-build installation, the [owner recovery procedure](portable-installation.md#recover-a-forgotten-owner-password)
also applies. Select the installed source deployment with `prod` in place of `dc`, and run
`prod run --rm --no-deps backend python -m florabase.auth.reset_password '<login-name>'`.

Check the internal published endpoint and container state:

```bash
make health
prod ps
prod logs --tail=100
```

`make health` checks the frontend, API liveness, and PostgreSQL-backed readiness through the frontend
proxy. For a non-default bind address or port, pass the deployment values as `APP_BIND_ADDRESS`
and `APP_PORT` to `make health`. Also verify login and a read-only application view through the
public HTTPS origin.

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

Run these steps from the deployment checkout with the `prod` function from
[First installation](#first-installation).

1. Review the target source, migrations and PostgreSQL image. Record the running source revision,
   image identities and Alembic revision, and retain access to the previous images and configuration.
   Keep the existing PostgreSQL image and service configuration for this application upgrade.
   Plan PostgreSQL changes as a separate reviewed operation.
2. Put the reverse proxy in maintenance mode or otherwise block application traffic. Disable
   automation that can restart services and stop any external database or media writers. From the
   **current** checkout, run `prod stop frontend backend` and check `prod ps --all` to confirm both
   services are stopped. Leave PostgreSQL running.
3. Create and validate the [final coordinated backup with writers stopped](backup-restore.md#backup-during-a-source-build-upgrade)
   using the **current** checkout and images. Copy the matched pair off-host and preserve the
   configuration and secrets separately. Proceed only once the backup and copy succeed.
4. Update the deployment checkout to the reviewed target, for example with `git pull --ff-only` on a
   reviewed release branch, then run `make build`. Keep the application services stopped.
5. With PostgreSQL still running and healthy, run the target backend's migration in a one-shot
   container. Check that the database revision from `alembic current` matches the head shown by
   `alembic heads` before starting the application.

   ```bash
   prod run --rm --no-deps -T backend alembic upgrade head &&
   prod run --rm --no-deps -T backend alembic current &&
   prod run --rm --no-deps -T backend alembic heads
   ```

6. Start the already built application services in order. Each command waits for health and leaves
   PostgreSQL untouched. Stop if either command fails.

   ```bash
   prod up --detach --wait --no-build --no-deps backend &&
   prod up --detach --wait --no-build --no-deps frontend
   ```

   Check `prod ps` and `make health`, and inspect the logs. Verify login and a read-only view
   through HTTPS with operator-only access before reopening traffic.

On backup, build, migration or health failure, halt the sequence and keep maintenance mode in place.
If startup was attempted, stop `frontend` and `backend` again. Inspect the logs and actual database
revision before deciding how to recover. Resume the prior version only after confirming its
compatibility with the database and media. After a schema or data change, use a reviewed forward fix
or restore the matched pre-upgrade database and media with the prior application version. An unchanged
Alembic revision alone cannot establish that every migration side effect was rolled back.

For a replacement restore, select the prior source, images and configuration first. Ensure the
stopped backend container uses the prior image, since `make restore` starts that container when
restore succeeds. If needed, rebuild or recover the prior images and run
`prod up --no-start --no-deps --no-build --force-recreate backend` to recreate it without starting it.
Follow the [restore procedure](backup-restore.md#destructive-restore), then bring back the backend
and frontend in the order shown above using the prior images. Verify health and HTTPS before
reopening traffic. Keep PostgreSQL and its volumes intact during investigation. Avoid
`docker compose down --volumes` and `docker compose down -v`, which can delete persistent data.

The attachment volume is initialized with UID/GID 10001 and mode 0700. An operator-provided bind
mount must grant that runtime account compatible ownership and permissions.

### Shared media migration

ATTACHMENT-005 adds explicit revisions `20261001_0027` and `20261001_0028`; startup does not apply it. Back up the
database and original attachment volume before the operator upgrade. No file moves or re-uploads
are needed. Populated downgrade requires that paired backup. See [shared media](media-library.md)
for Gallery workflows, removal semantics and regenerable thumbnail storage.

Explicit external Save/Refresh needs outbound public HTTP/HTTPS and DNS access. The backend rejects
internal destinations and never fetches during migration, startup, restore or ordinary reads. Saved
external snapshots persist in the existing attachment volume and belong in paired backups.
