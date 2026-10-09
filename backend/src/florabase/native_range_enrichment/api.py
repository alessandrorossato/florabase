from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from florabase.auth.dependencies import (
    AuthenticatedActor,
    require_authenticated_actor,
    require_csrf,
    require_owner,
)
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.core.config import Settings, get_settings
from florabase.db.session import get_database_session
from florabase.native_range_enrichment import service
from florabase.native_range_enrichment.model import NativeRangeProposal, WcvpLink
from florabase.native_range_enrichment.schemas import (
    ApplicationResponse,
    ApplyWrite,
    ProposalResponse,
    SourceStatus,
    WcvpLinkResponse,
    WcvpLinkWrite,
)
from florabase.native_range_enrichment.source import SourceUnavailableError, Taxon, WcvpSource

router = APIRouter(
    prefix="/botanical-identities/{identity_id}/native-range-enrichment",
    tags=["native range enrichment"],
)
Database = Annotated[Session, Depends(get_database_session)]
Reader = Annotated[AuthenticatedActor, Depends(require_authenticated_actor)]
Writer = Annotated[AuthenticatedActor, Depends(require_csrf)]


def source_dependency(settings: Annotated[Settings, Depends(get_settings)]) -> WcvpSource:
    return WcvpSource(settings.wcvp_snapshot_path)


Source = Annotated[WcvpSource, Depends(source_dependency)]


def fail(error: Exception) -> NoReturn:
    status = (
        503
        if isinstance(error, SourceUnavailableError)
        else 409
        if isinstance(error, service.EnrichmentConflictError)
        else 404
    )
    code = (
        "wcvp_source_unavailable"
        if status == 503
        else "native_range_proposal_stale"
        if status == 409
        else "enrichment_not_found"
    )
    raise HTTPException(status_code=status, detail={"code": code, "message": str(error)}) from error


def identity(database: Session, identity_id: UUID) -> BotanicalIdentity:
    record = database.get(BotanicalIdentity, identity_id)
    if record is None:
        fail(service.EnrichmentNotFoundError("Botanical identity not found."))
    return record


@router.get("/source", response_model=SourceStatus, operation_id="getNativeRangeSource")
def source_status(
    identity_id: UUID, database: Database, _actor: Reader, source: Source
) -> SourceStatus:
    record = identity(database, identity_id)
    link = database.get(WcvpLink, identity_id)
    linked = service.link_response(link, record) if link else None
    try:
        metadata = source.metadata()
        if linked is not None and linked.source != metadata:
            linked.stale = True
        return SourceStatus(available=True, source=metadata, link=linked)
    except SourceUnavailableError as error:
        return SourceStatus(available=False, message=str(error), link=linked)


@router.get("/taxa", response_model=list[Taxon], operation_id="searchWcvpTaxa")
def search_taxa(
    identity_id: UUID,
    database: Database,
    _actor: Reader,
    source: Source,
    q: Annotated[str, Query(min_length=2, max_length=200)],
) -> list[Taxon]:
    identity(database, identity_id)
    try:
        return source.search(q)
    except SourceUnavailableError as error:
        fail(error)


@router.put("/link", response_model=WcvpLinkResponse, operation_id="confirmWcvpTaxon")
def confirm(
    identity_id: UUID, payload: WcvpLinkWrite, database: Database, actor: Writer, source: Source
) -> WcvpLinkResponse:
    require_owner(actor)
    try:
        return service.confirm_link(
            database, identity_id, payload.external_id, payload.checksum, source
        )
    except (
        SourceUnavailableError,
        service.EnrichmentConflictError,
        service.EnrichmentNotFoundError,
    ) as error:
        fail(error)


@router.post(
    "/proposals",
    response_model=ProposalResponse,
    status_code=201,
    operation_id="createNativeRangeProposal",
)
def create_proposal(
    identity_id: UUID, database: Database, actor: Writer, source: Source
) -> ProposalResponse:
    require_owner(actor)
    try:
        return service.propose(database, identity_id, source)
    except (
        SourceUnavailableError,
        service.EnrichmentConflictError,
        service.EnrichmentNotFoundError,
    ) as error:
        fail(error)


@router.get(
    "/proposals", response_model=list[ProposalResponse], operation_id="listNativeRangeProposals"
)
def list_proposals(identity_id: UUID, database: Database, _actor: Reader) -> list[ProposalResponse]:
    identity(database, identity_id)
    proposals = database.scalars(
        select(NativeRangeProposal.id)
        .where(NativeRangeProposal.identity_id == identity_id)
        .order_by(NativeRangeProposal.created_at.desc(), NativeRangeProposal.id.desc())
        .limit(10)
    )
    return [service.inspect_proposal(database, identity_id, p) for p in proposals]


@router.get(
    "/proposals/{proposal_id}",
    response_model=ProposalResponse,
    operation_id="getNativeRangeProposal",
)
def read_proposal(
    identity_id: UUID, proposal_id: UUID, database: Database, _actor: Reader
) -> ProposalResponse:
    try:
        return service.inspect_proposal(database, identity_id, proposal_id)
    except service.EnrichmentNotFoundError as error:
        fail(error)


@router.post(
    "/proposals/{proposal_id}/apply",
    response_model=ApplicationResponse,
    operation_id="applyNativeRangeProposal",
)
def apply_proposal(
    identity_id: UUID, proposal_id: UUID, payload: ApplyWrite, database: Database, actor: Writer
) -> ApplicationResponse:
    require_owner(actor)
    try:
        return service.apply(database, identity_id, proposal_id, payload)
    except (service.EnrichmentConflictError, service.EnrichmentNotFoundError) as error:
        fail(error)
