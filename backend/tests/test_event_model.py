from datetime import UTC

from sqlalchemy import DateTime, Uuid

from florabase.db.base import Base
from florabase.events.model import Event, EventKind, utc_now


def test_event_is_focused_uuidv7_mapping_with_exact_vocabulary() -> None:
    assert Event.metadata is Base.metadata
    assert list(Event.__table__.columns.keys()) == [
        "id",
        "plant_id",
        "plant_group_id",
        "kind",
        "occurred_on_precision",
        "occurred_on_year",
        "occurred_on_month",
        "occurred_on_day",
        "notes",
        "destination_location_id",
        "recipient",
        "resulting_plant_id",
        "reversed_operation_receipt_id",
        "created_at",
        "updated_at",
    ]
    assert isinstance(Event.__table__.c.id.type, Uuid)
    assert Event.__table__.c.id.default.arg({}).version == 7
    for column in (Event.__table__.c.created_at, Event.__table__.c.updated_at):
        assert isinstance(column.type, DateTime)
        assert column.type.timezone is True
    assert utc_now().tzinfo is UTC
    assert {item.value for item in EventKind} == {
        "observation",
        "movement",
        "repotting",
        "flowering",
        "fruiting",
        "pruning",
        "treatment",
        "harvest",
        "extraction",
        "reintegration",
        "transfer",
        "death",
        "loss",
        "discarded",
        "other",
    }
    assert "payload" not in Event.__table__.columns
    assert "metadata" not in Event.__table__.columns
