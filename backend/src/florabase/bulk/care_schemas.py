"""Pydantic schemas for bulk care logging (CARE-BULK-001)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from florabase.events.schemas import _notes
from florabase.seed_lots.schemas import PartialDate

MAX_BULK_CARE_TARGETS = 500

BulkCareTargetKind = Literal["plant", "plant_group"]
BulkCareEventKind = Literal[
    "watering",
    "feeding",
    "treatment",
    "repotting",
    "pruning",
    "observation",
    "other",
]
BulkCareRowStatus = Literal["log", "skipped"]


class BulkCareRecordReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: BulkCareTargetKind
    id: UUID


class BulkCareRecordTargets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    records: list[BulkCareRecordReference] = Field(min_length=1, max_length=MAX_BULK_CARE_TARGETS)

    @field_validator("records")
    @classmethod
    def unique_records(cls, value: list[BulkCareRecordReference]) -> list[BulkCareRecordReference]:
        seen: set[tuple[BulkCareTargetKind, UUID]] = set()
        for row in value:
            key = (row.kind, row.id)
            if key in seen:
                raise ValueError("Duplicate record selected")
            seen.add(key)
        return value


class BulkCareLocationTargets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    location_id: UUID
    include_sublocations: bool = True


BulkCareTargets = BulkCareRecordTargets | BulkCareLocationTargets


class BulkCarePreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    targets: BulkCareTargets
    kind: BulkCareEventKind
    occurred_on: PartialDate | None = None
    notes: str | None = Field(default=None, max_length=20_000)

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value: object) -> object:
        if value is not None and not isinstance(value, str):
            return value
        return _notes(value)


class BulkCareApplyRequest(BulkCarePreviewRequest):
    target_signature: str = Field(min_length=16, max_length=128)


class BulkCareRow(BaseModel):
    kind: BulkCareTargetKind
    id: UUID
    label: str
    scientific_name: str | None = None
    location: str | None = None
    lifecycle: str | None = None
    status: BulkCareRowStatus
    reason: str | None = None


class BulkCarePreviewResponse(BaseModel):
    kind: BulkCareEventKind
    occurred_on: PartialDate | None
    notes: str | None
    location_label: str | None = None
    sublocation_count: int = 0
    total_count: int
    log_count: int
    plant_count: int
    plant_group_count: int
    skipped_count: int
    can_apply: bool
    target_signature: str
    rows: list[BulkCareRow]


class BulkCareApplyResponse(BaseModel):
    batch_id: UUID
    kind: BulkCareEventKind
    logged_count: int
    plant_count: int
    plant_group_count: int
    skipped_count: int


class BulkCareKeptEvent(BaseModel):
    id: UUID
    target_kind: BulkCareTargetKind
    target_id: UUID
    label: str
    reason: str


class BulkCareUndoResponse(BaseModel):
    batch_id: UUID
    deleted_count: int
    kept_count: int
    kept: list[BulkCareKeptEvent]
