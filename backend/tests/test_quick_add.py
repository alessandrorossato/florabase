from typing import Any
from uuid import uuid7

import pytest
from pydantic import ValidationError

from florabase.quick_add.schemas import QuickAddRequest


@pytest.mark.parametrize(
    "body",
    [
        {"identity": {}},
        {"identity": {"existing_id": str(uuid7()), "new": {"scientific_name": "A b"}}},
        {"identity": {"new": {"scientific_name": " "}}},
        {"identity": {"new": {"scientific_name": "A b", "wfo": {"source_taxon_id": "wfo-1"}}}},
        {
            "identity": {"existing_id": str(uuid7())},
            "quantity": {"value": 3, "is_approximate": False},
        },
        {
            "identity": {"existing_id": str(uuid7())},
            "material": "plant_group",
            "quantity": {"value": 0, "is_approximate": False},
        },
        {"identity": {"existing_id": str(uuid7())}, "material": "seed_lot"},
        {"identity": {"existing_id": str(uuid7())}, "lifecycle": "dead"},
    ],
)
def test_rejects_ambiguous_or_invalid_requests(body: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        QuickAddRequest.model_validate(body)


def test_defaults_to_one_plant_with_unknown_origin() -> None:
    request = QuickAddRequest.model_validate(
        {"identity": {"new": {"scientific_name": "  Genus   species "}}}
    )
    assert request.material == "plant"
    assert request.direct_origin_kind == "unknown"
    assert request.identity.new is not None
    assert request.identity.new.scientific_name == "Genus species"
