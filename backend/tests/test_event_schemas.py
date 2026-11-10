from uuid import uuid7

import pytest
from pydantic import ValidationError

from florabase.events.model import Phenophase
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


_STAGES = {
    "observation": [
        "bud_break",
        "leaf_color_change",
        "leaf_fall",
        "dormancy_entry",
        "dormancy_exit",
    ],
    "flowering": ["flowering_onset", "flowering_ongoing", "flowering_end"],
    "fruiting": ["fruit_set", "fruit_ripening", "fruit_ripe"],
}


@pytest.mark.parametrize(
    ("kind", "phase"), [(kind, phase) for kind, phases in _STAGES.items() for phase in phases]
)
def test_every_phenophase_is_accepted_on_its_own_kind_only(kind: str, phase: str) -> None:
    payload = EventCreate(kind=kind, phenology={"phase": phase})
    assert payload.phenology is not None
    assert payload.phenology.model_dump(mode="json") == {
        "phase": phase,
        "date_is_approximate": False,
    }
    for other in ("observation", "flowering", "fruiting", "measurement", "other", "pruning"):
        if other != kind:
            with pytest.raises(ValidationError):
                EventCreate.model_validate(
                    {
                        "kind": other,
                        "occurred_on": DAY,
                        "measurement": _height() if other == "measurement" else None,
                        "phenology": {"phase": phase},
                    }
                )


def test_phenology_vocabulary_is_closed_and_approximation_needs_a_date() -> None:
    assert {phase for phases in _STAGES.values() for phase in phases} == {
        item.value for item in Phenophase
    }
    month = {"precision": "month", "year": 2025, "month": 5}
    approximate = EventCreate(
        kind="flowering",
        occurred_on=month,
        phenology={"phase": "flowering_onset", "date_is_approximate": True},
    )
    assert approximate.phenology is not None
    assert approximate.phenology.date_is_approximate
    for body in (
        {
            "kind": "flowering",
            "phenology": {"phase": "flowering_onset", "date_is_approximate": True},
        },
        {"kind": "flowering", "phenology": {"phase": "Flowering"}},
        {"kind": "flowering", "phenology": {"phase": "flowering_onset", "certainty": "low"}},
        {"kind": "flowering", "phenology": {}},
    ):
        with pytest.raises(ValidationError):
            EventCreate.model_validate(body)
    # Existing stage-less flowering and fruiting entries remain valid.
    assert EventUpdate(kind="fruiting").phenology is None
