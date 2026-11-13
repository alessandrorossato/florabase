#!/bin/sh
set -eu
# Compose initializes volume ownership before the non-root application starts.
# CI makes pnpm's lockfile-driven replacement safe without an interactive terminal.
mkdir -p "$HOME"
if [ "${FLORABASE_QUALITY_OFFLINE:-0}" = "1" ]; then
  # Only Quality's network-disabled compose overlay opts into offline startup.
  # Validate lockfile alignment, every active package in .package-map.json, and .bin targets.
  if [ ! -f /app/node_modules/.pnpm/lock.yaml ] \
    || ! cmp -s /app/pnpm-lock.yaml /app/node_modules/.pnpm/lock.yaml \
    || ! node -e '
const fs = require("fs");
const path = require("path");
const root = "/app/node_modules";
const pkg = JSON.parse(fs.readFileSync("/app/package.json", "utf8"));
const map = JSON.parse(fs.readFileSync(path.join(root, ".package-map.json"), "utf8"));
const meta = JSON.parse(fs.readFileSync(path.join(root, ".modules.yaml"), "utf8"));
if (Array.isArray(meta.pendingBuilds) && meta.pendingBuilds.length > 0) process.exit(1);
const skipped = new Set(Array.isArray(meta.skipped) ? meta.skipped : []);
const declared = { ...(pkg.dependencies || {}), ...(pkg.devDependencies || {}) };
for (const name of Object.keys(declared)) {
  if (!fs.existsSync(path.join(root, name, "package.json"))) process.exit(1);
}
const entries = Object.entries(map.packages || {});
if (entries.length < 2) process.exit(1);
for (const [key, entry] of entries) {
  if (key === "." || skipped.has(key)) continue;
  const target = path.resolve(root, entry.url || "");
  if (
    !target.startsWith(root + "/")
    || !fs.existsSync(path.join(target, "package.json"))
  ) {
    process.exit(1);
  }
}
const bins = fs.readdirSync(path.join(root, ".bin"));
if (bins.length === 0) process.exit(1);
for (const bin of bins) {
  if (!fs.existsSync(path.join(root, ".bin", bin))) process.exit(1);
}
'; then
    echo "florabase-dev-entrypoint: Quality frontend dependencies are incomplete or out of sync with pnpm-lock.yaml; rebuild or reinitialize Quality state" >&2
    exit 1
  fi
  exec "$@"
fi
export CI=true
pnpm install --frozen-lockfile --prefer-offline
exec "$@"
