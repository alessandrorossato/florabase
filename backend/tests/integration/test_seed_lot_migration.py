from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid7

import pytest
from alembic.config import Config
from sqlalchemy import Connection, Engine, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from florabase.seed_lots.model import SeedLot

pytestmark = pytest.mark.integration


def _botanical_identity(connection: Connection) -> UUID:
    identity_id = uuid7()
    now = datetime.now(UTC)
    connection.execute(
        text(
            "INSERT INTO botanical_identities "
            "(id, scientific_name, created_at, updated_at) "
            "VALUES (:id, :name, :now, :now)"
        ),
        {"id": identity_id, "name": f"Testus {identity_id.hex}", "now": now},
    )
    return identity_id


def _insert_lot(connection: Connection, botanical_identity_id: UUID, **overrides: object) -> UUID:
    lot_id = uuid7()
    values: dict[str, object] = {
        "id": lot_id,
        "botanical_identity_id": botanical_identity_id,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        **overrides,
    }
    columns = ", ".join(values)
    parameters = ", ".join(f":{key}" for key in values)
    connection.execute(text(f"INSERT INTO seed_lots ({columns}) VALUES ({parameters})"), values)
    return lot_id


def _reject_lot(connection: Connection, required_identity_id: UUID, **overrides: object) -> None:
    with pytest.raises(DBAPIError), connection.begin_nested():
        _insert_lot(connection, required_identity_id, **overrides)


def test_seed_lot_migration_upgrade_downgrade_and_reupgrade(database_engine: Engine) -> None:
    config = Config("alembic.ini")
    try:
        command.downgrade(config, "20260830_0007")
        assert not inspect(database_engine).has_table("seed_lots")
        for retained_table in (
            "botanical_identities",
            "suppliers",
            "locations",
            "geographic_places",
        ):
            assert inspect(database_engine).has_table(retained_table)
        command.upgrade(config, "20260830_0008")
        assert inspect(database_engine).has_table("seed_lots")

        with database_engine.begin() as connection:
            identity_id = _botanical_identity(connection)
            _reject_lot(
                connection,
                identity_id,
                lifecycle="exhausted",
                quantity_kind="seed_count",
                quantity_value=Decimal("0"),
                quantity_is_approximate=False,
            )

        command.upgrade(config, "head")
        with database_engine.begin() as connection:
            identity_id = _botanical_identity(connection)
            _insert_lot(
                connection,
                identity_id,
                lifecycle="exhausted",
                quantity_kind="seed_count",
                quantity_value=Decimal("0"),
                quantity_is_approximate=False,
            )
            connection.execute(
                text("DELETE FROM seed_lots WHERE botanical_identity_id = :identity_id"),
                {"identity_id": identity_id},
            )

        command.downgrade(config, "20260830_0008")
        with database_engine.begin() as connection:
            identity_id = _botanical_identity(connection)
            _reject_lot(
                connection,
                identity_id,
                lifecycle="exhausted",
                quantity_kind="weight",
                quantity_value=Decimal("0"),
                quantity_unit="g",
                quantity_is_approximate=False,
            )
    finally:
        command.upgrade(config, "head")
    assert inspect(database_engine).has_table("seed_lots")

    with database_engine.begin() as connection:
        identity_id = _botanical_identity(connection)
        _insert_lot(
            connection,
            identity_id,
            lifecycle="exhausted",
            quantity_kind="weight",
            quantity_value=Decimal("0"),
            quantity_unit="mg",
            quantity_is_approximate=False,
        )
        connection.execute(
            text("DELETE FROM seed_lots WHERE botanical_identity_id = :identity_id"),
            {"identity_id": identity_id},
        )


def test_seed_lot_schema_minimal_defaults_uuid7_and_duplicate_lots(
    database_connection: Connection,
) -> None:
    columns = {
        column["name"]: column for column in inspect(database_connection).get_columns("seed_lots")
    }
    assert set(columns) == {
        "id",
        "botanical_identity_id",
        "label",
        "source_kind",
        "source_detail",
        "supplier_id",
        "material_provenance_place_id",
        "acquisition_date_precision",
        "acquisition_date_year",
        "acquisition_date_month",
        "acquisition_date_day",
        "harvest_date_precision",
        "harvest_date_year",
        "harvest_date_month",
        "harvest_date_day",
        "quantity_kind",
        "quantity_value",
        "quantity_unit",
        "quantity_is_approximate",
        "expected_viability_until_precision",
        "expected_viability_until_year",
        "expected_viability_until_month",
        "expected_viability_until_day",
        "location_id",
        "lifecycle",
        "notes",
        "created_at",
        "updated_at",
    }
    assert columns["botanical_identity_id"]["nullable"] is False
    assert columns["supplier_id"]["nullable"] is True
    assert columns["material_provenance_place_id"]["nullable"] is True
    assert columns["location_id"]["nullable"] is True
    assert "TIMESTAMP" in str(columns["created_at"]["type"])

    identity_id = _botanical_identity(database_connection)
    with Session(
        bind=database_connection, join_transaction_mode="create_savepoint"
    ) as database_session:
        minimal = SeedLot(botanical_identity_id=identity_id)
        database_session.add(minimal)
        database_session.flush()
        assert minimal.id.version == 7
        assert minimal.source_kind == "unknown"
        assert minimal.lifecycle == "active"
        assert minimal.created_at.tzinfo is UTC
        assert minimal.updated_at.tzinfo is UTC
        database_session.rollback()

    first = _insert_lot(database_connection, identity_id)
    second = _insert_lot(database_connection, identity_id)
    rows = database_connection.execute(
        text(
            "SELECT id, source_kind, lifecycle FROM seed_lots "
            "WHERE botanical_identity_id = :identity_id ORDER BY id"
        ),
        {"identity_id": identity_id},
    ).mappings()
    values = list(rows)
    assert len(values) == 2
    assert {row["id"] for row in values} == {first, second}
    assert all(row["id"].version == 7 for row in values)
    assert all(row["source_kind"] == "unknown" for row in values)
    assert all(row["lifecycle"] == "active" for row in values)

    now = datetime.now(UTC)
    with pytest.raises(IntegrityError), database_connection.begin_nested():
        database_connection.execute(
            text(
                "INSERT INTO seed_lots (id, botanical_identity_id, created_at, updated_at) "
                "VALUES (:id, NULL, :now, :now)"
            ),
            {"id": uuid7(), "now": now},
        )


def test_seed_lot_sources_text_and_all_lifecycle_states(
    database_connection: Connection,
) -> None:
    identity_id = _botanical_identity(database_connection)
    source_kinds = (
        "purchased",
        "purchased_fruit",
        "self_collected",
        "collection_produced",
        "gift_exchange",
        "other",
        "unknown",
    )
    for source_kind in source_kinds:
        _insert_lot(
            database_connection,
            identity_id,
            source_kind=source_kind,
            source_detail="Community seed library" if source_kind == "other" else None,
        )
    assert database_connection.execute(
        text("SELECT count(DISTINCT source_kind) FROM seed_lots WHERE botanical_identity_id=:id"),
        {"id": identity_id},
    ).scalar_one() == len(source_kinds)
    _reject_lot(
        database_connection,
        identity_id,
        source_kind="purchased",
        source_detail="Shop",
    )
    _reject_lot(database_connection, identity_id, source_kind="other", source_detail=" bad ")
    _reject_lot(database_connection, identity_id, source_kind="invented")

    inactive_ids = []
    for lifecycle in ("active", "exhausted", "discarded", "lost"):
        lot_id = _insert_lot(
            database_connection,
            identity_id,
            lifecycle=lifecycle,
            label="Thailand trip 2026",
            notes="First line\nSecond line with useful Unicode: เมล็ด",
        )
        if lifecycle != "active":
            inactive_ids.append(lot_id)
    assert (
        database_connection.execute(
            text("SELECT count(*) FROM seed_lots WHERE id = ANY(:ids)"),
            {"ids": inactive_ids},
        ).scalar_one()
        == 3
    )
    _reject_lot(database_connection, identity_id, lifecycle="expired")
    _reject_lot(database_connection, identity_id, label=" accidental  whitespace ")
    _reject_lot(database_connection, identity_id, notes="bad\rcontrol")


@pytest.mark.parametrize(
    "prefix",
    ["acquisition_date", "harvest_date", "expected_viability_until"],
)
def test_seed_lot_partial_dates_preserve_precision_and_reject_invalid_combinations(
    database_connection: Connection, prefix: str
) -> None:
    identity_id = _botanical_identity(database_connection)
    date_examples: tuple[tuple[str, dict[str, int]], ...] = (
        ("year", {"year": 2024}),
        ("month", {"year": 2024, "month": 5}),
        ("day", {"year": 2024, "month": 5, "day": 18}),
    )
    for precision, components in date_examples:
        values: dict[str, object] = {f"{prefix}_precision": precision}
        values.update({f"{prefix}_{key}": value for key, value in components.items()})
        lot_id = _insert_lot(database_connection, identity_id, **values)
        stored = database_connection.execute(
            text(
                f"SELECT {prefix}_precision, {prefix}_year, {prefix}_month, {prefix}_day "
                "FROM seed_lots WHERE id = :id"
            ),
            {"id": lot_id},
        ).one()
        assert stored == (
            precision,
            components.get("year"),
            components.get("month"),
            components.get("day"),
        )

    invalid: tuple[dict[str, object], ...] = (
        {f"{prefix}_month": 5},
        {f"{prefix}_precision": "month", f"{prefix}_month": 5},
        {
            f"{prefix}_precision": "year",
            f"{prefix}_year": 2024,
            f"{prefix}_month": 1,
        },
        {
            f"{prefix}_precision": "month",
            f"{prefix}_year": 2024,
            f"{prefix}_month": 13,
        },
        {
            f"{prefix}_precision": "day",
            f"{prefix}_year": 2023,
            f"{prefix}_month": 2,
            f"{prefix}_day": 29,
        },
        {
            f"{prefix}_precision": "week",
            f"{prefix}_year": 2024,
        },
    )
    for values in invalid:
        _reject_lot(database_connection, identity_id, **values)


def test_seed_lot_quantities_cover_exact_approximate_count_and_weight(
    database_connection: Connection,
) -> None:
    identity_id = _botanical_identity(database_connection)
    supported: tuple[dict[str, object], ...] = (
        {
            "quantity_kind": "seed_count",
            "quantity_value": Decimal("120"),
            "quantity_is_approximate": False,
        },
        {
            "quantity_kind": "seed_count",
            "quantity_value": Decimal("100"),
            "quantity_is_approximate": True,
        },
        {
            "quantity_kind": "weight",
            "quantity_value": Decimal("4.5"),
            "quantity_unit": "g",
            "quantity_is_approximate": False,
        },
        {
            "quantity_kind": "weight",
            "quantity_value": Decimal("250"),
            "quantity_unit": "mg",
            "quantity_is_approximate": True,
        },
    )
    for values in supported:
        _insert_lot(database_connection, identity_id, **values)

    for lifecycle, values in (
        (
            "discarded",
            {
                "quantity_kind": "seed_count",
                "quantity_value": Decimal("25"),
                "quantity_is_approximate": False,
            },
        ),
        (
            "lost",
            {
                "quantity_kind": "weight",
                "quantity_value": Decimal("2.5"),
                "quantity_unit": "g",
                "quantity_is_approximate": True,
            },
        ),
    ):
        _insert_lot(database_connection, identity_id, lifecycle=lifecycle, **values)

    invalid: tuple[dict[str, object], ...] = (
        {"quantity_kind": "seed_count"},
        {"quantity_value": Decimal("1")},
        {
            "quantity_kind": "seed_count",
            "quantity_value": Decimal("1.5"),
            "quantity_is_approximate": False,
        },
        {
            "quantity_kind": "seed_count",
            "quantity_value": Decimal("10"),
            "quantity_unit": "g",
            "quantity_is_approximate": False,
        },
        {
            "quantity_kind": "weight",
            "quantity_value": Decimal("1"),
            "quantity_is_approximate": False,
        },
        {
            "quantity_kind": "weight",
            "quantity_value": Decimal("1"),
            "quantity_unit": "kg",
            "quantity_is_approximate": False,
        },
        {
            "quantity_kind": "weight",
            "quantity_value": Decimal("0"),
            "quantity_unit": "g",
            "quantity_is_approximate": False,
        },
        {
            "quantity_kind": "seed_count",
            "quantity_value": Decimal("-1"),
            "quantity_is_approximate": True,
        },
    )
    for values in invalid:
        _reject_lot(database_connection, identity_id, **values)


def test_seed_lot_zero_quantity_means_exact_known_exhaustion(
    database_connection: Connection,
) -> None:
    identity_id = _botanical_identity(database_connection)
    supported: tuple[dict[str, object], ...] = (
        {"lifecycle": "exhausted"},
        {
            "lifecycle": "exhausted",
            "quantity_kind": "seed_count",
            "quantity_value": Decimal("0"),
            "quantity_is_approximate": False,
        },
        {
            "lifecycle": "exhausted",
            "quantity_kind": "weight",
            "quantity_value": Decimal("0"),
            "quantity_unit": "g",
            "quantity_is_approximate": False,
        },
        {
            "lifecycle": "exhausted",
            "quantity_kind": "weight",
            "quantity_value": Decimal("0"),
            "quantity_unit": "mg",
            "quantity_is_approximate": False,
        },
    )
    for values in supported:
        _insert_lot(database_connection, identity_id, **values)

    for lifecycle in ("active", "discarded", "lost"):
        _reject_lot(
            database_connection,
            identity_id,
            lifecycle=lifecycle,
            quantity_kind="seed_count",
            quantity_value=Decimal("0"),
            quantity_is_approximate=False,
        )

    _reject_lot(
        database_connection,
        identity_id,
        lifecycle="exhausted",
        quantity_kind="seed_count",
        quantity_value=Decimal("0"),
        quantity_is_approximate=True,
    )
    for quantity_kind, quantity_unit in (("seed_count", None), ("weight", "g")):
        _reject_lot(
            database_connection,
            identity_id,
            lifecycle="exhausted",
            quantity_kind=quantity_kind,
            quantity_value=Decimal("-1"),
            quantity_unit=quantity_unit,
            quantity_is_approximate=False,
        )


def test_seed_lot_independent_restrictive_foreign_keys(database_connection: Connection) -> None:
    identity_id = _botanical_identity(database_connection)
    supplier_id = uuid7()
    location_id = uuid7()
    provenance_id = database_connection.execute(
        text("SELECT id FROM geographic_places WHERE source_code = 'TH' AND place_kind='canonical'")
    ).scalar_one()
    now = datetime.now(UTC)
    database_connection.execute(
        text(
            "INSERT INTO suppliers (id, name, kind, created_at, updated_at) "
            "VALUES (:id, 'Seed supplier', 'seller', :now, :now)"
        ),
        {"id": supplier_id, "now": now},
    )
    database_connection.execute(
        text(
            "INSERT INTO locations (id, name, created_at, updated_at) "
            "VALUES (:id, 'Refrigerator', :now, :now)"
        ),
        {"id": location_id, "now": now},
    )
    lot_id = _insert_lot(
        database_connection,
        identity_id,
        supplier_id=supplier_id,
        material_provenance_place_id=provenance_id,
        location_id=location_id,
    )
    assert database_connection.execute(
        text(
            "SELECT botanical_identity_id, supplier_id, material_provenance_place_id, location_id "
            "FROM seed_lots WHERE id=:id"
        ),
        {"id": lot_id},
    ).one() == (identity_id, supplier_id, provenance_id, location_id)

    _reject_lot(database_connection, uuid7())
    for column in ("supplier_id", "material_provenance_place_id", "location_id"):
        _reject_lot(database_connection, identity_id, **{column: uuid7()})

    for table, referenced_id in (
        ("botanical_identities", identity_id),
        ("suppliers", supplier_id),
        ("geographic_places", provenance_id),
        ("locations", location_id),
    ):
        with pytest.raises(IntegrityError), database_connection.begin_nested():
            database_connection.execute(
                text(f"DELETE FROM {table} WHERE id = :id"), {"id": referenced_id}
            )
