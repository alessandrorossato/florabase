import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid7

import pytest
from fastapi import HTTPException, Response

from florabase.auth.dependencies import AuthenticatedActor
from florabase.core.config import CookieMode, Environment, Settings
from florabase.external_botany.api import (
    _provider_http_error,
    _require_identity,
    cached_occurrences,
    clear_occurrences,
    confirm,
    occurrence_summary,
    occurrence_tile,
    read_link,
    refresh,
    refresh_occurrences,
    remove_link,
    search,
)
from florabase.external_botany.provider import (
    OccurrenceTile,
    ProviderError,
    ProviderNotFoundError,
    ProviderRateLimitedError,
    ProviderResponseError,
)
from florabase.external_botany.schemas import (
    ExternalTaxonLinkCreate,
    OccurrenceEvidence,
    OccurrenceMapSummary,
    TaxonSearchResponse,
)


def settings() -> Settings:
    return Settings(
        _env_file=None,
        environment=Environment.TEST,
        database_url="postgresql+psycopg://test:test@db/test",
        cookie_mode=CookieMode.SECURE,
        cors_origins=[],
        canonical_origin=None,
    )


def actor() -> MagicMock:
    result = MagicMock(spec=AuthenticatedActor)
    result.owner = True
    return result


def test_identity_requirement_and_provider_error_mapping() -> None:
    database = MagicMock()
    identity_id = uuid7()
    with patch("florabase.external_botany.api.get_botanical_identity", return_value=object()):
        _require_identity(database, identity_id)

    with (
        patch("florabase.external_botany.api.get_botanical_identity", return_value=None),
        pytest.raises(HTTPException) as missing,
    ):
        _require_identity(database, identity_id)
    assert missing.value.status_code == 404

    for error, expected_status in (
        (ProviderNotFoundError(), 404),
        (ProviderResponseError(), 502),
        (ProviderRateLimitedError(), 503),
        (ProviderError(), 503),
    ):
        mapped = _provider_http_error(error)
        assert mapped.status_code == expected_status
        assert isinstance(mapped.detail, dict)
        assert mapped.detail["code"] == error.code


def test_search_normalizes_query_and_translates_provider_failure() -> None:
    database = MagicMock()
    provider = MagicMock()
    identity_id = uuid7()
    expected = TaxonSearchResponse(
        provider="gbif",
        query="Acacia acuminata",
        fetched_at="2026-09-09T12:00:00Z",
        from_cache=False,
        stale=False,
        candidates=[],
    )
    with (
        patch("florabase.external_botany.api._require_identity"),
        patch(
            "florabase.external_botany.api.search_taxa",
            AsyncMock(return_value=expected),
        ) as lookup,
    ):
        result = asyncio.run(
            search(identity_id, "  Acacia   acuminata ", actor(), database, provider, settings())
        )
    assert result is expected
    assert lookup.await_args is not None
    assert lookup.await_args.args[2] == "Acacia acuminata"

    with (
        patch("florabase.external_botany.api._require_identity"),
        pytest.raises(HTTPException) as blank,
    ):
        asyncio.run(search(identity_id, "   ", actor(), database, provider, settings()))
    assert blank.value.status_code == 422

    with (
        patch("florabase.external_botany.api._require_identity"),
        patch(
            "florabase.external_botany.api.search_taxa",
            AsyncMock(side_effect=ProviderError("offline")),
        ),
        pytest.raises(HTTPException) as unavailable,
    ):
        asyncio.run(search(identity_id, "Acacia", actor(), database, provider, settings()))
    assert unavailable.value.status_code == 503


def test_read_confirm_refresh_and_remove_link_outcomes() -> None:
    database = MagicMock()
    provider = MagicMock()
    identity_id = uuid7()
    linked = object()
    response = MagicMock()

    with (
        patch("florabase.external_botany.api._require_identity"),
        patch("florabase.external_botany.api.get_link", return_value=None),
    ):
        assert read_link(identity_id, actor(), database, settings()) is None
    with (
        patch("florabase.external_botany.api._require_identity"),
        patch("florabase.external_botany.api.get_link", return_value=linked),
        patch("florabase.external_botany.api.link_response", return_value=response),
    ):
        assert read_link(identity_id, actor(), database, settings()) is response

    with (
        patch("florabase.external_botany.api._require_identity"),
        patch("florabase.external_botany.api.confirm_link", AsyncMock(return_value=linked)),
        patch("florabase.external_botany.api.link_response", return_value=response),
    ):
        result = asyncio.run(
            confirm(
                identity_id,
                ExternalTaxonLinkCreate(external_id="BSJCX", scientific_name="Acacia acuminata"),
                actor(),
                database,
                provider,
                settings(),
            )
        )
    assert result is response

    with (
        patch("florabase.external_botany.api._require_identity"),
        patch(
            "florabase.external_botany.api.confirm_link",
            AsyncMock(side_effect=ProviderNotFoundError()),
        ),
        pytest.raises(HTTPException) as not_found,
    ):
        asyncio.run(
            confirm(
                identity_id,
                ExternalTaxonLinkCreate(external_id="gone", scientific_name="Acacia acuminata"),
                actor(),
                database,
                provider,
                settings(),
            )
        )
    assert not_found.value.status_code == 404

    with (
        patch("florabase.external_botany.api._require_identity"),
        patch("florabase.external_botany.api.get_link", return_value=None),
        pytest.raises(HTTPException) as missing_link,
    ):
        asyncio.run(refresh(identity_id, actor(), database, provider, settings()))
    assert missing_link.value.status_code == 404

    with (
        patch("florabase.external_botany.api._require_identity"),
        patch("florabase.external_botany.api.get_link", return_value=linked),
        patch("florabase.external_botany.api.refresh_link", AsyncMock(return_value=linked)),
        patch("florabase.external_botany.api.link_response", return_value=response),
    ):
        assert (
            asyncio.run(refresh(identity_id, actor(), database, provider, settings())) is response
        )

    with (
        patch("florabase.external_botany.api._require_identity"),
        patch("florabase.external_botany.api.unlink", return_value=False),
        pytest.raises(HTTPException) as absent,
    ):
        remove_link(identity_id, actor(), database)
    assert absent.value.status_code == 404

    with (
        patch("florabase.external_botany.api._require_identity"),
        patch("florabase.external_botany.api.unlink", return_value=True),
    ):
        removed = remove_link(identity_id, actor(), database)
    assert removed.status_code == 204


def occurrence_response() -> OccurrenceMapSummary:
    return OccurrenceMapSummary(
        source="GBIF occurrence records",
        provider="gbif",
        external_taxon_id="Q2M4",
        taxon_scientific_name="Calopteryx splendens",
        taxon_provider_url="https://www.gbif.org/species/Q2M4",
        checklist_key="7ddf754f-d193-4cc9-b351-99906754a03b",
        checklist_name="Catalogue of Life eXtended Release",
        total_matching_records=20,
        eligible_mapped_records=17,
        retrieved_at="2026-09-12T10:00:00Z",
        quality_policy={
            "occurrence_status": "PRESENT",
            "has_coordinate": True,
            "has_geospatial_issue": False,
        },
        binning="Zoom-appropriate hexagonal occurrence-record density",
        attribution="GBIF.org and the contributing data publishers",
        provider_url="https://www.gbif.org",
        licensing_url="https://www.gbif.org/terms",
    )


def test_occurrence_summary_requires_confirmed_link_without_provider_query() -> None:
    identity_id = uuid7()
    database = MagicMock()
    provider = MagicMock()
    with (
        patch("florabase.external_botany.api._require_identity"),
        patch("florabase.external_botany.api.get_link", return_value=None),
        pytest.raises(HTTPException) as missing,
    ):
        asyncio.run(occurrence_summary(identity_id, actor(), database, provider))
    assert missing.value.status_code == 409
    provider.occurrence_count.assert_not_called()


def test_occurrence_summary_uses_link_and_translates_provider_failure() -> None:
    identity_id = uuid7()
    database = MagicMock()
    provider = MagicMock()
    linked = MagicMock(external_id="Q2M4")
    expected = occurrence_response()
    with (
        patch("florabase.external_botany.api._require_occurrence_link", return_value=linked),
        patch(
            "florabase.external_botany.api.occurrence_map_summary",
            AsyncMock(return_value=expected),
        ) as summary,
    ):
        assert asyncio.run(occurrence_summary(identity_id, actor(), database, provider)) is expected
    summary.assert_awaited_once_with(provider, linked)

    with (
        patch("florabase.external_botany.api._require_occurrence_link", return_value=linked),
        patch(
            "florabase.external_botany.api.occurrence_map_summary",
            AsyncMock(side_effect=ProviderResponseError()),
        ),
        pytest.raises(HTTPException) as malformed,
    ):
        asyncio.run(occurrence_summary(identity_id, actor(), database, provider))
    assert malformed.value.status_code == 502


def test_occurrence_tile_validates_coordinates_and_proxies_png() -> None:
    identity_id = uuid7()
    database = MagicMock()
    provider = MagicMock()
    linked = MagicMock(external_id="Q2M4")

    with pytest.raises(HTTPException) as invalid:
        asyncio.run(occurrence_tile(identity_id, 3, 8, 0, actor(), database, provider, settings()))
    assert invalid.value.status_code == 422
    provider.occurrence_tile.assert_not_called()

    provider.occurrence_tile = AsyncMock(
        return_value=OccurrenceTile(content=b"png", media_type="image/png")
    )
    with patch("florabase.external_botany.api._require_occurrence_link", return_value=linked):
        response = asyncio.run(
            occurrence_tile(identity_id, 3, 4, 2, actor(), database, provider, settings())
        )
    assert response.status_code == 200
    assert response.body == b"png"
    assert response.media_type == "image/png"
    assert response.headers["cache-control"] == "private, no-store"
    provider.occurrence_tile.assert_awaited_once_with("Q2M4", 3, 4, 2)

    provider.occurrence_tile = AsyncMock(return_value=None)
    with patch("florabase.external_botany.api._require_occurrence_link", return_value=linked):
        empty = asyncio.run(
            occurrence_tile(identity_id, 0, 0, 0, actor(), database, provider, settings())
        )
    assert empty.status_code == 204


def test_occurrence_tile_local_cache_generation_and_storage_failures() -> None:
    identity_id, generation = uuid7(), uuid7()
    database, provider = MagicMock(), MagicMock()
    linked = MagicMock(external_id="Q2M4")

    with patch("florabase.external_botany.api._require_occurrence_link", return_value=linked):
        with pytest.raises(HTTPException) as missing_generation:
            asyncio.run(
                occurrence_tile(
                    identity_id,
                    0,
                    0,
                    0,
                    actor(),
                    database,
                    provider,
                    settings(),
                    local_only=True,
                )
            )
        assert missing_generation.value.status_code == 404
        provider.occurrence_tile.assert_not_called()

        with (
            patch(
                "florabase.external_botany.api.occurrence_cache.read",
                return_value=OccurrenceEvidence(generation=uuid7()),
            ),
            pytest.raises(HTTPException) as changed,
        ):
            asyncio.run(
                occurrence_tile(
                    identity_id, 0, 0, 0, actor(), database, provider, settings(), generation
                )
            )
        assert changed.value.status_code == 409

        with (
            patch(
                "florabase.external_botany.api.occurrence_cache.read",
                return_value=OccurrenceEvidence(generation=generation),
            ),
            patch("florabase.external_botany.api.TileCache") as storage_type,
        ):
            storage_type.return_value.read.return_value = None
            with pytest.raises(HTTPException) as local_miss:
                asyncio.run(
                    occurrence_tile(
                        identity_id,
                        0,
                        0,
                        0,
                        actor(),
                        database,
                        provider,
                        settings(),
                        generation,
                        local_only=True,
                    )
                )
        assert local_miss.value.status_code == 404
        provider.occurrence_tile.assert_not_called()

        with (
            patch(
                "florabase.external_botany.api.occurrence_cache.read",
                return_value=OccurrenceEvidence(generation=generation),
            ),
            patch("florabase.external_botany.api.TileCache") as storage_type,
        ):
            storage_type.return_value.read.return_value = (
                OccurrenceTile(content=b"cached", media_type="image/png"),
                "2026-10-21T00:00:00Z",
            )
            hit = asyncio.run(
                occurrence_tile(
                    identity_id, 0, 0, 0, actor(), database, provider, settings(), generation
                )
            )
        assert hit.body == b"cached"
        provider.occurrence_tile.assert_not_called()

        with (
            patch(
                "florabase.external_botany.api.occurrence_cache.read",
                return_value=OccurrenceEvidence(generation=generation),
            ),
            patch("florabase.external_botany.api.TileCache") as storage_type,
        ):
            storage_type.return_value.read.side_effect = OSError("cache storage unavailable")
            with pytest.raises(HTTPException) as unavailable:
                asyncio.run(
                    occurrence_tile(
                        identity_id, 0, 0, 0, actor(), database, provider, settings(), generation
                    )
                )
        assert unavailable.value.status_code == 503


def test_cached_occurrence_handlers_are_local_explicit_and_owner_guarded() -> None:
    identity_id, database = uuid7(), MagicMock()
    linked = MagicMock(external_id="Q2M4")
    evidence = OccurrenceEvidence()
    response = Response()
    with (
        patch("florabase.external_botany.api._require_occurrence_link", return_value=linked),
        patch("florabase.external_botany.api.occurrence_cache.read", return_value=evidence) as read,
    ):
        assert cached_occurrences(identity_id, actor(), database, response) is evidence
    assert response.headers["cache-control"] == "private, no-store"
    read.assert_called_once_with(database, linked)

    provider = MagicMock()
    with (
        patch("florabase.external_botany.api._require_occurrence_link", return_value=linked),
        patch(
            "florabase.external_botany.api.occurrence_cache.refresh",
            AsyncMock(return_value=evidence),
        ) as refresh_cache,
    ):
        assert (
            asyncio.run(refresh_occurrences(identity_id, actor(), database, provider)) is evidence
        )
    refresh_cache.assert_awaited_once_with(database, provider, linked)

    with (
        patch("florabase.external_botany.api._require_occurrence_link", return_value=linked),
        patch(
            "florabase.external_botany.api.occurrence_cache.refresh",
            AsyncMock(side_effect=ProviderRateLimitedError()),
        ),
        pytest.raises(HTTPException) as rate_limited,
    ):
        asyncio.run(refresh_occurrences(identity_id, actor(), database, provider))
    assert rate_limited.value.status_code == 503

    with (
        patch("florabase.external_botany.api._require_occurrence_link", return_value=linked),
        patch("florabase.external_botany.api.TileCache") as storage_type,
        patch("florabase.external_botany.api.occurrence_cache.clear") as clear_cache,
    ):
        assert clear_occurrences(identity_id, actor(), database, settings()).status_code == 204
    clear_cache.assert_called_once_with(database, storage_type.return_value, linked)
