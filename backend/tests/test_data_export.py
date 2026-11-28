"""DATA-EXPORT-001 contract: every table and column is classified before it can ship."""

import json
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from uuid import UUID

import florabase.main  # noqa: F401  (registers every model on Base.metadata)
from florabase.data_export.registry import (
    EXCLUDED,
    TABLES,
    UNMODELLED,
    classification_errors,
)
from florabase.data_export.service import (
    README,
    export_columns,
    format_value,
    table_for,
)
from florabase.db.base import Base

REVIEWED_COLUMNS = Path(__file__).parent / "fixtures" / "data_export" / "reviewed_columns.json"
SECRET_WORDS = ("password", "token", "digest", "csrf", "storage_key", "session")


def _headers(table: str) -> list[str]:
    entry = next(item for item in TABLES if item.table == table)
    return [column.header for column in export_columns(entry)]


def test_every_model_table_is_exported_or_excluded() -> None:
    assert classification_errors(set(Base.metadata.tables)) == []
    assert all(reason.strip() for reason in EXCLUDED.values())
    assert all(reason.strip() for reason in UNMODELLED.values())


def test_a_new_unregistered_table_fails_the_contract() -> None:
    names = {*Base.metadata.tables, "future_records"}
    assert classification_errors(names) == [
        "future_records: add it to data_export.registry TABLES or EXCLUDED (with a reason)"
    ]
    missing = set(Base.metadata.tables) - {"plants"}
    assert classification_errors(missing) == ["plants: listed in the registry but not a table"]


def test_every_column_of_an_exported_table_was_reviewed() -> None:
    """A new column of an exported table is exported automatically, so it needs a decision.

    Add it to tests/fixtures/data_export/reviewed_columns.json when it may be exported, or to the
    table's ``dropped`` columns in data_export/registry.py (with a reason) when it must not be.
    """
    reviewed = json.loads(REVIEWED_COLUMNS.read_text())
    current = {entry.table: sorted(table_for(entry.table).columns.keys()) for entry in TABLES}
    assert current == reviewed
    for entry in TABLES:
        columns = set(table_for(entry.table).columns.keys())
        assert set(entry.dropped) <= columns, entry.table
        assert all(reason.strip() for reason in entry.dropped.values())


def test_no_exported_column_points_at_an_excluded_table() -> None:
    """A reference to an excluded table (a user, a receipt) must be dropped with a reason."""
    for entry in TABLES:
        for column in table_for(entry.table).columns:
            targets = {key.column.table.name for key in column.foreign_keys}
            if targets & set(EXCLUDED):
                assert column.name in entry.dropped, (entry.table, column.name)


def test_no_secret_or_internal_column_is_exported() -> None:
    for entry in TABLES:
        for header in _headers(entry.table):
            assert not any(word in header for word in SECRET_WORDS), (entry.table, header)
            assert header not in entry.dropped, (entry.table, header)


def test_columns_collapse_partial_dates_and_add_labels() -> None:
    plants = _headers("plants")
    assert plants[:3] == ["id", "botanical_identity_id", "botanical_identity_label"]
    assert "collection_entry_date" in plants
    assert plants.index("collection_entry_date_precision") == (
        plants.index("collection_entry_date") + 1
    )
    assert not any(name.startswith("collection_entry_date_year") for name in plants)
    assert plants[plants.index("location_id") + 1] == "location_label"
    assert plants[plants.index("supplier_id") + 1] == "supplier_label"
    # Places are their own exported file; no label is promised for them.
    assert "material_provenance_place_label" not in plants
    seed_lots = _headers("seed_lots")
    for prefix in ("acquisition_date", "harvest_date", "expected_viability_until"):
        assert {prefix, f"{prefix}_precision"} <= set(seed_lots)
    assert "owner_display_name" in _headers("saved_views")
    assert "owner_id" not in _headers("saved_views")
    assert "actor_display_name" in _headers("botanical_identity_reconciliations")
    assert "storage_key" not in _headers("attachments")
    assert "reversed_operation_receipt_id" not in _headers("events")
    assert _headers("wfo_links") == [
        "identity_id",
        "identity_label",
        "version",
        "external_id",
        "confirmed_at",
    ]


def test_values_are_formatted_and_free_text_is_protected() -> None:
    class Kind(StrEnum):
        A = "seed"

    assert format_value(None) == ""
    assert format_value(True) == "true"
    assert format_value(False) == "false"
    assert format_value(Kind.A) == "seed"
    assert format_value(Decimal("-1.50")) == "-1.50"
    assert format_value(-3) == "-3"
    assert format_value(date(2026, 2, 3)) == "2026-02-03"
    plus_two = timezone(timedelta(hours=2))
    assert format_value(datetime(2026, 1, 1, 12, tzinfo=plus_two)) == "2026-01-01T10:00:00+00:00"
    assert format_value(datetime(2026, 1, 1, tzinfo=UTC)) == "2026-01-01T00:00:00+00:00"
    assert format_value(UUID(int=1)) == "00000000-0000-0000-0000-000000000001"
    assert format_value({"b": 1, "a": "x"}) == '{"a":"x","b":1}'
    for dangerous in ("=HYPERLINK(1)", "+1", "-2", "@SUM(A1)", "  =1"):
        assert format_value(dangerous) == "'" + dangerous
    assert format_value("Aloe vera") == "Aloe vera"


def test_readme_says_it_is_not_a_backup() -> None:
    assert "NOT a backup" in README
    assert "docs/operate/backup-restore.md" in README
