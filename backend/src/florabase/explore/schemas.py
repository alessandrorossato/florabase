from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

RepresentationScope = Literal["all", "living", "current", "historical"]


class CollectionRecordCategory(StrEnum):
    SEED_LOT = "seed_lot"
    SOWING = "sowing"
    PLANT = "plant"
    PLANT_GROUP = "plant_group"
    STORED_MATERIAL = "stored_material"


class CollectionIdentity(BaseModel):
    id: UUID
    display_label: str
    scientific_name: str
    cultivar_name: str | None
    common_name: str | None
    representation: Literal["living", "current", "historical"]
    retained_records: int = Field(ge=1)
    current_records: int = Field(ge=0)
    living_records: int = Field(ge=0)
    matches_scope: bool


class RepresentedIdentity(CollectionIdentity):
    occurrence_eligibility: Literal["available", "not_linked", "incompatible"]
    external_taxon_id: str | None


class RepresentedIdentityPage(BaseModel):
    items: list[RepresentedIdentity]
    total: int
    occurrence_ready: int
    offset: int
    limit: int


class NativeRangeIdentity(CollectionIdentity):
    matches_filters: bool = True
    native_range_count: int = Field(ge=0)


class NativeRangeIdentityPage(BaseModel):
    items: list[NativeRangeIdentity]
    total: int
    offset: int
    limit: int


class RecordedRangePlace(BaseModel):
    id: UUID
    name: str
    display_path: str
    place_kind: Literal["canonical", "custom"]
    source_code_type: str | None
    source_code: str | None


class RecordedPlaceCoverage(RecordedRangePlace):
    identity_count: int = Field(ge=1)


class TerritoryCoverage(BaseModel):
    id: UUID
    name: str
    source_code: str
    identity_count: int = Field(ge=1)


class NativeRangeOverview(BaseModel):
    represented: int
    with_range: int
    without_range: int
    territories: list[TerritoryCoverage]
    places: list[RecordedPlaceCoverage]
    places_total: int
    offset: int
    limit: int


class SelectedNativeRanges(BaseModel):
    identity: NativeRangeIdentity
    ranges: list[RecordedRangePlace]
    territories: list[TerritoryCoverage]
    total: int
    offset: int
    limit: int


class SelectedTerritoryCoverage(TerritoryCoverage):
    identity_ids: list[UUID] = Field(max_length=20)


class NativeRangeSelection(BaseModel):
    identities: list[NativeRangeIdentity] = Field(max_length=20)
    missing_ids: list[UUID] = Field(max_length=20)
    territories: list[SelectedTerritoryCoverage]
