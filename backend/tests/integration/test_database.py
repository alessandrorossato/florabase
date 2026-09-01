import pytest
from sqlalchemy import Connection, Engine, text

from florabase.api.health import database_readiness

pytestmark = pytest.mark.integration


def test_postgresql_18_has_current_migrations(database_connection: Connection) -> None:
    server_version = database_connection.execute(text("SHOW server_version_num")).scalar_one()
    revision = database_connection.execute(
        text("SELECT version_num FROM alembic_version")
    ).scalar_one()
    initialized = database_connection.execute(
        text("SELECT value FROM app_metadata WHERE key = 'schema_initialized'")
    ).scalar_one()

    assert int(server_version) // 10000 == 18
    assert revision == "20260901_0012"
    assert initialized == "true"
    database_readiness()


def test_each_test_uses_an_uncommitted_transaction(
    database_connection: Connection, database_engine: Engine
) -> None:
    database_connection.execute(
        text("INSERT INTO app_metadata (key, value) VALUES ('integration_isolation_probe', 'true')")
    )

    local_count = database_connection.execute(
        text("SELECT count(*) FROM app_metadata WHERE key = 'integration_isolation_probe'")
    ).scalar_one()
    with database_engine.connect() as independent_connection:
        external_count = independent_connection.execute(
            text("SELECT count(*) FROM app_metadata WHERE key = 'integration_isolation_probe'")
        ).scalar_one()

    assert local_count == 1
    assert external_count == 0
