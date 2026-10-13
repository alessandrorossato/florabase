#!/usr/bin/env python3
"""Persistent operator UAT using the dirty-source Feature Review runtime."""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import io
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, cast

from uat_source import ancestor, delivered, graph_at, read_transition, write_transition
from workflow_environment import (
    MEDIA_ROOT,
    Environment,
    Repository,
    WorkflowError,
    code_heads,
    migration_graph,
    require_upgradeable,
    run,
)

VOLUMES = {"postgres_data", "attachment_data", "frontend_node_modules"}


class UATPreview(Environment):
    def __init__(self, repository: Repository) -> None:
        super().__init__(repository, "uat")
        # UAT has fixed local configuration, never reads workstation secrets.
        self.env_source = Path("/dev/null")

    def require_context(self, *, retiring: bool = False) -> None:
        if (
            self.repository.source == self.repository.primary
            or self.repository.metadata == self.repository.common
        ):
            raise WorkflowError("UAT Preview requires the current linked feature worktree")
        if not re.fullmatch(r"florabase-uat-preview(?:-smoke-[0-9a-f]{12})?", self.project):
            raise WorkflowError("unexpected UAT project; refused")

        origin = self.repository.git("remote", "get-url", "origin")
        normalized = re.sub(
            r"^(?:git@github\.com:|ssh://git@github\.com/)", "https://github.com/", origin
        )
        if (
            normalized.rstrip("/").removesuffix(".git")
            != "https://github.com/alessandrorossato/florabase"
        ):
            raise WorkflowError("origin is not the expected Florabase repository")
        if not retiring:
            if self.repository.identity()["branch"] == "detached":
                delivered(self.repository)
                volumes = self.resource_volumes()
                if {item["Name"] for item in volumes} != {
                    f"{self.project}_{key}" for key in VOLUMES
                }:
                    raise WorkflowError(
                        "detached source is not the established persistent UAT owner"
                    )
            else:
                with contextlib.redirect_stdout(io.StringIO()):
                    self.repository.initialize()

    def resource_volumes(self) -> list[dict[str, Any]]:
        names = run(
            ["docker", "volume", "ls", "-q", "--filter", f"name=^{self.project}_"],
            capture=True,
        ).splitlines()
        return [
            json.loads(run(["docker", "volume", "inspect", name], capture=True))[0]
            for name in names
        ]

    def require_identity(self, *, running: bool = False, retiring: bool = False) -> None:
        self.require_context(retiring=retiring)
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
            launched = labels.get("io.florabase.sha", "")
            if not re.fullmatch(r"[0-9a-f]{40}", launched):
                raise WorkflowError("missing/unknown UAT launched Git identity; refused")
            if not ancestor(self.repository, launched, "HEAD"):
                delivered(self.repository, launched)
            if (
                container["State"].get("Paused")
                or container["State"].get("Restarting")
                or container["State"].get("Dead")
            ):
                raise WorkflowError("ambiguous UAT container state; refused")
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
                    f"/app/{name}": self.source / "backend" / name
                    for name in (
                        "src",
                        "tests",
                        "alembic",
                        "scripts",
                        "openapi.json",
                        "pyproject.toml",
                        "requirements.lock",
                        "requirements-dev.lock",
                    )
                },
                "frontend": {
                    "/app": self.source / "frontend",
                    "/backend/openapi.json": self.source / "backend/openapi.json",
                },
            }.get(service, {})
            if set(mounts) != set(targets) | set(source_mounts):
                raise WorkflowError("unexpected UAT mounts; refused")
            for destination, expected_source in source_mounts.items():
                mount = mounts.get(destination, {})
                if mount.get("Type") != "bind" or mount.get("Source") != str(expected_source):
                    raise WorkflowError("wrong running UAT source mount; refused")
            bindings = container.get("HostConfig", {}).get("PortBindings") or {}
            if service == "frontend" and bindings != {
                "5173/tcp": [{"HostIp": "127.0.0.1", "HostPort": self.url.rsplit(":", 1)[1]}]
            }:
                raise WorkflowError("wrong retained UAT frontend port identity; refused")
            if service in {"db", "backend"} and bindings:
                raise WorkflowError("UAT DB/backend ports must remain internal; refused")
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
        self.require_resource_users()
        if not retiring and self.repository.identity()["branch"] == "detached":
            self.require_marker()
        if running and not {"db", "backend", "frontend"}.issubset(services):
            raise WorkflowError("UAT is not initialized; run make uat-preview-up")

    @property
    def transition_path(self) -> Path:
        return self.repository.metadata / f"{self.project}-sync.json"

    def transition(self) -> dict[str, Any] | None:
        return read_transition(self.transition_path, self.repository, self.project)

    def require_idle(self) -> None:
        if self.transition():
            raise WorkflowError("UAT sync is interrupted; run make uat-preview-sync to resume")

    def require_resource_users(self) -> None:
        containers = {item["Id"] for item in self.containers()}
        names = run(
            ["docker", "network", "ls", "-q", "--filter", f"name=^{self.project}_"], capture=True
        ).splitlines()
        for name in names:
            network = json.loads(run(["docker", "network", "inspect", name], capture=True))[0]
            labels = network.get("Labels") or {}
            if (
                network["Name"] != f"{self.project}_internal"
                or labels.get("com.docker.compose.project") != self.project
                or labels.get("com.docker.compose.network") != "internal"
                or not set(network.get("Containers") or {}).issubset(containers)
            ):
                raise WorkflowError("ambiguous UAT network identity or foreign endpoint; refused")
        for volume in self.resource_volumes():
            users = run(
                ["docker", "ps", "-aq", "--no-trunc", "--filter", f"volume={volume['Name']}"],
                capture=True,
            ).splitlines()
            if not set(users).issubset(containers):
                raise WorkflowError("UAT volume has a foreign container user; refused")

    def marker_state(self) -> dict[str, Any]:
        # A stopped backend is sufficient: read ONLY the proven UAT media volume read-only.
        backend = next(
            (
                item
                for item in self.containers()
                if item["Config"]["Labels"].get("com.docker.compose.service") == "backend"
            ),
            None,
        )
        if backend is None:
            raise WorkflowError(
                "UAT media marker unavailable; established backend identity required"
            )
        program = (
            "import json; from pathlib import Path; "
            f"root=Path({MEDIA_ROOT!r}); "
            "print(json.dumps({name:json.loads((root/name).read_text()) if (root/name).is_file() else None "
            "for name in ['.uat-identity.json','.uat-fixture.json']}))"
        )
        return cast(
            dict[str, Any],
            json.loads(
                run(
                    [
                        "docker",
                        "run",
                        "--rm",
                        "--network",
                        "none",
                        "--read-only",
                        "--cap-drop",
                        "ALL",
                        "--user",
                        self.environment()["LOCAL_UID"] + ":" + self.environment()["LOCAL_GID"],
                        "--mount",
                        f"type=volume,src={self.project}_attachment_data,dst={MEDIA_ROOT},readonly",
                        "--entrypoint",
                        "python",
                        backend["Image"],
                        "-c",
                        program,
                    ],
                    capture=True,
                )
            ),
        )

    def require_marker(self) -> dict[str, Any]:
        state = self.marker_state()
        expected = {
            "project": self.project,
            "source": str(self.source),
            "database": "florabase_uat",
            "origin": self.url,
        }
        fixture = state.get(".uat-fixture.json")
        if (
            state.get(".uat-identity.json") != expected
            or not isinstance(fixture, dict)
            or fixture.get("state") != "ready"
        ):
            raise WorkflowError(
                "missing/mismatched UAT identity or incomplete fixture marker; refused"
            )
        return state

    def start_database(self) -> None:
        if any(
            item["Config"]["Labels"].get("com.docker.compose.service") == "db"
            for item in self.containers()
        ):
            self.compose("start", "--wait", "--wait-timeout", "120", "db")
        else:
            self.compose("up", "-d", "--wait", "--wait-timeout", "120", "db")

    def current(self) -> list[str]:
        database = self.compose(
            "exec",
            "-T",
            "db",
            "psql",
            "-U",
            "florabase_uat",
            "-d",
            "florabase_uat",
            "-Atc",
            "SELECT current_database() || '|' || current_user;",
            capture=True,
        )
        if database != "florabase_uat|florabase_uat":
            raise WorkflowError("actual UAT database identity mismatch; refused")
        revisions = super().current()
        if len(revisions) > 1:
            raise WorkflowError("ambiguous multiple UAT database revisions; refused")
        return revisions

    def volume_identity(self) -> list[dict[str, Any]]:
        return sorted(
            [
                {"name": item["Name"], "created": item["CreatedAt"], "labels": item.get("Labels")}
                for item in self.resource_volumes()
            ],
            key=lambda item: item["name"],
        )

    def stop_writers(self) -> None:
        for item in self.containers():
            if item["Config"]["Labels"].get("com.docker.compose.service") != "db" and item[
                "State"
            ].get("Running"):
                run(["docker", "container", "stop", item["Id"]])
        self.require_identity()
        if any(
            item["State"].get("Running")
            and item["Config"]["Labels"].get("com.docker.compose.service") != "db"
            for item in self.containers()
        ):
            raise WorkflowError("UAT writer restarted; refused")

    def sync(self) -> None:
        self.require_identity()
        self.require_marker()
        identity = self.repository.identity()
        if identity["branch"] != "detached" or identity["dirty"] != "no":
            raise WorkflowError(
                "sync requires a clean detached delivered owner; finish delivery first"
            )
        pending = self.transition()
        if pending is None:
            before = identity["sha"]
            delivered_head = delivered(self.repository)
            # Explicit synchronization may fetch. Ordinary status/up/seed never fetch or switch.
            self.repository.git("fetch", "--prune", "origin")
            target = self.repository.git("rev-parse", "origin/main")
            if not ancestor(self.repository, delivered_head, target):
                raise WorkflowError("origin/main no longer contains delivered owner; sync refused")
            self.require_identity()
            pending = {
                "version": 1,
                "source": str(self.source),
                "project": self.project,
                "before": before,
                "target": target,
                "volumes": self.volume_identity(),
            }
        target = pending["target"]
        graph = graph_at(self.repository, target)
        if self.volume_identity() != pending["volumes"]:
            raise WorkflowError("UAT volumes changed during sync; refused")
        # Start the existing, validated DB without recreation. Applications still use old code.
        self.compose("start", "--wait", "--wait-timeout", "120", "db")
        current = self.current()
        if not current:
            raise WorkflowError("established UAT database is unversioned; sync refused")
        require_upgradeable(current, graph)
        self.require_identity()
        if self.repository.identity() != identity:
            raise WorkflowError("UAT source changed during sync preflight; refused")
        write_transition(self.transition_path, pending)
        self.stop_writers()
        if self.repository.git("rev-parse", "HEAD") != target:
            self.repository.git("switch", "--detach", target)
        self.require_identity()
        self.compose("build")
        require_upgradeable(self.current(), graph)
        self.upgrade()
        self.compose("run", "--rm", "-T", "--no-deps", "dev-state-init")
        self.compose("up", "-d", "--wait", "--wait-timeout", "180")
        self.require_identity(running=True)
        self.require_marker()
        if self.volume_identity() != pending["volumes"] or self.current() != code_heads(graph):
            raise WorkflowError("UAT sync verification failed; resume sync with preserved volumes")
        self.transition_path.unlink()
        print("UAT synchronized to delivered main; DB/media/dependencies/operator state preserved")
        self.status()

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
        self.require_idle()
        self.require_identity(running=True)
        if self.current() != code_heads(migration_graph(self.source)):
            raise WorkflowError("UAT seed needs DB at code head; run up or explicit sync")
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
        self.require_idle()
        self.require_identity()
        self.compose("build")
        self.start_database()
        current = self.current()
        if not current and self.repository.identity()["branch"] == "detached":
            raise WorkflowError("established UAT database is unversioned; startup refused")
        require_upgradeable(current, migration_graph(self.source))
        self.stop_writers()
        self.compose("run", "--rm", "-T", "--no-deps", "dev-state-init")
        self.upgrade()
        self.compose("up", "-d", "--wait", "--wait-timeout", "180")
        self.require_identity(running=True)
        self.status()

    def status(self) -> None:
        print("Environment: persistent UAT Preview")
        identity = self.repository.identity()
        for key, value in identity.items():
            print(f"{key.title()}: {value}")
        print(f"Project: {self.project}\nURL: {self.url}")
        containers = self.containers()
        volumes = self.resource_volumes()
        if not containers and not volumes:
            print("UAT: missing; next: make uat-preview-up (attached feature only)")
            return
        for item in containers:
            labels = item["Config"].get("Labels", {})
            state = item["State"]
            health = (
                state.get("Health", {}).get("Status", "running")
                if state.get("Running")
                else "stopped"
            )
            print(
                f"{labels.get('com.docker.compose.service')}: {health}; source: {labels.get('io.florabase.source')}; launched HEAD: {labels.get('io.florabase.sha')}"
            )
        try:
            self.require_identity()
        except WorkflowError as error:
            print(f"UAT: foreign/ambiguous or invalid owner: {error}")
            raise
        if identity["branch"] == "detached":
            main = self.repository.git("rev-parse", "origin/main")
            relation = (
                "current with origin/main"
                if delivered(self.repository) == main
                and self.repository.git("rev-parse", "HEAD^{tree}")
                == self.repository.git("rev-parse", f"{main}^{{tree}}")
                else "stale but valid (behind origin/main)"
            )
            print(f"Owner: detached delivered valid; {relation} (cached origin/main: {main})")
        else:
            print("Owner: attached valid feature")
        pending = self.transition()
        print(f"Sync: {'interrupted; next: make uat-preview-sync' if pending else 'idle'}")
        graph = migration_graph(self.source)
        print(f"Code head: {','.join(code_heads(graph))}")
        if any(
            item["State"].get("Running")
            and item["Config"]["Labels"].get("com.docker.compose.service") == "db"
            for item in containers
        ):
            revisions = self.current()
            print(f"Database current: {','.join(revisions) or 'unversioned'}")
            try:
                require_upgradeable(revisions, graph)
            except WorkflowError as error:
                print(f"UAT: incompatible DB/code; stop remains safe: {error}")
                raise
        else:
            print("Database current: unavailable (database stopped; status does not start it)")
        try:
            state = self.marker_state()
            fixture = state.get(".uat-fixture.json") or {}
            print(
                f"Fixture: version {fixture.get('version', 'missing')}; state {fixture.get('state', 'missing')}; records {len(fixture.get('records', {}))}"
            )
        except WorkflowError:
            print("Fixture: unavailable (no established backend)")
        print("Next: make uat-preview-sync (delivered owner) or make uat-preview-up (same source)")
        print("UAT PREVIEW ONLY — Username: preview; Password: preview")

    def stop(self, *, remove: bool = False, confirm: str = "") -> None:
        if remove:
            raise WorkflowError("use guarded uat-preview-remove or uat-preview-reset")
        self.require_identity()
        containers = [item["Id"] for item in self.containers()]
        if containers:
            run(["docker", "container", "stop", *containers])
        self.require_identity()
        print(
            "UAT Preview stopped; containers, network, database, media and dependencies preserved"
        )

    def retirement_resources(self) -> tuple[list[str], list[dict[str, Any]], list[str]]:
        self.require_identity(retiring=True)
        containers = [item["Id"] for item in self.containers()]
        volumes = self.resource_volumes()
        networks: list[str] = []
        names = run(
            ["docker", "network", "ls", "-q", "--filter", f"name=^{self.project}_"],
            capture=True,
        ).splitlines()
        for name in names:
            network = json.loads(run(["docker", "network", "inspect", name], capture=True))[0]
            labels = network.get("Labels") or {}
            if (
                network["Name"] != f"{self.project}_internal"
                or labels.get("com.docker.compose.project") != self.project
                or labels.get("com.docker.compose.network") != "internal"
                or not set(network.get("Containers") or {}).issubset(containers)
            ):
                raise WorkflowError("ambiguous UAT retirement network identity; refused")
            networks.append(network["Id"])
        for volume in volumes:
            users = run(
                ["docker", "ps", "-aq", "--no-trunc", "--filter", f"volume={volume['Name']}"],
                capture=True,
            ).splitlines()
            if not set(users).issubset(containers):
                raise WorkflowError("UAT volume has a foreign container user; refused")
        return sorted(containers), sorted(volumes, key=lambda item: item["Name"]), sorted(networks)

    def remove(self, confirm: str) -> None:
        if confirm != self.project:
            raise WorkflowError(
                f"remove deletes ONLY UAT state; set CONFIRM_REMOVE_UAT_PREVIEW={self.project}"
            )
        containers, volumes, networks = self.retirement_resources()
        print("Retiring UAT owned by: " + str(self.source))
        print("Removing ONLY volumes: " + ", ".join(item["Name"] for item in volumes))
        # Stop every proved UAT writer before removing any container, network or volume.
        if containers:
            run(["docker", "container", "stop", *containers])
        if self.retirement_resources() != (containers, volumes, networks):
            raise WorkflowError("UAT resources changed during retirement; refused")
        if any(item["State"].get("Running") for item in self.containers()):
            raise WorkflowError("UAT writers are still running; refused")
        if containers:
            run(["docker", "container", "rm", *containers])
        if self.retirement_resources() != ([], volumes, networks):
            raise WorkflowError("UAT resources changed after stopping writers; refused")
        for network in networks:
            run(["docker", "network", "rm", network])
        if self.retirement_resources() != ([], volumes, []):
            raise WorkflowError("UAT resources changed before volume removal; refused")
        for volume in volumes:
            run(["docker", "volume", "rm", volume["Name"]])
        print("UAT Preview removed; next feature worktree can run up and seed fresh UAT")

    def reset(self, confirm: str) -> None:
        if confirm != self.project:
            raise WorkflowError(
                f"reset deletes ONLY UAT state; set CONFIRM_RESET_UAT_PREVIEW={self.project}"
            )
        if self.repository.identity()["branch"] == "detached":
            raise WorkflowError(
                "reset requires an attached feature owner; detached delivered owners use preserving sync "
                "or deliberate guarded remove"
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
    parser.add_argument(
        "action", choices=["up", "seed", "status", "stop", "sync", "reset", "remove"]
    )
    args = parser.parse_args()
    try:
        preview = UATPreview(Repository(Path.cwd()))
        with contextlib.ExitStack() as stack:
            if args.action != "status":
                lock = stack.enter_context(
                    (preview.repository.metadata / f"{preview.project}.lock").open("w")
                )
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            dispatch(preview, args.action)
    except (WorkflowError, ValueError, KeyError, OSError) as error:
        print(f"UAT Preview: {error}", file=sys.stderr)
        return 1
    return 0


def dispatch(preview: UATPreview, action: str) -> None:
    if action == "reset":
        preview.reset(os.environ.get("CONFIRM_RESET_UAT_PREVIEW", ""))
    elif action == "remove":
        preview.remove(os.environ.get("CONFIRM_REMOVE_UAT_PREVIEW", ""))
    else:
        getattr(preview, action)()


if __name__ == "__main__":
    raise SystemExit(main())
