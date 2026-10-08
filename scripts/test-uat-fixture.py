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
