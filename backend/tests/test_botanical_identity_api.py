from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock
from uuid import uuid7

import pytest
from fastapi import HTTPException, Response

from florabase.botanical_identities import api
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.reconciliation import (
    ReconciliationConflictError,
    ReconciliationNotFoundError,
)
from florabase.botanical_identities.schemas import (
    AcceptedNameCorrectionWrite,
    BotanicalIdentityCreate,
    BotanicalIdentityResponse,
    BotanicalIdentityUpdate,
    DuplicateIdentityMergeWrite,
    IdentityCollectionCounts,
    IdentityReconciliationResponse,
)
from florabase.botanical_identities.service import (
    BotanicalIdentityConflictError,
    BotanicalIdentityCoverReferencedError,
    BotanicalIdentityMergedError,
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

    monkeypatch.setattr(
        api,
        "list_botanical_identity_directory",
        lambda _database: [
            (
                item,
                "local",
                None,
                IdentityCollectionCounts(seed_lots=1, sowings=2, plants=3, plant_groups=4),
            )
        ],
    )
    listed = api.list_all(actor, database)[0]
    assert listed.id == item.id
    assert listed.compact_cover_kind == "local"
    assert listed.compact_external_cover_url is None
    assert listed.collection_counts == IdentityCollectionCounts(
        seed_lots=1, sowings=2, plants=3, plant_groups=4
    )

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

    monkeypatch.setattr(
        api,
        "delete_botanical_identity",
        lambda _database, _item: (_ for _ in ()).throw(BotanicalIdentityCoverReferencedError()),
    )
    with pytest.raises(HTTPException) as cover_referenced:
        api.delete(item.id, actor, database)
    assert cover_referenced.value.status_code == 409
    assert cast(dict[str, object], cover_referenced.value.detail)["code"] == (
        "botanical_identity_has_cover"
    )

    with pytest.raises(HTTPException) as forbidden:
        api.create(payload, Response(), cast(Any, SimpleNamespace(owner=False)), database)
    assert forbidden.value.status_code == 403

    monkeypatch.setattr(
        api,
        "update_botanical_identity",
        lambda _database, _item, _payload: (_ for _ in ()).throw(
            BotanicalIdentityMergedError(item.id)
        ),
    )
    with pytest.raises(HTTPException) as merged_conflict:
        api.update(item.id, update, actor, database)
    assert merged_conflict.value.status_code == 409
    assert cast(dict[str, object], merged_conflict.value.detail)["code"] == (
        "botanical_identity_merged"
    )


def test_reconciliation_api_endpoints_and_error_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = identity()
    actor = cast(Any, SimpleNamespace(owner=True, user_id=uuid7()))
    database = MagicMock()
    wfo_source = MagicMock()
    wcvp_v15 = MagicMock()
    wcvp_v16 = MagicMock()

    expected = IdentityReconciliationResponse(
        identity=BotanicalIdentityResponse.from_model(item),
        original_scientific_name=item.scientific_name,
        original_cultivar_name=None,
        original_common_name=None,
        original_display_label=item.scientific_name,
        former_names=[],
        suggestions=[],
        source_assessments=[],
        conflicts=[],
        has_source_conflict=False,
        reconciliations=[],
    )
    monkeypatch.setattr(api, "inspect_reconciliation", lambda *_args, **_kwargs: expected)
    assert (
        api.read_reconciliation(item.id, actor, database, wfo_source, wcvp_v15, wcvp_v16)
        is expected
    )

    correction = AcceptedNameCorrectionWrite(
        scientific_name="Trichocereus bridgesii",
        identity_updated_at=item.updated_at,
    )
    monkeypatch.setattr(api, "correct_accepted_name", lambda *_args, **_kwargs: expected)
    assert (
        api.correct_name(item.id, correction, actor, database, wfo_source, wcvp_v15, wcvp_v16)
        is expected
    )

    merge_payload = DuplicateIdentityMergeWrite(
        survivor_identity_id=uuid7(),
        duplicate_updated_at=item.updated_at,
        survivor_updated_at=item.updated_at,
    )
    monkeypatch.setattr(api, "merge_duplicate_identity", lambda *_args, **_kwargs: expected)
    assert (
        api.merge_duplicate(item.id, merge_payload, actor, database, wfo_source, wcvp_v15, wcvp_v16)
        is expected
    )

    monkeypatch.setattr(
        api,
        "inspect_reconciliation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ReconciliationNotFoundError("Not found")),
    )
    with pytest.raises(HTTPException) as not_found:
        api.read_reconciliation(item.id, actor, database, wfo_source, wcvp_v15, wcvp_v16)
    assert not_found.value.status_code == 404

    colliding_id = uuid7()
    monkeypatch.setattr(
        api,
        "correct_accepted_name",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ReconciliationConflictError(
                code="duplicate_botanical_identity",
                message="Collision",
                existing_id=colliding_id,
                conflicting_fields=["description"],
            )
        ),
    )
    with pytest.raises(HTTPException) as conflict_err:
        api.correct_name(item.id, correction, actor, database, wfo_source, wcvp_v15, wcvp_v16)
    assert conflict_err.value.status_code == 409
    detail = cast(dict[str, object], conflict_err.value.detail)
    assert detail["code"] == "duplicate_botanical_identity"
    assert detail["existing_id"] == str(colliding_id)
    assert detail["conflicting_fields"] == ["description"]


def test_botanical_identity_synonym_api_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    from florabase.botanical_identities.model import BotanicalIdentityName
    from florabase.botanical_identities.schemas import (
        OperatorSynonymCreate,
        OperatorSynonymUpdate,
    )
    from florabase.botanical_identities.service import (
        BotanicalIdentityConflictError,
        BotanicalIdentityMergedError,
        BotanicalIdentityNotFoundError,
        ImmutableHistoricalNameError,
        SynonymNotFoundError,
        SynonymValidationError,
    )

    item = identity()
    actor = cast(Any, SimpleNamespace(owner=True))
    database = MagicMock()
    now = datetime.now(UTC)
    synonym_row = BotanicalIdentityName(
        id=uuid7(),
        botanical_identity_id=item.id,
        scientific_name="Echinopsis lageniformis",
        cultivar_name=None,
        common_name="Bolivian torch",
        authorship=None,
        status_kind="operator_synonym",
        source_provider="operator",
        source_version=None,
        source_taxon_id=None,
        accepted_source_taxon_id=None,
        origin_identity_id=None,
        effective_from=now,
        superseded_at=now,
        created_at=now,
    )

    # 1. list_synonyms
    monkeypatch.setattr(api, "list_identity_synonyms", lambda *_args, **_kwargs: [synonym_row])
    listed = api.list_synonyms(item.id, actor, database)
    assert len(listed) == 1
    assert listed[0].scientific_name == "Echinopsis lageniformis"
    assert listed[0].status_kind == "operator_synonym"

    monkeypatch.setattr(
        api,
        "list_identity_synonyms",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(BotanicalIdentityNotFoundError()),
    )
    with pytest.raises(HTTPException) as not_found:
        api.list_synonyms(item.id, actor, database)
    assert not_found.value.status_code == 404

    # 2. create_synonym
    create_payload = OperatorSynonymCreate(scientific_name="Echinopsis lageniformis")
    monkeypatch.setattr(api, "add_operator_synonym", lambda *_args, **_kwargs: synonym_row)
    res = Response()
    created = api.create_synonym(item.id, create_payload, res, actor, database)
    assert created.id == synonym_row.id
    assert res.headers["Location"].endswith(str(synonym_row.id))

    # create_synonym error translations
    errors_and_codes = [
        (BotanicalIdentityNotFoundError(), 404),
        (BotanicalIdentityMergedError(uuid7()), 409),
        (SynonymValidationError("synonym_equals_accepted_name", "Same as accepted"), 409),
        (BotanicalIdentityConflictError(uuid7(), "Collision"), 409),
    ]
    for exc, code in errors_and_codes:
        monkeypatch.setattr(
            api,
            "add_operator_synonym",
            lambda *_args, exc=exc, **_kwargs: (_ for _ in ()).throw(exc),
        )
        with pytest.raises(HTTPException) as err:
            api.create_synonym(item.id, create_payload, Response(), actor, database)
        assert err.value.status_code == code

    # 3. update_synonym
    update_payload = OperatorSynonymUpdate(scientific_name="Echinopsis lageniformis")
    monkeypatch.setattr(api, "update_operator_synonym", lambda *_args, **_kwargs: synonym_row)
    updated = api.update_synonym(item.id, synonym_row.id, update_payload, actor, database)
    assert updated.id == synonym_row.id

    update_errors = [
        (BotanicalIdentityNotFoundError(), 404),
        (SynonymNotFoundError(), 404),
        (BotanicalIdentityMergedError(uuid7()), 409),
        (ImmutableHistoricalNameError(), 409),
        (SynonymValidationError("duplicate_identity_name", "Duplicate"), 409),
        (BotanicalIdentityConflictError(uuid7(), "Collision"), 409),
    ]
    for exc, code in update_errors:
        monkeypatch.setattr(
            api,
            "update_operator_synonym",
            lambda *_args, exc=exc, **_kwargs: (_ for _ in ()).throw(exc),
        )
        with pytest.raises(HTTPException) as err:
            api.update_synonym(item.id, synonym_row.id, update_payload, actor, database)
        assert err.value.status_code == code

    # 4. delete_synonym
    monkeypatch.setattr(api, "remove_operator_synonym", lambda *_args, **_kwargs: None)
    del_res = api.delete_synonym(item.id, synonym_row.id, actor, database)
    assert del_res.status_code == 204

    delete_errors = [
        (BotanicalIdentityNotFoundError(), 404),
        (SynonymNotFoundError(), 404),
        (BotanicalIdentityMergedError(uuid7()), 409),
        (ImmutableHistoricalNameError(), 409),
    ]
    for exc, code in delete_errors:
        monkeypatch.setattr(
            api,
            "remove_operator_synonym",
            lambda *_args, exc=exc, **_kwargs: (_ for _ in ()).throw(exc),
        )
        with pytest.raises(HTTPException) as err:
            api.delete_synonym(item.id, synonym_row.id, actor, database)
        assert err.value.status_code == code


def test_synonyms_for_identities_excludes_active_name_and_deduplicates() -> None:
    ident = identity()
    database = MagicMock()
    database.execute.return_value.all.return_value = [
        (ident.id, ident.scientific_name, ident.cultivar_name),
        (ident.id, "Cereus bridgesii", None),
        (ident.id, "Cereus bridgesii", "Inermis"),
        (ident.id, "Echinopsis lageniformis", None),
    ]
    assert api._synonyms_for_identities(database, []) == {}
    result = api._synonyms_for_identities(database, [ident])
    assert result[ident.id] == ["Cereus bridgesii", "Echinopsis lageniformis"]
