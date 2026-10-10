#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

fail() {
  printf 'feature-verify: %s\n' "$*" >&2
  printf 'FEATURE_VERIFICATION_FAILED\n' >&2
  exit 1
}

run_stage() {
  local name="$1"
  shift
  printf '\n== feature verification: %s ==\n' "${name}"
  "$@" || fail "stage failed: ${name}"
}

[[ "$#" -le 1 ]] || fail "only --full is supported"

command -v git >/dev/null 2>&1 || fail "git is required"
command -v make >/dev/null 2>&1 || fail "make is required"
command -v python3 >/dev/null 2>&1 || fail "python3 is required"
branch="$(git branch --show-current)"
[[ -n "${branch}" ]] || fail "detached HEAD is not supported"
[[ "${branch}" != "main" ]] || fail "run this command from a feature branch, not main"
[[ "${branch}" =~ ^(feat|fix|docs|ci)/[a-z0-9][a-z0-9._-]*$ ]] ||
  fail "branch must use feat/, fix/, docs/, or ci/ followed by a safe lowercase name"
git remote get-url origin >/dev/null 2>&1 || fail "origin remote is required"
python3 ./scripts/feature-tree-fingerprint.py invalidate
git fetch origin main || fail "could not fetch origin/main"
git show-ref --verify --quiet refs/remotes/origin/main || fail "origin/main is required"
git merge-base --is-ancestor origin/main HEAD ||
  fail "branch does not contain origin/main; rebase or merge deliberately before verification"
base_sha="$(git merge-base origin/main HEAD)"
initial_digest="$(python3 ./scripts/feature-tree-fingerprint.py digest)"

execution="$(mktemp)"
trap 'rm -f "${execution}"' EXIT
mode_args=()
case "${1:-}" in
  "") ;;
  --full) mode_args+=(--full) ;;
  *) fail "only --full is supported; focused checks cannot produce a delivery receipt" ;;
esac
run_stage "selected gate" python3 ./scripts/verification_gate.py --base "${base_sha}" "${mode_args[@]}" --execution "${execution}"
[[ "$(python3 ./scripts/feature-tree-fingerprint.py digest)" == "${initial_digest}" ]] ||
  fail "source tree changed during verification; freeze the tree and rerun make feature-verify"
run_stage "verification receipt" python3 ./scripts/feature-tree-fingerprint.py write --branch "${branch}" --base "${base_sha}" --execution "${execution}"

printf '\nFEATURE_VERIFICATION_PASSED\n'
