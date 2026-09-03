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
)
from florabase.locations.model import Location
from florabase.locations.service import display_path, list_locations
from florabase.plants.model import Plant, PlantGroup
from florabase.plants.schemas import BotanicalIdentitySummary, LocationSummary
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
    if payload.kind == EventKind.MOVEMENT:
        target.location_id = payload.destination_location_id
    lifecycle = {
        EventKind.DEATH: "dead",
        EventKind.LOSS: "lost",
        EventKind.DISCARDED: "discarded",
    }.get(payload.kind)
    if lifecycle is not None:
        if isinstance(target, PlantGroup) and lifecycle == "lost" and target.quantity_value == 0:
            raise EventDomainConflictError(
                "plant_group_lifecycle_conflict",
                "An exact-zero PlantGroup cannot be marked lost",
            )
        target.lifecycle = lifecycle
    if payload.kind in {EventKind.MOVEMENT, EventKind.DEATH, EventKind.LOSS, EventKind.DISCARDED}:
        target.updated_at = datetime.now(UTC)


def create_event(
    database: Session,
    target_type: TargetType,
    target_id: UUID,
    payload: EventCreate,
) -> Event:
    _require_destination(database, payload.destination_location_id)
    target = _lock_target(database, target_type, target_id)
    event = Event(
        plant_id=target.id if isinstance(target, Plant) else None,
        plant_group_id=target.id if isinstance(target, PlantGroup) else None,
        **_write_values(payload),
    )
    database.add(event)
    _apply_creation_side_effect(target, payload)
    database.flush()
    return event


def update_event(database: Session, event: Event, payload: EventUpdate) -> Event:
    _require_destination(database, payload.destination_location_id)
    for field, value in _write_values(payload).items():
        setattr(event, field, value)
    event.updated_at = datetime.now(UTC)
    database.flush()
    return event


def delete_event(database: Session, event: Event) -> None:
    database.delete(event)
    database.flush()


def _projection_statement() -> Any:
    plant_identity = aliased(BotanicalIdentity)
    plant_group_identity = aliased(BotanicalIdentity)
    return (
        select(Event, Plant, PlantGroup, Location, plant_identity, plant_group_identity)
        .outerjoin(Plant, Plant.id == Event.plant_id)
        .outerjoin(PlantGroup, PlantGroup.id == Event.plant_group_id)
        .outerjoin(Location, Location.id == Event.destination_location_id)
        .outerjoin(plant_identity, plant_identity.id == Plant.botanical_identity_id)
        .outerjoin(
            plant_group_identity,
            plant_group_identity.id == PlantGroup.botanical_identity_id,
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
                created_at=event.created_at,
                updated_at=event.updated_at,
            )
        )
    return responses
