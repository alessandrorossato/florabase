#!/usr/bin/env python3
"""Execute a deterministic impact plan and record completed checks for the exact gate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from verification_impact import describe, make_plan


def checks_for(plan: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def add(name: str, command: list[str]) -> None:
        checks.append({"id": name, "command": command})

    add("feature-graph", ["python3", "./scripts/check-features.py"])
    for suite in plan["workflow"]:
        add(suite, ["make", suite])
    if plan["mode"] == "full":
        add("quality", ["make", "check"])
    else:
        for stage in plan["static"]:
            if stage not in {"feature-graph", "whitespace"}:
                add(stage, ["make", stage])
        if plan["backend"]:
            add(
                "backend",
                [
                    "python3",
                    "./scripts/workflow_environment.py",
                    "quality",
                    "compose",
                    "--",
                    "run",
                    "--rm",
                    "--no-deps",
                    "backend",
                    "pytest",
                    "--no-cov",
                    "-m",
                    "not integration",
                    *[str(Path(p).relative_to("backend")) for p in plan["backend"]],
                ],
            )
        if plan["frontend"]:
            add(
                "frontend",
                [
                    "python3",
                    "./scripts/workflow_environment.py",
                    "quality",
                    "compose",
                    "--",
                    "run",
                    "--rm",
                    "--no-deps",
                    "frontend",
                    "pnpm",
                    "test",
                    *[str(Path(p).relative_to("frontend")) for p in plan["frontend"]],
                ],
            )
    if plan["integration"]:
        add(
            "integration",
            ["make", "test-integration"]
            if plan["mode"] == "full"
            else ["./scripts/test-integration.sh", *plan["integration"]],
        )
    if plan["builds"]:
        add("production-builds", ["make", "verify-build", "SERVICES=" + " ".join(plan["builds"])])
    if plan["migration"]:
        add(
            "migration-cycle",
            [
                "./scripts/verify-migration-cycle.sh",
                plan["base"],
                *(["--force-cycle"] if plan["migration_cycle"] else []),
            ],
        )
    add("whitespace", ["git", "diff", "--check", plan["base"]])
    add("staged-whitespace", ["git", "diff", "--cached", "--check"])
    add(
        "untracked-whitespace",
        ["python3", "./scripts/verification_gate.py", "--untracked-whitespace"],
    )
    return checks


def validate_execution(plan: dict[str, Any], completed: object) -> None:
    expected = [{**check, "result": "passed"} for check in checks_for(plan)]
    if completed != expected:
        raise ValueError(
            "required selected checks did not complete exactly; rerun make feature-verify"
        )


def execute(plan: dict[str, Any], path: Path) -> None:
    print(describe(plan), flush=True)
    completed = []
    for check in checks_for(plan):
        print(
            f"\n== feature verification: {check['id']} ==\nCommand: {' '.join(check['command'])}",
            flush=True,
        )
        result = subprocess.run(check["command"])
        if result.returncode:
            print(
                f"stage failed: {check['id']}; mode={plan['mode']} scopes={','.join(plan['affected_scopes'])}; command={' '.join(check['command'])}; disposable runner reports cleanup and residuals; recovery: make workflow-resources",
                file=sys.stderr,
            )
            raise SystemExit(result.returncode)
        completed.append({**check, "result": "passed"})
    path.write_text(json.dumps({"plan": plan, "completed": completed}, sort_keys=True) + "\n")


def check_untracked_whitespace() -> None:
    raw = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    for path in sorted(value for value in raw.split(b"\0") if value):
        name = path.decode("utf-8", "surrogateescape")
        result = subprocess.run(
            ["git", "diff", "--no-index", "--check", "--", "/dev/null", name],
            text=True,
            capture_output=True,
        )
        if result.stdout or result.stderr or result.returncode not in (0, 1):
            # Report locations only, never echo file content from check diagnostics.
            print(f"whitespace check failed: {name}", file=sys.stderr)
            raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base")
    parser.add_argument("--untracked-whitespace", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--execution", type=Path)
    args = parser.parse_args()
    if args.untracked_whitespace:
        check_untracked_whitespace()
        return
    if not args.base or not args.execution:
        parser.error("--base and --execution are required for gate execution")
    execute(make_plan(args.base, force_full=args.full), args.execution)


if __name__ == "__main__":
    main()
