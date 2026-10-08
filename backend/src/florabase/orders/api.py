from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from florabase.auth.dependencies import (
    AuthenticatedActor,
    require_authenticated_actor,
    require_csrf,
    require_owner,
)
from florabase.db.session import get_database_session
from florabase.orders import reconciliation, service
from florabase.orders.purchase_schemas import (
    PurchaseApplyRequest,
    PurchasePreview,
    PurchasePreviewRequest,
    PurchaseResolution,
    PurchaseSeedLotCreate,
    PurchaseSeedPage,
)
from florabase.orders.schemas import (
    OrderCreate,
    OrderDetailResponse,
    OrderPage,
    OrderResponse,
    OrderUpdate,
)
from florabase.seed_lots.schemas import SeedLotResponse

router = APIRouter(prefix="/orders", tags=["orders"])
Database = Annotated[Session, Depends(get_database_session)]
Reader = Annotated[AuthenticatedActor, Depends(require_authenticated_actor)]
Writer = Annotated[AuthenticatedActor, Depends(require_csrf)]
Offset = Annotated[int, Query(ge=0, le=100000)]
Limit = Annotated[int, Query(ge=1, le=100)]


def _error(error: service.OrderError) -> HTTPException:
    return HTTPException(
        status_code=error.status, detail={"code": error.code, "message": error.message}
    )


@router.get("", response_model=OrderPage, operation_id="listOrders")
def list_all(
    _actor: Reader,
    database: Database,
    q: Annotated[str, Query(max_length=200)] = "",
    supplier_id: UUID | None = None,
    offset: Offset = 0,
    limit: Limit = 50,
) -> OrderPage:
    return service.list_orders(
        database, q=q.strip(), supplier_id=supplier_id, offset=offset, limit=limit
    )


@router.get("/{order_id}", response_model=OrderDetailResponse, operation_id="getOrder")
def read(
    order_id: UUID,
    _actor: Reader,
    database: Database,
    seed_lots_offset: Offset = 0,
    seed_lots_limit: Limit = 50,
) -> OrderDetailResponse:
    try:
        return service.get_detail(
            database, order_id, offset=seed_lots_offset, limit=seed_lots_limit
        )
    except service.OrderError as error:
        raise _error(error) from error


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createOrder",
)
def create(
    payload: OrderCreate, response: Response, actor: Writer, database: Database
) -> OrderResponse:
    require_owner(actor)
    try:
        order = service.create_order(database, payload)
        response.headers["Location"] = f"/api/v1/orders/{order.id}"
        return service.get_detail(database, order.id)
    except service.OrderError as error:
        raise _error(error) from error


@router.patch("/{order_id}", response_model=OrderResponse, operation_id="updateOrder")
def update(
    order_id: UUID, payload: OrderUpdate, actor: Writer, database: Database
) -> OrderResponse:
    require_owner(actor)
    try:
        order = service.update_order(database, order_id, payload)
        return service.get_detail(database, order.id)
    except service.OrderError as error:
        raise _error(error) from error


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="deleteOrder")
def delete(order_id: UUID, actor: Writer, database: Database) -> Response:
    require_owner(actor)
    try:
        service.delete_order(database, order_id)
    except service.OrderError as error:
        raise _error(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{order_id}/purchase-context/preview",
    response_model=PurchasePreview,
    operation_id="previewPurchaseContext",
)
def preview_purchase(
    order_id: UUID, payload: PurchasePreviewRequest, _actor: Reader, database: Database
) -> PurchasePreview:
    try:
        return reconciliation.preview(database, order_id, payload)
    except service.OrderError as error:
        raise _error(error) from error


@router.post(
    "/{order_id}/purchase-context/apply",
    response_model=PurchaseResolution,
    operation_id="applyPurchaseContext",
)
def apply_purchase(
    order_id: UUID, payload: PurchaseApplyRequest, actor: Writer, database: Database
) -> PurchaseResolution:
    require_owner(actor)
    try:
        return reconciliation.apply(database, order_id, payload)
    except service.OrderError as error:
        raise _error(error) from error


@router.post(
    "/{order_id}/seed-lots",
    response_model=SeedLotResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createPurchaseSeedLot",
)
def create_purchase_lot(
    order_id: UUID, payload: PurchaseSeedLotCreate, actor: Writer, database: Database
) -> SeedLotResponse:
    require_owner(actor)
    try:
        return reconciliation.create(database, order_id, payload)
    except service.OrderError as error:
        raise _error(error) from error


@router.get(
    "/{order_id}/seed-lot-choices",
    response_model=PurchaseSeedPage,
    operation_id="listPurchaseSeedChoices",
)
def purchase_choices(
    order_id: UUID,
    _actor: Reader,
    database: Database,
    q: Annotated[str, Query(max_length=200)] = "",
    offset: Offset = 0,
    limit: Limit = 50,
) -> PurchaseSeedPage:
    try:
        return reconciliation.choices(database, order_id, q.strip(), offset, limit)
    except service.OrderError as error:
        raise _error(error) from error
