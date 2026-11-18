#!/usr/bin/env python3
"""PERF-001 controller for the isolated florabase-perf COMPREHENSIVE harness."""

from __future__ import annotations

import argparse
import gzip
import http.cookiejar
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[2]
PERF_DIR = Path(__file__).resolve().parent
if str(PERF_DIR) not in sys.path:
    sys.path.insert(0, str(PERF_DIR))

import comprehensive  # noqa: E402

COMPOSE = ROOT / "scripts/perf/compose.sh"
ORIGIN = "http://localhost:18080"
PROJECT = "florabase-perf"
DB_NAME = "florabase_perf"
DB_USER = "florabase_perf"


def compose(*args: str, input: str | None = None) -> str:
    return subprocess.check_output([str(COMPOSE), *args], input=input, text=True)


def compose_bytes(*args: str, data: bytes) -> bytes:
    return subprocess.check_output([str(COMPOSE), *args], input=data)


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


def _collect_image_metadata() -> list[dict[str, Any]]:
    raw = subprocess.check_output(
        [
            "docker",
            "image",
            "inspect",
            f"{PROJECT}-backend",
            f"{PROJECT}-frontend",
            "postgres:18.6-alpine",
            "--format",
            "{{json .}}",
        ],
        text=True,
    )
    items: list[dict[str, Any]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parsed = json.loads(line)
        items.append(
            {
                "id": parsed.get("Id"),
                "repo_tags": parsed.get("RepoTags", []),
                "size_bytes": parsed.get("Size"),
                "created": parsed.get("Created"),
            }
        )
    return items


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
            sql(
                "SELECT json_build_object('total', count(*), 'idle', "
                "count(*) FILTER (WHERE state='idle')) FROM pg_stat_activity "
                f"WHERE datname='{DB_NAME}' AND pid<>pg_backend_pid()"
            )
        ),
        "sessions": json.loads(
            sql(
                "SELECT json_build_object('count',count(*),'last_seen_at',"
                "max(last_seen_at),'idle_expires_at',max(idle_expires_at)) "
                "FROM auth_sessions WHERE revoked_at IS NULL"
            )
        ),
        "load": Path("/proc/loadavg").read_text(encoding="utf-8").strip(),
    }


def _check_perf_isolation() -> None:
    config = json.loads(compose("config", "--format", "json"))
    for name in ("db", "backend"):
        service = config["services"][name]
        if service.get("volumes") or not service.get("tmpfs") or service.get("ports"):
            raise RuntimeError("PERF isolation guard failed")
    if config["name"] != PROJECT:
        raise RuntimeError("Unexpected project")
    if compose("ps", "--all", "-q").strip():
        raise RuntimeError("PERF containers already exist; stop only PERF project first")


def start() -> dict[str, Any]:
    _check_perf_isolation()
    started_at = datetime.now(UTC).isoformat()
    times: dict[str, float] = {}

    begin = time.monotonic()
    bundle = comprehensive.provision_comprehensive_bundle(ROOT)
    times["provision_bundle_s"] = round(time.monotonic() - begin, 1)

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
        allow_baseline_drift=True,
    )
    manifest["targets_source"] = "validated_comprehensive_ledger"
    compose(
        "exec",
        "-T",
        "backend",
        "python",
        "-c",
        "import sys; from pathlib import Path; Path('/tmp/perf-manifest.json').write_text(sys.stdin.read())",
        input=json.dumps(manifest),
    )

    host = comprehensive.collect_host_metadata()
    return {
        "started_at": started_at,
        "startup": times,
        "manifest": manifest,
        "provisioning": {
            "route": "disposable_test_copy",
            "compose_file": "compose.integration.yaml",
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
        "source": comprehensive.collect_source_identity(ROOT),
        "generator": comprehensive.generator_identity(ROOT),
        "host": host,
        "software": _collect_software_versions(),
        "images": _collect_image_metadata(),
        # Retained fields for compatibility with existing reporting scripts.
        "platform": host["platform"],
        "cpu": host["machine"],
        "sha": comprehensive.collect_source_identity(ROOT)["head"],
    }


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
    paths = [
        "/dashboard",
        "/botanical-identities",
        "/seed-lots",
        "/sowings",
        "/plants",
        "/plant-groups",
        "/vegetative-lots",
        "/propagation-attempts",
        "/harvests",
        "/harvest-inventory",
        "/orders",
        "/suppliers",
        "/locations",
        "/geographic-places",
        "/provenance-sites",
        "/provenance-sites/map",
        "/events",
        "/history",
        "/schedule",
        "/media-assets",
        "/saved-views",
        "/explore/native-ranges/overview",
        "/explore/species-distribution/identities",
        "/explore/taxonomy/tree",
        "/search?q=Golden",
        f"/botanical-identities/{targets['identity']}",
        f"/botanical-identities/{targets['identity']}/collection",
        f"/botanical-identities/{targets['rich_identity']}/profile",
        f"/seed-lots/{targets['seed']}",
        f"/seed-lots/{targets['lineage_seed']}/lineage",
        f"/sowings/{targets['sowing']}",
        f"/sowings/{targets['sowing']}/germination",
        f"/plants/{targets['plant']}",
        f"/plants/{targets['plant']}/lineage",
        f"/plant-groups/{targets['group']}",
        f"/vegetative-lots/{targets['cutting_lot']}",
        f"/propagation-attempts/{targets['cutting_attempt']}",
        f"/harvests/{targets['harvest']}",
        f"/harvest-inventory/{targets['inventory']}",
        f"/orders/{targets['order']}",
        f"/suppliers/{targets['supplier']}",
        f"/locations/{targets['location']}",
        f"/provenance-sites/{targets['site']}",
        f"/collection-records/seed_lot/{targets['seed']}/photos",
        f"/media-assets/{targets['asset']}",
        f"/media-assets/{targets['asset']}/thumbnail",
        f"/collection-photos/local/{targets['photo_link']}/thumbnail",
        f"/attachments/{targets['attachment']}/content",
    ]
    results: dict[str, Any] = {}
    statements: dict[str, Any] = {}
    for path in paths:
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
        label = re.sub(r"[0-9a-f]{8}-[0-9a-f-]{27,}", "{id}", path)
        results[label] = {
            "first_ms": first,
            "median_ms": statistics.median(timings),
            "range_ms": [min(timings), max(timings)],
            "samples_ms": timings,
            "bytes": len(binary),
            "queries": sorted(set(counts)),
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
    return {
        "started_at": started_at,
        "completed_at": datetime.now(UTC).isoformat(),
        "manifest": manifest,
        "reads": results,
        "statements": statements,
        "create_edit_delete_ms": round((time.perf_counter() - begin) * 1000, 1),
        "resources": sample(),
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


def stop() -> dict[str, Any]:
    down_output = compose("down")
    remaining_containers = [
        line
        for line in subprocess.check_output(
            ["docker", "ps", "-aq", "--filter", f"label=com.docker.compose.project={PROJECT}"],
            text=True,
        ).splitlines()
        if line.strip()
    ]
    remaining_networks = [
        line
        for line in subprocess.check_output(
            [
                "docker",
                "network",
                "ls",
                "-q",
                "--filter",
                f"label=com.docker.compose.project={PROJECT}",
            ],
            text=True,
        ).splitlines()
        if line.strip()
    ]
    remaining_volumes = [
        line
        for line in subprocess.check_output(
            [
                "docker",
                "volume",
                "ls",
                "-q",
                "--filter",
                f"label=com.docker.compose.project={PROJECT}",
            ],
            text=True,
        ).splitlines()
        if line.strip()
    ]
    return {
        "project": PROJECT,
        "stopped_at": datetime.now(UTC).isoformat(),
        "compose_down_output": down_output.strip(),
        "containers_remaining": len(remaining_containers),
        "networks_remaining": len(remaining_networks),
        "volumes_remaining": len(remaining_volumes),
        "named_volumes_deleted": 0,
    }


def build_report(
    *,
    environment: dict[str, Any] | None = None,
    api_data: dict[str, Any] | None = None,
    transfer_data: dict[str, Any] | None = None,
    browser_data: dict[str, Any] | None = None,
    chunk_recovery: dict[str, Any] | None = None,
    cleanup_data: dict[str, Any] | None = None,
    profile_text: str | None = None,
    plans_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    combined: dict[str, Any] = {
        "schema_version": 2,
        "generated_at": datetime.now(UTC).isoformat(),
        "environment": environment,
        "api": api_data,
        "transfer": transfer_data,
        "browser": browser_data,
        "chunk_recovery": chunk_recovery,
        "cleanup": cleanup_data,
    }
    if profile_text is not None:
        combined["profile_summary"] = profile_text
    if plans_data is not None:
        combined["query_plans"] = plans_data
    combined["evaluation"] = comprehensive.evaluate_report(combined)
    return combined


def run_rehearsal(*, warmup_s: int = 20) -> dict[str, Any]:
    """Execute the end-to-end COMPREHENSIVE harness with guaranteed container cleanup."""
    env_data: dict[str, Any] | None = None
    api_data: dict[str, Any] | None = None
    transfer_data: dict[str, Any] | None = None
    browser_data: dict[str, Any] | None = None
    chunk_data: dict[str, Any] | None = None
    profile_text: str | None = None
    plans_data: dict[str, Any] | None = None
    cleanup_data: dict[str, Any] | None = None
    errors: list[str] = []

    with tempfile.TemporaryDirectory(prefix="florabase-perf-run-") as temporary:
        tmp = Path(temporary)
        env_path = tmp / "env.json"
        browser_path = tmp / "browser.json"
        chunk_path = tmp / "chunk.json"
        try:
            env_data = start()
            env_path.write_text(json.dumps(env_data, indent=2) + "\n", encoding="utf-8")
            if warmup_s > 0:
                time.sleep(warmup_s)
            api_data = api(env_path)
            transfer_data = transfer()
            subprocess.run(
                ["node", str(PERF_DIR / "browser.mjs"), str(env_path), str(browser_path)],
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
        except Exception as error:
            errors.append(f"{type(error).__name__}: {error}")
        finally:
            if compose("ps", "--all", "-q").strip():
                cleanup_data = stop()
            elif env_data is not None:
                cleanup_data = stop()

    report = build_report(
        environment=env_data,
        api_data=api_data,
        transfer_data=transfer_data,
        browser_data=browser_data,
        chunk_recovery=chunk_data,
        cleanup_data=cleanup_data,
        profile_text=profile_text,
        plans_data=plans_data,
    )
    report["warmup_s"] = warmup_s
    report["errors"] = errors
    return report


def _load_optional(path: Path | None) -> Any:
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=["start", "api", "sample", "transfer", "stop", "report", "run"],
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--env", type=Path)
    parser.add_argument("--api", type=Path)
    parser.add_argument("--transfer", type=Path)
    parser.add_argument("--browser", type=Path)
    parser.add_argument("--chunk", type=Path)
    parser.add_argument("--cleanup", type=Path)
    parser.add_argument("--plans", type=Path)
    parser.add_argument("--warmup-seconds", type=int, default=20)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Refusing to overwrite evidence; use a new output filename")

    if args.mode == "start":
        result = start()
    elif args.mode == "api":
        result = api(args.env)
    elif args.mode == "sample":
        result = sample()
    elif args.mode == "transfer":
        result = transfer()
    elif args.mode == "stop":
        result = stop()
    elif args.mode == "report":
        result = build_report(
            environment=_load_optional(args.env),
            api_data=_load_optional(args.api),
            transfer_data=_load_optional(args.transfer),
            browser_data=_load_optional(args.browser),
            chunk_recovery=_load_optional(args.chunk),
            cleanup_data=_load_optional(args.cleanup),
            plans_data=_load_optional(args.plans),
        )
    else:
        result = run_rehearsal(warmup_s=args.warmup_seconds)

    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"{args.mode}: {args.out}")
    if args.mode in {"run", "report"}:
        evaluation = result["evaluation"]
        if result.get("errors") or evaluation["invariant_status"] != "passed":
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
