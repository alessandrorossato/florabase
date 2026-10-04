from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy.exc import IntegrityError

from florabase.auth.dependencies import require_owner
from florabase.events.service import EventDomainConflictError
from florabase.harvests import inventory_service as service
from florabase.harvests.api import Database, Reader, Writer, _error
from florabase.harvests.inventory_schemas import (
    DispositionCreate,
    DispositionResponse,
    InventoryResponse,
    InventoryWrite,
)
from florabase.harvests.model import MaterialKind
from florabase.locations.service import LocationIntegrityError, LocationNotFoundError

router = APIRouter(tags=["harvest inventory"])


def error(database: Database, failure: Exception) -> HTTPException:
    database.rollback()
    if isinstance(failure, LookupError):
        return HTTPException(
            404, detail={"code": "harvest_inventory_not_found", "message": str(failure)}
        )
    if isinstance(failure, LocationNotFoundError):
        return HTTPException(
            404, detail={"code": "location_not_found", "message": "Storage Location not found"}
        )
    if isinstance(failure, LocationIntegrityError):
        return HTTPException(409, detail={"code": failure.code, "message": failure.message})
    return _error(database, failure)


@router.get(
    "/harvest-inventory",
    response_model=list[InventoryResponse],
    operation_id="listHarvestInventory",
)
def list_all(
    database: Database,
    _actor: Reader,
    harvest_id: UUID | None = None,
    state: Literal["active", "depleted"] | None = None,
    material_kind: MaterialKind | None = None,
    location_id: UUID | None = None,
) -> list[InventoryResponse]:
    return service.list_inventory(
        database,
        harvest_id=harvest_id,
        state=state,
        material_kind=material_kind,
        location_id=location_id,
    )


@router.get(
    "/harvest-inventory/{inventory_id}",
    response_model=InventoryResponse,
    operation_id="getHarvestInventory",
)
def read(inventory_id: UUID, database: Database, _actor: Reader) -> InventoryResponse:
    try:
        return service.read_inventory(database, inventory_id)
    except LookupError as failure:
        raise error(database, failure) from failure


@router.post(
    "/harvest-items/{item_id}/inventory",
    response_model=InventoryResponse,
    status_code=201,
    operation_id="trackHarvestMaterial",
)
def create(
    item_id: UUID, payload: InventoryWrite, database: Database, actor: Writer
) -> InventoryResponse:
    require_owner(actor)
    try:
        inventory = service.track(database, item_id, payload)
        database.commit()
        return service.read_inventory(database, inventory.id)
    except (
        LookupError,
        EventDomainConflictError,
        LocationIntegrityError,
        LocationNotFoundError,
        IntegrityError,
    ) as failure:
        raise error(database, failure) from failure


@router.put(
    "/harvest-inventory/{inventory_id}",
    response_model=InventoryResponse,
    operation_id="correctHarvestInventory",
)
def correct(
    inventory_id: UUID, payload: InventoryWrite, database: Database, actor: Writer
) -> InventoryResponse:
    require_owner(actor)
    try:
        service.correct(database, inventory_id, payload)
        database.commit()
        return service.read_inventory(database, inventory_id)
    except (
        LookupError,
        EventDomainConflictError,
        LocationIntegrityError,
        LocationNotFoundError,
        IntegrityError,
    ) as failure:
        raise error(database, failure) from failure


@router.delete(
    "/harvest-inventory/{inventory_id}", status_code=204, operation_id="removeHarvestTracking"
)
def remove(inventory_id: UUID, database: Database, actor: Writer) -> Response:
    require_owner(actor)
    try:
        service.remove_tracking(database, inventory_id)
        database.commit()
    except (LookupError, EventDomainConflictError, IntegrityError) as failure:
        raise error(database, failure) from failure
    return Response(status_code=204)


@router.get(
    "/harvest-inventory/{inventory_id}/dispositions",
    response_model=list[DispositionResponse],
    operation_id="listHarvestDispositions",
)
def history(inventory_id: UUID, database: Database, _actor: Reader) -> list[DispositionResponse]:
    try:
        return service.history(database, inventory_id)
    except LookupError as failure:
        raise error(database, failure) from failure


@router.post(
    "/harvest-inventory/{inventory_id}/dispositions",
    response_model=list[DispositionResponse],
    status_code=201,
    operation_id="recordHarvestDisposition",
)
def disposition(
    inventory_id: UUID, payload: DispositionCreate, database: Database, actor: Writer
) -> list[DispositionResponse]:
    require_owner(actor)
    try:
        service.record_disposition(database, inventory_id, payload)
        database.commit()
        return service.history(database, inventory_id)
    except (LookupError, EventDomainConflictError, IntegrityError) as failure:
        raise error(database, failure) from failure
