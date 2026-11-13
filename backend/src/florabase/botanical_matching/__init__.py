"""Deterministic read-only local botanical reference discovery and classification."""

from florabase.botanical_matching.classifier import (
    classify_existing_link,
    classify_provider_candidates,
    combine_identity_outcomes,
)
from florabase.botanical_matching.discovery import (
    build_match_report,
    discover_and_classify,
    format_match_report_markdown,
    load_collection_match_inputs,
    match_collection_identities,
)
from florabase.botanical_matching.normalizer import (
    analyze_identity_name,
    compare_authorship,
    normalize_whitespace,
    semantic_comparison_key,
)
from florabase.botanical_matching.schemas import (
    CandidateEvidence,
    ConfidenceTier,
    CrossSourceDisagreement,
    ExceptionCategorySummary,
    ExceptionExample,
    ExistingLinkInput,
    IdentityMatchInput,
    IdentityMatchResult,
    IdentityOverallStatus,
    MatchBatchReport,
    NormalizedNameAnalysis,
    ProviderMatchOutcome,
    ProviderOutcomeKind,
    SourceReportInfo,
)

__all__ = [
    "CandidateEvidence",
    "ConfidenceTier",
    "CrossSourceDisagreement",
    "ExceptionCategorySummary",
    "ExceptionExample",
    "ExistingLinkInput",
    "IdentityMatchInput",
    "IdentityMatchResult",
    "IdentityOverallStatus",
    "MatchBatchReport",
    "NormalizedNameAnalysis",
    "ProviderMatchOutcome",
    "ProviderOutcomeKind",
    "SourceReportInfo",
    "analyze_identity_name",
    "build_match_report",
    "classify_existing_link",
    "classify_provider_candidates",
    "combine_identity_outcomes",
    "compare_authorship",
    "discover_and_classify",
    "format_match_report_markdown",
    "load_collection_match_inputs",
    "match_collection_identities",
    "normalize_whitespace",
    "semantic_comparison_key",
]
