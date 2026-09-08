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
from florabase.db.session import get_database_session
from florabase.suppliers.model import Supplier
from florabase.suppliers.schemas import (
    SupplierCreate,
    SupplierDetailResponse,
    SupplierListResponse,
    SupplierResponse,
    SupplierUpdate,
)
from florabase.suppliers.service import (
    create_supplier,
    get_supplier,
    get_supplier_detail,
    list_suppliers,
    set_supplier_retired,
    update_supplier,
)

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "supplier_not_found", "message": "Supplier not found"},
    )


def _require_supplier(database: Session, supplier_id: UUID) -> Supplier:
    supplier = get_supplier(database, supplier_id)
    if supplier is None:
        raise _not_found()
    return supplier


@router.get("", response_model=list[SupplierListResponse], operation_id="listSuppliers")
def list_all(
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> list[SupplierListResponse]:
    return list_suppliers(database)


@router.post(
    "",
    response_model=SupplierResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createSupplier",
)
def create(
    payload: SupplierCreate,
    response: Response,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> SupplierResponse:
    require_owner(actor)
    supplier = create_supplier(database, payload)
    response.headers["Location"] = f"/api/v1/suppliers/{supplier.id}"
    return SupplierResponse.from_model(supplier)


@router.get("/{supplier_id}", response_model=SupplierDetailResponse, operation_id="getSupplier")
def read(
    supplier_id: UUID,
    _actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)],
    database: Annotated[Session, Depends(get_database_session)],
) -> SupplierDetailResponse:
    return get_supplier_detail(database, _require_supplier(database, supplier_id))


@router.put("/{supplier_id}", response_model=SupplierResponse, operation_id="updateSupplier")
def update(
    supplier_id: UUID,
    payload: SupplierUpdate,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> SupplierResponse:
    require_owner(actor)
    return SupplierResponse.from_model(
        update_supplier(database, _require_supplier(database, supplier_id), payload)
    )


@router.post(
    "/{supplier_id}/retire",
    response_model=SupplierResponse,
    operation_id="retireSupplier",
)
def retire(
    supplier_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> SupplierResponse:
    require_owner(actor)
    return SupplierResponse.from_model(
        set_supplier_retired(database, _require_supplier(database, supplier_id), retired=True)
    )


@router.post(
    "/{supplier_id}/reactivate",
    response_model=SupplierResponse,
    operation_id="reactivateSupplier",
)
def reactivate(
    supplier_id: UUID,
    actor: Annotated[AuthenticatedActor, Depends(require_csrf)],
    database: Annotated[Session, Depends(get_database_session)],
) -> SupplierResponse:
    require_owner(actor)
    return SupplierResponse.from_model(
        set_supplier_retired(database, _require_supplier(database, supplier_id), retired=False)
    )
