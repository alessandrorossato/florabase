#!/usr/bin/env bash
set -euo pipefail
# Arguments are validated exact test file selections; no arguments retains the complete suite.
args=()
for suite in "$@"; do args+=(--suite "${suite}"); done
exec python3 ./scripts/disposable_workflow.py integration "${args[@]}"
