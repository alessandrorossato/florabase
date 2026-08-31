#!/usr/bin/env bash
set -euo pipefail

backup_dir="${BACKUP_DIR:-backups}"
mkdir -p "$backup_dir"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
destination="$backup_dir/florabase-$timestamp.dump"
temporary="$destination.partial.$$"
trap 'rm -f "$temporary"' EXIT

if [[ -e "$destination" ]]; then
  echo "Refusing to overwrite existing backup: $destination" >&2
  exit 1
fi

docker compose exec -T db sh -c \
  'pg_dump --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --format=custom --no-owner --no-privileges' \
  >"$temporary"

test -s "$temporary"
docker compose exec -T db pg_restore --list <"$temporary" >/dev/null
mv --no-clobber "$temporary" "$destination"
trap - EXIT
echo "Created $destination"
