from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock
from uuid import uuid7

import pytest
from fastapi import HTTPException, Response

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.plants.model import Plant, PlantGroup
from florabase.plants.schemas import PlantGroupResponse, PlantResponse
from florabase.propagation import service
from florabase.propagation.schemas import (
    PlantFromSowingCreate,
    PlantGroupFromSowingCreate,
    SeedLotSowingTransitionCreate,
    SowingPlantGroupTransitionCreate,
    SowingPlantTransitionCreate,
)
from florabase.propagation.service import (
    PropagationConflictError,
    PropagationNotFoundError,
)
from florabase.seed_lots import api as seed_lot_api
from florabase.seed_lots.model import SeedLot
from florabase.seed_lots.schemas import SeedLotResponse
from florabase.sowings import api as sowing_api
from florabase.sowings.model import Sowing
from florabase.sowings.schemas import SowingResponse
from florabase.sowings.service import SowingProjection


def lot(
    *,
    value: Decimal | None = Decimal(100),
    approximate: bool | None = False,
    kind: str | None = "seed_count",
    unit: str | None = None,
    lifecycle: str = "active",
) -> SeedLot:
    return SeedLot(
        id=uuid7(),
        botanical_identity_id=uuid7(),
        quantity_kind=kind if value is not None else None,
        quantity_value=value,
        quantity_unit=unit,
        quantity_is_approximate=approximate if value is not None else None,
        lifecycle=lifecycle,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def sowing_transition(
    quantity: dict[str, object] | None, adjustment: dict[str, object]
) -> SeedLotSowingTransitionCreate:
    return SeedLotSowingTransitionCreate.model_validate(
        {"sowing": {"quantity": quantity}, "source_adjustment": adjustment}
    )


def database_for_lot(source: SeedLot) -> MagicMock:
    database = MagicMock()
    database.scalar.return_value = source
    database.get.side_effect = lambda model, item_id: (
        source if model is SeedLot and item_id == source.id else None
    )
    return database


def test_seed_lot_transition_exact_none_partial_zero_and_use_all() -> None:
    source = lot()
    database = database_for_lot(source)
    created, returned = service.create_sowing_from_seed_lot(
        database,
        source.id,
        sowing_transition(
            {"kind": "seed_count", "value": 20, "is_approximate": False},
            {"mode": "none"},
        ),
    )
    assert created.seed_lot_id == source.id
    assert returned.quantity_value == Decimal(100)

    service.create_sowing_from_seed_lot(
        database,
        source.id,
        sowing_transition(
            {"kind": "seed_count", "value": 20, "is_approximate": False},
            {"mode": "partial"},
        ),
    )
    assert source.quantity_value == Decimal(80)
    service.create_sowing_from_seed_lot(
        database,
        source.id,
        sowing_transition(
            {"kind": "seed_count", "value": 80, "is_approximate": False},
            {"mode": "partial"},
        ),
    )
    assert source.quantity_value == Decimal(0)
    assert source.lifecycle == "exhausted"

    weighted = lot(value=Decimal("2.5"), kind="weight", unit="g")
    database = database_for_lot(weighted)
    service.create_sowing_from_seed_lot(
        database, weighted.id, sowing_transition(None, {"mode": "use_all"})
    )
    assert weighted.quantity_value == 0
    assert weighted.quantity_unit == "g"
    assert weighted.lifecycle == "exhausted"


def test_seed_lot_transition_approximate_and_unknown_modes() -> None:
    approximate = lot(approximate=True)
    database = database_for_lot(approximate)
    service.create_sowing_from_seed_lot(
        database,
        approximate.id,
        sowing_transition(
            {"kind": "seed_count", "value": 20, "is_approximate": True},
            {
                "mode": "partial",
                "resulting_quantity": {
                    "kind": "seed_count",
                    "value": 75,
                    "is_approximate": True,
                },
            },
        ),
    )
    assert approximate.quantity_value == Decimal(75)
    assert approximate.quantity_is_approximate is True
    service.create_sowing_from_seed_lot(
        database, approximate.id, sowing_transition(None, {"mode": "use_all"})
    )
    assert approximate.quantity_value == Decimal(75)
    assert approximate.lifecycle == "exhausted"

    unknown = lot(value=None, approximate=None, kind=None)
    database = database_for_lot(unknown)
    service.create_sowing_from_seed_lot(
        database, unknown.id, sowing_transition(None, {"mode": "partial"})
    )
    assert unknown.quantity_value is None
    service.create_sowing_from_seed_lot(
        database, unknown.id, sowing_transition(None, {"mode": "use_all"})
    )
    assert unknown.quantity_value is None
    assert unknown.lifecycle == "exhausted"


@pytest.mark.parametrize(
    ("source", "quantity", "adjustment", "code"),
    [
        (
            lot(lifecycle="lost"),
            {"kind": "seed_count", "value": 1, "is_approximate": False},
            {"mode": "partial"},
            "seed_lot_not_active",
        ),
        (lot(), None, {"mode": "partial"}, "partial_usage_quantity_required"),
        (
            lot(),
            {"kind": "weight", "value": 1, "unit": "g", "is_approximate": False},
            {"mode": "partial"},
            "incompatible_seed_quantities",
        ),
        (
            lot(),
            {"kind": "seed_count", "value": 1, "is_approximate": True},
            {"mode": "partial"},
            "exact_source_requires_exact_usage",
        ),
        (
            lot(),
            {"kind": "seed_count", "value": 1, "is_approximate": False},
            {
                "mode": "partial",
                "resulting_quantity": {
                    "kind": "seed_count",
                    "value": 99,
                    "is_approximate": True,
                },
            },
            "exact_remainder_is_derived",
        ),
        (
            lot(value=Decimal(2)),
            {"kind": "seed_count", "value": 3, "is_approximate": False},
            {"mode": "partial"},
            "seed_lot_quantity_exceeded",
        ),
        (
            lot(approximate=True),
            {"kind": "seed_count", "value": 1, "is_approximate": True},
            {"mode": "partial"},
            "approximate_remainder_required",
        ),
        (
            lot(approximate=True),
            {"kind": "seed_count", "value": 1, "is_approximate": True},
            {
                "mode": "partial",
                "resulting_quantity": {
                    "kind": "weight",
                    "value": 1,
                    "unit": "g",
                    "is_approximate": True,
                },
            },
            "invalid_approximate_remainder",
        ),
        (
            lot(value=None, approximate=None, kind=None),
            None,
            {
                "mode": "partial",
                "resulting_quantity": {
                    "kind": "seed_count",
                    "value": 1,
                    "is_approximate": True,
                },
            },
            "unknown_source_numeric_remainder",
        ),
        (
            lot(),
            {"kind": "weight", "value": 100, "unit": "g", "is_approximate": False},
            {"mode": "use_all"},
            "incompatible_seed_quantities",
        ),
        (
            lot(),
            {"kind": "seed_count", "value": 99, "is_approximate": False},
            {"mode": "use_all"},
            "use_all_exact_quantity_mismatch",
        ),
    ],
)
def test_seed_lot_transition_conflicts(
    source: SeedLot,
    quantity: dict[str, object] | None,
    adjustment: dict[str, object],
    code: str,
) -> None:
    with pytest.raises(PropagationConflictError) as error:
        service.create_sowing_from_seed_lot(
            database_for_lot(source), source.id, sowing_transition(quantity, adjustment)
        )
    assert error.value.code == code


def test_missing_source_and_sowing_are_friendly() -> None:
    database = MagicMock()
    database.scalar.return_value = None
    with pytest.raises(PropagationNotFoundError) as source_error:
        service.create_sowing_from_seed_lot(
            database, uuid7(), sowing_transition(None, {"mode": "none"})
        )
    assert source_error.value.code == "seed_lot_not_found"
    with pytest.raises(PropagationNotFoundError) as sowing_error:
        service.create_plant_from_sowing(
            database,
            uuid7(),
            PlantFromSowingCreate(botanical_identity_id=uuid7()),
            "active",
        )
    assert sowing_error.value.code == "sowing_not_found"


def test_descendant_creation_and_explicit_summary() -> None:
    identity = BotanicalIdentity(id=uuid7(), scientific_name="Child")
    source = lot()
    sowing = Sowing(id=uuid7(), seed_lot_id=source.id, germinated_count=9, lifecycle="active")
    database = MagicMock()
    database.scalar.return_value = sowing
    database.get.side_effect = lambda model, item_id: (
        identity
        if model is BotanicalIdentity and item_id == identity.id
        else sowing
        if model is Sowing and item_id == sowing.id
        else None
    )
    plant, _ = service.create_plant_from_sowing(
        database,
        sowing.id,
        PlantFromSowingCreate(botanical_identity_id=identity.id, label=" One "),
        "completed",
    )
    assert plant.originating_sowing_id == sowing.id
    assert plant.label == "One"
    assert sowing.lifecycle == "completed"
    group, _ = service.create_plant_group_from_sowing(
        database,
        sowing.id,
        PlantGroupFromSowingCreate(
            botanical_identity_id=identity.id,
            quantity={"value": 5, "is_approximate": False},
        ),
        "active",
    )
    approximate_group = PlantGroup(
        id=uuid7(),
        botanical_identity_id=identity.id,
        originating_sowing_id=sowing.id,
        quantity_value=20,
        quantity_is_approximate=True,
        lifecycle="active",
    )
    unknown_group = PlantGroup(
        id=uuid7(),
        botanical_identity_id=identity.id,
        originating_sowing_id=sowing.id,
        lifecycle="active",
    )
    plant.id = uuid7()
    group.id = uuid7()
    group.quantity_value = 4
    extracted = Plant(
        id=uuid7(),
        botanical_identity_id=identity.id,
        originating_plant_group_id=group.id,
        lifecycle="active",
    )
    database.get.side_effect = lambda model, item_id: sowing if model is Sowing else None
    database.scalars.side_effect = [[group, approximate_group, unknown_group], [plant, extracted]]
    summary = service.propagation_summary(database, sowing.id)
    assert summary.exact_descendant_count == 6
    assert summary.approximate_plant_group_count == 1
    assert summary.unknown_plant_group_count == 1
    assert summary.germinated_count == 9
    assert {item.id for item in summary.plants} == {plant.id, extracted.id}
    assert summary.plant_groups[0].quantity is not None


def test_propagation_api_handlers_and_error_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    actor = cast(Any, SimpleNamespace(owner=True))
    database = MagicMock()
    source = lot()
    identity = BotanicalIdentity(id=source.botanical_identity_id, scientific_name="Source")
    sowing = Sowing(id=uuid7(), seed_lot_id=source.id, lifecycle="active")
    sowing_projection = SowingProjection(sowing, source, identity, None)
    sowing_response = cast(Any, SowingResponse).model_construct(id=sowing.id)
    seed_response = cast(Any, SeedLotResponse).model_construct(id=source.id)
    monkeypatch.setattr(seed_lot_api, "create_sowing_from_seed_lot", lambda *_: (sowing, source))
    monkeypatch.setattr(seed_lot_api, "get_sowing", lambda *_: sowing_projection)
    monkeypatch.setattr(seed_lot_api, "sowing_responses", lambda *_: [sowing_response])
    monkeypatch.setattr(seed_lot_api, "_response", lambda *_: seed_response)
    response = Response()
    result = seed_lot_api.create_sowing_transition(
        source.id,
        sowing_transition(None, {"mode": "none"}),
        response,
        actor,
        database,
    )
    assert result.sowing.id == sowing.id
    assert response.headers["location"].endswith(str(sowing.id))

    plant = Plant(id=uuid7(), botanical_identity_id=uuid7(), originating_sowing_id=sowing.id)
    group = PlantGroup(id=uuid7(), botanical_identity_id=uuid7(), originating_sowing_id=sowing.id)
    plant_response = cast(Any, PlantResponse).model_construct(id=plant.id)
    group_response = cast(Any, PlantGroupResponse).model_construct(id=group.id)
    monkeypatch.setattr(sowing_api, "create_plant_from_sowing", lambda *_: (plant, sowing))
    monkeypatch.setattr(sowing_api, "create_plant_group_from_sowing", lambda *_: (group, sowing))
    monkeypatch.setattr(sowing_api, "get_plant", lambda *_: object())
    monkeypatch.setattr(sowing_api, "get_plant_group", lambda *_: object())
    monkeypatch.setattr(sowing_api, "plant_responses", lambda *_: [plant_response])
    monkeypatch.setattr(sowing_api, "plant_group_responses", lambda *_: [group_response])
    monkeypatch.setattr(sowing_api, "_response", lambda *_: sowing_response)
    plant_result = sowing_api.create_plant_transition(
        sowing.id,
        SowingPlantTransitionCreate(
            plant={"botanical_identity_id": plant.botanical_identity_id},
            resulting_sowing_lifecycle="active",
        ),
        Response(),
        actor,
        database,
    )
    assert plant_result.plant.id == plant.id
    group_result = sowing_api.create_plant_group_transition(
        sowing.id,
        SowingPlantGroupTransitionCreate(
            plant_group={"botanical_identity_id": group.botanical_identity_id},
            resulting_sowing_lifecycle="failed",
        ),
        Response(),
        actor,
        database,
    )
    assert group_result.plant_group.id == group.id

    missing = PropagationNotFoundError("sowing_not_found", "Sowing not found")
    monkeypatch.setattr(
        sowing_api, "propagation_summary", lambda *_: (_ for _ in ()).throw(missing)
    )
    with pytest.raises(HTTPException) as error:
        sowing_api.read_propagation_summary(sowing.id, actor, database)
    assert error.value.status_code == 404
