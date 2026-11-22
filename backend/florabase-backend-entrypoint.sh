#!/bin/sh
set -eu
# Accept the single stack database password variable for libpq tools and SQLAlchemy.
if [ -z "${PGPASSWORD:-}" ] && [ -n "${FLORABASE_DB_PASSWORD:-}" ]; then
    export PGPASSWORD="$FLORABASE_DB_PASSWORD"
fi
exec "$@"
