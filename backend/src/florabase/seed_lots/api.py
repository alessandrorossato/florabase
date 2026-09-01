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
from florabase.lineage.schemas import LineageResponse
from florabase.lineage.service import LineageCycleError, lineage
from florabase.seed_lots.schemas import SeedLotCreate, SeedLotResponse, SeedLotUpdate
from florabase.seed_lots.service import (
    SeedLotProjection,
    SeedLotReferenceNotFoundError,
    create_seed_lot,
    get_seed_lot,
    list_seed_lots,
    responses,
    update_seed_lot,
)

router = APIRouter(prefix="/seed-lots", tags=["seed-lots"])


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "seed_lot_not_found", "message": "SeedLot not found"},
    )


def _reference_not_found(error: SeedLotReferenceNotFoundError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": error.code, "message": error.message},
    )


def _lineage_conflict(error: LineageCycleError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": error.code, "message": error.message},
    )


def _require_seed_lot(database: Session, seed_lot_id: UUID) -> SeedLotProjection:
    projection = get_seed_lot(database, seed_lot_id)
    if projection is None:
        raise _not_found()
    return projection


def _response(database: Session, seed_lot_id: UUID) -> SeedLotResponse:
    return responses(database, [_require_seed_lot(database, seed_lot_id)])[0]


@router.get("", response_model=list[SeedLotResponse], operation_id="listSeedLots")
def list_all(
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> list[SeedLotResponse]:
    return responses(database, list_seed_lots(database))


@router.post(
    "",
    response_model=SeedLotResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createSeedLot",
)
def create(
    payload: SeedLotCreate,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> SeedLotResponse:
    require_owner(actor)
    try:
        seed_lot = create_seed_lot(database, payload)
    except SeedLotReferenceNotFoundError as error:
        raise _reference_not_found(error) from error
    except LineageCycleError as error:
        raise _lineage_conflict(error) from error
    response.headers["Location"] = f"/api/v1/seed-lots/{seed_lot.id}"
    return _response(database, seed_lot.id)


@router.get("/{seed_lot_id}", response_model=SeedLotResponse, operation_id="getSeedLot")
def read(
    seed_lot_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> SeedLotResponse:
    return _response(database, seed_lot_id)


@router.get(
    "/{seed_lot_id}/lineage",
    response_model=LineageResponse,
    operation_id="getSeedLotLineage",
)
def read_lineage(
    seed_lot_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> LineageResponse:
    _require_seed_lot(database, seed_lot_id)
    try:
        return lineage(database, ("seed_lot", seed_lot_id))
    except LineageCycleError as error:
        raise _lineage_conflict(error) from error


@router.put("/{seed_lot_id}", response_model=SeedLotResponse, operation_id="updateSeedLot")
def update(
    seed_lot_id: UUID,
    payload: SeedLotUpdate,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> SeedLotResponse:
    require_owner(actor)
    projection = _require_seed_lot(database, seed_lot_id)
    try:
        update_seed_lot(database, projection.seed_lot, payload)
    except SeedLotReferenceNotFoundError as error:
        raise _reference_not_found(error) from error
    except LineageCycleError as error:
        raise _lineage_conflict(error) from error
    return _response(database, seed_lot_id)
