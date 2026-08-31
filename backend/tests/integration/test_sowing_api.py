from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid7

import pytest
from sqlalchemy import Connection, select
from sqlalchemy.orm import Session

from florabase.auth.dependencies import AuthenticatedActor, require_csrf
from florabase.auth.model import AuthSession
from florabase.auth.service import bootstrap_owner
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.core.config import get_settings
from florabase.db.session import get_database_session
from florabase.locations.model import Location
from florabase.main import app
from florabase.seed_lots.model import SeedLot
from integration.test_seed_lot_api import (
    ORIGIN,
    mutate,
    override_database,
    request,
    settings,
)

pytestmark = pytest.mark.integration

PASSWORD = "correct horse battery staple"


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
def references(database_connection: Connection) -> dict[str, str]:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        identity = BotanicalIdentity(scientific_name="Phoenix dactylifera")
        database.add(identity)
        database.flush()
        active = SeedLot(
            botanical_identity_id=identity.id,
            label="Active packet",
            quantity_kind="seed_count",
            quantity_value=Decimal("100"),
            quantity_is_approximate=False,
        )
        inactive = SeedLot(
            botanical_identity_id=identity.id, label="Historical packet", lifecycle="exhausted"
        )
        location = Location(name="Old bench", retired_at=datetime.now(UTC))
        database.add_all([active, inactive, location])
        database.commit()
        return {
            "active": str(active.id),
            "inactive": str(inactive.id),
            "location": str(location.id),
            "identity": str(identity.id),
        }


def test_minimal_full_detail_update_summaries_and_no_seed_lot_deduction(
    authenticated_browser: tuple[str, str],
    references: dict[str, str],
    database_connection: Connection,
) -> None:
    status_code, headers, minimal = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/sowings",
        {"seed_lot_id": references["active"]},
    )
    assert status_code == 201
    assert UUID(minimal["id"]).version == 7
    assert headers["location"] == f"/api/v1/sowings/{minimal['id']}"
    assert minimal["lifecycle"] == "active"
    assert minimal["sowing_date"] is None
    assert minimal["quantity"] is None
    payload = {
        "seed_lot_id": references["inactive"],
        "label": "  Historic   tray ",
        "sowing_date": {"precision": "month", "year": 2026, "month": 8},
        "quantity": {"kind": "seed_count", "value": 20, "is_approximate": False},
        "germinated_count": 12,
        "location_id": references["location"],
        "substrate": "  seed   mix ",
        "method_container": " covered  tray ",
        "pretreatment": " soak  overnight ",
        "temperature_min_c": "20.5",
        "temperature_max_c": 25,
        "environment": " warm  shelf ",
        "lifecycle": "failed",
        "notes": " Historic.\r\n Retained. ",
    }
    status_code, _, full = mutate(authenticated_browser, "POST", "/api/v1/sowings", payload)
    assert status_code == 201
    assert full["label"] == "Historic tray"
    assert full["seed_lot"]["label"] == "Historical packet"
    assert full["seed_lot"]["lifecycle"] == "exhausted"
    assert full["seed_lot"]["botanical_identity_display_label"] == "Phoenix dactylifera"
    assert full["location"]["display_path"] == "Old bench"
    assert full["temperature_min_c"] == "20.5"
    assert full["temperature_max_c"] == "25"
    assert full["notes"] == "Historic.\n Retained."
    cookie, _ = authenticated_browser
    assert request("GET", f"/api/v1/sowings/{full['id']}", headers={"cookie": cookie})[2] == full
    corrected = {
        **payload,
        "seed_lot_id": references["active"],
        "quantity": {"kind": "seed_count", "value": 10, "is_approximate": False},
        "germinated_count": 8,
        "lifecycle": "completed",
    }
    status_code, _, updated = mutate(
        authenticated_browser, "PUT", f"/api/v1/sowings/{full['id']}", corrected
    )
    assert status_code == 200
    assert updated["seed_lot_id"] == references["active"]
    assert updated["germinated_count"] == 8
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        lot = database.get(SeedLot, UUID(references["active"]))
        assert lot is not None
        assert lot.quantity_value == Decimal("100")


@pytest.mark.parametrize("lifecycle", ["active", "completed", "failed", "abandoned"])
def test_all_lifecycle_states_are_retained(
    authenticated_browser: tuple[str, str],
    references: dict[str, str],
    lifecycle: str,
) -> None:
    assert (
        mutate(
            authenticated_browser,
            "POST",
            "/api/v1/sowings",
            {
                "seed_lot_id": references["inactive"],
                "lifecycle": lifecycle,
                "germinated_count": 0,
            },
        )[0]
        == 201
    )


@pytest.mark.parametrize(
    "sowing_date",
    [
        {"precision": "year", "year": 2024},
        {"precision": "month", "year": 2024, "month": 5},
        {"precision": "day", "year": 2024, "month": 5, "day": 18},
    ],
)
def test_partial_date_precisions(
    authenticated_browser: tuple[str, str],
    references: dict[str, str],
    sowing_date: dict[str, object],
) -> None:
    status_code, _, body = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/sowings",
        {"seed_lot_id": references["active"], "sowing_date": sowing_date},
    )
    assert status_code == 201
    assert body["sowing_date"]["precision"] == sowing_date["precision"]
    assert body["sowing_date"]["month"] == sowing_date.get("month")
    assert body["sowing_date"]["day"] == sowing_date.get("day")


@pytest.mark.parametrize(
    ("quantity", "germinated", "expected"),
    [
        (None, 12, 201),
        ({"kind": "seed_count", "value": 20, "is_approximate": False}, 0, 201),
        ({"kind": "seed_count", "value": 20, "is_approximate": False}, 20, 201),
        ({"kind": "seed_count", "value": 20, "is_approximate": False}, 21, 422),
        ({"kind": "seed_count", "value": 20, "is_approximate": True}, 21, 201),
        ({"kind": "weight", "value": "0.5", "unit": "g", "is_approximate": False}, 37, 201),
        ({"kind": "weight", "value": 200, "unit": "mg", "is_approximate": True}, None, 201),
    ],
)
def test_quantity_and_germinated_count_rules(
    authenticated_browser: tuple[str, str],
    references: dict[str, str],
    quantity: dict[str, object] | None,
    germinated: int | None,
    expected: int,
) -> None:
    payload: dict[str, object] = {"seed_lot_id": references["active"]}
    if quantity is not None:
        payload["quantity"] = quantity
    if germinated is not None:
        payload["germinated_count"] = germinated
    assert mutate(authenticated_browser, "POST", "/api/v1/sowings", payload)[0] == expected


@pytest.mark.parametrize("lifecycle", ["active", "completed", "failed", "abandoned"])
def test_zero_quantity_is_rejected_for_every_lifecycle(
    authenticated_browser: tuple[str, str],
    references: dict[str, str],
    lifecycle: str,
) -> None:
    assert (
        mutate(
            authenticated_browser,
            "POST",
            "/api/v1/sowings",
            {
                "seed_lot_id": references["active"],
                "lifecycle": lifecycle,
                "quantity": {"kind": "seed_count", "value": 0, "is_approximate": False},
            },
        )[0]
        == 422
    )


def test_atomic_final_state_and_temperature_bounds(
    authenticated_browser: tuple[str, str],
    references: dict[str, str],
) -> None:
    initial = {
        "seed_lot_id": references["active"],
        "quantity": {"kind": "seed_count", "value": 20, "is_approximate": False},
        "germinated_count": 15,
    }
    _, _, created = mutate(authenticated_browser, "POST", "/api/v1/sowings", initial)
    valid = {
        **initial,
        "quantity": {"kind": "seed_count", "value": 10, "is_approximate": False},
        "germinated_count": 8,
        "temperature_min_c": 20,
    }
    assert mutate(authenticated_browser, "PUT", f"/api/v1/sowings/{created['id']}", valid)[0] == 200
    invalid = {**valid, "germinated_count": 15}
    assert (
        mutate(authenticated_browser, "PUT", f"/api/v1/sowings/{created['id']}", invalid)[0] == 422
    )
    approximate = {
        **invalid,
        "quantity": {"kind": "seed_count", "value": 10, "is_approximate": True},
        "temperature_min_c": None,
        "temperature_max_c": 25,
    }
    assert (
        mutate(authenticated_browser, "PUT", f"/api/v1/sowings/{created['id']}", approximate)[0]
        == 200
    )
    assert (
        mutate(
            authenticated_browser,
            "PUT",
            f"/api/v1/sowings/{created['id']}",
            {**approximate, "temperature_min_c": 26, "temperature_max_c": 25},
        )[0]
        == 422
    )


def test_deterministic_active_date_precision_label_order_and_history(
    authenticated_browser: tuple[str, str],
    references: dict[str, str],
) -> None:
    for lifecycle, date, label in (
        ("failed", {"precision": "day", "year": 2030, "month": 1, "day": 1}, "History"),
        ("active", None, "Undated"),
        ("active", {"precision": "year", "year": 2026}, "Year"),
        ("active", {"precision": "month", "year": 2026, "month": 8}, "Month"),
        ("active", {"precision": "day", "year": 2026, "month": 8, "day": 31}, "Day"),
    ):
        payload: dict[str, object] = {
            "seed_lot_id": references["active"],
            "lifecycle": lifecycle,
            "label": label,
        }
        if date is not None:
            payload["sowing_date"] = date
        assert mutate(authenticated_browser, "POST", "/api/v1/sowings", payload)[0] == 201
    cookie, _ = authenticated_browser
    status_code, _, body = request("GET", "/api/v1/sowings", headers={"cookie": cookie})
    assert status_code == 200
    assert [item["label"] for item in body] == ["Day", "Month", "Year", "Undated", "History"]
    assert (
        request("DELETE", f"/api/v1/sowings/{body[0]['id']}", headers={"cookie": cookie})[0] == 405
    )


def test_reference_not_found_validation_auth_origin_csrf_and_not_found(
    authenticated_browser: tuple[str, str],
    references: dict[str, str],
    database_connection: Connection,
) -> None:
    for field, code in (
        ("seed_lot_id", "seed_lot_not_found"),
        ("location_id", "location_not_found"),
    ):
        payload = {"seed_lot_id": references["active"], field: str(uuid7())}
        status_code, _, body = mutate(authenticated_browser, "POST", "/api/v1/sowings", payload)
        assert status_code == 404
        assert body["detail"]["code"] == code
    cookie, csrf = authenticated_browser
    assert request("GET", "/api/v1/sowings")[0] == 401
    assert request("POST", "/api/v1/sowings", body={"seed_lot_id": references["active"]})[0] == 401
    for headers in (
        {"cookie": cookie, "origin": ORIGIN},
        {"cookie": cookie, "origin": ORIGIN, "x-csrf-token": "wrong"},
        {"cookie": cookie, "origin": "https://evil.example", "x-csrf-token": csrf},
    ):
        assert (
            request(
                "POST",
                "/api/v1/sowings",
                body={"seed_lot_id": references["active"]},
                headers=headers,
            )[0]
            == 403
        )
    assert (
        mutate(
            authenticated_browser,
            "POST",
            "/api/v1/sowings",
            {"seed_lot_id": references["active"], "germinated_count": 1.5},
        )[0]
        == 422
    )
    missing = uuid7()
    status_code, _, body = request("GET", f"/api/v1/sowings/{missing}", headers={"cookie": cookie})
    assert status_code == 404
    assert body["detail"]["code"] == "sowing_not_found"

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
        status_code, _, body = request(
            "POST", "/api/v1/sowings", body={"seed_lot_id": references["active"]}
        )
    finally:
        app.dependency_overrides.pop(require_csrf, None)
    assert status_code == 403
    assert body["detail"] == "Request forbidden"
