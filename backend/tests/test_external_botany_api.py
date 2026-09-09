import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid7

import pytest
from fastapi import HTTPException

from florabase.auth.dependencies import AuthenticatedActor
from florabase.core.config import CookieMode, Environment, Settings
from florabase.external_botany.api import (
    _provider_http_error,
    _require_identity,
    confirm,
    read_link,
    refresh,
    remove_link,
    search,
)
from florabase.external_botany.provider import (
    ProviderError,
    ProviderNotFoundError,
    ProviderRateLimitedError,
    ProviderResponseError,
)
from florabase.external_botany.schemas import ExternalTaxonLinkCreate, TaxonSearchResponse


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
