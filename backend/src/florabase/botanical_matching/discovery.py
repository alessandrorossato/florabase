"""Read-only batched candidate discovery, collection inspection, and coverage reporting."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from datetime import datetime
from difflib import SequenceMatcher
from typing import Literal
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_matching.classifier import (
    classify_provider_candidates,
    combine_identity_outcomes,
    wcvp_record_to_evidence,
    wfo_candidate_to_evidence,
)
from florabase.botanical_matching.normalizer import analyze_identity_name, normalize_whitespace
from florabase.botanical_matching.schemas import (
    CandidateEvidence,
    ConfidenceTier,
    ExceptionCategorySummary,
    ExceptionExample,
    ExistingLinkInput,
    IdentityMatchInput,
    IdentityMatchResult,
    IdentityOverallStatus,
    MatchBatchReport,
    MatchProviderId,
    NormalizedNameAnalysis,
    ProviderCoverageSummary,
    ProviderMatchOutcome,
    ProviderOutcomeKind,
    SourceReportInfo,
)
from florabase.explore.schemas import RepresentationScope
from florabase.explore.service import collection_records
from florabase.external_botany.model import ExternalTaxonLink
from florabase.native_range_enrichment.model import WcvpLink
from florabase.native_range_enrichment.source import (
    SourceMetadata as WcvpSourceMetadata,
)
from florabase.native_range_enrichment.source import (
    SourceUnavailableError as WcvpSourceUnavailableError,
)
from florabase.native_range_enrichment.source import (
    Taxon as WcvpTaxon,
)
from florabase.native_range_enrichment.source import (
    WcvpExactBatchResult,
    WcvpMatchedRecord,
    WcvpSource,
)
from florabase.taxonomy.model import WfoLink
from florabase.taxonomy.schemas import TaxonomyEvidence
from florabase.taxonomy.source import (
    SourceUnavailableError as WfoSourceUnavailableError,
)
from florabase.taxonomy.source import (
    WfoCandidate,
    WfoExactBatchResult,
    WfoSource,
)

_FUZZY_MIN_RATIO = 0.88
_FUZZY_MAX_CANDIDATES = 5
_EXCEPTION_CODES = frozenset(
    {
        "homonym_ambiguity",
        "wfo_synonym_matched",
        "wcvp_synonym_ineligible",
        "resolved_accepted_target_available",
        "wfo_status_unplaced",
        "wfo_path_unresolved",
        "wcvp_rank_ineligible",
        "cultivar_species_anchor",
        "inline_cultivar_syntax",
        "hybrid_notation_variant",
        "hybrid_marker_dropped",
        "rank_token_normalized",
        "rank_mismatch",
        "rank_above_species",
        "inline_authorship_advisory",
        "authorship_mismatch",
        "authorship_advisory_disambiguation",
        "fuzzy_advisory_only",
        "cross_source_accepted_name_conflict",
        "cross_source_status_divergence",
        "cross_source_formatting_difference",
        "wcvp_version_conflict",
        "existing_gbif_conflict",
        "existing_link_preserved",
        "existing_link_differs_from_candidate",
        "existing_link_stale",
        "synthetic_evidence_present",
        "single_source_coverage_only",
        "no_match_found",
        "source_unavailable",
        "candidate_list_truncated",
    }
)


def _select_wfo_candidates(
    normalized: NormalizedNameAnalysis,
    exact_batch: WfoExactBatchResult,
    fuzzy_by_prefix: dict[str, list[WfoCandidate]],
) -> tuple[list[CandidateEvidence], bool]:
    for variant in normalized.lookup_variants:
        hits = exact_batch.matches.get(variant.query_key)
        if hits:
            truncated = variant.query_key in exact_batch.truncated_keys
            evidence = [
                wfo_candidate_to_evidence(
                    hit,
                    match_basis=variant.match_basis,
                    normalized=normalized,
                    path_error=exact_batch.path_errors.get(hit.taxon.source_taxon_id),
                )
                for hit in hits
            ]
            return evidence, truncated

    if fuzzy_by_prefix:
        stem_key = normalized.canonical_stem.casefold()
        seen_ids: set[str] = set()
        scored: list[tuple[float, WfoCandidate]] = []
        for prefix in normalized.fuzzy_prefixes:
            for hit in fuzzy_by_prefix.get(prefix, ()):
                tid = hit.taxon.source_taxon_id
                if tid in seen_ids:
                    continue
                seen_ids.add(tid)
                ratio = SequenceMatcher(
                    None, stem_key, hit.taxon.scientific_name.casefold()
                ).ratio()
                if ratio >= _FUZZY_MIN_RATIO:
                    scored.append((round(ratio, 4), hit))
        scored.sort(
            key=lambda item: (
                -item[0],
                item[1].taxon.scientific_name.casefold(),
                item[1].taxon.source_taxon_id,
            )
        )
        top = scored[:_FUZZY_MAX_CANDIDATES]
        if top:
            return (
                [
                    wfo_candidate_to_evidence(
                        hit,
                        match_basis="fuzzy_genus_fallback",
                        normalized=normalized,
                        path_error=exact_batch.path_errors.get(hit.taxon.source_taxon_id),
                        similarity_score=ratio,
                    )
                    for ratio, hit in top
                ],
                False,
            )
    return [], False


def _select_wcvp_candidates(
    provider: Literal["wcvp_v16", "wcvp_v15"],
    normalized: NormalizedNameAnalysis,
    exact_batch: WcvpExactBatchResult,
    fuzzy_by_prefix: dict[str, list[WcvpMatchedRecord]],
) -> tuple[list[CandidateEvidence], bool]:
    for variant in normalized.lookup_variants:
        hits = exact_batch.matches.get(variant.query_key)
        if hits:
            truncated = variant.query_key in exact_batch.truncated_keys
            evidence = [
                wcvp_record_to_evidence(
                    hit,
                    provider=provider,
                    match_basis=variant.match_basis,
                    normalized=normalized,
                )
                for hit in hits
            ]
            return evidence, truncated

    if fuzzy_by_prefix:
        stem_key = normalized.canonical_stem.casefold()
        seen_ids: set[str] = set()
        scored: list[tuple[float, WcvpMatchedRecord]] = []
        for prefix in normalized.fuzzy_prefixes:
            for hit in fuzzy_by_prefix.get(prefix, ()):
                tid = hit.taxon.external_id
                if tid in seen_ids:
                    continue
                seen_ids.add(tid)
                ratio = SequenceMatcher(None, stem_key, hit.taxon.name.casefold()).ratio()
                if ratio >= _FUZZY_MIN_RATIO:
                    scored.append((round(ratio, 4), hit))
        scored.sort(
            key=lambda item: (
                -item[0],
                item[1].taxon.name.casefold(),
                item[1].taxon.external_id,
            )
        )
        top = scored[:_FUZZY_MAX_CANDIDATES]
        if top:
            return (
                [
                    wcvp_record_to_evidence(
                        hit,
                        provider=provider,
                        match_basis="fuzzy_genus_fallback",
                        normalized=normalized,
                        similarity_score=ratio,
                    )
                    for ratio, hit in top
                ],
                False,
            )
    return [], False


def _query_wfo_batch(
    wfo_source: WfoSource | None,
    normalized_items: Sequence[NormalizedNameAnalysis],
    *,
    include_fuzzy_advisory: bool,
) -> tuple[SourceReportInfo, WfoExactBatchResult | None, dict[str, list[WfoCandidate]]]:
    if wfo_source is None:
        return (
            SourceReportInfo(provider="wfo", available=False, message="WFO source not configured."),
            None,
            {},
        )
    all_keys = [variant.query_key for item in normalized_items for variant in item.lookup_variants]
    try:
        exact_result = wfo_source.exact_matches_with_context(all_keys)
    except WfoSourceUnavailableError as error:
        return SourceReportInfo(provider="wfo", available=False, message=str(error)), None, {}

    fuzzy_map: dict[str, list[WfoCandidate]] = {}
    if include_fuzzy_advisory:
        unmatched_prefixes: list[str] = []
        for item in normalized_items:
            has_exact = any(exact_result.matches.get(v.query_key) for v in item.lookup_variants)
            if not has_exact:
                unmatched_prefixes.extend(item.fuzzy_prefixes)
        if unmatched_prefixes:
            try:
                fuzzy_batch = wfo_source.prefix_candidates(unmatched_prefixes, limit_per_prefix=15)
                fuzzy_map = fuzzy_batch.matches
                exact_result.path_errors.update(fuzzy_batch.path_errors)
            except WfoSourceUnavailableError:
                fuzzy_map = {}

    return (
        SourceReportInfo(
            provider="wfo",
            available=True,
            version=exact_result.metadata.version,
            checksum=exact_result.metadata.checksum,
        ),
        exact_result,
        fuzzy_map,
    )


def _query_wcvp_batch(
    provider: Literal["wcvp_v16", "wcvp_v15"],
    source: WcvpSource | None,
    normalized_items: Sequence[NormalizedNameAnalysis],
    *,
    include_fuzzy_advisory: bool,
) -> tuple[SourceReportInfo, WcvpExactBatchResult | None, dict[str, list[WcvpMatchedRecord]]]:
    if source is None:
        return (
            SourceReportInfo(
                provider=provider, available=False, message=f"{provider} source not configured."
            ),
            None,
            {},
        )
    all_keys = [variant.query_key for item in normalized_items for variant in item.lookup_variants]
    try:
        exact_result = source.exact_matches_with_context(all_keys)
    except WcvpSourceUnavailableError as error:
        return (
            SourceReportInfo(provider=provider, available=False, message=str(error)),
            None,
            {},
        )

    fuzzy_map: dict[str, list[WcvpMatchedRecord]] = {}
    if include_fuzzy_advisory:
        unmatched_prefixes: list[str] = []
        for item in normalized_items:
            has_exact = any(exact_result.matches.get(v.query_key) for v in item.lookup_variants)
            if not has_exact:
                unmatched_prefixes.extend(item.fuzzy_prefixes)
        if unmatched_prefixes:
            try:
                fuzzy_batch = source.prefix_candidates(unmatched_prefixes, limit_per_prefix=15)
                fuzzy_map = fuzzy_batch.matches
            except WcvpSourceUnavailableError:
                fuzzy_map = {}

    return (
        SourceReportInfo(
            provider=provider,
            available=True,
            version=exact_result.metadata.version,
            checksum=exact_result.metadata.checksum,
        ),
        exact_result,
        fuzzy_map,
    )


def _summarize_provider(
    provider: MatchProviderId, outcomes: Sequence[ProviderMatchOutcome]
) -> ProviderCoverageSummary:
    outcome_counts: Counter[ProviderOutcomeKind] = Counter()
    confidence_counts: Counter[ConfidenceTier] = Counter()
    auto_count = 0
    synthetic_count = 0
    verified_count = 0
    for outcome in outcomes:
        outcome_counts[outcome.outcome] += 1
        confidence_counts[outcome.confidence] += 1
        if outcome.auto_confirm_eligible:
            auto_count += 1
        if outcome.existing_link_posture == "synthetic_golden":
            synthetic_count += 1
        elif outcome.existing_link_posture in {
            "existing_verified_or_manual_current",
            "existing_verified_or_manual_stale",
        }:
            verified_count += 1
    return ProviderCoverageSummary(
        provider=provider,
        outcome_counts=dict(sorted(outcome_counts.items())),
        confidence_counts=dict(sorted(confidence_counts.items())),
        auto_confirm_eligible_count=auto_count,
        existing_synthetic_golden_count=synthetic_count,
        existing_verified_or_manual_count=verified_count,
    )


def build_match_report(
    results: Sequence[IdentityMatchResult],
    sources: Sequence[SourceReportInfo],
    *,
    max_examples: int = 5,
    include_results: bool = True,
) -> MatchBatchReport:
    overall_counts: Counter[IdentityOverallStatus] = Counter()
    represented_counts: Counter[IdentityOverallStatus] = Counter()
    exception_rows: dict[str, list[IdentityMatchResult]] = {}

    for item in results:
        overall_counts[item.overall_status] += 1
        if item.identity.represented:
            represented_counts[item.overall_status] += 1
        for code in item.reason_codes:
            if code in _EXCEPTION_CODES:
                exception_rows.setdefault(code, []).append(item)

    providers = [_summarize_provider("wfo", [item.wfo for item in results])]
    providers.append(_summarize_provider("wcvp_v16", [item.wcvp_v16 for item in results]))
    if any(item.wcvp_v15 is not None for item in results):
        providers.append(
            _summarize_provider(
                "wcvp_v15", [item.wcvp_v15 for item in results if item.wcvp_v15 is not None]
            )
        )

    exceptions: list[ExceptionCategorySummary] = []
    for code, rows in sorted(exception_rows.items(), key=lambda pair: (-len(pair[1]), pair[0])):
        sorted_rows = sorted(
            rows,
            key=lambda row: (
                not row.identity.represented,
                row.identity.scientific_name.casefold(),
                row.identity.cultivar_name or "",
            ),
        )
        examples = [
            ExceptionExample(
                scientific_name=row.identity.scientific_name,
                cultivar_name=row.identity.cultivar_name,
                represented=row.identity.represented,
                overall_status=row.overall_status,
                wfo_outcome=row.wfo.outcome,
                wcvp_v16_outcome=row.wcvp_v16.outcome,
                explanation=(
                    row.disagreements[0].message
                    if row.disagreements
                    else row.wfo.explanation
                    if code in row.wfo.reason_codes
                    else row.wcvp_v16.explanation
                ),
            )
            for row in sorted_rows[:max_examples]
        ]
        exceptions.append(
            ExceptionCategorySummary(
                reason_code=code,
                count=len(rows),
                represented_count=sum(1 for row in rows if row.identity.represented),
                examples=examples,
            )
        )

    total = len(results)
    represented = sum(1 for item in results if item.identity.represented)
    return MatchBatchReport(
        total_identities=total,
        represented_identities=represented,
        reference_only_identities=total - represented,
        sources=list(sources),
        overall_status_counts=dict(sorted(overall_counts.items())),
        represented_status_counts=dict(sorted(represented_counts.items())),
        providers=providers,
        exceptions=exceptions,
        results=list(results) if include_results else [],
    )


def discover_and_classify(
    inputs: Sequence[IdentityMatchInput],
    *,
    wfo_source: WfoSource | None = None,
    wcvp_v16_source: WcvpSource | None = None,
    wcvp_v15_source: WcvpSource | None = None,
    include_fuzzy_advisory: bool = True,
    max_examples: int = 5,
    include_results: bool = True,
) -> MatchBatchReport:
    """Run deterministic local candidate discovery and classification with bounded batch lookups."""
    normalized_items = [
        analyze_identity_name(item.scientific_name, item.cultivar_name) for item in inputs
    ]

    wfo_info, wfo_batch, wfo_fuzzy = _query_wfo_batch(
        wfo_source,
        normalized_items,
        include_fuzzy_advisory=include_fuzzy_advisory,
    )
    v16_info, v16_batch, v16_fuzzy = _query_wcvp_batch(
        "wcvp_v16",
        wcvp_v16_source,
        normalized_items,
        include_fuzzy_advisory=include_fuzzy_advisory,
    )
    sources: list[SourceReportInfo] = [wfo_info, v16_info]

    v15_info: SourceReportInfo | None = None
    v15_batch: WcvpExactBatchResult | None = None
    v15_fuzzy: dict[str, list[WcvpMatchedRecord]] = {}
    if wcvp_v15_source is not None:
        v15_info, v15_batch, v15_fuzzy = _query_wcvp_batch(
            "wcvp_v15",
            wcvp_v15_source,
            normalized_items,
            include_fuzzy_advisory=False,
        )
        sources.append(v15_info)

    results: list[IdentityMatchResult] = []
    for item, normalized in zip(inputs, normalized_items, strict=True):
        if wfo_batch is not None:
            wfo_cands, wfo_trunc = _select_wfo_candidates(normalized, wfo_batch, wfo_fuzzy)
        else:
            wfo_cands, wfo_trunc = [], False

        wfo_outcome = classify_provider_candidates(
            provider="wfo",
            source_available=wfo_info.available,
            source_version=wfo_info.version,
            source_checksum=wfo_info.checksum,
            identity=item,
            normalized=normalized,
            existing_link=item.existing_links.get("wfo"),
            candidates=wfo_cands,
            truncated=wfo_trunc,
        )

        if v16_batch is not None:
            v16_cands, v16_trunc = _select_wcvp_candidates(
                "wcvp_v16", normalized, v16_batch, v16_fuzzy
            )
        else:
            v16_cands, v16_trunc = [], False

        v16_outcome = classify_provider_candidates(
            provider="wcvp_v16",
            source_available=v16_info.available,
            source_version=v16_info.version,
            source_checksum=v16_info.checksum,
            identity=item,
            normalized=normalized,
            existing_link=item.existing_links.get("wcvp"),
            candidates=v16_cands,
            truncated=v16_trunc,
        )

        v15_outcome: ProviderMatchOutcome | None = None
        if v15_info is not None:
            if v15_batch is not None:
                v15_cands, v15_trunc = _select_wcvp_candidates(
                    "wcvp_v15", normalized, v15_batch, v15_fuzzy
                )
            else:
                v15_cands, v15_trunc = [], False
            v15_outcome = classify_provider_candidates(
                provider="wcvp_v15",
                source_available=v15_info.available,
                source_version=v15_info.version,
                source_checksum=v15_info.checksum,
                identity=item,
                normalized=normalized,
                existing_link=item.existing_links.get("wcvp"),
                candidates=v15_cands,
                truncated=v15_trunc,
            )

        results.append(
            combine_identity_outcomes(
                identity=item,
                normalized=normalized,
                wfo=wfo_outcome,
                wcvp_v16=v16_outcome,
                wcvp_v15=v15_outcome,
            )
        )

    return build_match_report(
        results, sources, max_examples=max_examples, include_results=include_results
    )


def _parse_iso_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _wfo_link_input(link: WfoLink, identity: BotanicalIdentity) -> ExistingLinkInput:
    try:
        evidence = TaxonomyEvidence.model_validate(link.evidence)
    except ValidationError:
        return ExistingLinkInput(
            provider="wfo",
            external_id=link.external_id,
            stale=True,
        )
    accepted = (
        evidence.classification[-1]
        if evidence.taxon.taxonomic_status == "synonym" and evidence.classification
        else evidence.taxon
    )
    return ExistingLinkInput(
        provider="wfo",
        external_id=link.external_id,
        source_version=evidence.source.version,
        source_checksum=evidence.source.checksum,
        scientific_name=evidence.taxon.scientific_name,
        accepted_external_id=accepted.source_taxon_id,
        accepted_scientific_name=accepted.scientific_name,
        authorship=evidence.taxon.authorship,
        taxonomic_status=evidence.taxon.taxonomic_status,
        identity_updated_at=evidence.identity_updated_at,
        stale=evidence.identity_updated_at != identity.updated_at,
        synthetic_golden=evidence.taxon.authorship.strip() == "Golden",
    )


def _wcvp_link_input(link: WcvpLink, identity: BotanicalIdentity) -> ExistingLinkInput:
    try:
        taxon = WcvpTaxon.model_validate(link.taxon)
        source = WcvpSourceMetadata.model_validate(link.source)
    except ValidationError:
        return ExistingLinkInput(
            provider="wcvp",
            external_id=link.external_id,
            stale=True,
        )
    snap_name = link.identity_snapshot.get("scientific_name")
    snap_updated = _parse_iso_datetime(link.identity_snapshot.get("updated_at"))
    stale = bool(
        (snap_updated is not None and snap_updated != identity.updated_at)
        or (
            isinstance(snap_name, str)
            and normalize_whitespace(snap_name).casefold()
            != normalize_whitespace(identity.scientific_name).casefold()
        )
    )
    return ExistingLinkInput(
        provider="wcvp",
        external_id=link.external_id,
        source_version=source.version,
        source_checksum=source.checksum,
        scientific_name=taxon.name,
        accepted_external_id=taxon.accepted_id,
        accepted_scientific_name=taxon.accepted_name or taxon.name,
        authorship=taxon.authorship,
        taxonomic_status=taxon.status,
        identity_updated_at=snap_updated,
        stale=stale,
        synthetic_golden=taxon.name.startswith("Golden ") or taxon.authorship.strip() == "Golden",
    )


def _gbif_link_input(link: ExternalTaxonLink) -> ExistingLinkInput:
    return ExistingLinkInput(
        provider="gbif",
        external_id=link.external_id,
        scientific_name=link.canonical_name or link.scientific_name,
        accepted_external_id=link.accepted_external_id,
        accepted_scientific_name=link.accepted_name,
        authorship=link.authorship,
        taxonomic_status=link.taxonomic_status,
        stale=False,
        synthetic_golden=False,
    )


def load_collection_match_inputs(
    database: Session,
    *,
    scope: RepresentationScope = "all",
    represented_only: bool = False,
    identity_ids: Sequence[UUID] | None = None,
    limit: int = 1000,
) -> list[IdentityMatchInput]:
    """Load active collection identities and existing links in O(1) bounded queries."""
    if not 1 <= limit <= 5000:
        raise ValueError("limit must be between 1 and 5000")

    records = collection_records()
    counts = (
        select(
            records.c.identity_id,
            func.count().label("retained"),
            func.sum(records.c.current).label("current"),
            func.sum(records.c.living).label("living"),
        )
        .group_by(records.c.identity_id)
        .subquery()
    )
    retained_col = func.coalesce(counts.c.retained, 0)
    current_col = func.coalesce(counts.c.current, 0)
    living_col = func.coalesce(counts.c.living, 0)

    statement = (
        select(
            BotanicalIdentity,
            retained_col.label("retained"),
        )
        .outerjoin(counts, counts.c.identity_id == BotanicalIdentity.id)
        .where(BotanicalIdentity.merged_into_id.is_(None))
        .order_by(
            func.lower(BotanicalIdentity.scientific_name),
            func.lower(BotanicalIdentity.cultivar_name),
            BotanicalIdentity.id,
        )
    )
    if represented_only:
        statement = statement.where(retained_col > 0)
    if scope == "living":
        statement = statement.where(living_col > 0)
    elif scope == "current":
        statement = statement.where(current_col > 0)
    elif scope == "historical":
        statement = statement.where(retained_col > 0, current_col == 0)
    if identity_ids is not None:
        ids = list(dict.fromkeys(identity_ids))
        if not ids:
            return []
        statement = statement.where(BotanicalIdentity.id.in_(ids))
    statement = statement.limit(limit)

    selected_rows: list[tuple[BotanicalIdentity, int]] = [
        (row[0], int(row[1])) for row in database.execute(statement).all()
    ]

    if not selected_rows:
        return []

    selected_ids = [identity.id for identity, _ in selected_rows]
    wfo_links = {
        link.identity_id: link
        for link in database.scalars(select(WfoLink).where(WfoLink.identity_id.in_(selected_ids)))
    }
    wcvp_links = {
        link.identity_id: link
        for link in database.scalars(select(WcvpLink).where(WcvpLink.identity_id.in_(selected_ids)))
    }
    gbif_links = {
        link.botanical_identity_id: link
        for link in database.scalars(
            select(ExternalTaxonLink).where(
                ExternalTaxonLink.botanical_identity_id.in_(selected_ids),
                ExternalTaxonLink.provider == "gbif",
            )
        )
    }

    inputs: list[IdentityMatchInput] = []
    for identity, retained in selected_rows:
        links: dict[Literal["wfo", "wcvp", "gbif"], ExistingLinkInput] = {}
        wfo_row = wfo_links.get(identity.id)
        if wfo_row is not None:
            links["wfo"] = _wfo_link_input(wfo_row, identity)
        wcvp_row = wcvp_links.get(identity.id)
        if wcvp_row is not None:
            links["wcvp"] = _wcvp_link_input(wcvp_row, identity)
        gbif_row = gbif_links.get(identity.id)
        if gbif_row is not None:
            links["gbif"] = _gbif_link_input(gbif_row)

        inputs.append(
            IdentityMatchInput(
                identity_id=identity.id,
                scientific_name=identity.scientific_name,
                cultivar_name=identity.cultivar_name,
                common_name=identity.common_name,
                updated_at=identity.updated_at,
                represented=retained > 0,
                retained_records=retained,
                existing_links=links,
            )
        )
    return inputs


def match_collection_identities(
    database: Session,
    *,
    wfo_source: WfoSource | None = None,
    wcvp_v16_source: WcvpSource | None = None,
    wcvp_v15_source: WcvpSource | None = None,
    scope: RepresentationScope = "all",
    represented_only: bool = False,
    identity_ids: Sequence[UUID] | None = None,
    limit: int = 1000,
    include_fuzzy_advisory: bool = True,
    max_examples: int = 5,
    include_results: bool = True,
) -> MatchBatchReport:
    """Load collection identities read-only and classify matches across local sources."""
    inputs = load_collection_match_inputs(
        database,
        scope=scope,
        represented_only=represented_only,
        identity_ids=identity_ids,
        limit=limit,
    )
    return discover_and_classify(
        inputs,
        wfo_source=wfo_source,
        wcvp_v16_source=wcvp_v16_source,
        wcvp_v15_source=wcvp_v15_source,
        include_fuzzy_advisory=include_fuzzy_advisory,
        max_examples=max_examples,
        include_results=include_results,
    )


def format_match_report_markdown(report: MatchBatchReport) -> str:
    """Render a deterministic Markdown coverage and exception report."""
    lines: list[str] = [
        "# Botanical Reference Matching Coverage & Exception Report",
        "",
        "## Source Metadata",
    ]
    for source in report.sources:
        status = (
            f"available (version={source.version}, checksum={source.checksum})"
            if source.available
            else f"unavailable ({source.message or 'not configured'})"
        )
        lines.append(f"- `{source.provider}`: {status}")

    lines.extend(
        [
            "",
            "## Identity Coverage Summary",
            f"- Total active identities: {report.total_identities}",
            f"- Represented in collection holdings: {report.represented_identities}",
            f"- Reference-only identities: {report.reference_only_identities}",
            "",
            "| Overall Status | Total | Represented |",
            "| --- | ---: | ---: |",
        ]
    )
    for status_key in (
        "ready_exact",
        "already_verified",
        "needs_review",
        "conflict",
        "ineligible",
        "unmatched",
        "source_unavailable",
    ):
        total_n = report.overall_status_counts.get(status_key, 0)
        rep_n = report.represented_status_counts.get(status_key, 0)
        if total_n or rep_n:
            lines.append(f"| `{status_key}` | {total_n} | {rep_n} |")

    lines.extend(
        [
            "",
            "## Per-Provider Outcome Breakdown",
            "| Provider | Outcome | Count |",
            "| --- | --- | ---: |",
        ]
    )
    for provider_summary in report.providers:
        for outcome_key, count in sorted(provider_summary.outcome_counts.items()):
            lines.append(f"| `{provider_summary.provider}` | `{outcome_key}` | {count} |")
        lines.append(
            f"| `{provider_summary.provider}` | `auto_confirm_eligible` (subset) | "
            f"{provider_summary.auto_confirm_eligible_count} |"
        )
        if provider_summary.existing_synthetic_golden_count:
            lines.append(
                f"| `{provider_summary.provider}` | `existing_synthetic_golden` | "
                f"{provider_summary.existing_synthetic_golden_count} |"
            )

    lines.extend(["", "## Exception Categories & Representative Examples"])
    if not report.exceptions:
        lines.append("- None.")
    for exc in report.exceptions:
        lines.append(
            f"### `{exc.reason_code}` ({exc.count} total, {exc.represented_count} represented)"
        )
        for ex in exc.examples:
            cultivar = f" '{ex.cultivar_name}'" if ex.cultivar_name else ""
            rep_tag = "represented" if ex.represented else "reference-only"
            lines.append(
                f"- `{ex.scientific_name}{cultivar}` [{rep_tag}, overall=`{ex.overall_status}`, "
                f"wfo=`{ex.wfo_outcome}`, wcvp_v16=`{ex.wcvp_v16_outcome}`]: {ex.explanation}"
            )
    lines.append("")
    return "\n".join(lines)
