from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID, uuid7

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import OperationalError

from florabase.events.model import Event
from florabase.plants.model import Plant, PlantGroup
from florabase.propagation import api
from florabase.propagation.reversal import RESULTS, ResultType, evaluate, reverse
from florabase.propagation.reversal_schemas import PropagationReversalCreate
from florabase.propagation.service import PropagationConflictError, PropagationNotFoundError
from florabase.propagation.snapshots import propagation_snapshot
from florabase.reversals.model import OperationReceipt
from florabase.reversals.service import seed_quantity
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing


def projection_values(record_id: UUID, lifecycle: str) -> dict[str, Any]:
    # Projections are mocked in API coordination tests; schema validation is tested separately.
    return {"id": record_id, "lifecycle": lifecycle}


def scenario(
    kind: ResultType = "sowing",
) -> tuple[SeedLot | Sowing, Sowing | Plant | PlantGroup, OperationReceipt]:
    source: SeedLot | Sowing = (
        SeedLot(
            id=uuid7(),
            lifecycle="active",
            quantity_kind="weight",
            quantity_value=Decimal("2.50"),
            quantity_unit="mg",
            quantity_is_approximate=True,
        )
        if kind == "sowing"
        else Sowing(id=uuid7(), seed_lot_id=uuid7(), lifecycle="active", germinated_count=13)
    )
    result: Sowing | Plant | PlantGroup
    if kind == "sowing":
        result = Sowing(id=uuid7(), seed_lot_id=source.id, lifecycle="active", germinated_count=3)
    elif kind == "plant":
        result = Plant(
            id=uuid7(),
            originating_sowing_id=source.id,
            botanical_identity_id=uuid7(),
            lifecycle="active",
        )
    else:
        result = PlantGroup(
            id=uuid7(),
            originating_sowing_id=source.id,
            botanical_identity_id=uuid7(),
            lifecycle="active",
            quantity_value=7,
            quantity_is_approximate=True,
        )
    receipt = OperationReceipt(
        id=uuid7(),
        kind=RESULTS[kind][1].value,
        status="applied",
        before_lifecycle="completed" if kind != "sowing" else "active",
        after_lifecycle="active",
        **seed_quantity(source).columns("before"),
        **seed_quantity(source).columns("after"),
        **propagation_snapshot(source, result),
    )
    if kind == "sowing":
        receipt.seed_lot_id, receipt.sowing_id = source.id, result.id
        receipt.before_quantity_value = Decimal("3.75")
    else:
        receipt.sowing_id = source.id
        setattr(receipt, f"{kind}_id", result.id)
    return source, result, receipt


def database_for(
    source: SeedLot | Sowing | None,
    result: Sowing | Plant | PlantGroup | None,
    receipt: OperationReceipt | None,
    *,
    kind: ResultType = "sowing",
    later: list[OperationReceipt] | None = None,
    active: list[OperationReceipt] | None = None,
    children: list[Plant] | None = None,
    events: list[Event] | None = None,
    produced: bool = False,
    historical: bool = False,
) -> MagicMock:
    db = MagicMock()
    db.scalar.side_effect = ([source, result] if receipt else [result]) + [
        uuid7() if historical else None
    ] * 20
    queries: list[list[Any]] = [[receipt] if receipt else []]
    if receipt and source is not None:
        queries.extend([later or [], active or []])
        if kind == "sowing":
            queries.extend([children or [], []])
        else:
            queries.append([uuid7()] if produced else [])
            if kind == "plant_group":
                queries.append(children or [])
            queries.append(events or [])
    db.scalars.side_effect = queries
    return db


@pytest.mark.parametrize("kind", ["sowing", "plant", "plant_group"])
def test_safe_restores_only_captured_source_and_keeps_result(kind: ResultType) -> None:
    source, result, receipt = scenario(kind)
    result.notes = "A retained note"
    db = database_for(source, result, receipt, kind=kind)
    reversed_operation = reverse(db, kind, result.id, confirm=False)
    assert reversed_operation.result is result
    assert result.lifecycle == "reversed"
    assert result.notes == "A retained note"
    assert receipt.status == "reversed"
    assert source.lifecycle == receipt.before_lifecycle
    if isinstance(source, SeedLot):
        assert source.quantity_value == Decimal("3.75")
        assert source.quantity_unit == "mg"
        assert source.quantity_is_approximate is True
    else:
        assert source.germinated_count == 13
    if isinstance(result, Sowing):
        assert result.germinated_count == 3
    db.delete.assert_not_called()
    db.flush.assert_called_once()
    # Mutations lock their receipt before the source and result, unlike advisory reads.
    assert db.scalars.call_args_list[0].args[0]._for_update_arg is not None
    assert db.scalar.call_args_list[0].args[0]._for_update_arg is not None
    assert db.scalar.call_args_list[1].args[0]._for_update_arg is not None


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ("legacy", "legacy_receipt_missing_result_snapshot"),
        ("status", "receipt_already_reversed"),
        ("origin", "receipt_relationship_mismatch"),
        ("lifecycle", "result_lifecycle_changed"),
        ("terminal", "result_terminal_lifecycle"),
        ("quantity", "result_structural_state_changed"),
        ("source_lifecycle", "source_lifecycle_changed"),
        ("source_quantity", "source_quantity_changed"),
        ("source_location", "source_structural_state_changed"),
    ],
)
def test_snapshot_guards_are_not_confirmation_overrides(change: str, reason: str) -> None:
    source, result, receipt = scenario()
    assert isinstance(source, SeedLot)
    assert isinstance(result, Sowing)
    if change == "legacy":
        receipt.result_snapshot_version = None
    elif change == "status":
        receipt.status = "reversed"
    elif change == "origin":
        result.seed_lot_id = uuid7()
    elif change == "lifecycle":
        result.lifecycle = "completed"
    elif change == "terminal":
        result.lifecycle = "lost"
    elif change == "quantity":
        result.quantity_value = Decimal(9)
    elif change == "source_lifecycle":
        source.lifecycle = "lost"
    elif change == "source_quantity":
        source.quantity_value = Decimal("1.1")
    else:
        source.location_id = uuid7()
    checked = evaluate(database_for(source, result, receipt), "sowing", result.id)
    assert checked.eligibility.status == "blocked"
    assert reason in {item.code for item in checked.eligibility.reasons}
    db = database_for(source, result, receipt)
    with pytest.raises(PropagationConflictError):
        reverse(db, "sowing", result.id, confirm=True)
    db.flush.assert_not_called()
    assert source.quantity_value != receipt.before_quantity_value


@pytest.mark.parametrize("kind", ["plant", "plant_group"])
def test_retained_observations_require_confirmation(kind: ResultType) -> None:
    source, result, receipt = scenario(kind)
    observations = [Event(id=uuid7(), kind="flowering", notes="Keep this")]
    checked = evaluate(
        database_for(source, result, receipt, kind=kind, events=observations), kind, result.id
    )
    assert checked.eligibility.status == "confirmation_required"
    assert checked.eligibility.retained_observation_ids == [observations[0].id]
    with pytest.raises(PropagationConflictError, match="propagation_confirmation_required"):
        reverse(
            database_for(source, result, receipt, kind=kind, events=observations),
            kind,
            result.id,
            confirm=False,
        )
    reverse(
        database_for(source, result, receipt, kind=kind, events=observations),
        kind,
        result.id,
        confirm=True,
    )
    assert observations[0].notes == "Keep this"


@pytest.mark.parametrize(
    ("dependency", "reason"),
    [
        ("later", "later_source_operation"),
        ("active", "active_downstream_operation"),
        ("transfer", "transfer_exists"),
        ("produced", "produced_seed_lot_exists"),
        ("event", "incompatible_result_history"),
        ("extraction", "later_extraction_exists"),
    ],
)
def test_dependencies_block_without_cascading(dependency: str, reason: str) -> None:
    source, result, receipt = scenario("plant_group")
    downstream = OperationReceipt(
        id=uuid7(),
        kind="plant_transfer" if dependency == "transfer" else "sowing_to_plant",
        plant_id=uuid7(),
        status="applied",
    )
    options: dict[str, Any] = {}
    if dependency == "later":
        options["later"] = [downstream]
    elif dependency in {"active", "transfer"}:
        options["active"] = [downstream]
    elif dependency == "produced":
        options["produced"] = True
    elif dependency == "event":
        options["events"] = [Event(id=uuid7(), kind="repotting")]
    else:
        options["children"] = [Plant(id=uuid7(), lifecycle="active")]
    checked = evaluate(
        database_for(source, result, receipt, kind="plant_group", **options),
        "plant_group",
        result.id,
    )
    assert reason in {item.code for item in checked.eligibility.reasons}
    assert downstream.status == "applied"
    assert result.lifecycle == "active"


@pytest.mark.parametrize("historical", [False, True])
def test_historical_lineage_needs_valid_reversed_receipt(historical: bool) -> None:
    source, result, receipt = scenario()
    child = Plant(id=uuid7(), lifecycle="reversed")
    checked = evaluate(
        database_for(source, result, receipt, children=[child], historical=historical),
        "sowing",
        result.id,
    )
    assert checked.eligibility.status == ("safe" if historical else "blocked")


def test_reintegrated_history_is_retained_but_not_active_dependency() -> None:
    source, result, receipt = scenario("plant_group")
    checked = evaluate(
        database_for(
            source,
            result,
            receipt,
            kind="plant_group",
            children=[Plant(id=uuid7(), lifecycle="reintegrated")],
            events=[Event(id=uuid7(), kind="reintegration")],
            historical=True,
        ),
        "plant_group",
        result.id,
    )
    assert checked.eligibility.status == "safe"


def test_missing_receipt_source_and_result_fail_closed() -> None:
    source, result, receipt = scenario()
    assert (
        evaluate(database_for(source, result, None), "sowing", result.id)
        .eligibility.reasons[0]
        .code
        == "propagation_receipt_not_found"
    )
    assert (
        evaluate(database_for(None, result, receipt), "sowing", result.id)
        .eligibility.reasons[0]
        .code
        == "receipt_relationship_mismatch"
    )
    with pytest.raises(PropagationNotFoundError):
        evaluate(database_for(source, None, receipt), "sowing", result.id)


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (PropagationNotFoundError("sowing_not_found", "Missing"), 404),
        (PropagationConflictError("source_quantity_changed", "Changed"), 409),
    ],
)
def test_api_preserves_typed_errors(
    monkeypatch: pytest.MonkeyPatch, error: Exception, status: int
) -> None:
    monkeypatch.setattr(api, "evaluate", MagicMock(side_effect=error))
    with pytest.raises(HTTPException) as caught:
        api._evaluate(MagicMock(), "sowing", uuid7())
    assert caught.value.status_code == status
    assert isinstance(caught.value.detail, dict)


@pytest.mark.parametrize("state", ["40001", "40P01", "55P03", "08000"])
def test_concurrency_errors_do_not_hide_other_database_failures(
    monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    class DatabaseError(Exception):
        sqlstate: str

    original = DatabaseError("database error")
    original.sqlstate = state
    error = OperationalError("query", {}, original)
    monkeypatch.setattr(api, "reverse", MagicMock(side_effect=error))
    with pytest.raises(OperationalError if state == "08000" else HTTPException):
        api._evaluate(MagicMock(), "plant", uuid7(), PropagationReversalCreate())


@pytest.mark.parametrize("kind", ["sowing", "plant", "plant_group"])
def test_result_oriented_api_returns_authoritative_source_and_result(
    monkeypatch: pytest.MonkeyPatch,
    kind: ResultType,
) -> None:
    from florabase.plants.schemas import PlantGroupResponse, PlantResponse
    from florabase.seed_lots.schemas import SeedLotResponse
    from florabase.sowings.schemas import SowingResponse

    source, result, receipt = scenario(kind)
    evaluation = evaluate(database_for(source, result, receipt, kind=kind), kind, result.id)
    monkeypatch.setattr(api, "_evaluate", MagicMock(return_value=evaluation))
    source_response = SowingResponse.model_construct(**projection_values(source.id, "completed"))
    sowing_response = (
        SowingResponse.model_construct(**projection_values(result.id, "reversed"))
        if kind == "sowing"
        else source_response
    )
    monkeypatch.setattr(api, "sowing_response", MagicMock(return_value=sowing_response))
    monkeypatch.setattr(
        api,
        "seed_lot_response",
        MagicMock(
            return_value=SeedLotResponse.model_construct(**projection_values(source.id, "active"))
        ),
    )
    monkeypatch.setattr(
        api,
        "_plant_response",
        MagicMock(
            return_value=PlantResponse.model_construct(**projection_values(result.id, "reversed"))
        ),
    )
    monkeypatch.setattr(
        api,
        "_plant_group_response",
        MagicMock(
            return_value=PlantGroupResponse.model_construct(
                **projection_values(result.id, "reversed")
            )
        ),
    )
    actor = MagicMock(owner=True)
    read_endpoint = getattr(api, f"{kind}_eligibility")
    endpoint = getattr(api, f"reverse_{kind}_creation")
    assert read_endpoint(result.id, actor, MagicMock()) == evaluation.eligibility
    response = endpoint(result.id, PropagationReversalCreate(), actor, MagicMock())
    assert response.operation_receipt_id == receipt.id
    assert response.operation_status == "reversed"
    assert getattr(response, kind).id == result.id
    assert getattr(response, kind).lifecycle == "reversed"
    if kind != "sowing":
        assert response.sowing.id == source.id
    with pytest.raises(HTTPException) as caught:
        endpoint(result.id, PropagationReversalCreate(), MagicMock(owner=False), MagicMock())
    assert caught.value.status_code == 403


@pytest.mark.parametrize("kind", ["sowing", "plant", "plant_group"])
def test_ordinary_correction_cannot_assign_or_leave_reversed(kind: ResultType) -> None:
    from florabase.plants.schemas import PlantGroupUpdate, PlantUpdate
    from florabase.plants.service import PlantDomainConflictError, update_plant, update_plant_group
    from florabase.sowings.schemas import SowingUpdate
    from florabase.sowings.service import SowingDomainConflictError, update_sowing

    _, result, _ = scenario(kind)
    for current, requested in (("reversed", "active"), ("active", "reversed")):
        result.lifecycle = current
        if isinstance(result, Sowing):
            payload_sowing = SowingUpdate(seed_lot_id=result.seed_lot_id, lifecycle=requested)
            with pytest.raises(SowingDomainConflictError):
                update_sowing(MagicMock(), result, payload_sowing)
        elif isinstance(result, Plant):
            payload_plant = PlantUpdate(
                botanical_identity_id=result.botanical_identity_id,
                originating_sowing_id=result.originating_sowing_id,
                lifecycle=requested,
            )
            with pytest.raises(PlantDomainConflictError):
                update_plant(MagicMock(), result, payload_plant)
        else:
            payload_group = PlantGroupUpdate(
                botanical_identity_id=result.botanical_identity_id,
                originating_sowing_id=result.originating_sowing_id,
                lifecycle=requested,
            )
            with pytest.raises(PlantDomainConflictError):
                update_plant_group(MagicMock(), result, payload_group)


def test_reversed_source_and_producers_are_never_forward_candidates() -> None:
    from florabase.plants.service import PlantDomainConflictError, _lock_forward_sowing
    from florabase.propagation.service import _lock_sowing
    from florabase.seed_lots.schemas import SeedLotCreate
    from florabase.seed_lots.service import SeedLotReferenceNotFoundError, _lock_new_producers

    db = MagicMock()
    db.scalar.return_value = Sowing(id=uuid7(), lifecycle="reversed")
    with pytest.raises(PropagationConflictError):
        _lock_sowing(db, uuid7())
    with pytest.raises(PlantDomainConflictError):
        _lock_forward_sowing(db, uuid7())
    for model, field in ((Plant, "producer_plant_id"), (PlantGroup, "producer_plant_group_id")):
        producer = model(id=uuid7(), lifecycle="reversed")
        db.scalar.return_value = producer
        payload = SeedLotCreate.model_validate(
            {
                "botanical_identity_id": str(uuid7()),
                "source_kind": "collection_produced",
                field: str(producer.id),
            }
        )
        with pytest.raises(SeedLotReferenceNotFoundError):
            _lock_new_producers(db, payload)


def test_new_forward_payloads_reject_reversed_operation_states() -> None:
    from pydantic import ValidationError

    from florabase.plants.schemas import PlantCreate, PlantGroupCreate
    from florabase.propagation.schemas import (
        PlantFromSowingCreate,
        PlantGroupFromSowingCreate,
        SeedLotSowingTransitionCreate,
        SowingPlantGroupTransitionCreate,
        SowingPlantTransitionCreate,
    )
    from florabase.sowings.schemas import SowingCreate

    identity = str(uuid7())
    for schema in (
        PlantCreate,
        PlantGroupCreate,
        PlantFromSowingCreate,
        PlantGroupFromSowingCreate,
    ):
        with pytest.raises(ValidationError):
            schema.model_validate({"botanical_identity_id": identity, "lifecycle": "reversed"})
    with pytest.raises(ValidationError):
        SowingCreate.model_validate({"seed_lot_id": str(uuid7()), "lifecycle": "reversed"})
    with pytest.raises(ValidationError):
        SeedLotSowingTransitionCreate.model_validate(
            {"sowing": {"lifecycle": "reversed"}, "source_adjustment": {"mode": "none"}}
        )
    for transition_schema, field in (
        (SowingPlantTransitionCreate, "plant"),
        (SowingPlantGroupTransitionCreate, "plant_group"),
    ):
        with pytest.raises(ValidationError):
            transition_schema.model_validate(
                {
                    field: {"botanical_identity_id": identity},
                    "resulting_sowing_lifecycle": "reversed",
                }
            )


def test_reversed_records_reject_current_state_events() -> None:
    from florabase.events.schemas import EventCreate
    from florabase.events.service import EventDomainConflictError, _apply_creation_side_effect

    for model in (Plant, PlantGroup):
        with pytest.raises(EventDomainConflictError) as caught:
            _apply_creation_side_effect(model(lifecycle="reversed"), EventCreate(kind="death"))
        assert caught.value.code == "reversed_result_is_historical"
