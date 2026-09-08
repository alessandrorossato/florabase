import unicodedata
from datetime import datetime
from typing import TYPE_CHECKING, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from florabase.geographic_places.model import GeographicPlace


def _normalize_name(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("Name must not be blank")
    if any(unicodedata.category(character) == "Cc" for character in normalized):
        raise ValueError("Name must not contain control characters")
    return normalized


class GeographicPlaceWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(max_length=255)
    parent_id: UUID
    place_type: Literal["city_town", "locality", "other_named_area"] = "other_named_area"

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        return _normalize_name(value) if isinstance(value, str) else value


class GeographicPlaceCreate(GeographicPlaceWrite):
    pass


class GeographicPlaceUpdate(GeographicPlaceWrite):
    pass


class GeographicPlaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    parent_id: UUID | None
    display_path: str
    place_kind: Literal["canonical", "custom"]
    place_type: Literal["city_town", "locality", "other_named_area"] | None
    provenance_site_count: int = 0
    direct_usage_count: int = 0
    source_name: str | None
    source_version: str | None
    source_code_type: str | None
    source_code: str | None
    retired_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(
        cls,
        place: GeographicPlace,
        *,
        display_path: str,
        provenance_site_count: int = 0,
        direct_usage_count: int = 0,
    ) -> Self:
        return cls.model_validate(
            {
                **place.__dict__,
                "place_type": getattr(
                    place,
                    "place_type",
                    None if place.place_kind == "canonical" else "other_named_area",
                ),
                "display_path": display_path,
                "provenance_site_count": provenance_site_count,
                "direct_usage_count": direct_usage_count,
            }
        )
