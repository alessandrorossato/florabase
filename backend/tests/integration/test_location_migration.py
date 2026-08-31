from datetime import UTC, datetime
from uuid import uuid7

import pytest
from alembic.config import Config
from sqlalchemy import Connection, Engine, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from alembic import command

pytestmark = pytest.mark.integration


def test_location_migration_upgrade_downgrade_and_reupgrade(database_engine: Engine) -> None:
    config = Config("alembic.ini")
    try:
        command.downgrade(config, "20260830_0005")
        assert not inspect(database_engine).has_table("locations")
        assert inspect(database_engine).has_table("suppliers")
        command.upgrade(config, "head")
        assert inspect(database_engine).has_table("locations")
        command.downgrade(config, "20260830_0005")
        assert not inspect(database_engine).has_table("locations")
    finally:
        command.upgrade(config, "head")
    assert inspect(database_engine).has_table("locations")


def test_location_schema_constraints_foreign_key_and_same_names(
    database_connection: Connection,
) -> None:
    columns = {
        column["name"]: column for column in inspect(database_connection).get_columns("locations")
    }
    assert set(columns) == {
        "id",
        "name",
        "parent_id",
        "retired_at",
        "created_at",
        "updated_at",
    }
    assert columns["parent_id"]["nullable"] is True
    assert columns["retired_at"]["nullable"] is True
    assert "TIMESTAMP" in str(columns["created_at"]["type"])
    assert "user_id" not in columns

    now = datetime.now(UTC)
    first_root = uuid7()
    second_root = uuid7()
    for location_id in (first_root, second_root):
        database_connection.execute(
            text(
                "INSERT INTO locations (id, name, created_at, updated_at) "
                "VALUES (:id, 'Greenhouse', :now, :now)"
            ),
            {"id": location_id, "now": now},
        )
    for parent_id in (first_root, second_root):
        database_connection.execute(
            text(
                "INSERT INTO locations (id, name, parent_id, created_at, updated_at) "
                "VALUES (:id, 'Shelf 1', :parent_id, :now, :now)"
            ),
            {"id": uuid7(), "parent_id": parent_id, "now": now},
        )
    assert (
        database_connection.execute(
            text("SELECT count(*) FROM locations WHERE name = 'Shelf 1'")
        ).scalar_one()
        == 2
    )

    for name in (" ", "Unnormalized  name", "Bad\x1fname"):
        with pytest.raises(DBAPIError), database_connection.begin_nested():
            database_connection.execute(
                text(
                    "INSERT INTO locations (id, name, created_at, updated_at) "
                    "VALUES (:id, :name, :now, :now)"
                ),
                {"id": uuid7(), "name": name, "now": now},
            )

    self_id = uuid7()
    with pytest.raises(DBAPIError), database_connection.begin_nested():
        database_connection.execute(
            text(
                "INSERT INTO locations (id, name, parent_id, created_at, updated_at) "
                "VALUES (:id, 'Self', :id, :now, :now)"
            ),
            {"id": self_id, "now": now},
        )
    with pytest.raises(IntegrityError), database_connection.begin_nested():
        database_connection.execute(
            text(
                "INSERT INTO locations (id, name, parent_id, created_at, updated_at) "
                "VALUES (:id, 'Orphan', :parent_id, :now, :now)"
            ),
            {"id": uuid7(), "parent_id": uuid7(), "now": now},
        )
    with pytest.raises(IntegrityError), database_connection.begin_nested():
        database_connection.execute(
            text("DELETE FROM locations WHERE id = :id"), {"id": first_root}
        )
