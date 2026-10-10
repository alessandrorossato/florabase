from collections.abc import Callable
from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock
from uuid import uuid7

import pytest
from fastapi import HTTPException, Response
from pydantic import ValidationError

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.events.service import EventDomainConflictError
from florabase.locations.model import Location
from florabase.plants.model import Plant
from florabase.schedule import api, service
from florabase.schedule.model import TARGETS, ScheduledActivity
from florabase.schedule.schemas import (
    ScheduleComplete,
    ScheduleEvent,
    SchedulePage,
    ScheduleTarget,
    ScheduleTargetPage,
    ScheduleTargetResponse,
    ScheduleUpdate,
    ScheduleVersion,
    ScheduleWrite,
)
from florabase.schedule.service import ScheduleError, _planned
from florabase.seed_lots.model import SeedLot


def activity(**changes: object) -> ScheduledActivity:
    item = ScheduledActivity()
    item.id = uuid7()
    item.activity_kind = "inspect"
    item.title = "Inspect"
    item.due_on = date(2026, 10, 10)
    item.notes = None
    item.status = "planned"
    item.version = 1
    item.linked_event_id = None
    item.created_at = datetime.now(UTC)
    item.updated_at = datetime.now(UTC)
    item.completed_at = None
    item.cancelled_at = None
    for kind in TARGETS:
        setattr(item, f"{kind}_id", None)
    for name, value in changes.items():
        setattr(item, name, value)
    return item


def test_concrete_day_and_normalized_intention() -> None:
    activity = ScheduleWrite(
        activity_kind="repot",
        title="  Repot   basil ",
        due_on="2026-10-10",
        notes=" \r\n plan \r\n",
    )
    assert activity.title == "Repot basil"
    assert activity.due_on == date(2026, 10, 10)
    assert activity.notes == "plan"
    assert activity.target is None


def test_invalid_intentions() -> None:
    invalid_changes: tuple[dict[str, object], ...] = (
        {"due_on": "2026-02-30"},
        {"due_on": "2026-10-10T00:00:00Z"},
        {"due_on": 0},
        {"due_on": "0"},
        {"due_on": False},
        {"due_on": {"year": 2026}},
        {"activity_kind": "recurring"},
        {"title": "   "},
        {"title": "a\x00b"},
        {"notes": "a\x00b"},
        {"status": "overdue"},
        {"priority": 1},
        {"target": {"kind": "harvest", "id": str(uuid7())}},
    )
    for changes in invalid_changes:
        payload: dict[str, object] = {
            "activity_kind": "inspect",
            "title": "Inspect",
            "due_on": "2026-10-10",
        }
        for key, value in changes.items():
            payload[key] = value
        with pytest.raises(ValidationError):
            ScheduleWrite.model_validate(payload)


def test_stale_and_terminal_transitions() -> None:
    for status, version in (("planned", 2), ("completed", 1), ("cancelled", 1)):
        with pytest.raises(ScheduleError, match="schedule_stale"):
            _planned(ScheduledActivity(status=status, version=version), 1)


def test_completion_requires_explicit_event_with_actual_day() -> None:
    assert ScheduleComplete(expected_version=1).event is None
    with pytest.raises(ValidationError):
        ScheduleComplete.model_validate({"expected_version": 1, "event": {"kind": "repotting"}})
    with pytest.raises(ValidationError):
        ScheduleEvent.model_validate({"kind": "movement", "occurred_on": "2026-10-09"})
    with pytest.raises(ValidationError):
        ScheduleUpdate.model_validate(
            {
                "activity_kind": "inspect",
                "title": "Inspect",
                "due_on": "2026-10-10",
                "expected_version": 0,
            }
        )


def test_event_requires_calendar_day_without_timestamp_coercion() -> None:
    for value in ("2026-10-10T00:00:00Z", 0, "0"):
        with pytest.raises(ValidationError):
            ScheduleEvent.model_validate({"kind": "repotting", "occurred_on": value})


def test_target_reference_lifecycle_labels_and_missing_reference() -> None:
    identifier = uuid7()
    item = activity(plant_id=identifier)
    assert service._target_ref(item) == ScheduleTarget(kind="plant", id=identifier)
    assert service._lifecycle(Location(retired_at=None)) == "active"
    assert service._lifecycle(Location(retired_at=datetime.now(UTC))) == "retired"
    assert service._lifecycle(Plant(lifecycle="transferred")) == "transferred"

    now = datetime.now(UTC)
    identity = BotanicalIdentity(
        id=uuid7(), scientific_name="Ocimum basilicum", created_at=now, updated_at=now
    )
    assert service._target_response("botanical_identity", identity).label == "Ocimum basilicum"
    assert service._target_response("location", Location(id=uuid7(), name="Bench")).label == "Bench"
    seed = SeedLot(id=uuid7(), label="Basil packet")
    assert service._target_response("seed_lot", seed).label == "Basil packet"

    database = MagicMock()
    database.scalar.return_value = None
    with pytest.raises(ScheduleError, match="schedule_target_missing"):
        service.require_target(database, ScheduleTarget(kind="plant", id=identifier), lock=True)
    database.scalar.return_value = seed
    assert service.require_target(database, ScheduleTarget(kind="seed_lot", id=identifier)) is seed


def test_schedule_response_resolves_exact_target_and_derives_overdue() -> None:
    today = date(2026, 10, 10)
    plant = Plant(id=uuid7(), label="Basil", lifecycle="active")
    item = activity(plant_id=plant.id, due_on=date(2026, 10, 9))
    database = MagicMock()
    database.scalars.return_value = [plant]
    response = service.responses(database, [item], today)[0]
    assert response.target is not None
    assert response.target.label == "Basil"
    assert response.target.kind == "plant"
    assert response.overdue is True
    item.status = "completed"
    assert service.responses(database, [item], today)[0].overdue is False
    assert service.responses(database, [], today) == []


def test_create_update_cancel_and_retained_inactive_target(monkeypatch: pytest.MonkeyPatch) -> None:
    database = MagicMock()
    payload = ScheduleWrite(
        activity_kind="inspect", title=" Inspect ", due_on="2026-10-10", notes=" plan "
    )
    created = service.create(database, payload)
    assert created.title == "Inspect"
    assert created.notes == "plan"
    database.add.assert_called_once_with(created)
    database.flush.assert_called_once()

    existing = activity(plant_id=uuid7())
    inactive = Plant(id=existing.plant_id, label="Old plant", lifecycle="transferred")
    monkeypatch.setattr(service, "require_activity", lambda *_args, **_kwargs: existing)
    monkeypatch.setattr(service, "require_target", lambda *_args, **_kwargs: inactive)
    update_payload = ScheduleUpdate(
        activity_kind="inspect",
        title="Reschedule retained target",
        due_on="2026-10-20",
        target=ScheduleTarget(kind="plant", id=existing.plant_id),
        expected_version=1,
    )
    updated = service.update(database, existing.id, update_payload)
    assert updated.version == 2
    assert updated.title == "Reschedule retained target"
    assert updated.updated_at.tzinfo is UTC

    cancelled = service.cancel(database, existing.id, 2)
    assert cancelled.status == "cancelled"
    assert cancelled.version == 3
    assert service.cancel(database, existing.id, 2) is cancelled
    with pytest.raises(ScheduleError, match="schedule_stale"):
        service.cancel(database, existing.id, 1)


def test_inactive_new_assignment_and_event_compatibility_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = MagicMock()
    inactive = Plant(id=uuid7(), lifecycle="dead")
    monkeypatch.setattr(service, "require_target", lambda *_args, **_kwargs: inactive)
    payload = ScheduleWrite(
        activity_kind="inspect",
        title="Inspect",
        due_on="2026-10-10",
        target=ScheduleTarget(kind="plant", id=inactive.id),
    )
    with pytest.raises(ScheduleError, match="schedule_target_inactive"):
        service.create(database, payload)

    item = activity()
    monkeypatch.setattr(service, "require_activity", lambda *_args, **_kwargs: item)
    with pytest.raises(ScheduleError, match="schedule_event_incompatible"):
        service.complete(
            database,
            item.id,
            ScheduleComplete(
                expected_version=1,
                event=ScheduleEvent(kind="observation", occurred_on="2026-10-10"),
            ),
        )
    item.plant_id = inactive.id
    with pytest.raises(ScheduleError, match="schedule_target_inactive"):
        service.complete(
            database,
            item.id,
            ScheduleComplete(
                expected_version=1,
                event=ScheduleEvent(kind="observation", occurred_on="2026-10-10"),
            ),
        )


def test_completion_event_success_retry_and_event_service_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = MagicMock()
    target = Plant(id=uuid7(), lifecycle="active")
    item = activity(activity_kind="repot", plant_id=target.id)
    monkeypatch.setattr(service, "require_activity", lambda *_args, **_kwargs: item)
    monkeypatch.setattr(service, "require_target", lambda *_args, **_kwargs: target)
    event = SimpleNamespace(id=uuid7())
    monkeypatch.setattr(service, "create_event", lambda *_args, **_kwargs: event)
    payload = ScheduleComplete(
        expected_version=1,
        event=ScheduleEvent(kind="repotting", occurred_on="2026-10-09", notes="Actual"),
    )
    completed = service.complete(database, item.id, payload)
    assert completed.status == "completed"
    assert completed.linked_event_id == event.id
    assert completed.version == 2
    assert completed.completed_at is not None
    assert service.complete(database, item.id, payload) is completed
    with pytest.raises(ScheduleError, match="schedule_stale"):
        service.complete(database, item.id, ScheduleComplete(expected_version=1))

    other = activity(activity_kind="repot", plant_id=target.id)
    monkeypatch.setattr(service, "require_activity", lambda *_args, **_kwargs: other)
    monkeypatch.setattr(
        service,
        "create_event",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            EventDomainConflictError("event_conflict", "conflict")
        ),
    )
    with pytest.raises(ScheduleError, match="event_conflict"):
        service.complete(database, other.id, payload)
    assert other.status == "planned"
    assert other.linked_event_id is None


def test_list_target_choices_and_retention_queries() -> None:
    database = MagicMock()
    database.scalar.side_effect = [2, 1, True]
    database.scalars.side_effect = [[], [Location(id=uuid7(), name="Bench")]]
    database.execute.return_value.one.return_value = (4, 2)
    page = service.list_activities(
        database, today=date(2026, 10, 10), window="today", q="a%_", limit=5
    )
    assert page.total == 2
    assert page.overdue_count == 4
    assert page.today_count == 2
    targets = service.target_choices(database, "location", "Bench", 0, 20)
    assert targets.total == 1
    assert targets.items[0].label == "Bench"
    assert service.retained_reference(database, "plant", uuid7()) is True
    with pytest.raises(ScheduleError, match="schedule_target_kind_required"):
        service.list_activities(database, today=date(2026, 10, 10), target_id=uuid7())


def test_schedule_reads_missing_items_and_remaining_list_windows() -> None:
    database = MagicMock()
    item = activity()
    database.scalar.return_value = item
    assert service.require_activity(database, item.id) is item
    assert service.read(database, item.id, date(2026, 10, 10)).id == item.id
    database.scalar.return_value = None
    with pytest.raises(ScheduleError, match="schedule_not_found"):
        service.require_activity(database, item.id, lock=True)

    for window in ("overdue", "next_seven_days", "later"):
        database.reset_mock()
        database.scalar.return_value = 0
        database.scalars.return_value = []
        database.execute.return_value.one.return_value = (0, 0)
        page = service.list_activities(
            database,
            today=date(2026, 10, 10),
            status="planned",
            window=window,
            activity_kind="inspect",
            target_kind="plant",
            target_id=uuid7(),
        )
        assert page.total == 0
        assert page.items == []


def test_complete_without_event_marks_planning_only(monkeypatch: pytest.MonkeyPatch) -> None:
    database = MagicMock()
    item = activity()
    monkeypatch.setattr(service, "require_activity", lambda *_args, **_kwargs: item)
    completed = service.complete(database, item.id, ScheduleComplete(expected_version=1))
    assert completed.status == "completed"
    assert completed.linked_event_id is None
    assert completed.completion_fingerprint
    assert completed.version == 2


def test_api_adapters_cover_defaults_success_owner_and_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = cast(Any, SimpleNamespace(owner=True))
    database = MagicMock()
    item = activity()
    response = Response()
    monkeypatch.setattr(service, "create", lambda *_args: item)
    monkeypatch.setattr(service, "read", lambda *_args: item)
    assert (
        api.create(
            ScheduleWrite(activity_kind="inspect", title="Inspect", due_on="2026-10-10"),
            response,
            actor,
            database,
            None,
        ).id
        == item.id
    )
    assert response.headers["location"].endswith(str(item.id))

    page = SchedulePage(
        items=[],
        total=0,
        offset=0,
        limit=50,
        today=date(2026, 10, 10),
        overdue_count=0,
        today_count=0,
    )
    monkeypatch.setattr(service, "list_activities", lambda *_args, **_kwargs: page)
    assert api.list_all(actor, database, None).items == []
    target_page = ScheduleTargetPage(items=[], total=0)
    monkeypatch.setattr(service, "target_choices", lambda *_args: target_page)
    assert api.targets("location", actor, database, "", 0, 50).items == []
    monkeypatch.setattr(service, "require_target", lambda *_args: Location(name="Bench"))
    target = ScheduleTargetResponse(kind="location", id=uuid7(), label="Bench", lifecycle="active")
    monkeypatch.setattr(service, "_target_response", lambda *_args: target)
    assert api.target("location", uuid7(), actor, database).id == target.id

    error = ScheduleError("schedule_not_found", "missing", 404)
    monkeypatch.setattr(service, "read", lambda *_args: (_ for _ in ()).throw(error))
    with pytest.raises(HTTPException) as caught:
        api.read(uuid7(), actor, database, None)
    assert caught.value.status_code == 404
    assert api._today(None) == datetime.now(UTC).date()


def test_remaining_api_transition_adapters_translate_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = cast(Any, SimpleNamespace(owner=True))
    database = MagicMock()
    item = activity()
    monkeypatch.setattr(service, "read", lambda *_args: item)
    monkeypatch.setattr(service, "update", lambda *_args: item)
    monkeypatch.setattr(service, "cancel", lambda *_args: item)
    monkeypatch.setattr(service, "complete", lambda *_args: item)
    assert api.read(item.id, actor, database, date(2026, 10, 10)).id == item.id
    assert (
        api.update(
            item.id,
            ScheduleUpdate(
                activity_kind="inspect", title="Inspect", due_on="2026-10-10", expected_version=1
            ),
            actor,
            database,
        ).id
        == item.id
    )
    version = ScheduleVersion(expected_version=1)
    assert api.cancel(item.id, version, actor, database).id == item.id
    assert (
        api.complete(item.id, ScheduleComplete(expected_version=1), actor, database).id == item.id
    )

    error = ScheduleError("schedule_stale", "stale")
    transitions: tuple[tuple[str, Callable[[], object]], ...] = (
        (
            "update",
            lambda: api.update(
                item.id,
                ScheduleUpdate(
                    activity_kind="inspect",
                    title="Inspect",
                    due_on="2026-10-10",
                    expected_version=1,
                ),
                actor,
                database,
            ),
        ),
        ("cancel", lambda: api.cancel(item.id, version, actor, database)),
        (
            "complete",
            lambda: api.complete(item.id, ScheduleComplete(expected_version=1), actor, database),
        ),
    )
    for name, invoke in transitions:
        monkeypatch.setattr(
            service, name, lambda *_args, _error=error, **_kwargs: (_ for _ in ()).throw(_error)
        )
        with pytest.raises(HTTPException) as caught:
            invoke()
        assert caught.value.status_code == 409

    monkeypatch.setattr(service, "require_target", lambda *_args: (_ for _ in ()).throw(error))
    with pytest.raises(HTTPException) as target_error:
        api.target("location", uuid7(), actor, database)
    assert target_error.value.status_code == 409

    monkeypatch.setattr(
        service, "list_activities", lambda *_args, **_kwargs: (_ for _ in ()).throw(error)
    )
    with pytest.raises(HTTPException) as list_error:
        api.list_all(actor, database, None)
    assert list_error.value.status_code == 409

    monkeypatch.setattr(service, "create", lambda *_args: (_ for _ in ()).throw(error))
    with pytest.raises(HTTPException) as create_error:
        api.create(
            ScheduleWrite(activity_kind="inspect", title="Inspect", due_on="2026-10-10"),
            Response(),
            actor,
            database,
        )
    assert create_error.value.status_code == 409
    with pytest.raises(HTTPException) as owner_error:
        api.create(
            ScheduleWrite(activity_kind="inspect", title="Inspect", due_on="2026-10-10"),
            Response(),
            cast(Any, SimpleNamespace(owner=False)),
            database,
        )
    assert owner_error.value.status_code == 403
