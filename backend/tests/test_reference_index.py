"""Reference indexes must have exactly the layout Florabase's builders write.

A crafted index can replace ``taxa`` with a view or an FTS5 virtual table and drive SQLite
extension code (CVE-2026-119373) from an ordinary owner search; independent QA reproduced that
with Florabase's own search SQL. These tests pin the supported layouts, the rejection of every
other schema before an application statement runs, and the connection hardening.
"""

import hashlib
import logging
import sqlite3
from collections.abc import Callable
from contextlib import closing
from pathlib import Path

import pytest
from test_native_range_enrichment import distribution, name
from test_taxonomy import GENUS, META, data

import florabase.native_range_enrichment.snapshot as wcvp_snapshot
import florabase.taxonomy.snapshot as wfo_snapshot
from florabase.core.config import Settings
from florabase.core.reference_index import UnsupportedIndexError, open_reference_index
from florabase.native_range_enrichment import source as wcvp
from florabase.taxonomy import source as wfo

SourceUnavailableError = (wfo.SourceUnavailableError, wcvp.SourceUnavailableError)
WCVP_SEARCH = (
    "SELECT t.*, a.name AS accepted_name FROM taxa t "
    "LEFT JOIN taxa a ON a.external_id=t.accepted_id "
    "WHERE t.search_name LIKE ? ESCAPE '\\' "
    "ORDER BY t.search_name, t.external_id LIMIT 25"
)
# Exactly what independent QA used: a taxa view over a detail=none FTS5 table with negative
# rowids, queried through a prefix MATCH by Florabase's unchanged search statement.
EXPLOIT = (
    "CREATE VIRTUAL TABLE f USING fts5(x, detail=none);"
    "INSERT INTO f(rowid, x) VALUES (-5, 'abc'), (-3, 'abd'), (-1, 'abe');"
    "CREATE VIEW taxa AS SELECT CAST(rowid AS TEXT) AS external_id, x AS name, '' AS authorship,"
    " 'Species' AS rank, 'Accepted' AS status, CAST(rowid AS TEXT) AS accepted_id,"
    " '' AS powo_id, '' AS reviewed, x AS search_name FROM f WHERE f MATCH 'ab*';"
)


def wfo_index(directory: Path) -> Path:
    destination = directory / "wfo.sqlite"
    wfo_snapshot.build_index(destination, *data(), META)
    return destination


def wcvp_index(directory: Path, version: wcvp.WcvpVersion = wcvp.DEFAULT_VERSION) -> Path:
    destination = directory / f"wcvp-{version}.sqlite"
    wcvp_snapshot.build_index(
        destination,
        [name(), name("101", "Synonym")],
        [distribution()],
        wcvp.SourceMetadata.for_release(version, "2026-10-28T00:00:00Z"),
    )
    return destination


def schema(path: Path) -> set[tuple[str, str, str, str | None]]:
    with closing(sqlite3.connect(path)) as db:
        return set(db.execute("SELECT type, name, tbl_name, sql FROM sqlite_schema"))


def reseal(path: Path) -> None:
    # A seal that matches: integrity of a copy, never provenance.
    path.with_suffix(".sha256").write_text(hashlib.sha256(path.read_bytes()).hexdigest() + "\n")


def snapshot_of(directory: Path) -> dict[str, tuple[bytes, int]]:
    return {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in directory.iterdir()}


def test_builder_output_is_exactly_the_supported_layout(tmp_path: Path) -> None:
    # The contracts equal the layout the builders wrote at 4329381 (unchanged DDL), so every
    # index built by a supported Florabase builder before this change stays accepted.
    assert schema(wfo_index(tmp_path)) == wfo.SCHEMA
    assert schema(wcvp_index(tmp_path, "15")) == wcvp.SCHEMA
    assert schema(wcvp_index(tmp_path, "16")) == wcvp.SCHEMA


def test_supported_indexes_keep_their_reference_operations(tmp_path: Path) -> None:
    source = wfo.WfoSource(wfo_index(tmp_path))
    assert source.metadata() == META
    assert source.search("Genus")[0].taxon.source_taxon_id == GENUS
    assert source.search("Old")[0].classification[-1].scientific_name == "Genus species"
    for version in ("15", "16"):
        index = wcvp.WcvpSource(wcvp_index(tmp_path, version), version)
        assert index.metadata().version == version
        assert [t.external_id for t in index.search("fixture")] == ["100", "101"]
        assert index.taxon("101").accepted_name == "Fixture species"
        assert index.distribution("100")[0]["area_code_l3"] == "BOL"


def test_dev_wcvp16_requires_seal_and_refuses_modified_index(tmp_path: Path) -> None:
    v15 = wcvp_index(tmp_path, "15")
    v16 = wcvp_index(tmp_path, "16")
    settings = Settings(
        wcvp_snapshot_path=v15, wcvp_v16_snapshot_path=v16, wcvp_v16_require_seal=True
    )
    assert wcvp.WcvpSource.from_settings(settings, "15").metadata().version == "15"
    assert wcvp.WcvpSource(v16, "16").metadata().version == "16"
    source = wcvp.WcvpSource.from_settings(settings)
    with pytest.raises(wcvp.SourceUnavailableError, match="seal is unavailable"):
        source.metadata()
    reseal(v16)
    assert source.metadata().version == "16"
    assert source.search("fixture")[0].name == "Fixture species"

    with closing(sqlite3.connect(v16)) as connection, connection:
        connection.execute("UPDATE taxa SET name = 'Modified species' WHERE external_id = '100'")
    with pytest.raises(wcvp.SourceUnavailableError, match="checksum does not match"):
        source.search("fixture")


def test_connection_is_hardened_read_only_and_holds_one_read_transaction(tmp_path: Path) -> None:
    with closing(open_reference_index(wfo_index(tmp_path), wfo.SCHEMA, "WFO")) as db:
        for option, expected in (
            (sqlite3.SQLITE_DBCONFIG_DEFENSIVE, True),
            (sqlite3.SQLITE_DBCONFIG_TRUSTED_SCHEMA, False),
            (sqlite3.SQLITE_DBCONFIG_ENABLE_VIEW, False),
            (sqlite3.SQLITE_DBCONFIG_ENABLE_TRIGGER, False),
            (sqlite3.SQLITE_DBCONFIG_ENABLE_LOAD_EXTENSION, False),
            (sqlite3.SQLITE_DBCONFIG_WRITABLE_SCHEMA, False),
        ):
            assert db.getconfig(option) is expected
        assert db.execute("PRAGMA trusted_schema").fetchone()[0] == 0
        assert db.execute("PRAGMA query_only").fetchone()[0] == 1
        assert db.execute("PRAGMA cell_size_check").fetchone()[0] == 1
        assert db.in_transaction
        with pytest.raises(sqlite3.OperationalError):
            db.execute("DELETE FROM taxa")
        with pytest.raises(sqlite3.OperationalError):
            db.execute("SELECT load_extension('x')")
        with pytest.raises(sqlite3.OperationalError):
            db.execute("ATTACH DATABASE ':memory:' AS other")


def test_view_over_fts5_exploit_is_refused_before_the_search_runs(tmp_path: Path) -> None:
    crafted = tmp_path / "crafted.sqlite"
    with closing(sqlite3.connect(crafted)) as db:
        db.executescript(EXPLOIT)
        db.execute("CREATE TABLE metadata(payload TEXT NOT NULL)")
        payload = wcvp.SourceMetadata.for_release(
            wcvp.DEFAULT_VERSION, "2026-10-28T00:00:00Z"
        ).model_dump_json()
        db.execute("INSERT INTO metadata VALUES (?)", (payload,))
        db.commit()
    # Control: an unhardened read-only connection runs the FTS5 prefix MATCH from the search.
    with closing(sqlite3.connect(f"{crafted.as_uri()}?mode=ro", uri=True)) as plain:
        assert plain.execute(WCVP_SEARCH, ("ab%",)).fetchall()
    before = snapshot_of(tmp_path)
    source = wcvp.WcvpSource(crafted)
    for operation in (
        source.metadata,
        lambda: source.search("ab"),
        lambda: source.taxon("-5"),
        lambda: source.distribution("-5"),
    ):
        with pytest.raises(SourceUnavailableError, match="not a supported index"):
            operation()
    assert snapshot_of(tmp_path) == before


def test_connection_hardening_is_a_second_layer_not_the_decisive_control(tmp_path: Path) -> None:
    view = tmp_path / "view.sqlite"
    with closing(sqlite3.connect(view)) as db:
        db.executescript(EXPLOIT)
    # Even if the schema allow-list were bypassed, views are disabled on the connection.
    with (
        closing(open_reference_index(view, frozenset(schema(view)), "test")) as db,
        pytest.raises(sqlite3.OperationalError),
    ):
        db.execute(WCVP_SEARCH, ("ab%",)).fetchall()
    direct = tmp_path / "direct.sqlite"
    with closing(sqlite3.connect(direct)) as db:
        db.executescript(
            "CREATE VIRTUAL TABLE taxa USING fts5(external_id, search_name, detail=none);"
            "INSERT INTO taxa(rowid, external_id, search_name) VALUES (-5, '1', 'abc');"
        )
    # A taxa that is itself FTS5 still reaches FTS5 code under the hardened settings, which is
    # why the exact schema contract, not trusted_schema, decides.
    with closing(open_reference_index(direct, frozenset(schema(direct)), "test")) as db:
        assert db.execute("SELECT external_id FROM taxa WHERE taxa MATCH 'ab*'").fetchall()
    with pytest.raises(UnsupportedIndexError):
        open_reference_index(direct, wcvp.SCHEMA, "WCVP")


def add_view(db: sqlite3.Connection) -> None:
    db.execute("CREATE VIEW extra AS SELECT 1")


def add_trigger(db: sqlite3.Connection) -> None:
    db.execute("CREATE TRIGGER extra AFTER INSERT ON metadata BEGIN SELECT 1; END")


def add_fts5(db: sqlite3.Connection) -> None:
    db.execute("CREATE VIRTUAL TABLE extra USING fts5(x)")


def add_unknown_module(db: sqlite3.Connection) -> None:
    db.execute("PRAGMA writable_schema=ON")
    db.execute(
        "INSERT INTO sqlite_schema VALUES "
        "('table', 'extra', 'extra', 0, 'CREATE VIRTUAL TABLE extra USING florabase_absent(x)')"
    )


def duplicate_automatic_index(db: sqlite3.Connection) -> None:
    # Same row as the contract's, but pointing at another b-tree (QA delta finding P3-1).
    root = db.execute("SELECT rootpage FROM sqlite_schema WHERE name='metadata'").fetchone()[0]
    db.execute("PRAGMA writable_schema=ON")
    db.execute(
        "INSERT INTO sqlite_schema VALUES ('index', 'sqlite_autoindex_taxa_1', 'taxa', ?, NULL)",
        (root,),
    )


def add_table(db: sqlite3.Connection) -> None:
    db.execute("CREATE TABLE extra(x)")


def add_index(db: sqlite3.Connection) -> None:
    db.execute("CREATE INDEX extra ON taxa(search_name)")


def add_statistics(db: sqlite3.Connection) -> None:
    db.execute("ANALYZE")


def drop_index(db: sqlite3.Connection) -> None:
    db.execute("DROP INDEX search_taxa")


def add_column(db: sqlite3.Connection) -> None:
    db.execute("ALTER TABLE taxa ADD COLUMN extra TEXT")


def replace_taxa_with_view(db: sqlite3.Connection) -> None:
    db.executescript(
        "ALTER TABLE taxa RENAME TO original; CREATE VIEW taxa AS SELECT * FROM original;"
    )


@pytest.mark.parametrize(
    "tamper",
    [
        add_view,
        add_trigger,
        add_fts5,
        add_unknown_module,
        duplicate_automatic_index,
        add_table,
        add_index,
        add_statistics,
        drop_index,
        add_column,
        replace_taxa_with_view,
    ],
)
def test_any_other_schema_object_or_layout_is_refused_despite_a_matching_seal(
    tmp_path: Path, tamper: Callable[[sqlite3.Connection], None], caplog: pytest.LogCaptureFixture
) -> None:
    index = wfo_index(tmp_path)
    with closing(sqlite3.connect(index)) as db:
        tamper(db)
        db.commit()
    reseal(index)
    before = snapshot_of(tmp_path)
    with (
        caplog.at_level(logging.WARNING, "florabase.core.reference_index"),
        pytest.raises(wfo.SourceUnavailableError) as raised,
    ):
        wfo.WfoSource(index).search("Genus")
    message = str(raised.value)
    assert message == (
        "The WFO source index is not a supported index built by Florabase's WFO builder."
    )
    assert "extra" not in message
    assert "CREATE" not in message
    assert "Refusing WFO reference index wfo.sqlite" in caplog.text
    assert snapshot_of(tmp_path) == before


def test_virtual_tables_are_never_connected_while_the_schema_is_checked(tmp_path: Path) -> None:
    index = wcvp_index(tmp_path)
    with closing(sqlite3.connect(index)) as db:
        add_unknown_module(db)
        db.commit()
    # A module that does not exist would fail if the check instantiated virtual tables.
    with pytest.raises(UnsupportedIndexError):
        open_reference_index(index, wcvp.SCHEMA, "WCVP")


@pytest.mark.parametrize(
    "content",
    [b"", b"not a database", b"SQLite format 3\x00" + b"\xff" * 84, None],
)
def test_malformed_databases_fail_closed(tmp_path: Path, content: bytes | None) -> None:
    index = wcvp_index(tmp_path)
    if content is None:
        # Truncate a real index mid-file.
        index.write_bytes(index.read_bytes()[: index.stat().st_size // 2])
    else:
        index.write_bytes(content)
    before = snapshot_of(tmp_path)
    with pytest.raises(wcvp.SourceUnavailableError):
        wcvp.WcvpSource(index).search("fixture")
    assert snapshot_of(tmp_path) == before


def test_unsupported_wfo_format_version_is_refused(tmp_path: Path) -> None:
    index = wfo_index(tmp_path)
    with closing(sqlite3.connect(index)) as db:
        db.execute("UPDATE metadata SET payload=json_set(payload, '$.format_version', 2)")
        db.commit()
    reseal(index)
    with pytest.raises(wfo.SourceUnavailableError, match="unavailable or invalid"):
        wfo.WfoSource(index).metadata()


def test_wcvp_release_mismatch_is_still_refused_with_a_valid_layout(tmp_path: Path) -> None:
    with pytest.raises(wcvp.SourceUnavailableError, match="unavailable or invalid"):
        wcvp.WcvpSource(wcvp_index(tmp_path, "16"), "15").metadata()
    with pytest.raises(wcvp.SourceUnavailableError, match="unavailable or invalid"):
        wcvp.WcvpSource(wcvp_index(tmp_path, "15")).metadata()


@pytest.mark.parametrize(
    ("module", "build"),
    [
        (wfo_snapshot, lambda path: wfo_snapshot.build_index(path, *data(), META)),
        (
            wcvp_snapshot,
            lambda path: wcvp_snapshot.build_index(
                path,
                [name()],
                [],
                wcvp.SourceMetadata.for_release(wcvp.DEFAULT_VERSION, "2026-10-28T00:00:00Z"),
            ),
        ),
    ],
)
def test_builders_never_publish_a_layout_the_reader_would_refuse(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module: object,
    build: Callable[[Path], None],
) -> None:
    monkeypatch.setattr(module, "SCHEMA", frozenset())
    destination = tmp_path / "index.sqlite"
    with pytest.raises(UnsupportedIndexError):
        build(destination)
    assert list(tmp_path.glob("*.sqlite")) == []
