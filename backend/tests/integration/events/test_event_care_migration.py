"""PostgreSQL migration cycle tests for 20261125_0049 (event care kinds and batch_id)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid7

import pytest
from alembic.config import Config
from sqlalchemy import Connection, create_engine, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from florabase.core.config import get_settings

pytestmark = pytest.mark.integration

BACKEND_ROOT = Path(__file__).resolve().parents[3]
PREVIOUS_REVISION = "20261123_0048"
TARGET_REVISION = "20261125_0049"


def _alembic_config() -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return config


def _insert_plant(connection: Connection) -> object:
    now = datetime.now(UTC)
    identity_id = uuid7()
    plant_id = uuid7()
    connection.execute(
        text(
            "INSERT INTO botanical_identities (id, scientific_name, created_at, updated_at) "
            "VALUES (:id, 'Hoya carnosa', :now, :now)"
        ),
        {"id": identity_id, "now": now},
    )
    connection.execute(
        text(
            "INSERT INTO plants "
            "(id, botanical_identity_id, label, direct_origin_kind, lifecycle, "
            "created_at, updated_at) "
            "VALUES (:id, :identity_id, 'Migration test plant', 'unknown', 'active', :now, :now)"
        ),
        {"id": plant_id, "identity_id": identity_id, "now": now},
    )
    return plant_id


def test_event_care_migration_preserves_data_and_guards_downgrade() -> None:
    """FN-03 migration cycle: existing events survive; new kinds block downgrade."""
    settings = get_settings()
    config = _alembic_config()
    engine = create_engine(settings.database_url)

    try:
        # Start cleanly at 20261123_0048 with existing events present.
        command.downgrade(config, PREVIOUS_REVISION)
        with engine.begin() as conn:
            plant_id = _insert_plant(conn)
            existing_obs_id = uuid7()
            existing_repot_id = uuid7()
            now = datetime.now(UTC)
            for eid, kind, note in (
                (existing_obs_id, "observation", "Before 0049"),
                (existing_repot_id, "repotting", "Repotted before 0049"),
            ):
                conn.execute(
                    text(
                        "INSERT INTO events (id, plant_id, kind, notes, created_at, updated_at) "
                        "VALUES (:id, :plant_id, :kind, :notes, :now, :now)"
                    ),
                    {"id": eid, "plant_id": plant_id, "kind": kind, "notes": note, "now": now},
                )

        # Upgrade to 20261125_0049: existing events remain intact with batch_id NULL.
        command.upgrade(config, TARGET_REVISION)
        batch_id = uuid7()
        watering_id = uuid7()
        feeding_id = uuid7()
        with engine.begin() as conn:
            rows = conn.execute(
                text("SELECT id, kind, batch_id FROM events WHERE id IN (:a, :b)"),
                {"a": existing_obs_id, "b": existing_repot_id},
            ).fetchall()
            assert len(rows) == 2
            assert all(row.batch_id is None for row in rows)

            # Partial index exists.
            idx = conn.execute(
                text(
                    "SELECT indexdef FROM pg_indexes "
                    "WHERE tablename = 'events' AND indexname = 'ix_events_batch_id'"
                )
            ).scalar_one()
            assert "WHERE (batch_id IS NOT NULL)" in idx

            # New kinds watering and feeding + batch_id insert cleanly.
            now = datetime.now(UTC)
            for eid, kind in ((watering_id, "watering"), (feeding_id, "feeding")):
                conn.execute(
                    text(
                        "INSERT INTO events "
                        "(id, plant_id, kind, batch_id, notes, created_at, updated_at) "
                        "VALUES (:id, :plant_id, :kind, :batch_id, 'Care log', :now, :now)"
                    ),
                    {
                        "id": eid,
                        "plant_id": plant_id,
                        "kind": kind,
                        "batch_id": batch_id,
                        "now": now,
                    },
                )

        # Downgrade must refuse while watering or feeding events exist.
        with pytest.raises(RuntimeError, match="Watering or feeding Events exist"):
            command.downgrade(config, PREVIOUS_REVISION)

        # Remove watering/feeding events; downgrade succeeds and preserves pre-existing events.
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM events WHERE id IN (:w, :f)"),
                {"w": watering_id, "f": feeding_id},
            )

        command.downgrade(config, PREVIOUS_REVISION)
        with engine.begin() as conn:
            col = conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'events' AND column_name = 'batch_id'"
                )
            ).scalar_one_or_none()
            assert col is None
            surviving = conn.execute(
                text("SELECT COUNT(*) FROM events WHERE id IN (:a, :b)"),
                {"a": existing_obs_id, "b": existing_repot_id},
            ).scalar_one()
            assert surviving == 2
            # Old ck_events_kind rejects watering again.
            with pytest.raises(IntegrityError):
                conn.execute(
                    text(
                        "INSERT INTO events (id, plant_id, kind, created_at, updated_at) "
                        "VALUES (:id, :plant_id, 'watering', :now, :now)"
                    ),
                    {"id": uuid7(), "plant_id": plant_id, "now": datetime.now(UTC)},
                )
    finally:
        # Restore DB to head and remove synthetic rows so later tests start clean.
        command.upgrade(config, "head")
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM events"))
            conn.execute(text("DELETE FROM plants"))
            conn.execute(text("DELETE FROM botanical_identities"))
        engine.dispose()
