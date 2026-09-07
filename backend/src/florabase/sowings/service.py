from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import case, desc, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.schemas import BotanicalIdentityResponse
from florabase.locations.model import Location
from florabase.locations.service import display_path, list_locations
from florabase.seed_lots.model import SeedLot
from florabase.seed_lots.schemas import PartialDate
from florabase.sowings.model import Sowing
from florabase.sowings.schemas import (
    SowingCreate,
    SowingLocationSummary,
    SowingQuantity,
    SowingResponse,
    SowingSeedLotSummary,
    SowingUpdate,
)


@dataclass(frozen=True)
class SowingReferenceNotFoundError(Exception):
    code: str
    message: str


@dataclass(frozen=True)
class SowingDomainConflictError(Exception):
    code: str
    message: str


@dataclass(frozen=True)
class SowingProjection:
    sowing: Sowing
    seed_lot: SeedLot
    botanical_identity: BotanicalIdentity
    location: Location | None


def _require_references(
    database: Session, payload: SowingCreate | SowingUpdate
) -> tuple[SeedLot, Location | None]:
    seed_lot = database.get(SeedLot, payload.seed_lot_id)
    if seed_lot is None:
        raise SowingReferenceNotFoundError("seed_lot_not_found", "SeedLot not found")
    location = database.get(Location, payload.location_id) if payload.location_id else None
    if payload.location_id is not None and location is None:
        raise SowingReferenceNotFoundError("location_not_found", "Location not found")
    return seed_lot, location


def _write_values(payload: SowingCreate | SowingUpdate) -> dict[str, object]:
    date = payload.sowing_date
    quantity = payload.quantity
    return {
        "seed_lot_id": payload.seed_lot_id,
        "label": payload.label,
        "sowing_date_precision": date.precision.value if date else None,
        "sowing_date_year": date.year if date else None,
        "sowing_date_month": date.month if date else None,
        "sowing_date_day": date.day if date else None,
        "quantity_kind": quantity.kind.value if quantity else None,
        "quantity_value": quantity.value if quantity else None,
        "quantity_unit": quantity.unit.value if quantity and quantity.unit else None,
        "quantity_is_approximate": quantity.is_approximate if quantity else None,
        "germinated_count": payload.germinated_count,
        "location_id": payload.location_id,
        "substrate": payload.substrate,
        "method_container": payload.method_container,
        "pretreatment": payload.pretreatment,
        "temperature_min_c": payload.temperature_min_c,
        "temperature_max_c": payload.temperature_max_c,
        "environment": payload.environment,
        "lifecycle": payload.lifecycle.value,
        "notes": payload.notes,
    }


def create_sowing(database: Session, payload: SowingCreate) -> Sowing:
    _require_references(database, payload)
    sowing = Sowing(**_write_values(payload))
    database.add(sowing)
    database.flush()
    return sowing


def update_sowing(database: Session, sowing: Sowing, payload: SowingUpdate) -> Sowing:
    database.refresh(sowing, with_for_update=True)
    if (sowing.lifecycle == "reversed") != (payload.lifecycle.value == "reversed"):
        raise SowingDomainConflictError(
            "reversed_lifecycle_immutable",
            "Reversed lifecycle is assigned only by reversal and cannot be changed",
        )
    if sowing.lifecycle == "reversed" and payload.seed_lot_id != sowing.seed_lot_id:
        raise SowingDomainConflictError(
            "reversed_origin_immutable", "Historical propagation origin cannot be changed"
        )
    _require_references(database, payload)
    for field, value in _write_values(payload).items():
        setattr(sowing, field, value)
    sowing.updated_at = datetime.now(UTC)
    database.flush()
    return sowing


def _projection_statement() -> Select[tuple[Sowing, SeedLot, BotanicalIdentity, Location]]:
    return (
        select(Sowing, SeedLot, BotanicalIdentity, Location)
        .join(SeedLot, SeedLot.id == Sowing.seed_lot_id)
        .join(BotanicalIdentity, BotanicalIdentity.id == SeedLot.botanical_identity_id)
        .outerjoin(Location, Location.id == Sowing.location_id)
    )


def get_sowing(database: Session, sowing_id: UUID) -> SowingProjection | None:
    row = database.execute(_projection_statement().where(Sowing.id == sowing_id)).one_or_none()
    return SowingProjection(*row) if row is not None else None


def list_sowings(
    database: Session, botanical_identity_id: UUID | None = None
) -> list[SowingProjection]:
    statement = _projection_statement()
    if botanical_identity_id is not None:
        statement = statement.where(SeedLot.botanical_identity_id == botanical_identity_id)
    statement = statement.order_by(
        case((Sowing.lifecycle == "active", 0), else_=1),
        case((Sowing.sowing_date_precision.is_not(None), 0), else_=1),
        desc(Sowing.sowing_date_year).nulls_last(),
        desc(Sowing.sowing_date_month).nulls_last(),
        desc(Sowing.sowing_date_day).nulls_last(),
        case(
            (Sowing.sowing_date_precision == "day", 0),
            (Sowing.sowing_date_precision == "month", 1),
            (Sowing.sowing_date_precision == "year", 2),
            else_=3,
        ),
        func.lower(Sowing.label).nulls_last(),
        Sowing.id,
    )
    return [SowingProjection(*row) for row in database.execute(statement)]


def _partial_date(sowing: Sowing) -> PartialDate | None:
    if sowing.sowing_date_precision is None:
        return None
    return PartialDate(
        precision=sowing.sowing_date_precision,
        year=sowing.sowing_date_year,
        month=sowing.sowing_date_month,
        day=sowing.sowing_date_day,
    )


def _quantity(sowing: Sowing) -> SowingQuantity | None:
    if sowing.quantity_kind is None:
        return None
    assert isinstance(sowing.quantity_value, Decimal)
    assert sowing.quantity_is_approximate is not None
    return SowingQuantity(
        kind=sowing.quantity_kind,
        value=sowing.quantity_value,
        unit=sowing.quantity_unit,
        is_approximate=sowing.quantity_is_approximate,
    )


def responses(database: Session, projections: list[SowingProjection]) -> list[SowingResponse]:
    locations = list_locations(database) if any(item.location for item in projections) else []
    result: list[SowingResponse] = []
    for item in projections:
        sowing = item.sowing
        botanical = BotanicalIdentityResponse.from_model(item.botanical_identity)
        result.append(
            SowingResponse(
                id=sowing.id,
                seed_lot_id=sowing.seed_lot_id,
                seed_lot=SowingSeedLotSummary(
                    id=item.seed_lot.id,
                    label=item.seed_lot.label,
                    lifecycle=item.seed_lot.lifecycle,
                    botanical_identity_id=item.seed_lot.botanical_identity_id,
                    botanical_identity_display_label=botanical.display_label,
                ),
                label=sowing.label,
                sowing_date=_partial_date(sowing),
                quantity=_quantity(sowing),
                germinated_count=sowing.germinated_count,
                location_id=sowing.location_id,
                location=(
                    SowingLocationSummary(
                        id=item.location.id,
                        display_path=display_path(item.location, locations),
                    )
                    if item.location
                    else None
                ),
                substrate=sowing.substrate,
                method_container=sowing.method_container,
                pretreatment=sowing.pretreatment,
                temperature_min_c=sowing.temperature_min_c,
                temperature_max_c=sowing.temperature_max_c,
                environment=sowing.environment,
                lifecycle=sowing.lifecycle,
                notes=sowing.notes,
                created_at=sowing.created_at,
                updated_at=sowing.updated_at,
            )
        )
    return result
