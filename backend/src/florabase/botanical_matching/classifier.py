"""Deterministic candidate classification, confidence scoring, and conflict detection."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from florabase.botanical_matching.normalizer import (
    compare_authorship,
    normalize_whitespace,
    semantic_comparison_key,
)
from florabase.botanical_matching.schemas import (
    CandidateEvidence,
    ConfidenceTier,
    CrossSourceDisagreement,
    ExistingLinkInput,
    ExistingLinkPosture,
    IdentityMatchInput,
    IdentityMatchResult,
    IdentityOverallStatus,
    MatchBasis,
    MatchProviderId,
    NormalizedNameAnalysis,
    ProviderMatchOutcome,
    QueryRankShape,
)
from florabase.native_range_enrichment.source import (
    RELEASES as WCVP_RELEASES,
)
from florabase.native_range_enrichment.source import (
    WcvpMatchedRecord,
)
from florabase.taxonomy.source import (
    CHECKSUM as WFO_OFFICIAL_CHECKSUM,
)
from florabase.taxonomy.source import (
    WfoCandidate,
)

_HIGH_LEVEL_RANKS = frozenset(
    {
        "kingdom",
        "subkingdom",
        "phylum",
        "class",
        "subclass",
        "superorder",
        "order",
        "suborder",
        "family",
        "subfamily",
        "tribe",
        "supertribe",
        "subtribe",
        "genus",
        "subgenus",
        "section",
        "subsection",
        "series",
        "subseries",
    }
)

_RANK_NORMALIZATION = {
    "species": "species",
    "nothospecies": "species",
    "subspecies": "subspecies",
    "nothosubspecies": "subspecies",
    "variety": "variety",
    "nothovariety": "variety",
    "subvariety": "subvariety",
    "form": "form",
    "subform": "subform",
    "convar": "convar",
    "prole": "prole",
    "lusus": "lusus",
}

_OFFICIAL_WCVP_CHECKSUMS = frozenset(release.checksum for release in WCVP_RELEASES.values())


def classify_existing_link(
    link: ExistingLinkInput | None,
    *,
    live_checksum: str | None,
    live_version: str | None,
) -> tuple[ExistingLinkPosture, str | None]:
    """Distinguish synthetic Golden fixture links from existing verified or manual links."""
    if link is None:
        return "none", None

    is_golden_author = (link.authorship or "").strip() == "Golden"
    is_golden_name = (link.scientific_name or "").startswith("Golden ")
    if link.synthetic_golden or is_golden_author or is_golden_name:
        return "synthetic_golden", link.external_id

    official_known = (
        link.source_checksum == WFO_OFFICIAL_CHECKSUM
        if link.provider == "wfo"
        else link.source_checksum in _OFFICIAL_WCVP_CHECKSUMS
        if link.provider == "wcvp"
        else False
    )
    matches_live = bool(
        live_checksum
        and link.source_checksum == live_checksum
        and (live_version is None or link.source_version in {None, live_version})
    )
    if link.stale or (official_known and live_checksum is not None and not matches_live):
        return "existing_verified_or_manual_stale", link.external_id
    return "existing_verified_or_manual_current", link.external_id


def wfo_candidate_to_evidence(
    candidate: WfoCandidate,
    *,
    match_basis: MatchBasis,
    normalized: NormalizedNameAnalysis,
    path_error: str | None = None,
    similarity_score: float | None = None,
) -> CandidateEvidence:
    taxon = candidate.taxon
    classification = candidate.classification
    accepted = (
        classification[-1] if taxon.taxonomic_status == "synonym" and classification else taxon
    )
    family = next((node.scientific_name for node in classification if node.rank == "family"), None)

    ineligible_reason: str | None = None
    if taxon.taxonomic_status == "unplaced":
        ineligible_reason = "wfo_status_unplaced"
    elif path_error is not None:
        ineligible_reason = "wfo_path_unresolved"
    elif not classification:
        ineligible_reason = "wfo_classification_unavailable"

    return CandidateEvidence(
        provider="wfo",
        external_id=taxon.source_taxon_id,
        scientific_name=taxon.scientific_name,
        authorship=taxon.authorship,
        rank=taxon.rank,
        taxonomic_status=taxon.taxonomic_status,
        accepted_external_id=accepted.source_taxon_id,
        accepted_scientific_name=accepted.scientific_name,
        accepted_authorship=accepted.authorship or None,
        accepted_rank=accepted.rank,
        accepted_status=accepted.taxonomic_status,
        provider_eligible=(
            ineligible_reason is None and taxon.taxonomic_status in {"accepted", "synonym"}
        ),
        ineligible_reason=ineligible_reason,
        match_basis=match_basis,
        authorship_relation=compare_authorship(normalized.extracted_authorship, taxon.authorship),
        classification_family=family,
        similarity_score=similarity_score,
    )


def wcvp_record_to_evidence(
    record: WcvpMatchedRecord,
    *,
    provider: Literal["wcvp_v16", "wcvp_v15"],
    match_basis: MatchBasis,
    normalized: NormalizedNameAnalysis,
    similarity_score: float | None = None,
) -> CandidateEvidence:
    taxon = record.taxon
    accepted = record.accepted_taxon
    accepted_name = accepted.name if accepted is not None else (taxon.accepted_name or taxon.name)

    ineligible_reason: str | None = None
    if not taxon.eligible:
        if taxon.status.casefold() == "synonym":
            ineligible_reason = "wcvp_synonym_ineligible"
        elif taxon.status != "Accepted":
            ineligible_reason = f"wcvp_status_{taxon.status.lower().replace(' ', '_')}"
        elif taxon.rank not in {"Species", "Subspecies", "Variety", "Form"}:
            ineligible_reason = "wcvp_rank_ineligible"
        else:
            ineligible_reason = "wcvp_accepted_id_mismatch"

    return CandidateEvidence(
        provider=provider,
        external_id=taxon.external_id,
        scientific_name=taxon.name,
        authorship=taxon.authorship,
        rank=taxon.rank,
        taxonomic_status=taxon.status,
        accepted_external_id=taxon.accepted_id,
        accepted_scientific_name=accepted_name,
        accepted_authorship=(
            accepted.authorship if accepted is not None and accepted.authorship else None
        ),
        accepted_rank=accepted.rank if accepted is not None else None,
        accepted_status=accepted.status if accepted is not None else None,
        provider_eligible=taxon.eligible,
        ineligible_reason=ineligible_reason,
        match_basis=match_basis,
        authorship_relation=compare_authorship(normalized.extracted_authorship, taxon.authorship),
        powo_id=taxon.powo_id or None,
        reviewed=taxon.reviewed or None,
        similarity_score=similarity_score,
    )


def _check_rank_alignment(
    rank_shape: QueryRankShape,
    infraspecific_ranks: Sequence[str],
    candidate_rank: str,
) -> tuple[bool, bool]:
    """Return (rank_mismatch, rank_above_species) cleanly without guessing."""
    norm = candidate_rank.strip().casefold()
    canonical = _RANK_NORMALIZATION.get(norm, norm)
    if norm in _HIGH_LEVEL_RANKS:
        if rank_shape == "uninomial":
            return False, True
        return True, True
    if rank_shape == "uninomial":
        return True, False
    if rank_shape in {"binomial", "hybrid_binomial"}:
        return canonical != "species", False
    if rank_shape in {"infraspecific", "hybrid_infraspecific"} and infraspecific_ranks:
        expected = _RANK_NORMALIZATION.get(infraspecific_ranks[-1], infraspecific_ranks[-1])
        return canonical != expected, False
    return False, False


def _dedupe_codes(codes: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for code in codes:
        if code and code not in seen:
            seen.add(code)
            ordered.append(code)
    return ordered


def classify_provider_candidates(
    *,
    provider: MatchProviderId,
    source_available: bool,
    source_version: str | None,
    source_checksum: str | None,
    identity: IdentityMatchInput,
    normalized: NormalizedNameAnalysis,
    existing_link: ExistingLinkInput | None,
    candidates: Sequence[CandidateEvidence],
    truncated: bool = False,
) -> ProviderMatchOutcome:
    """Classify discovered candidates for a single botanical reference provider."""
    existing_posture, existing_id = classify_existing_link(
        existing_link,
        live_checksum=source_checksum,
        live_version=source_version,
    )
    prefix_codes: list[str] = []
    if existing_posture == "synthetic_golden":
        prefix_codes.append("synthetic_evidence_present")

    if not source_available:
        return ProviderMatchOutcome(
            provider=provider,
            source_available=False,
            source_version=source_version,
            source_checksum=source_checksum,
            outcome="source_unavailable",
            confidence="none",
            auto_confirm_eligible=False,
            requires_operator_approval=False,
            existing_link_posture=existing_posture,
            existing_link_id=existing_id,
            reason_codes=_dedupe_codes([*prefix_codes, "source_unavailable"]),
            explanation=f"{provider} reference source is unavailable.",
        )

    ordered = sorted(
        candidates,
        key=lambda item: (
            -(item.similarity_score or 0.0),
            item.scientific_name.casefold(),
            item.authorship.casefold(),
            item.external_id,
        ),
    )

    if not ordered:
        return ProviderMatchOutcome(
            provider=provider,
            source_available=True,
            source_version=source_version,
            source_checksum=source_checksum,
            outcome="no_match",
            confidence="none",
            auto_confirm_eligible=False,
            requires_operator_approval=False,
            existing_link_posture=existing_posture,
            existing_link_id=existing_id,
            reason_codes=_dedupe_codes([*prefix_codes, "no_match_found"]),
            explanation=f"No matching taxon found in {provider} for '{identity.scientific_name}'.",
            truncated=truncated,
        )

    is_fuzzy = all(item.match_basis == "fuzzy_genus_fallback" for item in ordered)
    if is_fuzzy:
        codes = [*prefix_codes, "fuzzy_advisory_only"]
        if truncated:
            codes.append("candidate_list_truncated")
        return ProviderMatchOutcome(
            provider=provider,
            source_available=True,
            source_version=source_version,
            source_checksum=source_checksum,
            outcome="review_required",
            confidence="low",
            auto_confirm_eligible=False,
            requires_operator_approval=True,
            existing_link_posture=existing_posture,
            existing_link_id=existing_id,
            reason_codes=_dedupe_codes(codes),
            explanation=(
                f"Fuzzy advisory candidate(s) only in {provider}; manual operator review required."
            ),
            selected_candidate=ordered[0] if len(ordered) == 1 else None,
            candidates=ordered,
            truncated=truncated,
        )

    if len(ordered) > 1:
        author_matches = [
            item
            for item in ordered
            if item.authorship_relation in {"exact", "compatible_normalized"}
        ]
        advisory_author_id = author_matches[0].external_id if len(author_matches) == 1 else None
        codes = [*prefix_codes, "homonym_ambiguity"]
        if advisory_author_id is not None:
            codes.append("authorship_advisory_disambiguation")
        if truncated:
            codes.append("candidate_list_truncated")
        eligible_count = sum(1 for item in ordered if item.provider_eligible)
        confidence: ConfidenceTier = (
            "medium" if (advisory_author_id is not None or eligible_count == 1) else "low"
        )
        return ProviderMatchOutcome(
            provider=provider,
            source_available=True,
            source_version=source_version,
            source_checksum=source_checksum,
            outcome="ambiguous",
            confidence=confidence,
            auto_confirm_eligible=False,
            requires_operator_approval=True,
            existing_link_posture=existing_posture,
            existing_link_id=existing_id,
            reason_codes=_dedupe_codes(codes),
            explanation=(
                f"{len(ordered)} homonym/duplicate candidates matched '{identity.scientific_name}' "
                f"in {provider}; explicit operator selection required."
            ),
            selected_candidate=None,
            candidates=ordered,
            advisory_authorship_candidate_id=advisory_author_id,
            truncated=truncated,
        )

    candidate = ordered[0]
    if not candidate.provider_eligible:
        codes = [*prefix_codes, candidate.ineligible_reason or "provider_ineligible"]
        has_accepted_target = (
            candidate.accepted_external_id != candidate.external_id
            and (candidate.accepted_status or "").casefold() == "accepted"
        )
        if has_accepted_target:
            codes.append("resolved_accepted_target_available")
            explanation = (
                f"Matched {candidate.taxonomic_status.lower()} '{candidate.scientific_name}' "
                f"in {provider}, which resolves to accepted taxon "
                f"'{candidate.accepted_scientific_name}' ({candidate.accepted_external_id}); "
                "source contract does not allow direct link confirmation on this record."
            )
            in_confidence: ConfidenceTier = "high"
            needs_review = True
        else:
            explanation = (
                f"Matched record '{candidate.scientific_name}' ({candidate.external_id}) "
                f"in {provider} is ineligible ({candidate.ineligible_reason})."
            )
            in_confidence = "none"
            needs_review = False
        if truncated:
            codes.append("candidate_list_truncated")
        return ProviderMatchOutcome(
            provider=provider,
            source_available=True,
            source_version=source_version,
            source_checksum=source_checksum,
            outcome="ineligible",
            confidence=in_confidence,
            auto_confirm_eligible=False,
            requires_operator_approval=needs_review,
            existing_link_posture=existing_posture,
            existing_link_id=existing_id,
            reason_codes=_dedupe_codes(codes),
            explanation=explanation,
            selected_candidate=candidate,
            candidates=[candidate],
            truncated=truncated,
        )

    # Preserve already-linked non-synthetic records cleanly.
    if (
        existing_posture == "existing_verified_or_manual_current"
        and existing_id == candidate.external_id
    ):
        return ProviderMatchOutcome(
            provider=provider,
            source_available=True,
            source_version=source_version,
            source_checksum=source_checksum,
            outcome="already_linked",
            confidence="exact",
            auto_confirm_eligible=False,
            requires_operator_approval=False,
            existing_link_posture=existing_posture,
            existing_link_id=existing_id,
            reason_codes=_dedupe_codes(
                ["existing_link_preserved", "existing_link_matches_candidate"]
            ),
            explanation=(
                f"Identity already holds a verified/manual {provider} link "
                f"({candidate.external_id}) matching this taxon."
            ),
            selected_candidate=candidate,
            candidates=[candidate],
            truncated=truncated,
        )

    review_reasons: list[str] = []
    if existing_posture in {
        "existing_verified_or_manual_current",
        "existing_verified_or_manual_stale",
    }:
        review_reasons.append("existing_link_preserved")
        if existing_id != candidate.external_id:
            review_reasons.append("existing_link_differs_from_candidate")
        if existing_posture == "existing_verified_or_manual_stale":
            review_reasons.append("existing_link_stale")

    if candidate.taxonomic_status.casefold() == "synonym":
        review_reasons.append("wfo_synonym_matched")
    if normalized.has_cultivar:
        review_reasons.append("cultivar_species_anchor")
    if normalized.inline_cultivar_syntax:
        review_reasons.append("inline_cultivar_syntax")

    if candidate.match_basis == "hybrid_marker_dropped":
        review_reasons.append("hybrid_marker_dropped")
    elif candidate.match_basis in {"hybrid_sign_normalized", "hybrid_spacing_normalized"}:
        review_reasons.append("hybrid_notation_variant")
    elif candidate.match_basis == "rank_token_normalized":
        review_reasons.append("rank_token_normalized")
    elif candidate.match_basis == "inline_authorship_stripped":
        review_reasons.append("inline_authorship_advisory")
    elif candidate.match_basis == "inline_cultivar_stripped":
        review_reasons.append("inline_cultivar_syntax")

    if candidate.authorship_relation == "mismatch":
        review_reasons.append("authorship_mismatch")

    rank_mismatch, rank_above = _check_rank_alignment(
        normalized.detected_rank_shape, normalized.infraspecific_ranks, candidate.rank
    )
    if rank_mismatch:
        review_reasons.append("rank_mismatch")
    if rank_above:
        review_reasons.append("rank_above_species")

    if truncated:
        review_reasons.append("candidate_list_truncated")

    if not review_reasons:
        codes = [*prefix_codes, "exact_accepted_match"]
        return ProviderMatchOutcome(
            provider=provider,
            source_available=True,
            source_version=source_version,
            source_checksum=source_checksum,
            outcome="auto_eligible",
            confidence="exact",
            auto_confirm_eligible=True,
            requires_operator_approval=False,
            existing_link_posture=existing_posture,
            existing_link_id=existing_id,
            reason_codes=_dedupe_codes(codes),
            explanation=(
                f"Unique exact accepted match in {provider}: "
                f"{candidate.scientific_name} ({candidate.external_id})."
            ),
            selected_candidate=candidate,
            candidates=[candidate],
            truncated=truncated,
        )

    confidence_out: ConfidenceTier
    if "hybrid_marker_dropped" in review_reasons:
        confidence_out = "low"
    elif any(
        code in review_reasons
        for code in ("rank_mismatch", "authorship_mismatch", "rank_above_species")
    ):
        confidence_out = "medium"
    else:
        confidence_out = "high"

    return ProviderMatchOutcome(
        provider=provider,
        source_available=True,
        source_version=source_version,
        source_checksum=source_checksum,
        outcome="review_required",
        confidence=confidence_out,
        auto_confirm_eligible=False,
        requires_operator_approval=True,
        existing_link_posture=existing_posture,
        existing_link_id=existing_id,
        reason_codes=_dedupe_codes([*prefix_codes, *review_reasons]),
        explanation=(
            f"Candidate '{candidate.scientific_name}' ({candidate.external_id}) matched in "
            f"{provider}; operator review required ({', '.join(review_reasons)})."
        ),
        selected_candidate=candidate,
        candidates=[candidate],
        truncated=truncated,
    )


def _resolved_name_and_status(
    outcome: ProviderMatchOutcome,
) -> tuple[str | None, str | None, str | None]:
    selected = outcome.selected_candidate
    if not outcome.source_available or selected is None:
        return None, None, None
    if selected.match_basis == "fuzzy_genus_fallback":
        return None, None, None
    accepted_name = selected.accepted_scientific_name or selected.scientific_name
    return accepted_name, selected.taxonomic_status.casefold(), selected.accepted_external_id


def _downgrade_for_conflict(
    outcome: ProviderMatchOutcome, conflict_code: str
) -> ProviderMatchOutcome:
    updated_codes = _dedupe_codes([*outcome.reason_codes, conflict_code])
    if outcome.outcome == "auto_eligible":
        return outcome.model_copy(
            update={
                "outcome": "review_required",
                "auto_confirm_eligible": False,
                "requires_operator_approval": True,
                "reason_codes": updated_codes,
                "explanation": (
                    f"{outcome.explanation} Blocked from auto-confirm by {conflict_code}."
                ),
            }
        )
    if updated_codes != outcome.reason_codes:
        return outcome.model_copy(update={"reason_codes": updated_codes})
    return outcome


def combine_identity_outcomes(
    *,
    identity: IdentityMatchInput,
    normalized: NormalizedNameAnalysis,
    wfo: ProviderMatchOutcome,
    wcvp_v16: ProviderMatchOutcome,
    wcvp_v15: ProviderMatchOutcome | None = None,
) -> IdentityMatchResult:
    """Detect cross-source disagreements and roll up the explainable identity outcome."""
    disagreements: list[CrossSourceDisagreement] = []
    substantive_conflict = False

    wfo_acc, wfo_status, _ = _resolved_name_and_status(wfo)
    v16_acc, v16_status, v16_acc_id = _resolved_name_and_status(wcvp_v16)

    if wfo_acc and v16_acc:
        wfo_sem = semantic_comparison_key(wfo_acc)
        v16_sem = semantic_comparison_key(v16_acc)
        if wfo_sem != v16_sem:
            substantive_conflict = True
            disagreements.append(
                CrossSourceDisagreement(
                    kind="cross_source_accepted_name_conflict",
                    sources=["wfo", "wcvp_v16"],
                    message=(
                        f"WFO resolves candidate ({wfo_status}) to accepted taxon '{wfo_acc}' "
                        f"whereas WCVP v16 resolves candidate ({v16_status}) to accepted taxon "
                        f"'{v16_acc}'."
                    ),
                )
            )
        elif normalize_whitespace(wfo_acc).casefold() != normalize_whitespace(v16_acc).casefold():
            disagreements.append(
                CrossSourceDisagreement(
                    kind="cross_source_formatting_difference",
                    sources=["wfo", "wcvp_v16"],
                    message=(
                        f"WFO accepted name '{wfo_acc}' and WCVP v16 accepted name '{v16_acc}' "
                        "differ in hybrid or rank formatting."
                    ),
                )
            )

    if (
        wfo.selected_candidate is not None
        and wcvp_v16.selected_candidate is not None
        and wfo_status is not None
        and v16_status is not None
    ):
        wfo_is_acc = wfo_status == "accepted"
        v16_is_acc = v16_status == "accepted"
        if wfo_is_acc != v16_is_acc:
            substantive_conflict = True
            disagreements.append(
                CrossSourceDisagreement(
                    kind="cross_source_status_divergence",
                    sources=["wfo", "wcvp_v16"],
                    message=(
                        f"WFO classifies candidate as '{wfo.selected_candidate.taxonomic_status}' "
                        f"while WCVP v16 classifies candidate as "
                        f"'{wcvp_v16.selected_candidate.taxonomic_status}'."
                    ),
                )
            )

    if wcvp_v15 is not None:
        v15_acc, v15_status, v15_acc_id = _resolved_name_and_status(wcvp_v15)
        if (
            v15_acc
            and v16_acc
            and v15_status
            and v16_status
            and (
                semantic_comparison_key(v15_acc) != semantic_comparison_key(v16_acc)
                or v15_status != v16_status
                or v15_acc_id != v16_acc_id
            )
        ):
            substantive_conflict = True
            disagreements.append(
                CrossSourceDisagreement(
                    kind="wcvp_version_conflict",
                    sources=["wcvp_v15", "wcvp_v16"],
                    message=(
                        f"WCVP v15 ({v15_status}: {v15_acc}) and WCVP v16 "
                        f"({v16_status}: {v16_acc}) disagree."
                    ),
                )
            )

    gbif_link = identity.existing_links.get("gbif")
    if gbif_link is not None:
        gbif_posture, _ = classify_existing_link(gbif_link, live_checksum=None, live_version=None)
        gbif_acc = gbif_link.accepted_scientific_name or gbif_link.scientific_name
        if gbif_acc and gbif_posture != "synthetic_golden":
            gbif_sem = semantic_comparison_key(gbif_acc)
            for label, other_acc in (("wfo", wfo_acc), ("wcvp_v16", v16_acc)):
                if other_acc and semantic_comparison_key(other_acc) != gbif_sem:
                    substantive_conflict = True
                    disagreements.append(
                        CrossSourceDisagreement(
                            kind="existing_gbif_conflict",
                            sources=[label, "gbif"],
                            message=(
                                f"Existing GBIF link resolves to '{gbif_acc}', disagreeing with "
                                f"{label} ('{other_acc}')."
                            ),
                        )
                    )
                    break

    if substantive_conflict:
        wfo = _downgrade_for_conflict(wfo, "cross_source_conflict")
        wcvp_v16 = _downgrade_for_conflict(wcvp_v16, "cross_source_conflict")
        if wcvp_v15 is not None:
            wcvp_v15 = _downgrade_for_conflict(wcvp_v15, "cross_source_conflict")

    evaluated = [item for item in (wfo, wcvp_v16) if item.source_available]
    all_codes = _dedupe_codes(
        [
            *wfo.reason_codes,
            *wcvp_v16.reason_codes,
            *(wcvp_v15.reason_codes if wcvp_v15 is not None else ()),
            *(item.kind for item in disagreements),
        ]
    )

    overall_status: IdentityOverallStatus
    if not evaluated:
        overall_status = "source_unavailable"
    elif substantive_conflict:
        overall_status = "conflict"
    elif all(item.outcome == "already_linked" for item in evaluated):
        overall_status = "already_verified"
    elif all(item.outcome in {"auto_eligible", "already_linked"} for item in evaluated) and any(
        item.outcome == "auto_eligible" for item in evaluated
    ):
        overall_status = "ready_exact"
    elif all(item.outcome == "no_match" for item in evaluated):
        overall_status = "unmatched"
    elif all(
        item.outcome in {"ineligible", "no_match"} and not item.requires_operator_approval
        for item in evaluated
    ) and any(item.outcome == "ineligible" for item in evaluated):
        overall_status = "ineligible"
    else:
        wfo_covered = wfo.source_available and wfo.outcome not in {"no_match", "source_unavailable"}
        v16_covered = wcvp_v16.source_available and wcvp_v16.outcome not in {
            "no_match",
            "source_unavailable",
        }
        if (wfo.source_available and wcvp_v16.source_available) and (wfo_covered != v16_covered):
            all_codes = _dedupe_codes([*all_codes, "single_source_coverage_only"])
        overall_status = "needs_review"

    return IdentityMatchResult(
        identity=identity,
        normalized=normalized,
        overall_status=overall_status,
        reason_codes=all_codes,
        wfo=wfo,
        wcvp_v16=wcvp_v16,
        wcvp_v15=wcvp_v15,
        disagreements=disagreements,
        existing_gbif_link=gbif_link,
    )
