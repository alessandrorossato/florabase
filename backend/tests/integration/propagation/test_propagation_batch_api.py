from collections.abc import Iterator
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from integration.test_seed_lot_api import (
    ORIGIN,
    mutate,
    override_database,
    request,
    settings,
)
from sqlalchemy import Connection, func, select
from sqlalchemy.orm import Session

from florabase.auth.dependencies import AuthenticatedActor, require_csrf
from florabase.auth.model import AuthSession
from florabase.auth.service import bootstrap_owner
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.core.config import get_settings
from florabase.db.session import get_database_session
from florabase.events.model import Event, EventKind
from florabase.locations.model import Location
from florabase.main import app
from florabase.plants import service as plants_service
from florabase.plants.model import Plant, PlantGroup
from florabase.propagation import service as propagation_service
from florabase.reversals.model import OperationKind, OperationReceipt
from florabase.seed_lots.model import SeedLot

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
def batch_fixtures(database_connection: Connection) -> dict[str, str]:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        identity = BotanicalIdentity(scientific_name="Hoya carnosa")
        other_identity = BotanicalIdentity(scientific_name="Hoya bella")
        plant_location = Location(name="Bench 2", supports_plants=True, supports_sowings=True)
        sowing_only_location = Location(
            name="Propagation mat", supports_plants=False, supports_sowings=True
        )
        database.add_all([identity, other_identity, plant_location, sowing_only_location])
        database.flush()
        lot = SeedLot(
            botanical_identity_id=identity.id,
            label="HOY-24-07",
            quantity_kind="seed_count",
            quantity_value=Decimal(20),
            quantity_is_approximate=False,
        )
        database.add(lot)
        database.flush()
        database.commit()
        return {
            "identity_id": str(identity.id),
            "other_identity_id": str(other_identity.id),
            "plant_location_id": str(plant_location.id),
            "sowing_only_location_id": str(sowing_only_location.id),
            "seed_lot_id": str(lot.id),
        }


def test_pot_on_12_plants_receipts_and_newest_first_full_reversal(
    authenticated_browser: tuple[str, str],
    batch_fixtures: dict[str, str],
    database_connection: Connection,
) -> None:
    cookie, _csrf = authenticated_browser
    status_code, _, created_sowing = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/seed-lots/{batch_fixtures['seed_lot_id']}/create-sowing",
        {
            "sowing": {
                "label": "HOY-24-07",
                "quantity": {"kind": "seed_count", "value": 12, "is_approximate": False},
                "germinated_count": 12,
                "location_id": batch_fixtures["plant_location_id"],
            },
            "source_adjustment": {"mode": "partial"},
        },
    )
    assert status_code == 201
    sowing = created_sowing["sowing"]
    assert created_sowing["seed_lot"]["quantity"]["value"] == "8"

    status_code, _, pot_on = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/sowings/{sowing['id']}/pot-on",
        {
            "count": 12,
            "label_pattern": "HOY-24-07-{n}",
            "botanical_identity_id": batch_fixtures["identity_id"],
            "location_id": batch_fixtures["plant_location_id"],
            "collection_entry_date": {"precision": "day", "year": 2026, "month": 11, "day": 24},
            "notes": "Pricked out full tray",
            "resulting_sowing_lifecycle": "completed",
            "expected_sowing_updated_at": sowing["updated_at"],
        },
    )
    assert status_code == 201
    assert pot_on["sowing"]["lifecycle"] == "completed"
    plants = pot_on["plants"]
    assert len(plants) == 12
    assert [plant["label"] for plant in plants] == [f"HOY-24-07-{i:02d}" for i in range(1, 13)]
    assert all(plant["originating_sowing_id"] == sowing["id"] for plant in plants)
    assert all(plant["location_id"] == batch_fixtures["plant_location_id"] for plant in plants)

    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        receipts = list(
            database.scalars(
                select(OperationReceipt)
                .where(
                    OperationReceipt.sowing_id == UUID(sowing["id"]),
                    OperationReceipt.kind == OperationKind.SOWING_TO_PLANT.value,
                )
                .order_by(OperationReceipt.id)
            )
        )
    assert len(receipts) == 12
    for receipt in receipts[:-1]:
        assert receipt.before_lifecycle == "active"
        assert receipt.after_lifecycle == "active"
    assert receipts[-1].before_lifecycle == "active"
    assert receipts[-1].after_lifecycle == "completed"
    assert [str(receipt.plant_id) for receipt in receipts] == [plant["id"] for plant in plants]

    # Reversing the oldest plant first is blocked by REVERSAL-001 newest-first ordering.
    status_code, _, blocked = request(
        "GET",
        f"/api/v1/plants/{plants[0]['id']}/creation-reversal",
        headers={"cookie": cookie},
    )
    assert status_code == 200
    assert blocked["status"] == "blocked"
    assert any(reason["code"] == "later_source_operation" for reason in blocked["reasons"])

    # Reversing all 12 plants newest-first restores the sowing on the newest, then leaves it active.
    for index, plant in enumerate(reversed(plants)):
        status_code, _, reversal = mutate(
            authenticated_browser,
            "POST",
            f"/api/v1/plants/{plant['id']}/reverse-creation",
            {"confirm_retained_observations": False},
        )
        assert status_code == 200
        assert reversal["plant"]["lifecycle"] == "reversed"
        assert reversal["sowing"]["lifecycle"] == "active"
        if index == 0:
            assert plant["label"] == "HOY-24-07-12"

    # Reversing the sowing itself restores the SeedLot to its original exact quantity 20.
    status_code, _, sowing_reversal = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/sowings/{sowing['id']}/reverse-creation",
        {"confirm_retained_observations": False},
    )
    assert status_code == 200
    assert sowing_reversal["sowing"]["lifecycle"] == "reversed"
    assert sowing_reversal["seed_lot"]["lifecycle"] == "active"
    assert sowing_reversal["seed_lot"]["quantity"]["value"] == "20"


def test_pot_on_germinated_hint_stale_inactive_reversed_limits_and_rollback(
    authenticated_browser: tuple[str, str],
    batch_fixtures: dict[str, str],
    database_connection: Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cookie, _csrf = authenticated_browser
    _, _, created = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/seed-lots/{batch_fixtures['seed_lot_id']}/create-sowing",
        {
            "sowing": {"label": "TRAY-A", "germinated_count": 3},
            "source_adjustment": {"mode": "none"},
        },
    )
    sowing = created["sowing"]

    # Limits 0, 201, and expanded label > 255 return 422.
    for invalid_body in (
        {
            "count": 0,
            "botanical_identity_id": batch_fixtures["identity_id"],
            "resulting_sowing_lifecycle": "active",
        },
        {
            "count": 201,
            "botanical_identity_id": batch_fixtures["identity_id"],
            "resulting_sowing_lifecycle": "active",
        },
        {
            "count": 2,
            "label_pattern": "a" * 253 + "{n}",
            "counter_padding": 3,
            "botanical_identity_id": batch_fixtures["identity_id"],
            "resulting_sowing_lifecycle": "active",
        },
    ):
        status_code, _, _ = mutate(
            authenticated_browser,
            "POST",
            f"/api/v1/sowings/{sowing['id']}/pot-on",
            invalid_body,
        )
        assert status_code == 422

    # Invalid location scope (sowings-only location) rejects and rolls back cleanly.
    status_code, _, scope_err = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/sowings/{sowing['id']}/pot-on",
        {
            "count": 3,
            "label_pattern": "BAD-{n}",
            "botanical_identity_id": batch_fixtures["identity_id"],
            "location_id": batch_fixtures["sowing_only_location_id"],
            "resulting_sowing_lifecycle": "completed",
            "expected_sowing_updated_at": sowing["updated_at"],
        },
    )
    assert status_code == 409
    assert scope_err["detail"]["code"] == "location_scope_not_supported"

    # Failure at plant k=3 of 5 rolls back plants 1 and 2 as well as receipts and lifecycle.
    real_create_plant = plants_service.create_plant
    call_counter = 0

    def fail_on_third(database: Session, payload: Any, **kwargs: Any) -> Plant:
        nonlocal call_counter
        call_counter += 1
        if call_counter == 3:
            raise plants_service.PlantDomainConflictError(
                "location_scope_mismatch", "Simulated failure at plant 3"
            )
        return real_create_plant(database, payload, **kwargs)

    monkeypatch.setattr(propagation_service, "create_plant", fail_on_third)
    status_code, _, mid_err = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/sowings/{sowing['id']}/pot-on",
        {
            "count": 5,
            "label_pattern": "ROLLBACK-{n}",
            "botanical_identity_id": batch_fixtures["identity_id"],
            "resulting_sowing_lifecycle": "completed",
            "expected_sowing_updated_at": sowing["updated_at"],
        },
    )
    monkeypatch.setattr(propagation_service, "create_plant", real_create_plant)
    assert status_code == 409
    assert mid_err["detail"]["code"] == "location_scope_mismatch"

    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        assert (
            database.scalar(
                select(func.count())
                .select_from(Plant)
                .where(Plant.originating_sowing_id == UUID(sowing["id"]))
            )
            == 0
        )
        assert (
            database.scalar(
                select(func.count())
                .select_from(OperationReceipt)
                .where(
                    OperationReceipt.sowing_id == UUID(sowing["id"]),
                    OperationReceipt.kind == OperationKind.SOWING_TO_PLANT.value,
                )
            )
            == 0
        )

    # Germinated count is a hint, never enforced: count=5 succeeds when germinated_count=3.
    status_code, _, ok = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/sowings/{sowing['id']}/pot-on",
        {
            "count": 5,
            "label_pattern": "HINT-{n}",
            "botanical_identity_id": batch_fixtures["identity_id"],
            "resulting_sowing_lifecycle": "active",
            "expected_sowing_updated_at": sowing["updated_at"],
        },
    )
    assert status_code == 201
    assert len(ok["plants"]) == 5

    # Stale expected_sowing_updated_at returns 409 stale_preview.
    status_code, _, stale = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/sowings/{sowing['id']}/pot-on",
        {
            "count": 1,
            "botanical_identity_id": batch_fixtures["identity_id"],
            "resulting_sowing_lifecycle": "completed",
            "expected_sowing_updated_at": sowing["updated_at"],
        },
    )
    assert status_code == 409
    assert stale["detail"]["code"] == "stale_preview"

    # Complete the sowing and confirm inactive sowing is rejected with 409 sowing_not_active.
    status_code, _, completed_sowing = mutate(
        authenticated_browser,
        "PUT",
        f"/api/v1/sowings/{sowing['id']}",
        {
            "seed_lot_id": batch_fixtures["seed_lot_id"],
            "label": "TRAY-A",
            "germinated_count": 3,
            "lifecycle": "completed",
        },
    )
    assert status_code == 200
    status_code, _, inactive_err = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/sowings/{sowing['id']}/pot-on",
        {
            "count": 1,
            "botanical_identity_id": batch_fixtures["identity_id"],
            "resulting_sowing_lifecycle": "completed",
            "expected_sowing_updated_at": completed_sowing["updated_at"],
        },
    )
    assert status_code == 409
    assert inactive_err["detail"]["code"] == "sowing_not_active"

    # Reversed sowing is rejected with 409 reversed_sowing_is_historical.
    _, _, rev_created = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/seed-lots/{batch_fixtures['seed_lot_id']}/create-sowing",
        {"sowing": {"label": "TO-REVERSE"}, "source_adjustment": {"mode": "none"}},
    )
    rev_sowing_id = rev_created["sowing"]["id"]
    assert (
        mutate(
            authenticated_browser,
            "POST",
            f"/api/v1/sowings/{rev_sowing_id}/reverse-creation",
            {"confirm_retained_observations": False},
        )[0]
        == 200
    )
    rev_sowing = request("GET", f"/api/v1/sowings/{rev_sowing_id}", headers={"cookie": cookie})[2]
    status_code, _, rev_err = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/sowings/{rev_sowing_id}/pot-on",
        {
            "count": 1,
            "botanical_identity_id": batch_fixtures["identity_id"],
            "resulting_sowing_lifecycle": "active",
            "expected_sowing_updated_at": rev_sowing["updated_at"],
        },
    )
    assert status_code == 409
    assert rev_err["detail"]["code"] == "reversed_sowing_is_historical"


def test_group_split_exact_approximate_exceeded_reintegration_and_rollback(
    authenticated_browser: tuple[str, str],
    batch_fixtures: dict[str, str],
    database_connection: Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Create an active exact PlantGroup of 20.
    status_code, _, group = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/plant-groups",
        {
            "botanical_identity_id": batch_fixtures["identity_id"],
            "label": "GRP-A",
            "location_id": batch_fixtures["plant_location_id"],
            "quantity": {"value": 20, "is_approximate": False},
        },
    )
    assert status_code == 201

    # Split 5 from exact 20 -> group becomes 15, 5 plants, 5 extraction events, 5 receipts.
    status_code, _, split = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/plant-groups/{group['id']}/extract-batch",
        {
            "count": 5,
            "label_pattern": "GRP-A-{n}",
            "counter_padding": 2,
            "collection_entry_date": {"precision": "day", "year": 2026, "month": 11, "day": 24},
            "expected_plant_group_updated_at": group["updated_at"],
        },
    )
    assert status_code == 201
    assert split["plant_group"]["quantity"] == {"value": 15, "is_approximate": False}
    assert split["plant_group"]["lifecycle"] == "active"
    assert len(split["plants"]) == 5
    assert [plant["label"] for plant in split["plants"]] == [f"GRP-A-{i:02d}" for i in range(1, 6)]
    assert all(
        plant["location_id"] == batch_fixtures["plant_location_id"] for plant in split["plants"]
    )
    assert len(split["event_ids"]) == 5

    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        events = list(
            database.scalars(
                select(Event).where(
                    Event.plant_group_id == UUID(group["id"]),
                    Event.kind == EventKind.EXTRACTION.value,
                )
            )
        )
        receipts = list(
            database.scalars(
                select(OperationReceipt)
                .where(
                    OperationReceipt.plant_group_id == UUID(group["id"]),
                    OperationReceipt.kind == OperationKind.PLANT_GROUP_EXTRACTION.value,
                )
                .order_by(OperationReceipt.created_at)
            )
        )
    assert len(events) == 5
    assert len(receipts) == 5
    assert [
        (int(r.before_quantity_value or 0), int(r.after_quantity_value or 0)) for r in receipts
    ] == [
        (20, 19),
        (19, 18),
        (18, 17),
        (17, 16),
        (16, 15),
    ]

    # Reject splitting more than exact remaining quantity (16 > 15).
    status_code, _, exceed = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/plant-groups/{group['id']}/extract-batch",
        {
            "count": 16,
            "expected_plant_group_updated_at": split["plant_group"]["updated_at"],
        },
    )
    assert status_code == 409
    assert exceed["detail"]["code"] == "plant_group_quantity_exceeded"

    # Stale expected_plant_group_updated_at returns 409 stale_preview.
    status_code, _, stale = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/plant-groups/{group['id']}/extract-batch",
        {
            "count": 1,
            "expected_plant_group_updated_at": group["updated_at"],
        },
    )
    assert status_code == 409
    assert stale["detail"]["code"] == "stale_preview"

    # Mid-batch failure at plant 3 rolls back completely (group stays 15, still 5 plants).
    real_extract = plants_service.extract_plant
    extract_calls = 0

    def fail_third_extract(database: Session, group_id: UUID, item: Any) -> Any:
        nonlocal extract_calls
        extract_calls += 1
        if extract_calls == 3:
            raise plants_service.PlantDomainConflictError(
                "location_scope_mismatch", "Simulated split failure at 3"
            )
        return real_extract(database, group_id, item)

    monkeypatch.setattr(plants_service, "extract_plant", fail_third_extract)
    status_code, _, rollback_err = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/plant-groups/{group['id']}/extract-batch",
        {
            "count": 4,
            "expected_plant_group_updated_at": split["plant_group"]["updated_at"],
        },
    )
    monkeypatch.setattr(plants_service, "extract_plant", real_extract)
    assert status_code == 409
    assert rollback_err["detail"]["code"] == "location_scope_mismatch"
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        refreshed_group = database.get(PlantGroup, UUID(group["id"]))
        assert refreshed_group is not None
        assert refreshed_group.quantity_value == 15
        assert (
            database.scalar(
                select(func.count())
                .select_from(Plant)
                .where(Plant.originating_plant_group_id == UUID(group["id"]))
            )
            == 5
        )

    # PLANT-006 reintegration newest-first returns exact quantity back to 20.
    for expected_after, plant in zip([16, 17, 18, 19, 20], reversed(split["plants"]), strict=True):
        status_code, _, reintegrated = mutate(
            authenticated_browser,
            "POST",
            f"/api/v1/plants/{plant['id']}/reintegrate",
            {"confirm_retained_observations": False},
        )
        assert status_code == 201
        assert reintegrated["plant"]["lifecycle"] == "reintegrated"
        assert reintegrated["plant_group"]["quantity"] == {
            "value": expected_after,
            "is_approximate": False,
        }

    # Splitting all exact members completes the group at exact 0;
    # reintegrating newest reactivates it.
    _, _, tiny = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/plant-groups",
        {
            "botanical_identity_id": batch_fixtures["identity_id"],
            "quantity": {"value": 2, "is_approximate": False},
        },
    )
    status_code, _, emptied = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/plant-groups/{tiny['id']}/extract-batch",
        {"count": 2, "label_pattern": "TINY-{n}"},
    )
    assert status_code == 201
    assert emptied["plant_group"]["quantity"] == {"value": 0, "is_approximate": False}
    assert emptied["plant_group"]["lifecycle"] == "completed"
    status_code, _, restored = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/plants/{emptied['plants'][-1]['id']}/reintegrate",
        {"confirm_retained_observations": False},
    )
    assert status_code == 201
    assert restored["plant_group"]["lifecycle"] == "active"
    assert restored["plant_group"]["quantity"] == {"value": 1, "is_approximate": False}

    # Approximate group allows splitting beyond the approximate number and keeps quantity unchanged.
    _, _, approx = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/plant-groups",
        {
            "botanical_identity_id": batch_fixtures["identity_id"],
            "quantity": {"value": 3, "is_approximate": True},
        },
    )
    status_code, _, approx_split = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/plant-groups/{approx['id']}/extract-batch",
        {"count": 5, "label_pattern": "APX-{n}"},
    )
    assert status_code == 201
    assert len(approx_split["plants"]) == 5
    assert approx_split["plant_group"]["quantity"] == {"value": 3, "is_approximate": True}


def test_pot_on_and_extract_batch_require_auth_csrf_and_owner(
    authenticated_browser: tuple[str, str],
    batch_fixtures: dict[str, str],
    database_connection: Connection,
) -> None:
    cookie, csrf = authenticated_browser
    _, _, created_sowing = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/seed-lots/{batch_fixtures['seed_lot_id']}/create-sowing",
        {"sowing": {"label": "SEC-SOW"}, "source_adjustment": {"mode": "none"}},
    )
    _, _, group = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/plant-groups",
        {
            "botanical_identity_id": batch_fixtures["identity_id"],
            "quantity": {"value": 4, "is_approximate": False},
        },
    )

    pot_on_path = f"/api/v1/sowings/{created_sowing['sowing']['id']}/pot-on"
    pot_on_body = {
        "count": 1,
        "botanical_identity_id": batch_fixtures["identity_id"],
        "resulting_sowing_lifecycle": "active",
    }
    extract_path = f"/api/v1/plant-groups/{group['id']}/extract-batch"
    extract_body = {"count": 1}

    for path, body in ((pot_on_path, pot_on_body), (extract_path, extract_body)):
        assert request("POST", path, body=body)[0] == 401
        for bad_headers in (
            {"cookie": cookie, "origin": ORIGIN},
            {"cookie": cookie, "origin": ORIGIN, "x-csrf-token": "wrong"},
            {"cookie": cookie, "origin": "https://evil.example", "x-csrf-token": csrf},
        ):
            assert request("POST", path, body=body, headers=bad_headers)[0] == 403

    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        auth_session = database.scalars(select(AuthSession)).one()
        non_owner = AuthenticatedActor(
            user_id=auth_session.user_id,
            login_name="viewer",
            display_name=None,
            owner=False,
            session=auth_session,
        )
    app.dependency_overrides[require_csrf] = lambda: non_owner
    try:
        for path, body in ((pot_on_path, pot_on_body), (extract_path, extract_body)):
            status_code, _, detail = request("POST", path, body=body)
            assert status_code == 403
            assert detail["detail"] == "Request forbidden"
    finally:
        app.dependency_overrides.pop(require_csrf, None)
