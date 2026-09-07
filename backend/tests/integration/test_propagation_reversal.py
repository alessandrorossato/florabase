from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from typing import Any
from uuid import UUID, uuid7

import pytest
from sqlalchemy import Connection, Engine, delete, event, select
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.events.model import Event
from florabase.plants.model import Plant, PlantGroup
from florabase.propagation.reversal import evaluate, reverse
from florabase.propagation.schemas import SeedLotSowingTransitionCreate
from florabase.propagation.service import PropagationConflictError, create_sowing_from_seed_lot
from florabase.reversals.model import OperationReceipt
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing
from integration.test_propagation_api import (
    authenticated_browser as authenticated_browser,
)
from integration.test_propagation_api import (
    propagation_records as propagation_records,
)
from integration.test_propagation_api import (
    transition_payload,
)
from integration.test_seed_lot_api import mutate, request

pytestmark = pytest.mark.integration


def read(browser: tuple[str, str], path: str) -> Any:
    status, _, body = request("GET", path, headers={"cookie": browser[0]})
    assert status == 200, body
    return body


def start(
    browser: tuple[str, str],
    records: dict[str, str],
    lot: str = "exact",
    mode: str = "partial",
    **fields: Any,
) -> Any:
    quantity: dict[str, Any] = {"kind": "seed_count", "value": 20, "is_approximate": False}
    adjustment: dict[str, Any] = {"mode": mode}
    if lot == "approximate" and mode == "partial":
        adjustment["resulting_quantity"] = {**quantity, "value": 73, "is_approximate": True}
    if lot == "weight":
        quantity = {
            "kind": "weight",
            "value": "1.2",
            "unit": "g",
            "is_approximate": False,
        }
    code, _, body = mutate(
        browser,
        "POST",
        f"/api/v1/seed-lots/{records[lot]}/create-sowing",
        transition_payload(quantity, adjustment, **fields),
    )
    assert code == 201, body
    return body


def descendant(
    browser: tuple[str, str],
    records: dict[str, str],
    sowing: str,
    kind: str,
    lifecycle: str = "completed",
) -> Any:
    details: dict[str, Any] = {"botanical_identity_id": records["descendant_identity"]}
    if kind == "plant_group":
        details["quantity"] = {"value": 7, "is_approximate": True}
    code, _, body = mutate(
        browser,
        "POST",
        f"/api/v1/sowings/{sowing}/create-{kind.replace('_', '-')}",
        {kind: details, "resulting_sowing_lifecycle": lifecycle},
    )
    assert code == 201, body
    return body


def path(kind: str, result: str) -> str:
    collection = {"sowing": "sowings", "plant": "plants", "plant_group": "plant-groups"}[kind]
    return f"/api/v1/{collection}/{result}"


def undo(browser: tuple[str, str], kind: str, result: str, confirm: bool = False) -> Any:
    return mutate(
        browser,
        "POST",
        path(kind, result) + "/reverse-creation",
        {"confirm_retained_observations": confirm},
    )


@pytest.mark.parametrize(
    ("lot", "mode"),
    [
        ("exact", "partial"),
        ("exact_all", "use_all"),
        ("exact", "none"),
        ("approximate", "partial"),
        ("approximate_all", "use_all"),
        ("unknown", "partial"),
        ("unknown_all", "use_all"),
        ("weight", "partial"),
    ],
)
def test_seed_snapshot_round_trip_and_repeat(
    authenticated_browser: tuple[str, str], propagation_records: dict[str, str], lot: str, mode: str
) -> None:
    browser, records = authenticated_browser, propagation_records
    before = read(browser, f"/api/v1/seed-lots/{records[lot]}")
    created = start(browser, records, lot, mode)
    sowing = created["sowing"]["id"]
    assert read(browser, path("sowing", sowing) + "/creation-reversal")["status"] == "safe"
    code, _, result = undo(browser, "sowing", sowing)
    assert code == 200, result
    assert result["seed_lot"]["quantity"] == before["quantity"]
    assert result["seed_lot"]["lifecycle"] == before["lifecycle"]
    assert result["sowing"]["lifecycle"] == "reversed"
    assert result["operation_status"] == "reversed"
    assert read(browser, path("sowing", sowing))["seed_lot_id"] == records[lot]
    assert undo(browser, "sowing", sowing)[2]["detail"]["code"] == "receipt_already_reversed"
    repeated = start(browser, records, lot, mode)
    assert repeated["sowing"]["id"] != sowing
    assert read(browser, path("sowing", sowing))["lifecycle"] == "reversed"


@pytest.mark.parametrize("kind", ["plant", "plant_group"])
def test_descendant_causal_history_counts_and_repeat(
    authenticated_browser: tuple[str, str], propagation_records: dict[str, str], kind: str
) -> None:
    browser, records = authenticated_browser, propagation_records
    sowing = start(browser, records, germinated_count=12, lifecycle="completed")["sowing"]["id"]
    created = descendant(browser, records, sowing, kind, lifecycle="active")
    result_id = created[kind]["id"]
    blocked = read(browser, path("sowing", sowing) + "/creation-reversal")
    assert blocked["status"] == "blocked"
    assert "active_downstream_operation" in {r["code"] for r in blocked["reasons"]}
    assert undo(browser, "sowing", sowing)[0] == 409
    code, _, result = undo(browser, kind, result_id)
    assert code == 200, result
    assert result["sowing"]["lifecycle"] == "completed"
    assert result["sowing"]["germinated_count"] == 12
    assert result[kind]["lifecycle"] == "reversed"
    assert read(browser, path(kind, result_id))["originating_sowing_id"] == sowing
    assert read(browser, path(kind, result_id) + "/lineage")["ancestors"]
    summary = read(browser, path("sowing", sowing) + "/propagation-summary")
    assert summary["exact_descendant_count"] == 0
    assert summary["approximate_plant_group_count"] == 0
    assert summary["plants" if kind == "plant" else "plant_groups"][0]["lifecycle"] == "reversed"
    assert undo(browser, kind, result_id)[0] == 409
    repeated = descendant(browser, records, sowing, kind)[kind]["id"]
    assert repeated != result_id
    assert undo(browser, kind, repeated)[0] == 200
    assert read(browser, path("sowing", sowing) + "/creation-reversal")["status"] == "safe"
    assert undo(browser, "sowing", sowing)[0] == 200
    assert read(browser, path(kind, result_id))["lifecycle"] == "reversed"


def test_multiple_descendants_require_newest_first(
    authenticated_browser: tuple[str, str], propagation_records: dict[str, str]
) -> None:
    browser, records = authenticated_browser, propagation_records
    sowing = start(browser, records)["sowing"]["id"]
    first = descendant(browser, records, sowing, "plant", "active")["plant"]["id"]
    second = descendant(browser, records, sowing, "plant_group", "active")["plant_group"]["id"]
    assert undo(browser, "plant", first)[2]["detail"]["code"] == "later_source_operation"
    assert undo(browser, "plant_group", second)[0] == 200
    assert undo(browser, "sowing", sowing)[0] == 409
    assert undo(browser, "plant", first)[0] == 200
    assert undo(browser, "sowing", sowing)[0] == 200


@pytest.mark.parametrize(
    ("target", "field", "value", "reason"),
    [
        ("source", "quantity_value", Decimal(70), "source_quantity_changed"),
        ("source", "lifecycle", "lost", "source_lifecycle_changed"),
        ("result", "quantity_value", Decimal(19), "result_structural_state_changed"),
        ("result", "lifecycle", "completed", "result_lifecycle_changed"),
    ],
)
def test_corrections_never_overwritten(
    authenticated_browser: tuple[str, str],
    propagation_records: dict[str, str],
    database_connection: Connection,
    target: str,
    field: str,
    value: Any,
    reason: str,
) -> None:
    browser, records = authenticated_browser, propagation_records
    created = start(browser, records)
    sowing = created["sowing"]["id"]
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        record = db.get(
            SeedLot if target == "source" else Sowing,
            UUID(records["exact"] if target == "source" else sowing),
        )
        assert isinstance(record, (SeedLot, Sowing))
        setattr(record, field, value)
        db.commit()
    eligibility = read(browser, path("sowing", sowing) + "/creation-reversal")
    assert reason in {r["code"] for r in eligibility["reasons"]}
    assert undo(browser, "sowing", sowing)[0] == 409
    assert read(browser, path("sowing", sowing))["lifecycle"] != "reversed"


@pytest.mark.parametrize("kind", ["plant", "plant_group"])
def test_observations_confirm_and_metadata_preserved(
    authenticated_browser: tuple[str, str],
    propagation_records: dict[str, str],
    database_connection: Connection,
    kind: str,
) -> None:
    browser, records = authenticated_browser, propagation_records
    sowing = start(browser, records)["sowing"]["id"]
    result_id = descendant(browser, records, sowing, kind)[kind]["id"]
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        record = db.get(Plant if kind == "plant" else PlantGroup, UUID(result_id))
        assert isinstance(record, (Plant, PlantGroup))
        record.notes = "Keep my notes"
        record.label = "A corrected label"
        for event_kind in ("observation", "flowering", "fruiting"):
            db.add(Event(**{f"{kind}_id": record.id}, kind=event_kind, notes="Retain me"))
        db.commit()
    assert (
        read(browser, path(kind, result_id) + "/creation-reversal")["status"]
        == "confirmation_required"
    )
    assert (
        undo(browser, kind, result_id)[2]["detail"]["code"] == "propagation_confirmation_required"
    )
    code, _, result = undo(browser, kind, result_id, True)
    assert code == 200, result
    assert result[kind]["notes"] == "Keep my notes"
    assert len(read(browser, path(kind, result_id) + "/events")) == 3


@pytest.mark.parametrize(
    "dependency",
    [
        "transfer",
        "death",
        "produced_seed_lot",
        "cultivation",
        "identity",
        "group_quantity",
        "direct_lineage",
    ],
)
def test_dependency_blocks(
    authenticated_browser: tuple[str, str],
    propagation_records: dict[str, str],
    database_connection: Connection,
    dependency: str,
) -> None:
    browser, records = authenticated_browser, propagation_records
    sowing = start(browser, records)["sowing"]["id"]
    kind = "plant_group" if dependency == "group_quantity" else "plant"
    result_id = descendant(browser, records, sowing, kind)[kind]["id"]
    if dependency in {"transfer", "death", "cultivation"}:
        if dependency == "transfer":
            code, _, body = mutate(browser, "POST", path(kind, result_id) + "/transfer", {})
        else:
            code, _, body = mutate(
                browser,
                "POST",
                path(kind, result_id) + "/events",
                {"kind": "death" if dependency == "death" else "repotting"},
            )
        assert code == 201, body
    else:
        with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
            record = db.get(Plant if kind == "plant" else PlantGroup, UUID(result_id))
            assert isinstance(record, (Plant, PlantGroup))
            if dependency == "identity":
                record.botanical_identity_id = UUID(records["source_identity"])
            elif dependency == "group_quantity":
                assert isinstance(record, PlantGroup)
                record.quantity_value = 8
            elif dependency == "produced_seed_lot":
                db.add(
                    SeedLot(
                        botanical_identity_id=record.botanical_identity_id,
                        source_kind="collection_produced",
                        producer_plant_id=record.id,
                    )
                )
            else:
                db.add(
                    Plant(
                        botanical_identity_id=record.botanical_identity_id,
                        originating_sowing_id=UUID(sowing),
                    )
                )
            db.commit()
    checked_kind, checked_id = (
        ("sowing", sowing) if dependency == "direct_lineage" else (kind, result_id)
    )
    assert (
        read(browser, path(checked_kind, checked_id) + "/creation-reversal")["status"] == "blocked"
    )
    assert undo(browser, checked_kind, checked_id)[0] == 409


def test_extraction_reintegration_unblocks_group(
    authenticated_browser: tuple[str, str], propagation_records: dict[str, str]
) -> None:
    browser, records = authenticated_browser, propagation_records
    sowing = start(browser, records)["sowing"]["id"]
    group = descendant(browser, records, sowing, "plant_group")["plant_group"]["id"]
    code, _, extraction = mutate(browser, "POST", path("plant_group", group) + "/extract-plant", {})
    assert code == 201, extraction
    assert undo(browser, "plant_group", group)[0] == 409
    plant = extraction["plant"]["id"]
    code, _, body = mutate(browser, "POST", path("plant", plant) + "/reintegrate", {})
    assert code == 201, body
    assert undo(browser, "plant_group", group)[0] == 200
    assert read(browser, path("plant", plant))["lifecycle"] == "reintegrated"


def test_legacy_and_no_receipt_are_explicit(database_connection: Connection) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity = BotanicalIdentity(scientific_name="Legacy reversal")
        db.add(identity)
        db.flush()
        lot = SeedLot(botanical_identity_id=identity.id)
        db.add(lot)
        db.flush()
        sowing = Sowing(seed_lot_id=lot.id)
        db.add(sowing)
        db.flush()
        assert (
            evaluate(db, "sowing", sowing.id).eligibility.reasons[0].code
            == "propagation_receipt_not_found"
        )
        db.add(
            OperationReceipt(
                kind="seed_lot_to_sowing",
                seed_lot_id=lot.id,
                sowing_id=sowing.id,
                adjustment_mode="none",
                before_lifecycle="active",
                after_lifecycle="active",
            )
        )
        db.flush()
        assert (
            evaluate(db, "sowing", sowing.id).eligibility.reasons[0].code
            == "legacy_receipt_missing_result_snapshot"
        )


def test_injected_failure_rolls_back_source_result_receipt(
    database_connection: Connection, propagation_records: dict[str, str]
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        result, source = create_sowing_from_seed_lot(
            db,
            UUID(propagation_records["exact"]),
            SeedLotSowingTransitionCreate.model_validate(
                transition_payload(
                    {"kind": "seed_count", "value": 20, "is_approximate": False},
                    {"mode": "partial"},
                )
            ),
        )
        result_id, source_id = result.id, source.id
        db.commit()

        def fail(*args: Any) -> None:
            raise RuntimeError("injected reversal failure")

        event.listen(db, "after_flush", fail)
        try:
            with pytest.raises(RuntimeError, match="injected"):
                reverse(db, "sowing", result_id, confirm=False)
            db.rollback()
        finally:
            event.remove(db, "after_flush", fail)
        persisted_source = db.get(SeedLot, source_id)
        assert persisted_source is not None
        assert persisted_source.quantity_value == Decimal(100)
        persisted_result = db.get(Sowing, result_id)
        assert persisted_result is not None
        assert persisted_result.lifecycle == "active"
        receipt = db.scalar(select(OperationReceipt).where(OperationReceipt.sowing_id == result_id))
        assert receipt is not None
        assert receipt.status == "applied"


def test_concurrent_duplicate_reversal(database_engine: Engine) -> None:
    identity_id = uuid7()
    with Session(database_engine) as db:
        identity = BotanicalIdentity(id=identity_id, scientific_name=f"Reversal race {identity_id}")
        db.add(identity)
        db.flush()
        lot = SeedLot(
            botanical_identity_id=identity_id,
            quantity_kind="seed_count",
            quantity_value=Decimal(100),
            quantity_is_approximate=False,
        )
        db.add(lot)
        db.flush()
        sowing, _ = create_sowing_from_seed_lot(
            db,
            lot.id,
            SeedLotSowingTransitionCreate.model_validate(
                transition_payload(
                    {"kind": "seed_count", "value": 20, "is_approximate": False},
                    {"mode": "partial"},
                )
            ),
        )
        sowing_id, lot_id = sowing.id, lot.id
        db.commit()
    barrier = Barrier(2)

    def run(_: int) -> str:
        with Session(database_engine) as db:
            barrier.wait(timeout=10)
            try:
                reverse(db, "sowing", sowing_id, confirm=False)
                db.commit()
                return "reversed"
            except PropagationConflictError as error:
                db.rollback()
                return error.code

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            assert sorted(executor.map(run, range(2))) == ["receipt_already_reversed", "reversed"]
        with Session(database_engine) as db:
            source = db.get(SeedLot, lot_id)
            assert source is not None
            assert source.quantity_value == Decimal(100)
            result = db.get(Sowing, sowing_id)
            assert result is not None
            assert result.lifecycle == "reversed"
    finally:
        with Session(database_engine) as db:
            db.execute(delete(OperationReceipt).where(OperationReceipt.sowing_id == sowing_id))
            db.execute(delete(Sowing).where(Sowing.id == sowing_id))
            db.execute(delete(SeedLot).where(SeedLot.id == lot_id))
            db.execute(delete(BotanicalIdentity).where(BotanicalIdentity.id == identity_id))
            db.commit()


@pytest.mark.parametrize("kind", ["plant", "plant_group"])
def test_historical_forward_restrictions_and_auth(
    authenticated_browser: tuple[str, str],
    propagation_records: dict[str, str],
    kind: str,
) -> None:
    browser, records = authenticated_browser, propagation_records
    sowing = start(browser, records)["sowing"]["id"]
    created = descendant(browser, records, sowing, kind)[kind]
    result_id = created["id"]
    url = path(kind, result_id)
    assert request("GET", url + "/creation-reversal")[0] == 401
    assert (
        request("POST", url + "/reverse-creation", body={}, headers={"cookie": browser[0]})[0]
        == 403
    )
    assert (
        request(
            "POST",
            url + "/reverse-creation",
            body={},
            headers={
                "cookie": browser[0],
                "origin": "http://wrong-origin",
                "x-csrf-token": browser[1],
            },
        )[0]
        == 403
    )
    assert undo(browser, kind, result_id)[0] == 200
    assert mutate(browser, "POST", url + "/transfer", {})[0] == 409
    assert mutate(
        browser,
        "POST",
        url + "/events",
        {"kind": "movement", "destination_location_id": records["source_identity"]},
    )[0] in {404, 409}
    payload = {
        "botanical_identity_id": records["descendant_identity"],
        "originating_sowing_id": sowing,
        "lifecycle": "active",
    }
    if kind == "plant_group":
        payload["quantity"] = created["quantity"]
    assert mutate(browser, "PUT", url, payload)[0] == 409
    assert undo(browser, "sowing", sowing)[0] == 200
    assert (
        mutate(
            browser,
            "POST",
            path("sowing", sowing) + "/create-plant",
            {
                "plant": {"botanical_identity_id": records["descendant_identity"]},
                "resulting_sowing_lifecycle": "active",
            },
        )[0]
        == 409
    )
    assert (
        mutate(
            browser,
            "POST",
            "/api/v1/plants",
            {
                "botanical_identity_id": records["descendant_identity"],
                "originating_sowing_id": sowing,
            },
        )[0]
        == 409
    )
    assert (
        mutate(
            browser,
            "PUT",
            path("sowing", sowing),
            {"seed_lot_id": records["exact"], "lifecycle": "active"},
        )[0]
        == 409
    )
