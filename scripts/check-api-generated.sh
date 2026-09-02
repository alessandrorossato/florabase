#!/usr/bin/env bash
set -euo pipefail

docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend \
  python scripts/export_openapi.py --check
docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps frontend \
  pnpm exec openapi-typescript ../backend/openapi.json --output src/api/schema.d.ts --check
