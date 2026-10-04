import pytest
from alembic.config import Config
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from alembic import command
from florabase.harvests.inventory_schemas import InventoryWrite
from florabase.harvests.inventory_service import remove_tracking, track
from florabase.harvests.service import delete_harvest

from .test_harvest_inventory import q

pytestmark = pytest.mark.integration


def test_no_backfill_empty_cycle_and_populated_downgrade_guard(database_engine: Engine) -> None:
    config = Config("alembic.ini")
    command.downgrade(config, "20261002_0030")
    harvest_id = inventory_id = None
    try:
        # Previous revision has no new Location column; use SQL for the historical fixture.
        with database_engine.begin() as conn:
            from uuid import uuid7

            ids = {key: uuid7() for key in ("identity", "plant", "event", "harvest", "item")}
            conn.execute(
                text(
                    "INSERT INTO botanical_identities "
                    "(id,scientific_name,created_at,updated_at) VALUES "
                    "(:identity,'Inventory migration species',now(),now())"
                ),
                ids,
            )
            conn.execute(
                text(
                    "INSERT INTO plants "
                    "(id,botanical_identity_id,direct_origin_kind,lifecycle,created_at,updated_at)"
                    " VALUES (:plant,:identity,'unknown','dead',now(),now())"
                ),
                ids,
            )
            conn.execute(
                text(
                    "INSERT INTO events (id,plant_id,kind,created_at,updated_at) "
                    "VALUES (:event,:plant,'harvest',now(),now())"
                ),
                ids,
            )
            conn.execute(
                text(
                    "INSERT INTO harvests (id,plant_id,event_id,created_at,updated_at)"
                    " VALUES (:harvest,:plant,:event,now(),now())"
                ),
                ids,
            )
            conn.execute(
                text(
                    "INSERT INTO harvest_items "
                    "(id,harvest_id,material_kind,display_order,quantity_kind,quantity_value,quantity_is_approximate)"
                    " VALUES (:item,:harvest,'seed',0,'item_count',10,false)"
                ),
                ids,
            )
            harvest_id = ids["harvest"]
            item_id = ids["item"]
            event_id = ids["event"]
        command.upgrade(config, "head")
        with database_engine.connect() as conn:
            assert conn.scalar(text("SELECT count(*) FROM harvest_material_inventory")) == 0
            assert (
                conn.scalar(
                    text("SELECT quantity_value FROM harvest_items WHERE id=:id"), {"id": item_id}
                )
                == 10
            )
            assert (
                conn.scalar(text("SELECT event_id FROM harvests WHERE id=:id"), {"id": harvest_id})
                == event_id
            )
        command.downgrade(config, "20261002_0030")
        command.upgrade(config, "head")
        with Session(database_engine) as db:
            inventory = track(db, item_id, InventoryWrite(state="active", quantity=q("8")))
            db.commit()
            inventory_id = inventory.id
        with pytest.raises(RuntimeError, match="cannot be discarded"):
            command.downgrade(config, "20261002_0030")
        with database_engine.connect() as conn:
            assert (
                conn.scalar(
                    text("SELECT quantity_value FROM harvest_material_inventory WHERE id=:id"),
                    {"id": inventory_id},
                )
                == 8
            )
    finally:
        command.upgrade(config, "head")
        with Session(database_engine) as db:
            if inventory_id:
                remove_tracking(db, inventory_id)
            if harvest_id:
                delete_harvest(db, harvest_id)
            db.execute(text("DELETE FROM plants WHERE id=:id"), {"id": ids["plant"]})
            db.execute(
                text("DELETE FROM botanical_identities WHERE id=:id"), {"id": ids["identity"]}
            )
            db.commit()
