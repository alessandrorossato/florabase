from datetime import UTC, datetime
from uuid import uuid7

import pytest
from alembic.config import Config
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import DBAPIError

from alembic import command

pytestmark = pytest.mark.integration


def test_operation_receipt_migration_cycle_has_no_historical_backfill(
    database_engine: Engine,
) -> None:
    config = Config("alembic.ini")
    identity_id, plant_id, event_id, receipt_id = (uuid7() for _ in range(4))
    now = datetime.now(UTC)
    try:
        command.downgrade(config, "20260904_0015")
        assert not inspect(database_engine).has_table("operation_receipts")
        with database_engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO botanical_identities "
                    "(id, scientific_name, created_at, updated_at) "
                    "VALUES (:id, :name, :now, :now)"
                ),
                {"id": identity_id, "name": f"Historical {identity_id.hex}", "now": now},
            )
            connection.execute(
                text(
                    "INSERT INTO plants "
                    "(id, botanical_identity_id, direct_origin_kind, lifecycle, "
                    "created_at, updated_at) "
                    "VALUES (:id, :identity, 'unknown', 'transferred', :now, :now)"
                ),
                {"id": plant_id, "identity": identity_id, "now": now},
            )
            connection.execute(
                text(
                    "INSERT INTO events (id, plant_id, kind, created_at, updated_at) "
                    "VALUES (:id, :plant, 'transfer', :now, :now)"
                ),
                {"id": event_id, "plant": plant_id, "now": now},
            )

        command.upgrade(config, "20260905_0016")
        inspector = inspect(database_engine)
        assert inspector.has_table("operation_receipts")
        assert {
            "ck_operation_receipts_kind",
            "ck_operation_receipts_status",
            "ck_operation_receipts_adjustment_mode",
            "ck_operation_receipts_typed_references",
            "ck_operation_receipts_before_quantity",
            "ck_operation_receipts_after_quantity",
            "ck_operation_receipts_typed_state",
        } == {item["name"] for item in inspector.get_check_constraints("operation_receipts")}
        with database_engine.begin() as connection:
            assert (
                connection.execute(text("SELECT count(*) FROM operation_receipts")).scalar_one()
                == 0
            )
            connection.execute(
                text(
                    "INSERT INTO operation_receipts "
                    "(id, kind, status, plant_id, event_id, before_lifecycle, "
                    "after_lifecycle, created_at) VALUES "
                    "(:id, 'plant_transfer', 'applied', :plant, :event, "
                    "'dead', 'transferred', :now)"
                ),
                {"id": receipt_id, "plant": plant_id, "event": event_id, "now": now},
            )
            with pytest.raises(DBAPIError), connection.begin_nested():
                connection.execute(
                    text("UPDATE operation_receipts SET before_lifecycle = 'lost' WHERE id = :id"),
                    {"id": receipt_id},
                )
            connection.execute(
                text("UPDATE operation_receipts SET status = 'reversed' WHERE id = :id"),
                {"id": receipt_id},
            )
            with pytest.raises(DBAPIError), connection.begin_nested():
                connection.execute(
                    text(
                        "INSERT INTO operation_receipts "
                        "(id, kind, status, plant_id, before_lifecycle, after_lifecycle, "
                        "created_at) VALUES (:id, 'plant_transfer', 'applied', :plant, "
                        "'active', 'transferred', :now)"
                    ),
                    {"id": uuid7(), "plant": plant_id, "now": now},
                )

        command.downgrade(config, "20260904_0015")
        assert not inspect(database_engine).has_table("operation_receipts")
        command.upgrade(config, "20260905_0016")
        with database_engine.begin() as connection:
            assert (
                connection.execute(text("SELECT count(*) FROM operation_receipts")).scalar_one()
                == 0
            )
            connection.execute(text("DELETE FROM events WHERE id = :id"), {"id": event_id})
            connection.execute(text("DELETE FROM plants WHERE id = :id"), {"id": plant_id})
            connection.execute(
                text("DELETE FROM botanical_identities WHERE id = :id"), {"id": identity_id}
            )
    finally:
        command.upgrade(config, "head")
