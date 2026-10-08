from uuid import uuid7

import pytest
from alembic.config import Config
from sqlalchemy import Engine, inspect, text

from alembic import command

pytestmark = pytest.mark.integration


def test_saved_view_upgrade_populated_refusal_and_empty_downgrade_reupgrade(
    database_engine: Engine,
) -> None:
    config = Config("alembic.ini")
    owner_id, view_id = uuid7(), uuid7()
    command.downgrade(config, "20261005_0033")
    try:
        with database_engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO users (id, login_name, password_hash, enabled, owner, "
                    "password_changed_at, created_at, updated_at) "
                    "VALUES (:id, 'migration-view-owner', 'unused', true, true, "
                    "now(), now(), now())"
                ),
                {"id": owner_id},
            )
        command.upgrade(config, "head")
        with database_engine.begin() as conn:
            assert conn.scalar(text("SELECT count(*) FROM saved_views")) == 0
            conn.execute(
                text(
                    "INSERT INTO saved_views (id, owner_id, name, surface, state_version, "
                    "state, created_at, updated_at) VALUES (:id, :owner, 'Retained', "
                    "'global_search', 1, '{\"q\":\"basil\"}', now(), now())"
                ),
                {"id": view_id, "owner": owner_id},
            )
        with pytest.raises(RuntimeError, match="Saved Views exist"):
            command.downgrade(config, "20261005_0033")
        with database_engine.begin() as conn:
            assert (
                conn.scalar(
                    text("SELECT state->>'q' FROM saved_views WHERE id=:id"), {"id": view_id}
                )
                == "basil"
            )
            assert conn.scalar(text("SELECT version_num FROM alembic_version")) == "20261007_0035"
            conn.execute(text("DELETE FROM saved_views WHERE id=:id"), {"id": view_id})
        command.downgrade(config, "20261005_0033")
        with database_engine.connect() as conn:
            assert not inspect(conn).has_table("saved_views")
            assert (
                conn.scalar(text("SELECT login_name FROM users WHERE id=:id"), {"id": owner_id})
                == "migration-view-owner"
            )
        command.upgrade(config, "head")
        with database_engine.connect() as conn:
            assert inspect(conn).has_table("saved_views")
            assert conn.scalar(text("SELECT count(*) FROM saved_views")) == 0
    finally:
        command.upgrade(config, "head")
        with database_engine.begin() as conn:
            conn.execute(text("DELETE FROM saved_views WHERE owner_id=:id"), {"id": owner_id})
            conn.execute(text("DELETE FROM users WHERE id=:id"), {"id": owner_id})
