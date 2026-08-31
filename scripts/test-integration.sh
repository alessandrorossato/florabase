#!/usr/bin/env bash
set -euo pipefail

readonly compose_file="compose.integration.yaml"
readonly compose_project="florabase-integration"

cleanup() {
  docker compose --project-name "${compose_project}" --file "${compose_file}" down --volumes --remove-orphans
}

trap cleanup EXIT INT TERM
cleanup
docker compose \
  --project-name "${compose_project}" \
  --file "${compose_file}" \
  up --build --abort-on-container-exit --exit-code-from tests
