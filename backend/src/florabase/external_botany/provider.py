import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx

from florabase.core.config import Settings
from florabase.external_botany.schemas import TaxonCandidate

GBIF_PROVIDER_ID = "gbif"
GBIF_COL_XR_CHECKLIST_KEY = "7ddf754f-d193-4cc9-b351-99906754a03b"
GBIF_API_BASE_URL = "https://api.gbif.org"
MAX_PROVIDER_RESPONSE_BYTES = 1_000_000
MAX_OCCURRENCE_TILE_BYTES = 2_000_000


@dataclass(frozen=True)
class OccurrenceTile:
    content: bytes
    media_type: str


class ProviderError(Exception):
    code = "provider_unavailable"


class ProviderNotFoundError(ProviderError):
    code = "provider_taxon_not_found"


class ProviderRateLimitedError(ProviderError):
    code = "provider_rate_limited"


class ProviderResponseError(ProviderError):
    code = "provider_invalid_response"


class GbifBotanicalProvider:
    """Narrow GBIF taxon and occurrence adapter with fixed CoL XR semantics.

    See https://techdocs.gbif.org/en/data-processing/taxonomy-interpretation:
    checklistKey selects Catalogue of Life eXtended Release, while an omitted key
    defaults to the discontinued legacy backbone.
    """

    provider_id = GBIF_PROVIDER_ID

    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self._timeout = httpx.Timeout(
            connect=settings.botanical_provider_connect_timeout_seconds,
            read=settings.botanical_provider_read_timeout_seconds,
            write=settings.botanical_provider_read_timeout_seconds,
            pool=settings.botanical_provider_connect_timeout_seconds,
        )
        self._transport = transport

    async def search_payload(self, query: str) -> dict[str, object]:
        return await self._get(
            "/v2/species/match",
            {"scientificName": query, "checklistKey": GBIF_COL_XR_CHECKLIST_KEY},
        )

    async def taxon_payload(self, scientific_name: str) -> dict[str, object]:
        return await self._get(
            "/v2/species/match",
            {"scientificName": scientific_name, "checklistKey": GBIF_COL_XR_CHECKLIST_KEY},
        )

    async def occurrence_count(self, external_id: str, *, eligible: bool) -> int:
        params = {
            "taxon_key": external_id,
            "checklistKey": GBIF_COL_XR_CHECKLIST_KEY,
            "occurrenceStatus": "PRESENT",
            "limit": "0",
        }
        if eligible:
            params.update(hasCoordinate="true", hasGeospatialIssue="false")
        payload = await self._get("/v1/occurrence/search", params)
        count = payload.get("count")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ProviderResponseError("GBIF occurrence count was malformed")
        return count

    async def occurrence_tile(
        self, external_id: str, z: int, x: int, y: int
    ) -> OccurrenceTile | None:
        params = {
            "srs": "EPSG:3857",
            "bin": "hex",
            "hexPerTile": "51",
            "mode": "GEO_BOUNDS",
            "style": "purpleYellow-noborder.poly",
            "taxonKey": external_id,
            "checklistKey": GBIF_COL_XR_CHECKLIST_KEY,
            "occurrenceStatus": "PRESENT",
            "hasCoordinate": "true",
            "hasGeospatialIssue": "false",
        }
        return await self._get_tile(f"/v2/map/occurrence/adhoc/{z}/{x}/{y}@Hx.png", params)

    async def _get(self, path: str, params: Mapping[str, str]) -> dict[str, object]:
        headers = {"Accept": "application/json", "User-Agent": "Florabase/0.1 botanical-reference"}
        try:
            async with (
                httpx.AsyncClient(
                    base_url=GBIF_API_BASE_URL,
                    timeout=self._timeout,
                    transport=self._transport,
                    follow_redirects=False,
                ) as client,
                client.stream("GET", path, params=params, headers=headers) as response,
            ):
                if response.status_code == 404:
                    raise ProviderNotFoundError("GBIF taxon was not found")
                if response.status_code == 429:
                    raise ProviderRateLimitedError("GBIF rate limit reached")
                if response.status_code >= 500:
                    raise ProviderError("GBIF is temporarily unavailable")
                if response.status_code >= 400:
                    raise ProviderResponseError("GBIF rejected the botanical lookup")
                content_length = response.headers.get("Content-Length")
                if content_length is not None:
                    try:
                        if int(content_length) > MAX_PROVIDER_RESPONSE_BYTES:
                            raise ProviderResponseError(
                                "GBIF response exceeded the safe size limit"
                            )
                    except ValueError as error:
                        raise ProviderResponseError(
                            "GBIF returned an invalid content length"
                        ) from error
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > MAX_PROVIDER_RESPONSE_BYTES:
                        raise ProviderResponseError("GBIF response exceeded the safe size limit")
        except (httpx.TimeoutException, httpx.NetworkError) as error:
            raise ProviderError("GBIF is temporarily unavailable") from error
        try:
            payload = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ProviderResponseError("GBIF returned malformed JSON") from error
        if not isinstance(payload, dict):
            raise ProviderResponseError("GBIF returned an unexpected response")
        return payload

    async def _get_tile(self, path: str, params: Mapping[str, str]) -> OccurrenceTile | None:
        headers = {"Accept": "image/png", "User-Agent": "Florabase/0.1 occurrence-map"}
        try:
            async with (
                httpx.AsyncClient(
                    base_url=GBIF_API_BASE_URL,
                    timeout=self._timeout,
                    transport=self._transport,
                    follow_redirects=False,
                ) as client,
                client.stream("GET", path, params=params, headers=headers) as response,
            ):
                if response.status_code == 204:
                    return None
                if response.status_code == 429:
                    raise ProviderRateLimitedError("GBIF rate limit reached")
                if response.status_code >= 500:
                    raise ProviderError("GBIF is temporarily unavailable")
                if response.status_code >= 400:
                    raise ProviderResponseError("GBIF rejected the occurrence tile request")
                media_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip()
                if media_type != "image/png":
                    raise ProviderResponseError("GBIF occurrence tile was not a PNG image")
                content_length = response.headers.get("Content-Length")
                if content_length is not None:
                    try:
                        parsed_content_length = int(content_length)
                        if (
                            parsed_content_length < 0
                            or parsed_content_length > MAX_OCCURRENCE_TILE_BYTES
                        ):
                            raise ProviderResponseError(
                                "GBIF occurrence tile exceeded the safe size limit"
                            )
                    except ValueError as error:
                        raise ProviderResponseError(
                            "GBIF returned an invalid tile content length"
                        ) from error
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > MAX_OCCURRENCE_TILE_BYTES:
                        raise ProviderResponseError(
                            "GBIF occurrence tile exceeded the safe size limit"
                        )
        except (httpx.TimeoutException, httpx.NetworkError) as error:
            raise ProviderError("GBIF is temporarily unavailable") from error
        if not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ProviderResponseError("GBIF occurrence tile contained malformed PNG data")
        return OccurrenceTile(content=bytes(content), media_type=media_type)

    def normalize_search(self, payload: Mapping[str, object]) -> list[TaxonCandidate]:
        candidates: list[TaxonCandidate] = []
        primary = self._normalize_match(payload)
        if primary is not None:
            candidates.append(primary)
        alternatives = payload.get("alternatives", [])
        if alternatives is not None and not isinstance(alternatives, list):
            raise ProviderResponseError("GBIF alternatives were malformed")
        for alternative in alternatives or []:
            if not isinstance(alternative, dict):
                raise ProviderResponseError("GBIF alternative was malformed")
            normalized = self._normalize_match(alternative)
            if normalized is not None and all(
                item.external_id != normalized.external_id for item in candidates
            ):
                candidates.append(normalized)
        return candidates

    def normalize_taxon(
        self, payload: Mapping[str, object], expected_external_id: str
    ) -> TaxonCandidate:
        candidate = self._normalize_match(payload)
        if candidate is None:
            raise ProviderNotFoundError("GBIF taxon was not found")
        if candidate.external_id != expected_external_id:
            raise ProviderNotFoundError("GBIF taxon was not found")
        return candidate

    def _normalize_match(self, value: Mapping[str, object]) -> TaxonCandidate | None:
        usage_value = value.get("usage", value)
        if not isinstance(usage_value, dict):
            raise ProviderResponseError("GBIF usage was malformed")
        key = usage_value.get("key")
        name = usage_value.get("name") or usage_value.get("scientificName")
        if key is None or not isinstance(name, str) or not name.strip():
            if value.get("diagnostics") or value.get("matchType") == "NONE":
                return None
            raise ProviderResponseError("GBIF taxon fields were missing")
        accepted_value = value.get("acceptedUsage")
        if accepted_value is not None and not isinstance(accepted_value, dict):
            raise ProviderResponseError("GBIF accepted usage was malformed")
        classification_value = value.get("classification", [])
        if classification_value is not None and not isinstance(classification_value, list):
            raise ProviderResponseError("GBIF classification was malformed")
        classification: dict[str, str] = {}
        for item in classification_value or []:
            if (
                isinstance(item, dict)
                and isinstance(item.get("rank"), str)
                and isinstance(item.get("name"), str)
            ):
                classification[item["rank"].upper()] = item["name"]
        diagnostics = value.get("diagnostics", {})
        if diagnostics is not None and not isinstance(diagnostics, dict):
            raise ProviderResponseError("GBIF diagnostics were malformed")
        issues = value.get("issues", [])
        if issues is not None and not isinstance(issues, list):
            raise ProviderResponseError("GBIF issues were malformed")
        accepted = accepted_value or {}
        confidence = (diagnostics or {}).get("confidence")
        return TaxonCandidate(
            external_id=str(key),
            scientific_name=name.strip(),
            canonical_name=_optional_string(usage_value.get("canonicalName")),
            authorship=_optional_string(usage_value.get("authorship")),
            rank=_optional_string(usage_value.get("rank")),
            taxonomic_status=_optional_string(
                value.get("taxonomicStatus") or usage_value.get("status")
            ),
            accepted_external_id=str(accepted["key"]) if accepted.get("key") is not None else None,
            accepted_name=_optional_string(accepted.get("name")),
            kingdom=classification.get("KINGDOM"),
            phylum=classification.get("PHYLUM"),
            class_name=classification.get("CLASS"),
            order_name=classification.get("ORDER"),
            family=classification.get("FAMILY"),
            genus=classification.get("GENUS"),
            match_type=_optional_string(
                (diagnostics or {}).get("matchType") or value.get("matchType")
            ),
            confidence=confidence if isinstance(confidence, int) else None,
            issues=[issue for issue in issues or [] if isinstance(issue, str)],
        )


def _optional_string(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None
