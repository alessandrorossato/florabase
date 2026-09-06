from uuid import uuid7

import pytest
from alembic.config import Config
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import DBAPIError

from alembic import command

pytestmark = pytest.mark.integration


def test_plant_reintegration_migration_cycle_and_constraints(database_engine: Engine) -> None:
    config = Config("alembic.ini")
    try:
        command.downgrade(config, "20260905_0016")
        before = inspect(database_engine)
        assert "reversed_operation_receipt_id" not in {
            column["name"] for column in before.get_columns("events")
        }

        command.upgrade(config, "20260905_0017")
        upgraded = inspect(database_engine)
        assert "reversed_operation_receipt_id" in {
            column["name"] for column in upgraded.get_columns("events")
        }
        assert {
            "ck_events_reintegration_receipt",
            "ck_events_extraction_result",
            "ck_events_kind",
        } <= {item["name"] for item in upgraded.get_check_constraints("events")}
        assert "uq_events_reversed_operation_receipt_id" in {
            item["name"] for item in upgraded.get_unique_constraints("events")
        }
        assert any(
            item["name"] == "fk_events_reversed_operation_receipt_id"
            and item["referred_table"] == "operation_receipts"
            for item in upgraded.get_foreign_keys("events")
        )

        with (
            database_engine.begin() as connection,
            pytest.raises(DBAPIError),
            connection.begin_nested(),
        ):
            connection.execute(
                text(
                    "INSERT INTO events "
                    "(id, plant_group_id, kind, created_at, updated_at) "
                    "VALUES (:id, :group_id, 'reintegration', now(), now())"
                ),
                {"id": uuid7(), "group_id": uuid7()},
            )

        command.downgrade(config, "20260905_0016")
        command.upgrade(config, "20260905_0017")
    finally:
        command.upgrade(config, "head")
