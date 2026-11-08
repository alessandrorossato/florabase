#!/usr/bin/env python3
"""Fail closed unless the platform reports successful checks for the exact main commit."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from beta_release import SHA, inputs, require_remote_release_tag, run


def approved_ci_jobs(
    jobs: list[dict[str, Any]], sha: str, required: set[str] | None = None
) -> bool:
    passed = {
        job.get("name")
        for job in jobs
        if job.get("head_sha") == sha
        and job.get("conclusion") == "success"
        and job.get("status") == "completed"
    }
    if required is None:
        required = {"quality", "integration", "build", "release-migration"}
    return required <= passed and all(
        sum(job.get("name") == name for job in jobs) == 1 for name in required
    )


def approved_ci_run(value: dict[str, Any], sha: str, repo: str, workflow: str = "ci.yml") -> bool:
    return (
        value.get("path") == f".github/workflows/{workflow}"
        and value.get("head_sha") == sha
        and value.get("head_branch") == "main"
        and value.get("event") == "push"
        and value.get("status") == "completed"
        and value.get("conclusion") == "success"
        and (value.get("repository") or {}).get("full_name") == repo
        and (value.get("head_repository") or {}).get("full_name") == repo
    )


def require_workflow(repo: str, sha: str, workflow_file: str, required: set[str]) -> None:
    pages = json.loads(
        run(
            "gh",
            "api",
            "--paginate",
            "--slurp",
            f"repos/{repo}/actions/workflows/{workflow_file}/runs?head_sha={sha}&event=push&per_page=100",
        )
    )
    for page in pages:
        for workflow in page["workflow_runs"]:
            if not approved_ci_run(workflow, sha, repo, workflow_file):
                continue
            jobs = json.loads(
                run(
                    "gh",
                    "api",
                    "--paginate",
                    "--slurp",
                    f"repos/{repo}/actions/runs/{workflow['id']}/jobs?filter=latest&per_page=100",
                )
            )
            if approved_ci_jobs([job for batch in jobs for job in batch["jobs"]], sha, required):
                print(
                    f"EVIDENCE PASS: {workflow_file} run {workflow['id']} attempt {workflow['run_attempt']} at {sha}"
                )
                return
    raise ValueError(f"{workflow_file} and {sorted(required)} must succeed on exact main SHA {sha}")


def require_cli_policy() -> None:
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity-only", action="store_true")
    args = parser.parse_args()
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
    tag = f"v{locked['version']}"
    if run("git", "rev-parse", f"refs/tags/{tag}^{{commit}}") != sha:
        raise ValueError("protected version tag does not select this commit")
    require_remote_release_tag(repo, tag, sha)
    if not args.identity_only:
        require_cli_policy()
        require_workflow(
            repo,
            sha,
            "ci.yml",
            {"quality", "integration", "build", "release-migration"},
        )
        require_workflow(repo, sha, "beta-release-rehearsal.yml", {"rehearse"})
    # A failed API request is not evidence of absence. List successfully, then inspect identities.
    releases = json.loads(
        run("gh", "api", "--paginate", "--slurp", f"repos/{repo}/releases?per_page=100")
    )
    if any(item["tag_name"] == tag for page in releases for item in page):
        raise ValueError("release identity already exists; never replace published evidence")
    print("BETA_APPROVED_SOURCE_CHECKS_PASSED")


if __name__ == "__main__":
    main()
