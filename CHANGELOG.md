# Changelog

Notable changes to Florabase, newest first. Versions follow the
[versioning policy](docs/versioning.md). The engineering record of every increment is
[docs/progress.md](docs/progress.md); this file lists what an operator of an installation needs
to know.

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
