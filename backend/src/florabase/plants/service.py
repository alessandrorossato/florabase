from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import case, desc, func, select
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql import Select

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.schemas import BotanicalIdentityResponse
from florabase.geographic_places.model import GeographicPlace
from florabase.geographic_places.service import display_path as geographic_display_path
from florabase.geographic_places.service import list_geographic_places
from florabase.locations.model import Location
from florabase.locations.service import display_path as location_display_path
from florabase.locations.service import list_locations
from florabase.plants.model import Plant, PlantGroup
from florabase.plants.schemas import (
    BotanicalIdentitySummary,
    GeographicPlaceSummary,
    LocationSummary,
    OriginatingPlantGroupSummary,
    OriginatingSowingSummary,
    PlantCommonWrite,
    PlantCreate,
    PlantExtractionCreate,
    PlantGroupCreate,
    PlantGroupQuantity,
    PlantGroupResponse,
    PlantGroupUpdate,
    PlantResponse,
    PlantUpdate,
    SupplierSummary,
)
from florabase.seed_lots.model import SeedLot
from florabase.seed_lots.schemas import PartialDate
from florabase.sowings.model import Sowing
from florabase.suppliers.model import Supplier


@dataclass(frozen=True)
class PlantReferenceNotFoundError(Exception):
    code: str
    message: str


@dataclass(frozen=True)
class PlantDomainConflictError(Exception):
    code: str
    message: str


@dataclass(frozen=True)
class PlantProjection:
    plant: Plant
    botanical_identity: BotanicalIdentity
    originating_sowing: Sowing | None
    originating_seed_lot: SeedLot | None
    originating_botanical_identity: BotanicalIdentity | None
    supplier: Supplier | None
    material_provenance: GeographicPlace | None
    location: Location | None
    originating_plant_group: PlantGroup | None
    originating_plant_group_identity: BotanicalIdentity | None


@dataclass(frozen=True)
class PlantGroupProjection:
    plant_group: PlantGroup
    botanical_identity: BotanicalIdentity
    originating_sowing: Sowing | None
    originating_seed_lot: SeedLot | None
    originating_botanical_identity: BotanicalIdentity | None
    supplier: Supplier | None
    material_provenance: GeographicPlace | None
    location: Location | None


def _require_references(database: Session, payload: PlantCommonWrite) -> None:
    references: tuple[tuple[type[object], UUID | None, str, str], ...] = (
        (
            BotanicalIdentity,
            payload.botanical_identity_id,
            "botanical_identity_not_found",
            "Botanical identity not found",
        ),
        (Sowing, payload.originating_sowing_id, "sowing_not_found", "Sowing not found"),
        (Supplier, payload.supplier_id, "supplier_not_found", "Supplier not found"),
        (
            GeographicPlace,
            payload.material_provenance_place_id,
            "geographic_place_not_found",
            "Geographic place not found",
        ),
        (Location, payload.location_id, "location_not_found", "Location not found"),
    )
    for model, item_id, code, message in references:
        if item_id is not None and database.get(model, item_id) is None:
            raise PlantReferenceNotFoundError(code, message)


def _partial_date_values(value: PartialDate | None) -> dict[str, object]:
    return {
        "collection_entry_date_precision": value.precision.value if value else None,
        "collection_entry_date_year": value.year if value else None,
        "collection_entry_date_month": value.month if value else None,
        "collection_entry_date_day": value.day if value else None,
    }


def _common_write_values(payload: PlantCommonWrite) -> dict[str, object]:
    values: dict[str, object] = {
        "botanical_identity_id": payload.botanical_identity_id,
        "originating_sowing_id": payload.originating_sowing_id,
        "direct_origin_kind": (
            payload.direct_origin_kind.value
            if payload.direct_origin_kind
            else ("unknown" if payload.originating_sowing_id is None else None)
        ),
        "direct_origin_detail": payload.direct_origin_detail,
        "supplier_id": payload.supplier_id,
        "material_provenance_place_id": payload.material_provenance_place_id,
        "label": payload.label,
        "location_id": payload.location_id,
        "notes": payload.notes,
    }
    values.update(_partial_date_values(payload.collection_entry_date))
    return values


def create_plant(database: Session, payload: PlantCreate) -> Plant:
    _require_references(database, payload)
    plant = Plant(**_common_write_values(payload), lifecycle=payload.lifecycle.value)
    database.add(plant)
    database.flush()
    return plant


def update_plant(database: Session, plant: Plant, payload: PlantUpdate) -> Plant:
    _require_references(database, payload)
    if plant.originating_plant_group_id is not None:
        forbidden = {
            "originating_sowing_id",
            "direct_origin_kind",
            "direct_origin_detail",
            "supplier_id",
            "material_provenance_place_id",
        }
        if payload.model_fields_set & forbidden:
            raise PlantDomainConflictError(
                "extracted_plant_origin_immutable",
                "An extracted Plant's PlantGroup origin cannot be changed through ordinary editing",
            )
        values = {
            "botanical_identity_id": payload.botanical_identity_id,
            "label": payload.label,
            "location_id": payload.location_id,
            "notes": payload.notes,
            **_partial_date_values(payload.collection_entry_date),
        }
    else:
        values = _common_write_values(payload)
    values["lifecycle"] = payload.lifecycle.value
    for field, value in values.items():
        setattr(plant, field, value)
    plant.updated_at = datetime.now(UTC)
    database.flush()
    return plant


def extract_plant(
    database: Session, plant_group_id: UUID, payload: PlantExtractionCreate
) -> tuple[Plant, PlantGroup]:
    plant_group = database.scalar(
        select(PlantGroup).where(PlantGroup.id == plant_group_id).with_for_update()
    )
    if plant_group is None:
        raise PlantReferenceNotFoundError("plant_group_not_found", "PlantGroup not found")
    if plant_group.lifecycle != "active":
        raise PlantDomainConflictError(
            "plant_group_not_active", "Only an active PlantGroup can have a Plant extracted"
        )
    identity_id = payload.botanical_identity_id or plant_group.botanical_identity_id
    location_id = (
        payload.location_id
        if "location_id" in payload.model_fields_set
        else plant_group.location_id
    )
    if database.get(BotanicalIdentity, identity_id) is None:
        raise PlantReferenceNotFoundError(
            "botanical_identity_not_found", "Botanical identity not found"
        )
    if location_id is not None and database.get(Location, location_id) is None:
        raise PlantReferenceNotFoundError("location_not_found", "Location not found")
    plant = Plant(
        botanical_identity_id=identity_id,
        originating_plant_group_id=plant_group.id,
        originating_sowing_id=None,
        direct_origin_kind=None,
        direct_origin_detail=None,
        supplier_id=None,
        material_provenance_place_id=None,
        label=payload.label,
        location_id=location_id,
        notes=payload.notes,
        lifecycle="active",
        **_partial_date_values(payload.collection_entry_date),
    )
    database.add(plant)
    if plant_group.quantity_value is not None and plant_group.quantity_is_approximate is False:
        if plant_group.quantity_value < 1:
            raise PlantDomainConflictError(
                "plant_group_quantity_exhausted",
                "The PlantGroup has no exact members available to extract",
            )
        plant_group.quantity_value -= 1
        if plant_group.quantity_value == 0:
            plant_group.lifecycle = "completed"
        plant_group.updated_at = datetime.now(UTC)
    database.flush()
    return plant, plant_group


def create_plant_group(database: Session, payload: PlantGroupCreate) -> PlantGroup:
    _require_references(database, payload)
    values = _common_write_values(payload)
    values.update(
        quantity_value=payload.quantity.value if payload.quantity else None,
        quantity_is_approximate=(
            payload.quantity.is_approximate if payload.quantity is not None else None
        ),
        lifecycle=payload.lifecycle.value,
    )
    plant_group = PlantGroup(**values)
    database.add(plant_group)
    database.flush()
    return plant_group


def update_plant_group(
    database: Session, plant_group: PlantGroup, payload: PlantGroupUpdate
) -> PlantGroup:
    _require_references(database, payload)
    values = _common_write_values(payload)
    values.update(
        quantity_value=payload.quantity.value if payload.quantity else None,
        quantity_is_approximate=(
            payload.quantity.is_approximate if payload.quantity is not None else None
        ),
        lifecycle=payload.lifecycle.value,
    )
    for field, value in values.items():
        setattr(plant_group, field, value)
    plant_group.updated_at = datetime.now(UTC)
    database.flush()
    return plant_group


def _plant_projection_statement() -> Select[
    tuple[
        Plant,
        BotanicalIdentity,
        Sowing,
        SeedLot,
        BotanicalIdentity,
        Supplier,
        GeographicPlace,
        Location,
        PlantGroup,
        BotanicalIdentity,
    ]
]:
    sowing = aliased(Sowing)
    seed_lot = aliased(SeedLot)
    origin_identity = aliased(BotanicalIdentity)
    supplier = aliased(Supplier)
    place = aliased(GeographicPlace)
    location = aliased(Location)
    originating_group = aliased(PlantGroup)
    originating_group_identity = aliased(BotanicalIdentity)
    return (
        select(
            Plant,
            BotanicalIdentity,
            sowing,
            seed_lot,
            origin_identity,
            supplier,
            place,
            location,
            originating_group,
            originating_group_identity,
        )
        .join(BotanicalIdentity, BotanicalIdentity.id == Plant.botanical_identity_id)
        .outerjoin(sowing, sowing.id == Plant.originating_sowing_id)
        .outerjoin(seed_lot, seed_lot.id == sowing.seed_lot_id)
        .outerjoin(origin_identity, origin_identity.id == seed_lot.botanical_identity_id)
        .outerjoin(supplier, supplier.id == Plant.supplier_id)
        .outerjoin(place, place.id == Plant.material_provenance_place_id)
        .outerjoin(location, location.id == Plant.location_id)
        .outerjoin(originating_group, originating_group.id == Plant.originating_plant_group_id)
        .outerjoin(
            originating_group_identity,
            originating_group_identity.id == originating_group.botanical_identity_id,
        )
    )


def _plant_group_projection_statement() -> Select[
    tuple[
        PlantGroup,
        BotanicalIdentity,
        Sowing,
        SeedLot,
        BotanicalIdentity,
        Supplier,
        GeographicPlace,
        Location,
    ]
]:
    sowing = aliased(Sowing)
    seed_lot = aliased(SeedLot)
    origin_identity = aliased(BotanicalIdentity)
    supplier = aliased(Supplier)
    place = aliased(GeographicPlace)
    location = aliased(Location)
    return (
        select(
            PlantGroup,
            BotanicalIdentity,
            sowing,
            seed_lot,
            origin_identity,
            supplier,
            place,
            location,
        )
        .join(BotanicalIdentity, BotanicalIdentity.id == PlantGroup.botanical_identity_id)
        .outerjoin(sowing, sowing.id == PlantGroup.originating_sowing_id)
        .outerjoin(seed_lot, seed_lot.id == sowing.seed_lot_id)
        .outerjoin(origin_identity, origin_identity.id == seed_lot.botanical_identity_id)
        .outerjoin(supplier, supplier.id == PlantGroup.supplier_id)
        .outerjoin(place, place.id == PlantGroup.material_provenance_place_id)
        .outerjoin(location, location.id == PlantGroup.location_id)
    )


def get_plant(database: Session, plant_id: UUID) -> PlantProjection | None:
    row = database.execute(_plant_projection_statement().where(Plant.id == plant_id)).one_or_none()
    return PlantProjection(*row) if row is not None else None


def get_plant_group(database: Session, plant_group_id: UUID) -> PlantGroupProjection | None:
    row = database.execute(
        _plant_group_projection_statement().where(PlantGroup.id == plant_group_id)
    ).one_or_none()
    return PlantGroupProjection(*row) if row is not None else None


def _ordering(
    model: type[Plant] | type[PlantGroup],
) -> tuple[Any, ...]:
    return (
        case((model.lifecycle == "active", 0), else_=1),
        func.lower(BotanicalIdentity.scientific_name),
        func.lower(BotanicalIdentity.cultivar_name).nulls_first(),
        func.lower(model.label).nulls_first(),
        case((model.collection_entry_date_precision.is_not(None), 0), else_=1),
        desc(model.collection_entry_date_year).nulls_last(),
        desc(model.collection_entry_date_month).nulls_last(),
        desc(model.collection_entry_date_day).nulls_last(),
        case(
            (model.collection_entry_date_precision == "day", 0),
            (model.collection_entry_date_precision == "month", 1),
            (model.collection_entry_date_precision == "year", 2),
            else_=3,
        ),
        model.id,
    )


def list_plants(
    database: Session, botanical_identity_id: UUID | None = None
) -> list[PlantProjection]:
    statement = _plant_projection_statement()
    if botanical_identity_id is not None:
        statement = statement.where(Plant.botanical_identity_id == botanical_identity_id)
    return [
        PlantProjection(*row) for row in database.execute(statement.order_by(*_ordering(Plant)))
    ]


def list_plant_groups(
    database: Session, botanical_identity_id: UUID | None = None
) -> list[PlantGroupProjection]:
    statement = _plant_group_projection_statement()
    if botanical_identity_id is not None:
        statement = statement.where(PlantGroup.botanical_identity_id == botanical_identity_id)
    return [
        PlantGroupProjection(*row)
        for row in database.execute(statement.order_by(*_ordering(PlantGroup)))
    ]


def _partial_date(record: Plant | PlantGroup) -> PartialDate | None:
    if record.collection_entry_date_precision is None:
        return None
    return PartialDate(
        precision=record.collection_entry_date_precision,
        year=record.collection_entry_date_year,
        month=record.collection_entry_date_month,
        day=record.collection_entry_date_day,
    )


def _common_response_values(
    record: Plant | PlantGroup,
    botanical_identity: BotanicalIdentity,
    originating_sowing: Sowing | None,
    originating_seed_lot: SeedLot | None,
    originating_botanical_identity: BotanicalIdentity | None,
    supplier: Supplier | None,
    material_provenance: GeographicPlace | None,
    location: Location | None,
    places: list[GeographicPlace],
    locations: list[Location],
) -> dict[str, object]:
    botanical = BotanicalIdentityResponse.from_model(botanical_identity)
    origin_botanical = (
        BotanicalIdentityResponse.from_model(originating_botanical_identity)
        if originating_botanical_identity
        else None
    )
    return {
        "id": record.id,
        "botanical_identity_id": record.botanical_identity_id,
        "botanical_identity": BotanicalIdentitySummary(
            id=botanical.id, display_label=botanical.display_label
        ),
        "originating_sowing_id": record.originating_sowing_id,
        "originating_sowing": (
            OriginatingSowingSummary(
                id=originating_sowing.id,
                label=originating_sowing.label,
                lifecycle=originating_sowing.lifecycle,
                seed_lot_id=originating_sowing.seed_lot_id,
                botanical_identity_id=originating_seed_lot.botanical_identity_id,
                botanical_identity_display_label=origin_botanical.display_label,
            )
            if originating_sowing and originating_seed_lot and origin_botanical
            else None
        ),
        "direct_origin_kind": record.direct_origin_kind,
        "direct_origin_detail": record.direct_origin_detail,
        "supplier_id": record.supplier_id,
        "supplier": SupplierSummary(id=supplier.id, name=supplier.name) if supplier else None,
        "material_provenance_place_id": record.material_provenance_place_id,
        "material_provenance": (
            GeographicPlaceSummary(
                id=material_provenance.id,
                display_path=geographic_display_path(material_provenance, places),
            )
            if material_provenance
            else None
        ),
        "label": record.label,
        "collection_entry_date": _partial_date(record),
        "location_id": record.location_id,
        "location": (
            LocationSummary(id=location.id, display_path=location_display_path(location, locations))
            if location
            else None
        ),
        "notes": record.notes,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


def plant_responses(database: Session, projections: list[PlantProjection]) -> list[PlantResponse]:
    places = (
        list_geographic_places(database)
        if any(item.material_provenance for item in projections)
        else []
    )
    locations = list_locations(database) if any(item.location for item in projections) else []
    return [
        PlantResponse(
            **_common_response_values(
                item.plant,
                item.botanical_identity,
                item.originating_sowing,
                item.originating_seed_lot,
                item.originating_botanical_identity,
                item.supplier,
                item.material_provenance,
                item.location,
                places,
                locations,
            ),
            lifecycle=item.plant.lifecycle,
            originating_plant_group_id=item.plant.originating_plant_group_id,
            originating_plant_group=(
                OriginatingPlantGroupSummary(
                    id=item.originating_plant_group.id,
                    label=item.originating_plant_group.label,
                    lifecycle=item.originating_plant_group.lifecycle,
                    botanical_identity=BotanicalIdentitySummary(
                        id=item.originating_plant_group_identity.id,
                        display_label=BotanicalIdentityResponse.from_model(
                            item.originating_plant_group_identity
                        ).display_label,
                    ),
                    quantity=(
                        PlantGroupQuantity(
                            value=item.originating_plant_group.quantity_value,
                            is_approximate=item.originating_plant_group.quantity_is_approximate,
                        )
                        if item.originating_plant_group.quantity_value is not None
                        and item.originating_plant_group.quantity_is_approximate is not None
                        else None
                    ),
                )
                if item.originating_plant_group and item.originating_plant_group_identity
                else None
            ),
        )
        for item in projections
    ]


def plant_group_responses(
    database: Session, projections: list[PlantGroupProjection]
) -> list[PlantGroupResponse]:
    places = (
        list_geographic_places(database)
        if any(item.material_provenance for item in projections)
        else []
    )
    locations = list_locations(database) if any(item.location for item in projections) else []
    result: list[PlantGroupResponse] = []
    for item in projections:
        quantity = (
            PlantGroupQuantity(
                value=item.plant_group.quantity_value,
                is_approximate=item.plant_group.quantity_is_approximate,
            )
            if item.plant_group.quantity_value is not None
            and item.plant_group.quantity_is_approximate is not None
            else None
        )
        result.append(
            PlantGroupResponse(
                **_common_response_values(
                    item.plant_group,
                    item.botanical_identity,
                    item.originating_sowing,
                    item.originating_seed_lot,
                    item.originating_botanical_identity,
                    item.supplier,
                    item.material_provenance,
                    item.location,
                    places,
                    locations,
                ),
                quantity=quantity,
                lifecycle=item.plant_group.lifecycle,
            )
        )
    return result
