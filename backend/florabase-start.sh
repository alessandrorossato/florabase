#!/bin/sh
set -eu
# Production compose.yaml start sequence (ADR 0009):
# 1. Wait for PostgreSQL (bounded retry with pg_isready).
# 2. Run the separate guarded deploy step (paths, ownership, lock, init/keep/dump+upgrade,
#    marker, first owner).
# 3. Scrub one-time owner variables from the server process and exec the exact-head guard.
backoff="${FLORABASE_REFUSAL_BACKOFF_SECONDS:-3}"

fail_with_backoff() {
    if [ "$backoff" != "0" ]; then
        sleep "$backoff"
    fi
    exit 1
}

python -m florabase.db.release_schema wait-db || fail_with_backoff
python -m florabase.db.release_schema deploy || fail_with_backoff
unset FLORABASE_OWNER_LOGIN FLORABASE_OWNER_PASSWORD
exec python -m florabase.db.release_schema serve
