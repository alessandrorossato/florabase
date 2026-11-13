"""Read-only schemas for deterministic local botanical reference matching (Slice 1A)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ConfidenceTier = Literal["exact", "high", "medium", "low", "none"]
MatchProviderId = Literal["wfo", "wcvp_v16", "wcvp_v15"]
ProviderOutcomeKind = Literal[
    "auto_eligible",
    "already_linked",
    "review_required",
    "ambiguous",
    "ineligible",
    "no_match",
    "source_unavailable",
]
IdentityOverallStatus = Literal[
    "ready_exact",
    "already_verified",
    "needs_review",
    "conflict",
    "ineligible",
    "unmatched",
    "source_unavailable",
]
MatchBasis = Literal[
    "exact_literal",
    "normalized_whitespace",
    "rank_token_normalized",
    "hybrid_sign_normalized",
    "hybrid_spacing_normalized",
    "hybrid_marker_dropped",
    "inline_authorship_stripped",
    "inline_cultivar_stripped",
    "fuzzy_genus_fallback",
    "none",
]
QueryRankShape = Literal[
    "uninomial",
    "binomial",
    "infraspecific",
    "hybrid_binomial",
    "hybrid_infraspecific",
    "other",
]
AuthorshipRelation = Literal["not_provided", "exact", "compatible_normalized", "mismatch"]
ExistingLinkPosture = Literal[
    "none",
    "synthetic_golden",
    "existing_verified_or_manual_current",
    "existing_verified_or_manual_stale",
]


class ExistingLinkInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["wfo", "wcvp", "gbif"]
    external_id: str
    source_version: str | None = None
    source_checksum: str | None = None
    scientific_name: str | None = None
    accepted_external_id: str | None = None
    accepted_scientific_name: str | None = None
    authorship: str | None = None
    taxonomic_status: str | None = None
    identity_updated_at: datetime | None = None
    stale: bool = False
    synthetic_golden: bool = False


class IdentityMatchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identity_id: UUID | None = None
    scientific_name: str = Field(min_length=1, max_length=255)
    cultivar_name: str | None = Field(default=None, max_length=120)
    common_name: str | None = Field(default=None, max_length=160)
    updated_at: datetime | None = None
    represented: bool = False
    retained_records: int = 0
    existing_links: dict[Literal["wfo", "wcvp", "gbif"], ExistingLinkInput] = Field(
        default_factory=dict
    )


class LookupVariant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_key: str
    match_basis: MatchBasis


class NormalizedNameAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_scientific_name: str
    normalized_scientific_name: str
    canonical_stem: str
    extracted_authorship: str | None = None
    cultivar_name: str | None = None
    has_cultivar: bool
    inline_cultivar_syntax: bool
    detected_rank_shape: QueryRankShape
    infraspecific_ranks: list[str] = Field(default_factory=list)
    rank_marker_canonicalized: bool = False
    is_hybrid: bool = False
    fuzzy_prefixes: list[str] = Field(default_factory=list)
    lookup_variants: list[LookupVariant] = Field(default_factory=list)


class CandidateEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: MatchProviderId
    external_id: str
    scientific_name: str
    authorship: str
    rank: str
    taxonomic_status: str
    accepted_external_id: str
    accepted_scientific_name: str
    accepted_authorship: str | None = None
    accepted_rank: str | None = None
    accepted_status: str | None = None
    provider_eligible: bool
    ineligible_reason: str | None = None
    match_basis: MatchBasis
    authorship_relation: AuthorshipRelation
    classification_family: str | None = None
    powo_id: str | None = None
    reviewed: str | None = None
    similarity_score: float | None = None


class ProviderMatchOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: MatchProviderId
    source_available: bool
    source_version: str | None = None
    source_checksum: str | None = None
    outcome: ProviderOutcomeKind
    confidence: ConfidenceTier
    auto_confirm_eligible: bool
    requires_operator_approval: bool
    existing_link_posture: ExistingLinkPosture
    existing_link_id: str | None = None
    reason_codes: list[str] = Field(default_factory=list)
    explanation: str
    selected_candidate: CandidateEvidence | None = None
    candidates: list[CandidateEvidence] = Field(default_factory=list)
    advisory_authorship_candidate_id: str | None = None
    truncated: bool = False


class CrossSourceDisagreement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    sources: list[str]
    message: str


class IdentityMatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identity: IdentityMatchInput
    normalized: NormalizedNameAnalysis
    overall_status: IdentityOverallStatus
    reason_codes: list[str] = Field(default_factory=list)
    wfo: ProviderMatchOutcome
    wcvp_v16: ProviderMatchOutcome
    wcvp_v15: ProviderMatchOutcome | None = None
    disagreements: list[CrossSourceDisagreement] = Field(default_factory=list)
    existing_gbif_link: ExistingLinkInput | None = None


class SourceReportInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: MatchProviderId
    available: bool
    version: str | None = None
    checksum: str | None = None
    message: str | None = None


class ProviderCoverageSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: MatchProviderId
    outcome_counts: dict[ProviderOutcomeKind, int] = Field(default_factory=dict)
    confidence_counts: dict[ConfidenceTier, int] = Field(default_factory=dict)
    auto_confirm_eligible_count: int = 0
    existing_synthetic_golden_count: int = 0
    existing_verified_or_manual_count: int = 0


class ExceptionExample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scientific_name: str
    cultivar_name: str | None = None
    represented: bool
    overall_status: IdentityOverallStatus
    wfo_outcome: ProviderOutcomeKind
    wcvp_v16_outcome: ProviderOutcomeKind
    explanation: str


class ExceptionCategorySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason_code: str
    count: int
    represented_count: int
    examples: list[ExceptionExample] = Field(default_factory=list)


class MatchBatchReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_identities: int
    represented_identities: int
    reference_only_identities: int
    sources: list[SourceReportInfo]
    overall_status_counts: dict[IdentityOverallStatus, int] = Field(default_factory=dict)
    represented_status_counts: dict[IdentityOverallStatus, int] = Field(default_factory=dict)
    providers: list[ProviderCoverageSummary] = Field(default_factory=list)
    exceptions: list[ExceptionCategorySummary] = Field(default_factory=list)
    results: list[IdentityMatchResult] = Field(default_factory=list)
