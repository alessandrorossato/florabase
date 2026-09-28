#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
# Never load the operator's .env; fixed project and disposable credentials.
export POSTGRES_DB=florabase_perf POSTGRES_USER=florabase_perf
export POSTGRES_PASSWORD=disposable-perf-password
export FLORABASE_DATABASE_URL=postgresql+psycopg://florabase_perf:disposable-perf-password@db:5432/florabase_perf
export FLORABASE_CANONICAL_ORIGIN=http://localhost:18080
exec docker compose --env-file /dev/null --project-name florabase-perf \
  --file compose.yaml --file compose.perf.yaml "$@"
