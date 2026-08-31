import asyncio
import json
from collections.abc import Iterator, Mapping
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from typing import Any, cast
from uuid import UUID, uuid7

import pytest
from sqlalchemy import Connection, Engine, delete, func, select
from sqlalchemy.orm import Session
from starlette.types import Message, Receive, Scope, Send

from florabase.auth.dependencies import AuthenticatedActor, require_csrf
from florabase.auth.model import AuthSession
from florabase.auth.service import bootstrap_owner
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_profiles.model import BotanicalProfile
from florabase.botanical_profiles.schemas import BotanicalProfilePut
from florabase.botanical_profiles.service import put_botanical_profile
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
    try:
        yield response_headers["set-cookie"].split(";", 1)[0], body["csrf_token"]
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def identity_id(database_connection: Connection) -> UUID:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        identity = BotanicalIdentity(scientific_name="Solanum quitoense")
        database.add(identity)
        database.commit()
        return identity.id


def profile_path(identity_id: UUID) -> str:
    return f"/api/v1/botanical-identities/{identity_id}/profile"


def put_profile(
    browser: tuple[str, str], identity_id: UUID, body: Mapping[str, object]
) -> tuple[int, dict[str, str], Any]:
    cookie, csrf_token = browser
    return request(
        "PUT",
        profile_path(identity_id),
        body=body,
        headers={"cookie": cookie, "origin": ORIGIN, "x-csrf-token": csrf_token},
    )


def test_authenticated_create_read_update_and_clear_profile(
    authenticated_browser: tuple[str, str], identity_id: UUID
) -> None:
    cookie, _ = authenticated_browser
    status_code, _, absent = request("GET", profile_path(identity_id), headers={"cookie": cookie})
    assert status_code == 404
    assert absent["detail"]["code"] == "botanical_profile_not_found"

    status_code, headers, created = put_profile(
        authenticated_browser,
        identity_id,
        {
            "description": "  A fruiting shrub.\r\n\r\nSoftly hairy leaves.  ",
            "origin_distribution": "   ",
            "cultivation": "Warm conditions.\nProtect from frost.",
        },
    )
    assert status_code == 201
    assert headers["location"] == profile_path(identity_id)
    assert created == {
        "botanical_identity_id": str(identity_id),
        "description": "A fruiting shrub.\n\nSoftly hairy leaves.",
        "origin_distribution": None,
        "cultivation": "Warm conditions.\nProtect from frost.",
        "uses": None,
        "warnings": None,
    }

    read_status, _, read = request("GET", profile_path(identity_id), headers={"cookie": cookie})
    assert read_status == 200
    assert read == created

    update_status, _, updated = put_profile(
        authenticated_browser,
        identity_id,
        {"description": "Updated description.", "uses": "Fresh fruit and preserves."},
    )
    assert update_status == 200
    assert updated["description"] == "Updated description."
    assert updated["uses"] == "Fresh fruit and preserves."
    assert updated["cultivation"] is None

    clear_one_status, _, cleared_one = put_profile(
        authenticated_browser,
        identity_id,
        {"description": "", "uses": "Fresh fruit and preserves."},
    )
    assert clear_one_status == 200
    assert cleared_one["description"] is None
    assert cleared_one["uses"] == "Fresh fruit and preserves."

    clear_final_status, _, clear_final = put_profile(
        authenticated_browser, identity_id, {"uses": " \n "}
    )
    assert clear_final_status == 204
    assert clear_final is None
    after_status, _, after = request("GET", profile_path(identity_id), headers={"cookie": cookie})
    assert after_status == 404
    assert after["detail"]["code"] == "botanical_profile_not_found"


def test_empty_create_validation_and_nonexistent_parent_are_stable(
    authenticated_browser: tuple[str, str], identity_id: UUID
) -> None:
    empty_status, _, empty = put_profile(authenticated_browser, identity_id, {})
    assert empty_status == 422
    assert empty["detail"]["code"] == "botanical_profile_empty"

    missing_id = uuid7()
    missing_status, _, missing = put_profile(
        authenticated_browser, missing_id, {"description": "General knowledge."}
    )
    assert missing_status == 404
    assert missing["detail"]["code"] == "botanical_identity_not_found"

    cookie, _ = authenticated_browser
    read_status, _, read = request("GET", profile_path(missing_id), headers={"cookie": cookie})
    assert read_status == 404
    assert read["detail"]["code"] == "botanical_identity_not_found"

    invalid_status, _, _ = put_profile(
        authenticated_browser, identity_id, {"description": "bad\x1fcontrol"}
    )
    assert invalid_status == 422
    extra_status, _, _ = put_profile(
        authenticated_browser, identity_id, {"description": "Valid", "id": str(uuid7())}
    )
    assert extra_status == 422


def test_profile_security_requires_session_origin_csrf_and_owner(
    authenticated_browser: tuple[str, str],
    identity_id: UUID,
    database_connection: Connection,
) -> None:
    cookie, csrf_token = authenticated_browser
    path = profile_path(identity_id)

    status_code, _, body = request("GET", path)
    assert status_code == 401
    assert body["detail"] == "Authentication required"

    for headers in (
        {"origin": ORIGIN, "x-csrf-token": csrf_token},
        {"cookie": cookie, "origin": ORIGIN},
        {"cookie": cookie, "origin": ORIGIN, "x-csrf-token": "wrong"},
        {"cookie": cookie, "x-csrf-token": csrf_token},
        {"cookie": cookie, "origin": "https://evil.example", "x-csrf-token": csrf_token},
    ):
        status_code, _, _ = request(
            "PUT", path, body={"description": "General knowledge."}, headers=headers
        )
        assert status_code in {401, 403}

    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        auth_session = database.scalars(select(AuthSession)).one()
        non_owner = AuthenticatedActor(
            user_id=auth_session.user_id,
            login_name="editor",
            display_name=None,
            owner=False,
            session=auth_session,
        )
    app.dependency_overrides[require_csrf] = lambda: non_owner
    try:
        status_code, _, body = request("PUT", path, body={"description": "General knowledge."})
    finally:
        app.dependency_overrides.pop(require_csrf, None)
    assert status_code == 403
    assert body["detail"] == "Request forbidden"


def test_concurrent_first_writes_converge_on_one_profile(database_engine: Engine) -> None:
    identity_id = uuid7()
    with Session(database_engine) as database:
        database.add(BotanicalIdentity(id=identity_id, scientific_name=f"Concurrent {identity_id}"))
        database.commit()

    barrier = Barrier(2)

    def write(description: str) -> None:
        with Session(database_engine) as database:
            barrier.wait()
            put_botanical_profile(
                database,
                identity_id,
                BotanicalProfilePut(description=description),
            )
            database.commit()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(write, value) for value in ("First writer", "Second writer")]
            for future in futures:
                future.result()

        with Session(database_engine) as database:
            assert (
                database.scalar(
                    select(func.count())
                    .select_from(BotanicalProfile)
                    .where(BotanicalProfile.botanical_identity_id == identity_id)
                )
                == 1
            )
            profile = database.get(BotanicalProfile, identity_id)
            assert profile is not None
            assert profile.description in {"First writer", "Second writer"}
    finally:
        with Session(database_engine) as database:
            database.execute(
                delete(BotanicalProfile).where(
                    BotanicalProfile.botanical_identity_id == identity_id
                )
            )
            database.execute(delete(BotanicalIdentity).where(BotanicalIdentity.id == identity_id))
            database.commit()
