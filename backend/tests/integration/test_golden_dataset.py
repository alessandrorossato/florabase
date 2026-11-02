"""TEST-DATA-001: deterministic, isolated golden copies inside disposable PostgreSQL only."""

import hashlib
import json
import os
import select
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
LOCKS = COPIES / ".locks"
BUSY = 75
BASELINE_MODIFIED = 3
# Runs the real CLI with one function paused at a known point, so no test depends on timing.
HARNESS = """
import sys
sys.path.insert(0, "/review")
import golden_dataset as g

target, skip = sys.argv[1], int(sys.argv[2])
sys.argv = ["golden_dataset.py", *sys.argv[3:]]

def pause():
    print("PAUSED", flush=True)
    sys.stdin.readline()

def paused(function):
    calls = [0]
    def wrapper(*args, **kwargs):
        if calls[0] == skip:
            pause()
        calls[0] += 1
        return function(*args, **kwargs)
    return wrapper

if target == "start":
    pause()
else:
    owner = {"rmtree": g.shutil, "run": g.subprocess}.get(target, g)
    setattr(owner, target, paused(getattr(owner, target)))
raise SystemExit(g.main())
"""


def run(*arguments: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, SCRIPT, *arguments],
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


def start(*arguments: str) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, SCRIPT, *arguments],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
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


def execute(name: str, statement: str, **parameters: Any) -> None:
    engine = create_engine(copy_url(name))
    try:
        with engine.begin() as connection:
            connection.execute(text(statement), parameters)
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
    # Independent copies retire independently, so this also exercises per-copy locking.
    retiring = {name: start("retire-copy", "--copy", name) for name in created}
    for name, process in retiring.items():
        _, error = process.communicate(timeout=300)
        assert process.returncode == 0, (name, error)
        assert not copy_exists(name)


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


def database_exists(name: str) -> bool:
    engine = create_engine(get_settings().database_url)
    try:
        with engine.connect() as connection:
            statement = text("SELECT count(*) FROM pg_database WHERE datname = :name")
            return bool(connection.scalar(statement, {"name": name}))
    finally:
        engine.dispose()


def copy_exists(name: str) -> bool:
    return database_exists(name) and (COPIES / name).is_dir()


class Holder:
    """A real CLI process stopped at a known point inside its action."""

    def __init__(self, target: str, skip: int, *arguments: str) -> None:
        self.process = subprocess.Popen(
            [sys.executable, "-c", HARNESS, target, str(skip), *arguments],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def wait_until_paused(self) -> None:
        assert self.process.stdout is not None
        ready, _, _ = select.select([self.process.stdout], [], [], 120)
        assert ready, "holder never reached its pause point"
        line = self.process.stdout.readline()
        assert line == "PAUSED\n", (line, self.process.stderr and self.process.stderr.read())

    def release(self) -> None:
        assert self.process.stdin is not None
        self.process.stdin.write("go\n")
        self.process.stdin.flush()

    def finish(self) -> tuple[int, str]:
        _, error = self.process.communicate(timeout=300)
        return self.process.returncode, error

    def kill(self) -> None:
        if self.process.poll() is None:
            self.process.kill()
            self.process.communicate()


def assert_loses(name: str, *actions: str) -> None:
    """Each losing action reports busy at once, whichever action currently holds the copy."""
    contenders = {action: start(action, "--copy", name) for action in actions}
    for action, process in contenders.items():
        _, error = process.communicate(timeout=300)
        assert process.returncode == BUSY, (action, error)
        assert "holds" in error


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


def test_coverage_shows_only_smoke_as_currently_executable() -> None:
    manifest = plan_module.load_manifest()
    assert {
        name for name, item in manifest["profiles"].items() if item["status"] == "implemented"
    } == {"smoke"}
    rows = {
        row.split(" | ")[1].strip("`"): [cell.strip() for cell in row.split(" | ")]
        for row in plan_module.coverage_markdown(manifest).splitlines()
        if row.startswith("| ") and "`" in row.split(" | ")[1]
    }
    assert len(rows) == len(manifest["scenarios"])
    for entry in manifest["scenarios"]:
        status, runnable, planned = rows[entry["id"]][2:5]
        assert status == entry["status"]
        if entry["status"] == "implemented":
            assert (runnable, planned) == ("smoke", "comprehensive, stress"), entry["id"]
        else:
            assert runnable == "—", entry["id"]
    # Planned scenarios stay visible, including the two that define the deferred profiles.
    assert rows["comprehensive-volume-mix"][2:5] == ["planned", "—", "comprehensive"]
    assert rows["stress-volume-mix"][2:5] == ["planned", "—", "stress"]
    assert sum(entry["status"] == "planned" for entry in manifest["scenarios"]) == 10


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


def test_digest_covers_every_table_and_all_media(first: str) -> None:
    digest = succeed("digest", "--copy", first)
    actual = query(
        first,
        """
        SELECT array_agg(tablename::text) FROM pg_tables
        WHERE schemaname = 'public' AND tablename <> 'alembic_version'
        """,
    )
    # Session state, plus the unmodelled constant written by the first migration.
    excluded = {"auth_sessions", "login_throttles", "app_metadata"}
    assert set(digest["tables"]) == set(actual) - excluded
    assert digest["unresolved_uuids"] == 0
    assert digest["tables"]["harvest_seed_lot_conversions"]["rows"] == 2
    assert digest["tables"]["operation_receipts"]["rows"] > 0
    assert digest["tables"]["external_provider_cache"]["rows"] == 1
    # Canonical geography is content too, not only the custom places.
    assert digest["tables"]["geographic_places"]["rows"] == query(
        first, "SELECT count(*) FROM geographic_places"
    )
    files = sorted(hashlib.sha256(path.read_bytes()).hexdigest() for path in objects(first))
    assert digest["media_files"] == len(files) > 0
    assert digest["media_sha256"] == hashlib.sha256("\n".join(files).encode()).hexdigest()


def test_fresh_copies_match_the_reviewed_baseline(first: str, second: str) -> None:
    for name in (first, second):
        result = run("verify-baseline", "--copy", name)
        assert result.returncode == 0, (
            f"{result.stdout}\n{result.stderr}\nA migration or plan change needs a reviewed "
            "update of profiles.smoke.expected.baseline in scripts/fixtures/golden/scenarios.json; "
            "compare "
            f"with: {run('digest', '--copy', name).stdout}"
        )
        assert json.loads(result.stdout)["state"] == "baseline-verified"


def test_baseline_detects_invariant_valid_modifications(copies: list[str]) -> None:
    """Notes, relationships, reference data and timestamps written in text are all content."""
    name = new_copy(copies, "golden_modified")
    succeed("generate", "--copy", name)
    assert run("verify-baseline", "--copy", name).returncode == 0
    reviewed = plan_module.load_manifest()["profiles"]["smoke"]["expected"]["baseline"]
    plant = query(name, "SELECT id FROM plants WHERE location_id IS NOT NULL ORDER BY id LIMIT 1")
    other = query(
        name,
        "SELECT id FROM locations WHERE id <> "
        f"(SELECT location_id FROM plants WHERE id = '{plant}') ORDER BY id LIMIT 1",
    )
    prune = query(name, "SELECT id FROM events WHERE kind = 'pruning' ORDER BY id LIMIT 1")
    seed = query(name, "SELECT id FROM seed_lots WHERE label = 'Golden — seed lost'")
    place = query(
        name, "SELECT id FROM geographic_places WHERE place_kind = 'canonical' ORDER BY id LIMIT 1"
    )
    changes = (
        ("seed_lots", "notes", seed, "changed note"),
        ("seed_lots", "notes", seed, "stored until 2031-01-01 10:00:00"),
        ("plants", "location_id", plant, other),
        ("events", "notes", prune, "changed note"),
        ("geographic_places", "name", place, "Changed place"),
    )
    for table, column, identifier, value in changes:
        original = query(name, f"SELECT {column} FROM {table} WHERE id = '{identifier}'")
        statement = f"UPDATE {table} SET {column} = :value WHERE id = '{identifier}'"
        execute(name, statement, value=value)
        # verify-baseline runs the same domain validation and reports the two results separately.
        result = run("verify-baseline", "--copy", name)
        assert result.returncode == BASELINE_MODIFIED, (table, result.stdout)
        report = json.loads(result.stdout)
        assert report["state"] == "invariant-valid-baseline-modified"
        assert report["domain_problems"] == []
        assert [line.split(":")[0] for line in report["baseline_differences"]] == [f"table {table}"]
        assert report["canonical_sha256"] != reviewed["canonical_sha256"]
        if table == "events":
            # A modified copy passes `validate`, which claims nothing about the baseline, and the
            # diagnostic digest still reports it.
            assert succeed("validate", "--copy", name)["baseline"] == "not-checked"
            current = succeed("digest", "--copy", name)
            assert current["baseline"] == "not-checked"
            assert current["canonical_sha256"] == report["canonical_sha256"]
        execute(name, statement, value=original)
    assert run("verify-baseline", "--copy", name).returncode == 0


def test_baseline_detects_media_modifications(copies: list[str]) -> None:
    name = new_copy(copies, "golden_media_changed")
    succeed("generate", "--copy", name)
    victim = objects(name)[0]
    original = victim.read_bytes()

    # The file alone: also invalid, and the report keeps the two findings apart.
    victim.write_bytes(original + b"x")
    result = run("verify-baseline", "--copy", name)
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["state"] == "domain-invalid"
    assert any("media differs" in problem for problem in report["domain_problems"])
    assert any(line.startswith("media_sha256") for line in report["baseline_differences"])
    assert succeed("digest", "--copy", name)["media_files"] == len(objects(name))

    # File and row replaced together: every invariant holds, only the baseline can tell.
    replaced = original + b"x"
    execute(
        name,
        "UPDATE attachments SET sha256 = :sha, byte_size = :size WHERE sha256 = :old",
        sha=hashlib.sha256(replaced).hexdigest(),
        size=len(replaced),
        old=hashlib.sha256(original).hexdigest(),
    )
    succeed("validate", "--copy", name)
    result = run("verify-baseline", "--copy", name)
    assert result.returncode == BASELINE_MODIFIED, result.stdout
    differences = json.loads(result.stdout)["baseline_differences"]
    assert any(line.startswith("media_sha256") for line in differences)
    assert any(line.startswith("table attachments") for line in differences)


def test_baseline_applies_only_to_its_reviewed_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = pytest.importorskip("golden_dataset", reason="available in integration runner only")
    manifest = plan_module.load_manifest()
    baseline = manifest["profiles"]["smoke"]["expected"]["baseline"]
    plan = plan_module.build_plan("smoke")
    current = {"schema_revision": baseline["schema_revision"]}
    assert baseline["volume"] == plan["volume"]
    assert baseline["plan_sha256"] == plan_module.plan_digest(plan)
    assert runtime.baseline_unavailable(plan, current) is None
    other_volume = plan_module.build_plan("smoke", volume=plan["volume"] + 1)
    assert "volume" in runtime.baseline_unavailable(other_volume, current)
    assert "schema" in runtime.baseline_unavailable(plan, {"schema_revision": "other"})
    del manifest["profiles"]["smoke"]["expected"]["baseline"]
    monkeypatch.setattr(plan_module, "load_manifest", lambda: manifest)
    assert "no reviewed baseline" in runtime.baseline_unavailable(plan, current)


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
    # The diagnostic digest keeps working on a copy validation rejects.
    assert succeed("digest", "--copy", name)["canonical_sha256"]
    assert json.loads(run("verify-baseline", "--copy", name).stdout)["state"] == "domain-invalid"

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


def test_retirement_cannot_remove_a_copy_during_generation(copies: list[str], first: str) -> None:
    name = new_copy(copies, "golden_generating")
    holder = Holder("apply_node", 20, "generate", "--copy", name)
    try:
        holder.wait_until_paused()
        assert_loses(name, "retire-copy", "create-copy", "generate", "validate", "digest")
        assert copy_exists(name)
        holder.release()
        code, error = holder.finish()
    finally:
        holder.kill()
    assert code == 0, error
    assert ledger(name)["state"] == "ready"
    assert (
        succeed("digest", "--copy", name)["canonical_sha256"]
        == succeed("digest", "--copy", first)["canonical_sha256"]
    )


def test_retirement_cannot_remove_a_copy_during_validation(first: str, second: str) -> None:
    holder = Holder("validate", 0, "validate", "--copy", first)
    try:
        holder.wait_until_paused()
        assert_loses(first, "retire-copy", "generate", "digest")
        assert copy_exists(first)
        # Another copy stays fully usable while this one is held.
        succeed("validate", "--copy", second)
        holder.release()
        code, error = holder.finish()
    finally:
        holder.kill()
    assert code == 0, error


def test_creation_and_retirement_are_exclusive_and_keep_one_lock(copies: list[str]) -> None:
    name = "golden_lifecycle"
    copies.append(name)
    creating = Holder("run", 0, "create-copy", "--copy", name)
    try:
        # Database created, Alembic not yet run: the most exposed moment of creation.
        creating.wait_until_paused()
        assert_loses(name, "retire-copy", "generate", "validate")
        creating.release()
        code, error = creating.finish()
    finally:
        creating.kill()
    assert code == 0, error
    assert copy_exists(name)
    lock = LOCKS / f"{name}.lock"
    inode = lock.stat().st_ino
    assert not list((COPIES / name).rglob("*.lock"))

    retiring = Holder("rmtree", 0, "retire-copy", "--copy", name)
    try:
        # Database dropped, media still present: the split a lock inside the root could not cover.
        retiring.wait_until_paused()
        assert (COPIES / name).is_dir()
        assert_loses(name, "create-copy", "generate", "validate", "digest", "retire-copy")
        retiring.release()
        code, error = retiring.finish()
    finally:
        retiring.kill()
    assert code == 0, error
    assert not copy_exists(name)
    assert not (COPIES / name).exists()
    assert lock.stat().st_ino == inode

    # Losing to a finished retirement is an ordinary refusal; the same name can then be reused.
    late = run("validate", "--copy", name)
    assert late.returncode == 1
    assert "media root is missing" in late.stderr
    succeed("create-copy", "--copy", name)
    assert lock.stat().st_ino == inode


def test_a_killed_holder_never_blocks_the_copy(copies: list[str]) -> None:
    name = new_copy(copies, "golden_crashed")
    holder = Holder("apply_node", 5, "generate", "--copy", name)
    try:
        holder.wait_until_paused()
        assert run("retire-copy", "--copy", name).returncode == BUSY
    finally:
        holder.kill()
    succeed("retire-copy", "--copy", name)
    assert not copy_exists(name)


def test_simultaneous_lifecycle_actions_never_tear_a_copy(copies: list[str]) -> None:
    name = "golden_race"
    copies.append(name)
    creators = [Holder("start", 0, "create-copy", "--copy", name) for _ in range(4)]
    try:
        for holder in creators:
            holder.wait_until_paused()
        for holder in creators:
            holder.release()
        codes = [holder.finish()[0] for holder in creators]
    finally:
        for holder in creators:
            holder.kill()
    # Whoever arrives after the winner finished is refused because the copy already exists.
    assert codes.count(0) == 1, codes
    assert set(codes) <= {0, 1, BUSY}, codes
    assert copy_exists(name)

    racers = [
        Holder("start", 0, action, "--copy", name)
        for action in ("generate", "retire-copy", "validate", "digest")
    ]
    try:
        for holder in racers:
            holder.wait_until_paused()
        for holder in racers:
            holder.release()
        results = [holder.finish() for holder in racers]
    finally:
        for holder in racers:
            holder.kill()
    retired = results[1][0] == 0
    # Either order is legitimate; a database without media, or the reverse, never is.
    assert database_exists(name) != retired, results
    assert (COPIES / name).is_dir() != retired, results
    for code, _ in results:
        assert code in {0, 1, BUSY}, results


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
    assert (
        run("retire-copy", "--copy", name, env={"FLORABASE_WORKFLOW_MODE": "review"}).returncode
        == 1
    )
    assert copy_exists(name)
    # A refused name never reaches the lock directory, even with a traversal attempt.
    assert run("validate", "--copy", "golden_../../etc").returncode == 1
    assert all(path.name.startswith("golden_") for path in LOCKS.iterdir())

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
