#!/usr/bin/env python3
"""Small PERF-001 controller. Requires Docker; owns only florabase-perf containers."""

import argparse
import gzip
import http.cookiejar
import json
import platform
import re
import statistics
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "scripts/perf/compose.sh"
ORIGIN = "http://localhost:18080"


def compose(*args: str, input: str | None = None) -> str:
    return subprocess.check_output([str(COMPOSE), *args], input=input, text=True)


def sql(query: str) -> str:
    return compose(
        "exec",
        "-T",
        "db",
        "psql",
        "-U",
        "florabase_perf",
        "-d",
        "florabase_perf",
        "-qAt",
        "-c",
        query,
    ).strip()


def sample() -> dict[str, object]:
    return {
        "at": round(time.time(), 1),
        "containers": [
            json.loads(line)
            for line in subprocess.check_output(
                [
                    "docker",
                    "stats",
                    "--no-stream",
                    "--format",
                    "{{json .}}",
                    "florabase-perf-backend-1",
                    "florabase-perf-frontend-1",
                    "florabase-perf-db-1",
                ],
                text=True,
            ).splitlines()
        ],
        "connections": json.loads(
            sql(
                "SELECT json_build_object('total', count(*), 'idle', "
                "count(*) FILTER (WHERE state='idle')) FROM pg_stat_activity "
                "WHERE datname='florabase_perf' AND pid<>pg_backend_pid()"
            )
        ),
        "sessions": json.loads(
            sql(
                "SELECT json_build_object('count',count(*),'last_seen_at',"
                "max(last_seen_at),'idle_expires_at',max(idle_expires_at)) "
                "FROM auth_sessions WHERE revoked_at IS NULL"
            )
        ),
        "load": Path("/proc/loadavg").read_text().strip(),
    }


def start() -> dict[str, object]:
    config = json.loads(compose("config", "--format", "json"))
    for name in ("db", "backend"):
        service = config["services"][name]
        if service.get("volumes") or not service.get("tmpfs") or service.get("ports"):
            raise RuntimeError("PERF isolation guard failed")
    if config["name"] != "florabase-perf":
        raise RuntimeError("Unexpected project")
    if compose("ps", "--all", "-q").strip():
        raise RuntimeError(
            "PERF containers already exist; stop only PERF project first"
        )
    times = {}
    begin = time.monotonic()
    compose("up", "-d", "--wait", "db")
    times["database_health_s"] = round(time.monotonic() - begin, 1)
    sql("CREATE EXTENSION pg_stat_statements")
    begin = time.monotonic()
    compose("run", "--rm", "backend", "alembic", "upgrade", "head")
    times["migration_s"] = round(time.monotonic() - begin, 1)
    begin = time.monotonic()
    compose("up", "-d", "--wait", "backend", "frontend")
    times["application_health_s"] = round(time.monotonic() - begin, 1)
    begin = time.monotonic()
    raw = compose(
        "exec",
        "-T",
        "backend",
        "python",
        "-",
        input=(ROOT / "scripts/perf/fixture.py").read_text(),
    )
    manifest = json.loads(raw)
    times["fixture_s"] = round(time.monotonic() - begin, 1)
    sql("ANALYZE")
    return {
        "startup": times,
        "manifest": manifest,
        "platform": platform.platform(),
        "cpu": platform.machine(),
        "host": subprocess.check_output(
            ["docker", "info", "--format", "{{.NCPU}} CPUs; {{.MemTotal}} bytes RAM"],
            text=True,
        ).strip(),
        "sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "images": subprocess.check_output(
            [
                "docker",
                "image",
                "inspect",
                "florabase-perf-backend",
                "florabase-perf-frontend",
                "postgres:18.6-alpine",
                "--format",
                "{{.RepoTags}} {{.Size}}",
            ],
            text=True,
        ).splitlines(),
    }


def api() -> dict[str, object]:
    manifest = json.loads(
        compose("exec", "-T", "backend", "cat", "/tmp/perf-manifest.json")
    )
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
        {"login_name": "perf-owner", "password": "disposable-perf-owner-password"},
    )
    csrf = json.loads(login)["csrf_token"]
    paths = [
        "/dashboard",
        "/botanical-identities",
        "/seed-lots",
        "/sowings",
        "/plants",
        "/plant-groups",
        "/suppliers",
        "/locations",
        "/geographic-places",
        "/provenance-sites",
        "/events",
        "/provenance-sites/map",
        "/search?q=Perfplant",
    ]
    for kind, key in [
        ("botanical-identities", "identity"),
        ("seed-lots", "seed"),
        ("sowings", "sowing"),
        ("plants", "plant"),
        ("plant-groups", "group"),
        ("suppliers", "supplier"),
        ("locations", "location"),
        ("provenance-sites", "site"),
    ]:
        paths.append(f"/{kind}/{manifest[key]}")
    paths += [
        f"/botanical-identities/{manifest['identity']}/collection",
        f"/botanical-identities/{manifest['identity']}/profile",
        f"/sowings/{manifest['sowing']}/germination",
        f"/seed-lots/{manifest['seed']}/lineage",
        f"/collection-records/seed_lot/{manifest['seed']}/photos",
        f"/collection-photos/local/{manifest['photo']}/thumbnail",
        f"/attachments/{manifest['attachment']}/content",
    ]
    results = {}
    statements = {}
    for path in paths:
        first, binary = request(path)
        request(path)
        timings, counts = [], []
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
            "bytes": len(binary),
            "queries": sorted(set(counts)),
        }
        statements[label] = rows
    sql("SELECT pg_stat_statements_reset()")
    begin = time.perf_counter()
    _, created = request(
        "/botanical-identities", "POST", {"scientific_name": "Perf temporary"}, csrf
    )
    supplier_id = json.loads(created)["id"]
    request(
        f"/botanical-identities/{supplier_id}",
        "PUT",
        {"scientific_name": "Perf edited"},
        csrf,
    )
    request(f"/botanical-identities/{supplier_id}", "DELETE", csrf=csrf)
    return {
        "manifest": manifest,
        "reads": results,
        "statements": statements,
        "create_edit_delete_ms": round((time.perf_counter() - begin) * 1000, 1),
        "resources": sample(),
    }


def transfer() -> dict[str, object]:
    """Check static compression and protected integrity without timing budgets."""
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )

    def read(
        path: str, encoding: str
    ) -> tuple[bytes, str | None, str | None, str | None, str | None]:
        req = urllib.request.Request(
            ORIGIN + path, headers={"Accept-Encoding": encoding}
        )
        with opener.open(req, timeout=30) as response:
            return (
                response.read(),
                response.headers.get("Content-Encoding"),
                response.headers.get("Vary"),
                response.headers.get("Content-Type"),
                response.headers.get("Cache-Control"),
            )

    html, _, _, _, _ = read("/", "identity")
    assets = re.findall(
        r'(?:src|href)="(/assets/index-[^"]+\.(?:js|css))"', html.decode()
    )
    assert len(assets) == 2, "Expected production entry JS and CSS"
    result = {}
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
    runtime_config, config_encoding, _, _, cache_control = read(
        "/runtime-config.js", "gzip"
    )
    assert config_encoding is None and cache_control == "no-store"
    health, health_encoding, _, health_type, _ = read("/healthz", "gzip")
    assert health == b"ok\n" and health_encoding is None and health_type == "text/plain"
    login = urllib.request.Request(
        ORIGIN + "/api/v1/auth/login",
        data=json.dumps(
            {"login_name": "perf-owner", "password": "disposable-perf-owner-password"}
        ).encode(),
        headers={"Content-Type": "application/json", "Origin": ORIGIN},
    )
    with opener.open(login, timeout=30) as response:
        response.read()
    raw, raw_encoding, _, raw_type, _ = read("/api/v1/events", "identity")
    candidate, encoding, _, content_type, _ = read("/api/v1/events", "gzip")
    assert raw_encoding is None and content_type == raw_type
    assert encoding is None and raw == candidate, (
        "Protected API compression/representation changed"
    )
    return {
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["start", "api", "sample", "transfer", "stop"])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Refusing to overwrite evidence; use a new output filename")
    if args.mode == "start":
        result = start()
    elif args.mode == "api":
        result = api()
    elif args.mode == "sample":
        result = sample()
    elif args.mode == "transfer":
        result = transfer()
    else:
        result = {"cleanup": compose("down")}
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"{args.mode}: {args.out}")
