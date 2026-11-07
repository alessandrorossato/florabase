#!/bin/sh
# Florabase PostgreSQL entrypoint: refuse root, then run the upstream entrypoint unchanged.
florabase-postgres-refuse-root || exit 64
exec docker-entrypoint.sh "$@"
