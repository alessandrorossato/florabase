# Installing Florabase (v0.1.0-beta.1)

This guide is for people who want to **run** Florabase on their own server from the published
container images. You do not need the source code, Node.js, a Python development environment or a
compiler. Developers working on Florabase itself should read [development](development.md) instead.

> **Beta status.** `v0.1.0-beta.1` is a private, single-owner prerelease. It is not yet published;
> the commands below name the release assets it will carry. Keep a tested backup before every
> upgrade. Known limitations are listed at the end of this guide.

## What you install

| Part | Image | Role |
| --- | --- | --- |
| `frontend` | `ghcr.io/alessandrorossato/florabase-frontend` | nginx serving the built React app; forwards `/api/` to the backend; the only published port, on `127.0.0.1` |
| `backend` | `ghcr.io/alessandrorossato/florabase-backend` | FastAPI/Uvicorn API, owner authentication, media storage |
| `db` | `docker.io/library/postgres:18.6-alpine` | PostgreSQL 18, never published to the host |

Both application images come from one source commit and are pinned by immutable digest from one
signed release manifest, so the backend and frontend can never be mixed across versions. A small
host program, `florabasectl.py` (Python standard library only), installs, migrates, backs up,
restores and upgrades the stack. Docker Compose (or Dockhand) runs it.

Three release assets plus the manifest are all you download:

| Asset | Purpose |
| --- | --- |
| `release-manifest.json` | Exact image digests, source commit, PostgreSQL identity and database schema version |
| `compose.yaml` | The stack definition (image-only; no builds, no source mounts) |
| `florabasectl.py` | The installation controller |
| `florabase.env.example` | Annotated list of every stack variable (for review; the controller writes the real file) |

## Prerequisites

- A **linux/amd64** host. linux/arm64 (for example a Raspberry Pi or an ARM NAS) is **not supported
  in this beta**: no arm64 images are built or tested.
- Docker Engine **24.0 or newer** and the Docker Compose plugin **2.20 or newer**
  (`docker compose version`). Synology DSM 7.2 Container Manager (Engine 24.0.2, Compose 2.20.1)
  is the tested minimum.
- Python **3.8 or newer** on the host (`python3 --version`), for `florabasectl.py`.
- A root shell on the host (`sudo -i`). The controller creates directories owned by the
  container users and protects the secret files.
- At least 2 GiB of available memory and 20 GiB of free disk for the application, database, media
  and several backups. Keep the database on a local disk (ext4, Btrfs, XFS), never a network share.
- An **HTTPS reverse proxy on the same host** (nginx, Caddy, Traefik, Tailscale Serve and so on).
  Florabase only accepts HTTPS in production and always serves on its own host name, never on a
  sub-path such as `https://example.org/florabase/`.

The controller checks these for you:

```bash
python3 florabasectl.py --root /srv/florabase preflight --evidence preflight.json
```

`preflight.json` describes your host; keep it private.

## 1. Download and verify the release

Use a working directory outside the future installation root, for example `/srv/florabase-bundle`:

```bash
mkdir -p /srv/florabase-bundle && cd /srv/florabase-bundle
base=https://github.com/alessandrorossato/florabase/releases/download/v0.1.0-beta.1
for file in release-manifest.json compose.yaml florabasectl.py florabase.env.example; do
  curl --fail --location --remote-name "$base/$file"
done
sha256sum release-manifest.json compose.yaml florabasectl.py
```

Compare the printed SHA-256 values with the digests that GitHub shows for each asset on the
release page. Optionally verify the manifest's build provenance with the GitHub CLI:

```bash
gh attestation verify release-manifest.json --repo alessandrorossato/florabase \
  --signer-workflow alessandrorossato/florabase/.github/workflows/beta-images.yml \
  --source-ref refs/heads/main --deny-self-hosted-runners
```

Keep the manifest's SHA-256: every install and upgrade command requires it, and the controller
refuses a manifest whose hash differs. The controller never uses image tags.

If the GHCR packages are private for your release, log in first with a read-only token:
`docker login ghcr.io` (the password is read from the terminal).

## 2. Initialize the installation

Choose an installation root (any absolute path; examples use `/srv/florabase`, on Synology
`/volume1/docker/florabase`) and the **final** HTTPS address users will open:

```bash
python3 florabasectl.py --root /srv/florabase init --origin https://florabase.example.org
```

- `--origin` is the exact public origin: scheme and host (and port only if it is not 443), with
  no path or trailing slash. Login cookies and cross-site request protection are bound to it.
  Changing it later is not supported in this beta, so choose the final name now.
- `--http-port 8080` (default) is the loopback port your reverse proxy forwards to. The address
  is always `127.0.0.1`; no setting can publish Florabase, the API or PostgreSQL on another
  interface.
- `--db-memory 1g` and `--backend-memory 768m` are memory ceilings; lower them on small hosts.

`init` refuses a non-empty root, so it can never adopt or overwrite existing data. It creates:

| Directory | Owner / mode | Content |
| --- | --- | --- |
| `stack/` | root 0750 | `compose.yaml`, rendered `.env` and `reference.env` |
| `secrets/` | root 0700 | `db.env`, `backend.env`: randomly generated database credentials (0600) |
| `postgres/` | 70:70 0700 | PostgreSQL data |
| `media/` | 10001:10001 0700 | Uploaded original images and saved copies |
| `reference/` | root 0755 | Optional read-only botanical reference datasets |
| `backups/` | root 0700 | Recovery sets |
| `state/` | root 0700 | Installation record, current release, operation journal |
| `restore/`, `preserved/` | root 0700 | Restore drills and data set aside by a replacement restore |

No password, key or default credential is shipped in an image or in `compose.yaml`.

### Configuration reference

The controller renders `stack/.env` from your `init` choices and the release manifest;
`florabase.env.example` documents each variable. Do not edit the rendered files by hand: upgrades
compare them byte-for-byte and refuse drifted files. `florabasectl.py apply` re-renders and
redeploys the recorded configuration.

| Variable | Meaning |
| --- | --- |
| `FLORABASE_RELEASE_VERSION`, `FLORABASE_EXPECTED_ALEMBIC_HEAD` | Installed release and its database schema version |
| `FLORABASE_BACKEND_IMAGE`, `FLORABASE_FRONTEND_IMAGE`, `FLORABASE_POSTGRES_IMAGE` | Digest-pinned images from the manifest |
| `FLORABASE_CANONICAL_ORIGIN` | The HTTPS origin from `init --origin` |
| `FLORABASE_HTTP_PORT` | Loopback port for the reverse proxy |
| `FLORABASE_SECRETS_DIR`, `FLORABASE_POSTGRES_DIR`, `FLORABASE_MEDIA_DIR`, `FLORABASE_REFERENCE_DIR` | Absolute host paths under the root |
| `FLORABASE_DB_MEMORY`, `FLORABASE_BACKEND_MEMORY`, `FLORABASE_*_CPUS` | Resource ceilings (`0` CPUs = unlimited) |
| `FLORABASE_LOG_LEVEL` | Backend log level (`INFO` by default; logs are JSON) |

Secrets live only in `secrets/db.env` (`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`) and
`secrets/backend.env` (`FLORABASE_DATABASE_URL`). Back them up separately from the data.

## 3. Install the release

```bash
python3 florabasectl.py --root /srv/florabase install \
  --manifest /srv/florabase-bundle/release-manifest.json --manifest-sha256 <manifest-sha256>
```

This pulls the three images by digest, verifies their labels, platform and schema version, starts
PostgreSQL, **creates the database schema explicitly** (the only migration that ever runs without
a backup, because the database is empty), starts the application and runs acceptance checks. A
second `install` against a non-empty database is refused. If the install is interrupted, re-run
the same command.

## 4. Create the owner account

Florabase has exactly one owner account and no default login. Create it once:

```bash
python3 florabasectl.py --root /srv/florabase bootstrap-owner <login-name>
```

The password (at least 12 characters) is prompted without echo, or read from standard input for
automation; it is never accepted as a command-line argument. A second owner is refused. There is no
password reset in this beta, so store the password in a password manager.

## 5. Put Florabase behind HTTPS

Forward your HTTPS host name to `http://127.0.0.1:<http-port>` on the same host. The proxy must:

- terminate TLS for exactly the origin given to `init`, at the root path;
- pass the original `Host` header;
- allow request bodies of at least **32 MiB** (images up to 25 MiB plus form overhead);
- replace any forwarding headers sent by clients. Florabase does not derive its origin, scheme
  or user identity from `X-Forwarded-*` or `Forwarded` headers, but your proxy logs and rate
  limits might.

Minimal nginx server block (the same configuration the release acceptance test runs):

```nginx
server {
    listen 443 ssl;
    server_name florabase.example.org;
    ssl_certificate     /etc/ssl/florabase/fullchain.pem;
    ssl_certificate_key /etc/ssl/florabase/privkey.pem;
    client_max_body_size 32m;
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-For $remote_addr;
    }
}
```

With Tailscale (private access within your tailnet, no public exposure, Funnel off):

```bash
tailscale serve --bg --https=443 http://127.0.0.1:8080
```

Add HSTS, login rate limiting and certificate renewal in the proxy. Then accept the installation
through the public address, including an owner login and logout:

```bash
python3 florabasectl.py --root /srv/florabase acceptance \
  --base-url https://florabase.example.org --owner <login-name>
```

> **Docker Engine older than 28** may let other machines on the same local network reach ports
> published on `127.0.0.1`. On such hosts, confirm from another device that
> `http://<host-lan-address>:8080` is **not** reachable, and block the port in the host firewall
> if it is.

## Day-to-day operation

Containers restart automatically (`restart: unless-stopped`) after a crash, a Docker restart or a
reboot. Restarting **never** changes the database. From the stack directory you can use ordinary
Compose commands:

```bash
cd /srv/florabase/stack
docker compose ps
docker compose logs --tail=100 backend
docker compose restart backend frontend
```

`python3 florabasectl.py --root /srv/florabase status` summarizes health, the newest backup and any
unfinished operation, and exits non-zero when something needs attention. Schedule it hourly and
`backup` nightly (cron or DSM Task Scheduler, as root, with failure notification).

### Data and volumes

All persistent data lives in host directories under the root. The Compose volumes
(`florabase-prod_postgres_data`, `_attachment_data`, `_reference_data`) are only bind mounts onto
those directories: if a directory is missing the container refuses to start instead of creating an
empty database, and removing a Docker volume object never deletes the host data.

## Database migrations and upgrades

Florabase **never migrates the database on `docker compose up`, a restart or an image update.**
Before the server starts, the backend checks that the database is exactly at the schema version of
its release and refuses otherwise, with a message that names the action to take (see
[Troubleshooting](#troubleshooting)). A newer image therefore cannot silently change your data.

Upgrade with one controller command:

```bash
python3 florabasectl.py --root /srv/florabase promote \
  --manifest /srv/florabase-bundle/<new>/release-manifest.json --manifest-sha256 <sha256> \
  --confirm-migration
```

`--confirm-migration` is required only when the new release changes the schema; without it a
schema-changing release is refused before anything happens. `promote` is one serialized, journaled
operation that performs the upgrade sequence in order:

1. **Quiesce writers.** Refuses if another operation is unfinished, the stack files were edited,
   the volumes are foreign, the manifest or images fail verification, the database is newer than
   the target, or the PostgreSQL image would change. Then stops `backend` and `frontend`.
2. **Back up and verify.** Writes a pre-upgrade recovery set (database dump plus every original
   image), verifies it and records checksums.
3. **Migrate explicitly.** Runs the *target* backend image's one-shot migration
   (`docker compose --profile maintenance run --rm migrate`, which executes `alembic upgrade head`)
   against the stopped installation.
4. **Verify the schema.** Checks that the database is exactly at the target release's head.
5. **Start and check.** Pins the new image pair, starts the services and runs acceptance.

If anything fails, writers stay stopped and the command prints exactly one recovery choice:

| Situation | Command |
| --- | --- |
| Interrupted (killed, reboot) | `resume` continues from the recorded phase |
| Failed before the schema changed | `abort` returns to the previous release |
| Migrated, but the new application fails | `abort` is refused; `promote --after-failed` with a fixed release, or `restore-replace <pre-upgrade set>` |

Never run the `migrate` service by hand on a live installation, and never "downgrade" by pinning
older images: an older backend refuses a newer schema.

### PostgreSQL versions

The beta uses **PostgreSQL 18** (`18.6-alpine`, pinned by digest). Application upgrades never change
the PostgreSQL image; `promote` refuses a release whose PostgreSQL identity differs. A PostgreSQL
rebuild or minor update is separate, explicitly reviewed maintenance. A **major** version change
(for example to 19) cannot reuse the data directory: it needs a new installation restored from a
logical backup, and it is not automated in this beta. PostgreSQL itself refuses to start on a data
directory from another major version, so a wrong image fails instead of corrupting data. A database
created by PostgreSQL 18 cannot be opened by an older major version.

## Backups and restores

A **recovery set** pairs the PostgreSQL dump with the archive of every original image, the stack
document, table counts and checksums. Database and media are always taken together, with the
application stopped for a few seconds so both describe the same moment.

```bash
python3 florabasectl.py --root /srv/florabase backup          # prints BACKUP_COMPLETE <set-id>
python3 florabasectl.py --root /srv/florabase verify-backup <set-id>
python3 florabasectl.py --root /srv/florabase list-backups
python3 florabasectl.py --root /srv/florabase retention         # dry run; add --apply
```

Copy sets off the host. The controller can store a set in an encrypted
[restic](https://restic.net/) repository, check it, restore it to scratch space and verify every
checksum before reporting success:

```bash
python3 florabasectl.py --root /srv/florabase export <set-id> \
  --repository <restic-repository> --password-file /root/restic-password [--init]
```

Also keep, in a separate place, a copy of `secrets/`, `state/installation.json`, the restic
password and your proxy configuration.

**Test a restore without touching live data** (recommended after the first backup and regularly):

```bash
python3 florabasectl.py --root /srv/florabase restore-isolated <set-id> --http-port 18081 --owner <login>
python3 florabasectl.py --root /srv/florabase restore-remove --project <printed-name> --confirm <printed-name>
```

The drill restores into a separate project on another loopback port, compares the schema version
and every table count, verifies every original image and logs in.

**Replace live data with a set** (disaster recovery). Both confirmations must match exactly:

```bash
python3 florabasectl.py --root /srv/florabase restore-replace <set-id> \
  --confirm-installation <installation-id> --confirm-database florabase
```

The current `postgres/` and `media/` directories are moved to `preserved/<time>/`, not deleted, so
writes made after the set can still be inspected. All sessions are signed out. On a new host, run
`init` and `install` for the same release first, then `import-set` from restic and
`restore-replace`.

## Managing Florabase with Dockhand

Dockhand can show, start, stop, restart and inspect the stack's logs.
Installation, upgrades, migrations, backups and restores stay in `florabasectl.py` on the host,
because they must quiesce writers and take a verified backup first.

1. Install Florabase with `init`, `install` and `bootstrap-owner` as above.
2. In Dockhand, import `/srv/florabase/stack` as an **existing stack in place**. Dockhand (or its
   agent) must see `stack/` and `secrets/` at the same absolute paths as the host, because
   `env_file` paths are resolved on the Docker host.
3. In Settings → Environments → *your environment* → Updates, turn **Automatically update
   containers off**. Every Florabase container also carries the `dockhand.update=false` label.
4. Do not connect the stack to Git sync, auto-redeploy or a deployment webhook, and do not edit
   `compose.yaml` or `.env` in Dockhand's editor: the next upgrade refuses edited files.
5. Start, stop, restart and redeploy from Dockhand as needed. A redeploy of the recorded files is
   safe: the backend refuses to serve an incompatible schema. It is not an upgrade.
6. For an upgrade, run `promote` on the host. Dockhand then shows the new containers. Use
   `florabasectl.py check-release --manifest … --manifest-sha256 …` for release notifications, since
   excluded containers show no update badge.

Protect Dockhand itself: enable its authentication, never expose it publicly and back up its data
directory including its encryption key. Screenshots are not included: the Dockhand workflow above
has not yet been recorded on a real Dockhand installation for this release.

## Troubleshooting

| Symptom (backend log or command output) | Cause and action |
| --- | --- |
| `schema-guard: invalid configuration (ValidationError) …` | A setting is missing or invalid; the message names the field (values are never printed). Fix the installation with `florabasectl.py apply`; a hand-edited `.env` is the usual cause |
| `… database revision unavailable …` | PostgreSQL is not running or the credentials do not match. Check `docker compose ps db` and `logs db`; then `docker compose up -d` |
| `… not release head … (the database is not initialized …)` | Empty database: run `florabasectl.py install` |
| `… (a migration is pending …)` | Images are newer than the database. Use `promote`, which backs up and migrates; never run `migrate` by hand |
| `… (the database is newer than or foreign to this image …)` | An older or unrelated image was pinned. Run `florabasectl.py apply` to restore the recorded release, or restore a recovery set |
| `Failed to load …/secrets/backend.env: … no such file or directory` from Compose | The secrets directory is missing or unreadable; Compose changes nothing. Restore `secrets/` from your configuration backup |
| Login fails with HTTP 403 | The browser address differs from `--origin`, or the proxy changes the `Origin`/`Host`. Open exactly the configured origin |
| Uploads fail with HTTP 413 | The reverse proxy's body limit is below 32 MiB |
| `status` reports an old backup or low disk | Check the scheduled `backup`, free space under the root, and `retention --apply` |

Readiness is `GET /api/v1/ready` through the frontend; liveness is `/healthz`. With PostgreSQL
stopped, readiness fails (an error, or no answer within the client timeout when the `db` name cannot
be resolved) while `/healthz` stays live, and the backend healthcheck reports unhealthy.

## Uninstalling without losing data

Stopping and removing containers never removes data:

```bash
cd /srv/florabase/stack
docker compose down          # containers and network only
```

Never add `--volumes`/`-v` out of habit; even then, Florabase's bind-backed volumes leave the host
directories intact. To delete Florabase permanently, first take and verify a final `backup`, copy
it off the host, then remove `/srv/florabase` yourself. Removing the images
(`docker image rm …`) frees disk space and is safe once the containers are gone.

## Known limitations of this beta

- linux/amd64 only; arm64 is not built or tested.
- One owner account; no password change or reset, no additional users.
- The HTTPS origin and loopback-only publication are fixed at `init`; a reverse proxy on another
  machine is not supported.
- PostgreSQL major upgrades and automatic application promotion are not provided.
- Optional online map tiles (`runtime-config.js`) are not configurable in this stack.

Operator and developer background: [beta runtime runbook](beta-runtime-001.md),
[image release contract](beta-image-001.md), [security](security.md).
