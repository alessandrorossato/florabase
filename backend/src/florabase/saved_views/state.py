"""Explicit v1 contracts for existing directory controls, never component snapshots."""

from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StrictBool, field_validator

from florabase.harvests.model import MaterialKind
from florabase.history.schemas import HistoryCategory, HistorySubjectKind
from florabase.locations.schemas import LocationUsageScope
from florabase.media.schemas import MediaTargetFilter
from florabase.search.state import SearchViewState


class SavedViewSurface(StrEnum):
    GLOBAL_SEARCH = "global_search"
    SEED_LOTS = "seed_lots"
    SOWINGS = "sowings"
    PLANTS = "plants"
    HARVESTS = "harvests"
    STORED_MATERIAL = "stored_material"
    EVENTS = "events"
    HISTORY = "history"
    MEDIA = "media"
    BOTANICAL_IDENTITIES = "botanical_identities"
    SUPPLIERS = "suppliers"
    LOCATIONS = "locations"
    GEOGRAPHY = "geography"
    PROVENANCE_MAP = "provenance_map"


class TextState(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    q: str = Field(default="", max_length=200)


class SeedLotState(TextState):
    lifecycle: Literal["active", "history", "all"] = "active"


class SowingState(TextState):
    lifecycle: Literal["active", "completed", "all"] = "active"


class PlantState(SeedLotState):
    type: Literal["all", "plant", "group"] = "all"


class HarvestState(TextState):
    material: MaterialKind | None = None
    source_type: Literal["plant", "plant_group"] | None = None
    identity_id: UUID | None = None


class StoredMaterialState(TextState):
    state: Literal["active", "depleted", "all"] = "active"
    material: MaterialKind | None = None
    identity_id: UUID | None = None
    location_id: UUID | None = None


class EventState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: Literal["all", "observations", "cultivation", "status"] = "all"


class HistoryState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: list[HistoryCategory] = Field(default_factory=list, max_length=5)
    subject_kind: HistorySubjectKind | None = None
    year: int | None = Field(default=None, ge=1, le=9999, strict=True)

    @field_validator("category")
    @classmethod
    def ordered_categories(cls, value: list[HistoryCategory]) -> list[HistoryCategory]:
        return [item for item in HistoryCategory if item in value]


class MediaState(TextState):
    kind: Literal["local", "external"] | None = None
    association: Literal["all", "linked", "unlinked"] = "all"
    target: MediaTargetFilter | None = None


class LocationState(TextState):
    scope: LocationUsageScope | Literal["all"] = "all"


class GeographyState(TextState):
    mode: Literal["places", "sites", "map"] = "places"


class ProvenanceMapState(TextState):
    seed_lots: StrictBool = True
    plants: StrictBool = True


STATE_MODELS: dict[SavedViewSurface, type[BaseModel]] = {
    SavedViewSurface.GLOBAL_SEARCH: SearchViewState,
    SavedViewSurface.SEED_LOTS: SeedLotState,
    SavedViewSurface.SOWINGS: SowingState,
    SavedViewSurface.PLANTS: PlantState,
    SavedViewSurface.HARVESTS: HarvestState,
    SavedViewSurface.STORED_MATERIAL: StoredMaterialState,
    SavedViewSurface.EVENTS: EventState,
    SavedViewSurface.HISTORY: HistoryState,
    SavedViewSurface.MEDIA: MediaState,
    SavedViewSurface.BOTANICAL_IDENTITIES: TextState,
    SavedViewSurface.SUPPLIERS: TextState,
    SavedViewSurface.LOCATIONS: LocationState,
    SavedViewSurface.GEOGRAPHY: GeographyState,
    SavedViewSurface.PROVENANCE_MAP: ProvenanceMapState,
}


def canonical_state(
    surface: SavedViewSurface, version: int, state: dict[str, JsonValue]
) -> dict[str, JsonValue]:
    if version != 1:
        raise ValueError("Unsupported Saved View state version")
    parsed = STATE_MODELS[surface].model_validate(state)
    normalized: dict[str, JsonValue] = parsed.model_dump(
        mode="json", exclude_defaults=True, exclude_none=True
    )
    if not normalized:
        raise ValueError("Choose a search, filter or view mode before saving")
    return normalized
