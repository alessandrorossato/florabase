from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

BulkKind = Literal["seed_lot", "sowing", "plant", "plant_group", "harvest_inventory"]


class BulkReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: BulkKind
    id: UUID


class BulkPrecondition(BulkReference):
    expected_updated_at: AwareDatetime


class BulkLocationPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    records: list[BulkReference] = Field(min_length=1, max_length=100)
    target_location_id: UUID

    @model_validator(mode="after")
    def unique_references(self) -> Self:
        if len({(row.kind, row.id) for row in self.records}) != len(self.records):
            raise ValueError("duplicate_reference: select each typed record only once")
        return self


class BulkLocationApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    records: list[BulkPrecondition] = Field(min_length=1, max_length=100)
    target_location_id: UUID
    expected_target_updated_at: AwareDatetime

    @model_validator(mode="after")
    def unique_references(self) -> Self:
        if len({(row.kind, row.id) for row in self.records}) != len(self.records):
            raise ValueError("duplicate_reference: select each typed record only once")
        return self


class BulkLocationRow(BulkReference):
    label: str
    current_location_id: UUID | None
    current_location: str | None
    updated_at: datetime | None
    status: Literal["move", "unchanged", "conflict"]
    code: str | None = None
    message: str | None = None


class BulkLocationPreview(BaseModel):
    target_location_id: UUID
    target_location: str
    target_updated_at: datetime
    selected_count: int
    move_count: int
    unchanged_count: int
    can_apply: bool
    rows: list[BulkLocationRow]


class BulkLocationResult(BaseModel):
    moved_count: int
    unchanged_count: int
