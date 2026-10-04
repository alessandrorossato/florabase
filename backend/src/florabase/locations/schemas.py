import unicodedata
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from florabase.locations.model import Location


def _normalize_name(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("Name must not be blank")
    if any(unicodedata.category(character) == "Cc" for character in normalized):
        raise ValueError("Name must not contain control characters")
    return normalized


class LocationUsageScope(StrEnum):
    PLANTS = "plants"
    SOWINGS = "sowings"
    SEED_LOTS = "seed_lots"
    HARVEST_INVENTORY = "harvest_inventory"


class LocationWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(max_length=255)
    parent_id: UUID | None = None
    usage_scopes: set[LocationUsageScope] = Field(
        default_factory=lambda: set(LocationUsageScope), min_length=1
    )

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        return _normalize_name(value) if isinstance(value, str) else value


class LocationCreate(LocationWrite):
    pass


class LocationUpdate(LocationWrite):
    pass


class LocationUsageCount(BaseModel):
    active: int = 0
    total: int = 0


class LocationUsageSummary(BaseModel):
    harvest_inventory: LocationUsageCount = Field(default_factory=LocationUsageCount)
    plants: LocationUsageCount = Field(default_factory=LocationUsageCount)
    sowings: LocationUsageCount = Field(default_factory=LocationUsageCount)
    seed_lots: LocationUsageCount = Field(default_factory=LocationUsageCount)


class LocationCollectionUsage(LocationUsageSummary):
    """Per-record counts; plants here excludes PlantGroups, unlike legacy usage."""

    plant_groups: LocationUsageCount = Field(default_factory=LocationUsageCount)


class LocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    parent_id: UUID | None
    usage_scopes: list[LocationUsageScope]
    usage: LocationUsageSummary = Field(
        description="Legacy direct usage; plants combines Plant and PlantGroup records."
    )
    direct_usage: LocationCollectionUsage = Field(
        description="Records whose current location_id is exactly this Location, by record type."
    )
    usage_including_descendants: LocationCollectionUsage = Field(
        description="Current assignments to this Location or any descendant, counted once."
    )
    display_path: str
    retired_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(
        cls,
        location: Location,
        *,
        display_path: str,
        usage: LocationUsageSummary | None = None,
        direct_usage: LocationCollectionUsage | None = None,
        usage_including_descendants: LocationCollectionUsage | None = None,
    ) -> Self:
        scopes = [
            scope
            for scope, supported in (
                (LocationUsageScope.PLANTS, location.supports_plants),
                (LocationUsageScope.SOWINGS, location.supports_sowings),
                (LocationUsageScope.SEED_LOTS, location.supports_seed_lots),
                (LocationUsageScope.HARVEST_INVENTORY, location.supports_harvest_inventory),
            )
            if supported
        ]
        return cls.model_validate(
            {
                **location.__dict__,
                "display_path": display_path,
                "usage_scopes": scopes,
                "usage": usage or LocationUsageSummary(),
                "direct_usage": direct_usage or LocationCollectionUsage(),
                "usage_including_descendants": (
                    usage_including_descendants or LocationCollectionUsage()
                ),
            }
        )
