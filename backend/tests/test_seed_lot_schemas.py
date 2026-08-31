from decimal import Decimal

import pytest
from pydantic import ValidationError

from florabase.seed_lots.schemas import PartialDate, SeedLotCreate, SeedQuantity


def test_seed_lot_normalizes_text_and_defaults() -> None:
    payload = SeedLotCreate(
        botanical_identity_id="018f0000-0000-7000-8000-000000000001",
        label="  Trip   lot ",
        source_kind="other",
        source_detail="  local   exchange ",
        notes=" First line.\r\nSecond\tline. ",
    )
    assert payload.label == "Trip lot"
    assert payload.source_detail == "local exchange"
    assert payload.notes == "First line.\nSecond\tline."
    assert payload.lifecycle.value == "active"


@pytest.mark.parametrize(
    "value",
    [
        {"precision": "year", "year": 2024, "month": 1},
        {"precision": "month", "year": 2024},
        {"precision": "month", "year": 2024, "month": 1, "day": 1},
        {"precision": "day", "year": 2023, "month": 2, "day": 29},
    ],
)
def test_partial_date_rejects_precision_mismatch_and_invalid_calendar_date(
    value: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        PartialDate.model_validate(value)


@pytest.mark.parametrize(
    "value",
    [
        {"kind": "seed_count", "value": "1.5", "is_approximate": False},
        {"kind": "seed_count", "value": "1", "unit": "g", "is_approximate": False},
        {"kind": "weight", "value": "1", "is_approximate": False},
        {"kind": "weight", "value": "-1", "unit": "g", "is_approximate": False},
        {"kind": "weight", "value": "0", "unit": "g", "is_approximate": True},
    ],
)
def test_quantity_rejects_incoherent_values(value: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        SeedQuantity.model_validate(value)


def test_decimal_quantity_serializes_exactly_as_string() -> None:
    quantity = SeedQuantity(
        kind="weight", value=Decimal("4.500000000000000001"), unit="g", is_approximate=False
    )
    assert quantity.model_dump(mode="json")["value"] == "4.500000000000000001"


def test_source_detail_and_zero_lifecycle_are_cross_validated() -> None:
    identity_id = "018f0000-0000-7000-8000-000000000001"
    with pytest.raises(ValidationError):
        SeedLotCreate(
            botanical_identity_id=identity_id,
            source_kind="purchased",
            source_detail="catalog",
        )
    with pytest.raises(ValidationError):
        SeedLotCreate(
            botanical_identity_id=identity_id,
            quantity={"kind": "seed_count", "value": 0, "is_approximate": False},
        )
