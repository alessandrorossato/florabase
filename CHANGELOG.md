# Changelog

Notable changes to Florabase, newest first. Versions follow the
[versioning policy](docs/versioning.md). The engineering record of every increment is
[docs/progress.md](docs/progress.md); this file lists what an operator of an installation needs
to know.

## Unreleased

**Upgrading from `v0.1.0-beta.9`:** existing `compose.yaml` files without
`FLORABASE_REFERENCES_SETUP=auto` keep automatic reference provisioning **off** (zero outbound
reference requests) until you add `- FLORABASE_REFERENCES_SETUP=auto` to `backend.environment` and
redeploy. No new host folders or volume mounts are required.

### Added

- **Automatic botanical reference provisioning (`REF-SETUP-001`):** fresh installs using the
  shipped `compose.yaml` (`FLORABASE_REFERENCES_SETUP=auto`) download the pinned official WFO
  2026-06 and Kew WCVP v16 archives in a low-priority background worker after start-up, verify
  exact SHA-256 checksums before parsing, build and seal SQLite indexes atomically under
  `/var/lib/florabase/data/state/reference/` (`0700`, excluded from pre-upgrade dumps and paired
  backups), and enable taxonomy and native-range lookups without manual copying. Start-up and
  health checks never wait for provisioning.
- **Read-only reference status diagnostics:** authenticated `GET /api/v1/system/references` and a
  read-only **Reference index status** section in **Settings → Data sources** report each index as
  `off`, `preparing`, `ready`, `ready (setup off)`, `failed: <reason>`, or `manual`. Taxonomy and
  native-range screens indicate when reference data is being prepared in the background.

## v0.1.0-beta.9 — 2026-11-24

Prerelease of the private beta series: changes since `v0.1.0-beta.8`. No database migrations
(Alembic head unchanged); PostgreSQL moves to `18.6-alpine-florabase.5` (same PostgreSQL 18.6
cluster layout), and `compose.yaml` changes are comments only. Take `compose.yaml` from the
`v0.1.0-beta.9` tag, not from `main`.

**Upgrading from `v0.1.0-beta.8`:** take a paired backup, then run an update (pull and redeploy)
in your Compose manager; it pulls the new `:latest` `backend`, `frontend` and `florabase-postgres`
images. Your existing `compose.yaml` keeps working unchanged.

### Added

- **Directories:** Seeds, Sowings and Plants gain a `Sort by` select (name, newest/oldest date;
  undated last), applied before pagination and kept in the URL and saved views (`FN-02`).
- **Reference pickers:** selects over your own records (plant, sowing, identity, site, location,
  geography and similar) are now searchable, keyboard-operable pickers (`FN-04`).
- **Save and add another** in the Seeds, Sowings and Plants create forms keeps the form open with a
  fresh draft that retains the identity or seed lot (`UX-ENTRY-001`).
- **Scientific name suggestions:** creating an identity suggests names from the local WFO index
  when it is mounted. The optional read-only WFO/WCVP v16 reference index mount is documented in
  [docs/installation.md](docs/installation.md#optional-botanical-reference-datasets); `compose.yaml`
  only carries a comment pointing to it (`UI-REVIEW-002`).
- Plain-ASCII startup banner printed once per container start as the first output of
  `release_schema wait-db`, showing Florabase version, image revision (`FLORABASE_REVISION`),
  sanitized origin, environment, log format, and project URL without printing secrets
  (`RUNTIME-IDLE-001`).
- `release_schema` configuration validation errors now name each failing `FLORABASE_*` environment
  variable (and model-level message) without printing input values, context or URLs
  (`RUNTIME-IDLE-001`).

### Changed

- Lowered idle container CPU on low-power hosts (`RUNTIME-IDLE-001`):
  - Backend image `HEALTHCHECK` now uses busybox `wget` against `/api/v1/health` (liveness) on a
    30 s interval (`--start-period=60s --start-interval=2s --retries=3`) instead of spawning Python
    against `/api/v1/ready` every 10 s; `/api/v1/ready` remains unchanged for operators and
    `make health`.
  - PostgreSQL (`18.6-alpine-florabase.5`) and frontend image health checks move to a 30 s interval
    with short `--start-interval` (`1s` / `2s`), which Docker Engine 25+ honours and Engine 24
    safely ignores (cold start on Engine 24 may take up to one 30 s interval per service in the
    startup chain).
  - Successful (2xx) loopback `GET` probes to `/api/v1/health` and `/api/v1/ready` are filtered out
    of `uvicorn.access`; non-loopback probes and non-2xx responses stay logged.
- Installation and backup/restore documentation (`DOCS-003`):
  - Added a "Before you start" callout at the top of [docs/installation.md](docs/installation.md)
    and a prominent reminder in [README.md](README.md) that the one-time folder setup block in § 1
    must be run on the host before the first deploy.
  - Updated [docs/installation.md](docs/installation.md) and
    [docs/backup-restore.md](docs/backup-restore.md) for the minimal `:latest` `compose.yaml`
    rehearsal findings: paired backup runs over SSH in the stack folder (`docker compose ls`),
    archives `release-manifest.json` only when present, removes stale `.env`,
    `FLORABASE_HTTP_PORT`, `FLORABASE_DATA_DIR` and `FLORABASE_BACKUP_DIR` instruction placeholders,
    aligns Synology NAS paths with `compose.yaml` (`/volume1/docker/florabase/backup`), documents
    same-host port selection (editing the restore copy of `compose.yaml` or `ports: !override` on
    Compose 2.24.4+) and HTTPS/`sudo` notes for isolated restore drills, and clarifies that
    automatic pre-upgrade dumps run only when the database Alembic revision changes.
- Root community documentation (`DOCS-002`): README "What works today", contributor guide with
  DCO sign-off, updated supported versions in `SECURITY.md`, and a root
  [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md); finished increment records moved to
  `docs/archive/`, with [docs/README.md](docs/README.md) as the documentation index.

### Fixed

- Operator review after beta.8 (`UI-REVIEW-002`): gallery directories such as Plants keep
  card-sized tiles, so a single record no longer spans the whole page; the identity Media tab and
  media asset page are redesigned to fit one desktop screen, and external covers save a local copy
  by default.

## v0.1.0-beta.8 — 2026-11-22

Prerelease of the private beta series: changes since `v0.1.0-beta.7`. The installation is now a
minimal three-service `compose.yaml` on `:latest` images (#214, #216), with PostgreSQL
`18.6-alpine-florabase.4`. Take `compose.yaml` from the `v0.1.0-beta.8` tag, not from `main`.

### Added

- **Explore > Lineage:** find an identity or a lineage record and view every record of one
  botanical identity connected by explicitly recorded relationships, reachable from the identity
  overview (`LINEAGE-004`).

### Changed

- **Updates through a Compose manager:** an "update" (pull and redeploy) in Dockhand or
  Container Manager pulls whatever `:latest` currently points to for all three images. For
  `backend` and `frontend` that is the newest published release; for `florabase-postgres` it can
  be a rebuilt image within PostgreSQL 18 (Alpine security or guard updates). Take a paired backup
  before every update, as for any release upgrade; pin `@sha256:` digests instead of `:latest` if
  you want updates to happen only when you edit the file.
- Production `compose.yaml` on `main` is now a directly usable 40-line, three-service file (`db`,
  `backend`, `frontend`) referencing `:latest` images (`ghcr.io/alessandrorossato/florabase-*`),
  plain short bind mounts with Synology-style absolute host path examples, plain environment
  literals (no `.env` or Compose interpolation required), fixed `container_name` values, no YAML
  anchors, no inline shell scripts and no root containers
  ([ADR 0009](docs/decisions/0009-minimal-production-compose.md),
  [ADR 0010](docs/decisions/0010-deployable-latest-compose.md), `INSTALL-002`, `INSTALL-003`).
- Every published release (including betas) promotes both its immutable versioned tag and `:latest`
  for `backend` and `frontend`. **`florabase-postgres:latest` can move to a rebuilt image within
  PostgreSQL 18 on manager updates** (e.g. Alpine security or guard updates), and never crosses a
  PostgreSQL major version automatically (enforced by both the release publisher and the PostgreSQL
  entrypoint marker guard).
- Removed the root `prepare` and separate `migrate` services, template slots (`@VERSION@`,
  `@POSTGRESQL@`, `@BACKEND@`, `@FRONTEND@`), and rendered `compose.yaml` release asset (releases
  continue to attest all three OCI image indexes and `release-manifest.json` with immutable
  `@sha256:...` digests):
  - Folder creation and ownership (`postgres` `70:70` `0700`, `media` `10001:10001` `0700`, `state`
    `10001:10001` `0755`, `backup/pre-upgrade` `10001:10001` `0700`) are a one-time host step in
    [docs/installation.md](docs/installation.md#1-create-the-folders-and-set-owners-once). Missing
    host folders auto-created by Docker are refused fail-closed by the in-image guards.
  - Both `florabase-postgres-entrypoint` (`18.6-alpine-florabase.4`) and `backend`'s
    `release_schema` refuse to start if `FLORABASE_DB_PASSWORD` is still the placeholder
    `change-me`.
  - Data-directory, ownership/mode, marker and cluster-identity guards, image `HEALTHCHECK`,
    `PGDATA`/`POSTGRES_DB`/`POSTGRES_USER` defaults and UTC `timezone` live in
    `florabase-postgres:18.6-alpine-florabase.4` (same PostgreSQL 18.6 base and cluster layout).
  - Constant backend production settings live in the backend `runtime` image; `florabase-start`
    waits for PostgreSQL, checks data/backup mount separation via `stat` and `/proc/self/mountinfo`
    (no `FLORABASE_DATA_DIR`/`FLORABASE_BACKUP_DIR` env vars required), runs the guarded deploy
    step (latching `state/upgrade-failed.env` if an upgrade fails so restarts never write duplicate
    dumps), scrubs one-time owner variables and `exec`s the exact-head `release_schema serve` guard.
- All services share a single `FLORABASE_DB_PASSWORD` value and `TZ=Europe/Rome` (for container
  logs; database storage and backend sessions remain pinned to UTC).
- Custom networks (`internal: true`, `app`) and container-level hardening (`read_only`, `cap_drop`,
  `no-new-privileges`) live in the optional override snippet in
  [docs/security.md](docs/security.md#optional-container-hardening); `compose.yaml` uses Docker's
  default bridge network and publishes only `frontend` on `127.0.0.1:8080`.
- **Upgrading from `v0.1.0-beta.7`:** Take a paired backup (required because this release updates
  the PostgreSQL image identity from `18.6-alpine-florabase.3` to `18.6-alpine-florabase.4` on
  the same PostgreSQL 18.6 cluster layout), then replace `compose.yaml` with the new file edited
  with your existing data/backup folders, `FLORABASE_DB_PASSWORD`, and
  `FLORABASE_CANONICAL_ORIGIN`, and redeploy. Existing beta.7 folder owners and modes already
  match. Paired-backup `docker compose exec` snippets now read `$FLORABASE_DB_PASSWORD` instead of
  `$POSTGRES_PASSWORD`.

### Fixed

- Operator UI/UX review (`UI-REVIEW-001`): aligned harvest surfaces, one shared
  palette system for the Botanical, Herbarium and Mineral themes, saved views in the directory
  menu, a compact one-screen Schedule month with a single Agenda/Calendar toggle, map overviews as
  metric cards, Settings and lineage breadcrumbs, and copy fixes. The Online basemap is offered
  only when the operator enabled a tile provider.

## v1.0.0 — planned

Not yet released or published. The final release entry and upgrade notes will be confirmed
against the accepted release candidate when v1.0.0 is cut.

- The planned distribution is the single self-initializing `compose.yaml` for linux/amd64; see
  the [release scope](docs/release/scope-v1.md) and [installation guide](docs/installation.md).
- Upgrade from beta requires a paired backup and the documented upgrade or isolated restore.
  The supported origins remain subject to the G-MIGRATE and G-UPGRADE acceptance gates.

## v0.1.0-beta.7 — 2026-11-21

Prerelease of the private beta series: changes since `v0.1.0-beta.6`. The installation is now a
single self-initializing `compose.yaml` release asset (#205, #207), with digest-pinned linux/amd64
images and PostgreSQL `18.6-alpine-florabase.3`.

### Changed

- One self-initializing `compose.yaml` is the only installation file
  ([ADR 0008](docs/decisions/0008-self-initializing-single-compose.md)). Create an empty data
  folder and a separate backup folder, then deploy the file as-is with Dockhand or
  `docker compose up -d`. The one-shot `prepare` service refuses any folder that is neither empty
  nor this installation, and `migrate` initializes the schema, leaves a current one unchanged, or
  upgrades from the previous release after writing and verifying a dump in the backup folder.
- The first owner can be created once from `FLORABASE_OWNER_LOGIN` and `FLORABASE_OWNER_PASSWORD`;
  remove them after the first sign-in. The offline bootstrap and reset commands remain.
- The backend image includes the PostgreSQL 18 client tools used for the pre-upgrade dump.
- The release carries `compose.yaml`, `RELEASE.md`, `release-manifest.json` (schema version 3),
  the PostgreSQL SBOM and the source archive.
- Backend dependency updates: FastAPI 0.163.2, psycopg 3.3.9, pwdlib 0.4.2, pydantic-settings
  2.16.3, python-multipart 0.0.34 and SQLAlchemy 2.0.58 (#207).

### Removed

- The controller bundle (`florabasectl.py`, its `compose.yaml` and `florabase.env.example`) and
  `portable-compose.yaml`. A `v0.1.0-beta.6` installation moves to the new layout through its
  paired backup and the [isolated restore](docs/installation.md#isolated-restore).

## v0.1.0-beta.6 — 2026-11-21

Prerelease of the private beta series: changes since `v0.1.0-beta.5`. The GitHub Release carries
the same asset set as beta.5 plus the portable Compose asset, with digest-pinned linux/amd64
images including PostgreSQL `18.6-alpine-florabase.3`.

### Added

- Portable Docker Compose distribution: a three-service `portable-compose.yaml` release asset with
  explicit schema initialization, upgrade, paired backup and isolated restore (#161). See the
  [installation guide](docs/portable-installation.md), completed in #184.
- Owner password change in Settings → Account, and an offline password reset command for the
  portable installation (#179).
- Cuttings: vegetative material lots and rooting attempts. Delivered and still being finished
  for v1.0.0 (#167).
- Material ancestry explorer, phenology observations in the Journal, operator-managed botanical
  synonyms and installation as a web app (#167).
- Accepted-name correction with retained name history (#165).
- Plant height measurements with correction history (#163).
- Explicit date choice for Journal entries: Today, Another date or Date unknown; and a work-first
  Today page (#177).
- A collection onboarding guide and CSV templates for a first import (#159).
- After a session expires, a sign-in dialog keeps unsaved edits in place; a failed save is never
  repeated automatically and is retried with Save once signed in again as the same owner (#199).
- The bundled web server sends security headers, including a Content-Security-Policy (#200).
  Operators who put their own reverse proxy in front should check that it does not add a
  conflicting policy.

### Changed

- Date fields never fill in a missing year, month or day; an incomplete date must be completed
  or cleared before saving (#177).
- WCVP v16 is the default source for native-range enrichment; v15 stays available (#174).
- The reviewed WGSRPD crosswalk covers more regions (#175).
- Backend and frontend dependency updates (#169, #171).
- New Florabase logo, favicon and web-app icons (#186).
- A new Journal entry opens with Today selected; Another date and Date unknown stay available (#192).
- Cuttings: the Journal shows rooting observations and links back to the rooting attempt (#195).
- The frontend image is based on nginx 1.30.7 (#198), and the PostgreSQL image is
  `18.6-alpine-florabase.3` with updated Alpine packages (#196, #202).

### Fixed

- Merging duplicate botanical identities while another change is being saved can no longer
  leave a record pointing at the merged identity (#185).
- On an empty database, creating a Plant or Plant group links to Botanical identities when a
  first identity is needed (#192).
- Directories stay scrollable on short and mobile screens, and Escape closes a reference picker
  before its parent dialog (#195, #199).

### Security

- The production backend no longer serves the generated API documentation and schema routes;
  only the sign-in, health and readiness API routes are reachable without signing in (#196, #200).
- The frontend base image moves to nginx 1.30.7 for nginx security advisories fixed in that
  release (#198). The PostgreSQL image adds Alpine fixes for Kerberos, libxslt and libxml2
  (#196, #202).

### Upgrade notes

- The database schema head moves from `20261013_0042` to `20261110_0047`. Apply it with the
  explicit upgrade command of your installation path after a paired backup; the application
  never migrates at startup.
- Installations from the `v0.1.0-beta.5` controller bundle upgrade with the controller's
  documented upgrade, or move to the portable stack through a paired backup and the
  [isolated restore](docs/portable-installation.md#isolated-restore) procedure.
- The PostgreSQL image changes from `18.6-alpine-florabase.1` (beta.5) to
  `18.6-alpine-florabase.3`. Switching the database image digest is separate database
  maintenance, and the controller refuses it during an application upgrade: take a paired backup
  first, as described in
  [the PostgreSQL image notes](docs/security/beta-distribution-001/postgresql-image.md).

## v0.1.0-beta.5 — 2026-11-08

Prerelease of the private beta series. The only prerelease with a published GitHub Release:
controller bundle (`compose.yaml`, `florabasectl.py`, `florabase.env.example`), release
manifest, release notes, source archive, PostgreSQL SBOM and digest-pinned linux/amd64 images.

- Recovered the release pipeline after the beta.4 publication attempt (#158).

## v0.1.0-beta.4 — 2026-11-08

Tagged; no GitHub Release is published for it.

- The distribution is rehearsed before publication (#155).
- Consolidated beta installation guidance (#156).

## v0.1.0-beta.3 — 2026-11-07

Tagged; no GitHub Release is published for it.

- Registry preflight reads GHCR manifests directly (#154).

## v0.1.0-beta.2 — 2026-11-07

Tagged; no GitHub Release is published for it.

- Completed the hashed lock of the release tools (#152).

## v0.1.0-beta.1 — 2026-11-07

Tagged; no GitHub Release is published for it. First beta tag of the single-owner application:
botanical identities and profiles, suppliers, orders, locations, seed lots, sowings, plants and
plant groups, Journal and History, Schedule, harvests and stored material, media, maps, taxonomy,
search, saved views, bulk moves, labels and CSV import/export, with the controller-based
image distribution.
