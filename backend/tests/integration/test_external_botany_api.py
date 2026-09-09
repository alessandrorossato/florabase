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
from florabase.external_botany.provider import GbifBotanicalProvider, ProviderError
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

    async def search_payload(self, query: str) -> dict[str, object]:
        self.search_calls += 1
        return self._payload("A1", query)

    async def taxon_payload(self, scientific_name: str) -> dict[str, object]:
        self.taxon_calls += 1
        if self.fail_taxon:
            raise ProviderError("fixture outage")
        external_id = "B2" if scientific_name.endswith("B2") else "A1"
        return self._payload(external_id, scientific_name)

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

        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as anonymous:
            assert (
                await anonymous.get(
                    "/api/v1/botanical-identities/01900000-0000-7000-8000-000000000001/external-taxon-link"
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
