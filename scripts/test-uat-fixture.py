"""Real PostgreSQL fixture/guard regressions, run only in disposable UAT smoke."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session
from uat_fixture import FixtureError, read_manifest, require_identity, validate_manifest

from florabase.auth.security import validate_password
from florabase.core.config import get_settings
from florabase.db.session import get_engine


def test_normal_bootstrap_still_rejects_public_fixture_password() -> None:
    with pytest.raises(ValueError, match="12 and 1024"):
        validate_password("preview")


@pytest.mark.parametrize(
    "key,value",
    [
        ("FLORABASE_WORKFLOW_MODE", "dev"),
        ("FLORABASE_WORKFLOW_MODE", "production"),
        ("FLORABASE_UAT_PROJECT", "florabase"),
        ("FLORABASE_UAT_PROJECT", "florabase-preview"),
        ("FLORABASE_UAT_PROJECT", "florabase-prod"),
        ("FLORABASE_UAT_SOURCE", "relative"),
    ],
)
def test_seed_guard_refuses_wrong_runtime_identity(key: str, value: str) -> None:
    with Session(get_engine()) as database, patch.dict("os.environ", {key: value}):
        with pytest.raises(FixtureError, match="identity refused"):
            require_identity(get_settings(), database)


@pytest.mark.parametrize(
    "field,value",
    [
        ("database_url", "postgresql+psycopg://owner:unused@prod:5432/florabase"),
        ("environment", "production"),
        ("canonical_origin", "http://localhost:5173"),
        ("attachment_storage_root", Path("/tmp/not-uat")),
    ],
)
def test_seed_guard_refuses_wrong_database_origin_environment(field: str, value: object) -> None:
    settings = get_settings().model_copy(update={field: value})
    with (
        Session(get_engine()) as database,
        pytest.raises(FixtureError, match="identity refused"),
    ):
        require_identity(settings, database)


def test_exported_variables_without_resource_marker_are_insufficient(
    tmp_path: Path,
) -> None:
    with (
        Session(get_engine()) as database,
        patch("uat_fixture.Path.is_file", return_value=False),
    ):
        with pytest.raises(FixtureError, match="resource marker"):
            require_identity(get_settings(), database)


def test_wrong_connected_database_refuses_even_with_expected_marker() -> None:
    with (
        Session(get_engine()) as database,
        patch.object(database, "execute") as execute,
    ):
        execute.return_value.one.return_value = ("production", "production")
        with pytest.raises(FixtureError, match="Connected database"):
            require_identity(get_settings(), database)


@pytest.mark.parametrize(
    "manifest",
    [
        {"version": 1, "state": "building", "records": {}},
        {"version": 999, "state": "ready", "records": {}},
        {"version": 1, "state": "ready", "records": []},
    ],
)
def test_incompatible_or_interrupted_manifest_requires_explicit_reset(
    tmp_path: Path, manifest: dict[str, object]
) -> None:
    (tmp_path / ".uat-fixture.json").write_text(json.dumps(manifest))
    with pytest.raises(FixtureError, match="guarded uat-preview-reset"):
        read_manifest(tmp_path)


def test_missing_baseline_fails_without_recreating_or_deleting_operator_records() -> None:
    with Session(get_engine()) as database:
        root = require_identity(get_settings(), database)
        manifest = read_manifest(root)
        assert manifest is not None
        manifest["records"]["supplier:nursery"] = "0198f000-0000-7000-8000-000000000001"
        with pytest.raises(FixtureError, match="missing records"):
            validate_manifest(database, root, manifest)


def test_missing_binary_media_fails_with_explicit_reset_instruction() -> None:
    with Session(get_engine()) as database:
        root = require_identity(get_settings(), database)
        manifest = read_manifest(root)
        assert manifest is not None
        with patch("uat_fixture.Path.is_file", return_value=False):
            with pytest.raises(FixtureError, match="media content is missing"):
                validate_manifest(database, root, manifest)


def test_purchase_fixture_preserves_two_physical_lots_and_partial_unknown_knowledge() -> None:
    from decimal import Decimal
    from uuid import UUID

    from florabase.orders.model import Order
    from florabase.seed_lots.model import SeedLot

    with Session(get_engine()) as database:
        root = require_identity(get_settings(), database)
        manifest = read_manifest(root)
        assert manifest is not None
        records = manifest["records"]
        purchase = database.get(Order, UUID(records["order:exact"]))
        partial = database.get(Order, UUID(records["order:partial"]))
        packet_a = database.get(SeedLot, UUID(records["seed:0"]))
        packet_b = database.get(SeedLot, UUID(records["seed:3"]))
        assert purchase is not None and partial is not None
        assert packet_a is not None and packet_b is not None
        assert purchase.total_price == Decimal("42.50") and purchase.currency == "EUR"
        assert purchase.ordered_on_precision == "day" and purchase.ordered_on_day == 8
        assert packet_a.id != packet_b.id
        assert packet_a.botanical_identity_id == packet_b.botanical_identity_id
        assert packet_a.order_id == packet_b.order_id == purchase.id
        assert packet_a.supplier_id == packet_b.supplier_id == purchase.supplier_id
        assert packet_a.quantity_value == 48 and packet_b.quantity_value is None
        assert packet_a.acquisition_date_year is packet_b.acquisition_date_year is None
        assert (
            packet_a.material_provenance_place_id is packet_b.material_provenance_place_id is None
        )
        assert partial.ordered_on_precision == "month" and partial.ordered_on_day is None
        assert partial.total_price is partial.currency is partial.supplier_id is None


def test_species_distribution_fixture_scopes_and_truthful_link() -> None:
    from uuid import UUID

    from florabase.explore.service import list_identities
    from florabase.external_botany.model import ExternalTaxonLink

    with Session(get_engine()) as database:
        root = require_identity(get_settings(), database)
        manifest = read_manifest(root)
        assert manifest is not None
        records = manifest["records"]
        all_ids = {row.id for row in list_identities(database).items}
        assert UUID(records["identity:Viola tricolor"]) not in all_ids
        assert len(all_ids) == 5
        assert {row.scientific_name for row in list_identities(database, scope="living").items} == {
            "Ocimum basilicum",
            "Aloe vera",
        }
        assert {
            row.scientific_name for row in list_identities(database, scope="current").items
        } == {"Ocimum basilicum", "Aloe vera", "Lavandula angustifolia", "Salvia officinalis"}
        assert (
            list_identities(database, scope="historical").items[0].scientific_name
            == "Raphanus sativus"
        )
        link = database.get(ExternalTaxonLink, UUID(records["external_taxon:basil"]))
        assert link is not None
        assert link.external_id == "48GBK"
        assert link.scientific_name == "Ocimum basilicum L."
        assert list_identities(database).occurrence_ready == 1


def test_native_range_fixture_overlap_disjoint_custom_and_no_range() -> None:
    from uuid import UUID

    from florabase.explore import native_ranges

    with Session(get_engine()) as database:
        manifest = read_manifest(require_identity(get_settings(), database))
        assert manifest is not None
        records = manifest["records"]
        overview = native_ranges.overview(database)
        assert (overview.represented, overview.with_range, overview.without_range) == (5, 4, 1)
        units = {unit.source_code: unit.identity_count for unit in overview.territories}
        assert units["BR"] == 1
        assert units["AR"] == 1
        assert units["IT"] == 2
        basil = native_ranges.selected(database, UUID(records["identity:Ocimum basilicum"]))
        assert basil is not None
        assert {row.source_code for row in basil.ranges} == {"005", "BR"}
        aloe = native_ranges.selected(database, UUID(records["identity:Aloe vera"]))
        assert aloe is not None
        assert {row.source_code for row in aloe.ranges} == {"IT", "TH"}
        lavender = native_ranges.selected(
            database, UUID(records["identity:Lavandula angustifolia"])
        )
        assert lavender is not None
        assert any(row.place_kind == "custom" for row in lavender.ranges)
        assert {row.source_code for row in lavender.territories} == {"IT"}
        sage = native_ranges.selected(database, UUID(records["identity:Salvia officinalis"]))
        assert sage is not None
        assert sage.total == 0


def test_native_range_category_and_selection_fixture() -> None:
    from uuid import UUID

    from florabase.explore import native_ranges
    from florabase.explore.schemas import CollectionRecordCategory as Category

    with Session(get_engine()) as database:
        manifest = read_manifest(require_identity(get_settings(), database))
        assert manifest is not None
        ids = [
            UUID(manifest["records"]["identity:" + name])
            for name in ("Aloe vera", "Ocimum basilicum", "Lavandula angustifolia")
        ]
        selected = native_ranges.selection(database, ids)
        assert len(selected.identities) == 3
        assert not selected.missing_ids
        coverage = {unit.source_code: unit for unit in selected.territories}
        assert coverage["IT"].identity_count == 2
        assert coverage["BR"].identity_ids == [ids[1]]
        plants = native_ranges.list_identities(database, record=[Category.PLANT])
        assert {item.id for item in plants.items} == set(ids[:2])
        seeds = native_ranges.list_identities(database, record=[Category.SEED_LOT])
        both = native_ranges.list_identities(database, record=[Category.PLANT, Category.SEED_LOT])
        assert {item.id for item in both.items} == {item.id for item in plants.items} | {
            item.id for item in seeds.items
        }
        stored = native_ranges.list_identities(database, record=[Category.STORED_MATERIAL])
        assert [item.id for item in stored.items] == [ids[1]]
        assert (
            native_ranges.list_identities(
                database, scope="living", record=[Category.SEED_LOT]
            ).total
            == 0
        )


def test_additive_stored_fixture_preserves_existing_operator_inventory_and_is_idempotent(
    tmp_path: Path,
) -> None:
    from types import SimpleNamespace
    from unittest.mock import MagicMock
    from uuid import uuid7

    from uat_fixture import ensure_stored_material

    inventory = SimpleNamespace(id=uuid7(), state="depleted", quantity_value=None)
    manifest = {"version": 4, "state": "ready", "records": {"item:basil": str(uuid7())}}
    database = MagicMock()
    database.scalar.return_value = inventory
    with patch("uat_fixture.initialize_inventory") as initialize:
        ensure_stored_material(database, tmp_path, manifest)
        ensure_stored_material(database, tmp_path, manifest)
        initialize.assert_not_called()
    assert inventory.state == "depleted"
    assert manifest["records"]["inventory:basil"] == str(inventory.id)
    assert database.scalar.call_count == 1
    assert database.commit.call_count == 1
