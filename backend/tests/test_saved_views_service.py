from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock, patch
from uuid import uuid7

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from florabase.saved_views import api, service
from florabase.saved_views.model import SavedView
from florabase.saved_views.schemas import SavedViewCreate, SavedViewUpdate
from florabase.saved_views.state import SavedViewSurface


def record(**values: Any) -> SavedView:
    attributes = {
        "id": uuid7(),
        "owner_id": uuid7(),
        "name": "Basil",
        "surface": "seed_lots",
        "state_version": 1,
        "state": {"q": "basil"},
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    attributes.update(values)
    return SavedView(**attributes)


class UniqueViolationError(Exception):
    sqlstate = "23505"


def test_service_owner_queries_and_crud() -> None:
    database = MagicMock()
    owner_id, view_id = uuid7(), uuid7()
    saved = record(id=view_id, owner_id=owner_id)
    database.scalars.return_value = [saved]
    assert service.list_views(database, owner_id, None, 100) == [saved]
    assert service.list_views(database, owner_id, SavedViewSurface.SEED_LOTS) == [saved]
    database.scalar.return_value = saved
    database.scalars.return_value = [saved]
    assert service.get_view(database, owner_id, view_id) is saved

    payload = SavedViewCreate.model_validate(
        {"name": "Mint", "surface": "seed_lots", "state_version": 1, "state": {"q": "mint"}}
    )
    created = service.create_view(database, owner_id, payload)
    assert created.owner_id == owner_id
    assert created.name == "Mint"
    database.add.assert_called_once_with(created)

    renamed = service.update_view(database, saved, SavedViewUpdate(name="Herb"))
    assert renamed.name == "Herb"
    state_updated = service.update_view(
        database, saved, SavedViewUpdate(state_version=1, state={"q": "mint"})
    )
    assert state_updated.state == {"q": "mint"}
    assert database.flush.call_count == 3


def test_unique_violation_is_a_conflict_and_other_integrity_errors_propagate() -> None:
    database = MagicMock()
    unique = IntegrityError("insert", {}, UniqueViolationError("duplicate"))
    database.flush.side_effect = unique
    with pytest.raises(service.SavedViewConflictError):
        service._flush(database)
    other = IntegrityError("insert", {}, RuntimeError("connection lost"))
    database.flush.side_effect = other
    with pytest.raises(IntegrityError) as raised:
        service._flush(database)
    assert raised.value is other


def test_api_maps_owner_not_found_and_write_conflicts() -> None:
    owner_id = uuid7()
    actor = cast(Any, SimpleNamespace(user_id=owner_id))
    database = MagicMock()
    database.scalar.return_value = None
    saved = record(owner_id=owner_id)

    with pytest.raises(HTTPException) as missing:
        api._require(database, owner_id, uuid7())
    assert missing.value.status_code == 404

    database.scalars.return_value = [saved]
    listed = api.list_all(actor, database, SavedViewSurface.SEED_LOTS, 0)
    assert [item.id for item in listed] == [saved.id]

    create_payload = SavedViewCreate.model_validate(
        {"name": "Mint", "surface": "seed_lots", "state_version": 1, "state": {"q": "mint"}}
    )
    with (
        pytest.raises(HTTPException) as conflict,
        patch.object(
            service, "create_view", side_effect=service.SavedViewConflictError("duplicate")
        ),
    ):
        api.create(create_payload, actor, database)
    assert conflict.value.status_code == 409

    database.scalar.return_value = saved
    with (
        pytest.raises(HTTPException) as bad_state,
        patch.object(service, "update_view", side_effect=ValueError("unsupported")),
    ):
        api.update(saved.id, SavedViewUpdate(name="Changed"), actor, database)
    assert bad_state.value.status_code == 422

    with patch.object(service, "get_view", return_value=saved):
        assert api.delete(saved.id, actor, database).status_code == 204
    database.delete.assert_called_once_with(saved)
    database.flush.assert_called()
