from typing import Any

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Engine, inspect, text

from alembic import command
from florabase.application_settings.model import ApplicationSettings

pytestmark = pytest.mark.integration


def test_application_settings_upgrade_downgrade_reupgrade_and_metadata(
    database_engine: Engine,
) -> None:
    config = Config("alembic.ini")
    # This fixture is the disposable integration DB; protected UAT is never migrated here.
    command.downgrade(config, "20261009_0041")
    try:
        command.upgrade(config, "head")
        with database_engine.begin() as conn:
            assert conn.execute(
                text(
                    "SELECT id, public_qr_base_url, default_label_preset FROM application_settings"
                )
            ).one() == (1, None, "medium")
            conn.execute(
                text(
                    "UPDATE application_settings SET public_qr_base_url='https://flora.example', "
                    "default_label_preset='large' WHERE id=1"
                )
            )

        def belongs_to_settings(
            obj: Any, name: str | None, type_: str, reflected: bool, compare_to: Any
        ) -> bool:
            if type_ == "table":
                return name == "application_settings"
            return getattr(getattr(obj, "table", None), "name", None) == "application_settings"

        with database_engine.connect() as conn:
            context = MigrationContext.configure(conn, opts={"include_object": belongs_to_settings})
            assert compare_metadata(context, ApplicationSettings.metadata) == []
            checks = {
                item["name"] for item in inspect(conn).get_check_constraints("application_settings")
            }
            assert checks == {
                "ck_application_settings_singleton",
                "ck_application_settings_label_preset",
            }
        command.downgrade(config, "20261009_0041")
        with database_engine.connect() as conn:
            assert not inspect(conn).has_table("application_settings")
            assert inspect(conn).has_table("seed_lots")
            assert inspect(conn).has_table("scheduled_activities")
        command.upgrade(config, "head")
        with database_engine.connect() as conn:
            # Preference loss on downgrade is explicit; upgrades never guess a host.
            assert conn.scalar(text("SELECT public_qr_base_url FROM application_settings")) is None
    finally:
        command.upgrade(config, "head")
