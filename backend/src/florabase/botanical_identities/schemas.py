import unicodedata
from datetime import datetime
from typing import TYPE_CHECKING, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from florabase.botanical_identities.model import BotanicalIdentity


def _collapse_whitespace(value: str) -> str:
    return " ".join(value.split())


def _contains_control_character(value: str) -> bool:
    return any(unicodedata.category(character) == "Cc" for character in value)


def _normalize_required(value: str) -> str:
    normalized = _collapse_whitespace(value)
    if not normalized:
        raise ValueError("Value must not be blank")
    if _contains_control_character(normalized):
        raise ValueError("Value must not contain control characters")
    return normalized


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _collapse_whitespace(value)
    if not normalized:
        return None
    if _contains_control_character(normalized):
        raise ValueError("Value must not contain control characters")
    return normalized


def _normalize_cultivar(value: str | None) -> str | None:
    normalized = _normalize_optional(value)
    if normalized is None or len(normalized) < 2:
        return normalized
    quote_pairs = {
        ("'", "'"),
        ('"', '"'),
        ("\u2018", "\u2019"),
        ("\u201c", "\u201d"),
    }
    if (normalized[0], normalized[-1]) in quote_pairs:
        return _normalize_optional(normalized[1:-1])
    return normalized


class BotanicalIdentityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scientific_name: str = Field(max_length=255)
    cultivar_name: str | None = Field(default=None, max_length=120)
    common_name: str | None = Field(default=None, max_length=160)

    @field_validator("scientific_name", mode="before")
    @classmethod
    def normalize_scientific_name(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return _normalize_required(value)

    @field_validator("cultivar_name", mode="before")
    @classmethod
    def normalize_cultivar_name(cls, value: object) -> object:
        if value is not None and not isinstance(value, str):
            return value
        return _normalize_cultivar(value)

    @field_validator("common_name", mode="before")
    @classmethod
    def normalize_common_name(cls, value: object) -> object:
        if value is not None and not isinstance(value, str):
            return value
        return _normalize_optional(value)


class BotanicalIdentityUpdate(BotanicalIdentityCreate):
    pass


class IdentityCollectionCounts(BaseModel):
    """Active collection records, never quantities or inferred lineage."""

    seed_lots: int = Field(ge=0)
    sowings: int = Field(ge=0)
    plants: int = Field(ge=0)
    plant_groups: int = Field(ge=0)
    vegetative_lots: int = Field(default=0, ge=0)
    propagation_attempts: int = Field(default=0, ge=0)


class BotanicalIdentityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scientific_name: str
    cultivar_name: str | None
    common_name: str | None
    created_at: datetime
    updated_at: datetime
    display_label: str
    merged_into_id: UUID | None = None
    merged_at: datetime | None = None
    compact_cover_kind: Literal["local", "external"] | None = None
    compact_external_cover_url: str | None = None

    collection_counts: IdentityCollectionCounts | None = None

    @classmethod
    def from_model(
        cls,
        botanical_identity: BotanicalIdentity,
        *,
        compact_cover_kind: Literal["local", "external"] | None = None,
        compact_external_cover_url: str | None = None,
        collection_counts: IdentityCollectionCounts | None = None,
    ) -> Self:
        display_label = format_identity_display_label(
            botanical_identity.scientific_name,
            botanical_identity.cultivar_name,
        )
        return cls.model_validate(
            {
                "id": botanical_identity.id,
                "scientific_name": botanical_identity.scientific_name,
                "cultivar_name": botanical_identity.cultivar_name,
                "common_name": botanical_identity.common_name,
                "created_at": botanical_identity.created_at,
                "updated_at": botanical_identity.updated_at,
                "display_label": display_label,
                "merged_into_id": getattr(botanical_identity, "merged_into_id", None),
                "merged_at": getattr(botanical_identity, "merged_at", None),
                "compact_cover_kind": compact_cover_kind,
                "compact_external_cover_url": compact_external_cover_url,
                "collection_counts": collection_counts,
            }
        )


def format_identity_display_label(scientific_name: str, cultivar_name: str | None) -> str:
    if cultivar_name is not None:
        return f"{scientific_name} \u2018{cultivar_name}\u2019"
    return scientific_name


HistoricalNameStatusKind = Literal[
    "initial_recorded",
    "former_accepted",
    "merged_duplicate",
    "source_synonym",
    "operator_synonym",
]
ReconciliationSourceProvider = Literal["wfo", "wcvp", "gbif", "operator"]
AdvisorySourceProvider = Literal["wfo", "wcvp", "gbif"]
ReconciliationConflictKind = Literal[
    "wcvp_version_conflict",
    "cross_source_conflict",
    "duplicate_identity_collision",
]


class IdentityHistoricalNameResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    scientific_name: str
    cultivar_name: str | None = None
    common_name: str | None = None
    display_label: str
    authorship: str | None = None
    status_kind: HistoricalNameStatusKind
    source_provider: ReconciliationSourceProvider
    source_version: str | None = None
    source_taxon_id: str | None = None
    accepted_source_taxon_id: str | None = None
    origin_identity_id: UUID | None = None
    effective_from: datetime
    superseded_at: datetime | None = None


class CollidingIdentitySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    scientific_name: str
    cultivar_name: str | None = None
    common_name: str | None = None
    display_label: str
    updated_at: datetime
    collection_counts: IdentityCollectionCounts
    has_conflicting_profile_fields: bool = False
    conflicting_profile_fields: list[str] = Field(default_factory=list)


class AcceptedNameSuggestionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suggestion_id: str
    source_provider: AdvisorySourceProvider
    source_label: str
    source_version: str | None = None
    source_checksum: str | None = None
    link_version: UUID | None = None
    matched_taxon_id: str
    matched_scientific_name: str
    matched_authorship: str | None = None
    matched_status: str
    accepted_taxon_id: str
    accepted_scientific_name: str
    accepted_authorship: str | None = None
    accepted_rank: str | None = None
    stale: bool = False
    advisory_note: str | None = None
    colliding_identity: CollidingIdentitySummary | None = None


class SourceTaxonomicAssessmentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_provider: AdvisorySourceProvider
    source_label: str
    source_version: str | None = None
    source_checksum: str | None = None
    linked: bool
    link_version: UUID | None = None
    stale: bool = False
    taxon_id: str | None = None
    scientific_name: str | None = None
    authorship: str | None = None
    status: str | None = None
    accepted_taxon_id: str | None = None
    accepted_scientific_name: str | None = None
    accepted_authorship: str | None = None
    message: str | None = None


class ReconciliationConflictResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ReconciliationConflictKind
    message: str
    sources: list[str]
    colliding_identity_id: UUID | None = None


class IdentityReconciliationEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    kind: Literal["accepted_name_correction", "duplicate_identity_merge"]
    previous_scientific_name: str
    previous_cultivar_name: str | None = None
    previous_common_name: str | None = None
    applied_scientific_name: str
    applied_cultivar_name: str | None = None
    applied_common_name: str | None = None
    source_provider: ReconciliationSourceProvider
    duplicate_identity_id: UUID | None = None
    evidence: dict[str, object]
    created_at: datetime


class IdentityReconciliationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identity: BotanicalIdentityResponse
    original_scientific_name: str
    original_cultivar_name: str | None = None
    original_common_name: str | None = None
    original_display_label: str
    former_names: list[IdentityHistoricalNameResponse]
    suggestions: list[AcceptedNameSuggestionResponse]
    source_assessments: list[SourceTaxonomicAssessmentResponse]
    conflicts: list[ReconciliationConflictResponse]
    has_source_conflict: bool
    reconciliations: list[IdentityReconciliationEventResponse]


class AcceptedNameCorrectionWrite(BotanicalIdentityCreate):
    model_config = ConfigDict(extra="forbid")

    identity_updated_at: datetime
    source_provider: ReconciliationSourceProvider = "operator"
    source_version: str | None = Field(default=None, max_length=64)
    source_checksum: str | None = Field(default=None, max_length=128)
    link_version: UUID | None = None
    matched_taxon_id: str | None = Field(default=None, max_length=255)
    accepted_taxon_id: str | None = Field(default=None, max_length=255)
    accepted_authorship: str | None = Field(default=None, max_length=255)
    acknowledge_conflict: bool = False
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator(
        "source_version",
        "source_checksum",
        "matched_taxon_id",
        "accepted_taxon_id",
        "accepted_authorship",
        "notes",
        mode="before",
    )
    @classmethod
    def normalize_optional_fields(cls, value: object) -> object:
        if value is not None and not isinstance(value, str):
            return value
        return _normalize_optional(value)


class DuplicateIdentityMergeWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    survivor_identity_id: UUID
    duplicate_updated_at: datetime
    survivor_updated_at: datetime
    profile_resolution: Literal["fail_on_conflict", "keep_survivor"] = "fail_on_conflict"
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value: object) -> object:
        if value is not None and not isinstance(value, str):
            return value
        return _normalize_optional(value)
