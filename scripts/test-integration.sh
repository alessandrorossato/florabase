#!/usr/bin/env bash
set -euo pipefail

readonly compose_file="compose.integration.yaml"
readonly compose_project="florabase-integration-$(python3 -c 'import uuid; print(uuid.uuid4().hex[:12])')"

cleanup() {
  docker compose --project-name "${compose_project}" --file "${compose_file}" down --volumes --remove-orphans
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
docker compose \
  --project-name "${compose_project}" \
  --file "${compose_file}" \
  up --build --abort-on-container-exit --exit-code-from tests
