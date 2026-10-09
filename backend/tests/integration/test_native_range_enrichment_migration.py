from uuid import uuid7

import pytest
from alembic.config import Config
from sqlalchemy import Engine, text

from alembic import command

pytestmark = pytest.mark.integration


def test_enrichment_migration_empty_cycle_and_populated_refusal(database_engine: Engine) -> None:
    config = Config("alembic.ini")
    command.downgrade(config, "20261008_0038")
    identity_id = uuid7()
    with database_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO botanical_identities(id, scientific_name, created_at, updated_at) "
                "VALUES(:id, :name, now(), now())"
            ),
            {"id": identity_id, "name": f"Migration fixture {identity_id}"},
        )
        place_id = connection.scalar(
            text("SELECT id FROM geographic_places WHERE source_code='BO'")
        )
        connection.execute(
            text("INSERT INTO botanical_profiles(botanical_identity_id) VALUES(:id)"),
            {"id": identity_id},
        )
        connection.execute(
            text(
                "INSERT INTO botanical_profile_native_ranges"
                "(botanical_profile_id, geographic_place_id, created_at) "
                "VALUES(:id, :place, now())"
            ),
            {"id": identity_id, "place": place_id},
        )
    try:
        command.upgrade(config, "head")
        with database_engine.begin() as connection:
            assert (
                connection.scalar(
                    text(
                        "SELECT count(*) FROM botanical_profile_native_ranges "
                        "WHERE botanical_profile_id=:id"
                    ),
                    {"id": identity_id},
                )
                == 1
            )
            assert (
                connection.scalar(
                    text("SELECT version FROM native_range_revisions WHERE identity_id=:id"),
                    {"id": identity_id},
                )
                is None
            )
            connection.execute(
                text(
                    "INSERT INTO wcvp_links(identity_id, version, external_id, taxon, source, "
                    "identity_snapshot, confirmed_at) "
                    "VALUES(:id, :version, 'fixture', '{}', '{}', '{}', now())"
                ),
                {"id": identity_id, "version": uuid7()},
            )
        with pytest.raises(RuntimeError, match="downgrade would destroy"):
            command.downgrade(config, "20261008_0038")
        with database_engine.begin() as connection:
            assert (
                connection.scalar(text("SELECT version_num FROM alembic_version"))
                == "20261009_0039"
            )
            assert (
                connection.scalar(
                    text("SELECT count(*) FROM wcvp_links WHERE identity_id=:id"),
                    {"id": identity_id},
                )
                == 1
            )
            connection.execute(
                text("DELETE FROM wcvp_links WHERE identity_id=:id"), {"id": identity_id}
            )
        command.downgrade(config, "20261008_0038")
        command.upgrade(config, "head")
        with database_engine.begin() as connection:
            assert (
                connection.scalar(
                    text(
                        "SELECT count(*) FROM botanical_profile_native_ranges "
                        "WHERE botanical_profile_id=:id"
                    ),
                    {"id": identity_id},
                )
                == 1
            )
    finally:
        command.upgrade(config, "head")
        with database_engine.begin() as connection:
            connection.execute(
                text("DELETE FROM botanical_identities WHERE id=:id"), {"id": identity_id}
            )
