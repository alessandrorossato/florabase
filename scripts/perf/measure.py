#!/usr/bin/env python3
"""PERF-001 controller for the isolated florabase-perf COMPREHENSIVE harness."""

from __future__ import annotations

import argparse
import gzip
import http.cookiejar
import json
import os
import re
import signal
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import FrameType
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[2]
PERF_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = ROOT / "scripts"
for path_entry in (PERF_DIR, SCRIPTS_DIR):
    if str(path_entry) not in sys.path:
        sys.path.insert(0, str(path_entry))

import comprehensive  # noqa: E402
from workflow_resources import lock_root, machine_lock  # noqa: E402

COMPOSE = ROOT / "scripts/perf/compose.sh"
ORIGIN = "http://localhost:18080"
PROJECT = "florabase-perf"
DB_NAME = "florabase_perf"
DB_USER = "florabase_perf"

OWNER_LABEL = "io.florabase.workflow.owner"
SOURCE_LABEL = "io.florabase.workflow.source"
HEAD_LABEL = "io.florabase.workflow.source_head"
ROLE_LABEL = "io.florabase.workflow.lifecycle"
REVISION_LABEL = "org.opencontainers.image.revision"

# Process-local context set only while this process holds the machine lifecycle lock / override.
_ACTIVE_OVERRIDE_FILE: Path | None = None
_ACTIVE_LOCK_FD: int | None = None


@dataclass
class PerfInvocation:
    """Explicit ownership & lifecycle state for one benchmark invocation."""

    owner_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source: str = str(ROOT)
    source_head: str = ""
    override_dir: Path | None = None
    override_file: Path | None = None
    owns_resources: bool = False
    images_built: bool = False

    @property
    def backend_image(self) -> str:
        return f"{PROJECT}-backend:{self.owner_id}"

    @property
    def frontend_image(self) -> str:
        return f"{PROJECT}-frontend:{self.owner_id}"

    @property
    def image_tags(self) -> tuple[str, str]:
        return (self.backend_image, self.frontend_image)

    def has_owned_resources(self) -> bool:
        return self.owns_resources or self.images_built

    def labels(self) -> dict[str, str]:
        labels = {
            OWNER_LABEL: self.owner_id,
            SOURCE_LABEL: self.source,
            ROLE_LABEL: "perf-benchmark",
        }
        if self.source_head:
            labels[HEAD_LABEL] = self.source_head
        return labels

    def metadata(self) -> dict[str, Any]:
        return {
            "owner_id": self.owner_id,
            "source_head": self.source_head,
            "images": list(self.image_tags),
        }


def _compose_env_and_fds() -> tuple[dict[str, str], tuple[int, ...]]:
    """Return Compose env and synchronous-only lock fd inheritance.

    Only synchronous COMPOSE subprocesses receive _ACTIVE_LOCK_FD while the parent
    holds _perf_lock(); compose.sh validates the descriptor and closes it before exec
    so Docker Compose never passes the lock fd to background grandchildren.
    """
    env = dict(os.environ)
    if _ACTIVE_LOCK_FD is None:
        return env, ()
    env["FLORABASE_PERF_LOCK_FD"] = str(_ACTIVE_LOCK_FD)
    return env, (_ACTIVE_LOCK_FD,)


def compose(*args: str, input: str | None = None) -> str:
    """Run synchronous compose.sh command under active override and synchronous lock inheritance."""
    cmd = [str(COMPOSE)]
    if _ACTIVE_OVERRIDE_FILE is not None:
        cmd.extend(["--file", str(_ACTIVE_OVERRIDE_FILE)])
    cmd.extend(args)
    env, pass_fds = _compose_env_and_fds()
    return subprocess.check_output(cmd, input=input, text=True, env=env, pass_fds=pass_fds)


def compose_bytes(*args: str, data: bytes) -> bytes:
    """Run synchronous compose.sh command with binary stdin and synchronous lock inheritance."""
    cmd = [str(COMPOSE)]
    if _ACTIVE_OVERRIDE_FILE is not None:
        cmd.extend(["--file", str(_ACTIVE_OVERRIDE_FILE)])
    cmd.extend(args)
    env, pass_fds = _compose_env_and_fds()
    return subprocess.check_output(cmd, input=data, env=env, pass_fds=pass_fds)


def _docker_output(*args: str) -> str:
    return subprocess.check_output(["docker", *args], text=True)


def _docker_lines(*args: str) -> list[str]:
    return [line.strip() for line in _docker_output(*args).splitlines() if line.strip()]


def _docker_inspect_one(kind: str, identifier: str) -> dict[str, Any]:
    cmd = ["inspect"] if kind == "containers" else [kind[:-1], "inspect"]
    raw = json.loads(_docker_output(*cmd, identifier))
    if not raw:
        raise RuntimeError(f"Missing docker {kind} inspect output for {identifier}")
    return cast(dict[str, Any], raw[0])


def _resource_labels(item: dict[str, Any], kind: str) -> dict[str, str]:
    section = item.get("Config", {}) if kind in {"containers", "images"} else item
    labels = (section or {}).get("Labels") or {}
    return cast(dict[str, str], labels)


def _write_invocation_override(invocation: PerfInvocation, directory: Path) -> Path:
    labels = invocation.labels()
    build_labels = {**labels}
    if invocation.source_head:
        build_labels[REVISION_LABEL] = invocation.source_head
    override: dict[str, Any] = {
        "services": {
            "db": {"labels": labels},
            "backend": {
                "image": invocation.backend_image,
                "labels": labels,
                "build": {"labels": build_labels},
            },
            "frontend": {
                "image": invocation.frontend_image,
                "labels": labels,
                "build": {"labels": build_labels},
            },
        },
        "networks": {"internal": {"labels": labels}},
    }
    path = directory / "perf-ownership.json"
    path.write_text(json.dumps(override, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    invocation.override_dir = directory
    invocation.override_file = path
    return path


class _ActiveOverrideContext(AbstractContextManager[None]):
    def __init__(self, override_file: Path | None, lock_fd: int | None = None) -> None:
        self.override_file = override_file
        self.lock_fd = lock_fd
        self.prev_override: Path | None = None
        self.prev_lock_fd: int | None = None

    def __enter__(self) -> None:
        global _ACTIVE_OVERRIDE_FILE, _ACTIVE_LOCK_FD
        self.prev_override = _ACTIVE_OVERRIDE_FILE
        self.prev_lock_fd = _ACTIVE_LOCK_FD
        if self.override_file is not None:
            _ACTIVE_OVERRIDE_FILE = self.override_file
        if self.lock_fd is not None:
            _ACTIVE_LOCK_FD = self.lock_fd

    def __exit__(self, *_: object) -> None:
        global _ACTIVE_OVERRIDE_FILE, _ACTIVE_LOCK_FD
        _ACTIVE_OVERRIDE_FILE = self.prev_override
        _ACTIVE_LOCK_FD = self.prev_lock_fd


def _perf_lock() -> AbstractContextManager[Any]:
    return cast(
        AbstractContextManager[Any],
        machine_lock(PROJECT, f"{PROJECT} benchmark lifecycle"),
    )


def _invocation_state_path() -> Path:
    return cast(Path, lock_root() / f"{PROJECT}.invocation.json")


def _persist_invocation_state(invocation: PerfInvocation) -> None:
    path = _invocation_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    tmp.write_text(json.dumps(invocation.metadata(), sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _clear_invocation_state(owner_id: str | None) -> None:
    path = _invocation_state_path()
    if not path.is_file() or path.is_symlink():
        return
    try:
        recorded = json.loads(path.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return
    if owner_id is None or recorded.get("owner_id") == owner_id:
        path.unlink(missing_ok=True)


def sql(query: str) -> str:
    return compose(
        "exec",
        "-T",
        "db",
        "psql",
        "-U",
        DB_USER,
        "-d",
        DB_NAME,
        "-qAt",
        "-c",
        query,
    ).strip()


def _live_table_counts() -> tuple[dict[str, int], int, int]:
    """Read live per-table counts from florabase_perf matching golden_dataset.table_counts."""
    excluded = sorted(comprehensive.EXCLUDED_COUNT_TABLES | {"alembic_version", "app_metadata"})
    excluded_sql = ", ".join(f"'{name}'" for name in excluded)
    tables = json.loads(
        sql(
            "SELECT coalesce(json_agg(tablename ORDER BY tablename), '[]') "
            "FROM pg_tables WHERE schemaname = 'public' "
            f"AND tablename NOT IN ({excluded_sql})"
        )
    )
    counts: dict[str, int] = {}
    for table in tables:
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", table):
            raise RuntimeError(f"Unexpected table identifier: {table!r}")
        where = " WHERE place_kind = 'custom'" if table == "geographic_places" else ""
        count = int(sql(f'SELECT count(*) FROM "{table}"{where}'))
        if count:
            counts[table] = count
    canonical_places = int(
        sql("SELECT count(*) FROM geographic_places WHERE place_kind = 'canonical'")
    )
    attachments_count = int(sql("SELECT count(*) FROM attachments"))
    return counts, canonical_places, attachments_count


def _collect_software_versions() -> dict[str, str]:
    postgres_version = sql("SHOW server_version")
    backend_python = compose(
        "exec", "-T", "backend", "python", "-c", "import platform; print(platform.python_version())"
    ).strip()
    uvicorn_version = compose(
        "exec", "-T", "backend", "python", "-c", "import uvicorn; print(uvicorn.__version__)"
    ).strip()
    nginx_version = subprocess.check_output(
        ["docker", "exec", f"{PROJECT}-frontend-1", "nginx", "-v"],
        stderr=subprocess.STDOUT,
        text=True,
    ).strip()
    return {
        "postgresql": postgres_version,
        "backend_python": backend_python,
        "uvicorn": uvicorn_version,
        "nginx": nginx_version,
    }


def _collect_image_metadata(invocation: PerfInvocation | None = None) -> list[dict[str, Any]]:
    tags = (
        [invocation.backend_image, invocation.frontend_image, "postgres:18.6-alpine"]
        if invocation is not None
        else [f"{PROJECT}-backend", f"{PROJECT}-frontend", "postgres:18.6-alpine"]
    )
    raw = _docker_output("image", "inspect", *tags, "--format", "{{json .}}")
    items: list[dict[str, Any]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parsed = json.loads(line)
        labels = _resource_labels(parsed, "images")
        items.append(
            {
                "id": parsed.get("Id"),
                "repo_tags": parsed.get("RepoTags", []),
                "size_bytes": parsed.get("Size"),
                "created": parsed.get("Created"),
                "source_head": labels.get(HEAD_LABEL) or labels.get(REVISION_LABEL),
                "owner_id": labels.get(OWNER_LABEL),
            }
        )
    return items


def _collect_process_counts() -> dict[str, Any]:
    counts: dict[str, Any] = {}
    for service in comprehensive.REQUIRED_SERVICES:
        container = f"{PROJECT}-{service}-1"
        raw = _docker_output("top", container, "-eo", "pid,comm")
        lines = [line.strip() for line in raw.splitlines()[1:] if line.strip()]
        commands = [
            line.split(None, 1)[1] if len(line.split(None, 1)) == 2 else line for line in lines
        ]
        counts[service] = {
            "count": len(lines),
            "commands": commands,
        }
    return counts


def _sample_sql(query: str) -> str:
    """Read-only SQL query for sample telemetry without taking the compose lifecycle lock."""
    return subprocess.check_output(
        [
            "docker",
            "exec",
            f"{PROJECT}-db-1",
            "psql",
            "-U",
            DB_USER,
            "-d",
            DB_NAME,
            "-qAt",
            "-c",
            query,
        ],
        text=True,
    ).strip()


def sample() -> dict[str, Any]:
    return {
        "at": round(time.time(), 1),
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "containers": [
            json.loads(line)
            for line in subprocess.check_output(
                [
                    "docker",
                    "stats",
                    "--no-stream",
                    "--format",
                    "{{json .}}",
                    f"{PROJECT}-backend-1",
                    f"{PROJECT}-frontend-1",
                    f"{PROJECT}-db-1",
                ],
                text=True,
            ).splitlines()
        ],
        "connections": json.loads(
            _sample_sql(
                "SELECT json_build_object('total', count(*), 'idle', "
                "count(*) FILTER (WHERE state='idle')) FROM pg_stat_activity "
                f"WHERE datname='{DB_NAME}' AND pid<>pg_backend_pid()"
            )
        ),
        "sessions": json.loads(
            _sample_sql(
                "SELECT json_build_object('count',count(*),'last_seen_at',"
                "max(last_seen_at),'idle_expires_at',max(idle_expires_at)) "
                "FROM auth_sessions WHERE revoked_at IS NULL"
            )
        ),
        "load": Path("/proc/loadavg").read_text(encoding="utf-8").strip(),
    }


def _existing_project_networks() -> list[str]:
    try:
        return _docker_lines(
            "network", "ls", "-q", "--filter", f"label=com.docker.compose.project={PROJECT}"
        )
    except OSError, subprocess.CalledProcessError:
        return []


def _check_perf_isolation() -> None:
    config = json.loads(compose("config", "--format", "json"))
    for name in ("db", "backend"):
        service = config["services"][name]
        if service.get("volumes") or not service.get("tmpfs") or service.get("ports"):
            raise RuntimeError("PERF isolation guard failed")
    if config["name"] != PROJECT:
        raise RuntimeError("Unexpected project")
    if compose("ps", "--all", "-q").strip():
        raise RuntimeError("PERF containers already exist; stop only owned PERF project first")
    if _existing_project_networks():
        raise RuntimeError("PERF networks already exist; clean up owned PERF network first")


def _build_and_start_services(
    *,
    invocation: PerfInvocation,
    pin_mode: str,
    build_images: bool,
) -> dict[str, Any]:
    """Execute provisioning, optional build, startup, restore, and manifest validation."""
    started_at = datetime.now(UTC).isoformat()
    times: dict[str, float] = {}

    begin = time.monotonic()
    bundle = comprehensive.provision_comprehensive_bundle(ROOT)
    times["provision_bundle_s"] = round(time.monotonic() - begin, 1)

    if build_images:
        begin = time.monotonic()
        invocation.images_built = True
        compose("build", "backend", "frontend")
        times["build_images_s"] = round(time.monotonic() - begin, 1)

    invocation.owns_resources = True

    begin = time.monotonic()
    compose("up", "-d", "--wait", "db")
    times["database_health_s"] = round(time.monotonic() - begin, 1)

    begin = time.monotonic()
    compose_bytes(
        "exec",
        "-T",
        "db",
        "pg_restore",
        "-U",
        DB_USER,
        "-d",
        DB_NAME,
        "--single-transaction",
        "--no-owner",
        "--no-privileges",
        data=bundle.dump_bytes,
    )
    sql("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")
    sql("ANALYZE")
    times["restore_db_s"] = round(time.monotonic() - begin, 1)

    begin = time.monotonic()
    compose("up", "-d", "--wait", "backend", "frontend")
    times["application_health_s"] = round(time.monotonic() - begin, 1)

    begin = time.monotonic()
    compose_bytes(
        "exec",
        "-T",
        "backend",
        "python",
        "scripts/attachment_artifacts.py",
        "restore",
        data=bundle.originals_tar_bytes,
    )
    media_verify_output = compose(
        "exec", "-T", "backend", "python", "scripts/attachment_artifacts.py", "verify"
    )
    times["restore_media_s"] = round(time.monotonic() - begin, 1)

    live_schema_revision = sql("SELECT version_num FROM alembic_version")
    live_counts, live_canonical_places, live_attachments = _live_table_counts()
    attachment_id = sql(
        f"SELECT attachment_id::text FROM media_assets WHERE id = '{bundle.targets['asset']}'"
    )
    targets = comprehensive.resolve_targets(
        bundle.ledger.get("records", {}), attachment_id=attachment_id
    )
    manifest = comprehensive.validate_fixture_manifest(
        ledger=bundle.ledger,
        verify_baseline=bundle.verify_baseline,
        digest=bundle.digest,
        validate_report=bundle.validate,
        targets=targets,
        live_schema_revision=live_schema_revision,
        live_table_counts=live_counts,
        live_canonical_places_count=live_canonical_places,
        live_attachment_count=live_attachments,
        media_verify_output=media_verify_output,
        pin_mode=pin_mode,
    )
    manifest["targets_source"] = "validated_comprehensive_ledger"
    manifest_payload = {**manifest, "invocation": invocation.metadata()}
    compose(
        "exec",
        "-T",
        "backend",
        "python",
        "-c",
        "import sys; from pathlib import Path; Path('/tmp/perf-manifest.json').write_text(sys.stdin.read())",
        input=json.dumps(manifest_payload),
    )

    host = comprehensive.collect_host_metadata()
    source_identity = comprehensive.collect_source_identity(ROOT)
    return {
        "started_at": started_at,
        "pin_mode": pin_mode,
        "invocation": invocation.metadata(),
        "startup": times,
        "manifest": manifest,
        "provisioning": {
            "route": "disposable_test_copy",
            "compose_file": "scripts/compose_stacks.py integration",
            "provisioning_project": bundle.provisioning_project,
            "copy_name": bundle.copy_name,
            "provisioned_at": bundle.provisioned_at,
            "restored_via": ["pg_dump/pg_restore", "scripts/attachment_artifacts.py"],
            "golden_target_guards_preserved": True,
        },
        "runtime_config": {
            "project": PROJECT,
            "database": DB_NAME,
            "origin": ORIGIN,
            "environment": "development",
            "cookie_mode": "loopback-development",
            "storage_mode": "tmpfs",
            "tmpfs_mounts": {
                "db": "/var/lib/postgresql",
                "backend": "/var/lib/florabase/attachments",
            },
            "tmpfs_disclosure": (
                "PostgreSQL data and attachment storage run on tmpfs; disk durability/sync "
                "latency is excluded and results must not be silently compared against "
                "persistent-storage runs."
            ),
        },
        "source": source_identity,
        "generator": comprehensive.generator_identity(ROOT),
        "host": host,
        "software": _collect_software_versions(),
        "images": _collect_image_metadata(invocation if build_images else None),
        "process_counts": _collect_process_counts(),
        # Retained fields for compatibility with existing reporting scripts.
        "platform": host["platform"],
        "cpu": host["machine"],
        "sha": source_identity["head"],
    }


def start(
    *,
    pin_mode: str = comprehensive.PIN_MODE_STRICT,
    build_images: bool = True,
    invocation: PerfInvocation | None = None,
) -> dict[str, Any]:
    """Start isolated COMPREHENSIVE perf stack under strict ownership & lock guarantees."""
    if pin_mode not in comprehensive.VALID_PIN_MODES:
        raise comprehensive.FixtureValidationError(f"Unsupported pin_mode: {pin_mode!r}")
    standalone = invocation is None
    active_invocation = invocation or PerfInvocation(
        source=str(ROOT),
        source_head=comprehensive.collect_source_identity(ROOT)["head"],
    )
    lock_cm: AbstractContextManager[Any] = _perf_lock() if standalone else nullcontext()
    with lock_cm as lock:
        lock_fd = (
            lock.handle.fileno()
            if standalone and getattr(lock, "handle", None) is not None
            else _ACTIVE_LOCK_FD
        )
        with _ActiveOverrideContext(None, lock_fd=lock_fd):
            _check_perf_isolation()
        with tempfile.TemporaryDirectory(prefix="florabase-perf-override-") as tmp_dir:
            override_path = _write_invocation_override(active_invocation, Path(tmp_dir))
            try:
                with _ActiveOverrideContext(override_path, lock_fd=lock_fd):
                    env_data = _build_and_start_services(
                        invocation=active_invocation,
                        pin_mode=pin_mode,
                        build_images=build_images,
                    )
                if standalone:
                    _persist_invocation_state(active_invocation)
                return env_data
            except BaseException:
                if standalone and active_invocation.has_owned_resources():
                    _stop_owned(
                        owner_id=active_invocation.owner_id,
                        override_file=override_path,
                        image_tags=active_invocation.image_tags
                        if active_invocation.images_built
                        else (),
                    )
                raise


def _load_validated_manifest(env_file: Path | None = None) -> dict[str, Any]:
    if env_file is not None:
        env_data = json.loads(env_file.read_text(encoding="utf-8"))
        manifest = cast(dict[str, Any], env_data["manifest"])
    else:
        manifest = cast(
            dict[str, Any],
            json.loads(compose("exec", "-T", "backend", "cat", "/tmp/perf-manifest.json")),
        )
    if not manifest.get("valid") or manifest.get("profile") != comprehensive.GOLDEN_PROFILE:
        raise comprehensive.FixtureValidationError(
            "Manifest is missing valid COMPREHENSIVE validation status"
        )
    pin_mode = manifest.get("pin_mode", comprehensive.PIN_MODE_STRICT)
    if pin_mode not in comprehensive.VALID_PIN_MODES:
        raise comprehensive.FixtureValidationError(
            f"Manifest carries invalid pin_mode {pin_mode!r}"
        )
    comprehensive.resolve_targets(
        # Targets are already resolved UUIDs; verify every required key is present and well-formed.
        {
            comprehensive.MANIFEST_SCENARIO_KEYS[k]: v
            for k, v in (manifest.get("targets") or {}).items()
            if k in comprehensive.MANIFEST_SCENARIO_KEYS
        },
        attachment_id=(manifest.get("targets") or {}).get("attachment"),
    )
    return manifest


def _format_endpoint_path(template: str, targets: dict[str, str]) -> str:
    replacements = {
        "/botanical-identities/{id}": f"/botanical-identities/{targets['identity']}",
        "/botanical-identities/{id}/collection": f"/botanical-identities/{targets['identity']}/collection",
        "/botanical-identities/{id}/profile": f"/botanical-identities/{targets['rich_identity']}/profile",
        "/seed-lots/{id}": f"/seed-lots/{targets['seed']}",
        "/seed-lots/{id}/lineage": f"/seed-lots/{targets['lineage_seed']}/lineage",
        "/sowings/{id}": f"/sowings/{targets['sowing']}",
        "/sowings/{id}/germination": f"/sowings/{targets['sowing']}/germination",
        "/plants/{id}": f"/plants/{targets['plant']}",
        "/plants/{id}/lineage": f"/plants/{targets['plant']}/lineage",
        "/plant-groups/{id}": f"/plant-groups/{targets['group']}",
        "/vegetative-lots/{id}": f"/vegetative-lots/{targets['cutting_lot']}",
        "/propagation-attempts/{id}": f"/propagation-attempts/{targets['cutting_attempt']}",
        "/harvests/{id}": f"/harvests/{targets['harvest']}",
        "/harvest-inventory/{id}": f"/harvest-inventory/{targets['inventory']}",
        "/orders/{id}": f"/orders/{targets['order']}",
        "/suppliers/{id}": f"/suppliers/{targets['supplier']}",
        "/locations/{id}": f"/locations/{targets['location']}",
        "/provenance-sites/{id}": f"/provenance-sites/{targets['site']}",
        "/collection-records/seed_lot/{id}/photos": f"/collection-records/seed_lot/{targets['seed']}/photos",
        "/media-assets/{id}": f"/media-assets/{targets['asset']}",
        "/media-assets/{id}/thumbnail": f"/media-assets/{targets['asset']}/thumbnail",
        "/collection-photos/local/{id}/thumbnail": f"/collection-photos/local/{targets['photo_link']}/thumbnail",
        "/attachments/{id}/content": f"/attachments/{targets['attachment']}/content",
    }
    return replacements.get(template, template)


def api(env_file: Path | None = None) -> dict[str, Any]:
    started_at = datetime.now(UTC).isoformat()
    manifest = _load_validated_manifest(env_file)
    targets = cast(dict[str, str], manifest["targets"])
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )

    def request(
        path: str,
        method: str = "GET",
        body: dict[str, str] | None = None,
        csrf: str | None = None,
    ) -> tuple[float, bytes]:
        headers = {"Origin": ORIGIN}
        if csrf:
            headers["X-CSRF-Token"] = csrf
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            ORIGIN + "/api/v1" + path,
            method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers=headers,
        )
        begin = time.perf_counter()
        with opener.open(req, timeout=30) as response:
            binary = response.read()
        return round((time.perf_counter() - begin) * 1000, 1), binary

    _, login = request(
        "/auth/login",
        "POST",
        {
            "login_name": comprehensive.GOLDEN_OWNER_LOGIN,
            "password": comprehensive.GOLDEN_OWNER_PASSWORD,
        },
    )
    csrf = json.loads(login)["csrf_token"]

    extension_installed = (
        sql("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements')") == "t"
    )
    shared_preload_libraries = sql("SHOW shared_preload_libraries")
    sql("SELECT pg_stat_statements_reset()")
    request("/dashboard")
    probe_rows = json.loads(
        sql(
            "SELECT coalesce(json_agg(json_build_object('calls',calls)), '[]') "
            "FROM pg_stat_statements WHERE query ~* '^(SELECT|WITH)' AND query NOT LIKE '%pg_stat%'"
        )
    )
    probe_query_captured = sum(int(row.get("calls", 0)) for row in probe_rows) > 0
    if (
        not extension_installed
        or "pg_stat_statements" not in shared_preload_libraries
        or not probe_query_captured
    ):
        raise RuntimeError(
            "SQL instrumentation is inactive or failed probe verification: "
            f"extension={extension_installed}, preload={shared_preload_libraries!r}, probe={probe_query_captured}"
        )

    results: dict[str, Any] = {}
    statements: dict[str, Any] = {}
    for label in comprehensive.REQUIRED_API_ENDPOINTS:
        if label in results:
            raise RuntimeError(f"Duplicate endpoint label in API workload: {label}")
        path = _format_endpoint_path(label, targets)
        first, binary = request(path)
        request(path)
        timings: list[float] = []
        counts: list[int] = []
        rows: list[dict[str, Any]] = []
        for _ in range(7):
            sql("SELECT pg_stat_statements_reset()")
            elapsed, binary = request(path)
            rows = json.loads(
                sql(
                    "SELECT coalesce(json_agg(json_build_object('query',query,"
                    "'calls',calls,'ms',round(total_exec_time::numeric,2))), '[]') "
                    "FROM pg_stat_statements "
                    "WHERE query ~* '^(SELECT|WITH|INSERT|UPDATE|DELETE)' "
                    "AND query NOT LIKE '%pg_stat%' "
                    "AND query NOT IN ('SELECT $1', 'SELECT 1')"
                )
            )
            counts.append(sum(row["calls"] for row in rows))
            timings.append(elapsed)
        results[label] = {
            "first_ms": first,
            "median_ms": statistics.median(timings),
            "range_ms": [min(timings), max(timings)],
            "samples_ms": timings,
            "bytes": len(binary),
            "queries": sorted(set(counts)),
            "query_count_samples": counts,
            "sql_statements_count": len(rows),
            "sql_zero_queries_verified": bool(
                probe_query_captured and extension_installed and 0 in counts
            ),
            "sample_note": "7 samples; not a statistical p95",
        }
        statements[label] = rows

    sql("SELECT pg_stat_statements_reset()")
    begin = time.perf_counter()
    _, created = request(
        "/botanical-identities", "POST", {"scientific_name": "Perf temporary"}, csrf
    )
    created_id = json.loads(created)["id"]
    request(
        f"/botanical-identities/{created_id}",
        "PUT",
        {"scientific_name": "Perf edited"},
        csrf,
    )
    request(f"/botanical-identities/{created_id}", "DELETE", csrf=csrf)
    ced_ms = round((time.perf_counter() - begin) * 1000, 1)

    post_schema = sql("SELECT version_num FROM alembic_version")
    post_counts, post_canonical_places, post_attachments = _live_table_counts()
    remaining_created = int(
        sql(f"SELECT count(*) FROM botanical_identities WHERE id = '{created_id}'")
    )
    residual_named = int(
        sql(
            "SELECT count(*) FROM botanical_identities "
            "WHERE scientific_name IN ('Perf temporary', 'Perf edited')"
        )
    ) + int(
        sql(
            "SELECT count(*) FROM botanical_identity_names "
            "WHERE scientific_name IN ('Perf temporary', 'Perf edited')"
        )
    )
    media_verify_output = compose(
        "exec", "-T", "backend", "python", "scripts/attachment_artifacts.py", "verify"
    )
    expected_counts = cast(dict[str, int], manifest["table_counts"])
    integrity = comprehensive.evaluate_post_mutation_integrity(
        expected_counts=expected_counts,
        post_counts=post_counts,
        expected_canonical_places=int(manifest["canonical_geographic_places"]),
        post_canonical_places=post_canonical_places,
        expected_schema_revision=str(manifest["schema_revision"]),
        post_schema_revision=post_schema,
        created_identity_deleted=(remaining_created == 0),
        residual_perf_records=residual_named,
        media_verify_output=media_verify_output,
        expected_attachments=int(expected_counts["attachments"]),
    )
    if post_attachments != int(expected_counts["attachments"]):
        integrity["media_verified"] = False

    return {
        "started_at": started_at,
        "completed_at": datetime.now(UTC).isoformat(),
        "manifest": manifest,
        "sql_instrumentation": {
            "extension_installed": extension_installed,
            "shared_preload_libraries": shared_preload_libraries,
            "reset_executed_per_sample": True,
            "probe_query_captured": probe_query_captured,
            "sample_count_per_endpoint": 7,
            "endpoints_measured": len(results),
        },
        "reads": results,
        "statements": statements,
        "create_edit_delete_ms": ced_ms,
        "fixture_integrity_after_mutation": integrity,
        "resources": sample(),
    }


def live_occurrence(env_file: Path | None = None, *, attempts: int = 3) -> dict[str, Any]:
    """Separately probe live external occurrence summary endpoint without folding into local timings."""
    manifest = _load_validated_manifest(env_file)
    targets = cast(dict[str, str], manifest["targets"])
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )
    login_req = urllib.request.Request(
        ORIGIN + "/api/v1/auth/login",
        method="POST",
        data=json.dumps(
            {
                "login_name": comprehensive.GOLDEN_OWNER_LOGIN,
                "password": comprehensive.GOLDEN_OWNER_PASSWORD,
            }
        ).encode(),
        headers={"Content-Type": "application/json", "Origin": ORIGIN},
    )
    with opener.open(login_req, timeout=30) as response:
        response.read()

    probes: list[dict[str, Any]] = []
    endpoint = f"/api/v1/botanical-identities/{targets['identity']}/occurrence-map/summary"
    for _ in range(attempts):
        req = urllib.request.Request(ORIGIN + endpoint, headers={"Origin": ORIGIN})
        begin = time.perf_counter()
        try:
            with opener.open(req, timeout=10) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                probes.append(
                    {
                        "status": resp.status,
                        "seconds": round(time.perf_counter() - begin, 3),
                        "total": payload.get("total_matching_records"),
                        "eligible": payload.get("eligible_mapped_records"),
                        "error": None,
                    }
                )
        except urllib.error.HTTPError as err:
            probes.append(
                {
                    "status": err.code,
                    "seconds": round(time.perf_counter() - begin, 3),
                    "total": None,
                    "eligible": None,
                    "error": f"HTTPError {err.code}",
                }
            )
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as err:
            probes.append(
                {
                    "status": None,
                    "seconds": round(time.perf_counter() - begin, 3),
                    "total": None,
                    "eligible": None,
                    "error": f"{type(err).__name__}: {err}",
                }
            )
    return {
        "attempted": True,
        "endpoint": "/api/v1/botanical-identities/{id}/occurrence-map/summary",
        "folded_into_local_timings": False,
        "probes": probes,
    }


def transfer() -> dict[str, Any]:
    """Check static compression and protected integrity without timing budgets."""
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )

    def read(
        path: str, encoding: str
    ) -> tuple[bytes, str | None, str | None, str | None, str | None]:
        req = urllib.request.Request(ORIGIN + path, headers={"Accept-Encoding": encoding})
        with opener.open(req, timeout=30) as response:
            return (
                response.read(),
                response.headers.get("Content-Encoding"),
                response.headers.get("Vary"),
                response.headers.get("Content-Type"),
                response.headers.get("Cache-Control"),
            )

    html, _, _, _, _ = read("/", "identity")
    assets = re.findall(r'(?:src|href)="(/assets/index-[^"]+\.(?:js|css))"', html.decode())
    assert len(assets) == 2, "Expected production entry JS and CSS"
    result: dict[str, Any] = {}
    for path in assets:
        raw, raw_encoding, raw_vary, raw_type, _ = read(path, "identity")
        compressed, encoding, vary, content_type, _ = read(path, "gzip")
        assert raw_encoding is None
        assert encoding == "gzip" and gzip.decompress(compressed) == raw
        assert vary and "accept-encoding" in vary.lower()
        assert raw_vary and "accept-encoding" in raw_vary.lower()
        assert content_type == raw_type
        result[path] = {
            "content_type": content_type,
            "vary": vary,
            "raw_bytes": len(raw),
            "gzip_bytes": len(compressed),
        }
    runtime_config, config_encoding, _, _, cache_control = read("/runtime-config.js", "gzip")
    assert config_encoding is None and cache_control == "no-store"
    health, health_encoding, _, health_type, _ = read("/healthz", "gzip")
    assert health == b"ok\n" and health_encoding is None and health_type == "text/plain"
    login = urllib.request.Request(
        ORIGIN + "/api/v1/auth/login",
        data=json.dumps(
            {
                "login_name": comprehensive.GOLDEN_OWNER_LOGIN,
                "password": comprehensive.GOLDEN_OWNER_PASSWORD,
            }
        ).encode(),
        headers={"Content-Type": "application/json", "Origin": ORIGIN},
    )
    with opener.open(login, timeout=30) as response:
        response.read()
    raw, raw_encoding, _, raw_type, _ = read("/api/v1/events", "identity")
    candidate, encoding, _, content_type, _ = read("/api/v1/events", "gzip")
    assert raw_encoding is None and content_type == raw_type
    assert encoding is None and raw == candidate, "Protected API compression/representation changed"
    return {
        "measured_at": datetime.now(UTC).isoformat(),
        "static_assets": result,
        "runtime_configuration": {
            "bytes": len(runtime_config),
            "cache_control": cache_control,
            "compressed": False,
        },
        "health": {"content_type": health_type, "compressed": False},
        "authenticated_api_bytes": len(raw),
        "authenticated_api_content_type": raw_type,
        "protected_api_compressed": False,
    }


def _resolve_owner_id(env_file: Path | None = None) -> str | None:
    if env_file is not None:
        data = json.loads(env_file.read_text(encoding="utf-8"))
        inv = data.get("invocation")
        if isinstance(inv, dict) and isinstance(inv.get("owner_id"), str):
            return cast(str, inv["owner_id"])
    state_path = _invocation_state_path()
    if state_path.is_file() and not state_path.is_symlink():
        try:
            recorded = json.loads(state_path.read_text(encoding="utf-8"))
            if isinstance(recorded.get("owner_id"), str):
                return cast(str, recorded["owner_id"])
        except OSError, json.JSONDecodeError:
            pass
    try:
        raw = compose("exec", "-T", "backend", "cat", "/tmp/perf-manifest.json")
        manifest = json.loads(raw)
        inv = manifest.get("invocation")
        if isinstance(inv, dict) and isinstance(inv.get("owner_id"), str):
            return cast(str, inv["owner_id"])
    except OSError, subprocess.CalledProcessError, json.JSONDecodeError:
        pass
    return None


def _verify_project_ownership(owner_id: str | None) -> tuple[bool, list[str], list[str], list[str]]:
    containers = _docker_lines(
        "ps", "-aq", "--filter", f"label=com.docker.compose.project={PROJECT}"
    )
    networks = _docker_lines(
        "network", "ls", "-q", "--filter", f"label=com.docker.compose.project={PROJECT}"
    )
    volumes = _docker_lines(
        "volume", "ls", "-q", "--filter", f"label=com.docker.compose.project={PROJECT}"
    )
    if not (containers or networks or volumes):
        return True, [], [], []
    if not owner_id:
        raise RuntimeError(
            f"Refusing cleanup for {PROJECT}: no invocation owner_id found for existing resources"
        )
    for kind, ids in (("containers", containers), ("networks", networks), ("volumes", volumes)):
        for identifier in ids:
            inspected = _docker_inspect_one(kind, identifier)
            actual_owner = _resource_labels(inspected, kind).get(OWNER_LABEL)
            if actual_owner != owner_id:
                raise RuntimeError(
                    f"Refusing cleanup for {PROJECT}: foreign or unowned {kind[:-1]} {identifier} "
                    f"(owner {actual_owner!r} != {owner_id!r})"
                )
    return True, containers, networks, volumes


def _stop_owned(
    *,
    owner_id: str | None,
    override_file: Path | None = None,
    image_tags: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Verify invocation ownership and retire only resources owned by this invocation."""
    _, containers, networks, _volumes = _verify_project_ownership(owner_id)
    with _ActiveOverrideContext(override_file):
        down_output = compose("down") if (containers or networks) else ""

    images_removed: list[str] = []
    if owner_id:
        candidate_tags = list(image_tags) or [
            f"{PROJECT}-backend:{owner_id}",
            f"{PROJECT}-frontend:{owner_id}",
        ]
        # Untag only exact invocation-owned tags so foreign repo tags on shared layers remain untouched.
        for tag in candidate_tags:
            if not tag.endswith(f":{owner_id}"):
                continue
            try:
                inspected = _docker_inspect_one("images", tag)
            except OSError, subprocess.CalledProcessError, RuntimeError:
                continue
            labels = _resource_labels(inspected, "images")
            if labels.get(OWNER_LABEL) != owner_id:
                continue
            _docker_output("image", "rm", tag)
            images_removed.append(tag)

    remaining_containers = _docker_lines(
        "ps", "-aq", "--filter", f"label=com.docker.compose.project={PROJECT}"
    )
    remaining_networks = _docker_lines(
        "network", "ls", "-q", "--filter", f"label=com.docker.compose.project={PROJECT}"
    )
    remaining_volumes = _docker_lines(
        "volume", "ls", "-q", "--filter", f"label=com.docker.compose.project={PROJECT}"
    )
    remaining_images: list[str] = []
    if owner_id:
        for image_id in _docker_lines(
            "image", "ls", "-q", "--filter", f"label={OWNER_LABEL}={owner_id}"
        ):
            repo_tags = _docker_inspect_one("images", image_id).get("RepoTags") or []
            if not repo_tags or any(tag.endswith(f":{owner_id}") for tag in repo_tags):
                remaining_images.append(image_id)
    _clear_invocation_state(owner_id)
    return {
        "project": PROJECT,
        "owner_id": owner_id,
        "ownership_verified": True,
        "stopped_at": datetime.now(UTC).isoformat(),
        "compose_down_output": down_output.strip(),
        "images_removed": images_removed,
        "containers_remaining": len(remaining_containers),
        "networks_remaining": len(remaining_networks),
        "volumes_remaining": len(remaining_volumes),
        "images_remaining": len(remaining_images),
        "named_volumes_deleted": 0,
    }


def stop(env_file: Path | None = None, *, owner_id: str | None = None) -> dict[str, Any]:
    with _perf_lock() as lock:
        lock_fd = lock.handle.fileno() if getattr(lock, "handle", None) is not None else None
        with _ActiveOverrideContext(None, lock_fd=lock_fd):
            resolved_owner = owner_id or _resolve_owner_id(env_file)
            return _stop_owned(owner_id=resolved_owner)


def build_report(
    *,
    environment: dict[str, Any] | None = None,
    api_data: dict[str, Any] | None = None,
    transfer_data: dict[str, Any] | None = None,
    browser_data: dict[str, Any] | None = None,
    chunk_recovery: dict[str, Any] | None = None,
    cleanup_data: dict[str, Any] | None = None,
    live_occurrence_data: dict[str, Any] | None = None,
    profile_text: str | None = None,
    plans_data: dict[str, Any] | None = None,
    warmup_s: int | None = None,
    errors: list[str] | None = None,
    pin_mode: str | None = None,
) -> dict[str, Any]:
    effective_pin_mode = (
        pin_mode or (environment or {}).get("pin_mode") or comprehensive.PIN_MODE_STRICT
    )
    combined: dict[str, Any] = {
        "schema_version": 2,
        "generated_at": datetime.now(UTC).isoformat(),
        "pin_mode": effective_pin_mode,
        "warmup_s": warmup_s,
        "errors": list(errors) if errors is not None else [],
        "environment": environment,
        "api": api_data,
        "transfer": transfer_data,
        "browser": browser_data,
        "chunk_recovery": chunk_recovery,
        "cleanup": cleanup_data,
    }
    if live_occurrence_data is not None:
        combined["live_occurrence"] = live_occurrence_data
    if profile_text is not None:
        combined["profile_summary"] = profile_text
    if plans_data is not None:
        combined["query_plans"] = plans_data
    combined["evaluation"] = comprehensive.evaluate_report(combined, pin_mode=effective_pin_mode)
    return combined


def run_rehearsal(
    *,
    warmup_s: int = 20,
    pin_mode: str = comprehensive.PIN_MODE_STRICT,
    build_images: bool = True,
    include_live_occurrence: bool = True,
) -> dict[str, Any]:
    """Execute end-to-end COMPREHENSIVE harness with exclusive lock and ownership-verified cleanup."""
    if pin_mode not in comprehensive.VALID_PIN_MODES:
        raise comprehensive.FixtureValidationError(f"Unsupported pin_mode: {pin_mode!r}")

    env_data: dict[str, Any] | None = None
    api_data: dict[str, Any] | None = None
    transfer_data: dict[str, Any] | None = None
    browser_data: dict[str, Any] | None = None
    chunk_data: dict[str, Any] | None = None
    live_data: dict[str, Any] | None = None
    profile_text: str | None = None
    plans_data: dict[str, Any] | None = None
    cleanup_data: dict[str, Any] | None = None
    errors: list[str] = []

    source_head = comprehensive.collect_source_identity(ROOT)["head"]
    invocation = PerfInvocation(source=str(ROOT), source_head=source_head)
    handlers: dict[signal.Signals, Any] = {}

    def handle_signal(signum: int, _frame: FrameType | None) -> None:
        raise KeyboardInterrupt(f"Interrupted by signal {signum}")

    for sig in (signal.SIGINT, signal.SIGTERM):
        handlers[sig] = signal.signal(sig, handle_signal)

    try:
        with _perf_lock() as lock:
            lock_fd = lock.handle.fileno() if getattr(lock, "handle", None) is not None else None
            with tempfile.TemporaryDirectory(prefix="florabase-perf-run-") as temporary:
                tmp = Path(temporary)
                env_path = tmp / "env.json"
                browser_path = tmp / "browser.json"
                chunk_path = tmp / "chunk.json"
                override_path = _write_invocation_override(invocation, tmp)
                with _ActiveOverrideContext(override_path, lock_fd=lock_fd):
                    try:
                        env_data = start(
                            pin_mode=pin_mode,
                            build_images=build_images,
                            invocation=invocation,
                        )
                        env_path.write_text(json.dumps(env_data, indent=2) + "\n", encoding="utf-8")
                        if warmup_s > 0:
                            time.sleep(warmup_s)
                        api_data = api(env_path)
                        transfer_data = transfer()
                        subprocess.run(
                            [
                                "node",
                                str(PERF_DIR / "browser.mjs"),
                                str(env_path),
                                str(browser_path),
                            ],
                            cwd=ROOT,
                            check=True,
                            env={**os.environ, "PERF_SAMPLE_DIR": str(tmp / "samples")},
                        )
                        browser_data = json.loads(browser_path.read_text(encoding="utf-8"))
                        subprocess.run(
                            ["node", str(PERF_DIR / "verify-chunk-recovery.mjs"), str(chunk_path)],
                            cwd=ROOT,
                            check=True,
                        )
                        chunk_data = json.loads(chunk_path.read_text(encoding="utf-8"))
                        if include_live_occurrence:
                            live_data = live_occurrence(env_path)
                        profile_text = compose(
                            "exec",
                            "-T",
                            "backend",
                            "python",
                            "-",
                            input=(PERF_DIR / "profile.py").read_text(encoding="utf-8"),
                        )
                        plans_raw = compose(
                            "exec",
                            "-T",
                            "backend",
                            "python",
                            "-",
                            input=(PERF_DIR / "plans.py").read_text(encoding="utf-8"),
                        )
                        plans_data = json.loads(plans_raw)
                    except BaseException as error:
                        errors.append(f"{type(error).__name__}: {error}")
                    finally:
                        # Cleanup is permitted ONLY if THIS invocation created/owns resources.
                        if invocation.has_owned_resources():
                            try:
                                cleanup_data = _stop_owned(
                                    owner_id=invocation.owner_id,
                                    override_file=override_path,
                                    image_tags=invocation.image_tags
                                    if invocation.images_built
                                    else (),
                                )
                            except BaseException as cleanup_error:
                                errors.append(
                                    f"CleanupError({type(cleanup_error).__name__}): {cleanup_error}"
                                )
    except BaseException as outer_error:
        errors.append(f"{type(outer_error).__name__}: {outer_error}")
    finally:
        for sig, prev in handlers.items():
            signal.signal(sig, prev)

    return build_report(
        environment=env_data,
        api_data=api_data,
        transfer_data=transfer_data,
        browser_data=browser_data,
        chunk_recovery=chunk_data,
        cleanup_data=cleanup_data,
        live_occurrence_data=live_data,
        profile_text=profile_text,
        plans_data=plans_data,
        warmup_s=warmup_s,
        errors=errors,
        pin_mode=pin_mode,
    )


def _sanitized_external_location(path: Path) -> str:
    resolved = path.resolve()
    xdg_default = (Path.home() / ".local/state").resolve()
    try:
        rel = resolved.relative_to(xdg_default)
        return f"$XDG_STATE_HOME/{rel.as_posix()}"
    except ValueError:
        try:
            rel_home = resolved.relative_to(Path.home().resolve())
            return f"~/{rel_home.as_posix()}"
        except ValueError:
            return str(resolved)


def _load_optional(path: Path | None) -> Any:
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=["start", "api", "sample", "transfer", "live-occurrence", "stop", "report", "run"],
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--summary-out", type=Path)
    parser.add_argument("--env", type=Path)
    parser.add_argument("--api", type=Path)
    parser.add_argument("--transfer", type=Path)
    parser.add_argument("--browser", type=Path)
    parser.add_argument("--chunk", type=Path)
    parser.add_argument("--cleanup", type=Path)
    parser.add_argument("--plans", type=Path)
    parser.add_argument("--warmup-seconds", type=int, default=20)
    parser.add_argument(
        "--pin-mode",
        choices=[comprehensive.PIN_MODE_STRICT, comprehensive.PIN_MODE_ALLOW_MODIFIED],
        default=comprehensive.PIN_MODE_STRICT,
    )
    parser.add_argument("--no-build", action="store_true")
    parser.add_argument("--skip-live-occurrence", action="store_true")
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Refusing to overwrite evidence; use a new output filename")
    if args.summary_out is not None and args.summary_out.exists():
        parser.error("Refusing to overwrite summary evidence; use a new output filename")

    if args.mode == "start":
        result = start(pin_mode=args.pin_mode, build_images=not args.no_build)
    elif args.mode == "api":
        result = api(args.env)
    elif args.mode == "sample":
        result = sample()
    elif args.mode == "transfer":
        result = transfer()
    elif args.mode == "live-occurrence":
        result = live_occurrence(args.env)
    elif args.mode == "stop":
        result = stop(args.env)
    elif args.mode == "report":
        result = build_report(
            environment=_load_optional(args.env),
            api_data=_load_optional(args.api),
            transfer_data=_load_optional(args.transfer),
            browser_data=_load_optional(args.browser),
            chunk_recovery=_load_optional(args.chunk),
            cleanup_data=_load_optional(args.cleanup),
            plans_data=_load_optional(args.plans),
            warmup_s=args.warmup_seconds,
            pin_mode=args.pin_mode,
        )
    else:
        result = run_rehearsal(
            warmup_s=args.warmup_seconds,
            pin_mode=args.pin_mode,
            build_images=not args.no_build,
            include_live_occurrence=not args.skip_live_occurrence,
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(result, indent=2) + "\n"
    args.out.write_text(rendered, encoding="utf-8")
    print(f"{args.mode}: {args.out}")
    if args.summary_out is not None:
        args.summary_out.parent.mkdir(parents=True, exist_ok=True)
        full_provenance = {
            "sha256": comprehensive.sha256_bytes(rendered.encode("utf-8")),
            "bytes": len(rendered.encode("utf-8")),
            "external_location": _sanitized_external_location(args.out),
        }
        summary = comprehensive.summarize_report(result, full_artifact=full_provenance)
        args.summary_out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"{args.mode}-summary: {args.summary_out}")
    if args.mode in {"run", "report"}:
        evaluation = result["evaluation"]
        if result.get("errors") or evaluation["invariant_status"] != "passed":
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
