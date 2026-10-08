from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

RepresentationScope = Literal["all", "living", "current", "historical"]


class RepresentedIdentity(BaseModel):
    id: UUID
    display_label: str
    scientific_name: str
    cultivar_name: str | None
    common_name: str | None
    representation: Literal["living", "current", "historical"]
    retained_records: int = Field(ge=1)
    current_records: int = Field(ge=0)
    living_records: int = Field(ge=0)
    occurrence_eligibility: Literal["available", "not_linked", "incompatible"]
    external_taxon_id: str | None
    matches_scope: bool


class RepresentedIdentityPage(BaseModel):
    items: list[RepresentedIdentity]
    total: int
    occurrence_ready: int
    offset: int
    limit: int
