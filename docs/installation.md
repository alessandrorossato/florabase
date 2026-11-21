# Install Florabase

Florabase is installed with one file: the `compose.yaml` attached to each release
([ADR 0008](decisions/0008-self-initializing-single-compose.md)). A Compose manager such as Dockhand
deploys it as-is, or you run `docker compose up -d`. The only host step is creating two empty
folders. Building from source is for development only ([development](development.md)).

This guide applies from `v0.1.0-beta.7`. Use the documentation at the
`v0.1.0-beta.6` tag for that release's manual procedure.
[Florabase releases](https://github.com/alessandrorossato/florabase/releases)

## What you install

`compose.yaml` pins three linux/amd64 images by digest and defines five services:

| Service | Runs | Role |
| --- | --- | --- |
| `prepare` | once per deployment, PostgreSQL image, no network | Checks the two folders and creates their subfolders with the right owners. Refuses anything that is neither an empty folder nor this installation. |
| `db` | always | PostgreSQL 18. Creates its cluster only for a new installation. |
| `migrate` | once per deployment, backend image | Initializes the schema, leaves a current schema unchanged, or backs up and upgrades from the previous release. Creates the first owner once. |
| `backend` | always | The API. It never migrates and refuses to start unless the schema matches its image exactly. |
| `frontend` | always | The web app and the only published port, bound to `127.0.0.1`. |

Stopping or restarting services keeps all data. Docker restarts `db`, `backend` and `frontend`
after a host reboot; the backend schema check still applies.

## Prerequisites

- A linux/amd64 Docker host with Engine 24+ and Compose 2.20+. Other architectures are not built.
- A Compose manager that supports environment interpolation, long-form bind mounts, health and
  completion dependencies, and host-IP port bindings, or the Docker CLI on the host.
- Local storage for a data folder and a separate backup folder.
- A hostname dedicated to Florabase and an HTTPS reverse proxy on the Docker host with a
  certificate for it, or [Tailscale Serve](#tailscale-and-https). Florabase is served at the root
  of that origin, not under a subpath.
- Pull access to the release's GHCR images from the Docker host.
- Private storage, off the host, for backups and for the credentials needed to restore them.

### Verify the release assets

On an admin workstation with the GitHub CLI (`gh`), verify `compose.yaml` and
`release-manifest.json` against the protected release workflow and the full approved source SHA
from the release record. Keep both files for upgrades and recovery.

```bash
repo=alessandrorossato/florabase
(
  set -e
  for file in compose.yaml release-manifest.json; do
    gh attestation verify "$file" --repo "$repo" \
      --signer-workflow "$repo/.github/workflows/beta-images.yml" \
      --source-ref refs/heads/main --source-digest '<approved-40-character-commit>' \
      --deny-self-hosted-runners
  done
)
```

## Quick start

### 1. Create two empty folders

Create a data folder and a separate backup folder **inside** a storage volume, for example with a
NAS file manager. Never point Florabase at a volume mountpoint itself: when the volume is missing,
the folder is then missing too and the deployment fails instead of starting empty.

```text
/volume1/docker/florabase/data      FLORABASE_DATA_DIR    (empty)
/volume1/docker/backup/florabase    FLORABASE_BACKUP_DIR  (empty or existing; not inside the data folder)
```

`prepare` creates `postgres/` (owner `70`), `media/` and `state/` (owner `10001`) in the data
folder and `pre-upgrade/` (owner `10001`) in the backup folder. It adds the search permission for
other users to the two folder roots if it is missing, so the container users can reach their
subfolders. It never changes anything else, and Compose never creates a missing folder.

### 2. Set the variables

Set these in the manager's stack environment or in a mode-0600 `.env` next to `compose.yaml`.
Generate the database password with `openssl rand -hex 32`.

| Variable | Required | Meaning |
| --- | --- | --- |
| `FLORABASE_DATA_DIR` | yes | Absolute path of the data folder |
| `FLORABASE_BACKUP_DIR` | yes | Absolute path of the backup folder |
| `FLORABASE_DB_PASSWORD` | yes | PostgreSQL password, fixed when the database is created |
| `FLORABASE_CANONICAL_ORIGIN` | yes | The exact HTTPS origin, for example `https://florabase.example.org`, without a trailing slash or path |
| `FLORABASE_HTTP_PORT` | no | Loopback port of the frontend, default `8080` |
| `FLORABASE_OWNER_LOGIN` | once | Login name of the first owner: 3 to 64 lowercase letters, digits, `.`, `_` or `-`, starting with a letter or digit |
| `FLORABASE_OWNER_PASSWORD` | once | Password of the first owner, at least 12 characters |

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
folder.

### 4. Sign in as the owner

Sign in at the HTTPS address, then remove `FLORABASE_OWNER_PASSWORD` (and the login) from the stack
environment and change the password from the account page. Until removed, the password stays
visible in the manager's environment, in `docker inspect` and in manager exports; it is never
logged. Later deployments ignore the variables once any user exists and say so in the `migrate`
log. A restored database never gets a new owner.

### 5. Put Florabase behind HTTPS and check readiness

Forward your HTTPS hostname to `http://127.0.0.1:<FLORABASE_HTTP_PORT>` on the same host. The proxy
must terminate TLS for exactly `FLORABASE_CANONICAL_ORIGIN` at the root path, pass the original
`Host` header, allow request bodies of at least **32 MiB**, and replace any forwarding headers sent
by clients. Florabase never derives its origin, scheme or user identity from forwarded headers.

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
actually installs; Engine 24.0.2 and Compose 2.20.1 are the baseline.

1. Create the two folders with File Station inside a local Btrfs or ext4 shared folder, for example
   `/volume1/docker/florabase/data` and `/volume1/docker/backup/florabase`. Keep them out of SMB and
   NFS exports and avoid recursive ACL or ownership resets on them.
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

1. Read the release notes and verify the new `compose.yaml` and `release-manifest.json`. A change of
   PostgreSQL major version needs its own documented migration.
2. Take a [paired backup](#paired-backup) with the current release.
3. Replace the stack's `compose.yaml` with the new file, keeping the same stack name, folders,
   password and origin, and deploy it. Current Docker Compose versions stop the previous backend
   before `migrate` runs; with another manager, stop the stack before deploying a new release.

`migrate` upgrades only from the exact previous release. Before migrating it writes
`florabase-<from>-to-<to>-<UTC time>.dump` to `pre-upgrade/` in the backup folder and verifies it
with `pg_restore --list`. If the backup folder is missing or the dump cannot be written or verified,
nothing is migrated. Deleting old dumps is your decision.

The upgrade runs in one PostgreSQL transaction. If it fails, the database stays at the previous
release, the backend refuses to start and nothing is lost: fix the cause and deploy again, or
restore the dump or the paired backup with the [isolated restore](#isolated-restore). A database
from a newer or unknown release is refused and nothing starts. To go back after a successful
upgrade, restore the pre-upgrade backup into a new data folder with the previous release. For
`v0.1.0-beta.6`, which has no self-initializing layout, follow that tag's documentation; the
pre-upgrade dump holds the database only, so restore it together with the paired media backup.

## Paired backup

The automatic pre-upgrade dump protects against a failed migration; the paired database and media
backup remains the recovery procedure. Take both together while the application is stopped. In a
Bash shell, from the folder with `compose.yaml` and `.env` (the same values the manager uses), set
`project` to the stack name and run this as a block:

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
    export PGPASSWORD="$POSTGRES_PASSWORD"
    exec pg_dump -Fc --no-owner --no-privileges -U "$POSTGRES_USER" "$POSTGRES_DB"
  ' > "$backup/database.dump"
  dc run --rm --no-deps -T backend python /app/scripts/attachment_artifacts.py verify
  dc run --rm --no-deps -T backend python /app/scripts/attachment_artifacts.py archive \
    > "$backup/media.tar"
  cp compose.yaml release-manifest.json "$backup/"
  cd "$backup"
  sha256sum database.dump media.tar compose.yaml release-manifest.json > SHA256SUMS
)
dc up -d --wait
```

Treat a partially written backup directory as incomplete. Keep encrypted off-host copies of the set
and store the credentials separately. A restore drill is part of validating a backup.

## Isolated restore

Restore into a **new, empty data folder** under a distinct stack name, never over the live one.
This is also how a `v0.1.0-beta.6` installation moves to this layout: take its paired backup with
the beta.6 procedure, then restore it here.

1. Deploy the restore stack with its own empty data folder, a backup folder and a new database
   password, **without** the owner variables, and wait until it is healthy.
2. Stop the application services and replace the empty schema with the dump:

   Reuse the `dc` function from [Paired backup](#paired-backup), run from a folder whose
   `compose.yaml` and `.env` hold the restore stack's values.

   ```bash
   project=florabase-restore
   dc stop frontend backend
   dc exec -T db sh -ec '
     export PGPASSWORD="$POSTGRES_PASSWORD"
     psql -XAq -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
       -c "DROP SCHEMA public CASCADE" -c "CREATE SCHEMA public"
     exec pg_restore --single-transaction --exit-on-error --no-owner --no-privileges \
       -U "$POSTGRES_USER" -d "$POSTGRES_DB"
   ' < /path/to/backup/database.dump
   dc run --rm --no-deps -T backend python /app/scripts/attachment_artifacts.py restore \
     < /path/to/backup/media.tar
   dc run --rm --no-deps -T backend python /app/scripts/attachment_artifacts.py verify
   ```

3. Deploy again. `migrate` leaves a current schema unchanged, or backs up and upgrades a dump from
   the previous release. Sign in with the restored credentials and check the media, then switch
   traffic. Reset the owner password first if the backup may hold old credentials.

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

Read the `prepare`, `db` or `migrate` log: every refusal says why, and nothing was changed.

| Message | Meaning and action |
| --- | --- |
| `bind source path does not exist` | A folder is missing or its volume is not mounted. Mount or create it; never let it be created empty elsewhere. |
| `... exists and there is no installation marker; use an empty data folder` | The data folder holds something that is not this installation. Use a new empty folder, or restore into one. |
| `the installation marker exists but its database folder is missing or empty` | The database files are gone or the wrong folder is mounted. Fix the mount or restore from a backup. |
| `the installation uses PostgreSQL N, this image M` | A PostgreSQL major-version change needs its own migration. Deploy the previous release. |
| `the database folder belongs to another PostgreSQL cluster` | The marker and the database files come from different installations. Restore the matching pair. |
| `FLORABASE_BACKUP_DIR is inside FLORABASE_DATA_DIR` (or the reverse, or `the same`) | Use a backup folder outside the data folder. |
| `set both FLORABASE_OWNER_LOGIN and FLORABASE_OWNER_PASSWORD, or neither` / `first owner refused` | Fix the owner variables and deploy again. |
| `pre-upgrade backup failed` / `backup directory ... is missing or not writable` | Fix the backup folder or free space and deploy again. Nothing was migrated. |
| `database revision ... is neither image head ... nor the previous release head` | The database comes from a newer, older or unknown release. Deploy the matching release or restore. |
| `differs from image head` (backend) | The schema does not match the backend image; `migrate` did not complete. Read its log. |

## Uninstalling without losing data

Stop or remove the stack; containers and networks hold no data. The data folder and the backup
folder stay as they are. Delete them only after verifying an off-host backup.

## Known limitations of this beta

- linux/amd64 only.
- Upgrades go from the exact previous release; skipping a release requires installing each one in
  turn or restoring a backup.
- The first owner password stays in the stack environment until you remove it.
- Current Docker Compose versions stop the previous backend before they start the new `migrate`, so
  no writer runs during the dump and upgrade (observed with Compose 5.7.1). With another manager or
  an older Compose, stop the stack before deploying a new release.
