import asyncio
import contextlib
import json
import logging
import sys
from collections.abc import Generator, Iterator
from typing import Annotated, cast
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute, iter_route_contexts
from sqlalchemy.orm import Session

from florabase.core.config import CookieMode, Environment, LogFormat, Settings
from florabase.core.logging import JsonFormatter, configure_logging
from florabase.db.session import check_database, get_database_session, get_engine
from florabase.main import app, create_app, lifespan


def settings(*, log_format: LogFormat = LogFormat.JSON) -> Settings:
    return Settings.model_validate(
        {
            "environment": Environment.TEST,
            "database_url": "postgresql+psycopg://test:test@db/test",
            "cors_origins": ["http://localhost:5173"],
            "cookie_mode": CookieMode.SECURE,
            "log_format": log_format,
        }
    )


def test_json_formatter_includes_exception() -> None:
    formatter = JsonFormatter()
    try:
        raise RuntimeError("visible failure")
    except RuntimeError:
        record = logging.LogRecord(
            "florabase.test",
            logging.ERROR,
            __file__,
            1,
            "request failed",
            (),
            exc_info=sys.exc_info(),
        )

    payload = json.loads(formatter.format(record))

    assert payload["level"] == "ERROR"
    assert payload["message"] == "request failed"
    assert "RuntimeError: visible failure" in payload["exception"]


def test_configure_logging_supports_json_and_text() -> None:
    root = logging.getLogger()
    original_handlers = root.handlers.copy()
    original_level = root.level
    try:
        configure_logging(settings())
        assert isinstance(root.handlers[0].formatter, JsonFormatter)

        configure_logging(settings(log_format=LogFormat.TEXT))
        assert not isinstance(root.handlers[0].formatter, JsonFormatter)
    finally:
        root.handlers = original_handlers
        root.setLevel(original_level)


def test_database_check_executes_probe() -> None:
    engine = MagicMock()
    with patch("florabase.db.session.get_engine", return_value=engine):
        check_database()

    engine.connect.return_value.__enter__.return_value.execute.assert_called_once()


def test_database_session_commits_and_rolls_back() -> None:
    session = MagicMock()
    session_class = MagicMock()
    session_class.return_value.__enter__.return_value = session
    with (
        patch("florabase.db.session.get_engine", return_value=MagicMock()),
        patch("florabase.db.session.Session", session_class),
    ):
        successful = get_database_session()
        assert next(successful) is session
        with pytest.raises(StopIteration):
            next(successful)
        session.commit.assert_called_once()

        failing = cast(Generator[object], get_database_session())
        assert next(failing) is session
        with pytest.raises(RuntimeError, match="failure"):
            failing.throw(RuntimeError("failure"))
        session.rollback.assert_called_once()


def _session_dependencies(dependant: Dependant) -> Iterator[Dependant]:
    for dependency in dependant.dependencies:
        if dependency.call is get_database_session:
            yield dependency
        yield from _session_dependencies(dependency)


def test_every_route_uses_one_function_scoped_database_session() -> None:
    """TX-001: commit must precede the response, and one request must own one Session."""
    checked_routes = 0
    for context in iter_route_contexts(app.routes):
        route = context.route
        if not isinstance(route, APIRoute):
            continue
        sessions = list(_session_dependencies(route.dependant))
        if not sessions:
            continue
        checked_routes += 1
        scopes = {dependency.scope for dependency in sessions}
        assert scopes == {"function"}, f"{sorted(route.methods or ())} {context.path}: {scopes}"
    assert checked_routes > 150


def _send_probe_write(*, fail_commit: bool) -> list[str]:
    """Drive the production dependency declaration through ASGI and record the event order."""
    events: list[str] = []
    session = MagicMock()
    session.commit.side_effect = (
        RuntimeError("commit failed") if fail_commit else lambda: events.append("commit")
    )
    session.rollback.side_effect = lambda: events.append("rollback")
    session_class = MagicMock()
    session_class.return_value.__enter__.return_value = session
    probe = FastAPI()

    @probe.post("/write", status_code=201)
    def write(
        database: Annotated[Session, Depends(get_database_session, scope="function")],
    ) -> dict[str, bool]:
        events.append("endpoint")
        return {"ok": database is session}

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        if message["type"] == "http.response.start":
            events.append(f"response-start {message['status']}")

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/write",
        "raw_path": b"/write",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 1),
        "server": ("testserver", 80),
    }
    with (
        patch("florabase.db.session.get_engine", return_value=MagicMock()),
        patch("florabase.db.session.Session", session_class),
        contextlib.suppress(RuntimeError),
    ):
        asyncio.run(probe(scope, receive, send))  # type: ignore[arg-type]
    return events


def test_function_scoped_session_commits_before_response_start() -> None:
    assert _send_probe_write(fail_commit=False) == ["endpoint", "commit", "response-start 201"]


def test_function_scoped_commit_failure_never_sends_success() -> None:
    assert _send_probe_write(fail_commit=True) == ["endpoint", "rollback", "response-start 500"]


def test_engine_uses_central_settings() -> None:
    get_engine.cache_clear()
    with patch("florabase.db.session.get_settings", return_value=settings()):
        engine = get_engine()
    try:
        assert engine.url.database == "test"
    finally:
        engine.dispose()
        get_engine.cache_clear()


def test_app_applies_cors_and_lifespan_logging() -> None:
    with patch("florabase.main.get_settings", return_value=settings()):
        application = create_app()
    assert application.user_middleware[0].kwargs["allow_origins"] == ["http://localhost:5173"]

    async def enter_lifespan() -> None:
        with (
            patch("florabase.main.get_settings", return_value=settings()),
            patch("florabase.main.configure_logging") as configure,
        ):
            async with lifespan(application):
                configure.assert_called_once()

    asyncio.run(enter_lifespan())
