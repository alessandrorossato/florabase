from collections.abc import Sequence
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from florabase.auth.dependencies import (
    AuthenticatedActor,
    require_authenticated_actor,
    require_csrf,
    require_owner,
)
from florabase.botanical_identities.model import BotanicalIdentity, BotanicalIdentityName
from florabase.botanical_identities.reconciliation import (
    ReconciliationConflictError,
    ReconciliationNotFoundError,
    _historical_name_response,
    correct_accepted_name,
    inspect_reconciliation,
    merge_duplicate_identity,
)
from florabase.botanical_identities.schemas import (
    AcceptedNameCorrectionWrite,
    BotanicalIdentityCreate,
    BotanicalIdentityResponse,
    BotanicalIdentityUpdate,
    DuplicateIdentityMergeWrite,
    HistoricalNameStatusKind,
    IdentityHistoricalNameResponse,
    IdentityReconciliationResponse,
    OperatorSynonymCreate,
    OperatorSynonymUpdate,
)
from florabase.botanical_identities.service import (
    BotanicalIdentityConflictError,
    BotanicalIdentityCoverReferencedError,
    BotanicalIdentityMergedError,
    BotanicalIdentityNotFoundError,
    BotanicalIdentityReferencedError,
    ImmutableHistoricalNameError,
    SynonymNotFoundError,
    SynonymValidationError,
    add_operator_synonym,
    create_botanical_identity,
    delete_botanical_identity,
    get_botanical_identity,
    list_botanical_identity_directory,
    list_identity_synonyms,
    remove_operator_synonym,
    update_botanical_identity,
    update_operator_synonym,
)
from florabase.collection_views.schemas import BotanicalIdentityCollectionResponse
from florabase.collection_views.service import botanical_identity_collection
from florabase.core.config import Settings, get_settings
from florabase.db.session import get_database_session
from florabase.native_range_enrichment.source import WcvpSource
from florabase.taxonomy.source import WfoSource

router = APIRouter(prefix="/botanical-identities", tags=["botanical identities"])


def wfo_source_dependency(settings: Annotated[Settings, Depends(get_settings)]) -> WfoSource:
    return WfoSource(settings.wfo_snapshot_path)


def wcvp_v15_source_dependency(
    settings: Annotated[Settings, Depends(get_settings)],
) -> WcvpSource:
    return WcvpSource.from_settings(settings, "15")


def wcvp_v16_source_dependency(
    settings: Annotated[Settings, Depends(get_settings)],
) -> WcvpSource:
    return WcvpSource.from_settings(settings, "16")


def _reconciliation_fail(error: Exception) -> NoReturn:
    if isinstance(error, ReconciliationNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "botanical_identity_not_found",
                "message": "Botanical identity not found",
            },
        ) from error
    if isinstance(error, ReconciliationConflictError):
        detail: dict[str, object] = {
            "code": error.code,
            "message": error.message,
        }
        if error.existing_id is not None:
            detail["existing_id"] = str(error.existing_id)
        if error.conflicting_fields is not None:
            detail["conflicting_fields"] = error.conflicting_fields
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        ) from error
    raise error


def _conflict_detail(
    existing_id: UUID | None,
    message: str = "Botanical identity already exists",
    code: str = "botanical_identity_conflict",
) -> dict[str, str | None]:
    return {
        "code": code,
        "message": message,
        "existing_id": str(existing_id) if existing_id is not None else None,
    }


_SYNONYM_STATUS_KINDS = (
    "operator_synonym",
    "source_synonym",
    "initial_recorded",
    "former_accepted",
    "merged_duplicate",
)


def _synonyms_for_identities(
    database: Session, identities: Sequence[BotanicalIdentity]
) -> dict[UUID, list[str]]:
    if not identities:
        return {}
    identity_ids = [identity.id for identity in identities]
    active_names = {
        identity.id: (
            identity.scientific_name.casefold(),
            (identity.cultivar_name or "").casefold(),
        )
        for identity in identities
    }
    rows = database.execute(
        select(
            BotanicalIdentityName.botanical_identity_id,
            BotanicalIdentityName.scientific_name,
            BotanicalIdentityName.cultivar_name,
        )
        .where(
            BotanicalIdentityName.botanical_identity_id.in_(identity_ids),
            BotanicalIdentityName.status_kind.in_(_SYNONYM_STATUS_KINDS),
        )
        .order_by(BotanicalIdentityName.effective_from.asc(), BotanicalIdentityName.id.asc())
    ).all()
    synonyms_by_id: dict[UUID, list[str]] = {}
    for ident_id, scientific_name, cultivar_name in rows:
        active = active_names.get(ident_id)
        if (
            active is not None
            and (
                scientific_name.casefold(),
                (cultivar_name or "").casefold(),
            )
            == active
        ):
            continue
        names = synonyms_by_id.setdefault(ident_id, [])
        if scientific_name not in names:
            names.append(scientific_name)
    return synonyms_by_id


def _get_identity_synonyms(database: Session, identity: BotanicalIdentity) -> list[str]:
    return _synonyms_for_identities(database, [identity]).get(identity.id, [])


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
    database: Annotated[Session, Depends(get_database_session, scope="function")],
) -> list[BotanicalIdentityResponse]:
    directory_rows = list_botanical_identity_directory(database)
    synonyms_by_id = _synonyms_for_identities(
        database, [identity for identity, _, _, _ in directory_rows]
    )

    return [
        BotanicalIdentityResponse.from_model(
            botanical_identity,
            compact_cover_kind=compact_cover_kind,
            compact_external_cover_url=compact_external_cover_url,
            collection_counts=counts,
            synonyms=synonyms_by_id.get(botanical_identity.id, []),
        )
        for (
            botanical_identity,
            compact_cover_kind,
            compact_external_cover_url,
            counts,
        ) in directory_rows
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
    database: Annotated[Session, Depends(get_database_session, scope="function")],
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
    return BotanicalIdentityResponse.from_model(
        botanical_identity,
        synonyms=_get_identity_synonyms(database, botanical_identity),
    )


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
    database: Annotated[Session, Depends(get_database_session, scope="function")],
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
    return BotanicalIdentityResponse.from_model(
        botanical_identity,
        synonyms=_get_identity_synonyms(database, botanical_identity),
    )


@router.get(
    "/{botanical_identity_id}/collection",
    response_model=BotanicalIdentityCollectionResponse,
    operation_id="getBotanicalIdentityCollection",
)
def read_collection(
    botanical_identity_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session, scope="function")],
) -> BotanicalIdentityCollectionResponse:
    result = botanical_identity_collection(database, botanical_identity_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "botanical_identity_not_found",
                "message": "Botanical identity not found",
            },
        )
    return result


@router.put(
    "/{botanical_identity_id}",
    response_model=BotanicalIdentityResponse,
    operation_id="updateBotanicalIdentity",
)
def update(
    botanical_identity_id: UUID,
    payload: BotanicalIdentityUpdate,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session, scope="function")],
) -> BotanicalIdentityResponse:
    require_owner(actor)
    botanical_identity = get_botanical_identity(database, botanical_identity_id)
    if botanical_identity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "botanical_identity_not_found",
                "message": "Botanical identity not found",
            },
        )
    try:
        updated = update_botanical_identity(database, botanical_identity, payload)
    except BotanicalIdentityMergedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "botanical_identity_merged",
                "message": "Botanical identity has been merged into another identity",
                "existing_id": str(error.merged_into_id),
            },
        ) from error
    except BotanicalIdentityConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_conflict_detail(error.existing_id),
        ) from error
    return BotanicalIdentityResponse.from_model(
        updated,
        synonyms=_get_identity_synonyms(database, updated),
    )


@router.get(
    "/{botanical_identity_id}/reconciliation",
    response_model=IdentityReconciliationResponse,
    operation_id="getBotanicalIdentityReconciliation",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
        status.HTTP_404_NOT_FOUND: {"description": "Botanical identity not found"},
    },
)
def read_reconciliation(
    botanical_identity_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session, scope="function")],
    wfo_source: Annotated[WfoSource, Depends(wfo_source_dependency)],
    wcvp_v15_source: Annotated[WcvpSource, Depends(wcvp_v15_source_dependency)],
    wcvp_v16_source: Annotated[WcvpSource, Depends(wcvp_v16_source_dependency)],
) -> IdentityReconciliationResponse:
    try:
        return inspect_reconciliation(
            database,
            botanical_identity_id,
            wfo_source=wfo_source,
            wcvp_v15_source=wcvp_v15_source,
            wcvp_v16_source=wcvp_v16_source,
        )
    except (ReconciliationNotFoundError, ReconciliationConflictError) as error:
        _reconciliation_fail(error)


@router.post(
    "/{botanical_identity_id}/reconciliation/correct-name",
    response_model=IdentityReconciliationResponse,
    operation_id="correctBotanicalIdentityAcceptedName",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
        status.HTTP_403_FORBIDDEN: {"description": "Request forbidden"},
        status.HTTP_404_NOT_FOUND: {"description": "Botanical identity not found"},
        status.HTTP_409_CONFLICT: {"description": "Reconciliation conflict"},
    },
)
def correct_name(
    botanical_identity_id: UUID,
    payload: AcceptedNameCorrectionWrite,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session, scope="function")],
    wfo_source: Annotated[WfoSource, Depends(wfo_source_dependency)],
    wcvp_v15_source: Annotated[WcvpSource, Depends(wcvp_v15_source_dependency)],
    wcvp_v16_source: Annotated[WcvpSource, Depends(wcvp_v16_source_dependency)],
) -> IdentityReconciliationResponse:
    require_owner(actor)
    try:
        return correct_accepted_name(
            database,
            botanical_identity_id,
            payload,
            actor_user_id=actor.user_id,
            wfo_source=wfo_source,
            wcvp_v15_source=wcvp_v15_source,
            wcvp_v16_source=wcvp_v16_source,
        )
    except (ReconciliationNotFoundError, ReconciliationConflictError) as error:
        _reconciliation_fail(error)


@router.post(
    "/{botanical_identity_id}/reconciliation/merge-duplicate",
    response_model=IdentityReconciliationResponse,
    operation_id="mergeDuplicateBotanicalIdentity",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
        status.HTTP_403_FORBIDDEN: {"description": "Request forbidden"},
        status.HTTP_404_NOT_FOUND: {"description": "Botanical identity not found"},
        status.HTTP_409_CONFLICT: {"description": "Reconciliation conflict"},
    },
)
def merge_duplicate(
    botanical_identity_id: UUID,
    payload: DuplicateIdentityMergeWrite,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session, scope="function")],
    wfo_source: Annotated[WfoSource, Depends(wfo_source_dependency)],
    wcvp_v15_source: Annotated[WcvpSource, Depends(wcvp_v15_source_dependency)],
    wcvp_v16_source: Annotated[WcvpSource, Depends(wcvp_v16_source_dependency)],
) -> IdentityReconciliationResponse:
    require_owner(actor)
    try:
        return merge_duplicate_identity(
            database,
            botanical_identity_id,
            payload,
            actor_user_id=actor.user_id,
            wfo_source=wfo_source,
            wcvp_v15_source=wcvp_v15_source,
            wcvp_v16_source=wcvp_v16_source,
        )
    except (ReconciliationNotFoundError, ReconciliationConflictError) as error:
        _reconciliation_fail(error)


@router.delete(
    "/{botanical_identity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteBotanicalIdentity",
)
def delete(
    botanical_identity_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session, scope="function")],
) -> Response:
    require_owner(actor)
    botanical_identity = get_botanical_identity(database, botanical_identity_id)
    if botanical_identity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "botanical_identity_not_found",
                "message": "Botanical identity not found",
            },
        )
    try:
        delete_botanical_identity(database, botanical_identity)
    except BotanicalIdentityCoverReferencedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "botanical_identity_has_cover",
                "message": (
                    "Remove this botanical identity's cover image before deleting the identity."
                ),
            },
        ) from error
    except BotanicalIdentityReferencedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "botanical_identity_referenced",
                "message": (
                    "This botanical identity has collection records or retained native-range "
                    "source applications and cannot be deleted."
                ),
            },
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{botanical_identity_id}/synonyms",
    response_model=list[IdentityHistoricalNameResponse],
    operation_id="listBotanicalIdentitySynonyms",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
        status.HTTP_404_NOT_FOUND: {"description": "Botanical identity not found"},
    },
)
def list_synonyms(
    botanical_identity_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session, scope="function")],
    status_kind: HistoricalNameStatusKind | None = None,
) -> list[IdentityHistoricalNameResponse]:
    try:
        entries = list_identity_synonyms(database, botanical_identity_id, status_kind=status_kind)
    except BotanicalIdentityNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "botanical_identity_not_found",
                "message": "Botanical identity not found",
            },
        ) from error
    return [_historical_name_response(entry) for entry in entries]


@router.post(
    "/{botanical_identity_id}/synonyms",
    response_model=IdentityHistoricalNameResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createBotanicalIdentitySynonym",
    responses={
        status.HTTP_201_CREATED: {
            "headers": {
                "Location": {
                    "description": "Canonical URL of the created synonym",
                    "schema": {"type": "string"},
                }
            }
        },
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
        status.HTTP_403_FORBIDDEN: {"description": "Request forbidden"},
        status.HTTP_404_NOT_FOUND: {"description": "Botanical identity not found"},
        status.HTTP_409_CONFLICT: {"description": "Synonym conflict or validation failure"},
    },
)
def create_synonym(
    botanical_identity_id: UUID,
    payload: OperatorSynonymCreate,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session, scope="function")],
) -> IdentityHistoricalNameResponse:
    require_owner(actor)
    try:
        entry = add_operator_synonym(database, botanical_identity_id, payload)
    except BotanicalIdentityNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "botanical_identity_not_found",
                "message": "Botanical identity not found",
            },
        ) from error
    except BotanicalIdentityMergedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "botanical_identity_merged",
                "message": "Botanical identity has been merged into another identity",
                "existing_id": str(error.merged_into_id),
            },
        ) from error
    except SynonymValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": error.code, "message": error.message},
        ) from error
    except BotanicalIdentityConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_conflict_detail(
                error.existing_id,
                message=error.message,
                code="duplicate_botanical_identity",
            ),
        ) from error

    response.headers["Location"] = (
        f"/api/v1/botanical-identities/{botanical_identity_id}/synonyms/{entry.id}"
    )
    return _historical_name_response(entry)


@router.put(
    "/{botanical_identity_id}/synonyms/{name_id}",
    response_model=IdentityHistoricalNameResponse,
    operation_id="updateBotanicalIdentitySynonym",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
        status.HTTP_403_FORBIDDEN: {"description": "Request forbidden"},
        status.HTTP_404_NOT_FOUND: {"description": "Synonym or botanical identity not found"},
        status.HTTP_409_CONFLICT: {"description": "Synonym conflict or immutable historical name"},
    },
)
def update_synonym(
    botanical_identity_id: UUID,
    name_id: UUID,
    payload: OperatorSynonymUpdate,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session, scope="function")],
) -> IdentityHistoricalNameResponse:
    require_owner(actor)
    try:
        entry = update_operator_synonym(database, botanical_identity_id, name_id, payload)
    except BotanicalIdentityNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "botanical_identity_not_found",
                "message": "Botanical identity not found",
            },
        ) from error
    except SynonymNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "synonym_not_found", "message": "Synonym not found"},
        ) from error
    except BotanicalIdentityMergedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "botanical_identity_merged",
                "message": "Botanical identity has been merged into another identity",
                "existing_id": str(error.merged_into_id),
            },
        ) from error
    except ImmutableHistoricalNameError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "immutable_historical_name", "message": error.message},
        ) from error
    except SynonymValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": error.code, "message": error.message},
        ) from error
    except BotanicalIdentityConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_conflict_detail(
                error.existing_id,
                message=error.message,
                code="duplicate_botanical_identity",
            ),
        ) from error

    return _historical_name_response(entry)


@router.delete(
    "/{botanical_identity_id}/synonyms/{name_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteBotanicalIdentitySynonym",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
        status.HTTP_403_FORBIDDEN: {"description": "Request forbidden"},
        status.HTTP_404_NOT_FOUND: {"description": "Synonym or botanical identity not found"},
        status.HTTP_409_CONFLICT: {"description": "Immutable historical name or merged identity"},
    },
)
def delete_synonym(
    botanical_identity_id: UUID,
    name_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session, scope="function")],
) -> Response:
    require_owner(actor)
    try:
        remove_operator_synonym(database, botanical_identity_id, name_id)
    except BotanicalIdentityNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "botanical_identity_not_found",
                "message": "Botanical identity not found",
            },
        ) from error
    except SynonymNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "synonym_not_found", "message": "Synonym not found"},
        ) from error
    except BotanicalIdentityMergedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "botanical_identity_merged",
                "message": "Botanical identity has been merged into another identity",
                "existing_id": str(error.merged_into_id),
            },
        ) from error
    except ImmutableHistoricalNameError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "immutable_historical_name", "message": error.message},
        ) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)
