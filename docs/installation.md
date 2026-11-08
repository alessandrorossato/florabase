# Installing Florabase (v0.1.0-beta.4)

This guide is for people who want to **run** Florabase on their own server from the published
container images. You do not need the source code, Node.js, a Python development environment or a
compiler. To build and deploy from a checkout, see [source-build deployment](deployment.md). For
local development, see the [development guide](development.md).

> **Beta status.** This guide names the assets for the private, single-owner
> `v0.1.0-beta.4` prerelease. Proceed only when its GitHub Release and verified assets are
> available. The beta.4 publication has not yet occurred. A Git tag or a workflow artifact alone
> does not provide an installable release. Keep a tested backup before every upgrade.

## What you install

| Part | Image | Role |
| --- | --- | --- |
| `frontend` | `ghcr.io/alessandrorossato/florabase-frontend` | nginx serving the built React app; forwards `/api/` to the backend; the only published port, on `127.0.0.1` |
| `backend` | `ghcr.io/alessandrorossato/florabase-backend` | FastAPI/Uvicorn API, owner authentication, media storage |
| `db` | `ghcr.io/alessandrorossato/florabase-postgres` | PostgreSQL 18.6: the official `postgres:18.6-alpine` image without its unused `gosu` tool, runs only as uid/gid 70; never published to the host |

All three images are pinned by immutable digest in one attested (build-provenance) release manifest,
so they can never be mixed across versions. The backend and frontend come from one source commit; the
PostgreSQL image keeps one identity across releases (it is built reproducibly once, then re-verified
by every release), so application upgrades never change the database image ([details](security/beta-distribution-001/postgresql-image.md)). A small
host program, `florabasectl.py` (Python standard library only), installs, migrates, backs up,
restores and upgrades the stack. Docker Compose runs the containers.

Download these four installation assets from the release:

| Asset | Purpose |
| --- | --- |
| `release-manifest.json` | Exact image digests, source commit, PostgreSQL identity and database schema version |
| `compose.yaml` | The stack definition (image-only; no builds, no source mounts) |
| `florabasectl.py` | The installation controller |
| `florabase.env.example` | Annotated list of every stack variable (for review; the controller writes the real file) |

## Quick start

### Prerequisites

- A **linux/amd64** host. linux/arm64 (for example a Raspberry Pi or an ARM NAS) is **not supported
  in this beta**: no arm64 images are built or tested.
- Docker Engine **24.0 or newer** and the Docker Compose plugin **2.20 or newer**
  (`docker compose version`). The image-only stack avoids the `!override` and `!reset` tags used in
  repository overlays. Disposable smoke tests exercised Engine 24.0.2 and Compose 2.20.1 in an
  isolated daemon. Acceptance on the candidate Synology DSM 7.2 host remains pending.
  [Beta runtime evidence](beta-runtime-001.md#disposable-verification)
- Python **3.8 or newer** on the host (`python3 --version`), for `florabasectl.py`.
- Bash, GitHub CLI **2.103.3 or newer** with access to the repository and release attestations,
  and `curl` for health checks. Downloads and verification may run on an admin workstation.
- A root shell on the host (`sudo -i`). The controller creates directories owned by the
  container users and protects the secret files.
- At least 2 GiB of available memory and 20 GiB of free disk for the application, database, media
  and several backups. Keep the database on a local disk (ext4, Btrfs, XFS), never a network share.
- An **HTTPS reverse proxy on the same host** (nginx, Caddy, Traefik, Tailscale Serve and so on).
  Florabase only accepts HTTPS in production and always serves on its own host name, never on a
  sub-path such as `https://example.org/florabase/`.

### 1. Download and verify the release

Open the tagged release under **Releases** in the trusted
[`alessandrorossato/florabase` repository](https://github.com/alessandrorossato/florabase/releases).
Use `gh auth login --hostname github.com` with an account that can read the repository and its
attestations. Sign in as the user running `gh`; a private release needs authenticated downloads.
GitHub access and GHCR pull access are separate.

Get the approved full source commit from the trusted release record and confirm it is the commit
the release tag points to. Set `authorized_commit` below before running the block.
Use the release record to establish the commit independently of the downloaded manifest.

Run the following as one Bash block. It creates a private directory under the working directory.
Run it outside the future installation root, for example from `/srv` on Linux or from a private
admin directory. Any download, attestation or digest failure stops the block.

```bash
(
  set -e
  umask 077
  tag=v0.1.0-beta.4
  authorized_commit='<approved-40-character-commit>'
  [[ "$authorized_commit" =~ ^[0-9a-f]{40}$ ]]
  repo=alessandrorossato/florabase
  bundle_dir=$(mktemp -d "$PWD/florabase-bundle.XXXXXX")
  files=(release-manifest.json compose.yaml florabasectl.py florabase.env.example)
  patterns=()

  for file in "${files[@]}"; do
    patterns+=(--pattern "$file")
  done
  gh release download "$tag" --repo "$repo" --dir "$bundle_dir" "${patterns[@]}"
  cd "$bundle_dir"

  for file in "${files[@]}"; do
    gh attestation verify "$file" --repo "$repo" \
      --signer-workflow "$repo/.github/workflows/beta-images.yml" \
      --source-ref refs/heads/main --source-digest "$authorized_commit" --deny-self-hosted-runners
  done

  python3 - "${tag#v}" "$authorized_commit" <<'PYTHON'
import hashlib
import json
import sys
from pathlib import Path

manifest_bytes = Path("release-manifest.json").read_bytes()
manifest = json.loads(manifest_bytes)
if manifest["version"] != sys.argv[1]:
    sys.exit("STOP: manifest version differs from the selected release tag")
if manifest["source"]["url"] != "https://github.com/alessandrorossato/florabase":
    sys.exit("STOP: manifest identifies a different source repository")
if manifest["source"]["revision"] != sys.argv[2]:
    sys.exit("STOP: manifest source differs from the approved release commit")
for name in ("compose.yaml", "florabasectl.py", "florabase.env.example"):
    digest = hashlib.sha256(Path(name).read_bytes()).hexdigest()
    if manifest["install_bundle"][name] != "sha256:" + digest:
        sys.exit("STOP: manifest SHA-256 mismatch for " + name)
print("Manifest SHA-256:", hashlib.sha256(manifest_bytes).hexdigest())
print("Source revision:", manifest["source"]["revision"])
PYTHON
  printf 'Verified bundle directory: %s\n' "$bundle_dir"
)
```

Attestation verification checks the downloaded bytes against provenance from the protected release
workflow. The SHA-256 checks also bind all three bundle files to the selected release's attested
manifest. Keep the printed manifest hash for install and upgrade. If verification ran on a
workstation, transfer the files over a trusted connection. Check `sha256sum release-manifest.json`
against the previously recorded hash and repeat the bundle digest checks on the host before
execution. Keep the verified files under a root-only directory on the host and change to that
directory before running the controller.
[GitHub CLI attestation verification](https://cli.github.com/manual/gh_attestation_verify) ·
[Florabase release identity policy](beta-image-001.md#manifest-contract-and-consumption)

Now run the verified controller's host preflight. It checks platform, tool versions and local
resources. Keep the resulting `preflight.json` private and resolve any failed checks before
initializing the installation.

```bash
python3 florabasectl.py --root /srv/florabase preflight --evidence preflight.json
```

If the GHCR packages require authentication, run `docker login ghcr.io` in the same root shell
that will run the controller. Use your GitHub username and a classic personal access token with
`read:packages` and access to the packages. Docker reads the token from the terminal.
[GitHub Container registry authentication](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry#authenticating-to-the-container-registry)

### 2. Initialize the installation

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

`init` refuses a non-empty root. It creates the host layout and secrets. The controller renders
the stack during `install` and creates restore directories as needed.

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

#### Configuration reference

The controller renders `stack/.env` from your `init` choices and the release manifest;
`florabase.env.example` documents each variable. Do not edit the rendered files by hand: upgrades
check the recorded configuration and refuse drifted files. `florabasectl.py apply` re-renders
and redeploys the recorded release.

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

### 3. Install the release

From the verified bundle directory, substitute the manifest hash printed in step 1.

```bash
python3 florabasectl.py --root /srv/florabase install \
  --manifest release-manifest.json --manifest-sha256 '<manifest-sha256>'
```

This pulls the three images by digest, verifies their labels, platform and schema version, starts
PostgreSQL, **creates the database schema explicitly** (the only migration that ever runs without
a backup, because the database is empty), starts the application and runs acceptance checks. A
second `install` against a non-empty database is refused. If the install is interrupted, re-run
the same command.

### 4. Create the owner account

Florabase has exactly one owner account and no default login. Create it once:

```bash
python3 florabasectl.py --root /srv/florabase bootstrap-owner '<login-name>'
```

The password (at least 12 characters) is prompted without echo, or read from standard input for
automation; it is never accepted as a command-line argument. A second owner is refused. There is no
password reset in this beta, so store the password in a password manager.

### 5. Put Florabase behind HTTPS and check readiness

Forward your HTTPS host name to `http://127.0.0.1:<http-port>` on the same host. The proxy must:

- terminate TLS for exactly the origin given to `init`, at the root path;
- pass the original `Host` header;
- allow request bodies of at least **32 MiB** (images up to 25 MiB plus form overhead);
- replace any forwarding headers sent by clients. Florabase does not derive its origin, scheme
  or user identity from `X-Forwarded-*` or `Forwarded` headers, but your proxy logs and rate
  limits might.

Minimal nginx server block. The disposable runtime smoke uses a similar TLS proxy and deliberately
injects hostile forwarding headers to check that Florabase ignores them.

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

Add HSTS, login rate limiting and certificate renewal in the proxy. Then accept the installation
through the configured HTTPS address, including an owner login and logout. For tailnet access,
follow [Tailscale and HTTPS](#tailscale-and-https) first and use its origin in these checks.

```bash
curl --fail --show-error https://florabase.example.org/api/v1/ready
python3 florabasectl.py --root /srv/florabase acceptance \
  --base-url https://florabase.example.org --owner '<login-name>'
```

Open that same HTTPS address in a browser and sign in as the owner. Production cookies use
`Secure`, and the API checks the configured origin for state-changing requests.

> **Docker Engine older than 28** may let other machines on the same local network reach ports
> published on `127.0.0.1`. On such hosts, confirm from another device that
> `http://<host-lan-address>:8080` is **not** reachable, and block the port in the host firewall
> if it is.

## Linux and VPS

Use the host's local, rootful Docker daemon. Run `sudo -i` before preflight and controller
operations. Docker socket access is equivalent to root access, so keep Docker group membership and
socket access restricted. Enable Docker at boot using the host's service manager. On systemd hosts
with the Docker Engine package, use `systemctl enable --now docker`.

Use `/srv/florabase` on a persistent local filesystem, with verified bundles in separate
`/srv/florabase-bundle.*` directories. Mount the filesystem before Docker starts if it is on a
separate disk. Keep the same absolute paths across reboots. Follow the [quick start](#quick-start)
for registry login, preflight, initialization and owner setup. Allow inbound HTTPS to the proxy
from the intended clients. Keep port 8080, PostgreSQL and the backend off the public network.

## Synology NAS

The DS224+ is an amd64 candidate with a DSM Container Manager package. Check the versions actually
installed on the NAS. Engine 24.0.2 and Compose 2.20.1 were exercised in a disposable Linux daemon.
Synology filesystem, boot and network behavior still require a real-host run.
[Synology Container Manager](https://www.synology.com/en-in/dsm/packages/ContainerManager)

1. Install Container Manager through DSM. From a trusted administration network, use SSH and
   `sudo -i` to run `uname -m`, `docker version`, `docker compose version` and
   `python3 --version`. If the package exposes standalone Compose, check `docker-compose version`;
   the controller can detect it. Substitute `docker-compose` in any direct Compose examples in
   this guide. Use verified Python 3.8 or newer and check preflight for memory,
   disk and cgroup support. Allow for DSM's own memory use.
2. Create a restricted DSM shared folder on a local Btrfs or ext4 volume. For example, use the
   `docker` share on `/volume1` and reserve `/volume1/docker/florabase` as the installation root.
   Keep the verified bundle in a separate root-only directory. Substitute the NAS root for
   `/srv/florabase` in every quick-start and maintenance command. Let `init` create the empty
   installation layout before importing anything into a management UI.
3. Keep `postgres/` and `media/` on that local volume. Check their numeric ownership and mode
   from the NAS shell after `init`. PostgreSQL needs `70:70` and media needs `10001:10001`,
   both mode `0700`. Check DSM ACLs before admitting users to the share. Avoid recursive ACL or
   ownership resets, and keep the database, media and secrets out of SMB or NFS exports.
4. Set up HTTPS on the NAS itself. Verify LAN peers cannot reach the raw loopback port and that the
   HTTPS route works from the intended clients. Confirm the share is mounted and Container
   Manager and the proxy are running after a planned reboot. Check readiness and open an uploaded
   image to verify persistence.
5. Use DSM Task Scheduler to run [controller backups](#backups-and-restores) as root. Verify and
   copy recovery sets off the NAS. For DSM backups or snapshots, copy completed recovery sets and
   protect the separate configuration backup. A snapshot of a running database directory alone
   does not capture the paired database and media recovery set.

## Tailscale and HTTPS

For private access, run Tailscale on the same host as Docker, enable MagicDNS and HTTPS
certificates, and choose the full device DNS name before `init`. For example, use
`https://<device>.<tailnet>.ts.net` as the canonical origin and use it consistently for
acceptance and browser login. Keep Funnel disabled and restrict access with the tailnet policy.
[Tailscale HTTPS setup](https://tailscale.com/docs/how-to/set-up-https-certificates)

```bash
tailscale serve --bg --https=443 http://127.0.0.1:8080
tailscale serve status
```

Confirm Serve prints the expected HTTPS origin and target. Test readiness, owner login and uploads
from a permitted tailnet client. Check raw LAN port isolation separately, and repeat after reboot.
Serve's background mode is designed to persist across restarts. Florabase acceptance on a real
Tailscale host, including certificate renewal and reboot, is pending.
[Tailscale Serve reference](https://tailscale.com/docs/reference/tailscale-cli/serve)

## Day-to-day operation

Containers restart automatically (`restart: unless-stopped`) after a crash, a Docker restart or a
reboot. Restarting **never** changes the database. From the stack directory you can use ordinary
Compose commands:

```bash
cd /srv/florabase/stack
docker compose ps
docker compose logs --tail=100 backend
```

Run `status` from the verified bundle before restarting services. Use controller recovery if it
reports an unfinished upgrade or restore.

```bash
python3 florabasectl.py --root /srv/florabase status --json
```

`status` summarizes health, the newest backup and any unfinished operation. It exits non-zero
when something needs attention, including when the first backup is still missing. Schedule it
hourly and `backup` nightly (cron or DSM Task Scheduler, as root, with failure notification).
Use absolute paths to the verified controller and installation root in scheduled tasks.

From `/srv/florabase/stack`, restart the app services when needed and check readiness once they
start. PostgreSQL keeps running.

```bash
cd /srv/florabase/stack
docker compose restart backend frontend
curl --fail --show-error http://127.0.0.1:8080/api/v1/ready
```

### Data and volumes

All persistent data lives in host directories under the root. The Compose volumes
(`florabase-prod_postgres_data`, `_attachment_data`, `_reference_data`) are only bind mounts onto
those directories: if a directory is missing the container refuses to start instead of creating an
empty database, and removing a Docker volume object never deletes the host data.

### Optional botanical reference datasets

Florabase runs without them. The WFO taxonomy index (`--kind wfo`) and the WCVP v16 index
(`--kind wcvp-v16`) are SQLite files that the backend reads directly, so **use only indexes built
by Florabase's own builders from the pinned official archives**. Never install an index you
downloaded or received from someone else: a crafted SQLite file can drive known SQLite
memory-safety bugs inside the backend process, which holds the database credentials.

Build each index with the backend image of the release you run (its digest is in
`release-manifest.json`), offline, from the archive named in
[collection-taxonomy.md](collection-taxonomy.md) or [native-range-enrichment.md](native-range-enrichment.md).
The builder verifies the archive's pinned SHA-256 before reading it:

```bash
backend='ghcr.io/alessandrorossato/florabase-backend@sha256:<backend-index-digest>'
mkdir -m 0700 /srv/florabase-build && chown 10001:10001 /srv/florabase-build
docker run --rm --network none --read-only --tmpfs /tmp --user 10001:10001 \
  -v /path/to/wfo_plantlist_2026-06.zip:/in/archive.zip:ro -v /srv/florabase-build:/out \
  "$backend" python -m florabase.taxonomy.snapshot /in/archive.zip /out/wfo-2026-06.sqlite \
  --retrieved-at '<archive-retrieval-time-in-UTC>'
install -m 0644 /srv/florabase-build/wfo-2026-06.sqlite /srv/florabase-build/wfo-2026-06.sha256 \
  /srv/florabase/reference/
# The digest the builder recorded at build time (the WFO seal), not one computed from the copy.
python3 florabasectl.py --root /srv/florabase reference set --kind wfo \
  --file wfo-2026-06.sqlite --sha256 "$(cat /srv/florabase-build/wfo-2026-06.sha256)" \
  --provenance "florabase.taxonomy.snapshot from the pinned WFO 2026-06 archive"
```

For WCVP v16, run `python -m florabase.native_range_enrichment.snapshot /out/wcvp-v16.sqlite
--version 16 --archive /in/archive.zip --retrieved-at …` the same way. That builder writes no seal,
so record `sha256sum /srv/florabase-build/wcvp-v16.sqlite` right after the build, then pass that
value to `reference set --kind wcvp-v16`.

The SHA-256 you pass to `reference set` (and the WFO `.sha256` seal next to the index) proves
only that the file was not changed after you built it. It says nothing about who built the file,
so it does not make an index from another source safe. Provenance comes from building the index
yourself, as above.

As an additional safeguard, the backend refuses any index whose SQLite schema differs from the
exact layout the builder writes, including views, triggers, virtual tables and extra or altered
tables and indexes. It checks this before it runs any query. Each connection is read-only, with
views, triggers, extension loading and untrusted schema functions disabled. A refused index shows
as the source being unavailable in the app, and the backend log names the unexpected objects.
Rebuild such an index with the builder; do not edit it.

## Database migrations and upgrades

Florabase **never migrates the database on `docker compose up`, a restart or an image update.**
Before the server starts, the backend checks that the database is exactly at the schema version of
its release and refuses otherwise, with a message that names the action to take (see
[Troubleshooting](#troubleshooting)). A newer image therefore cannot silently change your data.

Download and verify the new release's files into a new directory exactly as in
[step 1](#1-download-and-verify-the-release), setting `tag` to the target version. Change to the
new verified bundle directory and substitute the new manifest hash.

```bash
python3 florabasectl.py --root /srv/florabase promote \
  --manifest release-manifest.json --manifest-sha256 '<manifest-sha256>' \
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

Check `status` for the recorded operation and phase. A promotion failure after the controller
starts the operation attempts to stop writers and reports the recovery choices:

| Situation | Command |
| --- | --- |
| Interrupted (killed, reboot) | `resume` continues from the recorded phase |
| Failed before the schema changed | `abort` returns to the previous release |
| Migrated, but the new application fails | `abort` is refused; `promote --after-failed` with a fixed release, or `restore-replace <pre-upgrade set>` |

Run `python3 florabasectl.py --root /srv/florabase resume` only for an in-progress operation.
Keep the target's verified bundle and image access available until acceptance succeeds.
If the controller reports a failed operation, use `abort` only when the database is still at the
previous release head. For a forward fix, use the normal `promote` command with the fixed verified
bundle and add `--after-failed`. To recover data from the pre-upgrade set, use the confirmations in
[replacement restore](#replace-live-data). Keep the HTTPS route unavailable to users while resolving
an interruption if the state of the application is uncertain.

Never run the `migrate` service by hand on a live installation, and never "downgrade" by pinning
older images: an older backend refuses a newer schema.

### PostgreSQL versions

The beta uses **PostgreSQL 18.6** in the Florabase PostgreSQL image (`18.6-alpine-florabase.1`,
pinned by digest). Application upgrades never change the PostgreSQL image; `promote` refuses a release
whose PostgreSQL identity differs. A new Florabase PostgreSQL version (an upstream rebuild, a security
fix or a minor update) is separate, explicitly announced maintenance with its own backup. The image
runs only as the `postgres` account (uid/gid 70): starting it as root stops immediately with
`florabase-postgres: refusing to run as root`, before anything on disk changes. This holds for the
image's own entry point and for the upstream `docker-entrypoint.sh` and `docker-ensure-initdb.sh`
when they are used as an overridden entry point. A **major** version change
(for example to 19) cannot reuse the data directory: it needs a new installation restored from a
logical backup, and it is not automated in this beta. PostgreSQL itself refuses to start on a data
directory from another major version, so a wrong image fails instead of corrupting data. A database
created by PostgreSQL 18 cannot be opened by an older major version.

## Backups and restores

A **recovery set** pairs the PostgreSQL dump with the archive of every original image, the stack
document, table counts and checksums. Database and media are always taken together, with the
application stopped while the set is created so both describe the same moment. Allow a maintenance
window that scales with the amount of data.

```bash
python3 florabasectl.py --root /srv/florabase backup          # prints BACKUP_COMPLETE <set-id>
python3 florabasectl.py --root /srv/florabase verify-backup '<set-id>'
python3 florabasectl.py --root /srv/florabase list-backups
python3 florabasectl.py --root /srv/florabase retention         # dry run; add --apply
```

Copy sets off the host. The controller can store a set in an encrypted
[restic](https://restic.net/) repository, check it, restore it to scratch space and verify every
checksum before reporting success:

```bash
python3 florabasectl.py --root /srv/florabase export '<set-id>' \
  --repository '<restic-repository>' --password-file /root/restic-password
```

Add `--init` only when creating a new restic repository. Keep the restic password file root-only.
For a remote repository that needs credentials, use a separate root-only `--restic-env-file`.
Check retention with the dry run before using `retention --apply`, which deletes expired local sets.

Keep separate protected copies of `secrets/`, `state/installation.json`, the restic password and
credentials, the proxy configuration, and the verified bundles and hashes needed to access the
backup's release. Record the canonical origin and any optional reference dataset configuration.

**Test a restore without touching live data** (recommended after the first backup and regularly):

```bash
python3 florabasectl.py --root /srv/florabase restore-isolated '<set-id>' --http-port 18081 --owner '<login>'
python3 florabasectl.py --root /srv/florabase restore-remove --project '<printed-name>' --confirm '<printed-name>'
```

The drill restores into a separate project on another loopback port, compares the schema version
and every table count, verifies every original image and logs in. Keep the drill port private.
`restore-remove` deletes the named drill project and its restored copy.

### Replace live data

Replacement discards active writes made after the recovery point. Take the installation out of
service, verify the selected set and check free space for both the old and restored copies. Use
the installation ID printed by `status` and the database name shown below.

```bash
python3 florabasectl.py --root /srv/florabase restore-replace '<set-id>' \
  --confirm-installation '<installation-id>' --confirm-database florabase
```

The current `postgres/` and `media/` directories are moved to `preserved/<time>/`, not deleted, so
writes made after the set can still be inspected. All sessions are signed out. Check readiness and
sign in again before returning the installation to service. If a replacement restore is interrupted,
preserve its marker, logs, recovery set and the directories under `preserved/`. Keep the proxy
route closed, check available space and re-run `restore-replace` for the same verified set.
`resume` is for interrupted promotions.

### Fresh-host disaster recovery

1. Prepare a clean host and private proxy route. Follow the [quick start](#quick-start) to verify the
   bundle for the release in the recovery set and pull its images. Run `init` using the original
   canonical origin and `install` using that bundle's manifest. Use the new root and new
   installation ID. Let `init` generate fresh database credentials. The logical restore brings
   back the saved owner, so skip `bootstrap-owner`.
2. Import the selected set from restic, or copy an off-host copy of the complete set directory into
   the new root's `backups/`. Keep it root-only, and verify it before replacement.

   ```bash
   python3 florabasectl.py --root /srv/florabase import-set '<set-id>' \
     --repository '<restic-repository>' --password-file /root/restic-password
   python3 florabasectl.py --root /srv/florabase verify-backup '<set-id>'
   ```

3. Run [replacement restore](#replace-live-data) with the new installation ID. Restore optional
   reference files and register them with the controller as needed. Check readiness, sign in with
   the recovered owner credentials, and open a restored image before routing users to the new host.

## Managing Florabase with Dockhand

Dockhand can show, start, stop, restart and inspect the stack's logs.
Installation, upgrades, migrations, backups and restores stay in `florabasectl.py` on the host,
because they must quiesce writers and take a verified backup first.

1. Install Florabase with `init`, `install` and `bootstrap-owner` as above.
2. Select the Docker environment that already runs `florabase-prod`. Use **Stacks → Import**
   only if Dockhand can adopt the existing project with its original `stack/compose.yaml` and
   `stack/.env` in place. Preserve the project name and host paths. The Compose runner must see
   `reference.env` next to the stack and the controller's secret files at their original absolute
   paths. If Dockhand needs to copy the stack or store the secrets in its own settings, use it for
   inspection only.
3. Disable automatic container updates in that environment. The Florabase services also carry
   the `dockhand.update=false` label. Leave Git sync, update hooks and stack editing disabled.
4. Use Dockhand for logs and routine lifecycle actions on the existing containers. During an
   unfinished controller operation, leave lifecycle actions to the controller. Run `promote`
   on the host for every upgrade. For release notifications, run `check-release` with the
   verified newer manifest and its `--manifest-sha256`.

Protect Dockhand itself: enable its authentication, never expose it publicly and back up its data
directory including its encryption key. Import behavior, lifecycle actions and update exclusions
still need to be checked on the selected Dockhand version. Promotion, backup and recovery are
controller procedures. [Dockhand manual](https://dockhand.pro/manual/)

## Troubleshooting

| Symptom (backend log or command output) | Cause and action |
| --- | --- |
| `schema-guard: invalid configuration (ValidationError) …` | A setting is missing or invalid; the message names the field (values are never printed). Fix the installation with `florabasectl.py apply`; a hand-edited `.env` is the usual cause |
| `… database revision unavailable …` | Check `docker compose ps db`, `docker compose logs db` and the protected credentials. Use `status` before restarting services in case an operation is pending |
| `… not release head … (the database is not initialized …)` | Use `install` for a new installation or to retry the same interrupted install. For an existing installation, investigate the mounted database path and recover from the verified set if needed |
| `… (a migration is pending …)` | Images are newer than the database. Use `promote`, which backs up and migrates; never run `migrate` by hand |
| `… (the database is newer than or foreign to this image …)` | An older or unrelated image was pinned. Run `florabasectl.py apply` to restore the recorded release, or restore a recovery set |
| `Failed to load …/secrets/backend.env: … no such file or directory` from Compose | The secrets directory is missing or unreadable; Compose changes nothing. Restore `secrets/` from your configuration backup |
| Login fails with HTTP 403 | The browser address differs from `--origin`, or the proxy changes the `Origin`/`Host`. Open exactly the configured origin |
| Uploads fail with HTTP 413 | The reverse proxy's body limit is below 32 MiB |
| `florabase-postgres: refusing to run as root` | The database container was started as root (for example `user: root` in an edited Compose file, or `docker run --user 0`). Use the release `compose.yaml`, which runs it as `70:70` |
| `Refusing WFO reference index …` / `Refusing WCVP reference index …` | The reference file is not an index built by Florabase's builder (unexpected or missing schema objects). Rebuild it as described under [optional botanical reference datasets](#optional-botanical-reference-datasets), then `reference set` it again |
| `status` reports an old backup or low disk | Check the scheduled `backup`, free space under the root, and `retention --apply` |

Readiness is `GET /api/v1/ready` through the frontend; liveness is `/healthz`. With PostgreSQL
stopped or hung, readiness answers 503 within a few seconds (connection attempts are bounded to 3 s;
name resolution adds the resolver's timeout) while `/healthz` stays live, and the backend
healthcheck reports unhealthy.

## Uninstalling without losing data

Stopping and removing containers never removes data:

```bash
cd /srv/florabase/stack
docker compose down          # containers and network only
```

Omit `--volumes` and retain the host directories. For permanent removal, take and verify a final
`backup` before stopping the stack, then copy the set off the host. Deleting the installation root
destroys the live database, media, secrets and local backups.

## What has been tested

| Evidence | Scope |
| --- | --- |
| Static procedure checks | Controller arguments, Compose paths and port bindings, and release asset and provenance expectations checked against the repository |
| Disposable runtime | Local candidate smoke on Engine 24.0.2, Compose 2.20.1 and Python 3.8 covered install, migrations, HTTPS via nginx, backup, restore and upgrade interruption. See the [runtime runbook](beta-runtime-001.md#disposable-verification) and [distribution evidence](beta-distribution-001-evidence.json) |
| Published release | End-to-end asset download and verification, GHCR pulls and installation of the published beta remain pending successful publication |
| Real hosts | Synology permissions and reboot, Dockhand import and lifecycle behavior, Tailscale TLS and reboot, network isolation, and off-host recovery on the selected host remain pending |

## Known limitations of this beta

- linux/amd64 only; arm64 is not built or tested.
- One owner account; no password change or reset, no additional users.
- The HTTPS origin and loopback-only publication are fixed at `init`; a reverse proxy on another
  machine is not supported.
- PostgreSQL major upgrades and automatic application promotion are not provided.
- Optional online map tiles (`runtime-config.js`) are not configurable in this stack.

Operator and developer background: [beta runtime runbook](beta-runtime-001.md),
[image release contract](beta-image-001.md), [security](security.md).
