from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from florabase.auth.dependencies import (
    AuthenticatedActor,
    require_authenticated_actor,
    require_csrf,
    require_owner,
)
from florabase.botanical_identities.service import get_botanical_identity
from florabase.core.config import Settings, get_settings
from florabase.db.session import get_database_session
from florabase.external_botany.provider import (
    GbifBotanicalProvider,
    ProviderError,
    ProviderNotFoundError,
    ProviderResponseError,
)
from florabase.external_botany.schemas import (
    ExternalTaxonLinkCreate,
    ExternalTaxonLinkResponse,
    TaxonSearchResponse,
)
from florabase.external_botany.service import (
    confirm_link,
    get_link,
    link_response,
    refresh_link,
    search_taxa,
    unlink,
)

router = APIRouter(prefix="/botanical-identities", tags=["external botanical data"])


def get_provider(settings: Annotated[Settings, Depends(get_settings)]) -> GbifBotanicalProvider:
    return GbifBotanicalProvider(settings)


def _require_identity(database: Session, identity_id: UUID) -> None:
    if get_botanical_identity(database, identity_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "botanical_identity_not_found",
                "message": "Botanical identity not found",
            },
        )


def _provider_http_error(error: ProviderError) -> HTTPException:
    if isinstance(error, ProviderNotFoundError):
        response_status = status.HTTP_404_NOT_FOUND
    elif isinstance(error, ProviderResponseError):
        response_status = status.HTTP_502_BAD_GATEWAY
    else:
        response_status = status.HTTP_503_SERVICE_UNAVAILABLE
    message = {
        "provider_taxon_not_found": "The GBIF taxon is no longer available.",
        "provider_rate_limited": "GBIF is temporarily rate limiting requests. Try again later.",
        "provider_invalid_response": "GBIF returned an unusable response.",
        "provider_unavailable": "GBIF is temporarily unavailable.",
    }.get(error.code, "The external botanical provider is unavailable.")
    return HTTPException(
        status_code=response_status, detail={"code": error.code, "message": message}
    )


@router.get(
    "/{botanical_identity_id}/external-taxa/search",
    response_model=TaxonSearchResponse,
    operation_id="searchExternalTaxa",
)
async def search(
    botanical_identity_id: UUID,
    query: Annotated[str, Query(min_length=1, max_length=255)],
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
    provider: Annotated[GbifBotanicalProvider, Depends(get_provider)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TaxonSearchResponse:
    _require_identity(database, botanical_identity_id)
    normalized_query = " ".join(query.split())
    if not normalized_query:
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_query", "message": "Search query cannot be blank"},
        )
    try:
        return await search_taxa(
            database, provider, normalized_query, settings.botanical_cache_ttl_seconds
        )
    except ProviderError as error:
        raise _provider_http_error(error) from error


@router.get(
    "/{botanical_identity_id}/external-taxon-link",
    response_model=ExternalTaxonLinkResponse | None,
    operation_id="getExternalTaxonLink",
)
def read_link(
    botanical_identity_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ExternalTaxonLinkResponse | None:
    _require_identity(database, botanical_identity_id)
    link = get_link(database, botanical_identity_id)
    return None if link is None else link_response(link, settings.botanical_cache_ttl_seconds)


@router.put(
    "/{botanical_identity_id}/external-taxon-link",
    response_model=ExternalTaxonLinkResponse,
    operation_id="confirmExternalTaxonLink",
)
async def confirm(
    botanical_identity_id: UUID,
    payload: ExternalTaxonLinkCreate,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
    provider: Annotated[GbifBotanicalProvider, Depends(get_provider)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ExternalTaxonLinkResponse:
    require_owner(actor)
    _require_identity(database, botanical_identity_id)
    try:
        link = await confirm_link(
            database,
            provider,
            botanical_identity_id,
            payload.external_id,
            payload.scientific_name,
            settings.botanical_cache_ttl_seconds,
        )
    except ProviderError as error:
        raise _provider_http_error(error) from error
    return link_response(link, settings.botanical_cache_ttl_seconds)


@router.post(
    "/{botanical_identity_id}/external-taxon-link/refresh",
    response_model=ExternalTaxonLinkResponse,
    operation_id="refreshExternalTaxonLink",
)
async def refresh(
    botanical_identity_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
    provider: Annotated[GbifBotanicalProvider, Depends(get_provider)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ExternalTaxonLinkResponse:
    require_owner(actor)
    _require_identity(database, botanical_identity_id)
    link = get_link(database, botanical_identity_id)
    if link is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "external_taxon_link_not_found", "message": "No GBIF taxon is linked"},
        )
    refreshed = await refresh_link(database, provider, link, settings.botanical_cache_ttl_seconds)
    return link_response(refreshed, settings.botanical_cache_ttl_seconds)


@router.delete(
    "/{botanical_identity_id}/external-taxon-link",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="unlinkExternalTaxon",
)
def remove_link(
    botanical_identity_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> Response:
    require_owner(actor)
    _require_identity(database, botanical_identity_id)
    if not unlink(database, botanical_identity_id):
        raise HTTPException(
            status_code=404,
            detail={"code": "external_taxon_link_not_found", "message": "No GBIF taxon is linked"},
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
