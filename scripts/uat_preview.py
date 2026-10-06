#!/usr/bin/env python3
"""Persistent operator UAT using the dirty-source Feature Review runtime."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from workflow_environment import (
    MEDIA_ROOT,
    Environment,
    Repository,
    WorkflowError,
    run,
)

VOLUMES = {"postgres_data", "attachment_data", "frontend_node_modules"}


class UATPreview(Environment):
    def __init__(self, repository: Repository) -> None:
        super().__init__(repository, "uat")
        # UAT has fixed local configuration, never reads workstation secrets.
        self.env_source = Path("/dev/null")

    def require_context(self) -> None:
        if self.repository.source == self.repository.primary:
            raise WorkflowError("UAT Preview requires the current linked feature worktree")
        with contextlib.redirect_stdout(io.StringIO()):
            self.repository.initialize()
        if not re.fullmatch(r"florabase-uat-preview(?:-smoke-[0-9a-f]{12})?", self.project):
            raise WorkflowError("unexpected UAT project; refused")

    def resource_volumes(self) -> list[dict[str, Any]]:
        names = run(
            ["docker", "volume", "ls", "-q", "--filter", f"name=^{self.project}_"],
            capture=True,
        ).splitlines()
        return [
            json.loads(run(["docker", "volume", "inspect", name], capture=True))[0]
            for name in names
        ]

    def require_identity(self, *, running: bool = False) -> None:
        self.require_context()
        self.validate()
        self.require_owner()
        for volume in self.resource_volumes():
            labels = volume.get("Labels") or {}
            key = labels.get("com.docker.compose.volume")
            if (
                key not in VOLUMES
                or volume["Name"] != f"{self.project}_{key}"
                or labels.get("com.docker.compose.project") != self.project
                or labels.get("io.florabase.source") != str(self.source)
            ):
                raise WorkflowError("ambiguous UAT volume identity; refused")
        services: set[str] = set()
        for container in self.containers():
            labels = container["Config"].get("Labels", {})
            service = labels.get("com.docker.compose.service")
            if (
                service not in {"db", "backend", "frontend", "dev-state-init"}
                or service in services
                or labels.get("com.docker.compose.project") != self.project
                or labels.get("io.florabase.role") != "uat"
                or labels.get("io.florabase.source") != str(self.source)
                or labels.get("com.docker.compose.project.working_dir") != str(self.source)
                or labels.get("com.docker.compose.oneoff", "False") != "False"
            ):
                raise WorkflowError("ambiguous UAT container identity; refused")
            services.add(service)
            networks = container["NetworkSettings"].get("Networks", {})
            if set(networks) != {f"{self.project}_internal"}:
                raise WorkflowError("ambiguous UAT network identity; refused")
            ports = container["NetworkSettings"].get("Ports", {})
            published = [entry for entries in ports.values() if entries for entry in entries]
            if service in {"db", "backend"} and published:
                raise WorkflowError("UAT DB/backend must remain internal; refused")
            if service == "frontend" and container["State"].get("Running"):
                if published != [{"HostIp": "127.0.0.1", "HostPort": self.url.rsplit(":", 1)[1]}]:
                    raise WorkflowError("UAT frontend must publish its loopback port only; refused")
            mounts = {item["Destination"]: item for item in container["Mounts"]}
            targets = {
                "db": {"/var/lib/postgresql": "postgres_data"},
                "backend": {MEDIA_ROOT: "attachment_data"},
                "frontend": {"/app/node_modules": "frontend_node_modules"},
                "dev-state-init": {
                    "/state/attachments": "attachment_data",
                    "/app/node_modules": "frontend_node_modules",
                },
            }[service]
            for destination, key in targets.items():
                mount = mounts.get(destination, {})
                if mount.get("Type") != "volume" or mount.get("Name") != f"{self.project}_{key}":
                    raise WorkflowError("ambiguous UAT persistent mount; refused")
            source_mounts = {
                "backend": {
                    "/app/src": self.source / "backend/src",
                    "/app/alembic": self.source / "backend/alembic",
                },
                "frontend": {"/app": self.source / "frontend"},
            }.get(service, {})
            for destination, expected_source in source_mounts.items():
                mount = mounts.get(destination, {})
                if mount.get("Type") != "bind" or mount.get("Source") != str(expected_source):
                    raise WorkflowError("wrong running UAT source mount; refused")
            settings = dict(
                item.split("=", 1) for item in container["Config"].get("Env", []) if "=" in item
            )
            expected = self.environment()
            if service == "db" and any(
                settings.get(key) != expected[key]
                for key in ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")
            ):
                raise WorkflowError("wrong running UAT database identity; refused")
            if service == "backend":
                required = {
                    "FLORABASE_WORKFLOW_MODE": "uat",
                    "FLORABASE_UAT_PROJECT": self.project,
                    "FLORABASE_UAT_SOURCE": str(self.source),
                    "FLORABASE_DATABASE_URL": expected["FLORABASE_DATABASE_URL"],
                    "FLORABASE_CANONICAL_ORIGIN": self.url,
                    "FLORABASE_ENVIRONMENT": "development",
                    "FLORABASE_COOKIE_MODE": "loopback-development",
                    "FLORABASE_ATTACHMENT_STORAGE_ROOT": MEDIA_ROOT,
                }
                if any(settings.get(key) != value for key, value in required.items()):
                    raise WorkflowError("wrong running UAT backend identity; refused")
            if (
                running
                and service in {"db", "backend", "frontend"}
                and not container["State"].get("Running")
            ):
                raise WorkflowError("UAT is stopped; run make uat-preview-up")
        if running and not {"db", "backend", "frontend"}.issubset(services):
            raise WorkflowError("UAT is not initialized; run make uat-preview-up")

    def fixture(self, action: str, *, capture: bool = False) -> str:
        self.require_identity(running=True)
        # The fixture helper is an explicit read-only mount, absent from production images.
        return self.compose(
            "run",
            "--rm",
            "-T",
            "--no-deps",
            "--volume",
            f"{self.source / 'scripts/uat_fixture.py'}:/uat/uat_fixture.py:ro",
            "backend",
            "python",
            "/uat/uat_fixture.py",
            action,
            capture=capture,
        )

    def seed(self) -> None:
        self.require_identity(running=True)
        identity = json.dumps(
            {
                "project": self.project,
                "source": str(self.source),
                "database": "florabase_uat",
                "origin": self.url,
            }
        )
        program = (
            "import json, pathlib, sys; "
            f"p=pathlib.Path({MEDIA_ROOT!r})/'.uat-identity.json'; "
            "value=json.loads(sys.argv[1]); "
            "assert not p.exists() or json.loads(p.read_text())==value, 'UAT identity marker mismatch'; "
            "p.write_text(json.dumps(value))"
        )
        self.compose("exec", "-T", "backend", "python", "-c", program, identity)
        self.fixture("seed")

    def up(self) -> None:
        self.require_identity()
        super().up()

    def status(self) -> None:
        print("Environment: UAT Preview (current feature worktree)")
        super().status()
        if any(
            item["State"].get("Running")
            and item["Config"]["Labels"].get("com.docker.compose.service") == "backend"
            for item in self.containers()
        ):
            print(self.fixture("status", capture=True))
        else:
            print("Fixture/owner initialized: unavailable (UAT stopped)")
        print("UAT PREVIEW ONLY — Username: preview; Password: preview")

    def stop(self, *, remove: bool = False, confirm: str = "") -> None:
        if remove:
            raise WorkflowError("use guarded uat-preview-reset")
        self.require_identity()
        self.compose("down", "--remove-orphans")
        print("UAT Preview stopped; database, media and dependencies preserved")

    def reset(self, confirm: str) -> None:
        if confirm != self.project:
            raise WorkflowError(
                f"reset deletes ONLY UAT state; set CONFIRM_RESET_UAT_PREVIEW={self.project}"
            )
        self.require_identity()
        volumes = self.resource_volumes()
        print("Resetting ONLY: " + ", ".join(item["Name"] for item in volumes))
        self.compose("down", "--remove-orphans")
        # Names and Docker ownership are proved individually before deletion. Never down -v.
        self.require_identity()
        for volume in volumes:
            run(["docker", "volume", "rm", volume["Name"]])
        self.up()
        self.seed()
        self.status()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["up", "seed", "status", "stop", "reset"])
    args = parser.parse_args()
    try:
        preview = UATPreview(Repository(Path.cwd()))
        if args.action == "reset":
            preview.reset(os.environ.get("CONFIRM_RESET_UAT_PREVIEW", ""))
        else:
            getattr(preview, args.action)()
    except (WorkflowError, ValueError, KeyError) as error:
        print(f"UAT Preview: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
