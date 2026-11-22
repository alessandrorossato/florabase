# ADR 0010: Directly usable `:latest` `compose.yaml` with plain bind mounts

- Status: accepted (operator decision, 2026-11-22); implemented by INSTALL-003
- Date: 2026-11-22
- Amends: [ADR 0009](0009-minimal-production-compose.md) (Compose template slots, bind-mount syntax, networks, and release compose asset)

## Context

[ADR 0009](0009-minimal-production-compose.md) simplified the production `compose.yaml` to three
non-root services, but kept it as a build-time template (`@VERSION@`, `@POSTGRESQL@`, `@BACKEND@`,
`@FRONTEND@`), required Compose `${VAR:?...}` interpolation and long-form `{type: bind, ...,
create_host_path: false}` mounts, passed `FLORABASE_DATA_DIR` / `FLORABASE_BACKUP_DIR` into
`backend`, and defined two custom networks (`internal`, `app`). Self-hosters using Dockhand,
Synology Container Manager, or plain `docker compose` expect `compose.yaml` on `main` to be
directly usable as-is: edit the host folder paths, password and origin in place and deploy.

## Decision

1. **Directly usable `compose.yaml` on `main` with `:latest`.** Template slots (`@VERSION@`,
   `@POSTGRESQL@`, `@BACKEND@`, `@FRONTEND@`) and `render_compose()` are removed. `compose.yaml`
   references `ghcr.io/alessandrorossato/florabase-{postgres,backend,frontend}:latest` directly.
   Every published release (including `0.1.0-beta.N`, `1.0.0-rc.N`, and `1.0.0`) promotes both
   its immutable versioned tag and `:latest` via `promote_image()` with the same digest-unchanged
   proof.
2. **PostgreSQL major-version safety on `:latest`.** `publish-beta-images.py` enforces in code
   that `florabase-postgres:latest` only moves within PostgreSQL major 18 (`18.*`). A rebuilt PG
   18 image (e.g. Alpine security update or entrypoint guard update) moves `:latest`; crossing to a
   newer PostgreSQL major version is refused by the publisher and by `florabase-postgres-entrypoint`
   (`FLORABASE_PG_MAJOR` vs `$PG_MAJOR`).
3. **Plain short bind mounts and plain literals (no `.env` required).** Volumes use short syntax
   with Synology-style absolute host path examples (`/volume1/docker/florabase/data`,
   `/volume1/docker/florabase/backup`) and comments instructing operators to edit only the left
   side. Environment variables use plain literals (`TZ=Europe/Rome`,
   `FLORABASE_DB_PASSWORD=change-me`, `FLORABASE_CANONICAL_ORIGIN=https://florabase.example.org`)
   and `frontend` publishes `127.0.0.1:8080:8080` literally.
4. **In-image guards preserve fail-closed safety without `create_host_path: false` or host-path
   env vars.**
   - Short bind syntax lets Docker auto-create a missing host folder (empty, `root:root`, `0755`).
     `florabase-postgres-entrypoint` refuses missing/wrongly-owned `postgres/`, `media/`, `state/`,
     and `backend`'s `release_schema deploy` refuses missing/wrongly-owned `state/`, `media/`, and
     `backup/pre-upgrade`, so no empty cluster is ever silently initialized.
   - Both `florabase-postgres-entrypoint` and `release_schema` (`wait-db`, `deploy`, `serve`)
     refuse to start if `FLORABASE_DB_PASSWORD` (or `POSTGRES_PASSWORD`/`PGPASSWORD`) is still the
     placeholder `change-me`, pointing to [docs/installation.md](../installation.md).
   - `FLORABASE_DATA_DIR` and `FLORABASE_BACKUP_DIR` are removed from `compose.yaml`. `backend`
     detects identical or nested data/backup bind mounts in-container via `(st_dev, st_ino)` and
     `/proc/self/mountinfo` (including btrfs subvolumes on the same device), warning and continuing
     if mountinfo is indeterminate and refusing on positive detection.
5. **Default network in `compose.yaml`; custom networks in the optional hardened override.**
   Custom `networks:` (`internal`, `app`) are dropped from `compose.yaml` (`db` and `backend`
   still publish no ports; `frontend` stays loopback-only) and documented in the optional hardened
   override snippet in [docs/security.md](../security.md#optional-container-hardening).
6. **Release provenance without a duplicate rendered `compose.yaml` asset.** Releases no longer
   attach or attest a rendered `compose.yaml`. Protected publication attests the three immutable
   OCI image indexes (`backend`, `frontend`, `postgresql`) and `release-manifest.json` (which
   records all `@sha256:...` digests and binds the tracked `compose.yaml` SHA-256). Operators who
   want digest pinning copy the three `reference` values from `release-manifest.json`.

## Consequences

- `compose.yaml` on `main` is 40 lines, directly usable with zero template rendering or Compose
  interpolation knowledge.
- `florabase-postgres:latest` can move to a rebuilt image within PostgreSQL 18 when a Compose
  manager pulls updates; major upgrades remain explicit and guarded.
- Operators opting into defense-in-depth (`internal: true` database isolation, `read_only`,
  `cap_drop: [ALL]`, `no-new-privileges`) layer the single documented override in
  [docs/security.md](../security.md#optional-container-hardening).
