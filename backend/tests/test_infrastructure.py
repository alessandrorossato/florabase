import asyncio
import json
import logging
import sys
from collections.abc import Generator
from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from florabase.core.config import CookieMode, Environment, LogFormat, Settings
from florabase.core.logging import JsonFormatter, configure_logging
from florabase.db.session import check_database, get_database_session, get_engine
from florabase.main import create_app, lifespan


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
