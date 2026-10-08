from typing import cast
from unittest.mock import MagicMock, patch
from uuid import uuid7

import pytest
from fastapi import HTTPException
from pydantic import JsonValue, ValidationError
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.explore import native_ranges
from florabase.explore.api import native_identities, native_overview, native_selected
from florabase.explore.schemas import NativeRangeIdentityPage, NativeRangeOverview
from florabase.geographic_places.model import GeographicPlace
from florabase.saved_views.state import SavedViewSurface, canonical_state


def test_saved_native_range_state_is_stable_and_separate() -> None:
    id_ = str(uuid7())
    surface = SavedViewSurface.NATIVE_RANGES
    assert canonical_state(
        surface,
        1,
        {
            "q": " tree ",
            "scope": "living",
            "mode": "species",
            "identity": id_.upper(),
            "withRange": True,
        },
    ) == {"q": "tree", "scope": "living", "mode": "species", "identity": [id_], "withRange": True}
    assert canonical_state(surface, 1, {"mode": "overview", "scope": "all", "withRange": True}) == {
        "withRange": True
    }
    invalid: list[dict[str, JsonValue]] = [
        {"scope": "dead"},
        {"mode": "map"},
        {"identity": "bad"},
        {"withRange": "true"},
        {"withRange": 1},
        {"offset": 50},
        {"geometry": {}},
        {"hover": "BR"},
        {"zoom": 1},
        {"q": "x" * 201},
    ]
    for state in invalid:
        with pytest.raises(ValidationError):
            canonical_state(surface, 1, state)
    with pytest.raises(ValueError, match="Choose a search"):
        canonical_state(surface, 1, {"mode": "overview", "scope": "all", "withRange": False})
    with pytest.raises(ValueError, match="Unsupported"):
        canonical_state(surface, 2, {"scope": "living"})
    with pytest.raises(ValidationError):
        canonical_state(SavedViewSurface.SPECIES_DISTRIBUTION, 1, {"mode": "species"})


def test_native_api_delegates_to_local_read_projection_only() -> None:
    actor, database = MagicMock(), MagicMock()
    page = NativeRangeIdentityPage(items=[], total=0, offset=0, limit=50)
    with patch("florabase.explore.api.native_ranges.list_identities", return_value=page) as read:
        assert native_identities(actor, database, "tree", "living", True, None, 0, 50) == page
        read.assert_called_once_with(
            database, q="tree", scope="living", with_range=True, record=(), offset=0, limit=50
        )
    overview = NativeRangeOverview(
        represented=0,
        with_range=0,
        without_range=0,
        territories=[],
        places=[],
        places_total=0,
        offset=0,
        limit=50,
    )
    with patch("florabase.explore.api.native_ranges.overview", return_value=overview) as read:
        assert native_overview(actor, database, "", "all", False, None, 0, 50) == overview
    with (
        patch("florabase.explore.api.native_ranges.selected", return_value=None),
        pytest.raises(HTTPException) as missing,
    ):
        native_selected(uuid7(), actor, database)
    assert missing.value.status_code == 404


def test_selection_and_category_canonical_sets_and_bounds() -> None:
    ids = sorted(str(uuid7()) for _ in range(21))
    surface = SavedViewSurface.NATIVE_RANGES
    assert canonical_state(
        surface,
        1,
        {
            "identity": [ids[1].upper(), ids[0], ids[1]],
            "record": ["stored_material", "plant", "plant"],
        },
    ) == {"identity": ids[:2], "record": ["plant", "stored_material"]}
    valid_ids: list[JsonValue] = [cast(JsonValue, value) for value in ids[:20]]
    valid_state: dict[str, JsonValue] = {"identity": valid_ids}
    assert canonical_state(surface, 1, valid_state) == {"identity": ids[:20]}
    oversized_ids: list[JsonValue] = [cast(JsonValue, value) for value in ids]
    invalid_states: list[dict[str, JsonValue]] = [
        {"identity": oversized_ids},
        {"identity": [ids[0], "bad"]},
        {"record": ["event"]},
        {"record": "plant"},
    ]
    for state in invalid_states:
        with pytest.raises(ValidationError):
            canonical_state(surface, 1, state)


def test_native_identity_page_keeps_collection_label_and_range_count() -> None:
    identity = BotanicalIdentity(
        id=uuid7(),
        scientific_name="Salvia officinalis",
        cultivar_name="Common Sage",
        common_name="Garden sage",
    )
    database = MagicMock()
    database.scalar.return_value = 1
    database.execute.return_value = [(identity, 3, 1, 0, 2)]

    page = native_ranges.list_identities(
        cast(Session, database), q="sage", scope="current", with_range=True
    )

    assert page.total == 1
    assert page.items[0].display_label == "Salvia officinalis \u2018Common Sage\u2019"
    assert page.items[0].common_name == "Garden sage"
    assert page.items[0].representation == "current"
    assert page.items[0].native_range_count == 2
    assert page.items[0].matches_filters
    assert database.execute.call_count == 1


def test_overview_assembles_distinct_territories_and_exact_place_paths() -> None:
    place_id, territory_id = uuid7(), uuid7()
    place = GeographicPlace(
        id=place_id,
        name="Custom ridge",
        parent_id=None,
        place_kind="custom",
        source_code_type=None,
        source_code=None,
    )
    summary = MagicMock()
    summary.one.return_value = (5, 3)
    database = MagicMock()
    database.scalar.return_value = 1
    database.execute.side_effect = [
        summary,
        [(territory_id, "Brazil", "BR", 3, None)],
        [(place, "Custom ridge", 2)],
    ]

    result = native_ranges.overview(cast(Session, database), record=[], offset=0, limit=10)

    assert (result.represented, result.with_range, result.without_range) == (5, 3, 2)
    assert result.territories[0].source_code == "BR"
    assert result.territories[0].identity_count == 3
    assert result.places_total == 1
    assert result.places[0].display_path == "Custom ridge"
    assert result.places[0].place_kind == "custom"
    assert result.places[0].identity_count == 2
    assert database.execute.call_count == 3


def test_selected_ranges_keeps_exact_places_and_returns_unrepresented_as_missing() -> None:
    identity = BotanicalIdentity(
        id=uuid7(),
        scientific_name="Ocimum basilicum",
        cultivar_name=None,
        common_name="Basil",
    )
    place_id, territory_id = uuid7(), uuid7()
    place = GeographicPlace(
        id=place_id,
        name="South America",
        parent_id=None,
        place_kind="canonical",
        source_code_type="un_m49",
        source_code="005",
    )
    database = MagicMock()
    database.execute.side_effect = [
        [(identity, 2, 1, 1, 2, True)],
        [(place, "World → South America", 1)],
        [(territory_id, "Brazil", "BR", 1, None)],
    ]
    database.scalar.return_value = 1

    result = native_ranges.selected(cast(Session, database), identity.id, scope="living")
    assert result is not None
    assert result.identity.display_label == "Ocimum basilicum"
    assert result.ranges[0].name == "South America"
    assert result.ranges[0].source_code == "005"
    assert result.territories[0].source_code == "BR"
    assert result.total == 1

    absent = native_ranges.selected(MagicMock(), uuid7())
    assert absent is None

    ids = [identity.id, uuid7()]
    selection_db = MagicMock()
    selection_db.execute.side_effect = [
        [(identity, 2, 1, 1, 2, True)],
        [(territory_id, "Brazil", "BR", 1, [identity.id])],
    ]
    comparison = native_ranges.selection(cast(Session, selection_db), [*ids[::-1], identity.id])
    assert [item.id for item in comparison.identities] == [identity.id]
    assert comparison.missing_ids == [ids[1]]
    assert comparison.territories[0].identity_ids == [identity.id]
    with pytest.raises(ValueError, match="at most 20"):
        native_ranges.selection(cast(Session, selection_db), [uuid7() for _ in range(21)])
