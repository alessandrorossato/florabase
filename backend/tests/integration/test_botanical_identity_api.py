import asyncio
import json
from collections.abc import Iterator, Mapping
from datetime import datetime
from typing import Any, cast
from uuid import UUID, uuid7

import pytest
from sqlalchemy import Connection, func, select
from sqlalchemy.orm import Session
from starlette.types import Message, Receive, Scope, Send

from florabase.auth.dependencies import AuthenticatedActor, require_csrf
from florabase.auth.model import AuthSession, User
from florabase.auth.service import bootstrap_owner
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.core.config import CookieMode, Environment, Settings, get_settings
from florabase.db.session import get_database_session
from florabase.main import app

pytestmark = pytest.mark.integration

PASSWORD = "correct horse battery staple"
ORIGIN = "https://florabase.example"


def settings() -> Settings:
    return Settings.model_validate(
        {
            "environment": Environment.TEST,
            "database_url": "postgresql+psycopg://unused",
            "canonical_origin": ORIGIN,
            "cookie_mode": CookieMode.SECURE,
        }
    )


def override_database(connection: Connection) -> Iterator[Session]:
    with Session(bind=connection, join_transaction_mode="create_savepoint") as database:
        try:
            yield database
            database.commit()
        except Exception:
            database.rollback()
            raise


async def asgi_request(
    method: str,
    path: str,
    *,
    body: Mapping[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], Any]:
    raw_body = json.dumps(body).encode() if body is not None else b""
    raw_headers = [(b"content-type", b"application/json")]
    raw_headers.extend(
        (name.lower().encode("ascii"), value.encode("ascii"))
        for name, value in (headers or {}).items()
    )
    response_status = 0
    response_headers: dict[str, str] = {}
    response_body = bytearray()
    request_sent = False

    async def receive() -> Message:
        nonlocal request_sent
        if request_sent:
            return {"type": "http.disconnect"}
        request_sent = True
        return {"type": "http.request", "body": raw_body, "more_body": False}

    async def send(message: Message) -> None:
        nonlocal response_status
        if message["type"] == "http.response.start":
            response_status = cast(int, message["status"])
            response_headers.update(
                (name.decode("latin-1"), value.decode("latin-1"))
                for name, value in message["headers"]
            )
        elif message["type"] == "http.response.body":
            response_body.extend(message.get("body", b""))

    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "https",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "headers": raw_headers,
        "client": ("127.0.0.1", 1234),
        "server": ("florabase.example", 443),
    }
    await app(scope, cast(Receive, receive), cast(Send, send))
    decoded = json.loads(response_body) if response_body else None
    return response_status, response_headers, decoded


def request(
    method: str,
    path: str,
    *,
    body: Mapping[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], Any]:
    return asyncio.run(asgi_request(method, path, body=body, headers=headers))


@pytest.fixture
def authenticated_browser(database_connection: Connection) -> Iterator[tuple[str, str]]:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        bootstrap_owner(database, "owner", PASSWORD, "Florabase Owner")
        database.commit()

    def database_override() -> Iterator[Session]:
        yield from override_database(database_connection)

    app.dependency_overrides[get_database_session] = database_override
    app.dependency_overrides[get_settings] = settings
    status_code, response_headers, body = request(
        "POST",
        "/api/v1/auth/login",
        body={"login_name": "owner", "password": PASSWORD},
        headers={"origin": ORIGIN},
    )
    assert status_code == 200
    cookie = response_headers["set-cookie"].split(";", 1)[0]
    try:
        yield cookie, body["csrf_token"]
    finally:
        app.dependency_overrides.clear()


def create_identity(
    browser: tuple[str, str], payload: Mapping[str, object]
) -> tuple[int, dict[str, str], Any]:
    cookie, csrf_token = browser
    return request(
        "POST",
        "/api/v1/botanical-identities",
        body=payload,
        headers={"cookie": cookie, "origin": ORIGIN, "x-csrf-token": csrf_token},
    )


def test_csrf_recovery_endpoint_rotates_only_csrf_and_enforces_session_origin(
    authenticated_browser: tuple[str, str], database_connection: Connection
) -> None:
    cookie, previous_csrf = authenticated_browser
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        persisted_before = database.scalars(select(AuthSession)).one()
        session_id = persisted_before.id
        session_digest = persisted_before.token_digest

    status_code, headers, body = request(
        "POST",
        "/api/v1/auth/csrf",
        headers={"cookie": cookie, "origin": ORIGIN},
    )
    assert status_code == 200
    assert headers["cache-control"] == "no-store"
    assert "set-cookie" not in headers
    assert set(body) == {"csrf_token"}
    new_csrf = body["csrf_token"]
    assert new_csrf != previous_csrf

    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        persisted_after = database.get(AuthSession, session_id)
        assert persisted_after is not None
        assert persisted_after.token_digest == session_digest

    old_status, _, _ = request(
        "POST",
        "/api/v1/botanical-identities",
        body={"scientific_name": "Acer palmatum"},
        headers={"cookie": cookie, "origin": ORIGIN, "x-csrf-token": previous_csrf},
    )
    assert old_status == 403
    new_status, _, _ = request(
        "POST",
        "/api/v1/botanical-identities",
        body={"scientific_name": "Acer palmatum"},
        headers={"cookie": cookie, "origin": ORIGIN, "x-csrf-token": new_csrf},
    )
    assert new_status == 201

    for invalid_cookie in (None, "__Host-florabase-session=invalid"):
        request_headers = {"origin": ORIGIN}
        if invalid_cookie is not None:
            request_headers["cookie"] = invalid_cookie
        invalid_status, _, invalid_body = request(
            "POST", "/api/v1/auth/csrf", headers=request_headers
        )
        assert invalid_status == 401
        assert invalid_body["detail"] == "Authentication required"

    for invalid_origin in (None, "https://evil.example"):
        request_headers = {"cookie": cookie}
        if invalid_origin is not None:
            request_headers["origin"] = invalid_origin
        invalid_status, _, invalid_body = request(
            "POST", "/api/v1/auth/csrf", headers=request_headers
        )
        assert invalid_status == 403
        assert invalid_body["detail"] == "Request forbidden"


def test_authenticated_owner_creates_and_reads_normalized_identity(
    authenticated_browser: tuple[str, str],
) -> None:
    status_code, headers, body = create_identity(
        authenticated_browser,
        {
            "scientific_name": "  Acer\tpalmatum ",
            "cultivar_name": " “Bloodgood” ",
            "common_name": " Japanese   maple ",
        },
    )

    identity_id = UUID(body["id"])
    assert status_code == 201
    assert identity_id.version == 7
    assert headers["location"] == f"/api/v1/botanical-identities/{identity_id}"
    assert body["scientific_name"] == "Acer palmatum"
    assert body["cultivar_name"] == "Bloodgood"
    assert body["common_name"] == "Japanese maple"
    assert body["display_label"] == "Acer palmatum \u2018Bloodgood\u2019"
    assert datetime.fromisoformat(body["created_at"]).utcoffset() is not None
    assert datetime.fromisoformat(body["updated_at"]).utcoffset() is not None

    cookie, _ = authenticated_browser
    read_status, _, read_body = request(
        "GET", f"/api/v1/botanical-identities/{identity_id}", headers={"cookie": cookie}
    )
    assert read_status == 200
    assert read_body == body


def test_optional_blanks_normalize_to_null(
    authenticated_browser: tuple[str, str],
) -> None:
    status_code, _, body = create_identity(
        authenticated_browser,
        {"scientific_name": "Solanum quitoense", "cultivar_name": " ", "common_name": "\t"},
    )
    assert status_code == 201
    assert body["cultivar_name"] is None
    assert body["common_name"] is None
    assert body["display_label"] == "Solanum quitoense"


def test_authenticated_directory_is_empty_safe_and_does_not_mutate(
    authenticated_browser: tuple[str, str], database_connection: Connection
) -> None:
    cookie, _ = authenticated_browser
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        count_before = database.scalar(select(func.count()).select_from(BotanicalIdentity))

    status_code, _, body = request(
        "GET", "/api/v1/botanical-identities", headers={"cookie": cookie}
    )

    assert status_code == 200
    assert body == []
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        count_after = database.scalar(select(func.count()).select_from(BotanicalIdentity))
    assert count_after == count_before == 0

    unauthenticated_status, _, unauthenticated_body = request("GET", "/api/v1/botanical-identities")
    assert unauthenticated_status == 401
    assert unauthenticated_body["detail"] == "Authentication required"


def test_directory_returns_created_identities_in_deterministic_botanical_order(
    authenticated_browser: tuple[str, str], database_connection: Connection
) -> None:
    created = {}
    for payload in (
        {"scientific_name": "Solanum quitoense", "cultivar_name": "Zulu"},
        {"scientific_name": "acer palmatum", "common_name": "Japanese maple"},
        {"scientific_name": "Solanum quitoense", "cultivar_name": "alba"},
        {"scientific_name": "Solanum quitoense"},
        {"scientific_name": "Annona cherimola"},
    ):
        status_code, _, body = create_identity(authenticated_browser, payload)
        assert status_code == 201
        created[body["display_label"]] = body["id"]

    cookie, _ = authenticated_browser
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        persisted_before = list(database.scalars(select(BotanicalIdentity)))
    status_code, _, body = request(
        "GET", "/api/v1/botanical-identities", headers={"cookie": cookie}
    )

    assert status_code == 200
    assert [item["display_label"] for item in body] == [
        "acer palmatum",
        "Annona cherimola",
        "Solanum quitoense",
        "Solanum quitoense \u2018alba\u2019",
        "Solanum quitoense \u2018Zulu\u2019",
    ]
    assert [item["id"] for item in body] == [created[item["display_label"]] for item in body]
    assert body[0]["common_name"] == "Japanese maple"
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        persisted_after = list(database.scalars(select(BotanicalIdentity)))
    assert [(item.id, item.updated_at) for item in persisted_after] == [
        (item.id, item.updated_at) for item in persisted_before
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {"scientific_name": "   "},
        {"scientific_name": "x" * 256},
        {"scientific_name": "Acer palmatum", "cultivar_name": "x" * 121},
        {"scientific_name": "Acer palmatum", "common_name": "x" * 161},
        {"scientific_name": "Acer\x00palmatum"},
        {"scientific_name": "Acer palmatum", "unknown": "value"},
        {"scientific_name": "Acer palmatum", "id": str(UUID(int=0))},
        {"scientific_name": "Acer palmatum", "created_at": "2026-08-28T00:00:00Z"},
    ],
)
def test_create_validation_rejects_invalid_or_read_only_input(
    authenticated_browser: tuple[str, str], payload: dict[str, object]
) -> None:
    status_code, _, _ = create_identity(authenticated_browser, payload)
    assert status_code == 422


def test_duplicate_conflicts_are_case_insensitive_and_qualified_identity_is_distinct(
    authenticated_browser: tuple[str, str],
) -> None:
    _, _, unqualified = create_identity(authenticated_browser, {"scientific_name": "Acer palmatum"})
    status_code, _, conflict = create_identity(
        authenticated_browser, {"scientific_name": "acer palmatum"}
    )
    assert status_code == 409
    assert conflict["detail"] == {
        "code": "botanical_identity_conflict",
        "message": "Botanical identity already exists",
        "existing_id": unqualified["id"],
    }

    status_code, _, qualified = create_identity(
        authenticated_browser,
        {"scientific_name": "Acer palmatum", "cultivar_name": "Bloodgood"},
    )
    assert status_code == 201
    assert qualified["id"] != unqualified["id"]
    for scientific_name, cultivar_name in (
        ("Acer palmatum", "Bloodgood"),
        ("acer palmatum", "bloodGOOD"),
    ):
        status_code, _, conflict = create_identity(
            authenticated_browser,
            {"scientific_name": scientific_name, "cultivar_name": cultivar_name},
        )
        assert status_code == 409
        assert conflict["detail"]["existing_id"] == qualified["id"]


def test_read_not_found_malformed_and_authentication_behavior(
    authenticated_browser: tuple[str, str],
) -> None:
    cookie, _ = authenticated_browser
    missing_id = uuid7()
    status_code, _, body = request(
        "GET", f"/api/v1/botanical-identities/{missing_id}", headers={"cookie": cookie}
    )
    assert status_code == 404
    assert body["detail"]["code"] == "botanical_identity_not_found"

    status_code, _, _ = request(
        "GET", "/api/v1/botanical-identities/not-a-uuid", headers={"cookie": cookie}
    )
    assert status_code == 422

    status_code, _, body = request("GET", f"/api/v1/botanical-identities/{missing_id}")
    assert status_code == 401
    assert body["detail"] == "Authentication required"


def test_create_requires_authentication_origin_csrf_and_owner(
    authenticated_browser: tuple[str, str], database_connection: Connection
) -> None:
    cookie, csrf_token = authenticated_browser
    path = "/api/v1/botanical-identities"
    payload = {"scientific_name": "Acer palmatum"}

    status_code, _, _ = request(
        "POST", path, body=payload, headers={"origin": ORIGIN, "x-csrf-token": csrf_token}
    )
    assert status_code == 401
    for headers in (
        {"cookie": cookie, "origin": ORIGIN},
        {"cookie": cookie, "origin": ORIGIN, "x-csrf-token": "wrong"},
        {"cookie": cookie, "x-csrf-token": csrf_token},
        {"cookie": cookie, "origin": "https://evil.example", "x-csrf-token": csrf_token},
    ):
        status_code, _, body = request("POST", path, body=payload, headers=headers)
        assert status_code == 403
        assert body["detail"] == "Request forbidden"

    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        owner = database.scalars(select(User)).one()
        auth_session = database.scalars(select(AuthSession)).one()
        member_actor = AuthenticatedActor(
            user_id=owner.id,
            login_name=owner.login_name,
            display_name=owner.display_name,
            owner=False,
            session=auth_session,
        )
    app.dependency_overrides[require_csrf] = lambda: member_actor
    status_code, _, body = request(
        "POST",
        path,
        body=payload,
    )
    assert status_code == 403
    assert body["detail"] == "Request forbidden"
