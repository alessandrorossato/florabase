# Install Florabase with portable Docker Compose

No published release includes `portable-compose.yaml` yet: the last published prerelease,
`v0.1.0-beta.5`, ships the controller bundle and no `portable-compose.yaml`. Download
`portable-compose.yaml` and `release-manifest.json` from the first later release that lists both
assets. The Compose file pins three
linux/amd64 images by digest and runs PostgreSQL, the API, and the frontend. Docker Compose 2.20+ on Engine 24+ is the baseline.
Use a Compose manager that supports Compose environment interpolation, long-form bind mounts,
health dependencies, and host-IP port bindings. Use Docker CLI access on the same host and
daemon for the occasional maintenance commands below.
[Florabase releases](https://github.com/alessandrorossato/florabase/releases)

## Prerequisites

This is the official installation of Florabase. Building from source is for development, and the
controller bundle is an advanced, best-effort alternative.

- A linux/amd64 Docker host with Engine 24+ and Compose 2.20+, shell access and local storage for
  the two data directories. Other architectures are not built.
- A hostname dedicated to Florabase and an HTTPS reverse proxy on the Docker host with a
  certificate for it. Florabase is served at the root of that origin, not under a subpath.
- An admin workstation with the GitHub CLI (`gh`) to verify the release assets.
- Pull access to the release's GHCR images from the Docker host.
- Private storage, off the host, for backups and for the credentials needed to restore them.

## Download and verify the release assets

On an admin workstation, verify both downloaded files against the protected release workflow and
the full approved source SHA from the release record. Keep the verified file with its release
manifest for upgrades and recovery. Configure GHCR pull access on the deployment host if required.

```bash
repo=alessandrorossato/florabase
(
  set -e
  for file in portable-compose.yaml release-manifest.json; do
    gh attestation verify "$file" --repo "$repo" \
      --signer-workflow "$repo/.github/workflows/beta-images.yml" \
      --source-ref refs/heads/main --source-digest '<approved-40-character-commit>' \
      --deny-self-hosted-runners
  done
)
```

## Configure

Create two dedicated, empty directories on local storage on the Docker host. These are examples.
NAS shared-folder ACLs and user-namespace mappings must allow the indicated container users to
traverse and write the respective directories. Check existing storage separately before switching
an established installation.

```bash
sudo mkdir -p /srv/florabase
sudo mkdir -m 0700 /srv/florabase/postgres /srv/florabase/media
sudo chown 70:70 /srv/florabase/postgres
sudo chown 10001:10001 /srv/florabase/media
```

Set these five variables in a mode-0600 `.env` next to `portable-compose.yaml`, or in the manager's
stack environment. For maintenance, use the same values through `.env` and the same Compose project
name that the manager uses. Keep the password file and Docker access private. Generate a
strong password with `openssl rand -hex 32`.

```dotenv
FLORABASE_POSTGRES_DIR=/srv/florabase/postgres
FLORABASE_MEDIA_DIR=/srv/florabase/media
FLORABASE_DB_PASSWORD=<generated-hex-password>
FLORABASE_CANONICAL_ORIGIN=https://florabase.example.org
FLORABASE_HTTP_PORT=8080
```

Terminate TLS at a reverse proxy on the Docker host. Route the entire hostname to
`http://127.0.0.1:8080` (or your configured port). Use the exact HTTPS origin without a trailing
slash or subpath. Only the frontend publishes a port. On Engine versions older than 28, check from
a separate LAN host that the loopback port is unreachable and enforce this at the host firewall.
PostgreSQL stays on an isolated bridge with the backend. A separate application bridge carries
frontend traffic and allows the backend to reach external providers.

### Reverse proxy example

The bundled frontend sends no security headers and applies no rate limit; the HTTPS proxy owns
both. This nginx server block is an example for the values above. Adapt the certificate paths and
translate it for another proxy.

```nginx
server {
    listen 443 ssl;
    server_name florabase.example.org;
    ssl_certificate     /etc/ssl/florabase/fullchain.pem;
    ssl_certificate_key /etc/ssl/florabase/privkey.pem;

    client_max_body_size 32m;

    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header X-Frame-Options "DENY" always;
    add_header Content-Security-Policy "default-src 'self'; img-src 'self' data: blob: https:; style-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'" always;
    # Add only after HTTPS works for every client of this hostname:
    # add_header Strict-Transport-Security "max-age=31536000" always;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

`img-src https:` permits external photo references, and online map tiles if they are enabled.
The content policy is a
starting point and has not been checked on every page: deploy it first as
`Content-Security-Policy-Report-Only`, use the application, and enforce it once the browser
console reports no violation. Florabase never reads its origin or the user's identity from
forwarded headers. Add a source-address request limit for `/api/v1/auth/` if the proxy is
reachable from untrusted networks; the application's own sign-in backoff is keyed by login name,
not by source address.

For the examples below, run from the directory with the verified file and private `.env` in a
Bash shell. Set `project` to the exact name of the deployed stack and use a distinct name for each
installation. Keep maintenance serialized with manager actions and disable automatic updates and
redeployments.

```bash
project=florabase
dc() { docker compose --project-name "$project" --file portable-compose.yaml "$@"; }
init_db() {
  dc stop db &&
    dc run --rm --no-deps -T -e POSTGRES_INITDB_ARGS=--auth=scram-sha-256 \
      --entrypoint sh db -ec '
        entries=$(ls -A /var/lib/postgresql)
        if [ -n "$entries" ]; then
          echo "PostgreSQL bind directory is not empty" >&2
          exit 1
        fi
        exec docker-ensure-initdb.sh
      ' &&
    dc up -d --wait db
}
```

## First install

Run this block on a fresh installation. The cluster initialization stops any normal database
container first and refuses a nonempty PostgreSQL bind directory. A regular deployment or
restart fails if the selected path has no cluster. If a first install was interrupted, inspect
the state and resume from the first incomplete step. Keep existing data while diagnosing the
failure.

```bash
(
  set -e
  init_db
  dc run --rm --no-deps -T backend python -m florabase.db.release_schema init
  dc run --rm --no-deps backend python -m florabase.auth.bootstrap owner
)
```

The owner command prompts for a separate password. Then deploy the full Compose project in your
manager, or run `dc up -d --wait`. Sign in at the HTTPS origin. Check `dc ps` and
`dc logs db backend` if services are unhealthy. An unknown, older or newer Alembic revision
prevents API startup. Existing installations use the upgrade or restore procedure.

## Recover a forgotten owner password

Use a trusted, unrecorded terminal on the deployment host. From the verified portable release
directory, confirm that `dc` selects the deployed project and that its existing PostgreSQL is
healthy. Pause automatic redeploys and resolve any interrupted upgrade or restore. Leave that DB
running and stop the two application services:

```bash
dc stop frontend backend
dc run --rm --no-deps backend python -m florabase.auth.reset_password '<login-name>'
```

Check the target shown in the prompt and enter the new password twice. The command requires the
installed image's Alembic revision and one enabled matching owner. It commits the new password,
revokes all sessions and clears both login and password-change backoff together. It never starts
the app or migrates the database. After confirmed success, run `dc up -d --wait` and sign in at the
configured HTTPS address. If the command reports an unconfirmed outcome, verify the credential
before reopening access, or reset again with a fresh password. If you restore an older backup,
run the reset before exposing the app because the backup can contain old credentials and sessions.

Automation can use `-T` on the Compose run and `--password-json-stdin` on the module. Feed exactly
one UTF-8 JSON string from a protected pipe (maximum 16 KiB). Keep the password out of command
arguments, environment variables, files and terminal recordings. At the HTTPS proxy, omit query
strings, request headers and request bodies from auth logs, including diagnostic logs.

## Paired backup

Use a fresh private backup directory on a different path from the two binds. Take the database and
original media together while all application writers are stopped. Run this as a block and only
resume service after it succeeds. Keep encrypted off-host copies of the whole set, the release
attestation/manifest, and the configuration and credentials required for recovery. Save the
credentials separately in your secret store.

```bash
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
  cp portable-compose.yaml release-manifest.json "$backup/"
  cd "$backup"
  sha256sum database.dump media.tar portable-compose.yaml release-manifest.json > SHA256SUMS
)
```

For a routine backup, run `dc up -d --wait` only after the block succeeds. For an upgrade, leave
writers stopped. Treat a partially written backup directory as incomplete. Checksum verification and a full restore
drill are part of validating a backup.

## Upgrade

1. Review the new release notes, verify its Compose asset and manifest, and confirm the PostgreSQL
   digest is identical to the current release. PostgreSQL major-version changes require their own
   documented migration. Keep the same project, binds, password and origin.
2. Pull the new images and take a successful paired backup using the **old** file and manifest.
   Keep the frontend and backend stopped. Record the old manifest's `alembic_head`.
3. Replace the Compose file with the verified new file. Keep the existing database running.
   Explicitly apply the new backend image's upgrade command with the old release head.

   ```bash
   previous_head='<old release manifest alembic_head>'
   dc run --rm --no-deps -T backend python -m florabase.db.release_schema upgrade "$previous_head"
   ```

4. Only after success, deploy the new stack and check HTTPS login, readiness and original media.
   Same-schema upgrades also work with the explicit command.

On failure, keep application writers stopped and preserve both binds and the paired backup.
Inspect the reported failure and database revision. The command accepts only the named previous
revision in the new image's history, and runs the pending migrations in a PostgreSQL transaction.
For an interrupted run, establish the actual revision before retrying. If the schema already
reached the target head, verify the new release and complete deployment. To revert after a
successful schema change, restore the pre-upgrade set into fresh paths with the previous release
and validate it before switching traffic.

## Isolated restore

Use the backed-up Compose and release manifest after validating the checksums
(`sha256sum -c SHA256SUMS` from the backup directory). Verify their provenance as you would for
first install. Use a different project, different empty bind paths with the specified owners, a
different frontend port, and a private test HTTPS origin. Keep this instance away from normal
traffic. Set up a separate working directory with the backed-up Compose file and the restore
project’s private `.env`. Change to that directory and set `project` before using `dc`.

Run the whole block below. It creates the PostgreSQL cluster and stops on any failure, including
a refusal to initialize a nonempty directory. It restores the dump into the fresh database and
the archive into the fresh media path.

```bash
(
  set -e
  init_db
  dc exec -T db sh -ec '
    export PGPASSWORD="$POSTGRES_PASSWORD"
    exec pg_restore --single-transaction --exit-on-error --no-owner --no-privileges \
      -U "$POSTGRES_USER" -d "$POSTGRES_DB"
  ' < "$backup/database.dump"
  dc run --rm --no-deps -T backend sh -ec '
    entries=$(ls -A "$FLORABASE_ATTACHMENT_STORAGE_ROOT")
    if [ -n "$entries" ]; then
      echo "Media bind directory is not empty" >&2
      exit 1
    fi
    exec python /app/scripts/attachment_artifacts.py restore
  ' < "$backup/media.tar"
  dc run --rm --no-deps -T backend python /app/scripts/attachment_artifacts.py verify
  dc up -d --wait
)
```

The dump supplies the Alembic revision and owner account. Verify HTTPS login with that owner and
retrieve representative originals. Stop the isolated project after the drill. For a real recovery,
switch the reverse proxy only after validation and preserve the original data and backup.

## Troubleshooting

Start with `dc ps` and `dc logs db backend frontend`. Keep both bind directories and any backup
untouched while diagnosing.

**Wrong origin.** `FLORABASE_CANONICAL_ORIGIN` must equal the address in the browser exactly:
`https`, the hostname, a port only if the browser shows one, and no path. Write an
internationalized hostname in its `xn--` form.

- If the variable is unset or empty, Compose refuses to start anything and prints
  `Set FLORABASE_CANONICAL_ORIGIN`.
- If the value is not an HTTPS origin or contains a path, the backend does not start and its log
  shows `schema-guard: serve failed (ValidationError)`.
- If the value is well formed and differs from the address in use, the page loads, sign-in shows
  "Florabase could not reach the authentication service", and `dc logs frontend` shows
  `POST /api/v1/auth/login 403`. The same happens when the application is opened directly on
  the published port instead of through the HTTPS proxy.

Correct the value in `.env` or the manager's stack environment and run `dc up -d --wait`.

**Schema revision mismatch.** The backend log shows
`schema-guard: database revision ... differs from image head ...` and the API does not start.
Compare the printed revision with the `alembic_head` of the previous and the current release
manifest.

- `empty` on a new installation: the schema was not initialized. Run the
  [first install](#first-install) block from the first incomplete step.
- The previous release's head: the explicit [upgrade](#upgrade) command was not run. Stop
  `frontend` and `backend`, take the paired backup with the old file if it is missing, and run
  step 3.
- A revision in neither manifest: the database is newer than these images. Deploy the Compose
  file of the release that wrote it, or [restore](#isolated-restore) the matching backup.

Never edit the `alembic_version` table to make the check pass.

**Unhealthy container.** `backend` starts only after `db` is healthy, and `frontend` only after
`backend`. Check `db` first, then `backend`, then `frontend`.

- `db` keeps restarting and its log says `Run initdb`: the PostgreSQL directory has no cluster.
  On a new installation run the [first install](#first-install) block. Otherwise check that
  the path is the one that holds your data, and its permissions below. A regular start never
  creates a cluster.
- `backend` restarts with `schema-guard: serve failed (ValidationError)`: the configuration is
  invalid. Check the origin above.
- `backend` restarts with `schema-guard: serve failed (OperationalError...)`: the database
  refused the connection. Check that `FLORABASE_DB_PASSWORD` is the password the cluster was
  initialized with. Changing the variable does not change the database's password, so restore
  the original value.
- `backend` restarts with a revision message: see the schema case above.
- `backend` keeps restarting with no `schema-guard` line and its log shows a failed application
  startup: check the media directory's owner below.

**Bind-mount permissions.** The containers run without root and cannot repair ownership. Both
directories must exist before the stack starts; Compose does not create them and fails at
start with a `bind source path does not exist` error when one is missing. If the media
directory is not readable, writable and traversable by `10001`, the backend stops during
startup and keeps restarting, and `frontend` never starts.

```bash
ls -ldn /srv/florabase/postgres /srv/florabase/media   # use the two paths from your .env
```

The PostgreSQL directory should be owned by `70:70` with mode `0700`, and the media directory by
`10001:10001`. Reapply the `chown` commands from [Configure](#configure). On a NAS, shared-folder
ACLs and user-namespace remapping can override these owners; give those numeric users traverse
and write access to the two directories and their parents.

**Lost owner password.** Follow
[Recover a forgotten owner password](#recover-a-forgotten-owner-password).

The [controller-based guide](installation.md) covers the advanced bundle, including journaled
operations and additional recovery tooling. To move from a controller installation to the portable
stack, use a verified paired logical dump and media archive with the isolated restore procedure.
Use a portable release compatible with the backup's schema and PostgreSQL version, and validate it
before moving traffic.
