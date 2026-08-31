import pytest
from alembic.config import Config
from sqlalchemy import Engine, inspect

from alembic import command

pytestmark = pytest.mark.integration


def test_upgrade_downgrade_and_reupgrade(database_engine: Engine) -> None:
    config = Config("alembic.ini")

    try:
        command.downgrade(config, "20260827_0001")
        assert not inspect(database_engine).has_table("botanical_identities")

        command.upgrade(config, "head")
        assert inspect(database_engine).has_table("botanical_identities")

        command.downgrade(config, "20260827_0001")
        assert not inspect(database_engine).has_table("botanical_identities")
    finally:
        command.upgrade(config, "head")

    assert inspect(database_engine).has_table("botanical_identities")


def test_authentication_migration_cycle_preserves_botanical_schema(database_engine: Engine) -> None:
    config = Config("alembic.ini")
    botanical_columns_before = [
        column["name"] for column in inspect(database_engine).get_columns("botanical_identities")
    ]

    try:
        command.downgrade(config, "20260828_0002")
        inspector = inspect(database_engine)
        assert inspector.has_table("botanical_identities")
        assert not inspector.has_table("users")
        assert not inspector.has_table("auth_sessions")
        assert not inspector.has_table("login_throttles")

        command.upgrade(config, "head")
        inspector = inspect(database_engine)
        assert inspector.has_table("users")
        assert inspector.has_table("auth_sessions")
        assert inspector.has_table("login_throttles")
    finally:
        command.upgrade(config, "head")

    assert [
        column["name"] for column in inspect(database_engine).get_columns("botanical_identities")
    ] == botanical_columns_before
