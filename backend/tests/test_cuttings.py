from uuid import uuid7

import pytest
from pydantic import ValidationError

from florabase.cuttings.model import PropagationAttempt, VegetativeLot, utc_now
from florabase.cuttings.schemas import (
    CuttingQuantity,
    PropagationAttemptUpdate,
    SourceAdjustment,
    VegetativeLotCreate,
    VegetativeLotUpdate,
)
from florabase.cuttings.service import apply_adjustment, attempt_response
from florabase.propagation.service import PropagationConflictError


@pytest.mark.parametrize(
    "source",
    ["unknown", "purchased", "gift_exchange", "self_collected", "other"],
)
def test_external_cuttings_sources_cannot_link_a_mother(source: str) -> None:
    values = {
        "material_type": "stem_cutting",
        "source_kind": source,
        "botanical_identity_id": uuid7(),
    }
    assert VegetativeLotCreate.model_validate(values).source_kind == source
    with pytest.raises(ValidationError, match="Only collection-produced"):
        VegetativeLotCreate.model_validate({**values, "mother_plant_id": uuid7()})


@pytest.mark.parametrize(
    "fields",
    [
        {"mother_plant_id": uuid7(), "mother_plant_group_id": uuid7()},
        {"supplier_id": uuid7()},
        {"order_id": uuid7()},
        {"material_provenance_place_id": uuid7()},
        {"provenance_site_id": uuid7()},
    ],
)
def test_collection_source_rejects_ambiguous_mother_and_external_origin(
    fields: dict[str, object],
) -> None:
    with pytest.raises(ValidationError, match="one mother and no external origin"):
        VegetativeLotCreate.model_validate(
            {
                "material_type": "leaf_cutting",
                "botanical_identity_id": uuid7(),
                "source_kind": "collection_produced",
                **fields,
            }
        )


def test_dates_and_exact_zero_are_validated() -> None:
    with pytest.raises(ValidationError, match="taken_on"):
        VegetativeLotCreate.model_validate(
            {
                "material_type": "stem_cutting",
                "botanical_identity_id": uuid7(),
                "taken_on": {"precision": "day", "year": 2026, "month": 2, "day": 30},
            }
        )
    with pytest.raises(ValidationError, match="zero remainder must be exact"):
        VegetativeLotUpdate.model_validate(
            {
                "material_type": "stem_cutting",
                "botanical_identity_id": uuid7(),
                "lifecycle": "active",
                "expected_updated_at": utc_now(),
                "quantity": {"value": 0, "is_approximate": False},
            }
        )
    with pytest.raises(ValidationError, match="End date precedes"):
        PropagationAttemptUpdate.model_validate(
            {
                "lifecycle": "failed",
                "expected_updated_at": utc_now(),
                "started_on": {"precision": "year", "year": 2026},
                "ended_on": {"precision": "year", "year": 2025},
            }
        )


@pytest.mark.parametrize(
    ("count", "approximate", "rooted", "expected"),
    [
        (None, None, 2, None),
        (5, True, 6, None),
        (5, False, None, None),
        (5, False, 0, 0),
        (5, False, 2, 40),
    ],
)
def test_rate_uses_only_exact_denominator_and_recorded_numerator(
    count: int | None,
    approximate: bool | None,
    rooted: int | None,
    expected: float | None,
) -> None:
    now = utc_now()
    attempt = PropagationAttempt(
        id=uuid7(),
        vegetative_lot_id=uuid7(),
        attempt_kind="cutting",
        lifecycle="active",
        created_at=now,
        updated_at=now,
        quantity_value=count,
        quantity_is_approximate=approximate,
        rooted_count=rooted,
    )
    assert attempt_response(attempt).rooting_rate_percent == expected


def test_partial_exact_and_use_all_unknown_adjustments() -> None:
    lot = VegetativeLot(lifecycle="active", quantity_value=3, quantity_is_approximate=False)
    partial = SourceAdjustment(mode="partial")
    with pytest.raises(PropagationConflictError, match="exceeds the available"):
        apply_adjustment(lot, CuttingQuantity(value=4, is_approximate=False), partial)
    apply_adjustment(lot, CuttingQuantity(value=1, is_approximate=False), partial)
    assert str(lot.lifecycle) == "active"
    assert lot.quantity_value == 2
    apply_adjustment(lot, CuttingQuantity(value=2, is_approximate=False), partial)
    assert lot.lifecycle == "exhausted"
    assert lot.quantity_value == 0

    unknown = VegetativeLot(lifecycle="active")
    apply_adjustment(unknown, None, partial)
    assert unknown.quantity_value is None
    apply_adjustment(unknown, None, SourceAdjustment(mode="use_all"))
    assert unknown.lifecycle == "exhausted"
    assert unknown.quantity_value is None


def test_create_start_update_observe_and_establish_cutting_records() -> None:
    from unittest.mock import MagicMock, patch

    from florabase.botanical_identities.model import BotanicalIdentity
    from florabase.cuttings import service
    from florabase.cuttings.model import CuttingRecord
    from florabase.cuttings.schemas import (
        EstablishPlant,
        EstablishPlantGroup,
        FastCreate,
        RootingObservationWrite,
    )
    from florabase.plants.model import Plant, PlantGroup
    from florabase.reversals.model import OperationReceipt

    now = utc_now()
    identity = BotanicalIdentity(id=uuid7(), scientific_name="Salvia rosmarinus")
    database = MagicMock()
    stored: dict[object, object] = {(BotanicalIdentity, identity.id): identity}

    def persist(record: CuttingRecord | OperationReceipt) -> None:
        if not record.id:
            record.id = uuid7()
        if not record.created_at:
            record.created_at = now
        if isinstance(record, CuttingRecord):
            record.updated_at = now
        if isinstance(record, VegetativeLot) and not record.lifecycle:
            record.lifecycle = "active"
        if isinstance(record, PropagationAttempt) and not record.lifecycle:
            record.lifecycle = "active"
            record.attempt_kind = "cutting"
        stored[type(record), record.id] = record

    database.get.side_effect = lambda model, key, **_: stored.get((model, key))
    database.add.side_effect = persist
    database.scalar.return_value = 0
    payload = FastCreate.model_validate(
        {
            "vegetative_lot": {
                "botanical_identity_id": identity.id,
                "material_type": "leaf_cutting",
                "initial_quantity": {"value": 5, "is_approximate": False},
                "taken_on": {"precision": "year", "year": 2026},
            },
            "source_adjustment": {"mode": "partial"},
            "propagation_attempt": {"quantity": {"value": 4, "is_approximate": False}},
        }
    )
    lot, attempt, receipt = service.fast_create(database, payload)
    remaining = service.lot_response(lot).quantity
    assert remaining is not None
    assert remaining.model_dump() == {"value": 1, "is_approximate": False}
    response = service.attempt_response(attempt)
    assert response.started_on == payload.vegetative_lot.taken_on
    assert receipt.vegetative_lot_id == lot.id
    assert receipt.propagation_attempt_id == attempt.id

    service.update_lot(
        database,
        lot.id,
        VegetativeLotUpdate.model_validate(
            {
                "botanical_identity_id": identity.id,
                "material_type": "root_cutting",
                "lifecycle": "active",
                "expected_updated_at": now,
                "quantity": None,
            }
        ),
    )
    assert lot.material_type == "root_cutting"
    assert lot.quantity_value is None

    check = service.save_observation(
        database,
        attempt.id,
        RootingObservationWrite(stage="rooted", rooted_count=3),
    )
    assert service.observation_response(check).rooted_count == 3
    service.update_attempt(
        database,
        attempt.id,
        PropagationAttemptUpdate.model_validate(
            {
                "lifecycle": "active",
                "expected_updated_at": now,
                "rooted_count": 3,
                "quantity": {"value": 4, "is_approximate": False},
            }
        ),
    )
    assert service.attempt_response(attempt).rooting_rate_percent == 75
    with pytest.raises(PropagationConflictError, match="exceeds the recorded"):
        service.establish(
            database,
            attempt.id,
            EstablishPlantGroup.model_validate(
                {
                    "quantity": {"value": 4, "is_approximate": False},
                }
            ),
        )
    child = Plant(id=uuid7(), botanical_identity_id=identity.id, lifecycle="active")
    with patch.object(service, "create_plant", return_value=child) as create:
        plant, establishment = service.establish(
            database, attempt.id, EstablishPlant(label="Clone")
        )
    assert plant is child
    assert establishment.plant_id == child.id
    assert create.call_args.kwargs["propagation_attempt_id"] == attempt.id
    group = PlantGroup(id=uuid7(), botanical_identity_id=identity.id, lifecycle="active")
    with patch.object(service, "create_plant_group", return_value=group) as create:
        result, establishment = service.establish(
            database,
            attempt.id,
            EstablishPlantGroup(resulting_attempt_lifecycle="completed"),
        )
    assert result is group
    assert establishment.plant_group_id == group.id
    assert create.call_args.kwargs["propagation_attempt_id"] == attempt.id
    assert establishment.after_lifecycle == "completed"


def test_cutting_directory_and_detail_routes_preserve_observations_and_unknown_counts() -> None:
    from unittest.mock import MagicMock

    from florabase.cuttings import api
    from florabase.cuttings.model import RootingObservation
    from florabase.plants.model import Plant, PlantGroup

    database = MagicMock()
    reader = MagicMock()
    now = utc_now()
    identity_id = uuid7()
    lot = VegetativeLot(
        id=uuid7(),
        material_type="root_cutting",
        source_kind="unknown",
        lifecycle="active",
        botanical_identity_id=identity_id,
        created_at=now,
        updated_at=now,
    )
    attempt = PropagationAttempt(
        id=uuid7(),
        vegetative_lot_id=lot.id,
        attempt_kind="cutting",
        lifecycle="active",
        created_at=now,
        updated_at=now,
    )
    observation = RootingObservation(
        id=uuid7(),
        propagation_attempt_id=attempt.id,
        stage="inspection",
        created_at=now,
        updated_at=now,
        rooted_count=0,
    )
    receipt_id = uuid7()
    records = {(VegetativeLot, lot.id): lot, (PropagationAttempt, attempt.id): attempt}
    database.get.side_effect = lambda model, key, **_: records.get((model, key))
    database.scalars.side_effect = [[lot], [attempt], [attempt], [observation]]
    database.scalar.return_value = receipt_id
    result = api.list_lots(
        reader,
        database,
        q="%literal_",
        material_type="root_cutting",
        has_known_mother=False,
    )
    assert result[0].quantity is None
    assert "NOT (" in str(database.scalars.call_args.args[0])
    assert api.list_attempts(reader, database, q="Perlite", lifecycle="active")[0].id == attempt.id
    assert api.get_lot(lot.id, reader, database).attempts[0].id == attempt.id
    detail = api.get_attempt(attempt.id, reader, database)
    assert detail.observations[0].rooted_count == 0
    assert detail.operation_receipt_id == receipt_id

    plants = [Plant(id=uuid7(), lifecycle="active"), Plant(id=uuid7(), lifecycle="reversed")]
    groups = [
        PlantGroup(id=uuid7(), lifecycle="active", quantity_value=2, quantity_is_approximate=False),
        PlantGroup(id=uuid7(), lifecycle="active", quantity_value=4, quantity_is_approximate=True),
        PlantGroup(id=uuid7(), lifecycle="active"),
    ]
    database.execute.side_effect = [
        [(plant, receipt_id) for plant in plants],
        [(group, None) for group in groups],
    ]
    database.scalar.return_value = 1  # An extracted individual from a rooted group.
    summary = api.propagation_summary(attempt.id, reader, database)
    assert len(summary.offspring) == 5
    assert summary.exact_descendant_count == 4
    assert summary.approximate_plant_group_count == 1
    assert summary.unknown_plant_group_count == 1


def test_cutting_lot_route_reports_missing_and_conflict_with_no_commit() -> None:
    from unittest.mock import MagicMock

    from fastapi import HTTPException

    from florabase.cuttings import api
    from florabase.locations.service import LocationIntegrityError, LocationNotFoundError

    database = MagicMock()
    database.get.return_value = None
    with pytest.raises(HTTPException) as missing:
        api.delete_lot(uuid7(), None, database)
    assert missing.value.status_code == 404
    with pytest.raises(HTTPException) as bad_scope, api._domain_errors():
        raise LocationIntegrityError("location_scope_not_supported", "Scope not enabled")
    assert bad_scope.value.status_code == 409
    with pytest.raises(HTTPException) as missing_location, api._domain_errors():
        raise LocationNotFoundError
    assert missing_location.value.status_code == 404
    database.commit.assert_not_called()


@pytest.mark.parametrize("mode", ["none", "partial", "use_all"])
def test_approximate_lot_requires_explicit_partial_remainder(mode: str) -> None:
    lot = VegetativeLot(lifecycle="active", quantity_value=10, quantity_is_approximate=True)
    payload = SourceAdjustment.model_validate({"mode": mode})
    used = CuttingQuantity(value=4, is_approximate=True)
    if mode == "partial":
        with pytest.raises(PropagationConflictError, match="Confirm an approximate"):
            apply_adjustment(lot, used, payload)
        payload = SourceAdjustment.model_validate(
            {
                "mode": mode,
                "resulting_quantity": {"value": 7, "is_approximate": True},
            }
        )
    apply_adjustment(lot, used, payload)
    assert lot.quantity_value == (7 if mode == "partial" else 10)
    assert lot.quantity_is_approximate is True
    assert lot.lifecycle == ("exhausted" if mode == "use_all" else "active")
