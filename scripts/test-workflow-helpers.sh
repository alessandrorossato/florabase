#!/usr/bin/env bash
set -euo pipefail

readonly repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly feature_start="${repository_root}/scripts/feature-start.sh"
readonly feature_finish="${repository_root}/scripts/feature-finish.sh"
temporary_root="$(mktemp -d)"
trap 'rm -rf "${temporary_root}"' EXIT

fail() {
  printf 'workflow helper tests: %s\n' "$*" >&2
  exit 1
}

assert_attachment_configuration() {
  local compose="${repository_root}/compose.yaml"
  local development="${repository_root}/compose.dev.yaml"
  local integration="${repository_root}/compose.integration.yaml"
  local nginx="${repository_root}/frontend/nginx.conf"
  local dockerfile="${repository_root}/backend/Dockerfile"
  local backup="${repository_root}/scripts/backup.sh"
  local restore="${repository_root}/scripts/restore.sh"
  local makefile="${repository_root}/Makefile"

  [[ "$(grep -Fc 'attachment_data:/var/lib/florabase/attachments' "${compose}")" -eq 1 ]] ||
    fail "production attachment volume must be mounted exactly once"
  grep -Fq 'attachment_data:' "${compose}" || fail "production attachment volume is not declared"
  grep -Fq 'FLORABASE_ATTACHMENT_STORAGE_ROOT: /tmp/florabase-attachments' "${development}" ||
    fail "development attachment storage override is missing"
  grep -Fq 'FLORABASE_ATTACHMENT_STORAGE_ROOT: /tmp/florabase-attachments' "${integration}" ||
    fail "integration attachment storage override is missing"
  grep -Fq 'client_max_body_size 32m;' "${nginx}" || fail "proxy upload ceiling is missing"
  grep -Fq -- '--owner=10001 --group=10001 --mode=0700' "${dockerfile}" ||
    fail "attachment directory is not created for the runtime user"
  grep -Fq 'USER florabase' "${dockerfile}" || fail "backend runtime is not non-root"

  grep -Fq 'docker compose stop backend' "${backup}" || fail "backup does not quiesce writes"
  grep -Fq 'attachment_artifacts.py verify' "${backup}" || fail "backup does not verify content"
  grep -Fq 'attachment_artifacts.py archive' "${backup}" || fail "backup does not archive content"
  grep -Fq '.attachments.tar' "${backup}" || fail "backup does not create paired artifacts"
  grep -Fq 'ATTACHMENTS_FILE' "${restore}" || fail "restore does not require attachment content"
  grep -Fq 'attachment_artifacts.py restore' "${restore}" || fail "restore does not restore content"
  grep -Fq 'attachment_artifacts.py verify' "${restore}" || fail "restore does not verify content"
  grep -Fq 'ATTACHMENTS_FILE' "${makefile}" || fail "Make restore does not pass the content artifact"
}

expect_failure() {
  if "$@" >/dev/null 2>&1; then
    fail "expected failure: $*"
  fi
}

assert_attachment_configuration

database_backup="${temporary_root}/florabase-20260913T120000Z.dump"
mismatched_attachment_backup="${temporary_root}/florabase-20260913T120001Z.attachments.tar"
touch "${database_backup}" "${mismatched_attachment_backup}"
expect_failure env FILE="${database_backup}" ATTACHMENTS_FILE="${mismatched_attachment_backup}" \
  CONFIRM_REPLACE=yes "${repository_root}/scripts/restore.sh"

new_fixture() {
  local name="$1"
  local remote="${temporary_root}/${name}-remote.git"
  local seed="${temporary_root}/${name}-seed"
  local work="${temporary_root}/${name}-work"

  git init --bare --initial-branch=main "${remote}" >/dev/null
  git init --initial-branch=main "${seed}" >/dev/null
  git -C "${seed}" config user.name "Workflow Test"
  git -C "${seed}" config user.email "workflow@example.invalid"
  printf 'base\n' >"${seed}/tracked.txt"
  git -C "${seed}" add tracked.txt
  git -C "${seed}" commit -m base >/dev/null
  git -C "${seed}" remote add origin "${remote}"
  git -C "${seed}" push --set-upstream origin main >/dev/null
  git clone "${remote}" "${work}" >/dev/null 2>&1
  git -C "${work}" config user.name "Workflow Test"
  git -C "${work}" config user.email "workflow@example.invalid"
  printf '%s\n' "${seed}|${work}|${remote}"
}

IFS='|' read -r seed work remote <<<"$(new_fixture start)"
expect_failure env -C "${work}" "${feature_start}"
printf 'dirty\n' >>"${work}/tracked.txt"
expect_failure env -C "${work}" BRANCH=feat/dirty "${feature_start}"
git -C "${work}" restore tracked.txt
printf 'updated\n' >>"${seed}/tracked.txt"
git -C "${seed}" commit -am update >/dev/null
git -C "${seed}" push >/dev/null
env -C "${work}" BRANCH=feat/created "${feature_start}" >/dev/null
[[ "$(git -C "${work}" branch --show-current)" == "feat/created" ]] || fail "branch was not created"
[[ "$(git -C "${work}" show HEAD:tracked.txt)" == $'base\nupdated' ]] || fail "branch did not start from updated main"
git -C "${work}" switch main >/dev/null
expect_failure env -C "${work}" BRANCH=feat/created "${feature_start}"

IFS='|' read -r seed work remote <<<"$(new_fixture divergent)"
printf 'local\n' >>"${work}/tracked.txt"
git -C "${work}" commit -am local >/dev/null
printf 'remote\n' >>"${seed}/tracked.txt"
git -C "${seed}" commit -am remote >/dev/null
git -C "${seed}" push >/dev/null
expect_failure env -C "${work}" BRANCH=feat/divergent "${feature_start}"

IFS='|' read -r seed work remote <<<"$(new_fixture finish)"
expect_failure env -C "${work}" "${feature_finish}"
git -C "${work}" switch -c feat/finish >/dev/null
printf 'feature\n' >"${work}/feature.txt"
git -C "${work}" add feature.txt
git -C "${work}" commit -m feature >/dev/null
feature_oid="$(git -C "${work}" rev-parse HEAD)"
printf 'dirty\n' >>"${work}/feature.txt"
expect_failure env -C "${work}" "${feature_finish}"
git -C "${work}" restore feature.txt

mock_bin="${temporary_root}/bin"
mkdir -p "${mock_bin}"
cat >"${mock_bin}/gh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "auth" && "${2:-}" == "status" ]]; then
  exit "${MOCK_AUTH_EXIT:-0}"
fi
if [[ "${1:-}" == "pr" && "${2:-}" == "view" ]]; then
  printf '%s\n' "${MOCK_PR_STATE:-OPEN}|main|${MOCK_HEAD_REF:-feat/finish}|${MOCK_HEAD_OID:-missing}|${MOCK_MERGE_OID:-missing}"
  exit "${MOCK_PR_EXIT:-0}"
fi
exit 1
EOF
chmod +x "${mock_bin}/gh"

expect_failure env -C "${work}" PATH="${mock_bin}:${PATH}" MOCK_PR_STATE=OPEN \
  MOCK_HEAD_OID="${feature_oid}" "${feature_finish}"
git -C "${work}" show-ref --verify --quiet refs/heads/feat/finish || fail "open PR deleted branch"
expect_failure env -C "${work}" PATH="${mock_bin}:${PATH}" MOCK_PR_EXIT=1 \
  "${feature_finish}"
git -C "${work}" show-ref --verify --quiet refs/heads/feat/finish || fail "unknown PR state deleted branch"

git -C "${work}" push --set-upstream origin feat/finish >/dev/null
git -C "${seed}" fetch origin feat/finish >/dev/null
git -C "${seed}" merge --squash origin/feat/finish >/dev/null
git -C "${seed}" commit -m 'squash feature' >/dev/null
merge_oid="$(git -C "${seed}" rev-parse HEAD)"
git -C "${seed}" push origin main >/dev/null
env -C "${work}" PATH="${mock_bin}:${PATH}" MOCK_PR_STATE=MERGED \
  MOCK_HEAD_OID="${feature_oid}" MOCK_MERGE_OID="${merge_oid}" "${feature_finish}" >/dev/null
[[ "$(git -C "${work}" branch --show-current)" == "main" ]] || fail "finish did not switch to main"
if git -C "${work}" show-ref --verify --quiet refs/heads/feat/finish; then
  fail "verified merged branch was not deleted"
fi
[[ "$(git -C "${work}" rev-parse HEAD)" == "${merge_oid}" ]] || fail "main was not updated"

dev_upgrade_plan="$(make --directory "${repository_root}" --dry-run dev-upgrade)"
[[ "$(grep -c 'alembic current' <<<"${dev_upgrade_plan}")" -eq 2 ]] || fail "dev-upgrade must show both revisions"
grep -q 'alembic upgrade head' <<<"${dev_upgrade_plan}" || fail "dev-upgrade is not wired to upgrade head"

printf 'workflow helper tests: all passed\n'
