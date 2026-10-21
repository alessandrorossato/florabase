import asyncio
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid7

import pytest
from PIL import Image

from florabase.external_botany import occurrence_cache
from florabase.external_botany.model import ExternalProviderCache, ExternalTaxonLink
from florabase.external_botany.provider import OccurrenceTile, ProviderError
from florabase.external_botany.schemas import OccurrenceMapSummary
from florabase.external_botany.tile_cache import TileCache, cacheable, contract_key


def png() -> bytes:
    output = BytesIO()
    Image.new("RGBA", (2, 2), (10, 20, 30, 255)).save(output, format="PNG")
    return output.getvalue()


def summary(external_id: str = "opaque") -> OccurrenceMapSummary:
    return OccurrenceMapSummary(
        source="GBIF",
        provider="gbif",
        external_taxon_id=external_id,
        taxon_scientific_name="Ocimum basilicum",
        taxon_provider_url="https://www.gbif.org",
        checklist_key="fixed",
        checklist_name="CoL",
        total_matching_records=9,
        eligible_mapped_records=7,
        retrieved_at=datetime.now(UTC),
        quality_policy={
            "occurrence_status": "PRESENT",
            "has_coordinate": True,
            "has_geospatial_issue": False,
        },
        binning="hex",
        attribution="GBIF and publishers",
        provider_url="https://www.gbif.org",
        licensing_url="https://www.gbif.org/terms",
    )


def test_durable_tiles_empty_isolation_bounds_and_clear(tmp_path: Path) -> None:
    storage = TileCache(tmp_path, total_bytes=1000, taxon_bytes=600, max_files=3)
    first, other = contract_key("opaque/A"), contract_key("opaque/B")
    generation = uuid7()
    tile = OccurrenceTile(png(), "image/png")
    assert storage.read(first, generation, 1, 0, 0) is None
    assert storage.write(first, generation, 1, 0, 0, tile)
    assert storage.write(first, generation, 1, 0, 1, None)
    reopened = TileCache(tmp_path)
    hit = reopened.read(first, generation, 1, 0, 0)
    assert hit is not None
    assert hit[0] is not None
    assert hit[0].content == png()
    empty = reopened.read(first, generation, 1, 0, 1)
    assert empty is not None
    assert empty[0] is None
    assert reopened.read(other, generation, 1, 0, 0) is None
    assert reopened.read(first, uuid7(), 1, 0, 0) is None
    for x in range(4):
        storage.write(other, generation, 2, x, 0, tile)
    files = list(storage.root.glob("*.tile"))
    assert len(files) <= 3
    assert sum(file.stat().st_size for file in files) <= 1000
    assert sum(file.stat().st_size for file in files if file.name.startswith(other)) <= 600
    storage.clear(other)
    assert not list(storage.root.glob(f"{other}.*"))


def test_tile_validation_policy_and_safe_paths(tmp_path: Path) -> None:
    storage = TileCache(tmp_path)
    key, generation = contract_key("../external"), uuid7()
    for value in (b"not PNG", b"\x89PNG\r\n\x1a\ncorrupt"):
        with pytest.raises(ValueError, match="Invalid"):
            storage.write(key, generation, 0, 0, 0, OccurrenceTile(value, "image/png"))
    with pytest.raises(ValueError, match="Invalid"):
        storage.write("../escape", generation, 0, 0, 0, None)
    with pytest.raises(ValueError, match="Invalid"):
        storage.read(key, generation, 1, 2, 0)
    for policy in ("no-store", "public, no-cache", "max-age=20, must-revalidate"):
        assert not cacheable(policy)
        assert not storage.write(key, generation, 0, 0, 0, None, policy=policy)
    assert storage.write(key, generation, 0, 0, 0, None, policy="public, max-age=1200")
    path = storage.path(key, generation, 0, 0, 0)
    path.unlink()
    secret = tmp_path / "outside"
    secret.write_text("outside")
    path.symlink_to(secret)
    assert storage.read(key, generation, 0, 0, 0) is None
    storage.write(key, generation, 0, 0, 0, None)
    assert secret.read_text() == "outside"


def test_duplicate_tile_requests_share_fetch_and_cache_survives_provider_failure(
    tmp_path: Path,
) -> None:
    provider = MagicMock()
    provider.occurrence_tile = AsyncMock(return_value=OccurrenceTile(png(), "image/png"))
    storage, generation = TileCache(tmp_path), uuid7()

    async def run() -> None:
        await asyncio.gather(
            *(
                occurrence_cache.fetch_tile(storage, provider, "opaque", generation, 1, 0, 0)
                for _ in range(8)
            )
        )

    asyncio.run(run())
    assert provider.occurrence_tile.await_count == 1
    provider.occurrence_tile.side_effect = ProviderError("offline")
    assert (
        asyncio.run(occurrence_cache.fetch_tile(storage, provider, "opaque", generation, 1, 0, 0))
        is not None
    )
    assert provider.occurrence_tile.await_count == 1


def test_local_summary_miss_stale_isolation_and_failed_refresh() -> None:
    database, provider = MagicMock(), MagicMock()
    link = ExternalTaxonLink(external_id="opaque", scientific_name="Ocimum basilicum")
    database.get.return_value = None
    assert occurrence_cache.read(database, link).summary is None
    generation = uuid7()
    expected = summary()
    cached = ExternalProviderCache(
        provider="gbif",
        resource_key=occurrence_cache.key(link),
        fetched_at=datetime.now(UTC) - timedelta(days=2),
        payload={
            "summary": expected.model_dump(mode="json"),
            "generation": str(generation),
        },
    )
    database.get.return_value = cached
    assert occurrence_cache.read(database, link).stale
    with patch(
        "florabase.external_botany.occurrence_cache.occurrence_map_summary",
        AsyncMock(side_effect=ProviderError("offline")),
    ):
        result = asyncio.run(occurrence_cache.refresh(database, provider, link))
    assert result.generation == generation
    assert result.summary == expected
    assert result.provider_error
    database.execute.assert_not_called()
    link.external_id = "different"
    assert occurrence_cache.read(database, link).summary is None


def test_successful_refresh_persists_new_generation_and_prunes_old_summaries() -> None:
    database = MagicMock()
    database.get.return_value = None
    provider = MagicMock(cache_summary_allowed=True)
    link = ExternalTaxonLink(external_id="opaque", scientific_name="Ocimum basilicum")
    expected = summary()
    with patch(
        "florabase.external_botany.occurrence_cache.occurrence_map_summary",
        AsyncMock(return_value=expected),
    ):
        result = asyncio.run(occurrence_cache.refresh(database, provider, link))

    assert result.summary == expected
    assert result.generation is not None
    assert result.persisted is True
    assert database.execute.call_count == 3
    database.flush.assert_called_once()


def test_refresh_respects_no_store_and_missing_cache_error() -> None:
    database = MagicMock()
    database.get.return_value = None
    link = ExternalTaxonLink(external_id="opaque", scientific_name="Ocimum basilicum")
    provider = MagicMock(cache_summary_allowed=False)
    expected = summary()
    with patch(
        "florabase.external_botany.occurrence_cache.occurrence_map_summary",
        AsyncMock(return_value=expected),
    ):
        result = asyncio.run(occurrence_cache.refresh(database, provider, link))
    assert result.summary == expected
    assert result.generation is None
    assert result.persisted is False
    database.execute.assert_not_called()

    with (
        patch(
            "florabase.external_botany.occurrence_cache.occurrence_map_summary",
            AsyncMock(side_effect=ProviderError("offline")),
        ),
        pytest.raises(ProviderError, match="offline"),
    ):
        asyncio.run(occurrence_cache.refresh(database, provider, link))


def test_corrupt_summary_is_a_local_miss_and_clear_removes_exact_taxon_cache(
    tmp_path: Path,
) -> None:
    database = MagicMock()
    link = ExternalTaxonLink(external_id="opaque", scientific_name="Ocimum basilicum")
    corrupt = ExternalProviderCache(
        provider="gbif",
        resource_key=occurrence_cache.key(link),
        fetched_at=datetime.now(UTC),
        payload={"summary": {"invalid": True}, "generation": "not-a-uuid"},
    )
    database.get.return_value = corrupt
    assert occurrence_cache.read(database, link).summary is None

    storage = TileCache(tmp_path)
    generation = uuid7()
    cache_key = contract_key(link.external_id)
    storage.write(cache_key, generation, 0, 0, 0, None)
    occurrence_cache.clear(database, storage, link)
    database.execute.assert_called_once()
    database.flush.assert_called_once()
    assert storage.read(cache_key, generation, 0, 0, 0) is None


def test_empty_tiles_follow_response_cache_policy(tmp_path: Path) -> None:
    storage, generation = TileCache(tmp_path), uuid7()
    provider = MagicMock(empty_tile_cache_control="public, max-age=1200")
    provider.occurrence_tile = AsyncMock(return_value=None)
    assert (
        asyncio.run(occurrence_cache.fetch_tile(storage, provider, "opaque", generation, 0, 0, 0))
        is None
    )
    key = contract_key("opaque")
    hit = storage.read(key, generation, 0, 0, 0)
    assert hit is not None
    assert hit[0] is None

    another = TileCache(tmp_path / "private")
    provider.empty_tile_cache_control = "no-store"
    assert (
        asyncio.run(occurrence_cache.fetch_tile(another, provider, "opaque", generation, 0, 0, 0))
        is None
    )
    assert another.read(key, generation, 0, 0, 0) is None
