from datetime import UTC

from sqlalchemy import DateTime, Numeric, Uuid

from florabase.db.base import Base
from florabase.seed_lots.model import (
    PartialDatePrecision,
    SeedLot,
    SeedLotLifecycle,
    SeedLotSourceKind,
    SeedQuantityKind,
    SeedWeightUnit,
    utc_now,
)


def test_seed_lot_mapping_has_only_the_persistence_contract() -> None:
    assert SeedLot.metadata is Base.metadata
    assert list(SeedLot.__table__.columns.keys()) == [
        "id",
        "botanical_identity_id",
        "label",
        "source_kind",
        "source_detail",
        "producer_plant_id",
        "producer_plant_group_id",
        "supplier_id",
        "material_provenance_place_id",
        "provenance_site_id",
        "acquisition_date_precision",
        "acquisition_date_year",
        "acquisition_date_month",
        "acquisition_date_day",
        "harvest_date_precision",
        "harvest_date_year",
        "harvest_date_month",
        "harvest_date_day",
        "quantity_kind",
        "quantity_value",
        "quantity_unit",
        "quantity_is_approximate",
        "expected_viability_until_precision",
        "expected_viability_until_year",
        "expected_viability_until_month",
        "expected_viability_until_day",
        "location_id",
        "lifecycle",
        "notes",
        "created_at",
        "updated_at",
    ]
    assert isinstance(SeedLot.__table__.c.id.type, Uuid)
    assert isinstance(SeedLot.__table__.c.quantity_value.type, Numeric)
    created_type = SeedLot.__table__.c.created_at.type
    updated_type = SeedLot.__table__.c.updated_at.type
    assert isinstance(created_type, DateTime)
    assert isinstance(updated_type, DateTime)
    assert created_type.timezone is True
    assert updated_type.timezone is True
    assert not any(
        name in SeedLot.__table__.columns
        for name in ("sowing_id", "order_id", "parent_seed_lot_id", "lineage_edge_id")
    )


def test_seed_lot_application_defaults_and_vocabularies() -> None:
    lot = SeedLot(botanical_identity_id=SeedLot.__table__.c.id.default.arg({}))
    id_default = SeedLot.__table__.c.id.default
    created_default = SeedLot.__table__.c.created_at.default

    assert id_default is not None
    assert created_default is not None
    assert id_default.arg({}).version == 7
    assert created_default.arg({}).tzinfo is UTC
    assert utc_now().tzinfo is UTC
    assert SeedLot.__table__.c.source_kind.default.arg == "unknown"
    assert SeedLot.__table__.c.lifecycle.default.arg == "active"
    assert lot.source_kind is None  # SQLAlchemy applies column defaults at insert time.
    assert {item.value for item in SeedLotSourceKind} == {
        "purchased",
        "purchased_fruit",
        "self_collected",
        "collection_produced",
        "gift_exchange",
        "other",
        "unknown",
    }
    assert {item.value for item in PartialDatePrecision} == {"year", "month", "day"}
    assert {item.value for item in SeedQuantityKind} == {"seed_count", "weight"}
    assert {item.value for item in SeedWeightUnit} == {"g", "mg"}
    assert {item.value for item in SeedLotLifecycle} == {
        "active",
        "exhausted",
        "discarded",
        "lost",
    }
