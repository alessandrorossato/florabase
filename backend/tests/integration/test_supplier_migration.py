from datetime import UTC, datetime
from uuid import uuid7

import pytest
from alembic.config import Config
from sqlalchemy import Connection, Engine, inspect, text
from sqlalchemy.exc import DBAPIError

from alembic import command

pytestmark = pytest.mark.integration


def test_supplier_migration_upgrade_downgrade_and_reupgrade(database_engine: Engine) -> None:
    config = Config("alembic.ini")
    try:
        command.downgrade(config, "20260829_0004")
        assert not inspect(database_engine).has_table("suppliers")
        assert inspect(database_engine).has_table("botanical_identities")
        command.upgrade(config, "head")
        assert inspect(database_engine).has_table("suppliers")
        command.downgrade(config, "20260829_0004")
        assert not inspect(database_engine).has_table("suppliers")
    finally:
        command.upgrade(config, "head")
    assert inspect(database_engine).has_table("suppliers")


def test_supplier_schema_types_constraints_and_same_name_coexistence(
    database_connection: Connection,
) -> None:
    columns = {
        column["name"]: column for column in inspect(database_connection).get_columns("suppliers")
    }
    assert set(columns) == {
        "id",
        "name",
        "kind",
        "website",
        "email",
        "phone",
        "notes",
        "retired_at",
        "created_at",
        "updated_at",
    }
    assert columns["retired_at"]["nullable"] is True
    assert "TIMESTAMP" in str(columns["created_at"]["type"])
    assert not any(key in columns for key in ("user_id", "address", "geographic_origin"))

    now = datetime.now(UTC)
    for supplier_id, kind in ((uuid7(), "seller"), (uuid7(), "person")):
        database_connection.execute(
            text(
                "INSERT INTO suppliers (id, name, kind, created_at, updated_at) "
                "VALUES (:id, 'Shared name', :kind, :now, :now)"
            ),
            {"id": supplier_id, "kind": kind, "now": now},
        )
    assert (
        database_connection.execute(
            text("SELECT count(*) FROM suppliers WHERE name = 'Shared name'")
        ).scalar_one()
        == 2
    )

    invalid_rows = (
        {"name": " ", "kind": "seller"},
        {"name": "Unnormalized  name", "kind": "seller"},
        {"name": "Supplier", "kind": "wholesaler"},
        {"name": "Supplier", "kind": "seller", "website": "ftp://example.com"},
        {"name": "Supplier", "kind": "seller", "email": "bad email"},
        {"name": "Supplier", "kind": "seller", "notes": " surrounding "},
        {"name": "Supplier", "kind": "seller", "notes": "bad\x1fcontrol"},
    )
    for values in invalid_rows:
        with pytest.raises(DBAPIError), database_connection.begin_nested():
            database_connection.execute(
                text(
                    "INSERT INTO suppliers "
                    "(id, name, kind, website, email, notes, created_at, updated_at) "
                    "VALUES (:id, :name, :kind, :website, :email, :notes, :now, :now)"
                ),
                {
                    "id": uuid7(),
                    "website": None,
                    "email": None,
                    "notes": None,
                    "now": now,
                    **values,
                },
            )
