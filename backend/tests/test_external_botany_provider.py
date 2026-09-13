import asyncio

import httpx
import pytest

from florabase.core.config import CookieMode, Environment, Settings
from florabase.external_botany.provider import (
    GBIF_COL_XR_CHECKLIST_KEY,
    MAX_OCCURRENCE_TILE_BYTES,
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


def test_occurrence_counts_use_exact_opaque_col_xr_taxon_and_quality_policy() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url.path == "/v1/occurrence/search"
        assert request.url.params["taxon_key"] == "Q2M4"
        assert request.url.params["checklistKey"] == GBIF_COL_XR_CHECKLIST_KEY
        assert request.url.params["occurrenceStatus"] == "PRESENT"
        assert request.url.params["limit"] == "0"
        assert "scientificName" not in request.url.params
        return httpx.Response(200, json={"count": 17})

    provider = GbifBotanicalProvider(settings(), httpx.MockTransport(handler))
    assert asyncio.run(provider.occurrence_count("Q2M4", eligible=False)) == 17
    assert asyncio.run(provider.occurrence_count("Q2M4", eligible=True)) == 17
    assert "hasCoordinate" not in requests[0].url.params
    assert "hasGeospatialIssue" not in requests[0].url.params
    assert requests[1].url.params["hasCoordinate"] == "true"
    assert requests[1].url.params["hasGeospatialIssue"] == "false"


@pytest.mark.parametrize("count", [None, -1, True, "17", 17.5])
def test_occurrence_count_rejects_malformed_provider_values(count: object) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"count": count})

    provider = GbifBotanicalProvider(settings(), httpx.MockTransport(handler))
    with pytest.raises(ProviderResponseError):
        asyncio.run(provider.occurrence_count("Q2M4", eligible=True))


def test_occurrence_tile_is_fixed_hex_png_query_without_forwarded_metadata() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.gbif.org"
        assert request.url.path == "/v2/map/occurrence/adhoc/3/4/2@Hx.png"
        assert dict(request.url.params) == {
            "srs": "EPSG:3857",
            "bin": "hex",
            "hexPerTile": "51",
            "mode": "GEO_BOUNDS",
            "style": "purpleYellow-noborder.poly",
            "taxonKey": "Q2M4",
            "checklistKey": GBIF_COL_XR_CHECKLIST_KEY,
            "occurrenceStatus": "PRESENT",
            "hasCoordinate": "true",
            "hasGeospatialIssue": "false",
        }
        assert set(request.headers).isdisjoint(
            {"cookie", "x-csrf-token", "x-florabase-record", "authorization"}
        )
        return httpx.Response(
            200,
            content=b"\x89PNG\r\n\x1a\nfixture",
            headers={"Content-Type": "image/png"},
        )

    provider = GbifBotanicalProvider(settings(), httpx.MockTransport(handler))
    tile = asyncio.run(provider.occurrence_tile("Q2M4", 3, 4, 2))
    assert tile is not None
    assert tile.content == b"\x89PNG\r\n\x1a\nfixture"
    assert tile.media_type == "image/png"


def test_occurrence_tile_handles_empty_and_rejects_non_png_or_oversize() -> None:
    async def empty_handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(204)

    provider = GbifBotanicalProvider(settings(), httpx.MockTransport(empty_handler))
    assert asyncio.run(provider.occurrence_tile("Q2M4", 0, 0, 0)) is None

    async def non_png_handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"detail": "not an image"})

    provider = GbifBotanicalProvider(settings(), httpx.MockTransport(non_png_handler))
    with pytest.raises(ProviderResponseError):
        asyncio.run(provider.occurrence_tile("Q2M4", 0, 0, 0))

    async def malformed_png_handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-png", headers={"Content-Type": "image/png"})

    provider = GbifBotanicalProvider(settings(), httpx.MockTransport(malformed_png_handler))
    with pytest.raises(ProviderResponseError):
        asyncio.run(provider.occurrence_tile("Q2M4", 0, 0, 0))

    async def oversized_handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"x",
            headers={
                "Content-Type": "image/png",
                "Content-Length": str(MAX_OCCURRENCE_TILE_BYTES + 1),
            },
        )

    provider = GbifBotanicalProvider(settings(), httpx.MockTransport(oversized_handler))
    with pytest.raises(ProviderResponseError):
        asyncio.run(provider.occurrence_tile("Q2M4", 0, 0, 0))


def test_occurrence_tile_translates_timeout_and_upstream_failure() -> None:
    async def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    provider = GbifBotanicalProvider(settings(), httpx.MockTransport(timeout_handler))
    with pytest.raises(ProviderError):
        asyncio.run(provider.occurrence_tile("Q2M4", 0, 0, 0))

    async def failure_handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    provider = GbifBotanicalProvider(settings(), httpx.MockTransport(failure_handler))
    with pytest.raises(ProviderError):
        asyncio.run(provider.occurrence_tile("Q2M4", 0, 0, 0))
