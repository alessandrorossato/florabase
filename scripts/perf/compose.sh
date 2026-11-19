#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
# Never load the operator's .env; fixed project and disposable credentials.
LOCK_DIR="${FLORABASE_LOCK_DIR:-$HOME/.local/state/florabase/locks}"
if [ -z "${FLORABASE_PERF_LOCK_FD:-}" ] || [ ! -e "/proc/$$/fd/${FLORABASE_PERF_LOCK_FD}" ]; then
  mkdir -p "$LOCK_DIR"
  exec 9>"$LOCK_DIR/florabase-perf.lock"
  if ! flock -n 9; then
    echo "florabase-perf lifecycle lock is held by another invocation; wait and retry" >&2
    exit 1
  fi
fi
export POSTGRES_DB=florabase_perf POSTGRES_USER=florabase_perf
export POSTGRES_PASSWORD=disposable-perf-password
export FLORABASE_DATABASE_URL=postgresql+psycopg://florabase_perf:disposable-perf-password@db:5432/florabase_perf
export FLORABASE_CANONICAL_ORIGIN=http://localhost:18080
exec docker compose --env-file /dev/null --project-name florabase-perf \
  --file compose.yaml --file compose.perf.yaml "$@"
