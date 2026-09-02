from datetime import UTC, datetime
from uuid import UUID, uuid7

import pytest
from alembic.config import Config
from sqlalchemy import Connection, Engine, inspect, text
from sqlalchemy.exc import DBAPIError

from alembic import command

pytestmark = pytest.mark.integration


def _plant(connection: Connection) -> UUID:
    identity_id = uuid7()
    plant_id = uuid7()
    now = datetime.now(UTC)
    connection.execute(
        text(
            "INSERT INTO botanical_identities (id, scientific_name, created_at, updated_at) "
            "VALUES (:id, :name, :now, :now)"
        ),
        {"id": identity_id, "name": f"Eventus {identity_id.hex}", "now": now},
    )
    connection.execute(
        text(
            "INSERT INTO plants "
            "(id, botanical_identity_id, direct_origin_kind, created_at, updated_at) "
            "VALUES (:id, :identity, 'unknown', :now, :now)"
        ),
        {"id": plant_id, "identity": identity_id, "now": now},
    )
    return plant_id


def _insert(connection: Connection, **overrides: object) -> UUID:
    event_id = uuid7()
    values: dict[str, object] = {
        "id": event_id,
        "kind": "observation",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        **overrides,
    }
    connection.execute(
        text(
            f"INSERT INTO events ({', '.join(values)}) "
            f"VALUES ({', '.join(f':{key}' for key in values)})"
        ),
        values,
    )
    return event_id


def _reject(connection: Connection, **overrides: object) -> None:
    with pytest.raises(DBAPIError), connection.begin_nested():
        _insert(connection, **overrides)


def test_event_migration_upgrade_downgrade_and_reupgrade(database_engine: Engine) -> None:
    config = Config("alembic.ini")
    try:
        command.downgrade(config, "20260901_0013")
        assert not inspect(database_engine).has_table("events")
        command.upgrade(config, "20260902_0014")
        inspector = inspect(database_engine)
        assert {item["name"] for item in inspector.get_columns("events")} == {
            "id",
            "plant_id",
            "plant_group_id",
            "kind",
            "occurred_on_precision",
            "occurred_on_year",
            "occurred_on_month",
            "occurred_on_day",
            "notes",
            "destination_location_id",
            "created_at",
            "updated_at",
        }
        assert {item["name"] for item in inspector.get_indexes("events")} == {
            "ix_events_plant_timeline",
            "ix_events_plant_group_timeline",
            "ix_events_destination_location_id",
        }
        assert {item["name"] for item in inspector.get_check_constraints("events")} == {
            "ck_events_exactly_one_target",
            "ck_events_kind",
            "ck_events_occurred_on",
            "ck_events_movement_destination",
            "ck_events_notes",
        }
        command.downgrade(config, "20260901_0013")
        assert not inspect(database_engine).has_table("events")
        command.upgrade(config, "20260902_0014")
    finally:
        command.upgrade(config, "head")
    assert inspect(database_engine).has_table("events")


def test_event_database_invariants_and_restrictive_references(
    database_connection: Connection,
) -> None:
    plant_id = _plant(database_connection)
    now = datetime.now(UTC)
    location_id = uuid7()
    database_connection.execute(
        text(
            "INSERT INTO locations (id, name, created_at, updated_at) "
            "VALUES (:id, 'Event destination', :now, :now)"
        ),
        {"id": location_id, "now": now},
    )
    for kind in (
        "observation",
        "repotting",
        "flowering",
        "fruiting",
        "pruning",
        "treatment",
        "harvest",
        "death",
        "loss",
        "discarded",
        "other",
    ):
        _insert(database_connection, plant_id=plant_id, kind=kind)
    movement_id = _insert(
        database_connection,
        plant_id=plant_id,
        kind="movement",
        destination_location_id=location_id,
    )
    for date_values in (
        {"occurred_on_precision": "year", "occurred_on_year": 2024},
        {"occurred_on_precision": "month", "occurred_on_year": 2024, "occurred_on_month": 5},
        {
            "occurred_on_precision": "day",
            "occurred_on_year": 2024,
            "occurred_on_month": 5,
            "occurred_on_day": 18,
        },
    ):
        _insert(database_connection, plant_id=plant_id, **date_values)
    _reject(database_connection)
    _reject(database_connection, plant_id=plant_id, plant_group_id=uuid7())
    _reject(database_connection, plant_id=plant_id, kind="watering")
    _reject(database_connection, plant_id=plant_id, kind="movement")
    _reject(database_connection, plant_id=plant_id, destination_location_id=location_id)
    _reject(database_connection, plant_id=plant_id, occurred_on_month=5)
    _reject(
        database_connection,
        plant_id=plant_id,
        occurred_on_precision="day",
        occurred_on_year=2023,
        occurred_on_month=2,
        occurred_on_day=29,
    )
    _reject(database_connection, plant_id=plant_id, notes=" bad ")
    _reject(database_connection, plant_id=uuid7())
    _reject(
        database_connection,
        plant_id=plant_id,
        kind="movement",
        destination_location_id=uuid7(),
    )
    with pytest.raises(DBAPIError), database_connection.begin_nested():
        database_connection.execute(text("DELETE FROM plants WHERE id = :id"), {"id": plant_id})
    with pytest.raises(DBAPIError), database_connection.begin_nested():
        database_connection.execute(
            text("DELETE FROM locations WHERE id = :id"), {"id": location_id}
        )
    database_connection.execute(text("DELETE FROM events WHERE id = :id"), {"id": movement_id})
