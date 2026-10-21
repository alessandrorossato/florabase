"""Local-only reads and explicit snapshot refresh; never refresh implicitly on a miss."""

import asyncio
from datetime import timedelta
from uuid import UUID, uuid7
from weakref import WeakKeyDictionary

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from florabase.external_botany.model import ExternalProviderCache, ExternalTaxonLink
from florabase.external_botany.provider import (
    GbifBotanicalProvider,
    OccurrenceTile,
    ProviderError,
    ProviderResponseError,
)
from florabase.external_botany.schemas import OccurrenceEvidence, OccurrenceMapSummary
from florabase.external_botany.service import occurrence_map_summary, utc_now
from florabase.external_botany.tile_cache import TileCache, contract_key, validate_png

PREFIX = "occurrence-v1:"
_inflight: WeakKeyDictionary[
    asyncio.AbstractEventLoop, dict[str, asyncio.Task[OccurrenceTile | None]]
] = WeakKeyDictionary()
_limits: WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore] = WeakKeyDictionary()


def key(link: ExternalTaxonLink) -> str:
    return PREFIX + contract_key(link.external_id)


def read(database: Session, link: ExternalTaxonLink) -> OccurrenceEvidence:
    cached = database.get(ExternalProviderCache, ("gbif", key(link)))
    if cached is None:
        return OccurrenceEvidence()
    try:
        summary = OccurrenceMapSummary.model_validate(cached.payload["summary"])
        generation = UUID(str(cached.payload["generation"]))
        if summary.external_taxon_id != link.external_id:
            return OccurrenceEvidence()
        return OccurrenceEvidence(
            summary=summary,
            generation=generation,
            stale=cached.fetched_at < utc_now() - timedelta(days=1),
            provider_error=str(cached.payload["provider_error"])
            if cached.payload.get("provider_error")
            else None,
        )
    except (ValueError, KeyError, TypeError) as _error:
        return OccurrenceEvidence()


async def refresh(
    database: Session, provider: GbifBotanicalProvider, link: ExternalTaxonLink
) -> OccurrenceEvidence:
    previous = read(database, link)
    try:
        summary = await occurrence_map_summary(provider, link)
    except ProviderError as error:
        if previous.summary is None:
            raise
        previous.provider_error = error.code
        return previous
    generation = uuid7()
    persisted = getattr(provider, "cache_summary_allowed", True) is not False
    if persisted:
        database.execute(select(func.pg_advisory_xact_lock(748_001)))
        statement = insert(ExternalProviderCache).values(
            provider="gbif",
            resource_key=key(link),
            fetched_at=summary.retrieved_at,
            payload={"summary": summary.model_dump(mode="json"), "generation": str(generation)},
        )
        database.execute(
            statement.on_conflict_do_update(
                index_elements=[ExternalProviderCache.provider, ExternalProviderCache.resource_key],
                set_={
                    "fetched_at": statement.excluded.fetched_at,
                    "payload": statement.excluded.payload,
                },
            )
        )
        obsolete = (
            select(ExternalProviderCache.resource_key)
            .where(
                ExternalProviderCache.provider == "gbif",
                ExternalProviderCache.resource_key.startswith(PREFIX),
            )
            .order_by(ExternalProviderCache.fetched_at.desc(), ExternalProviderCache.resource_key)
            .offset(256)
        )
        database.execute(
            delete(ExternalProviderCache).where(
                ExternalProviderCache.provider == "gbif",
                ExternalProviderCache.resource_key.in_(obsolete),
            )
        )
        database.flush()
    return OccurrenceEvidence(
        summary=summary, generation=generation if persisted else None, persisted=persisted
    )


def clear(database: Session, storage: TileCache, link: ExternalTaxonLink) -> None:
    storage.clear(contract_key(link.external_id))
    database.execute(
        delete(ExternalProviderCache).where(
            ExternalProviderCache.provider == "gbif",
            ExternalProviderCache.resource_key == key(link),
        )
    )
    database.flush()


async def fetch_tile(
    storage: TileCache,
    provider: GbifBotanicalProvider,
    external_id: str,
    generation: UUID,
    z: int,
    x: int,
    y: int,
) -> OccurrenceTile | None:
    cache_key = contract_key(external_id)
    existing = storage.read(cache_key, generation, z, x, y)
    if existing is not None:
        return existing[0]
    loop = asyncio.get_running_loop()
    pending = _inflight.setdefault(loop, {})
    request_key = f"{storage.root}:{cache_key}:{generation}:{z}/{x}/{y}"
    limit = _limits.setdefault(loop, asyncio.Semaphore(4))

    async def fetch() -> OccurrenceTile | None:
        async with limit:
            hit = storage.read(cache_key, generation, z, x, y)
            if hit is not None:
                return hit[0]
            tile = await provider.occurrence_tile(external_id, z, x, y)
            if tile is not None:
                try:
                    validate_png(tile.content)
                except ValueError as error:
                    raise ProviderResponseError("Invalid occurrence PNG") from error
            policy = (
                tile.cache_control if tile else getattr(provider, "empty_tile_cache_control", None)
            )
            storage.write(cache_key, generation, z, x, y, tile, policy=policy)
            return tile

    if request_key not in pending:
        task = asyncio.create_task(fetch())
        pending[request_key] = task

        def completed(value: asyncio.Task[OccurrenceTile | None]) -> None:
            pending.pop(request_key, None)
            if not value.cancelled():
                value.exception()  # Observe failures even if every waiting client disconnected.

        task.add_done_callback(completed)
    return await asyncio.shield(pending[request_key])
