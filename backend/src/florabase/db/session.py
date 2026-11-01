from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from florabase.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)


def check_database() -> None:
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))


def get_database_session() -> Iterator[Session]:
    """Yield the request's single transaction-owning Session.

    Declare it only as ``Depends(get_database_session, scope="function")``. Function scope runs
    this commit after the endpoint and response serialization but before the response is sent,
    so a 2xx is never observable before its transaction commits and a commit failure becomes an
    error response. FastAPI's default request scope would run it after the response is sent, and
    mixing scopes would give one request two independent sessions.
    """
    with Session(get_engine()) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
