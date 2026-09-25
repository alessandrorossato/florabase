from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid7

import pytest

from florabase.sowings.germination_service import germination_detail
from florabase.sowings.model import GerminationObservation, Sowing


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
