from datetime import UTC, datetime
from uuid import uuid7

import pytest
from alembic.config import Config
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import DBAPIError

from alembic import command

pytestmark = pytest.mark.integration


def test_plant_transfer_migration_cycle_preserves_old_rows(database_engine: Engine) -> None:
    config = Config("alembic.ini")
    try:
        command.downgrade(config, "20260902_0014")
        before = inspect(database_engine)
        assert "recipient" not in {column["name"] for column in before.get_columns("events")}
        command.upgrade(config, "20260904_0015")
        upgraded = inspect(database_engine)
        assert {"recipient", "resulting_plant_id"} <= {
            column["name"] for column in upgraded.get_columns("events")
        }
        assert "ix_events_resulting_plant_id" in {
            index["name"] for index in upgraded.get_indexes("events")
        }
        assert {"ck_events_transfer_recipient", "ck_events_extraction_result"} <= {
            constraint["name"] for constraint in upgraded.get_check_constraints("events")
        }
        assert "uq_plants_id_originating_plant_group_id" in {
            constraint["name"] for constraint in upgraded.get_unique_constraints("plants")
        }
        assert any(
            foreign_key["name"] == "fk_events_resulting_plant_source_group"
            and foreign_key["constrained_columns"] == ["resulting_plant_id", "plant_group_id"]
            for foreign_key in upgraded.get_foreign_keys("events")
        )

        now = datetime.now(UTC)
        identity_id, plant_id, group_id, extracted_id = (uuid7() for _ in range(4))
        transfer_id, extraction_id = uuid7(), uuid7()
        with database_engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO botanical_identities "
                    "(id, scientific_name, created_at, updated_at) "
                    "VALUES (:id, :name, :now, :now)"
                ),
                {"id": identity_id, "name": f"Transfer {identity_id.hex}", "now": now},
            )
            connection.execute(
                text(
                    "INSERT INTO plant_groups "
                    "(id, botanical_identity_id, direct_origin_kind, quantity_value, "
                    "quantity_is_approximate, lifecycle, created_at, updated_at) "
                    "VALUES (:id, :identity, 'unknown', 4, false, 'transferred', :now, :now)"
                ),
                {"id": group_id, "identity": identity_id, "now": now},
            )
            for item_id, lifecycle, origin_group in (
                (plant_id, "transferred", None),
                (extracted_id, "active", group_id),
            ):
                connection.execute(
                    text(
                        "INSERT INTO plants "
                        "(id, botanical_identity_id, originating_plant_group_id, "
                        "direct_origin_kind, lifecycle, created_at, updated_at) "
                        "VALUES (:id, :identity, :group_id, :origin, :lifecycle, :now, :now)"
                    ),
                    {
                        "id": item_id,
                        "identity": identity_id,
                        "group_id": origin_group,
                        "origin": None if origin_group else "unknown",
                        "lifecycle": lifecycle,
                        "now": now,
                    },
                )
            connection.execute(
                text(
                    "INSERT INTO events "
                    "(id, plant_id, kind, recipient, created_at, updated_at) "
                    "VALUES (:id, :plant, 'transfer', 'Community garden', :now, :now)"
                ),
                {"id": transfer_id, "plant": plant_id, "now": now},
            )
            connection.execute(
                text(
                    "INSERT INTO events "
                    "(id, plant_group_id, kind, resulting_plant_id, created_at, updated_at) "
                    "VALUES (:id, :group_id, 'extraction', :plant, :now, :now)"
                ),
                {
                    "id": extraction_id,
                    "group_id": group_id,
                    "plant": extracted_id,
                    "now": now,
                },
            )

        command.downgrade(config, "20260902_0014")
        downgraded = inspect(database_engine)
        assert "recipient" not in {column["name"] for column in downgraded.get_columns("events")}
        with database_engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT lifecycle FROM plants WHERE id = :id"), {"id": plant_id}
                ).scalar_one()
                == "active"
            )
            assert (
                connection.execute(
                    text("SELECT lifecycle FROM plant_groups WHERE id = :id"), {"id": group_id}
                ).scalar_one()
                == "active"
            )
            assert set(
                connection.execute(
                    text("SELECT kind FROM events WHERE id IN (:transfer, :extraction)"),
                    {"transfer": transfer_id, "extraction": extraction_id},
                ).scalars()
            ) == {"other"}
        command.upgrade(config, "20260904_0015")
        with database_engine.begin() as connection:
            connection.execute(
                text("DELETE FROM events WHERE id IN (:transfer, :extraction)"),
                {"transfer": transfer_id, "extraction": extraction_id},
            )
            connection.execute(
                text("DELETE FROM plants WHERE id IN (:plant, :extracted)"),
                {"plant": plant_id, "extracted": extracted_id},
            )
            connection.execute(text("DELETE FROM plant_groups WHERE id = :id"), {"id": group_id})
            connection.execute(
                text("DELETE FROM botanical_identities WHERE id = :id"),
                {"id": identity_id},
            )
    finally:
        command.upgrade(config, "head")


def test_plant_transfer_database_constraints_are_focused(database_engine: Engine) -> None:
    now = datetime.now(UTC)
    identity_id, plant_id, group_id, extracted_id = (uuid7() for _ in range(4))
    with database_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO botanical_identities (id, scientific_name, created_at, updated_at) "
                "VALUES (:id, :name, :now, :now)"
            ),
            {"id": identity_id, "name": f"Constraint {identity_id.hex}", "now": now},
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
                "INSERT INTO plant_groups "
                "(id, botanical_identity_id, direct_origin_kind, quantity_value, "
                "quantity_is_approximate, lifecycle, created_at, updated_at) "
                "VALUES (:id, :identity, 'unknown', 6, false, 'transferred', :now, :now)"
            ),
            {"id": group_id, "identity": identity_id, "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO plants "
                "(id, botanical_identity_id, originating_plant_group_id, lifecycle, "
                "created_at, updated_at) "
                "VALUES (:id, :identity, :group_id, 'active', :now, :now)"
            ),
            {"id": extracted_id, "identity": identity_id, "group_id": group_id, "now": now},
        )
        with pytest.raises(DBAPIError), connection.begin_nested():
            connection.execute(
                text(
                    "INSERT INTO events (id, plant_id, kind, recipient, created_at, updated_at) "
                    "VALUES (:id, :plant, 'observation', 'Invalid', :now, :now)"
                ),
                {"id": uuid7(), "plant": plant_id, "now": now},
            )
        with pytest.raises(DBAPIError), connection.begin_nested():
            connection.execute(
                text(
                    "INSERT INTO events (id, plant_group_id, kind, created_at, updated_at) "
                    "VALUES (:id, :group_id, 'extraction', :now, :now)"
                ),
                {"id": uuid7(), "group_id": group_id, "now": now},
            )
        with pytest.raises(DBAPIError), connection.begin_nested():
            connection.execute(
                text(
                    "INSERT INTO events "
                    "(id, plant_group_id, kind, resulting_plant_id, created_at, updated_at) "
                    "VALUES (:id, :group_id, 'extraction', :plant_id, :now, :now)"
                ),
                {"id": uuid7(), "group_id": group_id, "plant_id": plant_id, "now": now},
            )
        connection.execute(
            text(
                "INSERT INTO events "
                "(id, plant_group_id, kind, resulting_plant_id, created_at, updated_at) "
                "VALUES (:id, :group_id, 'extraction', :plant_id, :now, :now)"
            ),
            {"id": uuid7(), "group_id": group_id, "plant_id": extracted_id, "now": now},
        )
        connection.execute(text("DELETE FROM events WHERE plant_group_id = :id"), {"id": group_id})
        connection.execute(
            text("DELETE FROM plants WHERE id IN (:plant, :extracted)"),
            {"plant": plant_id, "extracted": extracted_id},
        )
        connection.execute(text("DELETE FROM plant_groups WHERE id = :id"), {"id": group_id})
        connection.execute(
            text("DELETE FROM botanical_identities WHERE id = :id"),
            {"id": identity_id},
        )
