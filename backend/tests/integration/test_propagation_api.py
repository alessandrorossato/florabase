from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from uuid import UUID, uuid7

import pytest
from sqlalchemy import Connection, Engine, delete, func, select
from sqlalchemy.orm import Session

from florabase.auth.service import bootstrap_owner
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.core.config import get_settings
from florabase.db.session import get_database_session
from florabase.main import app
from florabase.plants.model import Plant, PlantGroup
from florabase.propagation.schemas import SeedLotSowingTransitionCreate
from florabase.propagation.service import (
    PropagationConflictError,
    create_sowing_from_seed_lot,
)
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing
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
def propagation_records(database_connection: Connection) -> dict[str, str]:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        source_identity = BotanicalIdentity(scientific_name="Propagation source")
        descendant_identity = BotanicalIdentity(scientific_name="Propagation descendant")
        database.add_all([source_identity, descendant_identity])
        database.flush()
        lots = {
            "exact": SeedLot(
                botanical_identity_id=source_identity.id,
                quantity_kind="seed_count",
                quantity_value=Decimal(120),
                quantity_is_approximate=False,
            ),
            "exact_all": SeedLot(
                botanical_identity_id=source_identity.id,
                quantity_kind="seed_count",
                quantity_value=Decimal(20),
                quantity_is_approximate=False,
            ),
            "approximate": SeedLot(
                botanical_identity_id=source_identity.id,
                quantity_kind="seed_count",
                quantity_value=Decimal(100),
                quantity_is_approximate=True,
            ),
            "approximate_all": SeedLot(
                botanical_identity_id=source_identity.id,
                quantity_kind="seed_count",
                quantity_value=Decimal(100),
                quantity_is_approximate=True,
            ),
            "unknown": SeedLot(botanical_identity_id=source_identity.id),
            "unknown_all": SeedLot(botanical_identity_id=source_identity.id),
            "weight": SeedLot(
                botanical_identity_id=source_identity.id,
                quantity_kind="weight",
                quantity_value=Decimal("5.5"),
                quantity_unit="g",
                quantity_is_approximate=False,
            ),
        }
        database.add_all(lots.values())
        database.commit()
        return {
            **{name: str(lot.id) for name, lot in lots.items()},
            "source_identity": str(source_identity.id),
            "descendant_identity": str(descendant_identity.id),
        }


def transition_payload(
    quantity: dict[str, object] | None,
    source_adjustment: dict[str, object],
    **sowing_fields: object,
) -> dict[str, object]:
    return {
        "sowing": {"quantity": quantity, **sowing_fields},
        "source_adjustment": source_adjustment,
    }


def test_seed_lot_transition_modes_precision_units_and_ordinary_creation(
    authenticated_browser: tuple[str, str],
    propagation_records: dict[str, str],
) -> None:
    exact_path = f"/api/v1/seed-lots/{propagation_records['exact']}/create-sowing"
    status_code, _, exact = mutate(
        authenticated_browser,
        "POST",
        exact_path,
        transition_payload(
            {"kind": "seed_count", "value": 20, "is_approximate": False},
            {"mode": "partial"},
        ),
    )
    assert status_code == 201
    assert exact["seed_lot"]["quantity"]["value"] == "100"
    assert exact["seed_lot"]["lifecycle"] == "active"

    status_code, _, exhausted = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/seed-lots/{propagation_records['exact_all']}/create-sowing",
        transition_payload(
            {"kind": "seed_count", "value": 20, "is_approximate": False},
            {"mode": "partial"},
        ),
    )
    assert status_code == 201
    assert exhausted["seed_lot"]["quantity"] == {
        "kind": "seed_count",
        "value": "0",
        "unit": None,
        "is_approximate": False,
    }
    assert exhausted["seed_lot"]["lifecycle"] == "exhausted"

    status_code, _, approximate = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/seed-lots/{propagation_records['approximate']}/create-sowing",
        transition_payload(
            {"kind": "seed_count", "value": 20, "is_approximate": True},
            {
                "mode": "partial",
                "resulting_quantity": {
                    "kind": "seed_count",
                    "value": 77,
                    "is_approximate": True,
                },
            },
        ),
    )
    assert status_code == 201
    assert approximate["seed_lot"]["quantity"]["value"] == "77"
    assert approximate["seed_lot"]["quantity"]["is_approximate"] is True

    for lot_name in ("approximate_all", "unknown_all"):
        status_code, _, used_all = mutate(
            authenticated_browser,
            "POST",
            f"/api/v1/seed-lots/{propagation_records[lot_name]}/create-sowing",
            transition_payload(None, {"mode": "use_all"}),
        )
        assert status_code == 201
        assert used_all["seed_lot"]["lifecycle"] == "exhausted"
        if lot_name == "approximate_all":
            assert used_all["seed_lot"]["quantity"]["is_approximate"] is True
        else:
            assert used_all["seed_lot"]["quantity"] is None

    status_code, _, unknown = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/seed-lots/{propagation_records['unknown']}/create-sowing",
        transition_payload(None, {"mode": "partial"}),
    )
    assert status_code == 201
    assert unknown["seed_lot"]["quantity"] is None
    assert unknown["seed_lot"]["lifecycle"] == "active"

    status_code, _, weight = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/seed-lots/{propagation_records['weight']}/create-sowing",
        transition_payload(
            {"kind": "weight", "value": "0.5", "unit": "g", "is_approximate": False},
            {"mode": "partial"},
        ),
    )
    assert status_code == 201
    assert weight["seed_lot"]["quantity"]["value"] == "5.0"

    ordinary_status, _, ordinary = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/sowings",
        {
            "seed_lot_id": propagation_records["exact"],
            "quantity": {"kind": "seed_count", "value": 10, "is_approximate": False},
        },
    )
    assert ordinary_status == 201
    assert ordinary["quantity"]["value"] == "10"


def test_seed_lot_transition_rejects_oversubscription_false_precision_and_rolls_back(
    authenticated_browser: tuple[str, str],
    propagation_records: dict[str, str],
    database_connection: Connection,
) -> None:
    exact_id = UUID(propagation_records["exact"])
    exact_path = f"/api/v1/seed-lots/{exact_id}/create-sowing"
    for quantity in (
        {"kind": "seed_count", "value": 121, "is_approximate": False},
        {"kind": "weight", "value": 1, "unit": "g", "is_approximate": False},
        {"kind": "seed_count", "value": 20, "is_approximate": True},
    ):
        status_code, _, body = mutate(
            authenticated_browser,
            "POST",
            exact_path,
            transition_payload(quantity, {"mode": "partial"}),
        )
        assert status_code == 409
        assert body["detail"]["code"] in {
            "seed_lot_quantity_exceeded",
            "incompatible_seed_quantities",
            "exact_source_requires_exact_usage",
        }
    missing_remainder = transition_payload(
        {"kind": "seed_count", "value": 20, "is_approximate": True},
        {"mode": "partial"},
    )
    assert (
        mutate(
            authenticated_browser,
            "POST",
            f"/api/v1/seed-lots/{propagation_records['approximate']}/create-sowing",
            missing_remainder,
        )[0]
        == 409
    )
    assert (
        mutate(
            authenticated_browser,
            "POST",
            f"/api/v1/seed-lots/{propagation_records['weight']}/create-sowing",
            transition_payload(
                {"kind": "seed_count", "value": 5, "is_approximate": False},
                {"mode": "use_all"},
            ),
        )[0]
        == 409
    )
    status_code, _, _ = mutate(
        authenticated_browser,
        "POST",
        exact_path,
        transition_payload(
            {"kind": "seed_count", "value": 20, "is_approximate": False},
            {"mode": "partial"},
            location_id=str(uuid7()),
        ),
    )
    assert status_code == 404
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        lot = database.get(SeedLot, exact_id)
        assert lot is not None
        assert lot.quantity_value == Decimal(120)
        assert (
            database.scalar(
                select(func.count()).select_from(Sowing).where(Sowing.seed_lot_id == exact_id)
            )
            == 0
        )


def test_descendant_transitions_lifecycle_summary_and_correction_boundaries(
    authenticated_browser: tuple[str, str],
    propagation_records: dict[str, str],
) -> None:
    _, _, created = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/seed-lots/{propagation_records['exact']}/create-sowing",
        transition_payload(
            {"kind": "seed_count", "value": 20, "is_approximate": False},
            {"mode": "partial"},
        ),
    )
    sowing_id = created["sowing"]["id"]
    identity_id = propagation_records["descendant_identity"]
    plant_path = f"/api/v1/sowings/{sowing_id}/create-plant"
    for lifecycle in ("active", "completed"):
        status_code, headers, result = mutate(
            authenticated_browser,
            "POST",
            plant_path,
            {
                "plant": {"botanical_identity_id": identity_id},
                "resulting_sowing_lifecycle": lifecycle,
            },
        )
        assert status_code == 201
        assert result["plant"]["originating_sowing_id"] == sowing_id
        assert result["sowing"]["lifecycle"] == lifecycle
        assert headers["location"].endswith(result["plant"]["id"])
    group_path = f"/api/v1/sowings/{sowing_id}/create-plant-group"
    exact_group_id = ""
    for lifecycle, quantity in (
        ("active", {"value": 5, "is_approximate": False}),
        ("failed", {"value": 20, "is_approximate": True}),
        ("abandoned", None),
    ):
        status_code, _, result = mutate(
            authenticated_browser,
            "POST",
            group_path,
            {
                "plant_group": {
                    "botanical_identity_id": identity_id,
                    "quantity": quantity,
                },
                "resulting_sowing_lifecycle": lifecycle,
            },
        )
        assert status_code == 201
        assert result["plant_group"]["originating_sowing_id"] == sowing_id
        assert result["sowing"]["lifecycle"] == lifecycle
        if quantity == {"value": 5, "is_approximate": False}:
            exact_group_id = result["plant_group"]["id"]

    assert (
        mutate(
            authenticated_browser,
            "POST",
            f"/api/v1/plant-groups/{exact_group_id}/extract-plant",
            {},
        )[0]
        == 201
    )

    cookie, _ = authenticated_browser
    status_code, _, summary = request(
        "GET",
        f"/api/v1/sowings/{sowing_id}/propagation-summary",
        headers={"cookie": cookie},
    )
    assert status_code == 200
    assert len(summary["plants"]) == 3
    assert len(summary["plant_groups"]) == 3
    assert summary["exact_descendant_count"] == 7
    assert summary["approximate_plant_group_count"] == 1
    assert summary["unknown_plant_group_count"] == 1
    assert summary["germinated_count"] is None

    _, _, direct_same_identity = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/plants",
        {"botanical_identity_id": identity_id},
    )
    assert direct_same_identity["originating_sowing_id"] is None
    unchanged = request(
        "GET",
        f"/api/v1/sowings/{sowing_id}/propagation-summary",
        headers={"cookie": cookie},
    )[2]
    assert unchanged["exact_descendant_count"] == 7

    corrected = {
        **created["sowing"],
        "seed_lot_id": propagation_records["exact"],
        "quantity": {"kind": "seed_count", "value": 15, "is_approximate": False},
    }
    for key in ("id", "seed_lot", "location", "created_at", "updated_at"):
        corrected.pop(key, None)
    assert mutate(authenticated_browser, "PUT", f"/api/v1/sowings/{sowing_id}", corrected)[0] == 200
    lot = request(
        "GET", f"/api/v1/seed-lots/{propagation_records['exact']}", headers={"cookie": cookie}
    )[2]
    assert lot["quantity"]["value"] == "100"
    assert (
        request("GET", f"/api/v1/sowings/{sowing_id}", headers={"cookie": cookie})[2]["lifecycle"]
        == "active"
    )


def test_transition_security_missing_records_and_atomic_descendant_failure(
    authenticated_browser: tuple[str, str],
    propagation_records: dict[str, str],
) -> None:
    missing = uuid7()
    body = transition_payload(None, {"mode": "none"})
    assert (
        mutate(authenticated_browser, "POST", f"/api/v1/seed-lots/{missing}/create-sowing", body)[0]
        == 404
    )
    cookie, csrf = authenticated_browser
    path = f"/api/v1/seed-lots/{propagation_records['unknown']}/create-sowing"
    assert request("POST", path, body=body)[0] == 401
    for headers in (
        {"cookie": cookie, "origin": ORIGIN},
        {"cookie": cookie, "origin": ORIGIN, "x-csrf-token": "wrong"},
        {"cookie": cookie, "origin": "https://evil.example", "x-csrf-token": csrf},
    ):
        assert request("POST", path, body=body, headers=headers)[0] == 403
    assert request("GET", f"/api/v1/sowings/{missing}/propagation-summary")[0] == 401
    assert (
        request(
            "GET", f"/api/v1/sowings/{missing}/propagation-summary", headers={"cookie": cookie}
        )[0]
        == 404
    )

    _, _, created = mutate(authenticated_browser, "POST", path, body)
    sowing_id = created["sowing"]["id"]
    status_code, _, invalid = mutate(
        authenticated_browser,
        "POST",
        f"/api/v1/sowings/{sowing_id}/create-plant",
        {
            "plant": {"botanical_identity_id": str(uuid7())},
            "resulting_sowing_lifecycle": "completed",
        },
    )
    assert status_code == 404
    assert invalid["detail"]["code"] == "botanical_identity_not_found"
    current = request("GET", f"/api/v1/sowings/{sowing_id}", headers={"cookie": cookie})[2]
    assert current["lifecycle"] == "active"
    summary = request(
        "GET", f"/api/v1/sowings/{sowing_id}/propagation-summary", headers={"cookie": cookie}
    )[2]
    assert summary["plants"] == []


def test_concurrent_exact_consumption_cannot_oversubscribe(database_engine: Engine) -> None:
    identity_id = uuid7()
    seed_lot_id = uuid7()
    with Session(database_engine) as database:
        database.add(
            BotanicalIdentity(id=identity_id, scientific_name=f"Concurrent {identity_id.hex}")
        )
        database.add(
            SeedLot(
                id=seed_lot_id,
                botanical_identity_id=identity_id,
                quantity_kind="seed_count",
                quantity_value=Decimal(10),
                quantity_is_approximate=False,
            )
        )
        database.commit()
    barrier = Barrier(2)
    payload = SeedLotSowingTransitionCreate.model_validate(
        transition_payload(
            {"kind": "seed_count", "value": 8, "is_approximate": False},
            {"mode": "partial"},
        )
    )

    def consume() -> str:
        with Session(database_engine) as database:
            barrier.wait()
            try:
                create_sowing_from_seed_lot(database, seed_lot_id, payload)
                database.commit()
                return "created"
            except PropagationConflictError:
                database.rollback()
                return "conflict"

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(lambda _: consume(), range(2)))
        assert sorted(outcomes) == ["conflict", "created"]
        with Session(database_engine) as database:
            lot = database.get(SeedLot, seed_lot_id)
            assert lot is not None
            assert lot.quantity_value == Decimal(2)
            assert (
                database.scalar(
                    select(func.count())
                    .select_from(Sowing)
                    .where(Sowing.seed_lot_id == seed_lot_id)
                )
                == 1
            )
    finally:
        with Session(database_engine) as database:
            database.execute(
                delete(Plant).where(
                    Plant.originating_sowing_id.in_(
                        select(Sowing.id).where(Sowing.seed_lot_id == seed_lot_id)
                    )
                )
            )
            database.execute(
                delete(PlantGroup).where(
                    PlantGroup.originating_sowing_id.in_(
                        select(Sowing.id).where(Sowing.seed_lot_id == seed_lot_id)
                    )
                )
            )
            database.execute(delete(Sowing).where(Sowing.seed_lot_id == seed_lot_id))
            database.execute(delete(SeedLot).where(SeedLot.id == seed_lot_id))
            database.execute(delete(BotanicalIdentity).where(BotanicalIdentity.id == identity_id))
            database.commit()
