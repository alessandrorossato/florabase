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
from florabase.propagation.schemas import (
    SeedLotSowingTransitionCreate,
    SeedLotSowingTransitionResponse,
)
from florabase.propagation.service import (
    PropagationConflictError,
    PropagationNotFoundError,
    create_sowing_from_seed_lot,
)
from florabase.seed_lots.schemas import SeedLotCreate, SeedLotResponse, SeedLotUpdate
from florabase.seed_lots.service import (
    SeedLotDomainConflictError,
    SeedLotProjection,
    SeedLotReferenceNotFoundError,
    create_seed_lot,
    get_seed_lot,
    list_seed_lots,
    responses,
    update_seed_lot,
)
from florabase.sowings.service import (
    SowingDomainConflictError,
    SowingReferenceNotFoundError,
    get_sowing,
)
from florabase.sowings.service import (
    responses as sowing_responses,
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


def _domain_conflict(
    error: SeedLotDomainConflictError | SowingDomainConflictError,
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": error.code, "message": error.message},
    )


def _lineage_conflict(error: LineageCycleError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": error.code, "message": error.message},
    )


def _propagation_conflict(error: PropagationConflictError) -> HTTPException:
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
    except SeedLotDomainConflictError as error:
        raise _domain_conflict(error) from error
    except SeedLotReferenceNotFoundError as error:
        raise _reference_not_found(error) from error
    except LineageCycleError as error:
        raise _lineage_conflict(error) from error
    response.headers["Location"] = f"/api/v1/seed-lots/{seed_lot.id}"
    return _response(database, seed_lot.id)


@router.post(
    "/{seed_lot_id}/create-sowing",
    response_model=SeedLotSowingTransitionResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createSowingFromSeedLot",
)
def create_sowing_transition(
    seed_lot_id: UUID,
    payload: SeedLotSowingTransitionCreate,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> SeedLotSowingTransitionResponse:
    require_owner(actor)
    try:
        sowing, seed_lot = create_sowing_from_seed_lot(database, seed_lot_id, payload)
    except PropagationNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": error.code, "message": error.message},
        ) from error
    except SowingReferenceNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": error.code, "message": error.message},
        ) from error
    except SowingDomainConflictError as error:
        raise _domain_conflict(error) from error
    except PropagationConflictError as error:
        raise _propagation_conflict(error) from error
    sowing_projection = get_sowing(database, sowing.id)
    if sowing_projection is None:
        raise RuntimeError("Created Sowing could not be projected")
    response.headers["Location"] = f"/api/v1/sowings/{sowing.id}"
    return SeedLotSowingTransitionResponse(
        sowing=sowing_responses(database, [sowing_projection])[0],
        seed_lot=_response(database, seed_lot.id),
    )


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
    except SeedLotDomainConflictError as error:
        raise _domain_conflict(error) from error
    except SeedLotReferenceNotFoundError as error:
        raise _reference_not_found(error) from error
    except LineageCycleError as error:
        raise _lineage_conflict(error) from error
    return _response(database, seed_lot_id)
