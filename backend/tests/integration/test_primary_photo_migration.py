import pytest
from alembic.config import Config
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError

from alembic import command

pytestmark = pytest.mark.integration


def test_primary_photo_migration_cycle_and_constraints(database_engine: Engine) -> None:
    config = Config("alembic.ini")
    command.downgrade(config, "20260925_0025")
    assert not inspect(database_engine).has_table("collection_primary_photos")
    assert inspect(database_engine).has_table("local_collection_photos")
    from uuid import uuid7

    ids = {
        table: uuid7()
        for table in (
            "botanical_identities",
            "plants",
            "attachments",
            "local_collection_photos",
            "external_image_references",
            "botanical_identity_cover_images",
        )
    }
    with database_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO botanical_identities (id, scientific_name, created_at, updated_at) "
                "VALUES (:id, 'Primary migration fixture', now(), now())"
            ),
            {"id": ids["botanical_identities"]},
        )
        connection.execute(
            text(
                "INSERT INTO plants (id, botanical_identity_id, direct_origin_kind, lifecycle, "
                "created_at, updated_at) VALUES (:id, :identity, 'unknown', 'active', now(), now())"
            ),
            {"id": ids["plants"], "identity": ids["botanical_identities"]},
        )
        connection.execute(
            text(
                "INSERT INTO attachments (id, storage_key, original_filename, media_type, "
                "byte_size, sha256, state, created_at) "
                "VALUES (:id, :key, 'leaf.png', 'image/png', 1, :sha, 'active', now())"
            ),
            {"id": ids["attachments"], "key": "objects/aa/" + "a" * 32, "sha": "a" * 64},
        )
        connection.execute(
            text(
                "INSERT INTO local_collection_photos (id, plant_id, attachment_id, caption, "
                "created_at, updated_at) VALUES (:id, :plant, :file, 'Preserved leaf', "
                "now(), now())"
            ),
            {
                "id": ids["local_collection_photos"],
                "plant": ids["plants"],
                "file": ids["attachments"],
            },
        )
        connection.execute(
            text(
                "INSERT INTO external_image_references (id, plant_id, image_url, source_url, "
                "attribution, created_at, updated_at) VALUES (:id, :plant, "
                "'https://example.test/image.jpg', 'https://example.test/source', "
                "'Preserved author', now(), now())"
            ),
            {"id": ids["external_image_references"], "plant": ids["plants"]},
        )
        connection.execute(
            text(
                "INSERT INTO botanical_identity_cover_images (id, botanical_identity_id, "
                "source_mode, "
                "image_url, source_url, attribution, created_at, updated_at) VALUES (:id, "
                ":identity, "
                "'external', 'https://example.test/cover.jpg', 'https://example.test/source', "
                "'Cover author', now(), now())"
            ),
            {"id": ids["botanical_identity_cover_images"], "identity": ids["botanical_identities"]},
        )

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
    command.upgrade(config, "20260925_0026")
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
    with database_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO collection_primary_photos (id, plant_id, local_collection_photo_id, "
                "created_at, updated_at) VALUES (gen_random_uuid(), :plant, :link, now(), now())"
            ),
            {"plant": ids["plants"], "link": ids["local_collection_photos"]},
        )
    command.downgrade(config, "20260925_0025")
    assert not inspect(database_engine).has_table("collection_primary_photos")
    assert inspect(database_engine).has_table("local_collection_photos")
    assert inspect(database_engine).has_table("external_image_references")
    assert photo_state() == original
    command.upgrade(config, "20260925_0026")
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

    command.upgrade(config, "head")
