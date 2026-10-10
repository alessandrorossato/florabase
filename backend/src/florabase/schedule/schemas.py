import re
from datetime import date, datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator, model_validator

from florabase.events.schemas import _notes, _single_line

ActivityKind = Literal[
    "repot", "water", "fertilize", "move", "check_germination", "inspect", "harvest", "follow_up"
]
ScheduleStatus = Literal["planned", "completed", "cancelled"]
TargetKind = Literal["botanical_identity", "seed_lot", "sowing", "plant", "plant_group", "location"]
DateWindow = Literal["all", "overdue", "today", "next_seven_days", "later"]


def _calendar_day(value: object) -> object:
    if type(value) is date or (
        isinstance(value, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value)
    ):
        return value
    raise ValueError("Use a complete calendar date in YYYY-MM-DD format, without a time")


CalendarDay = Annotated[date, BeforeValidator(_calendar_day)]


class ScheduleTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: TargetKind
    id: UUID


class ScheduleTargetResponse(ScheduleTarget):
    label: str
    lifecycle: str | None


class ScheduleWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    activity_kind: ActivityKind
    title: str = Field(min_length=1, max_length=255)
    due_on: CalendarDay
    target: ScheduleTarget | None = None
    notes: str | None = Field(default=None, max_length=20000)

    @field_validator("title", mode="before")
    @classmethod
    def title_text(cls, value: object) -> object:
        return _single_line(value) if isinstance(value, str) else value

    @field_validator("notes", mode="before")
    @classmethod
    def notes_text(cls, value: object) -> object:
        return _notes(value) if isinstance(value, str) else value


class ScheduleUpdate(ScheduleWrite):
    expected_version: int = Field(ge=1)


class ScheduleVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)


class ScheduleEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["observation", "repotting", "movement", "other"]
    occurred_on: CalendarDay
    destination_location_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=20000)

    @field_validator("notes", mode="before")
    @classmethod
    def notes_text(cls, value: object) -> object:
        return _notes(value) if isinstance(value, str) else value

    @model_validator(mode="after")
    def destination(self) -> Self:
        if (self.kind == "movement") != (self.destination_location_id is not None):
            raise ValueError("Only Movement requires a destination Location")
        return self


class ScheduleComplete(ScheduleVersion):
    event: ScheduleEvent | None = None


class ScheduleResponse(BaseModel):
    id: UUID
    activity_kind: ActivityKind
    title: str
    due_on: date
    target: ScheduleTargetResponse | None
    notes: str | None
    status: ScheduleStatus
    version: int
    overdue: bool
    linked_event_id: UUID | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    cancelled_at: datetime | None


class SchedulePage(BaseModel):
    items: list[ScheduleResponse]
    total: int
    offset: int
    limit: int
    today: date
    overdue_count: int
    today_count: int


class ScheduleTargetPage(BaseModel):
    items: list[ScheduleTargetResponse]
    total: int
