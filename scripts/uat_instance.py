#!/usr/bin/env python3
"""Per-worktree UAT instances: own project, port, PostgreSQL, media and golden dataset profile."""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
import re
import socket
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

from uat_preview import VOLUMES, UATPreview
from workflow_environment import (
    MEDIA_ROOT,
    Repository,
    WorkflowError,
    code_heads,
    migration_graph,
    require_upgradeable,
    run,
)
from workflow_resources import ResourceError, machine_lock

PREFIX = "florabase-uat-branch-"
NAME = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?")
# Four slots bound networks (Docker address pools), image tags and memory; the singleton UAT
# Preview/Review keep 15174, Sourcing 15175, Stable Preview 15173 and DEV 5173.
PORTS = range(15180, 15184)
PROFILES = ("smoke", "comprehensive")
DATABASE = "golden_uat"  # Accepted by golden_dataset.uat_instance_target, never by the v4 fixture.
LEDGER = ".golden-dataset.json"
OWNER = "UAT INSTANCE ONLY — Username: golden-owner; Password: disposable-golden-owner-password"
# One capacity lock with canonical FULL: heavy builds and seeds never overlap a FULL gate.
HEAVY = {"up", "reset", "seed"}
LABEL_INSTANCE = "io.florabase.uat.instance"


def instance_volumes() -> list[dict[str, Any]]:
    """Every UAT instance volume on this Docker engine, whatever its source."""
    names = run(
        ["docker", "volume", "ls", "-q", "--filter", f"label={LABEL_INSTANCE}"], capture=True
    ).splitlines()
    if not names:
        return []
    return list(json.loads(run(["docker", "volume", "inspect", *names], capture=True)))


def published_ports(exclude: set[str]) -> set[int]:
    """Host ports bound or reserved by any container (running or stopped) outside `exclude`."""
    ids = set(run(["docker", "ps", "-aq", "--no-trunc"], capture=True).splitlines()) - exclude
    if not ids:
        return set()
    ports: set[int] = set()
    for container in json.loads(run(["docker", "inspect", *sorted(ids)], capture=True)):
        bindings = [
            *((container.get("HostConfig") or {}).get("PortBindings") or {}).values(),
            *((container.get("NetworkSettings") or {}).get("Ports") or {}).values(),
        ]
        ports |= {
            int(item["HostPort"])
            for group in bindings
            if group
            for item in group
            if str(item.get("HostPort", "")).isdigit()
        }
    return ports


def bindable(port: int) -> bool:
    with socket.socket() as probe:
        # TIME_WAIT from a just-stopped instance is not a listener; a real listener still refuses.
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


class UATInstance(UATPreview):
    PROJECT_PATTERN = PREFIX + NAME.pattern
    ROLE_LABEL = "uat-instance"
    WORKFLOW_MODE = "uat-instance"
    LABEL = "UAT instance"
    CONFIRM_RESET = "CONFIRM_RESET_UAT_INSTANCE"
    CONFIRM_REMOVE = "CONFIRM_REMOVE_UAT_INSTANCE"
    PORTS: range | tuple[int, ...] = PORTS

    def __init__(self, repository: Repository, profile: str = "") -> None:
        super().__init__(repository)
        if profile and profile not in PROFILES:
            raise WorkflowError(f"PROFILE must be one of {', '.join(PROFILES)}")
        self.requested_profile = profile
        record = self.recorded()
        self.port: int | None = None
        if record:
            self.instance, self.port, self.profile = record
        else:
            self.instance, self.profile = self.derived_name(), profile or "smoke"
            self.project = PREFIX + self.instance
        self.url = f"http://localhost:{self.port or 0}"

    def derived_name(self) -> str:
        branch = self.repository.identity()["branch"]
        if branch == "detached":
            raise WorkflowError(
                "no UAT instance is recorded for this worktree; start one from an attached branch"
            )
        name = branch.replace("/", "-")
        if not NAME.fullmatch(name):
            raise WorkflowError(
                f"branch {branch} cannot name a UAT instance (lowercase letters, digits, '-' and "
                "'/' only, at most 40 characters)"
            )
        return name

    def recorded(self) -> tuple[str, int, str] | None:
        """The one instance whose volumes name this source; labels are the allocation record."""
        owned = [
            item
            for item in instance_volumes()
            if (item.get("Labels") or {}).get("io.florabase.source") == str(self.source)
        ]
        if not owned:
            return None
        records = {
            (
                (item.get("Labels") or {}).get(LABEL_INSTANCE, ""),
                (item.get("Labels") or {}).get("io.florabase.uat.port", ""),
                (item.get("Labels") or {}).get("io.florabase.uat.profile", ""),
            )
            for item in owned
        }
        if len(records) != 1:
            raise WorkflowError("this source owns ambiguous UAT instance volumes; refused")
        name, port, profile = records.pop()
        if (
            not NAME.fullmatch(name)
            or not port.isdigit()
            or int(port) not in self.PORTS
            or profile not in PROFILES
            or not {item["Name"] for item in owned} <= {f"{PREFIX}{name}_{key}" for key in VOLUMES}
        ):
            raise WorkflowError("unrecognized UAT instance volume record; refused")
        self.project = PREFIX + name
        return name, int(port), profile

    def environment(self) -> dict[str, str]:
        env = super().environment()
        password = env["POSTGRES_PASSWORD"]
        env.update(
            {
                "POSTGRES_DB": DATABASE,
                "POSTGRES_USER": DATABASE,
                "FLORABASE_DATABASE_URL": (
                    f"postgresql+psycopg://{DATABASE}:{password}@db:5432/{DATABASE}"
                ),
                "FRONTEND_PORT": str(self.port or ""),
                "FLORABASE_ROLE": self.ROLE_LABEL,
                "FLORABASE_UAT_INSTANCE": self.instance,
                "FLORABASE_UAT_PROFILE": self.profile,
            }
        )
        return env

    def command(self, *args: str) -> list[str]:
        return [*super().command(), "--file", str(self.source / "compose.uat-instance.yaml"), *args]

    def require_profile(self) -> None:
        """Only a confirmed reset changes the profile; up and seed refuse a different request."""
        if self.requested_profile and self.requested_profile != self.profile:
            raise WorkflowError(
                f"{self.project} holds the {self.profile} profile; change it only with make "
                f"uat-instance-reset PROFILE={self.requested_profile} "
                f"{self.CONFIRM_RESET}={self.project}"
            )

    def remove_oneoffs(self) -> None:
        """One-off seed/validate containers an interrupted run left, of exactly this source."""
        ids = run(
            [
                "docker",
                "ps",
                "-aq",
                "--no-trunc",
                "--filter",
                f"label=com.docker.compose.project={self.project}",
                "--filter",
                "label=com.docker.compose.oneoff=True",
            ],
            capture=True,
        ).splitlines()
        items = json.loads(run(["docker", "inspect", *ids], capture=True)) if ids else []
        for item in items:  # Prove every one before removing any.
            labels = item["Config"].get("Labels") or {}
            if (
                labels.get("com.docker.compose.project") != self.project
                or labels.get("com.docker.compose.service") != "backend"
                or labels.get("io.florabase.source") != str(self.source)
                or labels.get("com.docker.compose.project.working_dir") != str(self.source)
            ):
                raise WorkflowError("unrecognized UAT instance one-off container; refused")
        for item in items:
            run(["docker", "rm", "--force", item["Id"]])

    def require_recorded(self) -> None:
        if self.port is None:
            raise WorkflowError(
                f"no UAT instance exists for this worktree; next: make uat-instance-up "
                f"(would create {self.project})"
            )

    def allocate(self) -> None:
        """Choose or re-prove this instance's port and name against every other owner."""
        others = [
            item
            for item in instance_volumes()
            if (item.get("Labels") or {}).get("io.florabase.source") != str(self.source)
        ]
        claimed = {(item.get("Labels") or {}).get(LABEL_INSTANCE) for item in others}
        if self.instance in claimed:
            owner = next(
                (item.get("Labels") or {}).get("io.florabase.source")
                for item in others
                if (item.get("Labels") or {}).get(LABEL_INSTANCE) == self.instance
            )
            raise WorkflowError(f"{self.project} belongs to {owner}; refused")
        taken = {(item.get("Labels") or {}).get("io.florabase.uat.port") for item in others}
        own = {item["Id"] for item in self.containers()}
        busy = published_ports(own)
        if self.port is None:
            if {port for port in self.PORTS if str(port) in taken} == set(self.PORTS):
                raise WorkflowError(
                    f"all {len(self.PORTS)} UAT instance slots are allocated; remove an unused "
                    "instance first (make uat-instance-list)"
                )
            free = [
                port
                for port in self.PORTS
                if str(port) not in taken and port not in busy and bindable(port)
            ]
            if not free:
                raise WorkflowError("no free UAT instance port; nothing was created")
            self.port = free[0]
        elif str(self.port) in taken or self.port in busy:
            raise WorkflowError(f"port {self.port} is claimed by another project; refused")
        elif not any(item["State"].get("Running") for item in self.containers()) and not bindable(
            self.port
        ):
            raise WorkflowError(f"port {self.port} is held by another listener; refused")
        self.url = f"http://localhost:{self.port}"
        self.require_network_capacity()

    def require_network_capacity(self) -> None:
        """Fail before building when Docker's address pools cannot hold one more network."""
        if run(
            ["docker", "network", "ls", "-q", "--filter", f"name=^{self.project}_internal$"],
            capture=True,
        ):
            return
        probe = f"{self.project}-pool-probe-{uuid.uuid4().hex[:8]}"
        try:
            run(
                ["docker", "network", "create", "--label", "io.florabase.role=pool-probe", probe],
                capture=True,
            )
        except WorkflowError as error:
            raise WorkflowError(
                "Docker cannot allocate another network (address pools exhausted?); stop or "
                "remove unused projects; nothing was created"
            ) from error
        finally:
            # By exact name, so even an interrupted create cannot leave a pool consumed.
            if run(["docker", "network", "ls", "-q", "--filter", f"name=^{probe}$"], capture=True):
                run(["docker", "network", "rm", probe])

    def marker_state(self) -> dict[str, Any]:
        # Read ONLY the proven instance media volume, read-only, without the ledger's records.
        backend = next(
            (
                item
                for item in self.containers()
                if item["Config"]["Labels"].get("com.docker.compose.service") == "backend"
            ),
            None,
        )
        if backend is None:
            raise WorkflowError("UAT instance dataset unavailable; established backend required")
        program = (
            "import json; from pathlib import Path; "
            f"p=Path({MEDIA_ROOT!r})/{LEDGER!r}; "
            "v=json.loads(p.read_text()) if p.is_file() else None; "
            "print(json.dumps(v and {**{k: v.get(k) for k in "
            "['dataset','profile','version','seed','anchor_date','volume','plan_sha256',"
            "'schema_revision','state','diagnostic']}, 'records': len(v.get('records', {}))}))"
        )
        environment = self.environment()
        output = run(
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
                environment["LOCAL_UID"] + ":" + environment["LOCAL_GID"],
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
        return {LEDGER: json.loads(output)}

    def require_marker(self) -> dict[str, Any]:
        state = self.marker_state()
        ledger = state[LEDGER]
        if not ledger or ledger.get("state") != "ready" or ledger.get("profile") != self.profile:
            raise WorkflowError("missing, incomplete or mismatched UAT instance dataset; refused")
        return state

    def golden(self, action: str) -> subprocess.CompletedProcess[str]:
        self.require_identity(running=True)
        # The golden runtime is an explicit read-only mount, absent from production images.
        return subprocess.run(
            self.command(
                "run",
                "--rm",
                "-T",
                "--no-deps",
                "--volume",
                f"{self.source / 'scripts'}:/golden:ro",
                "backend",
                "python",
                "/golden/golden_dataset.py",
                action,
                "--profile",
                self.profile,
            ),
            env=self.environment(),
            text=True,
            stdout=subprocess.PIPE,
            check=False,
        )

    def seed(self) -> None:
        self.require_recorded()
        self.require_profile()
        self.require_identity(running=True)
        if self.current() != code_heads(migration_graph(self.source)):
            raise WorkflowError(
                "UAT instance seed needs the DB at code head; run make uat-instance-up"
            )
        result = self.golden("generate")
        print(result.stdout, end="")
        if result.returncode:
            raise WorkflowError(
                f"golden {self.profile} generation refused or failed; inspect, then "
                f"make uat-instance-reset {self.CONFIRM_RESET}={self.project}"
            )
        print(f"UAT instance {self.instance} seeded with golden {self.profile.upper()}")
        print(OWNER)

    def validate_dataset(self) -> int:
        """0 verified, 1 domain-invalid or refused, 3 changed since seed, 4 baseline unavailable."""
        self.require_recorded()
        self.require_identity(running=True)
        result = self.golden("verify-baseline")
        print(result.stdout, end="")
        lines = result.stdout.splitlines()
        try:
            state = json.loads(lines[-1]).get("state", "refused") if lines else "refused"
        except ValueError:
            state = "refused"
        print(f"UAT instance {self.instance} dataset ({self.profile}): {state}")
        return result.returncode

    def up(self) -> None:
        self.require_profile()
        self.require_context()  # Refuse a wrong source before any Docker probe or allocation.
        self.allocate()
        super().up()

    def reset(self, confirm: str) -> None:
        if confirm == self.project and self.requested_profile:
            self.profile = self.requested_profile  # Fresh volumes carry the new profile label.
        self.require_recorded()
        if confirm == self.project:
            self.remove_oneoffs()
        super().reset(confirm)

    def stop(self, *, remove: bool = False, confirm: str = "") -> None:
        self.require_recorded()
        super().stop(remove=remove, confirm=confirm)

    def remove(self, confirm: str) -> None:
        self.require_recorded()
        if confirm == self.project:
            self.remove_oneoffs()
        super().remove(confirm)
        # Exact development tags only this project builds; a tag still in use is retained.
        for service in ("backend", "frontend"):
            tag = f"{self.project}-{service}-development"
            if run(["docker", "image", "ls", "-q", tag], capture=True):
                try:
                    run(["docker", "image", "rm", tag])
                except WorkflowError:
                    print(f"Retained image tag {tag}: still in use")

    def status(self) -> None:
        print(f"Environment: per-worktree UAT instance {self.instance}")
        for key, value in self.repository.identity().items():
            print(f"{key.title()}: {value}")
        print(f"Project: {self.project}\nProfile: {self.profile}")
        if self.port is None:
            print("Instance: missing; next: make uat-instance-up [PROFILE=smoke|comprehensive]")
            return
        print(f"URL: {self.url}")
        containers = self.containers()
        for item in containers:
            labels = item["Config"].get("Labels", {})
            state = item["State"]
            health = (
                state.get("Health", {}).get("Status", "running")
                if state.get("Running")
                else "stopped"
            )
            print(
                f"{labels.get('com.docker.compose.service')}: {health}; "
                f"source: {labels.get('io.florabase.source')}; "
                f"launched HEAD: {labels.get('io.florabase.sha')}"
            )
        self.require_identity()
        print("Owner: valid")
        graph = migration_graph(self.source)
        print(f"Code head: {','.join(code_heads(graph))}")
        if any(
            item["State"].get("Running")
            and item["Config"]["Labels"].get("com.docker.compose.service") == "db"
            for item in containers
        ):
            revisions = self.current()
            print(f"Database current: {','.join(revisions) or 'unversioned'}")
            require_upgradeable(revisions, graph)
        else:
            print("Database current: unavailable (database stopped; status does not start it)")
        try:
            ledger = self.marker_state()[LEDGER]
        except WorkflowError:
            ledger = None
            print("Dataset: unavailable (no established backend)")
        else:
            if ledger is None:
                print("Dataset: not seeded; next: make uat-instance-seed")
            else:
                print("Dataset manifest: " + json.dumps(ledger, sort_keys=True))
        print(OWNER)


def list_instances() -> None:
    """Machine-wide read-only view of every instance allocation and its running state."""
    groups: dict[str, dict[str, Any]] = {}
    for item in instance_volumes():
        labels = item.get("Labels") or {}
        entry = groups.setdefault(
            labels.get(LABEL_INSTANCE, "?"),
            {
                "port": labels.get("io.florabase.uat.port"),
                "profile": labels.get("io.florabase.uat.profile"),
                "sources": set(),
            },
        )
        entry["sources"].add(labels.get("io.florabase.source", "?"))
    print(f"UAT instances: {len(groups)} of {len(PORTS)} slots ({PORTS.start}-{PORTS.stop - 1})")
    for name, entry in sorted(groups.items()):
        project = PREFIX + name
        running = run(
            [
                "docker",
                "ps",
                "-q",
                "--filter",
                f"label=com.docker.compose.project={project}",
            ],
            capture=True,
        ).splitlines()
        sources = sorted(entry["sources"])
        present = all(Path(source).is_dir() for source in sources)
        print(
            f"{project}: port {entry['port']}; profile {entry['profile']}; "
            f"{'running' if running else 'stopped'} ({len(running)} containers); "
            f"source {', '.join(sources)}{'' if present else ' (MISSING SOURCE)'}"
        )


ACTIONS = ("up", "seed", "status", "validate", "stop", "reset", "remove", "list")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=ACTIONS)
    parser.add_argument("--profile", default="", help="smoke (default) or comprehensive")
    args = parser.parse_args()
    try:
        if args.action == "list":
            list_instances()
            return 0
        instance = UATInstance(Repository(Path.cwd()), args.profile)
        with contextlib.ExitStack() as stack:
            if args.action != "status":
                lock = stack.enter_context(
                    (instance.repository.metadata / f"{instance.project}.lock").open("w")
                )
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                stack.enter_context(machine_lock(instance.project, f"{instance.project} lifecycle"))
            if args.action in HEAVY:
                stack.enter_context(
                    machine_lock(
                        "verification-full",
                        "heavy build capacity (canonical FULL or a UAT instance build/seed)",
                    )
                )
            return dispatch(instance, args.action)
    except BlockingIOError:
        print("UAT instance: another lifecycle command holds this instance", file=sys.stderr)
        return 1
    except (WorkflowError, ResourceError, ValueError, KeyError, OSError) as error:
        print(f"UAT instance: {error}", file=sys.stderr)
        return 1


def dispatch(instance: UATInstance, action: str) -> int:
    if action == "reset":
        instance.reset(os.environ.get(UATInstance.CONFIRM_RESET, ""))
    elif action == "remove":
        instance.remove(os.environ.get(UATInstance.CONFIRM_REMOVE, ""))
    elif action == "validate":
        return instance.validate_dataset()
    else:
        getattr(instance, action)()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
