#!/usr/bin/env bash
set -euo pipefail

backup_dir="${BACKUP_DIR:-backups}"
mkdir -p "$backup_dir"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
database_destination="$backup_dir/florabase-$timestamp.dump"
attachment_destination="$backup_dir/florabase-$timestamp.attachments.tar"
database_temporary="$database_destination.partial.$$"
attachment_temporary="$attachment_destination.partial.$$"
backend_stopped=false
backup_complete=false

cleanup() {
  rm -f "$database_temporary" "$attachment_temporary"
  if [[ "$backup_complete" == false ]]; then
    rm -f "$database_destination" "$attachment_destination"
  fi
  if [[ "$backend_stopped" == true ]]; then
    docker compose start backend >/dev/null
  fi
}
trap cleanup EXIT

for destination in "$database_destination" "$attachment_destination"; do
  if [[ -e "$destination" ]]; then
    echo "Refusing to overwrite existing backup: $destination" >&2
    exit 1
  fi
done

docker compose stop backend
backend_stopped=true
docker compose run --rm --no-deps backend python scripts/attachment_artifacts.py verify

docker compose exec -T db sh -c \
  'pg_dump --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --format=custom --no-owner --no-privileges' \
  >"$database_temporary"
docker compose run --rm --no-deps -T backend \
  python scripts/attachment_artifacts.py archive >"$attachment_temporary"

test -s "$database_temporary"
test -s "$attachment_temporary"
docker compose exec -T db pg_restore --list <"$database_temporary" >/dev/null
docker compose run --rm --no-deps -T backend \
  python scripts/attachment_artifacts.py validate-archive <"$attachment_temporary"
mv --no-clobber "$database_temporary" "$database_destination"
mv --no-clobber "$attachment_temporary" "$attachment_destination"
docker compose start backend >/dev/null
backend_stopped=false
backup_complete=true
trap - EXIT
echo "Created coordinated backup artifacts:"
echo "  $database_destination"
echo "  $attachment_destination"
