from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from florabase.explore.schemas import CollectionIdentity
from florabase.taxonomy.source import WfoMetadata, WfoTaxon


class TaxonomyEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: WfoMetadata
    taxon: WfoTaxon
    classification: list[WfoTaxon]
    identity_updated_at: datetime


class TaxonomyLink(BaseModel):
    version: UUID
    evidence: TaxonomyEvidence
    confirmed_at: datetime
    stale: bool


class TaxonomyLinkWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_taxon_id: str = Field(pattern=r"^wfo-[0-9]{10}$")
    checksum: str = Field(min_length=64, max_length=64)
    expected_version: UUID | None
    identity_updated_at: datetime


class TaxonomyIdentity(CollectionIdentity):
    source_taxon_id: str | None = None
    classification_ids: list[str] = Field(default_factory=list)
    unresolved_reason: str | None = None
    synonym_of: str | None = None


class TaxonomyCounts(BaseModel):
    represented: int = 0
    living: int = 0
    current: int = 0
    historical: int = 0


class TaxonomyNode(BaseModel):
    taxon: WfoTaxon
    parent_id: str | None
    counts: TaxonomyCounts
    identity_ids: list[UUID]


class TaxonomyTree(BaseModel):
    source: WfoMetadata | None = None
    source_available: bool
    message: str | None = None
    identities: list[TaxonomyIdentity]
    nodes: list[TaxonomyNode]
    counts: TaxonomyCounts
    unresolved: int


class TaxonomyNodeDetail(BaseModel):
    node: TaxonomyNode
    represented_genera: list[WfoTaxon]
    identities: list[TaxonomyIdentity]


class TaxonomyRelated(BaseModel):
    identity: TaxonomyIdentity
    relation: Literal["Same source taxon", "Same genus", "Same family", "Same order"]


class IdentityTaxonomy(BaseModel):
    source_available: bool
    source: WfoMetadata | None = None
    message: str | None = None
    link: TaxonomyLink | None = None
    related: list[TaxonomyRelated] = Field(default_factory=list)
