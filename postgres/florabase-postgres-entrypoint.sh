#!/bin/sh
# Florabase PostgreSQL entrypoint guard. This image has no gosu, so the upstream root branch
# (prepare directories as root, then drop privileges) cannot work. Refuse before the upstream
# entrypoint creates, chowns or initializes anything.
if [ "$(id -u)" = "0" ]; then
    echo "florabase-postgres: refusing to run as root. This image has no gosu and supports only" \
        "the postgres account (uid/gid 70:70); the Florabase stack sets user: \"70:70\"." >&2
    exit 64
fi
exec docker-entrypoint.sh "$@"
