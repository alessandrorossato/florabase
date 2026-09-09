from uuid import UUID, uuid7

import pytest
from alembic.config import Config
from sqlalchemy import Connection, Engine, delete, insert, inspect, text
from sqlalchemy.exc import DBAPIError

from alembic import command
from florabase.botanical_identities.model import BotanicalIdentity, utc_now
from florabase.botanical_profiles.model import BotanicalProfile

pytestmark = pytest.mark.integration


def create_identity(connection: Connection, scientific_name: str = "Acer palmatum") -> UUID:
    identity_id = uuid7()
    now = utc_now()
    connection.execute(
        insert(BotanicalIdentity).values(
            id=identity_id,
            scientific_name=scientific_name,
            cultivar_name=None,
            common_name=None,
            created_at=now,
            updated_at=now,
        )
    )
    return identity_id


def test_profile_migration_upgrade_downgrade_and_reupgrade(database_engine: Engine) -> None:
    config = Config("alembic.ini")
    try:
        command.downgrade(config, "20260828_0003")
        assert not inspect(database_engine).has_table("botanical_profiles")
        assert inspect(database_engine).has_table("botanical_identities")

        command.upgrade(config, "head")
        assert inspect(database_engine).has_table("botanical_profiles")

        command.downgrade(config, "20260828_0003")
        assert not inspect(database_engine).has_table("botanical_profiles")
    finally:
        command.upgrade(config, "head")

    assert inspect(database_engine).has_table("botanical_profiles")


def test_profile_database_constraints_and_parent_cascade(
    database_connection: Connection,
) -> None:
    identity_id = create_identity(database_connection)
    database_connection.execute(
        insert(BotanicalProfile).values(
            botanical_identity_id=identity_id,
            description="First paragraph.\n\nSecond paragraph.",
        )
    )

    constraints = {
        row.name
        for row in database_connection.execute(
            text(
                """
                SELECT conname AS name
                FROM pg_constraint
                WHERE conrelid = 'botanical_profiles'::regclass
                """
            )
        ).mappings()
    }
    assert "pk_botanical_profiles" in constraints
    assert "fk_botanical_profiles_identity" in constraints
    assert "ck_botanical_profiles_at_least_one_section" not in constraints
    assert "ck_botanical_profiles_description_no_control" in constraints

    with pytest.raises(DBAPIError), database_connection.begin_nested():
        database_connection.execute(
            insert(BotanicalProfile).values(
                botanical_identity_id=identity_id,
                cultivation="General guidance.",
            )
        )

    for values in (
        {"description": ""},
        {"description": " surrounding whitespace "},
        {"description": "unsupported\x1fcontrol"},
        {"description": "x" * 20_001},
        {"botanical_identity_id": uuid7(), "description": "Missing parent"},
    ):
        with pytest.raises(DBAPIError), database_connection.begin_nested():
            database_connection.execute(
                insert(BotanicalProfile).values(
                    botanical_identity_id=values.pop("botanical_identity_id", identity_id),
                    **values,
                )
            )

    database_connection.execute(
        delete(BotanicalIdentity).where(BotanicalIdentity.id == identity_id)
    )
    assert (
        database_connection.execute(
            text(
                "SELECT count(*) FROM botanical_profiles WHERE botanical_identity_id = :identity_id"
            ),
            {"identity_id": identity_id},
        ).scalar_one()
        == 0
    )
