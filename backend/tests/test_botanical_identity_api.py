from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock
from uuid import uuid7

import pytest
from fastapi import HTTPException, Response

from florabase.botanical_identities import api
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.schemas import BotanicalIdentityCreate, BotanicalIdentityUpdate
from florabase.botanical_identities.service import (
    BotanicalIdentityConflictError,
    BotanicalIdentityReferencedError,
)
from florabase.collection_views.schemas import BotanicalIdentityCollectionResponse


def identity() -> BotanicalIdentity:
    now = datetime.now(UTC)
    return BotanicalIdentity(
        id=uuid7(), scientific_name="Acer palmatum", created_at=now, updated_at=now
    )


def test_botanical_identity_api_success_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    item = identity()
    actor = cast(Any, SimpleNamespace(owner=True))
    database = MagicMock()
    payload = BotanicalIdentityCreate(scientific_name=item.scientific_name)
    update = BotanicalIdentityUpdate(scientific_name="Acer japonicum")

    monkeypatch.setattr(api, "list_botanical_identities", lambda _database: [item])
    assert api.list_all(actor, database)[0].id == item.id

    monkeypatch.setattr(api, "create_botanical_identity", lambda _database, _payload: item)
    response = Response()
    assert api.create(payload, response, actor, database).id == item.id
    assert response.headers["location"].endswith(str(item.id))

    monkeypatch.setattr(api, "get_botanical_identity", lambda _database, _id: item)
    assert api.read(item.id, actor, database).id == item.id
    collection = cast(BotanicalIdentityCollectionResponse, MagicMock())
    monkeypatch.setattr(api, "botanical_identity_collection", lambda _database, _id: collection)
    assert api.read_collection(item.id, actor, database) is collection

    monkeypatch.setattr(api, "update_botanical_identity", lambda _database, _item, _payload: item)
    assert api.update(item.id, update, actor, database).id == item.id
    monkeypatch.setattr(api, "delete_botanical_identity", lambda _database, _item: None)
    assert api.delete(item.id, actor, database).status_code == 204


def test_botanical_identity_api_translates_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    item = identity()
    actor = cast(Any, SimpleNamespace(owner=True))
    database = MagicMock()
    payload = BotanicalIdentityCreate(scientific_name=item.scientific_name)
    update = BotanicalIdentityUpdate(scientific_name="Acer japonicum")

    monkeypatch.setattr(api, "get_botanical_identity", lambda _database, _id: None)
    for operation in (
        lambda: api.read(item.id, actor, database),
        lambda: api.update(item.id, update, actor, database),
        lambda: api.delete(item.id, actor, database),
    ):
        with pytest.raises(HTTPException) as missing:
            operation()
        assert missing.value.status_code == 404

    monkeypatch.setattr(api, "botanical_identity_collection", lambda _database, _id: None)
    with pytest.raises(HTTPException) as missing_collection:
        api.read_collection(item.id, actor, database)
    assert missing_collection.value.status_code == 404

    monkeypatch.setattr(
        api,
        "create_botanical_identity",
        lambda _database, _payload: (_ for _ in ()).throw(BotanicalIdentityConflictError(item.id)),
    )
    with pytest.raises(HTTPException) as create_conflict:
        api.create(payload, Response(), actor, database)
    assert create_conflict.value.status_code == 409

    monkeypatch.setattr(api, "get_botanical_identity", lambda _database, _id: item)
    monkeypatch.setattr(
        api,
        "update_botanical_identity",
        lambda _database, _item, _payload: (_ for _ in ()).throw(
            BotanicalIdentityConflictError(item.id)
        ),
    )
    with pytest.raises(HTTPException) as update_conflict:
        api.update(item.id, update, actor, database)
    assert update_conflict.value.status_code == 409

    monkeypatch.setattr(
        api,
        "delete_botanical_identity",
        lambda _database, _item: (_ for _ in ()).throw(BotanicalIdentityReferencedError()),
    )
    with pytest.raises(HTTPException) as referenced:
        api.delete(item.id, actor, database)
    assert referenced.value.status_code == 409

    with pytest.raises(HTTPException) as forbidden:
        api.create(payload, Response(), cast(Any, SimpleNamespace(owner=False)), database)
    assert forbidden.value.status_code == 403
