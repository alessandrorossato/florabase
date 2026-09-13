#!/usr/bin/env bash
set -euo pipefail

source_file="${FILE:?FILE is required}"
attachment_file="${ATTACHMENTS_FILE:?ATTACHMENTS_FILE is required}"
if [[ ! -f "$source_file" ]]; then
  echo "Backup does not exist: $source_file" >&2
  exit 2
fi
if [[ ! -f "$attachment_file" ]]; then
  echo "Attachment backup does not exist: $attachment_file" >&2
  exit 2
fi
database_name="$(basename "$source_file")"
attachment_name="$(basename "$attachment_file")"
if [[ ! "$database_name" =~ ^florabase-([0-9]{8}T[0-9]{6}Z)\.dump$ ]]; then
  echo "Database backup name must use the Florabase timestamped backup format." >&2
  exit 2
fi
timestamp="${BASH_REMATCH[1]}"
if [[ "$attachment_name" != "florabase-${timestamp}.attachments.tar" ]]; then
  echo "Attachment backup must match the database backup timestamp." >&2
  exit 2
fi
if [[ "${CONFIRM_REPLACE:-}" != "yes" ]]; then
  echo "Restore replaces the target database. Re-run with CONFIRM_REPLACE=yes." >&2
  exit 2
fi

docker compose exec -T db pg_restore --list <"$source_file" >/dev/null
docker compose run --rm --no-deps -T backend \
  python scripts/attachment_artifacts.py validate-archive <"$attachment_file"
target_database="$(docker compose exec -T db sh -c 'printf "%s" "$POSTGRES_DB"')"
if [[ -z "$target_database" ]]; then
  echo "The database container did not report a target database; refusing restore." >&2
  exit 2
fi
if [[ "${CONFIRM_DATABASE:-}" != "$target_database" ]]; then
  echo "Restore target is '$target_database'. Re-run with CONFIRM_DATABASE=$target_database." >&2
  exit 2
fi
docker compose stop backend
docker compose exec -T db sh -c \
  'dropdb --if-exists --force --username "$POSTGRES_USER" "$POSTGRES_DB"'
docker compose exec -T db sh -c \
  'createdb --username "$POSTGRES_USER" --owner "$POSTGRES_USER" "$POSTGRES_DB"'
docker compose exec -T db sh -c \
  'pg_restore --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --no-owner --no-privileges' \
  <"$source_file"
docker compose run --rm --no-deps -T backend \
  python scripts/attachment_artifacts.py restore <"$attachment_file"
docker compose run --rm --no-deps backend python scripts/attachment_artifacts.py verify
docker compose start backend
echo "Restore completed from $source_file and $attachment_file"
