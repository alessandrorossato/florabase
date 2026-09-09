from uuid import uuid7

import pytest
from alembic.config import Config
from sqlalchemy import Engine, delete, inspect, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from alembic import command
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_profiles.model import BotanicalProfile, BotanicalProfileNativeRange
from florabase.geographic_places.model import GeographicPlace

pytestmark = pytest.mark.integration


def test_native_range_migration_cycle_and_populated_downgrade_guard(
    database_engine: Engine,
) -> None:
    config = Config("alembic.ini")
    identity_id = uuid7()
    place_id = uuid7()
    try:
        command.downgrade(config, "20260909_0021")
        assert not inspect(database_engine).has_table("botanical_profile_native_ranges")
        command.upgrade(config, "head")
        assert inspect(database_engine).has_table("botanical_profile_native_ranges")

        with Session(database_engine) as database:
            database.add(
                BotanicalIdentity(
                    id=identity_id,
                    scientific_name=f"Migration native range {identity_id}",
                )
            )
            world = database.scalars(
                select(GeographicPlace).where(GeographicPlace.source_code == "001")
            ).one()
            database.add(
                GeographicPlace(
                    id=place_id,
                    name="Migration locality",
                    parent_id=world.id,
                    place_kind="custom",
                    place_type="locality",
                )
            )
            database.add(BotanicalProfile(botanical_identity_id=identity_id))
            database.flush()
            database.add(
                BotanicalProfileNativeRange(
                    botanical_profile_id=identity_id,
                    geographic_place_id=place_id,
                )
            )
            database.commit()

        inspector = inspect(database_engine)
        primary_key = inspector.get_pk_constraint("botanical_profile_native_ranges")
        assert primary_key["constrained_columns"] == [
            "botanical_profile_id",
            "geographic_place_id",
        ]
        foreign_keys = {
            tuple(item["constrained_columns"]): item
            for item in inspector.get_foreign_keys("botanical_profile_native_ranges")
        }
        assert foreign_keys[("botanical_profile_id",)]["options"]["ondelete"] == "CASCADE"
        assert foreign_keys[("geographic_place_id",)]["options"]["ondelete"] == "RESTRICT"
        with Session(database_engine) as database:
            persisted = database.get(BotanicalProfileNativeRange, (identity_id, place_id))
            assert persisted is not None
            assert persisted.created_at.tzinfo is not None

        with pytest.raises(DBAPIError):
            command.downgrade(config, "20260909_0021")

        with Session(database_engine) as database:
            database.execute(
                delete(BotanicalProfileNativeRange).where(
                    BotanicalProfileNativeRange.botanical_profile_id == identity_id
                )
            )
            database.execute(
                delete(BotanicalProfile).where(
                    BotanicalProfile.botanical_identity_id == identity_id
                )
            )
            database.execute(delete(GeographicPlace).where(GeographicPlace.id == place_id))
            database.execute(delete(BotanicalIdentity).where(BotanicalIdentity.id == identity_id))
            database.commit()
        command.downgrade(config, "20260909_0021")
        assert not inspect(database_engine).has_table("botanical_profile_native_ranges")
    finally:
        command.upgrade(config, "head")


def test_database_rejects_a_completely_empty_profile(database_engine: Engine) -> None:
    identity_id = uuid7()
    with Session(database_engine) as database:
        database.add(
            BotanicalIdentity(
                id=identity_id,
                scientific_name=f"Empty profile guard {identity_id}",
            )
        )
        database.add(BotanicalProfile(botanical_identity_id=identity_id))
        with pytest.raises(DBAPIError):
            database.commit()

    with Session(database_engine) as database:
        assert database.get(BotanicalIdentity, identity_id) is None
