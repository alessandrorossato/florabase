#!/usr/bin/env python3
"""Isolated integration, migration and build invocations with verified automatic retirement."""

from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from workflow_resources import Disposable, Owner, ResourceError

MIGRATION_REPORT = "MIGRATION_CYCLE_PASSED "
SCHEMA_REPORT = "MIGRATION_SCHEMA_VERIFIED "


def base_revision(base: str) -> str:
    paths = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", base, "backend/alembic/versions"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.splitlines()
    return migration_head(
        [
            (
                path,
                subprocess.run(
                    ["git", "show", f"{base}:{path}"], check=True, text=True, stdout=subprocess.PIPE
                ).stdout,
            )
            for path in paths
        ]
    )


def migration_head(sources: list[tuple[str, str]]) -> str:
    revisions: set[str] = set()
    referenced: set[str] = set()
    for path, source in sources:
        values: dict[str, Any] = {}
        for node in ast.parse(source).body:
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                name, value = node.target.id, node.value
            elif (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
            ):
                name, value = node.targets[0].id, node.value
            else:
                continue
            if name in {"revision", "down_revision"} and value is not None:
                values[name] = ast.literal_eval(value)
        revision = values.get("revision")
        if not isinstance(revision, str) or not all(c.isalnum() or c == "_" for c in revision):
            raise ResourceError(f"invalid literal migration revision: {path}")
        revisions.add(revision)
        parent = values.get("down_revision")
        referenced.update([parent] if isinstance(parent, str) else parent or [])
    heads = sorted(revisions - referenced)
    if len(heads) != 1:
        raise ResourceError(f"expected one migration head, found {heads}")
    return heads[0]


def expected_migration_evidence(base: str) -> dict[str, Any]:
    revision = base_revision(base)
    head = migration_head(
        [(str(p), p.read_text()) for p in sorted(Path("backend/alembic/versions").glob("*.py"))]
    )
    return {
        "cycle_executed": True,
        "result": "passed",
        "verified_revisions": [revision, head, revision, head],
        "cleanup_verified": True,
    }


def safe_suites(paths: list[str], root: Path) -> list[str]:
    if not paths:
        return []
    safe: list[str] = []
    for path in paths:
        value = Path(path)
        if (
            value.is_absolute()
            or ".." in value.parts
            or not path.startswith("backend/tests/integration/test_")
            or value.suffix != ".py"
            or not (root / value).is_file()
        ):
            raise ResourceError(f"integration selection must name existing test files: {path}")
        safe.append(str(value.relative_to("backend")))
    return sorted(set(safe))


def execute(
    role: str, *, base: str = "", suites: list[str] | None = None, builds: list[str] | None = None
) -> None:
    root = Path.cwd().resolve()
    selected = safe_suites(suites or [], root)
    evidence = expected_migration_evidence(base) if role == "feature-migration" else None
    revision = evidence["verified_revisions"][0] if evidence else ""
    owner = Owner.disposable(role, root)
    # Labels are applied to all resources before creation, including built image outputs.
    services = ["backend", "frontend"] if role == "verification-build" else ["db", "tests"]
    labels = {
        key: value for key, value in owner.labels().items() if key != "com.docker.compose.project"
    }
    override: dict[str, Any] = {
        "services": {name: {"labels": labels} for name in services},
        "networks": {
            ("internal" if role == "verification-build" else "integration"): {"labels": labels}
        },
    }
    for service in services:
        if service != "db":
            override["services"][service]["build"] = {"labels": owner.labels()}
            override["services"][service]["image"] = f"{owner.project}-{service}"
    if role == "verification-build":
        override["volumes"] = {
            key: {"labels": labels} for key in ("postgres_data", "attachment_data")
        }
    if selected:
        override["services"]["tests"]["command"] = [
            "/bin/sh",
            "-ec",
            "python -c 'from florabase.core.config import get_settings; from florabase.db.testing import require_disposable_test_database; require_disposable_test_database(get_settings())'; alembic upgrade head; exec pytest --no-cov -m integration \"$@\"",
            "selected-integration",
            *selected,
        ]
    with tempfile.TemporaryDirectory(prefix="florabase-disposable-config-") as temporary:
        path = Path(temporary) / "ownership.json"
        path.write_text(json.dumps(override))
        env = {k: v for k, v in os.environ.items() if not k.startswith("COMPOSE_")}
        if role == "verification-build":
            env.update(
                POSTGRES_DB="build_only",
                POSTGRES_USER="build_only",
                POSTGRES_PASSWORD="disposable-build-only",
                FLORABASE_DATABASE_URL="postgresql+psycopg://build_only:disposable-build-only@db:5432/build_only",
            )
        command = [
            "docker",
            "compose",
            "--env-file",
            "/dev/null",
            "--project-name",
            owner.project,
            "--project-directory",
            str(root),
            "--file",
            str(
                root
                / ("compose.yaml" if role == "verification-build" else "compose.integration.yaml")
            ),
            "--file",
            str(path),
        ]
        try:
            with Disposable(owner):
                if role == "verification-build":
                    action = ["build", *(builds or ["backend", "frontend"])]
                elif role == "feature-migration":
                    print(
                        f"migration verification: cycling {revision} -> head -> {revision} -> head",
                        flush=True,
                    )
                    action = [
                        "run",
                        "--rm",
                        "--build",
                        "-T",
                        "tests",
                        "python",
                        "scripts/verify_migration_cycle.py",
                        revision,
                    ]
                else:
                    action = [
                        "up",
                        "--build",
                        "--abort-on-container-exit",
                        "--exit-code-from",
                        "tests",
                    ]
                print("Executing: " + " ".join([*command, *action]), flush=True)
                result = subprocess.run(
                    [*command, *action],
                    env=env,
                    check=True,
                    text=True,
                    stdout=subprocess.PIPE if evidence else None,
                )
                if evidence:
                    print(result.stdout, end="", flush=True)
                    reports = [
                        line.removeprefix(SCHEMA_REPORT)
                        for line in result.stdout.splitlines()
                        if line.startswith(SCHEMA_REPORT)
                    ]
                    if (
                        len(reports) != 1
                        or json.loads(reports[0]) != evidence["verified_revisions"]
                    ):
                        raise ResourceError(
                            "migration schema execution evidence missing or mismatched"
                        )
            # Emitted only after the database commands AND verified ownership cleanup succeed.
            if evidence:
                print(MIGRATION_REPORT + json.dumps(evidence, sort_keys=True), flush=True)
        except BaseException:
            print(
                f"Recovery: python3 scripts/workflow_resources.py cleanup-disposable --project {owner.project} --role {owner.role} --owner {owner.identity}",
                file=sys.stderr,
            )
            raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("role", choices=["integration", "feature-migration", "verification-build"])
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--force-cycle", action="store_true")
    parser.add_argument("--suite", action="append", default=[])
    parser.add_argument("--build", action="append", choices=["backend", "frontend"], default=[])
    args = parser.parse_args()
    try:
        if args.role == "feature-migration" and not args.force_cycle:
            from verification_impact import changed_paths

            if not any(
                p.startswith("backend/alembic/versions/") and p.endswith(".py")
                for p in changed_paths(args.base)
            ):
                print("migration verification: no Alembic revisions added")
                return 0
        execute(args.role, base=args.base, suites=args.suite, builds=args.build)
    except (ResourceError, subprocess.CalledProcessError, OSError, ValueError) as error:
        print(
            f"disposable workflow failed: {error}; inspect make workflow-resources", file=sys.stderr
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
