from uuid import uuid7

import pytest
from alembic.config import Config
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import DBAPIError

from alembic import command

pytestmark = pytest.mark.integration


def test_snapshot_migration_cycle_no_backfill_immutability_and_safe_downgrade(
    database_engine: Engine,
) -> None:
    config = Config("alembic.ini")
    identity, lot, sowing, receipt = (uuid7() for _ in range(4))
    try:
        command.downgrade(config, "20260905_0017")
        with database_engine.begin() as db:
            db.execute(
                text(
                    "INSERT INTO botanical_identities (id, scientific_name, created_at"
                    ", updated_at) VALUES (:id, 'Legacy propagation', now(), now())"
                ),
                {"id": identity},
            )
            db.execute(
                text(
                    "INSERT INTO seed_lots (id, botanical_identity_id, source_kind, li"
                    "fecycle, created_at, updated_at) VALUES (:id, :identity, 'unknown"
                    "', 'active', now(), now())"
                ),
                {"id": lot, "identity": identity},
            )
            db.execute(
                text(
                    "INSERT INTO sowings (id, seed_lot_id, lifecycle, created_at, upda"
                    "ted_at) VALUES (:id, :lot, 'active', now(), now())"
                ),
                {"id": sowing, "lot": lot},
            )
            db.execute(
                text(
                    "INSERT INTO operation_receipts (id, kind, status, seed_lot_id, so"
                    "wing_id, adjustment_mode, before_lifecycle, after_lifecycle, crea"
                    "ted_at) VALUES (:id, 'seed_lot_to_sowing', 'applied', :lot, :sowi"
                    "ng, 'none', 'active', 'active', now())"
                ),
                {"id": receipt, "lot": lot, "sowing": sowing},
            )
        command.upgrade(config, "head")
        assert "result_snapshot_version" in {
            c["name"] for c in inspect(database_engine).get_columns("operation_receipts")
        }
        with database_engine.begin() as db:
            assert (
                db.scalar(
                    text("SELECT result_snapshot_version FROM operation_receipts WHERE id = :id"),
                    {"id": receipt},
                )
                is None
            )
            with pytest.raises(DBAPIError, match="immutable"), db.begin_nested():
                db.execute(
                    text(
                        "UPDATE operation_receipts SET result_snapshot_version = 1, result"
                        "_lifecycle = 'active' WHERE id = :id"
                    ),
                    {"id": receipt},
                )
        command.downgrade(config, "20260905_0017")
        command.upgrade(config, "head")
        with database_engine.begin() as db:
            db.execute(
                text("UPDATE sowings SET lifecycle = 'reversed' WHERE id = :id"), {"id": sowing}
            )
        with pytest.raises(DBAPIError, match="propagation history"):
            command.downgrade(config, "20260905_0017")
        with database_engine.begin() as db:
            db.execute(
                text("UPDATE sowings SET lifecycle = 'active' WHERE id = :id"), {"id": sowing}
            )
            # New snapshot evidence cannot be discarded on downgrade.
            db.execute(text("DELETE FROM operation_receipts WHERE id = :id"), {"id": receipt})
            db.execute(
                text(
                    "INSERT INTO operation_receipts (id, kind, status, seed_lot_id, so"
                    "wing_id, adjustment_mode, before_lifecycle, after_lifecycle, crea"
                    "ted_at, result_snapshot_version, result_lifecycle) VALUES (:id, '"
                    "seed_lot_to_sowing', 'applied', :lot, :sowing, 'none', 'active', "
                    "'active', now(), 1, 'active')"
                ),
                {"id": receipt, "lot": lot, "sowing": sowing},
            )
            with pytest.raises(DBAPIError, match="immutable"), db.begin_nested():
                db.execute(
                    text(
                        "UPDATE operation_receipts SET result_lifecycle = 'completed' "
                        "WHERE id = :id"
                    ),
                    {"id": receipt},
                )
            with pytest.raises(DBAPIError), db.begin_nested():
                db.execute(
                    text(
                        "INSERT INTO operation_receipts (id, kind, status, seed_lot_id, so"
                        "wing_id, adjustment_mode, before_lifecycle, after_lifecycle, crea"
                        "ted_at, result_snapshot_version) VALUES (:id, 'seed_lot_to_sowing"
                        "', 'applied', :lot, :sowing, 'none', 'active', 'active', now(), 1"
                        ")"
                    ),
                    {"id": uuid7(), "lot": lot, "sowing": sowing},
                )
        with pytest.raises(DBAPIError, match="propagation history"):
            command.downgrade(config, "20260905_0017")
    finally:
        command.upgrade(config, "head")
        with database_engine.begin() as db:
            for table, key in (
                ("operation_receipts", receipt),
                ("sowings", sowing),
                ("seed_lots", lot),
                ("botanical_identities", identity),
            ):
                db.execute(text(f"DELETE FROM {table} WHERE id = :id"), {"id": key})
