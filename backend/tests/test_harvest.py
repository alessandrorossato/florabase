from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast
from unittest.mock import MagicMock
from uuid import uuid7

import pytest
from fastapi import HTTPException, Response
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.events.model import Event
from florabase.events.schemas import EventUpdate
from florabase.events.service import EventDomainConflictError, delete_event, update_event
from florabase.harvests import api, service
from florabase.harvests.model import Harvest, HarvestItem, MaterialKind
from florabase.harvests.schemas import HarvestQuantity, HarvestWrite
from florabase.plants.model import Plant, PlantGroup


def payload(**values: object) -> HarvestWrite:
    return HarvestWrite.model_validate(
        {"plant_id": str(uuid7()), "items": [{"material_kind": "fruit"}], **values}
    )


@pytest.mark.parametrize("material", list(MaterialKind))
def test_material_vocabulary_and_unknown_quantity(material: MaterialKind) -> None:
    data = payload(items=[{"material_kind": material, "description": " Optional \r\ncontext "}])
    assert data.items[0].quantity is None
    assert data.items[0].description == "Optional \ncontext"


@pytest.mark.parametrize(
    ("kind", "unit", "value"),
    [
        ("item_count", None, "18"),
        ("weight", "g", "42"),
        ("weight", "kg", "1.2"),
        ("weight", "mg", "0.1"),
    ],
)
@pytest.mark.parametrize("approximate", [True, False])
def test_explicit_quantity_precision(
    kind: str, unit: str | None, value: str, approximate: bool
) -> None:
    quantity = HarvestQuantity.model_validate(
        {"kind": kind, "unit": unit, "value": value, "is_approximate": approximate}
    )
    assert quantity.model_dump(mode="json")["value"] == value
    assert quantity.is_approximate is approximate


@pytest.mark.parametrize(
    "values",
    [
        {"value": "0"},
        {"value": "-1"},
        {"value": "NaN"},
        {"value": "Infinity"},
        {"value": "1.1"},
        {"unit": "g"},
        {"kind": "weight"},
    ],
)
def test_invalid_quantities(values: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        HarvestQuantity.model_validate(
            {"kind": "item_count", "value": "1", "is_approximate": False, **values}
        )


@pytest.mark.parametrize(
    "values",
    [
        {"plant_id": None},
        {"plant_group_id": str(uuid7())},
        {"items": []},
        {"location_id": str(uuid7())},
        {"items": [{"id": str(uuid7()), "material_kind": "unknown"}]},
    ],
)
def test_source_and_aggregate_validation(values: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        payload(**values)


@pytest.mark.parametrize(
    "date",
    [
        None,
        {"precision": "year", "year": 2026},
        {"precision": "month", "year": 2026, "month": 8},
        {"precision": "day", "year": 2026, "month": 8, "day": 21},
    ],
)
def test_partial_dates_and_normalization(date: dict[str, object] | None) -> None:
    result = payload(occurred_on=date, label="  useful  label ", notes=" Notes\r\nmore ")
    assert result.label == "useful label"
    assert result.notes == "Notes\nmore"
    assert (result.occurred_on is None) == (date is None)


def source(group: bool = False) -> Plant | PlantGroup:
    return (PlantGroup if group else Plant)(
        id=uuid7(),
        botanical_identity_id=uuid7(),
        direct_origin_kind="unknown",
        lifecycle="dead",
        location_id=uuid7(),
    )


@pytest.mark.parametrize("group", [False, True])
def test_atomic_create_never_mutates_source(group: bool) -> None:
    record = source(group)
    db = MagicMock()
    db.scalar.return_value = record
    db.scalars.return_value = []
    data = payload(
        plant_id=None if group else record.id,
        plant_group_id=record.id if group else None,
        items=[
            {
                "material_kind": "root",
                "quantity": {
                    "kind": "weight",
                    "value": "1.2",
                    "unit": "kg",
                    "is_approximate": True,
                },
            },
            {"material_kind": "seed"},
        ],
    )
    before = dict(record.__dict__)
    harvest = service.write_harvest(db, data)
    added = [call.args[0] for call in db.add.call_args_list]
    assert isinstance(added[0], Event)
    assert added[0].kind == "harvest"
    assert harvest.event_id == added[0].id
    assert (added[0].plant_id, added[0].plant_group_id) == (data.plant_id, data.plant_group_id)
    assert sum(isinstance(item, HarvestItem) for item in added) == 2
    assert before == record.__dict__
    db.commit.assert_not_called()


def test_correction_keeps_event_and_stable_line_ids() -> None:
    record = source(True)
    old_id = uuid7()
    harvest = Harvest(id=uuid7(), event_id=uuid7(), plant_id=uuid7())
    event = Event(id=harvest.event_id, kind="harvest", plant_id=harvest.plant_id)
    db = MagicMock()
    db.scalar.side_effect = [harvest, record, event]
    db.scalars.side_effect = [
        [HarvestItem(id=old_id, harvest_id=harvest.id, display_order=0, material_kind="leaf")],
        [],
    ]
    result = service.write_harvest(
        db,
        payload(
            plant_id=None,
            plant_group_id=record.id,
            items=[{"id": old_id, "material_kind": "leaf"}],
            occurred_on={"precision": "year", "year": 2025},
            notes="Corrected",
        ),
        harvest.id,
    )
    assert result is harvest
    assert event.plant_id is None
    assert event.plant_group_id == record.id
    assert event.notes == harvest.notes == "Corrected"
    assert event.occurred_on_year == harvest.occurred_on_year == 2025
    assert db.add.call_args.args[0].id == old_id


@pytest.mark.parametrize("existing", [False, True])
def test_rejects_foreign_line_ids(existing: bool) -> None:
    db = MagicMock()
    record = source()
    harvest = Harvest(id=uuid7(), event_id=uuid7())
    db.scalar.side_effect = [harvest, record, Event(id=harvest.event_id)] if existing else [record]
    db.scalars.return_value = []
    with pytest.raises(EventDomainConflictError, match=r"material line|material lines"):
        service.write_harvest(
            db,
            payload(items=[{"id": uuid7(), "material_kind": "fruit"}]),
            harvest.id if existing else None,
        )


def test_missing_source_and_missing_harvest() -> None:
    db = MagicMock()
    db.scalar.return_value = None
    with pytest.raises(LookupError):
        service.require_harvest(db, uuid7())
    with pytest.raises(LookupError):
        service.write_harvest(db, payload())


def test_missing_owned_event_detected() -> None:
    db = MagicMock()
    harvest = Harvest(id=uuid7(), event_id=uuid7())
    db.scalar.side_effect = [harvest, source(), None]
    with pytest.raises(RuntimeError):
        service.write_harvest(db, payload(), harvest.id)


def test_aggregate_delete_unlinks_media_and_removes_event() -> None:
    db = MagicMock()
    harvest = Harvest(id=uuid7(), event_id=uuid7())
    event = Event(id=harvest.event_id)
    db.scalar.side_effect = [harvest, None, None]
    db.get.return_value = event
    service.delete_harvest(db, harvest.id)
    assert [call.args[0] for call in db.delete.call_args_list] == [harvest, event]
    db.commit.assert_not_called()
    db.scalar.side_effect = [harvest, uuid7()]
    with pytest.raises(EventDomainConflictError):
        service.delete_harvest(db, harvest.id)


def test_owned_event_cannot_mutate_as_ordinary_history() -> None:
    db = MagicMock()
    db.scalar.return_value = uuid7()
    event = Event(id=uuid7(), kind="harvest")
    with pytest.raises(EventDomainConflictError, match="structured Harvest"):
        update_event(db, event, EventUpdate(kind="harvest"))
    with pytest.raises(EventDomainConflictError, match="structured Harvest"):
        delete_event(db, event)
    db.delete.assert_not_called()


def test_batched_projection_search_filters_and_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(UTC)
    record = source()
    identity = BotanicalIdentity(
        id=record.botanical_identity_id,
        scientific_name="Test species",
        common_name="Coffee",
        created_at=now,
        updated_at=now,
    )
    harvest = Harvest(
        id=uuid7(),
        event_id=uuid7(),
        plant_id=record.id,
        occurred_on_precision="year",
        occurred_on_year=2026,
        created_at=now,
        updated_at=now,
    )
    lines = [
        HarvestItem(
            id=uuid7(),
            harvest_id=harvest.id,
            display_order=i,
            material_kind=kind,
            quantity_kind="weight" if i == 0 else None,
            quantity_value=Decimal("1.2") if i == 0 else None,
            quantity_unit="kg" if i == 0 else None,
            quantity_is_approximate=False if i == 0 else None,
        )
        for i, kind in enumerate(["seed", "leaf", "fruit"])
    ]
    db = MagicMock()
    db.execute.return_value.all.return_value = [(harvest, record, None, identity)]
    db.scalars.return_value = lines
    monkeypatch.setattr(service, "primary_summaries", lambda *_: {})
    result = service.list_harvests(
        db,
        harvest_id=harvest.id,
        event_ids=[harvest.event_id],
        botanical_identity_id=identity.id,
        plant_id=record.id,
        query="Coffee%",
        material_kind="seed",
        source_type="plant",
    )
    assert result[0].display_title == "Coffee — Seeds + Leaves + more harvest"
    assert result[0].items[0].quantity is not None
    assert result[0].source.lifecycle == "dead"
    db.scalar.return_value = harvest
    assert service.read_harvest(db, harvest.id).event_id == harvest.event_id
    db.execute.return_value.all.return_value = []
    assert service.list_harvests(db, plant_group_id=uuid7(), source_type="plant_group") == []


def test_api_save_rollback_and_read_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    db = MagicMock()
    monkeypatch.setattr(
        api,
        "write_harvest",
        lambda *_: (_ for _ in ()).throw(IntegrityError("sql", {}, Exception("constraint"))),
    )
    with pytest.raises(HTTPException) as error:
        api._save(db, payload())
    assert error.value.status_code == 409
    db.rollback.assert_called_once()
    monkeypatch.setattr(
        api, "read_harvest", lambda *_: (_ for _ in ()).throw(LookupError("Harvest not found"))
    )
    with pytest.raises(HTTPException) as missing:
        api.read(uuid7(), db, MagicMock())
    assert missing.value.status_code == 404
    assert cast(Any, api._error(db, EventDomainConflictError("owned", "message"))).detail == {
        "code": "owned",
        "message": "message",
    }


def test_api_success_paths_and_owner_requirement(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    from florabase.harvests.schemas import HarvestResponse, HarvestSource
    from florabase.plants.schemas import BotanicalIdentitySummary

    db = MagicMock()
    owner = cast(Any, SimpleNamespace(owner=True))
    now = datetime.now(UTC)
    result = HarvestResponse(
        id=uuid7(),
        plant_id=uuid7(),
        plant_group_id=None,
        label=None,
        display_title="Coffee — Fruit harvest",
        source=HarvestSource(
            type="plant",
            id=uuid7(),
            display_name="Coffee",
            label=None,
            lifecycle="dead",
            botanical_identity=BotanicalIdentitySummary(id=uuid7(), display_label="Coffee"),
        ),
        occurred_on=None,
        notes=None,
        items=[],
        event_id=uuid7(),
        created_at=now,
        updated_at=now,
    )
    monkeypatch.setattr(api, "write_harvest", lambda *_: Harvest(id=result.id))
    monkeypatch.setattr(api, "read_harvest", lambda *_: result)
    monkeypatch.setattr(api, "list_harvests", lambda *_args, **_kwargs: [result])
    monkeypatch.setattr(api, "delete_harvest", lambda *_: None)
    response = Response()
    assert api.create(payload(), response, db, owner) is result
    assert response.headers["Location"] == f"/api/v1/harvests/{result.id}"
    assert api.update(result.id, payload(), db, owner) is result
    assert api.read(result.id, db, owner) is result
    assert api.list_all(db, owner) == [result]
    assert api.delete(result.id, db, owner).status_code == 204
    with pytest.raises(HTTPException) as forbidden:
        api.create(payload(), Response(), db, cast(Any, SimpleNamespace(owner=False)))
    assert forbidden.value.status_code == 403
    monkeypatch.setattr(api, "delete_harvest", lambda *_: (_ for _ in ()).throw(LookupError()))
    with pytest.raises(HTTPException):
        api.delete(result.id, db, owner)
