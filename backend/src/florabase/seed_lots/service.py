from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid7

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql import Select

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.schemas import BotanicalIdentityResponse
from florabase.geographic_places.model import GeographicPlace
from florabase.geographic_places.service import display_path as geographic_display_path
from florabase.geographic_places.service import list_geographic_places
from florabase.lineage.service import validate_producer_assignment
from florabase.locations.model import Location
from florabase.locations.service import display_path as location_display_path
from florabase.locations.service import list_locations
from florabase.plants.model import Plant, PlantGroup
from florabase.seed_lots.model import SeedLot
from florabase.seed_lots.schemas import (
    BotanicalIdentitySummary,
    GeographicPlaceSummary,
    LocationSummary,
    PartialDate,
    ProducerPlantGroupSummary,
    ProducerPlantSummary,
    SeedLotCreate,
    SeedLotResponse,
    SeedLotUpdate,
    SeedQuantity,
    SupplierSummary,
)
from florabase.suppliers.model import Supplier


@dataclass(frozen=True)
class SeedLotReferenceNotFoundError(Exception):
    code: str
    message: str


@dataclass(frozen=True)
class SeedLotProjection:
    seed_lot: SeedLot
    botanical_identity: BotanicalIdentity
    supplier: Supplier | None
    material_provenance: GeographicPlace | None
    location: Location | None
    producer_plant: Plant | None = None
    producer_plant_identity: BotanicalIdentity | None = None
    producer_plant_group: PlantGroup | None = None
    producer_plant_group_identity: BotanicalIdentity | None = None


def _require_references(
    database: Session, payload: SeedLotCreate | SeedLotUpdate
) -> tuple[
    BotanicalIdentity,
    Supplier | None,
    GeographicPlace | None,
    Location | None,
    Plant | None,
    PlantGroup | None,
]:
    botanical_identity = database.get(BotanicalIdentity, payload.botanical_identity_id)
    if botanical_identity is None:
        raise SeedLotReferenceNotFoundError(
            "botanical_identity_not_found", "Botanical identity not found"
        )
    supplier = database.get(Supplier, payload.supplier_id) if payload.supplier_id else None
    if payload.supplier_id is not None and supplier is None:
        raise SeedLotReferenceNotFoundError("supplier_not_found", "Supplier not found")
    place = (
        database.get(GeographicPlace, payload.material_provenance_place_id)
        if payload.material_provenance_place_id
        else None
    )
    if payload.material_provenance_place_id is not None and place is None:
        raise SeedLotReferenceNotFoundError(
            "geographic_place_not_found", "Geographic place not found"
        )
    location = database.get(Location, payload.location_id) if payload.location_id else None
    if payload.location_id is not None and location is None:
        raise SeedLotReferenceNotFoundError("location_not_found", "Location not found")
    producer_plant = (
        database.get(Plant, payload.producer_plant_id) if payload.producer_plant_id else None
    )
    if payload.producer_plant_id is not None and producer_plant is None:
        raise SeedLotReferenceNotFoundError("producer_plant_not_found", "Producer Plant not found")
    producer_group = (
        database.get(PlantGroup, payload.producer_plant_group_id)
        if payload.producer_plant_group_id
        else None
    )
    if payload.producer_plant_group_id is not None and producer_group is None:
        raise SeedLotReferenceNotFoundError(
            "producer_plant_group_not_found", "Producer PlantGroup not found"
        )
    return botanical_identity, supplier, place, location, producer_plant, producer_group


def _partial_date_values(prefix: str, value: PartialDate | None) -> dict[str, object]:
    return {
        f"{prefix}_precision": value.precision.value if value else None,
        f"{prefix}_year": value.year if value else None,
        f"{prefix}_month": value.month if value else None,
        f"{prefix}_day": value.day if value else None,
    }


def _quantity_values(value: SeedQuantity | None) -> dict[str, object]:
    return {
        "quantity_kind": value.kind.value if value else None,
        "quantity_value": value.value if value else None,
        "quantity_unit": value.unit.value if value and value.unit else None,
        "quantity_is_approximate": value.is_approximate if value else None,
    }


def _write_values(payload: SeedLotCreate | SeedLotUpdate) -> dict[str, object]:
    values: dict[str, object] = {
        "botanical_identity_id": payload.botanical_identity_id,
        "label": payload.label,
        "source_kind": payload.source_kind.value,
        "source_detail": payload.source_detail,
        "producer_plant_id": payload.producer_plant_id,
        "producer_plant_group_id": payload.producer_plant_group_id,
        "supplier_id": payload.supplier_id,
        "material_provenance_place_id": payload.material_provenance_place_id,
        "location_id": payload.location_id,
        "lifecycle": payload.lifecycle.value,
        "notes": payload.notes,
    }
    values.update(_partial_date_values("acquisition_date", payload.acquisition_date))
    values.update(_partial_date_values("harvest_date", payload.harvest_date))
    values.update(
        _partial_date_values("expected_viability_until", payload.expected_viability_until)
    )
    values.update(_quantity_values(payload.quantity))
    return values


def create_seed_lot(database: Session, payload: SeedLotCreate) -> SeedLot:
    _lock_new_producers(database, payload)
    _require_references(database, payload)
    seed_lot = SeedLot(id=uuid7(), **_write_values(payload))
    validate_producer_assignment(
        database, seed_lot.id, payload.producer_plant_id, payload.producer_plant_group_id
    )
    database.add(seed_lot)
    database.flush()
    return seed_lot


def update_seed_lot(database: Session, seed_lot: SeedLot, payload: SeedLotUpdate) -> SeedLot:
    database.refresh(seed_lot, with_for_update=True)
    _lock_new_producers(database, payload, seed_lot)
    _require_references(database, payload)
    validate_producer_assignment(
        database, seed_lot.id, payload.producer_plant_id, payload.producer_plant_group_id
    )
    for field, value in _write_values(payload).items():
        setattr(seed_lot, field, value)
    seed_lot.updated_at = datetime.now(UTC)
    database.flush()
    return seed_lot


def _projection_statement() -> Select[
    tuple[
        SeedLot,
        BotanicalIdentity,
        Supplier,
        GeographicPlace,
        Location,
        Plant,
        BotanicalIdentity,
        PlantGroup,
        BotanicalIdentity,
    ]
]:
    supplier = aliased(Supplier)
    place = aliased(GeographicPlace)
    location = aliased(Location)
    producer_plant = aliased(Plant)
    producer_plant_identity = aliased(BotanicalIdentity)
    producer_group = aliased(PlantGroup)
    producer_group_identity = aliased(BotanicalIdentity)
    return (
        select(
            SeedLot,
            BotanicalIdentity,
            supplier,
            place,
            location,
            producer_plant,
            producer_plant_identity,
            producer_group,
            producer_group_identity,
        )
        .join(BotanicalIdentity, BotanicalIdentity.id == SeedLot.botanical_identity_id)
        .outerjoin(supplier, supplier.id == SeedLot.supplier_id)
        .outerjoin(place, place.id == SeedLot.material_provenance_place_id)
        .outerjoin(location, location.id == SeedLot.location_id)
        .outerjoin(producer_plant, producer_plant.id == SeedLot.producer_plant_id)
        .outerjoin(
            producer_plant_identity,
            producer_plant_identity.id == producer_plant.botanical_identity_id,
        )
        .outerjoin(producer_group, producer_group.id == SeedLot.producer_plant_group_id)
        .outerjoin(
            producer_group_identity,
            producer_group_identity.id == producer_group.botanical_identity_id,
        )
    )


def get_seed_lot(database: Session, seed_lot_id: UUID) -> SeedLotProjection | None:
    row = database.execute(_projection_statement().where(SeedLot.id == seed_lot_id)).one_or_none()
    return SeedLotProjection(*row) if row is not None else None


def list_seed_lots(
    database: Session, botanical_identity_id: UUID | None = None
) -> list[SeedLotProjection]:
    statement = _projection_statement()
    if botanical_identity_id is not None:
        statement = statement.where(SeedLot.botanical_identity_id == botanical_identity_id)
    statement = statement.order_by(
        case((SeedLot.lifecycle == "active", 0), else_=1),
        func.lower(BotanicalIdentity.scientific_name),
        func.lower(BotanicalIdentity.cultivar_name).nulls_first(),
        func.lower(SeedLot.label).nulls_first(),
        SeedLot.id,
    )
    return [SeedLotProjection(*row) for row in database.execute(statement)]


def _partial_date(seed_lot: SeedLot, prefix: str) -> PartialDate | None:
    precision = getattr(seed_lot, f"{prefix}_precision")
    if precision is None:
        return None
    return PartialDate(
        precision=precision,
        year=getattr(seed_lot, f"{prefix}_year"),
        month=getattr(seed_lot, f"{prefix}_month"),
        day=getattr(seed_lot, f"{prefix}_day"),
    )


def _quantity(seed_lot: SeedLot) -> SeedQuantity | None:
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


def responses(database: Session, projections: list[SeedLotProjection]) -> list[SeedLotResponse]:
    places = (
        list_geographic_places(database)
        if any(item.material_provenance for item in projections)
        else []
    )
    locations = list_locations(database) if any(item.location for item in projections) else []
    result: list[SeedLotResponse] = []
    for item in projections:
        seed_lot = item.seed_lot
        botanical = BotanicalIdentityResponse.from_model(item.botanical_identity)
        result.append(
            SeedLotResponse(
                id=seed_lot.id,
                botanical_identity_id=seed_lot.botanical_identity_id,
                botanical_identity=BotanicalIdentitySummary(
                    id=botanical.id, display_label=botanical.display_label
                ),
                label=seed_lot.label,
                source_kind=seed_lot.source_kind,
                source_detail=seed_lot.source_detail,
                producer_plant_id=seed_lot.producer_plant_id,
                producer_plant=(
                    ProducerPlantSummary(
                        id=item.producer_plant.id,
                        label=item.producer_plant.label,
                        lifecycle=item.producer_plant.lifecycle,
                        botanical_identity=BotanicalIdentitySummary(
                            id=item.producer_plant_identity.id,
                            display_label=BotanicalIdentityResponse.from_model(
                                item.producer_plant_identity
                            ).display_label,
                        ),
                    )
                    if item.producer_plant and item.producer_plant_identity
                    else None
                ),
                producer_plant_group_id=seed_lot.producer_plant_group_id,
                producer_plant_group=(
                    ProducerPlantGroupSummary(
                        id=item.producer_plant_group.id,
                        label=item.producer_plant_group.label,
                        lifecycle=item.producer_plant_group.lifecycle,
                        botanical_identity=BotanicalIdentitySummary(
                            id=item.producer_plant_group_identity.id,
                            display_label=BotanicalIdentityResponse.from_model(
                                item.producer_plant_group_identity
                            ).display_label,
                        ),
                    )
                    if item.producer_plant_group and item.producer_plant_group_identity
                    else None
                ),
                supplier_id=seed_lot.supplier_id,
                supplier=(
                    SupplierSummary(id=item.supplier.id, name=item.supplier.name)
                    if item.supplier
                    else None
                ),
                material_provenance_place_id=seed_lot.material_provenance_place_id,
                material_provenance=(
                    GeographicPlaceSummary(
                        id=item.material_provenance.id,
                        display_path=geographic_display_path(item.material_provenance, places),
                    )
                    if item.material_provenance
                    else None
                ),
                acquisition_date=_partial_date(seed_lot, "acquisition_date"),
                harvest_date=_partial_date(seed_lot, "harvest_date"),
                quantity=_quantity(seed_lot),
                expected_viability_until=_partial_date(seed_lot, "expected_viability_until"),
                location_id=seed_lot.location_id,
                location=(
                    LocationSummary(
                        id=item.location.id,
                        display_path=location_display_path(item.location, locations),
                    )
                    if item.location
                    else None
                ),
                lifecycle=seed_lot.lifecycle,
                notes=seed_lot.notes,
                created_at=seed_lot.created_at,
                updated_at=seed_lot.updated_at,
            )
        )
    return result


def _lock_new_producers(
    database: Session, payload: SeedLotCreate | SeedLotUpdate, existing: SeedLot | None = None
) -> None:
    for model, field in ((PlantGroup, "producer_plant_group_id"), (Plant, "producer_plant_id")):
        producer_id = getattr(payload, field)
        if producer_id is None or (
            existing is not None and producer_id == getattr(existing, field)
        ):
            continue
        producer = database.scalar(
            select(model)
            .where(model.id == producer_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        assert producer is None or isinstance(producer, (Plant, PlantGroup))
        if producer is not None and producer.lifecycle in {"reversed", "reintegrated"}:
            raise SeedLotReferenceNotFoundError(
                "producer_is_historical",
                "A reversed or reintegrated record cannot produce a new SeedLot",
            )
