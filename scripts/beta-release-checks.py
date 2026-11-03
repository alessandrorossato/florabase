#!/usr/bin/env python3
"""Fail closed unless the platform reports successful checks for the exact main commit."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from beta_release import SHA, inputs, run


def approved_ci_jobs(jobs: list[dict[str, Any]], sha: str) -> bool:
    passed = {
        job.get("name")
        for job in jobs
        if job.get("head_sha") == sha
        and job.get("conclusion") == "success"
        and job.get("status") == "completed"
    }
    return {"quality", "integration", "build"} <= passed


def approved_ci_run(value: dict[str, Any], sha: str, repo: str) -> bool:
    return (
        value.get("path") == ".github/workflows/ci.yml"
        and value.get("head_sha") == sha
        and value.get("head_branch") == "main"
        and value.get("event") == "push"
        and value.get("status") == "completed"
        and value.get("conclusion") == "success"
        and (value.get("repository") or {}).get("full_name") == repo
        and (value.get("head_repository") or {}).get("full_name") == repo
    )


def main() -> None:
    help_text = run("gh", "attestation", "verify", "--help")
    for flag in (
        "--signer-workflow",
        "--source-ref",
        "--deny-self-hosted-runners",
        "--source-digest",
    ):
        if flag not in help_text:
            raise ValueError(
                "installed GitHub CLI does not support release verification policy: " + flag
            )
    locked = inputs(Path.cwd(), publication=True)
    sha = os.environ["GITHUB_SHA"]
    repo = os.environ["GITHUB_REPOSITORY"]
    if (
        os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
        or os.environ.get("GITHUB_REF") != "refs/heads/main"
        or not SHA.fullmatch(sha)
        or run("git", "rev-parse", "HEAD") != sha
    ):
        raise ValueError("manual main dispatch at the exact approved source is required")
    if run("git", "rev-parse", f"refs/tags/v{locked['version']}^{{commit}}") != sha:
        raise ValueError("protected version tag does not select this commit")
    pages = json.loads(
        run(
            "gh",
            "api",
            "--paginate",
            "--slurp",
            f"repos/{repo}/actions/workflows/ci.yml/runs?head_sha={sha}&event=push&per_page=100",
        )
    )
    approved = False
    for page in pages:
        for workflow in page["workflow_runs"]:
            if not approved_ci_run(workflow, sha, repo):
                continue
            jobs = json.loads(
                run(
                    "gh",
                    "api",
                    "--paginate",
                    "--slurp",
                    f"repos/{repo}/actions/runs/{workflow['id']}/attempts/{workflow['run_attempt']}/jobs?per_page=100",
                )
            )
            if approved_ci_jobs([job for batch in jobs for job in batch["jobs"]], sha):
                approved = True
    if not approved:
        raise ValueError(
            "canonical main CI workflow and all three jobs must succeed on this exact commit"
        )
    # A failed API request is not evidence of absence. List successfully, then inspect identities.
    releases = json.loads(
        run("gh", "api", "--paginate", "--slurp", f"repos/{repo}/releases?per_page=100")
    )
    if any(item["tag_name"] == "v" + locked["version"] for page in releases for item in page):
        raise ValueError("release identity already exists; never replace published evidence")
    print("BETA_APPROVED_SOURCE_CHECKS_PASSED")


if __name__ == "__main__":
    main()
