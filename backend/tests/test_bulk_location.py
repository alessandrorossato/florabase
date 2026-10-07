from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import MagicMock
from uuid import uuid7

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from florabase.auth.dependencies import AuthenticatedActor
from florabase.bulk import api, service
from florabase.bulk.schemas import (
    BulkKind,
    BulkLocationApplyRequest,
    BulkLocationPreviewRequest,
    BulkLocationResult,
    BulkPrecondition,
    BulkReference,
)
from florabase.events.service import EventDomainConflictError, EventReferenceNotFoundError
from florabase.harvests.inventory_model import HarvestMaterialInventory as Inventory
from florabase.locations.model import Location
from florabase.sowings.model import Sowing

NOW = datetime(2026, 10, 6, tzinfo=UTC)


@pytest.mark.parametrize(
    "changes",
    [
        {"records": []},
        {"records": [{"kind": "plant", "id": "bad"}]},
        {"records": [{"kind": "harvest", "id": str(uuid7())}]},
        {"records": [{"kind": "MediaAsset", "id": str(uuid7())}]},
        {"target_location_id": "bad"},
        {"query": {"location": "Terrace"}},
        {"action": "delete"},
        {"records": [{"kind": "plant", "id": str(uuid7())} for _ in range(101)]},
    ],
)
def test_preview_rejects_malformed_or_unbounded(changes: dict[str, Any]) -> None:
    payload = {
        "records": [{"kind": "plant", "id": str(uuid7())}],
        "target_location_id": str(uuid7()),
    }
    with pytest.raises(ValidationError):
        BulkLocationPreviewRequest.model_validate(payload | changes)


@pytest.mark.parametrize("apply", [False, True])
def test_duplicate_typed_references_rejected(apply: bool) -> None:
    row = {"kind": "plant", "id": str(uuid7())}
    if apply:
        row["expected_updated_at"] = NOW.isoformat()
    payload: dict[str, Any] = {"records": [row, row], "target_location_id": str(uuid7())}
    if apply:
        payload["expected_target_updated_at"] = NOW.isoformat()
    with pytest.raises(ValidationError, match="duplicate_reference"):
        (BulkLocationApplyRequest if apply else BulkLocationPreviewRequest).model_validate(payload)


def test_apply_requires_aware_preconditions() -> None:
    with pytest.raises(ValidationError):
        BulkPrecondition(
            kind="plant",
            id=uuid7(),
            expected_updated_at=datetime.fromisoformat("2026-10-06T00:00:00"),
        )
    with pytest.raises(ValidationError):
        BulkLocationApplyRequest.model_validate(
            {"records": [{"kind": "plant", "id": str(uuid7())}], "target_location_id": str(uuid7())}
        )


def fixture(
    monkeypatch: pytest.MonkeyPatch, *, kind: str = "seed_lot", state: str = "active"
) -> tuple[MagicMock, Any, Location, BulkLocationPreviewRequest]:
    target = Location(
        id=uuid7(),
        name="Greenhouse",
        parent_id=None,
        updated_at=NOW,
        supports_seed_lots=True,
        supports_sowings=True,
        supports_plants=True,
        supports_harvest_inventory=True,
    )
    row = service.MODELS[cast(BulkKind, kind)](
        id=uuid7(),
        location_id=None,
        updated_at=NOW,
        **(
            {"state": state, "material_kind": "seed"}
            if kind == "harvest_inventory"
            else {"lifecycle": state}
        ),
    )
    db = MagicMock(spec=Session)
    db.get.return_value = target
    monkeypatch.setattr(
        service, "_records", lambda *_args, **_kwargs: {(kind, row.id): (row, "Basil")}
    )
    monkeypatch.setattr(service, "list_locations", lambda _db: [target])
    request = BulkLocationPreviewRequest(
        records=[BulkReference(kind=kind, id=row.id)], target_location_id=target.id
    )
    return db, row, target, request


@pytest.mark.parametrize("kind", list(service.MODELS))
def test_preview_and_domain_dispatch(monkeypatch: pytest.MonkeyPatch, kind: str) -> None:
    db, row, target, request = fixture(monkeypatch, kind=kind)
    result = service.preview(cast(Session, db), request)
    assert result.can_apply
    assert result.move_count == 1
    assert result.rows[0].current_location is None
    event = MagicMock()
    monkeypatch.setattr(service, "create_event", event)
    applied = service.apply(
        cast(Session, db),
        BulkLocationApplyRequest(
            records=[BulkPrecondition(kind=kind, id=row.id, expected_updated_at=NOW)],
            target_location_id=target.id,
            expected_target_updated_at=NOW,
        ),
    )
    assert applied.moved_count == 1
    if kind in {"plant", "plant_group"}:
        assert event.call_args.args[1:3] == (kind, row.id)
        assert event.call_args.args[3].kind == "movement"
        assert event.call_args.args[3].occurred_on is None
    else:
        assert row.location_id == target.id
        assert row.updated_at > NOW
    db.flush.assert_called_once()


@pytest.mark.parametrize("kind", list(service.MODELS))
def test_preview_inactive_and_scope_conflicts(monkeypatch: pytest.MonkeyPatch, kind: str) -> None:
    db, row, target, request = fixture(
        monkeypatch, kind=kind, state="depleted" if kind == "harvest_inventory" else "reversed"
    )
    result = service.preview(cast(Session, db), request)
    assert not result.can_apply
    assert result.rows[0].code == "record_not_active"
    if isinstance(row, Inventory):
        row.state = "active"
    else:
        row.lifecycle = "active"
    setattr(target, "supports_" + service.SCOPES[cast(BulkKind, kind)].value, False)
    result = service.preview(cast(Session, db), request)
    assert result.rows[0].code == "location_scope_not_supported"


@pytest.mark.parametrize("change", ["record", "target", "inactive", "missing", "noop"])
def test_apply_refuses_without_mutation(monkeypatch: pytest.MonkeyPatch, change: str) -> None:
    db, row, target, request = fixture(monkeypatch)
    payload = BulkLocationApplyRequest(
        records=[BulkPrecondition(kind="seed_lot", id=row.id, expected_updated_at=NOW)],
        target_location_id=target.id,
        expected_target_updated_at=NOW,
    )
    if change == "record":
        row.updated_at = NOW + timedelta(seconds=1)
    elif change == "target":
        target.updated_at = NOW + timedelta(seconds=1)
    elif change == "inactive":
        row.lifecycle = "exhausted"
    elif change == "missing":
        monkeypatch.setattr(service, "_records", lambda *_args, **_kwargs: {})
    else:
        row.location_id = target.id
        result = service.preview(cast(Session, db), request)
        assert result.unchanged_count == 1
        assert not result.can_apply
        assert result.rows[0].current_location == "Greenhouse"
    before = row.location_id
    with pytest.raises(service.BulkConflictError):
        service.apply(cast(Session, db), payload)
    assert row.location_id == before
    db.flush.assert_not_called()


def test_target_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    db, _row, _target, payload = fixture(monkeypatch)
    db.get.return_value = None
    with pytest.raises(service.BulkConflictError, match="target_location_not_found"):
        service.preview(cast(Session, db), payload)


@pytest.mark.parametrize("kind", list(service.MODELS))
@pytest.mark.parametrize("lock", [False, True])
def test_grouped_lookup_and_labels(kind: str, lock: bool) -> None:
    model = service.MODELS[cast(BulkKind, kind)]
    row = (
        model(id=uuid7(), label="Packet")
        if model is not Inventory
        else Inventory(id=uuid7(), material_kind="seed")
    )
    db = MagicMock(spec=Session)
    db.execute.return_value = [(row, "Basil")]
    result = service._records(cast(Session, db), [BulkReference(kind=kind, id=row.id)], lock=lock)
    assert result[cast(BulkKind, kind), row.id][0] is row
    assert "Basil" in result[cast(BulkKind, kind), row.id][1]
    assert db.execute.call_count == 1
    assert db.scalars.call_count == int(lock and kind == "harvest_inventory")


def test_unchanged_mixed_selection_not_written(monkeypatch: pytest.MonkeyPatch) -> None:
    db, row, target, request = fixture(monkeypatch)
    unchanged = Sowing(
        id=uuid7(), label="Already there", lifecycle="active", updated_at=NOW, location_id=target.id
    )
    monkeypatch.setattr(
        service,
        "_records",
        lambda *_args, **_kwargs: {
            ("seed_lot", row.id): (row, "Packet"),
            ("sowing", unchanged.id): (unchanged, "Already there"),
        },
    )
    request.records.append(BulkReference(kind="sowing", id=unchanged.id))
    result = service.preview(cast(Session, db), request)
    assert (result.move_count, result.unchanged_count) == (1, 1)
    applied = service.apply(
        cast(Session, db),
        BulkLocationApplyRequest(
            records=[
                BulkPrecondition(kind=item.kind, id=item.id, expected_updated_at=NOW)
                for item in request.records
            ],
            target_location_id=target.id,
            expected_target_updated_at=NOW,
        ),
    )
    assert applied.unchanged_count == 1
    assert unchanged.updated_at == NOW


@pytest.mark.parametrize(
    "error",
    [
        service.BulkConflictError("target_location_not_found", "Missing"),
        service.BulkConflictError("stale_preview", "Stale"),
        EventDomainConflictError("historical", "Historical"),
        EventReferenceNotFoundError("missing", "Missing"),
        IntegrityError("sql", {}, Exception()),
        OperationalError("sql", {}, Exception()),
    ],
)
def test_route_rolls_back_safe_structured_failures(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    db, row, target, _request = fixture(monkeypatch)
    monkeypatch.setattr(api, "require_owner", lambda _actor: None)

    def fail(*_args: Any) -> None:
        raise error

    monkeypatch.setattr(service, "apply", fail)
    payload = BulkLocationApplyRequest(
        records=[BulkPrecondition(kind="seed_lot", id=row.id, expected_updated_at=NOW)],
        target_location_id=target.id,
        expected_target_updated_at=NOW,
    )
    with pytest.raises(HTTPException) as exception:
        api.apply(payload, cast(Session, db), cast(AuthenticatedActor, None))
    assert exception.value.status_code in {404, 409}
    assert "sql" not in str(exception.value.detail)
    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_routes_preview_failure_and_success(monkeypatch: pytest.MonkeyPatch) -> None:
    db, row, target, request = fixture(monkeypatch)
    monkeypatch.setattr(api, "require_owner", lambda _actor: None)
    actor = cast(AuthenticatedActor, None)
    assert api.preview(request, cast(Session, db), actor).selected_count == 1
    result = api.apply(
        BulkLocationApplyRequest(
            records=[BulkPrecondition(kind="seed_lot", id=row.id, expected_updated_at=NOW)],
            target_location_id=target.id,
            expected_target_updated_at=NOW,
        ),
        cast(Session, db),
        actor,
    )
    assert result == BulkLocationResult(moved_count=1, unchanged_count=0)
    db.commit.assert_called_once()
    db.get.return_value = None
    with pytest.raises(HTTPException) as exception:
        api.preview(request, cast(Session, db), actor)
    assert exception.value.status_code == 404
