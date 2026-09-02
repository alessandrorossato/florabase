from datetime import UTC, datetime
from uuid import UUID, uuid7

import pytest
from alembic.config import Config
from sqlalchemy import Connection, Engine, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from alembic import command

pytestmark = pytest.mark.integration


def _insert_identity_and_group(connection: Connection) -> tuple[UUID, UUID]:
    identity_id = uuid7()
    group_id = uuid7()
    now = datetime.now(UTC)
    connection.execute(
        text(
            "INSERT INTO botanical_identities (id, scientific_name, created_at, updated_at) "
            "VALUES (:id, :name, :now, :now)"
        ),
        {"id": identity_id, "name": f"Migration {identity_id}", "now": now},
    )
    connection.execute(
        text(
            "INSERT INTO plant_groups "
            "(id, botanical_identity_id, direct_origin_kind, lifecycle, created_at, updated_at) "
            "VALUES (:id, :identity, 'unknown', 'active', :now, :now)"
        ),
        {"id": group_id, "identity": identity_id, "now": now},
    )
    return identity_id, group_id


def _insert_plant(
    connection: Connection, identity_id: UUID, group_id: UUID, **overrides: object
) -> UUID:
    plant_id = uuid7()
    values: dict[str, object] = {
        "id": plant_id,
        "botanical_identity_id": identity_id,
        "originating_plant_group_id": group_id,
        "direct_origin_kind": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        **overrides,
    }
    columns = ", ".join(values)
    parameters = ", ".join(f":{name}" for name in values)
    connection.execute(text(f"INSERT INTO plants ({columns}) VALUES ({parameters})"), values)
    return plant_id


def test_plant_extraction_migration_cycle(database_engine: Engine) -> None:
    config = Config("alembic.ini")
    try:
        command.downgrade(config, "20260901_0012")
        assert "originating_plant_group_id" not in {
            column["name"] for column in inspect(database_engine).get_columns("plants")
        }
        with database_engine.begin() as connection:
            identity_id, group_id = _insert_identity_and_group(connection)
        command.upgrade(config, "20260901_0013")
        inspector = inspect(database_engine)
        assert "originating_plant_group_id" in {
            column["name"] for column in inspector.get_columns("plants")
        }
        assert "ix_plants_originating_plant_group_id" in {
            index["name"] for index in inspector.get_indexes("plants")
        }
        assert (
            "plant_groups",
            ("originating_plant_group_id",),
            "RESTRICT",
        ) in {
            (
                foreign_key["referred_table"],
                tuple(foreign_key["constrained_columns"]),
                foreign_key["options"].get("ondelete"),
            )
            for foreign_key in inspector.get_foreign_keys("plants")
        }
        with database_engine.begin() as connection:
            _insert_plant(connection, identity_id, group_id)
            for invalid in (
                {"direct_origin_kind": "unknown"},
                {"supplier_id": uuid7()},
                {"material_provenance_place_id": uuid7()},
            ):
                with pytest.raises((DBAPIError, IntegrityError)), connection.begin_nested():
                    _insert_plant(connection, identity_id, group_id, **invalid)
        command.downgrade(config, "20260901_0012")
        assert "originating_plant_group_id" not in {
            column["name"] for column in inspect(database_engine).get_columns("plants")
        }
        command.upgrade(config, "20260901_0013")
        assert "originating_plant_group_id" in {
            column["name"] for column in inspect(database_engine).get_columns("plants")
        }
    finally:
        command.upgrade(config, "head")
