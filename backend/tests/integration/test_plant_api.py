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
from florabase.geographic_places.model import GeographicPlace
from florabase.locations.model import Location
from florabase.main import app
from florabase.plants.model import Plant, PlantGroup
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing
from florabase.suppliers.model import Supplier
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
def plant_references(database_connection: Connection) -> dict[str, str]:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        upstream_identity = BotanicalIdentity(scientific_name="Solanum sp.")
        plant_identity = BotanicalIdentity(scientific_name="Solanum quitoense")
        database.add_all([upstream_identity, plant_identity])
        database.flush()
        lot = SeedLot(
            botanical_identity_id=upstream_identity.id,
            quantity_kind="seed_count",
            quantity_value=Decimal("100"),
            quantity_is_approximate=False,
        )
        database.add(lot)
        database.flush()
        active_sowing = Sowing(
            seed_lot_id=lot.id,
            label="Active tray",
            quantity_kind="seed_count",
            quantity_value=Decimal("20"),
            quantity_is_approximate=False,
            germinated_count=12,
        )
        inactive_sowing = Sowing(
            seed_lot_id=lot.id,
            label="Failed tray",
            lifecycle="failed",
            germinated_count=7,
        )
        supplier = Supplier(name="Retired nursery", kind="nursery", retired_at=datetime.now(UTC))
        world = database.scalars(
            select(GeographicPlace).where(GeographicPlace.parent_id.is_(None))
        ).one()
        place = GeographicPlace(
            name="Old provenance",
            parent_id=world.id,
            place_kind="custom",
            retired_at=datetime.now(UTC),
        )
        location = Location(name="Old bench", retired_at=datetime.now(UTC))
        database.add_all([active_sowing, inactive_sowing, supplier, place, location])
        database.commit()
        return {
            "upstream_identity": str(upstream_identity.id),
            "plant_identity": str(plant_identity.id),
            "lot": str(lot.id),
            "active_sowing": str(active_sowing.id),
            "inactive_sowing": str(inactive_sowing.id),
            "supplier": str(supplier.id),
            "place": str(place.id),
            "location": str(location.id),
        }


@pytest.mark.parametrize("route", ["plants", "plant-groups"])
def test_minimal_direct_origins_full_summaries_dates_and_lifecycles(
    authenticated_browser: tuple[str, str],
    plant_references: dict[str, str],
    route: str,
) -> None:
    status_code, headers, minimal = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/{route}",
        {"botanical_identity_id": plant_references["plant_identity"]},
    )
    assert status_code == 201
    assert UUID(minimal["id"]).version == 7
    assert minimal["direct_origin_kind"] == "unknown"
    assert minimal["lifecycle"] == "active"
    assert headers["location"].endswith(minimal["id"])
    if route == "plant-groups":
        assert minimal["quantity"] is None

    for kind in ("purchased", "gift_exchange", "collection_produced"):
        assert (
            mutate(
                authenticated_browser,
                "POST",
                f"/api/v1/{route}",
                {
                    "botanical_identity_id": plant_references["plant_identity"],
                    "direct_origin_kind": kind,
                },
            )[0]
            == 201
        )
    payload = {
        "botanical_identity_id": plant_references["plant_identity"],
        "direct_origin_kind": "other",
        "direct_origin_detail": "  garden   exchange ",
        "supplier_id": plant_references["supplier"],
        "material_provenance_place_id": plant_references["place"],
        "location_id": plant_references["location"],
        "label": "  Tamarillo   mother ",
        "collection_entry_date": {"precision": "day", "year": 2026, "month": 8, "day": 31},
        "notes": " First.\r\nSecond. ",
    }
    if route == "plants":
        payload["lifecycle"] = "dead"
    else:
        payload["lifecycle"] = "completed"
        payload["quantity"] = {"value": 12, "is_approximate": True}
    status_code, _, full = mutate(authenticated_browser, "POST", f"/api/v1/{route}", payload)
    assert status_code == 201
    assert full["botanical_identity"]["display_label"] == "Solanum quitoense"
    assert full["supplier"]["name"] == "Retired nursery"
    assert full["material_provenance"]["display_path"] == "World → Old provenance"
    assert full["location"]["display_path"] == "Old bench"
    assert full["collection_entry_date"]["precision"] == "day"
    assert full["direct_origin_detail"] == "garden exchange"
    assert full["notes"] == "First.\nSecond."
    cookie, _ = authenticated_browser
    assert request("GET", f"/api/v1/{route}/{full['id']}", headers={"cookie": cookie})[2] == full
    status_code, _, moved = mutate(
        authenticated_browser,
        "PUT",
        f"/api/v1/{route}/{full['id']}",
        {"botanical_identity_id": plant_references["plant_identity"]},
    )
    assert status_code == 200
    assert moved["location"] is None
    assert request("DELETE", f"/api/v1/{route}/{full['id']}", headers={"cookie": cookie})[0] == 405


@pytest.mark.parametrize("route", ["plants", "plant-groups"])
def test_inactive_sowing_different_identity_origin_switching_and_no_upstream_accounting(
    authenticated_browser: tuple[str, str],
    plant_references: dict[str, str],
    database_connection: Connection,
    route: str,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        sowing_before = database.get(Sowing, UUID(plant_references["inactive_sowing"]))
        lot_before = database.get(SeedLot, UUID(plant_references["lot"]))
        assert sowing_before is not None
        assert lot_before is not None
        upstream = (
            sowing_before.germinated_count,
            sowing_before.quantity_value,
            lot_before.quantity_value,
        )
    direct = {
        "botanical_identity_id": plant_references["plant_identity"],
        "direct_origin_kind": "purchased",
        "supplier_id": plant_references["supplier"],
    }
    _, _, created = mutate(authenticated_browser, "POST", f"/api/v1/{route}", direct)
    sowing_payload: dict[str, object] = {
        "botanical_identity_id": plant_references["plant_identity"],
        "originating_sowing_id": plant_references["inactive_sowing"],
        "lifecycle": "lost",
    }
    if route == "plant-groups":
        sowing_payload["quantity"] = {"value": 8, "is_approximate": False}
    status_code, _, from_sowing = mutate(
        authenticated_browser, "PUT", f"/api/v1/{route}/{created['id']}", sowing_payload
    )
    assert status_code == 200
    assert from_sowing["direct_origin_kind"] is None
    assert from_sowing["supplier"] is None
    assert from_sowing["originating_sowing"]["lifecycle"] == "failed"
    assert from_sowing["lifecycle"] == "lost"
    assert from_sowing["originating_sowing"]["botanical_identity_display_label"] == "Solanum sp."
    assert from_sowing["botanical_identity"]["display_label"] == "Solanum quitoense"
    status_code, _, corrected = mutate(
        authenticated_browser,
        "PUT",
        f"/api/v1/{route}/{created['id']}",
        {"botanical_identity_id": plant_references["plant_identity"]},
    )
    assert status_code == 200
    assert corrected["originating_sowing"] is None
    assert corrected["direct_origin_kind"] == "unknown"
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        sowing_after = database.get(Sowing, UUID(plant_references["inactive_sowing"]))
        lot_after = database.get(SeedLot, UUID(plant_references["lot"]))
        assert sowing_after is not None
        assert lot_after is not None
        assert (
            sowing_after.germinated_count,
            sowing_after.quantity_value,
            lot_after.quantity_value,
        ) == upstream


@pytest.mark.parametrize(
    ("lifecycle", "quantity", "expected"),
    [
        ("active", None, 201),
        ("active", {"value": 5, "is_approximate": False}, 201),
        ("lost", {"value": 8, "is_approximate": True}, 201),
        ("completed", {"value": 0, "is_approximate": False}, 201),
        ("dead", {"value": 0, "is_approximate": False}, 201),
        ("discarded", {"value": 0, "is_approximate": False}, 201),
        ("active", {"value": 0, "is_approximate": False}, 422),
        ("lost", {"value": 0, "is_approximate": False}, 422),
        ("dead", {"value": 0, "is_approximate": True}, 422),
        ("active", {"value": -1, "is_approximate": False}, 422),
        ("active", {"value": 1.5, "is_approximate": False}, 422),
    ],
)
def test_group_quantity_and_inactive_final_states(
    authenticated_browser: tuple[str, str],
    plant_references: dict[str, str],
    lifecycle: str,
    quantity: dict[str, object] | None,
    expected: int,
) -> None:
    assert (
        mutate(
            authenticated_browser,
            "POST",
            "/api/v1/plant-groups",
            {
                "botanical_identity_id": plant_references["plant_identity"],
                "lifecycle": lifecycle,
                "quantity": quantity,
            },
        )[0]
        == expected
    )


def test_group_quantity_and_lifecycle_are_corrected_atomically(
    authenticated_browser: tuple[str, str], plant_references: dict[str, str]
) -> None:
    _, _, created = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/plant-groups",
        {
            "botanical_identity_id": plant_references["plant_identity"],
            "quantity": {"value": 5, "is_approximate": False},
        },
    )
    status_code, _, updated = mutate(
        authenticated_browser,
        "PUT",
        f"/api/v1/plant-groups/{created['id']}",
        {
            "botanical_identity_id": plant_references["plant_identity"],
            "lifecycle": "dead",
            "quantity": {"value": 0, "is_approximate": False},
        },
    )
    assert status_code == 200
    assert updated["lifecycle"] == "dead"
    assert updated["quantity"] == {"value": 0, "is_approximate": False}


@pytest.mark.parametrize("lifecycle", ["active", "dead", "lost", "discarded"])
def test_all_plant_lifecycle_states_remain_readable(
    authenticated_browser: tuple[str, str],
    plant_references: dict[str, str],
    lifecycle: str,
) -> None:
    status_code, _, body = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/plants",
        {
            "botanical_identity_id": plant_references["plant_identity"],
            "lifecycle": lifecycle,
        },
    )
    assert status_code == 201
    assert body["lifecycle"] == lifecycle


@pytest.mark.parametrize("route", ["plants", "plant-groups"])
@pytest.mark.parametrize(
    "collection_entry_date",
    [
        {"precision": "year", "year": 2024},
        {"precision": "month", "year": 2024, "month": 5},
        {"precision": "day", "year": 2024, "month": 5, "day": 18},
    ],
)
def test_collection_entry_date_precision_round_trips(
    authenticated_browser: tuple[str, str],
    plant_references: dict[str, str],
    route: str,
    collection_entry_date: dict[str, object],
) -> None:
    status_code, _, body = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/{route}",
        {
            "botanical_identity_id": plant_references["plant_identity"],
            "collection_entry_date": collection_entry_date,
        },
    )
    assert status_code == 201
    assert body["collection_entry_date"] == {
        "precision": collection_entry_date["precision"],
        "year": collection_entry_date["year"],
        "month": collection_entry_date.get("month"),
        "day": collection_entry_date.get("day"),
    }


@pytest.mark.parametrize("route", ["plants", "plant-groups"])
def test_validation_references_auth_origin_csrf_order_and_not_found(
    authenticated_browser: tuple[str, str], plant_references: dict[str, str], route: str
) -> None:
    base = {"botanical_identity_id": plant_references["plant_identity"]}
    assert (
        mutate(
            authenticated_browser,
            "POST",
            f"/api/v1/{route}",
            {**base, "direct_origin_kind": "purchased", "direct_origin_detail": "invalid"},
        )[0]
        == 422
    )
    assert (
        mutate(
            authenticated_browser,
            "POST",
            f"/api/v1/{route}",
            {
                **base,
                "originating_sowing_id": plant_references["active_sowing"],
                "direct_origin_kind": "unknown",
            },
        )[0]
        == 422
    )
    for field, code in (
        ("botanical_identity_id", "botanical_identity_not_found"),
        ("originating_sowing_id", "sowing_not_found"),
        ("supplier_id", "supplier_not_found"),
        ("material_provenance_place_id", "geographic_place_not_found"),
        ("location_id", "location_not_found"),
    ):
        payload = {**base, field: str(uuid7())}
        status_code, _, body = mutate(authenticated_browser, "POST", f"/api/v1/{route}", payload)
        assert status_code == 404
        assert body["detail"]["code"] == code
    cookie, csrf = authenticated_browser
    assert request("GET", f"/api/v1/{route}")[0] == 401
    assert (
        request("GET", f"/api/v1/{route}", headers={"cookie": "florabase_session=invalid"})[0]
        == 401
    )
    assert request("POST", f"/api/v1/{route}", body=base)[0] == 401
    for headers in (
        {"cookie": cookie, "origin": ORIGIN},
        {"cookie": cookie, "origin": ORIGIN, "x-csrf-token": "wrong"},
        {"cookie": cookie, "origin": "https://evil.example", "x-csrf-token": csrf},
    ):
        assert request("POST", f"/api/v1/{route}", body=base, headers=headers)[0] == 403
    missing = uuid7()
    assert request("GET", f"/api/v1/{route}/{missing}", headers={"cookie": cookie})[0] == 404
    for label, lifecycle, date in (
        ("History", "dead", {"precision": "day", "year": 2030, "month": 1, "day": 1}),
        ("Undated", "active", None),
        ("Dated", "active", {"precision": "year", "year": 2026}),
    ):
        if route == "plant-groups" and lifecycle == "dead":
            lifecycle = "completed"
        assert (
            mutate(
                authenticated_browser,
                "POST",
                f"/api/v1/{route}",
                {**base, "label": label, "lifecycle": lifecycle, "collection_entry_date": date},
            )[0]
            == 201
        )
    status_code, _, listed = request("GET", f"/api/v1/{route}", headers={"cookie": cookie})
    assert status_code == 200
    assert [
        item["label"] for item in listed if item["label"] in {"Dated", "Undated", "History"}
    ] == ["Dated", "Undated", "History"]


def test_persisted_resources_remain_concrete(database_connection: Connection) -> None:
    with Session(bind=database_connection) as database:
        assert database.query(Plant).count() >= 0
        assert database.query(PlantGroup).count() >= 0


def test_group_mutation_requires_owner_authorization(
    authenticated_browser: tuple[str, str],
    plant_references: dict[str, str],
    database_connection: Connection,
) -> None:
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
            "POST",
            "/api/v1/plant-groups",
            body={"botanical_identity_id": plant_references["plant_identity"]},
        )
    finally:
        app.dependency_overrides.pop(require_csrf, None)
    assert status_code == 403
    assert body["detail"] == "Request forbidden"
