#!/usr/bin/env python3
"""Fail closed unless the platform reports successful checks for the exact main commit."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from beta_release import SHA, inputs, run


def successful_checks(checks: list[dict[str, Any]], sha: str) -> bool:
    # Restrict the producer as well as the label; arbitrary external statuses are insufficient.
    return all(
        any(
            c.get("name") == name
            and c.get("head_sha") == sha
            and c.get("conclusion") == "success"
            and c.get("app", {}).get("slug") == "github-actions"
            for c in checks
        )
        for name in ("quality", "integration", "build")
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
    data = json.loads(
        run("gh", "api", f"repos/{repo}/commits/{sha}/check-runs?filter=latest&per_page=100")
    )
    if not successful_checks(data["check_runs"], sha):
        raise ValueError("quality, integration and build must succeed on this exact commit")
    # A failed API request is not evidence of absence. List successfully, then inspect identities.
    releases = json.loads(
        run("gh", "api", "--paginate", "--slurp", f"repos/{repo}/releases?per_page=100")
    )
    if any(item["tag_name"] == "v" + locked["version"] for page in releases for item in page):
        raise ValueError("release identity already exists; never replace published evidence")
    print("BETA_APPROVED_SOURCE_CHECKS_PASSED")


if __name__ == "__main__":
    main()
