from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from florabase.auth.dependencies import AuthenticatedActor, require_csrf, require_owner
from florabase.db.session import get_database_session
from florabase.plants.service import PlantDomainConflictError, PlantReferenceNotFoundError
from florabase.quick_add.schemas import QuickAddRequest, QuickAddResponse
from florabase.quick_add.service import QuickAddError, quick_add
from florabase.taxonomy.api import Source
from florabase.taxonomy.service import TaxonomyConflictError, TaxonomyNotFoundError
from florabase.taxonomy.source import SourceUnavailableError

router = APIRouter(prefix="/quick-add", tags=["quick add"])
Database = Annotated[Session, Depends(get_database_session, scope="function")]
Writer = Annotated[AuthenticatedActor, Depends(require_csrf)]


@router.post(
    "/plant",
    response_model=QuickAddResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="quickAddPlant",
    responses={
        404: {"description": "Botanical identity, Location or Supplier not found"},
        409: {"description": "Identity, link or record changed meanwhile"},
        422: {"description": "Invalid request, or the picked WFO name no longer matches"},
        503: {"description": "WFO index unavailable for a picked WFO name"},
    },
)
def quick_add_plant(
    payload: QuickAddRequest,
    response: Response,
    database: Database,
    actor: Writer,
    source: Source,
) -> QuickAddResponse:
    """Add a Plant or PlantGroup, creating its identity and WFO link when needed, atomically."""
    require_owner(actor)
    try:
        result = quick_add(database, payload, source)
    except QuickAddError as error:
        raise HTTPException(error.status, {"code": error.code, "message": error.message}) from error
    except PlantReferenceNotFoundError as error:
        raise HTTPException(404, {"code": error.code, "message": error.message}) from error
    except PlantDomainConflictError as error:
        raise HTTPException(409, {"code": error.code, "message": error.message}) from error
    except SourceUnavailableError as error:
        raise HTTPException(
            503,
            {
                "code": "taxonomy_unavailable",
                "message": "The WFO index is not available. Save without the WFO link.",
            },
        ) from error
    except TaxonomyNotFoundError as error:
        raise HTTPException(
            404, {"code": "botanical_identity_not_found", "message": str(error)}
        ) from error
    except TaxonomyConflictError as error:
        raise HTTPException(
            409,
            {
                "code": "taxonomy_conflict",
                "message": "The identity or its WFO link changed meanwhile. Try again.",
            },
        ) from error
    prefix = "plants" if result.record_kind == "plant" else "plant-groups"
    response.headers["Location"] = f"/api/v1/{prefix}/{result.record_id}"
    return result
