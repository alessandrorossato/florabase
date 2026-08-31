from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid7

import pytest
from alembic.config import Config
from sqlalchemy import Connection, Engine, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from alembic import command

pytestmark = pytest.mark.integration


def _references(connection: Connection) -> tuple[UUID, UUID]:
    identity_id, lot_id = uuid7(), uuid7()
    now = datetime.now(UTC)
    connection.execute(
        text(
            "INSERT INTO botanical_identities (id, scientific_name, created_at, updated_at) "
            "VALUES (:id, :name, :now, :now)"
        ),
        {"id": identity_id, "name": f"Sowingus {identity_id.hex}", "now": now},
    )
    connection.execute(
        text(
            "INSERT INTO seed_lots (id, botanical_identity_id, created_at, updated_at) "
            "VALUES (:id, :identity, :now, :now)"
        ),
        {"id": lot_id, "identity": identity_id, "now": now},
    )
    return identity_id, lot_id


def _insert_sowing(connection: Connection, seed_lot_id: UUID, **overrides: object) -> UUID:
    sowing_id = uuid7()
    values: dict[str, object] = {
        "id": sowing_id,
        "seed_lot_id": seed_lot_id,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        **overrides,
    }
    columns = ", ".join(values)
    parameters = ", ".join(f":{key}" for key in values)
    connection.execute(text(f"INSERT INTO sowings ({columns}) VALUES ({parameters})"), values)
    return sowing_id


def _reject(connection: Connection, seed_lot_id: UUID, **overrides: object) -> None:
    with pytest.raises(DBAPIError), connection.begin_nested():
        _insert_sowing(connection, seed_lot_id, **overrides)


def test_sowing_migration_upgrade_downgrade_and_reupgrade(database_engine: Engine) -> None:
    config = Config("alembic.ini")
    try:
        command.downgrade(config, "20260830_0009")
        inspector = inspect(database_engine)
        assert not inspector.has_table("sowings")
        assert inspector.has_table("seed_lots")
        assert inspector.has_table("locations")
        command.upgrade(config, "20260831_0010")
        inspector = inspect(database_engine)
        assert inspector.has_table("sowings")
        columns = {item["name"] for item in inspector.get_columns("sowings")}
        assert columns == {
            "id",
            "seed_lot_id",
            "label",
            "sowing_date_precision",
            "sowing_date_year",
            "sowing_date_month",
            "sowing_date_day",
            "quantity_kind",
            "quantity_value",
            "quantity_unit",
            "quantity_is_approximate",
            "germinated_count",
            "location_id",
            "substrate",
            "method_container",
            "pretreatment",
            "temperature_min_c",
            "temperature_max_c",
            "environment",
            "lifecycle",
            "notes",
            "created_at",
            "updated_at",
        }
        inspected_columns = {item["name"]: item for item in inspector.get_columns("sowings")}
        assert inspected_columns["seed_lot_id"]["nullable"] is False
        assert str(inspected_columns["germinated_count"]["type"]) == "INTEGER"
        assert {item["name"] for item in inspector.get_indexes("sowings")} == {
            "ix_sowings_seed_lot_id",
            "ix_sowings_location_id",
            "ix_sowings_lifecycle",
        }
        foreign_keys = inspector.get_foreign_keys("sowings")
        assert {
            (item["referred_table"], tuple(item["constrained_columns"])) for item in foreign_keys
        } == {("seed_lots", ("seed_lot_id",)), ("locations", ("location_id",))}
        command.downgrade(config, "20260830_0009")
        assert not inspect(database_engine).has_table("sowings")
        assert inspect(database_engine).has_table("seed_lots")
        command.upgrade(config, "20260831_0010")
    finally:
        command.upgrade(config, "head")
    assert inspect(database_engine).has_table("sowings")


def test_sowing_database_invariants_and_restrictive_references(
    database_connection: Connection,
) -> None:
    identity_id, lot_id = _references(database_connection)
    location_id = uuid7()
    now = datetime.now(UTC)
    database_connection.execute(
        text(
            "INSERT INTO locations (id, name, retired_at, created_at, updated_at) "
            "VALUES (:id, 'Retired bench', :now, :now, :now)"
        ),
        {"id": location_id, "now": now},
    )
    for lifecycle in ("active", "completed", "failed", "abandoned"):
        _insert_sowing(database_connection, lot_id, lifecycle=lifecycle, location_id=location_id)
    with pytest.raises(IntegrityError), database_connection.begin_nested():
        database_connection.execute(
            text(
                "INSERT INTO sowings (id, seed_lot_id, created_at, updated_at) "
                "VALUES (:id, NULL, :now, :now)"
            ),
            {"id": uuid7(), "now": now},
        )
    _reject(database_connection, lot_id, lifecycle="lost")
    _reject(database_connection, uuid7())
    _reject(database_connection, lot_id, location_id=uuid7())
    _reject(database_connection, lot_id, label=" bad  spacing ")
    _reject(database_connection, lot_id, notes="bad\rcontrol")
    for invalid_date in (
        {"sowing_date_month": 5},
        {"sowing_date_precision": "month", "sowing_date_year": 2024},
        {
            "sowing_date_precision": "day",
            "sowing_date_year": 2023,
            "sowing_date_month": 2,
            "sowing_date_day": 29,
        },
    ):
        _reject(database_connection, lot_id, **invalid_date)
    for valid_date in (
        {"sowing_date_precision": "year", "sowing_date_year": 2024},
        {"sowing_date_precision": "month", "sowing_date_year": 2024, "sowing_date_month": 5},
        {
            "sowing_date_precision": "day",
            "sowing_date_year": 2024,
            "sowing_date_month": 5,
            "sowing_date_day": 18,
        },
    ):
        _insert_sowing(database_connection, lot_id, **valid_date)
    invalid_quantities = (
        {"quantity_kind": "seed_count"},
        {
            "quantity_kind": "seed_count",
            "quantity_value": Decimal("0"),
            "quantity_is_approximate": False,
        },
        {
            "quantity_kind": "seed_count",
            "quantity_value": Decimal("-1"),
            "quantity_is_approximate": False,
        },
        {
            "quantity_kind": "seed_count",
            "quantity_value": Decimal("1.5"),
            "quantity_is_approximate": False,
        },
        {
            "quantity_kind": "seed_count",
            "quantity_value": Decimal("1"),
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
    )
    for quantity in invalid_quantities:
        _reject(database_connection, lot_id, **quantity)
    _reject(database_connection, lot_id, germinated_count=-1)
    _reject(
        database_connection,
        lot_id,
        quantity_kind="seed_count",
        quantity_value=Decimal("20"),
        quantity_is_approximate=False,
        germinated_count=21,
    )
    _insert_sowing(
        database_connection,
        lot_id,
        quantity_kind="seed_count",
        quantity_value=Decimal("20"),
        quantity_is_approximate=True,
        germinated_count=21,
    )
    _insert_sowing(
        database_connection,
        lot_id,
        quantity_kind="weight",
        quantity_value=Decimal("1"),
        quantity_unit="g",
        quantity_is_approximate=False,
        germinated_count=37,
    )
    _reject(
        database_connection,
        lot_id,
        temperature_min_c=Decimal("25.1"),
        temperature_max_c=Decimal("25"),
    )
    retained_id = _insert_sowing(database_connection, lot_id, location_id=location_id)
    for table, item_id in (("seed_lots", lot_id), ("locations", location_id)):
        with pytest.raises(IntegrityError), database_connection.begin_nested():
            database_connection.execute(text(f"DELETE FROM {table} WHERE id=:id"), {"id": item_id})
    database_connection.execute(text("DELETE FROM sowings WHERE id=:id"), {"id": retained_id})
    assert (
        database_connection.execute(
            text("SELECT quantity_value FROM seed_lots WHERE id=:id"), {"id": lot_id}
        ).scalar_one_or_none()
        is None
    )
    assert identity_id is not None
