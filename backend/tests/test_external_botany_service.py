import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid7

import pytest

from florabase.external_botany.model import ExternalProviderCache, ExternalTaxonLink
from florabase.external_botany.provider import ProviderError
from florabase.external_botany.schemas import TaxonCandidate
from florabase.external_botany.service import (
    _payload,
    confirm_link,
    get_link,
    link_response,
    refresh_link,
    search_taxa,
    unlink,
)


def candidate(*, external_id: str = "BSJCX", name: str = "Acacia acuminata") -> TaxonCandidate:
    return TaxonCandidate(
        external_id=external_id,
        scientific_name=name,
        canonical_name=name,
        rank="SPECIES",
        taxonomic_status="ACCEPTED",
        kingdom="Plantae",
        family="Fabaceae",
        genus="Acacia",
    )


def link(*, refreshed_at: datetime | None = None) -> ExternalTaxonLink:
    now = datetime.now(UTC)
    return ExternalTaxonLink(
        id=uuid7(),
        botanical_identity_id=uuid7(),
        provider="gbif",
        external_id="BSJCX",
        scientific_name="Acacia acuminata",
        canonical_name="Acacia acuminata",
        authorship=None,
        rank="SPECIES",
        taxonomic_status="ACCEPTED",
        accepted_external_id=None,
        accepted_name=None,
        kingdom="Plantae",
        phylum=None,
        class_name=None,
        order_name=None,
        family="Fabaceae",
        genus="Acacia",
        linked_at=now,
        last_refreshed_at=refreshed_at or now,
        last_refresh_attempt_at=now,
        refresh_error=None,
    )


def test_payload_uses_fresh_cache_and_stale_fallback() -> None:
    database = MagicMock()
    provider = MagicMock()
    provider.provider_id = "gbif"
    cached = ExternalProviderCache(
        provider="gbif",
        resource_key="key",
        fetched_at=datetime.now(UTC),
        payload={"cached": True},
    )
    database.get.return_value = cached
    fetch = AsyncMock(return_value={"fresh": True})

    result = asyncio.run(_payload(database, provider, "key", fetch, 3600))
    assert result == ({"cached": True}, cached.fetched_at, True, False, None)
    fetch.assert_not_awaited()

    cached.fetched_at = datetime.now(UTC) - timedelta(days=2)
    fetch.side_effect = ProviderError("offline")
    result = asyncio.run(
        _payload(database, provider, "key", fetch, 3600, allow_stale_on_error=True)
    )
    assert result == (
        {"cached": True},
        cached.fetched_at,
        True,
        True,
        "provider_unavailable",
    )

    with pytest.raises(ProviderError):
        asyncio.run(_payload(database, provider, "key", fetch, 3600))


def test_payload_persists_provider_result_and_search_normalizes_it() -> None:
    database = MagicMock()
    database.get.return_value = None
    provider = MagicMock()
    provider.provider_id = "gbif"
    provider.search_payload = AsyncMock(return_value={"usage": {"key": "BSJCX"}})
    provider.normalize_search.return_value = [candidate()]

    result = asyncio.run(search_taxa(database, provider, "Acacia  acuminata", 3600))

    assert result.provider == "gbif"
    assert result.query == "Acacia  acuminata"
    assert result.from_cache is False
    assert result.candidates[0].external_id == "BSJCX"
    database.execute.assert_called_once()
    database.flush.assert_called_once_with()


def test_confirm_link_uses_atomic_upsert_and_lookup_is_provider_scoped() -> None:
    database = MagicMock()
    provider = MagicMock()
    provider.provider_id = "gbif"
    identity_id = uuid7()
    persisted = link()
    database.scalar.return_value = persisted
    fetched_at = datetime.now(UTC)

    with patch(
        "florabase.external_botany.service._fetch_taxon",
        AsyncMock(return_value=(candidate(), fetched_at, False, None)),
    ):
        result = asyncio.run(
            confirm_link(database, provider, identity_id, "BSJCX", "Acacia acuminata", 3600)
        )

    assert result is persisted
    database.scalar.assert_called_once()
    database.flush.assert_called_once_with()

    database.reset_mock()
    database.scalar.return_value = persisted
    assert get_link(database, identity_id) is persisted
    database.scalar.assert_called_once()


def test_refresh_updates_success_and_preserves_link_on_provider_failures() -> None:
    database = MagicMock()
    provider = MagicMock()
    current = link()
    fetched_at = datetime.now(UTC)
    updated = candidate(external_id="BSJCX", name="Acacia acuminata Benth.")

    with patch(
        "florabase.external_botany.service._fetch_taxon",
        AsyncMock(return_value=(updated, fetched_at, False, None)),
    ):
        assert asyncio.run(refresh_link(database, provider, current, 3600)) is current
    assert current.scientific_name == "Acacia acuminata Benth."
    assert current.last_refreshed_at == fetched_at
    assert current.refresh_error is None

    with patch(
        "florabase.external_botany.service._fetch_taxon",
        AsyncMock(return_value=(updated, fetched_at, True, "provider_unavailable")),
    ):
        asyncio.run(refresh_link(database, provider, current, 3600))
    assert current.refresh_error == "provider_unavailable"

    with patch(
        "florabase.external_botany.service._fetch_taxon",
        AsyncMock(side_effect=ProviderError("offline")),
    ):
        asyncio.run(refresh_link(database, provider, current, 3600))
    assert current.refresh_error == "provider_unavailable"
    assert database.flush.call_count == 3


def test_unlink_and_link_response_report_database_and_freshness_state() -> None:
    database = MagicMock()
    database.execute.return_value.rowcount = 1
    identity_id = uuid7()
    assert unlink(database, identity_id)

    database.execute.return_value.rowcount = 0
    assert not unlink(database, identity_id)

    stale_link = link(refreshed_at=datetime.now(UTC) - timedelta(days=2))
    response = link_response(stale_link, 3600)
    assert response.stale is True
    assert response.provider_display_name == "GBIF"
    assert response.provider_url == "https://www.gbif.org/species/BSJCX"
