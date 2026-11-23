# Install Florabase

Florabase is installed with one directly usable `compose.yaml` file
([ADR 0008](decisions/0008-self-initializing-single-compose.md),
[ADR 0009](decisions/0009-minimal-production-compose.md),
[ADR 0010](decisions/0010-deployable-latest-compose.md)). Take `compose.yaml` from the **latest
release tag** (`https://github.com/alessandrorossato/florabase/blob/<latest-tag>/compose.yaml` —
see [Florabase releases](https://github.com/alessandrorossato/florabase/releases)) rather than
`main`, because `main` may be ahead of the published `:latest` images. Create the data and backup
folders with their container owners once, edit the host folder paths, database password and
canonical origin in `compose.yaml`, and deploy in a Compose manager such as Dockhand or with
`docker compose up -d`. Building from source is for development only
([development](development.md)).

This guide applies from `v0.1.0-beta.8` (and upgrades `v0.1.0-beta.7` installations in place). Use
the documentation at the `v0.1.0-beta.6` tag for that release's manual procedure.
[Florabase releases](https://github.com/alessandrorossato/florabase/releases)

> **Before you start:** Run the one-time
> [folder setup block](#1-create-the-folders-and-set-owners-once) on the Docker host **before** the
> first deploy. If the folders or their owners are missing, `db` and `backend` refuse to start.

## What you install

`compose.yaml` references three linux/amd64 `:latest` images (`ghcr.io/alessandrorossato/florabase-*`)
and defines three non-root services. No container runs as root:

| Service | Container | Role |
| --- | --- | --- |
| `db` | `florabase-db` (`70:70`) | PostgreSQL 18 (`florabase-postgres:latest`, currently `18.6-alpine-florabase.5`). Refuses the `change-me` placeholder password, validates folder owners, modes, empty-folder rules, marker and cluster identity before PostgreSQL starts; pins session `timezone` to `UTC`. |
| `backend` | `florabase-backend` (`10001:10001`) | Runs `florabase-start`: refuses `change-me`, waits for `db`, runs the guarded deploy step (mount separation via `stat` and `/proc/self/mountinfo`, backup checks, advisory lock, init/keep/verified pre-upgrade dump and upgrade, atomic marker, one-time first owner), scrubs owner variables, then `exec`s the exact-head API server (`release_schema serve`). |
| `frontend` | `florabase-frontend` (`101:101`) | The web app and the only published port, bound to `127.0.0.1:8080`. |

Stopping or restarting services keeps all data. Docker restarts `db`, `backend` and `frontend`
after a host reboot; all image guards and the exact-head schema check still apply. Operators who
want `internal: true` database network isolation, read-only root filesystems and dropped
capabilities can layer the optional
[hardened Compose override](security.md#optional-container-hardening).

## Prerequisites

- A linux/amd64 Docker host with Engine 24+ and Compose 2.20+. Other architectures are not built.
- A Compose manager such as Dockhand or Synology Container Manager, or the Docker CLI on the host.
- Local storage for a data folder and a separate backup folder.
- A hostname dedicated to Florabase and an HTTPS reverse proxy on the Docker host with a
  certificate for it, or [Tailscale Serve](#tailscale-and-https). Florabase is served at the root
  of that origin, not under a subpath.
- Pull access to GHCR (`ghcr.io/alessandrorossato/florabase-*`) from the Docker host.
- Private storage, off the host, for backups and for the credentials needed to restore them.

### Verify the release provenance (optional digest pinning)

Every published release attests its three OCI image indexes (`backend`, `frontend`, `postgresql`)
and `release-manifest.json` (which records the exact immutable `@sha256:...` digests and the
SHA-256 of `compose.yaml`). On an admin workstation with the GitHub CLI (`gh`), verify
`release-manifest.json` against the protected release workflow and the approved source SHA:

```bash
repo=alessandrorossato/florabase
gh attestation verify release-manifest.json --repo "$repo" \
  --signer-workflow "$repo/.github/workflows/beta-images.yml" \
  --source-ref refs/heads/main --source-digest '<approved-40-character-commit>' \
  --deny-self-hosted-runners
```

You can also verify any pulled image directly with `gh attestation verify oci://<image>@sha256:...`.
Operators who prefer digest pinning over `:latest` replace the three `image:` lines in
`compose.yaml` with the `reference` values from `release-manifest.json`.

## Quick start

### 1. Create the folders and set owners once

Create a data folder and a separate backup folder **inside** a storage volume, never at a volume
mountpoint itself. Even though short bind syntax lets Docker auto-create a missing host folder
(empty, root-owned), the in-image guards in `db` and `backend` refuse to start until these folders
and owners exist, so an empty database is never silently initialized on the wrong disk.

```bash
DATA=/volume1/docker/florabase/data
BACKUP=/volume1/docker/florabase/backup

mkdir -p "$DATA/postgres" "$DATA/media" "$DATA/state" "$BACKUP/pre-upgrade"
chmod a+rx "$DATA" && chmod a+x "$BACKUP"
chown 70:70 "$DATA/postgres" && chmod 0700 "$DATA/postgres"
chown 10001:10001 "$DATA/media" "$DATA/state" "$BACKUP/pre-upgrade"
chmod 0700 "$DATA/media" "$BACKUP/pre-upgrade" && chmod 0755 "$DATA/state"
```

This matches the `v0.1.0-beta.7` layout exactly. If any folder is missing or has the wrong owner
or mode, `db` or `backend` refuses to start and prints a message pointing back to this block.

### 2. Edit `compose.yaml`

Download `compose.yaml` from the latest release tag
(`https://github.com/alessandrorossato/florabase/blob/<latest-tag>/compose.yaml`) into your stack
directory or paste it into Dockhand, then edit these values in place (no `.env` file is required).
Generate the database password with `openssl rand -hex 32`:

| Field | Required | Meaning |
| --- | --- | --- |
| Volume left-hand paths | yes | Absolute host paths for your data folder (same path on `db` and `backend`) and separate backup folder (on `backend`). Change only the left side of each `:` mount. |
| `FLORABASE_DB_PASSWORD` | yes | PostgreSQL password, identical in both `db` and `backend`, fixed when the database is created. Both services refuse to start while it is still `change-me`. |
| `FLORABASE_CANONICAL_ORIGIN` | yes | The exact HTTPS origin, for example `https://florabase.example.org`, without a trailing slash or path. `backend` refuses to start while it is still the placeholder `https://florabase.example.org`. |
| `frontend` port | no | Loopback port of the frontend, default `127.0.0.1:8080:8080`. Keep the `127.0.0.1:` prefix. |
| `TZ` | no | IANA timezone for container logs, default `Europe/Rome` (database storage and sessions always stay in UTC). |
| `FLORABASE_OWNER_LOGIN` | once | Uncomment on first deploy to create the first owner: 3 to 64 lowercase letters, digits, `.`, `_` or `-`, starting with a letter or digit. |
| `FLORABASE_OWNER_PASSWORD` | once | Uncomment on first deploy: password of the first owner, at least 12 characters. |

Set both owner variables or neither. Without them, the stack still starts and you create the owner
offline with `docker compose --project-name florabase run --rm --no-deps backend python -m
florabase.auth.bootstrap <login>`, using the stack's own name.

### 3. Deploy

In Dockhand, create a stack from `compose.yaml` and its environment, and deploy it. On the command
line:

```bash
docker compose --project-name florabase up -d --wait
```

The first deployment creates the database cluster, initializes the schema, records the
installation and creates the owner. If it fails, for example because of a wrong owner variable,
correct the variable and deploy again: the pending installation is resumed without emptying the
folder (`db` keeps `postgres/installation.pending` until `state/installation.env` is written, and
`backend` keeps `state/installation.pending` across initial schema creation).

On each start, `backend` prints a plain-ASCII startup banner as its first stdout lines (version,
image revision, scheme and authority of `FLORABASE_CANONICAL_ORIGIN`, environment, log format, and
project URL; passwords, database URLs and owner variables are never printed). Container image health
checks run every 30 s once healthy (`backend` probes `/api/v1/health`; `/api/v1/ready` stays the
operator database readiness endpoint). Docker Engine 25+ honours the shorter `start-interval`
(`1s`–`2s`) during startup; Engine 24 ignores `start-interval`, so a cold start on Engine 24 can
take up to one 30 s interval per service in the `db` → `backend` → `frontend` chain.

### 4. Sign in as the owner

Sign in at the HTTPS address, then remove `FLORABASE_OWNER_PASSWORD` (and the login) from the stack
environment and change the password from the account page. `florabase-start` removes both
variables from the API server process before starting `uvicorn`, but until you remove them from
the stack environment they remain visible in the manager's configuration, `docker inspect` and
manager exports; the password is never logged. Later deployments ignore the variables once any
user exists and say so in the `backend` log. A restored database never gets a new owner.

### 5. Put Florabase behind HTTPS and check readiness

Forward your HTTPS hostname to `http://127.0.0.1:<port>` on the same host, where `<port>` is the
host port of the `frontend` mapping (default `8080`). The proxy must terminate TLS for exactly
`FLORABASE_CANONICAL_ORIGIN` at the root path, pass the original `Host` header, allow request
bodies of at least **32 MiB**, and replace any forwarding headers sent by clients. Florabase never
derives its origin, scheme or user identity from forwarded headers.

```nginx
server {
    listen 443 ssl;
    server_name florabase.example.org;
    ssl_certificate     /etc/ssl/florabase/fullchain.pem;
    ssl_certificate_key /etc/ssl/florabase/privkey.pem;
    client_max_body_size 32m;
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $http_host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header Forwarded "";
    }
}
```

The bundled frontend sends the [baseline security headers](security.md); pass them through. Add
HSTS once HTTPS works for every client, plus a source-address limit for `/api/v1/auth/` if the
proxy is reachable from untrusted networks. Then check readiness and sign in:

```bash
curl --fail --show-error https://florabase.example.org/api/v1/ready
```

> **Docker Engine older than 28** may let other machines on the same local network reach ports
> published on `127.0.0.1`. On such hosts, confirm from another device that
> `http://<host-lan-address>:8080` is **not** reachable, and block the port in the host firewall
> if it is.

Once Florabase answers on its HTTPS origin, browsers can install it as an online-only app. See
[Install Florabase as an app](pwa.md).

## Synology NAS

The DS224+ is an amd64 target with Container Manager. Check the Engine and Compose versions it
actually installs; Engine 24.0.2 and Compose 2.20.1 are the baseline. Backups, restores and the
offline password reset need SSH access with the `docker compose` CLI on the NAS.

1. Run the [folder setup block](#1-create-the-folders-and-set-owners-once) inside a local Btrfs or
   ext4 shared folder, for example `/volume1/docker/florabase/data` and
   `/volume1/docker/florabase/backup`. Keep them out of SMB and NFS exports and avoid recursive ACL
   or ownership resets on them.
2. Deploy `compose.yaml` with Dockhand or Container Manager using the variables above.
3. Set up HTTPS with [Tailscale Serve](#tailscale-and-https) or the DSM reverse proxy, verify that
   LAN peers cannot reach the raw port, and repeat the readiness and sign-in check after a planned
   reboot.
4. Schedule the [paired backup](#paired-backup) and copy completed sets off the NAS. A snapshot of
   a running database folder alone is not a backup.

## Tailscale and HTTPS

For private access, run Tailscale on the same host as Docker, enable MagicDNS and HTTPS
certificates, and use the full device name as the canonical origin, for example
`https://<device>.<tailnet>.ts.net`. Keep Funnel disabled and restrict access with the tailnet
policy. [Tailscale HTTPS setup](https://tailscale.com/docs/how-to/set-up-https-certificates)

```bash
tailscale serve --bg --https=443 http://127.0.0.1:8080
tailscale serve status
```

Confirm Serve prints the expected origin and target, then test readiness, owner sign-in and an
upload from a permitted tailnet client, and again after a reboot.
[Tailscale Serve reference](https://tailscale.com/docs/reference/tailscale-cli/serve)

## Upgrade

1. Read the release notes (and optionally verify `release-manifest.json`). Note that
   `florabase-postgres:latest` can move to a rebuilt image within PostgreSQL 18 on manager updates
   (for example Alpine security or entrypoint guard updates), but never crosses a PostgreSQL major
   version automatically; a PostgreSQL major upgrade needs its own documented maintenance.
2. Take a [paired backup](#paired-backup) with the current release.
3. Pull and redeploy the stack (`docker compose --project-name florabase pull && docker compose
   --project-name florabase up -d --wait`, or use your Compose manager's update action). When
   upgrading from `v0.1.0-beta.7`, replace `compose.yaml` with the new file edited with your
   existing folder paths, password and origin; existing beta.7 folder owners and modes already
   match.

Before migrating, `backend`'s guarded deploy step writes
`florabase-<from>-to-<to>-<UTC time>.dump` to `pre-upgrade/` in the backup folder and verifies it
with `pg_restore --list`. This automatic pre-upgrade dump is written only when the database
revision changes; an image-only update (same Alembic head) writes none, so the paired backup in
step 2 is the only recovery point. If the backup folder is missing or unwritable, or the dump
cannot be written or verified, nothing is migrated. Deleting old dumps is your decision.

The upgrade runs in one PostgreSQL transaction. If it fails, the database stays at the previous
release, `backend` writes `state/upgrade-failed.env` (recording the revisions and dump filename)
and refuses to start or write duplicate dumps on subsequent restarts. Fix the cause (or restore
from backup), remove `state/upgrade-failed.env` inside your data folder (the left side of the
`/var/lib/florabase/data` mount), and deploy again. A database
from a newer or unknown release is refused and nothing starts. To go back after a successful
upgrade, restore the pre-upgrade backup into a new data folder with the previous release. For
`v0.1.0-beta.6`, which has no self-initializing layout, follow that tag's documentation; the
pre-upgrade dump holds the database only, so restore it together with the paired media backup.

## Paired backup

The automatic pre-upgrade dump protects against a failed migration; the paired database and media
backup remains the recovery procedure. Take both together while the application is stopped. Over
SSH in a Bash shell, run this block in the folder that holds the stack's `compose.yaml`
(`docker compose ls` shows the stack's project name and config file path; Dockhand keeps its own
copy of `compose.yaml`). If you want `release-manifest.json` archived with the backup, download it
from the release assets of the deployed tag next to `compose.yaml` first; the block includes it
when present and continues without error when it is absent. Set `project` to the stack name and run
this as a block:

```bash
project=florabase
dc() { docker compose --project-name "$project" --file compose.yaml "$@"; }
backup='/absolute/path/to/a/new/backup-directory'
(
  set -e
  umask 077
  mkdir "$backup"
  dc stop frontend backend
  dc exec -T db sh -ec '
    export PGPASSWORD="$FLORABASE_DB_PASSWORD"
    exec pg_dump -Fc --no-owner --no-privileges -U "$POSTGRES_USER" "$POSTGRES_DB"
  ' > "$backup/database.dump"
  dc run --rm --no-deps -T backend python /app/scripts/attachment_artifacts.py verify
  dc run --rm --no-deps -T backend python /app/scripts/attachment_artifacts.py archive \
    > "$backup/media.tar"
  files=(database.dump media.tar compose.yaml)
  cp compose.yaml "$backup/"
  if [ -f release-manifest.json ]; then
    cp release-manifest.json "$backup/"
    files+=(release-manifest.json)
  fi
  cd "$backup"
  sha256sum "${files[@]}" > SHA256SUMS
)
dc up -d --wait
```

Treat a partially written backup directory as incomplete. Keep encrypted off-host copies of the set
and store the credentials separately. A restore drill is part of validating a backup.

## Isolated restore

Restore into a **new, empty data folder** (prepared with the
[folder setup block](#1-create-the-folders-and-set-owners-once)) under a distinct stack name,
never over the live one. This is also how a `v0.1.0-beta.6` installation moves to this layout:
take its paired backup with the beta.6 procedure, then restore it here. On a normal Linux host (for
example when running a restore drill on a laptop), the folder setup block needs `sudo` for `chown`,
and because the production backend refuses a non-`https://` `FLORABASE_CANONICAL_ORIGIN`, a restore
drill on another host needs an HTTPS origin too (see [Tailscale and HTTPS](#tailscale-and-https)).

Because `compose.yaml` sets fixed `container_name: florabase-<role>` names and binds the default
loopback port `127.0.0.1:8080:8080`, create a temporary local override file next to the restore
stack's `compose.yaml` so the restore containers and host port do not collide with the live stack
when restoring on the **same** host (the `ports: !override` mapping is not needed when restoring on
a different host; with Compose 2.20.1 on the same host, edit the port directly in the restore copy
of `compose.yaml` if `!override` is unavailable):

```yaml
# restore-override.yaml (local only, never committed)
services:
  db:
    container_name: florabase-restore-db
  backend:
    container_name: florabase-restore-backend
  frontend:
    container_name: florabase-restore-frontend
    ports: !override
      - "127.0.0.1:8081:8080"
```

1. Deploy the restore stack with its own prepared empty data folder, a backup folder, a distinct
   host port for the `frontend` mapping (default `8080`; needed only when restoring on the same
   host), and a new database password, **without** the owner variables, and wait until it is
   healthy:

   ```bash
   project=florabase-restore
   dc() {
     docker compose --project-name "$project" --file compose.yaml --file restore-override.yaml "$@"
   }
   dc up -d --wait
   ```

2. Stop the application services and replace the empty schema with the dump:

   ```bash
   dc stop frontend backend
   dc exec -T db sh -ec '
     export PGPASSWORD="$FLORABASE_DB_PASSWORD"
     psql -XAq -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
       -c "DROP SCHEMA public CASCADE" -c "CREATE SCHEMA public"
     exec pg_restore --single-transaction --exit-on-error --no-owner --no-privileges \
       -U "$POSTGRES_USER" -d "$POSTGRES_DB"
   ' < /path/to/backup/database.dump
   dc run --rm --no-deps -T backend python /app/scripts/attachment_artifacts.py restore \
     < /path/to/backup/media.tar
   dc run --rm --no-deps -T backend python /app/scripts/attachment_artifacts.py verify
   ```

3. Deploy again (`dc up -d --wait`). The guarded deploy step leaves a current schema unchanged, or
   backs up and upgrades a dump from the previous release. Sign in with the restored credentials
   and check the media, then switch traffic. Reset the owner password first if the backup may hold
   old credentials.

## Recover a forgotten owner password

From a trusted, unrecorded terminal on the host, with `dc` selecting the deployed stack and the
database healthy, stop the application services and reset offline:

```bash
dc stop frontend backend
dc run --rm --no-deps backend python -m florabase.auth.reset_password '<login-name>'
dc up -d --wait
```

The command commits the new password, revokes all sessions and clears the sign-in backoff. It never
migrates. Automation can use `-T` and `--password-json-stdin` with exactly one UTF-8 JSON string
from a protected pipe; keep the password out of arguments, environment variables and logs.

## Optional botanical reference datasets

Florabase runs without them. The production `compose.yaml` of this release mounts no reference
dataset folder, so WFO and WCVP v16 index lookups are unavailable there. Only indexes built by
Florabase's own builders from the pinned official archives are ever supported
([SQLite reference indexes](security/beta-distribution-001/sqlite-reference-indexes.md)).

## Troubleshooting

Read the `db` or `backend` log: every refusal says why, and nothing was changed.

| Message | Meaning and action |
| --- | --- |
| `bind source path does not exist` | A folder is missing or its volume is not mounted. Mount or create it; never let it be created empty elsewhere. |
| `missing required folder ...` / `has owner ..., expected ...` / `has mode ..., expected ...` / `is missing or not writable; run the folder setup commands in docs/installation.md` | A required subfolder is missing or has the wrong owner/mode. Run the [folder setup block](#1-create-the-folders-and-set-owners-once) and deploy again. |
| `... exists and there is no installation marker; use an empty data folder` | The data folder holds something that is not this installation. Use a new empty folder, or restore into one. |
| `the installation marker exists but its database folder is missing or empty` | The database files are gone or the wrong folder is mounted. Fix the mount or restore from a backup. |
| `the installation uses PostgreSQL N, this image M` | A PostgreSQL major-version change needs its own migration. Deploy the previous release. |
| `the database folder belongs to another PostgreSQL cluster` | The marker and the database files come from different installations. Restore the matching pair. |
| `the data and backup folders are the same` / `the backup folder is inside the data folder` (or `FLORABASE_BACKUP_DIR is inside FLORABASE_DATA_DIR`) | Use a backup folder (the left side of the `/var/lib/florabase/backup` mount) outside your data folder (the left side of the `/var/lib/florabase/data` mount). |
| `set both FLORABASE_OWNER_LOGIN and FLORABASE_OWNER_PASSWORD, or neither` / `first owner refused` | Fix the owner variables and deploy again. |
| `pre-upgrade backup failed` / `backup directory ... is missing or not writable` | Fix your backup folder (the left side of the `/var/lib/florabase/backup` mount) or free space and deploy again. Nothing was migrated. |
| `previous upgrade from ... to ... failed ... remove state/upgrade-failed.env before redeploying` | A prior upgrade failed after writing a verified pre-upgrade dump. Inspect the earlier log, resolve the database issue or restore, remove `state/upgrade-failed.env` inside your data folder (the left side of the `/var/lib/florabase/data` mount), and deploy again. |
| `database revision ... is neither image head ... nor the previous release head` | The database comes from a newer, older or unknown release. Deploy the matching release or restore. |
| `differs from image head` (`release_schema serve`) | The schema does not match the backend image; the guarded deploy step did not complete. Read the `backend` log. |

## Uninstalling without losing data

Stop or remove the stack; containers and networks hold no data. The data folder and the backup
folder stay as they are. Delete them only after verifying an off-host backup.

## Known limitations of this beta

- linux/amd64 only.
- Upgrades go from the exact previous release; skipping a release requires installing each one in
  turn or restoring a backup.
- The first owner password stays in the stack environment (and `florabase-backend`'s container
  configuration) until you remove it; `florabase-start` scrubs it from the `uvicorn` process
  environment before serving requests.
- `florabase-backend` mounts your backup folder (the left side of the `/var/lib/florabase/backup`
  mount) read-write so its guarded start step can write pre-upgrade dumps without a separate
  `migrate` container; keep off-host encrypted copies of paired backups.
