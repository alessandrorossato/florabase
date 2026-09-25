from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from florabase.sowings.germination_schemas import (
    GerminationObservationResponse,
    GerminationObservationWrite,
    GerminationSeriesPoint,
    GerminationSummary,
    SowingGerminationDetail,
)
from florabase.sowings.model import GerminationObservation, Sowing
from florabase.sowings.service import _partial_date, _quantity


@dataclass(frozen=True)
class GerminationConflictError(Exception):
    code: str
    message: str


def exact_sowing_date(sowing: Sowing) -> date | None:
    if sowing.sowing_date_precision != "day":
        return None
    assert sowing.sowing_date_year is not None
    assert sowing.sowing_date_month is not None
    assert sowing.sowing_date_day is not None
    return date(sowing.sowing_date_year, sowing.sowing_date_month, sowing.sowing_date_day)


def exact_seed_count(sowing: Sowing) -> Decimal | None:
    if sowing.quantity_kind != "seed_count" or sowing.quantity_is_approximate is not False:
        return None
    return sowing.quantity_value


def _observations(database: Session, sowing_id: UUID) -> list[GerminationObservation]:
    return list(
        database.scalars(
            select(GerminationObservation)
            .where(GerminationObservation.sowing_id == sowing_id)
            .order_by(GerminationObservation.observed_on, GerminationObservation.id)
        )
    )


def _locked_sowing(database: Session, sowing_id: UUID) -> Sowing | None:
    # Every observation mutation and Sowing edit serializes on this parent row.
    return database.scalar(
        select(Sowing)
        .where(Sowing.id == sowing_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def _validate(
    sowing: Sowing, observations: list[GerminationObservation], payload: GerminationObservationWrite
) -> None:
    sown_on = exact_sowing_date(sowing)
    if sown_on is not None and payload.observed_on < sown_on:
        raise GerminationConflictError(
            "observation_before_sowing", "Observation date cannot precede the exact Sowing date"
        )
    limit = exact_seed_count(sowing)
    if limit is not None and sum(item.newly_germinated_count for item in observations) > limit:
        raise GerminationConflictError(
            "observations_exceed_seeds", "Observed germinations exceed the exact seed count sown"
        )


def create_observation(
    database: Session, sowing_id: UUID, payload: GerminationObservationWrite
) -> GerminationObservation | None:
    sowing = _locked_sowing(database, sowing_id)
    if sowing is None:
        return None
    observations = _observations(database, sowing_id)
    if any(item.observed_on == payload.observed_on for item in observations):
        raise GerminationConflictError(
            "observation_date_exists", "Edit the existing observation for this date"
        )
    observation = GerminationObservation(sowing_id=sowing_id, **payload.model_dump())
    _validate(sowing, [*observations, observation], payload)
    database.add(observation)
    database.flush()
    return observation


def update_observation(
    database: Session, sowing_id: UUID, observation_id: UUID, payload: GerminationObservationWrite
) -> GerminationObservation | None:
    sowing = _locked_sowing(database, sowing_id)
    if sowing is None:
        return None
    observations = _observations(database, sowing_id)
    observation = next((item for item in observations if item.id == observation_id), None)
    if observation is None:
        return None
    if any(
        item.id != observation_id and item.observed_on == payload.observed_on
        for item in observations
    ):
        raise GerminationConflictError(
            "observation_date_exists", "Edit the existing observation for this date"
        )
    observation.observed_on = payload.observed_on
    observation.newly_germinated_count = payload.newly_germinated_count
    observation.updated_at = datetime.now(UTC)
    _validate(sowing, observations, payload)
    database.flush()
    return observation


def delete_observation(database: Session, sowing_id: UUID, observation_id: UUID) -> bool:
    sowing = _locked_sowing(database, sowing_id)
    if sowing is None:
        return False
    observation = database.scalar(
        select(GerminationObservation).where(
            GerminationObservation.sowing_id == sowing_id,
            GerminationObservation.id == observation_id,
        )
    )
    if observation is None:
        return False
    database.delete(observation)
    database.flush()
    return True


def germination_detail(database: Session, sowing_id: UUID) -> SowingGerminationDetail | None:
    sowing = database.get(Sowing, sowing_id)
    if sowing is None:
        return None
    observations = _observations(database, sowing_id)
    sown_on = exact_sowing_date(sowing)
    seed_count = exact_seed_count(sowing)
    cumulative = 0
    first: date | None = None
    series: list[GerminationSeriesPoint] = []
    t50: Decimal | None = None
    previous_count = 0
    previous_day = Decimal(0)
    threshold = seed_count / 2 if seed_count is not None and seed_count > 0 else None
    for observation in observations:
        cumulative += observation.newly_germinated_count
        if first is None and observation.newly_germinated_count > 0:
            first = observation.observed_on
        elapsed = (observation.observed_on - sown_on).days if sown_on is not None else None
        series.append(
            GerminationSeriesPoint(
                observed_on=observation.observed_on,
                newly_germinated_count=observation.newly_germinated_count,
                cumulative_germinated_count=cumulative,
                days_since_sowing=elapsed if elapsed is not None and elapsed >= 0 else None,
            )
        )
        if (
            threshold is not None
            and elapsed is not None
            and elapsed >= 0
            and t50 is None
            and cumulative >= threshold
            and cumulative > previous_count
        ):
            # Linear interpolation from the prior observation, or sowing day/count 0.
            t50 = previous_day + (Decimal(elapsed) - previous_day) * (
                threshold - Decimal(previous_count)
            ) / Decimal(cumulative - previous_count)
        previous_count = cumulative
        if elapsed is not None and elapsed >= 0:
            previous_day = Decimal(elapsed)
    percentage = (
        Decimal(cumulative) / seed_count * 100
        if observations and seed_count is not None and seed_count > 0
        else None
    )
    return SowingGerminationDetail(
        sowing_id=sowing.id,
        sowing_date=_partial_date(sowing),
        quantity=_quantity(sowing),
        simple_germinated_count=sowing.germinated_count,
        observations=[
            GerminationObservationResponse.model_validate(item, from_attributes=True)
            for item in observations
        ],
        summary=GerminationSummary(
            observed_cumulative_count=cumulative,
            first_germination_on=first,
            days_to_first_germination=(first - sown_on).days
            if first and sown_on and first >= sown_on
            else None,
            last_observation_on=observations[-1].observed_on if observations else None,
            germination_percentage=percentage,
            cumulative_series=series,
            t50_days=t50,
        ),
    )
