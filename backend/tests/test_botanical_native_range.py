from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock, patch
from uuid import uuid7

import pytest
from fastapi import HTTPException, Response

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_profiles import api
from florabase.botanical_profiles.model import BotanicalProfile, BotanicalProfileNativeRange
from florabase.botanical_profiles.schemas import (
    BotanicalNativeRangeCreate,
    BotanicalNativeRangeResponse,
)
from florabase.botanical_profiles.service import (
    BotanicalIdentityNotFoundError,
    BotanicalNativeRangeConflictError,
    BotanicalNativeRangeNotFoundError,
    GeographicPlaceNotFoundError,
    add_botanical_native_range,
    list_botanical_native_ranges,
    remove_botanical_native_range,
)
from florabase.geographic_places.model import GeographicPlace


def place(name: str = "Brazil") -> GeographicPlace:
    return GeographicPlace(
        id=uuid7(),
        name=name,
        parent_id=None,
        place_kind="canonical",
        source_name="unicode_cldr",
        source_version="48.2.1",
        source_code_type="iso_3166_1_alpha_2",
        source_code="BR",
    )


def test_list_native_ranges_validates_identity_derives_paths_and_sorts() -> None:
    database = MagicMock()
    identity_id = uuid7()
    world = place("World")
    brazil = place()
    brazil.parent_id = world.id
    native_range = BotanicalProfileNativeRange(
        botanical_profile_id=identity_id,
        geographic_place_id=brazil.id,
        created_at=datetime.now(UTC),
    )
    with (
        patch(
            "florabase.botanical_profiles.service.botanical_identity_exists",
            return_value=False,
        ),
        pytest.raises(BotanicalIdentityNotFoundError),
    ):
        list_botanical_native_ranges(database, identity_id)

    database.scalars.return_value = [native_range]
    with (
        patch(
            "florabase.botanical_profiles.service.botanical_identity_exists",
            return_value=True,
        ),
        patch(
            "florabase.botanical_profiles.service.list_geographic_places",
            return_value=[world, brazil],
        ),
    ):
        result = list_botanical_native_ranges(database, identity_id)
    assert [item.geographic_place_path for item in result] == ["World → Brazil"]


def test_add_native_range_handles_missing_records_profile_creation_and_duplicate() -> None:
    database = MagicMock()
    identity_id = uuid7()
    geographic_place = place()
    identity = BotanicalIdentity(id=identity_id, scientific_name="Test plant")
    profile = BotanicalProfile(botanical_identity_id=identity_id, description="Reference")

    database.scalar.return_value = None
    with pytest.raises(GeographicPlaceNotFoundError):
        add_botanical_native_range(database, identity_id, geographic_place.id)

    database.scalar.side_effect = [geographic_place, None]
    with pytest.raises(BotanicalIdentityNotFoundError):
        add_botanical_native_range(database, identity_id, geographic_place.id)

    database.reset_mock()
    database.scalar.side_effect = [geographic_place, identity, profile]
    database.get.return_value = BotanicalProfileNativeRange(
        botanical_profile_id=identity_id,
        geographic_place_id=geographic_place.id,
    )
    with pytest.raises(BotanicalNativeRangeConflictError):
        add_botanical_native_range(database, identity_id, geographic_place.id)

    database.reset_mock()
    database.scalar.side_effect = [geographic_place, identity, None]
    database.get.return_value = None
    expected = MagicMock(spec=BotanicalNativeRangeResponse)
    with (
        patch(
            "florabase.botanical_profiles.service.list_geographic_places",
            return_value=[geographic_place],
        ),
        patch(
            "florabase.botanical_profiles.service.BotanicalNativeRangeResponse.from_models",
            return_value=expected,
        ),
    ):
        result = add_botanical_native_range(database, identity_id, geographic_place.id)
    assert result is expected
    assert any(isinstance(call.args[0], BotanicalProfile) for call in database.add.call_args_list)
    assert any(
        isinstance(call.args[0], BotanicalProfileNativeRange)
        for call in database.add.call_args_list
    )


def test_remove_native_range_cleans_only_a_truly_empty_profile() -> None:
    database = MagicMock()
    identity_id = uuid7()
    geographic_place = place()
    identity = BotanicalIdentity(id=identity_id, scientific_name="Test plant")
    profile = BotanicalProfile(botanical_identity_id=identity_id)
    native_range = BotanicalProfileNativeRange(
        botanical_profile_id=identity_id,
        geographic_place_id=geographic_place.id,
    )

    database.scalar.side_effect = [geographic_place, None]
    with pytest.raises(BotanicalIdentityNotFoundError):
        remove_botanical_native_range(database, identity_id, geographic_place.id)

    database.reset_mock()
    database.scalar.side_effect = [geographic_place, identity, None]
    with pytest.raises(BotanicalNativeRangeNotFoundError):
        remove_botanical_native_range(database, identity_id, geographic_place.id)

    database.reset_mock()
    database.scalar.side_effect = [geographic_place, identity, profile]
    database.get.return_value = None
    with pytest.raises(BotanicalNativeRangeNotFoundError):
        remove_botanical_native_range(database, identity_id, geographic_place.id)

    database.reset_mock()
    database.scalar.side_effect = [geographic_place, identity, profile, 0]
    database.get.return_value = native_range
    remove_botanical_native_range(database, identity_id, geographic_place.id)
    assert database.delete.call_args_list == [
        ((native_range,), {}),
        ((profile,), {}),
    ]

    database.reset_mock()
    profile.description = "Reference"
    database.scalar.side_effect = [geographic_place, identity, profile, 0]
    database.get.return_value = native_range
    remove_botanical_native_range(database, identity_id, geographic_place.id)
    database.delete.assert_called_once_with(native_range)


def test_native_range_api_maps_success_and_domain_errors() -> None:
    database = MagicMock()
    actor = cast(Any, SimpleNamespace(owner=True))
    identity_id = uuid7()
    geographic_place_id = uuid7()
    payload = BotanicalNativeRangeCreate(geographic_place_id=geographic_place_id)
    native_range = BotanicalNativeRangeResponse(
        botanical_profile_id=identity_id,
        geographic_place_id=geographic_place_id,
        geographic_place_name="Brazil",
        geographic_place_path="World → Brazil",
        created_at=datetime.now(UTC),
    )

    with patch(
        "florabase.botanical_profiles.api.list_botanical_native_ranges",
        return_value=[native_range],
    ):
        assert api.list_native_ranges(identity_id, actor, database) == [native_range]
    with (
        patch(
            "florabase.botanical_profiles.api.list_botanical_native_ranges",
            side_effect=BotanicalIdentityNotFoundError,
        ),
        pytest.raises(HTTPException) as missing_identity,
    ):
        api.list_native_ranges(identity_id, actor, database)
    assert missing_identity.value.status_code == 404

    response = Response()
    with patch(
        "florabase.botanical_profiles.api.add_botanical_native_range",
        return_value=native_range,
    ):
        assert api.add_native_range(identity_id, payload, response, actor, database) is native_range
    assert response.headers["location"].endswith(str(geographic_place_id))

    for failure, status_code in (
        (BotanicalIdentityNotFoundError(), 404),
        (GeographicPlaceNotFoundError(), 404),
        (BotanicalNativeRangeConflictError(), 409),
    ):
        with (
            patch(
                "florabase.botanical_profiles.api.add_botanical_native_range",
                side_effect=failure,
            ),
            pytest.raises(HTTPException) as caught,
        ):
            api.add_native_range(identity_id, payload, Response(), actor, database)
        assert caught.value.status_code == status_code

    with patch("florabase.botanical_profiles.api.remove_botanical_native_range"):
        assert (
            api.remove_native_range(identity_id, geographic_place_id, actor, database).status_code
            == 204
        )
    for remove_failure in (
        BotanicalIdentityNotFoundError(),
        BotanicalNativeRangeNotFoundError(),
    ):
        with (
            patch(
                "florabase.botanical_profiles.api.remove_botanical_native_range",
                side_effect=remove_failure,
            ),
            pytest.raises(HTTPException) as caught,
        ):
            api.remove_native_range(identity_id, geographic_place_id, actor, database)
        assert caught.value.status_code == 404
