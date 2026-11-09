#!/usr/bin/env python3
"""Exercise protected beta image stages against an owned local OCI registry only."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from beta_release import inputs

_publisher_spec = importlib.util.spec_from_file_location(
    "publisher", Path(__file__).with_name("publish-beta-images.py")
)
if _publisher_spec is None or _publisher_spec.loader is None:
    raise RuntimeError("could not load protected publisher preflight")
_publisher = importlib.util.module_from_spec(_publisher_spec)
_publisher_spec.loader.exec_module(_publisher)
published_digest = _publisher.published_digest


def release_candidate(root: Path, base: str, version: str) -> bool:
    """A change is a release candidate unless its base already names this exact version.

    Ordinary pull requests inherit the published base version; a version bump, a manual run and a
    push without a usable base are candidates, so they keep the strict tag-absence check.
    """
    if not re.fullmatch(r"[0-9a-f]{40}", base) or set(base) == {"0"}:
        return True
    shown = subprocess.run(
        ["git", "-C", str(root), "show", f"{base}:release/inputs.json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if shown.returncode:
        return True
    return bool(json.loads(shown.stdout).get("version") != version)


def verify_ghcr_read_only(locked: dict[str, Any], candidate: bool = True) -> dict[str, Any]:
    token = os.environ.get("GITHUB_TOKEN")
    actor = os.environ.get("GITHUB_ACTOR")
    if not token or not actor:
        raise ValueError("hosted rehearsal requires GitHub Actions read-only package credentials")
    version = locked["version"]
    observations: dict[str, Any] = {
        "status": "passed",
        "scope": "pull only",
        "release_candidate": candidate,
        "tags": {},
    }
    for name in ("backend", "frontend"):
        digest = published_digest(
            "alessandrorossato/florabase-" + name,
            version,
            actor,
            token,
            actions="pull",
        )
        if digest is not None and candidate:
            raise ValueError("versioned GHCR image already exists; rehearsal refuses reuse")
        # Not a candidate: the base's published release; protected publication still refuses reuse.
        observations["tags"][name] = {
            "version": version,
            "status": "absent" if digest is None else "published_base_version",
            "digest": digest,
        }
    pg = locked["postgresql"]
    digest = published_digest(
        "alessandrorossato/florabase-postgres",
        pg["version"],
        actor,
        token,
        actions="pull",
    )
    if digest is not None and digest != pg["index_digest"]:
        raise ValueError("GHCR PostgreSQL version tag differs from the pinned identity")
    observations["tags"]["postgresql"] = {
        "version": pg["version"],
        "status": "absent" if digest is None else "present_and_matches_pin",
        "digest": digest,
    }
    return observations


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--hosted", action="store_true", help="also check GHCR with pull-only scope"
    )
    parser.add_argument(
        "--base", default="", help="base commit; an unchanged published version is not a candidate"
    )
    args = parser.parse_args()
    root = Path.cwd()
    output = args.output.resolve()
    if output.is_relative_to(root):
        raise ValueError("release output must be outside the source checkout")
    if args.hosted:
        if (
            os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"
            or os.environ.get("GITHUB_REPOSITORY") != _publisher.REPOSITORY
        ):
            raise ValueError("--hosted requires the repository's GitHub-hosted rehearsal")
        locked = inputs(root, publication=True)
        candidate = release_candidate(root, args.base, locked["version"])
        print(f"RELEASE CANDIDATE: {'yes' if candidate else 'no (published base version)'}")
        observation = verify_ghcr_read_only(locked, candidate)
        print("GHCR READ ONLY: PASS", flush=True)
        print(json.dumps(observation), flush=True)
    _publisher.run_pipeline(root, output)
    print(
        "ATTEST: inputs validated; GitHub issuance requires protected publication",
        flush=True,
    )
    print(
        "RELEASE: assets and draft inputs validated; GitHub API writes require protected publication",
        flush=True,
    )
    print("BETA_RELEASE_REHEARSAL_PASSED", flush=True)


if __name__ == "__main__":
    main()
