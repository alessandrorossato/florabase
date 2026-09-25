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


def test_germination_api_keeps_simple_total_independent(
    authenticated_browser: tuple[str, str], references: dict[str, str]
) -> None:
    payload = {
        "seed_lot_id": references["active"],
        "sowing_date": {"precision": "day", "year": 2026, "month": 4, "day": 10},
        "quantity": {"kind": "seed_count", "value": 20, "is_approximate": False},
        "germinated_count": 12,
    }
    created = mutate(authenticated_browser, "POST", "/api/v1/sowings", payload)
    assert created[0] == 201
    sowing_id = created[2]["id"]
    base = f"/api/v1/sowings/{sowing_id}/germination-observations"
    first = mutate(
        authenticated_browser,
        "POST",
        base,
        {"observed_on": "2026-04-10", "newly_germinated_count": 0},
    )
    assert first[0] == 201
    assert first[2]["summary"]["first_germination_on"] is None
    second = mutate(
        authenticated_browser,
        "POST",
        base,
        {"observed_on": "2026-04-14", "newly_germinated_count": 10},
    )
    assert second[0] == 201
    assert second[2]["simple_germinated_count"] == 12
    assert second[2]["summary"]["observed_cumulative_count"] == 10
    assert second[2]["summary"]["t50_days"] == "4"
    observation_id = second[2]["observations"][1]["id"]
    corrected = mutate(
        authenticated_browser,
        "PUT",
        f"{base}/{observation_id}",
        {"observed_on": "2026-04-14", "newly_germinated_count": 8},
    )
    assert corrected[0] == 200
    assert corrected[2]["summary"]["t50_days"] is None
    cookie, _ = authenticated_browser
    assert (
        request("GET", f"/api/v1/sowings/{sowing_id}/germination", headers={"cookie": cookie})[0]
        == 200
    )
    deleted = mutate(authenticated_browser, "DELETE", f"{base}/{observation_id}", None)
    assert deleted[0] == 200
    assert deleted[2]["summary"]["observed_cumulative_count"] == 0
    assert (
        request("GET", f"/api/v1/sowings/{sowing_id}", headers={"cookie": cookie})[2][
            "germinated_count"
        ]
        == 12
    )


def test_germination_api_requires_authentication_owner_csrf_and_exact_origin(
    authenticated_browser: tuple[str, str], references: dict[str, str]
) -> None:
    sowing = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/sowings",
        {"seed_lot_id": references["active"]},
    )
    assert sowing[0] == 201
    url = f"/api/v1/sowings/{sowing[2]['id']}/germination"
    collection = f"/api/v1/sowings/{sowing[2]['id']}/germination-observations"
    payload = {"observed_on": "2026-04-10", "newly_germinated_count": 0}
    cookie, csrf = authenticated_browser

    assert request("GET", url)[0] == 401
    assert request("POST", collection, body=payload)[0] == 401
    assert request("GET", url, headers={"cookie": cookie})[0] == 200
    assert (
        request(
            "POST",
            collection,
            body=payload,
            headers={"cookie": cookie, "origin": ORIGIN},
        )[0]
        == 403
    )
    assert (
        request(
            "POST",
            collection,
            body=payload,
            headers={"cookie": cookie, "origin": ORIGIN, "x-csrf-token": "wrong"},
        )[0]
        == 403
    )
    assert (
        request(
            "POST",
            collection,
            body=payload,
            headers={"cookie": cookie, "origin": "https://attacker.example", "x-csrf-token": csrf},
        )[0]
        == 403
    )

    created = mutate(authenticated_browser, "POST", collection, payload)
    assert created[0] == 201


def test_germination_edits_and_sowing_corrections_preserve_observation_invariants(
    authenticated_browser: tuple[str, str], references: dict[str, str]
) -> None:
    payload = {
        "seed_lot_id": references["active"],
        "sowing_date": {"precision": "day", "year": 2026, "month": 4, "day": 10},
        "quantity": {"kind": "seed_count", "value": 10, "is_approximate": False},
        "germinated_count": 4,
    }
    created = mutate(authenticated_browser, "POST", "/api/v1/sowings", payload)
    assert created[0] == 201
    sowing_id = created[2]["id"]
    base = f"/api/v1/sowings/{sowing_id}/germination-observations"
    detail_url = f"/api/v1/sowings/{sowing_id}/germination"

    assert (
        mutate(
            authenticated_browser,
            "POST",
            base,
            {"observed_on": "2026-04-09", "newly_germinated_count": 1},
        )[0]
        == 409
    )
    zero = mutate(
        authenticated_browser,
        "POST",
        base,
        {"observed_on": "2026-04-10", "newly_germinated_count": 0},
    )
    assert zero[0] == 201
    zero_id = zero[2]["observations"][0]["id"]
    assert zero[2]["summary"]["first_germination_on"] is None
    assert zero[2]["summary"]["germination_percentage"] == "0"
    assert zero[2]["summary"]["t50_days"] is None
    assert (
        mutate(
            authenticated_browser,
            "POST",
            base,
            {"observed_on": "2026-04-10", "newly_germinated_count": 0},
        )[0]
        == 409
    )
    exact_limit = mutate(
        authenticated_browser,
        "POST",
        base,
        {"observed_on": "2026-04-14", "newly_germinated_count": 0},
    )
    assert exact_limit[0] == 201
    positive = mutate(
        authenticated_browser,
        "POST",
        base,
        {"observed_on": "2026-04-12", "newly_germinated_count": 7},
    )
    assert positive[0] == 201
    positive_id = positive[2]["observations"][1]["id"]
    assert [item["observed_on"] for item in positive[2]["observations"]] == [
        "2026-04-10",
        "2026-04-12",
        "2026-04-14",
    ]
    assert [
        point["cumulative_germinated_count"]
        for point in positive[2]["summary"]["cumulative_series"]
    ] == [0, 7, 7]
    assert positive[2]["summary"]["first_germination_on"] == "2026-04-12"
    assert positive[2]["summary"]["days_to_first_germination"] == 2
    assert positive[2]["summary"]["observed_cumulative_count"] == 7
    assert positive[2]["simple_germinated_count"] == 4

    raised = mutate(
        authenticated_browser,
        "PUT",
        f"{base}/{positive_id}",
        {"observed_on": "2026-04-12", "newly_germinated_count": 10},
    )
    assert raised[0] == 200
    assert raised[2]["summary"]["observed_cumulative_count"] == 10
    assert raised[2]["summary"]["germination_percentage"] == "100"
    assert raised[2]["summary"]["t50_days"] == "1"
    assert (
        mutate(
            authenticated_browser,
            "PUT",
            f"{base}/{positive_id}",
            {"observed_on": "2026-04-12", "newly_germinated_count": 11},
        )[0]
        == 409
    )
    assert (
        mutate(
            authenticated_browser,
            "PUT",
            f"{base}/{positive_id}",
            {"observed_on": "2026-04-10", "newly_germinated_count": 10},
        )[0]
        == 409
    )

    last_zero = mutate(
        authenticated_browser,
        "POST",
        base,
        {"observed_on": "2026-04-16", "newly_germinated_count": 0},
    )
    assert last_zero[0] == 201
    too_much = mutate(
        authenticated_browser,
        "POST",
        base,
        {"observed_on": "2026-04-17", "newly_germinated_count": 1},
    )
    assert too_much[0] == 409

    assert (
        mutate(
            authenticated_browser,
            "PUT",
            f"/api/v1/sowings/{sowing_id}",
            {**payload, "quantity": {"kind": "seed_count", "value": 9, "is_approximate": False}},
        )[0]
        == 409
    )
    valid_edit = mutate(
        authenticated_browser,
        "PUT",
        f"/api/v1/sowings/{sowing_id}",
        {**payload, "quantity": {"kind": "seed_count", "value": 10, "is_approximate": False}},
    )
    assert valid_edit[0] == 200

    for quantity in (
        {"kind": "seed_count", "value": 10, "is_approximate": True},
        {"kind": "weight", "value": "2", "unit": "g", "is_approximate": False},
        None,
    ):
        changed = mutate(
            authenticated_browser,
            "PUT",
            f"/api/v1/sowings/{sowing_id}",
            {**payload, "quantity": quantity},
        )
        assert changed[0] == 200
        detail = request("GET", detail_url, headers={"cookie": authenticated_browser[0]})[2]
        assert len(detail["observations"]) == 4
        assert detail["summary"]["germination_percentage"] is None
        assert detail["summary"]["t50_days"] is None

    later_date = mutate(
        authenticated_browser,
        "PUT",
        f"/api/v1/sowings/{sowing_id}",
        {**payload, "sowing_date": {"precision": "day", "year": 2026, "month": 4, "day": 11}},
    )
    assert later_date[0] == 409
    for sowing_date in (
        {"precision": "month", "year": 2026, "month": 4},
        None,
    ):
        changed = mutate(
            authenticated_browser,
            "PUT",
            f"/api/v1/sowings/{sowing_id}",
            {**payload, "quantity": payload["quantity"], "sowing_date": sowing_date},
        )
        assert changed[0] == 200
        detail = request("GET", detail_url, headers={"cookie": authenticated_browser[0]})[2]
        assert len(detail["observations"]) == 4
        assert detail["summary"]["days_to_first_germination"] is None

    removed_zero = mutate(authenticated_browser, "DELETE", f"{base}/{zero_id}", None)
    assert removed_zero[0] == 200
    assert removed_zero[2]["summary"]["first_germination_on"] == "2026-04-12"
    assert removed_zero[2]["simple_germinated_count"] == 4
    removed_positive = mutate(authenticated_browser, "DELETE", f"{base}/{positive_id}", None)
    assert removed_positive[0] == 200
    assert removed_positive[2]["summary"]["first_germination_on"] is None
    assert removed_positive[2]["summary"]["observed_cumulative_count"] == 0
    assert removed_positive[2]["summary"]["germination_percentage"] == "0"


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
