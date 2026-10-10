from datetime import UTC, date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from florabase.auth.dependencies import (
    AuthenticatedActor,
    require_authenticated_actor,
    require_csrf,
    require_owner,
)
from florabase.db.session import get_database_session
from florabase.schedule import service
from florabase.schedule.schemas import (
    ActivityKind,
    CalendarDay,
    DateWindow,
    ScheduleComplete,
    SchedulePage,
    ScheduleResponse,
    ScheduleStatus,
    ScheduleTarget,
    ScheduleTargetPage,
    ScheduleTargetResponse,
    ScheduleUpdate,
    ScheduleVersion,
    ScheduleWrite,
    TargetKind,
)

router = APIRouter(prefix="/schedule", tags=["schedule"])
Database = Annotated[Session, Depends(get_database_session)]
Reader = Annotated[AuthenticatedActor, Depends(require_authenticated_actor)]
Writer = Annotated[AuthenticatedActor, Depends(require_csrf)]
Day = Annotated[
    CalendarDay | None,
    Query(description="Calendar day for overdue. Defaults to UTC; browser supplies its local day."),
]


def _today(day: date | None) -> date:
    return day or datetime.now(UTC).date()


def _error(error: service.ScheduleError) -> HTTPException:
    return HTTPException(
        status_code=error.status, detail={"code": error.code, "message": error.message}
    )


@router.get("", response_model=SchedulePage, operation_id="listScheduledActivities")
def list_all(
    _actor: Reader,
    database: Database,
    today: Day = None,
    status: ScheduleStatus = "planned",
    window: DateWindow = "all",
    activity_kind: ActivityKind | None = None,
    target_kind: TargetKind | None = None,
    target_id: UUID | None = None,
    q: Annotated[str, Query(max_length=200)] = "",
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> SchedulePage:
    try:
        return service.list_activities(
            database,
            today=_today(today),
            status=status,
            window=window,
            activity_kind=activity_kind,
            target_kind=target_kind,
            target_id=target_id,
            q=q,
            offset=offset,
            limit=limit,
        )
    except service.ScheduleError as error:
        raise _error(error) from error


@router.get(
    "/targets/{kind}", response_model=ScheduleTargetPage, operation_id="listScheduleTargets"
)
def targets(
    kind: TargetKind,
    _actor: Reader,
    database: Database,
    q: Annotated[str, Query(max_length=200)] = "",
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ScheduleTargetPage:
    return service.target_choices(database, kind, q, offset, limit)


@router.get(
    "/targets/{kind}/{identifier}",
    response_model=ScheduleTargetResponse,
    operation_id="getScheduleTarget",
)
def target(
    kind: TargetKind, identifier: UUID, _actor: Reader, database: Database
) -> ScheduleTargetResponse:
    try:
        return service._target_response(
            kind, service.require_target(database, ScheduleTarget(kind=kind, id=identifier))
        )
    except service.ScheduleError as error:
        raise _error(error) from error


@router.get("/{identifier}", response_model=ScheduleResponse, operation_id="getScheduledActivity")
def read(
    identifier: UUID, _actor: Reader, database: Database, today: Day = None
) -> ScheduleResponse:
    try:
        return service.read(database, identifier, _today(today))
    except service.ScheduleError as error:
        raise _error(error) from error


@router.post(
    "", response_model=ScheduleResponse, status_code=201, operation_id="createScheduledActivity"
)
def create(
    payload: ScheduleWrite, response: Response, actor: Writer, database: Database, today: Day = None
) -> ScheduleResponse:
    require_owner(actor)
    try:
        activity = service.create(database, payload)
        response.headers["Location"] = f"/api/v1/schedule/{activity.id}"
        return service.read(database, activity.id, _today(today))
    except service.ScheduleError as error:
        raise _error(error) from error


@router.put(
    "/{identifier}", response_model=ScheduleResponse, operation_id="updateScheduledActivity"
)
def update(
    identifier: UUID, payload: ScheduleUpdate, actor: Writer, database: Database, today: Day = None
) -> ScheduleResponse:
    require_owner(actor)
    try:
        activity = service.update(database, identifier, payload)
        return service.read(database, activity.id, _today(today))
    except service.ScheduleError as error:
        raise _error(error) from error


@router.post(
    "/{identifier}/cancel", response_model=ScheduleResponse, operation_id="cancelScheduledActivity"
)
def cancel(
    identifier: UUID, payload: ScheduleVersion, actor: Writer, database: Database, today: Day = None
) -> ScheduleResponse:
    require_owner(actor)
    try:
        activity = service.cancel(database, identifier, payload.expected_version)
        return service.read(database, activity.id, _today(today))
    except service.ScheduleError as error:
        raise _error(error) from error


@router.post(
    "/{identifier}/complete",
    response_model=ScheduleResponse,
    operation_id="completeScheduledActivity",
)
def complete(
    identifier: UUID,
    payload: ScheduleComplete,
    actor: Writer,
    database: Database,
    today: Day = None,
) -> ScheduleResponse:
    require_owner(actor)
    try:
        activity = service.complete(database, identifier, payload)
        return service.read(database, activity.id, _today(today))
    except service.ScheduleError as error:
        raise _error(error) from error
