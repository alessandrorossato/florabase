#!/usr/bin/env python3
"""Conservative remote checks using the existing complete-tree impact policy."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from verification_gate import checks_for, run_checks
from verification_impact import describe, make_plan, plan_paths


def ci_plan() -> dict[str, Any]:
    sha = os.environ.get("GITHUB_SHA", "")
    actual = subprocess.run(
        ["git", "rev-list", "--parents", "-1", "HEAD"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.split()
    if not re.fullmatch(r"[0-9a-f]{40}", sha) or actual[0] != sha:
        raise ValueError("checkout must match the exact platform GITHUB_SHA; refusing verification")
    # Only the platform's exact two-parent PR merge can select less than full.
    try:
        if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
            raise ValueError("main or unsupported event")
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        base = event["pull_request"]["base"]["sha"]
        head = event["pull_request"]["head"]["sha"]
        if not all(isinstance(v, str) and re.fullmatch(r"[0-9a-f]{40}", v) for v in (base, head)):
            raise ValueError("invalid event revisions")
        if actual != [sha, base, head]:
            raise ValueError("checkout does not match event merge/base/head")
    except (KeyError, TypeError, ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"Remote impact: FULL fallback ({error})", flush=True)
        # No selection is possible here; avoid hashing the entire tree just to run everything.
        return plan_paths([], sha, force_full=True)
    return make_plan(base)


def ci_checks_for(plan: dict[str, Any], job: str) -> list[dict[str, Any]]:
    if job not in {"quality", "integration", "build"}:
        raise ValueError("unknown required job")
    if plan["docs_only"]:
        return checks_for(plan)
    if job == "quality":
        return [
            {"id": "feature-graph", "command": ["python3", "./scripts/check-features.py"]},
            *[{"id": suite, "command": ["make", suite]} for suite in plan["workflow"]],
            {"id": "quality", "command": ["make", "check"]},
        ]
    if job == "integration":
        return [{"id": "integration", "command": ["make", "test-integration"]}]
    return [
        {
            "id": "production-builds",
            "command": ["make", "verify-build", "SERVICES=backend frontend"],
        }
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", choices=("quality", "integration", "build"))
    args = parser.parse_args()
    plan = ci_plan()
    print("Local acceptance policy plan (remote commands follow):", flush=True)
    print(describe(plan), flush=True)
    print(f"Required job: {args.job}; remote product suites remain exhaustive", flush=True)
    run_checks(plan, ci_checks_for(plan, args.job))
    print(f"CI_JOB_PASSED: {args.job}; no local delivery receipt issued", flush=True)


if __name__ == "__main__":
    main()
