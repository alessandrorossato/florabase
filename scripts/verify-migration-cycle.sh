#!/usr/bin/env bash
set -euo pipefail
exec python3 ./scripts/disposable_workflow.py feature-migration --base "${1:?base SHA required}" "${@:2}"
