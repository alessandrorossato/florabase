#!/usr/bin/env bash
set -euo pipefail

fail() {
  printf 'migration verification: %s\n' "$*" >&2
  exit 1
}

readonly base_sha="$1"
readonly changed_migrations="$({
  git diff --name-only "${base_sha}" -- backend/alembic/versions
  git ls-files --others --exclude-standard -- backend/alembic/versions
} | grep '\.py$' | sort -u || true)"
if [[ -z "${changed_migrations}" ]]; then
  printf 'migration verification: no Alembic revisions added\n'
  exit 0
fi

readonly base_revision="$(python3 - "${base_sha}" <<'PY'
from __future__ import annotations

import ast
import subprocess
import sys

base = sys.argv[1]
paths = subprocess.run(
    ["git", "ls-tree", "-r", "--name-only", base, "backend/alembic/versions"],
    check=True, text=True, stdout=subprocess.PIPE,
).stdout.splitlines()
revisions: set[str] = set()
referenced: set[str] = set()
for path in paths:
    source = subprocess.run(
        ["git", "show", f"{base}:{path}"], check=True, text=True, stdout=subprocess.PIPE,
    ).stdout
    module = ast.parse(source)
    values = {
        node.target.id: ast.literal_eval(node.value)
        for node in module.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id in {"revision", "down_revision"}
        and isinstance(node.value, (ast.Constant, ast.Tuple, ast.List))
    }
    revision = values.get("revision")
    down_revision = values.get("down_revision")
    if not isinstance(revision, str):
        raise SystemExit(f"migration {path} has no literal revision")
    revisions.add(revision)
    if isinstance(down_revision, str):
        referenced.add(down_revision)
    elif isinstance(down_revision, (tuple, list)):
        referenced.update(item for item in down_revision if isinstance(item, str))
heads = sorted(revisions - referenced)
if len(heads) != 1:
    raise SystemExit(f"expected one Alembic head at {base}, found {heads}")
print(heads[0])
PY
)" || fail "could not determine the previous main Alembic head"

readonly project="florabase-feature-migration-$$"
cleanup() {
  docker compose --project-name "${project}" --file compose.integration.yaml down --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

printf 'migration verification: revisions added; cycling %s -> head -> %s -> head in disposable PostgreSQL\n' "${base_revision}" "${base_revision}"
docker compose --project-name "${project}" --file compose.integration.yaml run --rm tests \
  /bin/sh -ec "alembic upgrade '${base_revision}'; alembic upgrade head; alembic downgrade '${base_revision}'; alembic upgrade head"
printf 'migration verification: passed\n'
