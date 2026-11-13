#!/bin/sh
set -eu
# Compose initializes volume ownership before the non-root application starts.
# Scope CI=true to pnpm install so pnpm 11 does not auto-reinstall on every script run under network_mode: none.
mkdir -p "$HOME"
lock_copy="/app/node_modules/.pnpm/lock.yaml"
# Skip pnpm install when node_modules already matches the mounted lockfile;
# Quality containers run with network_mode: none and no mounted pnpm store.
if [ ! -d /app/node_modules/.bin ] \
  || [ ! -f "$lock_copy" ] \
  || ! cmp -s /app/pnpm-lock.yaml "$lock_copy"; then
  CI=true pnpm install --frozen-lockfile --prefer-offline
fi
exec "$@"
