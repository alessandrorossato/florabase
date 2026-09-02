#!/usr/bin/env bash
set -euo pipefail

fail() {
  printf 'feature-finish: %s\n' "$*" >&2
  exit 1
}

branch="$(git branch --show-current)"
[[ -n "${branch}" ]] || fail "detached HEAD is not supported"
[[ "${branch}" != "main" ]] || fail "run this command from the merged feature branch, not main"
[[ -z "$(git status --porcelain)" ]] || fail "working tree is not clean"
git remote get-url origin >/dev/null 2>&1 || fail "origin remote is required"
command -v gh >/dev/null 2>&1 || fail "GitHub CLI is required to verify the squash-merged PR"

branch_oid="$(git rev-parse HEAD)"
git fetch --prune origin
git show-ref --verify --quiet refs/remotes/origin/main || fail "origin/main is required"

gh auth status >/dev/null 2>&1 || fail "GitHub CLI authentication is unavailable"
pr_state="$({
  gh pr view "${branch}" \
    --json state,baseRefName,headRefName,headRefOid,mergeCommit \
    --jq '[.state, .baseRefName, .headRefName, .headRefOid, .mergeCommit.oid] | join("|")'
} 2>/dev/null)" || fail "could not establish pull-request merge state"
IFS='|' read -r state base_ref head_ref head_oid merge_oid <<<"${pr_state}"

[[ "${state}" == "MERGED" ]] || fail "pull request for ${branch} is not merged"
[[ "${base_ref}" == "main" && "${head_ref}" == "${branch}" ]] ||
  fail "merged pull request does not match ${branch} into main"
[[ "${head_oid}" == "${branch_oid}" ]] ||
  fail "local branch changed after the pull request head was merged"
[[ -n "${merge_oid}" ]] || fail "merged pull request has no merge commit to verify"
git merge-base --is-ancestor "${merge_oid}" origin/main ||
  fail "the pull request merge commit is not present on origin/main"
git merge-base --is-ancestor main origin/main ||
  fail "local main cannot be fast-forwarded cleanly to origin/main"

git switch main
git merge --ff-only origin/main
# A squash-merged branch is not an ancestor of main. GitHub state and both exact OIDs were checked
# above, so delete the unchanged local ref atomically without using force-delete.
git update-ref -d "refs/heads/${branch}" "${branch_oid}"
git fetch --prune origin
git status --short --branch
