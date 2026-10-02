#!/bin/sh
set -eu
# Compose initializes volume ownership before the non-root application starts.
# CI makes pnpm's lockfile-driven replacement safe without an interactive terminal.
export CI=true
mkdir -p "$HOME"
pnpm install --frozen-lockfile --prefer-offline
exec "$@"
