from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, Literal, cast
from unittest.mock import MagicMock
from uuid import uuid7

import pytest
from fastapi import HTTPException, Response

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.events import api, service
from florabase.events.model import Event
from florabase.events.schemas import EventCreate, EventResponse, EventUpdate, PlantEventTarget
from florabase.events.service import (
    EventDomainConflictError,
    EventProjection,
    EventReferenceNotFoundError,
)
from florabase.locations.model import Location
from florabase.plants.model import Plant, PlantGroup


def _targets() -> tuple[Plant, PlantGroup, Location, Location]:
    now = datetime.now(UTC)
    plant = Plant(
        id=uuid7(),
        botanical_identity_id=uuid7(),
        direct_origin_kind="unknown",
        lifecycle="active",
        created_at=now,
        updated_at=now,
    )
    group = PlantGroup(
        id=uuid7(),
        botanical_identity_id=uuid7(),
        direct_origin_kind="unknown",
        lifecycle="active",
        created_at=now,
        updated_at=now,
    )
    first = Location(id=uuid7(), name="Bench", created_at=now, updated_at=now)
    second = Location(id=uuid7(), name="Greenhouse", created_at=now, updated_at=now)
    return plant, group, first, second


def _database(target: Plant | PlantGroup, *locations: Location) -> MagicMock:
    database = MagicMock()
    lookup = {(type(item), item.id): item for item in (target, *locations)}
    database.get.side_effect = lambda model, item_id: lookup.get((model, item_id))
    database.scalar.return_value = target
    return database


@pytest.mark.parametrize(
    ("kind", "lifecycle"),
    [("death", "dead"), ("loss", "lost"), ("discarded", "discarded")],
)
@pytest.mark.parametrize("target_kind", ["plant", "plant_group"])
def test_create_event_locks_target_and_applies_lifecycle_once(
    kind: str, lifecycle: str, target_kind: Literal["plant", "plant_group"]
) -> None:
    plant, group, _, _ = _targets()
    target = plant if target_kind == "plant" else group
    database = _database(target)
    event = service.create_event(database, target_kind, target.id, EventCreate(kind=kind))
    assert (event.plant_id, event.plant_group_id) == (
        (plant.id, None) if target_kind == "plant" else (None, group.id)
    )
    assert target.lifecycle == lifecycle
    database.add.assert_called_once_with(event)
    statement = database.scalar.call_args.args[0]
    assert statement._for_update_arg is not None


def test_movement_create_updates_location_but_update_and_delete_do_not_reapply_or_reverse() -> None:
    plant, _, old_location, destination = _targets()
    plant.location_id = old_location.id
    database = _database(plant, old_location, destination)
    event = service.create_event(
        database,
        "plant",
        plant.id,
        EventCreate(kind="movement", destination_location_id=destination.id),
    )
    assert plant.location_id == destination.id
    service.update_event(database, event, EventUpdate(kind="observation", notes="corrected"))
    assert event.destination_location_id is None
    assert plant.location_id == destination.id
    service.delete_event(database, event)
    assert plant.location_id == destination.id
    database.delete.assert_called_once_with(event)


def test_event_update_never_applies_lifecycle_side_effect() -> None:
    plant, _, _, _ = _targets()
    plant.lifecycle = "active"
    database = _database(plant)
    event = Event(plant_id=plant.id, kind="observation")
    service.update_event(database, event, EventUpdate(kind="death"))
    assert plant.lifecycle == "active"
    service.update_event(database, event, EventUpdate(kind="observation"))
    assert plant.lifecycle == "active"


def test_missing_target_location_and_exact_zero_group_conflict_are_explicit() -> None:
    database = MagicMock()
    database.scalar.return_value = None
    with pytest.raises(EventReferenceNotFoundError) as target_error:
        service.create_event(database, "plant", uuid7(), EventCreate(kind="observation"))
    assert target_error.value.code == "plant_not_found"

    plant, group, _, _ = _targets()
    database = _database(plant)
    with pytest.raises(EventReferenceNotFoundError) as location_error:
        service.create_event(
            database,
            "plant",
            plant.id,
            EventCreate(kind="movement", destination_location_id=uuid7()),
        )
    assert location_error.value.code == "location_not_found"

    group.quantity_value = 0
    group.quantity_is_approximate = False
    group.lifecycle = "completed"
    database = _database(group)
    with pytest.raises(EventDomainConflictError):
        service.create_event(database, "plant_group", group.id, EventCreate(kind="loss"))


def test_listing_uses_dated_known_component_order_and_requires_target() -> None:
    plant, _, _, _ = _targets()
    database = _database(plant)
    database.execute.return_value.__iter__.return_value = iter([])
    assert service.list_events(database, "plant", plant.id) == []
    statement = database.execute.call_args.args[0]
    assert len(statement._order_by_clauses) == 6
    database.get.return_value = None
    with pytest.raises(EventReferenceNotFoundError):
        service.list_events(database, "plant", uuid7())


def test_get_and_response_projection_are_typed_and_target_aware(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plant, group, _, destination = _targets()
    now = datetime.now(UTC)
    plant_identity = BotanicalIdentity(
        id=plant.botanical_identity_id,
        scientific_name="Solanum betaceum",
        created_at=now,
        updated_at=now,
    )
    group_identity = BotanicalIdentity(
        id=group.botanical_identity_id,
        scientific_name="Capsicum annuum",
        created_at=now,
        updated_at=now,
    )
    plant_event = Event(
        id=uuid7(),
        plant_id=plant.id,
        kind="movement",
        occurred_on_precision="month",
        occurred_on_year=2026,
        occurred_on_month=9,
        destination_location_id=destination.id,
        created_at=now,
        updated_at=now,
    )
    group_event = Event(
        id=uuid7(),
        plant_group_id=group.id,
        kind="observation",
        created_at=now,
        updated_at=now,
    )
    database = MagicMock()
    database.execute.return_value.one_or_none.return_value = (
        plant_event,
        plant,
        None,
        destination,
        plant_identity,
        None,
    )
    assert service.get_event(database, plant_event.id) == EventProjection(
        plant_event, plant, None, destination, plant_identity, None
    )
    database.execute.return_value.one_or_none.return_value = None
    assert service.get_event(database, uuid7()) is None
    monkeypatch.setattr(service, "list_locations", lambda _: [destination])
    responses = service.event_responses(
        database,
        [
            EventProjection(plant_event, plant, None, destination, plant_identity, None),
            EventProjection(group_event, None, group, None, None, group_identity),
        ],
    )
    assert responses[0].target.type == "plant"
    assert responses[0].occurred_on is not None
    assert responses[0].destination_location is not None
    assert responses[0].destination_location.display_path == "Greenhouse"
    assert responses[1].target.type == "plant_group"
    with pytest.raises(RuntimeError):
        service.event_responses(
            database, [EventProjection(group_event, None, None, None, None, None)]
        )


def test_event_api_routes_and_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    plant, _, _, _ = _targets()
    now = datetime.now(UTC)
    identity = BotanicalIdentity(
        id=plant.botanical_identity_id,
        scientific_name="Solanum betaceum",
        created_at=now,
        updated_at=now,
    )
    event = Event(
        id=uuid7(),
        plant_id=plant.id,
        kind="observation",
        created_at=now,
        updated_at=now,
    )
    projection = EventProjection(event, plant, None, None, identity, None)
    response_model = EventResponse(
        id=event.id,
        target=PlantEventTarget(
            id=plant.id,
            label=plant.label,
            lifecycle="active",
            botanical_identity={
                "id": identity.id,
                "display_label": "Solanum betaceum",
            },
        ),
        kind="observation",
        occurred_on=None,
        notes=None,
        destination_location_id=None,
        destination_location=None,
        created_at=now,
        updated_at=now,
    )
    database = MagicMock()
    actor = cast(Any, SimpleNamespace(owner=True))
    payload = EventCreate(kind="observation")
    monkeypatch.setattr(api, "list_events", lambda _db, _type, _id: [projection])
    monkeypatch.setattr(api, "event_responses", lambda _db, _items: [response_model])
    monkeypatch.setattr(api, "get_event", lambda _db, _id: projection)
    monkeypatch.setattr(api, "create_event", lambda _db, _type, _id, _payload: event)
    monkeypatch.setattr(api, "update_event", lambda _db, item, _payload: item)
    monkeypatch.setattr(api, "delete_event", lambda _db, _item: None)

    assert api.list_plant_events(plant.id, actor, database) == [response_model]
    assert api.list_plant_group_events(plant.id, actor, database) == [response_model]
    response = Response()
    assert api.create_plant_event(plant.id, payload, response, actor, database) == response_model
    assert response.headers["location"].endswith(str(event.id))
    assert (
        api.create_plant_group_event(plant.id, payload, Response(), actor, database)
        == response_model
    )
    assert api.read_event(event.id, actor, database) == response_model
    assert (
        api.update_one_event(
            event.id,
            EventUpdate(kind="observation", notes="Corrected"),
            actor,
            database,
        )
        == response_model
    )
    assert api.delete_one_event(event.id, actor, database).status_code == 204

    monkeypatch.setattr(api, "get_event", lambda _db, _id: None)
    with pytest.raises(HTTPException) as missing:
        api.read_event(uuid7(), actor, database)
    assert missing.value.status_code == 404
    error = EventReferenceNotFoundError("location_not_found", "Location not found")
    monkeypatch.setattr(
        api,
        "create_event",
        lambda _db, _type, _id, _payload: (_ for _ in ()).throw(error),
    )
    with pytest.raises(HTTPException) as invalid:
        api.create_plant_event(plant.id, payload, Response(), actor, database)
    assert invalid.value.status_code == 404
    monkeypatch.setattr(
        api,
        "list_events",
        lambda _db, _type, _id: (_ for _ in ()).throw(error),
    )
    with pytest.raises(HTTPException) as invalid_list:
        api.list_plant_events(plant.id, actor, database)
    assert invalid_list.value.status_code == 404
    conflict = EventDomainConflictError("conflict", "Conflict")
    assert api._translate(conflict).status_code == 409
    with pytest.raises(HTTPException) as forbidden:
        api.create_plant_event(
            plant.id,
            payload,
            Response(),
            cast(Any, SimpleNamespace(owner=False)),
            database,
        )
    assert forbidden.value.status_code == 403
