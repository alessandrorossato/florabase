from datetime import UTC, datetime
from uuid import UUID, uuid7

import pytest
from alembic.config import Config
from sqlalchemy import Connection, Engine, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from alembic import command

pytestmark = pytest.mark.integration


def _identity(connection: Connection, name: str = "Parent plant") -> UUID:
    item_id = uuid7()
    now = datetime.now(UTC)
    connection.execute(
        text(
            "INSERT INTO botanical_identities (id, scientific_name, created_at, updated_at) "
            "VALUES (:id, :name, :now, :now)"
        ),
        {"id": item_id, "name": f"{name} {item_id.hex}", "now": now},
    )
    return item_id


def _plant(connection: Connection, table: str, identity_id: UUID, lifecycle: str) -> UUID:
    item_id = uuid7()
    now = datetime.now(UTC)
    connection.execute(
        text(
            f"INSERT INTO {table} "
            "(id, botanical_identity_id, direct_origin_kind, lifecycle, created_at, updated_at) "
            "VALUES (:id, :identity_id, 'unknown', :lifecycle, :now, :now)"
        ),
        {"id": item_id, "identity_id": identity_id, "lifecycle": lifecycle, "now": now},
    )
    return item_id


def _lot(connection: Connection, identity_id: UUID, **overrides: object) -> UUID:
    item_id = uuid7()
    values: dict[str, object] = {
        "id": item_id,
        "botanical_identity_id": identity_id,
        "source_kind": "collection_produced",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        **overrides,
    }
    columns = ", ".join(values)
    parameters = ", ".join(f":{key}" for key in values)
    connection.execute(text(f"INSERT INTO seed_lots ({columns}) VALUES ({parameters})"), values)
    return item_id


def _reject_lot(connection: Connection, identity_id: UUID, **overrides: object) -> None:
    with pytest.raises(DBAPIError), connection.begin_nested():
        _lot(connection, identity_id, **overrides)


def test_lineage_migration_upgrade_downgrade_and_reupgrade(database_engine: Engine) -> None:
    config = Config("alembic.ini")
    try:
        command.downgrade(config, "20260831_0011")
        inspector = inspect(database_engine)
        columns = {item["name"] for item in inspector.get_columns("seed_lots")}
        assert "producer_plant_id" not in columns
        assert "producer_plant_group_id" not in columns

        command.upgrade(config, "20260901_0012")
        inspector = inspect(database_engine)
        columns = {item["name"] for item in inspector.get_columns("seed_lots")}
        assert {"producer_plant_id", "producer_plant_group_id"} <= columns
        assert {
            (
                item["referred_table"],
                tuple(item["constrained_columns"]),
                item["options"]["ondelete"],
            )
            for item in inspector.get_foreign_keys("seed_lots")
            if item["constrained_columns"][0].startswith("producer_")
        } == {
            ("plants", ("producer_plant_id",), "RESTRICT"),
            ("plant_groups", ("producer_plant_group_id",), "RESTRICT"),
        }
        assert {
            "ix_seed_lots_producer_plant_id",
            "ix_seed_lots_producer_plant_group_id",
        } <= {item["name"] for item in inspector.get_indexes("seed_lots")}
        assert {
            "ck_seed_lots_producer_exclusive",
            "ck_seed_lots_producer_source_kind",
        } <= {item["name"] for item in inspector.get_check_constraints("seed_lots")}

        command.downgrade(config, "20260831_0011")
        inspector = inspect(database_engine)
        columns = {item["name"] for item in inspector.get_columns("seed_lots")}
        assert "producer_plant_id" not in columns
        assert inspector.has_table("plants")
        assert inspector.has_table("plant_groups")
        command.upgrade(config, "20260901_0012")
    finally:
        command.upgrade(config, "head")
    assert "producer_plant_id" in {
        item["name"] for item in inspect(database_engine).get_columns("seed_lots")
    }


def test_lineage_database_invariants_and_restrictive_producers(
    database_connection: Connection,
) -> None:
    identity_id = _identity(database_connection)
    plant_id = _plant(database_connection, "plants", identity_id, "dead")
    group_id = _plant(database_connection, "plant_groups", identity_id, "completed")

    _lot(database_connection, identity_id)
    plant_lot_id = _lot(database_connection, identity_id, producer_plant_id=plant_id)
    group_lot_id = _lot(database_connection, identity_id, producer_plant_group_id=group_id)
    _reject_lot(
        database_connection,
        identity_id,
        producer_plant_id=plant_id,
        producer_plant_group_id=group_id,
    )
    for source_kind in (
        "purchased",
        "purchased_fruit",
        "self_collected",
        "gift_exchange",
        "other",
        "unknown",
    ):
        _reject_lot(
            database_connection,
            identity_id,
            source_kind=source_kind,
            producer_plant_id=plant_id,
        )
    _reject_lot(database_connection, identity_id, producer_plant_id=uuid7())
    _reject_lot(database_connection, identity_id, producer_plant_group_id=uuid7())

    for table, item_id in (("plants", plant_id), ("plant_groups", group_id)):
        with pytest.raises(IntegrityError), database_connection.begin_nested():
            database_connection.execute(text(f"DELETE FROM {table} WHERE id=:id"), {"id": item_id})
    database_connection.execute(
        text("DELETE FROM seed_lots WHERE id IN (:plant_lot, :group_lot)"),
        {"plant_lot": plant_lot_id, "group_lot": group_lot_id},
    )
