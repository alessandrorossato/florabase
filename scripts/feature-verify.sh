#!/usr/bin/env bash
set -euo pipefail

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

check_whitespace() {
  git diff --check
  git diff --cached --check
}

command -v git >/dev/null 2>&1 || fail "git is required"
command -v make >/dev/null 2>&1 || fail "make is required"
command -v python3 >/dev/null 2>&1 || fail "python3 is required"
command -v docker >/dev/null 2>&1 || fail "docker is required"
branch="$(git branch --show-current)"
[[ -n "${branch}" ]] || fail "detached HEAD is not supported"
[[ "${branch}" != "main" ]] || fail "run this command from a feature branch, not main"
[[ "${branch}" =~ ^(feat|fix|docs|ci)/[a-z0-9][a-z0-9._-]*$ ]] ||
  fail "branch must use feat/, fix/, docs/, or ci/ followed by a safe lowercase name"
git remote get-url origin >/dev/null 2>&1 || fail "origin remote is required"
git fetch origin main || fail "could not fetch origin/main"
git show-ref --verify --quiet refs/remotes/origin/main || fail "origin/main is required"
git merge-base --is-ancestor origin/main HEAD ||
  fail "branch does not contain origin/main; rebase or merge deliberately before verification"
base_sha="$(git merge-base origin/main HEAD)"

run_stage "feature graph" python3 ./scripts/check-features.py
run_stage "workflow helpers" make test-workflow-helpers
run_stage "feature workflow helpers" make test-feature-workflow
run_stage "quality" make check
run_stage "integration" make test-integration
run_stage "production builds" make build
run_stage "migration cycle" ./scripts/verify-migration-cycle.sh "${base_sha}"
run_stage "whitespace errors" check_whitespace
run_stage "verification receipt" python3 ./scripts/feature-tree-fingerprint.py write --branch "${branch}" --base "${base_sha}"

printf '\nFEATURE_VERIFICATION_PASSED\n'
