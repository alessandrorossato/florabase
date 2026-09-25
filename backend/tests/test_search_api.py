from typing import Any, cast

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

import florabase.search.api as search_api
from florabase.auth.dependencies import AuthenticatedActor
from florabase.search.schemas import SearchKind, SearchResponse
from florabase.search.service import SearchFilters


def test_search_api_trims_query_and_passes_bounded_paging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, SearchFilters, int, int]] = []

    def capture(
        _database: Session,
        query: str,
        filters: SearchFilters,
        *,
        offset: int,
        limit: int,
    ) -> SearchResponse:
        calls.append((query, filters, offset, limit))
        return SearchResponse(query=query, total=0, offset=offset, limit=limit, groups=[])

    monkeypatch.setattr(search_api, "search", capture)
    response = search_api.read_search(
        cast(AuthenticatedActor, None),
        cast(Session, None),
        q="  Acmella  ",
        kind=[SearchKind.SEED_LOT],
        lifecycle="active",
        offset=5,
        limit=10,
    )

    assert response.query == "Acmella"
    assert calls[0][0] == "Acmella"
    assert calls[0][2:] == (5, 10)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"year": 2024}, "Lifecycle and year require one collection record type"),
        (
            {"kind": [SearchKind.BOTANICAL_IDENTITY], "lifecycle": "active"},
            "Lifecycle and year require one collection record type",
        ),
        (
            {"kind": [SearchKind.EVENT], "lifecycle": "active"},
            "Events have kinds, not lifecycle states",
        ),
        (
            {"kind": [SearchKind.SEED_LOT], "event_kind": "observation"},
            "Event kind requires the Event record type",
        ),
    ],
)
def test_search_api_rejects_inapplicable_filter_combinations(
    kwargs: dict[str, Any], message: str
) -> None:
    with pytest.raises(HTTPException, match=message):
        search_api.read_search(cast(AuthenticatedActor, None), cast(Session, None), **kwargs)


def test_search_api_rejects_lifecycle_outside_the_kind_vocabulary() -> None:
    with pytest.raises(HTTPException, match="Lifecycle does not apply"):
        search_api.read_search(
            cast(AuthenticatedActor, None),
            cast(Session, None),
            kind=[SearchKind.PLANT],
            lifecycle="not-a-plant-lifecycle",
        )
