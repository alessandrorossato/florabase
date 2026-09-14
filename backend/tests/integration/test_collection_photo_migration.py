import pytest
from alembic.config import Config
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from alembic import command

pytestmark = pytest.mark.integration


def test_collection_photo_migration_constraints_guarded_downgrade_and_reupgrade(
    database_engine: Engine,
) -> None:
    config = Config("alembic.ini")
    try:
        command.downgrade(config, "20260913_0023")
        inspector = inspect(database_engine)
        assert not inspector.has_table("local_collection_photos")
        assert not inspector.has_table("external_image_references")
        assert not inspector.has_table("botanical_identity_cover_images")
        command.upgrade(config, "head")
        assert inspect(database_engine).has_table("botanical_identity_cover_images")

        with database_engine.begin() as connection:
            identity_id = connection.execute(text("SELECT gen_random_uuid() ")).scalar_one()
            second_identity_id = connection.execute(text("SELECT gen_random_uuid() ")).scalar_one()
            plant_id = connection.execute(text("SELECT gen_random_uuid() ")).scalar_one()
            reference_id = connection.execute(text("SELECT gen_random_uuid() ")).scalar_one()
            attachment_id = connection.execute(text("SELECT gen_random_uuid() ")).scalar_one()
            local_photo_id = connection.execute(text("SELECT gen_random_uuid() ")).scalar_one()
            cover_id = connection.execute(text("SELECT gen_random_uuid() ")).scalar_one()
            connection.execute(
                text(
                    "INSERT INTO botanical_identities "
                    "(id, scientific_name, created_at, updated_at) "
                    "VALUES (:id, 'Photo migration test', now(), now())"
                ),
                {"id": identity_id},
            )
            connection.execute(
                text(
                    "INSERT INTO botanical_identities "
                    "(id, scientific_name, created_at, updated_at) "
                    "VALUES (:id, 'Second photo migration test', now(), now())"
                ),
                {"id": second_identity_id},
            )
            connection.execute(
                text(
                    "INSERT INTO botanical_identity_cover_images "
                    "(id, botanical_identity_id, source_mode, image_url, source_url, "
                    "attribution, created_at, updated_at) VALUES (:id, :identity_id, "
                    "'external', 'https://images.example.test/cover.jpg', "
                    "'https://example.test/cover', 'Cover author', now(), now())"
                ),
                {"id": cover_id, "identity_id": identity_id},
            )
            with (
                pytest.raises(IntegrityError, match="botanical_identity_id"),
                connection.begin_nested(),
            ):
                connection.execute(
                    text(
                        "INSERT INTO botanical_identity_cover_images "
                        "(id, botanical_identity_id, source_mode, image_url, source_url, "
                        "attribution, created_at, updated_at) VALUES (gen_random_uuid(), "
                        ":identity_id, 'external', 'https://images.example.test/other.jpg', "
                        "'https://example.test/other', 'Other author', now(), now())"
                    ),
                    {"identity_id": identity_id},
                )
            with (
                pytest.raises(IntegrityError, match="source_fields"),
                connection.begin_nested(),
            ):
                connection.execute(
                    text(
                        "INSERT INTO botanical_identity_cover_images "
                        "(id, botanical_identity_id, source_mode, created_at, updated_at) "
                        "VALUES (gen_random_uuid(), :identity_id, 'local', now(), now())"
                    ),
                    {"identity_id": second_identity_id},
                )
            with (
                pytest.raises(IntegrityError, match="image_url"),
                connection.begin_nested(),
            ):
                connection.execute(
                    text(
                        "INSERT INTO botanical_identity_cover_images "
                        "(id, botanical_identity_id, source_mode, image_url, source_url, "
                        "attribution, created_at, updated_at) VALUES (gen_random_uuid(), "
                        ":identity_id, 'external', 'http://example.test/cover.jpg', "
                        "'https://example.test/cover', 'Author', now(), now())"
                    ),
                    {"identity_id": second_identity_id},
                )
            connection.execute(
                text(
                    "INSERT INTO plants "
                    "(id, botanical_identity_id, direct_origin_kind, lifecycle, "
                    "created_at, updated_at) "
                    "VALUES (:id, :identity_id, 'unknown', 'active', now(), now())"
                ),
                {"id": plant_id, "identity_id": identity_id},
            )
            connection.execute(
                text(
                    "INSERT INTO external_image_references "
                    "(id, plant_id, image_url, source_url, attribution, created_at, updated_at) "
                    "VALUES (:id, :plant_id, 'https://example.test/image.jpg', "
                    "'https://example.test/source', 'Author', now(), now())"
                ),
                {"id": reference_id, "plant_id": plant_id},
            )
            connection.execute(
                text(
                    "INSERT INTO attachments "
                    "(id, storage_key, original_filename, media_type, byte_size, sha256, "
                    "state, created_at) VALUES (:id, :key, 'leaf.png', 'image/png', 1, "
                    ":digest, 'active', now())"
                ),
                {
                    "id": attachment_id,
                    "key": "objects/aa/" + "a" * 32,
                    "digest": "a" * 64,
                },
            )
            connection.execute(
                text(
                    "INSERT INTO local_collection_photos "
                    "(id, attachment_id, plant_id, caption, created_at, updated_at) "
                    "VALUES (:id, :attachment_id, :plant_id, 'Leaf', now(), now())"
                ),
                {
                    "id": local_photo_id,
                    "attachment_id": attachment_id,
                    "plant_id": plant_id,
                },
            )
            with (
                pytest.raises(IntegrityError, match="attachment_id"),
                connection.begin_nested(),
            ):
                connection.execute(
                    text(
                        "INSERT INTO local_collection_photos "
                        "(id, attachment_id, plant_id, created_at, updated_at) "
                        "VALUES (gen_random_uuid(), :attachment_id, :plant_id, now(), now())"
                    ),
                    {"attachment_id": attachment_id, "plant_id": plant_id},
                )
            with (
                pytest.raises(IntegrityError, match="attachment image ownership"),
                connection.begin_nested(),
            ):
                connection.execute(
                    text(
                        "INSERT INTO botanical_identity_cover_images "
                        "(id, botanical_identity_id, source_mode, attachment_id, "
                        "created_at, updated_at) VALUES (gen_random_uuid(), "
                        ":identity_id, 'local', :attachment_id, now(), now())"
                    ),
                    {"identity_id": second_identity_id, "attachment_id": attachment_id},
                )
            with (
                pytest.raises(IntegrityError, match="caption"),
                connection.begin_nested(),
            ):
                connection.execute(
                    text(
                        "INSERT INTO external_image_references "
                        "(id, plant_id, image_url, source_url, attribution, caption, "
                        "created_at, updated_at) VALUES (gen_random_uuid(), :plant_id, "
                        "'https://example.test/image.jpg', 'https://example.test/source', "
                        "'Author', :caption, now(), now())"
                    ),
                    {"plant_id": plant_id, "caption": "x" * 2001},
                )
            with (
                pytest.raises(IntegrityError, match="exactly_one_target"),
                connection.begin_nested(),
            ):
                connection.execute(
                    text(
                        "INSERT INTO external_image_references "
                        "(id, image_url, source_url, attribution, created_at, updated_at) "
                        "VALUES (gen_random_uuid(), 'https://example.test/image.jpg', "
                        "'https://example.test/source', 'Author', now(), now())"
                    )
                )
            with (
                pytest.raises(IntegrityError, match="image_url"),
                connection.begin_nested(),
            ):
                connection.execute(
                    text(
                        "INSERT INTO external_image_references "
                        "(id, plant_id, image_url, source_url, attribution, "
                        "created_at, updated_at) VALUES (gen_random_uuid(), :plant_id, "
                        "'http://example.test/image.jpg', 'https://example.test/source', "
                        "'Author', now(), now())"
                    ),
                    {"plant_id": plant_id},
                )

        with pytest.raises(ProgrammingError, match="cannot downgrade"):
            command.downgrade(config, "20260913_0023")

        with database_engine.begin() as connection:
            connection.execute(text("DELETE FROM botanical_identity_cover_images"))
            connection.execute(text("DELETE FROM local_collection_photos"))
            connection.execute(text("DELETE FROM external_image_references"))
            connection.execute(
                text("DELETE FROM attachments WHERE id = :id"), {"id": attachment_id}
            )
            connection.execute(text("DELETE FROM plants WHERE id = :id"), {"id": plant_id})
            connection.execute(
                text("DELETE FROM botanical_identities WHERE id = :id"), {"id": identity_id}
            )
            connection.execute(
                text("DELETE FROM botanical_identities WHERE id = :id"),
                {"id": second_identity_id},
            )
        command.downgrade(config, "20260913_0023")
        assert not inspect(database_engine).has_table("external_image_references")
        assert not inspect(database_engine).has_table("botanical_identity_cover_images")
    finally:
        command.upgrade(config, "head")

    assert inspect(database_engine).has_table("local_collection_photos")
    assert inspect(database_engine).has_table("botanical_identity_cover_images")
