import os
import time
from collections.abc import Iterator
from functools import lru_cache
from typing import Any

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from florabase.core.config import get_settings

# Readiness must answer within the health check timeout even when PostgreSQL hangs or the network
# drops packets; libpq otherwise waits indefinitely while connecting or for a reply.
READINESS_CONNECT_TIMEOUT_SECONDS = 3
READINESS_STATEMENT_TIMEOUT_MILLISECONDS = 2000
# /api/v1/ready is unauthenticated: reuse a success briefly so a request flood cannot make every
# request open a new PostgreSQL connection. Failures are never cached.
READINESS_SUCCESS_CACHE_SECONDS = 1.0
_readiness_ok_until = 0.0


def database_connect_args(url: str, *, options: str = "") -> dict[str, Any]:
    """Pin PostgreSQL sessions to UTC and fall back to FLORABASE_DB_PASSWORD when needed."""
    session_options = "-c timezone=UTC" if not options else f"{options} -c timezone=UTC"
    args: dict[str, Any] = {"options": session_options}
    parsed = make_url(url)
    if (
        parsed.password is None
        and not os.environ.get("PGPASSWORD")
        and (password := os.environ.get("FLORABASE_DB_PASSWORD"))
    ):
        args["password"] = password
    return args


@lru_cache
def get_engine() -> Engine:
    url = get_settings().database_url
    return create_engine(
        url,
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args=database_connect_args(url),
    )


@lru_cache
def get_readiness_engine() -> Engine:
    """Unpooled, time-bounded engine: a probe never waits on a stale pooled connection."""
    url = get_settings().database_url
    return create_engine(
        url,
        poolclass=NullPool,
        connect_args={
            "connect_timeout": READINESS_CONNECT_TIMEOUT_SECONDS,
            **database_connect_args(
                url, options=f"-c statement_timeout={READINESS_STATEMENT_TIMEOUT_MILLISECONDS}"
            ),
        },
    )


def check_database() -> None:
    global _readiness_ok_until
    if time.monotonic() < _readiness_ok_until:
        return
    with get_readiness_engine().connect() as connection:
        connection.execute(text("SELECT 1"))
    _readiness_ok_until = time.monotonic() + READINESS_SUCCESS_CACHE_SECONDS


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
