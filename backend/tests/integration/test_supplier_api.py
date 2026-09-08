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
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.core.config import CookieMode, Environment, Settings, get_settings
from florabase.db.session import get_database_session
from florabase.main import app
from florabase.plants.model import Plant, PlantGroup
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing
from florabase.suppliers.model import Supplier

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


def test_create_minimal_full_list_get_update_retire_reactivate_and_retention(
    authenticated_browser: tuple[str, str], database_connection: Connection
) -> None:
    first_status, headers, first = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/suppliers",
        {"name": "  Rare   Palm Seeds ", "kind": "seller"},
    )
    assert first_status == 201
    first_id = UUID(first["id"])
    assert first_id.version == 7
    assert headers["location"] == f"/api/v1/suppliers/{first_id}"
    assert first["name"] == "Rare Palm Seeds"
    assert first["website"] is first["email"] is first["phone"] is first["notes"] is None

    full_status, _, full = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/suppliers",
        {
            "name": "Local nursery",
            "kind": "nursery",
            "website": "https://nursery.example",
            "email": " hello@nursery.example ",
            "phone": " +39  123 ",
            "notes": " Seasonal stock.\r\nCall first. ",
        },
    )
    assert full_status == 201
    assert full["email"] == "hello@nursery.example"
    assert full["phone"] == "+39 123"
    assert full["notes"] == "Seasonal stock.\nCall first."

    # Same display name is a legitimate distinct stable identity.
    duplicate_status, _, duplicate = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/suppliers",
        {"name": "Rare Palm Seeds", "kind": "person"},
    )
    assert duplicate_status == 201
    assert duplicate["id"] != first["id"]

    cookie, _ = authenticated_browser
    list_status, _, listed = request("GET", "/api/v1/suppliers", headers={"cookie": cookie})
    assert list_status == 200
    assert [(item["name"], item["kind"]) for item in listed] == [
        ("Local nursery", "nursery"),
        ("Rare Palm Seeds", "person"),
        ("Rare Palm Seeds", "seller"),
    ]
    get_status, _, got = request("GET", f"/api/v1/suppliers/{first_id}", headers={"cookie": cookie})
    assert get_status == 200
    assert {key: got[key] for key in first} == first
    assert got["usage_counts"]["direct_records_total"] == 0
    assert got["seed_lots"] == got["plants"] == got["plant_groups"] == []
    assert got["recent_acquisitions"] == []

    update_status, _, updated = mutate(
        authenticated_browser,
        "PUT",
        f"/api/v1/suppliers/{first_id}",
        {"name": "Rare Palm Seeds Europe", "kind": "seller", "email": "eu@example.com"},
    )
    assert update_status == 200
    assert updated["name"] == "Rare Palm Seeds Europe"
    assert updated["email"] == "eu@example.com"

    retire_status, _, retired = mutate(
        authenticated_browser, "POST", f"/api/v1/suppliers/{first_id}/retire"
    )
    assert retire_status == 200
    assert retired["retired_at"] is not None
    list_status, _, listed = request("GET", "/api/v1/suppliers", headers={"cookie": cookie})
    assert list_status == 200
    assert listed[-1]["id"] == str(first_id)
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        assert (
            database.scalar(
                select(func.count()).select_from(Supplier).where(Supplier.id == first_id)
            )
            == 1
        )

    reactivate_status, _, active = mutate(
        authenticated_browser, "POST", f"/api/v1/suppliers/{first_id}/reactivate"
    )
    assert reactivate_status == 200
    assert active["retired_at"] is None


def test_supplier_hub_counts_direct_links_preserves_history_and_orders_known_dates(
    authenticated_browser: tuple[str, str], database_connection: Connection
) -> None:
    supplier = Supplier(name="RareSeeds Shop", kind="seller")
    identity = BotanicalIdentity(scientific_name="Clitoria ternatea")
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        database.add_all([supplier, identity])
        database.flush()
        current_seed = SeedLot(
            botanical_identity_id=identity.id,
            label="Thai blue seeds",
            source_kind="purchased",
            supplier_id=supplier.id,
            acquisition_date_precision="day",
            acquisition_date_year=2026,
            acquisition_date_month=8,
            acquisition_date_day=30,
            lifecycle="active",
        )
        historical_seed = SeedLot(
            botanical_identity_id=identity.id,
            source_kind="purchased",
            supplier_id=supplier.id,
            lifecycle="lost",
        )
        direct_plant = Plant(
            botanical_identity_id=identity.id,
            direct_origin_kind="purchased",
            supplier_id=supplier.id,
            collection_entry_date_precision="year",
            collection_entry_date_year=2025,
            lifecycle="transferred",
        )
        direct_group = PlantGroup(
            botanical_identity_id=identity.id,
            direct_origin_kind="gift_exchange",
            supplier_id=supplier.id,
            label="Blue group",
            collection_entry_date_precision="month",
            collection_entry_date_year=2026,
            collection_entry_date_month=9,
            lifecycle="active",
        )
        database.add_all([current_seed, historical_seed, direct_plant, direct_group])
        database.flush()
        sowing = Sowing(seed_lot_id=current_seed.id, lifecycle="completed")
        database.add(sowing)
        database.flush()
        propagated_plant = Plant(
            botanical_identity_id=identity.id,
            originating_sowing_id=sowing.id,
            lifecycle="active",
        )
        database.add(propagated_plant)
        database.commit()
        supplier_id = supplier.id
        current_seed_id = current_seed.id
        historical_seed_id = historical_seed.id
        direct_plant_id = direct_plant.id
        direct_group_id = direct_group.id
        propagated_plant_id = propagated_plant.id

    cookie, _ = authenticated_browser
    status_code, _, detail = request(
        "GET", f"/api/v1/suppliers/{supplier_id}", headers={"cookie": cookie}
    )
    assert status_code == 200
    assert detail["usage_counts"] == {
        "seed_lots_active": 1,
        "seed_lots_total": 2,
        "plants_active": 0,
        "plants_total": 1,
        "plant_groups_active": 1,
        "plant_groups_total": 1,
        "direct_records_active": 2,
        "direct_records_total": 4,
    }
    assert [item["id"] for item in detail["seed_lots"]] == [
        str(current_seed_id),
        str(historical_seed_id),
    ]
    assert [item["id"] for item in detail["plants"]] == [str(direct_plant_id)]
    assert [item["id"] for item in detail["plant_groups"]] == [str(direct_group_id)]
    assert all(
        item["id"] != str(propagated_plant_id)
        for items in (detail["plants"], detail["recent_acquisitions"])
        for item in items
    )
    assert [item["record_type"] for item in detail["recent_acquisitions"]] == [
        "plant_group",
        "seed_lot",
        "plant",
    ]
    assert detail["seed_lots"][0]["botanical_identity"]["display_label"] == ("Clitoria ternatea")
    assert detail["seed_lots"][1]["acquisition_date"] is None

    list_status, _, listed = request("GET", "/api/v1/suppliers", headers={"cookie": cookie})
    assert list_status == 200
    summary = next(item for item in listed if item["id"] == str(supplier_id))
    assert summary["usage_counts"] == detail["usage_counts"]

    retire_status, _, retired = mutate(
        authenticated_browser, "POST", f"/api/v1/suppliers/{supplier_id}/retire"
    )
    assert retire_status == 200
    assert retired["retired_at"] is not None
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        retained_seed = database.get(SeedLot, current_seed_id)
        retained_plant = database.get(Plant, direct_plant_id)
        retained_group = database.get(PlantGroup, direct_group_id)
        assert retained_seed is not None
        assert retained_seed.supplier_id == supplier_id
        assert retained_plant is not None
        assert retained_plant.supplier_id == supplier_id
        assert retained_group is not None
        assert retained_group.supplier_id == supplier_id


@pytest.mark.parametrize(
    "payload",
    [
        {"name": " ", "kind": "seller"},
        {"name": "Source", "kind": "invalid"},
        {"name": "Source", "kind": "other", "website": "ftp://example.com"},
        {"name": "Source", "kind": "other", "email": "bad"},
        {"name": "Bad\u0000Name", "kind": "other"},
    ],
)
def test_supplier_validation(
    authenticated_browser: tuple[str, str], payload: Mapping[str, object]
) -> None:
    status_code, _, _ = mutate(authenticated_browser, "POST", "/api/v1/suppliers", payload)
    assert status_code == 422


def test_supplier_not_found_authentication_origin_csrf_and_owner(
    authenticated_browser: tuple[str, str], database_connection: Connection
) -> None:
    cookie, csrf = authenticated_browser
    missing = uuid7()
    status_code, _, body = request(
        "GET", f"/api/v1/suppliers/{missing}", headers={"cookie": cookie}
    )
    assert status_code == 404
    assert body["detail"]["code"] == "supplier_not_found"
    assert request("GET", "/api/v1/suppliers")[0] == 401

    payload = {"name": "Source", "kind": "other"}
    for headers in (
        {"origin": ORIGIN, "x-csrf-token": csrf},
        {"cookie": cookie, "origin": ORIGIN},
        {"cookie": cookie, "origin": ORIGIN, "x-csrf-token": "wrong"},
        {"cookie": cookie, "x-csrf-token": csrf},
        {"cookie": cookie, "origin": "https://evil.example", "x-csrf-token": csrf},
    ):
        assert request("POST", "/api/v1/suppliers", body=payload, headers=headers)[0] in {401, 403}

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
        status_code, _, body = request("POST", "/api/v1/suppliers", body=payload)
    finally:
        app.dependency_overrides.pop(require_csrf, None)
    assert status_code == 403
    assert body["detail"] == "Request forbidden"
