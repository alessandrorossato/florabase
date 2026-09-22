from unittest.mock import MagicMock, patch
from uuid import uuid7

import pytest
from sqlalchemy.exc import IntegrityError

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.schemas import (
    BotanicalIdentityCreate,
    BotanicalIdentityUpdate,
    IdentityCollectionCounts,
)
from florabase.botanical_identities.service import (
    BotanicalIdentityConflictError,
    BotanicalIdentityCoverReferencedError,
    BotanicalIdentityReferencedError,
    create_botanical_identity,
    delete_botanical_identity,
    list_botanical_identity_directory,
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
    database.scalar.side_effect = [0, 0, 0, 0]
    delete_botanical_identity(database, identity)
    database.delete.assert_called_once_with(identity)

    database = MagicMock()
    database.scalar.side_effect = [0, 1, 0, 0]
    with pytest.raises(BotanicalIdentityReferencedError):
        delete_botanical_identity(database, identity)
    database.delete.assert_not_called()

    database = MagicMock()
    database.scalar.return_value = 1
    with pytest.raises(BotanicalIdentityCoverReferencedError):
        delete_botanical_identity(database, identity)
    database.delete.assert_not_called()


def test_directory_uses_one_aggregate_query_and_maps_cover_and_collection_counts() -> None:
    identity = BotanicalIdentity(id=uuid7(), scientific_name="Acer palmatum")
    database = MagicMock()
    database.execute.return_value.all.return_value = [
        (identity, "external", "https://example.test/maple.jpg", 2, 3, 4, 5)
    ]

    result = list_botanical_identity_directory(database)

    assert result == [
        (
            identity,
            "external",
            "https://example.test/maple.jpg",
            IdentityCollectionCounts(seed_lots=2, sowings=3, plants=4, plant_groups=5),
        )
    ]
    database.execute.assert_called_once()
    sql = str(database.execute.call_args.args[0])
    assert "count(" in sql.lower()
    assert "sowings" in sql.lower()
    assert "plant_groups" in sql.lower()
