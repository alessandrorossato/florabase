from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid7

import pytest

from florabase.sowings.germination_schemas import GerminationObservationWrite
from florabase.sowings.germination_service import (
    GerminationConflictError,
    create_observation,
    delete_observation,
    germination_detail,
    update_observation,
)
from florabase.sowings.model import GerminationObservation, Sowing


def _exact_sowing(*, seed_count: int = 20) -> Sowing:
    return Sowing(
        id=uuid7(),
        seed_lot_id=uuid7(),
        sowing_date_precision="day",
        sowing_date_year=2026,
        sowing_date_month=4,
        sowing_date_day=10,
        quantity_kind="seed_count",
        quantity_value=Decimal(seed_count),
        quantity_is_approximate=False,
        lifecycle="active",
    )


def _observation(sowing: Sowing, *, observed_on: date, count: int) -> GerminationObservation:
    now = datetime.now(UTC)
    return GerminationObservation(
        id=uuid7(),
        sowing_id=sowing.id,
        observed_on=observed_on,
        newly_germinated_count=count,
        created_at=now,
        updated_at=now,
    )


def test_summary_uses_incremental_observations_and_exact_seed_threshold() -> None:
    now = datetime.now(UTC)
    sowing = Sowing(
        id=uuid7(),
        seed_lot_id=uuid7(),
        sowing_date_precision="day",
        sowing_date_year=2026,
        sowing_date_month=4,
        sowing_date_day=10,
        quantity_kind="seed_count",
        quantity_value=Decimal("21"),
        quantity_is_approximate=False,
        germinated_count=12,
        lifecycle="active",
    )
    observations = [
        GerminationObservation(
            id=uuid7(),
            sowing_id=sowing.id,
            observed_on=observed_on,
            newly_germinated_count=count,
            created_at=now,
            updated_at=now,
        )
        for observed_on, count in (
            (date(2026, 4, 10), 0),
            (date(2026, 4, 14), 8),
            (date(2026, 4, 16), 4),
        )
    ]
    database = MagicMock()
    database.get.return_value = sowing
    database.scalars.return_value = observations

    detail = germination_detail(database, sowing.id)

    assert detail is not None
    assert detail.simple_germinated_count == 12
    assert detail.summary.observed_cumulative_count == 12
    assert detail.summary.first_germination_on == date(2026, 4, 14)
    assert detail.summary.days_to_first_germination == 4
    assert detail.summary.germination_percentage == Decimal(12) / Decimal(21) * 100
    assert detail.summary.t50_days == Decimal("5.25")
    assert [point.cumulative_germinated_count for point in detail.summary.cumulative_series] == [
        0,
        8,
        12,
    ]


@pytest.mark.parametrize(
    ("seed_count", "counts", "expected_t50"),
    [
        (20, [(2, 4), (5, 6)], "5"),  # Exact threshold, no interpolation needed.
        (20, [(4, 12)], "3.333333333333333333333333333"),  # Baseline interpolation.
        (21, [(4, 8), (6, 4)], "5.25"),  # Fractional threshold is 10.5.
        (20, [(3, 2), (4, 16)], "3.5"),  # Large single-day crossing.
        (20, [(1, 0), (2, 0), (5, 12)], "4.5"),
    ],
)
def test_t50_uses_exact_sown_seed_threshold_and_linear_interpolation(
    seed_count: int, counts: list[tuple[int, int]], expected_t50: str
) -> None:
    now = datetime.now(UTC)
    sowing = Sowing(
        id=uuid7(),
        seed_lot_id=uuid7(),
        sowing_date_precision="day",
        sowing_date_year=2026,
        sowing_date_month=4,
        sowing_date_day=10,
        quantity_kind="seed_count",
        quantity_value=Decimal(seed_count),
        quantity_is_approximate=False,
        lifecycle="active",
    )
    observations = [
        GerminationObservation(
            id=uuid7(),
            sowing_id=sowing.id,
            observed_on=date(2026, 4, 10 + day),
            newly_germinated_count=count,
            created_at=now,
            updated_at=now,
        )
        for day, count in counts
    ]
    database = MagicMock()
    database.get.return_value = sowing
    database.scalars.return_value = observations

    detail = germination_detail(database, sowing.id)

    assert detail is not None
    assert str(detail.summary.t50_days) == expected_t50


@pytest.mark.parametrize(
    ("precision", "quantity_kind", "approximate", "has_observations"),
    [
        ("month", "seed_count", False, True),
        ("day", "seed_count", True, True),
        ("day", "weight", False, True),
        ("day", None, False, True),
        ("day", "seed_count", False, False),
    ],
)
def test_timing_and_percentage_are_unavailable_without_exact_inputs(
    precision: str,
    quantity_kind: str | None,
    approximate: bool,
    has_observations: bool,
) -> None:
    now = datetime.now(UTC)
    sowing = Sowing(
        id=uuid7(),
        seed_lot_id=uuid7(),
        sowing_date_precision=precision,
        sowing_date_year=2026,
        sowing_date_month=4 if precision != "year" else None,
        sowing_date_day=10 if precision == "day" else None,
        quantity_kind=quantity_kind,
        quantity_value=Decimal("20") if quantity_kind else None,
        quantity_unit="g" if quantity_kind == "weight" else None,
        quantity_is_approximate=approximate if quantity_kind else None,
        lifecycle="active",
    )
    observations = (
        [
            GerminationObservation(
                id=uuid7(),
                sowing_id=sowing.id,
                observed_on=date(2026, 4, 10),
                newly_germinated_count=10,
                created_at=now,
                updated_at=now,
            )
        ]
        if has_observations
        else []
    )
    database = MagicMock()
    database.get.return_value = sowing
    database.scalars.return_value = observations

    detail = germination_detail(database, sowing.id)

    assert detail is not None
    assert detail.summary.t50_days is None
    if precision != "day":
        assert detail.summary.days_to_first_germination is None
    if quantity_kind != "seed_count" or approximate or not has_observations:
        assert detail.summary.germination_percentage is None


def test_create_observation_rejects_conflicts_and_persists_valid_input() -> None:
    sowing = _exact_sowing(seed_count=10)
    existing = _observation(sowing, observed_on=date(2026, 4, 12), count=4)
    database = MagicMock()
    database.scalar.return_value = sowing
    database.scalars.return_value = [existing]

    with pytest.raises(GerminationConflictError, match="existing observation") as duplicate:
        create_observation(
            database,
            sowing.id,
            GerminationObservationWrite(observed_on=existing.observed_on, newly_germinated_count=1),
        )
    assert duplicate.value.code == "observation_date_exists"

    with pytest.raises(GerminationConflictError, match="cannot precede") as before_sowing:
        create_observation(
            database,
            sowing.id,
            GerminationObservationWrite(observed_on=date(2026, 4, 9), newly_germinated_count=1),
        )
    assert before_sowing.value.code == "observation_before_sowing"

    with pytest.raises(GerminationConflictError, match="exceed") as over_seed_count:
        create_observation(
            database,
            sowing.id,
            GerminationObservationWrite(observed_on=date(2026, 4, 13), newly_germinated_count=7),
        )
    assert over_seed_count.value.code == "observations_exceed_seeds"

    created = create_observation(
        database,
        sowing.id,
        GerminationObservationWrite(observed_on=date(2026, 4, 13), newly_germinated_count=6),
    )

    assert created is not None
    assert created.observed_on == date(2026, 4, 13)
    assert created.newly_germinated_count == 6
    database.add.assert_called_once_with(created)
    database.flush.assert_called_once_with()


def test_create_observation_returns_none_for_missing_sowing() -> None:
    database = MagicMock()
    database.scalar.return_value = None

    result = create_observation(
        database,
        uuid7(),
        GerminationObservationWrite(observed_on=date(2026, 4, 13), newly_germinated_count=1),
    )

    assert result is None
    database.scalars.assert_not_called()
    database.add.assert_not_called()


def test_update_observation_handles_missing_records_and_updates_existing() -> None:
    sowing = _exact_sowing()
    observation = _observation(sowing, observed_on=date(2026, 4, 12), count=4)
    other = _observation(sowing, observed_on=date(2026, 4, 13), count=3)
    payload = GerminationObservationWrite(observed_on=date(2026, 4, 14), newly_germinated_count=5)

    missing_sowing = MagicMock()
    missing_sowing.scalar.return_value = None
    assert update_observation(missing_sowing, sowing.id, observation.id, payload) is None
    missing_sowing.scalars.assert_not_called()

    missing_observation = MagicMock()
    missing_observation.scalar.return_value = sowing
    missing_observation.scalars.return_value = [other]
    assert update_observation(missing_observation, sowing.id, observation.id, payload) is None
    missing_observation.flush.assert_not_called()

    database = MagicMock()
    database.scalar.return_value = sowing
    database.scalars.return_value = [observation, other]
    with pytest.raises(GerminationConflictError, match="existing observation") as duplicate:
        update_observation(
            database,
            sowing.id,
            observation.id,
            GerminationObservationWrite(observed_on=other.observed_on, newly_germinated_count=5),
        )
    assert duplicate.value.code == "observation_date_exists"

    updated = update_observation(database, sowing.id, observation.id, payload)

    assert updated is observation
    assert observation.observed_on == payload.observed_on
    assert observation.newly_germinated_count == payload.newly_germinated_count
    assert observation.updated_at.tzinfo is UTC
    database.flush.assert_called_once_with()


def test_delete_observation_handles_missing_records_and_deletes_existing() -> None:
    sowing = _exact_sowing()
    observation = _observation(sowing, observed_on=date(2026, 4, 12), count=4)

    missing_sowing = MagicMock()
    missing_sowing.scalar.return_value = None
    assert delete_observation(missing_sowing, sowing.id, observation.id) is False
    missing_sowing.delete.assert_not_called()

    missing_observation = MagicMock()
    missing_observation.scalar.side_effect = [sowing, None]
    assert delete_observation(missing_observation, sowing.id, observation.id) is False
    missing_observation.delete.assert_not_called()

    database = MagicMock()
    database.scalar.side_effect = [sowing, observation]
    assert delete_observation(database, sowing.id, observation.id) is True
    database.delete.assert_called_once_with(observation)
    database.flush.assert_called_once_with()


def test_germination_detail_returns_none_for_missing_sowing() -> None:
    database = MagicMock()
    database.get.return_value = None

    assert germination_detail(database, uuid7()) is None
    database.scalars.assert_not_called()
