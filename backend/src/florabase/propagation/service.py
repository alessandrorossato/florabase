from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from florabase.plants.model import Plant, PlantGroup
from florabase.plants.schemas import PlantCreate, PlantGroupCreate, PlantGroupQuantity
from florabase.plants.service import create_plant, create_plant_group
from florabase.propagation.schemas import (
    PartialSourceAdjustment,
    PlantFromSowingCreate,
    PlantGroupFromSowingCreate,
    PropagationPlantGroupSummary,
    PropagationPlantSummary,
    SeedLotSowingTransitionCreate,
    SowingPropagationSummary,
)
from florabase.seed_lots.model import SeedLot
from florabase.seed_lots.schemas import SeedQuantity
from florabase.sowings.model import Sowing
from florabase.sowings.schemas import SowingCreate, SowingQuantity
from florabase.sowings.service import create_sowing


@dataclass(frozen=True)
class PropagationNotFoundError(Exception):
    code: str
    message: str


@dataclass(frozen=True)
class PropagationConflictError(Exception):
    code: str
    message: str


def _compatible(left: SeedQuantity, right: SeedQuantity | SowingQuantity) -> bool:
    return left.kind == right.kind and left.unit == right.unit


def _stored_quantity(seed_lot: SeedLot) -> SeedQuantity | None:
    if seed_lot.quantity_kind is None:
        return None
    assert isinstance(seed_lot.quantity_value, Decimal)
    assert seed_lot.quantity_is_approximate is not None
    return SeedQuantity(
        kind=seed_lot.quantity_kind,
        value=seed_lot.quantity_value,
        unit=seed_lot.quantity_unit,
        is_approximate=seed_lot.quantity_is_approximate,
    )


def _set_seed_lot_quantity(seed_lot: SeedLot, quantity: SeedQuantity | None) -> None:
    seed_lot.quantity_kind = quantity.kind.value if quantity else None
    seed_lot.quantity_value = quantity.value if quantity else None
    seed_lot.quantity_unit = quantity.unit.value if quantity and quantity.unit else None
    seed_lot.quantity_is_approximate = quantity.is_approximate if quantity else None


def _require_active_source(seed_lot: SeedLot) -> None:
    if seed_lot.lifecycle != "active":
        raise PropagationConflictError(
            "seed_lot_not_active", "Only an active SeedLot can be adjusted by propagation"
        )


def _apply_partial_adjustment(
    seed_lot: SeedLot,
    sowing: SowingCreate,
    adjustment: PartialSourceAdjustment,
) -> None:
    _require_active_source(seed_lot)
    source = _stored_quantity(seed_lot)
    used = sowing.quantity
    if source is None:
        if adjustment.resulting_quantity is not None:
            raise PropagationConflictError(
                "unknown_source_numeric_remainder",
                "An unknown SeedLot quantity must remain unknown after partial use",
            )
        return
    if used is None:
        raise PropagationConflictError(
            "partial_usage_quantity_required",
            "A numeric SeedLot quantity requires a Sowing quantity for partial use",
        )
    if not _compatible(source, used):
        raise PropagationConflictError(
            "incompatible_seed_quantities",
            "SeedLot and Sowing quantities must use the same dimension and unit",
        )
    if not source.is_approximate:
        if used.is_approximate:
            raise PropagationConflictError(
                "exact_source_requires_exact_usage",
                "An exact SeedLot can only be subtracted by an exact Sowing quantity",
            )
        if adjustment.resulting_quantity is not None:
            raise PropagationConflictError(
                "exact_remainder_is_derived",
                "The remainder of an exact SeedLot is calculated by Florabase",
            )
        remainder = source.value - used.value
        if remainder < 0:
            raise PropagationConflictError(
                "seed_lot_quantity_exceeded",
                "Sowing quantity exceeds the exact quantity available in the SeedLot",
            )
        _set_seed_lot_quantity(
            seed_lot,
            SeedQuantity(
                kind=source.kind,
                value=remainder,
                unit=source.unit,
                is_approximate=False,
            ),
        )
        if remainder == 0:
            seed_lot.lifecycle = "exhausted"
        return
    confirmed_remainder = adjustment.resulting_quantity
    if confirmed_remainder is None:
        raise PropagationConflictError(
            "approximate_remainder_required",
            "Partial use of an approximate SeedLot requires a confirmed approximate remainder",
        )
    if not confirmed_remainder.is_approximate or not _compatible(source, confirmed_remainder):
        raise PropagationConflictError(
            "invalid_approximate_remainder",
            "The confirmed remainder must stay approximate and use the source dimension and unit",
        )
    _set_seed_lot_quantity(seed_lot, confirmed_remainder)


def _validate_use_all(seed_lot: SeedLot, sowing: SowingCreate) -> SeedQuantity | None:
    _require_active_source(seed_lot)
    source = _stored_quantity(seed_lot)
    used = sowing.quantity
    if source is None or used is None:
        return source
    if not _compatible(source, used):
        raise PropagationConflictError(
            "incompatible_seed_quantities",
            "SeedLot and Sowing quantities must use the same dimension and unit",
        )
    if not source.is_approximate and not used.is_approximate and source.value != used.value:
        raise PropagationConflictError(
            "use_all_exact_quantity_mismatch",
            "An exact Sowing quantity must equal the exact source quantity when using all",
        )
    return source


def create_sowing_from_seed_lot(
    database: Session, seed_lot_id: UUID, payload: SeedLotSowingTransitionCreate
) -> tuple[Sowing, SeedLot]:
    seed_lot = database.scalar(select(SeedLot).where(SeedLot.id == seed_lot_id).with_for_update())
    if seed_lot is None:
        raise PropagationNotFoundError("seed_lot_not_found", "SeedLot not found")
    sowing_payload = SowingCreate(seed_lot_id=seed_lot.id, **payload.sowing.model_dump())
    adjustment = payload.source_adjustment
    if adjustment.mode == "partial":
        _apply_partial_adjustment(seed_lot, sowing_payload, adjustment)
    elif adjustment.mode == "use_all":
        source = _validate_use_all(seed_lot, sowing_payload)
        if source is not None and not source.is_approximate:
            _set_seed_lot_quantity(
                seed_lot,
                SeedQuantity(
                    kind=source.kind,
                    value=Decimal(0),
                    unit=source.unit,
                    is_approximate=False,
                ),
            )
        seed_lot.lifecycle = "exhausted"
    if adjustment.mode != "none":
        seed_lot.updated_at = datetime.now(UTC)
    sowing = create_sowing(database, sowing_payload)
    database.flush()
    return sowing, seed_lot


def _lock_sowing(database: Session, sowing_id: UUID) -> Sowing:
    sowing = database.scalar(select(Sowing).where(Sowing.id == sowing_id).with_for_update())
    if sowing is None:
        raise PropagationNotFoundError("sowing_not_found", "Sowing not found")
    return sowing


def create_plant_from_sowing(
    database: Session,
    sowing_id: UUID,
    payload: PlantFromSowingCreate,
    resulting_lifecycle: str,
) -> tuple[Plant, Sowing]:
    sowing = _lock_sowing(database, sowing_id)
    plant = create_plant(
        database,
        PlantCreate(
            **payload.model_dump(),
            originating_sowing_id=sowing.id,
        ),
    )
    sowing.lifecycle = resulting_lifecycle
    sowing.updated_at = datetime.now(UTC)
    database.flush()
    return plant, sowing


def create_plant_group_from_sowing(
    database: Session,
    sowing_id: UUID,
    payload: PlantGroupFromSowingCreate,
    resulting_lifecycle: str,
) -> tuple[PlantGroup, Sowing]:
    sowing = _lock_sowing(database, sowing_id)
    plant_group = create_plant_group(
        database,
        PlantGroupCreate(
            **payload.model_dump(),
            originating_sowing_id=sowing.id,
        ),
    )
    sowing.lifecycle = resulting_lifecycle
    sowing.updated_at = datetime.now(UTC)
    database.flush()
    return plant_group, sowing


def propagation_summary(database: Session, sowing_id: UUID) -> SowingPropagationSummary:
    sowing = database.get(Sowing, sowing_id)
    if sowing is None:
        raise PropagationNotFoundError("sowing_not_found", "Sowing not found")
    groups = list(
        database.scalars(
            select(PlantGroup)
            .where(PlantGroup.originating_sowing_id == sowing_id)
            .order_by(PlantGroup.id)
        )
    )
    group_ids = [group.id for group in groups]
    plants = list(
        database.scalars(
            select(Plant)
            .where(
                or_(
                    Plant.originating_sowing_id == sowing_id,
                    Plant.originating_plant_group_id.in_(group_ids),
                )
            )
            .order_by(Plant.id)
        )
    )
    exact_group_individuals = sum(
        group.quantity_value or 0 for group in groups if group.quantity_is_approximate is False
    )
    return SowingPropagationSummary(
        sowing_id=sowing.id,
        lifecycle=sowing.lifecycle,
        germinated_count=sowing.germinated_count,
        plants=[
            PropagationPlantSummary(
                id=plant.id,
                botanical_identity_id=plant.botanical_identity_id,
                label=plant.label,
                lifecycle=plant.lifecycle,
            )
            for plant in plants
        ],
        plant_groups=[
            PropagationPlantGroupSummary(
                id=group.id,
                botanical_identity_id=group.botanical_identity_id,
                label=group.label,
                lifecycle=group.lifecycle,
                quantity=(
                    PlantGroupQuantity(
                        value=group.quantity_value,
                        is_approximate=group.quantity_is_approximate,
                    )
                    if group.quantity_value is not None
                    and group.quantity_is_approximate is not None
                    else None
                ),
            )
            for group in groups
        ],
        exact_descendant_count=len(plants) + exact_group_individuals,
        approximate_plant_group_count=sum(
            group.quantity_is_approximate is True for group in groups
        ),
        unknown_plant_group_count=sum(group.quantity_value is None for group in groups),
    )
