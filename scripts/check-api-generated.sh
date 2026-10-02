#!/usr/bin/env bash
set -euo pipefail

python3 ./scripts/workflow_environment.py quality compose -- run --rm --no-deps backend \
  python scripts/export_openapi.py --check
python3 ./scripts/workflow_environment.py quality compose -- run --rm --no-deps frontend \
  pnpm exec openapi-typescript ../backend/openapi.json --output src/api/schema.d.ts --check
