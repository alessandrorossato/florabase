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
        expected_ids = {
            UUID(records["identity:" + name])
            for name in (
                "Ocimum basilicum",
                "Lavandula angustifolia",
                "Aloe vera",
                "Raphanus sativus",
                "Salvia officinalis",
            )
        } | {UUID(records["identity:genovese"])}
        if "identity:Ocimum tenuiflorum" in records:
            expected_ids.add(UUID(records["identity:Ocimum tenuiflorum"]))
        assert all_ids == expected_ids
        assert {row.scientific_name for row in list_identities(database, scope="living").items} == {
            "Ocimum basilicum",
            "Aloe vera",
        }
        current_names = {
            row.scientific_name for row in list_identities(database, scope="current").items
        }
        expected_names = {
            "Ocimum basilicum",
            "Aloe vera",
            "Lavandula angustifolia",
            "Salvia officinalis",
        }
        if "identity:Ocimum tenuiflorum" in records:
            expected_names.add("Ocimum tenuiflorum")
        assert current_names == expected_names
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
        optional_holy = int("identity:Ocimum tenuiflorum" in records)
        assert (overview.represented, overview.with_range, overview.without_range) == (
            6 + optional_holy,
            4,
            2 + optional_holy,
        )
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


def test_dashboard_extension_is_idempotent_and_keeps_operator_edits() -> None:
    from uuid import UUID

    from uat_fixture import ensure_dashboard

    from florabase.collection_views.service import dashboard
    from florabase.seed_lots.model import SeedLot
    from florabase.sowings.model import Sowing

    with Session(get_engine()) as database:
        root = require_identity(get_settings(), database)
        manifest = read_manifest(root)
        assert manifest is not None
        assert manifest["dashboard_extension"] == 1
        lot = database.get(SeedLot, UUID(manifest["records"]["seed:dashboard_unlinked"]))
        sowing = database.get(Sowing, UUID(manifest["records"]["sowing:dashboard_unknown"]))
        assert lot is not None
        assert sowing is not None
        assert lot.order_id is None
        assert sowing.germinated_count is None
        result = dashboard(database).overview
        assert result.purchase_packets_without_order >= 1
        assert result.sowings_unknown_germination >= 1
        assert result.sowings_zero_germination >= 1
        lot.notes = "Operator edit"
        sowing.germinated_count = 2
        database.flush()
        with patch("uat_fixture.seeds.create_seed_lot") as create:
            ensure_dashboard(database, root, manifest)
            create.assert_not_called()
        assert lot.notes == "Operator edit"
        assert sowing.germinated_count == 2
        database.rollback()


def test_manual_review_and_schedule_fixture_coverage_preserves_operator_edits() -> None:
    from collections import Counter
    from datetime import timedelta
    from uuid import UUID

    from sqlalchemy import select
    from uat_fixture import seed

    from florabase.botanical_identities.model import BotanicalIdentity
    from florabase.botanical_profiles.model import BotanicalProfile
    from florabase.schedule.model import TARGETS, ScheduledActivity
    from florabase.seed_lots.model import SeedLot

    with Session(get_engine()) as database:
        root = require_identity(get_settings(), database)
        manifest = read_manifest(root)
        assert manifest is not None and manifest["manual_review_extension"] == 1
        records = manifest["records"]
        cultivar = database.get(BotanicalIdentity, UUID(records["identity:genovese"]))
        assert cultivar is not None and cultivar.cultivar_name == "Genovese"
        profile = database.scalar(
            select(BotanicalProfile).where(BotanicalProfile.botanical_identity_id == cultivar.id)
        )
        assert profile is not None and "Synthetic UAT" in (profile.description or "")
        packet = database.get(SeedLot, UUID(records["seed:genovese"]))
        assert packet is not None and packet.quantity_value is None
        assert packet.order_id == UUID(records["order:partial"])
        activities = list(database.scalars(select(ScheduledActivity)))
        assert len(activities) == 19
        assert Counter(a.status for a in activities) == {
            "planned": 16,
            "completed": 2,
            "cancelled": 1,
        }
        anchor = database.get(ScheduledActivity, UUID(records["schedule:today"]))
        overdue = database.get(ScheduledActivity, UUID(records["schedule:overdue"]))
        collection = database.get(ScheduledActivity, UUID(records["schedule:collection"]))
        assert anchor is not None and overdue is not None and collection is not None
        assert overdue.due_on == anchor.due_on - timedelta(days=3) and overdue.status == "planned"
        assert sum(a.due_on == anchor.due_on and a.status == "planned" for a in activities) == 7
        assert any(
            a.due_on.month != anchor.due_on.month and a.due_on > anchor.due_on for a in activities
        )
        assert all(
            any(getattr(a, f"{kind}_id") is not None for a in activities) for kind in TARGETS
        )
        assert all(getattr(collection, f"{kind}_id") is None for kind in TARGETS)
        original = {a.id: (a.due_on, a.status, a.version) for a in activities}
        collection.title = "Operator-edited collection review"
        collection.due_on += timedelta(days=20)
        packet.notes = "Operator-edited packet"
        database.flush()
        with patch("uat_fixture.schedule.create") as create:
            assert seed(database, root) == manifest
            assert seed(database, root) == manifest
            create.assert_not_called()
        assert packet.notes == "Operator-edited packet"
        assert collection.title == "Operator-edited collection review"
        assert collection.due_on == original[collection.id][0] + timedelta(days=20)
        assert {
            a.id: (a.due_on, a.status, a.version) for a in activities if a.id != collection.id
        } == {key: value for key, value in original.items() if key != collection.id}
        database.rollback()
