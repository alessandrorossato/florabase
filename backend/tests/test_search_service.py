from types import SimpleNamespace
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

import florabase.search.service as search_service
from florabase.events.model import EventKind
from florabase.search.schemas import SearchKind
from florabase.search.service import SearchFilters

RECORD_ID = UUID("01900000-0000-7000-8000-000000000101")


def _database() -> Session:
    return cast(Session, ProjectionSession())


class ProjectionSession:
    """Return a stable projection row while exercising query construction."""

    def scalar(self, _statement: object) -> int:
        return 1

    def execute(self, _statement: object) -> list[tuple[UUID, str, None, UUID, str]]:
        return [(RECORD_ID, "Stored label", None, RECORD_ID, "group")]


def test_search_builds_typed_groups_and_uses_hierarchical_text_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    location = SimpleNamespace(id=RECORD_ID, parent_id=None)
    place = SimpleNamespace(id=RECORD_ID, parent_id=None)
    monkeypatch.setattr(search_service, "list_locations", lambda _database: [location])
    monkeypatch.setattr(search_service, "list_geographic_places", lambda _database: [place])
    monkeypatch.setattr(search_service, "location_path", lambda _item, _items: "Glasshouse")
    monkeypatch.setattr(search_service, "geographic_path", lambda _item, _items: "Alta valley")

    result = search_service.search(
        _database(),
        "glasshouse",
        SearchFilters(kinds=tuple(SearchKind)),
        limit=1,
    )

    assert result.total == len(SearchKind)
    assert {group.kind for group in result.groups} == set(SearchKind)
    assert all(group.total == 1 and len(group.items) == 1 for group in result.groups)
    assert next(group for group in result.groups if group.kind == SearchKind.EVENT).items[
        0
    ].href == (f"#/plant-groups/{RECORD_ID}?tab=events")
    assert (
        next(group for group in result.groups if group.kind == SearchKind.LOCATION).items[0].title
        == "Glasshouse"
    )
    assert (
        next(group for group in result.groups if group.kind == SearchKind.GEOGRAPHIC_PLACE)
        .items[0]
        .title
        == "Alta valley"
    )


def test_search_empty_request_and_collection_filters_follow_recorded_links(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = SimpleNamespace(id=RECORD_ID, parent_id=None)
    child_id = UUID("01900000-0000-7000-8000-000000000102")
    child = SimpleNamespace(id=child_id, parent_id=RECORD_ID)
    monkeypatch.setattr(search_service, "list_locations", lambda _database: [root, child])
    monkeypatch.setattr(search_service, "list_geographic_places", lambda _database: [])
    monkeypatch.setattr(search_service, "location_path", lambda item, _items: str(item.id))

    empty = search_service.search(_database(), "", SearchFilters())
    assert empty.groups == []
    assert empty.total == 0

    filtered = search_service.search(
        _database(),
        "packet",
        SearchFilters(
            kinds=(SearchKind.SEED_LOT,),
            identity_id=RECORD_ID,
            lifecycle="active",
            location_id=RECORD_ID,
            supplier_id=RECORD_ID,
            provenance_place_id=RECORD_ID,
            provenance_site_id=RECORD_ID,
            year=2024,
        ),
    )
    assert [group.kind for group in filtered.groups] == [SearchKind.SEED_LOT]

    with_provenance = search_service.search(
        _database(),
        "",
        SearchFilters(kinds=(SearchKind.SOWING,), provenance_place_id=RECORD_ID),
    )
    assert with_provenance.groups == []


def test_search_event_filters_use_the_event_target_and_exclude_inapplicable_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        search_service,
        "list_locations",
        lambda _database: [SimpleNamespace(id=RECORD_ID, parent_id=None)],
    )
    monkeypatch.setattr(search_service, "location_path", lambda item, _items: str(item.id))
    event_result = search_service.search(
        _database(),
        "",
        SearchFilters(
            kinds=(SearchKind.EVENT,),
            identity_id=RECORD_ID,
            event_kind=EventKind.OBSERVATION,
            year=2024,
        ),
    )
    assert [group.kind for group in event_result.groups] == [SearchKind.EVENT]

    blocked_by_location = search_service.search(
        _database(),
        "",
        SearchFilters(location_id=RECORD_ID, event_kind=EventKind.OBSERVATION),
    )
    assert all(group.kind != SearchKind.EVENT for group in blocked_by_location.groups)


def test_search_reference_records_are_suppressed_by_collection_only_filters() -> None:
    result = search_service.search(
        _database(),
        "",
        SearchFilters(kinds=(SearchKind.BOTANICAL_IDENTITY,), identity_id=RECORD_ID),
    )
    assert result.groups == []
