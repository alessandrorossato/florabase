import pytest
from alembic.config import Config
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from florabase.attachments.model import Attachment
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.collection_photos.model import (
    BotanicalIdentityCoverImage,
    CollectionPrimaryPhoto,
    ExternalImageReference,
    LocalCollectionPhoto,
)
from florabase.plants.model import Plant

pytestmark = pytest.mark.integration


def test_primary_photo_migration_cycle_and_constraints(database_engine: Engine) -> None:
    config = Config("alembic.ini")
    command.downgrade(config, "20260925_0025")
    assert not inspect(database_engine).has_table("collection_primary_photos")
    assert inspect(database_engine).has_table("local_collection_photos")
    with Session(database_engine) as database:
        identity = BotanicalIdentity(scientific_name="Primary migration fixture")
        database.add(identity)
        database.flush()
        plant = Plant(botanical_identity_id=identity.id, direct_origin_kind="unknown")
        attachment = Attachment(
            storage_key="objects/aa/" + "a" * 32,
            original_filename="leaf.png",
            media_type="image/png",
            byte_size=1,
            sha256="a" * 64,
            state="active",
        )
        database.add_all([plant, attachment])
        database.flush()
        local = LocalCollectionPhoto(
            plant_id=plant.id, attachment_id=attachment.id, caption="Preserved leaf"
        )
        external = ExternalImageReference(
            plant_id=plant.id,
            image_url="https://example.test/image.jpg",
            source_url="https://example.test/source",
            attribution="Preserved author",
        )
        cover = BotanicalIdentityCoverImage(
            botanical_identity_id=identity.id,
            source_mode="external",
            image_url="https://example.test/cover.jpg",
            source_url="https://example.test/source",
            attribution="Cover author",
        )
        database.add_all([local, external, cover])
        database.commit()
        ids = {
            "botanical_identities": identity.id,
            "plants": plant.id,
            "attachments": attachment.id,
            "local_collection_photos": local.id,
            "external_image_references": external.id,
            "botanical_identity_cover_images": cover.id,
        }

    def photo_state() -> dict[str, dict[str, object]]:
        with database_engine.connect() as connection:
            return {
                table: dict(
                    connection.execute(
                        text(f"SELECT * FROM {table} WHERE id = :id"), {"id": ids[table]}
                    )
                    .mappings()
                    .one()
                )
                for table in (
                    "attachments",
                    "local_collection_photos",
                    "external_image_references",
                    "botanical_identity_cover_images",
                )
            }

    original = photo_state()
    command.upgrade(config, "head")
    assert inspect(database_engine).has_table("collection_primary_photos")
    assert photo_state() == original
    with database_engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM collection_primary_photos")) == 0
    checks = {
        item["name"]
        for item in inspect(database_engine).get_check_constraints("collection_primary_photos")
    }
    assert "ck_collection_primary_photos_exactly_one_target" in checks
    assert "ck_collection_primary_photos_exactly_one_source" in checks
    unique_columns = {
        tuple(item["column_names"])
        for item in inspect(database_engine).get_unique_constraints("collection_primary_photos")
    }
    assert unique_columns == {
        ("seed_lot_id",),
        ("plant_id",),
        ("plant_group_id",),
        ("local_collection_photo_id",),
        ("external_image_reference_id",),
    }
    with database_engine.begin() as connection:
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(
                text(
                    "INSERT INTO collection_primary_photos (id, created_at, updated_at) "
                    "VALUES (gen_random_uuid(), now(), now())"
                )
            )
        with pytest.raises(IntegrityError, match="exactly_one_source"), connection.begin_nested():
            connection.execute(
                text(
                    "INSERT INTO collection_primary_photos "
                    "(id, seed_lot_id, created_at, updated_at) "
                    "VALUES (gen_random_uuid(), gen_random_uuid(), now(), now())"
                )
            )
    with Session(database_engine) as database:
        database.add(
            CollectionPrimaryPhoto(
                plant_id=ids["plants"], local_collection_photo_id=ids["local_collection_photos"]
            )
        )
        database.commit()
    command.downgrade(config, "20260925_0025")
    assert not inspect(database_engine).has_table("collection_primary_photos")
    assert inspect(database_engine).has_table("local_collection_photos")
    assert inspect(database_engine).has_table("external_image_references")
    assert photo_state() == original
    command.upgrade(config, "head")
    assert photo_state() == original
    with database_engine.begin() as connection:
        assert connection.scalar(text("SELECT count(*) FROM collection_primary_photos")) == 0
        for table in (
            "local_collection_photos",
            "external_image_references",
            "botanical_identity_cover_images",
            "attachments",
            "plants",
            "botanical_identities",
        ):
            connection.execute(text(f"DELETE FROM {table} WHERE id = :id"), {"id": ids[table]})
