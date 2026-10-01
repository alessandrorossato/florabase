"""Representative pre-Harvest history survives; populated downgrade is guarded."""

from uuid import uuid7

import pytest
from alembic.config import Config
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from alembic import command
from florabase.harvests.schemas import HarvestWrite
from florabase.harvests.service import delete_harvest, write_harvest

pytestmark = pytest.mark.integration


def test_history_preserved_guarded_and_empty_cycle(database_engine: Engine) -> None:
    config = Config("alembic.ini")
    ids = {key: uuid7() for key in ("identity", "plant", "event", "asset", "link")}
    command.downgrade(config, "20261001_0028")
    harvest_id = None
    try:
        with database_engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO botanical_identities (id, scientific_name, created_at, "
                    "updated_at) VALUES (:identity, 'Harvest migration species', now(), "
                    "now())"
                ),
                ids,
            )
            conn.execute(
                text(
                    "INSERT INTO plants (id, botanical_identity_id, direct_origin_kind, "
                    "lifecycle, created_at, updated_at) VALUES (:plant, :identity, "
                    "'unknown', 'dead', now(), now())"
                ),
                ids,
            )
            conn.execute(
                text(
                    "INSERT INTO events (id, plant_id, kind, notes, created_at, "
                    "updated_at) VALUES (:event, :plant, 'harvest', 'Historical "
                    "free-form collection', now(), now())"
                ),
                ids,
            )
            conn.execute(
                text(
                    "INSERT INTO media_assets (id, kind, image_url, source_url, "
                    "attribution, state, created_at, updated_at) VALUES (:asset, "
                    "'external', 'https://example.test/fruit.jpg', "
                    "'https://example.test', 'Gardener', 'active', now(), now())"
                ),
                ids,
            )
            conn.execute(
                text(
                    "INSERT INTO record_media_links (id, media_asset_id, source_kind, "
                    "plant_id, display_order, caption, created_at, updated_at) VALUES "
                    "(:link, :asset, 'external', :plant, 2, 'Original context', now(), "
                    "now())"
                ),
                ids,
            )
        command.upgrade(config, "head")
        with database_engine.connect() as conn:
            assert conn.scalar(text("SELECT count(*) FROM harvests")) == 0
            assert (
                conn.scalar(text("SELECT notes FROM events WHERE id = :event"), ids)
                == "Historical free-form collection"
            )
            assert (
                conn.scalar(text("SELECT caption FROM record_media_links WHERE id = :link"), ids)
                == "Original context"
            )
        with Session(database_engine) as db:
            harvest = write_harvest(
                db,
                HarvestWrite.model_validate(
                    {"plant_id": ids["plant"], "items": [{"material_kind": "fruit"}]}
                ),
            )
            db.commit()
            harvest_id = harvest.id
        with pytest.raises(RuntimeError, match="Structured Harvest history"):
            command.downgrade(config, "20261001_0028")
        with Session(database_engine) as db:
            delete_harvest(db, harvest_id)
            db.commit()
            harvest_id = None
        command.downgrade(config, "20261001_0028")
        command.upgrade(config, "head")
    finally:
        command.upgrade(config, "head")
        if harvest_id:
            with Session(database_engine) as db:
                delete_harvest(db, harvest_id)
                db.commit()
        with database_engine.begin() as conn:
            for table, key in (
                ("record_media_links", "link"),
                ("media_assets", "asset"),
                ("events", "event"),
                ("plants", "plant"),
                ("botanical_identities", "identity"),
            ):
                conn.execute(text(f"DELETE FROM {table} WHERE id = :id"), {"id": ids[key]})
