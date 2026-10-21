import asyncio
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast
from uuid import uuid7

import httpx
import pytest
from sqlalchemy import Connection, Engine, delete, func, select
from sqlalchemy.orm import Session

from florabase.auth.service import bootstrap_owner
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.core.config import CookieMode, Environment, Settings, get_settings
from florabase.db.session import get_database_session
from florabase.external_botany.api import get_provider
from florabase.external_botany.model import ExternalProviderCache, ExternalTaxonLink
from florabase.external_botany.provider import GbifBotanicalProvider, OccurrenceTile, ProviderError
from florabase.external_botany.service import _taxon_key, confirm_link
from florabase.main import app

pytestmark = pytest.mark.integration

PASSWORD = "correct horse battery staple"
ORIGIN = "https://florabase.example"


def settings() -> Settings:
    return Settings.model_validate(
        {
            "environment": Environment.TEST,
            "database_url": "postgresql+psycopg://unused",
            "canonical_origin": ORIGIN,
            "cookie_mode": CookieMode.SECURE,
            "botanical_cache_ttl_seconds": 3600,
        }
    )


class StubGbifProvider:
    provider_id = "gbif"

    def __init__(self) -> None:
        self.search_calls = 0
        self.taxon_calls = 0
        self.fail_taxon = False
        self.occurrence_count_calls: list[tuple[str, bool]] = []
        self.occurrence_tile_calls: list[tuple[str, int, int, int]] = []

    async def search_payload(self, query: str) -> dict[str, object]:
        self.search_calls += 1
        return self._payload("A1", query)

    async def taxon_payload(self, scientific_name: str) -> dict[str, object]:
        self.taxon_calls += 1
        if self.fail_taxon:
            raise ProviderError("fixture outage")
        external_id = "B2" if scientific_name.endswith("B2") else "A1"
        return self._payload(external_id, scientific_name)

    async def occurrence_count(self, external_id: str, *, eligible: bool) -> int:
        self.occurrence_count_calls.append((external_id, eligible))
        return 7 if eligible else 9

    async def occurrence_tile(self, external_id: str, z: int, x: int, y: int) -> OccurrenceTile:
        self.occurrence_tile_calls.append((external_id, z, x, y))
        return OccurrenceTile(content=b"png", media_type="image/png")

    def normalize_search(self, payload: dict[str, object]) -> list[Any]:
        from florabase.external_botany.provider import GbifBotanicalProvider

        return GbifBotanicalProvider(settings()).normalize_search(payload)

    def normalize_taxon(self, payload: dict[str, object], expected_external_id: str) -> Any:
        from florabase.external_botany.provider import GbifBotanicalProvider

        return GbifBotanicalProvider(settings()).normalize_taxon(payload, expected_external_id)

    @staticmethod
    def _payload(external_id: str, name: str) -> dict[str, object]:
        return {
            "usage": {
                "key": external_id,
                "name": name,
                "canonicalName": name,
                "authorship": "L.",
                "rank": "SPECIES",
                "status": "ACCEPTED",
            },
            "classification": [
                {"key": "P", "name": "Plantae", "rank": "KINGDOM"},
                {"key": "F", "name": "Testaceae", "rank": "FAMILY"},
            ],
            "diagnostics": {"matchType": "EXACT", "confidence": 99},
        }


@pytest.fixture
def external_api(
    database_connection: Connection,
) -> Iterator[tuple[httpx.ASGITransport, StubGbifProvider]]:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        bootstrap_owner(database, "owner", PASSWORD, "Florabase Owner")
        database.commit()

    def database_override() -> Iterator[Session]:
        with Session(
            bind=database_connection, join_transaction_mode="create_savepoint"
        ) as database:
            try:
                yield database
                database.commit()
            except Exception:
                database.rollback()
                raise

    provider = StubGbifProvider()
    app.dependency_overrides[get_database_session] = database_override
    app.dependency_overrides[get_settings] = settings
    app.dependency_overrides[get_provider] = lambda: provider
    try:
        yield httpx.ASGITransport(app=app), provider
    finally:
        app.dependency_overrides.clear()


def test_authenticated_explicit_link_cache_refresh_replace_and_unlink(
    external_api: tuple[httpx.ASGITransport, StubGbifProvider],
    database_connection: Connection,
) -> None:
    transport, provider = external_api

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
            login = await client.post(
                "/api/v1/auth/login",
                json={"login_name": "owner", "password": PASSWORD},
                headers={"Origin": ORIGIN},
            )
            assert login.status_code == 200
            csrf = login.json()["csrf_token"]
            mutation_headers = {"Origin": ORIGIN, "X-CSRF-Token": csrf}
            created = await client.post(
                "/api/v1/botanical-identities",
                json={
                    "scientific_name": "Operator name",
                    "cultivar_name": "Operator cultivar",
                    "common_name": "Operator common name",
                },
                headers=mutation_headers,
            )
            assert created.status_code == 201
            identity_id = created.json()["id"]
            base = f"/api/v1/botanical-identities/{identity_id}"

            assert (await client.get(f"{base}/external-taxon-link")).json() is None
            first_search = await client.get(
                f"{base}/external-taxa/search", params={"query": "Operator name"}
            )
            second_search = await client.get(
                f"{base}/external-taxa/search", params={"query": "Operator name"}
            )
            assert first_search.status_code == second_search.status_code == 200
            assert first_search.json()["candidates"][0]["external_id"] == "A1"
            assert second_search.json()["from_cache"] is True
            assert provider.search_calls == 1
            assert (await client.get(f"{base}/external-taxon-link")).json() is None

            without_csrf = await client.put(
                f"{base}/external-taxon-link",
                json={"external_id": "A1", "scientific_name": "Provider name A1"},
            )
            assert without_csrf.status_code == 403
            arbitrary_url = await client.put(
                f"{base}/external-taxon-link",
                json={
                    "external_id": "A1",
                    "scientific_name": "Provider name A1",
                    "provider_url": "http://127.0.0.1",
                },
                headers=mutation_headers,
            )
            assert arbitrary_url.status_code == 422

            linked = await client.put(
                f"{base}/external-taxon-link",
                json={"external_id": "A1", "scientific_name": "Provider name A1"},
                headers=mutation_headers,
            )
            assert linked.status_code == 200
            assert linked.json()["provider"] == "gbif"
            assert linked.json()["provider_url"] == "https://www.gbif.org/species/A1"

            occurrence_summary = await client.get(f"{base}/occurrence-map/summary")
            assert occurrence_summary.status_code == 200
            assert occurrence_summary.json()["external_taxon_id"] == "A1"
            assert occurrence_summary.json()["total_matching_records"] == 9
            assert occurrence_summary.json()["eligible_mapped_records"] == 7
            assert set(provider.occurrence_count_calls) == {("A1", False), ("A1", True)}

            invalid_tile = await client.get(f"{base}/occurrence-map/tiles/2/4/0.png")
            assert invalid_tile.status_code == 422
            assert provider.occurrence_tile_calls == []
            tile = await client.get(
                f"{base}/occurrence-map/tiles/2/1/3.png",
                params={"url": "http://127.0.0.1/private", "supplier": "not-forwarded"},
            )
            assert tile.status_code == 200
            assert tile.content == b"png"
            assert tile.headers["cache-control"] == "private, no-store"
            assert provider.occurrence_tile_calls == [("A1", 2, 1, 3)]

            replaced = await client.put(
                f"{base}/external-taxon-link",
                json={"external_id": "B2", "scientific_name": "Provider name B2"},
                headers=mutation_headers,
            )
            assert replaced.status_code == 200
            assert replaced.json()["external_id"] == "B2"

            provider.fail_taxon = True
            refreshed = await client.post(
                f"{base}/external-taxon-link/refresh", headers=mutation_headers
            )
            assert refreshed.status_code == 200
            assert refreshed.json()["external_id"] == "B2"
            assert refreshed.json()["refresh_error"] == "provider_unavailable"

            unchanged = (await client.get(base)).json()
            assert unchanged["scientific_name"] == "Operator name"
            assert unchanged["cultivar_name"] == "Operator cultivar"
            assert unchanged["common_name"] == "Operator common name"

            removed = await client.delete(f"{base}/external-taxon-link", headers=mutation_headers)
            assert removed.status_code == 204
            assert (await client.get(f"{base}/external-taxon-link")).json() is None
            count_calls = len(provider.occurrence_count_calls)
            assert (await client.get(f"{base}/occurrence-map/summary")).status_code == 409
            assert len(provider.occurrence_count_calls) == count_calls

        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as anonymous:
            assert (
                await anonymous.get(
                    "/api/v1/botanical-identities/01900000-0000-7000-8000-000000000001/external-taxon-link"
                )
            ).status_code == 401
            assert (
                await anonymous.get(
                    "/api/v1/botanical-identities/01900000-0000-7000-8000-000000000001/occurrence-map/summary"
                )
            ).status_code == 401
            assert (
                await anonymous.get(
                    "/api/v1/botanical-identities/01900000-0000-7000-8000-000000000001/occurrence-map/tiles/0/0/0.png"
                )
            ).status_code == 401

    asyncio.run(scenario())

    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        assert database.scalar(select(func.count()).select_from(ExternalTaxonLink)) == 0
        assert database.scalar(select(func.count()).select_from(ExternalProviderCache)) == 3
        identity = database.scalar(select(BotanicalIdentity))
        assert identity is not None
        assert identity.scientific_name == "Operator name"


def test_concurrent_confirmations_converge_on_one_link_and_cache_row(
    database_engine: Engine,
) -> None:
    identity_id = uuid7()
    with Session(database_engine) as database:
        database.add(BotanicalIdentity(id=identity_id, scientific_name="Concurrent identity"))
        database.commit()

    def worker(external_id: str) -> None:
        with Session(database_engine) as database:
            asyncio.run(
                confirm_link(
                    database,
                    cast(GbifBotanicalProvider, StubGbifProvider()),
                    identity_id,
                    external_id,
                    f"Provider name {external_id}",
                    3600,
                )
            )
            database.commit()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(worker, external_id) for external_id in ("A1", "B2")]
            for future in futures:
                future.result()

        with Session(database_engine) as database:
            links = database.scalars(
                select(ExternalTaxonLink).where(
                    ExternalTaxonLink.botanical_identity_id == identity_id
                )
            ).all()
            assert len(links) == 1
            assert links[0].external_id in {"A1", "B2"}
            assert (
                database.scalar(
                    select(func.count())
                    .select_from(ExternalProviderCache)
                    .where(
                        ExternalProviderCache.resource_key.in_(
                            (
                                _taxon_key("A1", "Provider name A1"),
                                _taxon_key("B2", "Provider name B2"),
                            )
                        )
                    )
                )
                == 2
            )
    finally:
        with Session(database_engine) as database:
            database.execute(
                delete(ExternalProviderCache).where(
                    ExternalProviderCache.resource_key.in_(
                        (
                            _taxon_key("A1", "Provider name A1"),
                            _taxon_key("B2", "Provider name B2"),
                        )
                    )
                )
            )
            identity = database.get(BotanicalIdentity, identity_id)
            if identity is not None:
                database.delete(identity)
            database.commit()


def test_occurrence_snapshots_are_local_durable_authorized_and_taxon_scoped(
    external_api: tuple[httpx.ASGITransport, StubGbifProvider],
    database_connection: Connection,
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import UTC, datetime, timedelta
    from io import BytesIO
    from unittest.mock import AsyncMock

    from PIL import Image
    from sqlalchemy import update

    from florabase.external_botany.tile_cache import contract_key

    transport, provider = external_api
    app.dependency_overrides[get_settings] = lambda: settings().model_copy(
        update={"attachment_storage_root": tmp_path}
    )
    content = BytesIO()
    Image.new("RGBA", (2, 2), (10, 20, 30, 255)).save(content, format="PNG")
    tiles = AsyncMock(side_effect=[OccurrenceTile(content.getvalue(), "image/png"), None])
    monkeypatch.setattr(provider, "occurrence_tile", tiles)

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
            assert (
                await client.get(f"/api/v1/botanical-identities/{uuid7()}/occurrence-map/cache")
            ).status_code == 401
            login = await client.post(
                "/api/v1/auth/login",
                json={"login_name": "owner", "password": PASSWORD},
                headers={"Origin": ORIGIN},
            )
            headers = {"Origin": ORIGIN, "X-CSRF-Token": login.json()["csrf_token"]}
            created = await client.post(
                "/api/v1/botanical-identities",
                json={"scientific_name": "Local snapshot test"},
                headers=headers,
            )
            base = f"/api/v1/botanical-identities/{created.json()['id']}"
            linked = await client.put(
                f"{base}/external-taxon-link",
                json={"external_id": "A1", "scientific_name": "Provider A1"},
                headers=headers,
            )
            assert linked.status_code == 200
            cache = f"{base}/occurrence-map/cache"
            assert (await client.get(cache)).json()["summary"] is None
            assert provider.occurrence_count_calls == []
            assert (await client.post(cache)).status_code == 403
            first = await client.post(cache, headers=headers)
            assert first.status_code == 200
            generation = first.json()["generation"]
            tile = f"{base}/occurrence-map/tiles/1/0/0.png?generation={generation}"
            missing = await client.get(tile + "&local_only=true")
            assert missing.status_code == 404
            tiles.assert_not_awaited()
            downloaded = await client.get(tile + "&local_only=false")
            assert downloaded.status_code == 200
            assert downloaded.content == content.getvalue()
            assert (await client.get(tile + "&local_only=true")).content == content.getvalue()
            empty = f"{base}/occurrence-map/tiles/1/0/1.png?generation={generation}"
            assert (await client.get(empty + "&local_only=false")).status_code == 204
            assert (await client.get(empty + "&local_only=true")).status_code == 204
            assert tiles.await_count == 2
            with Session(
                bind=database_connection, join_transaction_mode="create_savepoint"
            ) as database:
                database.execute(
                    update(ExternalProviderCache)
                    .where(
                        ExternalProviderCache.resource_key == "occurrence-v1:" + contract_key("A1")
                    )
                    .values(fetched_at=datetime.now(UTC) - timedelta(days=2))
                )
                database.commit()
            cached = await client.get(cache)
            assert cached.json()["generation"] == generation
            assert cached.json()["stale"] is True
            assert len(provider.occurrence_count_calls) == 2
            original_count = provider.occurrence_count
            monkeypatch.setattr(
                provider, "occurrence_count", AsyncMock(side_effect=ProviderError("offline"))
            )
            fallback = await client.post(cache, headers=headers)
            assert fallback.status_code == 200
            assert fallback.json()["generation"] == generation
            assert fallback.json()["provider_error"] == "provider_unavailable"
            assert (await client.get(tile + "&local_only=true")).status_code == 200
            monkeypatch.setattr(provider, "occurrence_count", original_count)
            refreshed = await client.post(cache, headers=headers)
            assert refreshed.json()["generation"] != generation
            assert (await client.get(tile + "&local_only=true")).status_code == 409
            changed = await client.put(
                f"{base}/external-taxon-link",
                json={"external_id": "B2", "scientific_name": "Provider B2"},
                headers=headers,
            )
            assert changed.status_code == 200
            assert (await client.get(cache)).json()["summary"] is None
            assert (await client.get(tile + "&local_only=false")).status_code == 409
            assert tiles.await_count == 2
            assert (await client.delete(cache)).status_code == 403
            assert (await client.delete(cache, headers=headers)).status_code == 204

    asyncio.run(scenario())
