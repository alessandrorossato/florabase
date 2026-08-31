#!/usr/bin/env bash
set -euo pipefail

base_url="http://${APP_BIND_ADDRESS:-127.0.0.1}:${APP_PORT:-8080}"
curl --fail --silent --show-error "$base_url/healthz" >/dev/null
curl --fail --silent --show-error "$base_url/api/v1/health"
echo
curl --fail --silent --show-error "$base_url/api/v1/ready"
echo
