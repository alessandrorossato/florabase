#!/usr/bin/env python3
"""Candidate-owned Review, reusing the repository's Compose ownership validation."""
# ruff: noqa: T201 -- This explicit Review CLI reports its actions on stdout.

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SOURCE / "scripts"))
from workflow_environment import Environment, Repository  # noqa: E402


class TaxonomyReview(Environment):
    def __init__(self) -> None:
        super().__init__(Repository(SOURCE), "review")
        suffix = hashlib.sha256(str(self.repository.metadata).encode()).hexdigest()[:8]
        self.project = f"florabase-taxonomy-review-{suffix}"
        self.url = "http://localhost:15278"
        self.env_source = Path("/dev/null")
        self.workflow_overlay = Path(__file__).with_name("compose.yaml")

    def environment(self) -> dict[str, str]:
        return {**super().environment(), "FRONTEND_PORT": "15278"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=["up", "status", "seed", "enhance", "source", "conflict", "check"]
    )
    parser.add_argument("availability", nargs="?", choices=["available", "unavailable"])
    args = parser.parse_args()
    environment = TaxonomyReview()
    if args.action == "up":
        environment.up()
        return
    environment.validate()
    environment.require_owner()
    if args.action == "status":
        environment.status()
        environment.compose("exec", "-T", "backend", "python", "/review/runtime.py", "status")
        print(f"Credentials reference: {SOURCE / '.taxonomy-review/credentials.json'}")
        return
    payload = None
    if args.action == "seed":
        directory = SOURCE / ".taxonomy-review"
        directory.mkdir(mode=0o700, exist_ok=True)
        credentials = directory / "credentials.json"
        if not credentials.exists():
            descriptor = os.open(credentials, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w") as stream:
                json.dump(
                    {"login": "taxonomy-review", "password": secrets.token_urlsafe(24)}, stream
                )
        payload = credentials.read_text()
    command = (
        ["exec", "-T", "backend", "python", "/review/enhance.py"]
        if args.action == "enhance"
        else ["exec", "-T", "backend", "python", "/review/runtime.py", args.action]
    )
    if args.action == "source":
        if args.availability is None:
            parser.error("source requires available or unavailable")
        command.append(args.availability)
    subprocess.run(
        environment.command(*command),
        env=environment.environment(),
        input=payload,
        text=True,
        check=True,
    )


if __name__ == "__main__":
    main()
