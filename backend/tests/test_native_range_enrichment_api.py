from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid7

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from florabase.auth.dependencies import AuthenticatedActor
from florabase.core.config import Settings
from florabase.native_range_enrichment import api, service
from florabase.native_range_enrichment.model import WcvpLink
from florabase.native_range_enrichment.schemas import (
    ApplyWrite,
    SourceStatus,
    WcvpLinkResponse,
    WcvpLinkWrite,
)
from florabase.native_range_enrichment.source import (
    ARCHIVE_SHA256,
    SourceMetadata,
    SourceUnavailableError,
    Taxon,
    WcvpSource,
)

_DEFAULT = object()


class Database:
    def __init__(self, identity: Any = _DEFAULT, wcvp_link: Any = _DEFAULT) -> None:
        self.identity = identity
        self.wcvp_link = wcvp_link
        self.ids: list[object] = []

    def get(self, model: object, _key: object) -> Any:
        return self.wcvp_link if model is WcvpLink else self.identity

    def scalars(self, _statement: object) -> list[object]:
        return self.ids


def as_session(database: Database | None = None) -> Session:
    return cast(Session, database or Database())


def actor(*, owner: bool = False) -> AuthenticatedActor:
    return cast(AuthenticatedActor, SimpleNamespace(owner=owner))


def source(value: Any) -> WcvpSource:
    return cast(WcvpSource, value)


def source_metadata(retrieved_at: str = "2026-10-09T06:16:20+00:00") -> SourceMetadata:
    return SourceMetadata(retrieved_at=retrieved_at)


def taxon() -> Taxon:
    return Taxon(
        external_id="100",
        name="Fixture species",
        authorship="A. Author",
        rank="Species",
        status="Accepted",
        accepted_id="100",
        powo_id="",
        reviewed="1",
    )


def link(metadata: SourceMetadata, *, stale: bool = False) -> WcvpLinkResponse:
    return WcvpLinkResponse(
        version=uuid7(),
        taxon=taxon(),
        source=metadata,
        confirmed_at=datetime.now(UTC),
        stale=stale,
    )


def test_error_translation_and_identity_lookup() -> None:
    for error, expected in [
        (SourceUnavailableError("offline"), 503),
        (service.EnrichmentConflictError("stale"), 409),
        (service.EnrichmentNotFoundError("missing"), 404),
    ]:
        with pytest.raises(HTTPException) as caught:
            api.fail(error)
        assert caught.value.status_code == expected
        assert cast(dict[str, str], caught.value.detail)["message"] == str(error)
    identity_record = object()
    assert api.identity(as_session(Database(identity_record)), uuid7()) is identity_record
    with pytest.raises(HTTPException) as missing:
        api.identity(as_session(Database(None)), uuid7())
    assert missing.value.status_code == 404


def test_source_dependency_uses_optional_configured_path() -> None:
    from pathlib import Path

    settings = Settings(wcvp_snapshot_path=Path("/tmp/wcvp.sqlite"))
    assert api.source_dependency(settings).path == settings.wcvp_snapshot_path


def test_source_status_marks_reprovisioned_link_stale(monkeypatch: pytest.MonkeyPatch) -> None:
    metadata = source_metadata()
    previous = link(source_metadata("2026-10-08T00:00:00+00:00"))
    monkeypatch.setattr(service, "link_response", lambda *_: previous)
    response = api.source_status(
        uuid7(), as_session(), actor(), source(SimpleNamespace(metadata=lambda: metadata))
    )
    assert response.available is True
    assert response.source == metadata
    assert response.link is not None
    assert response.link.stale is True

    matching = link(metadata)
    monkeypatch.setattr(service, "link_response", lambda *_: matching)
    unchanged = api.source_status(
        uuid7(), as_session(), actor(), source(SimpleNamespace(metadata=lambda: metadata))
    )
    assert unchanged.link is not None
    assert unchanged.link.stale is False

    monkeypatch.setattr(service, "link_response", lambda *_: previous)
    missing = api.source_status(
        uuid7(),
        as_session(Database(SimpleNamespace(), wcvp_link=None)),
        actor(),
        source(
            SimpleNamespace(
                metadata=lambda: (_ for _ in ()).throw(SourceUnavailableError("offline"))
            )
        ),
    )
    assert missing == SourceStatus(available=False, message="offline")


def test_search_and_confirm_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    identity_id = uuid7()
    selected = taxon()
    taxa_source = SimpleNamespace(search=lambda query: [selected] if query == "Fi" else [])
    assert api.search_taxa(identity_id, as_session(), actor(), source(taxa_source), "Fi") == [
        selected
    ]

    saved = link(source_metadata())
    monkeypatch.setattr(service, "confirm_link", lambda *_: saved)
    confirmed = api.confirm(
        identity_id,
        WcvpLinkWrite(external_id=selected.external_id, checksum=ARCHIVE_SHA256),
        as_session(),
        actor(owner=True),
        source(SimpleNamespace()),
    )
    assert confirmed == saved
    with pytest.raises(HTTPException) as denied:
        api.confirm(
            identity_id,
            WcvpLinkWrite(external_id=selected.external_id, checksum=ARCHIVE_SHA256),
            as_session(),
            actor(owner=False),
            source(SimpleNamespace()),
        )
    assert denied.value.status_code == 403


def test_search_source_failure_is_retryable() -> None:
    with pytest.raises(HTTPException) as unavailable:
        api.search_taxa(
            uuid7(),
            as_session(),
            actor(),
            source(
                SimpleNamespace(
                    search=lambda _query: (_ for _ in ()).throw(SourceUnavailableError("offline"))
                )
            ),
            "Fi",
        )
    assert unavailable.value.status_code == 503


def test_mutating_routes_translate_domain_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    identity_id = uuid7()
    owner = actor(owner=True)
    monkeypatch.setattr(
        service,
        "confirm_link",
        lambda *_: (_ for _ in ()).throw(service.EnrichmentConflictError("stale")),
    )
    with pytest.raises(HTTPException) as stale:
        api.confirm(
            identity_id,
            WcvpLinkWrite(external_id="100", checksum=ARCHIVE_SHA256),
            as_session(),
            owner,
            source(SimpleNamespace()),
        )
    assert stale.value.status_code == 409

    monkeypatch.setattr(
        service,
        "propose",
        lambda *_: (_ for _ in ()).throw(SourceUnavailableError("offline")),
    )
    with pytest.raises(HTTPException) as unavailable:
        api.create_proposal(identity_id, as_session(), owner, source(SimpleNamespace()))
    assert unavailable.value.status_code == 503


def test_proposal_routes_delegate_and_scope_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    identity_id = uuid7()
    proposal_id = uuid7()
    proposal_result = cast(Any, SimpleNamespace(proposal_id=proposal_id))
    application_result = cast(Any, SimpleNamespace(proposal_id=proposal_id))
    monkeypatch.setattr(service, "propose", lambda *_: proposal_result)
    result = api.create_proposal(identity_id, as_session(), actor(owner=True), source(object()))
    assert result == proposal_result

    first, second = uuid7(), uuid7()
    database = Database()
    database.ids = [first, second]
    seen: list[tuple[object, object]] = []
    monkeypatch.setattr(
        service,
        "inspect_proposal",
        lambda _db, target, proposal: inspect_and_record(seen, target, proposal, proposal_result),
    )
    session = as_session(database)
    assert api.list_proposals(identity_id, session, actor()) == [proposal_result, proposal_result]
    assert seen == [(identity_id, first), (identity_id, second)]
    assert api.read_proposal(identity_id, first, session, actor()) == proposal_result

    monkeypatch.setattr(service, "apply", lambda *_: application_result)
    applied_result = api.apply_proposal(
        identity_id,
        proposal_id,
        ApplyWrite(selected_place_ids=[uuid7()]),
        session,
        actor(owner=True),
    )
    assert applied_result == application_result

    monkeypatch.setattr(
        service,
        "inspect_proposal",
        lambda *_: (_ for _ in ()).throw(service.EnrichmentNotFoundError("missing")),
    )
    with pytest.raises(HTTPException) as missing:
        api.read_proposal(identity_id, first, session, actor())
    assert missing.value.status_code == 404

    monkeypatch.setattr(
        service,
        "apply",
        lambda *_: (_ for _ in ()).throw(service.EnrichmentConflictError("stale")),
    )
    with pytest.raises(HTTPException) as stale:
        api.apply_proposal(
            identity_id,
            proposal_id,
            ApplyWrite(selected_place_ids=[uuid7()]),
            session,
            actor(owner=True),
        )
    assert stale.value.status_code == 409


def inspect_and_record(
    seen: list[tuple[object, object]], target: object, proposal: object, response: Any
) -> Any:
    seen.append((target, proposal))
    return response
