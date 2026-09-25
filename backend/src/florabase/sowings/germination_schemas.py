from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from florabase.seed_lots.schemas import PartialDate
from florabase.sowings.schemas import SignedDecimalString, SowingQuantity


class GerminationObservationWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observed_on: date
    newly_germinated_count: int = Field(ge=0)


class GerminationObservationResponse(GerminationObservationWrite):
    id: UUID
    created_at: datetime
    updated_at: datetime


class GerminationSeriesPoint(BaseModel):
    observed_on: date
    newly_germinated_count: int
    cumulative_germinated_count: int
    days_since_sowing: int | None


class GerminationSummary(BaseModel):
    observed_cumulative_count: int
    first_germination_on: date | None
    days_to_first_germination: int | None
    last_observation_on: date | None
    germination_percentage: SignedDecimalString | None
    cumulative_series: list[GerminationSeriesPoint]
    t50_days: SignedDecimalString | None


class SowingGerminationDetail(BaseModel):
    sowing_id: UUID
    sowing_date: PartialDate | None
    quantity: SowingQuantity | None
    simple_germinated_count: int | None
    observations: list[GerminationObservationResponse]
    summary: GerminationSummary
