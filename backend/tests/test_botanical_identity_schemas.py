from datetime import UTC, datetime
from uuid import uuid7

import pytest
from pydantic import ValidationError

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.schemas import (
    BotanicalIdentityCreate,
    BotanicalIdentityResponse,
)


def test_create_normalizes_only_the_botanical_identity_contract() -> None:
    payload = BotanicalIdentityCreate.model_validate(
        {
            "scientific_name": "  Acer\t palmatum  ",
            "cultivar_name": "  \u2018 Bloodgood \u2019  ",
            "common_name": "  Japanese   maple  ",
        }
    )

    assert payload.model_dump() == {
        "scientific_name": "Acer palmatum",
        "cultivar_name": "Bloodgood",
        "common_name": "Japanese maple",
    }


def test_optional_blanks_become_null_and_control_characters_are_rejected() -> None:
    payload = BotanicalIdentityCreate(
        scientific_name="Acer palmatum", cultivar_name="  ", common_name="\t"
    )
    assert payload.cultivar_name is None
    assert payload.common_name is None

    for field in ("scientific_name", "cultivar_name", "common_name"):
        values: dict[str, str] = {"scientific_name": "Acer palmatum", field: "bad\x00value"}
        with pytest.raises(ValidationError, match="control characters"):
            BotanicalIdentityCreate.model_validate(values)


def test_response_derives_canonical_label_without_persisting_it() -> None:
    now = datetime.now(UTC)
    botanical_identity = BotanicalIdentity(
        id=uuid7(),
        scientific_name="Acer palmatum",
        cultivar_name="Bloodgood",
        common_name="Japanese maple",
        created_at=now,
        updated_at=now,
    )

    response = BotanicalIdentityResponse.from_model(botanical_identity)

    assert response.display_label == "Acer palmatum \u2018Bloodgood\u2019"
    assert "display_label" not in BotanicalIdentity.__table__.columns
