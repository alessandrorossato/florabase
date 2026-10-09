from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from florabase.auth.dependencies import (
    AuthenticatedActor,
    require_authenticated_actor,
    require_csrf,
    require_owner,
)
from florabase.core.config import Settings, get_settings
from florabase.db.session import get_database_session
from florabase.explore.schemas import CollectionRecordCategory, RepresentationScope
from florabase.taxonomy import service
from florabase.taxonomy.schemas import (
    IdentityTaxonomy,
    TaxonomyLink,
    TaxonomyLinkWrite,
    TaxonomyNodeDetail,
    TaxonomyTree,
)
from florabase.taxonomy.source import SourceUnavailableError, WfoCandidate, WfoSource

router = APIRouter(tags=["taxonomy"])
Database = Annotated[Session, Depends(get_database_session)]
Reader = Annotated[AuthenticatedActor, Depends(require_authenticated_actor)]
Writer = Annotated[AuthenticatedActor, Depends(require_csrf)]
Categories = Annotated[list[CollectionRecordCategory] | None, Query(max_length=5)]
Search = Annotated[str, Query(max_length=200)]


def source_dependency(settings: Annotated[Settings, Depends(get_settings)]) -> WfoSource:
    return WfoSource(settings.wfo_snapshot_path)


Source = Annotated[WfoSource, Depends(source_dependency)]


def fail(error: Exception) -> NoReturn:
    status = (
        503
        if isinstance(error, SourceUnavailableError)
        else 409
        if isinstance(error, service.TaxonomyConflictError)
        else 404
    )
    raise HTTPException(
        status_code=status,
        detail={
            "code": "taxonomy_unavailable"
            if status == 503
            else "taxonomy_conflict"
            if status == 409
            else "taxonomy_not_found",
            "message": str(error),
        },
    ) from error


@router.get(
    "/explore/taxonomy/tree", response_model=TaxonomyTree, operation_id="getCollectionTaxonomy"
)
def tree(
    database: Database,
    _actor: Reader,
    source: Source,
    scope: RepresentationScope = "all",
    record: Categories = None,
    q: Search = "",
) -> TaxonomyTree:
    try:
        return service.tree(database, source, scope=scope, record=record or (), q=q)
    except service.TaxonomyConflictError as error:
        fail(error)


@router.get(
    "/explore/taxonomy/nodes/{source_taxon_id}",
    response_model=TaxonomyNodeDetail,
    operation_id="getCollectionTaxonomyNode",
)
def node(
    source_taxon_id: str,
    database: Database,
    _actor: Reader,
    source: Source,
    scope: RepresentationScope = "all",
    record: Categories = None,
    q: Search = "",
) -> TaxonomyNodeDetail:
    try:
        return service.node_detail(
            service.tree(database, source, scope=scope, record=record or (), q=q), source_taxon_id
        )
    except (service.TaxonomyNotFoundError, service.TaxonomyConflictError) as error:
        fail(error)


@router.get(
    "/botanical-identities/{identity_id}/taxonomy",
    response_model=IdentityTaxonomy,
    operation_id="getIdentityTaxonomy",
)
def read(
    identity_id: UUID,
    database: Database,
    _actor: Reader,
    source: Source,
    scope: RepresentationScope = "all",
    record: Categories = None,
    q: Search = "",
) -> IdentityTaxonomy:
    try:
        return service.identity_taxonomy(database, source, identity_id, scope, record or (), q)
    except (
        service.TaxonomyNotFoundError,
        service.TaxonomyConflictError,
        SourceUnavailableError,
    ) as error:
        fail(error)


@router.get(
    "/botanical-identities/{identity_id}/taxonomy/candidates",
    response_model=list[WfoCandidate],
    operation_id="searchWfoTaxa",
)
def candidates(
    identity_id: UUID,
    database: Database,
    _actor: Reader,
    source: Source,
    q: Annotated[str, Query(min_length=2, max_length=200)],
) -> list[WfoCandidate]:
    from florabase.botanical_identities.model import BotanicalIdentity

    if database.get(BotanicalIdentity, identity_id) is None:
        fail(service.TaxonomyNotFoundError("Botanical identity not found."))
    try:
        return source.search(q)
    except SourceUnavailableError as error:
        fail(error)


@router.put(
    "/botanical-identities/{identity_id}/taxonomy/link",
    response_model=TaxonomyLink,
    operation_id="confirmWfoTaxon",
)
def confirm(
    identity_id: UUID, payload: TaxonomyLinkWrite, database: Database, actor: Writer, source: Source
) -> TaxonomyLink:
    require_owner(actor)
    try:
        return service.confirm(database, identity_id, payload, source)
    except (
        service.TaxonomyNotFoundError,
        service.TaxonomyConflictError,
        SourceUnavailableError,
    ) as error:
        fail(error)


@router.delete(
    "/botanical-identities/{identity_id}/taxonomy/link",
    status_code=204,
    operation_id="unlinkWfoTaxon",
)
def unlink(identity_id: UUID, version: UUID, database: Database, actor: Writer) -> None:
    require_owner(actor)
    try:
        service.unlink(database, identity_id, version)
    except (service.TaxonomyNotFoundError, service.TaxonomyConflictError) as error:
        fail(error)
