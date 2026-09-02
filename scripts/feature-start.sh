#!/usr/bin/env bash
set -euo pipefail

branch="${BRANCH:-}"

fail() {
  printf 'feature-start: %s\n' "$*" >&2
  exit 1
}

[[ -n "${branch}" ]] || fail "BRANCH is required (for example, BRANCH=feat/event-001)"
[[ "${branch}" =~ ^(feat|fix|docs|ci)/[a-z0-9][a-z0-9._-]*$ ]] ||
  fail "BRANCH must use feat/, fix/, docs/, or ci/ followed by a safe lowercase name"
[[ -z "$(git status --porcelain)" ]] || fail "working tree is not clean"
git remote get-url origin >/dev/null 2>&1 || fail "origin remote is required"

git fetch --prune origin
git show-ref --verify --quiet refs/heads/main || fail "local main branch is required"
git show-ref --verify --quiet refs/remotes/origin/main || fail "origin/main is required"
git show-ref --verify --quiet "refs/heads/${branch}" && fail "local branch ${branch} already exists"
git show-ref --verify --quiet "refs/remotes/origin/${branch}" &&
  fail "remote branch origin/${branch} already exists"
git merge-base --is-ancestor main origin/main ||
  fail "local main cannot be fast-forwarded cleanly to origin/main"

git switch main
git merge --ff-only origin/main
git switch --create "${branch}"
git status --short --branch
