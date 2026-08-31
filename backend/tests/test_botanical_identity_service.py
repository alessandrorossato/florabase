from unittest.mock import MagicMock, patch
from uuid import uuid7

import pytest
from sqlalchemy.exc import IntegrityError

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.schemas import BotanicalIdentityCreate
from florabase.botanical_identities.service import (
    BotanicalIdentityConflictError,
    create_botanical_identity,
)


def integrity_error(constraint_name: str) -> IntegrityError:
    original = MagicMock()
    original.diag.constraint_name = constraint_name
    return IntegrityError("insert", {}, original)


def test_unique_race_maps_only_the_botanical_identity_constraint() -> None:
    database = MagicMock()
    existing = BotanicalIdentity(id=uuid7(), scientific_name="Acer palmatum")
    payload = BotanicalIdentityCreate(scientific_name="acer palmatum")
    database.flush.side_effect = integrity_error("uq_botanical_identities_name_cultivar_ci")

    with (
        patch(
            "florabase.botanical_identities.service.find_duplicate",
            side_effect=[None, existing],
        ),
        pytest.raises(BotanicalIdentityConflictError) as caught,
    ):
        create_botanical_identity(database, payload)

    assert caught.value.existing_id == existing.id


def test_unrelated_integrity_error_is_not_misreported_as_a_duplicate() -> None:
    database = MagicMock()
    payload = BotanicalIdentityCreate(scientific_name="Acer palmatum")
    failure = integrity_error("some_other_constraint")
    database.flush.side_effect = failure

    with (
        patch("florabase.botanical_identities.service.find_duplicate", return_value=None),
        pytest.raises(IntegrityError) as caught,
    ):
        create_botanical_identity(database, payload)

    assert caught.value is failure
