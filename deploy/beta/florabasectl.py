#!/usr/bin/env python3
"""Florabase beta host controller (BETA-RUNTIME-001).

Python >= 3.8 standard library only, so the release bundle runs on Synology DSM and other Linux
Docker hosts without installation. Every mutating command takes one host lock and appends to a
durable journal. The operator runbook is docs/beta-runtime-001.md.
"""

from __future__ import annotations

import argparse
import datetime
import fcntl
import getpass
import hashlib
import http.cookies
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import IO, Any, Dict, Sequence

FORMAT = 1
PROJECT = "florabase-prod"
PLATFORM = "linux/amd64"
SOURCE_URL = "https://github.com/alessandrorossato/florabase"
MIN_ENGINE = (24, 0)
MIN_COMPOSE = (2, 20)
POSTGRES_UID = 70
BACKEND_UID = 10001
RESTIC_IMAGE = (
    "docker.io/restic/restic:0.17.3"
    "@sha256:8f5a62b422a2cb1277ea0dd6e826fe1acf649e5b9f02d60e5268d5fd1976255a"
)
BUNDLE = Path(__file__).resolve().parent
CONTAINER_REFERENCE = "/var/lib/florabase/reference"
REFERENCE_SETTINGS = {
    "wfo": "FLORABASE_WFO_SNAPSHOT_PATH",
    "wcvp-v16": "FLORABASE_WCVP_V16_SNAPSHOT_PATH",
}
SESSION_COOKIE = "__Host-florabase-session"
SERVICES = ("db", "backend", "frontend")
PHASES = ("validated", "quiesced", "backed_up", "migrated", "pinned", "started", "accepted")
DIGEST = r"sha256:[a-f0-9]{64}"
BACKUP_MAX_AGE_HOURS = 26

Json = Dict[str, Any]

# Read-only probes executed in a backend image (WORKDIR /app holds alembic.ini).
HEADS_SCRIPT = (
    "from alembic.config import Config\n"
    "from alembic.script import ScriptDirectory\n"
    "print(' '.join(sorted(ScriptDirectory.from_config(Config('alembic.ini')).get_heads())))\n"
)
PROBE_SCRIPT = r"""
import json, sys
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from florabase.db.session import get_engine
script = ScriptDirectory.from_config(Config("alembic.ini"))
heads = sorted(script.get_heads())
known = set()
for head in heads:
    known.update(revision.revision for revision in script.iterate_revisions(head, "base"))
counts = None
with get_engine().connect() as connection:
    current = sorted(MigrationContext.configure(connection).get_current_heads())
    tables = sorted(inspect(connection).get_table_names(schema="public"))
    if "--counts" in sys.argv:
        counts = {}
        for table in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            counts[table] = connection.execute(text("SELECT count(*) FROM public." + quoted)).scalar_one()
print("FLORABASE_PROBE " + json.dumps({"heads": heads, "current": current,
    "known": sorted(known & set(current)), "tables": tables, "counts": counts}))
"""
MEDIA_WRITE_SCRIPT = r"""
import os, uuid
from florabase.attachments.storage import AttachmentStorage
from florabase.core.config import get_settings
storage = AttachmentStorage.from_settings(get_settings())
path = storage.temporary / ("acceptance-" + uuid.uuid4().hex)
with path.open("xb") as stream:
    stream.write(b"florabase-acceptance")
    stream.flush()
    os.fsync(stream.fileno())
assert path.read_bytes() == b"florabase-acceptance"
path.unlink()
print("FLORABASE_MEDIA_WRITABLE")
"""


class Refusal(Exception):
    """A precondition failed before anything was changed (exit 2)."""


class Failure(Exception):
    """An operation failed; the journal and printed recovery choice apply (exit 1)."""


def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(value: str) -> datetime.datetime:
    return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=datetime.timezone.utc
    )


def say(message: str) -> None:
    print("florabasectl: " + message, flush=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fsync_directory(path: Path) -> None:
    descriptor = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_atomic(path: Path, data: bytes, mode: int = 0o600) -> None:
    temporary = path.with_name("." + path.name + ".tmp-" + uuid.uuid4().hex[:8])
    descriptor = os.open(str(temporary), os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(str(temporary), mode)
        os.replace(str(temporary), str(path))
    except BaseException:
        if temporary.exists():
            temporary.unlink()
        raise
    fsync_directory(path.parent)


def write_json(path: Path, value: Any, mode: int = 0o600) -> None:
    write_atomic(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode(), mode)


def read_json(path: Path) -> Json:
    try:
        value = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise Refusal(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise Refusal(f"{path} must contain a JSON object")
    return value


def parse_version(text: str) -> tuple[int, ...]:
    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text)
    if not match:
        raise Refusal(f"cannot parse version from {text!r}")
    return tuple(int(part) for part in match.groups(default="0"))


def test_mode() -> bool:
    return os.environ.get("FLORABASECTL_TEST_MODE") == "1"


def fault_point(name: str) -> None:
    """Test-only crash injection; inert unless FLORABASECTL_TEST_MODE=1."""
    if test_mode() and os.environ.get("FLORABASECTL_TEST_FAULT") == name:
        say("TEST FAULT: SIGKILL at " + name)
        os.kill(os.getpid(), signal.SIGKILL)


# --------------------------------------------------------------------------- manifests


def validate_manifest(manifest: Json, *, test_candidate: bool = False) -> None:
    """Stdlib subset of release/manifest.schema.json plus cross-field identity rules."""

    def need(condition: bool, message: str) -> None:
        if not condition:
            raise Refusal("release manifest: " + message)

    need(manifest.get("schema_version") == 1, "schema_version must be 1")
    distribution = "test-candidate" if test_candidate else "registry-candidate"
    need(manifest.get("distribution") == distribution, "distribution must be " + distribution)
    need(
        bool(re.fullmatch(r"0\.1\.0-beta\.[1-9][0-9]*", str(manifest.get("version", "")))),
        "invalid version",
    )
    source = manifest.get("source")
    need(isinstance(source, dict), "source is required")
    assert isinstance(source, dict)
    need(source.get("url") == SOURCE_URL, "unexpected source url")
    need(bool(re.fullmatch(r"[a-f0-9]{40}", str(source.get("revision", "")))), "bad revision")
    need(source.get("dirty") is False, "source must be clean")
    need(manifest.get("platforms") == [PLATFORM], "platforms must be [linux/amd64]")
    need(
        bool(re.fullmatch(r"[A-Za-z0-9_]+", str(manifest.get("alembic_head", "")))),
        "invalid alembic_head",
    )
    loopback = r"(?:127\.0\.0\.1|localhost):[0-9]{2,5}/"
    postgres = manifest.get("postgresql")
    need(isinstance(postgres, dict), "postgresql is required")
    assert isinstance(postgres, dict)
    postgres_pattern = r"docker\.io/library/postgres:[a-zA-Z0-9.-]+@" + DIGEST
    if test_candidate:
        postgres_pattern = (
            "(?:" + postgres_pattern + "|" + loopback + r"postgres:[a-zA-Z0-9.-]+@" + DIGEST + ")"
        )
    need(
        bool(re.fullmatch(postgres_pattern, str(postgres.get("reference", "")))),
        "invalid postgresql reference",
    )
    need(postgres.get("platform") == PLATFORM, "postgresql platform must be linux/amd64")
    need(isinstance(postgres.get("version"), str), "postgresql version required")
    images = manifest.get("images")
    need(isinstance(images, dict) and set(images) == {"backend", "frontend"}, "images pair")
    assert isinstance(images, dict)
    entries = [("postgresql", postgres)] + [
        (name, images[name]) for name in ("backend", "frontend")
    ]
    for name, entry in entries:
        need(isinstance(entry, dict), name + " entry")
        for field in ("index_digest", "platform_digest"):
            need(bool(re.fullmatch(DIGEST, str(entry.get(field, "")))), name + " " + field)
        need(
            str(entry.get("reference", "")).endswith("@" + str(entry.get("index_digest"))),
            name + " reference must pin its index digest",
        )
        need(entry.get("platform") == PLATFORM, name + " platform")
        if name == "postgresql":
            continue
        repository = r"ghcr\.io/alessandrorossato/florabase-" + name
        if test_candidate:
            repository = "(?:" + repository + "|" + loopback + "florabase-" + name + ")"
        need(
            bool(re.fullmatch(repository + "@" + DIGEST, str(entry.get("reference", "")))),
            name + " reference must be an approved digest reference",
        )


def postgres_identity(manifest: Json) -> Json:
    keys = ("repository", "version", "reference", "index_digest", "platform_digest", "platform")
    return {key: manifest["postgresql"].get(key) for key in keys}


def release_record(manifest: Json, manifest_sha256: str) -> Json:
    return {
        "version": manifest["version"],
        "source_revision": manifest["source"]["revision"],
        "alembic_head": manifest["alembic_head"],
        "manifest_sha256": manifest_sha256,
        "images": {
            "backend": manifest["images"]["backend"]["reference"],
            "frontend": manifest["images"]["frontend"]["reference"],
            "postgres": manifest["postgresql"]["reference"],
        },
        "postgres_identity": postgres_identity(manifest),
        "manifest": manifest,
    }


def load_manifest(path: Path, expected_sha256: str, allow_test: bool) -> tuple[Json, str]:
    if allow_test and not test_mode():
        raise Refusal("--allow-test-candidate requires FLORABASECTL_TEST_MODE=1")
    if not re.fullmatch(r"[a-f0-9]{64}", expected_sha256):
        raise Refusal("--manifest-sha256 must be the 64-hex digest from the authorized record")
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise Refusal(f"manifest digest {actual} does not match the authorized digest")
    manifest = read_json(path)
    validate_manifest(manifest, test_candidate=allow_test)
    return manifest, actual


# --------------------------------------------------------------------------- process runner


class Runner:
    """Runs docker/compose with a sanitized environment; .env is the single stack truth."""

    def __init__(self) -> None:
        self.base_env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("COMPOSE_", "FLORABASE_"))
        }
        self.compose = self.detect_compose()

    def detect_compose(self) -> list[str]:
        override = os.environ.get("FLORABASECTL_COMPOSE")
        if override:
            return override.split()
        for candidate in (["docker", "compose"], ["docker-compose"]):
            try:
                subprocess.run(
                    candidate + ["version", "--short"],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env=self.base_env,
                )
                return candidate
            except (OSError, subprocess.CalledProcessError):
                continue
        return ["docker", "compose"]

    def run(
        self,
        argv: Sequence[str],
        *,
        env: dict[str, str] | None = None,
        stdin: IO[bytes] | None = None,
        input_bytes: bytes | None = None,
        stdout: IO[bytes] | None = None,
        timeout: float | None = 900,
        check: bool = True,
    ) -> str:
        environment = dict(self.base_env)
        environment.update(env or {})
        try:
            result = subprocess.run(
                list(argv),
                env=environment,
                # Children never inherit the controller's stdin (it may carry a password).
                stdin=stdin if stdin is not None or input_bytes is not None else subprocess.DEVNULL,
                input=input_bytes,
                stdout=stdout if stdout is not None else subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as error:
            raise Failure("timed out: " + " ".join(argv[:4])) from error
        except OSError as error:
            raise Failure(f"cannot run {argv[0]}: {error}") from error
        if check and result.returncode != 0:
            tail = result.stderr.decode(errors="replace").strip().splitlines()[-15:]
            raise Failure(
                "command failed ({}): {}\n{}".format(
                    result.returncode, " ".join(argv[:6]), "\n".join(tail)
                )
            )
        if stdout is not None or result.stdout is None:
            return ""
        return str(result.stdout.decode(errors="replace").strip())

    def docker_json(self, *args: str) -> Any:
        return json.loads(self.run(["docker"] + list(args)) or "null")


# --------------------------------------------------------------------------- layout and stack


class Layout:
    def __init__(self, root: Path) -> None:
        if not root.is_absolute():
            raise Refusal("--root must be absolute")
        self.root = root
        self.stack = root / "stack"
        self.secrets = root / "secrets"
        self.postgres = root / "postgres"
        self.media = root / "media"
        self.reference = root / "reference"
        self.backups = root / "backups"
        self.state = root / "state"
        self.restore = root / "restore"
        self.preserved = root / "preserved"
        self.installation_file = self.state / "installation.json"
        self.current_file = self.state / "current.json"
        self.operation_file = self.state / "operation.json"
        self.journal_file = self.state / "journal.jsonl"
        self.lock_file = self.state / "controller.lock"
        self.restore_marker = self.state / "restore-pending.json"


class Stack:
    """One Compose project bound to one stack directory and its controller-rendered .env."""

    def __init__(self, runner: Runner, project: str, directory: Path) -> None:
        self.runner = runner
        self.project = project
        self.directory = directory

    def command(self, *args: str, profile: bool = False) -> list[str]:
        command = list(self.runner.compose) + [
            "--project-name",
            self.project,
            "--project-directory",
            str(self.directory),
            "--file",
            str(self.directory / "compose.yaml"),
            "--env-file",
            str(self.directory / ".env"),
        ]
        if profile:
            command += ["--profile", "maintenance"]
        return command + list(args)

    def compose(
        self,
        *args: str,
        image: str | None = None,
        profile: bool = False,
        **kwargs: Any,
    ) -> str:
        env = {"FLORABASE_BACKEND_IMAGE": image} if image else None
        return self.runner.run(self.command(*args, profile=profile), env=env, **kwargs)

    def tool(self, *argv: str, image: str | None = None, **kwargs: Any) -> str:
        return self.compose(
            "run", "--rm", "--no-deps", "-T", "tools", *argv, image=image, profile=True, **kwargs
        )

    def probe(self, image: str | None = None, counts: bool = False) -> Json:
        argv = ["python", "-c", PROBE_SCRIPT] + (["--counts"] if counts else [])
        output = self.tool(*argv, image=image)
        for line in output.splitlines():
            if line.startswith("FLORABASE_PROBE "):
                value = json.loads(line[len("FLORABASE_PROBE ") :])
                assert isinstance(value, dict)
                return value
        raise Failure("database probe produced no result")

    def container(self, service: str) -> Json | None:
        identifiers = self.compose("ps", "-a", "-q", service).split()
        if not identifiers:
            return None
        if len(identifiers) != 1:
            raise Failure(f"expected one {service} container, found {len(identifiers)}")
        value = self.runner.docker_json("inspect", identifiers[0])
        return value[0] if value else None

    def stop_writers(self) -> None:
        self.compose("stop", "frontend", "backend")

    def start(self, timeout: float = 300) -> None:
        """Explicit bounded start order; Compose's own dependency wait has no timeout."""
        self.compose("up", "-d", "db")
        self.wait_healthy(["db"], timeout)
        # A fresh gate run per start: a previous release's success never authorizes this one.
        self.compose("up", "-d", "--force-recreate", "schema-gate")
        self.wait_completed("schema-gate", 180)
        self.compose("up", "-d", "--no-deps", "backend", "frontend")
        self.wait_healthy(SERVICES, timeout)

    def logs(self, service: str) -> str:
        return self.compose("logs", "--no-color", "--tail", "20", service, check=False)

    def wait_completed(self, service: str, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        while True:
            state = (self.container(service) or {}).get("State") or {}
            if state.get("Status") == "exited":
                if state.get("ExitCode") == 0:
                    return
                raise Failure(f"{service} refused to start the release:\n{self.logs(service)}")
            if time.monotonic() > deadline:
                raise Failure(f"{service} did not complete in time")
            time.sleep(1)

    def wait_healthy(self, services: Sequence[str], timeout: float = 300) -> None:
        deadline = time.monotonic() + timeout
        restarts: dict[str, int] = {}
        while True:
            pending = []
            for service in services:
                details = self.container(service) or {}
                state = details.get("State") or {}
                health = (state.get("Health") or {}).get("Status")
                if state.get("Running") and health == "healthy":
                    continue
                count = int(details.get("RestartCount", 0))
                restarts.setdefault(service, count)
                if (state.get("Status") == "exited" and state.get("ExitCode")) or (
                    count - restarts[service] >= 2
                ):
                    raise Failure(f"{service} is crashing:\n{self.logs(service)}")
                pending.append("{}={}".format(service, health or state.get("Status", "missing")))
            if not pending:
                return
            if time.monotonic() > deadline:
                raise Failure("services not healthy in time: " + ", ".join(pending))
            time.sleep(2)

    def volume_devices(self) -> dict[str, str]:
        """Bind device per existing project volume; "" marks a plain (non-bind) volume."""
        names = self.runner.run(
            ["docker", "volume", "ls", "-q", "--filter", "name=^" + self.project + "_"]
        ).split()
        devices: dict[str, str] = {}
        for volume in ("postgres_data", "attachment_data", "reference_data"):
            name = self.project + "_" + volume
            if name not in names:
                continue
            details = self.runner.docker_json("volume", "inspect", name)[0]
            options = details.get("Options") or {}
            bound = options.get("type") == "none" and options.get("o") == "bind"
            devices[volume] = str(options.get("device", "")) if bound else ""
        return devices


def normalize_repository(name: str) -> str:
    """Docker reports Hub images as `postgres`; manifests use docker.io/library/postgres."""
    last = name.rsplit("/", 1)[-1]
    if ":" in last:
        name = name[: len(name) - len(last)] + last.split(":", 1)[0]
    for prefix in ("docker.io/", "index.docker.io/"):
        if name.startswith(prefix):
            name = name[len(prefix) :]
    if name.startswith("library/"):
        name = name[len("library/") :]
    return name


def classify(probe: Json) -> str:
    current = probe["current"]
    if not current:
        return "empty" if not probe["tables"] else "unmanaged"
    if any(revision not in probe["known"] for revision in current):
        return "unknown"
    return "current" if sorted(current) == sorted(probe["heads"]) else "behind"


# --------------------------------------------------------------------------- controller


class Controller:
    def __init__(self, root: Path, runner: Runner | None = None) -> None:
        self.layout = Layout(root)
        self.runner = runner or Runner()
        self.stack = Stack(self.runner, PROJECT, self.layout.stack)
        self._lock: IO[str] | None = None

    # ---- state

    def installation(self) -> Json:
        if not self.layout.installation_file.exists():
            raise Refusal(f"no installation at {self.layout.root}; run init first")
        value = read_json(self.layout.installation_file)
        if value.get("format") != FORMAT:
            raise Refusal("unsupported installation format")
        return value

    def current(self) -> Json | None:
        if not self.layout.current_file.exists():
            return None
        return read_json(self.layout.current_file)

    def require_current(self) -> Json:
        current = self.current()
        if current is None:
            raise Refusal("no release is installed; run install")
        return current

    def operation(self) -> Json | None:
        if not self.layout.operation_file.exists():
            return None
        return read_json(self.layout.operation_file)

    def require_no_pending_restore(self) -> None:
        if self.layout.restore_marker.exists():
            pending = read_json(self.layout.restore_marker)
            raise Refusal(
                "replacement restore of {} was interrupted; re-run restore-replace first".format(
                    pending.get("set_id")
                )
            )

    def journal(self, event: str, **details: Any) -> None:
        record = {"at": utc_now(), "event": event}
        record.update(details)
        line = (json.dumps(record, sort_keys=True) + "\n").encode()
        descriptor = os.open(
            str(self.layout.journal_file), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600
        )
        try:
            os.write(descriptor, line)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def lock(self) -> None:
        """One mutating controller at a time; the kernel releases it if the process dies."""
        self.layout.state.mkdir(mode=0o700, parents=True, exist_ok=True)
        handle = open(str(self.layout.lock_file), "a+")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            handle.close()
            raise Refusal("another florabasectl operation holds the host lock") from error
        handle.seek(0)
        handle.truncate()
        handle.write(f"{os.getpid()} {utc_now()}\n")
        handle.flush()
        self._lock = handle

    # ---- rendering

    def render_env(self, installation: Json, images: Json, layout: Layout) -> bytes:
        limits = installation["limits"]
        lines = [
            "# Rendered by florabasectl from state/installation.json and the deployed release.",
            "# Do not edit: drift is refused. Change configuration with florabasectl.",
            "FLORABASE_RELEASE_VERSION=" + images.get("version", ""),
            "FLORABASE_BACKEND_IMAGE=" + images["backend"],
            "FLORABASE_FRONTEND_IMAGE=" + images["frontend"],
            "FLORABASE_POSTGRES_IMAGE=" + images["postgres"],
            "FLORABASE_SECRETS_DIR=" + str(layout.secrets),
            "FLORABASE_POSTGRES_DIR=" + str(layout.postgres),
            "FLORABASE_MEDIA_DIR=" + str(layout.media),
            "FLORABASE_REFERENCE_DIR=" + str(layout.reference),
            "FLORABASE_CANONICAL_ORIGIN=" + installation["canonical_origin"],
            "FLORABASE_BIND_ADDRESS=" + installation["bind_address"],
            "FLORABASE_HTTP_PORT=" + str(installation["http_port"]),
            "FLORABASE_LOG_LEVEL=INFO",
            "FLORABASE_DB_MEMORY=" + limits["db_memory"],
            "FLORABASE_DB_CPUS=" + limits["db_cpus"],
            "FLORABASE_BACKEND_MEMORY=" + limits["backend_memory"],
            "FLORABASE_BACKEND_CPUS=" + limits["backend_cpus"],
        ]
        return ("\n".join(lines) + "\n").encode()

    @staticmethod
    def render_reference(installation: Json) -> bytes:
        lines = ["# Optional read-only reference datasets, rendered by florabasectl."]
        for kind, setting in sorted(REFERENCE_SETTINGS.items()):
            entry = installation.get("reference", {}).get(kind)
            if entry:
                lines.append("{}={}/{}".format(setting, CONTAINER_REFERENCE, entry["file"]))
        return ("\n".join(lines) + "\n").encode()

    def expected_stack(
        self, installation: Json, images: Json, layout: Layout | None = None
    ) -> dict[str, bytes]:
        return {
            ".env": self.render_env(installation, images, layout or self.layout),
            "reference.env": self.render_reference(installation),
        }

    def write_stack(
        self, installation: Json, images: Json, compose: bytes, layout: Layout | None = None
    ) -> str:
        layout = layout or self.layout
        digest = hashlib.sha256(compose).hexdigest()
        # Content-addressed copy lets abort/apply recover the exact deployed stack document.
        write_atomic(layout.state / ("compose-" + digest + ".yaml"), compose)
        layout.stack.mkdir(mode=0o750, exist_ok=True)
        write_atomic(layout.stack / "compose.yaml", compose, 0o640)
        for name, content in self.expected_stack(installation, images, layout).items():
            write_atomic(layout.stack / name, content, 0o640)
        return digest

    def stored_compose(self, release: Json) -> bytes:
        path = self.layout.state / ("compose-" + release["stack_sha256"] + ".yaml")
        if not path.exists() or sha256_file(path) != release["stack_sha256"]:
            raise Refusal(f"stack document {release['stack_sha256']} is not recorded")
        return bytes(path.read_bytes())

    def check_drift(self, installation: Json, images: Json, stack_sha256: str) -> None:
        """Dockhand/manual edits must never become a second, unrecorded source of truth."""
        problems = []
        compose = self.layout.stack / "compose.yaml"
        if not compose.exists() or sha256_file(compose) != stack_sha256:
            problems.append("compose.yaml")
        for name, content in self.expected_stack(installation, images).items():
            path = self.layout.stack / name
            if not path.exists() or path.read_bytes() != content:
                problems.append(name)
        if problems:
            raise Refusal(
                "stack files differ from the recorded release ({}); restore them with "
                "'florabasectl apply' after reviewing the change".format(", ".join(problems))
            )

    def check_volumes(self, stack: Stack | None = None, layout: Layout | None = None) -> None:
        stack = stack or self.stack
        layout = layout or self.layout
        expected = {
            "postgres_data": str(layout.postgres),
            "attachment_data": str(layout.media),
            "reference_data": str(layout.reference),
        }
        for volume, device in stack.volume_devices().items():
            if device != expected[volume]:
                raise Refusal(
                    f"existing volume {stack.project}_{volume} is not bound to "
                    f"{expected[volume]} (found {device or 'a plain Docker volume'}); "
                    "refusing to adopt it"
                )

    # ---- images

    def ensure_image(self, reference: str) -> Json:
        try:
            details = self.runner.docker_json("image", "inspect", reference)
        except Failure:
            self.runner.run(["docker", "pull", "--platform", PLATFORM, reference], timeout=1800)
            details = self.runner.docker_json("image", "inspect", reference)
        image = details[0]
        assert isinstance(image, dict)
        return image

    def verify_image(self, entry: Json, manifest: Json | None, kind: str) -> Json:
        reference = entry["reference"]
        image = self.ensure_image(reference)
        if "{}/{}".format(image.get("Os"), image.get("Architecture")) != PLATFORM:
            raise Refusal(kind + " image platform is not linux/amd64")
        repository = normalize_repository(reference.split("@", 1)[0])
        if not any(
            normalize_repository(item.split("@", 1)[0]) == repository
            and item.endswith("@" + entry["index_digest"])
            for item in image.get("RepoDigests") or []
        ):
            raise Refusal("{} image does not carry digest {}".format(kind, entry["index_digest"]))
        argv = ["docker", "manifest", "inspect"]
        if test_mode() and re.match(r"(127\.0\.0\.1|localhost):", repository):
            argv.append("--insecure")
        listing = json.loads(self.runner.run(argv + [reference], timeout=300))
        if "manifests" in listing:
            matches = [
                item["digest"]
                for item in listing["manifests"]
                if item.get("platform", {}).get("os") == "linux"
                and item.get("platform", {}).get("architecture") == "amd64"
            ]
            if matches != [entry["platform_digest"]]:
                raise Refusal(kind + " platform manifest digest does not match the release")
        elif entry["platform_digest"] != entry["index_digest"]:
            raise Refusal(kind + " single-platform image must record equal digests")
        if manifest is not None:
            labels = (image.get("Config") or {}).get("Labels") or {}
            for key, expected in (
                ("version", manifest["version"]),
                ("revision", manifest["source"]["revision"]),
                ("source", SOURCE_URL),
            ):
                if labels.get("org.opencontainers.image." + key) != expected:
                    raise Refusal(f"{kind} OCI {key} label does not match the release")
            user = str((image.get("Config") or {}).get("User", "")).split(":")[0]
            if user in {"", "root", "0"} or not (image.get("Config") or {}).get("Healthcheck"):
                raise Refusal(kind + " image must declare a non-root user and healthcheck")
        return image

    def image_heads(self, reference: str) -> list[str]:
        output = self.runner.run(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--read-only",
                "--entrypoint",
                "python",
                reference,
                "-c",
                HEADS_SCRIPT,
            ]
        )
        return output.split()

    def verify_release(self, manifest: Json) -> None:
        say("verifying release images and identities")
        for name in ("backend", "frontend"):
            self.verify_image(manifest["images"][name], manifest, name)
        self.verify_image(manifest["postgresql"], None, "postgresql")
        heads = self.image_heads(manifest["images"]["backend"]["reference"])
        if heads != [manifest["alembic_head"]]:
            raise Refusal(f"backend image Alembic heads {heads} differ from manifest")

    # ---- commands: host

    def preflight(self, evidence: Path | None) -> int:
        runner = self.runner
        checks: list[tuple[str, bool, str]] = []
        uname = os.uname()
        checks.append(("linux", uname.sysname == "Linux", uname.sysname))
        checks.append(("amd64", uname.machine in {"x86_64", "amd64"}, uname.machine))
        checks.append(("python>=3.8", sys.version_info >= (3, 8), sys.version.split()[0]))
        server = runner.run(["docker", "version", "--format", "{{.Server.Version}}"])
        checks.append(("engine>=24.0", parse_version(server)[:2] >= MIN_ENGINE, server))
        compose = runner.run(list(runner.compose) + ["version", "--short"])
        checks.append(("compose>=2.20", parse_version(compose)[:2] >= MIN_COMPOSE, compose))
        info = runner.docker_json("info", "--format", "{{json .}}")
        checks.append(
            ("memory-cgroup", bool(info.get("MemoryLimit")), str(info.get("MemoryLimit")))
        )
        checks.append(("pids-limit", bool(info.get("PidsLimit")), str(info.get("PidsLimit"))))
        root = self.layout.root if self.layout.root.exists() else self.layout.root.parent
        usage = shutil.disk_usage(str(root))
        meminfo = {}
        with open("/proc/meminfo") as stream:
            for line in stream:
                key, _, value = line.partition(":")
                meminfo[key] = int(value.split()[0]) * 1024
        with open("/proc/uptime") as stream:
            uptime = float(stream.read().split()[0])
        mounts = []
        with open("/proc/mounts") as stream:
            for line in stream:
                parts = line.split()
                if str(root).startswith(parts[1]):
                    mounts.append((len(parts[1]), parts[1], parts[2]))
        filesystem = max(mounts)[2] if mounts else "unknown"
        checks.append(("disk>=20GiB", usage.free >= 20 * 1024**3, str(usage.free)))
        available = meminfo.get("MemAvailable", 0)
        checks.append(("memavailable>=2GiB", available >= 2 * 1024**3, str(available)))
        checks.append(("local-filesystem", filesystem in {"ext4", "btrfs", "xfs"}, filesystem))
        report = {
            "at": utc_now(),
            "host": {"kernel": uname.release, "machine": uname.machine, "uptime_seconds": uptime},
            "python": sys.version.split()[0],
            "engine": server,
            "compose": compose,
            "compose_command": runner.compose,
            "docker_info": {
                key: info.get(key)
                for key in (
                    "OperatingSystem",
                    "KernelVersion",
                    "NCPU",
                    "MemTotal",
                    "Driver",
                    "CgroupVersion",
                    "MemoryLimit",
                    "SwapLimit",
                    "CpuCfsQuota",
                    "CpuCfsPeriod",
                    "PidsLimit",
                    "InitBinary",
                    "Warnings",
                )
            },
            "memory": {"total": meminfo.get("MemTotal"), "available": available},
            "disk": {"path": str(root), "free": usage.free, "total": usage.total},
            "filesystem": filesystem,
            "checks": [{"name": n, "ok": ok, "observed": o} for n, ok, o in checks],
        }
        if evidence:
            write_json(evidence, report, 0o644)
        for name, ok, observed in checks:
            say("{:<20} {:<4} {}".format(name, "ok" if ok else "FAIL", observed))
        if not info.get("CpuCfsQuota"):
            say("CPU CFS quota unsupported: keep FLORABASE_*_CPUS at 0 (unlimited)")
        failed = [name for name, ok, _ in checks if not ok]
        if failed:
            say("PREFLIGHT_FAILED " + ",".join(failed))
            return 1
        say(
            "PREFLIGHT_PASSED (host evidence only; capacity acceptance remains an operator decision)"
        )
        return 0

    def init(self, args: argparse.Namespace) -> None:
        layout = self.layout
        if os.geteuid() != 0:
            raise Refusal("init must run as root to assign PostgreSQL/media ownership")
        origin = args.origin.rstrip("/")
        if not re.fullmatch(r"https://[a-z0-9.-]+(?::[0-9]{1,5})?", origin):
            raise Refusal("--origin must be the exact https://host canonical origin")
        if layout.root.exists() and any(layout.root.iterdir()):
            raise Refusal(f"{layout.root} exists and is not empty; refusing adoption")
        if args.http_port < 1024 or args.http_port > 65535:
            raise Refusal("--http-port must be 1024-65535")
        layout.root.mkdir(mode=0o750, parents=True, exist_ok=True)
        for path, owner, mode in (
            (layout.state, 0, 0o700),
            (layout.secrets, 0, 0o700),
            (layout.backups, 0, 0o700),
            (layout.stack, 0, 0o750),
            (layout.reference, 0, 0o755),
            (layout.postgres, POSTGRES_UID, 0o700),
            (layout.media, BACKEND_UID, 0o700),
        ):
            path.mkdir(mode=mode)
            os.chown(str(path), owner, owner)
            os.chmod(str(path), mode)
        self.write_secrets(layout)
        installation = {
            "format": FORMAT,
            "installation_id": uuid.uuid4().hex,
            "created_at": utc_now(),
            "root": str(layout.root),
            "project": PROJECT,
            "canonical_origin": origin,
            "bind_address": args.bind_address,
            "http_port": args.http_port,
            "database": {"name": "florabase", "user": "florabase"},
            "limits": {
                "db_memory": args.db_memory,
                "db_cpus": args.db_cpus,
                "backend_memory": args.backend_memory,
                "backend_cpus": args.backend_cpus,
            },
            "reference": {},
        }
        write_json(layout.installation_file, installation)
        self.journal("init", installation_id=installation["installation_id"])
        say("initialized installation {}".format(installation["installation_id"]))

    @staticmethod
    def write_secrets(layout: Layout) -> None:
        password = secrets.token_hex(32)
        write_atomic(
            layout.secrets / "db.env",
            f"POSTGRES_DB=florabase\nPOSTGRES_USER=florabase\nPOSTGRES_PASSWORD={password}\n".encode(),
        )
        write_atomic(
            layout.secrets / "backend.env",
            f"FLORABASE_DATABASE_URL=postgresql+psycopg://florabase:{password}@db:5432/florabase\n".encode(),
        )

    # ---- commands: install and acceptance

    def install(self, args: argparse.Namespace) -> None:
        self.lock()
        installation = self.installation()
        if self.current() is not None or self.operation() is not None:
            raise Refusal("a release is already installed; use promote")
        manifest, digest = load_manifest(
            args.manifest, args.manifest_sha256, args.allow_test_candidate
        )
        self.check_volumes()
        self.verify_release(manifest)
        record = release_record(manifest, digest)
        images = dict(record["images"], version=record["version"])
        compose = (BUNDLE / "compose.yaml").read_bytes()
        # An interrupted install of the same manifest may continue from its own migration.
        pending = self.layout.state / "install-pending.json"
        resumable = pending.exists() and read_json(pending).get("manifest_sha256") == digest
        write_json(pending, {"manifest_sha256": digest, "at": utc_now()})
        stack_sha256 = self.write_stack(installation, images, compose)
        self.journal("install-start", release=record["version"], manifest_sha256=digest)
        self.stack.compose("up", "-d", "db")
        self.stack.wait_healthy(["db"])
        probe = self.stack.probe()
        state = classify(probe)
        if state == "empty" or (resumable and state == "behind"):
            say("migrating database to " + manifest["alembic_head"])
            self.stack.compose("run", "--rm", "-T", "migrate", profile=True, timeout=1800)
        elif not (resumable and state == "current"):
            raise Failure(f"database is {state} (not empty); install refuses adoption")
        probe = self.stack.probe()
        if classify(probe) != "current" or probe["current"] != [manifest["alembic_head"]]:
            raise Failure("database revision after migration is {}".format(probe["current"]))
        self.stack.start()
        current = dict(
            record, stack_sha256=stack_sha256, deployed_at=utc_now(), operation="install"
        )
        self.acceptance_checks(installation, current)
        write_json(self.layout.current_file, current)
        pending.unlink()
        self.journal("install-complete", release=record["version"])
        say("INSTALL_COMPLETE {} (bootstrap the owner next)".format(record["version"]))

    def bootstrap_owner(self, login: str, display_name: str | None) -> None:
        self.lock()
        self.require_current()
        password = read_password()
        argv = ["python", "-m", "florabase.auth.bootstrap", login, "--password-stdin"]
        if display_name:
            argv += ["--display-name", display_name]
        output = self.stack.tool(*argv, input_bytes=(password + "\n").encode())
        self.journal("bootstrap-owner", login=login)
        say(output or "owner created")

    def acceptance_checks(
        self,
        installation: Json,
        current: Json,
        *,
        stack: Stack | None = None,
        layout: Layout | None = None,
        http_port: int | None = None,
        owner: tuple[str, str] | None = None,
        base_url: str | None = None,
    ) -> None:
        stack = stack or self.stack
        layout = layout or self.layout
        for path, uid in ((layout.postgres, POSTGRES_UID), (layout.media, BACKEND_UID)):
            info = path.stat()
            if (info.st_uid, info.st_gid, info.st_mode & 0o7777) != (uid, uid, 0o700):
                raise Failure(f"{path} must be owned by {uid}:{uid} with mode 0700")
        images = current["images"]
        expected = {
            "db": images["postgres"],
            "backend": images["backend"],
            "frontend": images["frontend"],
        }
        for service in SERVICES:
            details = stack.container(service)
            if details is None:
                raise Failure(service + " container is missing")
            state = details["State"]
            if not state.get("Running") or (state.get("Health") or {}).get("Status") != "healthy":
                raise Failure(service + " is not running healthy")
            pinned = self.runner.docker_json("image", "inspect", expected[service])[0]["Id"]
            if details["Image"] != pinned:
                raise Failure(service + " does not run the pinned image")
            if (details["Config"].get("Labels") or {}).get("dockhand.update") != "false":
                raise Failure(service + " lacks dockhand.update=false")
            if any(mount.get("Type") == "bind" for mount in details.get("Mounts", [])):
                raise Failure(service + " has a host bind mount")
            published = {
                port: bindings
                for port, bindings in (details["NetworkSettings"].get("Ports") or {}).items()
                if bindings
            }
            if service != "frontend" and published:
                raise Failure(service + " publishes a host port")
            if service == "frontend":
                hosts = {b["HostIp"] for bindings in published.values() for b in bindings}
                if hosts != {installation["bind_address"]}:
                    raise Failure("frontend must publish only on " + installation["bind_address"])
        probe = stack.probe()
        if classify(probe) != "current" or probe["current"] != [current["alembic_head"]]:
            raise Failure("database revision {} is not release head".format(probe["current"]))
        stack.tool("python", "scripts/attachment_artifacts.py", "verify")
        if "FLORABASE_MEDIA_WRITABLE" not in stack.tool("python", "-c", MEDIA_WRITE_SCRIPT):
            raise Failure("media storage write/read check failed")
        port = http_port or installation["http_port"]
        address = installation["bind_address"]
        host = "127.0.0.1" if address in {"0.0.0.0", "127.0.0.1"} else address
        local = f"http://{host}:{port}"
        http_acceptance(local, current)
        if base_url:
            http_acceptance(base_url.rstrip("/"), current)
        if owner:
            owner_acceptance(base_url or local, installation["canonical_origin"], *owner)
        say(
            "ACCEPTANCE_PASSED release={} revision={}".format(
                current["version"], probe["current"][0]
            )
        )

    def acceptance(self, args: argparse.Namespace) -> None:
        owner = (args.owner, read_password()) if args.owner else None
        installation = self.installation()
        current = self.require_current()
        # After a reboot or redeploy, give the bounded health checks time before judging.
        self.stack.wait_healthy(SERVICES, timeout=240)
        self.acceptance_checks(installation, current, owner=owner, base_url=args.base_url)

    # ---- backups

    def database_release(self, candidates: Sequence[Json]) -> Json:
        """The release whose backend image is exactly at the database's Alembic head."""
        for release in candidates:
            try:
                if classify(self.stack.probe(image=release["images"]["backend"])) == "current":
                    return release
            except Failure:
                continue
        raise Failure("no recorded release matches the database revision; use restore-replace")

    def backup(self, kind: str, *, writers_held: bool, release: Json | None = None) -> str:
        """Paired DB+media recovery set; writers stay stopped unless the caller restarts them."""
        installation = self.installation()
        current = release or self.require_current()
        image = current["images"]["backend"]
        layout = self.layout
        stack = self.stack
        running = {
            service: bool(((stack.container(service) or {}).get("State") or {}).get("Running"))
            for service in ("backend", "frontend")
        }
        set_id = "{}-{}-{}".format(
            datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            kind,
            uuid.uuid4().hex[:6],
        )
        partial = layout.backups / (".partial-" + set_id)
        partial.mkdir(mode=0o700)
        try:
            stack.stop_writers()
            say(f"backup {set_id}: writers stopped; verifying media")
            stack.tool("python", "scripts/attachment_artifacts.py", "verify", image=image)
            with (partial / "database.dump").open("wb") as output:
                stack.compose(
                    "exec",
                    "-T",
                    "db",
                    "sh",
                    "-c",
                    'pg_dump --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" '
                    "--format=custom --no-owner --no-privileges",
                    stdout=output,
                    timeout=7200,
                )
            with (partial / "attachments.tar").open("wb") as output:
                stack.tool(
                    "python",
                    "scripts/attachment_artifacts.py",
                    "archive",
                    image=image,
                    stdout=output,
                )
            probe = stack.probe(image=image, counts=True)
            if classify(probe) != "current" or probe["current"] != [current["alembic_head"]]:
                raise Failure("database is not at the recorded release head; cannot record set")
            shutil.copyfile(str(layout.stack / "compose.yaml"), str(partial / "compose.yaml"))
            metadata = {
                "format": FORMAT,
                "set_id": set_id,
                "kind": kind,
                "created_at": utc_now(),
                "installation_id": installation["installation_id"],
                "release": {
                    key: current[key]
                    for key in ("version", "source_revision", "manifest_sha256", "alembic_head")
                },
                "images": current["images"],
                "tool_image": image,
                "postgres_identity": current["postgres_identity"],
                "alembic_revision": probe["current"],
                "table_counts": probe["counts"],
                "configuration": {
                    "canonical_origin": installation["canonical_origin"],
                    "http_port": installation["http_port"],
                    "bind_address": installation["bind_address"],
                    "database": installation["database"],
                    "reference": installation.get("reference", {}),
                    "stack_sha256": sha256_file(partial / "compose.yaml"),
                },
                "volumes": stack.volume_devices(),
                "artifacts": {},
            }
            self.validate_artifacts(partial, metadata["tool_image"], current["images"]["postgres"])
            for name in ("database.dump", "attachments.tar", "compose.yaml"):
                metadata["artifacts"][name] = {
                    "sha256": sha256_file(partial / name),
                    "bytes": (partial / name).stat().st_size,
                }
            write_json(partial / "metadata.json", metadata)
            sums = "".join(
                f"{sha256_file(partial / name)}  {name}\n"
                for name in ("attachments.tar", "compose.yaml", "database.dump", "metadata.json")
            )
            write_atomic(partial / "SHA256SUMS", sums.encode())
            for path in partial.iterdir():
                with path.open("rb") as stream:
                    os.fsync(stream.fileno())
            os.rename(str(partial), str(layout.backups / set_id))
            fsync_directory(layout.backups)
        except BaseException:
            shutil.rmtree(str(partial), ignore_errors=True)
            if not writers_held and any(running.values()):
                stack.start()
            raise
        if not writers_held and any(running.values()):
            stack.start()
        self.journal("backup", set_id=set_id, kind=kind)
        say(f"BACKUP_COMPLETE {set_id}")
        return set_id

    def validate_artifacts(self, directory: Path, backend_image: str, postgres_image: str) -> None:
        with (directory / "database.dump").open("rb") as stream:
            listing = self.runner.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-i",
                    "--network",
                    "none",
                    "--entrypoint",
                    "pg_restore",
                    postgres_image,
                    "--list",
                ],
                stdin=stream,
            )
        if "TABLE DATA" not in listing:
            raise Failure("database dump has no table data")
        with (directory / "attachments.tar").open("rb") as stream:
            self.runner.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-i",
                    "--network",
                    "none",
                    "--read-only",
                    "--entrypoint",
                    "python",
                    backend_image,
                    "scripts/attachment_artifacts.py",
                    "validate-archive",
                ],
                stdin=stream,
            )

    def recovery_set(self, set_id: str) -> tuple[Path, Json]:
        if not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z-[a-z-]+-[a-f0-9]{6}", set_id):
            raise Refusal("invalid recovery set id")
        directory = self.layout.backups / set_id
        if not directory.is_dir():
            raise Refusal(f"recovery set {set_id} does not exist")
        return directory, verify_checksums(directory)

    def verify_backup(self, set_id: str) -> Json:
        directory, metadata = self.recovery_set(set_id)
        self.ensure_image(metadata["tool_image"])
        self.ensure_image(metadata["images"]["postgres"])
        self.validate_artifacts(directory, metadata["tool_image"], metadata["images"]["postgres"])
        say(f"RECOVERY_SET_VERIFIED {set_id}")
        return metadata

    def sets(self) -> list[Json]:
        result: list[Json] = []
        if not self.layout.backups.exists():
            return result
        for path in sorted(self.layout.backups.iterdir()):
            if (
                path.is_dir()
                and not path.name.startswith(".")
                and (path / "metadata.json").exists()
            ):
                result.append(read_json(path / "metadata.json"))
        return result

    def retention(self, daily: int, weekly: int, upgrades: int, apply: bool) -> list[str]:
        self.lock()
        keep, remove = select_retained(self.sets(), daily, weekly, upgrades)
        for set_id in remove:
            say(("removing " if apply else "would remove ") + set_id)
            if apply:
                shutil.rmtree(str(self.layout.backups / set_id))
                self.journal("retention-remove", set_id=set_id)
        say("retaining {} set(s){}".format(len(keep), "" if apply else " (dry run; pass --apply)"))
        return remove

    # ---- off-host export (restic, encrypted)

    def restic(self, args: argparse.Namespace, *argv: str, mounts: Sequence[str] = ()) -> str:
        password = Path(args.password_file).resolve()
        if password.stat().st_mode & 0o077:
            raise Refusal("restic password file must not be group/world accessible")
        command = [
            "docker",
            "run",
            "--rm",
            "--network",
            args.network,
            "-e",
            "RESTIC_REPOSITORY=" + args.repository,
            "-e",
            "RESTIC_PASSWORD_FILE=/run/florabase/restic-password",
            "-v",
            f"{password}:/run/florabase/restic-password:ro",
        ]
        if args.repository.startswith("/"):
            command += ["-v", f"{args.repository}:{args.repository}"]
        if args.restic_env_file:
            command += ["--env-file", str(Path(args.restic_env_file).resolve())]
        for mount in mounts:
            command += ["-v", mount]
        command += [args.restic_image, "--no-cache"] + list(argv)
        return self.runner.run(command, timeout=None)

    def export(self, args: argparse.Namespace) -> None:
        self.lock()
        directory, metadata = self.recovery_set(args.set_id)
        if args.init:
            self.restic(args, "init")
        snapshot_root = "/florabase-set/" + args.set_id
        self.restic(
            args,
            "backup",
            "--host",
            "florabase",
            "--tag",
            "florabase",
            "--tag",
            "set:" + args.set_id,
            snapshot_root,
            mounts=[f"{directory}:{snapshot_root}:ro"],
        )
        self.restic(args, "check")
        verify_dir = self.layout.state / ("export-verify-" + uuid.uuid4().hex[:8])
        verify_dir.mkdir(mode=0o700)
        try:
            self.restic(
                args,
                "restore",
                "latest",
                "--tag",
                "set:" + args.set_id,
                "--target",
                "/verify",
                mounts=[f"{verify_dir}:/verify"],
            )
            restored = verify_dir / "florabase-set" / args.set_id
            verify_checksums(restored)
        finally:
            shutil.rmtree(str(verify_dir), ignore_errors=True)
        self.journal("export", set_id=args.set_id, repository=redact(args.repository))
        say("EXPORT_VERIFIED {} -> {}".format(metadata["set_id"], redact(args.repository)))

    def import_set(self, args: argparse.Namespace) -> None:
        self.lock()
        self.installation()
        target = self.layout.backups / args.set_id
        if target.exists():
            raise Refusal("recovery set already present locally")
        staging = self.layout.backups / (".import-" + uuid.uuid4().hex[:8])
        staging.mkdir(mode=0o700)
        try:
            self.restic(
                args,
                "restore",
                "latest",
                "--tag",
                "set:" + args.set_id,
                "--target",
                "/import",
                mounts=[f"{staging}:/import"],
            )
            restored = staging / "florabase-set" / args.set_id
            verify_checksums(restored)
            os.rename(str(restored), str(target))
            fsync_directory(self.layout.backups)
        finally:
            shutil.rmtree(str(staging), ignore_errors=True)
        self.journal("import-set", set_id=args.set_id)
        say(f"IMPORTED {args.set_id}")

    # ---- restore

    def restore_into(
        self, stack: Stack, layout: Layout, directory: Path, metadata: Json, installation: Json
    ) -> None:
        """Fresh DB/media dirs + exact set images; the caller owns quiescence and switching."""
        current = metadata_release(metadata)
        compose = (directory / "compose.yaml").read_bytes()
        images = dict(current["images"], version=current["version"])
        self.write_stack(installation, images, compose, layout)
        stack.compose("up", "-d", "db")
        stack.wait_healthy(["db"])
        with (directory / "database.dump").open("rb") as stream:
            stack.compose(
                "exec",
                "-T",
                "db",
                "sh",
                "-c",
                'pg_restore --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" '
                "--no-owner --no-privileges --exit-on-error",
                stdin=stream,
                timeout=7200,
            )
        with (directory / "attachments.tar").open("rb") as stream:
            stack.tool("python", "scripts/attachment_artifacts.py", "restore", stdin=stream)
        stack.tool("python", "scripts/attachment_artifacts.py", "verify")
        probe = stack.probe(counts=True)
        if probe["current"] != metadata["alembic_revision"]:
            raise Failure("restored revision {} differs from set".format(probe["current"]))
        if probe["counts"] != metadata["table_counts"]:
            differing = sorted(
                table
                for table in set(probe["counts"]) | set(metadata["table_counts"])
                if probe["counts"].get(table) != metadata["table_counts"].get(table)
            )
            raise Failure("restored table counts differ: " + ", ".join(differing))
        # Restored authentication state must not admit old sessions; owner logs in again.
        stack.compose(
            "exec",
            "-T",
            "db",
            "sh",
            "-c",
            'psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -v ON_ERROR_STOP=1 '
            '-c "DELETE FROM auth_sessions"',
        )
        stack.start()

    def restore_isolated(self, args: argparse.Namespace) -> None:
        owner = (args.owner, read_password()) if args.owner else None
        self.lock()
        installation = self.installation()
        directory, metadata = self.recovery_set(args.set_id)
        if args.http_port == installation["http_port"]:
            raise Refusal("isolated restore needs a private port different from the live stack")
        for image in metadata["images"].values():
            self.ensure_image(image)
        project = "florabase-restore-" + uuid.uuid4().hex[:8]
        base = self.layout.restore / project
        drill = Layout(base)
        self.layout.restore.mkdir(mode=0o700, exist_ok=True)
        base.mkdir(mode=0o700)
        for path, uid in (
            (drill.state, 0),
            (drill.secrets, 0),
            (drill.stack, 0),
            (drill.reference, 0),
            (drill.postgres, POSTGRES_UID),
            (drill.media, BACKEND_UID),
        ):
            path.mkdir(mode=0o700)
            os.chown(str(path), uid, uid)
        os.chmod(str(drill.reference), 0o755)
        write_json(
            base / "restore.json", {"project": project, "set_id": args.set_id, "at": utc_now()}
        )
        self.write_secrets(drill)
        drill_installation = dict(
            installation,
            http_port=args.http_port,
            bind_address="127.0.0.1",
            reference={},
        )
        stack = Stack(self.runner, project, drill.stack)
        self.journal("restore-isolated-start", project=project, set_id=args.set_id)
        self.restore_into(stack, drill, directory, metadata, drill_installation)
        self.acceptance_checks(
            drill_installation,
            metadata_release(metadata),
            stack=stack,
            layout=drill,
            http_port=args.http_port,
            owner=owner,
        )
        self.journal("restore-isolated-complete", project=project, set_id=args.set_id)
        say(f"ISOLATED_RESTORE_PASSED project={project} url=http://127.0.0.1:{args.http_port}")
        say(f"remove with: restore-remove --project {project} --confirm {project}")

    def restore_remove(self, project: str, confirm: str) -> None:
        self.lock()
        if project != confirm or not re.fullmatch(r"florabase-restore-[a-f0-9]{8}", project):
            raise Refusal("--confirm must repeat the exact florabase-restore-* project")
        base = self.layout.restore / project
        marker = base / "restore.json"
        if not marker.exists() or read_json(marker).get("project") != project:
            raise Refusal(f"no isolated restore drill named {project}")
        stack = Stack(self.runner, project, base / "stack")
        stack.compose("down", "--remove-orphans")
        for volume in ("postgres_data", "attachment_data", "reference_data"):
            name = project + "_" + volume
            if self.runner.run(["docker", "volume", "ls", "-q", "--filter", "name=^" + name + "$"]):
                self.runner.run(["docker", "volume", "rm", name])
        shutil.rmtree(str(base))
        self.journal("restore-remove", project=project)
        say("removed isolated restore drill " + project)

    def restore_replace(self, args: argparse.Namespace) -> None:
        self.lock()
        installation = self.installation()
        current = self.require_current()
        if args.confirm_installation != installation["installation_id"]:
            raise Refusal("--confirm-installation must equal " + installation["installation_id"])
        if args.confirm_database != installation["database"]["name"]:
            raise Refusal("--confirm-database must equal " + installation["database"]["name"])
        directory, metadata = self.recovery_set(args.set_id)
        if metadata["postgres_identity"] != current["postgres_identity"]:
            raise Refusal("set uses a different PostgreSQL image; that is database maintenance")
        for image in metadata["images"].values():
            self.ensure_image(image)
        self.check_volumes()
        operation = self.operation()
        candidates = [current] + (
            [operation["pinned_before"], operation["target"]] if operation else []
        )
        self.journal("restore-replace-start", set_id=args.set_id)
        try:
            self.backup("safety", writers_held=True, release=self.database_release(candidates))
        except (Failure, Refusal) as error:
            say(f"safety logical backup unavailable ({error}); raw data is preserved instead")
        write_json(self.layout.restore_marker, {"set_id": args.set_id, "at": utc_now()})
        self.stack.compose("stop")
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        preserved = self.layout.preserved / stamp
        self.layout.preserved.mkdir(mode=0o700, exist_ok=True)
        preserved.mkdir(mode=0o700)
        for path, uid in ((self.layout.postgres, POSTGRES_UID), (self.layout.media, BACKEND_UID)):
            os.rename(str(path), str(preserved / path.name))
            path.mkdir(mode=0o700)
            os.chown(str(path), uid, uid)
        fsync_directory(self.layout.root)
        self.journal("restore-replace-preserved", path=str(preserved))
        self.restore_into(self.stack, self.layout, directory, metadata, installation)
        restored = dict(
            metadata_release(metadata),
            stack_sha256=metadata["configuration"]["stack_sha256"],
            deployed_at=utc_now(),
            operation="restore:" + args.set_id,
        )
        self.acceptance_checks(installation, restored)
        write_json(self.layout.current_file, restored)
        if operation is not None:
            operation.update(status="superseded", superseded_by="restore:" + args.set_id)
            self.archive_operation(operation)
        self.layout.restore_marker.unlink()
        self.journal("restore-replace-complete", set_id=args.set_id, preserved=str(preserved))
        say(f"RESTORE_REPLACE_COMPLETE {args.set_id} (previous data kept in {preserved})")

    # ---- promotion

    def promote(self, args: argparse.Namespace) -> None:
        self.lock()
        self.require_no_pending_restore()
        installation = self.installation()
        current = self.require_current()
        operation = self.operation()
        if operation is not None:
            if operation["status"] == "in_progress":
                raise Refusal(
                    "operation {} is in progress; use resume or abort".format(operation["id"])
                )
            if not args.after_failed:
                raise Refusal(
                    "operation {} failed; choose abort, restore-replace, or a forward fix "
                    "with promote --after-failed".format(operation["id"])
                )
        elif args.after_failed:
            raise Refusal("--after-failed needs a failed operation")
        manifest, digest = load_manifest(
            args.manifest, args.manifest_sha256, args.allow_test_candidate
        )
        target = release_record(manifest, digest)
        if target["postgres_identity"] != current["postgres_identity"]:
            raise Refusal(
                "release changes the PostgreSQL image; application promotion never does that "
                "(separate database maintenance required)"
            )
        pinned = (
            operation["target"]
            if operation and operation["phase_index"] >= PHASES.index("pinned")
            else current
        )
        self.check_drift(
            installation, dict(pinned["images"], version=pinned["version"]), pinned["stack_sha256"]
        )
        if target["images"] == pinned["images"]:
            raise Refusal("target image pair is already deployed")
        self.check_volumes()
        self.verify_release(manifest)
        probe = self.stack.probe(image=target["images"]["backend"])
        state = classify(probe)
        if state in {"unknown", "empty", "unmanaged"}:
            raise Refusal(
                "database revision {} is {} for the target release; no downgrade or adoption".format(
                    probe["current"], state
                )
            )
        if state == "behind" and not args.confirm_migration:
            raise Refusal(
                "target release migrates {} -> {}; review it and pass --confirm-migration".format(
                    probe["current"], probe["heads"]
                )
            )
        compose = (BUNDLE / "compose.yaml").read_bytes()
        target["stack_sha256"] = hashlib.sha256(compose).hexdigest()
        new = {
            "id": datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            + "-"
            + uuid.uuid4().hex[:6],
            "kind": "promote",
            "status": "in_progress",
            "phase": PHASES[0],
            "phase_index": 0,
            "created_at": utc_now(),
            "previous": current,
            "pinned_before": pinned,
            "target": target,
            "compose": compose.decode(),
            "migration": state == "behind",
        }
        if operation is not None:
            operation.update(status="superseded", superseded_by=new["id"])
            self.archive_operation(operation)
        write_json(self.layout.operation_file, new)
        self.journal(
            "promote-start",
            operation=new["id"],
            target=target["version"],
            backend=target["images"]["backend"],
            migration=new["migration"],
        )
        fault_point("validated")
        self.advance(installation, new)

    def set_phase(self, operation: Json, phase: str, **details: Any) -> None:
        operation.update(details, phase=phase, phase_index=PHASES.index(phase))
        write_json(self.layout.operation_file, operation)
        self.journal("phase", operation=operation["id"], phase=phase, **details)
        fault_point(phase)

    def advance(self, installation: Json, operation: Json) -> None:
        target = operation["target"]
        stack = self.stack
        try:
            if operation["phase"] == "validated":
                stack.stop_writers()
                self.set_phase(operation, "quiesced")
            if operation["phase"] == "quiesced":
                stack.stop_writers()
                release = self.database_release([operation["pinned_before"], operation["previous"]])
                set_id = self.backup("pre-upgrade", writers_held=True, release=release)
                self.set_phase(operation, "backed_up", backup=set_id)
            if operation["phase"] == "backed_up":
                stack.stop_writers()
                probe = stack.probe(image=target["images"]["backend"])
                state = classify(probe)
                if state == "behind":
                    if not operation["migration"]:
                        raise Failure("database requires an unconfirmed migration")
                    say("migrating {} -> {}".format(probe["current"], probe["heads"]))
                    stack.compose(
                        "run",
                        "--rm",
                        "-T",
                        "migrate",
                        image=target["images"]["backend"],
                        profile=True,
                        timeout=3600,
                    )
                    probe = stack.probe(image=target["images"]["backend"])
                if classify(probe) != "current" or probe["current"] != [target["alembic_head"]]:
                    raise Failure(
                        "database revision {} is not target head".format(probe["current"])
                    )
                self.set_phase(operation, "migrated", revision=probe["current"])
            if operation["phase"] == "migrated":
                self.write_stack(
                    installation,
                    dict(target["images"], version=target["version"]),
                    operation["compose"].encode(),
                )
                self.set_phase(operation, "pinned")
            if operation["phase"] == "pinned":
                stack.start()
                self.set_phase(operation, "started")
            if operation["phase"] == "started":
                self.acceptance_checks(installation, target)
                self.set_phase(operation, "accepted")
            deployed = dict(target, deployed_at=utc_now(), operation=operation["id"])
            write_json(self.layout.current_file, deployed)
            operation["status"] = "completed"
            self.archive_operation(operation)
            self.journal("promote-complete", operation=operation["id"], release=target["version"])
            say("PROMOTE_COMPLETE {} {}".format(target["version"], target["images"]["backend"]))
        except (Failure, Refusal, OSError, KeyError, ValueError) as error:
            operation.update(status="failed", error=str(error), failed_at=utc_now())
            write_json(self.layout.operation_file, operation)
            self.journal(
                "promote-failed",
                operation=operation["id"],
                phase=operation["phase"],
                error=str(error),
            )
            try:
                stack.stop_writers()
            except Failure as stop_error:
                say(f"WARNING: could not stop writers: {stop_error}")
            raise Failure(
                "promotion {} failed after phase {}: {}\nWriters are stopped. Recovery choices: "
                "'abort' (only if the database revision is unchanged), 'promote --after-failed' "
                "with a tested forward fix, or 'restore-replace {}' (writers have been stopped "
                "since that pre-upgrade set).".format(
                    operation["id"], operation["phase"], error, operation.get("backup", "<set>")
                )
            ) from error

    def resume(self) -> None:
        self.lock()
        self.require_no_pending_restore()
        installation = self.installation()
        operation = self.operation()
        if operation is None or operation["status"] != "in_progress":
            raise Refusal("no interrupted operation to resume")
        self.journal("resume", operation=operation["id"], phase=operation["phase"])
        say("resuming {} after phase {}".format(operation["id"], operation["phase"]))
        self.advance(installation, operation)

    def abort(self) -> None:
        self.lock()
        self.require_no_pending_restore()
        installation = self.installation()
        operation = self.operation()
        if operation is None or operation["status"] not in {"in_progress", "failed"}:
            raise Refusal("no interrupted or failed operation to abort")
        previous = operation["previous"]
        probe = self.stack.probe(image=previous["images"]["backend"])
        if classify(probe) != "current" or probe["current"] != [previous["alembic_head"]]:
            raise Refusal(
                "database revision {} changed; abort cannot downgrade. Use promote --after-failed "
                "(forward fix) or restore-replace {}".format(
                    probe["current"], operation.get("backup", "<pre-upgrade set>")
                )
            )
        images = dict(previous["images"], version=previous["version"])
        self.write_stack(installation, images, self.stored_compose(previous))
        self.stack.start()
        self.acceptance_checks(installation, previous)
        operation.update(status="aborted", aborted_at=utc_now())
        self.archive_operation(operation)
        write_json(self.layout.current_file, dict(previous, deployed_at=utc_now()))
        self.journal("abort", operation=operation["id"])
        say("ABORTED {}; previous release {} serving".format(operation["id"], previous["version"]))

    def archive_operation(self, operation: Json) -> None:
        archive = self.layout.state / "operations"
        archive.mkdir(mode=0o700, exist_ok=True)
        write_json(archive / (operation["id"] + ".json"), operation)
        if self.layout.operation_file.exists():
            self.layout.operation_file.unlink()
            fsync_directory(self.layout.state)

    # ---- configuration, status and notifications

    def reference(self, args: argparse.Namespace) -> None:
        self.lock()
        installation = self.installation()
        current = self.require_current()
        self.check_drift(
            installation,
            dict(current["images"], version=current["version"]),
            current["stack_sha256"],
        )
        if self.operation() is not None:
            raise Refusal("resolve the active operation first")
        entries = installation.setdefault("reference", {})
        if args.action == "clear":
            entries.pop(args.kind, None)
        else:
            if not re.fullmatch(r"[A-Za-z0-9._-]+", args.file or ""):
                raise Refusal("--file must be a plain file name inside the reference directory")
            path = self.layout.reference / args.file
            if not path.is_file() or path.is_symlink():
                raise Refusal(f"{path} is not a regular file")
            actual = sha256_file(path)
            if actual != args.sha256:
                raise Refusal(f"reference dataset digest {actual} does not match")
            entries[args.kind] = {
                "file": args.file,
                "sha256": actual,
                "bytes": path.stat().st_size,
                "provenance": args.provenance,
                "recorded_at": utc_now(),
            }
        write_json(self.layout.installation_file, installation)
        self.apply_locked(installation, current)
        self.journal("reference", kind=args.kind, action=args.action)

    def apply(self) -> None:
        self.lock()
        installation = self.installation()
        current = self.require_current()
        if self.operation() is not None:
            raise Refusal("resolve the active operation first")
        self.apply_locked(installation, current)

    def apply_locked(self, installation: Json, current: Json) -> None:
        self.require_no_pending_restore()
        self.check_volumes()
        images = dict(current["images"], version=current["version"])
        self.write_stack(installation, images, self.stored_compose(current))
        self.stack.start()
        self.acceptance_checks(installation, current)
        self.journal("apply", release=current["version"])

    def status(self, as_json: bool) -> int:
        installation = self.installation()
        current = self.current()
        operation = self.operation()
        problems = []
        services = {}
        for service in SERVICES:
            details = self.stack.container(service)
            state = (details or {}).get("State") or {}
            health = (state.get("Health") or {}).get("Status") or state.get("Status", "missing")
            services[service] = health
            if health != "healthy":
                problems.append(f"{service} {health}")
        sets = self.sets()
        newest = sets[-1]["created_at"] if sets else None
        if newest is None:
            problems.append("no recovery set")
        else:
            age = datetime.datetime.now(datetime.timezone.utc) - parse_time(newest)
            if age > datetime.timedelta(hours=BACKUP_MAX_AGE_HOURS):
                problems.append(f"newest recovery set is older than {BACKUP_MAX_AGE_HOURS}h")
        if operation is not None:
            problems.append("operation {} {}".format(operation["id"], operation["status"]))
        if self.layout.restore_marker.exists():
            problems.append("interrupted replacement restore")
        usage = shutil.disk_usage(str(self.layout.root))
        if usage.free < 5 * 1024**3:
            problems.append("less than 5 GiB free")
        report = {
            "installation_id": installation["installation_id"],
            "release": current and {k: current[k] for k in ("version", "images", "alembic_head")},
            "services": services,
            "operation": operation and {k: operation.get(k) for k in ("id", "status", "phase")},
            "newest_recovery_set": newest,
            "disk_free": usage.free,
            "problems": problems,
        }
        if as_json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            for key, value in report.items():
                print(f"{key}: {json.dumps(value)}")
        return 1 if problems else 0

    def check_release(self, args: argparse.Namespace) -> int:
        """Separate release notification; never relies on Dockhand update badges."""
        manifest, digest = load_manifest(
            args.manifest, args.manifest_sha256, args.allow_test_candidate
        )
        current = self.require_current()
        target = release_record(manifest, digest)
        if target["images"] == current["images"]:
            say("release {} is deployed".format(manifest["version"]))
            return 0
        if target["postgres_identity"] != current["postgres_identity"]:
            say("release {} changes PostgreSQL: separate maintenance".format(manifest["version"]))
        say("RELEASE_AVAILABLE {} (operator promotion required)".format(manifest["version"]))
        return 10


def metadata_release(metadata: Json) -> Json:
    release = metadata["release"]
    return {
        "version": release["version"],
        "source_revision": release["source_revision"],
        "manifest_sha256": release["manifest_sha256"],
        "alembic_head": release["alembic_head"],
        "images": metadata["images"],
        "postgres_identity": metadata["postgres_identity"],
        "stack_sha256": metadata["configuration"]["stack_sha256"],
    }


def verify_checksums(directory: Path) -> Json:
    sums = directory / "SHA256SUMS"
    if not sums.exists():
        raise Refusal(f"{directory} has no SHA256SUMS")
    names = set()
    for line in sums.read_text().splitlines():
        expected, _, name = line.partition("  ")
        if "/" in name or name in names:
            raise Refusal("unsafe SHA256SUMS entry")
        names.add(name)
        if sha256_file(directory / name) != expected:
            raise Failure(f"checksum mismatch for {directory.name}/{name}")
    required = {"attachments.tar", "compose.yaml", "database.dump", "metadata.json"}
    if names != required:
        raise Failure("recovery set must checksum exactly " + ", ".join(sorted(required)))
    metadata = read_json(directory / "metadata.json")
    for name, details in metadata["artifacts"].items():
        if sha256_file(directory / name) != details["sha256"]:
            raise Failure("metadata digest mismatch for " + name)
    return metadata


def select_retained(
    sets: list[Json], daily: int, weekly: int, upgrades: int
) -> tuple[list[str], list[str]]:
    """Newest per day/ISO week, recent pre-upgrade sets and always the newest set."""
    ordered = sorted(sets, key=lambda item: item["created_at"], reverse=True)
    keep: list[str] = []
    days: list[str] = []
    weeks: list[tuple[int, int]] = []
    upgrade_sets = 0
    for item in ordered:
        created = parse_time(item["created_at"])
        day = created.strftime("%Y-%m-%d")
        week = created.isocalendar()[:2]
        retained = item is ordered[0]
        if day not in days and len(days) < daily:
            days.append(day)
            retained = True
        if week not in weeks and len(weeks) < weekly:
            weeks.append(week)
            retained = True
        if item["kind"] in {"pre-upgrade", "safety"} and upgrade_sets < upgrades:
            upgrade_sets += 1
            retained = True
        if retained:
            keep.append(item["set_id"])
    remove = [item["set_id"] for item in ordered if item["set_id"] not in keep]
    return keep, remove


def redact(repository: str) -> str:
    return re.sub(r"//[^@/]*@", "//***@", repository)


def read_password() -> str:
    if sys.stdin.isatty():
        password = getpass.getpass("Owner password: ")
    else:
        password = sys.stdin.readline().rstrip("\r\n")
    if not password:
        raise Refusal("an owner password is required on stdin")
    return password


def http_request(
    url: str,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, Any, bytes]:
    request = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    try:
        response = urllib.request.urlopen(request, timeout=20)
    except urllib.error.HTTPError as error:
        response = error
    except (urllib.error.URLError, OSError) as error:
        raise Failure(f"{method} {url}: {error}") from error
    with response:
        return int(response.status), response.headers, response.read()


def http_acceptance(base: str, current: Json) -> None:
    for path in ("/healthz", "/api/v1/health", "/api/v1/ready"):
        status, _, _ = http_request(base + path)
        if status != 200:
            raise Failure(f"{base}{path} returned {status}")
    status, _, body = http_request(base + "/release.json")
    release = json.loads(body.decode()) if status == 200 else {}
    if (
        release.get("version") != current["version"]
        or release.get("revision") != current["source_revision"]
    ):
        raise Failure("frontend release surface does not match the deployed release")
    status, _, _ = http_request(base + "/api/v1/auth/session")
    if status != 401:
        raise Failure(f"anonymous session must be rejected, got {status}")


def owner_acceptance(base: str, origin: str, login: str, password: str) -> None:
    payload = json.dumps({"login_name": login, "password": password}).encode()
    status, headers, body = http_request(
        base + "/api/v1/auth/login",
        "POST",
        payload,
        {"Origin": origin, "Content-Type": "application/json"},
    )
    if status != 200:
        raise Failure(f"owner login returned {status}")
    jar = http.cookies.SimpleCookie()
    for value in headers.get_all("Set-Cookie") or []:
        jar.load(value)
    morsel = jar.get(SESSION_COOKIE)
    if (
        morsel is None
        or not morsel["secure"]
        or not morsel["httponly"]
        or str(morsel["samesite"]).lower() != "strict"
        or morsel["path"] != "/"
    ):
        raise Failure("session cookie lacks Secure/HttpOnly/SameSite=Strict/Path=/")
    cookie = {"Cookie": morsel.key + "=" + morsel.value}
    csrf = json.loads(body.decode())["csrf_token"]
    status, _, body = http_request(base + "/api/v1/auth/session", headers=cookie)
    session = json.loads(body.decode()) if status == 200 else {}
    if session.get("owner") is not True or session.get("canonical_origin") != origin:
        raise Failure("owner session does not match the canonical origin")
    foreign = dict(cookie, Origin="https://foreign.invalid")
    foreign["X-CSRF-Token"] = csrf
    if http_request(base + "/api/v1/auth/logout", "POST", b"", foreign)[0] != 403:
        raise Failure("foreign Origin logout was not refused")
    if (
        http_request(base + "/api/v1/auth/logout", "POST", b"", dict(cookie, Origin=origin))[0]
        != 403
    ):
        raise Failure("logout without CSRF token was not refused")
    good = dict(cookie, Origin=origin)
    good["X-CSRF-Token"] = csrf
    if http_request(base + "/api/v1/auth/logout", "POST", b"", good)[0] != 200:
        raise Failure("owner logout failed")
    if http_request(base + "/api/v1/auth/session", headers=cookie)[0] != 401:
        raise Failure("session survived logout")
    say(f"OWNER_LOGIN_PASSED origin={origin}")


# --------------------------------------------------------------------------- CLI


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--root", required=True, type=Path, help="installation root directory")
    commands = root.add_subparsers(dest="command", required=True)

    def manifest_args(command: argparse.ArgumentParser) -> None:
        command.add_argument("--manifest", required=True, type=Path)
        command.add_argument("--manifest-sha256", required=True)
        command.add_argument("--allow-test-candidate", action="store_true", help=argparse.SUPPRESS)

    def restic_args(command: argparse.ArgumentParser) -> None:
        command.add_argument("set_id")
        command.add_argument("--repository", required=True)
        command.add_argument("--password-file", required=True)
        command.add_argument("--restic-env-file")
        command.add_argument("--restic-image", default=RESTIC_IMAGE)
        command.add_argument("--network", default="bridge")

    command = commands.add_parser("preflight", help="record host qualification evidence")
    command.add_argument("--evidence", type=Path)
    command = commands.add_parser("init", help="create directories, secrets and configuration")
    command.add_argument("--origin", required=True)
    command.add_argument("--http-port", type=int, default=8080)
    command.add_argument("--bind-address", default="127.0.0.1")
    command.add_argument("--db-memory", default="1g")
    command.add_argument("--db-cpus", default="0")
    command.add_argument("--backend-memory", default="768m")
    command.add_argument("--backend-cpus", default="0")
    manifest_args(commands.add_parser("install", help="install the first release"))
    command = commands.add_parser("bootstrap-owner", help="create the owner (password on stdin)")
    command.add_argument("login")
    command.add_argument("--display-name")
    command = commands.add_parser("acceptance", help="verify the running release")
    command.add_argument("--base-url", help="e.g. https://node.tailnet.ts.net")
    command.add_argument("--owner", help="also log in as this owner (password on stdin)")
    commands.add_parser("status", help="health/backup/operation summary").add_argument(
        "--json", action="store_true"
    )
    commands.add_parser("backup", help="create a paired recovery set")
    commands.add_parser("verify-backup", help="verify a recovery set").add_argument("set_id")
    commands.add_parser("list-backups", help="list recovery sets")
    command = commands.add_parser("retention", help="expire recovery sets (dry run by default)")
    command.add_argument("--daily", type=int, default=7)
    command.add_argument("--weekly", type=int, default=4)
    command.add_argument("--upgrades", type=int, default=3)
    command.add_argument("--apply", action="store_true")
    command = commands.add_parser("export", help="encrypted off-host copy with restic")
    restic_args(command)
    command.add_argument("--init", action="store_true", help="initialize a new repository")
    restic_args(commands.add_parser("import-set", help="fetch a set from restic"))
    command = commands.add_parser("restore-isolated", help="restore a set into a new project")
    command.add_argument("set_id")
    command.add_argument("--http-port", type=int, required=True)
    command.add_argument("--owner", help="log in as this owner after restore (password on stdin)")
    command = commands.add_parser("restore-remove", help="remove an isolated restore drill")
    command.add_argument("--project", required=True)
    command.add_argument("--confirm", required=True)
    command = commands.add_parser("restore-replace", help="replace live data with a set")
    command.add_argument("set_id")
    command.add_argument("--confirm-installation", required=True)
    command.add_argument("--confirm-database", required=True)
    command = commands.add_parser("promote", help="serialized journaled application upgrade")
    manifest_args(command)
    command.add_argument("--confirm-migration", action="store_true")
    command.add_argument("--after-failed", action="store_true", help="forward fix a failed upgrade")
    commands.add_parser("resume", help="continue an interrupted promotion")
    commands.add_parser("abort", help="return to the previous release if the schema is unchanged")
    commands.add_parser("apply", help="re-render stack files and redeploy the current release")
    command = commands.add_parser("reference", help="provision optional read-only datasets")
    command.add_argument("action", choices=("set", "clear"))
    command.add_argument("--kind", required=True, choices=sorted(REFERENCE_SETTINGS))
    command.add_argument("--file")
    command.add_argument("--sha256")
    command.add_argument("--provenance", default="")
    manifest_args(commands.add_parser("check-release", help="notify about an approved release"))
    return root


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    controller = Controller(args.root.resolve() if args.root.exists() else args.root)
    command = args.command
    try:
        if command == "preflight":
            return controller.preflight(args.evidence)
        if command == "init":
            controller.init(args)
        elif command == "install":
            controller.install(args)
        elif command == "bootstrap-owner":
            controller.bootstrap_owner(args.login, args.display_name)
        elif command == "acceptance":
            controller.acceptance(args)
        elif command == "status":
            return controller.status(args.json)
        elif command == "backup":
            controller.lock()
            controller.require_no_pending_restore()
            if controller.operation() is not None:
                raise Refusal("resolve the active operation before an ordinary backup")
            controller.backup("manual", writers_held=False)
        elif command == "verify-backup":
            controller.verify_backup(args.set_id)
        elif command == "list-backups":
            for item in controller.sets():
                print("{set_id}  {kind:<11}  {release[version]}  {alembic_revision}".format(**item))
        elif command == "retention":
            controller.retention(args.daily, args.weekly, args.upgrades, args.apply)
        elif command == "export":
            controller.export(args)
        elif command == "import-set":
            controller.import_set(args)
        elif command == "restore-isolated":
            controller.restore_isolated(args)
        elif command == "restore-remove":
            controller.restore_remove(args.project, args.confirm)
        elif command == "restore-replace":
            controller.restore_replace(args)
        elif command == "promote":
            controller.promote(args)
        elif command == "resume":
            controller.resume()
        elif command == "abort":
            controller.abort()
        elif command == "apply":
            controller.apply()
        elif command == "reference":
            controller.reference(args)
        elif command == "check-release":
            return controller.check_release(args)
    except Refusal as error:
        print(f"florabasectl: REFUSED: {error}", file=sys.stderr)
        return 2
    except Failure as error:
        print(f"florabasectl: FAILED: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
