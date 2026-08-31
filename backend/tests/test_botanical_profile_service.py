from unittest.mock import MagicMock, patch
from uuid import uuid7

import pytest
from fastapi import HTTPException, Response

from florabase.auth.dependencies import AuthenticatedActor
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_profiles.api import put, read
from florabase.botanical_profiles.model import BotanicalProfile
from florabase.botanical_profiles.schemas import BotanicalProfilePut
from florabase.botanical_profiles.service import (
    BotanicalIdentityNotFoundError,
    EmptyProfileError,
    PutProfileResult,
    botanical_identity_exists,
    get_botanical_profile,
    put_botanical_profile,
)


def test_profile_lookup_and_parent_existence_use_the_identity_key() -> None:
    database = MagicMock()
    identity_id = uuid7()
    profile = BotanicalProfile(botanical_identity_id=identity_id, description="Reference")
    identity = BotanicalIdentity(id=identity_id, scientific_name="Acer palmatum")
    database.get.side_effect = [profile, identity, None]

    assert get_botanical_profile(database, identity_id) is profile
    assert botanical_identity_exists(database, identity_id)
    assert not botanical_identity_exists(database, uuid7())


def test_put_profile_handles_missing_parent_empty_create_and_final_clear() -> None:
    database = MagicMock()
    identity_id = uuid7()

    with (
        patch(
            "florabase.botanical_profiles.service.botanical_identity_exists",
            return_value=False,
        ),
        pytest.raises(BotanicalIdentityNotFoundError),
    ):
        put_botanical_profile(database, identity_id, BotanicalProfilePut(description="Reference"))

    with (
        patch(
            "florabase.botanical_profiles.service.botanical_identity_exists",
            return_value=True,
        ),
        patch("florabase.botanical_profiles.service.get_botanical_profile", return_value=None),
        pytest.raises(EmptyProfileError),
    ):
        put_botanical_profile(database, identity_id, BotanicalProfilePut())

    profile = BotanicalProfile(botanical_identity_id=identity_id, description="Reference")
    with (
        patch(
            "florabase.botanical_profiles.service.botanical_identity_exists",
            return_value=True,
        ),
        patch("florabase.botanical_profiles.service.get_botanical_profile", return_value=profile),
    ):
        result = put_botanical_profile(database, identity_id, BotanicalProfilePut())
    assert result == PutProfileResult(profile=None, created=False)
    database.delete.assert_called_once_with(profile)
    database.flush.assert_called_once_with()


def test_put_profile_uses_postgresql_upsert_for_create_and_update() -> None:
    database = MagicMock()
    identity_id = uuid7()
    persisted = BotanicalProfile(botanical_identity_id=identity_id, uses="Ornamental")
    database.scalars.return_value.one.return_value = persisted

    with (
        patch(
            "florabase.botanical_profiles.service.botanical_identity_exists",
            return_value=True,
        ),
        patch("florabase.botanical_profiles.service.get_botanical_profile", return_value=None),
    ):
        created = put_botanical_profile(
            database, identity_id, BotanicalProfilePut(uses="Ornamental")
        )
    assert created == PutProfileResult(profile=persisted, created=True)
    assert database.scalars.call_count == 1

    with (
        patch(
            "florabase.botanical_profiles.service.botanical_identity_exists",
            return_value=True,
        ),
        patch(
            "florabase.botanical_profiles.service.get_botanical_profile",
            return_value=persisted,
        ),
    ):
        updated = put_botanical_profile(
            database, identity_id, BotanicalProfilePut(description="Updated")
        )
    assert updated == PutProfileResult(profile=persisted, created=False)


def test_profile_api_maps_read_and_put_outcomes() -> None:
    database = MagicMock()
    actor = MagicMock(spec=AuthenticatedActor)
    actor.owner = True
    identity_id = uuid7()
    profile = BotanicalProfile(botanical_identity_id=identity_id, description="Reference")

    with patch("florabase.botanical_profiles.api.get_botanical_profile", return_value=profile):
        assert read(identity_id, actor, database).description == "Reference"

    with (
        patch("florabase.botanical_profiles.api.get_botanical_profile", return_value=None),
        patch("florabase.botanical_profiles.api.botanical_identity_exists", return_value=False),
        pytest.raises(HTTPException) as missing_identity,
    ):
        read(identity_id, actor, database)
    assert isinstance(missing_identity.value.detail, dict)
    assert missing_identity.value.detail["code"] == "botanical_identity_not_found"

    with (
        patch("florabase.botanical_profiles.api.get_botanical_profile", return_value=None),
        patch("florabase.botanical_profiles.api.botanical_identity_exists", return_value=True),
        pytest.raises(HTTPException) as missing_profile,
    ):
        read(identity_id, actor, database)
    assert isinstance(missing_profile.value.detail, dict)
    assert missing_profile.value.detail["code"] == "botanical_profile_not_found"

    for failure, code in (
        (BotanicalIdentityNotFoundError(), "botanical_identity_not_found"),
        (EmptyProfileError(), "botanical_profile_empty"),
    ):
        with (
            patch("florabase.botanical_profiles.api.put_botanical_profile", side_effect=failure),
            pytest.raises(HTTPException) as caught,
        ):
            put(identity_id, BotanicalProfilePut(), Response(), actor, database)
        assert isinstance(caught.value.detail, dict)
        assert caught.value.detail["code"] == code

    response = Response()
    with patch(
        "florabase.botanical_profiles.api.put_botanical_profile",
        return_value=PutProfileResult(profile=None, created=False),
    ):
        cleared = put(identity_id, BotanicalProfilePut(), response, actor, database)
    assert isinstance(cleared, Response)
    assert cleared.status_code == 204

    response = Response()
    with patch(
        "florabase.botanical_profiles.api.put_botanical_profile",
        return_value=PutProfileResult(profile=profile, created=True),
    ):
        result = put(
            identity_id,
            BotanicalProfilePut(description="Reference"),
            response,
            actor,
            database,
        )
    assert result is not None
    assert response.status_code == 201
    assert response.headers["location"].endswith(f"/{identity_id}/profile")
