#!/usr/bin/env python3
"""Execute a deterministic impact plan and record completed checks for the exact gate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from disposable_workflow import MIGRATION_REPORT, expected_migration_evidence
from verification_impact import describe, make_plan


def checks_for(plan: dict[str, Any]) -> list[dict[str, Any]]:
    if plan["migration"] not in {"skip", "affected-cycle", "full-cycle"} or (
        plan["mode"] == "full" and plan["migration"] != "full-cycle"
    ):
        raise ValueError("invalid migration decision")
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
    if plan["migration"] != "skip":
        add(
            "migration-cycle",
            [
                "./scripts/verify-migration-cycle.sh",
                plan["base"],
                "--force-cycle",
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
    expected = []
    for check in checks_for(plan):
        item = {**check, "result": "passed"}
        if check["id"] == "migration-cycle":
            item["evidence"] = expected_migration_evidence(plan["base"])
        expected.append(item)
    # JSON preserves boolean types; Python equality alone equates True with 1.
    if json.dumps(completed, sort_keys=True) != json.dumps(expected, sort_keys=True):
        raise ValueError(
            "required selected checks did not complete exactly; rerun make feature-verify"
        )


def migration_result(plan: dict[str, Any], completed: list[dict[str, Any]]) -> dict[str, Any]:
    required = plan["migration"] != "skip"
    evidence = next((c["evidence"] for c in completed if c["id"] == "migration-cycle"), None)
    return {
        "decision": plan["migration"],
        "cycle_required": required,
        "cycle_executed": evidence is not None and evidence["cycle_executed"] is True,
        "result": "passed" if required else "skipped_by_impact",
        "evidence": evidence,
    }


def execute(plan: dict[str, Any], path: Path) -> None:
    print(describe(plan), flush=True)
    completed = []
    for check in checks_for(plan):
        print(
            f"\n== feature verification: {check['id']} ==\nCommand: {' '.join(check['command'])}",
            flush=True,
        )
        migration = check["id"] == "migration-cycle"
        result = subprocess.run(
            check["command"], text=True, stdout=subprocess.PIPE if migration else None
        )
        if migration:
            print(result.stdout, end="", flush=True)
        if result.returncode:
            print(
                f"stage failed: {check['id']}; mode={plan['mode']} scopes={','.join(plan['affected_scopes'])}; command={' '.join(check['command'])}; disposable runner reports cleanup and residuals; recovery: make workflow-resources",
                file=sys.stderr,
            )
            raise SystemExit(result.returncode)
        item = {**check, "result": "passed"}
        if migration:
            reports = [
                line.removeprefix(MIGRATION_REPORT)
                for line in result.stdout.splitlines()
                if line.startswith(MIGRATION_REPORT)
            ]
            if len(reports) != 1 or json.loads(reports[0]) != expected_migration_evidence(
                plan["base"]
            ):
                raise ValueError("migration cycle did not report verified execution and cleanup")
            item["evidence"] = json.loads(reports[0])
        completed.append(item)
    validate_execution(plan, completed)
    path.write_text(
        json.dumps(
            {"plan": plan, "completed": completed, "migration": migration_result(plan, completed)},
            sort_keys=True,
        )
        + "\n"
    )


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
