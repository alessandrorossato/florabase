"""TEST-DATA-002: the COMPREHENSIVE golden profile; manual, so it costs CI nothing by default."""

import json
import os
import select
import subprocess
import sys
import time
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from florabase.core.config import get_settings

sys.path.insert(0, "/review")
plan_module = pytest.importorskip("golden_plan", reason="available in integration runner only")
pytestmark = pytest.mark.integration
SCRIPT = "/review/golden_dataset.py"
COPIES = Path("/tmp/florabase-golden")
PROFILE = ("--profile", "comprehensive")
BUSY = 75
BASELINE_MODIFIED = 3
WALL_CLOCK_COLUMNS = {("app_metadata", "created_at")}
TIMINGS: dict[str, float] = {}
GENERATION: dict[str, Any] = {}
# Support rows produced by a domain record, not records anyone would count.
NOT_DOMAIN_RECORDS = {"application_settings", "users", "external_provider_cache"}
SEARCH_PATH = "test_golden_comprehensive"
HOLD_VALIDATION = """
import sys
sys.path.insert(0, "/review")
import golden_dataset as g

validate = g.validate
def paused(*args, **kwargs):
    print("PAUSED", flush=True)
    sys.stdin.readline()
    return validate(*args, **kwargs)
g.validate = paused
sys.argv = ["golden_dataset.py", *sys.argv[1:]]
raise SystemExit(g.main())
"""


def run(*arguments: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, SCRIPT, *arguments],
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )


def succeed(*arguments: str, env: dict[str, str] | None = None) -> dict[str, Any]:
    result = run(*arguments, env=env)
    assert result.returncode == 0, result.stderr or result.stdout
    return json.loads(result.stdout) if result.stdout else {}


def timed(label: str, *arguments: str, env: dict[str, str] | None = None) -> dict[str, Any]:
    """Wall time of the real CLI process, including its application import."""
    started = time.monotonic()
    value = succeed(*arguments, env=env)
    TIMINGS[label] = round(time.monotonic() - started, 2)
    return value


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


def verify(name: str) -> tuple[int, dict[str, Any]]:
    result = run("verify-baseline", "--copy", name, *PROFILE)
    return result.returncode, json.loads(result.stdout)


def expected() -> dict[str, Any]:
    value: dict[str, Any] = plan_module.load_manifest()["profiles"]["comprehensive"]["expected"]
    return value


@pytest.fixture(scope="module", autouse=True)
def explicitly_selected(request: pytest.FixtureRequest) -> None:
    """Only `make golden-dataset-comprehensive-check` names this file; the full suite skips it."""
    arguments = request.config.invocation_params.args
    if not any(SEARCH_PATH in str(argument) for argument in arguments):
        pytest.skip("COMPREHENSIVE runs only when this module is selected explicitly")


@pytest.fixture(scope="module")
def copies(explicitly_selected: None) -> Iterator[list[str]]:
    created: list[str] = []
    yield created
    for name in created:
        succeed("retire-copy", "--copy", name)
        assert not (COPIES / name).exists()


@pytest.fixture(scope="module")
def first(copies: list[str]) -> str:
    name = "golden_compr_first"
    timed("create-copy", "create-copy", "--copy", name)
    copies.append(name)
    GENERATION.update(
        timed(
            "generate-and-validate",
            "generate",
            "--copy",
            name,
            *PROFILE,
            env={"PYTHONHASHSEED": "1", "TZ": "UTC"},
        )
    )
    return name


@pytest.fixture(scope="module")
def second(copies: list[str]) -> str:
    """The only other full generation: the independent copy that negatives may damage."""
    name = "golden_compr_second"
    succeed("create-copy", "--copy", name)
    copies.append(name)
    succeed("generate", "--copy", name, *PROFILE, env={"PYTHONHASHSEED": "2", "TZ": "Asia/Tokyo"})
    return name


def test_independent_copies_have_identical_logical_content(first: str, second: str) -> None:
    left = timed("digest", "digest", "--copy", first)
    right = succeed("digest", "--copy", second)
    assert left["canonical_sha256"] == right["canonical_sha256"], {
        table: (left["tables"][table], right["tables"][table])
        for table in left["tables"]
        if left["tables"][table] != right["tables"][table]
    }
    assert left["unresolved_uuids"] == right["unresolved_uuids"] == 0
    # Stable identifiers are scenario keys; database ids stay genuine, per-copy UUIDv7 values.
    left_records, right_records = ledger(first)["records"], ledger(second)["records"]
    assert set(left_records) == set(right_records)
    key = "seed:seed-collection-produced/from-plant"
    assert left_records[key] != right_records[key]
    assert left["media_files"] == right["media_files"] > 0


def test_fresh_copies_match_the_independently_pinned_baseline(first: str, second: str) -> None:
    started = time.monotonic()
    code, report = verify(first)
    TIMINGS["verify-baseline"] = round(time.monotonic() - started, 2)
    assert code == 0, (
        f"{report}\nA migration or plan change needs a reviewed update of "
        "profiles.comprehensive.expected in scripts/fixtures/golden/scenarios.json"
    )
    assert report["state"] == "baseline-verified"
    assert report["canonical_sha256"] == expected()["baseline"]["canonical_sha256"]
    code, report = verify(second)
    assert (code, report["state"]) == (0, "baseline-verified")


def test_record_count_is_within_the_reviewed_target(first: str) -> None:
    timed("validate", "validate", "--copy", first, *PROFILE)
    counts = expected()["tables"]
    domain = sum(count for table, count in counts.items() if table not in NOT_DOMAIN_RECORDS)
    assert 3000 <= domain <= 5000, domain
    # Volume must not come from one table: each of these is a separately reviewed domain area.
    for table, least in {
        "botanical_identities": 100,
        "suppliers": 20,
        "orders": 40,
        "seed_lots": 300,
        "sowings": 300,
        "germination_observations": 100,
        "plants": 100,
        "plant_groups": 50,
        "events": 300,
        "harvests": 30,
        "harvest_material_inventory": 20,
        "harvest_seed_lot_conversions": 5,
        "locations": 20,
        "geographic_places": 5,
        "provenance_sites": 15,
        "scheduled_activities": 30,
        "saved_views": 15,
        "media_assets": 25,
        "record_media_links": 25,
        "wfo_links": 5,
        "wcvp_links": 3,
        "native_range_proposals": 2,
        "native_range_applications": 1,
        "external_taxon_links": 3,
    }.items():
        assert counts[table] >= least, table


def test_semantic_coverage_reaches_every_domain_state(first: str) -> None:
    """States a raw row count cannot prove, each read from the database, not the plan."""
    states = (
        "SELECT array_agg(DISTINCT lifecycle::text) FROM {table}",
        {
            "seed_lots": {"active", "exhausted", "discarded", "lost"},
            "sowings": {"active", "completed", "failed", "abandoned"},
            "plants": {
                "active",
                "reversed",
                "reintegrated",
                "transferred",
                "dead",
                "lost",
                "discarded",
            },
            "plant_groups": {"active", "transferred", "completed", "dead", "lost", "discarded"},
        },
    )
    for table, wanted in states[1].items():
        found = set(query(first, states[0].format(table=table)))
        assert wanted <= found, (table, wanted - found)
    events = set(query(first, "SELECT array_agg(DISTINCT kind::text) FROM events"))
    assert events >= {
        "observation", "movement", "repotting", "flowering", "fruiting", "pruning", "treatment",
        "harvest", "extraction", "reintegration", "transfer", "death", "loss", "discarded", "other",
    }, events  # fmt: skip
    materials = set(
        query(first, "SELECT array_agg(DISTINCT material_kind::text) FROM harvest_items")
    )
    assert materials == {
        "fruit", "flower", "leaf", "root", "seed", "stem_or_shoot", "whole_plant", "other",
    }, materials  # fmt: skip
    kinds = set(
        query(first, "SELECT array_agg(DISTINCT kind::text) FROM harvest_material_dispositions")
    )
    assert kinds >= {"consumed", "processed", "discarded", "gifted", "used_for_propagation"}, kinds
    surfaces = set(query(first, "SELECT array_agg(DISTINCT surface::text) FROM saved_views"))
    assert len(surfaces) == 17, surfaces
    sources = set(query(first, "SELECT array_agg(DISTINCT source_kind::text) FROM seed_lots"))
    assert sources == {
        "purchased", "purchased_fruit", "self_collected", "collection_produced",
        "gift_exchange", "other", "unknown",
    }, sources  # fmt: skip
    for statement in (
        "SELECT count(*) FROM locations WHERE retired_at IS NOT NULL",
        "SELECT count(*) FROM suppliers WHERE retired_at IS NOT NULL",
        "SELECT count(*) FROM geographic_places WHERE retired_at IS NOT NULL",
        "SELECT count(*) FROM external_taxon_links WHERE taxonomic_status = 'SYNONYM'",
        "SELECT count(*) FROM external_taxon_links WHERE refresh_error IS NOT NULL",
        "SELECT count(*) FROM seed_lots WHERE producer_plant_id IS NOT NULL",
        "SELECT count(*) FROM seed_lots WHERE producer_plant_group_id IS NOT NULL",
        "SELECT count(*) FROM plants WHERE originating_plant_group_id IS NOT NULL",
        "SELECT count(*) FROM media_assets WHERE kind = 'external' AND attachment_id IS NOT NULL",
        "SELECT count(*) FROM botanical_identity_cover_images WHERE source_mode = 'local'",
    ):
        assert query(first, statement) > 0, statement
    # The projected synonym relationship through the real taxonomy service.
    projections = expected()["projections"]
    assert projections["taxonomy.synonyms"] == [
        "Aloe barbadensis",
        "Lycopersicon esculentum",
        "Rosmarinus officinalis",
    ]
    assert projections["taxonomy.stale"] == 1
    assert projections["lineage.generation2_ancestors"] >= 3
    assert projections["search.unicode"] >= 1


def test_every_timestamp_comes_from_the_plan(first: str) -> None:
    """Including the columns only this profile populates, such as confirmations and retirements."""
    plan = plan_module.build_plan("comprehensive")
    start = query(first, "SELECT min(created_at) FROM users")
    assert start.isoformat() == f"{plan['anchor_date']}T12:00:00+00:00"
    latest = start + timedelta(seconds=len(plan["nodes"]))
    engine = create_engine(copy_url(first))
    try:
        with engine.connect() as connection:
            columns = connection.execute(
                text(
                    """
                    SELECT c.table_name, c.column_name FROM information_schema.columns c
                    JOIN information_schema.tables t USING (table_schema, table_name)
                    WHERE c.table_schema = 'public' AND t.table_type = 'BASE TABLE'
                    AND c.data_type LIKE 'timestamp%'
                    """
                )
            ).all()
    finally:
        engine.dispose()
    canonical = "AND place_kind = 'custom'"
    for table, column in {(row[0], row[1]) for row in columns} - WALL_CLOCK_COLUMNS:
        scope = canonical if table == "geographic_places" else ""
        statement = f"SELECT max({column}) FROM {table} WHERE {column} IS NOT NULL {scope}"
        value = query(first, statement)
        assert value is None or start <= value <= latest, (table, column, value)
    assert query(first, "SELECT min(applied_at) FROM native_range_applications") >= start
    assert query(first, "SELECT min(confirmed_at) FROM wfo_links") >= start


def test_digest_retains_timestamps_this_profile_populates(first: str) -> None:
    """Exhaustive over columns SMOKE leaves empty, so its timestamp test cannot speak for them."""
    runtime = pytest.importorskip("golden_dataset", reason="available in integration runner only")
    root = COPIES / first
    engine = create_engine(copy_url(first))
    try:
        with Session(engine) as database:
            reviewed = runtime.canonical_digest(database, root)["canonical_sha256"]
            for table, column in (
                ("wfo_links", "confirmed_at"),
                ("wcvp_links", "confirmed_at"),
                ("native_range_applications", "applied_at"),
                ("native_range_proposals", "created_at"),
                ("locations", "retired_at"),
                ("geographic_places", "retired_at"),
                ("media_assets", "fetched_at"),
            ):
                for sign in "+-":
                    try:
                        database.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER USER"))
                        database.execute(
                            text(
                                f"UPDATE {table} SET {column} = {column} {sign} "
                                f"interval '720 hours' WHERE {column} IS NOT NULL"
                            )
                        )
                    except IntegrityError:
                        database.rollback()
                        continue
                    changed = runtime.canonical_digest(database, root)["canonical_sha256"]
                    assert changed != reviewed, (table, column)
                    database.rollback()
                    break
                else:
                    pytest.fail(f"Could not move {table}.{column} in either direction")
    finally:
        engine.dispose()


def test_only_movement_completion_hashes_are_normalized(first: str) -> None:
    """The fingerprint exception stays one row wide; every other completion hash is content."""
    runtime = pytest.importorskip("golden_dataset", reason="available in integration runner only")
    derived = """
        SELECT count(*) FROM scheduled_activities a JOIN events e ON e.id = a.linked_event_id
        WHERE e.destination_location_id IS NOT NULL
    """
    assert query(first, derived) == 1
    root = COPIES / first
    change = (
        "UPDATE scheduled_activities SET completion_fingerprint = repeat('0', 64) WHERE id = :id"
    )
    engine = create_engine(copy_url(first))
    try:
        with Session(engine) as database:
            reviewed = runtime.canonical_digest(database, root)["canonical_sha256"]
            for key, sensitive in (
                ("schedule:schedule-states/completed", True),
                ("schedule:schedule-states/completed-event", True),
                ("schedule:schedule-history-states/repot", True),
                ("schedule:schedule-history-states/move", False),
            ):
                database.execute(text(change), {"id": ledger(first)["records"][key]})
                changed = runtime.canonical_digest(database, root)["canonical_sha256"]
                assert (changed != reviewed) is sensitive, key
                database.rollback()
    finally:
        engine.dispose()


def test_version_uuids_are_named_not_counted_as_unowned(first: str) -> None:
    """A link's version is random per copy; relationships to it must survive normalization."""
    runtime = pytest.importorskip("golden_dataset", reason="available in integration runner only")
    assert runtime.VERSION_UUID_COLUMNS == {"wcvp_links": "version", "wfo_links": "version"}
    value = query(first, "SELECT evidence->>'link_version' FROM native_range_proposals LIMIT 1")
    linked = query(first, f"SELECT count(*) FROM wcvp_links WHERE version = '{value}'")
    assert linked == 1


@pytest.mark.parametrize(
    ("table", "column", "where", "value"),
    [
        # Each is invariant-valid: only the reviewed baseline can tell.
        ("wfo_links", "evidence", "true", '{"taxon": {}}'),
        ("native_range_proposals", "evidence", "true", '{"format_version": 1, "choices": []}'),
        ("provenance_sites", "notes", "name LIKE 'Golden mix site 1 %'", "changed"),
        ("saved_views", "name", "name LIKE 'Golden view — search'", "Golden renamed"),
        ("harvests", "notes", "label = 'Golden — seed harvest'", "changed"),
    ],
)
def test_baseline_detects_invariant_valid_changes(
    second: str, table: str, column: str, where: str, value: str
) -> None:
    kind = "jsonb" if column == "evidence" else "text"
    identifier = "identity_id" if table == "wfo_links" else "id"
    row = query(second, f"SELECT {identifier} FROM {table} WHERE {where} ORDER BY 1 LIMIT 1")
    original = query(second, f"SELECT {column}::text FROM {table} WHERE {identifier} = '{row}'")
    restore = f"UPDATE {table} SET {column} = CAST(:value AS {kind}) WHERE {identifier} = '{row}'"
    execute(second, f"ALTER TABLE {table} DISABLE TRIGGER USER")
    try:
        execute(second, restore, value=value)
        code, report = verify(second)
        # A stored evidence edit may also break a projection; either way it never verifies.
        assert code != 0, (table, report)
        assert any(line.startswith(f"table {table}") for line in report["baseline_differences"])
    finally:
        execute(second, restore, value=original)
        execute(second, f"ALTER TABLE {table} ENABLE TRIGGER USER")
    assert verify(second)[0] == 0


def test_baseline_detects_a_swapped_relationship(second: str) -> None:
    """Two plants trade Locations: every count and every checked field stays valid."""
    rows = """
        SELECT id FROM plants WHERE location_id = (
            SELECT location_id FROM plants WHERE label LIKE 'Golden mix%' AND lifecycle = 'active'
            AND location_id IS NOT NULL GROUP BY location_id ORDER BY location_id
            OFFSET {offset} LIMIT 1
        ) AND label LIKE 'Golden mix%' AND lifecycle = 'active' ORDER BY id LIMIT 1
    """
    one, other = query(second, rows.format(offset=0)), query(second, rows.format(offset=1))
    first_location = query(second, f"SELECT location_id FROM plants WHERE id = '{one}'")
    second_location = query(second, f"SELECT location_id FROM plants WHERE id = '{other}'")
    assert first_location != second_location
    swap = "UPDATE plants SET location_id = :value WHERE id = :id"
    execute(second, swap, value=second_location, id=one)
    execute(second, swap, value=first_location, id=other)
    code, report = verify(second)
    assert code == BASELINE_MODIFIED, report
    assert [line.split(":")[0] for line in report["baseline_differences"]] == ["table plants"]
    execute(second, swap, value=first_location, id=one)
    execute(second, swap, value=second_location, id=other)
    assert verify(second)[0] == 0


def test_validation_detects_domain_damage(second: str) -> None:
    records = ledger(second)["records"]
    former = records["location:location-movement-history/former"]
    retired = query(second, f"SELECT retired_at FROM locations WHERE id = '{former}'")
    statement = f"UPDATE locations SET retired_at = :value WHERE id = '{former}'"
    execute(second, statement, value=None)
    result = run("validate", "--copy", second, *PROFILE)
    assert result.returncode == 1
    assert "retired_at: expected a value" in result.stderr
    assert "read projections differ" in result.stderr  # locations.retired changed as well
    execute(second, statement, value=retired)

    link = records["wfo_link:taxonomy-wfo-links/synonym-tomato"]
    identity = (
        "UPDATE botanical_identities SET updated_at = updated_at {} interval '1 hour' "
        f"WHERE id = '{link}'"
    )
    execute(second, identity.format("+"))
    result = run("validate", "--copy", second, *PROFILE)
    assert result.returncode == 1
    assert "read projections differ" in result.stderr  # A stale link leaves the synonym list.
    execute(second, identity.format("-"))
    assert run("validate", "--copy", second, *PROFILE).returncode == 0

    # Damage that breaks a read is reported with the rest, not as a crash that hides them.
    path = COPIES / second / ".golden-dataset.json"
    original = path.read_text()
    damaged = json.loads(original)
    del damaged["records"]["plant:seed-collection-produced/second-generation"]
    path.write_text(json.dumps(damaged))
    result = run("validate", "--copy", second, *PROFILE)
    path.write_text(original)
    assert result.returncode == 1
    assert "plan node not recorded" in result.stderr
    assert "read projections failed: KeyError" in result.stderr
    assert run("validate", "--copy", second, *PROFILE).returncode == 0


def test_validation_detects_media_damage(second: str) -> None:
    root = COPIES / second
    thumbnails = sorted((root / ".thumbnails").iterdir())
    assert thumbnails, "this profile stores the derivative of each saved external copy"
    stray = root / ".thumbnails" / "stray.webp"
    stray.write_bytes(b"not a derivative")
    result = run("validate", "--copy", second, *PROFILE)
    assert result.returncode == 1
    assert "unmanaged media file" in result.stderr
    stray.unlink()

    # A managed thumbnail's bytes are not checked by domain validation; the baseline sees them.
    victim = thumbnails[0]
    original = victim.read_bytes()
    victim.write_bytes(original + b"x")
    code, report = verify(second)
    assert code == BASELINE_MODIFIED, report
    assert any(line.startswith("media_sha256") for line in report["baseline_differences"])
    victim.write_bytes(original)

    assert verify(second)[0] == 0

    # A stored copy is legitimate only where the plan declares one.
    runtime = pytest.importorskip("golden_dataset", reason="available in integration runner only")
    engine = create_engine(copy_url(second))
    try:
        with Session(engine) as database:
            found = runtime.media_problems(database, root)
    finally:
        engine.dispose()
    assert sum("external asset was fetched" in problem for problem in found) == 2, found


def test_profile_identity_is_enforced(first: str, copies: list[str]) -> None:
    """A copy is exactly one reviewed profile; the wrong one is refused, never adopted."""
    # Default SMOKE arguments reach a COMPREHENSIVE copy.
    result = run("generate", "--copy", first)
    assert result.returncode == 1
    assert "different golden plan owns" in result.stderr
    result = run("validate", "--copy", first)
    assert result.returncode == 1
    assert "belongs to a different plan" in result.stderr
    assert json.loads(run("verify-baseline", "--copy", first).stdout)["state"] == "domain-invalid"
    # Beside it, SMOKE is untouched: same reviewed baseline, same default path.
    name = "golden_compr_smoke"
    succeed("create-copy", "--copy", name)
    copies.append(name)
    succeed("generate", "--copy", name)
    code = run("verify-baseline", "--copy", name).returncode
    assert code == 0
    result = run("generate", "--copy", name, *PROFILE)
    assert result.returncode == 1
    assert "different golden plan owns" in result.stderr
    # STRESS stays out of scope and refuses.
    result = run("generate", "--copy", name, "--profile", "stress")
    assert result.returncode == 1
    assert "not generated yet" in result.stderr


def test_repeat_generation_is_idempotent(first: str) -> None:
    before = ledger(first)
    timed("generate-ready", "generate", "--copy", first, *PROFILE)
    assert ledger(first) == before
    assert verify(first)[0] == 0


def test_contention_fails_fast_on_this_profile(first: str) -> None:
    holder = subprocess.Popen(
        [sys.executable, "-c", HOLD_VALIDATION, "validate", "--copy", first, *PROFILE],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert holder.stdout is not None
        assert holder.stdin is not None
        ready, _, _ = select.select([holder.stdout], [], [], 120)
        assert ready, "holder never reached its pause point"
        assert holder.stdout.readline() == "PAUSED\n"
        started = time.monotonic()
        for action in ("retire-copy", "generate", "digest", "verify-baseline"):
            arguments = (
                ("--copy", first, *PROFILE) if action != "retire-copy" else ("--copy", first)
            )
            result = run(action, *arguments)
            assert result.returncode == BUSY, (action, result.stderr)
        # Well under one generation, so a loser cannot have waited for the holder.
        assert time.monotonic() - started < 30
        assert (COPIES / first).is_dir()
        holder.stdin.write("go\n")
        holder.stdin.flush()
        _, error = holder.communicate(timeout=120)
        assert holder.returncode == 0, error
    finally:
        if holder.poll() is None:
            holder.kill()
            holder.communicate()


def test_failures_are_atomic_or_never_ready(copies: list[str], first: str) -> None:
    plan = plan_module.build_plan("comprehensive")
    graph = sum(node["kind"] not in {
        "primary", "external_cover", "local_cover", "media_copy", "media_copy_remove"
    } for node in plan["nodes"])  # fmt: skip
    name = "golden_compr_failure"
    succeed("create-copy", "--copy", name)
    copies.append(name)
    # Late in the atomic graph: uploads and the synthetic indexes already ran.
    failed = run("generate", "--copy", name, *PROFILE, "--fail-after", str(graph - 1))
    assert failed.returncode == 1
    state = ledger(name)
    assert (state["state"], state["clean"], state["records"]) == ("failed", True, {})
    assert query(name, "SELECT count(*) FROM seed_lots") == 0
    assert query(name, "SELECT count(*) FROM attachments") == 0
    assert [
        path for path in (COPIES / name).rglob("*") if path.is_file() and "objects" in path.parts
    ] == []
    # In the finishing phase, covers and copies commit one by one: never ready, never repaired.
    failed = run("generate", "--copy", name, *PROFILE, "--fail-after", str(graph + 3))
    assert failed.returncode == 1
    state = ledger(name)
    assert (state["state"], state["clean"]) == ("failed", False)
    assert run("validate", "--copy", name, *PROFILE).returncode == 1
    retried = run("generate", "--copy", name, *PROFILE)
    assert retried.returncode == 1
    assert "retire it instead of repairing" in retried.stderr


def test_refused_nodes_fail_when_a_rule_stops_refusing(first: str) -> None:
    """The plan's refusal evidence cannot pass by accident: either way of being wrong fails."""
    runtime = pytest.importorskip("golden_dataset", reason="available in integration runner only")
    from florabase.attachments.storage import AttachmentStorage

    engine = create_engine(copy_url(first))
    root = COPIES / first
    try:
        with Session(engine) as database:
            storage = AttachmentStorage(root)
            ledger_stub: dict[str, Any] = {"records": {}, "created_files": []}
            allowed = {"name": "Golden accepted by the owning service", "parent_id": None}
            with pytest.raises(runtime.GoldenError, match="was not refused"):
                runtime.refused(
                    database,
                    storage,
                    {"kind": "location", "error": "LocationHierarchyError", "payload": allowed},
                    ledger_stub,
                )
            database.rollback()
            with pytest.raises(runtime.GoldenError, match="Expected SeedLotIntegrityError"):
                runtime.refused(
                    database,
                    storage,
                    {
                        "kind": "location",
                        "error": "SeedLotIntegrityError",
                        "payload": {"name": "", "parent_id": None},
                    },
                    ledger_stub,
                )
            database.rollback()
    finally:
        engine.dispose()
    assert verify(first)[0] == 0


def test_measurements_are_reported(first: str, capsys: pytest.CaptureFixture[str]) -> None:
    """Not a benchmark: one run's cost, with ceilings that only catch a runaway."""
    size = query(first, f"SELECT pg_database_size('{first}')")
    media = sum(path.stat().st_size for path in (COPIES / first).rglob("*") if path.is_file())
    tables = expected()["tables"]
    summary = {
        "nodes": expected()["nodes"],
        "rows": sum(tables.values()),
        "domain_records": sum(c for t, c in tables.items() if t not in NOT_DOMAIN_RECORDS),
        "process_seconds": TIMINGS,
        "generate_seconds": GENERATION["seconds"],
        "generate_peak_rss_kib": GENERATION["peak_rss_kib"],
        "database_bytes": size,
        "media_bytes": media,
        "media_files": expected()["baseline"]["media_files"],
    }
    with capsys.disabled():
        report = json.dumps(summary, sort_keys=True)
        sys.stdout.write(f"\nGOLDEN_COMPREHENSIVE_MEASUREMENTS {report}\n")
    assert TIMINGS["generate-and-validate"] < 300
    assert TIMINGS["verify-baseline"] < 120
    assert size < 200 * 1024 * 1024
    assert media < 50 * 1024 * 1024
