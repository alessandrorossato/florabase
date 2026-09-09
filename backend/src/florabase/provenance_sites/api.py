from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from florabase.auth.dependencies import (
    AuthenticatedActor,
    require_authenticated_actor,
    require_csrf,
    require_owner,
)
from florabase.db.session import get_database_session
from florabase.provenance_sites.model import ProvenanceSite
from florabase.provenance_sites.schemas import (
    ProvenanceMapResponse,
    ProvenanceSiteCreate,
    ProvenanceSiteResponse,
    ProvenanceSiteUpdate,
)
from florabase.provenance_sites.service import (
    ProvenanceSiteError,
    collection_provenance_map,
    create_provenance_site,
    delete_provenance_site,
    get_provenance_site,
    list_provenance_sites,
    responses,
    update_provenance_site,
)

router = APIRouter(prefix="/provenance-sites", tags=["provenance-sites"])


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "provenance_site_not_found", "message": "ProvenanceSite not found"},
    )


def _require(database: Session, site_id: UUID) -> ProvenanceSite:
    site = get_provenance_site(database, site_id)
    if site is None:
        raise _not_found()
    return site


def _response(database: Session, site: ProvenanceSite) -> ProvenanceSiteResponse:
    return responses(database, [site])[0]


def _conflict(error: ProvenanceSiteError) -> HTTPException:
    status_code = (
        status.HTTP_404_NOT_FOUND
        if error.code == "geographic_place_not_found"
        else status.HTTP_409_CONFLICT
    )
    return HTTPException(
        status_code=status_code, detail={"code": error.code, "message": error.message}
    )


@router.get("", response_model=list[ProvenanceSiteResponse], operation_id="listProvenanceSites")
def list_all(
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> list[ProvenanceSiteResponse]:
    return responses(database, list_provenance_sites(database))


@router.post(
    "",
    response_model=ProvenanceSiteResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createProvenanceSite",
)
def create(
    payload: ProvenanceSiteCreate,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> ProvenanceSiteResponse:
    require_owner(actor)
    try:
        site = create_provenance_site(database, payload)
    except ProvenanceSiteError as error:
        raise _conflict(error) from error
    response.headers["Location"] = f"/api/v1/provenance-sites/{site.id}"
    return _response(database, site)


@router.get(
    "/map",
    response_model=ProvenanceMapResponse,
    operation_id="getCollectionProvenanceMap",
)
def read_map(
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> ProvenanceMapResponse:
    return collection_provenance_map(database)


@router.get("/{site_id}", response_model=ProvenanceSiteResponse, operation_id="getProvenanceSite")
def read(
    site_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> ProvenanceSiteResponse:
    return _response(database, _require(database, site_id))


@router.put(
    "/{site_id}", response_model=ProvenanceSiteResponse, operation_id="updateProvenanceSite"
)
def update(
    site_id: UUID,
    payload: ProvenanceSiteUpdate,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> ProvenanceSiteResponse:
    require_owner(actor)
    try:
        return _response(
            database, update_provenance_site(database, _require(database, site_id), payload)
        )
    except ProvenanceSiteError as error:
        raise _conflict(error) from error


@router.delete(
    "/{site_id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="deleteProvenanceSite"
)
def delete(
    site_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> Response:
    require_owner(actor)
    try:
        delete_provenance_site(database, _require(database, site_id))
    except ProvenanceSiteError as error:
        raise _conflict(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
