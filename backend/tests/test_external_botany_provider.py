import asyncio

import httpx
import pytest

from florabase.core.config import CookieMode, Environment, Settings
from florabase.external_botany.provider import (
    GBIF_COL_XR_CHECKLIST_KEY,
    GbifBotanicalProvider,
    ProviderError,
    ProviderNotFoundError,
    ProviderRateLimitedError,
    ProviderResponseError,
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


def response_payload() -> dict[str, object]:
    return {
        "usage": {
            "key": "BSJCX",
            "name": "Acacia acuminata Benth.",
            "canonicalName": "Acacia acuminata",
            "authorship": "Benth.",
            "rank": "SPECIES",
        },
        "acceptedUsage": {"key": "BSJCX", "name": "Acacia acuminata Benth."},
        "taxonomicStatus": "ACCEPTED",
        "classification": [
            {"key": "P", "name": "Plantae", "rank": "KINGDOM"},
            {"key": "623QT", "name": "Fabaceae", "rank": "FAMILY"},
            {"key": "C8VYK", "name": "Acacia", "rank": "GENUS"},
        ],
        "diagnostics": {"matchType": "EXACT", "confidence": 99},
        "issues": ["TAXON_ID_NOT_FOUND"],
    }


def test_gbif_match_uses_col_xr_and_normalizes_candidates() -> None:
    payload = response_payload()
    synonym = {
        "usage": {
            "key": "SYN1",
            "name": "Racosperma acuminatum (Benth.) Pedley",
            "canonicalName": "Racosperma acuminatum",
            "authorship": "(Benth.) Pedley",
            "rank": "SPECIES",
        },
        "acceptedUsage": {"key": "BSJCX", "name": "Acacia acuminata Benth."},
        "taxonomicStatus": "SYNONYM",
        "classification": [{"key": "P", "name": "Plantae", "rank": "KINGDOM"}],
        "diagnostics": {"matchType": "FUZZY", "confidence": 82},
    }
    payload["alternatives"] = [synonym]

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["checklistKey"] == GBIF_COL_XR_CHECKLIST_KEY
        assert request.url.params["scientificName"] == "Acacia acuminata"
        assert request.headers["User-Agent"].startswith("Florabase/")
        return httpx.Response(200, json=payload)

    provider = GbifBotanicalProvider(settings(), httpx.MockTransport(handler))
    raw = asyncio.run(provider.search_payload("Acacia acuminata"))
    candidates = provider.normalize_search(raw)
    assert [candidate.external_id for candidate in candidates] == ["BSJCX", "SYN1"]
    assert candidates[0].canonical_name == "Acacia acuminata"
    assert candidates[0].authorship == "Benth."
    assert candidates[0].rank == "SPECIES"
    assert candidates[0].family == "Fabaceae"
    assert candidates[0].kingdom == "Plantae"
    assert candidates[0].match_type == "EXACT"
    assert candidates[0].confidence == 99
    assert candidates[0].issues == ["TAXON_ID_NOT_FOUND"]
    assert candidates[1].taxonomic_status == "SYNONYM"
    assert candidates[1].accepted_name == "Acacia acuminata Benth."


def test_gbif_confirms_a_taxon_with_name_match_and_exact_opaque_id() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/species/match"
        assert request.url.params["scientificName"] == "Acacia acuminata"
        assert request.url.params["checklistKey"] == GBIF_COL_XR_CHECKLIST_KEY
        return httpx.Response(200, json=response_payload())

    provider = GbifBotanicalProvider(settings(), httpx.MockTransport(handler))
    raw = asyncio.run(provider.taxon_payload("Acacia acuminata"))
    assert provider.normalize_taxon(raw, "BSJCX").external_id == "BSJCX"
    with pytest.raises(ProviderNotFoundError):
        provider.normalize_taxon(raw, "not-the-selected-id")


@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [
        (404, ProviderNotFoundError),
        (429, ProviderRateLimitedError),
        (500, ProviderError),
        (400, ProviderResponseError),
    ],
)
def test_gbif_translates_http_failures(status_code: int, error_type: type[ProviderError]) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"message": "upstream detail is not exposed"})

    provider = GbifBotanicalProvider(settings(), httpx.MockTransport(handler))
    with pytest.raises(error_type):
        asyncio.run(provider.taxon_payload("Acacia acuminata"))


def test_gbif_translates_timeout_and_malformed_payloads() -> None:
    async def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(ProviderError):
        asyncio.run(
            GbifBotanicalProvider(settings(), httpx.MockTransport(timeout_handler)).search_payload(
                "Acer"
            )
        )

    async def malformed_handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

    with pytest.raises(ProviderResponseError):
        asyncio.run(
            GbifBotanicalProvider(
                settings(), httpx.MockTransport(malformed_handler)
            ).search_payload("Acer")
        )


def test_gbif_rejects_malformed_shapes_and_normalizes_no_match() -> None:
    provider = GbifBotanicalProvider(settings())
    assert provider.normalize_search({"diagnostics": {"matchType": "NONE"}}) == []
    with pytest.raises(ProviderResponseError):
        provider.normalize_search({"usage": [], "alternatives": []})
    with pytest.raises(ProviderResponseError):
        provider.normalize_search({**response_payload(), "classification": {}})
