import pytest
from alembic.config import Config
from sqlalchemy import Engine, inspect, text

from alembic import command

pytestmark = pytest.mark.integration


def test_external_botany_upgrade_downgrade_reupgrade(database_engine: Engine) -> None:
    config = Config("alembic.ini")
    try:
        command.downgrade(config, "20260908_0020")
        inspector = inspect(database_engine)
        assert not inspector.has_table("external_taxon_links")
        assert not inspector.has_table("external_provider_cache")

        command.upgrade(config, "head")
        inspector = inspect(database_engine)
        assert inspector.has_table("external_taxon_links")
        assert inspector.has_table("external_provider_cache")
        with database_engine.connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM external_taxon_links")) == 0

        command.downgrade(config, "20260908_0020")
        command.upgrade(config, "head")
    finally:
        command.upgrade(config, "head")


def test_external_botany_downgrade_refuses_data_loss(database_engine: Engine) -> None:
    config = Config("alembic.ini")
    with database_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO external_provider_cache (provider, resource_key, fetched_at, payload) "
                "VALUES ('gbif', 'fixture', now(), '{}'::jsonb)"
            )
        )
    try:
        with pytest.raises(Exception, match="cannot downgrade while external botanical"):
            command.downgrade(config, "20260908_0020")
    finally:
        with database_engine.begin() as connection:
            connection.execute(text("DELETE FROM external_provider_cache"))
        command.upgrade(config, "head")
