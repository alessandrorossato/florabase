# Backup and restore

## Coordinated database and attachment backup

With the stack running:

```bash
make backup
```

The command stops the backend to quiesce application writes, verifies every managed attachment's
stored size and SHA-256 against PostgreSQL metadata, then creates two same-timestamp artifacts under
ignored `backups/`:

- `florabase-<timestamp>.dump` — a validated custom-format PostgreSQL dump;
- `florabase-<timestamp>.attachments.tar` — the validated contents of the backend-only attachment
  volume.

The backend restarts after successful backup or ordinary backup failure. The command refuses to
overwrite either artifact and removes an incomplete pair. Protect both as sensitive data and copy
both off-host according to the desired recovery point objective. The pair is application-consistent
because writes are stopped, but it is not an atomic PostgreSQL/filesystem snapshot; direct writes to
the database or Docker volume are unsupported and outside this guarantee.

Validate a dump without restoring it:

```bash
docker compose exec -T db pg_restore --list < backups/example.dump >/dev/null
```

Validate the paired attachment archive without extracting it:

```bash
docker compose run --rm --no-deps -T backend \
  python scripts/attachment_artifacts.py validate-archive \
  < backups/example.attachments.tar
```

The validator accepts only the server-owned `objects/<shard>/<opaque-key>` layout and rejects
absolute paths, traversal, links, devices, duplicate members, and unrelated files.

## Destructive restore

Restore replaces the configured database and attachment content. It validates both artifacts before
stopping the backend, checks the exact database confirmation, recreates and restores PostgreSQL
without source ownership/privileges, safely stages and swaps the attachment object tree, verifies
active stored sizes and SHA-256 digests, and only then restarts the backend:

```bash
make restore \
  FILE=backups/example.dump \
  ATTACHMENTS_FILE=backups/example.attachments.tar \
  CONFIRM_REPLACE=yes \
  CONFIRM_DATABASE=florabase
make health
```

`CONFIRM_DATABASE` must exactly match `POSTGRES_DB` inside the running database container; the restore script checks it before stopping the backend or dropping anything. Confirm the target `.env` and preserve a pre-restore backup first. Test restore procedures against an isolated disposable stack before relying on them in production. A failed restore may leave the backend stopped; inspect logs and database state before retrying.

Never mix artifacts from different timestamps: restore rejects names that do not match the
`florabase-<timestamp>.dump` and `florabase-<timestamp>.attachments.tar` pair. An attachment row in
`pending_delete` may validly have a file or may already have no file; it remains inaccessible and the
next authenticated DELETE finishes its deterministic cleanup. Active metadata with missing,
size-mismatched, or digest-mismatched content fails verification and keeps the backend stopped after
restore.

## Isolated restore drill

The following smoke test uses a network-isolated, tmpfs-backed PostgreSQL container. It does not connect to or replace the Compose database. Set `dump_file` to the custom-format dump being tested:

```bash
dump_file=backups/example.dump
restore_container=florabase-restore-smoke

test -f "$dump_file"
test -z "$(docker ps --all --quiet --filter name="^/${restore_container}$")"
docker run --detach \
  --name "$restore_container" \
  --network none \
  --tmpfs /var/lib/postgresql:rw \
  --env POSTGRES_DB=restore_smoke \
  --env POSTGRES_USER=restore_smoke \
  --env POSTGRES_PASSWORD=restore-smoke-only \
  postgres:18.6-alpine
trap 'docker rm --force "$restore_container" >/dev/null 2>&1 || true' EXIT

for attempt in $(seq 1 30); do
  docker exec "$restore_container" \
    pg_isready --username restore_smoke --dbname restore_smoke && break
  test "$attempt" -lt 30
  sleep 1
done

docker exec --interactive "$restore_container" \
  pg_restore --username restore_smoke --dbname restore_smoke \
  --no-owner --no-privileges < "$dump_file"
docker exec "$restore_container" \
  psql --username restore_smoke --dbname restore_smoke --tuples-only --no-align \
  --command "SELECT version_num FROM alembic_version; SELECT key, value FROM app_metadata ORDER BY key;"
docker compose exec -T db sh -c \
  'psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --tuples-only --no-align --command "SELECT version_num FROM alembic_version; SELECT key, value FROM app_metadata ORDER BY key;"'
docker logs "$restore_container"

docker rm --force "$restore_container"
trap - EXIT
```

Compare the isolated and source query output. The Alembic revision and infrastructure metadata must match. The final removal is safe because the drill container is explicitly named, has no network, and stores its database only in tmpfs.

## Complete recovery set

From `ATTACHMENT-002` onward a PostgreSQL dump alone is not a complete Florabase backup. Coordinate
and protect:

- the matching PostgreSQL custom-format dump and attachment-volume tar archive;
- deployment configuration and secrets stored in an appropriate secrets backup;
- the exact application image/source version and migration revision.

The attachment archive intentionally excludes transient upload/restore files. A crash in the narrow
window after permanent-file rename but before metadata commit can leave an unreferenced object; the
archive retains such objects rather than silently deleting data. Automated orphan reconciliation is
not part of ATTACHMENT-002.

Encryption, retention, off-site copies, restore drills, and access control are operator responsibilities.
