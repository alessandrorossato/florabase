# BETA-RUNTIME-001 — image-only beta runtime and recovery runbook

This increment delivers the versioned distribution stack, a host controller and disposable proof
that install, persistence, recovery and upgrade work on the Synology DSM 7.2 Container Manager software
baseline (Engine 24.0.2, Compose 2.20.1, Python 3.8). It
does **not** deploy to Synology or any persistent host, approve a host, publish images or admit real
collection use. Real-host installation stays an explicit operator action (see
[Outstanding operator evidence](#outstanding-operator-evidence)). The contract it implements is the
[foundation runtime contract](beta-foundation-001.md#smallest-beta-deployment-architecture).

## What ships

| Path | Purpose |
| --- | --- |
| `deploy/beta/compose.yaml` | Stack format 1: image-only, project `florabase-prod`, no build/source binds, only frontend on loopback |
| `deploy/beta/florabasectl.py` | Host controller; Python ≥ 3.8 standard library only (DSM 7.2 ships 3.8) |
| `scripts/test-beta-runtime.py` | Offline stack contract + controller safety rules (host Python and Python 3.8) |
| `scripts/smoke-beta-runtime.py` | Disposable Engine 24.0.2 + Compose 2.20.1 drills; `scripts/smoke_beta_runtime_client.py` is its HTTP client |

`make test-beta-runtime` runs the offline suite (also part of `make workflow-check`);
`make smoke-beta-runtime` runs the disposable drills. The two bundle files are the release
artifacts an operator copies to the host; no checkout, Git or package installation is needed there.

## Stack design

- **Pinned images.** `.env` carries the backend/frontend digest pair from one release manifest and
  the PostgreSQL digest recorded at install. Missing pins, secrets directory or data paths fail
  `docker compose config` instead of falling back to defaults.
- **Startup never migrates.** `schema-gate` (one-shot, backend image) compares the database Alembic
  revision with the image head and refuses otherwise; `backend` depends on its success, `frontend` on
  backend health. `migrate` and `tools` exist only in the `maintenance` profile and are run by the
  controller. A Dockhand redeploy or manual `docker compose up -d` therefore cannot migrate, and
  cannot start an image whose schema differs from the database.
- **Durable identities.** Named volumes `florabase-prod_postgres_data`, `_attachment_data` and
  `_reference_data` are local-driver *bind* volumes onto host directories. A missing directory stops
  the container instead of creating an empty database; removing the Docker volume object never
  deletes host data. The controller refuses any existing project volume that is plain or bound
  elsewhere (for example one left by the source-build `compose.yaml`, which shares the project name).
- **Private exposure.** Only frontend publishes, on `127.0.0.1:${FLORABASE_HTTP_PORT}` for host
  Tailscale Serve. Database and backend have no ports. CORS is empty, cookies secure, origin exact.
- **Hardening and bounds.** All containers are read-only with tmpfs scratch, `cap_drop: ALL`,
  `no-new-privileges`, memory and PID limits; PostgreSQL runs as 70:70, backend as 10001, nginx
  as 101. Memory ceilings (PostgreSQL 1 GiB, backend 768 MiB, frontend 128 MiB, one-shot tasks
  512 MiB) are limits, not reservations; on a host with only 2 GB of RAM lower them with `init --db-memory`/
  `--backend-memory` and measure real use first. JSON logs rotate at 10 MiB × 5 per container. CPU limits default to unlimited (`0`)
  because Synology kernels may lack CFS quota; set them only where `preflight` reports support.
- **Update exclusion.** `dockhand.update=false` is on every service; the controller verifies it on
  the running db/backend/frontend containers during acceptance.
- **Optional datasets.** WFO/WCVP snapshots are mounted read-only from `reference/` and configured
  only when recorded (`reference.env`); an empty setting would otherwise parse as the current
  directory.

## Host layout

`init` creates one root at a path you choose with `--root`; nothing is hardcoded. Examples in this
runbook use `/volume1/docker/florabase` (a typical Synology share) or `/srv/florabase`:

| Directory | Owner / mode | Content |
| --- | --- | --- |
| `stack/` | root 0750 | `compose.yaml`, rendered `.env` and `reference.env` (Dockhand imports this directory in place) |
| `secrets/` | root 0700 | `db.env`, `backend.env` (generated, 0600; never in Git, labels, logs or arguments) |
| `postgres/` | 70:70 0700 | Live PGDATA; keep on local Btrfs/ext4, never a network share |
| `media/` | 10001:10001 0700 | Originals (thumbnails regenerate) |
| `reference/` | root 0755 | Optional read-only WFO/WCVP indexes |
| `backups/` | root 0700 | Recovery sets |
| `state/` | root 0700 | `installation.json`, `current.json`, operation, journal, lock, stack documents |
| `restore/`, `preserved/` | root 0700 | Isolated drills; data set aside by a replacement restore |

The stack files are rendered from `state/` and checked byte-for-byte before every promotion. An
edit made in Dockhand or by hand is refused as drift rather than becoming a second source of truth;
`apply` re-renders the recorded configuration.

## Installation (operator)

Run everything as root on the host (`sudo -i` on DSM). Replace the example paths and hostname.

1. **Qualify the host.** Copy `compose.yaml` and `florabasectl.py` to, for example,
   `/volume1/docker/florabase-bundle/`. Then run
   `python3 florabasectl.py --root /volume1/docker/florabase preflight --evidence preflight.json`.
   It records kernel, Engine/Compose/Python versions, cgroup memory/PID/CPU support, Docker
   warnings, available memory, free disk, filesystem and uptime. Engine ≥ 24.0, Compose ≥ 2.20,
   Python ≥ 3.8, linux/amd64 and memory/PID cgroups are mandatory. Capacity thresholds (2 GiB
   available memory, 20 GiB free) are screening budgets. The raw `preflight.json` describes your host
   (kernel, capacity, filesystem, uptime): keep it on the host. Only the sanitized fields required by the
   [image runbook](beta-image-001.md#platform-screening-and-publication-prerequisite) belong in Git.
2. **Authorize the release.** Obtain `release-manifest.json` and its SHA-256 from the authorized
   release record. Verify its attestation exactly as in the
   [manifest consumption](beta-image-001.md#manifest-contract-and-consumption) section. The
   controller requires `--manifest-sha256` and re-validates the manifest, OCI labels, platform
   digests and Alembic head after pulling. It never uses tags.
3. **Initialize.** Run
   `python3 florabasectl.py --root /volume1/docker/florabase init --origin https://<node>.<tailnet>.ts.net`.
   This creates the layout, random database credentials and an installation ID. It refuses a
   non-empty root, so it never adopts data. Use `--http-port` if 8080 is taken.
4. **Install.** Run `... install --manifest release-manifest.json --manifest-sha256 <sha256>`.
   This pulls by digest, starts PostgreSQL, migrates the *empty* database explicitly, starts the
   application through the gate and runs acceptance. An interrupted install of the same manifest can
   be re-run; any other non-empty database is refused.
5. **Create the owner.** Run `... bootstrap-owner <login>`; the password is read from the terminal or
   stdin, never from arguments.
6. **Expose privately.** Install the Tailscale DSM package, keep Funnel off, restrict tailnet ACLs to
   the approved users/devices and run `tailscale serve --bg --https=443 http://127.0.0.1:8080`.
   Avoid sensitive node names: certificates are published in transparency logs.
7. **Accept over HTTPS.** Run
   `... acceptance --base-url https://<node>.<tailnet>.ts.net --owner <login>` (password on stdin).
   This checks container health and pinned image identity, update labels, no binds or extra ports,
   exact Alembic head, verified originals, a media write/read, the release surface, anonymous
   refusal, secure cookie attributes, the owner session, foreign-Origin and missing-CSRF refusal,
   and logout.
8. **Schedule backups and checks.** Add these to DSM Task Scheduler (user root, email on failure) or cron:
   `... backup` nightly; `... export <newest-set> --repository <off-host repo> --password-file <file>`
   after it; `... retention --apply` weekly; and `... status` hourly. `status` exits 1 on an unhealthy
   service, a recovery set older than 26 h, an unresolved operation or < 5 GiB free.

### Dockhand

The application does not depend on Dockhand; any amd64 Docker host with Compose ≥ 2.20 works. Where
Dockhand is the control plane, the following applies:

- Pin and record the Dockhand image digest; enable its authentication at first launch; never expose
  it publicly. Back up its data directory, including `.encryption_key` (or `ENCRYPTION_KEY`).
- Import `stack/` as an existing stack in place. Dockhand must see the stack **and** `secrets/`
  directories at identical absolute paths, because `env_file` resolves on the Docker host.
- Settings → Environments → *environment* → Updates: **Automatically update containers off**.
  Scheduled update checks may stay on: excluded containers show no badge, so release notifications
  come from `florabasectl check-release` (exit 10 when an approved manifest differs) instead.
- No Git stack, auto-sync, force-redeploy or deployment webhook for this stack. A manual Dockhand
  redeploy of the recorded files is harmless, because the gate refuses schema mismatches. It is not
  an upgrade path: promotion is only through the controller.
- Labels win over UI policy per the Dockhand manual, but behavior on the pinned Dockhand version is
  **not yet verified**; record it during real-host acceptance.

## Health and migration contract

Readiness for the controller means all of the following:

- db/backend/frontend are healthy and run exactly the pinned images;
- the gate-verified Alembic head equals the release manifest;
- every original verifies against its database SHA-256;
- media storage accepts a write/read;
- HTTP surfaces answer and the frontend `/release.json` matches the release.

Container health alone is not readiness. Migration runs only from the **target** backend image, after
writers are stopped and a fresh verified pre-upgrade recovery set exists. An unknown or ahead
revision is refused before any change, and the database is never downgraded automatically.

## Recovery sets

`backup` stops backend and frontend, verifies all originals, then writes `pg_dump` (custom format)
plus the original-object archive. It validates both with the recorded images (`pg_restore --list`,
archive validation) and records `metadata.json`:

- installation and release identity, image references and the PostgreSQL identity;
- Alembic revision and exact row counts of every table;
- the non-secret configuration and stack-document digest, plus volume devices;
- per-artifact SHA-256.

It also writes `SHA256SUMS` and the stack document, renames the set into place atomically and
restarts writers. `verify-backup <set>` re-checks everything, using no live service.

- **Off-host copy:** `export <set> --repository <restic repo> --password-file <0600 file> [--init]
  [--restic-env-file <credentials>]` stores the set in an encrypted restic repository, runs
  `restic check`, restores the snapshot to scratch space and verifies every checksum before
  reporting success. `import-set` fetches a set onto a new host. Keep the restic password and the
  `secrets/` and Dockhand key backups in separate custody.
- **Retention:** `retention` (dry run) / `--apply` keeps the newest set per day for 7 days, per
  ISO week for 4 weeks, the 3 newest pre-upgrade/safety sets and always the newest set.
- **Isolated drill:** `restore-isolated <set> --http-port 18081 [--owner <login>]` restores into a new
  `florabase-restore-*` project with its own directories, secrets and loopback port. It compares
  revision and exact table counts, verifies every original and invalidates restored sessions before
  serving, then runs acceptance and optional owner login. Live data is never mounted.
  Remove the drill with `restore-remove --project <name> --confirm <name>`.
- **Replacement:** `restore-replace <set> --confirm-installation <id> --confirm-database florabase`
  needs both exact confirmations and the same PostgreSQL identity. It first takes a best-effort
  logical safety set, then moves the current `postgres/` and `media/` into `preserved/<time>/`
  (nothing is deleted) and restores into fresh directories with the set's own images and stack
  document. It invalidates sessions and runs acceptance. Writes made after the set are lost; the
  preserved directories keep them for diagnosis.

Proposed defaults for operator acceptance: RPO ≤ 24 h (nightly set plus one before every upgrade),
RTO ≤ 4 h on the real host and link. The smoke's restore timings on synthetic data are recorded in the
evidence; they are not host RTO.

## Upgrades

`check-release` reports an approved manifest. `promote --manifest … --manifest-sha256 …
[--confirm-migration]` runs a single serialized, journaled operation:

1. Refuse if another controller holds the lock, an operation is unresolved, stack files drifted,
   volumes are foreign, the manifest/images fail verification, or the PostgreSQL identity differs.
   PostgreSQL changes are separate database maintenance and never ride on an application release.
   An unknown/ahead schema is refused, and a schema change needs `--confirm-migration`.
2. `validated` → stop writers → `quiesced` → fresh pre-upgrade recovery set → `backed_up`.
3. Run the target image's migration and verify the head → `migrated`.
4. Atomically pin the new pair and stack document → `pinned`.
5. Start db, gate, backend and frontend with bounded waits; a crash loop fails fast → `started`.
6. Run acceptance → `accepted`, then record `current.json`.

Every phase is fsynced to `state/operation.json` and `state/journal.jsonl`. On failure the operation
is marked failed, writers stay stopped and one recovery choice is printed. There is no retry loop.

| Situation | Command |
| --- | --- |
| Process killed or host rebooted mid-run | `resume` (continues from the recorded phase; `promote` refuses meanwhile) |
| Failed before any schema change | `abort` (re-pins the previous pair after proving the revision unchanged) |
| Migration applied, application failed | `abort` refuses; use `promote --after-failed` with a tested forward fix, or `restore-replace <pre-upgrade set>` |
| Writers resumed after a bad upgrade | Stop and decide explicitly; a restore loses later writes |

Promotion stays manual. An automatic schedule may later call `promote` only for manifests marked
schema-compatible, after the same gates have been proven on the real host.

## Disposable verification

`make smoke-beta-runtime` builds candidate images from the working tree and starts a
network-isolated `docker:24.0.2-dind` daemon with owned, disk-backed volumes, plus the
checksum-verified official Compose 2.20.1 plugin. It runs the controller from a copied bundle under
Python 3.8.20 and pulls only from a loopback registry inside that daemon. Test-only backend variants
add a compatible revision (B), a failing migration (C), a migrated-but-crashing application (D) and
its forward fix (E). The sequence:

- preflight, init (twice: refused), install with wrong then right digest, owner bootstrap/login;
- seed suppliers, an unlinked original, a shared original linked twice and an external asset with
  a saved local copy; recreate backend/frontend and restart the daemon, then compare the exact data;
- backup, verification and tamper detection;
- isolated restore with login, compared to the source and proven not to touch the live database;
- encrypted restic export, then import of the set from the repository;
- compatible promote, with PostgreSQL container/image and volume identities unchanged;
- refusal of the older, unaware release;
- failed migration → abort;
- failed application after migration → refused abort → explicit forward fix;
- replacement restore after wrong-ID refusals, with sessions invalidated and failed data preserved;
- SIGKILL after migration → refused promote → resume;
- final status clean, update labels verified, unrelated nested workload and host `florabase-prod`
  resources unchanged.

All owned containers, networks, volumes and images are retired on exit. The disposable smoke uses a
test-only manifest distribution (`test-candidate`), which the controller accepts only with
`FLORABASECTL_TEST_MODE=1` and `--allow-test-candidate`, and only for loopback registries. The
recorded run is in [beta-runtime-001-evidence.json](beta-runtime-001-evidence.json).

## Outstanding operator evidence

None of the following was available or touched here; each needs a real-host record before
BETA-ACCEPTANCE-001:

- The selected host's DSM/OS version, Python 3 version, and Container Manager Engine/Compose plugin path (`docker
  compose` or standalone `docker-compose`; `FLORABASECTL_COMPOSE` overrides detection);
  `preflight` evidence including CFS/memory warnings.
- Btrfs ownership/ACL behavior for `postgres/` 0700 at uid 70; UPS and memory headroom alongside
  DSM tasks.
- Pinned Dockhand version: label exclusion, environment update toggle, stack import, secrets path
  access and redeploy behavior; Dockhand data/key backup.
- Tailscale Serve persistence across reboot and certificate renewal; HTTPS `acceptance --base-url`
  with owner login from desktop and phone.
- A real reboot, the off-host restic destination and credentials custody, and accepted RPO/RTO,
  retention and maintenance window.
- Whether WFO/WCVP are needed on day one (`reference set --kind wfo --file … --sha256 …`).

## Coordination and limits

- `release/inputs.json` and security-owned image files are unchanged. The controller's default
  restic image (`restic/restic:0.17.3@sha256:8f5a62b4…`) is a **new runtime-owned pin** that
  BETA-SECURITY-001 should scan before real use.
- Restore depends on registry availability of the recorded image digests (GHCR versions are
  retained, never deleted). Offline image archives are not part of recovery sets.
- The frontend `runtime-config.js` override for optional map settings is not wired into this
  stack.
