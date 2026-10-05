import pytest
from alembic.config import Config
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from alembic import command
from florabase.harvests.conversion_model import HarvestSeedLotConversion
from florabase.harvests.conversion_service import create
from florabase.seed_lots.schemas import SeedLotCreate
from florabase.seed_lots.service import create_seed_lot

from .test_harvest_inventory import setup
from .test_harvest_seed_conversion import payload

pytestmark = pytest.mark.integration


def test_empty_cycle_no_backfill_and_populated_guard(database_engine: Engine) -> None:
    config = Config("alembic.ini")
    with Session(database_engine) as db:
        inventory, harvest_payload = setup(db)
        from florabase.plants.model import Plant

        source = db.get(Plant, harvest_payload.plant_id)
        assert source is not None
        identity_id, source_location_id = source.botanical_identity_id, source.location_id
        legacy_lot = create_seed_lot(
            db,
            SeedLotCreate(
                botanical_identity_id=source.botanical_identity_id,
                source_kind="collection_produced",
                producer_plant_id=source.id,
                quantity=payload().quantity,
            ),
        )
        inventory_id, harvest_id, legacy_id = inventory.id, inventory.harvest_id, legacy_lot.id
        db.commit()
    command.downgrade(config, "20261003_0031")
    command.upgrade(config, "head")
    with database_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM harvest_seed_lot_conversions")) == 0
        assert (
            conn.scalar(text("SELECT count(*) FROM seed_lots WHERE id=:id"), {"id": legacy_id}) == 1
        )
        assert (
            conn.scalar(
                text("SELECT quantity_value FROM harvest_material_inventory WHERE id=:id"),
                {"id": inventory_id},
            )
            == 10
        )
    command.downgrade(config, "20261003_0031")
    command.upgrade(config, "head")
    with Session(database_engine) as db:
        conversion = create(db, inventory_id, payload())
        conversion_id, lot_id = conversion.id, conversion.seed_lot_id
        db.commit()
    try:
        with pytest.raises(RuntimeError, match="cannot be discarded"):
            command.downgrade(config, "20261003_0031")
        with Session(database_engine) as db:
            assert db.get(HarvestSeedLotConversion, conversion_id) is not None
    finally:
        with database_engine.begin() as conn:
            conn.execute(
                text("DELETE FROM harvest_seed_lot_conversions WHERE id=:id"), {"id": conversion_id}
            )
            conn.execute(
                text("DELETE FROM harvest_material_dispositions WHERE inventory_id=:id"),
                {"id": inventory_id},
            )
            conn.execute(
                text("DELETE FROM harvest_material_inventory WHERE id=:id"), {"id": inventory_id}
            )
            conn.execute(text("DELETE FROM seed_lots WHERE id=:id"), {"id": lot_id})
            conn.execute(text("DELETE FROM seed_lots WHERE id=:id"), {"id": legacy_id})
        from florabase.harvests.service import delete_harvest

        with Session(database_engine) as db:
            delete_harvest(db, harvest_id)
            db.execute(
                text("DELETE FROM plants WHERE botanical_identity_id=:id"), {"id": identity_id}
            )
            db.execute(
                text("DELETE FROM plant_groups WHERE botanical_identity_id=:id"),
                {"id": identity_id},
            )
            db.execute(text("DELETE FROM locations WHERE id=:id"), {"id": source_location_id})
            db.execute(text("DELETE FROM botanical_identities WHERE id=:id"), {"id": identity_id})
            db.commit()
