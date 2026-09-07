from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from florabase.propagation.schemas import (
    SeedLotSowingTransitionResponse,
    SowingPlantGroupTransitionResponse,
    SowingPlantTransitionResponse,
)

ReversalReasonCode = Literal[
    "propagation_receipt_not_found",
    "receipt_relationship_mismatch",
    "receipt_already_reversed",
    "legacy_receipt_missing_result_snapshot",
    "result_lifecycle_changed",
    "result_structural_state_changed",
    "result_terminal_lifecycle",
    "source_lifecycle_changed",
    "source_quantity_changed",
    "source_structural_state_changed",
    "later_source_operation",
    "transfer_exists",
    "active_downstream_operation",
    "downstream_lineage",
    "produced_seed_lot_exists",
    "later_extraction_exists",
    "incompatible_result_history",
]


class ReversalReason(BaseModel):
    code: ReversalReasonCode
    message: str
    entity_type: Literal["seed_lot", "sowing", "plant", "plant_group"] | None = None
    entity_id: UUID | None = None


class PropagationReversalEligibility(BaseModel):
    status: Literal["safe", "confirmation_required", "blocked"]
    operation_receipt_id: UUID | None
    operation_status: Literal["applied", "reversed"] | None
    source_id: UUID | None
    source_type: Literal["seed_lot", "sowing"]
    reasons: list[ReversalReason]
    retained_observation_ids: list[UUID]


class PropagationReversalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirm_retained_observations: bool = False


class SowingCreationReversalResponse(SeedLotSowingTransitionResponse):
    operation_receipt_id: UUID
    operation_status: Literal["reversed"] = "reversed"


class PlantCreationReversalResponse(SowingPlantTransitionResponse):
    operation_receipt_id: UUID
    operation_status: Literal["reversed"] = "reversed"


class PlantGroupCreationReversalResponse(SowingPlantGroupTransitionResponse):
    operation_receipt_id: UUID
    operation_status: Literal["reversed"] = "reversed"
