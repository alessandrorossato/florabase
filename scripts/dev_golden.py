#!/usr/bin/env python3
"""Operate the persistent COMPREHENSIVE baseline on the exact primary DEV stack."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import golden_plan
from dev_golden_snapshot import (
    ARTIFACTS,
    LEDGER,
    Stage,
    checksums,
    command,
    isolated_stage,
    originals_identity,
    sha256,
)
from workflow_environment import (
    DEV_PROJECT,
    MEDIA_ROOT,
    Environment,
    Repository,
    WorkflowError,
    code_heads,
    dev_golden_pending,
    migration_graph,
)
from workflow_resources import ResourceError, docker, machine_lock

PG_MOUNT = "/var/lib/postgresql"
PGDATA = f"{PG_MOUNT}/18/docker"
TARGET = "florabase"
VOLUMES = ("postgres_data", "attachment_data", "frontend_node_modules")
PORTS = {"db": 5432, "backend": 8000, "frontend": 5173}
CONFIRMATIONS = {
    "init": "initialize-florabase-dev",
    "reset": "replace-florabase-dev",
    "recover": "recover-florabase-dev",
}
HELPER_LABEL = "io.florabase.dev-golden.operation"
PROJECT_LABEL = "com.docker.compose.project"
REQUIRED_SERVICES = {"db", "backend", "frontend", "dev-state-init"}


def require(condition: Any, message: str) -> None:
    if not condition:
        raise WorkflowError(message)


def settings(container: dict[str, Any]) -> dict[str, str]:
    return dict(item.split("=", 1) for item in container["Config"]["Env"])


def inspect(*args: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = json.loads(docker(*args))
    return result


def local_docker() -> None:
    host = os.environ.get("DOCKER_HOST") if not os.environ.get("DOCKER_CONTEXT") else None
    if host is None:
        host = docker("context", "inspect", "--format", "{{.Endpoints.docker.Host}}")
    require(
        host == "unix:///var/run/docker.sock",
        "DEV Golden requires the workstation Docker socket",
    )


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(json.dumps(value).encode())
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)
    sync_directory(path.parent)


def sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def exact_port(container: dict[str, Any], port: int | None, published: int | None = None) -> bool:
    bindings = container["HostConfig"].get("PortBindings") or {}
    if port is None:
        return not bindings
    return bindings == {
        f"{port}/tcp": [{"HostIp": "127.0.0.1", "HostPort": str(published or port)}]
    }


def check_snapshot(stage: Stage, owner_profile: bytes) -> dict[str, Any]:
    require(
        stage.helper("owner-export") == owner_profile,
        "Restored DEV owner profile differs",
    )
    report: dict[str, Any] = json.loads(stage.helper("verify-promoted"))
    return report


class DevGolden:
    def __init__(
        self, env: Environment, state: Path, *, ports: dict[str, int] | None = None
    ) -> None:
        self.env = env
        self.pending = state
        self.ports = ports or PORTS
        self.origin = f"http://localhost:{self.ports['frontend']}"
        self.services: dict[str, dict[str, Any]] = {}
        self.images: dict[str, str] = {}
        self.resources: dict[str, Any] = {}
        (self.head,) = code_heads(migration_graph(env.source))

    @property
    def project(self) -> str:
        return self.env.project

    def volume(self, key: str) -> str:
        return f"{self.project}_{key}"

    def validate(self, *, helpers: set[str] | None = None) -> None:
        env = self.env
        env.validate(require_durable_dev=True)
        require(env.url == self.origin, f"DEV must use {self.origin}")
        config = json.loads(env.compose("config", "--format", "json", capture=True))
        require(
            set(config["services"]) == REQUIRED_SERVICES,
            "Unexpected DEV Compose services",
        )
        require(set(config["volumes"]) == set(VOLUMES), "Unexpected DEV Compose volumes")
        require(set(config["networks"]) == {"internal"}, "Unexpected DEV Compose network")
        configured = config["services"]
        configured_db = configured["db"]["environment"]
        require(
            configured_db["POSTGRES_DB"] == configured_db["POSTGRES_USER"] == TARGET,
            "DEV Golden requires the exact local florabase database and role",
        )
        self.services = env.dev_containers(env.containers())
        require(
            set(self.services) == REQUIRED_SERVICES,
            "DEV must have all four service containers",
        )
        arguments = env.command()
        expected_files = ",".join(
            value
            for flag, value in zip(arguments[:-1], arguments[1:], strict=True)
            if flag == "--file"
        )
        expected_network = f"{self.project}_internal"
        ids = set(helpers or ())
        for service, container in self.services.items():
            ids.add(container["Id"])
            labels = container["Config"]["Labels"]
            require(
                labels.get("io.florabase.role") == "dev"
                and labels.get("io.florabase.branch") == "main"
                and labels.get("io.florabase.source") == str(env.source)
                and labels.get("com.docker.compose.project.working_dir") == str(env.source)
                and labels.get("com.docker.compose.project.config_files") == expected_files
                and container["Name"] == f"/{self.project}-{service}-1"
                and container["HostConfig"]["NetworkMode"] == expected_network
                and not container["HostConfig"]["Privileged"]
                and exact_port(container, PORTS.get(service), self.ports.get(service)),
                f"DEV {service} does not have the exact primary main identity",
            )
            mounts = {(item["Destination"], item["Type"]): item for item in container["Mounts"]}
            require(
                len(mounts) == len(configured[service].get("volumes", [])),
                f"Unexpected {service} mounts",
            )
            for spec in configured[service].get("volumes", []):
                mount = mounts.get((spec["target"], spec["type"]), {})
                expected = (
                    self.volume(spec["source"]) if spec["type"] == "volume" else spec["source"]
                )
                actual = mount.get("Name") if spec["type"] == "volume" else mount.get("Source")
                require(
                    actual == expected and mount["RW"] != spec.get("read_only", False),
                    f"DEV {service} mount differs from primary configuration",
                )
            self.images[service] = container["Image"]

        db = self.services["db"]
        database = settings(db)
        backend = settings(self.services["backend"])
        url = urlsplit(backend["FLORABASE_DATABASE_URL"])
        require(
            database["POSTGRES_DB"] == database["POSTGRES_USER"] == TARGET
            and database["PGDATA"] == PGDATA
            and db["Config"]["Image"] == configured["db"]["image"]
            and db["Config"]["Cmd"] == ["postgres"]
            and db["Config"]["Entrypoint"] == ["docker-entrypoint.sh"]
            and url.scheme == "postgresql+psycopg"
            and url.hostname == "db"
            and url.port in {None, 5432}
            and url.username == TARGET
            and url.path == f"/{TARGET}"
            and not url.query
            and not url.fragment
            and backend["FLORABASE_DATABASE_URL"]
            == configured["backend"]["environment"]["FLORABASE_DATABASE_URL"]
            and backend["FLORABASE_CANONICAL_ORIGIN"] == self.origin
            and backend["FLORABASE_ATTACHMENT_STORAGE_ROOT"] == MEDIA_ROOT
            and self.services["backend"]["Config"]["User"] == configured["backend"]["user"],
            "DEV database, authentication, or durable media settings differ from primary DEV",
        )
        for key in VOLUMES:
            name = self.volume(key)
            (volume,) = inspect("volume", "inspect", name)
            labels = volume["Labels"] or {}
            require(
                volume["Name"] == name
                and volume["Driver"] == "local"
                and volume["Scope"] == "local"
                and not volume["Options"]
                and labels.get("com.docker.compose.project") == self.project
                and labels.get("com.docker.compose.volume") == key,
                f"Foreign or ambiguous DEV volume: {name}",
            )
            self.require_users("volume", name, ids)
            self.resources[key] = {key: volume[key] for key in ("Name", "Mountpoint", "CreatedAt")}
        (network,) = inspect("network", "inspect", expected_network)
        labels = network["Labels"] or {}
        require(
            network["Name"] == expected_network
            and network["Driver"] == "bridge"
            and network["Scope"] == "local"
            and labels.get("com.docker.compose.project") == self.project
            and labels.get("com.docker.compose.network") == "internal",
            "Foreign or ambiguous DEV network",
        )
        self.require_users("network", expected_network, ids)
        self.resources["network"] = network["Id"]

    @staticmethod
    def require_users(kind: str, name: str, allowed: set[str]) -> None:
        users = set(docker("ps", "-aq", "--no-trunc", "--filter", f"{kind}={name}").splitlines())
        require(not users - allowed, f"Foreign container uses DEV {kind} {name}")

    def service(self, name: str) -> str:
        identifier: str = self.services[name]["Id"]
        return identifier

    def database(self, container: str, program: str, *args: str, **kwargs: Any) -> bytes:
        return command(["docker", "exec", "-i", container, program, "-U", TARGET, *args], **kwargs)

    def scalar(self, container: str, query: str, *, database: str = TARGET) -> str:
        return (
            self.database(
                container,
                "psql",
                "-XAt",
                "-d",
                database,
                "-v",
                "ON_ERROR_STOP=1",
                "-c",
                query,
            )
            .decode()
            .strip()
        )

    def system_id(self, container: str) -> str:
        value = self.scalar(
            container,
            "SELECT system_identifier FROM pg_control_system()",
            database="postgres",
        )
        require(value.isdigit(), "Could not prove DEV PostgreSQL cluster identity")
        return value

    def revision(self, container: str) -> str:
        return self.scalar(container, "SELECT version_num FROM alembic_version")

    def media(self, action: str, *, token: str, **kwargs: Any) -> bytes:
        writing = action in {"restore-media", "write-ledger"}
        return command(
            [
                "docker",
                "run",
                "--rm",
                "-i",
                "--network",
                "none",
                "--read-only",
                "--name",
                self.helper_name(token, "media"),
                "--label",
                f"{HELPER_LABEL}={token}",
                "--label",
                f"{PROJECT_LABEL}={self.helper_name(token, 'media')}",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--user",
                self.services["backend"]["Config"]["User"],
                "--tmpfs",
                "/tmp",
                "--env",
                "PYTHONDONTWRITEBYTECODE=1",
                "--env",
                "FLORABASE_ENVIRONMENT=test",
                "--env",
                "FLORABASE_DATABASE_URL=postgresql+psycopg://unused@invalid/unused",
                "--mount",
                f"type=volume,source={self.volume('attachment_data')},target={MEDIA_ROOT}"
                + ("" if writing else ",readonly"),
                "--mount",
                f"type=bind,source={self.env.source / 'scripts'},target=/review,readonly",
                "--mount",
                f"type=bind,source={self.env.source / 'backend/scripts'},target=/app/scripts,readonly",
                "--mount",
                f"type=bind,source={self.env.source / 'backend/src'},target=/app/src,readonly",
                "--entrypoint",
                "python",
                self.images["backend"],
                "/review/dev_golden_payload.py",
                action,
                "--live-media",
            ],
            **kwargs,
        )

    def helper_name(self, token: str, kind: str) -> str:
        return f"{self.project}-dev-golden-{token}-{kind}"

    def helpers(self, token: str) -> dict[str, str]:
        result: dict[str, str] = {}
        require(re.fullmatch(r"[0-9a-f]{32}", token), "Invalid DEV Golden operation token")
        for kind, key, path, image in (
            ("db", "postgres_data", PG_MOUNT, "db"),
            ("media", "attachment_data", MEDIA_ROOT, "backend"),
        ):
            name = self.helper_name(token, kind)
            ids = docker("ps", "-aq", "--no-trunc", "--filter", f"name=^/{name}$").splitlines()
            if not ids:
                continue
            (item,) = inspect("inspect", *ids)
            mounts = {m["Destination"]: m for m in item["Mounts"] if m["Type"] == "volume"}
            require(
                item["Name"] == f"/{name}"
                and item["Image"] == self.images[image]
                and (item["Config"]["Labels"] or {}).get(HELPER_LABEL) == token
                and (item["Config"]["Labels"] or {}).get(PROJECT_LABEL) == name
                and item["HostConfig"]["NetworkMode"] == "none"
                and exact_port(item, None)
                and set(mounts) == {path}
                and mounts[path]["Name"] == self.volume(key),
                "DEV Golden helper identity is ambiguous; recovery refused",
            )
            result[kind] = item["Id"]
        return result

    @contextmanager
    def offline_db(self, transaction: dict[str, Any]) -> Iterator[str]:
        token = transaction["token"]
        require(
            all(not item["State"]["Running"] for item in self.env.containers()),
            "Stop the proven DEV writers before using the isolated database",
        )
        self.require_users("volume", self.volume("postgres_data"), {self.service("db")})
        name = self.helper_name(token, "db")
        # Use the original image and exact PGDATA. Bypass the initializer so a missing cluster
        # cannot be recreated. No network or published ports are present during maintenance.
        identifier = docker(
            "run",
            "-d",
            "--name",
            name,
            "--label",
            f"{HELPER_LABEL}={token}",
            "--label",
            f"{PROJECT_LABEL}={name}",
            "--network",
            "none",
            "--user",
            "postgres",
            "--entrypoint",
            "postgres",
            "--mount",
            f"type=volume,source={self.volume('postgres_data')},target={PG_MOUNT}",
            self.images["db"],
            "-D",
            PGDATA,
            "-c",
            "listen_addresses=",
        )
        try:
            for _ in range(90):
                try:
                    if self.system_id(identifier) == transaction["system_id"]:
                        break
                    raise WorkflowError("Offline PostgreSQL system identifier changed")
                except WorkflowError as error:
                    if str(error) != "snapshot command failed (docker exec)":
                        raise
                    time.sleep(1)
            else:
                raise WorkflowError("Offline PostgreSQL did not become ready")
            yield identifier
        finally:
            self.remove_helpers(token)

    def remove_helpers(self, token: str) -> None:
        for kind, identifier in self.helpers(token).items():
            if kind == "db":
                docker("stop", "--timeout", "60", identifier)
                docker("rm", identifier)
            else:
                docker("rm", "--force", identifier)

    def capture(self, container: str, directory: Path, token: str) -> None:
        directory.mkdir(mode=0o700)
        self.database(
            container,
            "pg_dump",
            "-d",
            TARGET,
            "-Fc",
            "--no-owner",
            "--no-privileges",
            destination=directory / ARTIFACTS[0],
        )
        self.media("archive", token=token, destination=directory / ARTIFACTS[1])
        self.media("read-ledger", token=token, destination=directory / LEDGER)
        sync_directory(directory)
        sync_directory(directory.parent)

    def restore(self, container: str, directory: Path, token: str) -> None:
        self.database(container, "dropdb", "--if-exists", TARGET)
        self.database(container, "createdb", "--template=template0", TARGET)
        self.database(
            container,
            "pg_restore",
            "-d",
            TARGET,
            "--single-transaction",
            "--no-owner",
            "--no-privileges",
            source=directory / ARTIFACTS[0],
        )
        self.media("restore-media", token=token, source=directory / ARTIFACTS[1])
        self.media("write-ledger", token=token, source=directory / LEDGER)

    def require_online(self) -> None:
        require(
            all(self.services[name]["State"]["Running"] for name in PORTS),
            "Start primary DEV with make dev-up first",
        )
        require(
            not self.services["dev-state-init"]["State"]["Running"],
            "DEV state initializer is still running",
        )

    def pin_available(self) -> bool:
        pin = golden_plan.load_manifest()["profiles"]["comprehensive"]["expected"]["baseline"]
        revision: str = pin["schema_revision"]
        digest: str = pin["plan_sha256"]
        plan = golden_plan.build_plan("comprehensive")
        return self.head == revision and golden_plan.plan_digest(plan) == digest

    def status(self) -> None:
        if self.pending.exists():
            print(
                f"DEV Golden maintenance pending: {self.pending}. Use dev-golden-reset RECOVER=1."
            )
            return
        if not self.env.containers():
            self.env.validate(require_durable_dev=True)
            print("DEV has no service containers. Start primary DEV with make dev-up.")
            return
        self.validate()
        self.env.status()
        if not self.services["backend"]["State"]["Running"]:
            print("DEV Golden ledger unavailable while the backend is stopped")
            return
        raw = command(
            [
                "docker",
                "exec",
                self.service("backend"),
                "python",
                "-c",
                f"from pathlib import Path; p=Path({str(Path(MEDIA_ROOT) / LEDGER)!r}); "
                "print(p.read_text() if p.is_file() else '')",
            ]
        )
        if raw.strip():
            ledger = json.loads(raw)
            print(
                json.dumps(
                    {
                        key: ledger.get(key)
                        for key in (
                            "profile",
                            "schema_revision",
                            "plan_sha256",
                            "state",
                        )
                    },
                    sort_keys=True,
                )
            )
        else:
            print("DEV Golden ledger absent")

    def verify(self) -> int:
        require(not self.pending.exists(), "DEV Golden recovery is pending")
        self.validate()
        self.require_online()
        if not self.pin_available() or self.revision(self.service("db")) != self.head:
            print("baseline-unavailable: DEV schema, primary code and COMPREHENSIVE pin must agree")
            return 4
        with tempfile.TemporaryDirectory(prefix="florabase-dev-golden-verify-") as temporary:
            snapshot = Path(temporary) / "collection"
            self.capture(self.service("db"), snapshot, uuid.uuid4().hex)
            if not (snapshot / LEDGER).stat().st_size:
                print("baseline-unavailable: DEV Golden ledger absent")
                return 4
            with isolated_stage(self.env.source) as stage:
                stage.load(snapshot)
                report = json.loads(stage.helper("verify-promoted"))
                print(json.dumps(report, sort_keys=True))
                return {
                    "baseline-verified": 0,
                    "invariant-valid-baseline-modified": 3,
                    "domain-invalid": 1,
                    "baseline-unavailable": 4,
                }[report["state"]]

    def write_journal(self, transaction: dict[str, Any], phase: str) -> None:
        transaction["phase"] = phase
        atomic_json(self.pending, transaction)

    def restart(self, transaction: dict[str, Any]) -> None:
        require(not self.helpers(transaction["token"]), "DEV Golden helper still exists")
        self.validate()
        self.write_journal(transaction, "start")
        start = time.monotonic()
        self.env.compose("start", "--wait", "--wait-timeout", "180", "db", "backend", "frontend")
        self.pending.unlink()
        sync_directory(self.pending.parent)
        print(f"DEV healthy after {time.monotonic() - start:.1f}s at {self.env.url}")

    def require_current(self) -> None:
        self.validate()
        self.require_online()
        identity = self.env.repo.identity()
        for service in ("backend", "frontend"):
            labels = self.services[service]["Config"]["Labels"]
            require(
                labels.get("io.florabase.sha") == identity["sha"]
                and labels.get("io.florabase.dirty") == identity["dirty"] == "no",
                "Refresh DEV application containers from clean primary main with make dev-up",
            )
        db = self.service("db")
        require(self.revision(db) == self.head, "Upgrade DEV explicitly before promotion")
        standard = self.scalar(
            db,
            """
            SELECT current_db.datdba = current_user::regrole
                AND current_db.datacl IS NULL AND current_db.datconnlimit = -1
                AND current_db.datallowconn AND NOT current_db.datistemplate
                AND NOT EXISTS (SELECT FROM pg_db_role_setting WHERE setdatabase = current_db.oid)
                AND shobj_description(current_db.oid, 'pg_database') IS NULL
                AND (current_db.encoding, current_db.datlocprovider, current_db.datcollate,
                     current_db.datctype, current_db.datlocale, current_db.dattablespace)
                    IS NOT DISTINCT FROM
                    (standard_db.encoding, standard_db.datlocprovider, standard_db.datcollate,
                     standard_db.datctype, standard_db.datlocale, standard_db.dattablespace)
            FROM pg_database current_db CROSS JOIN pg_database standard_db
            WHERE current_db.datname = current_database() AND standard_db.datname = 'template0'
        """,
        )
        require(standard == "t", "DEV database has nonstandard database-level settings")

    @contextmanager
    def maintenance(self) -> Iterator[tuple[str, Path, dict[str, Any]]]:
        require(
            not self.pending.exists(),
            "DEV Golden recovery is pending; use dev-golden-reset RECOVER=1",
        )
        self.require_current()
        token = uuid.uuid4().hex
        self.pending.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        sync_directory(self.pending.parent.parent)
        operation = self.pending.parent / token
        operation.mkdir(mode=0o700)
        sync_directory(operation.parent)
        transaction: dict[str, Any] = {
            "token": token,
            "source": str(self.env.source),
            "project": self.project,
            "system_id": self.system_id(self.service("db")),
            "resources": self.resources,
            "containers": {name: self.service(name) for name in REQUIRED_SERVICES},
            "head": self.head,
            "source_sha": self.env.repo.git("rev-parse", "HEAD"),
        }
        self.write_journal(transaction, "preflight")
        try:
            self.env.stop_dev()
            with self.offline_db(transaction) as offline:
                yield offline, operation, transaction
            self.restart(transaction)
        except BaseException:
            if transaction["phase"] == "preflight":
                self.restart(transaction)
            raise

    def verified_backup(
        self, stage: Stage, offline: str, operation: Path, transaction: dict[str, Any]
    ) -> Path:
        backup = operation / "before"
        self.capture(offline, backup, transaction["token"])
        stage.load(backup)
        transaction["backup"] = checksums(backup)
        atomic_json(operation / "before.json", transaction)
        print(f"Verified recovery snapshot {operation.name}: {backup}", flush=True)
        return backup

    def change(self, action: str) -> None:
        require(
            not self.pending.exists(),
            "DEV Golden recovery is pending; use dev-golden-reset RECOVER=1",
        )
        self.require_current()
        require(
            self.pin_available(),
            "COMPREHENSIVE pin is unavailable for this primary schema and plan",
        )
        with isolated_stage(self.env.source) as stage:
            stage.prepare_empty()
            print(json.dumps(stage.golden("generate"), sort_keys=True), flush=True)
            print(json.dumps(stage.golden("verify-baseline"), sort_keys=True), flush=True)
            with tempfile.TemporaryDirectory(prefix="florabase-dev-golden-promotion-") as temporary:
                scratch = Path(temporary)
                approved = scratch / "approved"
                stage.export(approved)
                with self.maintenance() as (offline, operation, transaction):
                    token = transaction["token"]
                    backup = self.verified_backup(stage, offline, operation, transaction)
                    state = stage.helper("state").decode().strip()
                    require(
                        action == "reset" or state == "empty",
                        "DEV collection is occupied; use explicit dev-golden-reset authorization",
                    )
                    credentials = stage.helper("owner-export")
                    stage.load(approved)
                    stage.helper("owner-import", data=credentials)
                    promoted = scratch / "promoted"
                    stage.export(promoted)
                    require(
                        check_snapshot(stage, credentials)["state"] == "baseline-verified",
                        "Prepared collection failed baseline verification",
                    )
                    self.write_journal(transaction, "replace")
                    require(
                        checksums(backup) == transaction["backup"],
                        "Backup checksum changed",
                    )
                    self.restore(offline, promoted, token)
                    captured = scratch / "after"
                    self.capture(offline, captured, token)
                    stage.load(captured)
                    report = check_snapshot(stage, credentials)
                    require(
                        report["state"] == "baseline-verified",
                        "Promoted DEV failed baseline verification",
                    )
                    print(json.dumps(report, sort_keys=True), flush=True)

    def restore_checked(self, stage: Stage, offline: str, backup: Path, token: str) -> None:
        stage.load(backup)
        database_identity = stage.database_identity()
        self.restore(offline, backup, token)
        with tempfile.TemporaryDirectory(prefix="florabase-dev-golden-recovery-") as temp:
            restored = Path(temp) / "restored"
            self.capture(offline, restored, token)
            stage.load(restored)
            require(
                self.revision(offline) == self.head
                and stage.database_identity() == database_identity
                and originals_identity(restored) == originals_identity(backup)
                and sha256(restored / LEDGER) == sha256(backup / LEDGER),
                "Recovered database, originals or ledger differ from the verified pair",
            )

    def restore_backup(self, token: str) -> None:
        require(re.fullmatch(r"[0-9a-f]{32}", token), "Invalid DEV Golden backup ID")
        require(not self.pending.exists(), "Recover the pending DEV Golden operation first")
        self.require_current()
        operation = self.pending.parent / token
        backup = operation / "before"
        recorded = json.loads((operation / "before.json").read_text())
        require(
            recorded["token"] == token
            and recorded["source"] == str(self.env.source)
            and recorded["project"] == self.project
            and recorded["head"] == self.head
            and recorded["resources"] == self.resources
            and recorded["system_id"] == self.system_id(self.service("db"))
            and recorded["backup"] == checksums(backup),
            "Backup identity or pair checksum differs from this DEV installation",
        )
        with (
            isolated_stage(self.env.source) as stage,
            tempfile.TemporaryDirectory(prefix="florabase-dev-golden-archived-") as temporary,
        ):
            stage.load(backup)
            with self.maintenance() as (offline, operation, transaction):
                self.verified_backup(stage, offline, operation, transaction)
                credentials = stage.helper("owner-export")
                require(checksums(backup) == recorded["backup"], "Backup checksum changed")
                stage.load(backup)
                stage.helper("owner-import", data=credentials)
                selected = Path(temporary) / "selected"
                stage.export(selected)
                self.write_journal(transaction, "replace")
                self.restore_checked(stage, offline, selected, transaction["token"])
                require(
                    stage.helper("owner-export") == credentials,
                    "Restored DEV owner profile differs",
                )
        print(f"Restored verified DEV backup {token}")

    def recover(self) -> None:
        require(self.pending.is_file(), "No pending DEV Golden operation")
        transaction = json.loads(self.pending.read_text())
        token = transaction["token"]
        require(
            transaction["source"] == str(self.env.source)
            and transaction["project"] == self.project
            and transaction["head"] == self.head
            and transaction["source_sha"] == self.env.repo.git("rev-parse", "HEAD")
            and transaction["phase"] in {"preflight", "replace", "start"},
            "Pending operation belongs to another source, project or code head",
        )
        self.services = self.env.dev_containers(self.env.containers())
        self.images = {name: item["Image"] for name, item in self.services.items()}
        helpers = self.helpers(token)
        self.validate(helpers=set(helpers.values()))
        require(
            self.resources == transaction["resources"]
            and transaction["containers"]
            == {name: self.service(name) for name in REQUIRED_SERVICES},
            "DEV Docker identities changed during the operation",
        )
        if transaction["phase"] == "replace":
            require(
                all(not item["State"]["Running"] for item in self.services.values()),
                "DEV writers are running during incomplete replacement; recovery refused",
            )
            backup = self.pending.parent / token / "before"
            require(
                checksums(backup) == transaction["backup"],
                "Recovery snapshot checksum changed",
            )
            self.remove_helpers(token)
            with isolated_stage(self.env.source) as stage:
                stage.load(backup)
                with self.offline_db(transaction) as offline:
                    self.restore_checked(stage, offline, backup, token)
            print(f"Recovered previous DEV collection from {backup}", flush=True)
        else:
            self.remove_helpers(token)
        self.restart(transaction)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", "verify", "init", "reset"))
    args = parser.parse_args()
    action = (
        "recover" if args.action == "reset" and os.environ.get("RECOVER") == "1" else args.action
    )
    try:
        if action in CONFIRMATIONS:
            expected = CONFIRMATIONS[action]
            require(
                os.environ.get("CONFIRM_DEV_GOLDEN") == expected,
                f"Set CONFIRM_DEV_GOLDEN={expected} for this DEV Golden operation",
            )
        local_docker()
        repo = Repository(Path.cwd())
        repo.require_origin()
        require(
            repo.source == repo.primary and repo.git("branch", "--show-current") == "main",
            "Run DEV Golden from the primary main checkout",
        )
        env = Environment(repo, "dev")
        require(env.project == DEV_PROJECT, "Unexpected DEV project")
        pending = dev_golden_pending(env)
        recovering = action == "recover" and not os.environ.get("BACKUP") and pending.is_file()
        require(not repo.git("status", "--porcelain"), "Primary main must be clean")
        require(
            action in {"status", "verify"}
            or recovering
            or repo.git("rev-parse", "HEAD") == repo.git("rev-parse", "origin/main"),
            "Primary main must match origin/main",
        )
        target = DevGolden(env, pending)
        with machine_lock(DEV_PROJECT, f"DEV Golden {action}"):
            if action == "status":
                target.status()
                return 0
            with machine_lock("verification-full", f"DEV Golden {action}"):
                require(
                    action == "recover" or not os.environ.get("BACKUP"),
                    "BACKUP requires RECOVER=1",
                )
                if action == "verify":
                    return target.verify()
                if action == "recover":
                    backup = os.environ.get("BACKUP", "")
                    if backup:
                        target.restore_backup(backup)
                    else:
                        target.recover()
                else:
                    target.change(action)
    except (WorkflowError, ResourceError, OSError, ValueError, KeyError) as error:
        print(f"DEV Golden: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
