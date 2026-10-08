from typing import Any
from uuid import uuid7

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, text

from alembic import command

from .test_saved_views import payload
from .test_supplier_api import authenticated_browser as authenticated_browser
from .test_supplier_api import mutate

pytestmark = pytest.mark.integration


def test_distribution_saved_view_persisted_management(
    authenticated_browser: tuple[str, str],
) -> None:
    identity = str(uuid7())
    state: dict[str, Any] = {"scope": "living", "q": " basil ", "identity": identity.upper()}
    status, _, created = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/saved-views",
        payload("Living species", "species_distribution", state),
    )
    assert status == 201
    assert created["state"] == {"scope": "living", "q": "basil", "identity": identity}
    path = f"/api/v1/saved-views/{created['id']}"
    assert (
        mutate(authenticated_browser, "PATCH", path, {"name": "Renamed"})[2]["state"]
        == created["state"]
    )
    assert mutate(
        authenticated_browser, "PATCH", path, {"state_version": 1, "state": {"scope": "historical"}}
    )[2]["state"] == {"scope": "historical"}
    for invalid in ({"loaded": True}, {"offset": 50}, {"scope": "dead"}, {"identity": "bad"}):
        assert (
            mutate(authenticated_browser, "PATCH", path, {"state_version": 1, "state": invalid})[0]
            == 422
        )
    assert mutate(authenticated_browser, "DELETE", path)[0] == 204


def test_distribution_surface_upgrade_preserves_views_and_refuses_populated_downgrade(
    database_engine: Engine,
) -> None:
    config = Config("alembic.ini")
    current_head = ScriptDirectory.from_config(config).get_current_head()
    owner, old, history = uuid7(), uuid7(), uuid7()
    command.downgrade(config, "20261008_0036")
    with database_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (id, login_name, password_hash, enabled, owner, "
                "password_changed_at, created_at, updated_at) VALUES (:id, :login, "
                "'unused', true, true, now(), now(), now())"
            ),
            {"id": owner, "login": str(owner)},
        )
        connection.execute(
            text(
                "INSERT INTO saved_views (id, owner_id, name, surface, state_version, "
                "state, created_at, updated_at) VALUES (:id, :owner, 'Existing', "
                "'events', 1, '{\"category\":\"status\"}', now(), now())"
            ),
            {"id": old, "owner": owner},
        )
    try:
        command.upgrade(config, "head")
        with database_engine.begin() as connection:
            assert connection.scalar(
                text("SELECT state FROM saved_views WHERE id=:id"), {"id": old}
            ) == {"category": "status"}
            connection.execute(
                text(
                    "INSERT INTO saved_views (id, owner_id, name, surface, state_version, "
                    "state, created_at, updated_at) VALUES (:id, :owner, 'Distribution', "
                    "'species_distribution', 1, '{\"scope\": \"living\"}', now(), now())"
                ),
                {"id": history, "owner": owner},
            )
        with pytest.raises(RuntimeError, match="Species distribution Saved Views exist"):
            command.downgrade(config, "20261008_0036")
        with database_engine.begin() as connection:
            assert (
                connection.scalar(
                    text("SELECT count(*) FROM saved_views WHERE id IN (:old, :history)"),
                    {"old": old, "history": history},
                )
                == 2
            )
            assert (
                connection.scalar(text("SELECT version_num FROM alembic_version")) == current_head
            )
            connection.execute(text("DELETE FROM saved_views WHERE id=:id"), {"id": history})
        command.downgrade(config, "20261008_0036")
        command.upgrade(config, "head")
        with database_engine.connect() as connection:
            assert (
                connection.scalar(
                    text("SELECT count(*) FROM saved_views WHERE id=:id"), {"id": old}
                )
                == 1
            )
    finally:
        command.upgrade(config, "head")
        with database_engine.begin() as connection:
            connection.execute(text("DELETE FROM saved_views WHERE owner_id=:id"), {"id": owner})
            connection.execute(text("DELETE FROM users WHERE id=:id"), {"id": owner})
