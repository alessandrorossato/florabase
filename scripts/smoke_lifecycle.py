#!/usr/bin/env python3
"""Attach registered positive ownership/cleanup to existing disposable real workflow fixtures."""

from __future__ import annotations

import hashlib
import json
import tempfile
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any

from workflow_environment import Environment, Repository, run
from workflow_resources import Disposable, Owner


def overlay(config: dict[str, Any], owner: Owner) -> dict[str, Any]:
    labels = {
        key: value for key, value in owner.labels().items() if key != "com.docker.compose.project"
    }
    result: dict[str, Any] = {"services": {}, "networks": {}, "volumes": {}}
    for name, service in config["services"].items():
        value: dict[str, Any] = {"labels": labels}
        if service.get("build"):
            value["build"] = {"labels": owner.labels()}
        result["services"][name] = value
    for kind in ("networks", "volumes"):
        for name, value in config.get(kind, {}).items():
            if value.get("external"):
                raise ValueError("disposable smoke may not mount external state")
            result[kind][name] = {"labels": labels}
    return result


class SmokeLifecycle(AbstractContextManager["SmokeLifecycle"]):
    def __init__(self, env: Environment) -> None:
        self.env = env
        self.owner = Owner.smoke_fixture(env.project, env.source)
        self.lifetime = Disposable(self.owner)
        self.temporary: tempfile.TemporaryDirectory[str] | None = None

    def __enter__(self) -> SmokeLifecycle:
        self.lifetime.__enter__()  # BEFORE configuration/bootstrap/build creates any resources.
        try:
            config = json.loads(self.env.compose("config", "--format", "json", capture=True))
            self.temporary = tempfile.TemporaryDirectory(prefix="florabase-smoke-ownership-")
            path = Path(self.temporary.name) / "ownership.json"
            path.write_text(json.dumps(overlay(config, self.owner)))
            self.env.workflow_overlay = path
        except BaseException:
            self.__exit__()
            raise
        return self

    def __exit__(self, *exception: object) -> None:
        try:
            self.lifetime.__exit__(*exception)
        finally:
            self.env.workflow_overlay = None
            if self.temporary:
                self.temporary.cleanup()


def operator_snapshot(repo: Repository, extra: tuple[str, ...] = ()) -> dict[str, Any]:
    """Persistent environments' containers, volumes and live database content digests."""
    snapshot: dict[str, Any] = {
        "git": Environment(repo, "dev").repo.identity(),
        "projects": {},
    }
    for project in (
        "florabase",
        "florabase-feature-review",
        "florabase-preview",
        "florabase-prod",
        "florabase-uat-preview",
        "florabase-sourcing-preview",
        *extra,
    ):
        ids = run(
            [
                "docker",
                "ps",
                "-aq",
                "--filter",
                f"label=com.docker.compose.project={project}",
            ],
            capture=True,
        ).splitlines()
        volumes = run(
            [
                "docker",
                "volume",
                "ls",
                "-q",
                "--filter",
                f"label=com.docker.compose.project={project}",
            ],
            capture=True,
        ).splitlines()
        containers = json.loads(run(["docker", "inspect", *ids], capture=True)) if ids else []
        result: dict[str, Any] = {
            "containers": [
                (
                    item["Id"],
                    item["State"]["StartedAt"],
                    item["State"]["Running"],
                    item["Mounts"],
                )
                for item in containers
            ],
            "volumes": json.loads(run(["docker", "volume", "inspect", *volumes], capture=True))
            if volumes
            else [],
        }
        for item in containers:
            if (
                item["State"].get("Running")
                and item["Config"]["Labels"].get("com.docker.compose.service") == "db"
            ):
                data = run(
                    [
                        "docker",
                        "exec",
                        item["Id"],
                        "sh",
                        "-ec",
                        'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --data-only --inserts --no-owner --no-privileges',
                    ],
                    capture=True,
                )
                # PostgreSQL dump restriction tokens are random; exclude them from the checksum.
                data = "\n".join(
                    line
                    for line in data.splitlines()
                    if not line.startswith(("\\restrict", "\\unrestrict"))
                )
                result["database_digest"] = hashlib.sha256(data.encode()).hexdigest()
        snapshot["projects"][project] = result
    return snapshot
