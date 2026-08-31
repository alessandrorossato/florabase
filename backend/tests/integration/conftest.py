from collections.abc import Iterator

import pytest
from sqlalchemy import Connection, Engine, create_engine

from florabase.core.config import Settings, get_settings
from florabase.db.testing import require_disposable_test_database


@pytest.fixture(scope="session")
def integration_settings() -> Settings:
    settings = get_settings()
    require_disposable_test_database(settings)
    return settings


@pytest.fixture(scope="session")
def database_engine(integration_settings: Settings) -> Iterator[Engine]:
    engine = create_engine(integration_settings.database_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def database_connection(database_engine: Engine) -> Iterator[Connection]:
    with database_engine.connect() as connection, connection.begin() as transaction:
        yield connection
        transaction.rollback()
