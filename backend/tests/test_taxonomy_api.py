from types import SimpleNamespace
from typing import cast
from uuid import uuid7

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import florabase.taxonomy.service as taxonomy_service
from florabase.auth.dependencies import AuthenticatedActor, require_authenticated_actor
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.db.session import get_database_session
from florabase.taxonomy import api, service
from florabase.taxonomy.schemas import (
    IdentityTaxonomy,
    TaxonomyLink,
    TaxonomyLinkWrite,
    TaxonomyNodeDetail,
    TaxonomyTree,
)
from florabase.taxonomy.source import SourceUnavailableError, WfoCandidate, WfoSource


def session() -> Session:
    return cast(Session, SimpleNamespace(get=lambda _model, _identity_id: object()))


def actor() -> AuthenticatedActor:
    return cast(AuthenticatedActor, SimpleNamespace(owner=True))


def source() -> WfoSource:
    return cast(WfoSource, SimpleNamespace(search=lambda _query: []))


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (SourceUnavailableError("offline"), 503, "taxonomy_unavailable"),
        (service.TaxonomyConflictError("stale"), 409, "taxonomy_conflict"),
        (service.TaxonomyNotFoundError("missing"), 404, "taxonomy_not_found"),
    ],
)
def test_fail_maps_taxonomy_errors(error: Exception, status: int, code: str) -> None:
    with pytest.raises(HTTPException) as raised:
        api.fail(error)
    assert raised.value.status_code == status
    detail = cast(dict[str, str], raised.value.detail)
    assert detail["code"] == code


def test_read_routes_dispatch_with_default_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    database, wfo = session(), source()
    tree = cast(TaxonomyTree, object())
    identity_taxonomy = cast(IdentityTaxonomy, object())
    monkeypatch.setattr(taxonomy_service, "tree", lambda *args, **kwargs: tree)
    assert api.tree(database, actor(), wfo) is tree
    node = cast(TaxonomyNodeDetail, object())
    monkeypatch.setattr(taxonomy_service, "node_detail", lambda _value, _selected: node)
    assert api.node("wfo-0000000001", database, actor(), wfo) is node
    monkeypatch.setattr(taxonomy_service, "identity_taxonomy", lambda *args: identity_taxonomy)
    assert api.read(uuid7(), database, actor(), wfo) is identity_taxonomy


def test_node_and_identity_routes_map_domain_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    database, wfo = session(), source()
    monkeypatch.setattr(
        taxonomy_service, "tree", lambda *args, **kwargs: cast(TaxonomyTree, object())
    )

    def missing_node(*_args: object) -> TaxonomyNodeDetail:
        raise service.TaxonomyNotFoundError("missing node")

    monkeypatch.setattr(taxonomy_service, "node_detail", missing_node)
    with pytest.raises(HTTPException) as raised:
        api.node("wfo-0000000001", database, actor(), wfo)
    assert raised.value.status_code == 404

    def unavailable(*_args: object) -> IdentityTaxonomy:
        raise SourceUnavailableError("offline")

    monkeypatch.setattr(taxonomy_service, "identity_taxonomy", unavailable)
    with pytest.raises(HTTPException) as raised:
        api.read(uuid7(), database, actor(), wfo)
    assert raised.value.status_code == 503


def test_candidates_confirms_and_unlinks(monkeypatch: pytest.MonkeyPatch) -> None:
    identity_id = uuid7()
    database = session()
    wfo = source()
    candidate = cast(WfoCandidate, object())
    link = cast(TaxonomyLink, object())
    monkeypatch.setattr(api, "require_owner", lambda _actor: None)
    monkeypatch.setattr(wfo, "search", lambda query: [candidate])
    assert api.candidates(identity_id, database, actor(), wfo, "Fi") == [candidate]
    monkeypatch.setattr(taxonomy_service, "confirm", lambda *args: link)
    payload = cast(TaxonomyLinkWrite, object())
    assert api.confirm(identity_id, payload, database, actor(), wfo) is link
    called: list[tuple[object, ...]] = []

    def unlink(*args: object) -> None:
        called.append(args)

    monkeypatch.setattr(taxonomy_service, "unlink", unlink)
    version = uuid7()
    assert api.unlink(identity_id, version, database, actor()) is None
    assert called == [(database, identity_id, version)]


def test_candidates_and_write_routes_map_missing_and_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity_id = uuid7()
    database = cast(Session, SimpleNamespace(get=lambda *_args: None))
    with pytest.raises(HTTPException) as raised:
        api.candidates(identity_id, database, actor(), source(), "Fi")
    assert raised.value.status_code == 404

    database = session()
    wfo = source()
    monkeypatch.setattr(
        wfo, "search", lambda _query: (_ for _ in ()).throw(SourceUnavailableError("offline"))
    )
    with pytest.raises(HTTPException) as raised:
        api.candidates(identity_id, database, actor(), wfo, "Fi")
    assert raised.value.status_code == 503

    monkeypatch.setattr(api, "require_owner", lambda _actor: None)

    def conflict(*_args: object) -> TaxonomyLink:
        raise service.TaxonomyConflictError("stale")

    monkeypatch.setattr(taxonomy_service, "confirm", conflict)
    with pytest.raises(HTTPException) as raised:
        api.confirm(identity_id, cast(TaxonomyLinkWrite, object()), database, actor(), wfo)
    assert raised.value.status_code == 409

    def not_found(*_args: object) -> None:
        raise service.TaxonomyNotFoundError("missing")

    monkeypatch.setattr(taxonomy_service, "unlink", not_found)
    with pytest.raises(HTTPException) as raised:
        api.unlink(identity_id, uuid7(), database, actor())
    assert raised.value.status_code == 404


def test_candidates_uses_botanical_identity_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []

    def lookup(model: object, identity_id: object) -> object:
        calls.extend([model, identity_id])
        return object()

    database = cast(Session, SimpleNamespace(get=lookup))
    wfo = source()
    assert api.candidates(uuid7(), database, actor(), wfo, "Fi") == []
    assert calls[0] is BotanicalIdentity


@pytest.mark.parametrize(
    ("query", "status", "normalized"),
    [
        ("", 422, None),
        ("  \t  ", 422, None),
        (" O ", 422, None),
        (" Oc ", 200, "Oc"),
        ("Ocimum", 200, "Ocimum"),
        ("x" * 200, 200, "x" * 200),
        (" " + "x" * 200 + " ", 200, "x" * 200),
        ("x" * 201, 422, None),
    ],
)
def test_candidate_prefix_is_trimmed_before_length_validation(
    query: str, status: int, normalized: str | None
) -> None:
    searches: list[str] = []

    def search(value: str) -> list[WfoCandidate]:
        searches.append(value)
        return []

    wfo = cast(WfoSource, SimpleNamespace(search=search))
    application = FastAPI()
    application.include_router(api.router)
    application.dependency_overrides[require_authenticated_actor] = actor
    application.dependency_overrides[get_database_session] = session
    application.dependency_overrides[api.source_dependency] = lambda: wfo
    response = TestClient(application).get(
        f"/botanical-identities/{uuid7()}/taxonomy/candidates", params={"q": query}
    )
    assert response.status_code == status
    assert searches == ([] if normalized is None else [normalized])


def test_tree_cover_projection_is_an_explicit_optional_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    result = cast(TaxonomyTree, object())

    def read(*_args: object, **kwargs: object) -> TaxonomyTree:
        calls.append(kwargs)
        return result

    monkeypatch.setattr(taxonomy_service, "tree", read)
    assert api.tree(session(), actor(), source(), include_covers=True) is result
    assert calls[-1]["include_covers"] is True
    assert api.tree(session(), actor(), source()) is result
    assert calls[-1]["include_covers"] is False
