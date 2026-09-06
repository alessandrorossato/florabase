from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import case, desc, func, select
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql import Select

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.schemas import BotanicalIdentityResponse
from florabase.events.model import Event, EventKind
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
    ReintegrationEligibilityStatus,
    ReintegrationReason,
    SupplierSummary,
)
from florabase.reversals.model import OperationKind, OperationReceipt, OperationStatus
from florabase.reversals.service import add_receipt, group_quantity
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


@dataclass(frozen=True)
class ReintegrationEvaluation:
    status: ReintegrationEligibilityStatus
    receipt: OperationReceipt | None
    plant: Plant
    plant_group: PlantGroup | None
    reasons: tuple[ReintegrationReason, ...]
    retained_observations: tuple[Event, ...]


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
    if plant.lifecycle == "reintegrated" and payload.lifecycle.value != "reintegrated":
        raise PlantDomainConflictError(
            "reintegrated_plant_lifecycle_immutable",
            "A reintegrated Plant cannot be reactivated or assigned another lifecycle",
        )
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
) -> tuple[Plant, PlantGroup, Event]:
    plant_group = database.scalar(
        select(PlantGroup).where(PlantGroup.id == plant_group_id).with_for_update()
    )
    if plant_group is None:
        raise PlantReferenceNotFoundError("plant_group_not_found", "PlantGroup not found")
    if plant_group.lifecycle != "active":
        raise PlantDomainConflictError(
            "plant_group_not_active", "Only an active PlantGroup can have a Plant extracted"
        )
    before_lifecycle = plant_group.lifecycle
    before_quantity = group_quantity(plant_group)
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
    event = Event(
        plant_group_id=plant_group.id,
        kind=EventKind.EXTRACTION.value,
        resulting_plant_id=plant.id,
        occurred_on_precision=(
            payload.collection_entry_date.precision.value
            if payload.collection_entry_date is not None
            else None
        ),
        occurred_on_year=(
            payload.collection_entry_date.year
            if payload.collection_entry_date is not None
            else None
        ),
        occurred_on_month=(
            payload.collection_entry_date.month
            if payload.collection_entry_date is not None
            else None
        ),
        occurred_on_day=(
            payload.collection_entry_date.day if payload.collection_entry_date is not None else None
        ),
    )
    database.add(event)
    database.flush()
    add_receipt(
        database,
        kind=OperationKind.PLANT_GROUP_EXTRACTION,
        plant_id=plant.id,
        plant_group_id=plant_group.id,
        event_id=event.id,
        before_lifecycle=before_lifecycle,
        after_lifecycle=plant_group.lifecycle,
        before_quantity=before_quantity,
        after_quantity=group_quantity(plant_group),
    )
    return plant, plant_group, event


_RETAINABLE_OBSERVATION_KINDS = {
    EventKind.OBSERVATION.value,
    EventKind.FLOWERING.value,
    EventKind.FRUITING.value,
}


def _reason(code: str, message: str) -> ReintegrationReason:
    return ReintegrationReason(code=code, message=message)


def _quantity_matches_receipt(plant_group: PlantGroup, receipt: OperationReceipt) -> bool:
    current = group_quantity(plant_group)
    return (
        current.kind == receipt.after_quantity_kind
        and current.value == receipt.after_quantity_value
        and current.unit == receipt.after_quantity_unit
        and current.is_approximate == receipt.after_quantity_is_approximate
    )


def evaluate_reintegration(
    database: Session, plant_id: UUID, *, lock: bool = False
) -> ReintegrationEvaluation:
    receipt_statement = select(OperationReceipt).where(
        OperationReceipt.kind == OperationKind.PLANT_GROUP_EXTRACTION.value,
        OperationReceipt.plant_id == plant_id,
    )
    if lock:
        receipt_statement = receipt_statement.with_for_update()
    receipt = database.scalar(receipt_statement)
    group_statement = (
        select(PlantGroup).where(PlantGroup.id == receipt.plant_group_id)
        if receipt is not None
        else None
    )
    if lock and group_statement is not None:
        group_statement = group_statement.with_for_update()
    plant_group = database.scalar(group_statement) if group_statement is not None else None
    plant_statement = select(Plant).where(Plant.id == plant_id)
    if lock:
        plant_statement = plant_statement.with_for_update()
    plant = database.scalar(plant_statement)
    if plant is None:
        raise PlantReferenceNotFoundError("plant_not_found", "Plant not found")
    if receipt is None:
        return ReintegrationEvaluation(
            status=ReintegrationEligibilityStatus.BLOCKED,
            receipt=None,
            plant=plant,
            plant_group=None,
            reasons=(
                _reason(
                    "extraction_receipt_not_found",
                    "This Plant has no authoritative extraction receipt and cannot be "
                    "reintegrated automatically.",
                ),
            ),
            retained_observations=(),
        )

    if plant_group is None:
        raise PlantReferenceNotFoundError("plant_group_not_found", "Original PlantGroup not found")

    reasons: list[ReintegrationReason] = []
    if receipt.status == OperationStatus.REVERSED.value:
        reasons.append(
            _reason("receipt_already_reversed", "This extraction has already been reintegrated.")
        )

    original_event = database.get(Event, receipt.event_id)
    if (
        original_event is None
        or original_event.kind != EventKind.EXTRACTION.value
        or original_event.plant_group_id != plant_group.id
        or original_event.resulting_plant_id != plant.id
        or plant.originating_plant_group_id != plant_group.id
    ):
        reasons.append(
            _reason(
                "plant_state_changed",
                "The Plant no longer matches the recorded extraction relationship.",
            )
        )
    if plant.lifecycle != "active":
        reasons.append(
            _reason(
                "transfer_exists" if plant.lifecycle == "transferred" else "plant_state_changed",
                "The Plant lifecycle changed after extraction; resolve that state before "
                "reintegration.",
            )
        )
    if plant.updated_at > receipt.created_at:
        reasons.append(
            _reason(
                "plant_state_changed",
                "The Plant was corrected after extraction; automatic reintegration would "
                "overwrite later facts.",
            )
        )

    later_plant_receipts = list(
        database.scalars(
            select(OperationReceipt).where(
                OperationReceipt.plant_id == plant.id,
                OperationReceipt.id != receipt.id,
                OperationReceipt.status == OperationStatus.APPLIED.value,
            )
        )
    )
    if any(item.kind == OperationKind.PLANT_TRANSFER.value for item in later_plant_receipts):
        reasons.append(
            _reason("transfer_exists", "Undo the later Plant transfer before reintegration.")
        )
    elif later_plant_receipts:
        reasons.append(
            _reason(
                "downstream_dependency",
                "Another authoritative operation depends on this Plant.",
            )
        )

    if database.scalar(
        select(func.count()).select_from(SeedLot).where(SeedLot.producer_plant_id == plant.id)
    ):
        reasons.append(
            _reason(
                "produced_seed_lot_exists",
                "This Plant produced one or more SeedLots, so its extraction cannot be "
                "reintegrated.",
            )
        )

    later_group_receipts = list(
        database.scalars(
            select(OperationReceipt).where(
                OperationReceipt.plant_group_id == plant_group.id,
                OperationReceipt.id != receipt.id,
                OperationReceipt.created_at > receipt.created_at,
                OperationReceipt.status == OperationStatus.APPLIED.value,
            )
        )
    )
    if any(
        item.kind == OperationKind.PLANT_GROUP_EXTRACTION.value for item in later_group_receipts
    ):
        reasons.append(
            _reason(
                "later_extraction_exists",
                "Reintegrate the later extracted Plant first so this snapshot can be "
                "restored safely.",
            )
        )
    if any(item.kind == OperationKind.PLANT_GROUP_TRANSFER.value for item in later_group_receipts):
        reasons.append(
            _reason("source_group_transferred", "Undo the later PlantGroup transfer first.")
        )
    if plant_group.lifecycle != receipt.after_lifecycle or not _quantity_matches_receipt(
        plant_group, receipt
    ):
        reasons.append(
            _reason(
                "source_group_changed",
                "The original PlantGroup no longer matches the extraction snapshot.",
            )
        )

    reversed_later_cutoff = database.scalar(
        select(func.max(Event.created_at))
        .join(OperationReceipt, Event.reversed_operation_receipt_id == OperationReceipt.id)
        .where(
            OperationReceipt.plant_group_id == plant_group.id,
            OperationReceipt.created_at > receipt.created_at,
            OperationReceipt.status == OperationStatus.REVERSED.value,
        )
    )
    allowed_group_update = reversed_later_cutoff or receipt.created_at
    if plant_group.updated_at > allowed_group_update:
        reasons.append(
            _reason(
                "source_group_changed",
                "The original PlantGroup was corrected after extraction.",
            )
        )

    later_plant_events = list(
        database.scalars(
            select(Event).where(Event.plant_id == plant.id, Event.created_at > receipt.created_at)
        )
    )
    observations = tuple(
        event for event in later_plant_events if event.kind in _RETAINABLE_OBSERVATION_KINDS
    )
    if any(event.kind not in _RETAINABLE_OBSERVATION_KINDS for event in later_plant_events):
        reasons.append(
            _reason(
                "downstream_dependency",
                "Later Plant history includes work that is not a retainable observation.",
            )
        )

    unique_reasons = tuple({item.code: item for item in reasons}.values())
    if unique_reasons:
        status = ReintegrationEligibilityStatus.BLOCKED
    elif observations:
        status = ReintegrationEligibilityStatus.CONFIRMATION_REQUIRED
    else:
        status = ReintegrationEligibilityStatus.SAFE
    return ReintegrationEvaluation(
        status=status,
        receipt=receipt,
        plant=plant,
        plant_group=plant_group,
        reasons=unique_reasons,
        retained_observations=observations,
    )


def reintegrate_plant(
    database: Session, plant_id: UUID, *, confirm_retained_observations: bool
) -> tuple[Plant, PlantGroup, Event, OperationReceipt]:
    evaluation = evaluate_reintegration(database, plant_id, lock=True)
    if evaluation.status == ReintegrationEligibilityStatus.BLOCKED:
        reason = evaluation.reasons[0]
        raise PlantDomainConflictError(reason.code, reason.message)
    if (
        evaluation.status == ReintegrationEligibilityStatus.CONFIRMATION_REQUIRED
        and not confirm_retained_observations
    ):
        raise PlantDomainConflictError(
            "reintegration_confirmation_required",
            "Confirm that the Plant and its observations will remain as historical records.",
        )
    receipt = evaluation.receipt
    plant_group = evaluation.plant_group
    if receipt is None or plant_group is None:
        raise RuntimeError("Eligible reintegration is missing its authoritative receipt or group")

    plant_group.lifecycle = receipt.before_lifecycle
    plant_group.quantity_value = (
        int(receipt.before_quantity_value)
        if receipt.before_quantity_kind == "count" and receipt.before_quantity_value is not None
        else None
    )
    plant_group.quantity_is_approximate = receipt.before_quantity_is_approximate
    plant_group.updated_at = datetime.now(UTC)
    evaluation.plant.lifecycle = "reintegrated"
    evaluation.plant.updated_at = datetime.now(UTC)
    event = Event(
        plant_group_id=plant_group.id,
        kind=EventKind.REINTEGRATION.value,
        resulting_plant_id=evaluation.plant.id,
        reversed_operation_receipt_id=receipt.id,
    )
    database.add(event)
    receipt.status = OperationStatus.REVERSED.value
    database.flush()
    return evaluation.plant, plant_group, event, receipt


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
