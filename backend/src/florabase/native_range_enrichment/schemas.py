from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from florabase.native_range_enrichment.source import SourceMetadata, Taxon


class WcvpLinkWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    external_id: str = Field(min_length=1, max_length=255)
    checksum: str = Field(pattern=r"^[0-9a-f]{64}$")


class WcvpLinkResponse(BaseModel):
    version: UUID
    taxon: Taxon
    source: SourceMetadata
    confirmed_at: datetime
    stale: bool


class SourceStatus(BaseModel):
    available: bool
    source: SourceMetadata | None = None
    message: str | None = None
    link: WcvpLinkResponse | None = None


class RangeChoice(BaseModel):
    place_id: UUID
    name: str
    path: str
    code: str | None
    change: Literal["ADD", "KEEP", "CURRENT-ONLY"]
    assertions: list[str] = Field(default_factory=list)


class SourceAssertion(BaseModel):
    assertion_id: str
    original: dict[str, str]
    status: Literal["native", "introduced", "qualified"]
    mapping: Literal["equivalent", "unresolved", "partial", "unsupported_split"]
    note: str
    place_ids: list[UUID] = Field(default_factory=list)


class ProposalEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format_version: Literal[1] = 1
    link_version: UUID
    identity_snapshot: dict[str, object]
    destination_version: int
    current_ids: list[UUID]
    source: SourceMetadata
    taxon: Taxon
    retrieved_at: datetime
    crosswalk_version: str
    choices: list[RangeChoice]
    assertions: list[SourceAssertion]


class ApplicationResponse(BaseModel):
    proposal_id: UUID
    applied_at: datetime
    added: list[UUID]
    kept: list[UUID]
    destination_version: int


class ProposalResponse(ProposalEvidence):
    id: UUID
    created_at: datetime
    applied_at: datetime | None = None
    application: ApplicationResponse | None = None


class ApplyWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    selected_place_ids: list[UUID] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_selection(self) -> ApplyWrite:
        if len(set(self.selected_place_ids)) != len(self.selected_place_ids):
            raise ValueError("Select each proposed place only once")
        return self
