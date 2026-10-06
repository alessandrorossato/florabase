"""Empty Supplier history rolls back; populated history refuses before mutation."""

from uuid import uuid7

import pytest
from alembic.config import Config
from sqlalchemy import Engine, inspect, select, text
from sqlalchemy.orm import Session

from alembic import command
from florabase.collection_photos.model import MediaAsset, RecordMediaLink
from florabase.media import service
from florabase.media.schemas import LinkWrite

from .test_shared_media import external, fixture

pytestmark = pytest.mark.integration


def test_supplier_media_migration_preserves_existing_media_and_refuses_history(
    database_engine: Engine,
) -> None:
    config = Config("alembic.ini")
    command.downgrade(config, "20261004_0032")
    supplier_id = uuid7()
    try:
        with database_engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO suppliers (id, name, kind, created_at, updated_at) "
                    "VALUES (:id, 'Existing nursery', 'nursery', now(), now())"
                ),
                {"id": supplier_id},
            )
        command.upgrade(config, "head")
        with Session(database_engine) as db:
            assert (
                db.scalar(select(RecordMediaLink).where(RecordMediaLink.supplier_id == supplier_id))
                is None
            )
        command.downgrade(config, "20261004_0032")
        with database_engine.connect() as conn:
            assert "supplier_id" not in {
                column["name"] for column in inspect(conn).get_columns("record_media_links")
            }
            assert (
                conn.scalar(text("SELECT name FROM suppliers WHERE id=:id"), {"id": supplier_id})
                == "Existing nursery"
            )
        command.upgrade(config, "head")
        with Session(database_engine) as db:
            plant, _, identity = fixture(db)
            plant_ids = db.scalars(
                select(type(plant).id).where(type(plant).botanical_identity_id == identity.id)
            ).all()
            identity_id = identity.id
            asset = external(db)
            asset_id = asset.id
            plant_link = service.create_link(db, "plant", plant.id, asset.id, LinkWrite())
            plant_link_id = plant_link.id
            supplier_link = service.create_link(
                db, "supplier", supplier_id, asset.id, LinkWrite(caption="Retained")
            )
            supplier_link_id = supplier_link.id
        try:
            with pytest.raises(RuntimeError, match="Supplier media history exists"):
                command.downgrade(config, "20261004_0032")
            with Session(database_engine) as db:
                assert db.scalar(text("SELECT version_num FROM alembic_version")) == "20261006_0034"
                retained = db.get(RecordMediaLink, supplier_link_id)
                assert retained is not None
                assert retained.caption == "Retained"
                assert db.get(RecordMediaLink, plant_link_id) is not None
                assert db.get(MediaAsset, asset_id) is not None
                service.unlink(db, supplier_link_id)
            command.downgrade(config, "20261004_0032")
            command.upgrade(config, "head")
            with Session(database_engine) as db:
                assert db.get(RecordMediaLink, plant_link_id) is not None
                assert db.get(MediaAsset, asset_id) is not None
        finally:
            command.upgrade(config, "head")
            with database_engine.begin() as conn:
                conn.execute(
                    text("DELETE FROM record_media_links WHERE media_asset_id=:id"),
                    {"id": asset_id},
                )
                conn.execute(text("DELETE FROM media_assets WHERE id=:id"), {"id": asset_id})
                for pid in plant_ids:
                    conn.execute(text("DELETE FROM plants WHERE id=:id"), {"id": pid})
                conn.execute(
                    text("DELETE FROM botanical_identities WHERE id=:id"), {"id": identity_id}
                )
    finally:
        command.upgrade(config, "head")
        with database_engine.begin() as conn:
            conn.execute(text("DELETE FROM suppliers WHERE id=:id"), {"id": supplier_id})
