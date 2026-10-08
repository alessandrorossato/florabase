from collections.abc import Callable
from typing import cast
from unittest.mock import MagicMock, patch
from uuid import uuid7

import pytest
from fastapi import HTTPException
from pydantic import JsonValue, ValidationError
from sqlalchemy import Row
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.engine.interfaces import Dialect

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.explore.api import list_all, read
from florabase.explore.schemas import (
    RepresentationScope,
    RepresentedIdentity,
    RepresentedIdentityPage,
)
from florabase.explore.service import get_identity, list_identities, projection, response
from florabase.saved_views.state import SavedViewSurface, canonical_state


def postgres_dialect() -> Dialect:
    factory = cast(Callable[[], Dialect], dialect)
    return factory()


def test_saved_state_is_local_and_canonical() -> None:
    identity = uuid7()
    surface = SavedViewSurface.SPECIES_DISTRIBUTION
    assert canonical_state(
        surface, 1, {"scope": "all", "q": " basil ", "identity": str(identity).upper()}
    ) == {"q": "basil", "identity": str(identity)}
    assert canonical_state(surface, 1, {"scope": "historical"}) == {"scope": "historical"}
    invalid: list[dict[str, JsonValue]] = [
        {"scope": "dead"},
        {"identity": "bad"},
        {"offset": 50},
        {"loaded": True},
        {"tiles": []},
        {"occurrences": 42},
        {"q": "x" * 201},
    ]
    for state in invalid:
        with pytest.raises(ValidationError):
            canonical_state(surface, 1, state)
    with pytest.raises(ValueError, match="Choose a search"):
        canonical_state(surface, 1, {"scope": "all"})
    with pytest.raises(ValueError, match="Unsupported"):
        canonical_state(surface, 2, {"scope": "living"})


def test_api_delegates_only_to_local_projection_and_missing_selection() -> None:
    actor, db = MagicMock(), MagicMock()
    page = RepresentedIdentityPage(items=[], total=0, occurrence_ready=0, offset=0, limit=50)
    with patch("florabase.explore.api.service.list_identities", return_value=page) as local:
        assert list_all(actor, db, q="basil", scope="living", offset=0, limit=50) == page
        local.assert_called_once_with(db, q="basil", scope="living", offset=0, limit=50)
    with (
        patch("florabase.explore.api.service.get_identity", return_value=None),
        pytest.raises(HTTPException) as missing,
    ):
        read(uuid7(), actor, db)
    assert missing.value.status_code == 404


def test_response_keeps_exact_representation_and_provider_link_states() -> None:
    identity = BotanicalIdentity(
        id=uuid7(),
        scientific_name="Ocimum basilicum",
        cultivar_name="Genovese",
        common_name="Basil",
    )
    living = response(
        cast(
            Row[tuple[BotanicalIdentity, int, int, int, str | None, int]],
            (identity, 4, 3, 2, "48GBK", 1),
        ),
        "living",
    )
    assert living == RepresentedIdentity(
        id=identity.id,
        display_label="Ocimum basilicum \u2018Genovese\u2019",
        scientific_name="Ocimum basilicum",
        cultivar_name="Genovese",
        common_name="Basil",
        representation="living",
        retained_records=4,
        current_records=3,
        living_records=2,
        occurrence_eligibility="available",
        external_taxon_id="48GBK",
        matches_scope=True,
    )
    current = response(
        cast(
            Row[tuple[BotanicalIdentity, int, int, int, str | None, int]],
            (identity, 2, 1, 0, None, 0),
        ),
        "current",
    )
    assert current.representation == "current"
    assert current.matches_scope
    assert current.occurrence_eligibility == "not_linked"
    historical = response(
        cast(
            Row[tuple[BotanicalIdentity, int, int, int, str | None, int]],
            (identity, 2, 0, 0, None, 1),
        ),
        "living",
    )
    assert historical.representation == "historical"
    assert not historical.matches_scope
    assert historical.occurrence_eligibility == "incompatible"


@pytest.mark.parametrize(
    ("scope", "expected_column"),
    [
        ("all", None),
        ("living", "living"),
        ("current", "current"),
        ("historical", "current"),
    ],
)
def test_list_projection_is_bounded_two_query_and_scope_aware(
    scope: RepresentationScope, expected_column: str | None
) -> None:
    identity = BotanicalIdentity(
        id=uuid7(),
        scientific_name="Ocimum basilicum",
        cultivar_name=None,
        common_name="Basil",
    )
    count_result, page_result = MagicMock(), MagicMock()
    count_result.one.return_value = (3, 1)
    current, living = (0, 0) if scope == "historical" else (1, 1)
    page_result.all.return_value = [(identity, 2, current, living, "48GBK", 1)]
    database = MagicMock()
    database.execute.side_effect = [count_result, page_result]

    page = list_identities(database, scope=scope, q="basil", offset=100, limit=100)

    assert database.execute.call_count == 2
    count_sql, page_sql = [
        str(
            call.args[0].compile(
                dialect=postgres_dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )
        for call in database.execute.call_args_list
    ]
    assert "count(" in count_sql.lower()
    assert "basil" in count_sql.lower()
    assert "limit 100 offset 100" in page_sql.lower()
    assert "order by lower(" in page_sql.lower()
    if expected_column:
        where_clause = " ".join(page_sql.lower().split()).split(" where ", 1)[1]
        assert f".{expected_column} " in where_clause
        assert ("= 0" if scope == "historical" else "> 0") in where_clause
    assert page.total == 3
    assert page.occurrence_ready == 1
    assert page.items[0].matches_scope


def test_get_identity_returns_exact_local_projection_or_none() -> None:
    identity = BotanicalIdentity(id=uuid7(), scientific_name="Ocimum basilicum")
    row = (identity, 1, 1, 0, None, 0)
    database = MagicMock()
    database.execute.return_value.one_or_none.return_value = row
    result = get_identity(database, identity.id, "current")
    assert result is not None
    assert result.id == identity.id
    assert result.representation == "current"
    assert result.matches_scope
    database.execute.return_value.one_or_none.return_value = None
    assert get_identity(database, uuid7(), "all") is None


def test_projection_includes_only_owned_collection_relationships() -> None:
    sql = str(projection().compile(dialect=postgres_dialect()))
    assert "seed_lots" in sql
    assert "sowings" in sql
    assert "plants" in sql
    assert "plant_groups" in sql
    assert "harvest_material_inventory" in sql
    assert "external_taxon_links" in sql
    assert "outer join" in sql.lower()
