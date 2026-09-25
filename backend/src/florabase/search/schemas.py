from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class SearchKind(StrEnum):
    SEED_LOT = "seed_lot"
    SOWING = "sowing"
    PLANT = "plant"
    PLANT_GROUP = "plant_group"
    EVENT = "event"
    BOTANICAL_IDENTITY = "botanical_identity"
    BOTANICAL_PROFILE = "botanical_profile"
    SUPPLIER = "supplier"
    LOCATION = "location"
    GEOGRAPHIC_PLACE = "geographic_place"
    PROVENANCE_SITE = "provenance_site"


class SearchHit(BaseModel):
    kind: SearchKind
    id: UUID
    title: str
    context: str
    href: str


class SearchGroup(BaseModel):
    kind: SearchKind
    total: int
    items: list[SearchHit]


class SearchResponse(BaseModel):
    query: str
    total: int
    offset: int
    limit: int
    groups: list[SearchGroup]
