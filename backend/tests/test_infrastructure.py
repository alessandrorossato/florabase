import asyncio
import contextlib
import json
import logging
import sys
from collections.abc import Callable, Generator, Iterator, Sequence
from typing import Annotated, cast
from unittest.mock import MagicMock, patch

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute, APIWebSocketRoute, iter_route_contexts
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from starlette.routing import BaseRoute

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
    """Every node in a resolved dependency tree, at any depth, that yields the request Session."""
    for dependency in dependant.dependencies:
        if dependency.call is get_database_session:
            yield dependency
        yield from _session_dependencies(dependency)


def _database_session_violations(routes: Sequence[BaseRoute]) -> tuple[set[str], list[str]]:
    """Inspect each route's effective dependency tree, as FastAPI resolves it per request.

    ``RouteContext.dependant`` merges application, every enclosing router, and route-level
    dependencies with nested sub-dependencies such as authentication and CSRF. Every Session node
    must be function-scoped, so it commits before the response starts, and cached, so all nodes in
    one request share the same Session; FastAPI's cache key includes the scope, and an uncached
    node is solved again, so either deviation creates an independent second transaction.
    """
    operations: set[str] = set()
    violations: list[str] = []
    for context in iter_route_contexts(routes):
        if not isinstance(context.route, APIRoute | APIWebSocketRoute):
            continue
        methods = sorted(context.methods or {"WEBSOCKET"})
        operations.update(f"{method} {context.path}" for method in methods)
        for dependency in _session_dependencies(context.dependant):
            if dependency.scope != "function":
                violations.append(f"{methods} {context.path}: scope={dependency.scope!r}")
            if not dependency.use_cache:
                violations.append(f"{methods} {context.path}: use_cache=False")
    return operations, violations


def test_every_route_uses_one_function_scoped_cached_database_session() -> None:
    """TX-001: commit must precede the response, and one request must own one Session."""
    operations, violations = _database_session_violations(app.routes)
    assert violations == []
    documented = {
        f"{method.upper()} {path}"
        for path, item in app.openapi()["paths"].items()
        for method in item
    }
    assert operations == documented
    session_routes = [
        context
        for context in iter_route_contexts(app.routes)
        if isinstance(context.route, APIRoute)
        and any(True for _ in _session_dependencies(context.dependant))
    ]
    assert len(session_routes) > 150


def _authenticated(
    database: Annotated[Session, Depends(get_database_session, scope="function")],
) -> Session:
    return database


def _uncached_authenticated(
    database: Annotated[Session, Depends(get_database_session, scope="function", use_cache=False)],
) -> Session:
    return database


def _request_scoped_authenticated(
    database: Annotated[Session, Depends(get_database_session)],
) -> Session:
    return database


def _guarded_app(actor: Callable[..., Session]) -> FastAPI:
    """Nest the Session under a router-level authentication dependency, like require_csrf."""
    router = APIRouter(prefix="/guarded", dependencies=[Depends(actor)])

    @router.post("/write")
    def write(
        actor_database: Annotated[Session, Depends(actor)],
        database: Annotated[Session, Depends(get_database_session, scope="function")],
    ) -> dict[str, bool]:
        return {"shared": actor_database is database}

    probe = FastAPI()
    outer = APIRouter(prefix="/api")
    outer.include_router(router)
    probe.include_router(outer)
    return probe


def test_session_guard_accepts_nested_cached_function_scope() -> None:
    operations, violations = _database_session_violations(_guarded_app(_authenticated).routes)
    assert operations == {"POST /api/guarded/write"}
    assert violations == []


@pytest.mark.parametrize(
    ("actor", "expected"),
    [
        (_uncached_authenticated, "use_cache=False"),
        (_request_scoped_authenticated, "scope=None"),
    ],
)
def test_session_guard_rejects_nested_uncached_or_request_scoped_session(
    actor: Callable[..., Session], expected: str
) -> None:
    _, violations = _database_session_violations(_guarded_app(actor).routes)
    assert violations
    assert all(violation.endswith(expected) for violation in violations)
    assert all(
        "POST" in violation and "/api/guarded/write" in violation for violation in violations
    )


def _shares_one_session(actor: Callable[..., Session]) -> bool:
    """Resolve the endpoint's cached Session first, then an authentication-style dependency."""
    probe = FastAPI()

    @probe.post("/write")
    def write(
        database: Annotated[Session, Depends(get_database_session, scope="function")],
        actor_database: Annotated[Session, Depends(actor)],
    ) -> dict[str, bool]:
        return {"shared": actor_database is database}

    session_class = MagicMock()
    session_class.return_value.__enter__.side_effect = lambda: MagicMock()
    with (
        patch("florabase.db.session.get_engine", return_value=MagicMock()),
        patch("florabase.db.session.Session", session_class),
        TestClient(probe) as client,
    ):
        return bool(client.post("/write").json()["shared"])


def test_rejected_session_declarations_really_open_a_second_session() -> None:
    """The rejected declarations are not cosmetic: each can split one request's transaction."""
    assert _shares_one_session(_authenticated)
    assert not _shares_one_session(_uncached_authenticated)
    assert not _shares_one_session(_request_scoped_authenticated)


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
