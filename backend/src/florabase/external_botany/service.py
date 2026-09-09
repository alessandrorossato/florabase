from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any, cast
from uuid import UUID, uuid7

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from florabase.external_botany.model import ExternalProviderCache, ExternalTaxonLink
from florabase.external_botany.provider import GbifBotanicalProvider, ProviderError
from florabase.external_botany.schemas import (
    ExternalTaxonLinkResponse,
    TaxonCandidate,
    TaxonSearchResponse,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def _search_key(query: str) -> str:
    digest = sha256(" ".join(query.casefold().split()).encode()).hexdigest()
    return f"match-v2-colxr:{digest}"


def _taxon_key(external_id: str, scientific_name: str) -> str:
    request = f"{external_id}\x00{' '.join(scientific_name.casefold().split())}"
    return f"taxon-v2-colxr:{sha256(request.encode()).hexdigest()}"


async def _payload(
    database: Session,
    provider: GbifBotanicalProvider,
    resource_key: str,
    fetch: Callable[[], Awaitable[dict[str, object]]],
    ttl_seconds: int,
    *,
    force: bool = False,
    allow_stale_on_error: bool = False,
) -> tuple[dict[str, object], datetime, bool, bool, str | None]:
    cached = database.get(ExternalProviderCache, (provider.provider_id, resource_key))
    now = utc_now()
    if (
        cached is not None
        and not force
        and cached.fetched_at >= now - timedelta(seconds=ttl_seconds)
    ):
        return cached.payload, cached.fetched_at, True, False, None
    try:
        payload = await fetch()
    except ProviderError as error:
        if cached is not None and allow_stale_on_error:
            return cached.payload, cached.fetched_at, True, True, error.code
        raise
    statement = insert(ExternalProviderCache).values(
        provider=provider.provider_id,
        resource_key=resource_key,
        fetched_at=now,
        payload=payload,
    )
    statement = statement.on_conflict_do_update(
        index_elements=[ExternalProviderCache.provider, ExternalProviderCache.resource_key],
        set_={"fetched_at": now, "payload": payload},
    )
    database.execute(statement)
    database.flush()
    return payload, now, False, False, None


async def search_taxa(
    database: Session,
    provider: GbifBotanicalProvider,
    query: str,
    ttl_seconds: int,
) -> TaxonSearchResponse:
    payload, fetched_at, from_cache, stale, provider_error = await _payload(
        database,
        provider,
        _search_key(query),
        lambda: provider.search_payload(query),
        ttl_seconds,
        allow_stale_on_error=True,
    )
    candidates = provider.normalize_search(payload)
    return TaxonSearchResponse(
        provider=provider.provider_id,
        query=query,
        fetched_at=fetched_at,
        from_cache=from_cache,
        stale=stale,
        provider_error=provider_error,
        candidates=candidates,
    )


async def _fetch_taxon(
    database: Session,
    provider: GbifBotanicalProvider,
    external_id: str,
    scientific_name: str,
    ttl_seconds: int,
    *,
    force: bool = False,
    allow_stale_on_error: bool = False,
) -> tuple[TaxonCandidate, datetime, bool, str | None]:
    payload, fetched_at, _, stale, provider_error = await _payload(
        database,
        provider,
        _taxon_key(external_id, scientific_name),
        lambda: provider.taxon_payload(scientific_name),
        ttl_seconds,
        force=force,
        allow_stale_on_error=allow_stale_on_error,
    )
    return provider.normalize_taxon(payload, external_id), fetched_at, stale, provider_error


def get_link(database: Session, identity_id: UUID) -> ExternalTaxonLink | None:
    return database.scalar(
        select(ExternalTaxonLink).where(
            ExternalTaxonLink.botanical_identity_id == identity_id,
            ExternalTaxonLink.provider == "gbif",
        )
    )


def _candidate_values(candidate: TaxonCandidate) -> dict[str, Any]:
    return candidate.model_dump(exclude={"match_type", "confidence", "issues"})


async def confirm_link(
    database: Session,
    provider: GbifBotanicalProvider,
    identity_id: UUID,
    external_id: str,
    scientific_name: str,
    ttl_seconds: int,
) -> ExternalTaxonLink:
    candidate, fetched_at, _, _ = await _fetch_taxon(
        database, provider, external_id, scientific_name, ttl_seconds
    )
    now = utc_now()
    values = _candidate_values(candidate)
    values.update(
        id=uuid7(),
        botanical_identity_id=identity_id,
        provider=provider.provider_id,
        linked_at=now,
        last_refreshed_at=fetched_at,
        last_refresh_attempt_at=now,
        refresh_error=None,
    )
    base_statement = insert(ExternalTaxonLink).values(**values)
    excluded = base_statement.excluded
    upsert_statement = base_statement.on_conflict_do_update(
        constraint="uq_external_taxon_links_identity_provider",
        set_={
            column: getattr(excluded, column)
            for column in values
            if column not in {"id", "botanical_identity_id", "provider"}
        },
    ).returning(ExternalTaxonLink)
    link = database.scalar(upsert_statement)
    assert link is not None
    database.flush()
    return link


async def refresh_link(
    database: Session,
    provider: GbifBotanicalProvider,
    link: ExternalTaxonLink,
    ttl_seconds: int,
) -> ExternalTaxonLink:
    now = utc_now()
    link.last_refresh_attempt_at = now
    try:
        candidate, fetched_at, stale, provider_error = await _fetch_taxon(
            database,
            provider,
            link.external_id,
            link.scientific_name,
            ttl_seconds,
            force=True,
            allow_stale_on_error=True,
        )
    except ProviderError as error:
        link.refresh_error = error.code
        database.flush()
        return link
    if stale:
        link.refresh_error = provider_error
        database.flush()
        return link
    for field, value in _candidate_values(candidate).items():
        setattr(link, field, value)
    link.last_refreshed_at = fetched_at
    link.refresh_error = None
    database.flush()
    return link


def unlink(database: Session, identity_id: UUID) -> bool:
    result = cast(
        CursorResult[Any],
        database.execute(
            delete(ExternalTaxonLink).where(
                ExternalTaxonLink.botanical_identity_id == identity_id,
                ExternalTaxonLink.provider == "gbif",
            )
        ),
    )
    return bool(result.rowcount)


def link_response(link: ExternalTaxonLink, ttl_seconds: int) -> ExternalTaxonLinkResponse:
    stale = link.last_refreshed_at < utc_now() - timedelta(seconds=ttl_seconds)
    return ExternalTaxonLinkResponse.from_model(link, stale=stale)
