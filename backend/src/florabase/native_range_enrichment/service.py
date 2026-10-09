from datetime import UTC, datetime
from uuid import UUID, uuid7

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_profiles.model import BotanicalProfile, BotanicalProfileNativeRange
from florabase.geographic_places.model import GeographicPlace
from florabase.geographic_places.service import display_path, list_geographic_places
from florabase.native_range_enrichment.crosswalk import (
    CROSSWALK_VERSION,
    EQUIVALENT,
    GEOGRAPHY_SOURCE,
    classify,
)
from florabase.native_range_enrichment.model import (
    NativeRangeApplication,
    NativeRangeProposal,
    NativeRangeRevision,
    WcvpLink,
)
from florabase.native_range_enrichment.schemas import (
    ApplicationResponse,
    ApplyWrite,
    ProposalEvidence,
    ProposalResponse,
    RangeChoice,
    WcvpLinkResponse,
)
from florabase.native_range_enrichment.source import (
    ARCHIVE_SHA256,
    VERSION,
    SourceMetadata,
    Taxon,
    WcvpSource,
)


class EnrichmentConflictError(Exception):
    pass


class EnrichmentNotFoundError(Exception):
    pass


def identity_snapshot(identity: BotanicalIdentity) -> dict[str, object]:
    return {
        "scientific_name": identity.scientific_name,
        "cultivar_name": identity.cultivar_name,
        "common_name": identity.common_name,
        "updated_at": identity.updated_at.isoformat(),
    }


def identity_for_review(database: Session, identity_id: UUID) -> BotanicalIdentity:
    identity = database.scalar(
        select(BotanicalIdentity)
        .where(BotanicalIdentity.id == identity_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if identity is None:
        raise EnrichmentNotFoundError("Botanical identity not found.")
    return identity


def link_response(link: WcvpLink, identity: BotanicalIdentity) -> WcvpLinkResponse:
    return WcvpLinkResponse(
        version=link.version,
        taxon=Taxon.model_validate(link.taxon),
        source=SourceMetadata.model_validate(link.source),
        confirmed_at=link.confirmed_at,
        stale=link.identity_snapshot != identity_snapshot(identity),
    )


def confirm_link(
    database: Session, identity_id: UUID, external_id: str, checksum: str, source: WcvpSource
) -> WcvpLinkResponse:
    metadata = source.metadata()
    taxon = source.taxon(external_id)
    if checksum != metadata.checksum or not taxon.eligible:
        raise EnrichmentConflictError(
            "Select and confirm an accepted WCVP taxon from the reviewed snapshot."
        )
    identity = identity_for_review(database, identity_id)
    link = database.get(WcvpLink, identity_id)
    if link is None:
        link = WcvpLink(identity_id=identity_id)
        database.add(link)
    link.version = uuid7()
    link.external_id = taxon.external_id
    link.taxon = taxon.model_dump(mode="json")
    link.source = metadata.model_dump(mode="json")
    link.identity_snapshot = identity_snapshot(identity)
    link.confirmed_at = datetime.now(UTC)
    database.flush()
    return link_response(link, identity)


def range_version(database: Session, identity_id: UUID) -> int:
    return (
        database.scalar(
            select(NativeRangeRevision.version).where(
                NativeRangeRevision.identity_id == identity_id
            )
        )
        or 0
    )


def current_ids(database: Session, identity_id: UUID) -> list[UUID]:
    return list(
        database.scalars(
            select(BotanicalProfileNativeRange.geographic_place_id)
            .where(BotanicalProfileNativeRange.botanical_profile_id == identity_id)
            .order_by(BotanicalProfileNativeRange.geographic_place_id)
        )
    )


def propose(database: Session, identity_id: UUID, source: WcvpSource) -> ProposalResponse:
    metadata = source.metadata()
    identity = identity_for_review(database, identity_id)
    link = database.get(WcvpLink, identity_id)
    if link is None or link.identity_snapshot != identity_snapshot(identity):
        raise EnrichmentConflictError(
            "Confirm the WCVP taxon for the current botanical identity first."
        )
    taxon = source.taxon(link.external_id)
    if (
        not taxon.eligible
        or taxon.model_dump(mode="json") != link.taxon
        or metadata.model_dump(mode="json") != link.source
    ):
        raise EnrichmentConflictError(
            "The confirmed source link is stale. Review and confirm it again."
        )
    rows = source.distribution(link.external_id)
    places = list_geographic_places(database)
    by_id = {p.id: p for p in places}
    by_code = {
        p.source_code: p
        for p in places
        if (p.source_name, p.source_version, p.source_code_type) == GEOGRAPHY_SOURCE
    }
    current = current_ids(database, identity_id)
    choices = {
        p: RangeChoice(
            place_id=p,
            name=by_id[p].name,
            path=display_path(by_id[p], places),
            code=by_id[p].source_code,
            change="CURRENT-ONLY",
        )
        for p in current
    }
    assertions = []
    for row in rows:
        assertion = classify(row)
        if assertion.mapping == "equivalent" and assertion.status == "native":
            place = by_code.get(EQUIVALENT[row["area_code_l3"]])
            if place is None or place.retired_at is not None:
                assertion.mapping = "unresolved"
                assertion.note = "The exact canonical GeographicPlace is unavailable."
            else:
                assertion.place_ids = [place.id]
                if place.id not in choices:
                    choices[place.id] = RangeChoice(
                        place_id=place.id,
                        name=place.name,
                        path=display_path(place, places),
                        code=place.source_code,
                        change="ADD",
                    )
                choice = choices[place.id]
                if place.id in current:
                    choice.change = "KEEP"
                choice.assertions.append(assertion.assertion_id)
        assertions.append(assertion)
    evidence = ProposalEvidence(
        link_version=link.version,
        identity_snapshot=identity_snapshot(identity),
        destination_version=range_version(database, identity_id),
        current_ids=current,
        source=metadata,
        taxon=taxon,
        retrieved_at=datetime.now(UTC),
        crosswalk_version=CROSSWALK_VERSION,
        choices=sorted(choices.values(), key=lambda p: (p.path.casefold(), p.place_id)),
        assertions=assertions,
    )
    proposal = NativeRangeProposal(
        identity_id=identity_id, evidence=evidence.model_dump(mode="json")
    )
    database.add(proposal)
    database.flush()
    return inspect_proposal(database, identity_id, proposal.id)


def inspect_proposal(database: Session, identity_id: UUID, proposal_id: UUID) -> ProposalResponse:
    proposal = database.get(NativeRangeProposal, proposal_id)
    if proposal is None or proposal.identity_id != identity_id:
        raise EnrichmentNotFoundError("Native-range proposal not found.")
    application = database.get(NativeRangeApplication, proposal_id)
    return ProposalResponse(
        **ProposalEvidence.model_validate(proposal.evidence).model_dump(),
        id=proposal.id,
        created_at=proposal.created_at,
        applied_at=application.applied_at if application else None,
        application=ApplicationResponse(
            proposal_id=application.proposal_id,
            applied_at=application.applied_at,
            added=application.evidence["added"],
            kept=application.evidence["kept"],
            destination_version=application.evidence["destination_version_after"],
        )
        if application
        else None,
    )


def apply(
    database: Session, identity_id: UUID, proposal_id: UUID, selection: ApplyWrite
) -> ApplicationResponse:
    proposal = inspect_proposal(database, identity_id, proposal_id)
    # Canonical range writers already lock places before identity; use the same order.
    selected = set(selection.selected_place_ids)
    choices = {c.place_id: c for c in proposal.choices if c.change in {"ADD", "KEEP"}}
    if not selected <= choices.keys():
        raise EnrichmentConflictError("Only reviewed mapped native ranges may be selected.")
    places = list(
        database.scalars(
            select(GeographicPlace)
            .where(GeographicPlace.id.in_(selected))
            .order_by(GeographicPlace.id)
            .with_for_update()
        )
    )
    if len(places) != len(selected) or any(
        (p.source_name, p.source_version, p.source_code_type) != GEOGRAPHY_SOURCE
        or p.retired_at is not None
        or p.source_code != choices[p.id].code
        for p in places
    ):
        raise EnrichmentConflictError(
            "The mapped geography changed. Retrieve and review a new proposal."
        )
    identity = identity_for_review(database, identity_id)
    link = database.get(WcvpLink, identity_id, populate_existing=True)
    if (
        database.get(NativeRangeApplication, proposal_id, populate_existing=True) is not None
        or link is None
        or link.version != proposal.link_version
        or link.identity_snapshot != identity_snapshot(identity)
        or proposal.identity_snapshot != identity_snapshot(identity)
        or proposal.destination_version != range_version(database, identity_id)
        or proposal.current_ids != current_ids(database, identity_id)
        or proposal.crosswalk_version != CROSSWALK_VERSION
        or proposal.source.version != VERSION
        or proposal.source.checksum != ARCHIVE_SHA256
        or link.source != proposal.source.model_dump(mode="json")
        or link.taxon != proposal.taxon.model_dump(mode="json")
    ):
        raise EnrichmentConflictError(
            "Proposal, identity, link or recorded ranges changed. Retrieve and re-review."
        )
    added = sorted(p for p in selected if choices[p].change == "ADD")
    kept = sorted(set(proposal.current_ids))
    if added:
        database.execute(
            insert(BotanicalProfile)
            .values(botanical_identity_id=identity_id)
            .on_conflict_do_nothing(index_elements=[BotanicalProfile.botanical_identity_id])
        )
        for place_id in added:
            database.add(
                BotanicalProfileNativeRange(
                    botanical_profile_id=identity_id, geographic_place_id=place_id
                )
            )
        database.flush()
    application = NativeRangeApplication(
        proposal_id=proposal_id,
        identity_id=identity_id,
        evidence={
            "format_version": 1,
            "proposal": proposal.model_dump(mode="json"),
            "selected_place_ids": [str(p) for p in sorted(selected)],
            "added": [str(p) for p in added],
            "kept": [str(p) for p in kept],
            "removed": [],
            "destination_version_after": range_version(database, identity_id),
        },
    )
    database.add(application)
    database.flush()
    return ApplicationResponse(
        proposal_id=proposal_id,
        applied_at=application.applied_at,
        added=added,
        kept=kept,
        destination_version=range_version(database, identity_id),
    )
