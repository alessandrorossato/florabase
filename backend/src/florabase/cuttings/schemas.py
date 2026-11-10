from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from florabase.cuttings.model import (
    AttemptLifecycle,
    LotLifecycle,
    MaterialType,
    RootingStage,
    SourceKind,
)
from florabase.seed_lots.schemas import PartialDate, _notes, _single_line

Line = Annotated[
    str | None,
    Field(max_length=255),
    BeforeValidator(lambda value: _single_line(value) if isinstance(value, str) else value),
]
SetupText = Annotated[
    str | None,
    Field(max_length=500),
    BeforeValidator(lambda value: _single_line(value) if isinstance(value, str) else value),
]
Notes = Annotated[
    str | None,
    Field(max_length=20_000),
    BeforeValidator(lambda value: _notes(value) if isinstance(value, str) else value),
]
Count = Annotated[int, Field(strict=True, ge=0, le=2_147_483_647)]
Temperature = Annotated[Decimal, Field(ge=-50, le=70, decimal_places=2)]


class CuttingWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notes: Notes = None


class CuttingQuantity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Count
    is_approximate: bool


class PositiveCuttingQuantity(CuttingQuantity):
    value: Count = Field(gt=0)


class LotSource(CuttingWrite):
    botanical_identity_id: UUID | None = None
    label: Line = None
    material_type: MaterialType
    source_kind: SourceKind = "unknown"
    source_detail: Line = None
    mother_plant_id: UUID | None = None
    mother_plant_group_id: UUID | None = None
    supplier_id: UUID | None = None
    order_id: UUID | None = None
    material_provenance_place_id: UUID | None = None
    provenance_site_id: UUID | None = None
    location_id: UUID | None = None
    taken_on: PartialDate | None = None

    @model_validator(mode="after")
    def validate_source(self) -> Self:
        mothers = (self.mother_plant_id, self.mother_plant_group_id)
        external = (
            self.supplier_id,
            self.order_id,
            self.material_provenance_place_id,
            self.provenance_site_id,
        )
        if self.source_kind == "collection_produced":
            if all(mothers) or any(external):
                raise ValueError(
                    "Collection-produced cuttings allow one mother and no external origin"
                )
        elif any(mothers):
            raise ValueError("Only collection-produced cuttings can link a mother")
        if self.botanical_identity_id is None and not any(mothers):
            raise ValueError("Select a botanical identity or a mother specimen")
        if self.order_id is not None and self.source_kind != "purchased":
            raise ValueError("Only purchased cuttings can link an order")
        if self.source_detail is not None and self.source_kind != "other":
            raise ValueError("Source detail is only available for Other")
        return self


class VegetativeLotCreate(LotSource):
    initial_quantity: PositiveCuttingQuantity | None = None


class VegetativeLotUpdate(LotSource):
    expected_updated_at: datetime
    lifecycle: Literal["active", "exhausted", "discarded", "lost"]
    quantity: CuttingQuantity | None

    @model_validator(mode="after")
    def validate_remainder(self) -> Self:
        if (
            self.quantity is not None
            and self.quantity.value == 0
            and (self.quantity.is_approximate or self.lifecycle != "exhausted")
        ):
            raise ValueError("A zero remainder must be exact and exhausted")
        return self


class VegetativeLotResponse(LotSource):
    id: UUID
    botanical_identity_id: UUID
    initial_quantity: PositiveCuttingQuantity | None
    quantity: CuttingQuantity | None
    lifecycle: LotLifecycle
    created_at: datetime
    updated_at: datetime


class AttemptSetup(CuttingWrite):
    label: Line = None
    started_on: PartialDate | None = None
    quantity: PositiveCuttingQuantity | None = None
    location_id: UUID | None = None
    hormone_treatment: SetupText = None
    substrate: SetupText = None
    container: SetupText = None
    environment: SetupText = None
    temperature_min_c: Temperature | None = None
    temperature_max_c: Temperature | None = None

    @model_validator(mode="after")
    def validate_temperatures(self) -> Self:
        if (
            self.temperature_min_c is not None
            and self.temperature_max_c is not None
            and self.temperature_min_c > self.temperature_max_c
        ):
            raise ValueError("Maximum temperature must be at least the minimum")
        return self


def definitely_before(first: PartialDate, second: PartialDate) -> bool:
    return (first.year, first.month or 12, first.day or 31) < (
        second.year,
        second.month or 1,
        second.day or 1,
    )


class AttemptState(AttemptSetup):
    ended_on: PartialDate | None = None
    rooted_count: Count | None = None

    @model_validator(mode="after")
    def validate_outcome(self) -> Self:
        if self.started_on and self.ended_on and definitely_before(self.ended_on, self.started_on):
            raise ValueError("End date precedes start date")
        if (
            self.rooted_count is not None
            and self.quantity is not None
            and not self.quantity.is_approximate
            and self.rooted_count > self.quantity.value
        ):
            raise ValueError("Rooted count exceeds the exact starting count")
        return self


class PropagationAttemptUpdate(AttemptState):
    expected_updated_at: datetime
    lifecycle: Literal["active", "completed", "failed", "abandoned"]

    @model_validator(mode="after")
    def validate_failure(self) -> Self:
        if self.lifecycle == "failed" and self.rooted_count not in (None, 0):
            raise ValueError("A failed attempt cannot have surviving cuttings")
        return self


class PropagationAttemptResponse(AttemptState):
    id: UUID
    vegetative_lot_id: UUID
    attempt_kind: Literal["cutting"] = "cutting"
    lifecycle: AttemptLifecycle
    rooting_rate_percent: float | None
    created_at: datetime
    updated_at: datetime


class SourceAdjustment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["none", "partial", "use_all"]
    resulting_quantity: PositiveCuttingQuantity | None = None

    @model_validator(mode="after")
    def validate_remainder(self) -> Self:
        if self.resulting_quantity is not None and self.mode != "partial":
            raise ValueError("Only partial use can specify a remaining quantity")
        return self


class AttemptCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    propagation_attempt: AttemptSetup
    source_adjustment: SourceAdjustment


class FastCreate(AttemptCreate):
    vegetative_lot: VegetativeLotCreate


class AttemptTransitionResponse(BaseModel):
    vegetative_lot: VegetativeLotResponse
    propagation_attempt: PropagationAttemptResponse
    operation_receipt_id: UUID


class RootingObservationWrite(CuttingWrite):
    observed_on: PartialDate | None = None
    stage: RootingStage
    rooted_count: Count | None = None


class RootingObservationResponse(RootingObservationWrite):
    id: UUID
    propagation_attempt_id: UUID
    created_at: datetime
    updated_at: datetime


class EstablishPlant(CuttingWrite):
    label: Line = None
    collection_entry_date: PartialDate | None = None
    location_id: UUID | None = None
    resulting_attempt_lifecycle: Literal["active", "completed", "abandoned"] = "active"


class EstablishPlantGroup(EstablishPlant):
    quantity: PositiveCuttingQuantity | None = None


class VegetativeLotDetail(VegetativeLotResponse):
    attempts: list[PropagationAttemptResponse]


class PropagationAttemptDetail(PropagationAttemptResponse):
    vegetative_lot: VegetativeLotResponse
    observations: list[RootingObservationResponse]
    operation_receipt_id: UUID | None


class EstablishmentResponse(BaseModel):
    id: UUID
    kind: Literal["plant", "plant_group"]
    operation_receipt_id: UUID


class EstablishedCutting(BaseModel):
    id: UUID
    kind: Literal["plant", "plant_group"]
    label: str | None
    lifecycle: str
    quantity: CuttingQuantity | None
    operation_receipt_id: UUID | None


class CuttingPropagationSummary(BaseModel):
    attempt_id: UUID
    lifecycle: AttemptLifecycle
    rooted_count: int | None
    offspring: list[EstablishedCutting]
    exact_descendant_count: int
    approximate_plant_group_count: int
    unknown_plant_group_count: int
