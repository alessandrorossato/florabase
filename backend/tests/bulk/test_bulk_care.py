"""Unit tests for bulk care logging schemas, service, and API (CARE-BULK-001 + FN-03)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4, uuid7

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from florabase.auth.dependencies import AuthenticatedActor
from florabase.auth.model import AuthSession
from florabase.bulk import care_api, care_service
from florabase.bulk.care_schemas import (
    MAX_BULK_CARE_TARGETS,
    BulkCareApplyRequest,
    BulkCareApplyResponse,
    BulkCareLocationTargets,
    BulkCarePreviewRequest,
    BulkCareRecordReference,
    BulkCareRecordTargets,
    BulkCareUndoResponse,
)
from florabase.events.model import Event, EventKind
from florabase.events.schemas import EventCreate
from florabase.events.service import EventDomainConflictError
from florabase.locations.model import Location
from florabase.plants.model import Plant, PlantGroup
from florabase.plants.schemas import RetainedObservation
from florabase.plants.service import _RETAINABLE_OBSERVATION_KINDS
from florabase.propagation.reversal import RETAINABLE
from florabase.seed_lots.schemas import PartialDate


def _actor(*, owner: bool = True) -> AuthenticatedActor:
    return AuthenticatedActor(
        user_id=uuid4(),
        login_name="owner" if owner else "viewer",
        display_name="Owner" if owner else "Viewer",
        owner=owner,
        session=AuthSession(id=uuid4(), token_digest=b"c" * 32),
    )


class _FakeDatabase:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.flushed = False
        self.deleted: list[object] = []
        self._locations: dict[UUID, Location] = {}
        self._events: list[Event] = []

    def get(self, model: object, key: UUID, **_kwargs: object) -> object:
        if model is Location:
            return self._locations.get(key)
        return None

    def scalars(self, _stmt: object) -> list[object]:
        return list(self._events)

    def delete(self, obj: object) -> None:
        self.deleted.append(obj)

    def flush(self) -> None:
        self.flushed = True

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


def _session(db: _FakeDatabase) -> Session:
    return cast(Session, db)


def test_bulk_care_allowed_and_disallowed_kinds_and_validation() -> None:
    target = BulkCareRecordTargets(records=[BulkCareRecordReference(kind="plant", id=uuid7())])
    for kind in (
        "watering",
        "feeding",
        "treatment",
        "repotting",
        "pruning",
        "observation",
        "other",
    ):
        req = BulkCarePreviewRequest.model_validate(
            {
                "targets": target.model_dump(),
                "kind": kind,
                "occurred_on": {"precision": "day", "year": 2026, "month": 11, "day": 25},
                "notes": "  2 ml/L NPK  ",
            }
        )
        assert req.kind == kind
        assert req.notes == "2 ml/L NPK"

    for disallowed in (
        "movement",
        "measurement",
        "flowering",
        "fruiting",
        "harvest",
        "extraction",
        "reintegration",
        "transfer",
        "death",
        "loss",
        "discarded",
    ):
        with pytest.raises(ValidationError):
            BulkCarePreviewRequest.model_validate(
                {"targets": target.model_dump(), "kind": disallowed}
            )

    # Single-entry EventCreate allows watering and feeding too (FN-03).
    assert EventCreate(kind=EventKind.WATERING).kind == EventKind.WATERING
    assert EventCreate(kind=EventKind.FEEDING).kind == EventKind.FEEDING

    # Reversal & reintegration retainable sets include watering/feeding (not treatment/repotting).
    assert {"watering", "feeding"} <= RETAINABLE
    assert {"watering", "feeding"} <= _RETAINABLE_OBSERVATION_KINDS
    for blocking in ("treatment", "repotting", "pruning"):
        assert blocking not in RETAINABLE
        assert blocking not in _RETAINABLE_OBSERVATION_KINDS
    assert (
        RetainedObservation(id=uuid7(), kind="watering", occurred_on=None, notes=None).kind
        == "watering"
    )
    assert (
        RetainedObservation(id=uuid7(), kind="feeding", occurred_on=None, notes=None).kind
        == "feeding"
    )

    # Duplicate records rejected; > 500 records rejected; empty records rejected.
    dup = uuid7()
    with pytest.raises(ValidationError, match="Duplicate"):
        BulkCareRecordTargets(
            records=[
                BulkCareRecordReference(kind="plant", id=dup),
                BulkCareRecordReference(kind="plant", id=dup),
            ]
        )
    with pytest.raises(ValidationError):
        BulkCareRecordTargets(records=[])
    with pytest.raises(ValidationError):
        BulkCareRecordTargets(
            records=[
                BulkCareRecordReference(kind="plant", id=uuid7())
                for _ in range(MAX_BULK_CARE_TARGETS + 1)
            ]
        )


def test_bulk_care_service_selection_location_stale_cap_and_undo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 11, 25, 10, 0, tzinfo=UTC)
    loc_root = Location(id=uuid7(), name="Greenhouse", parent_id=None, updated_at=now)
    loc_bench = Location(id=uuid7(), name="Bench 2", parent_id=loc_root.id, updated_at=now)
    p1 = Plant(
        id=uuid7(), label="Hoya 1", lifecycle="active", location_id=loc_bench.id, updated_at=now
    )
    p2 = Plant(
        id=uuid7(), label="Hoya dead", lifecycle="dead", location_id=loc_bench.id, updated_at=now
    )
    g1 = PlantGroup(
        id=uuid7(), label="Tray A", lifecycle="active", location_id=loc_bench.id, updated_at=now
    )
    missing_id = uuid7()

    db = _FakeDatabase()
    db._locations[loc_root.id] = loc_root
    db._locations[loc_bench.id] = loc_bench

    monkeypatch.setattr(care_service, "list_locations", lambda _db: [loc_root, loc_bench])
    monkeypatch.setattr(
        care_service,
        "_fetch_records_by_refs",
        lambda _db, _refs, *, lock: {
            ("plant", p1.id): (p1, "Hoya carnosa"),
            ("plant", p2.id): (p2, "Hoya kerrii"),
            ("plant_group", g1.id): (g1, "Lithops lesliei"),
        },
    )

    req = BulkCarePreviewRequest(
        targets=BulkCareRecordTargets(
            records=[
                BulkCareRecordReference(kind="plant", id=p1.id),
                BulkCareRecordReference(kind="plant", id=p2.id),
                BulkCareRecordReference(kind="plant_group", id=g1.id),
                BulkCareRecordReference(kind="plant", id=missing_id),
            ]
        ),
        kind="watering",
        occurred_on=PartialDate.model_validate(
            {"precision": "day", "year": 2026, "month": 11, "day": 25}
        ),
        notes="Rainwater",
    )
    preview = care_service.preview_bulk_care(_session(db), req)
    assert preview.total_count == 4
    assert preview.log_count == 2
    assert preview.plant_count == 1
    assert preview.plant_group_count == 1
    assert preview.skipped_count == 2
    assert preview.can_apply is True
    assert any(
        row.id == p2.id and row.status == "skipped" and row.reason == "Inactive (dead)"
        for row in preview.rows
    )
    assert any(row.id == missing_id and row.status == "skipped" for row in preview.rows)

    # Apply with matching signature creates events sharing one batch_id.
    created_calls: list[tuple[str, UUID, UUID | None]] = []

    def fake_create_event(
        _db: Session,
        target_type: str,
        target_id: UUID,
        _payload: EventCreate,
        *,
        batch_id: UUID | None = None,
    ) -> Event:
        created_calls.append((target_type, target_id, batch_id))
        return Event(id=uuid7(), kind="watering", batch_id=batch_id, created_at=now, updated_at=now)

    monkeypatch.setattr(care_service, "create_event", fake_create_event)
    applied = care_service.apply_bulk_care(
        _session(db),
        BulkCareApplyRequest(
            targets=req.targets,
            kind=req.kind,
            occurred_on=req.occurred_on,
            notes=req.notes,
            target_signature=preview.target_signature,
        ),
    )
    assert applied.logged_count == 2
    assert applied.plant_count == 1
    assert applied.plant_group_count == 1
    assert applied.skipped_count == 2
    assert len(created_calls) == 2
    assert all(call[2] == applied.batch_id for call in created_calls)

    # Stale signature -> stale_preview error.
    with pytest.raises(care_service.BulkCareError) as stale:
        care_service.apply_bulk_care(
            _session(db),
            BulkCareApplyRequest(
                targets=req.targets,
                kind=req.kind,
                occurred_on=req.occurred_on,
                notes=req.notes,
                target_signature="0" * 64,
            ),
        )
    assert stale.value.code == "stale_preview"

    # Location not found -> 404 code.
    with pytest.raises(care_service.BulkCareError) as missing_loc:
        care_service.preview_bulk_care(
            _session(db),
            BulkCarePreviewRequest(
                targets=BulkCareLocationTargets(location_id=uuid7(), include_sublocations=True),
                kind="feeding",
            ),
        )
    assert missing_loc.value.code == "location_not_found"

    # Location subtree with > 500 records rejected.
    monkeypatch.setattr(
        care_service, "_subtree_location_ids", lambda _db, _lid, _inc: [loc_root.id, loc_bench.id]
    )
    monkeypatch.setattr(
        db,
        "scalars",
        lambda _stmt: [loc_root, loc_bench],
    )
    monkeypatch.setattr(
        care_service,
        "_fetch_records_in_locations",
        lambda _db, _ids, *, lock: [
            ("plant", p1, "Hoya carnosa") for _ in range(MAX_BULK_CARE_TARGETS + 1)
        ],
    )
    with pytest.raises(care_service.BulkCareError) as too_many:
        care_service.preview_bulk_care(
            _session(db),
            BulkCarePreviewRequest(
                targets=BulkCareLocationTargets(location_id=loc_root.id, include_sublocations=True),
                kind="feeding",
            ),
        )
    assert too_many.value.code == "too_many_targets"

    # Empty location -> can_apply=False and apply -> nothing_to_log.
    monkeypatch.setattr(care_service, "_fetch_records_in_locations", lambda _db, _ids, *, lock: [])
    empty_preview = care_service.preview_bulk_care(
        _session(db),
        BulkCarePreviewRequest(
            targets=BulkCareLocationTargets(location_id=loc_root.id, include_sublocations=True),
            kind="feeding",
        ),
    )
    assert empty_preview.can_apply is False
    assert empty_preview.sublocation_count == 1
    with pytest.raises(care_service.BulkCareError) as empty_apply:
        care_service.apply_bulk_care(
            _session(db),
            BulkCareApplyRequest(
                targets=BulkCareLocationTargets(location_id=loc_root.id, include_sublocations=True),
                kind="feeding",
                target_signature=empty_preview.target_signature,
            ),
        )
    assert empty_apply.value.code == "nothing_to_log"

    # Undo: deletes unedited unguarded events, keeps edited and guarded ones, 404 on unknown batch.
    batch_id = uuid7()
    ev_unedited = Event(
        id=uuid7(),
        plant_id=p1.id,
        kind="watering",
        batch_id=batch_id,
        created_at=now,
        updated_at=now,
    )
    ev_edited = Event(
        id=uuid7(),
        plant_group_id=g1.id,
        kind="watering",
        batch_id=batch_id,
        created_at=now,
        updated_at=now + timedelta(seconds=5),
    )
    ev_photo = Event(
        id=uuid7(),
        plant_id=p1.id,
        kind="watering",
        batch_id=batch_id,
        created_at=now,
        updated_at=now,
    )
    ev_schedule = Event(
        id=uuid7(),
        plant_id=p1.id,
        kind="watering",
        batch_id=batch_id,
        created_at=now,
        updated_at=now,
    )
    ev_operation = Event(
        id=uuid7(),
        plant_id=p1.id,
        kind="watering",
        batch_id=batch_id,
        created_at=now,
        updated_at=now,
    )
    ev_harvest = Event(
        id=uuid7(),
        plant_id=p1.id,
        kind="watering",
        batch_id=batch_id,
        created_at=now,
        updated_at=now,
    )
    conflict_by_id = {
        ev_photo.id: EventDomainConflictError("event_has_photos", "has photo"),
        ev_schedule.id: EventDomainConflictError("event_retained_by_schedule", "schedule"),
        ev_operation.id: EventDomainConflictError("operation_event_requires_undo", "op"),
        ev_harvest.id: EventDomainConflictError("harvest_event_owned", "harvest"),
    }

    def fake_delete_event(session: Session, event: Event) -> None:
        if event.id in conflict_by_id:
            raise conflict_by_id[event.id]
        session.delete(event)

    monkeypatch.setattr(care_service, "delete_event", fake_delete_event)
    monkeypatch.setattr(
        db,
        "scalars",
        lambda _stmt: [ev_unedited, ev_edited, ev_photo, ev_schedule, ev_operation, ev_harvest],
    )
    undone = care_service.undo_bulk_care(_session(db), batch_id)
    assert undone.deleted_count == 1
    assert undone.kept_count == 5
    assert [(item.id, item.reason) for item in undone.kept] == [
        (ev_edited.id, "edited"),
        (ev_photo.id, "has_photos"),
        (ev_schedule.id, "linked_to_schedule"),
        (ev_operation.id, "operation_owned"),
        (ev_harvest.id, "harvest_owned"),
    ]
    assert undone.kept[0].target_kind == "plant_group"
    assert db.deleted == [ev_unedited]

    # Unexpected delete_event conflict fails closed instead of silently keeping.
    ev_unknown = Event(
        id=uuid7(),
        plant_id=p1.id,
        kind="watering",
        batch_id=batch_id,
        created_at=now,
        updated_at=now,
    )
    monkeypatch.setattr(
        care_service,
        "delete_event",
        lambda _s, _e: (_ for _ in ()).throw(EventDomainConflictError("other_conflict", "boom")),
    )
    monkeypatch.setattr(db, "scalars", lambda _stmt: [ev_unknown])
    with pytest.raises(EventDomainConflictError):
        care_service.undo_bulk_care(_session(db), batch_id)

    monkeypatch.setattr(db, "scalars", lambda _stmt: [])
    with pytest.raises(care_service.BulkCareError) as missing_batch:
        care_service.undo_bulk_care(_session(db), uuid7())
    assert missing_batch.value.code == "batch_not_found"


def test_bulk_care_api_error_mapping_and_owner_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _FakeDatabase()
    actor = _actor(owner=True)
    viewer = _actor(owner=False)
    req = BulkCarePreviewRequest(
        targets=BulkCareLocationTargets(location_id=uuid7()),
        kind="watering",
    )

    with pytest.raises(HTTPException) as non_owner:
        care_api.preview(req, _session(db), viewer)
    assert non_owner.value.status_code == 403

    # Map 404, 422, 409, domain conflict, and generic integrity error cleanly.
    for error, expected_status in (
        (care_service.BulkCareError("location_not_found", "missing"), 404),
        (care_service.BulkCareError("batch_not_found", "missing"), 404),
        (care_service.BulkCareError("nothing_to_log", "empty"), 422),
        (care_service.BulkCareError("too_many_targets", "cap"), 422),
        (care_service.BulkCareError("stale_preview", "stale"), 409),
        (EventDomainConflictError("conflict", "bad"), 409),
        (IntegrityError("stmt", {}, Exception("boom")), 409),
    ):
        exc = care_api._failure(_session(db), error)
        assert exc.status_code == expected_status
        assert db.rolled_back is True

    # Verify apply & undo endpoints commit on success and rollback on error.
    dummy_apply: Any = BulkCareApplyRequest(
        targets=req.targets, kind="watering", target_signature="a" * 64
    )
    monkeypatch.setattr(
        care_service,
        "apply_bulk_care",
        lambda _db, _p: BulkCareApplyResponse(
            batch_id=uuid7(),
            kind="watering",
            logged_count=1,
            plant_count=1,
            plant_group_count=0,
            skipped_count=0,
        ),
    )
    fresh = _FakeDatabase()
    res = care_api.apply(dummy_apply, _session(fresh), actor)
    assert res.logged_count == 1
    assert fresh.committed is True

    monkeypatch.setattr(
        care_service,
        "undo_bulk_care",
        lambda _db, bid: BulkCareUndoResponse(batch_id=bid, deleted_count=1, kept_count=0, kept=[]),
    )
    fresh_undo = _FakeDatabase()
    bid = uuid7()
    undo_res = care_api.undo(bid, _session(fresh_undo), actor)
    assert undo_res.deleted_count == 1
    assert fresh_undo.committed is True

    # Undo concurrency error uses its own message (N1), not apply's message.
    monkeypatch.setattr(
        care_service,
        "undo_bulk_care",
        lambda _db, _bid: (_ for _ in ()).throw(IntegrityError("stmt", {}, Exception("boom"))),
    )
    undo_err_db = _FakeDatabase()
    with pytest.raises(HTTPException) as undo_exc:
        care_api.undo(bid, _session(undo_err_db), actor)
    assert undo_exc.value.status_code == 409
    assert cast(Any, undo_exc.value.detail) == {
        "code": "concurrent_change",
        "message": "Undo did not complete. Refresh and try again.",
    }
    assert undo_err_db.rolled_back is True


def test_events_saved_view_accepts_care_and_preserves_existing_categories() -> None:
    from florabase.saved_views.state import SavedViewSurface, canonical_state

    assert canonical_state(SavedViewSurface.EVENTS, 1, {"category": ["care"]}) == {
        "category": ["care"]
    }
    assert canonical_state(
        SavedViewSurface.EVENTS,
        1,
        {"category": ["observations", "cultivation", "status"]},
    ) == {"category": ["observations", "cultivation", "status"]}
    assert canonical_state(
        SavedViewSurface.EVENTS,
        1,
        {"category": ["status", "care", "observations", "cultivation"]},
    ) == {"category": ["care", "observations", "cultivation", "status"]}
