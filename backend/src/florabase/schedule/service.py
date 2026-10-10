from dataclasses import dataclass
from datetime import UTC, date, datetime
from hashlib import sha256
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.schemas import BotanicalIdentityResponse
from florabase.events.schemas import EventCreate
from florabase.events.service import (
    EventDomainConflictError,
    EventReferenceNotFoundError,
    create_event,
)
from florabase.locations.model import Location
from florabase.plants.model import Plant, PlantGroup
from florabase.schedule.model import TARGETS, ScheduledActivity
from florabase.schedule.schemas import (
    ActivityKind,
    DateWindow,
    ScheduleComplete,
    SchedulePage,
    ScheduleResponse,
    ScheduleStatus,
    ScheduleTarget,
    ScheduleTargetPage,
    ScheduleTargetResponse,
    ScheduleUpdate,
    ScheduleWrite,
    TargetKind,
)
from florabase.seed_lots.model import SeedLot
from florabase.seed_lots.schemas import PartialDate
from florabase.sowings.model import Sowing

TargetRecord = BotanicalIdentity | SeedLot | Sowing | Plant | PlantGroup | Location

MODELS: dict[
    str,
    type[BotanicalIdentity]
    | type[SeedLot]
    | type[Sowing]
    | type[Plant]
    | type[PlantGroup]
    | type[Location],
] = {
    "botanical_identity": BotanicalIdentity,
    "seed_lot": SeedLot,
    "sowing": Sowing,
    "plant": Plant,
    "plant_group": PlantGroup,
    "location": Location,
}
EVENT_KINDS = {
    "repot": {"repotting"},
    "move": {"movement"},
    "inspect": {"observation"},
    "follow_up": {"observation", "other"},
}


@dataclass
class ScheduleError(Exception):
    code: str
    message: str
    status: int = 409


def _target_ref(activity: ScheduledActivity) -> ScheduleTarget | None:
    for kind in TARGETS:
        identifier = getattr(activity, f"{kind}_id")
        if identifier is not None:
            return ScheduleTarget(kind=cast(TargetKind, kind), id=identifier)
    return None


def _lifecycle(record: TargetRecord) -> str | None:
    if isinstance(record, Location):
        return "retired" if record.retired_at is not None else "active"
    return cast(str | None, getattr(record, "lifecycle", None))


def _target_response(kind: str, record: TargetRecord) -> ScheduleTargetResponse:
    if isinstance(record, BotanicalIdentity):
        label = BotanicalIdentityResponse.from_model(record).display_label
    elif isinstance(record, Location):
        label = record.name
    else:
        label = getattr(record, "label", None) or f"{kind.replace('_', ' ').title()} {record.id}"
    return ScheduleTargetResponse(
        kind=cast(TargetKind, kind), id=record.id, label=label, lifecycle=_lifecycle(record)
    )


def require_target(
    database: Session, target: ScheduleTarget, *, lock: bool = False
) -> TargetRecord:
    model = MODELS[target.kind]
    statement = select(model).where(model.id == target.id).execution_options(populate_existing=True)
    if lock:
        statement = statement.with_for_update()
    record = database.scalar(statement)
    if record is None:
        raise ScheduleError(
            "schedule_target_missing", "The selected collection record no longer exists", 404
        )
    return cast(TargetRecord, record)


def responses(
    database: Session, activities: list[ScheduledActivity], today: date
) -> list[ScheduleResponse]:
    # At most six target queries regardless of page size. No inferred related targets.
    targets: dict[tuple[str, UUID], ScheduleTargetResponse] = {}
    for kind, model in MODELS.items():
        identifiers = {getattr(item, f"{kind}_id") for item in activities} - {None}
        if identifiers:
            for record in database.scalars(select(model).where(model.id.in_(identifiers))):
                target = cast(TargetRecord, record)
                targets[kind, target.id] = _target_response(kind, target)
    result = []
    for activity in activities:
        ref = _target_ref(activity)
        result.append(
            ScheduleResponse(
                id=activity.id,
                activity_kind=cast(ActivityKind, activity.activity_kind),
                title=activity.title,
                due_on=activity.due_on,
                notes=activity.notes,
                target=targets[(ref.kind, ref.id)] if ref else None,
                status=cast(ScheduleStatus, activity.status),
                version=activity.version,
                overdue=activity.status == "planned" and activity.due_on < today,
                linked_event_id=activity.linked_event_id,
                created_at=activity.created_at,
                updated_at=activity.updated_at,
                completed_at=activity.completed_at,
                cancelled_at=activity.cancelled_at,
            )
        )
    return result


def require_activity(
    database: Session, identifier: UUID, *, lock: bool = False
) -> ScheduledActivity:
    statement = (
        select(ScheduledActivity)
        .where(ScheduledActivity.id == identifier)
        .execution_options(populate_existing=True)
    )
    if lock:
        statement = statement.with_for_update()
    activity = database.scalar(statement)
    if activity is None:
        raise ScheduleError("schedule_not_found", "Scheduled activity not found", 404)
    return activity


def read(database: Session, identifier: UUID, today: date) -> ScheduleResponse:
    return responses(database, [require_activity(database, identifier)], today)[0]


def _assign(database: Session, activity: ScheduledActivity, payload: ScheduleWrite) -> None:
    if payload.target:
        record = require_target(database, payload.target, lock=True)
        # Retained historical targets remain understandable and may be rescheduled or closed.
        if payload.target != _target_ref(activity) and _lifecycle(record) not in {None, "active"}:
            raise ScheduleError(
                "schedule_target_inactive",
                "Choose a current collection record for new planned work",
            )
    for kind in TARGETS:
        setattr(
            activity,
            f"{kind}_id",
            payload.target.id if payload.target and payload.target.kind == kind else None,
        )
    activity.activity_kind = payload.activity_kind
    activity.title = payload.title
    activity.due_on = payload.due_on
    activity.notes = payload.notes


def create(database: Session, payload: ScheduleWrite) -> ScheduledActivity:
    activity = ScheduledActivity()
    _assign(database, activity, payload)
    database.add(activity)
    database.flush()
    return activity


def _planned(activity: ScheduledActivity, version: int) -> None:
    if activity.version != version or activity.status != "planned":
        raise ScheduleError(
            "schedule_stale", "This activity changed. Reload it before trying again"
        )


def _changed(activity: ScheduledActivity) -> None:
    activity.version += 1
    activity.updated_at = datetime.now(UTC)


def update(database: Session, identifier: UUID, payload: ScheduleUpdate) -> ScheduledActivity:
    activity = require_activity(database, identifier, lock=True)
    _planned(activity, payload.expected_version)
    _assign(database, activity, payload)
    _changed(activity)
    database.flush()
    return activity


def cancel(database: Session, identifier: UUID, version: int) -> ScheduledActivity:
    activity = require_activity(database, identifier, lock=True)
    if activity.status == "cancelled" and activity.version == version + 1:
        return activity
    _planned(activity, version)
    activity.status = "cancelled"
    activity.cancelled_at = datetime.now(UTC)
    _changed(activity)
    database.flush()
    return activity


def complete(database: Session, identifier: UUID, payload: ScheduleComplete) -> ScheduledActivity:
    activity = require_activity(database, identifier, lock=True)
    fingerprint = sha256(payload.model_dump_json().encode()).hexdigest()
    if activity.status == "completed" and activity.completion_fingerprint == fingerprint:
        return activity
    _planned(activity, payload.expected_version)
    if payload.event:
        ref = _target_ref(activity)
        if (
            ref is None
            or ref.kind not in {"plant", "plant_group"}
            or payload.event.kind not in EVENT_KINDS.get(activity.activity_kind, set())
        ):
            raise ScheduleError(
                "schedule_event_incompatible",
                (
                    "This activity cannot record that Event. Complete without an Event or use "
                    "the existing Journal workflow"
                ),
            )
        record = require_target(database, ref, lock=True)
        if _lifecycle(record) != "active":
            raise ScheduleError(
                "schedule_target_inactive",
                "Recording this activity requires a current Plant or Plant group",
            )
        actual = payload.event.occurred_on
        event_payload = EventCreate(
            kind=payload.event.kind,
            occurred_on=PartialDate(
                precision="day", year=actual.year, month=actual.month, day=actual.day
            ),
            destination_location_id=payload.event.destination_location_id,
            notes=payload.event.notes,
        )
        try:
            event = create_event(database, ref.kind, ref.id, event_payload)
        except (EventDomainConflictError, EventReferenceNotFoundError) as error:
            raise ScheduleError(error.code, error.message) from error
        activity.linked_event_id = event.id
    activity.status = "completed"
    activity.completed_at = datetime.now(UTC)
    activity.completion_fingerprint = fingerprint
    _changed(activity)
    database.flush()
    return activity


def list_activities(
    database: Session,
    *,
    today: date,
    status: ScheduleStatus = "planned",
    window: DateWindow = "all",
    activity_kind: ActivityKind | None = None,
    target_kind: TargetKind | None = None,
    target_id: UUID | None = None,
    q: str = "",
    offset: int = 0,
    limit: int = 50,
) -> SchedulePage:
    model = ScheduledActivity
    criteria: list[Any] = [model.status == status]
    if activity_kind:
        criteria.append(model.activity_kind == activity_kind)
    if target_kind:
        column = getattr(model, f"{target_kind}_id")
        criteria.append(column == target_id if target_id else column.is_not(None))
    elif target_id:
        raise ScheduleError(
            "schedule_target_kind_required", "Target ID requires its record type", 422
        )
    if q.strip():
        criteria.append(
            or_(
                model.title.icontains(q.strip(), autoescape=True),
                model.notes.icontains(q.strip(), autoescape=True),
            )
        )
    if window == "overdue":
        criteria.extend([model.status == "planned", model.due_on < today])
    elif window == "today":
        criteria.append(model.due_on == today)
    elif window == "next_seven_days":
        criteria.extend(
            [
                model.due_on > today,
                model.due_on <= date.fromordinal(min(today.toordinal() + 7, date.max.toordinal())),
            ]
        )
    elif window == "later":
        criteria.append(
            model.due_on > date.fromordinal(min(today.toordinal() + 7, date.max.toordinal()))
        )
    count = database.scalar(select(func.count()).select_from(model).where(*criteria)) or 0
    items = list(
        database.scalars(
            select(model)
            .where(*criteria)
            .order_by(model.due_on, model.id)
            .offset(offset)
            .limit(limit)
        )
    )
    overdue_count, today_count = database.execute(
        select(
            func.count().filter(model.due_on < today), func.count().filter(model.due_on == today)
        ).where(model.status == "planned")
    ).one()
    return SchedulePage(
        items=responses(database, items, today),
        total=count,
        offset=offset,
        limit=limit,
        today=today,
        overdue_count=overdue_count,
        today_count=today_count,
    )


def target_choices(
    database: Session, kind: TargetKind, q: str, offset: int, limit: int
) -> ScheduleTargetPage:
    model = MODELS[kind]
    label = (
        model.scientific_name
        if model is BotanicalIdentity
        else model.name
        if model is Location
        else cast(type[SeedLot] | type[Sowing] | type[Plant] | type[PlantGroup], model).label
    )
    criteria = [label.icontains(q.strip(), autoescape=True)] if q.strip() else []
    count = database.scalar(select(func.count()).select_from(model).where(*criteria)) or 0
    rows = database.scalars(
        select(model)
        .where(*criteria)
        .order_by(func.lower(label).nulls_last(), model.id)
        .offset(offset)
        .limit(limit)
    )
    return ScheduleTargetPage(
        items=[_target_response(kind, cast(TargetRecord, record)) for record in rows], total=count
    )


def retained_reference(database: Session, kind: str, identifier: UUID) -> bool:
    return (
        database.scalar(
            select(ScheduledActivity.id)
            .where(getattr(ScheduledActivity, f"{kind}_id") == identifier)
            .limit(1)
        )
        is not None
    )
