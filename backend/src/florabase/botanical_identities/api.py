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
from florabase.botanical_identities.schemas import (
    BotanicalIdentityCreate,
    BotanicalIdentityResponse,
)
from florabase.botanical_identities.service import (
    BotanicalIdentityConflictError,
    create_botanical_identity,
    get_botanical_identity,
    list_botanical_identities,
)
from florabase.db.session import get_database_session

router = APIRouter(prefix="/botanical-identities", tags=["botanical identities"])


def _conflict_detail(existing_id: UUID | None) -> dict[str, str | None]:
    return {
        "code": "botanical_identity_conflict",
        "message": "Botanical identity already exists",
        "existing_id": str(existing_id) if existing_id is not None else None,
    }


@router.get(
    "",
    response_model=list[BotanicalIdentityResponse],
    operation_id="listBotanicalIdentities",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
    },
)
def list_all(
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> list[BotanicalIdentityResponse]:
    return [
        BotanicalIdentityResponse.from_model(botanical_identity)
        for botanical_identity in list_botanical_identities(database)
    ]


@router.post(
    "",
    response_model=BotanicalIdentityResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createBotanicalIdentity",
    responses={
        status.HTTP_201_CREATED: {
            "headers": {
                "Location": {
                    "description": "Canonical URL of the created BotanicalIdentity",
                    "schema": {"type": "string"},
                }
            }
        },
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
        status.HTTP_403_FORBIDDEN: {"description": "Request forbidden"},
        status.HTTP_409_CONFLICT: {"description": "Botanical identity already exists"},
    },
)
def create(
    payload: BotanicalIdentityCreate,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> BotanicalIdentityResponse:
    require_owner(actor)
    try:
        botanical_identity = create_botanical_identity(database, payload)
    except BotanicalIdentityConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_conflict_detail(error.existing_id),
        ) from error
    response.headers["Location"] = f"/api/v1/botanical-identities/{botanical_identity.id}"
    return BotanicalIdentityResponse.from_model(botanical_identity)


@router.get(
    "/{botanical_identity_id}",
    response_model=BotanicalIdentityResponse,
    operation_id="getBotanicalIdentity",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
        status.HTTP_404_NOT_FOUND: {"description": "Botanical identity not found"},
    },
)
def read(
    botanical_identity_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> BotanicalIdentityResponse:
    botanical_identity = get_botanical_identity(database, botanical_identity_id)
    if botanical_identity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "botanical_identity_not_found",
                "message": "Botanical identity not found",
            },
        )
    return BotanicalIdentityResponse.from_model(botanical_identity)
