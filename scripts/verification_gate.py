#!/usr/bin/env python3
"""Execute a deterministic impact plan and record completed checks for the exact gate."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from disposable_workflow import MIGRATION_REPORT, expected_migration_evidence
from verification_impact import describe, make_plan
from workflow_resources import ResourceError, machine_lock, verification_lock

# Workflow suites that need the Quality Docker project; the others are offline host suites.
DOCKER_WORKFLOW = frozenset({"workflow-check"})
JOURNAL_NAME = "florabase-verification-last-run.json"


def checks_for(plan: dict[str, Any]) -> list[dict[str, Any]]:
    if plan["migration"] not in {"skip", "affected-cycle", "full-cycle"} or (
        plan["mode"] == "full" and plan["migration"] != "full-cycle"
    ):
        raise ValueError("invalid migration decision")
    checks: list[dict[str, Any]] = []

    def add(name: str, command: list[str]) -> None:
        checks.append({"id": name, "command": command})

    # Cheapest deterministic checks first: graph and source-state defects must never wait behind
    # Docker suites. feature-verify.sh compares the frozen working tree, index and HEAD after the
    # last stage, so checking whitespace early covers exactly the tree every later stage verified.
    add("feature-graph", ["python3", "./scripts/check-features.py"])
    add("whitespace", ["git", "diff", "--check", plan["base"]])
    add("staged-whitespace", ["git", "diff", "--cached", "--check"])
    add(
        "untracked-whitespace",
        ["python3", "./scripts/verification_gate.py", "--untracked-whitespace"],
    )
    # Offline host suites run before the Docker-backed workflow static/type checks.
    for suite in [s for s in plan["workflow"] if s not in DOCKER_WORKFLOW]:
        add(suite, ["make", suite])
    for suite in [s for s in plan["workflow"] if s in DOCKER_WORKFLOW]:
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
    # Independent disposable stages, cheapest observed first: builds (cached), one PostgreSQL
    # migration cycle, then the PostgreSQL integration suite.
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
    if plan["integration"]:
        add(
            "integration",
            ["make", "test-integration"]
            if plan["mode"] == "full"
            else ["./scripts/test-integration.sh", *plan["integration"]],
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


def stage_summary(records: list[dict[str, Any]], pending: list[str]) -> str:
    lines = ["Stage summary (stage, result, elapsed):"]
    lines += [f"  {r['id']:<26} {r['status']:<11} {r['elapsed']:>9.2f}s" for r in records]
    lines += [f"  {name:<26} {'not run':<11} {'-':>10}" for name in pending]
    lines.append(f"  {'total':<26} {'':<11} {sum(r['elapsed'] for r in records):>9.2f}s")
    return "\n".join(lines)


def write_journal(path: Path | None, plan: dict[str, Any], records: list[dict[str, Any]]) -> None:
    """Diagnostics only: timing/outcome of the latest run. Never read back as evidence."""
    if path is None:
        return
    value = {
        "purpose": "diagnostics only; never verification evidence",
        "base": plan["base"],
        "mode": plan["mode"],
        "stages": records,
    }
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    os.replace(temporary, path)


def run_checks(
    plan: dict[str, Any], checks: list[dict[str, Any]], journal: Path | None = None
) -> list[dict[str, Any]]:
    completed: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for index, check in enumerate(checks):
        print(
            f"\n== feature verification: {check['id']} ==\nCommand: {' '.join(check['command'])}",
            flush=True,
        )
        migration = check["id"] == "migration-cycle"
        started = time.monotonic()
        try:
            # Stages never read the launcher's stdin: a terminal, a pipe and CI behave identically.
            result = subprocess.run(
                check["command"],
                text=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE if migration else None,
            )
        except KeyboardInterrupt:
            records.append(
                {"id": check["id"], "status": "interrupted", "elapsed": time.monotonic() - started}
            )
            write_journal(journal, plan, records)
            print(
                f"stage interrupted: {check['id']}; no new receipt issued; disposable runners "
                "report cleanup and residuals: make workflow-resources",
                file=sys.stderr,
            )
            print(stage_summary(records, [c["id"] for c in checks[index + 1 :]]), file=sys.stderr)
            raise SystemExit(130) from None
        elapsed = time.monotonic() - started
        if migration:
            print(result.stdout, end="", flush=True)
        if result.returncode:
            records.append({"id": check["id"], "status": "failed", "elapsed": elapsed})
            write_journal(journal, plan, records)
            print(
                f"stage failed: {check['id']}; exit={result.returncode}; "
                f"elapsed={elapsed:.2f}s; mode={plan['mode']} "
                f"scopes={','.join(plan['affected_scopes'])}; command={' '.join(check['command'])}; "
                f"prior stages passed={','.join(c['id'] for c in completed) or 'none'}; "
                "no new receipt issued; diagnose the failing command/test from original output; "
                "local gate failure requires make feature-verify after fixes; "
                "transient remote failure may rerun only the failed job at the same SHA; "
                "disposable runner reports cleanup and residuals: make workflow-resources",
                file=sys.stderr,
            )
            print(stage_summary(records, [c["id"] for c in checks[index + 1 :]]), file=sys.stderr)
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
                records.append({"id": check["id"], "status": "failed", "elapsed": elapsed})
                write_journal(journal, plan, records)
                raise ValueError("migration cycle did not report verified execution and cleanup")
            item["evidence"] = json.loads(reports[0])
        completed.append(item)
        records.append({"id": check["id"], "status": "passed", "elapsed": elapsed})
        write_journal(journal, plan, records)
        print(f"stage passed: {check['id']}; elapsed={elapsed:.2f}s", flush=True)
    print(stage_summary(records, []), flush=True)
    return completed


def execute(plan: dict[str, Any], path: Path, journal: Path | None = None) -> None:
    print(describe(plan), flush=True)
    checks = checks_for(plan)
    print("Stage order: " + " -> ".join(c["id"] for c in checks), flush=True)
    completed = run_checks(plan, checks, journal)
    validate_execution(plan, completed)
    path.write_text(
        json.dumps(
            {"plan": plan, "completed": completed, "migration": migration_result(plan, completed)},
            sort_keys=True,
        )
        + "\n"
    )


def execute_locked(plan: dict[str, Any], path: Path) -> None:
    metadata = Path(
        subprocess.run(
            ["git", "rev-parse", "--absolute-git-dir"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip()
    )
    # FULL competes for shared CPU, BuildKit and Docker address pools across every checkout.
    full_lock = (
        machine_lock("verification-full", "canonical FULL verification")
        if plan["mode"] == "full"
        else contextlib.nullcontext()
    )
    with verification_lock(metadata), full_lock:
        (metadata / "info").mkdir(parents=True, exist_ok=True)
        execute(plan, path, metadata / "info" / JOURNAL_NAME)


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
    try:
        execute_locked(make_plan(args.base, force_full=args.full), args.execution)
    except ResourceError as error:
        print(f"verification refused: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
