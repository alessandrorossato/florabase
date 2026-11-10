from datetime import UTC, datetime, timedelta
from typing import Literal, cast
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import (
    BotanicalIdentity,
    BotanicalIdentityName,
    BotanicalIdentityReconciliation,
)
from florabase.botanical_identities.schemas import (
    AcceptedNameCorrectionWrite,
    AcceptedNameSuggestionResponse,
    BotanicalIdentityResponse,
    CollidingIdentitySummary,
    DuplicateIdentityMergeWrite,
    HistoricalNameStatusKind,
    IdentityCollectionCounts,
    IdentityHistoricalNameResponse,
    IdentityReconciliationEventResponse,
    IdentityReconciliationResponse,
    ReconciliationConflictResponse,
    ReconciliationSourceProvider,
    SourceTaxonomicAssessmentResponse,
    format_identity_display_label,
)
from florabase.botanical_identities.service import (
    UNIQUE_IDENTITY_CONSTRAINT,
    _constraint_name,
    find_duplicate,
)
from florabase.botanical_profiles.model import (
    PROFILE_FIELDS,
    BotanicalProfile,
    BotanicalProfileNativeRange,
)
from florabase.collection_photos.model import BotanicalIdentityCoverImage
from florabase.cuttings.model import PropagationAttempt, VegetativeLot
from florabase.external_botany.model import ExternalTaxonLink
from florabase.lineage.service import lock_lineage_writes
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
    WcvpSource,
)
from florabase.plants.model import Plant, PlantGroup
from florabase.schedule.model import ScheduledActivity
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing
from florabase.taxonomy.model import WfoLink
from florabase.taxonomy.schemas import TaxonomyEvidence
from florabase.taxonomy.source import (
    SourceUnavailableError as WfoSourceUnavailableError,
)
from florabase.taxonomy.source import (
    WfoSource,
    path,
)

INFRASPECIFIC_MARKERS = frozenset(
    {"subsp.", "ssp.", "var.", "subvar.", "f.", "forma", "subf.", "convar.", "prol."}
)


class ReconciliationNotFoundError(Exception):
    pass


class ReconciliationConflictError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        existing_id: UUID | None = None,
        conflicting_fields: list[str] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.existing_id = existing_id
        self.conflicting_fields = conflicting_fields
        super().__init__(message)


def record_superseded_identity_name(
    database: Session,
    identity: BotanicalIdentity,
    *,
    now: datetime,
    source_provider: ReconciliationSourceProvider = "operator",
    source_version: str | None = None,
    source_taxon_id: str | None = None,
    accepted_source_taxon_id: str | None = None,
    authorship: str | None = None,
) -> BotanicalIdentityName:
    prior = database.scalar(
        select(BotanicalIdentityName)
        .where(
            BotanicalIdentityName.botanical_identity_id == identity.id,
            BotanicalIdentityName.status_kind.in_(("initial_recorded", "former_accepted")),
        )
        .order_by(
            BotanicalIdentityName.superseded_at.desc().nulls_last(),
            BotanicalIdentityName.effective_from.desc(),
            BotanicalIdentityName.id.desc(),
        )
        .limit(1)
    )
    if prior is None:
        status_kind: HistoricalNameStatusKind = "initial_recorded"
        effective_from = identity.created_at
    else:
        status_kind = "former_accepted"
        effective_from = prior.superseded_at or identity.updated_at
    superseded_at = max(now, effective_from)
    entry = BotanicalIdentityName(
        botanical_identity_id=identity.id,
        scientific_name=identity.scientific_name,
        cultivar_name=identity.cultivar_name,
        common_name=identity.common_name,
        authorship=authorship,
        status_kind=status_kind,
        source_provider=source_provider,
        source_version=source_version,
        source_taxon_id=source_taxon_id,
        accepted_source_taxon_id=accepted_source_taxon_id,
        origin_identity_id=None,
        effective_from=effective_from,
        superseded_at=superseded_at,
        created_at=now,
    )
    database.add(entry)
    return entry


def identity_collection_counts(database: Session, identity_id: UUID) -> IdentityCollectionCounts:
    seed_lots = int(
        database.scalar(
            select(func.count())
            .select_from(SeedLot)
            .where(SeedLot.botanical_identity_id == identity_id, SeedLot.lifecycle == "active")
        )
        or 0
    )
    sowings = int(
        database.scalar(
            select(func.count())
            .select_from(Sowing)
            .join(SeedLot, Sowing.seed_lot_id == SeedLot.id)
            .where(SeedLot.botanical_identity_id == identity_id, Sowing.lifecycle == "active")
        )
        or 0
    )
    plants = int(
        database.scalar(
            select(func.count())
            .select_from(Plant)
            .where(Plant.botanical_identity_id == identity_id, Plant.lifecycle == "active")
        )
        or 0
    )
    plant_groups = int(
        database.scalar(
            select(func.count())
            .select_from(PlantGroup)
            .where(
                PlantGroup.botanical_identity_id == identity_id,
                PlantGroup.lifecycle == "active",
            )
        )
        or 0
    )
    vegetative_lots = int(
        database.scalar(
            select(func.count())
            .select_from(VegetativeLot)
            .where(
                VegetativeLot.botanical_identity_id == identity_id,
                VegetativeLot.lifecycle == "active",
            )
        )
        or 0
    )
    propagation_attempts = int(
        database.scalar(
            select(func.count())
            .select_from(PropagationAttempt)
            .join(VegetativeLot, PropagationAttempt.vegetative_lot_id == VegetativeLot.id)
            .where(
                VegetativeLot.botanical_identity_id == identity_id,
                PropagationAttempt.lifecycle == "active",
            )
        )
        or 0
    )
    return IdentityCollectionCounts(
        seed_lots=seed_lots,
        sowings=sowings,
        plants=plants,
        plant_groups=plant_groups,
        vegetative_lots=vegetative_lots,
        propagation_attempts=propagation_attempts,
    )


def _conflicting_profile_fields(
    database: Session, duplicate_id: UUID, survivor_id: UUID
) -> list[str]:
    dup_profile = database.get(BotanicalProfile, duplicate_id)
    surv_profile = database.get(BotanicalProfile, survivor_id)
    if dup_profile is None or surv_profile is None:
        return []
    conflicts: list[str] = []
    for field in PROFILE_FIELDS:
        dup_val = (getattr(dup_profile, field) or "").strip()
        surv_val = (getattr(surv_profile, field) or "").strip()
        if dup_val and surv_val and dup_val != surv_val:
            conflicts.append(field)
    return conflicts


def _colliding_identity_summary(
    database: Session,
    current_identity: BotanicalIdentity,
    target_scientific_name: str,
    target_cultivar_name: str | None,
) -> CollidingIdentitySummary | None:
    existing = find_duplicate(database, target_scientific_name, target_cultivar_name)
    if existing is None or existing.id == current_identity.id:
        return None
    conflicts = _conflicting_profile_fields(database, current_identity.id, existing.id)
    return CollidingIdentitySummary(
        id=existing.id,
        scientific_name=existing.scientific_name,
        cultivar_name=existing.cultivar_name,
        common_name=existing.common_name,
        display_label=format_identity_display_label(
            existing.scientific_name, existing.cultivar_name
        ),
        updated_at=existing.updated_at,
        collection_counts=identity_collection_counts(database, existing.id),
        has_conflicting_profile_fields=bool(conflicts),
        conflicting_profile_fields=conflicts,
    )


def _split_gbif_scientific_name(raw_name: str) -> tuple[str, str | None]:
    tokens = raw_name.split()
    if not tokens:
        return raw_name.strip(), None
    if len(tokens) == 1:
        return tokens[0], None
    idx = 1
    if tokens[1] in {"\u00d7", "x"} and len(tokens) >= 3:
        idx = 3
    elif tokens[1][0].islower() or tokens[1].startswith("\u00d7"):
        idx = 2
    if len(tokens) >= idx + 2 and tokens[idx].lower() in INFRASPECIFIC_MARKERS:
        idx += 2
    canonical = " ".join(tokens[:idx])
    authorship = " ".join(tokens[idx:]).strip() or None
    return canonical, authorship


def _historical_name_response(entry: BotanicalIdentityName) -> IdentityHistoricalNameResponse:
    return IdentityHistoricalNameResponse(
        id=entry.id,
        scientific_name=entry.scientific_name,
        cultivar_name=entry.cultivar_name,
        common_name=entry.common_name,
        display_label=format_identity_display_label(entry.scientific_name, entry.cultivar_name),
        authorship=entry.authorship,
        status_kind=cast(HistoricalNameStatusKind, entry.status_kind),
        source_provider=cast(ReconciliationSourceProvider, entry.source_provider),
        source_version=entry.source_version,
        source_taxon_id=entry.source_taxon_id,
        accepted_source_taxon_id=entry.accepted_source_taxon_id,
        origin_identity_id=entry.origin_identity_id,
        effective_from=entry.effective_from,
        superseded_at=entry.superseded_at,
    )


def _reconciliation_event_response(
    event: BotanicalIdentityReconciliation,
) -> IdentityReconciliationEventResponse:
    return IdentityReconciliationEventResponse(
        id=event.id,
        kind=cast(Literal["accepted_name_correction", "duplicate_identity_merge"], event.kind),
        previous_scientific_name=event.previous_scientific_name,
        previous_cultivar_name=event.previous_cultivar_name,
        previous_common_name=event.previous_common_name,
        applied_scientific_name=event.applied_scientific_name,
        applied_cultivar_name=event.applied_cultivar_name,
        applied_common_name=event.applied_common_name,
        source_provider=cast(ReconciliationSourceProvider, event.source_provider),
        duplicate_identity_id=event.duplicate_identity_id,
        evidence=dict(event.evidence),
        created_at=event.created_at,
    )


def _inspect_wfo(
    database: Session,
    identity: BotanicalIdentity,
    wfo_source: WfoSource | None,
) -> tuple[list[SourceTaxonomicAssessmentResponse], list[AcceptedNameSuggestionResponse]]:
    assessments: list[SourceTaxonomicAssessmentResponse] = []
    suggestions: list[AcceptedNameSuggestionResponse] = []
    link = database.get(WfoLink, identity.id)
    live_metadata = None
    if wfo_source is not None:
        try:
            live_metadata = wfo_source.metadata()
        except WfoSourceUnavailableError:
            live_metadata = None

    if link is not None:
        try:
            evidence = TaxonomyEvidence.model_validate(link.evidence)
        except ValidationError:
            assessments.append(
                SourceTaxonomicAssessmentResponse(
                    source_provider="wfo",
                    source_label="World Flora Online",
                    linked=True,
                    link_version=link.version,
                    stale=True,
                    taxon_id=link.external_id,
                    message="Stored WFO link evidence is invalid; review the link.",
                )
            )
            return assessments, suggestions

        stale = evidence.identity_updated_at != identity.updated_at
        if live_metadata is not None and (
            evidence.source.checksum != live_metadata.checksum
            or evidence.source.version != live_metadata.version
        ):
            stale = True

        accepted_taxon = (
            evidence.classification[-1]
            if evidence.taxon.taxonomic_status == "synonym" and evidence.classification
            else evidence.taxon
        )
        accepted_authorship = accepted_taxon.authorship or None
        if wfo_source is not None and live_metadata is not None:
            try:
                nodes = wfo_source.hierarchy([link.external_id])
                live_path = path(nodes, link.external_id)
                if not live_path or live_path != evidence.classification:
                    stale = True
                elif live_path:
                    accepted_taxon = live_path[-1]
                    accepted_authorship = accepted_taxon.authorship or None
            except WfoSourceUnavailableError:
                pass

        label = f"World Flora Online ({evidence.source.version})"
        assessments.append(
            SourceTaxonomicAssessmentResponse(
                source_provider="wfo",
                source_label=label,
                source_version=evidence.source.version,
                source_checksum=evidence.source.checksum,
                linked=True,
                link_version=link.version,
                stale=stale,
                taxon_id=evidence.taxon.source_taxon_id,
                scientific_name=evidence.taxon.scientific_name,
                authorship=evidence.taxon.authorship or None,
                status=evidence.taxon.taxonomic_status,
                accepted_taxon_id=accepted_taxon.source_taxon_id,
                accepted_scientific_name=accepted_taxon.scientific_name,
                accepted_authorship=accepted_authorship,
                message=(
                    f"Confirmed WFO synonym of {accepted_taxon.scientific_name}."
                    if evidence.taxon.taxonomic_status == "synonym"
                    else "Confirmed WFO accepted taxon."
                ),
            )
        )
        if (
            evidence.taxon.taxonomic_status == "synonym"
            or accepted_taxon.scientific_name.casefold() != identity.scientific_name.casefold()
        ) and accepted_taxon.scientific_name.casefold() != identity.scientific_name.casefold():
            suggestions.append(
                AcceptedNameSuggestionResponse(
                    suggestion_id=(
                        f"wfo:{evidence.source.version}:{evidence.taxon.source_taxon_id}:"
                        f"{accepted_taxon.source_taxon_id}"
                    ),
                    source_provider="wfo",
                    source_label=label,
                    source_version=evidence.source.version,
                    source_checksum=evidence.source.checksum,
                    link_version=link.version,
                    matched_taxon_id=evidence.taxon.source_taxon_id,
                    matched_scientific_name=evidence.taxon.scientific_name,
                    matched_authorship=evidence.taxon.authorship or None,
                    matched_status=evidence.taxon.taxonomic_status,
                    accepted_taxon_id=accepted_taxon.source_taxon_id,
                    accepted_scientific_name=accepted_taxon.scientific_name,
                    accepted_authorship=accepted_authorship,
                    accepted_rank=accepted_taxon.rank,
                    stale=stale,
                    advisory_note=(
                        "Identity changed since WFO confirmation; review before applying."
                        if stale
                        else None
                    ),
                    colliding_identity=_colliding_identity_summary(
                        database,
                        identity,
                        accepted_taxon.scientific_name,
                        identity.cultivar_name,
                    ),
                )
            )
        return assessments, suggestions

    if wfo_source is not None and live_metadata is not None:
        label = f"World Flora Online ({live_metadata.version})"
        try:
            candidates = [
                candidate
                for candidate in wfo_source.search(identity.scientific_name)
                if candidate.taxon.scientific_name.casefold() == identity.scientific_name.casefold()
            ]
        except WfoSourceUnavailableError:
            candidates = []
        if len(candidates) == 1:
            candidate = candidates[0]
            accepted = (
                candidate.classification[-1]
                if candidate.taxon.taxonomic_status == "synonym" and candidate.classification
                else candidate.taxon
            )
            assessments.append(
                SourceTaxonomicAssessmentResponse(
                    source_provider="wfo",
                    source_label=label,
                    source_version=live_metadata.version,
                    source_checksum=live_metadata.checksum,
                    linked=False,
                    taxon_id=candidate.taxon.source_taxon_id,
                    scientific_name=candidate.taxon.scientific_name,
                    authorship=candidate.taxon.authorship or None,
                    status=candidate.taxon.taxonomic_status,
                    accepted_taxon_id=accepted.source_taxon_id,
                    accepted_scientific_name=accepted.scientific_name,
                    accepted_authorship=accepted.authorship or None,
                    message="Advisory exact-name match in local WFO snapshot (unlinked).",
                )
            )
            if (
                candidate.taxon.taxonomic_status == "synonym"
                and accepted.scientific_name.casefold() != identity.scientific_name.casefold()
            ):
                suggestions.append(
                    AcceptedNameSuggestionResponse(
                        suggestion_id=(
                            f"wfo:{live_metadata.version}:{candidate.taxon.source_taxon_id}:"
                            f"{accepted.source_taxon_id}"
                        ),
                        source_provider="wfo",
                        source_label=label,
                        source_version=live_metadata.version,
                        source_checksum=live_metadata.checksum,
                        link_version=None,
                        matched_taxon_id=candidate.taxon.source_taxon_id,
                        matched_scientific_name=candidate.taxon.scientific_name,
                        matched_authorship=candidate.taxon.authorship or None,
                        matched_status=candidate.taxon.taxonomic_status,
                        accepted_taxon_id=accepted.source_taxon_id,
                        accepted_scientific_name=accepted.scientific_name,
                        accepted_authorship=accepted.authorship or None,
                        accepted_rank=accepted.rank,
                        stale=False,
                        advisory_note="Unlinked exact-name match in local WFO snapshot.",
                        colliding_identity=_colliding_identity_summary(
                            database,
                            identity,
                            accepted.scientific_name,
                            identity.cultivar_name,
                        ),
                    )
                )
    return assessments, suggestions


def _inspect_wcvp_release(
    database: Session,
    identity: BotanicalIdentity,
    wcvp_link: WcvpLink | None,
    source: WcvpSource | None,
) -> tuple[SourceTaxonomicAssessmentResponse | None, AcceptedNameSuggestionResponse | None]:
    if source is None:
        return None, None
    try:
        metadata = source.metadata()
    except WcvpSourceUnavailableError:
        return None, None

    matched_taxon: WcvpTaxon | None = None
    linked_for_release = False
    stale = False
    if wcvp_link is not None:
        try:
            link_source = WcvpSourceMetadata.model_validate(wcvp_link.source)
        except ValidationError:
            link_source = None
        if link_source is not None and link_source.version == metadata.version:
            linked_for_release = True
            snap_name = str(wcvp_link.identity_snapshot.get("scientific_name") or "")
            stale = (
                snap_name.casefold() != identity.scientific_name.casefold()
                or link_source.checksum != metadata.checksum
            )
        try:
            candidate = source.taxon(wcvp_link.external_id)
            if (
                linked_for_release
                or candidate.name.casefold() == identity.scientific_name.casefold()
            ):
                matched_taxon = candidate
        except WcvpSourceUnavailableError:
            matched_taxon = None

    if matched_taxon is None:
        try:
            exact = [
                t
                for t in source.search(identity.scientific_name)
                if t.name.casefold() == identity.scientific_name.casefold()
            ]
        except WcvpSourceUnavailableError:
            exact = []
        if len(exact) == 1:
            matched_taxon = exact[0]
        elif len(exact) > 1:
            synonyms = [t for t in exact if t.status.lower() == "synonym" and t.accepted_name]
            accepted_exact = [t for t in exact if t.status.lower() == "accepted"]
            if len(accepted_exact) == 1 and not synonyms:
                matched_taxon = accepted_exact[0]
            elif len(synonyms) == 1 and not accepted_exact:
                matched_taxon = synonyms[0]

    if matched_taxon is None:
        return None, None

    accepted_id = matched_taxon.accepted_id or matched_taxon.external_id
    accepted_name = matched_taxon.accepted_name or matched_taxon.name
    accepted_authorship: str | None = matched_taxon.authorship or None
    accepted_rank: str | None = matched_taxon.rank
    if accepted_id and accepted_id != matched_taxon.external_id:
        try:
            accepted_obj = source.taxon(accepted_id)
            accepted_name = accepted_obj.name
            accepted_authorship = accepted_obj.authorship or None
            accepted_rank = accepted_obj.rank
        except WcvpSourceUnavailableError:
            accepted_authorship = None

    label = f"Kew WCVP v{metadata.version}"
    assessment = SourceTaxonomicAssessmentResponse(
        source_provider="wcvp",
        source_label=label,
        source_version=metadata.version,
        source_checksum=metadata.checksum,
        linked=linked_for_release,
        link_version=wcvp_link.version if linked_for_release and wcvp_link is not None else None,
        stale=stale,
        taxon_id=matched_taxon.external_id,
        scientific_name=matched_taxon.name,
        authorship=matched_taxon.authorship or None,
        status=matched_taxon.status,
        accepted_taxon_id=accepted_id,
        accepted_scientific_name=accepted_name,
        accepted_authorship=accepted_authorship,
        message=(
            f"WCVP v{metadata.version} {matched_taxon.status.lower()}"
            + (
                f" of {accepted_name}."
                if accepted_name.casefold() != matched_taxon.name.casefold()
                else "."
            )
        ),
    )

    suggestion: AcceptedNameSuggestionResponse | None = None
    if (
        matched_taxon.status.lower() != "accepted"
        and accepted_name
        and accepted_name.casefold() != identity.scientific_name.casefold()
    ):
        suggestion = AcceptedNameSuggestionResponse(
            suggestion_id=(f"wcvp:{metadata.version}:{matched_taxon.external_id}:{accepted_id}"),
            source_provider="wcvp",
            source_label=label,
            source_version=metadata.version,
            source_checksum=metadata.checksum,
            link_version=(
                wcvp_link.version if linked_for_release and wcvp_link is not None else None
            ),
            matched_taxon_id=matched_taxon.external_id,
            matched_scientific_name=matched_taxon.name,
            matched_authorship=matched_taxon.authorship or None,
            matched_status=matched_taxon.status,
            accepted_taxon_id=accepted_id,
            accepted_scientific_name=accepted_name,
            accepted_authorship=accepted_authorship,
            accepted_rank=accepted_rank,
            stale=stale,
            advisory_note=(
                f"Confirmed WCVP link is on a different release than v{metadata.version}."
                if wcvp_link is not None and not linked_for_release
                else None
            ),
            colliding_identity=_colliding_identity_summary(
                database,
                identity,
                accepted_name,
                identity.cultivar_name,
            ),
        )
    return assessment, suggestion


def _inspect_wcvp(
    database: Session,
    identity: BotanicalIdentity,
    wcvp_v15_source: WcvpSource | None,
    wcvp_v16_source: WcvpSource | None,
) -> tuple[
    list[SourceTaxonomicAssessmentResponse],
    list[AcceptedNameSuggestionResponse],
    list[ReconciliationConflictResponse],
]:
    assessments: list[SourceTaxonomicAssessmentResponse] = []
    suggestions: list[AcceptedNameSuggestionResponse] = []
    conflicts: list[ReconciliationConflictResponse] = []
    wcvp_link = database.get(WcvpLink, identity.id)

    v15_assessment, v15_suggestion = _inspect_wcvp_release(
        database, identity, wcvp_link, wcvp_v15_source
    )
    v16_assessment, v16_suggestion = _inspect_wcvp_release(
        database, identity, wcvp_link, wcvp_v16_source
    )

    if v15_assessment is not None:
        assessments.append(v15_assessment)
    if v15_suggestion is not None:
        suggestions.append(v15_suggestion)
    if v16_assessment is not None:
        assessments.append(v16_assessment)
    if v16_suggestion is not None:
        suggestions.append(v16_suggestion)

    if wcvp_link is not None and v15_assessment is None and v16_assessment is None:
        try:
            stored_taxon = WcvpTaxon.model_validate(wcvp_link.taxon)
            stored_source = WcvpSourceMetadata.model_validate(wcvp_link.source)
            accepted_name = stored_taxon.accepted_name or stored_taxon.name
            accepted_id = stored_taxon.accepted_id or stored_taxon.external_id
            stale = (
                str(wcvp_link.identity_snapshot.get("scientific_name") or "").casefold()
                != identity.scientific_name.casefold()
            )
            label = f"Kew WCVP v{stored_source.version}"
            assessments.append(
                SourceTaxonomicAssessmentResponse(
                    source_provider="wcvp",
                    source_label=label,
                    source_version=stored_source.version,
                    source_checksum=stored_source.checksum,
                    linked=True,
                    link_version=wcvp_link.version,
                    stale=stale,
                    taxon_id=stored_taxon.external_id,
                    scientific_name=stored_taxon.name,
                    authorship=stored_taxon.authorship or None,
                    status=stored_taxon.status,
                    accepted_taxon_id=accepted_id,
                    accepted_scientific_name=accepted_name,
                    accepted_authorship=stored_taxon.authorship or None,
                    message=f"Stored WCVP v{stored_source.version} link evidence.",
                )
            )
            if (
                stored_taxon.status.lower() != "accepted"
                and accepted_name.casefold() != identity.scientific_name.casefold()
            ):
                suggestions.append(
                    AcceptedNameSuggestionResponse(
                        suggestion_id=(
                            f"wcvp:{stored_source.version}:{stored_taxon.external_id}:{accepted_id}"
                        ),
                        source_provider="wcvp",
                        source_label=label,
                        source_version=stored_source.version,
                        source_checksum=stored_source.checksum,
                        link_version=wcvp_link.version,
                        matched_taxon_id=stored_taxon.external_id,
                        matched_scientific_name=stored_taxon.name,
                        matched_authorship=stored_taxon.authorship or None,
                        matched_status=stored_taxon.status,
                        accepted_taxon_id=accepted_id,
                        accepted_scientific_name=accepted_name,
                        accepted_authorship=None,
                        accepted_rank=stored_taxon.rank,
                        stale=stale,
                        colliding_identity=_colliding_identity_summary(
                            database,
                            identity,
                            accepted_name,
                            identity.cultivar_name,
                        ),
                    )
                )
        except ValidationError:
            pass

    if v15_assessment is not None and v16_assessment is not None:
        v15_acc = (
            v15_assessment.accepted_scientific_name or v15_assessment.scientific_name or ""
        ).casefold()
        v16_acc = (
            v16_assessment.accepted_scientific_name or v16_assessment.scientific_name or ""
        ).casefold()
        v15_status = (v15_assessment.status or "").casefold()
        v16_status = (v16_assessment.status or "").casefold()
        if (
            v15_status != v16_status
            or v15_acc != v16_acc
            or v15_assessment.accepted_taxon_id != v16_assessment.accepted_taxon_id
        ):
            v15_display = v15_assessment.accepted_scientific_name or v15_assessment.scientific_name
            v16_display = v16_assessment.accepted_scientific_name or v16_assessment.scientific_name
            conflicts.append(
                ReconciliationConflictResponse(
                    kind="wcvp_version_conflict",
                    message=(
                        f"WCVP v15 ({v15_assessment.status}: {v15_display}) "
                        f"and WCVP v16 ({v16_assessment.status}: {v16_display}) "
                        "disagree on taxonomic status or accepted placement."
                    ),
                    sources=["wcvp:15", "wcvp:16"],
                )
            )
    return assessments, suggestions, conflicts


def _inspect_gbif(
    database: Session,
    identity: BotanicalIdentity,
) -> tuple[list[SourceTaxonomicAssessmentResponse], list[AcceptedNameSuggestionResponse]]:
    assessments: list[SourceTaxonomicAssessmentResponse] = []
    suggestions: list[AcceptedNameSuggestionResponse] = []
    link = database.scalar(
        select(ExternalTaxonLink).where(
            ExternalTaxonLink.botanical_identity_id == identity.id,
            ExternalTaxonLink.provider == "gbif",
        )
    )
    if link is None:
        return assessments, suggestions

    matched_canonical = link.canonical_name or _split_gbif_scientific_name(link.scientific_name)[0]
    accepted_canonical = matched_canonical
    accepted_authorship: str | None = link.authorship
    advisory_note: str | None = None
    if link.accepted_name:
        accepted_canonical, parsed_authorship = _split_gbif_scientific_name(link.accepted_name)
        accepted_authorship = parsed_authorship
        if parsed_authorship:
            advisory_note = (
                f"Derived canonical scientific name '{accepted_canonical}' from GBIF "
                f"accepted_name '{link.accepted_name}'."
            )

    status_text = link.taxonomic_status or "UNKNOWN"
    accepted_id = link.accepted_external_id or link.external_id
    assessments.append(
        SourceTaxonomicAssessmentResponse(
            source_provider="gbif",
            source_label="GBIF / Catalogue of Life XR",
            source_version=link.last_refreshed_at.date().isoformat(),
            source_checksum=None,
            linked=True,
            link_version=link.id,
            stale=bool(link.refresh_error),
            taxon_id=link.external_id,
            scientific_name=matched_canonical,
            authorship=link.authorship,
            status=status_text,
            accepted_taxon_id=accepted_id,
            accepted_scientific_name=accepted_canonical,
            accepted_authorship=accepted_authorship,
            message=(
                f"GBIF / CoL XR {status_text.lower()}"
                + (
                    f" of {accepted_canonical}."
                    if accepted_canonical.casefold() != matched_canonical.casefold()
                    else "."
                )
            ),
        )
    )
    if (
        status_text.upper() != "ACCEPTED"
        and accepted_canonical
        and accepted_canonical.casefold() != identity.scientific_name.casefold()
    ):
        suggestions.append(
            AcceptedNameSuggestionResponse(
                suggestion_id=f"gbif:{link.external_id}:{accepted_id}",
                source_provider="gbif",
                source_label="GBIF / Catalogue of Life XR",
                source_version=link.last_refreshed_at.date().isoformat(),
                source_checksum=None,
                link_version=link.id,
                matched_taxon_id=link.external_id,
                matched_scientific_name=matched_canonical,
                matched_authorship=link.authorship,
                matched_status=status_text,
                accepted_taxon_id=accepted_id,
                accepted_scientific_name=accepted_canonical,
                accepted_authorship=accepted_authorship,
                accepted_rank=link.rank,
                stale=bool(link.refresh_error),
                advisory_note=advisory_note,
                colliding_identity=_colliding_identity_summary(
                    database,
                    identity,
                    accepted_canonical,
                    identity.cultivar_name,
                ),
            )
        )
    return assessments, suggestions


def inspect_reconciliation(
    database: Session,
    identity_id: UUID,
    *,
    wfo_source: WfoSource | None = None,
    wcvp_v15_source: WcvpSource | None = None,
    wcvp_v16_source: WcvpSource | None = None,
) -> IdentityReconciliationResponse:
    identity = database.get(BotanicalIdentity, identity_id)
    if identity is None:
        raise ReconciliationNotFoundError("Botanical identity not found.")

    former_rows = list(
        database.scalars(
            select(BotanicalIdentityName)
            .where(BotanicalIdentityName.botanical_identity_id == identity.id)
            .order_by(
                BotanicalIdentityName.effective_from.asc(),
                BotanicalIdentityName.id.asc(),
            )
        )
    )
    former_names = [_historical_name_response(row) for row in former_rows]
    initial_row = next((row for row in former_rows if row.status_kind == "initial_recorded"), None)
    original_scientific_name = (
        initial_row.scientific_name if initial_row is not None else identity.scientific_name
    )
    original_cultivar_name = (
        initial_row.cultivar_name if initial_row is not None else identity.cultivar_name
    )
    original_common_name = (
        initial_row.common_name if initial_row is not None else identity.common_name
    )

    reconciliation_rows = list(
        database.scalars(
            select(BotanicalIdentityReconciliation)
            .where(
                or_(
                    BotanicalIdentityReconciliation.identity_id == identity.id,
                    BotanicalIdentityReconciliation.duplicate_identity_id == identity.id,
                )
            )
            .order_by(
                BotanicalIdentityReconciliation.created_at.desc(),
                BotanicalIdentityReconciliation.id.desc(),
            )
        )
    )
    reconciliations = [_reconciliation_event_response(row) for row in reconciliation_rows]

    wfo_assessments, wfo_suggestions = _inspect_wfo(database, identity, wfo_source)
    wcvp_assessments, wcvp_suggestions, wcvp_conflicts = _inspect_wcvp(
        database, identity, wcvp_v15_source, wcvp_v16_source
    )
    gbif_assessments, gbif_suggestions = _inspect_gbif(database, identity)

    source_assessments = [*wfo_assessments, *wcvp_assessments, *gbif_assessments]
    suggestions = [*wfo_suggestions, *wcvp_suggestions, *gbif_suggestions]
    conflicts: list[ReconciliationConflictResponse] = list(wcvp_conflicts)

    # Check cross-source disagreements across assessments that resolved an accepted name.
    resolved_by_source: dict[str, str] = {}
    display_by_source: dict[str, str] = {}
    for assessment in source_assessments:
        acc_name = assessment.accepted_scientific_name or assessment.scientific_name
        if acc_name:
            key = (
                f"{assessment.source_provider}:{assessment.source_version}"
                if assessment.source_provider == "wcvp" and assessment.source_version
                else assessment.source_provider
            )
            resolved_by_source[key] = acc_name.casefold()
            display_by_source[key] = f"{assessment.source_label} ({acc_name})"

    distinct_accepted = set(resolved_by_source.values())
    if len(distinct_accepted) > 1:
        non_wcvp_only = {k.split(":")[0] for k in resolved_by_source}
        if len(non_wcvp_only) > 1:
            conflicts.append(
                ReconciliationConflictResponse(
                    kind="cross_source_conflict",
                    message=(
                        "Advisory botanical sources disagree on the accepted scientific name: "
                        + ", ".join(display_by_source[k] for k in sorted(display_by_source))
                        + "."
                    ),
                    sources=sorted(resolved_by_source.keys()),
                )
            )

    has_source_conflict = any(
        conflict.kind in {"wcvp_version_conflict", "cross_source_conflict"}
        for conflict in conflicts
    )

    seen_collisions: set[UUID] = set()
    for suggestion in suggestions:
        if (
            suggestion.colliding_identity is not None
            and suggestion.colliding_identity.id not in seen_collisions
        ):
            seen_collisions.add(suggestion.colliding_identity.id)
            conflicts.append(
                ReconciliationConflictResponse(
                    kind="duplicate_identity_collision",
                    message=(
                        f"Suggested accepted name '{suggestion.colliding_identity.display_label}' "
                        "already exists as a separate BotanicalIdentity in the collection. "
                        "In-place correction is refused; use explicit duplicate-identity "
                        "reconciliation to select a survivor and repoint holdings."
                    ),
                    sources=[suggestion.source_provider],
                    colliding_identity_id=suggestion.colliding_identity.id,
                )
            )

    identity_response = BotanicalIdentityResponse.from_model(
        identity,
        collection_counts=identity_collection_counts(database, identity.id),
    )
    return IdentityReconciliationResponse(
        identity=identity_response,
        original_scientific_name=original_scientific_name,
        original_cultivar_name=original_cultivar_name,
        original_common_name=original_common_name,
        original_display_label=format_identity_display_label(
            original_scientific_name, original_cultivar_name
        ),
        former_names=former_names,
        suggestions=suggestions,
        source_assessments=source_assessments,
        conflicts=conflicts,
        has_source_conflict=has_source_conflict,
        reconciliations=reconciliations,
    )


def correct_accepted_name(
    database: Session,
    identity_id: UUID,
    payload: AcceptedNameCorrectionWrite,
    *,
    actor_user_id: UUID | None = None,
    wfo_source: WfoSource | None = None,
    wcvp_v15_source: WcvpSource | None = None,
    wcvp_v16_source: WcvpSource | None = None,
) -> IdentityReconciliationResponse:
    identity = database.scalar(
        select(BotanicalIdentity)
        .where(BotanicalIdentity.id == identity_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if identity is None:
        raise ReconciliationNotFoundError("Botanical identity not found.")
    if identity.merged_into_id is not None:
        raise ReconciliationConflictError(
            code="botanical_identity_merged",
            message=(
                "This botanical identity has been merged into another identity and cannot be "
                "modified."
            ),
            existing_id=identity.merged_into_id,
        )
    if identity.updated_at != payload.identity_updated_at:
        raise ReconciliationConflictError(
            code="reconciliation_stale",
            message=(
                "The botanical identity changed since reconciliation was opened. "
                "Reload and review again."
            ),
        )
    if (
        payload.scientific_name.casefold() == identity.scientific_name.casefold()
        and (payload.cultivar_name or "").casefold() == (identity.cultivar_name or "").casefold()
    ):
        raise ReconciliationConflictError(
            code="reconciliation_noop",
            message=(
                "The proposed accepted name is already the current recorded name of this "
                "botanical identity."
            ),
        )

    existing = find_duplicate(database, payload.scientific_name, payload.cultivar_name)
    if existing is not None and existing.id != identity.id:
        raise ReconciliationConflictError(
            code="duplicate_botanical_identity",
            message=(
                "Another active botanical identity already uses this accepted name and cultivar. "
                "In-place correction never merges duplicate identities; review and confirm "
                "duplicate-identity reconciliation instead."
            ),
            existing_id=existing.id,
        )

    inspection = inspect_reconciliation(
        database,
        identity_id,
        wfo_source=wfo_source,
        wcvp_v15_source=wcvp_v15_source,
        wcvp_v16_source=wcvp_v16_source,
    )
    if inspection.has_source_conflict and not payload.acknowledge_conflict:
        raise ReconciliationConflictError(
            code="reconciliation_conflict_unacknowledged",
            message=(
                "Advisory botanical sources or WCVP releases disagree on the accepted name. "
                "Acknowledge the conflict explicitly before confirming this correction."
            ),
        )

    matched_suggestion: AcceptedNameSuggestionResponse | None = None
    if payload.source_provider != "operator":
        candidates = [
            s
            for s in inspection.suggestions
            if s.source_provider == payload.source_provider
            and s.accepted_scientific_name.casefold() == payload.scientific_name.casefold()
            and (payload.source_version is None or s.source_version == payload.source_version)
            and (
                payload.accepted_taxon_id is None
                or s.accepted_taxon_id == payload.accepted_taxon_id
            )
        ]
        if not candidates:
            raise ReconciliationConflictError(
                code="reconciliation_stale",
                message=(
                    "The selected advisory source suggestion is no longer available or does not "
                    "match the requested accepted name. Reload and review before confirming."
                ),
            )
        matched_suggestion = candidates[0]
        if matched_suggestion.stale:
            raise ReconciliationConflictError(
                code="reconciliation_stale",
                message=(
                    "The selected source suggestion is based on a stale source link. "
                    "Refresh or re-confirm the source link before applying."
                ),
            )
        if (
            matched_suggestion.source_checksum is not None
            and payload.source_checksum != matched_suggestion.source_checksum
        ):
            raise ReconciliationConflictError(
                code="reconciliation_stale",
                message=(
                    "The source snapshot checksum changed or was not provided. "
                    "Reload and review the current snapshot before confirming."
                ),
            )
        if (
            matched_suggestion.link_version is not None
            and payload.link_version != matched_suggestion.link_version
        ):
            raise ReconciliationConflictError(
                code="reconciliation_stale",
                message=(
                    "The confirmed source link version changed. Reload and review before "
                    "confirming."
                ),
            )

    now = datetime.now(UTC)
    previous_scientific_name = identity.scientific_name
    previous_cultivar_name = identity.cultivar_name
    previous_common_name = identity.common_name

    superseded_entry = record_superseded_identity_name(
        database,
        identity,
        now=now,
        source_provider=payload.source_provider,
        source_version=(
            matched_suggestion.source_version
            if matched_suggestion is not None
            else payload.source_version
        ),
        source_taxon_id=(
            matched_suggestion.matched_taxon_id
            if matched_suggestion is not None
            else payload.matched_taxon_id
        ),
        accepted_source_taxon_id=(
            matched_suggestion.accepted_taxon_id
            if matched_suggestion is not None
            else payload.accepted_taxon_id
        ),
        authorship=(
            matched_suggestion.matched_authorship if matched_suggestion is not None else None
        ),
    )

    identity.scientific_name = payload.scientific_name
    identity.cultivar_name = payload.cultivar_name
    identity.common_name = payload.common_name
    identity.updated_at = max(now, identity.updated_at + timedelta(microseconds=1))

    reconciliation = BotanicalIdentityReconciliation(
        identity_id=identity.id,
        duplicate_identity_id=None,
        actor_user_id=actor_user_id,
        kind="accepted_name_correction",
        previous_scientific_name=previous_scientific_name,
        previous_cultivar_name=previous_cultivar_name,
        previous_common_name=previous_common_name,
        applied_scientific_name=identity.scientific_name,
        applied_cultivar_name=identity.cultivar_name,
        applied_common_name=identity.common_name,
        source_provider=payload.source_provider,
        evidence={
            "format_version": "1",
            "superseded_name_id": str(superseded_entry.id),
            "source_provider": payload.source_provider,
            "source_version": (
                matched_suggestion.source_version
                if matched_suggestion is not None
                else payload.source_version
            ),
            "source_checksum": (
                matched_suggestion.source_checksum
                if matched_suggestion is not None
                else payload.source_checksum
            ),
            "link_version": (
                str(matched_suggestion.link_version)
                if matched_suggestion is not None and matched_suggestion.link_version is not None
                else str(payload.link_version)
                if payload.link_version is not None
                else None
            ),
            "matched_taxon_id": (
                matched_suggestion.matched_taxon_id
                if matched_suggestion is not None
                else payload.matched_taxon_id
            ),
            "accepted_taxon_id": (
                matched_suggestion.accepted_taxon_id
                if matched_suggestion is not None
                else payload.accepted_taxon_id
            ),
            "accepted_authorship": (
                matched_suggestion.accepted_authorship
                if matched_suggestion is not None
                else payload.accepted_authorship
            ),
            "acknowledge_conflict": payload.acknowledge_conflict,
            "conflicts_present": [
                conflict.model_dump(mode="json") for conflict in inspection.conflicts
            ],
            "notes": payload.notes,
        },
        created_at=now,
    )
    try:
        with database.begin_nested():
            database.add(reconciliation)
            database.flush()
    except IntegrityError as error:
        if _constraint_name(error) == UNIQUE_IDENTITY_CONSTRAINT:
            colliding = find_duplicate(database, payload.scientific_name, payload.cultivar_name)
            raise ReconciliationConflictError(
                code="duplicate_botanical_identity",
                message=(
                    "Another active botanical identity already uses this accepted name and "
                    "cultivar."
                ),
                existing_id=colliding.id if colliding is not None else None,
            ) from error
        raise

    return inspect_reconciliation(
        database,
        identity.id,
        wfo_source=wfo_source,
        wcvp_v15_source=wcvp_v15_source,
        wcvp_v16_source=wcvp_v16_source,
    )


def merge_duplicate_identity(
    database: Session,
    duplicate_identity_id: UUID,
    payload: DuplicateIdentityMergeWrite,
    *,
    actor_user_id: UUID | None = None,
    wfo_source: WfoSource | None = None,
    wcvp_v15_source: WcvpSource | None = None,
    wcvp_v16_source: WcvpSource | None = None,
) -> IdentityReconciliationResponse:
    survivor_identity_id = payload.survivor_identity_id
    if duplicate_identity_id == survivor_identity_id:
        raise ReconciliationConflictError(
            code="reconciliation_invalid",
            message="A botanical identity cannot be merged into itself.",
        )

    # A cutting write may derive its identity from its mother. Serialize before either
    # identity or collection row is locked so the merge cannot leave a new lot on a tombstone.
    lock_lineage_writes(database)
    for lock_id in sorted((duplicate_identity_id, survivor_identity_id)):
        database.scalar(
            select(BotanicalIdentity)
            .where(BotanicalIdentity.id == lock_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    duplicate = database.get(BotanicalIdentity, duplicate_identity_id)
    survivor = database.get(BotanicalIdentity, survivor_identity_id)
    if duplicate is None or survivor is None:
        raise ReconciliationNotFoundError("Botanical identity not found.")

    if duplicate.merged_into_id is not None:
        raise ReconciliationConflictError(
            code="botanical_identity_merged",
            message="The duplicate botanical identity has already been merged.",
            existing_id=duplicate.merged_into_id,
        )
    if survivor.merged_into_id is not None:
        raise ReconciliationConflictError(
            code="botanical_identity_merged",
            message="The survivor botanical identity has been merged into another identity.",
            existing_id=survivor.merged_into_id,
        )
    if (
        duplicate.updated_at != payload.duplicate_updated_at
        or survivor.updated_at != payload.survivor_updated_at
    ):
        raise ReconciliationConflictError(
            code="reconciliation_stale",
            message=(
                "One or both botanical identities changed since review began. "
                "Reload and inspect both records before merging."
            ),
        )

    conflicting_fields = _conflicting_profile_fields(database, duplicate.id, survivor.id)
    if conflicting_fields and payload.profile_resolution != "keep_survivor":
        raise ReconciliationConflictError(
            code="botanical_profile_conflict",
            message=(
                "Both identities have differing reference profile text in: "
                f"{', '.join(conflicting_fields)}. Confirm with "
                "profile_resolution='keep_survivor' or reconcile the profile text first."
            ),
            conflicting_fields=conflicting_fields,
        )

    now = datetime.now(UTC)
    dup_profile = database.get(BotanicalProfile, duplicate.id)
    surv_profile = database.get(BotanicalProfile, survivor.id)
    dup_place_ids = list(
        database.scalars(
            select(BotanicalProfileNativeRange.geographic_place_id)
            .where(BotanicalProfileNativeRange.botanical_profile_id == duplicate.id)
            .order_by(BotanicalProfileNativeRange.geographic_place_id)
        )
    )
    copied_profile_fields: list[str] = []
    if dup_profile is not None or dup_place_ids:
        if surv_profile is None:
            surv_profile = BotanicalProfile(botanical_identity_id=survivor.id)
            database.add(surv_profile)
            database.flush()
        if dup_profile is not None:
            for field in PROFILE_FIELDS:
                dup_val = getattr(dup_profile, field)
                surv_val = getattr(surv_profile, field)
                if dup_val and dup_val.strip() and not (surv_val and surv_val.strip()):
                    setattr(surv_profile, field, dup_val)
                    copied_profile_fields.append(field)

    surv_place_ids = set(
        database.scalars(
            select(BotanicalProfileNativeRange.geographic_place_id).where(
                BotanicalProfileNativeRange.botanical_profile_id == survivor.id
            )
        )
    )
    unioned_place_ids: list[str] = []
    for place_id in dup_place_ids:
        if place_id not in surv_place_ids:
            database.add(
                BotanicalProfileNativeRange(
                    botanical_profile_id=survivor.id,
                    geographic_place_id=place_id,
                    created_at=now,
                )
            )
            unioned_place_ids.append(str(place_id))

    seed_lot_ids = [
        str(item_id)
        for item_id in database.scalars(
            select(SeedLot.id)
            .where(SeedLot.botanical_identity_id == duplicate.id)
            .order_by(SeedLot.id)
        )
    ]
    if seed_lot_ids:
        database.execute(
            update(SeedLot)
            .where(SeedLot.botanical_identity_id == duplicate.id)
            .values(botanical_identity_id=survivor.id)
        )

    plant_ids = [
        str(item_id)
        for item_id in database.scalars(
            select(Plant.id).where(Plant.botanical_identity_id == duplicate.id).order_by(Plant.id)
        )
    ]
    if plant_ids:
        database.execute(
            update(Plant)
            .where(Plant.botanical_identity_id == duplicate.id)
            .values(botanical_identity_id=survivor.id)
        )

    plant_group_ids = [
        str(item_id)
        for item_id in database.scalars(
            select(PlantGroup.id)
            .where(PlantGroup.botanical_identity_id == duplicate.id)
            .order_by(PlantGroup.id)
        )
    ]
    if plant_group_ids:
        database.execute(
            update(PlantGroup)
            .where(PlantGroup.botanical_identity_id == duplicate.id)
            .values(botanical_identity_id=survivor.id)
        )

    vegetative_lot_ids = [
        str(item_id)
        for item_id in database.scalars(
            select(VegetativeLot.id)
            .where(VegetativeLot.botanical_identity_id == duplicate.id)
            .order_by(VegetativeLot.id)
        )
    ]
    if vegetative_lot_ids:
        database.execute(
            update(VegetativeLot)
            .where(VegetativeLot.botanical_identity_id == duplicate.id)
            .values(botanical_identity_id=survivor.id)
        )

    scheduled_activity_ids = [
        str(item_id)
        for item_id in database.scalars(
            select(ScheduledActivity.id)
            .where(ScheduledActivity.botanical_identity_id == duplicate.id)
            .order_by(ScheduledActivity.id)
        )
    ]
    if scheduled_activity_ids:
        database.execute(
            update(ScheduledActivity)
            .where(ScheduledActivity.botanical_identity_id == duplicate.id)
            .values(botanical_identity_id=survivor.id)
        )

    surv_cover = database.scalar(
        select(BotanicalIdentityCoverImage).where(
            BotanicalIdentityCoverImage.botanical_identity_id == survivor.id
        )
    )
    dup_cover = database.scalar(
        select(BotanicalIdentityCoverImage).where(
            BotanicalIdentityCoverImage.botanical_identity_id == duplicate.id
        )
    )
    adopted_cover_id: str | None = None
    if surv_cover is None and dup_cover is not None:
        dup_cover.botanical_identity_id = survivor.id
        adopted_cover_id = str(dup_cover.id)

    surv_ext_providers = set(
        database.scalars(
            select(ExternalTaxonLink.provider).where(
                ExternalTaxonLink.botanical_identity_id == survivor.id
            )
        )
    )
    for ext_link in database.scalars(
        select(ExternalTaxonLink).where(ExternalTaxonLink.botanical_identity_id == duplicate.id)
    ):
        if ext_link.provider not in surv_ext_providers:
            ext_link.botanical_identity_id = survivor.id

    dup_former_names = list(
        database.scalars(
            select(BotanicalIdentityName)
            .where(BotanicalIdentityName.botanical_identity_id == duplicate.id)
            .order_by(
                BotanicalIdentityName.effective_from.asc(),
                BotanicalIdentityName.id.asc(),
            )
        )
    )
    for dup_name in dup_former_names:
        database.add(
            BotanicalIdentityName(
                botanical_identity_id=survivor.id,
                scientific_name=dup_name.scientific_name,
                cultivar_name=dup_name.cultivar_name,
                common_name=dup_name.common_name,
                authorship=dup_name.authorship,
                status_kind="merged_duplicate",
                source_provider=dup_name.source_provider,
                source_version=dup_name.source_version,
                source_taxon_id=dup_name.source_taxon_id,
                accepted_source_taxon_id=dup_name.accepted_source_taxon_id,
                origin_identity_id=dup_name.origin_identity_id or duplicate.id,
                effective_from=dup_name.effective_from,
                superseded_at=dup_name.superseded_at or max(now, dup_name.effective_from),
                created_at=now,
            )
        )

    database.add(
        BotanicalIdentityName(
            botanical_identity_id=survivor.id,
            scientific_name=duplicate.scientific_name,
            cultivar_name=duplicate.cultivar_name,
            common_name=duplicate.common_name,
            authorship=None,
            status_kind="merged_duplicate",
            source_provider="operator",
            source_version=None,
            source_taxon_id=None,
            accepted_source_taxon_id=None,
            origin_identity_id=duplicate.id,
            effective_from=duplicate.created_at,
            superseded_at=max(now, duplicate.created_at),
            created_at=now,
        )
    )

    database.execute(
        update(BotanicalIdentity)
        .where(BotanicalIdentity.merged_into_id == duplicate.id)
        .values(merged_into_id=survivor.id)
    )

    duplicate_snapshot = {
        "id": str(duplicate.id),
        "scientific_name": duplicate.scientific_name,
        "cultivar_name": duplicate.cultivar_name,
        "common_name": duplicate.common_name,
        "created_at": duplicate.created_at.isoformat(),
        "updated_at": duplicate.updated_at.isoformat(),
    }
    survivor_snapshot = {
        "id": str(survivor.id),
        "scientific_name": survivor.scientific_name,
        "cultivar_name": survivor.cultivar_name,
        "common_name": survivor.common_name,
        "created_at": survivor.created_at.isoformat(),
        "updated_at": survivor.updated_at.isoformat(),
    }

    duplicate.merged_into_id = survivor.id
    duplicate.merged_at = now
    duplicate.updated_at = max(now, duplicate.updated_at + timedelta(microseconds=1))
    survivor.updated_at = max(now, survivor.updated_at + timedelta(microseconds=1))

    reconciliation = BotanicalIdentityReconciliation(
        identity_id=survivor.id,
        duplicate_identity_id=duplicate.id,
        actor_user_id=actor_user_id,
        kind="duplicate_identity_merge",
        previous_scientific_name=duplicate.scientific_name,
        previous_cultivar_name=duplicate.cultivar_name,
        previous_common_name=duplicate.common_name,
        applied_scientific_name=survivor.scientific_name,
        applied_cultivar_name=survivor.cultivar_name,
        applied_common_name=survivor.common_name,
        source_provider="operator",
        evidence={
            "format_version": "1",
            "duplicate_identity_snapshot": duplicate_snapshot,
            "survivor_identity_snapshot": survivor_snapshot,
            "repointed_records": {
                "seed_lot_ids": seed_lot_ids,
                "plant_ids": plant_ids,
                "plant_group_ids": plant_group_ids,
                "scheduled_activity_ids": scheduled_activity_ids,
                "vegetative_lot_ids": vegetative_lot_ids,
            },
            "profile_resolution": payload.profile_resolution,
            "conflicting_profile_fields": conflicting_fields,
            "copied_profile_fields": copied_profile_fields,
            "unioned_native_range_place_ids": unioned_place_ids,
            "adopted_cover_id": adopted_cover_id,
            "notes": payload.notes,
        },
        created_at=now,
    )
    database.add(reconciliation)
    database.flush()

    return inspect_reconciliation(
        database,
        survivor.id,
        wfo_source=wfo_source,
        wcvp_v15_source=wcvp_v15_source,
        wcvp_v16_source=wcvp_v16_source,
    )
