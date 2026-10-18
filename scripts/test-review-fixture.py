"""Review fixture guards; optional read/rollback-only checks against seeded Review itself."""

import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid7

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from uat_fixture import (
    MODELS,
    FixtureError,
    read_manifest,
    require_empty_review_collection,
    require_identity,
    review_owner,
    seed,
    validate_manifest,
    write_manifest,
)

from florabase.core.config import Settings, get_settings
from florabase.db.session import get_engine
from florabase.geographic_places.model import GeographicPlace
from florabase.seed_lots.model import SeedLot


@pytest.fixture
def review_environment(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("FLORABASE_WORKFLOW_MODE", "review")
    monkeypatch.setenv("FLORABASE_REVIEW_PROJECT", "florabase-feature-review")
    monkeypatch.setenv("FLORABASE_REVIEW_SOURCE", "/candidate/worktree")
    return get_settings().model_copy(
        update={
            "database_url": "postgresql+psycopg://florabase_review:unused@db:5432/florabase_review",
            "canonical_origin": "http://localhost:15174",
            "attachment_storage_root": Path("/var/lib/florabase/attachments"),
        }
    )


def test_review_runtime_accepts_exact_marker_and_connected_database(
    review_environment: Settings,
) -> None:
    database = MagicMock()
    database.execute.return_value.one.return_value = ("florabase_review", "florabase_review")
    marker = json.dumps(
        {
            "project": "florabase-feature-review",
            "source": "/candidate/worktree",
            "database": "florabase_review",
            "origin": "http://localhost:15174",
        }
    )
    with (
        patch("uat_fixture.Path.exists", return_value=False),
        patch("uat_fixture.Path.is_file", return_value=True),
        patch("uat_fixture.Path.read_text", return_value=marker),
    ):
        assert (
            require_identity(review_environment, database)
            == review_environment.attachment_storage_root
        )


@pytest.mark.parametrize(
    "key,value",
    [
        ("FLORABASE_WORKFLOW_MODE", "uat"),
        ("FLORABASE_WORKFLOW_MODE", "dev"),
        ("FLORABASE_WORKFLOW_MODE", "production"),
        ("FLORABASE_REVIEW_PROJECT", "florabase-uat-preview"),
        ("FLORABASE_REVIEW_PROJECT", "florabase"),
        ("FLORABASE_REVIEW_PROJECT", "florabase-preview"),
        ("FLORABASE_REVIEW_PROJECT", "florabase-prod"),
        ("FLORABASE_REVIEW_PROJECT", "unknown"),
        ("FLORABASE_REVIEW_SOURCE", "relative"),
    ],
)
def test_review_runtime_refuses_wrong_role_project_source_before_db(
    review_environment: Settings,
    key: str,
    value: str,
) -> None:
    database = MagicMock()
    with (
        patch.dict(os.environ, {key: value}),
        pytest.raises(FixtureError, match="identity refused"),
    ):
        require_identity(review_environment, database)
    database.execute.assert_not_called()


@pytest.mark.parametrize(
    "field,value",
    [
        ("database_url", "postgresql+psycopg://florabase_uat:unused@db:5432/florabase_uat"),
        (
            "database_url",
            "postgresql+psycopg://florabase_review:unused@foreign:5432/florabase_review",
        ),
        ("environment", "production"),
        ("canonical_origin", "http://localhost:5173"),
        ("attachment_storage_root", Path("/tmp/not-review")),
    ],
)
def test_review_runtime_refuses_wrong_configuration(
    review_environment: Settings,
    field: str,
    value: object,
) -> None:
    database = MagicMock()
    with pytest.raises(FixtureError, match="identity refused"):
        require_identity(review_environment.model_copy(update={field: value}), database)
    database.execute.assert_not_called()


def test_review_runtime_requires_own_marker_and_actual_database(
    review_environment: Settings,
) -> None:
    database = MagicMock()
    marker = json.dumps(
        {
            "project": "florabase-feature-review",
            "source": "/candidate/worktree",
            "database": "florabase_review",
            "origin": "http://localhost:15174",
        }
    )
    with patch("uat_fixture.Path.exists", return_value=False):
        with (
            patch("uat_fixture.Path.is_file", return_value=False),
            pytest.raises(FixtureError, match="resource marker"),
        ):
            require_identity(review_environment, database)
        for content in (marker.replace("/candidate/worktree", "/foreign/worktree"), marker):
            database.execute.return_value.one.return_value = ("florabase_uat", "florabase_uat")
            with (
                patch("uat_fixture.Path.is_file", return_value=True),
                patch("uat_fixture.Path.read_text", return_value=content),
                pytest.raises(FixtureError),
            ):
                require_identity(review_environment, database)
    with (
        patch("uat_fixture.Path.exists", return_value=True),
        pytest.raises(FixtureError, match="UAT bookkeeping"),
    ):
        require_identity(review_environment, database)


def test_review_bookkeeping_never_reads_or_writes_uat_state(
    review_environment: Settings, tmp_path: Path
) -> None:
    uat = tmp_path / ".uat-fixture.json"
    uat.write_text("UAT sentinel")
    manifest = {"version": 4, "state": "ready", "records": {}}
    assert read_manifest(tmp_path) is None
    write_manifest(tmp_path, manifest)
    assert read_manifest(tmp_path) == manifest
    assert uat.read_text() == "UAT sentinel"
    assert not (tmp_path / ".uat-fixture.tmp").exists()
    for invalid in (
        {"version": 4, "state": "building", "records": {}},
        {"version": 99, "state": "ready", "records": {}},
    ):
        (tmp_path / ".review-fixture.json").write_text(json.dumps(invalid))
        with pytest.raises(FixtureError, match="inspect Review state"):
            read_manifest(tmp_path)


def test_review_owner_requires_exactly_one_enabled_account(review_environment: Settings) -> None:
    database = MagicMock()
    for owners in (
        [],
        [SimpleNamespace(owner=False, enabled=True)],
        [SimpleNamespace(owner=True, enabled=False)],
        [object(), object()],
    ):
        database.scalars.return_value = owners
        with pytest.raises(FixtureError, match="exactly one enabled owner"):
            review_owner(database)
    owner = SimpleNamespace(id=uuid7(), owner=True, enabled=True, password_hash="unchanged")
    database.scalars.return_value = [owner]
    assert review_owner(database) is owner
    assert owner.password_hash == "unchanged"


def test_review_refuses_unrecognized_collection_without_replacing_owner(
    review_environment: Settings, tmp_path: Path
) -> None:
    database = MagicMock()
    database.scalars.return_value = [SimpleNamespace(id=uuid7(), owner=True, enabled=True)]
    database.scalar.return_value = uuid7()
    with (
        patch("uat_fixture.bootstrap_owner") as bootstrap,
        pytest.raises(FixtureError, match="Unrecognized populated Review"),
    ):
        seed(database, tmp_path)
    bootstrap.assert_not_called()
    database.commit.assert_not_called()
    assert not (tmp_path / ".review-fixture.json").exists()


def test_review_empty_baseline_allows_migrated_canonical_geography_but_refuses_custom() -> None:
    database = MagicMock()

    def canonical_references(query: object) -> object:
        sql = str(query)
        if "FROM geographic_places" in sql and "geographic_places.place_kind =" not in sql:
            return GeographicPlace(name="Canonical reference", place_kind="canonical")
        return None

    database.scalar.side_effect = canonical_references
    require_empty_review_collection(database)

    def custom_geography(query: object) -> object:
        if "FROM geographic_places" in str(query):
            return GeographicPlace(name="Operator custom place", place_kind="custom")
        return None

    database.scalar.side_effect = custom_geography
    with pytest.raises(FixtureError, match="Unrecognized populated Review"):
        require_empty_review_collection(database)


@pytest.mark.skipif(
    os.environ.get("REVIEW_FIXTURE_LIVE_TEST") != "1",
    reason="requires explicitly seeded, guarded Review",
)
def test_live_review_repeat_seed_preserves_owner_records_media_and_operator_edits() -> None:
    with Session(get_engine()) as database:
        root = require_identity(get_settings(), database)
        manifest = read_manifest(root)
        assert manifest is not None
        validate_manifest(database, root, manifest)
        assert len(manifest["records"]) in {66, 68, 80, 82}
        assert all(
            manifest.get(key) == 1
            for key in (
                "schedule_extension",
                "schedule_calendar_extension",
                "dashboard_extension",
                "manual_review_extension",
            )
        )
        assert "inventory:basil" in manifest["records"]
        owner = review_owner(database)
        credentials = (owner.id, owner.login_name, owner.password_hash, owner.password_changed_at)
        before = {
            key: database.scalar(select(func.count()).select_from(model))
            for key, model in MODELS.items()
        }
        files = {
            path.relative_to(root): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file() and not path.name.endswith(".lock")
        }
        packet = database.scalar(select(SeedLot).limit(1))
        assert packet is not None
        packet.notes = "Rollback-only operator edit preservation probe"
        database.flush()
        assert seed(database, root) == manifest
        assert seed(database, root) == manifest
        assert packet.notes == "Rollback-only operator edit preservation probe"
        assert (
            owner.id,
            owner.login_name,
            owner.password_hash,
            owner.password_changed_at,
        ) == credentials
        assert {
            key: database.scalar(select(func.count()).select_from(model))
            for key, model in MODELS.items()
        } == before
        assert {
            path.relative_to(root): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file() and not path.name.endswith(".lock")
        } == files
        assert not (root / ".uat-identity.json").exists()
        assert not (root / ".uat-fixture.json").exists()
        database.rollback()


def test_collection_visual_extension_never_runs_in_uat(tmp_path: Path) -> None:
    from uat_fixture import ensure_collection_visual

    manifest = {"state": "ready", "records": {}}
    with (
        patch("uat_fixture.fixture_prefix", return_value="uat"),
        patch("uat_fixture.harvests.write_harvest") as create,
    ):
        ensure_collection_visual(MagicMock(), tmp_path, manifest)
    create.assert_not_called()
    assert manifest == {"state": "ready", "records": {}}


def test_collection_visual_extension_preserves_repeated_review_seed(tmp_path: Path) -> None:
    from uat_fixture import ensure_collection_visual

    manifest = {"state": "ready", "collection_visual_extension": 1, "records": {}}
    with (
        patch("uat_fixture.fixture_prefix", return_value="review"),
        patch("uat_fixture.harvests.write_harvest") as create,
    ):
        ensure_collection_visual(MagicMock(), tmp_path, manifest)
    create.assert_not_called()
    assert manifest["state"] == "ready"
