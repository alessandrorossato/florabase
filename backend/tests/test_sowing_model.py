from datetime import UTC

from sqlalchemy import DateTime, Integer, Numeric, Uuid

from florabase.db.base import Base
from florabase.sowings.model import Sowing, SowingLifecycle, utc_now


def test_sowing_mapping_has_only_the_first_persistence_slice() -> None:
    assert Sowing.metadata is Base.metadata
    assert list(Sowing.__table__.columns.keys()) == [
        "id",
        "seed_lot_id",
        "label",
        "sowing_date_precision",
        "sowing_date_year",
        "sowing_date_month",
        "sowing_date_day",
        "quantity_kind",
        "quantity_value",
        "quantity_unit",
        "quantity_is_approximate",
        "germinated_count",
        "location_id",
        "substrate",
        "method_container",
        "pretreatment",
        "temperature_min_c",
        "temperature_max_c",
        "environment",
        "lifecycle",
        "notes",
        "created_at",
        "updated_at",
    ]
    assert isinstance(Sowing.__table__.c.id.type, Uuid)
    assert isinstance(Sowing.__table__.c.quantity_value.type, Numeric)
    assert isinstance(Sowing.__table__.c.temperature_min_c.type, Numeric)
    assert isinstance(Sowing.__table__.c.germinated_count.type, Integer)
    for column in (Sowing.__table__.c.created_at, Sowing.__table__.c.updated_at):
        assert isinstance(column.type, DateTime)
        assert column.type.timezone is True
    assert not any(
        name in Sowing.__table__.columns
        for name in ("botanical_identity_id", "plant_id", "plant_group_id", "attachment_id")
    )


def test_sowing_application_defaults_and_lifecycle() -> None:
    assert Sowing.__table__.c.id.default.arg({}).version == 7
    assert Sowing.__table__.c.created_at.default.arg({}).tzinfo is UTC
    assert utc_now().tzinfo is UTC
    assert Sowing.__table__.c.lifecycle.default.arg == "active"
    assert {item.value for item in SowingLifecycle} == {
        "active",
        "reversed",
        "completed",
        "failed",
        "abandoned",
    }
