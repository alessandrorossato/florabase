#!/usr/bin/env python3
"""Focused real PostgreSQL cycle regression on synthetic Git/Docker fixtures; no receipt."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from disposable_workflow import (
    MIGRATION_REPORT,
    base_revision,
    expected_migration_evidence,
)
from verification_gate import checks_for
from verification_impact import make_plan
from workflow_resources import Owner, Resources, docker

ROOT = Path(__file__).resolve().parent.parent


def protected_signature() -> dict[str, Any]:
    return {
        project: {
            kind: docker(*command, "--filter", f"label=com.docker.compose.project={project}")
            for kind, command in (
                ("containers", ["ps", "-aq", "--no-trunc"]),
                ("networks", ["network", "ls", "-q"]),
                ("volumes", ["volume", "ls", "-q"]),
            )
        }
        for project in (
            "florabase",
            "florabase-dev",
            "florabase-feature-review",
            "florabase-uat-preview",
            "florabase-preview",
            "florabase-prod",
        )
    }


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, text=True, capture_output=True
    ).stdout.strip()


def run_cycle(base: str, *, failure: bool = False, forced: bool = False) -> dict[str, Any]:
    plan = make_plan(base, force_full=forced)
    if plan["mode"] != "full" or plan["migration"] != "full-cycle":
        raise RuntimeError("fixture did not select exhaustive migration verification")
    check = next(c for c in checks_for(plan) if c["id"] == "migration-cycle")
    result = subprocess.run(check["command"], text=True, capture_output=True)
    print(result.stdout, end="", flush=True)
    print(result.stderr, end="", flush=True)
    if (result.returncode != 0) != failure:
        raise RuntimeError(f"unexpected migration result {result.returncode}")
    if failure and (
        "synthetic existing-chain failure" not in result.stderr or MIGRATION_REPORT in result.stdout
    ):
        raise RuntimeError("failed chain was not rejected without success evidence")
    reports = [
        json.loads(line.removeprefix(MIGRATION_REPORT))
        for line in result.stdout.splitlines()
        if line.startswith(MIGRATION_REPORT)
    ]
    if not failure and reports != [expected_migration_evidence(base)]:
        raise RuntimeError("successful migration did not report all verified states and cleanup")
    owners = [line for line in result.stdout.splitlines() if line.startswith("Cleanup registered:")]
    if len(owners) != 1:
        raise RuntimeError("missing exact run ownership")
    fields = owners[0].split()
    owner = Owner(
        fields[2], "feature-migration", str(Path.cwd().resolve()), fields[3].removeprefix("owner=")
    )
    if any(Resources(owner).inventory().values()):
        raise RuntimeError("migration fixture has residual owned resources")
    if "RESOURCE_CLEANUP_PASSED" not in result.stdout:
        raise RuntimeError("migration cleanup did not pass")
    return {
        "plan": plan,
        "command": check["command"],
        "returncode": result.returncode,
        "project": owner.project,
        "residuals": 0,
        "evidence": reports[0] if reports else None,
    }


def main() -> None:
    before = protected_signature()
    previous = Path.cwd()
    results = []
    try:
        with tempfile.TemporaryDirectory(prefix="florabase-migration-smoke-") as temporary:
            fixture = Path(temporary) / "source"
            subprocess.run(
                ["git", "clone", "--quiet", "--no-hardlinks", str(ROOT), str(fixture)], check=True
            )
            git(fixture, "config", "user.name", "Synthetic smoke")
            git(fixture, "config", "user.email", "smoke@example.invalid")
            for path in (
                "scripts/disposable_workflow.py",
                "scripts/verification_impact.py",
                "scripts/verification_gate.py",
                "scripts/feature-tree-fingerprint.py",
                "backend/scripts/verify_migration_cycle.py",
            ):
                shutil.copy2(ROOT / path, fixture / path)
            git(fixture, "add", ".")
            git(fixture, "commit", "-m", "synthetic verification baseline")
            os.chdir(fixture)
            base = git(fixture, "rev-parse", "HEAD")
            lock = fixture / "frontend/pnpm-lock.yaml"
            lock.write_text(lock.read_text() + "\n# synthetic dependency impact\n")
            if make_plan(base)["changed_paths"] != ["frontend/pnpm-lock.yaml"]:
                raise RuntimeError("dependency regression fixture contains other differences")
            results.append(run_cycle(base))
            results.append(run_cycle(base, forced=True))

            # Exercise a nontrivial downgrade/re-upgrade in this disposable source only.
            revision = base_revision(base)
            added = fixture / "backend/alembic/versions/synthetic_cycle.py"
            added.write_text(
                "from alembic import op\n"
                f"revision = 'synthetic_cycle'\ndown_revision = {revision!r}\n"
                "def upgrade():\n    op.execute('CREATE TABLE synthetic_cycle_probe (id integer)')\n"
                "def downgrade():\n    op.execute('DROP TABLE synthetic_cycle_probe')\n"
            )
            results.append(run_cycle(base))
            added.unlink()
            git(fixture, "restore", "frontend/pnpm-lock.yaml")

            # The broken upgrade is already in the fixture base. There is NO feature migration diff.
            existing = sorted((fixture / "backend/alembic/versions").glob("*.py"))[0]
            existing.write_text(
                existing.read_text().replace(
                    "def upgrade() -> None:",
                    "def upgrade() -> None:\n    raise RuntimeError('synthetic existing-chain failure')",
                    1,
                )
            )
            if "synthetic existing-chain failure" not in existing.read_text():
                raise RuntimeError("could not prepare broken existing-chain fixture")
            git(fixture, "add", ".")
            git(fixture, "commit", "-m", "synthetic broken existing migration baseline")
            broken_base = git(fixture, "rev-parse", "HEAD")
            lock.write_text(lock.read_text() + "\n# synthetic dependency impact\n")
            if make_plan(broken_base)["changed_paths"] != ["frontend/pnpm-lock.yaml"]:
                raise RuntimeError("broken-chain fixture has migration differences")
            results.append(run_cycle(broken_base, failure=True))
    finally:
        os.chdir(previous)
        if protected_signature() != before:
            raise RuntimeError("protected environment resource identity changed")
    print(
        "MIGRATION_SMOKE_PASSED "
        + json.dumps({"cases": results, "protected_unchanged": True}, sort_keys=True)
    )


if __name__ == "__main__":
    main()
