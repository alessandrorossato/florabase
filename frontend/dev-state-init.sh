#!/bin/sh
set -eu
# Only these project-local named volumes are writable here; no source bind mounts.
chown -R "${LOCAL_UID:-1000}:${LOCAL_GID:-1000}" /app/node_modules /state/attachments
chmod 0700 /state/attachments
