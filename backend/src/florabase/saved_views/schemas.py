import unicodedata
from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StrictInt,
    field_validator,
    model_validator,
)

from florabase.saved_views.model import SavedView
from florabase.saved_views.state import SavedViewSurface, canonical_state


class NameWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("name", mode="before", check_fields=False)
    @classmethod
    def normalize_name(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        value = value.strip()
        if not value or any(unicodedata.category(c) == "Cc" for c in value):
            raise ValueError("Name must not be blank or contain control characters")
        return value


class SavedViewCreate(NameWrite):
    name: str = Field(min_length=1, max_length=120)
    surface: SavedViewSurface
    state_version: StrictInt
    state: dict[str, JsonValue]

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        self.state = canonical_state(self.surface, self.state_version, self.state)
        return self


class SavedViewUpdate(NameWrite):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    state_version: StrictInt | None = None
    state: dict[str, JsonValue] | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Choose a name or current view to update")
        if any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError("Updated fields cannot be null")
        if ("state" in self.model_fields_set) != ("state_version" in self.model_fields_set):
            raise ValueError("State and state_version must be replaced together")
        return self


class SavedViewResponse(BaseModel):
    id: UUID
    name: str
    surface: SavedViewSurface
    state_version: int
    state: dict[str, JsonValue]
    created_at: datetime
    updated_at: datetime
    compatibility: Literal["supported", "unsupported_version", "invalid_state"]

    @classmethod
    def from_model(cls, record: SavedView) -> Self:
        surface = SavedViewSurface(record.surface)
        compatibility: Literal["supported", "unsupported_version", "invalid_state"] = "supported"
        if record.state_version != 1:
            compatibility = "unsupported_version"
        else:
            try:
                canonical_state(surface, record.state_version, record.state)
            except ValueError:
                compatibility = "invalid_state"
        return cls(
            id=record.id,
            name=record.name,
            surface=surface,
            state_version=record.state_version,
            state=record.state,
            created_at=record.created_at,
            updated_at=record.updated_at,
            compatibility=compatibility,
        )
