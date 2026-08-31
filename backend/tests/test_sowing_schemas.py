from decimal import Decimal

import pytest
from pydantic import ValidationError

from florabase.sowings.schemas import SowingCreate, SowingQuantity

SEED_LOT_ID = "018f0000-0000-7000-8000-000000000001"


def test_sowing_minimal_defaults_and_full_text_normalization() -> None:
    minimal = SowingCreate(seed_lot_id=SEED_LOT_ID)
    assert minimal.lifecycle.value == "active"
    assert minimal.quantity is None
    full = SowingCreate(
        seed_lot_id=SEED_LOT_ID,
        label="  Spring   tray ",
        substrate="  seed   mix ",
        method_container=" covered   tray ",
        pretreatment=" soak   12 h ",
        environment=" warm   shelf ",
        notes=" First.\r\nSecond\tline. ",
    )
    assert full.label == "Spring tray"
    assert full.substrate == "seed mix"
    assert full.notes == "First.\nSecond\tline."


@pytest.mark.parametrize(
    "quantity",
    [
        {"kind": "seed_count", "value": 0, "is_approximate": False},
        {"kind": "seed_count", "value": "1.5", "is_approximate": False},
        {"kind": "seed_count", "value": 1, "unit": "g", "is_approximate": False},
        {"kind": "weight", "value": 1, "is_approximate": False},
        {"kind": "weight", "value": -1, "unit": "mg", "is_approximate": False},
    ],
)
def test_sowing_quantity_rejects_zero_and_incoherent_values(
    quantity: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        SowingQuantity.model_validate(quantity)


def test_sowing_final_state_germination_and_temperature_validation() -> None:
    valid = SowingCreate(
        seed_lot_id=SEED_LOT_ID,
        quantity={"kind": "seed_count", "value": 10, "is_approximate": False},
        germinated_count=10,
        temperature_min_c="20.5",
        temperature_max_c="25",
    )
    assert valid.temperature_min_c == Decimal("20.5")
    assert valid.model_dump(mode="json")["temperature_min_c"] == "20.5"
    for changes in (
        {"germinated_count": -1},
        {
            "quantity": {"kind": "seed_count", "value": 10, "is_approximate": False},
            "germinated_count": 11,
        },
        {"temperature_min_c": 26, "temperature_max_c": 25},
    ):
        with pytest.raises(ValidationError):
            SowingCreate(seed_lot_id=SEED_LOT_ID, **changes)
    assert (
        SowingCreate(
            seed_lot_id=SEED_LOT_ID,
            quantity={"kind": "seed_count", "value": 10, "is_approximate": True},
            germinated_count=11,
        ).germinated_count
        == 11
    )
    assert (
        SowingCreate(
            seed_lot_id=SEED_LOT_ID,
            quantity={"kind": "weight", "value": 1, "unit": "g", "is_approximate": False},
            germinated_count=37,
        ).germinated_count
        == 37
    )
