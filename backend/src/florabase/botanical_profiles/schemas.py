import unicodedata
from datetime import datetime
from typing import TYPE_CHECKING, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from florabase.botanical_profiles.model import MAX_PROFILE_SECTION_LENGTH, PROFILE_FIELDS

if TYPE_CHECKING:
    from florabase.botanical_profiles.model import BotanicalProfile, BotanicalProfileNativeRange
    from florabase.geographic_places.model import GeographicPlace


def _normalize_profile_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return None
    if any(
        unicodedata.category(character) == "Cc" and character not in {"\n", "\t"}
        for character in normalized
    ):
        raise ValueError("Value must not contain unsupported control characters")
    return normalized


class BotanicalProfilePut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str | None = Field(default=None, max_length=MAX_PROFILE_SECTION_LENGTH)
    origin_distribution: str | None = Field(default=None, max_length=MAX_PROFILE_SECTION_LENGTH)
    cultivation: str | None = Field(default=None, max_length=MAX_PROFILE_SECTION_LENGTH)
    uses: str | None = Field(default=None, max_length=MAX_PROFILE_SECTION_LENGTH)
    warnings: str | None = Field(default=None, max_length=MAX_PROFILE_SECTION_LENGTH)

    @field_validator(
        "description",
        "origin_distribution",
        "cultivation",
        "uses",
        "warnings",
        mode="before",
    )
    @classmethod
    def normalize_section(cls, value: object) -> object:
        if value is not None and not isinstance(value, str):
            return value
        return _normalize_profile_text(value)

    @property
    def is_empty(self) -> bool:
        return all(getattr(self, field) is None for field in PROFILE_FIELDS)


class BotanicalProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    botanical_identity_id: UUID
    description: str | None
    origin_distribution: str | None
    cultivation: str | None
    uses: str | None
    warnings: str | None

    @classmethod
    def from_model(cls, profile: BotanicalProfile) -> Self:
        return cls.model_validate(profile)


class BotanicalNativeRangeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    geographic_place_id: UUID


class BotanicalNativeRangeResponse(BaseModel):
    botanical_profile_id: UUID
    geographic_place_id: UUID
    geographic_place_name: str
    geographic_place_path: str
    created_at: datetime

    @classmethod
    def from_models(
        cls,
        native_range: BotanicalProfileNativeRange,
        place: GeographicPlace,
        *,
        geographic_place_path: str,
    ) -> Self:
        return cls(
            botanical_profile_id=native_range.botanical_profile_id,
            geographic_place_id=native_range.geographic_place_id,
            geographic_place_name=place.name,
            geographic_place_path=geographic_place_path,
            created_at=native_range.created_at,
        )
