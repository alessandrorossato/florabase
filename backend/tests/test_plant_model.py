from datetime import UTC

from sqlalchemy import Boolean, DateTime, Integer, Uuid

from florabase.db.base import Base
from florabase.plants.model import (
    DirectOriginKind,
    Plant,
    PlantGroup,
    PlantGroupLifecycle,
    PlantLifecycle,
    utc_now,
)


def test_plant_and_group_are_distinct_focused_mappings() -> None:
    assert Plant.metadata is Base.metadata
    assert PlantGroup.metadata is Base.metadata
    common = [
        "id",
        "botanical_identity_id",
        "originating_sowing_id",
    ]
    plant_origin = ["originating_plant_group_id"]
    common_tail = [
        "direct_origin_kind",
        "direct_origin_detail",
        "supplier_id",
        "material_provenance_place_id",
        "label",
        "collection_entry_date_precision",
        "collection_entry_date_year",
        "collection_entry_date_month",
        "collection_entry_date_day",
    ]
    tail = ["location_id", "lifecycle", "notes", "created_at", "updated_at"]
    assert list(Plant.__table__.columns.keys()) == common + plant_origin + common_tail + tail
    assert list(PlantGroup.__table__.columns.keys()) == [
        *common,
        *common_tail,
        "quantity_value",
        "quantity_is_approximate",
        *tail,
    ]
    assert isinstance(Plant.__table__.c.id.type, Uuid)
    assert isinstance(PlantGroup.__table__.c.quantity_value.type, Integer)
    assert isinstance(PlantGroup.__table__.c.quantity_is_approximate.type, Boolean)
    for model in (Plant, PlantGroup):
        for column in (model.__table__.c.created_at, model.__table__.c.updated_at):
            assert isinstance(column.type, DateTime)
            assert column.type.timezone is True
        assert not any(
            name in model.__table__.columns
            for name in (
                "lineage_edge_id",
                "event_id",
                "attachment_id",
            )
        )
    assert "quantity_value" not in Plant.__table__.columns


def test_plant_defaults_uuidv7_and_exact_vocabularies() -> None:
    for model in (Plant, PlantGroup):
        assert model.__table__.c.id.default.arg({}).version == 7
        assert model.__table__.c.created_at.default.arg({}).tzinfo is UTC
        assert model.__table__.c.lifecycle.default.arg == "active"
    assert Plant.__table__.c.direct_origin_kind.default is None
    assert PlantGroup.__table__.c.direct_origin_kind.default is None
    assert utc_now().tzinfo is UTC
    assert {item.value for item in DirectOriginKind} == {
        "purchased",
        "gift_exchange",
        "collection_produced",
        "other",
        "unknown",
    }
    assert {item.value for item in PlantLifecycle} == {"active", "dead", "lost", "discarded"}
    assert {item.value for item in PlantGroupLifecycle} == {
        "active",
        "completed",
        "dead",
        "lost",
        "discarded",
    }
