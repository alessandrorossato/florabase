from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid7

import pytest
from sqlalchemy.orm import Session
from test_taxonomy import FAMILY, META, SECOND, SPECIES, SYNONYM, data

import florabase.explore.service as collection
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.taxonomy import service
from florabase.taxonomy.model import WfoLink
from florabase.taxonomy.schemas import TaxonomyEvidence, TaxonomyIdentity, TaxonomyLinkWrite
from florabase.taxonomy.snapshot import build_index
from florabase.taxonomy.source import SourceUnavailableError, WfoMetadata, WfoSource, WfoTaxon, path


class Result:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self.rows = rows

    def all(self) -> list[tuple[object, ...]]:
        return self.rows


class Database:
    def __init__(self, rows: list[tuple[object, ...]] | None = None) -> None:
        self.rows = rows or []
        self.links: list[WfoLink] = []
        self.identity: BotanicalIdentity | None = None
        self.added: list[object] = []
        self.deleted: list[object] = []

    def execute(self, _statement: object) -> Result:
        return Result(self.rows)

    def scalars(self, _statement: object) -> list[WfoLink]:
        return self.links

    def scalar(self, _statement: object) -> BotanicalIdentity | None:
        return self.identity

    def get(self, model: object, _key: object, **_kwargs: object) -> object | None:
        if model is BotanicalIdentity:
            return self.identity
        if model is WfoLink:
            return self.links[0] if self.links else None
        return None

    def add(self, value: object) -> None:
        self.added.append(value)
        if isinstance(value, WfoLink):
            self.links.append(value)

    def delete(self, value: object) -> None:
        self.deleted.append(value)
        self.links.remove(cast(WfoLink, value))

    def flush(self) -> None:
        pass


def as_session(database: Database) -> Session:
    return cast(Session, database)


def as_source(source: Any) -> WfoSource:
    return cast(WfoSource, source)


def identity(name: str = "Genus species") -> BotanicalIdentity:
    return BotanicalIdentity(
        id=uuid7(), scientific_name=name, updated_at=datetime(2026, 10, 9, tzinfo=UTC)
    )


@pytest.fixture
def source(tmp_path: Any) -> WfoSource:
    path = tmp_path / "taxonomy.sqlite"
    build_index(path, *data(), META)
    return WfoSource(path)


def linked(
    identity_record: BotanicalIdentity, source: WfoSource, taxon_id: str = SPECIES
) -> WfoLink:
    nodes = source.hierarchy([taxon_id])
    evidence = TaxonomyEvidence(
        source=source.metadata(),
        taxon=nodes[taxon_id],
        classification=path(nodes, taxon_id),
        identity_updated_at=identity_record.updated_at,
    )
    return WfoLink(
        identity_id=identity_record.id,
        version=uuid7(),
        external_id=taxon_id,
        evidence=evidence.model_dump(mode="json"),
        confirmed_at=datetime.now(UTC),
    )


def projection_row(
    record: BotanicalIdentity, counts: tuple[int, int, int] = (1, 1, 0)
) -> tuple[object, ...]:
    retained, current, living = counts
    return record, retained, current, living, None, 0


def test_project_counts_and_query_keep_only_matching_identity_paths(source: WfoSource) -> None:
    nodes = source.hierarchy([SPECIES, SECOND])
    first = TaxonomyIdentity(
        id=uuid7(),
        display_label="Genus species",
        scientific_name="Genus species",
        cultivar_name=None,
        common_name=None,
        representation="current",
        retained_records=3,
        current_records=2,
        living_records=0,
        matches_scope=True,
        classification_ids=[n.source_taxon_id for n in path(nodes, SPECIES)],
    )
    second = first.model_copy(
        update={
            "id": uuid7(),
            "scientific_name": "Genus second",
            "display_label": "Genus second",
            "representation": "historical",
            "current_records": 0,
            "living_records": 0,
            "classification_ids": [n.source_taxon_id for n in path(nodes, SECOND)],
        }
    )
    unresolved = first.model_copy(
        update={
            "id": uuid7(),
            "scientific_name": "Unknown plant",
            "display_label": "Unknown plant",
            "common_name": "Garden flower",
            "classification_ids": [],
        }
    )
    tree = service.project([first, second, unresolved], nodes, META, None, "flower")
    assert [i.id for i in tree.identities] == [unresolved.id]
    assert tree.unresolved == 1
    assert tree.counts == service.counts([unresolved])
    assert service.counts([first, second]).historical == 1
    assert service.project([first], nodes, None, "offline").source_available is False


def test_tree_projects_confirmed_and_unresolved_links_and_enforces_bound(
    source: WfoSource, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = identity()
    no_link = identity("Unplaced species")
    database = Database([projection_row(record), projection_row(no_link, (1, 0, 0))])
    database.links = [linked(record, source)]
    tree = service.tree(as_session(database), source)
    assert tree.source_available
    assert tree.unresolved == 1
    assert tree.identities[0].classification_ids[-1] == SPECIES
    assert tree.identities[1].unresolved_reason == "Not linked to taxonomy source"
    detail = service.node_detail(tree, FAMILY)
    assert len(detail.identities) == 1
    with pytest.raises(service.TaxonomyNotFoundError):
        service.node_detail(tree, "wfo-9999999999")

    monkeypatch.setattr(
        collection,
        "filtered_projection",
        lambda *_args, **_kwargs: SimpleNamespace(
            order_by=lambda *_a: SimpleNamespace(limit=lambda _n: object())
        ),
    )
    database.rows = [projection_row(identity())] * 5001
    with pytest.raises(service.TaxonomyConflictError, match="5,000"):
        service.tree(as_session(database), source)


def test_tree_marks_stale_and_source_unavailable_links_unresolved(source: WfoSource) -> None:
    record = identity()
    database = Database([projection_row(record)])
    old_link = linked(record, source)
    old_link.evidence = {**old_link.evidence, "identity_updated_at": "2026-10-08T00:00:00Z"}
    database.links = [old_link]
    stale = service.tree(as_session(database), source)
    assert (
        stale.identities[0].unresolved_reason
        == "Identity changed since source confirmation; review the link"
    )

    class Unavailable:
        def metadata(self) -> WfoMetadata:
            raise SourceUnavailableError("source offline")

    offline = service.tree(as_session(database), as_source(Unavailable()))
    assert not offline.source_available
    assert offline.message == "source offline"
    assert offline.identities[0].unresolved_reason == "Taxonomy source unavailable"


def test_tree_rejects_invalid_and_different_release_evidence(source: WfoSource) -> None:
    invalid_record = identity()
    release_record = identity("Genus second")
    invalid = linked(invalid_record, source)
    invalid.evidence = {"malformed": True}
    release_mismatch = linked(release_record, source, SECOND)
    release_source = cast(dict[str, object], release_mismatch.evidence["source"])
    release_mismatch.evidence = {
        **release_mismatch.evidence,
        "source": {**release_source, "checksum": "0" * 64},
    }
    database = Database([projection_row(invalid_record), projection_row(release_record)])
    database.links = [invalid, release_mismatch]

    result = service.tree(as_session(database), source)

    reasons = {item.id: item.unresolved_reason for item in result.identities}
    assert reasons[invalid_record.id] == "Stored source evidence is invalid; review the link"
    assert reasons[release_record.id] == "Source version mismatch; review the link"


def test_confirm_and_unlink_require_current_versions(source: WfoSource) -> None:
    record = identity()
    database = Database()
    database.identity = record
    payload = TaxonomyLinkWrite(
        source_taxon_id=SPECIES,
        checksum=META.checksum,
        expected_version=None,
        identity_updated_at=record.updated_at,
    )
    confirmed = service.confirm(as_session(database), record.id, payload, source)
    assert not confirmed.stale
    assert len(database.added) == 1
    with pytest.raises(service.TaxonomyConflictError):
        service.confirm(as_session(database), record.id, payload, source)
    with pytest.raises(service.TaxonomyConflictError):
        service.unlink(as_session(database), record.id, uuid7())
    service.unlink(as_session(database), record.id, confirmed.version)
    assert len(database.deleted) == 1

    database.identity = None
    with pytest.raises(service.TaxonomyNotFoundError):
        service.unlink(as_session(database), record.id, uuid7())


def test_confirm_rejects_unclassified_or_stale_source_inputs(source: WfoSource) -> None:
    record = identity()
    database = Database()
    database.identity = record
    payload = TaxonomyLinkWrite(
        source_taxon_id="wfo-0000000004",
        checksum=META.checksum,
        expected_version=None,
        identity_updated_at=record.updated_at,
    )
    with pytest.raises(service.TaxonomyConflictError, match="classified taxon"):
        service.confirm(as_session(database), record.id, payload, source)
    payload = payload.model_copy(update={"source_taxon_id": SPECIES, "checksum": "0" * 64})
    with pytest.raises(service.TaxonomyConflictError):
        service.confirm(as_session(database), record.id, payload, source)
    payload = payload.model_copy(
        update={"checksum": META.checksum, "identity_updated_at": datetime(2026, 10, 8, tzinfo=UTC)}
    )
    with pytest.raises(service.TaxonomyConflictError, match="changed"):
        service.confirm(as_session(database), record.id, payload, source)


def test_confirm_requires_existing_identity(source: WfoSource) -> None:
    record = identity()
    payload = TaxonomyLinkWrite(
        source_taxon_id=SPECIES,
        checksum=META.checksum,
        expected_version=None,
        identity_updated_at=record.updated_at,
    )
    with pytest.raises(service.TaxonomyNotFoundError):
        service.confirm(as_session(Database()), record.id, payload, source)


def test_identity_taxonomy_reports_missing_identity_and_related_peers(source: WfoSource) -> None:
    primary = identity()
    primary_link = linked(primary, source, SYNONYM)
    peer = identity("Genus second")
    database = Database([projection_row(primary), projection_row(peer)])
    database.identity = primary
    database.links = [primary_link, linked(peer, source, SECOND)]
    with pytest.raises(service.TaxonomyNotFoundError):
        service.identity_taxonomy(as_session(Database()), source, primary.id, "all", (), "")
    result = service.identity_taxonomy(as_session(database), source, primary.id, "all", (), "")
    assert result.source_available
    assert result.link is not None
    assert result.related[0].identity.id == peer.id
    assert result.related[0].relation == "Same genus"

    class Unavailable:
        def metadata(self) -> WfoMetadata:
            raise SourceUnavailableError("offline")

    unavailable = service.identity_taxonomy(
        as_session(database), as_source(Unavailable()), primary.id, "all", (), ""
    )
    assert unavailable.message == "offline"
    assert unavailable.link is not None


def test_identity_taxonomy_omits_related_peers_for_another_release(source: WfoSource) -> None:
    record = identity()
    link = linked(record, source)
    saved_source = cast(dict[str, object], link.evidence["source"])
    link.evidence = {
        **link.evidence,
        "source": {**saved_source, "version": "2025-12"},
    }
    database = Database()
    database.identity = record
    database.links = [link]

    result = service.identity_taxonomy(as_session(database), source, record.id, "all", (), "")

    assert result.source_available
    assert result.link is not None
    assert result.related == []


def test_identity_taxonomy_flags_source_placement_changed_after_confirmation(
    source: WfoSource, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = identity()
    link = linked(record, source)
    database = Database([projection_row(record)])
    database.identity = record
    database.links = [link]
    original_hierarchy = source.hierarchy

    def changed_hierarchy(_identifiers: object) -> dict[str, WfoTaxon]:
        return original_hierarchy([SECOND])

    monkeypatch.setattr(source, "hierarchy", changed_hierarchy)
    result = service.identity_taxonomy(as_session(database), source, record.id, "all", (), "")

    assert result.source_available
    assert result.message == "Source placement differs from confirmed evidence; review the link."
