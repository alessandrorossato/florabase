# Backup and restore

## Database backup

With the stack running:

```bash
make backup
```

This streams `pg_dump --format=custom` from the PostgreSQL container into a new UTC-timestamped file under ignored `backups/`. It refuses to overwrite the timestamp target and checks that output is non-empty. Protect dumps as sensitive data and copy them off-host according to the desired recovery point objective.

Validate a dump without restoring it:

```bash
docker compose exec -T db pg_restore --list < backups/example.dump >/dev/null
```

## Destructive restore

Restore replaces the configured database, stops the backend, validates the archive listing, recreates the database, restores without source ownership/privileges, and restarts the backend:

```bash
make restore FILE=backups/example.dump CONFIRM_REPLACE=yes CONFIRM_DATABASE=florabase
make health
```

`CONFIRM_DATABASE` must exactly match `POSTGRES_DB` inside the running database container; the restore script checks it before stopping the backend or dropping anything. Confirm the target `.env` and preserve a pre-restore backup first. Test restore procedures against an isolated disposable stack before relying on them in production. A failed restore may leave the backend stopped; inspect logs and database state before retrying.

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

No attachment or upload storage exists today, so all application-managed collection and account data
is in PostgreSQL. A database dump still does not include deployment configuration, reverse-proxy
configuration, TLS material, or secrets. Coordinate and protect:

- the PostgreSQL custom-format dump;
- deployment configuration and secrets stored in an appropriate secrets backup;
- the exact application image/source version and migration revision.

If attachment storage is implemented later, its documented durable volume and a database-consistent
copy will also be required; current backup behavior must not be assumed to cover future files.

Encryption, retention, off-site copies, restore drills, and access control are operator responsibilities.
