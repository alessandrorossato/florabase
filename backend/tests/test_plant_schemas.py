import pytest
from pydantic import ValidationError

from florabase.plants.schemas import PlantCreate, PlantGroupCreate

IDENTITY_ID = "018f0000-0000-7000-8000-000000000001"
SOWING_ID = "018f0000-0000-7000-8000-000000000002"


def test_minimum_origin_defaults_and_text_normalization() -> None:
    plant = PlantCreate(botanical_identity_id=IDENTITY_ID)
    group = PlantGroupCreate(botanical_identity_id=IDENTITY_ID)
    assert plant.direct_origin_kind == "unknown"
    assert plant.lifecycle == "active"
    assert group.direct_origin_kind == "unknown"
    assert group.quantity is None
    assert PlantCreate(botanical_identity_id=IDENTITY_ID, lifecycle="transferred").lifecycle == (
        "transferred"
    )
    with pytest.raises(ValidationError):
        PlantCreate(botanical_identity_id=IDENTITY_ID, lifecycle="reintegrated")
    full = PlantCreate(
        botanical_identity_id=IDENTITY_ID,
        direct_origin_kind="other",
        direct_origin_detail="  garden   exchange ",
        label=" Tamarillo   mother ",
        notes=" First.\r\nSecond\tline. ",
    )
    assert full.direct_origin_detail == "garden exchange"
    assert full.label == "Tamarillo mother"
    assert full.notes == "First.\nSecond\tline."


def test_sowing_and_direct_origin_are_exclusive() -> None:
    sowing = PlantCreate(botanical_identity_id=IDENTITY_ID, originating_sowing_id=SOWING_ID)
    assert sowing.direct_origin_kind is None
    for extra in (
        {"direct_origin_kind": "unknown"},
        {"supplier_id": IDENTITY_ID},
        {"material_provenance_place_id": IDENTITY_ID},
    ):
        with pytest.raises(ValidationError):
            PlantCreate(
                botanical_identity_id=IDENTITY_ID,
                originating_sowing_id=SOWING_ID,
                **extra,
            )
    with pytest.raises(ValidationError):
        PlantCreate(
            botanical_identity_id=IDENTITY_ID,
            direct_origin_kind="purchased",
            direct_origin_detail="invalid",
        )


@pytest.mark.parametrize(
    ("lifecycle", "quantity", "valid"),
    [
        ("active", None, True),
        ("active", {"value": 12, "is_approximate": False}, True),
        ("lost", {"value": 8, "is_approximate": True}, True),
        ("transferred", {"value": 8, "is_approximate": False}, True),
        ("transferred", None, True),
        ("completed", {"value": 0, "is_approximate": False}, True),
        ("dead", {"value": 0, "is_approximate": False}, True),
        ("discarded", {"value": 0, "is_approximate": False}, True),
        ("active", {"value": 0, "is_approximate": False}, False),
        ("lost", {"value": 0, "is_approximate": False}, False),
        ("transferred", {"value": 0, "is_approximate": False}, False),
        ("dead", {"value": 0, "is_approximate": True}, False),
        ("active", {"value": -1, "is_approximate": False}, False),
        ("active", {"value": 1.5, "is_approximate": False}, False),
    ],
)
def test_group_quantity_final_state_rules(
    lifecycle: str, quantity: dict[str, object] | None, valid: bool
) -> None:
    payload = {"botanical_identity_id": IDENTITY_ID, "lifecycle": lifecycle, "quantity": quantity}
    if valid:
        PlantGroupCreate.model_validate(payload)
    else:
        with pytest.raises(ValidationError):
            PlantGroupCreate.model_validate(payload)


@pytest.mark.parametrize(
    "value",
    [
        {"precision": "year", "year": 2024},
        {"precision": "month", "year": 2024, "month": 5},
        {"precision": "day", "year": 2024, "month": 5, "day": 18},
    ],
)
def test_collection_entry_date_preserves_precision(value: dict[str, object]) -> None:
    plant = PlantCreate(botanical_identity_id=IDENTITY_ID, collection_entry_date=value)
    assert plant.collection_entry_date is not None
    assert plant.collection_entry_date.precision == value["precision"]
