import asyncio
import json
from collections.abc import Iterator, Mapping
from datetime import UTC, datetime
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
from florabase.geographic_places.model import GeographicPlace
from florabase.locations.model import Location
from florabase.main import app
from florabase.seed_lots.model import SeedLot
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


@pytest.fixture
def references(database_connection: Connection) -> dict[str, str]:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        identity = BotanicalIdentity(scientific_name="Phoenix dactylifera", cultivar_name="Medjool")
        supplier = Supplier(name="Heritage Seeds", kind="seller", retired_at=datetime.now(UTC))
        location = Location(name="Archive drawer", retired_at=datetime.now(UTC))
        parent = database.scalars(
            select(GeographicPlace).where(GeographicPlace.place_kind == "canonical").limit(1)
        ).one()
        place = GeographicPlace(
            name="Historic oasis",
            parent_id=parent.id,
            place_kind="custom",
            retired_at=datetime.now(UTC),
        )
        database.add_all([identity, supplier, location, place])
        database.commit()
        return {
            "identity": str(identity.id),
            "supplier": str(supplier.id),
            "location": str(location.id),
            "place": str(place.id),
        }


def test_minimal_full_duplicate_historical_references_summaries_and_live_renames(
    authenticated_browser: tuple[str, str],
    references: dict[str, str],
    database_connection: Connection,
) -> None:
    minimal_status, headers, minimal = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/seed-lots",
        {"botanical_identity_id": references["identity"]},
    )
    assert minimal_status == 201
    assert UUID(minimal["id"]).version == 7
    assert headers["location"] == f"/api/v1/seed-lots/{minimal['id']}"
    assert minimal["source_kind"] == "unknown"
    assert minimal["lifecycle"] == "active"
    assert minimal["quantity"] is None

    payload = {
        "botanical_identity_id": references["identity"],
        "label": "  Historic   packet ",
        "source_kind": "other",
        "source_detail": "  estate   archive ",
        "supplier_id": references["supplier"],
        "material_provenance_place_id": references["place"],
        "acquisition_date": {"precision": "year", "year": 1998},
        "harvest_date": {"precision": "month", "year": 1997, "month": 10},
        "quantity": {"kind": "seed_count", "value": "0", "is_approximate": False},
        "expected_viability_until": {
            "precision": "day",
            "year": 2001,
            "month": 5,
            "day": 2,
        },
        "location_id": references["location"],
        "lifecycle": "exhausted",
        "notes": " Archived.\r\n Keep record. ",
    }
    full_status, _, full = mutate(authenticated_browser, "POST", "/api/v1/seed-lots", payload)
    assert full_status == 201
    assert full["label"] == "Historic packet"
    assert full["source_detail"] == "estate archive"
    assert full["notes"] == "Archived.\n Keep record."
    assert full["quantity"]["value"] == "0"
    assert full["botanical_identity"]["display_label"] == "Phoenix dactylifera \u2018Medjool\u2019"
    assert full["supplier"] == {"id": references["supplier"], "name": "Heritage Seeds"}
    assert full["material_provenance"]["display_path"].endswith("Historic oasis")
    assert full["location"]["display_path"] == "Archive drawer"

    duplicate_status, _, duplicate = mutate(
        authenticated_browser, "POST", "/api/v1/seed-lots", payload
    )
    assert duplicate_status == 201
    assert duplicate["id"] != full["id"]

    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        identity = database.get(BotanicalIdentity, UUID(references["identity"]))
        supplier = database.get(Supplier, UUID(references["supplier"]))
        location = database.get(Location, UUID(references["location"]))
        place = database.get(GeographicPlace, UUID(references["place"]))
        assert identity is not None
        assert supplier is not None
        assert location is not None
        assert place is not None
        identity.scientific_name = "Phoenix canariensis"
        identity.cultivar_name = None
        supplier.name = "Renamed supplier"
        location.name = "Renamed drawer"
        place.name = "Renamed oasis"
        database.commit()

    cookie, _ = authenticated_browser
    get_status, _, renamed = request(
        "GET", f"/api/v1/seed-lots/{full['id']}", headers={"cookie": cookie}
    )
    assert get_status == 200
    assert renamed["botanical_identity"]["display_label"] == "Phoenix canariensis"
    assert renamed["supplier"]["name"] == "Renamed supplier"
    assert renamed["location"]["display_path"] == "Renamed drawer"
    assert renamed["material_provenance"]["display_path"].endswith("Renamed oasis")


@pytest.mark.parametrize(
    "source_kind",
    [
        "purchased",
        "purchased_fruit",
        "self_collected",
        "collection_produced",
        "gift_exchange",
        "other",
        "unknown",
    ],
)
def test_every_source_kind(
    authenticated_browser: tuple[str, str], references: dict[str, str], source_kind: str
) -> None:
    payload: dict[str, object] = {
        "botanical_identity_id": references["identity"],
        "source_kind": source_kind,
    }
    if source_kind == "other":
        payload["source_detail"] = " exchange "
    status_code, _, body = mutate(authenticated_browser, "POST", "/api/v1/seed-lots", payload)
    assert status_code == 201
    assert body["source_kind"] == source_kind


@pytest.mark.parametrize("field", ["acquisition_date", "harvest_date", "expected_viability_until"])
@pytest.mark.parametrize(
    "partial_date",
    [
        {"precision": "year", "year": 2024},
        {"precision": "month", "year": 2024, "month": 5},
        {"precision": "day", "year": 2024, "month": 5, "day": 18},
    ],
)
def test_every_partial_date_precision(
    authenticated_browser: tuple[str, str],
    references: dict[str, str],
    field: str,
    partial_date: dict[str, object],
) -> None:
    status_code, _, body = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/seed-lots",
        {"botanical_identity_id": references["identity"], field: partial_date},
    )
    assert status_code == 201
    assert body[field]["precision"] == partial_date["precision"]
    assert body[field]["year"] == partial_date["year"]
    assert body[field]["month"] == partial_date.get("month")
    assert body[field]["day"] == partial_date.get("day")


@pytest.mark.parametrize(
    "partial_date",
    [
        {"precision": "year", "year": 2024, "month": 1},
        {"precision": "month", "year": 2024},
        {"precision": "day", "year": 2023, "month": 2, "day": 29},
        {"precision": "day", "year": 2024, "month": 1},
    ],
)
def test_malformed_partial_dates(
    authenticated_browser: tuple[str, str],
    references: dict[str, str],
    partial_date: dict[str, object],
) -> None:
    assert (
        mutate(
            authenticated_browser,
            "POST",
            "/api/v1/seed-lots",
            {"botanical_identity_id": references["identity"], "acquisition_date": partial_date},
        )[0]
        == 422
    )


@pytest.mark.parametrize(
    ("quantity", "lifecycle", "expected"),
    [
        ({"kind": "seed_count", "value": 120, "is_approximate": False}, "active", "120"),
        ({"kind": "seed_count", "value": 100, "is_approximate": True}, "active", "100"),
        ({"kind": "weight", "value": "4.5", "unit": "g", "is_approximate": False}, "active", "4.5"),
        (
            {"kind": "weight", "value": "4500", "unit": "mg", "is_approximate": True},
            "active",
            "4500",
        ),
        ({"kind": "seed_count", "value": 0, "is_approximate": False}, "exhausted", "0"),
    ],
)
def test_valid_exact_approximate_count_weight_units_and_exhausted_zero(
    authenticated_browser: tuple[str, str],
    references: dict[str, str],
    quantity: dict[str, object],
    lifecycle: str,
    expected: str,
) -> None:
    status_code, _, body = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/seed-lots",
        {
            "botanical_identity_id": references["identity"],
            "quantity": quantity,
            "lifecycle": lifecycle,
        },
    )
    assert status_code == 201
    assert body["quantity"]["value"] == expected


def test_lifecycle_quantity_corrections_are_atomic_and_inactive_unknown_is_valid(
    authenticated_browser: tuple[str, str], references: dict[str, str]
) -> None:
    base = {"botanical_identity_id": references["identity"], "lifecycle": "lost"}
    status_code, _, lot = mutate(authenticated_browser, "POST", "/api/v1/seed-lots", base)
    assert status_code == 201
    assert lot["quantity"] is None

    active = {
        "botanical_identity_id": references["identity"],
        "lifecycle": "active",
        "quantity": {"kind": "seed_count", "value": 5, "is_approximate": False},
    }
    status_code, _, corrected = mutate(
        authenticated_browser, "PUT", f"/api/v1/seed-lots/{lot['id']}", active
    )
    assert status_code == 200
    assert corrected["lifecycle"] == "active"

    exhausted = {
        **active,
        "lifecycle": "exhausted",
        "quantity": {"kind": "seed_count", "value": 0, "is_approximate": False},
    }
    assert (
        mutate(authenticated_browser, "PUT", f"/api/v1/seed-lots/{lot['id']}", exhausted)[0] == 200
    )
    assert mutate(authenticated_browser, "PUT", f"/api/v1/seed-lots/{lot['id']}", active)[0] == 200

    for lifecycle in ("active", "discarded", "lost"):
        invalid = {**exhausted, "lifecycle": lifecycle}
        assert (
            mutate(authenticated_browser, "PUT", f"/api/v1/seed-lots/{lot['id']}", invalid)[0]
            == 422
        )


def test_deterministic_active_first_list_keeps_inactive_and_no_delete(
    authenticated_browser: tuple[str, str], database_connection: Connection
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        alpha = BotanicalIdentity(scientific_name="alpha plant")
        zeta = BotanicalIdentity(scientific_name="Zeta plant")
        database.add_all([alpha, zeta])
        database.commit()
        ids = (str(alpha.id), str(zeta.id))
    for identity_id, lifecycle, label in (
        (ids[1], "active", "B"),
        (ids[0], "active", "A"),
        (ids[0], "lost", "C"),
    ):
        assert (
            mutate(
                authenticated_browser,
                "POST",
                "/api/v1/seed-lots",
                {"botanical_identity_id": identity_id, "lifecycle": lifecycle, "label": label},
            )[0]
            == 201
        )
    cookie, _ = authenticated_browser
    status_code, _, first = request("GET", "/api/v1/seed-lots", headers={"cookie": cookie})
    _, _, second = request("GET", "/api/v1/seed-lots", headers={"cookie": cookie})
    assert status_code == 200
    assert first == second
    assert [(item["lifecycle"], item["botanical_identity"]["display_label"]) for item in first] == [
        ("active", "alpha plant"),
        ("active", "Zeta plant"),
        ("lost", "alpha plant"),
    ]
    assert (
        request("DELETE", f"/api/v1/seed-lots/{first[0]['id']}", headers={"cookie": cookie})[0]
        == 405
    )
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        assert database.scalar(select(func.count()).select_from(SeedLot)) == 3


@pytest.mark.parametrize(
    ("field", "code"),
    [
        ("botanical_identity_id", "botanical_identity_not_found"),
        ("supplier_id", "supplier_not_found"),
        ("material_provenance_place_id", "geographic_place_not_found"),
        ("location_id", "location_not_found"),
    ],
)
def test_missing_references(
    authenticated_browser: tuple[str, str],
    references: dict[str, str],
    field: str,
    code: str,
) -> None:
    payload = {"botanical_identity_id": references["identity"], field: str(uuid7())}
    status_code, _, body = mutate(authenticated_browser, "POST", "/api/v1/seed-lots", payload)
    assert status_code == 404
    assert body["detail"]["code"] == code


def test_validation_not_found_authentication_origin_csrf_and_owner(
    authenticated_browser: tuple[str, str],
    references: dict[str, str],
    database_connection: Connection,
) -> None:
    cookie, csrf = authenticated_browser
    missing = uuid7()
    status_code, _, body = request(
        "GET", f"/api/v1/seed-lots/{missing}", headers={"cookie": cookie}
    )
    assert status_code == 404
    assert body["detail"]["code"] == "seed_lot_not_found"
    assert request("GET", "/api/v1/seed-lots")[0] == 401

    for payload in (
        {
            "botanical_identity_id": references["identity"],
            "source_kind": "purchased",
            "source_detail": "x",
        },
        {
            "botanical_identity_id": references["identity"],
            "source_kind": "other",
            "source_detail": " \t ",
        },
        {"botanical_identity_id": references["identity"], "label": "bad\u0000label"},
        {"botanical_identity_id": references["identity"], "notes": "bad\u0000notes"},
    ):
        expected = 201 if payload.get("source_detail") == " \t " else 422
        assert mutate(authenticated_browser, "POST", "/api/v1/seed-lots", payload)[0] == expected

    payload = {"botanical_identity_id": references["identity"]}
    for headers in (
        {"origin": ORIGIN, "x-csrf-token": csrf},
        {"cookie": cookie, "origin": ORIGIN},
        {"cookie": cookie, "origin": ORIGIN, "x-csrf-token": "wrong"},
        {"cookie": cookie, "x-csrf-token": csrf},
        {"cookie": cookie, "origin": "https://evil.example", "x-csrf-token": csrf},
    ):
        assert request("POST", "/api/v1/seed-lots", body=payload, headers=headers)[0] in {401, 403}

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
        status_code, _, body = request("POST", "/api/v1/seed-lots", body=payload)
    finally:
        app.dependency_overrides.pop(require_csrf, None)
    assert status_code == 403
    assert body["detail"] == "Request forbidden"
