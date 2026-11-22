#!/usr/bin/env python3
"""Scoped remote checks using the repository complete-tree impact policy."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

_IMPORT_ERROR: Exception | None = None
try:
    from verification_gate import (
        backend_test_command,
        checks_for,
        docs_checks_for,
        frontend_test_command,
        run_checks,
        validate_plan,
    )
    from verification_impact import describe, make_plan, plan_paths, plan_tier
except Exception as _error:
    _IMPORT_ERROR = _error


def _require_imports() -> None:
    if _IMPORT_ERROR is not None:
        raise _IMPORT_ERROR


def ci_plan() -> dict[str, Any]:
    _require_imports()
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
    batch_name = r"ci/(?:wf-04-)?batch-[a-z0-9][a-z0-9._-]*"
    event_head = os.environ.get("GITHUB_HEAD_REF", "")
    batch_branch = event_head if re.fullmatch(batch_name, event_head) else ""
    try:
        if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
            raise ValueError("main or unsupported event")
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        base = event["pull_request"]["base"]["sha"]
        head = event["pull_request"]["head"]["sha"]
        branch = event["pull_request"]["head"].get("ref", "")
        if isinstance(branch, str) and re.fullmatch(batch_name, branch):
            if event_head and branch != event_head:
                batch_branch = branch
                raise ValueError("batch branch differs from platform GITHUB_HEAD_REF")
            batch_branch = branch
        if batch_branch and branch != batch_branch:
            raise ValueError("batch branch missing from GitHub event")
        if not all(isinstance(v, str) and re.fullmatch(r"[0-9a-f]{40}", v) for v in (base, head)):
            raise ValueError("invalid event revisions")
        if actual != [sha, base, head]:
            raise ValueError("checkout does not match event merge/base/head")
    except (KeyError, TypeError, ValueError, OSError, subprocess.CalledProcessError) as error:
        if batch_branch:
            raise ValueError("cannot prove exact batch PR parents") from error
        print(f"Remote impact: FULL fallback ({error})", flush=True)
        # No selection is possible here; avoid hashing the entire tree just to run everything.
        return plan_paths([], sha, force_full=True)
    if batch_branch:
        from feature_batch import validate_platform_tree
        from workflow_environment import Repository

        validate_platform_tree(Repository(Path.cwd()), batch_branch, base, head, sha)
    return make_plan(base)


def ci_checks_for(plan: dict[str, Any], job: str) -> list[dict[str, Any]]:
    _require_imports()
    if job not in {"quality", "integration", "build"}:
        raise ValueError("unknown required job")
    tier = validate_plan(plan)
    if tier == "docs":
        return checks_for(plan)
    if tier in {"affected", "product-frontend"}:
        if job == "quality":
            checks: list[dict[str, Any]] = [
                {"id": "feature-graph", "command": ["python3", "./scripts/check-features.py"]},
                {"id": "doc-links", "command": ["python3", "./scripts/check-doc-links.py"]},
                {"id": "test-doc-links", "command": ["python3", "./scripts/test-doc-links.py"]},
            ]
            for stage in plan["static"]:
                if stage not in {"feature-graph", "whitespace"}:
                    checks.append({"id": stage, "command": ["make", stage]})
            if plan["backend"]:
                checks.append({"id": "backend", "command": backend_test_command(plan)})
            if plan["frontend"]:
                checks.append({"id": "frontend", "command": frontend_test_command(plan)})
            return checks
        if job == "integration":
            if plan["integration"]:
                return [
                    {
                        "id": "integration",
                        "command": ["./scripts/test-integration.sh", *plan["integration"]],
                    }
                ]
            return docs_checks_for(plan)
        if plan["builds"]:
            return [
                {
                    "id": "production-builds",
                    "command": ["make", "verify-build", "SERVICES=" + " ".join(plan["builds"])],
                }
            ]
        return []
    if job == "quality":
        return [
            {"id": "feature-graph", "command": ["python3", "./scripts/check-features.py"]},
            {"id": "doc-links", "command": ["python3", "./scripts/check-doc-links.py"]},
            {"id": "test-doc-links", "command": ["python3", "./scripts/test-doc-links.py"]},
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


def _write_github_output(name: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with Path(output_path).open("a", encoding="utf-8") as stream:
            stream.write(f"{name}={value}\n")


def rehearse_scope() -> bool:
    """Decide whether release rehearsal may exit early on a proven docs-only PR.

    Any non-docs tier, non-PR event or error falls back to running the full rehearsal
    (writing skip=false and exiting 0) so the workflow step never fails prematurely.
    """
    try:
        plan = ci_plan()
        tier = validate_plan(plan)
        print("Rehearsal scope plan:", flush=True)
        print(describe(plan), flush=True)
        if tier == "docs" and plan["docs_only"] is True:
            print(
                "REHEARSE_SKIPPED: docs-only PR; release rehearsal not required",
                flush=True,
            )
            _write_github_output("skip", "true")
            return True
        print(
            f"REHEARSE_REQUIRED: tier={tier}; running full release rehearsal",
            flush=True,
        )
        _write_github_output("skip", "false")
        return False
    except Exception as error:
        print(
            f"Rehearsal scope fallback: running full rehearsal ({error})",
            flush=True,
        )
        _write_github_output("skip", "false")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", choices=("quality", "integration", "build", "rehearse-scope"))
    args = parser.parse_args()
    if args.job == "rehearse-scope":
        rehearse_scope()
        return
    plan = ci_plan()
    tier = plan_tier(plan)
    print("Verification impact plan (remote commands follow):", flush=True)
    print(describe(plan), flush=True)
    scope_note = (
        "docs checks only"
        if tier == "docs"
        else "selected suites and builds"
        if tier in {"affected", "product-frontend"}
        else "complete product suites and both builds"
    )
    print(f"Required job: {args.job}; tier={tier} ({scope_note})", flush=True)
    run_checks(plan, ci_checks_for(plan, args.job))
    print(f"CI_JOB_PASSED: {args.job}; no local delivery receipt issued", flush=True)


if __name__ == "__main__":
    main()
