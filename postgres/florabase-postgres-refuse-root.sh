#!/bin/sh
# Florabase PostgreSQL has no gosu: the upstream root branch (prepare directories as root, then
# drop privileges) cannot work. Called first by every entry point, before anything touches disk.
if [ "$(id -u)" = "0" ]; then
    echo "florabase-postgres: refusing to run as root. This image has no gosu and supports only" \
        "the postgres account (uid/gid 70:70); the Florabase stack sets user: \"70:70\"." >&2
    exit 64
fi
