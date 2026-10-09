import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier
from typing import Any
from uuid import uuid7

import httpx
import pytest
from sqlalchemy import Connection, Engine, event
from sqlalchemy.orm import Session
from test_taxonomy import GENUS, META, SECOND, SPECIES, SYNONYM, data

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.explore import native_ranges
from florabase.explore.schemas import CollectionRecordCategory
from florabase.main import app
from florabase.plants.model import Plant
from florabase.seed_lots.model import SeedLot
from florabase.taxonomy import service
from florabase.taxonomy.api import source_dependency
from florabase.taxonomy.model import WfoLink
from florabase.taxonomy.schemas import TaxonomyEvidence, TaxonomyLinkWrite
from florabase.taxonomy.snapshot import build_index
from florabase.taxonomy.source import CHECKSUM, ROOT, SourceUnavailableError, WfoSource, path

from .test_species_distribution import identity
from .test_supplier_api import ORIGIN
from .test_supplier_api import authenticated_browser as authenticated_browser

pytestmark = pytest.mark.integration


def request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
) -> tuple[int, dict[str, str], Any]:
    async def perform() -> tuple[int, dict[str, str], Any]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=ORIGIN
        ) as client:
            response = await client.request(method, url, headers=headers, json=body)
            return (
                response.status_code,
                dict(response.headers),
                response.json() if response.content else None,
            )

    return asyncio.run(perform())


@pytest.fixture
def source(tmp_path: Path) -> WfoSource:
    p = tmp_path / "wfo.sqlite"
    build_index(p, *data(), META)
    return WfoSource(p)


def link(db: Session, taxon: Any, external: str, source: WfoSource) -> Any:
    return service.confirm(
        db,
        taxon.id,
        TaxonomyLinkWrite(
            source_taxon_id=external,
            checksum=CHECKSUM,
            expected_version=None,
            identity_updated_at=taxon.updated_at,
        ),
        source,
    )


def test_collection_pruning_counts_filters_search_related_stale_and_query_bounds(
    database_connection: Connection, source: WfoSource
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        a, b, c, d, unlinked, reference = [
            identity(db, name)
            for name in ("Alpha", "Beta", "Synonym", "Historical", "Unlinked", "Reference")
        ]
        db.add_all(
            [
                Plant(botanical_identity_id=a.id, direct_origin_kind="unknown"),
                SeedLot(botanical_identity_id=a.id),
                SeedLot(botanical_identity_id=b.id),
                SeedLot(botanical_identity_id=c.id),
                SeedLot(botanical_identity_id=d.id, lifecycle="exhausted"),
                SeedLot(botanical_identity_id=unlinked.id),
            ]
        )
        db.flush()
        for ident, external in (
            (a, SPECIES),
            (b, SECOND),
            (c, SYNONYM),
            (d, SPECIES),
            (reference, SECOND),
        ):
            link(db, ident, external, source)
        statements: list[str] = []

        def count(_conn: Any, _cursor: Any, sql: str, _params: Any, _ctx: Any, _many: Any) -> None:
            if sql.lstrip().upper().startswith(("SELECT", "WITH")):
                statements.append(sql)

        event.listen(database_connection, "before_cursor_execute", count)
        try:
            statements.clear()
            started = time.monotonic()
            result = service.tree(db, source)
            elapsed = time.monotonic() - started
            assert len(statements) == 2
            assert result.counts.represented == 5
            assert result.unresolved == 1
            root = service.node_detail(result, ROOT)
            assert root.node.counts.model_dump() == {
                "represented": 4,
                "living": 1,
                "current": 3,
                "historical": 1,
            }
            assert service.node_detail(result, GENUS).node.counts.represented == 4
            assert len(result.nodes) == 6
            assert reference.id not in {i.id for i in result.identities}
            assert next(i for i in result.identities if i.id == c.id).synonym_of == "Genus species"
            assert service.tree(db, source, q="family").counts.represented == 4
            assert service.tree(db, source, q="%_").counts.represented == 0
            for scope in ("all", "living", "current", "historical"):
                for categories in (
                    [],
                    [CollectionRecordCategory.SEED_LOT],
                    [CollectionRecordCategory.PLANT],
                    [CollectionRecordCategory.SEED_LOT, CollectionRecordCategory.PLANT],
                ):
                    actual = service.tree(db, source, scope=scope, record=categories)
                    expected = native_ranges.list_identities(db, scope=scope, record=categories)
                    assert {i.id for i in actual.identities} == {i.id for i in expected.items}
            assert (
                service.tree(
                    db, source, scope="living", record=[CollectionRecordCategory.SEED_LOT]
                ).counts.represented
                == 0
            )
            related = service.identity_taxonomy(db, source, a.id, "current", (), "")
            assert {r.identity.id for r in related.related} == {b.id, c.id}
            assert related.related[0].relation == "Same source taxon"
            assert related.related[1].relation == "Same genus"
            assert (
                service.identity_taxonomy(db, source, a.id, "historical", (), "")
                .related[0]
                .identity.id
                == d.id
            )
            assert service.tree(db, source).model_dump_json() == result.model_dump_json()
            with pytest.raises(service.TaxonomyNotFoundError):
                service.node_detail(result, "wfo-9999999999")
            missing = service.tree(db, WfoSource(None))
            assert not missing.source_available
            assert missing.unresolved == 5
            assert missing.nodes == []
            assert (
                service.identity_taxonomy(db, WfoSource(None), a.id, "all", (), "").link is not None
            )
            stored = db.get(WfoLink, a.id)
            assert stored is not None
            assert service.link_response(stored, a).evidence.source.checksum == CHECKSUM
            previous = stored.evidence
            old = TaxonomyEvidence.model_validate(previous)
            stored.evidence = old.model_copy(
                update={"source": old.source.model_copy(update={"version": "2025-12"})}
            ).model_dump(mode="json")
            db.flush()
            mismatch = next(i for i in service.tree(db, source).identities if i.id == a.id)
            assert mismatch.unresolved_reason == "Source version mismatch; review the link"
            assert service.identity_taxonomy(db, source, a.id, "all", (), "").related == []
            stored.evidence = previous
            db.flush()
            a.scientific_name = "Changed " + uuid7().hex
            db.flush()
            reason = next(
                i for i in service.tree(db, source).identities if i.id == a.id
            ).unresolved_reason
            assert reason is not None
            assert reason.startswith("Identity changed")
            print(  # noqa: T201 -- explicit performance evidence
                "TAXONOMY measured",
                elapsed,
                "seconds",
                len(result.model_dump_json()),
                "response bytes",
                len(result.nodes),
                "nodes",
            )
        finally:
            event.remove(database_connection, "before_cursor_execute", count)


def test_confirmation_revalidation_and_unlink_preserve_identity(
    database_connection: Connection, source: WfoSource
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        a = identity(db)
        original = a.scientific_name
        first = link(db, a, SPECIES, source)
        payload = TaxonomyLinkWrite(
            source_taxon_id=SECOND,
            checksum=CHECKSUM,
            expected_version=None,
            identity_updated_at=a.updated_at,
        )
        with pytest.raises(service.TaxonomyConflictError):
            service.confirm(db, a.id, payload, source)
        payload.expected_version = first.version
        payload.checksum = "0" * 64
        with pytest.raises(service.TaxonomyConflictError):
            service.confirm(db, a.id, payload, source)
        payload.checksum = CHECKSUM
        second = service.confirm(db, a.id, payload, source)
        assert a.scientific_name == original
        assert second.version != first.version
        with pytest.raises(service.TaxonomyConflictError):
            service.unlink(db, a.id, first.version)
        service.unlink(db, a.id, second.version)
        assert db.get(WfoLink, a.id) is None
        assert a.scientific_name == original
        with pytest.raises(SourceUnavailableError):
            link(db, a, SPECIES, WfoSource(None))


def test_authenticated_taxonomy_api_and_no_network(
    authenticated_browser: tuple[str, str], source: WfoSource
) -> None:
    cookie, csrf = authenticated_browser
    reader = {"cookie": cookie}
    writer = {"cookie": cookie, "origin": ORIGIN, "x-csrf-token": csrf}
    app.dependency_overrides[source_dependency] = lambda: source
    try:
        assert request("GET", "/api/v1/explore/taxonomy/tree")[0] == 401
        status, _, response = request("GET", "/api/v1/explore/taxonomy/tree", headers=reader)
        assert status == 200
        assert response["source_available"]
        assert (
            request("GET", "/api/v1/explore/taxonomy/tree?scope=invalid", headers=reader)[0] == 422
        )
        assert (
            request("GET", "/api/v1/explore/taxonomy/tree?record=invalid", headers=reader)[0] == 422
        )
        assert (
            request("GET", "/api/v1/explore/taxonomy/nodes/wfo-9999999999", headers=reader)[0]
            == 404
        )
        status, _, record = request(
            "POST",
            "/api/v1/botanical-identities",
            headers=writer,
            body={"scientific_name": "API " + uuid7().hex},
        )
        assert status == 201
        prefix = f"/api/v1/botanical-identities/{record['id']}/taxonomy"
        assert request("GET", prefix + "/candidates?q=Genus", headers=reader)[0] == 200
        payload = {
            "source_taxon_id": SPECIES,
            "checksum": CHECKSUM,
            "expected_version": None,
            "identity_updated_at": record["updated_at"],
        }
        assert request("PUT", prefix + "/link", body=payload, headers=reader)[0] == 403
        status, _, confirmed = request("PUT", prefix + "/link", body=payload, headers=writer)
        assert status == 200
        assert request("PUT", prefix + "/link", body=payload, headers=writer)[0] == 409
        assert (
            request("GET", prefix, headers=reader)[2]["link"]["evidence"]["taxon"][
                "source_taxon_id"
            ]
            == SPECIES
        )
        assert request("DELETE", prefix + "?bad=ignored", headers=writer)[0] == 405
        assert (
            request("DELETE", prefix + f"/link?version={confirmed['version']}", headers=writer)[0]
            == 204
        )
    finally:
        app.dependency_overrides.pop(source_dependency, None)


def test_representative_collection_constant_query_count(
    database_connection: Connection, source: WfoSource
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        template = TaxonomyEvidence(
            source=META,
            taxon=source.hierarchy([SPECIES])[SPECIES],
            classification=path(source.hierarchy([SPECIES]), SPECIES),
            identity_updated_at=datetime.now(UTC),
        )
        for index in range(500):
            item = identity(db, f"Performance {index:04d}")
            db.add_all(
                [
                    SeedLot(botanical_identity_id=item.id),
                    WfoLink(
                        identity_id=item.id,
                        external_id=SPECIES,
                        evidence=template.model_copy(
                            update={"identity_updated_at": item.updated_at}
                        ).model_dump(mode="json"),
                    ),
                ]
            )
        db.flush()
        selects: list[str] = []

        def count(_conn: Any, _cursor: Any, sql: str, _params: Any, _ctx: Any, _many: Any) -> None:
            if sql.lstrip().upper().startswith(("SELECT", "WITH")):
                selects.append(sql)

        event.listen(database_connection, "before_cursor_execute", count)
        try:
            started = time.monotonic()
            result = service.tree(db, source)
            elapsed = time.monotonic() - started
            assert len(selects) == 2
            assert result.counts.represented == 500
            assert result.unresolved == 0
            assert len(result.nodes) == 5
            print(  # noqa: T201 -- explicit performance evidence
                "TAXONOMY 500 identities",
                elapsed,
                "seconds",
                len(result.model_dump_json().encode()),
                "response bytes",
                len(result.nodes),
                "nodes",
                len(selects),
                "PostgreSQL SELECTs",
            )
        finally:
            event.remove(database_connection, "before_cursor_execute", count)


def test_concurrent_confirmations_revalidate_expected_absence(
    database_engine: Engine, source: WfoSource
) -> None:
    with Session(database_engine) as db:
        item = identity(db, "Concurrent")
        ident, revision = item.id, item.updated_at
        db.commit()
    barrier = Barrier(2)

    def confirm_one(external: str) -> str:
        with Session(database_engine) as db:
            barrier.wait(timeout=10)
            try:
                service.confirm(
                    db,
                    ident,
                    TaxonomyLinkWrite(
                        source_taxon_id=external,
                        checksum=CHECKSUM,
                        expected_version=None,
                        identity_updated_at=revision,
                    ),
                    source,
                )
                db.commit()
                return "confirmed"
            except service.TaxonomyConflictError:
                db.rollback()
                return "conflict"

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(confirm_one, [SPECIES, SECOND]))
        assert sorted(outcomes) == ["confirmed", "conflict"]
        with Session(database_engine) as db:
            stored = db.get(WfoLink, ident)
            assert stored is not None
            assert stored.external_id in {SPECIES, SECOND}
    finally:
        with Session(database_engine) as db:
            existing = db.get(BotanicalIdentity, ident)
            assert existing is not None
            db.delete(existing)
            db.commit()
