from datetime import UTC, datetime, timedelta, timezone
from typing import Any, cast
from unittest.mock import MagicMock
from uuid import uuid7

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError

from florabase.plants import api as plants_api
from florabase.plants import service as plants_service
from florabase.plants.model import Plant, PlantGroup, PlantLifecycle
from florabase.plants.schemas import PlantGroupExtractBatchCreate
from florabase.plants.service import PlantDomainConflictError, PlantReferenceNotFoundError
from florabase.propagation import api as propagation_api
from florabase.propagation import service as propagation_service
from florabase.propagation.labels import (
    MAX_BATCH_COUNT,
    MAX_LABEL_LENGTH,
    default_counter_padding,
    expand_label_pattern,
    normalize_single_line,
)
from florabase.propagation.schemas import SowingPotOnCreate
from florabase.propagation.service import PropagationConflictError, PropagationNotFoundError
from florabase.sowings.model import Sowing, SowingLifecycle


def _sowing(*, lifecycle: str = "active", updated_at: datetime | None = None) -> Sowing:
    now = updated_at or datetime.now(UTC)
    return Sowing(
        id=uuid7(),
        seed_lot_id=uuid7(),
        lifecycle=lifecycle,
        created_at=now,
        updated_at=now,
    )


def _group(
    *,
    lifecycle: str = "active",
    quantity_value: int | None = 20,
    quantity_is_approximate: bool | None = False,
    updated_at: datetime | None = None,
) -> PlantGroup:
    now = updated_at or datetime.now(UTC)
    return PlantGroup(
        id=uuid7(),
        botanical_identity_id=uuid7(),
        lifecycle=lifecycle,
        quantity_value=quantity_value,
        quantity_is_approximate=quantity_is_approximate,
        created_at=now,
        updated_at=now,
    )


def test_label_pattern_expansion_padding_start_and_literal_braces() -> None:
    assert default_counter_padding(12, 1) == 2
    assert default_counter_padding(9, 1) == 1
    assert default_counter_padding(100, 1) == 3
    assert default_counter_padding(3, 9) == 2

    labels = expand_label_pattern("HOY-24-07-{n}", count=12)
    assert len(labels) == 12
    assert labels[0] == "HOY-24-07-01"
    assert labels[11] == "HOY-24-07-12"

    shifted = expand_label_pattern("TRAY-{n}", count=3, counter_start=9)
    assert shifted == ["TRAY-09", "TRAY-10", "TRAY-11"]

    padded = expand_label_pattern("P-{n}", count=2, counter_start=1, counter_padding=4)
    assert padded == ["P-0001", "P-0002"]

    unpadded = expand_label_pattern("P-{n}", count=12, counter_start=1, counter_padding=1)
    assert unpadded[0] == "P-1"
    assert unpadded[11] == "P-12"

    zero_start = expand_label_pattern("Z-{n}", count=3, counter_start=0)
    assert zero_start == ["Z-0", "Z-1", "Z-2"]

    no_placeholder = expand_label_pattern("HOY-24-07", count=3)
    assert no_placeholder == ["HOY-24-07", "HOY-24-07", "HOY-24-07"]

    literal_braces = expand_label_pattern("Lot {A} #{n}", count=2)
    assert literal_braces == ["Lot {A} #1", "Lot {A} #2"]

    repeated_placeholder = expand_label_pattern("{n}/{n}", count=2, counter_padding=2)
    assert repeated_placeholder == ["01/01", "02/02"]

    assert expand_label_pattern(None, count=3) == [None, None, None]
    assert expand_label_pattern("   \t  ", count=2) == [None, None]
    assert expand_label_pattern("  HOY   {n}  ", count=2) == ["HOY 1", "HOY 2"]


def test_label_pattern_rejects_control_chars_limits_and_overflow() -> None:
    with pytest.raises(ValueError, match="control characters"):
        normalize_single_line("bad\x00label")

    with pytest.raises(ValueError, match="control characters"):
        expand_label_pattern("bad\x07{n}", count=2)

    with pytest.raises(ValueError, match="between 1 and 200"):
        expand_label_pattern("A-{n}", count=0)

    with pytest.raises(ValueError, match="between 1 and 200"):
        expand_label_pattern("A-{n}", count=MAX_BATCH_COUNT + 1)

    with pytest.raises(ValueError, match="non-negative"):
        expand_label_pattern("A-{n}", count=1, counter_start=-1)

    with pytest.raises(ValueError, match="non-negative"):
        expand_label_pattern("A-{n}", count=1, counter_padding=-1)

    # Raw pattern is 254 chars (<= 255), but expanding {n} with 5 digits makes 256 chars.
    exact_pattern = "x" * (MAX_LABEL_LENGTH - 5) + "{n}"
    assert len(expand_label_pattern(exact_pattern, count=1, counter_padding=5)[0] or "") == 255

    overflow_pattern = "x" * (MAX_LABEL_LENGTH - 4) + "{n}"
    with pytest.raises(ValueError, match="255"):
        expand_label_pattern(overflow_pattern, count=1, counter_padding=5)


def test_sowing_pot_on_schema_validation() -> None:
    identity_id = uuid7()
    base: dict[str, object] = {
        "count": 3,
        "botanical_identity_id": identity_id,
        "resulting_sowing_lifecycle": "completed",
    }
    parsed = SowingPotOnCreate.model_validate(base)
    assert parsed.counter_start == 1
    assert parsed.counter_padding is None
    assert parsed.plant_lifecycle == PlantLifecycle.ACTIVE

    for bad_count in (0, -2, 201):
        with pytest.raises(ValidationError):
            SowingPotOnCreate.model_validate({**base, "count": bad_count})

    for forbidden_plant_lifecycle in ("reversed", "reintegrated"):
        with pytest.raises(ValidationError):
            SowingPotOnCreate.model_validate({**base, "plant_lifecycle": forbidden_plant_lifecycle})

    with pytest.raises(ValidationError):
        SowingPotOnCreate.model_validate({**base, "resulting_sowing_lifecycle": "reversed"})

    with pytest.raises(ValidationError):
        SowingPotOnCreate.model_validate(
            {
                **base,
                "label_pattern": "x" * 252 + "{n}",
                "counter_padding": 4,
            }
        )

    with pytest.raises(ValidationError):
        SowingPotOnCreate.model_validate(
            {**base, "expected_sowing_updated_at": "2026-11-24T12:00:00"}
        )

    with pytest.raises(ValidationError):
        SowingPotOnCreate.model_validate({**base, "unexpected": True})


def test_extract_batch_schema_validation() -> None:
    parsed = PlantGroupExtractBatchCreate.model_validate({"count": 5, "label_pattern": "G-{n}"})
    assert parsed.counter_start == 1
    assert parsed.counter_padding is None

    for bad_count in (0, 201):
        with pytest.raises(ValidationError):
            PlantGroupExtractBatchCreate.model_validate({"count": bad_count})

    with pytest.raises(ValidationError):
        PlantGroupExtractBatchCreate.model_validate(
            {"count": 2, "label_pattern": "y" * 253 + "{n}", "counter_padding": 3}
        )

    with pytest.raises(ValidationError):
        PlantGroupExtractBatchCreate.model_validate(
            {"count": 1, "expected_plant_group_updated_at": "2026-11-24T12:00:00"}
        )


def test_create_plants_from_sowing_batch_applies_lifecycle_only_on_last(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sowing = _sowing(lifecycle="active")
    database = MagicMock()
    database.scalar.return_value = sowing
    calls: list[tuple[str | None, str]] = []

    def fake_create(
        _database: Any,
        sowing_id: Any,
        plant_payload: Any,
        resulting_lifecycle: str,
    ) -> tuple[Plant, Sowing]:
        assert sowing_id == sowing.id
        calls.append((plant_payload.label, resulting_lifecycle))
        sowing.lifecycle = resulting_lifecycle
        plant = Plant(
            id=uuid7(),
            botanical_identity_id=plant_payload.botanical_identity_id,
            originating_sowing_id=sowing.id,
            label=plant_payload.label,
            lifecycle=plant_payload.lifecycle.value,
        )
        return plant, sowing

    monkeypatch.setattr(propagation_service, "create_plant_from_sowing", fake_create)
    offset_tz = timezone(timedelta(hours=2))
    payload = SowingPotOnCreate(
        count=4,
        label_pattern="HOY-{n}",
        botanical_identity_id=uuid7(),
        resulting_sowing_lifecycle=SowingLifecycle.COMPLETED,
        expected_sowing_updated_at=sowing.updated_at.astimezone(offset_tz),
    )

    plants, updated = propagation_service.create_plants_from_sowing_batch(
        database, sowing.id, payload
    )

    assert len(plants) == 4
    assert updated.lifecycle == "completed"
    assert calls == [
        ("HOY-1", "active"),
        ("HOY-2", "active"),
        ("HOY-3", "active"),
        ("HOY-4", "completed"),
    ]


def test_create_plants_from_sowing_batch_rejects_missing_stale_inactive_and_reversed() -> None:
    identity_id = uuid7()
    payload = SowingPotOnCreate(
        count=2,
        botanical_identity_id=identity_id,
        resulting_sowing_lifecycle=SowingLifecycle.ACTIVE,
    )

    missing_db = MagicMock()
    missing_db.scalar.return_value = None
    with pytest.raises(PropagationNotFoundError) as missing_exc:
        propagation_service.create_plants_from_sowing_batch(missing_db, uuid7(), payload)
    assert missing_exc.value.code == "sowing_not_found"

    reversed_sowing = _sowing(lifecycle="reversed")
    reversed_db = MagicMock()
    reversed_db.scalar.return_value = reversed_sowing
    with pytest.raises(PropagationConflictError) as rev_exc:
        propagation_service.create_plants_from_sowing_batch(
            reversed_db, reversed_sowing.id, payload
        )
    assert rev_exc.value.code == "reversed_sowing_is_historical"

    for inactive in ("completed", "failed", "abandoned"):
        inactive_sowing = _sowing(lifecycle=inactive)
        inactive_db = MagicMock()
        inactive_db.scalar.return_value = inactive_sowing
        with pytest.raises(PropagationConflictError) as inactive_exc:
            propagation_service.create_plants_from_sowing_batch(
                inactive_db, inactive_sowing.id, payload
            )
        assert inactive_exc.value.code == "sowing_not_active"

    active_sowing = _sowing(lifecycle="active")
    stale_db = MagicMock()
    stale_db.scalar.return_value = active_sowing
    stale_payload = SowingPotOnCreate(
        count=2,
        botanical_identity_id=identity_id,
        resulting_sowing_lifecycle=SowingLifecycle.COMPLETED,
        expected_sowing_updated_at=active_sowing.updated_at - timedelta(seconds=5),
    )
    with pytest.raises(PropagationConflictError) as stale_exc:
        propagation_service.create_plants_from_sowing_batch(
            stale_db, active_sowing.id, stale_payload
        )
    assert stale_exc.value.code == "stale_preview"


def test_extract_plants_batch_guards_and_location_inheritance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_db = MagicMock()
    missing_db.scalar.return_value = None
    with pytest.raises(PlantReferenceNotFoundError) as missing_exc:
        plants_service.extract_plants_batch(
            missing_db, uuid7(), PlantGroupExtractBatchCreate(count=2)
        )
    assert missing_exc.value.code == "plant_group_not_found"

    inactive_group = _group(lifecycle="completed", quantity_value=0)
    inactive_db = MagicMock()
    inactive_db.scalar.return_value = inactive_group
    with pytest.raises(PlantDomainConflictError) as inactive_exc:
        plants_service.extract_plants_batch(
            inactive_db, inactive_group.id, PlantGroupExtractBatchCreate(count=1)
        )
    assert inactive_exc.value.code == "plant_group_not_active"

    small_group = _group(lifecycle="active", quantity_value=3, quantity_is_approximate=False)
    small_db = MagicMock()
    small_db.scalar.return_value = small_group
    with pytest.raises(PlantDomainConflictError) as exceed_exc:
        plants_service.extract_plants_batch(
            small_db, small_group.id, PlantGroupExtractBatchCreate(count=4)
        )
    assert exceed_exc.value.code == "plant_group_quantity_exceeded"

    stale_db = MagicMock()
    stale_db.scalar.return_value = small_group
    with pytest.raises(PlantDomainConflictError) as stale_exc:
        plants_service.extract_plants_batch(
            stale_db,
            small_group.id,
            PlantGroupExtractBatchCreate(
                count=2,
                expected_plant_group_updated_at=small_group.updated_at - timedelta(seconds=10),
            ),
        )
    assert stale_exc.value.code == "stale_preview"

    # Location omission preserves model_fields_set so extract_plant inherits group.location_id.
    approx_group = _group(lifecycle="active", quantity_value=5, quantity_is_approximate=True)
    approx_db = MagicMock()
    approx_db.scalar.return_value = approx_group
    seen_fields: list[set[str]] = []

    def fake_extract(_db: Any, group_id: Any, item: Any) -> tuple[Plant, PlantGroup, Any]:
        assert group_id == approx_group.id
        seen_fields.append(set(item.model_fields_set))
        return (
            Plant(id=uuid7(), botanical_identity_id=approx_group.botanical_identity_id),
            approx_group,
            MagicMock(id=uuid7()),
        )

    monkeypatch.setattr(plants_service, "extract_plant", fake_extract)
    plants, _group_out, events = plants_service.extract_plants_batch(
        approx_db,
        approx_group.id,
        PlantGroupExtractBatchCreate(count=2, label_pattern="A-{n}"),
    )
    assert len(plants) == 2
    assert len(events) == 2
    assert all("location_id" not in fields for fields in seen_fields)

    seen_fields.clear()
    plants_service.extract_plants_batch(
        approx_db,
        approx_group.id,
        PlantGroupExtractBatchCreate(count=1, location_id=None),
    )
    assert seen_fields == [
        {"botanical_identity_id", "label", "collection_entry_date", "notes", "location_id"}
    ]


def test_api_routes_map_concurrency_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    actor = cast(Any, MagicMock(role="owner"))

    class FakeOrigError(Exception):
        sqlstate = "40P01"

    def raise_deadlock(*_args: Any, **_kwargs: Any) -> Any:
        raise OperationalError("SELECT", {}, FakeOrigError())

    monkeypatch.setattr(propagation_api, "create_plants_from_sowing_batch", raise_deadlock)
    with pytest.raises(HTTPException) as pot_on_exc:
        propagation_api.pot_on_sowing(
            uuid7(),
            SowingPotOnCreate(
                count=1,
                botanical_identity_id=uuid7(),
                resulting_sowing_lifecycle=SowingLifecycle.ACTIVE,
            ),
            actor,
            MagicMock(),
        )
    assert pot_on_exc.value.status_code == 409
    assert cast(object, pot_on_exc.value.detail) == {
        "code": "propagation_concurrency_conflict",
        "message": "Concurrent work conflicted. Refresh and retry.",
    }

    monkeypatch.setattr(plants_api, "extract_plants_batch", raise_deadlock)
    with pytest.raises(HTTPException) as extract_exc:
        plants_api.extract_plants_batch_route(
            uuid7(),
            PlantGroupExtractBatchCreate(count=1),
            actor,
            MagicMock(),
        )
    assert extract_exc.value.status_code == 409
    assert cast(object, extract_exc.value.detail) == {
        "code": "propagation_concurrency_conflict",
        "message": "Concurrent work conflicted. Refresh and retry.",
    }
