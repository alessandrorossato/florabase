from datetime import UTC, datetime
from uuid import UUID, uuid7

import pytest
from alembic.config import Config
from sqlalchemy import Connection, Engine, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from alembic import command

pytestmark = pytest.mark.integration


def _references(connection: Connection) -> dict[str, UUID]:
    now = datetime.now(UTC)
    values = {
        name: uuid7() for name in ("identity", "lot", "sowing", "supplier", "place", "location")
    }
    connection.execute(
        text(
            "INSERT INTO botanical_identities (id, scientific_name, created_at, updated_at) "
            "VALUES (:id, :name, :now, :now)"
        ),
        {"id": values["identity"], "name": f"Planta {values['identity'].hex}", "now": now},
    )
    connection.execute(
        text(
            "INSERT INTO seed_lots (id, botanical_identity_id, created_at, updated_at) "
            "VALUES (:id, :identity, :now, :now)"
        ),
        {"id": values["lot"], "identity": values["identity"], "now": now},
    )
    connection.execute(
        text(
            "INSERT INTO sowings (id, seed_lot_id, lifecycle, created_at, updated_at) "
            "VALUES (:id, :lot, 'failed', :now, :now)"
        ),
        {"id": values["sowing"], "lot": values["lot"], "now": now},
    )
    connection.execute(
        text(
            "INSERT INTO suppliers (id, name, created_at, updated_at) "
            "VALUES (:id, 'Retired supplier', :now, :now)"
        ),
        {"id": values["supplier"], "now": now},
    )
    connection.execute(
        text(
            "INSERT INTO geographic_places "
            "(id, name, place_kind, retired_at, created_at, updated_at) "
            "VALUES (:id, 'Old provenance', 'custom', :now, :now, :now)"
        ),
        {"id": values["place"], "now": now},
    )
    connection.execute(
        text(
            "INSERT INTO locations (id, name, retired_at, created_at, updated_at) "
            "VALUES (:id, 'Old bench', :now, :now, :now)"
        ),
        {"id": values["location"], "now": now},
    )
    return values


def _insert(connection: Connection, table: str, identity: UUID, **overrides: object) -> UUID:
    item_id = uuid7()
    values: dict[str, object] = {
        "id": item_id,
        "botanical_identity_id": identity,
        "direct_origin_kind": "unknown",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        **overrides,
    }
    columns = ", ".join(values)
    parameters = ", ".join(f":{key}" for key in values)
    connection.execute(text(f"INSERT INTO {table} ({columns}) VALUES ({parameters})"), values)
    return item_id


def _reject(connection: Connection, table: str, identity: UUID, **overrides: object) -> None:
    with pytest.raises(DBAPIError), connection.begin_nested():
        _insert(connection, table, identity, **overrides)


def test_plant_migration_upgrade_downgrade_and_reupgrade(database_engine: Engine) -> None:
    config = Config("alembic.ini")
    try:
        command.downgrade(config, "20260831_0010")
        inspector = inspect(database_engine)
        assert not inspector.has_table("plants")
        assert not inspector.has_table("plant_groups")
        assert inspector.has_table("sowings")
        assert inspector.has_table("seed_lots")
        command.upgrade(config, "20260831_0011")
        inspector = inspect(database_engine)
        plant_columns = {item["name"] for item in inspector.get_columns("plants")}
        group_columns = {item["name"] for item in inspector.get_columns("plant_groups")}
        assert plant_columns == {
            "id",
            "botanical_identity_id",
            "originating_sowing_id",
            "direct_origin_kind",
            "direct_origin_detail",
            "supplier_id",
            "material_provenance_place_id",
            "label",
            "collection_entry_date_precision",
            "collection_entry_date_year",
            "collection_entry_date_month",
            "collection_entry_date_day",
            "location_id",
            "lifecycle",
            "notes",
            "created_at",
            "updated_at",
        }
        assert group_columns == plant_columns | {"quantity_value", "quantity_is_approximate"}
        for table in ("plants", "plant_groups"):
            assert {item["name"] for item in inspector.get_indexes(table)} == {
                f"ix_{table}_{column}"
                for column in (
                    "botanical_identity_id",
                    "originating_sowing_id",
                    "supplier_id",
                    "material_provenance_place_id",
                    "location_id",
                    "lifecycle",
                )
            }
            assert {
                (item["referred_table"], tuple(item["constrained_columns"]))
                for item in inspector.get_foreign_keys(table)
            } == {
                ("botanical_identities", ("botanical_identity_id",)),
                ("sowings", ("originating_sowing_id",)),
                ("suppliers", ("supplier_id",)),
                ("geographic_places", ("material_provenance_place_id",)),
                ("locations", ("location_id",)),
            }
        command.downgrade(config, "20260831_0010")
        inspector = inspect(database_engine)
        assert not inspector.has_table("plants")
        assert not inspector.has_table("plant_groups")
        assert inspector.has_table("sowings")
        command.upgrade(config, "20260831_0011")
    finally:
        command.upgrade(config, "head")
    assert inspect(database_engine).has_table("plants")
    assert inspect(database_engine).has_table("plant_groups")


def test_plant_database_invariants_and_restrictive_references(
    database_connection: Connection,
) -> None:
    refs = _references(database_connection)
    for table in ("plants", "plant_groups"):
        _insert(database_connection, table, refs["identity"])
        _insert(
            database_connection,
            table,
            refs["identity"],
            direct_origin_kind="other",
            direct_origin_detail="garden exchange",
            supplier_id=refs["supplier"],
            material_provenance_place_id=refs["place"],
            location_id=refs["location"],
        )
        _insert(
            database_connection,
            table,
            refs["identity"],
            direct_origin_kind=None,
            originating_sowing_id=refs["sowing"],
        )
        _reject(database_connection, table, refs["identity"], direct_origin_kind="self_collected")
        _reject(
            database_connection,
            table,
            refs["identity"],
            originating_sowing_id=refs["sowing"],
            direct_origin_kind="unknown",
        )
        _reject(
            database_connection,
            table,
            refs["identity"],
            direct_origin_kind="purchased",
            direct_origin_detail="invalid",
        )
        _reject(database_connection, table, refs["identity"], label=" bad  spacing ")
        _reject(database_connection, table, refs["identity"], notes="bad\rcontrol")
        _reject(database_connection, table, uuid7())
        _reject(
            database_connection,
            table,
            refs["identity"],
            originating_sowing_id=uuid7(),
            direct_origin_kind=None,
        )
        _reject(database_connection, table, refs["identity"], supplier_id=uuid7())
        _reject(database_connection, table, refs["identity"], material_provenance_place_id=uuid7())
        _reject(database_connection, table, refs["identity"], location_id=uuid7())
        for invalid_date in (
            {"collection_entry_date_month": 5},
            {"collection_entry_date_precision": "month", "collection_entry_date_year": 2024},
            {
                "collection_entry_date_precision": "day",
                "collection_entry_date_year": 2023,
                "collection_entry_date_month": 2,
                "collection_entry_date_day": 29,
            },
        ):
            _reject(database_connection, table, refs["identity"], **invalid_date)
        for valid_date in (
            {"collection_entry_date_precision": "year", "collection_entry_date_year": 2024},
            {
                "collection_entry_date_precision": "month",
                "collection_entry_date_year": 2024,
                "collection_entry_date_month": 5,
            },
            {
                "collection_entry_date_precision": "day",
                "collection_entry_date_year": 2024,
                "collection_entry_date_month": 5,
                "collection_entry_date_day": 18,
            },
        ):
            _insert(database_connection, table, refs["identity"], **valid_date)

    for lifecycle in ("active", "dead", "lost", "discarded"):
        _insert(database_connection, "plants", refs["identity"], lifecycle=lifecycle)
    _reject(database_connection, "plants", refs["identity"], lifecycle="completed")
    for lifecycle in ("active", "completed", "dead", "lost", "discarded"):
        _insert(database_connection, "plant_groups", refs["identity"], lifecycle=lifecycle)
    _reject(database_connection, "plant_groups", refs["identity"], lifecycle="failed")
    for lifecycle in ("completed", "dead", "discarded"):
        _insert(
            database_connection,
            "plant_groups",
            refs["identity"],
            lifecycle=lifecycle,
            quantity_value=0,
            quantity_is_approximate=False,
        )
    for invalid_quantity in (
        {"quantity_value": 1},
        {"quantity_is_approximate": False},
        {"quantity_value": -1, "quantity_is_approximate": False},
        {"quantity_value": 0, "quantity_is_approximate": True, "lifecycle": "dead"},
        {"quantity_value": 0, "quantity_is_approximate": False, "lifecycle": "active"},
        {"quantity_value": 0, "quantity_is_approximate": False, "lifecycle": "lost"},
    ):
        _reject(database_connection, "plant_groups", refs["identity"], **invalid_quantity)
    _insert(
        database_connection,
        "plant_groups",
        refs["identity"],
        quantity_value=12,
        quantity_is_approximate=False,
    )
    _insert(
        database_connection,
        "plant_groups",
        refs["identity"],
        lifecycle="lost",
        quantity_value=8,
        quantity_is_approximate=True,
    )

    retained = _insert(
        database_connection,
        "plants",
        refs["identity"],
        direct_origin_kind=None,
        originating_sowing_id=refs["sowing"],
        location_id=refs["location"],
    )
    for table, item_id in (
        ("botanical_identities", refs["identity"]),
        ("sowings", refs["sowing"]),
        ("locations", refs["location"]),
    ):
        with pytest.raises(IntegrityError), database_connection.begin_nested():
            database_connection.execute(text(f"DELETE FROM {table} WHERE id=:id"), {"id": item_id})
    database_connection.execute(text("DELETE FROM plants WHERE id=:id"), {"id": retained})
