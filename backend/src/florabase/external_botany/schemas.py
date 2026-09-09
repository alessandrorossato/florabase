from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator

from florabase.external_botany.model import ExternalTaxonLink


class TaxonCandidate(BaseModel):
    external_id: str
    scientific_name: str
    canonical_name: str | None = None
    authorship: str | None = None
    rank: str | None = None
    taxonomic_status: str | None = None
    accepted_external_id: str | None = None
    accepted_name: str | None = None
    kingdom: str | None = None
    phylum: str | None = None
    class_name: str | None = None
    order_name: str | None = None
    family: str | None = None
    genus: str | None = None
    match_type: str | None = None
    confidence: int | None = None
    issues: list[str] = Field(default_factory=list)


class TaxonSearchResponse(BaseModel):
    provider: str
    query: str
    fetched_at: datetime
    from_cache: bool
    stale: bool
    provider_error: str | None = None
    candidates: list[TaxonCandidate]


class ExternalTaxonLinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    external_id: str = Field(min_length=1, max_length=255)
    scientific_name: str = Field(min_length=1, max_length=255)

    @field_validator("scientific_name")
    @classmethod
    def normalize_scientific_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Scientific name cannot be blank")
        return normalized


class ExternalTaxonLinkResponse(BaseModel):
    provider: str
    provider_display_name: str
    external_id: str
    provider_url: str
    scientific_name: str
    canonical_name: str | None
    authorship: str | None
    rank: str | None
    taxonomic_status: str | None
    accepted_external_id: str | None
    accepted_name: str | None
    kingdom: str | None
    phylum: str | None
    class_name: str | None
    order_name: str | None
    family: str | None
    genus: str | None
    linked_at: datetime
    last_refreshed_at: datetime
    last_refresh_attempt_at: datetime
    refresh_error: str | None
    stale: bool

    @classmethod
    def from_model(cls, link: ExternalTaxonLink, *, stale: bool) -> Self:
        values = {column.name: getattr(link, column.name) for column in link.__table__.columns}
        values.update(
            provider_display_name="GBIF" if link.provider == "gbif" else link.provider,
            provider_url=f"https://www.gbif.org/species/{link.external_id}",
            stale=stale,
        )
        return cls.model_validate(values)
