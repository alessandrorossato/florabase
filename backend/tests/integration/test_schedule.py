from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from threading import Barrier
from typing import cast
from uuid import uuid7

import pytest
from alembic.config import Config
from sqlalchemy import Connection, Engine, delete, func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.service import (
    BotanicalIdentityReferencedError,
    delete_botanical_identity,
)
from florabase.events.model import Event
from florabase.events.service import EventDomainConflictError, delete_event
from florabase.history.service import list_history
from florabase.locations.model import Location
from florabase.locations.service import LocationIntegrityError, delete_location
from florabase.plants.model import Plant
from florabase.schedule import service
from florabase.schedule.model import ScheduledActivity
from florabase.schedule.schemas import (
    DateWindow,
    ScheduleComplete,
    ScheduleEvent,
    ScheduleStatus,
    ScheduleTarget,
    ScheduleUpdate,
    ScheduleWrite,
)

from .test_supplier_api import ORIGIN, mutate, request
from .test_supplier_api import authenticated_browser as authenticated_browser

pytestmark = pytest.mark.integration
DAY = date(2026, 10, 9)


def test_planning_boundaries_filters_dates_and_retention(database_connection: Connection) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity = BotanicalIdentity(scientific_name="Schedulus honestus")
        location = Location(name="Schedule bench")
        db.add_all([identity, location])
        db.flush()
        plant = Plant(
            direct_origin_kind="unknown",
            botanical_identity_id=identity.id,
            label="Basil",
            lifecycle="active",
        )
        db.add(plant)
        db.flush()
        prior_history = list_history(db).total
        prior_events = db.scalar(select(func.count()).select_from(Event))
        activities = [
            service.create(
                db,
                ScheduleWrite(
                    activity_kind="inspect",
                    title=f"Inspect %_ {delta}",
                    due_on=DAY.fromordinal(DAY.toordinal() + delta),
                    target=ScheduleTarget(kind="plant", id=plant.id),
                ),
            )
            for delta in (-1, 0, 3, 20)
        ]
        for window, index in (("overdue", 0), ("today", 1), ("next_seven_days", 2), ("later", 3)):
            page = service.list_activities(db, today=DAY, window=cast(DateWindow, window), q="%_")
            assert [a.id for a in page.items] == [activities[index].id]
        page = service.list_activities(
            db, today=DAY, target_kind="plant", target_id=plant.id, limit=2
        )
        assert page.total == 4
        assert len(page.items) == 2
        assert page.overdue_count == page.today_count == 1
        assert service.read(db, activities[0].id, DAY).overdue is True
        assert activities[0].status == "planned"
        service.complete(db, activities[0].id, ScheduleComplete(expected_version=1))
        assert service.read(db, activities[0].id, DAY).overdue is False
        assert db.scalar(select(func.count()).select_from(Event)) == prior_events
        completion = list_history(db)
        assert completion.total == prior_history + 1
        assert completion.items[0].source_kind == "scheduled_activity"
        assert completion.items[0].source_id == activities[0].id
        assert completion.items[0].occurred_at == activities[0].completed_at
        assert completion.items[0].related[0].id == plant.id
        service.cancel(db, activities[1].id, 1)
        assert service.cancel(db, activities[1].id, 1).version == 2
        with pytest.raises(service.ScheduleError):
            service.complete(db, activities[1].id, ScheduleComplete(expected_version=1))
        plant.lifecycle = "dead"
        db.flush()
        changed = service.update(
            db,
            activities[2].id,
            ScheduleUpdate(
                activity_kind="inspect",
                title="Retained target",
                due_on=DAY,
                target=ScheduleTarget(kind="plant", id=plant.id),
                expected_version=1,
            ),
        )
        retained = service.read(db, changed.id, DAY).target
        assert retained is not None
        assert retained.lifecycle == "dead"
        with pytest.raises(service.ScheduleError, match="schedule_target_inactive"):
            service.complete(
                db,
                changed.id,
                ScheduleComplete(
                    expected_version=2, event=ScheduleEvent(kind="observation", occurred_on=DAY)
                ),
            )
        assert changed.status == "planned"
        for kind, target in (("location", location), ("botanical_identity", identity)):
            activity = service.create(
                db,
                ScheduleWrite(
                    activity_kind="follow_up",
                    title="Retained",
                    due_on=DAY,
                    target=ScheduleTarget(kind=kind, id=target.id),
                ),
            )
            service.cancel(db, activity.id, 1)
        with pytest.raises(LocationIntegrityError):
            delete_location(db, location.id)
        with pytest.raises(BotanicalIdentityReferencedError):
            delete_botanical_identity(db, identity)
        with pytest.raises(IntegrityError), db.begin_nested():
            db.execute(delete(Plant).where(Plant.id == plant.id))


def test_event_atomicity_actual_date_and_exact_retry(database_connection: Connection) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity = BotanicalIdentity(scientific_name="Schedulus eventus")
        db.add(identity)
        db.flush()
        plant = Plant(
            direct_origin_kind="unknown", botanical_identity_id=identity.id, lifecycle="active"
        )
        db.add(plant)
        db.flush()
        activity = service.create(
            db,
            ScheduleWrite(
                activity_kind="repot",
                title="Repot",
                due_on=date(2026, 10, 20),
                target=ScheduleTarget(kind="plant", id=plant.id),
            ),
        )
        invalid = ScheduleComplete(
            expected_version=1, event=ScheduleEvent(kind="observation", occurred_on=DAY)
        )
        with pytest.raises(service.ScheduleError):
            service.complete(db, activity.id, invalid)
        assert activity.status == "planned"
        assert activity.linked_event_id is None
        payload = ScheduleComplete(
            expected_version=1,
            event=ScheduleEvent(kind="repotting", occurred_on=DAY, notes="Actual occurrence"),
        )
        completed = service.complete(db, activity.id, payload)
        event_id = completed.linked_event_id
        event = db.get(Event, event_id)
        assert event is not None
        assert event.occurred_on_day == 9
        assert event.occurred_on_month == 10
        assert service.complete(db, activity.id, payload).linked_event_id == event_id
        assert (
            db.scalar(select(func.count()).select_from(Event).where(Event.plant_id == plant.id))
            == 1
        )
        with pytest.raises(service.ScheduleError):
            service.complete(db, activity.id, ScheduleComplete(expected_version=1))
        with pytest.raises(EventDomainConflictError, match="event_retained_by_schedule"):
            delete_event(db, event)
        movement = service.create(
            db,
            ScheduleWrite(
                activity_kind="move",
                title="Move",
                due_on=DAY,
                target=ScheduleTarget(kind="plant", id=plant.id),
            ),
        )
        with pytest.raises(service.ScheduleError):
            service.complete(
                db,
                movement.id,
                ScheduleComplete(
                    expected_version=1,
                    event=ScheduleEvent(
                        kind="movement", occurred_on=DAY, destination_location_id=uuid7()
                    ),
                ),
            )
        assert movement.status == "planned"
        assert plant.location_id is None


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("edit", "edit"),
        ("edit", "complete"),
        ("cancel", "complete"),
        ("complete", "complete"),
        ("event", "event"),
    ],
)
def test_real_concurrent_transitions(database_engine: Engine, left: str, right: str) -> None:
    with Session(database_engine) as db:
        identity = BotanicalIdentity(scientific_name=f"Race {uuid7()}")
        db.add(identity)
        db.flush()
        plant = Plant(
            direct_origin_kind="unknown", botanical_identity_id=identity.id, lifecycle="active"
        )
        db.add(plant)
        db.flush()
        activity = service.create(
            db,
            ScheduleWrite(
                activity_kind="repot",
                title="Race",
                due_on=DAY,
                target=ScheduleTarget(kind="plant", id=plant.id),
            ),
        )
        identifier, plant_id, identity_id = activity.id, plant.id, identity.id
        db.commit()
    barrier = Barrier(2)

    def act(action: str) -> str:
        with Session(database_engine) as db:
            barrier.wait(timeout=10)
            try:
                if action == "edit":
                    service.update(
                        db,
                        identifier,
                        ScheduleUpdate(
                            activity_kind="repot",
                            title="Rescheduled",
                            due_on=date(2026, 10, 30),
                            expected_version=1,
                            target=ScheduleTarget(kind="plant", id=plant_id),
                        ),
                    )
                elif action == "cancel":
                    service.cancel(db, identifier, 1)
                else:
                    service.complete(
                        db,
                        identifier,
                        ScheduleComplete(
                            expected_version=1,
                            event=ScheduleEvent(kind="repotting", occurred_on=DAY)
                            if action == "event"
                            else None,
                        ),
                    )
                db.commit()
                return "ok"
            except service.ScheduleError:
                db.rollback()
                return "conflict"

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(act, action) for action in (left, right)]
            results = [future.result(timeout=20) for future in futures]
        expected = 2 if left == right and left in {"complete", "event"} else 1
        assert results.count("ok") == expected
        with Session(database_engine) as db:
            stored = db.get(ScheduledActivity, identifier)
            assert stored is not None
            assert stored.version == 2
            assert db.scalar(
                select(func.count()).select_from(Event).where(Event.plant_id == plant_id)
            ) == (1 if left == "event" else 0)
    finally:
        with database_engine.begin() as connection:
            connection.execute(delete(ScheduledActivity).where(ScheduledActivity.id == identifier))
            connection.execute(delete(Event).where(Event.plant_id == plant_id))
            connection.execute(delete(Plant).where(Plant.id == plant_id))
            connection.execute(delete(BotanicalIdentity).where(BotanicalIdentity.id == identity_id))


def test_api_auth_origin_validation_and_stale_protection(
    authenticated_browser: tuple[str, str],
) -> None:
    payload = {"activity_kind": "inspect", "title": "Inspect", "due_on": "2026-10-09"}
    assert request("GET", "/api/v1/schedule")[0] == 401
    cookie, csrf = authenticated_browser
    for headers in (
        {"cookie": cookie},
        {"cookie": cookie, "origin": ORIGIN},
        {"cookie": cookie, "origin": "https://wrong.example", "x-csrf-token": csrf},
    ):
        assert request("POST", "/api/v1/schedule", body=payload, headers=headers)[0] == 403
    assert (
        mutate(
            authenticated_browser, "POST", "/api/v1/schedule", {**payload, "due_on": "2026-02-30"}
        )[0]
        == 422
    )
    status, headers, item = mutate(authenticated_browser, "POST", "/api/v1/schedule", payload)
    assert status == 201
    assert headers["location"].endswith(item["id"])
    path = f"/api/v1/schedule/{item['id']}"
    assert (
        mutate(
            authenticated_browser,
            "PUT",
            path,
            {**payload, "expected_version": 1, "due_on": "2026-10-30"},
        )[0]
        == 200
    )
    assert (
        mutate(authenticated_browser, "POST", path + "/complete", {"expected_version": 1})[0] == 409
    )
    assert (
        mutate(authenticated_browser, "POST", path + "/complete", {"expected_version": 2})[0] == 200
    )
    assert (
        mutate(authenticated_browser, "POST", path + "/complete", {"expected_version": 2})[0] == 200
    )
    assert (
        mutate(authenticated_browser, "POST", path + "/cancel", {"expected_version": 2})[0] == 409
    )
    assert request("GET", path, headers={"cookie": cookie})[2]["status"] == "completed"


def test_migration_preserves_unrelated_records_and_guards_evidence(database_engine: Engine) -> None:
    config = Config("alembic.ini")
    identity_id = uuid7()
    activity_id = uuid7()
    with database_engine.begin() as c:
        c.execute(
            text(
                "INSERT INTO botanical_identities (id,scientific_name,created_at,updated_at) "
                "VALUES (:id,'Migration sentinel',now(),now())"
            ),
            {"id": identity_id},
        )
        c.execute(
            text(
                "INSERT INTO scheduled_activities "
                "(id,activity_kind,title,due_on,status,version,created_at,updated_at) "
                "VALUES (:id,'inspect','Retained',DATE '2026-10-09','planned',1,now(),now())"
            ),
            {"id": activity_id},
        )
    try:
        with pytest.raises(DBAPIError, match="Retained scheduled activities prevent downgrade"):
            command.downgrade(config, "20261009_0040")
        with database_engine.begin() as c:
            assert (
                c.scalar(
                    text("SELECT count(*) FROM scheduled_activities WHERE id=:id"),
                    {"id": activity_id},
                )
                == 1
            )
            c.execute(delete(ScheduledActivity).where(ScheduledActivity.id == activity_id))
        command.downgrade(config, "20261009_0040")
        command.upgrade(config, "head")
        with database_engine.connect() as c:
            assert (
                c.scalar(
                    text("SELECT count(*) FROM botanical_identities WHERE id=:id"),
                    {"id": identity_id},
                )
                == 1
            )
    finally:
        command.upgrade(config, "head")
        with database_engine.begin() as c:
            c.execute(delete(ScheduledActivity).where(ScheduledActivity.id == activity_id))
            c.execute(delete(BotanicalIdentity).where(BotanicalIdentity.id == identity_id))


@pytest.mark.parametrize("mutation", ["retire", "delete"])
def test_target_mutation_and_deletion_serialize_with_schedule(
    database_engine: Engine, mutation: str
) -> None:
    with Session(database_engine) as db:
        location = Location(name=f"Race bench {uuid7()}")
        db.add(location)
        db.flush()
        activity = service.create(
            db,
            ScheduleWrite(
                activity_kind="inspect",
                title="Inspect bench",
                due_on=DAY,
                target=ScheduleTarget(kind="location", id=location.id),
            ),
        )
        identifier, location_id = activity.id, location.id
        db.commit()
    barrier = Barrier(2)

    def modify() -> str:
        with Session(database_engine) as db:
            barrier.wait(timeout=10)
            if mutation == "delete":
                try:
                    delete_location(db, location_id)
                except LocationIntegrityError:
                    db.rollback()
                    return "retained"
            else:
                record = db.scalar(
                    select(Location).where(Location.id == location_id).with_for_update()
                )
                assert record is not None
                record.retired_at = datetime.now(UTC)
            db.commit()
            return "ok"

    def edit() -> str:
        with Session(database_engine) as db:
            barrier.wait(timeout=10)
            service.update(
                db,
                identifier,
                ScheduleUpdate(
                    activity_kind="inspect",
                    title="New day",
                    due_on=date(2026, 10, 15),
                    target=ScheduleTarget(kind="location", id=location_id),
                    expected_version=1,
                ),
            )
            db.commit()
            return "ok"

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(modify), pool.submit(edit)]
            results = [f.result(timeout=20) for f in futures]
        assert results[1] == "ok"
        assert results[0] == ("retained" if mutation == "delete" else "ok")
        with Session(database_engine) as db:
            projection = service.read(db, identifier, DAY)
            assert projection.target is not None
            assert projection.target.id == location_id
            assert projection.version == 2
    finally:
        with database_engine.begin() as c:
            c.execute(delete(ScheduledActivity).where(ScheduledActivity.id == identifier))
            c.execute(delete(Location).where(Location.id == location_id))


def test_api_filters_target_choices_and_boundary_dates(
    authenticated_browser: tuple[str, str],
) -> None:
    from .test_search import _api_get

    payload = {"activity_kind": "inspect", "title": "Literal %_ title", "due_on": "2026-10-08"}
    assert mutate(authenticated_browser, "POST", "/api/v1/schedule", payload)[0] == 201
    cookie, _ = authenticated_browser
    for query, expected in (
        ("today=2026-10-09&window=overdue", 1),
        ("today=2026-10-09&window=today", 0),
        ("q=%25_", 1),
        ("q=absent", 0),
        ("activity_kind=water", 0),
        ("status=planned&status=completed&activity_kind=water&activity_kind=inspect&q=%25_", 1),
        ("status=completed&status=cancelled&q=%25_", 0),
    ):
        status, body = _api_get("/api/v1/schedule?" + query, cookie)
        assert status == 200
        assert body["total"] == expected
    assert _api_get("/api/v1/schedule?today=2026-10-10T00:00:00Z", cookie)[0] == 422
    assert _api_get("/api/v1/schedule?today=0", cookie)[0] == 422
    assert _api_get("/api/v1/schedule?status=overdue", cookie)[0] == 422
    assert _api_get("/api/v1/schedule?" + "&".join(["status=planned"] * 4), cookie)[0] == 422
    assert _api_get("/api/v1/schedule?target_id=" + str(uuid7()), cookie)[0] == 422
    assert _api_get("/api/v1/schedule?today=9999-12-31&window=later", cookie)[0] == 200
    assert _api_get("/api/v1/schedule/targets/plant?limit=1", cookie)[0] == 200


@pytest.mark.parametrize(
    ("start", "end", "outside"),
    [
        (date(2024, 2, 1), date(2024, 2, 29), date(2024, 3, 1)),
        (date(2026, 12, 1), date(2026, 12, 31), date(2027, 1, 1)),
    ],
)
def test_calendar_range_intersects_existing_filters_and_preserves_order(
    database_connection: Connection,
    start: date,
    end: date,
    outside: date,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        location = Location(name="Calendar range bench")
        db.add(location)
        db.flush()
        rows = [
            service.create(
                db,
                ScheduleWrite(
                    activity_kind="inspect",
                    title="Calendar boundary",
                    due_on=due,
                    target=ScheduleTarget(kind="location", id=location.id),
                ),
            )
            for due in (start - date.resolution, start, end, end, outside)
        ]
        page = service.list_activities(
            db,
            today=end,
            due_from=start,
            due_to=end,
            target_kind="location",
            target_id=location.id,
            activity_kind="inspect",
            q="Calendar boundary",
            limit=2,
        )
        assert page.total == 3
        assert [a.id for a in page.items] == [rows[1].id, min(rows[2].id, rows[3].id)]
        assert page.items[0].overdue is True
        tail = service.list_activities(
            db,
            today=end,
            due_from=start,
            due_to=end,
            target_kind="location",
            target_id=location.id,
            offset=2,
        )
        assert [a.id for a in tail.items] == [max(rows[2].id, rows[3].id)]
        assert tail.items[0].overdue is False
        assert (
            service.list_activities(
                db,
                today=end,
                due_from=start,
                due_to=end,
                window="today",
                target_kind="location",
                target_id=location.id,
            ).total
            == 2
        )
        assert (
            service.list_activities(
                db,
                today=end,
                due_from=start,
                due_to=end,
                window="overdue",
                target_kind="location",
                target_id=location.id,
            ).total
            == 1
        )
        assert (
            service.list_activities(
                db,
                today=end,
                due_from=start,
                due_to=end,
                activity_kind="water",
                target_kind="location",
                target_id=location.id,
            ).total
            == 0
        )
        service.complete(db, rows[1].id, ScheduleComplete(expected_version=1))
        service.cancel(db, rows[2].id, 1)
        for status, row in (("completed", rows[1]), ("cancelled", rows[2])):
            terminal = service.list_activities(
                db,
                today=end,
                due_from=start,
                due_to=end,
                target_kind="location",
                target_id=location.id,
                status=cast(ScheduleStatus, status),
            )
            assert [a.id for a in terminal.items] == [row.id]
            assert not terminal.items[0].overdue
        assert (
            service.list_activities(
                db, today=end, due_from=outside, target_kind="location", target_id=location.id
            ).total
            == 1
        )
        assert (
            service.list_activities(
                db, today=end, due_to=start, target_kind="location", target_id=location.id
            ).total
            == 1
        )


def test_calendar_api_auth_date_validation_and_versioned_reschedule(
    authenticated_browser: tuple[str, str],
) -> None:
    from .test_search import _api_get

    cookie, _ = authenticated_browser
    query = (
        "/api/v1/schedule?due_from=2024-02-01&due_to=2024-02-29&today=2024-02-29&q=Calendar%20API"
    )
    assert _api_get(query, "")[0] == 401
    payload = {"activity_kind": "inspect", "title": "Calendar API", "due_on": "2024-02-29"}
    status, _, created = mutate(authenticated_browser, "POST", "/api/v1/schedule", payload)
    assert status == 201
    status, page = _api_get(query, cookie)
    assert status == 200
    items = page["items"]
    assert isinstance(items, list)
    assert [a["id"] for a in items] == [created["id"]]
    assert items[0]["due_on"] == "2024-02-29"
    assert not items[0]["overdue"]
    for bad in (
        "due_from=2024-03-01&due_to=2024-02-29",
        "due_from=2024-02-30",
        "due_to=2024-02-29T00:00:00Z",
    ):
        assert _api_get("/api/v1/schedule?" + bad, cookie)[0] == 422
    path = f"/api/v1/schedule/{created['id']}"
    assert (
        mutate(
            authenticated_browser,
            "PUT",
            path,
            {**payload, "due_on": "2024-03-01", "expected_version": 1},
        )[0]
        == 200
    )
    assert (
        mutate(authenticated_browser, "POST", path + "/cancel", {"expected_version": 1})[0] == 409
    )
    assert _api_get(query, cookie)[1]["items"] == []
    assert (
        mutate(authenticated_browser, "POST", path + "/cancel", {"expected_version": 2})[0] == 200
    )


def test_schedule_note_search_is_literal_and_filtered_before_calendar_count_and_page(
    database_connection: Connection,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        activities = [
            service.create(
                db,
                ScheduleWrite(
                    activity_kind="inspect",
                    title="Readiness check",
                    due_on=due,
                    notes=notes,
                ),
            )
            for due, notes in (
                (date(2026, 10, 1), "Inspection bench %_ context"),
                (date(2026, 10, 2), "Inspection bench second"),
                (date(2026, 11, 1), "Inspection bench next month"),
                (date(2026, 10, 3), "Inspection bench cancelled"),
            )
        ]
        service.cancel(db, activities[-1].id, 1)
        start, end = date(2026, 10, 1), date(2026, 10, 31)
        page = service.list_activities(
            db, today=DAY, q="inspection BENCH", limit=1, due_from=start, due_to=end
        )
        assert page.total == 2
        assert [item.id for item in page.items] == [activities[0].id]
        tail = service.list_activities(
            db, today=DAY, q="Inspection bench", offset=50, due_from=start, due_to=end
        )
        assert tail.total == 2
        assert tail.items == []
        literal = service.list_activities(db, today=DAY, q="%_", due_from=start, due_to=end)
        assert literal.total == 1
        assert literal.items[0].id == activities[0].id
        assert service.list_activities(db, today=DAY, q="Inspection bench").total == 3
        assert (
            service.list_activities(
                db,
                today=DAY,
                q="Inspection bench",
                activity_kind="water",
                due_from=start,
                due_to=end,
            ).total
            == 0
        )


def test_multiselect_filters_union_within_dimensions_intersect_before_paging(
    database_connection: Connection,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity = BotanicalIdentity(scientific_name="Filterus combinatus")
        location = Location(name="Multi filter bench")
        db.add_all([identity, location])
        db.flush()
        plant = Plant(
            direct_origin_kind="unknown",
            botanical_identity_id=identity.id,
            lifecycle="active",
            label="Filter plant",
        )
        db.add(plant)
        db.flush()
        first = service.create(
            db,
            ScheduleWrite(
                activity_kind="inspect",
                title="Multi %_ inspect",
                due_on=DAY,
                target=ScheduleTarget(kind="plant", id=plant.id),
            ),
        )
        second = service.create(
            db,
            ScheduleWrite(
                activity_kind="water",
                title="Multi %_ water",
                due_on=DAY,
                target=ScheduleTarget(kind="location", id=location.id),
            ),
        )
        third = service.create(
            db,
            ScheduleWrite(
                activity_kind="water",
                title="Multi %_ cancelled",
                due_on=DAY,
                target=ScheduleTarget(kind="plant", id=plant.id),
            ),
        )
        service.create(
            db, ScheduleWrite(activity_kind="inspect", title="Multi %_ untargeted", due_on=DAY)
        )
        service.complete(db, second.id, ScheduleComplete(expected_version=1))
        service.cancel(db, third.id, 1)
        expected = sorted([first.id, second.id])
        page = service.list_activities(
            db,
            today=DAY,
            status=("planned", "completed"),
            activity_kind=("inspect", "water"),
            target_kind=("plant", "location"),
            q="Multi %_",
            window="today",
            limit=1,
        )
        assert page.total == 2
        assert [item.id for item in page.items] == expected[:1]
        tail = service.list_activities(
            db,
            today=DAY,
            status=("planned", "completed"),
            activity_kind=("inspect", "water"),
            target_kind=("plant", "location"),
            q="Multi %_",
            window="today",
            limit=1,
            offset=1,
        )
        assert tail.total == 2
        assert [item.id for item in tail.items] == expected[1:]
        assert (
            service.list_activities(
                db, today=DAY, status=("planned", "completed", "cancelled"), q="Multi %_"
            ).total
            == 4
        )
        assert (
            service.list_activities(
                db,
                today=DAY,
                status=("planned", "completed"),
                activity_kind=("water",),
                target_kind=("plant", "location"),
                q="Multi %_",
            ).total
            == 1
        )
        assert (
            service.list_activities(
                db, today=DAY, status=("completed", "cancelled"), window="overdue", q="Multi %_"
            ).total
            == 0
        )
        assert (
            service.list_activities(
                db,
                today=DAY,
                status=("planned", "completed", "cancelled"),
                target_kind=(
                    "botanical_identity",
                    "seed_lot",
                    "sowing",
                    "plant",
                    "plant_group",
                    "location",
                ),
                q="Multi %_",
            ).total
            == 3
        )
        with pytest.raises(service.ScheduleError, match="schedule_target_kind_required"):
            service.list_activities(
                db, today=DAY, target_kind=("plant", "location"), target_id=plant.id
            )
