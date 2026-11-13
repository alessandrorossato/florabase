#!/bin/sh
set -eu
# Compose initializes volume ownership before the non-root application starts.
# CI makes pnpm's lockfile-driven replacement safe without an interactive terminal.
mkdir -p "$HOME"
if [ "${FLORABASE_QUALITY_OFFLINE:-0}" = "1" ]; then
  # Offline Quality relies on the prepared dependency volume and rejects lockfile drift;
  # actual module and file presence is verified when each Quality tool executes.
  if [ ! -s /app/node_modules/.pnpm/lock.yaml ] \
    || ! cmp -s /app/pnpm-lock.yaml /app/node_modules/.pnpm/lock.yaml; then
    echo "florabase-dev-entrypoint: Quality frontend dependencies are missing or out of sync with pnpm-lock.yaml; run 'make quality-clean' or rebuild" >&2
    exit 1
  fi
  exec "$@"
fi
export CI=true
pnpm install --frozen-lockfile --prefer-offline
exec "$@"
