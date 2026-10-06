from datetime import UTC, datetime
from typing import Any
from uuid import uuid7

import pytest
from pydantic import ValidationError

from florabase.saved_views.model import SavedView
from florabase.saved_views.schemas import SavedViewCreate, SavedViewResponse, SavedViewUpdate
from florabase.saved_views.state import SavedViewSurface, canonical_state


@pytest.mark.parametrize(
    ("surface", "state", "expected"),
    [
        (
            "global_search",
            {"q": "  Árbol  ", "kind": ["plant", "seed_lot", "plant"], "year": 2026},
            None,
        ),
        (
            "global_search",
            {"q": "  Árbol  ", "kind": ["plant", "seed_lot", "plant"]},
            {"q": "Árbol", "kind": ["seed_lot", "plant"]},
        ),
        ("seed_lots", {"q": " basil ", "lifecycle": "active"}, {"q": "basil"}),
        ("sowings", {"lifecycle": "completed"}, {"lifecycle": "completed"}),
        (
            "plants",
            {"q": "basil", "lifecycle": "history", "type": "group"},
            {"q": "basil", "lifecycle": "history", "type": "group"},
        ),
        (
            "harvests",
            {"material": "seed", "source_type": "plant_group"},
            {"material": "seed", "source_type": "plant_group"},
        ),
        (
            "stored_material",
            {"state": "all", "location_id": "AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA"},
            {"state": "all", "location_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"},
        ),
        ("events", {"category": "cultivation"}, {"category": "cultivation"}),
        (
            "media",
            {"q": "leaf", "association": "all", "target": "supplier"},
            {"q": "leaf", "target": "supplier"},
        ),
        ("botanical_identities", {"q": "Ocimum"}, {"q": "Ocimum"}),
        ("suppliers", {"q": "店"}, {"q": "店"}),
        ("locations", {"scope": "harvest_inventory"}, {"scope": "harvest_inventory"}),
        ("geography", {"q": "Italy", "mode": "map"}, {"q": "Italy", "mode": "map"}),
        ("provenance_map", {"seed_lots": False, "plants": True}, {"seed_lots": False}),
    ],
)
def test_surface_canonical_contract(
    surface: str, state: dict[str, Any], expected: dict[str, Any] | None
) -> None:
    if expected is None:
        with pytest.raises(ValueError, match="one collection record type"):
            canonical_state(SavedViewSurface(surface), 1, state)
    else:
        assert canonical_state(SavedViewSurface(surface), 1, state) == expected
        assert canonical_state(SavedViewSurface(surface), 1, expected) == expected


@pytest.mark.parametrize(
    "state",
    [
        {"offset": 40, "q": "basil"},
        {"page": 2, "q": "basil"},
        {"selected_id": str(uuid7()), "q": "basil"},
        {"q": []},
        {"q": 1},
        {"q": "x" * 121},
        {"kind": ["bogus"]},
        {"location_id": "not-uuid"},
        {"kind": ["harvest"], "lifecycle": "active"},
        {"kind": ["event"], "event_kind": "bogus"},
        {"event_kind": "observation"},
        {"kind": ["plant"], "lifecycle": "completed"},
        {"kind": ["plant"], "year": 0},
        {"kind": ["plant"], "year": "2026"},
        {"kind": ["media_asset"], "year": 2026},
        {"q": "  "},
        {},
    ],
)
def test_global_state_rejects_noise_invalid_and_default(state: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match=r"validation error|Choose a search"):
        canonical_state(SavedViewSurface.GLOBAL_SEARCH, 1, state)


@pytest.mark.parametrize("surface", list(SavedViewSurface))
def test_each_surface_rejects_unknown_transient_keys(surface: SavedViewSurface) -> None:
    with pytest.raises(ValueError, match=r"validation error|Choose a search"):
        canonical_state(surface, 1, {"q": "basil", "scroll": 12})
    with pytest.raises(ValueError, match="version"):
        canonical_state(surface, 2, {"q": "basil"})


@pytest.mark.parametrize(
    ("surface", "state"),
    [
        ("seed_lots", {"lifecycle": "completed"}),
        ("sowings", {"lifecycle": "history"}),
        ("plants", {"type": "plant_group"}),
        ("harvests", {"source_type": "seed_lot"}),
        ("harvests", {"material": "cutting"}),
        ("stored_material", {"state": "unknown"}),
        ("stored_material", {"location_id": "wrong"}),
        ("events", {"category": "flowering"}),
        ("media", {"target": "botanical_identity"}),
        ("media", {"kind": "video"}),
        ("geography", {"mode": "unknown"}),
        ("locations", {"scope": "suppliers"}),
        ("provenance_map", {"seed_lots": "false"}),
        ("suppliers", {"q": "x" * 201}),
    ],
)
def test_directory_contract_rejects_new_semantics(surface: str, state: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match=r"validation error|Choose a search"):
        canonical_state(SavedViewSurface(surface), 1, state)


def test_create_trims_unicode_name_and_state() -> None:
    payload = SavedViewCreate(
        name="  葉っぱ Árbol  ", surface="global_search", state_version=1, state={"q": " basil "}
    )
    assert payload.name == "葉っぱ Árbol"
    assert payload.state == {"q": "basil"}


@pytest.mark.parametrize(
    "changes",
    [
        {"name": " "},
        {"name": "x" * 121},
        {"name": "foo\nbar"},
        {"surface": "#/plants"},
        {"state_version": 2},
        {"state_version": True},
    ],
)
def test_invalid_create(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        SavedViewCreate.model_validate(
            {
                "name": "Basil",
                "surface": "global_search",
                "state_version": 1,
                "state": {"q": "basil"},
                **changes,
            }
        )


@pytest.mark.parametrize(
    "payload",
    [{}, {"name": None}, {"state": {"q": "basil"}}, {"state_version": 1}, {"surface": "plants"}],
)
def test_patch_requires_explicit_non_null_fields_and_immutable_surface(
    payload: dict[str, Any],
) -> None:
    with pytest.raises(ValidationError):
        SavedViewUpdate.model_validate(payload)


@pytest.mark.parametrize(
    ("version", "state", "compatibility"),
    [
        (1, {"q": "basil"}, "supported"),
        (9, {"q": "basil", "future": True}, "unsupported_version"),
        (1, {"selected": "bad"}, "invalid_state"),
    ],
)
def test_read_stale_and_future_remains_manageable(
    version: int, state: dict[str, Any], compatibility: str
) -> None:
    record = SavedView(
        id=uuid7(),
        owner_id=uuid7(),
        name="Retained",
        surface="global_search",
        state_version=version,
        state=state,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    response = SavedViewResponse.from_model(record)
    assert response.compatibility == compatibility
    assert response.state == state


def test_stale_exact_reference_is_retained_without_lookup() -> None:
    missing = str(uuid7())
    assert canonical_state(SavedViewSurface.GLOBAL_SEARCH, 1, {"identity_id": missing}) == {
        "identity_id": missing
    }
