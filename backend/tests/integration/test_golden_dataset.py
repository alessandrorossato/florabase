"""TEST-DATA-001: deterministic, isolated golden copies inside disposable PostgreSQL only."""

import fcntl
import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from florabase.core.config import Environment, get_settings

sys.path.insert(0, "/review")
plan_module = pytest.importorskip("golden_plan", reason="available in integration runner only")
pytestmark = pytest.mark.integration
SCRIPT = "/review/golden_dataset.py"
COPIES = Path("/tmp/florabase-golden")


def run(*arguments: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, SCRIPT, *arguments],
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


def succeed(*arguments: str, env: dict[str, str] | None = None) -> dict[str, Any]:
    result = run(*arguments, env=env)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout) if result.stdout else {}


def copy_url(name: str) -> str:
    url = make_url(get_settings().database_url).set(database=name)
    return url.render_as_string(hide_password=False)


def query(name: str, statement: str) -> Any:
    engine = create_engine(copy_url(name))
    try:
        with engine.connect() as connection:
            return connection.scalar(text(statement))
    finally:
        engine.dispose()


def execute(name: str, statement: str) -> None:
    engine = create_engine(copy_url(name))
    try:
        with engine.begin() as connection:
            connection.execute(text(statement))
    finally:
        engine.dispose()


def ledger(name: str) -> dict[str, Any]:
    value: dict[str, Any] = json.loads((COPIES / name / ".golden-dataset.json").read_text())
    return value


def objects(name: str) -> list[Path]:
    root = COPIES / name
    return sorted(path for path in root.rglob("*") if path.is_file() and "objects" in path.parts)


@pytest.fixture(scope="module")
def copies() -> Iterator[list[str]]:
    created: list[str] = []
    yield created
    for name in created:
        succeed("retire-copy", "--copy", name)
        assert not (COPIES / name).exists()


def new_copy(copies: list[str], name: str) -> str:
    succeed("create-copy", "--copy", name)
    copies.append(name)
    return name


@pytest.fixture(scope="module")
def first(copies: list[str]) -> str:
    name = new_copy(copies, "golden_first")
    succeed("generate", "--copy", name, env={"PYTHONHASHSEED": "1", "TZ": "UTC"})
    return name


@pytest.fixture(scope="module")
def second(copies: list[str]) -> str:
    name = new_copy(copies, "golden_second")
    succeed("generate", "--copy", name, env={"PYTHONHASHSEED": "2", "TZ": "Asia/Tokyo"})
    return name


def test_plan_is_deterministic_and_pinned() -> None:
    manifest = plan_module.load_manifest()
    digest = plan_module.plan_digest(plan_module.build_plan("smoke"))
    assert digest == plan_module.plan_digest(plan_module.build_plan("smoke"))
    assert digest == manifest["profiles"]["smoke"]["expected"]["plan_sha256"]
    for seed in ("1", "2"):
        output = subprocess.run(
            [sys.executable, "/review/golden_plan.py", "summary"],
            env={**os.environ, "PYTHONHASHSEED": seed},
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert json.loads(output)["plan_sha256"] == digest


def test_scenario_randomness_is_independent_of_other_scenarios() -> None:
    manifest = plan_module.load_manifest()
    full = plan_module.build_plan("smoke", manifest=manifest)
    manifest["scenarios"] = [
        entry for entry in manifest["scenarios"] if entry["id"] != "media-references"
    ]
    reduced = plan_module.build_plan("smoke", manifest=manifest)
    volume = [node for node in full["nodes"] if node["scenario"] == "volume-background"]
    assert volume
    assert volume == [node for node in reduced["nodes"] if node["scenario"] == "volume-background"]


def test_manifest_contract_and_generated_coverage() -> None:
    manifest = plan_module.load_manifest()
    identifiers = [entry["id"] for entry in manifest["scenarios"]]
    assert len(identifiers) == len(set(identifiers))
    implemented = {e["id"] for e in manifest["scenarios"] if e["status"] == "implemented"}
    assert implemented == set(plan_module.SCENARIOS)
    keys = {node["key"] for node in plan_module.build_plan("smoke")["nodes"]}
    for entry in manifest["scenarios"]:
        assert entry["covers"], entry["id"]
        assert entry["status"] in {"implemented", "planned"}
        for invariant in entry["invariants"]:
            assert invariant["key"] in keys, invariant
            assert invariant.get("equals_ref", invariant["key"]) in keys, invariant
    assert plan_module.COVERAGE.read_text() == plan_module.coverage_markdown(manifest)


@pytest.mark.parametrize("profile", ["comprehensive", "stress", "unknown"])
def test_unimplemented_profiles_refuse(profile: str) -> None:
    with pytest.raises(plan_module.PlanError):
        plan_module.build_plan(profile)


def test_independent_copies_have_identical_logical_content(first: str, second: str) -> None:
    left, right = (succeed("digest", "--copy", name) for name in (first, second))
    assert left["canonical_sha256"] == right["canonical_sha256"], {
        table: (left["tables"][table], right["tables"][table])
        for table in left["tables"]
        if left["tables"][table] != right["tables"][table]
    }
    assert left["schema_revision"] == right["schema_revision"]
    # Stable identifiers are scenario keys; database ids stay genuine, per-copy UUIDv7 values.
    left_records, right_records = ledger(first)["records"], ledger(second)["records"]
    assert set(left_records) == set(right_records)
    key = "seed:seed-quantity-states/unknown"
    assert left_records[key] != right_records[key]
    assert [path.read_bytes() for path in objects(first)] != []
    assert sorted(path.read_bytes() for path in objects(first)) == sorted(
        path.read_bytes() for path in objects(second)
    )


def test_digest_covers_every_table_and_is_sensitive_to_content(
    copies: list[str], first: str
) -> None:
    digest = succeed("digest", "--copy", first)
    actual = query(
        first,
        """
        SELECT array_agg(tablename::text) FROM pg_tables
        WHERE schemaname = 'public' AND tablename <> 'alembic_version'
        """,
    )
    # Secrets, session and cache state, plus the unmodelled constant written by the first migration.
    excluded = {"auth_sessions", "login_throttles", "external_provider_cache", "app_metadata"}
    assert set(digest["tables"]) == set(actual) - excluded
    assert digest["unresolved_uuids"] == 0
    assert digest["tables"]["harvest_seed_lot_conversions"]["rows"] == 2
    assert digest["tables"]["operation_receipts"]["rows"] > 0

    name = new_copy(copies, "golden_sensitive")
    succeed("generate", "--copy", name)
    before = succeed("digest", "--copy", name)
    assert before["canonical_sha256"] == digest["canonical_sha256"]
    changes = {
        "seed_lots": "UPDATE seed_lots SET notes = 'changed' WHERE label = 'Golden — seed lost'",
        "plants": "UPDATE plants SET location_id = NULL WHERE location_id IS NOT NULL",
        "events": "UPDATE events SET notes = 'changed' WHERE kind = 'pruning'",
    }
    for statement in changes.values():
        execute(name, statement)
    after = succeed("digest", "--copy", name)
    assert after["canonical_sha256"] != before["canonical_sha256"]
    changed = {
        table for table in before["tables"] if before["tables"][table] != after["tables"][table]
    }
    assert changed == set(changes)


def test_repeat_generation_is_idempotent(first: str) -> None:
    fingerprint = (
        "SELECT md5(row::text) FROM "
        "(SELECT count(*), max(created_at), max(updated_at) FROM seed_lots) AS row"
    )
    before, ledger_before = query(first, fingerprint), ledger(first)
    succeed("generate", "--copy", first)
    assert query(first, fingerprint) == before
    assert ledger(first) == ledger_before


def test_validation_detects_damage_only_in_the_damaged_copy(copies: list[str], second: str) -> None:
    name = new_copy(copies, "golden_damaged")
    succeed("generate", "--copy", name)
    succeed("validate", "--copy", name)

    stray = COPIES / name / "objects" / "stray"
    stray.write_bytes(b"unmanaged")
    failed = run("validate", "--copy", name)
    assert failed.returncode == 1
    assert "unmanaged media file" in failed.stderr
    stray.unlink()

    victim = objects(name)[0]
    original = victim.read_bytes()
    victim.write_bytes(original + b"x")
    failed = run("validate", "--copy", name)
    assert failed.returncode == 1
    assert "media differs" in failed.stderr
    victim.unlink()
    failed = run("validate", "--copy", name)
    assert failed.returncode == 1
    assert "media missing" in failed.stderr
    victim.write_bytes(original)
    succeed("validate", "--copy", name)

    key = ledger(name)["records"]["seed:seed-quantity-states/unknown"]
    execute(name, f"UPDATE seed_lots SET label = 'Real looking label' WHERE id = '{key}'")
    failed = run("validate", "--copy", name)
    assert failed.returncode == 1
    assert "not marked synthetic" in failed.stderr
    execute(
        name,
        "UPDATE seed_lots SET quantity_kind = 'seed_count', quantity_value = 5, "
        f"quantity_is_approximate = false WHERE id = '{key}'",
    )
    failed = run("validate", "--copy", name)
    assert failed.returncode == 1
    assert "quantity_value: expected null" in failed.stderr
    execute(name, f"DELETE FROM seed_lots WHERE id = '{key}'")
    failed = run("validate", "--copy", name)
    assert failed.returncode == 1
    assert "managed record missing" in failed.stderr

    # The independently generated neighbour shares neither rows nor files.
    succeed("validate", "--copy", second)


def test_failed_generation_leaves_nothing_and_can_retry(copies: list[str], first: str) -> None:
    name = new_copy(copies, "golden_failure")
    for position in ("150", "0"):
        failed = run("generate", "--copy", name, "--fail-after", position)
        assert failed.returncode == 1
        assert "Injected failure" in failed.stderr
        state = ledger(name)
        assert (state["state"], state["clean"], state["records"]) == ("failed", True, {})
        assert query(name, "SELECT count(*) FROM users") == 0
        assert query(name, "SELECT count(*) FROM seed_lots") == 0
        assert query(name, "SELECT count(*) FROM attachments") == 0
        assert objects(name) == []
    succeed("generate", "--copy", name)
    assert (
        succeed("digest", "--copy", name)["canonical_sha256"]
        == succeed("digest", "--copy", first)["canonical_sha256"]
    )


def test_failure_after_commit_is_never_reported_as_ready(copies: list[str]) -> None:
    name = new_copy(copies, "golden_prepared")
    graph = sum(
        node["kind"] not in {"primary", "external_cover"}
        for node in plan_module.build_plan("smoke")["nodes"]
    )
    failed = run("generate", "--copy", name, "--fail-after", str(graph))
    assert failed.returncode == 1
    assert "after the graph committed" in failed.stderr
    state = ledger(name)
    assert (state["state"], state["clean"]) == ("failed", False)
    assert query(name, "SELECT count(*) FROM users") == 1
    assert run("validate", "--copy", name).returncode == 1
    retried = run("generate", "--copy", name)
    assert retried.returncode == 1
    assert "retire it instead of repairing" in retried.stderr


def test_concurrent_action_on_a_copy_is_refused(copies: list[str]) -> None:
    name = new_copy(copies, "golden_locked")
    with (COPIES / name / ".golden-dataset.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        result = run("generate", "--copy", name)
    assert result.returncode == 1
    assert "holds this copy" in result.stderr
    assert query(name, "SELECT count(*) FROM users") == 0


def test_network_access_fails_the_run() -> None:
    probe = (
        "import sys, httpx, socket; sys.path.insert(0, '/review'); import golden_dataset as g\n"
        "g.deny_network()\n"
        "for attempt in (lambda: httpx.get('https://example.invalid/'),\n"
        "                lambda: socket.create_connection(('example.invalid', 443))):\n"
        "    try:\n"
        "        attempt()\n"
        "    except g.GoldenError:\n"
        "        continue\n"
        "    raise SystemExit('network was reachable')\n"
    )
    subprocess.run([sys.executable, "-c", probe], check=True, timeout=60)


def test_generation_refuses_any_other_target(
    copies: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    name = new_copy(copies, "golden_guard")
    runtime = pytest.importorskip("golden_dataset", reason="available in integration runner only")
    monkeypatch.chdir("/app")
    settings = get_settings().model_copy(
        update={"database_url": copy_url(name), "attachment_storage_root": COPIES / name}
    )
    engine = create_engine(copy_url(name))
    try:
        with Session(engine) as database:
            assert runtime.require_target(settings, database) == COPIES / name
            for update in (
                {"database_disposable": False},
                {"environment": Environment.DEVELOPMENT},
                {"attachment_storage_root": Path("/var/lib/florabase/attachments")},
                {"attachment_storage_root": COPIES / "golden_other"},
                {"database_url": get_settings().database_url},
                {"database_url": copy_url("florabase_review")},
                {"database_url": copy_url("florabase")},
                {
                    "database_url": copy_url("golden_other"),
                    "attachment_storage_root": COPIES / "golden_other",
                },
            ):
                with pytest.raises(runtime.GoldenError):
                    runtime.require_target(settings.model_copy(update=update), database)
            for mode in ("review", "uat", "sourcing"):
                with monkeypatch.context() as patch:
                    patch.setenv("FLORABASE_WORKFLOW_MODE", mode)
                    with pytest.raises(runtime.GoldenError):
                        runtime.require_target(settings, database)
    finally:
        engine.dispose()
    target = {
        "FLORABASE_DATABASE_URL": copy_url(name),
        "FLORABASE_ATTACHMENT_STORAGE_ROOT": str(COPIES / name),
    }
    for override in (
        {"FLORABASE_DATABASE_URL": get_settings().database_url},
        {"FLORABASE_WORKFLOW_MODE": "review"},
    ):
        assert run("generate", env={**target, **override}).returncode == 1, override
    assert query(name, "SELECT count(*) FROM users") == 0
    assert run("retire-copy", "--copy", "florabase_review").returncode == 1
    assert run("create-copy", "--copy", "florabase").returncode == 1

    # A populated collection and foreign media are never adopted.
    execute(
        name,
        "INSERT INTO locations (id, name, created_at, updated_at) "
        "VALUES (gen_random_uuid(), 'Foreign', now(), now())",
    )
    result = run("generate", env=target)
    assert result.returncode == 1
    assert "no data changed" in result.stderr
    execute(name, "DELETE FROM locations")
    (COPIES / name / "foreign").write_bytes(b"foreign")
    result = run("generate", env=target)
    assert result.returncode == 1
    assert "not empty" in result.stderr
    (COPIES / name / "foreign").unlink()


def test_stale_schema_is_refused(copies: list[str]) -> None:
    name = new_copy(copies, "golden_stale")
    execute(name, "UPDATE alembic_version SET version_num = '20200101_0001'")
    result = run("generate", "--copy", name)
    assert result.returncode == 1
    assert "not code head" in result.stderr
