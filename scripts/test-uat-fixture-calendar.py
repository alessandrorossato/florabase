"""Focused additive Calendar fixture contract; no database/environment reset."""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session
from uat_fixture import (
    VERSION,
    FixtureError,
    ensure_manual_review,
    ensure_schedule,
    ensure_schedule_calendar,
    read_manifest,
    write_manifest,
)


def test_calendar_extension_is_additive_and_idempotent(tmp_path: Path) -> None:
    refs = ("plant:direct", "group:basil", "seed:0", "location:Greenhouse bench", "sowing:basil")
    original = {ref: str(uuid4()) for ref in refs}
    original["schedule:today"] = str(uuid4())
    manifest = {
        "version": VERSION,
        "state": "ready",
        "records": dict(original),
        "schedule_extension": 1,
    }
    db = MagicMock()
    with patch(
        "uat_fixture.schedule.create", side_effect=lambda *_args: SimpleNamespace(id=uuid4())
    ) as create:
        ensure_schedule_calendar(db, tmp_path, manifest)
        assert create.call_count == 7
        days = [call.args[1].due_on for call in create.call_args_list]
        today = datetime.now(UTC).date()
        assert days[:5] == [today] * 5
        assert days[5].month == today.month and days[5] >= today
        assert days[6] > days[5] and days[6].day == 5
        kinds = {call.args[1].target.kind for call in create.call_args_list}
        assert len(kinds) == 5
        assert manifest["schedule_calendar_extension"] == 1
        assert all(manifest["records"][key] == value for key, value in original.items())
        ensure_schedule_calendar(db, tmp_path, manifest)
        assert create.call_count == 7
        db.commit.assert_called_once()
        assert read_manifest(tmp_path) == manifest


def test_v4_manual_review_upgrade_is_additive_and_preserves_prior_ids(tmp_path: Path) -> None:
    original = {
        key: str(uuid4())
        for key in ("order:partial", "location:Indoor seed shelf", "schedule:today")
    }
    manifest = {"version": VERSION, "state": "ready", "records": dict(original)}
    db = MagicMock()
    cultivar, packet, activity = [SimpleNamespace(id=uuid4()) for _ in range(3)]
    with (
        patch(
            "uat_fixture.identities.create_botanical_identity", return_value=cultivar
        ) as create_identity,
        patch("uat_fixture.put_botanical_profile") as profile,
        patch("uat_fixture.seeds.create_seed_lot", return_value=packet) as create_seed,
        patch("uat_fixture.schedule.create", return_value=activity) as create_activity,
    ):
        ensure_manual_review(db, tmp_path, manifest)
        ensure_manual_review(db, tmp_path, manifest)
        create_identity.assert_called_once()
        assert create_identity.call_args.args[1].cultivar_name == "Genovese"
        profile.assert_called_once()
        assert "Synthetic UAT" in profile.call_args.args[2].description
        create_seed.assert_called_once()
        assert str(create_seed.call_args.args[1].order_id) == original["order:partial"]
        assert create_seed.call_args.args[1].quantity is None
        create_activity.assert_called_once()
        assert create_activity.call_args.args[1].target is None
        assert create_activity.call_args.args[1].due_on == datetime.now(UTC).date()
        db.commit.assert_called_once()
    assert all(manifest["records"][key] == value for key, value in original.items())
    assert manifest["version"] == 4 and manifest["manual_review_extension"] == 1
    assert read_manifest(tmp_path) == manifest


def test_interrupted_manual_upgrade_stays_building_and_requires_explicit_reset(
    tmp_path: Path,
) -> None:
    import pytest
    from uat_fixture import FixtureError

    manifest = {"version": VERSION, "state": "ready", "records": {}}
    with patch(
        "uat_fixture.identities.create_botanical_identity", side_effect=RuntimeError("interrupted")
    ):
        with pytest.raises(RuntimeError, match="interrupted"):
            ensure_manual_review(MagicMock(), tmp_path, manifest)
    with pytest.raises(FixtureError, match="guarded uat-preview-reset"):
        read_manifest(tmp_path)


@pytest.mark.parametrize("extend", [ensure_schedule, ensure_schedule_calendar])
def test_schedule_commit_before_marker_failure_cannot_be_silently_reseeded(
    tmp_path: Path, extend: Callable[[Session, Path, dict[str, Any]], None]
) -> None:
    refs = (
        "plant:direct",
        "plant:derived",
        "group:basil",
        "seed:0",
        "location:Greenhouse bench",
        "sowing:basil",
        "identity:Ocimum basilicum",
    )
    manifest = {
        "version": VERSION,
        "state": "ready",
        "records": {ref: str(uuid4()) for ref in refs},
    }
    db = MagicMock()

    def interrupted_write(root: Path, value: dict[str, Any]) -> None:
        if value["state"] == "ready":
            raise OSError("interrupted after commit")
        write_manifest(root, value)

    with (
        patch(
            "uat_fixture.schedule.create", side_effect=lambda *_args: SimpleNamespace(id=uuid4())
        ),
        patch("uat_fixture.schedule.complete"),
        patch("uat_fixture.schedule.cancel"),
        patch("uat_fixture.write_manifest", side_effect=interrupted_write),
    ):
        with pytest.raises(OSError, match="interrupted after commit"):
            extend(db, tmp_path, manifest)
    db.commit.assert_called_once()
    with pytest.raises(FixtureError, match="guarded uat-preview-reset"):
        read_manifest(tmp_path)
