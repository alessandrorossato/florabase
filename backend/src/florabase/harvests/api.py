from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from florabase.auth.dependencies import (
    AuthenticatedActor,
    require_authenticated_actor,
    require_csrf,
    require_owner,
)
from florabase.db.session import get_database_session
from florabase.events.service import EventDomainConflictError
from florabase.harvests.model import MaterialKind
from florabase.harvests.schemas import HarvestResponse, HarvestWrite
from florabase.harvests.service import delete_harvest, list_harvests, read_harvest, write_harvest

router = APIRouter(prefix="/harvests", tags=["harvests"])
Database = Annotated[Session, Depends(get_database_session)]
Reader = Annotated[AuthenticatedActor, Depends(require_authenticated_actor)]
Writer = Annotated[AuthenticatedActor, Depends(require_csrf)]


def _error(database: Session, error: Exception) -> HTTPException:
    database.rollback()
    if isinstance(error, LookupError):
        return HTTPException(404, detail={"code": "harvest_not_found", "message": str(error)})
    if isinstance(error, EventDomainConflictError):
        return HTTPException(409, detail={"code": error.code, "message": error.message})
    return HTTPException(
        409,
        detail={
            "code": "harvest_conflict",
            "message": "Harvest conflicts with another record; refresh and try again",
        },
    )


@router.get("", response_model=list[HarvestResponse], operation_id="listHarvests")
def list_all(
    database: Database,
    _actor: Reader,
    botanical_identity_id: UUID | None = None,
    plant_id: UUID | None = None,
    plant_group_id: UUID | None = None,
    query: str = "",
    material_kind: MaterialKind | None = None,
    source_type: Literal["plant", "plant_group"] | None = None,
) -> list[HarvestResponse]:
    return list_harvests(
        database,
        botanical_identity_id=botanical_identity_id,
        plant_id=plant_id,
        plant_group_id=plant_group_id,
        query=query,
        material_kind=material_kind,
        source_type=source_type,
    )


@router.get("/{harvest_id}", response_model=HarvestResponse, operation_id="getHarvest")
def read(harvest_id: UUID, database: Database, _actor: Reader) -> HarvestResponse:
    try:
        return read_harvest(database, harvest_id)
    except LookupError as error:
        raise _error(database, error) from error


def _save(
    database: Session, payload: HarvestWrite, harvest_id: UUID | None = None
) -> HarvestResponse:
    try:
        harvest = write_harvest(database, payload, harvest_id)
        database.commit()
        return read_harvest(database, harvest.id)
    except (LookupError, EventDomainConflictError, IntegrityError) as error:
        raise _error(database, error) from error


@router.post("", response_model=HarvestResponse, status_code=201, operation_id="createHarvest")
def create(
    payload: HarvestWrite, response: Response, database: Database, actor: Writer
) -> HarvestResponse:
    require_owner(actor)
    result = _save(database, payload)
    response.headers["Location"] = f"/api/v1/harvests/{result.id}"
    return result


@router.put("/{harvest_id}", response_model=HarvestResponse, operation_id="updateHarvest")
def update(
    harvest_id: UUID, payload: HarvestWrite, database: Database, actor: Writer
) -> HarvestResponse:
    require_owner(actor)
    return _save(database, payload, harvest_id)


@router.delete("/{harvest_id}", status_code=204, operation_id="deleteHarvest")
def delete(harvest_id: UUID, database: Database, actor: Writer) -> Response:
    require_owner(actor)
    try:
        delete_harvest(database, harvest_id)
        database.commit()
    except (LookupError, EventDomainConflictError, IntegrityError) as error:
        raise _error(database, error) from error
    return Response(status_code=204)
