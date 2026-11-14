#!/bin/sh
set -eu
# Compose initializes volume ownership before the non-root application starts.
# CI makes pnpm's lockfile-driven replacement safe without an interactive terminal.
mkdir -p "$HOME"
if [ "${FLORABASE_QUALITY_OFFLINE:-0}" = "1" ]; then
  # Offline Quality validates Florabase's own lockfile provenance marker
  # (written at image build time when dependencies were installed), rather than
  # pnpm's internal lockfile/metadata; requested tools verify package presence.
  lock_marker=/app/node_modules/.florabase-pnpm-lock.sha256
  if [ ! -r /app/pnpm-lock.yaml ] \
    || [ ! -s /app/pnpm-lock.yaml ] \
    || [ ! -r "$lock_marker" ] \
    || [ ! -s "$lock_marker" ] \
    || [ "$(cat "$lock_marker")" != "$(sha256sum /app/pnpm-lock.yaml | cut -d' ' -f1)" ]; then
    echo "florabase-dev-entrypoint: Quality frontend dependency marker is missing or out of sync with pnpm-lock.yaml; run 'make quality-clean' to safely reinitialize only this worktree's Quality state" >&2
    exit 1
  fi
  exec "$@"
fi
export CI=true
pnpm install --frozen-lockfile --prefer-offline
exec "$@"
