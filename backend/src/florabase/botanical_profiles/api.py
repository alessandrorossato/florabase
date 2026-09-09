from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from florabase.auth.dependencies import (
    AuthenticatedActor,
    require_authenticated_actor,
    require_csrf,
    require_owner,
)
from florabase.botanical_profiles.schemas import (
    BotanicalNativeRangeCreate,
    BotanicalNativeRangeResponse,
    BotanicalProfilePut,
    BotanicalProfileResponse,
)
from florabase.botanical_profiles.service import (
    BotanicalIdentityNotFoundError,
    BotanicalNativeRangeConflictError,
    BotanicalNativeRangeNotFoundError,
    EmptyProfileError,
    GeographicPlaceNotFoundError,
    add_botanical_native_range,
    botanical_identity_exists,
    get_botanical_profile,
    list_botanical_native_ranges,
    put_botanical_profile,
    remove_botanical_native_range,
)
from florabase.db.session import get_database_session

router = APIRouter(
    prefix="/botanical-identities/{botanical_identity_id}/profile",
    tags=["botanical profiles"],
)


def _identity_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "botanical_identity_not_found",
            "message": "Botanical identity not found",
        },
    )


def _place_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "geographic_place_not_found",
            "message": "Geographic place not found",
        },
    )


@router.get(
    "",
    response_model=BotanicalProfileResponse,
    operation_id="getBotanicalProfile",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
        status.HTTP_404_NOT_FOUND: {"description": "Identity or profile not found"},
    },
)
def read(
    botanical_identity_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> BotanicalProfileResponse:
    profile = get_botanical_profile(database, botanical_identity_id)
    if profile is not None:
        return BotanicalProfileResponse.from_model(profile)
    if not botanical_identity_exists(database, botanical_identity_id):
        raise _identity_not_found()
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "botanical_profile_not_found", "message": "Botanical profile not found"},
    )


@router.put(
    "",
    response_model=BotanicalProfileResponse,
    operation_id="putBotanicalProfile",
    responses={
        status.HTTP_201_CREATED: {"description": "Botanical profile created"},
        status.HTTP_204_NO_CONTENT: {
            "description": "Final meaningful profile datum cleared; profile removed"
        },
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
        status.HTTP_403_FORBIDDEN: {"description": "Request forbidden"},
        status.HTTP_404_NOT_FOUND: {"description": "Botanical identity not found"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "Profile content invalid"},
    },
)
def put(
    botanical_identity_id: UUID,
    payload: BotanicalProfilePut,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> BotanicalProfileResponse | Response:
    require_owner(actor)
    try:
        result = put_botanical_profile(database, botanical_identity_id, payload)
    except BotanicalIdentityNotFoundError as error:
        raise _identity_not_found() from error
    except EmptyProfileError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "botanical_profile_empty",
                "message": (
                    "A botanical profile requires meaningful data, such as a populated text "
                    "section or structured native range"
                ),
            },
        ) from error

    if result.profile is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    if result.created:
        response.status_code = status.HTTP_201_CREATED
        response.headers["Location"] = (
            f"/api/v1/botanical-identities/{botanical_identity_id}/profile"
        )
    return BotanicalProfileResponse.from_model(result.profile)


@router.get(
    "/native-ranges",
    response_model=list[BotanicalNativeRangeResponse],
    operation_id="listBotanicalNativeRanges",
)
def list_native_ranges(
    botanical_identity_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> list[BotanicalNativeRangeResponse]:
    try:
        return list_botanical_native_ranges(database, botanical_identity_id)
    except BotanicalIdentityNotFoundError as error:
        raise _identity_not_found() from error


@router.post(
    "/native-ranges",
    response_model=BotanicalNativeRangeResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="addBotanicalNativeRange",
)
def add_native_range(
    botanical_identity_id: UUID,
    payload: BotanicalNativeRangeCreate,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> BotanicalNativeRangeResponse:
    require_owner(actor)
    try:
        native_range = add_botanical_native_range(
            database, botanical_identity_id, payload.geographic_place_id
        )
    except BotanicalIdentityNotFoundError as error:
        raise _identity_not_found() from error
    except GeographicPlaceNotFoundError as error:
        raise _place_not_found() from error
    except BotanicalNativeRangeConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "botanical_native_range_exists",
                "message": "This geographic place is already in the native range",
            },
        ) from error
    response.headers["Location"] = (
        f"/api/v1/botanical-identities/{botanical_identity_id}/profile/native-ranges/"
        f"{payload.geographic_place_id}"
    )
    return native_range


@router.delete(
    "/native-ranges/{geographic_place_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="removeBotanicalNativeRange",
)
def remove_native_range(
    botanical_identity_id: UUID,
    geographic_place_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> Response:
    require_owner(actor)
    try:
        remove_botanical_native_range(database, botanical_identity_id, geographic_place_id)
    except BotanicalIdentityNotFoundError as error:
        raise _identity_not_found() from error
    except BotanicalNativeRangeNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "botanical_native_range_not_found",
                "message": "Botanical native range not found",
            },
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
