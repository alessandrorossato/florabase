# ADR 0009: Minimal three-service production `compose.yaml`

- Status: accepted (operator decision, 2026-11-22); implemented by INSTALL-002
- Date: 2026-11-22
- Amends: [ADR 0008](0008-self-initializing-single-compose.md) (rules 1, 3 and 4; Compose shape)

## Context

`v0.1.0-beta.7` shipped the first single self-initializing `compose.yaml` (ADR 0008, INSTALL-001).
While it preserved every data-safety invariant, the rendered file was 188 lines long and contained
four YAML anchors, two multi-line inline shell scripts, a root-privileged `prepare` service, a
separate `migrate` service, explicit container hardening blocks and two custom networks. Operators
installing Florabase in Dockhand or Synology Container Manager expect a short, flat, self-evident
Compose file where operational complexity lives inside the images rather than inline in YAML.

## Decision

The production `compose.yaml` stays the single image-only, digest-pinned, attested release asset
(ADR 0008), simplified to **three non-root services** (`db`, `backend`, `frontend`) with no YAML
anchors, no inline shell scripts, no `entrypoint` overrides, no `healthcheck` blocks and no root
containers:

1. **Operator-owned folder setup (amends ADR 0008 rule 1).** The root `prepare` service is removed;
   no container in `compose.yaml` runs as root (`user: "0:0"` is gone). The operator creates the
   data and backup folders and sets owners and modes once using the copy-paste block in
   [docs/installation.md](../installation.md) (`postgres` `70:70` `0700`, `media` `10001:10001`
   `0700`, `state` `10001:10001` `0755`, `backup/pre-upgrade` `10001:10001` `0700` — identical to
   the `v0.1.0-beta.7` layout). Every bind mount keeps `create_host_path: false`, so an unmounted
   volume still fails closed instead of creating an empty host directory.
2. **In-image guards replace inline scripts (preserves ADR 0008 rule 2).**
   - `florabase-postgres:18.6-alpine-florabase.4` (`USER 70:70`, `gosu` removed, root refused with
     exit 64) carries `ENV PGDATA=/var/lib/postgresql/postgres/18/docker`, `POSTGRES_DB=florabase`,
     `POSTGRES_USER=florabase`, an image `HEALTHCHECK`, `CMD ["postgres", "-c", "timezone=UTC"]`,
     `FLORABASE_DB_PASSWORD` → `POSTGRES_PASSWORD` mapping, and the full pre-start guard in
     `florabase-postgres-entrypoint`: directory/owner/mode validation (pointing to
     `docs/installation.md` on mismatch), empty-folder enforcement, marker validation (PG major,
     cluster existence and `pg_controldata` system identifier) and a 70-owned
     `postgres/installation.pending` retry marker (removed once `state/installation.env` exists).
   - The backend `runtime` image carries its constant production `ENV` values, derives `PGPASSWORD`
     from `FLORABASE_DB_PASSWORD` in `florabase-backend-entrypoint`, pins PostgreSQL sessions to
     UTC (`-c timezone=UTC`), and validates host path absoluteness, data/backup non-nesting and
     same-folder refusal, backup/media/state writability, and empty `media/` on fresh installs
     before any dump or migration.
3. **Guarded start sequence in `backend` (amends ADR 0008 rules 3 and 4).** The separate `migrate`
   service is removed. The long-running server process (`uvicorn`) still **never migrates**;
   `backend` runs `florabase-start`, which executes:
   1. a bounded `pg_isready` wait for PostgreSQL (`release_schema wait-db`);
   2. a separate guarded deploy subprocess (`release_schema deploy`: advisory lock, init / keep /
      verified pre-upgrade `pg_dump` + upgrade / refuse, atomic `state/installation.env`, first
      owner creation once, and `state/installation.pending` around initial schema creation);
   3. scrubbing `FLORABASE_OWNER_LOGIN` and `FLORABASE_OWNER_PASSWORD` from the server process
      environment;
   4. `exec python -m florabase.db.release_schema serve`, which keeps the exact-head schema guard
      before `exec`ing `uvicorn` as PID 1.
   - **No repeated dumps on failed upgrade:** if an upgrade fails after writing its verified
     pre-upgrade dump, `deploy` atomically writes `state/upgrade-failed.env` (recording source
     revision, target revision, dump filename and error summary). Subsequent container restarts
     under `restart: unless-stopped` refuse immediately without writing additional dumps until the
     operator resolves the cause and removes `state/upgrade-failed.env`.
   - **Refusal backoff:** refusals in `florabase-postgres-entrypoint` and `florabase-start` log one
     clear line, sleep a short backoff (3 seconds by default, under Docker's 10-second reset window
     so Docker's exponential restart backoff also applies) and exit `1`, so logs do not flood while
     `docker compose up -d --wait` still fails fast.
4. **Minimal Compose defaults and optional hardening.** Fixed `container_name: florabase-<role>`
   values, `TZ=${TZ:-Europe/Rome}` (log/display only; DB and SQLAlchemy sessions remain pinned to
   UTC), and Compose's default bridge network replace the custom `internal`/`app` networks and
   inline hardening blocks (`read_only`, `tmpfs`, `cap_drop`, `no-new-privileges`). Only `frontend`
   publishes a port, bound literally to `127.0.0.1:${FLORABASE_HTTP_PORT:-8080}:8080`. Operators
   who want read-only root filesystems, dropped capability bounding sets and split networks apply
   the documented override snippet in [docs/security.md](../security.md).

## Consequences

- `compose.yaml` drops from 188 lines to 41 lines while preserving every ADR 0008 data-safety
  refusal and `v0.1.0-beta.7` folder-layout compatibility.
- Trade-offs explicitly accepted by the operator and documented in [docs/security.md](../security.md):
  - `backend` now mounts `FLORABASE_BACKUP_DIR` read-write and carries the one-time
    `FLORABASE_OWNER_*` variables in its container configuration (`docker inspect`) until removed
    (scrubbed from the `uvicorn` process environment before `exec`).
  - Default deployments run without `read_only`, `cap_drop: [ALL]`, `no-new-privileges`, or the
    `internal`/`app` network split; images remain non-root (`70`, `10001`, `101`), setuid/setgid
    stripped, and `gosu`-free, and an optional hardened override is documented.
  - Fixed `container_name` values mean side-by-side stacks (such as isolated restore and automated
    smoke tests) load a small untracked override resetting `container_name`.
- `florabase-postgres` advances to `18.6-alpine-florabase.4` under the BETA-RUNTIME-001 database
  maintenance rule (reproducible identity, Trivy scan, SBOM, paired backup/restore smoke).
