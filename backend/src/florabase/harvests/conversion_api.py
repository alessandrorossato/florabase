from uuid import UUID

from fastapi import APIRouter
from sqlalchemy.exc import IntegrityError

from florabase.auth.dependencies import require_owner
from florabase.events.service import EventDomainConflictError
from florabase.harvests import conversion_service as service
from florabase.harvests.api import Database, Reader, Writer
from florabase.harvests.conversion_schemas import (
    ConversionCreate,
    ConversionEligibility,
    ConversionResponse,
)
from florabase.harvests.inventory_api import error
from florabase.lineage.service import LineageCycleError
from florabase.locations.service import LocationIntegrityError, LocationNotFoundError
from florabase.seed_lots.service import SeedLotDomainConflictError, SeedLotReferenceNotFoundError

router = APIRouter(tags=["Harvest seed conversions"])


@router.get(
    "/harvest-seed-conversions",
    response_model=list[ConversionResponse],
    operation_id="listHarvestSeedConversions",
)
def list_all(
    database: Database,
    _actor: Reader,
    inventory_id: UUID | None = None,
    seed_lot_id: UUID | None = None,
) -> list[ConversionResponse]:
    return service.list_conversions(database, inventory_id=inventory_id, seed_lot_id=seed_lot_id)


@router.post(
    "/harvest-inventory/{inventory_id}/create-seed-lot",
    response_model=ConversionResponse,
    status_code=201,
    operation_id="createSeedLotFromHarvest",
)
def create(
    inventory_id: UUID, payload: ConversionCreate, database: Database, actor: Writer
) -> ConversionResponse:
    require_owner(actor)
    try:
        result = service.create(database, inventory_id, payload)
        database.commit()
        return next(
            row
            for row in service.list_conversions(database, seed_lot_id=result.seed_lot_id)
            if row.id == result.id
        )
    except (
        SeedLotDomainConflictError,
        SeedLotReferenceNotFoundError,
        LineageCycleError,
    ) as failure:
        raise error(database, EventDomainConflictError(failure.code, failure.message)) from failure
    except (
        LookupError,
        EventDomainConflictError,
        LocationIntegrityError,
        LocationNotFoundError,
        IntegrityError,
    ) as failure:
        raise error(database, failure) from failure


@router.get(
    "/harvest-seed-conversions/{conversion_id}/reversal",
    response_model=ConversionEligibility,
    operation_id="getHarvestSeedConversionReversal",
)
def eligibility(conversion_id: UUID, database: Database, _actor: Reader) -> ConversionEligibility:
    try:
        return service.evaluate(database, conversion_id)[-1]
    except LookupError as failure:
        raise error(database, failure) from failure


@router.post(
    "/harvest-seed-conversions/{conversion_id}/reverse",
    response_model=ConversionResponse,
    operation_id="reverseHarvestSeedConversion",
)
def reverse(conversion_id: UUID, database: Database, actor: Writer) -> ConversionResponse:
    require_owner(actor)
    try:
        result = service.reverse(database, conversion_id)
        database.commit()
        return next(
            row
            for row in service.list_conversions(database, seed_lot_id=result.seed_lot_id)
            if row.id == result.id
        )
    except (LookupError, EventDomainConflictError, IntegrityError) as failure:
        raise error(database, failure) from failure
