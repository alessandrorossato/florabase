import asyncio
import json
from collections.abc import Iterator, Mapping
from typing import Any, cast
from uuid import UUID, uuid7

import pytest
from sqlalchemy import Connection, func, select
from sqlalchemy.orm import Session
from starlette.types import Message, Receive, Scope, Send

from florabase.auth.dependencies import AuthenticatedActor, require_csrf
from florabase.auth.model import AuthSession
from florabase.auth.service import bootstrap_owner
from florabase.core.config import CookieMode, Environment, Settings, get_settings
from florabase.db.session import get_database_session
from florabase.locations.model import Location
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
        (name.lower().encode(), value.encode()) for name, value in (headers or {}).items()
    )
    response_status = 0
    response_headers: dict[str, str] = {}
    response_body = bytearray()
    sent = False

    async def receive() -> Message:
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": raw_body, "more_body": False}

    async def send(message: Message) -> None:
        nonlocal response_status
        if message["type"] == "http.response.start":
            response_status = cast(int, message["status"])
            response_headers.update(
                (name.decode(), value.decode()) for name, value in message["headers"]
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
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": raw_headers,
        "client": ("127.0.0.1", 1),
        "server": ("florabase.example", 443),
    }
    await app(scope, cast(Receive, receive), cast(Send, send))
    return response_status, response_headers, json.loads(response_body) if response_body else None


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


def mutate(
    browser: tuple[str, str], method: str, path: str, body: Mapping[str, object] | None = None
) -> tuple[int, dict[str, str], Any]:
    cookie, csrf = browser
    return request(
        method, path, body=body, headers={"cookie": cookie, "origin": ORIGIN, "x-csrf-token": csrf}
    )


def create_location(
    browser: tuple[str, str], name: str, parent_id: str | None = None
) -> tuple[int, dict[str, str], Any]:
    return mutate(browser, "POST", "/api/v1/locations", {"name": name, "parent_id": parent_id})


def test_root_child_deep_hierarchy_rename_reparent_paths_and_deterministic_list(
    authenticated_browser: tuple[str, str],
) -> None:
    root_status, headers, house = create_location(authenticated_browser, "  House  ")
    assert root_status == 201
    house_id = UUID(house["id"])
    assert house_id.version == 7
    assert headers["location"] == f"/api/v1/locations/{house_id}"
    assert house["name"] == house["display_path"] == "House"
    assert house["parent_id"] is None

    _, _, garden = create_location(authenticated_browser, "Garden")
    _, _, basement = create_location(authenticated_browser, "Basement", house["id"])
    _, _, cabinet = create_location(authenticated_browser, "Seed cabinet", basement["id"])
    _, _, drawer = create_location(authenticated_browser, "Drawer A", cabinet["id"])
    assert drawer["display_path"] == "House → Basement → Seed cabinet → Drawer A"

    # Identical sibling names are allowed and stable UUID remains identity.
    _, _, first_shelf = create_location(authenticated_browser, "Shelf 1", house["id"])
    duplicate_status, _, second_shelf = create_location(
        authenticated_browser, "Shelf 1", house["id"]
    )
    assert duplicate_status == 201
    assert first_shelf["id"] != second_shelf["id"]

    update_status, _, renamed = mutate(
        authenticated_browser,
        "PUT",
        f"/api/v1/locations/{cabinet['id']}",
        {"name": "Seed cupboard", "parent_id": garden["id"]},
    )
    assert update_status == 200
    assert renamed["display_path"] == "Garden → Seed cupboard"

    cookie, _ = authenticated_browser
    get_status, _, got = request(
        "GET", f"/api/v1/locations/{drawer['id']}", headers={"cookie": cookie}
    )
    assert get_status == 200
    assert got["display_path"] == "Garden → Seed cupboard → Drawer A"

    list_status, _, first_list = request("GET", "/api/v1/locations", headers={"cookie": cookie})
    second_status, _, second_list = request("GET", "/api/v1/locations", headers={"cookie": cookie})
    assert list_status == second_status == 200
    assert first_list == second_list
    assert [item["display_path"] for item in first_list] == sorted(
        [item["display_path"] for item in first_list], key=str.casefold
    )


def test_cycle_missing_parent_and_validation_rejection(
    authenticated_browser: tuple[str, str],
) -> None:
    _, _, root = create_location(authenticated_browser, "Greenhouse")
    _, _, child = create_location(authenticated_browser, "Upper shelf", root["id"])
    _, _, leaf = create_location(authenticated_browser, "Tray", child["id"])

    for parent_id in (root["id"], child["id"], leaf["id"]):
        status_code, _, body = mutate(
            authenticated_browser,
            "PUT",
            f"/api/v1/locations/{root['id']}",
            {"name": "Greenhouse", "parent_id": parent_id},
        )
        assert status_code == 409
        assert body["detail"]["code"] == "location_cycle"

    status_code, _, body = create_location(authenticated_browser, "Shelf", str(uuid7()))
    assert status_code == 409
    assert body["detail"]["code"] == "location_parent_not_found"
    for name in (" ", "Bad\u0000name"):
        assert create_location(authenticated_browser, name)[0] == 422


def test_safe_retirement_reactivation_retention_and_retired_ancestor_rules(
    authenticated_browser: tuple[str, str], database_connection: Connection
) -> None:
    _, _, root = create_location(authenticated_browser, "House")
    _, _, child = create_location(authenticated_browser, "Basement", root["id"])
    _, _, leaf = create_location(authenticated_browser, "Cabinet", child["id"])

    blocked_status, _, blocked = mutate(
        authenticated_browser, "POST", f"/api/v1/locations/{root['id']}/retire"
    )
    assert blocked_status == 409
    assert blocked["detail"]["code"] == "location_active_descendants"

    for item in (leaf, child, root):
        status_code, _, retired = mutate(
            authenticated_browser, "POST", f"/api/v1/locations/{item['id']}/retire"
        )
        assert status_code == 200
        assert retired["retired_at"] is not None

    blocked_status, _, blocked = mutate(
        authenticated_browser, "POST", f"/api/v1/locations/{leaf['id']}/reactivate"
    )
    assert blocked_status == 409
    assert blocked["detail"]["code"] == "location_retired_ancestor"
    blocked_status, _, blocked = create_location(authenticated_browser, "Drawer", child["id"])
    assert blocked_status == 409
    assert blocked["detail"]["code"] == "location_retired_ancestor"

    for item in (root, child, leaf):
        assert (
            mutate(authenticated_browser, "POST", f"/api/v1/locations/{item['id']}/reactivate")[0]
            == 200
        )

    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        assert database.scalar(select(func.count()).select_from(Location)) == 3


def test_not_found_authentication_origin_csrf_and_owner(
    authenticated_browser: tuple[str, str], database_connection: Connection
) -> None:
    cookie, csrf = authenticated_browser
    missing = uuid7()
    status_code, _, body = request(
        "GET", f"/api/v1/locations/{missing}", headers={"cookie": cookie}
    )
    assert status_code == 404
    assert body["detail"]["code"] == "location_not_found"
    assert request("GET", "/api/v1/locations")[0] == 401

    payload = {"name": "Greenhouse", "parent_id": None}
    for headers in (
        {"origin": ORIGIN, "x-csrf-token": csrf},
        {"cookie": cookie, "origin": ORIGIN},
        {"cookie": cookie, "origin": ORIGIN, "x-csrf-token": "wrong"},
        {"cookie": cookie, "x-csrf-token": csrf},
        {"cookie": cookie, "origin": "https://evil.example", "x-csrf-token": csrf},
    ):
        assert request("POST", "/api/v1/locations", body=payload, headers=headers)[0] in {401, 403}

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
        status_code, _, body = request("POST", "/api/v1/locations", body=payload)
    finally:
        app.dependency_overrides.pop(require_csrf, None)
    assert status_code == 403
    assert body["detail"] == "Request forbidden"
