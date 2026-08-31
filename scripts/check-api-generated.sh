#!/usr/bin/env bash
set -euo pipefail

temporary_dir="$(mktemp -d)"
cp backend/openapi.json "$temporary_dir/openapi.json"
cp frontend/src/api/schema.d.ts "$temporary_dir/schema.d.ts"
restore_generated_files() {
  cp "$temporary_dir/openapi.json" backend/openapi.json
  cp "$temporary_dir/schema.d.ts" frontend/src/api/schema.d.ts
  rm -rf "$temporary_dir"
}
trap restore_generated_files EXIT

docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend python scripts/export_openapi.py
docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps frontend pnpm api:generate

cmp "$temporary_dir/openapi.json" backend/openapi.json
cmp "$temporary_dir/schema.d.ts" frontend/src/api/schema.d.ts
