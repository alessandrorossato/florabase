from unittest.mock import MagicMock, patch
from uuid import uuid7

import pytest
from sqlalchemy.exc import IntegrityError

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.schemas import BotanicalIdentityCreate, BotanicalIdentityUpdate
from florabase.botanical_identities.service import (
    BotanicalIdentityConflictError,
    BotanicalIdentityReferencedError,
    create_botanical_identity,
    delete_botanical_identity,
    update_botanical_identity,
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


def test_update_corrects_the_same_identity_and_rejects_a_duplicate() -> None:
    database = MagicMock()
    identity = BotanicalIdentity(id=uuid7(), scientific_name="Acer palmatum")
    payload = BotanicalIdentityUpdate(
        scientific_name="Acer japonicum", common_name="Fullmoon maple"
    )
    with patch("florabase.botanical_identities.service.find_duplicate", return_value=None):
        assert update_botanical_identity(database, identity, payload) is identity
    assert identity.scientific_name == "Acer japonicum"
    assert identity.common_name == "Fullmoon maple"

    duplicate = BotanicalIdentity(id=uuid7(), scientific_name="Acer japonicum")
    with (
        patch(
            "florabase.botanical_identities.service.find_duplicate",
            return_value=duplicate,
        ),
        pytest.raises(BotanicalIdentityConflictError),
    ):
        update_botanical_identity(database, identity, payload)


def test_delete_allows_unused_identity_and_rejects_collection_references() -> None:
    identity = BotanicalIdentity(id=uuid7(), scientific_name="Acer palmatum")
    database = MagicMock()
    database.scalar.side_effect = [0, 0, 0]
    delete_botanical_identity(database, identity)
    database.delete.assert_called_once_with(identity)

    database = MagicMock()
    database.scalar.side_effect = [1, 0, 0]
    with pytest.raises(BotanicalIdentityReferencedError):
        delete_botanical_identity(database, identity)
    database.delete.assert_not_called()
