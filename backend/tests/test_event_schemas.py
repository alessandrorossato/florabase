from uuid import uuid7

import pytest
from pydantic import ValidationError

from florabase.events.schemas import EventCreate, EventUpdate


@pytest.mark.parametrize(
    "kind",
    [
        "observation",
        "repotting",
        "flowering",
        "fruiting",
        "pruning",
        "treatment",
        "harvest",
        "transfer",
        "death",
        "loss",
        "discarded",
        "other",
    ],
)
def test_event_vocabulary_allows_optional_partial_data(kind: str) -> None:
    assert EventCreate(kind=kind).notes is None


@pytest.mark.parametrize(
    "occurred_on",
    [
        {"precision": "year", "year": 2024},
        {"precision": "month", "year": 2024, "month": 5},
        {"precision": "day", "year": 2024, "month": 5, "day": 18},
    ],
)
def test_event_reuses_partial_date_and_normalizes_notes(occurred_on: dict[str, object]) -> None:
    payload = EventCreate(kind="observation", occurred_on=occurred_on, notes=" First.\r\nSecond. ")
    assert payload.occurred_on is not None
    assert payload.occurred_on.model_dump(mode="json", exclude_none=True) == occurred_on
    assert payload.notes == "First.\nSecond."


def test_movement_destination_is_whole_payload_invariant() -> None:
    location_id = uuid7()
    assert (
        EventCreate(kind="movement", destination_location_id=location_id).destination_location_id
        == location_id
    )
    with pytest.raises(ValidationError):
        EventCreate(kind="movement")
    with pytest.raises(ValidationError):
        EventUpdate(kind="observation", destination_location_id=location_id)
    with pytest.raises(ValidationError):
        EventCreate.model_validate({"kind": "watering"})
    with pytest.raises(ValidationError):
        EventCreate.model_validate({"kind": "observation", "plant_id": str(uuid7())})


def test_transfer_and_extraction_fields_are_strictly_scoped() -> None:
    plant_id = uuid7()
    transfer = EventCreate(kind="transfer", recipient="  Garden   club ")
    assert transfer.recipient == "Garden club"
    extraction = EventCreate(kind="extraction", resulting_plant_id=plant_id)
    assert extraction.resulting_plant_id == plant_id
    with pytest.raises(ValidationError):
        EventCreate(kind="observation", recipient="Garden club")
    with pytest.raises(ValidationError):
        EventCreate(kind="extraction")
    with pytest.raises(ValidationError):
        EventCreate(kind="observation", resulting_plant_id=plant_id)


DAY = {"precision": "day", "year": 2026, "month": 5, "day": 1}


def _height(**overrides: object) -> dict[str, object]:
    return {"quantity": "height", "value": "12.50", "unit": "cm", **overrides}


def test_height_measurement_keeps_recorded_resolution_and_unit() -> None:
    payload = EventCreate(kind="measurement", occurred_on=DAY, measurement=_height())
    assert payload.measurement is not None
    assert payload.measurement.model_dump(mode="json") == {
        "quantity": "height",
        "value": "12.50",
        "unit": "cm",
        "is_approximate": False,
    }
    scientific = EventCreate(kind="measurement", occurred_on=DAY, measurement=_height(value="1E+2"))
    assert scientific.measurement is not None
    assert scientific.measurement.model_dump(mode="json")["value"] == "100"
    month = {"precision": "month", "year": 2026, "month": 5}
    assert EventCreate(
        kind="measurement", occurred_on=month, measurement=_height(value="200", unit="m")
    )


@pytest.mark.parametrize(
    "body",
    [
        {"kind": "measurement", "occurred_on": DAY},
        {"kind": "measurement", "measurement": _height()},
        {"kind": "observation", "occurred_on": DAY, "measurement": _height()},
        {"kind": "measurement", "occurred_on": DAY, "measurement": _height(unit="g")},
        {"kind": "measurement", "occurred_on": DAY, "measurement": _height(unit="in")},
        {"kind": "measurement", "occurred_on": DAY, "measurement": _height(quantity="weight")},
        {"kind": "measurement", "occurred_on": DAY, "measurement": _height(value="0")},
        {"kind": "measurement", "occurred_on": DAY, "measurement": _height(value="-3")},
        {"kind": "measurement", "occurred_on": DAY, "measurement": _height(value="NaN")},
        {"kind": "measurement", "occurred_on": DAY, "measurement": _height(value="1.2345")},
        {
            "kind": "measurement",
            "occurred_on": DAY,
            "measurement": _height(value="200.001", unit="m"),
        },
        {"kind": "measurement", "occurred_on": DAY, "measurement": _height(note="x")},
    ],
)
def test_invalid_measurements_are_refused(body: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        EventCreate.model_validate(body)
