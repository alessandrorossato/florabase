from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, cast
from uuid import UUID

from sqlalchemy import case, desc, select
from sqlalchemy.orm import Session, aliased

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.schemas import BotanicalIdentityResponse
from florabase.events.model import Event, EventKind
from florabase.events.schemas import (
    EventCreate,
    EventResponse,
    EventUpdate,
    PlantEventTarget,
    PlantGroupEventTarget,
    ResultingPlantSummary,
    TransferCreate,
)
from florabase.locations.model import Location
from florabase.locations.service import display_path, list_locations
from florabase.plants.model import Plant, PlantGroup
from florabase.plants.schemas import BotanicalIdentitySummary, LocationSummary
from florabase.reversals.model import OperationKind, OperationReceipt
from florabase.reversals.service import add_receipt, group_quantity
from florabase.seed_lots.schemas import PartialDate

TargetType = Literal["plant", "plant_group"]
Target = Plant | PlantGroup


@dataclass(frozen=True)
class EventReferenceNotFoundError(Exception):
    code: str
    message: str


@dataclass(frozen=True)
class EventDomainConflictError(Exception):
    code: str
    message: str


@dataclass(frozen=True)
class EventProjection:
    event: Event
    plant: Plant | None
    plant_group: PlantGroup | None
    destination_location: Location | None
    plant_identity: BotanicalIdentity | None
    plant_group_identity: BotanicalIdentity | None
    resulting_plant: Plant | None
    resulting_plant_identity: BotanicalIdentity | None
    original_operation_receipt: OperationReceipt | None = None
    reversed_operation_receipt: OperationReceipt | None = None


def _partial_date_values(value: PartialDate | None) -> dict[str, object]:
    return {
        "occurred_on_precision": value.precision.value if value else None,
        "occurred_on_year": value.year if value else None,
        "occurred_on_month": value.month if value else None,
        "occurred_on_day": value.day if value else None,
    }


def _write_values(payload: EventCreate | EventUpdate) -> dict[str, object]:
    return {
        "kind": payload.kind.value,
        "notes": payload.notes,
        "destination_location_id": payload.destination_location_id,
        "recipient": payload.recipient,
        "resulting_plant_id": payload.resulting_plant_id,
        **_partial_date_values(payload.occurred_on),
    }


def _target_model(target_type: TargetType) -> type[Plant] | type[PlantGroup]:
    return Plant if target_type == "plant" else PlantGroup


def _lock_target(database: Session, target_type: TargetType, target_id: UUID) -> Target:
    target = database.scalar(
        select(_target_model(target_type))
        .where(_target_model(target_type).id == target_id)
        .with_for_update()
    )
    if target is None:
        label = "Plant" if target_type == "plant" else "PlantGroup"
        raise EventReferenceNotFoundError(f"{target_type}_not_found", f"{label} not found")
    return cast(Target, target)


def _require_destination(database: Session, location_id: UUID | None) -> None:
    if location_id is not None and database.get(Location, location_id) is None:
        raise EventReferenceNotFoundError("location_not_found", "Location not found")


def _apply_creation_side_effect(target: Target, payload: EventCreate) -> None:
    if (
        isinstance(target, Plant)
        and target.lifecycle == "reintegrated"
        and payload.kind
        in {
            EventKind.MOVEMENT,
            EventKind.TRANSFER,
            EventKind.DEATH,
            EventKind.LOSS,
            EventKind.DISCARDED,
        }
    ):
        raise EventDomainConflictError(
            "reintegrated_plant_is_historical",
            "A reintegrated Plant is historical and cannot receive a current-state Event",
        )
    if payload.kind == EventKind.TRANSFER and target.lifecycle != "active":
        label = "Plant" if isinstance(target, Plant) else "PlantGroup"
        raise EventDomainConflictError(
            "target_not_active", f"Only an active {label} can be transferred"
        )
    if payload.kind == EventKind.MOVEMENT:
        target.location_id = payload.destination_location_id
    lifecycle = {
        EventKind.DEATH: "dead",
        EventKind.LOSS: "lost",
        EventKind.DISCARDED: "discarded",
        EventKind.TRANSFER: "transferred",
    }.get(payload.kind)
    if lifecycle is not None:
        if isinstance(target, PlantGroup) and lifecycle == "lost" and target.quantity_value == 0:
            raise EventDomainConflictError(
                "plant_group_lifecycle_conflict",
                "An exact-zero PlantGroup cannot be marked lost",
            )
        target.lifecycle = lifecycle
    if payload.kind in {
        EventKind.MOVEMENT,
        EventKind.DEATH,
        EventKind.LOSS,
        EventKind.DISCARDED,
        EventKind.TRANSFER,
    }:
        target.updated_at = datetime.now(UTC)


def create_event(
    database: Session,
    target_type: TargetType,
    target_id: UUID,
    payload: EventCreate,
) -> Event:
    if payload.kind in {EventKind.EXTRACTION, EventKind.REINTEGRATION}:
        raise EventDomainConflictError(
            "extraction_operation_required",
            "Extraction and reintegration Events are created only by their "
            "authoritative operations",
        )
    _require_destination(database, payload.destination_location_id)
    target = _lock_target(database, target_type, target_id)
    event = Event(
        plant_id=target.id if isinstance(target, Plant) else None,
        plant_group_id=target.id if isinstance(target, PlantGroup) else None,
        **_write_values(payload),
    )
    _apply_creation_side_effect(target, payload)
    database.add(event)
    database.flush()
    return event


def transfer_target(
    database: Session,
    target_type: TargetType,
    target_id: UUID,
    payload: TransferCreate,
) -> tuple[Event, Target]:
    target = _lock_target(database, target_type, target_id)
    before_lifecycle = target.lifecycle
    before_quantity = group_quantity(target) if isinstance(target, PlantGroup) else None
    event_payload = EventCreate(
        kind=EventKind.TRANSFER,
        occurred_on=payload.occurred_on,
        recipient=payload.recipient,
        notes=payload.notes,
    )
    event = Event(
        plant_id=target.id if isinstance(target, Plant) else None,
        plant_group_id=target.id if isinstance(target, PlantGroup) else None,
        **_write_values(event_payload),
    )
    _apply_creation_side_effect(target, event_payload)
    database.add(event)
    database.flush()
    add_receipt(
        database,
        kind=(
            OperationKind.PLANT_GROUP_TRANSFER
            if isinstance(target, PlantGroup)
            else OperationKind.PLANT_TRANSFER
        ),
        plant_id=target.id if isinstance(target, Plant) else None,
        plant_group_id=target.id if isinstance(target, PlantGroup) else None,
        event_id=event.id,
        before_lifecycle=before_lifecycle,
        after_lifecycle=target.lifecycle,
        before_quantity=before_quantity,
        after_quantity=group_quantity(target) if isinstance(target, PlantGroup) else None,
    )
    return event, target


def update_event(database: Session, event: Event, payload: EventUpdate) -> Event:
    operation_kinds = {EventKind.EXTRACTION.value, EventKind.REINTEGRATION.value}
    if event.kind in operation_kinds:
        raise EventDomainConflictError(
            "operation_event_immutable",
            "An authoritative extraction or reintegration Event cannot be edited as ordinary "
            "history",
        )
    if payload.kind.value in operation_kinds and event.kind != payload.kind.value:
        raise EventDomainConflictError(
            "extraction_operation_required",
            "An existing Event cannot be converted into an authoritative operation Event",
        )
    if event.kind in operation_kinds and payload.kind.value != event.kind:
        raise EventDomainConflictError(
            "operation_event_kind_immutable",
            "An authoritative operation Event cannot be converted into another Event kind",
        )
    _require_destination(database, payload.destination_location_id)
    for field, value in _write_values(payload).items():
        setattr(event, field, value)
    event.updated_at = datetime.now(UTC)
    database.flush()
    return event


def delete_event(database: Session, event: Event) -> None:
    owner = database.scalar(
        select(OperationReceipt.id).where(OperationReceipt.event_id == event.id)
    )
    if owner is not None or event.reversed_operation_receipt_id is not None:
        raise EventDomainConflictError(
            "operation_event_requires_undo",
            "An Event owned by an authoritative operation cannot be deleted as an ordinary Event",
        )
    database.delete(event)
    database.flush()


def _projection_statement() -> Any:
    plant_identity = aliased(BotanicalIdentity)
    plant_group_identity = aliased(BotanicalIdentity)
    resulting_plant = aliased(Plant)
    resulting_plant_identity = aliased(BotanicalIdentity)
    original_receipt = aliased(OperationReceipt)
    reversed_receipt = aliased(OperationReceipt)
    return (
        select(
            Event,
            Plant,
            PlantGroup,
            Location,
            plant_identity,
            plant_group_identity,
            resulting_plant,
            resulting_plant_identity,
            original_receipt,
            reversed_receipt,
        )
        .outerjoin(Plant, Plant.id == Event.plant_id)
        .outerjoin(PlantGroup, PlantGroup.id == Event.plant_group_id)
        .outerjoin(Location, Location.id == Event.destination_location_id)
        .outerjoin(plant_identity, plant_identity.id == Plant.botanical_identity_id)
        .outerjoin(
            plant_group_identity,
            plant_group_identity.id == PlantGroup.botanical_identity_id,
        )
        .outerjoin(resulting_plant, resulting_plant.id == Event.resulting_plant_id)
        .outerjoin(
            resulting_plant_identity,
            resulting_plant_identity.id == resulting_plant.botanical_identity_id,
        )
        .outerjoin(original_receipt, original_receipt.event_id == Event.id)
        .outerjoin(
            reversed_receipt,
            reversed_receipt.id == Event.reversed_operation_receipt_id,
        )
    )


def get_event(database: Session, event_id: UUID) -> EventProjection | None:
    row = database.execute(_projection_statement().where(Event.id == event_id)).one_or_none()
    return EventProjection(*row) if row is not None else None


def _timeline_ordering() -> tuple[object, ...]:
    return (
        case((Event.occurred_on_precision.is_not(None), 0), else_=1),
        desc(Event.occurred_on_year).nulls_last(),
        desc(Event.occurred_on_month).nulls_last(),
        desc(Event.occurred_on_day).nulls_last(),
        desc(Event.created_at),
        desc(Event.id),
    )


def list_events(
    database: Session, target_type: TargetType, target_id: UUID
) -> list[EventProjection]:
    model = _target_model(target_type)
    if database.get(model, target_id) is None:
        label = "Plant" if target_type == "plant" else "PlantGroup"
        raise EventReferenceNotFoundError(f"{target_type}_not_found", f"{label} not found")
    target_column = Event.plant_id if target_type == "plant" else Event.plant_group_id
    return [
        EventProjection(*row)
        for row in database.execute(
            _projection_statement()
            .where(target_column == target_id)
            .order_by(*_timeline_ordering())
        )
    ]


def list_all_events(
    database: Session,
    *,
    botanical_identity_id: UUID | None = None,
    limit: int | None = None,
) -> list[EventProjection]:
    statement = _projection_statement()
    if botanical_identity_id is not None:
        statement = statement.where(
            (Plant.botanical_identity_id == botanical_identity_id)
            | (PlantGroup.botanical_identity_id == botanical_identity_id)
        )
    statement = statement.order_by(*_timeline_ordering())
    if limit is not None:
        statement = statement.limit(limit)
    return [EventProjection(*row) for row in database.execute(statement)]


def _partial_date(event: Event) -> PartialDate | None:
    if event.occurred_on_precision is None:
        return None
    return PartialDate(
        precision=event.occurred_on_precision,
        year=event.occurred_on_year,
        month=event.occurred_on_month,
        day=event.occurred_on_day,
    )


def event_responses(database: Session, projections: list[EventProjection]) -> list[EventResponse]:
    locations = list_locations(database)
    responses: list[EventResponse] = []
    for projection in projections:
        event = projection.event
        operation_receipt = (
            projection.original_operation_receipt or projection.reversed_operation_receipt
        )
        target: PlantEventTarget | PlantGroupEventTarget
        if projection.plant is not None:
            if projection.plant_identity is None:
                raise RuntimeError("Plant botanical identity invariant was violated")
            identity = BotanicalIdentityResponse.from_model(projection.plant_identity)
            target = PlantEventTarget(
                id=projection.plant.id,
                label=projection.plant.label,
                lifecycle=projection.plant.lifecycle,
                botanical_identity=BotanicalIdentitySummary(
                    id=identity.id, display_label=identity.display_label
                ),
            )
        elif projection.plant_group is not None:
            if projection.plant_group_identity is None:
                raise RuntimeError("PlantGroup botanical identity invariant was violated")
            identity = BotanicalIdentityResponse.from_model(projection.plant_group_identity)
            target = PlantGroupEventTarget(
                id=projection.plant_group.id,
                label=projection.plant_group.label,
                lifecycle=projection.plant_group.lifecycle,
                botanical_identity=BotanicalIdentitySummary(
                    id=identity.id, display_label=identity.display_label
                ),
            )
        else:
            raise RuntimeError("Event target foreign key invariant was violated")
        destination = projection.destination_location
        responses.append(
            EventResponse(
                id=event.id,
                target=target,
                kind=event.kind,
                occurred_on=_partial_date(event),
                notes=event.notes,
                destination_location_id=event.destination_location_id,
                destination_location=(
                    LocationSummary(
                        id=destination.id, display_path=display_path(destination, locations)
                    )
                    if destination is not None
                    else None
                ),
                recipient=event.recipient,
                resulting_plant_id=event.resulting_plant_id,
                resulting_plant=(
                    ResultingPlantSummary(
                        id=projection.resulting_plant.id,
                        label=projection.resulting_plant.label,
                        botanical_identity=BotanicalIdentitySummary(
                            id=projection.resulting_plant_identity.id,
                            display_label=BotanicalIdentityResponse.from_model(
                                projection.resulting_plant_identity
                            ).display_label,
                        ),
                    )
                    if projection.resulting_plant is not None
                    and projection.resulting_plant_identity is not None
                    else None
                ),
                operation_kind=(operation_receipt.kind if operation_receipt else None),
                operation_status=(operation_receipt.status if operation_receipt else None),
                created_at=event.created_at,
                updated_at=event.updated_at,
            )
        )
    return responses
