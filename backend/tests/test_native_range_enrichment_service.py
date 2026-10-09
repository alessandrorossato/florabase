from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid7

import pytest
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.native_range_enrichment import service
from florabase.native_range_enrichment.crosswalk import CROSSWALK_VERSION
from florabase.native_range_enrichment.model import (
    NativeRangeApplication,
    NativeRangeProposal,
    NativeRangeRevision,
    WcvpLink,
)
from florabase.native_range_enrichment.schemas import (
    ApplyWrite,
    ProposalEvidence,
    ProposalResponse,
    RangeChoice,
    SourceAssertion,
)
from florabase.native_range_enrichment.source import (
    ARCHIVE_SHA256,
    SourceMetadata,
    Taxon,
    WcvpSource,
)


class Database:
    def __init__(self, identity: object, link: object | None = None) -> None:
        self.identity = identity
        self.link = link
        self.scalar_value: object = None
        self.added: list[object] = []
        self.proposal: NativeRangeProposal | None = None
        self.application: NativeRangeApplication | None = None
        self.places: list[object] = []

    def scalar(self, _statement: object) -> object:
        return self.scalar_value

    def scalars(self, _statement: object) -> list[object]:
        return self.places

    def get(self, model: object, _key: object, **_kwargs: object) -> object | None:
        if model is WcvpLink:
            return self.link
        if model is NativeRangeRevision:
            return None
        if model is NativeRangeApplication:
            return self.application
        if model is NativeRangeProposal:
            return self.proposal
        return None

    def add(self, value: object) -> None:
        self.added.append(value)
        if isinstance(value, NativeRangeProposal):
            self.proposal = value
        if isinstance(value, NativeRangeApplication):
            self.application = value

    def execute(self, _statement: object) -> None:
        pass

    def flush(self) -> None:
        if self.proposal is not None and self.proposal.created_at is None:
            self.proposal.created_at = datetime.now(UTC)
        if self.application is not None and self.application.applied_at is None:
            self.application.applied_at = datetime.now(UTC)


def as_session(database: Database) -> Session:
    return cast(Session, database)


def as_source(source: Any) -> WcvpSource:
    return cast(WcvpSource, source)


def identity() -> Any:
    return SimpleNamespace(
        id=uuid7(),
        scientific_name="Fixture species",
        cultivar_name=None,
        common_name=None,
        updated_at=datetime(2026, 10, 9, tzinfo=UTC),
    )


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


def metadata() -> SourceMetadata:
    return SourceMetadata(retrieved_at="2026-10-09T06:16:20+00:00")


def link_for(record: Any) -> WcvpLink:
    return WcvpLink(
        identity_id=record.id,
        version=uuid7(),
        external_id="100",
        taxon=taxon().model_dump(mode="json"),
        source=metadata().model_dump(mode="json"),
        identity_snapshot=service.identity_snapshot(record),
        confirmed_at=datetime.now(UTC),
    )


def test_identity_and_range_helpers() -> None:
    record = identity()
    assert service.identity_snapshot(record)["scientific_name"] == "Fixture species"
    database = Database(record)
    assert service.range_version(as_session(database), record.id) == 0
    database.places = []
    assert service.current_ids(as_session(database), record.id) == []


def test_identity_review_locks_and_requires_existing_identity() -> None:
    record = identity()
    database = Database(record)
    database.scalar_value = record
    assert service.identity_for_review(as_session(database), record.id) == record
    database.scalar_value = None
    with pytest.raises(service.EnrichmentNotFoundError):
        service.identity_for_review(as_session(database), record.id)


def test_confirm_link_creates_and_replaces_exact_confirmed_taxon(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = identity()
    database = Database(record)
    source = SimpleNamespace(metadata=metadata, taxon=lambda _external_id: taxon())
    monkeypatch.setattr(service, "identity_for_review", lambda *_: record)
    result = service.confirm_link(
        as_session(database), record.id, "100", ARCHIVE_SHA256, as_source(source)
    )
    assert result.taxon.external_id == "100"
    assert result.stale is False
    assert database.link is None
    saved = next(value for value in database.added if isinstance(value, WcvpLink))
    database.link = saved
    replaced = service.confirm_link(
        as_session(database), record.id, "100", ARCHIVE_SHA256, as_source(source)
    )
    assert replaced.version != result.version
    assert len([value for value in database.added if isinstance(value, WcvpLink)]) == 1

    with pytest.raises(service.EnrichmentConflictError):
        service.confirm_link(as_session(database), record.id, "100", "0" * 64, as_source(source))
    source.taxon = lambda _external_id: taxon().model_copy(update={"status": "Synonym"})
    with pytest.raises(service.EnrichmentConflictError):
        service.confirm_link(
            as_session(database), record.id, "100", ARCHIVE_SHA256, as_source(source)
        )


def test_link_response_marks_identity_edits_stale() -> None:
    record = identity()
    linked = link_for(record)
    assert service.link_response(linked, cast(BotanicalIdentity, record)).stale is False
    record.scientific_name = "Different name"
    assert service.link_response(linked, cast(BotanicalIdentity, record)).stale is True


def test_proposal_freezes_exact_assertions_and_mapped_current_diff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = identity()
    linked = link_for(record)
    addition = uuid7()
    existing = uuid7()
    geography = [
        SimpleNamespace(
            id=addition,
            name="Bolivia",
            path="South America / Bolivia",
            source_name="unicode_cldr",
            source_version="48.2.1",
            source_code_type="iso_3166_1_alpha_2",
            source_code="BO",
            retired_at=None,
        ),
        SimpleNamespace(
            id=existing,
            name="Italy",
            path="Europe / Italy",
            source_name="unicode_cldr",
            source_version="48.2.1",
            source_code_type="iso_3166_1_alpha_2",
            source_code="IT",
            retired_at=None,
        ),
    ]
    rows = [
        {
            "plant_locality_id": "a1",
            "plant_name_id": "100",
            "continent_code_l1": "SAM",
            "continent": "South America",
            "region_code_l2": "SAM",
            "region": "South America",
            "area_code_l3": "BOL",
            "area": "Bolivia",
            "introduced": "0",
            "extinct": "0",
            "location_doubtful": "0",
        },
        {
            "plant_locality_id": "a2",
            "plant_name_id": "100",
            "continent_code_l1": "SAM",
            "continent": "South America",
            "region_code_l2": "SAM",
            "region": "South America",
            "area_code_l3": "ZZZ",
            "area": "Unknown",
            "introduced": "1",
            "extinct": "0",
            "location_doubtful": "0",
        },
    ]
    source = SimpleNamespace(
        metadata=metadata,
        taxon=lambda _external_id: taxon(),
        distribution=lambda _external_id: rows,
    )
    database = Database(record, linked)
    monkeypatch.setattr(service, "identity_for_review", lambda *_: record)
    monkeypatch.setattr(service, "range_version", lambda *_: 3)
    monkeypatch.setattr(service, "current_ids", lambda *_: [existing])
    monkeypatch.setattr(service, "list_geographic_places", lambda *_: geography)
    monkeypatch.setattr(service, "display_path", lambda place, _places: place.path)
    frozen = cast(Any, object())
    monkeypatch.setattr(service, "inspect_proposal", lambda *_: frozen)
    assert service.propose(as_session(database), record.id, as_source(source)) is frozen
    stored = database.proposal
    assert stored is not None
    evidence = ProposalEvidence.model_validate(stored.evidence)
    assert evidence.crosswalk_version == CROSSWALK_VERSION
    assert evidence.destination_version == 3
    assert evidence.current_ids == [existing]
    assert {choice.change for choice in evidence.choices} == {"ADD", "CURRENT-ONLY"}
    assert evidence.assertions[0].original == rows[0]
    assert evidence.assertions[1].status == "introduced"
    assert evidence.assertions[1].place_ids == []

    linked.identity_snapshot = {}
    with pytest.raises(service.EnrichmentConflictError):
        service.propose(as_session(database), record.id, as_source(source))


def test_inspect_proposal_includes_immutable_application_outcome() -> None:
    record_id = uuid7()
    proposal_id = uuid7()
    evidence = ProposalEvidence(
        link_version=uuid7(),
        identity_snapshot={},
        destination_version=1,
        current_ids=[],
        source=metadata(),
        taxon=taxon(),
        retrieved_at=datetime.now(UTC),
        crosswalk_version=CROSSWALK_VERSION,
        choices=[],
        assertions=[
            SourceAssertion(
                assertion_id="a1",
                original={"area_code_l3": "BOL"},
                status="native",
                mapping="equivalent",
                note="reviewed",
            )
        ],
    )
    database = Database(identity())
    database.proposal = NativeRangeProposal(
        id=proposal_id,
        identity_id=record_id,
        created_at=datetime.now(UTC),
        evidence=evidence.model_dump(mode="json"),
    )
    database.application = NativeRangeApplication(
        proposal_id=proposal_id,
        identity_id=record_id,
        applied_at=datetime.now(UTC),
        evidence={
            "added": [str(uuid7())],
            "kept": [],
            "destination_version_after": 2,
        },
    )
    response = service.inspect_proposal(as_session(database), record_id, proposal_id)
    assert response.application is not None
    assert len(response.application.added) == 1
    with pytest.raises(service.EnrichmentNotFoundError):
        service.inspect_proposal(as_session(database), uuid7(), proposal_id)


def test_apply_validates_selection_and_applies_additive_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = identity()
    linked = link_for(record)
    added, existing = uuid7(), uuid7()
    evidence = ProposalEvidence(
        link_version=linked.version,
        identity_snapshot=service.identity_snapshot(cast(BotanicalIdentity, record)),
        destination_version=3,
        current_ids=[existing],
        source=metadata(),
        taxon=taxon(),
        retrieved_at=datetime.now(UTC),
        crosswalk_version=CROSSWALK_VERSION,
        choices=[
            RangeChoice(
                place_id=added,
                name="Bolivia",
                path="South America / Bolivia",
                code="BO",
                change="ADD",
            ),
            RangeChoice(
                place_id=existing,
                name="Italy",
                path="Europe / Italy",
                code="IT",
                change="KEEP",
            ),
        ],
        assertions=[],
    )
    proposal = ProposalResponse(
        **evidence.model_dump(),
        id=uuid7(),
        created_at=datetime.now(UTC),
    )
    database = Database(record, linked)
    database.places = [
        SimpleNamespace(
            id=added,
            source_name="unicode_cldr",
            source_version="48.2.1",
            source_code_type="iso_3166_1_alpha_2",
            source_code="BO",
            retired_at=None,
        )
    ]
    monkeypatch.setattr(service, "inspect_proposal", lambda *_: proposal)
    monkeypatch.setattr(service, "identity_for_review", lambda *_: record)
    versions = iter([3, 4, 4])
    monkeypatch.setattr(service, "range_version", lambda *_: next(versions))
    monkeypatch.setattr(service, "current_ids", lambda *_: [existing])

    with pytest.raises(service.EnrichmentConflictError):
        service.apply(
            as_session(database), record.id, proposal.id, ApplyWrite(selected_place_ids=[uuid7()])
        )

    result = service.apply(
        as_session(database), record.id, proposal.id, ApplyWrite(selected_place_ids=[added])
    )
    assert result.added == [added]
    assert result.kept == [existing]
    assert database.application is not None
    assert database.application.evidence["removed"] == []
    assert database.application.evidence["destination_version_after"] == 4

    database.application = None
    keep_proposal = proposal.model_copy(update={"id": uuid7(), "destination_version": 4})
    monkeypatch.setattr(service, "inspect_proposal", lambda *_: keep_proposal)
    database.places = [
        SimpleNamespace(
            id=existing,
            source_name="unicode_cldr",
            source_version="48.2.1",
            source_code_type="iso_3166_1_alpha_2",
            source_code="IT",
            retired_at=None,
        )
    ]
    monkeypatch.setattr(service, "range_version", lambda *_: 4)
    before = len(database.added)
    kept = service.apply(
        as_session(database),
        record.id,
        keep_proposal.id,
        ApplyWrite(selected_place_ids=[existing]),
    )
    assert kept.added == []
    assert kept.kept == [existing]
    assert len(database.added) == before + 1
