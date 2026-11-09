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
                "quantity": {"value": 0, "is_approximate": False},
            }
        )
    with pytest.raises(ValidationError, match="End date precedes"):
        PropagationAttemptUpdate.model_validate(
            {
                "lifecycle": "failed",
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
