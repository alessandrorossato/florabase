"""Canonical reusable SEARCH-002 state; query execution stays in the search capability."""

from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

from florabase.events.model import EventKind
from florabase.search.schemas import SearchKind
from florabase.search.service import SearchFilters, validate_filters


class SearchViewState(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    q: str = Field(default="", max_length=120)
    kind: list[SearchKind] = Field(default_factory=list, max_length=13)
    identity_id: UUID | None = None
    lifecycle: str = Field(default="", max_length=32)
    location_id: UUID | None = None
    supplier_id: UUID | None = None
    provenance_place_id: UUID | None = None
    provenance_site_id: UUID | None = None
    event_kind: EventKind | None = None
    year: StrictInt | None = Field(default=None, ge=1, le=9999)

    @field_validator("kind")
    @classmethod
    def normalize_kinds(cls, value: list[SearchKind]) -> list[SearchKind]:
        return [kind for kind in SearchKind if kind in value]

    @model_validator(mode="after")
    def valid_combination(self) -> Self:
        validate_filters(
            SearchFilters(
                kinds=tuple(self.kind),
                identity_id=self.identity_id,
                lifecycle=self.lifecycle,
                location_id=self.location_id,
                supplier_id=self.supplier_id,
                provenance_place_id=self.provenance_place_id,
                provenance_site_id=self.provenance_site_id,
                event_kind=self.event_kind,
                year=self.year,
            )
        )
        return self
