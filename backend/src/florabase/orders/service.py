from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.schemas import BotanicalIdentityResponse
from florabase.orders.model import Order
from florabase.orders.schemas import (
    OrderCreate,
    OrderDetailResponse,
    OrderPage,
    OrderResponse,
    OrderUpdate,
    OrderWrite,
)
from florabase.seed_lots.model import SeedLot
from florabase.seed_lots.schemas import PartialDate, SupplierSummary
from florabase.suppliers.model import Supplier
from florabase.suppliers.schemas import SupplierBotanicalIdentitySummary, SupplierSeedLotLink


@dataclass(frozen=True)
class OrderError(Exception):
    code: str
    message: str
    status: int = 409


def get_order(database: Session, order_id: UUID, *, lock: bool = False) -> Order:
    statement = select(Order).where(Order.id == order_id)
    if lock:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    order = database.scalar(statement)
    if order is None:
        raise OrderError("order_not_found", "Order not found", 404)
    return order


def ordered_on(order: Order) -> PartialDate | None:
    if order.ordered_on_precision is None:
        return None
    return PartialDate.model_validate(
        {
            "precision": order.ordered_on_precision,
            "year": order.ordered_on_year,
            "month": order.ordered_on_month,
            "day": order.ordered_on_day,
        }
    )


def write_state(order: Order) -> OrderWrite:
    return OrderWrite(
        supplier_id=order.supplier_id,
        ordered_on=ordered_on(order),
        order_reference=order.order_reference,
        total_price=order.total_price,
        currency=order.currency,
        notes=order.notes,
    )


def _assign(order: Order, payload: OrderWrite) -> None:
    for field in ("supplier_id", "order_reference", "total_price", "currency", "notes"):
        setattr(order, field, getattr(payload, field))
    date = payload.ordered_on
    order.ordered_on_precision = date.precision.value if date else None
    order.ordered_on_year = date.year if date else None
    order.ordered_on_month = date.month if date else None
    order.ordered_on_day = date.day if date else None


def _supplier(database: Session, supplier_id: UUID | None, *, previous: UUID | None = None) -> None:
    if supplier_id is None:
        return
    supplier = database.get(Supplier, supplier_id)
    if supplier is None:
        raise OrderError("supplier_not_found", "Supplier not found", 404)
    if supplier.retired_at is not None and supplier_id != previous:
        raise OrderError("supplier_retired", "Choose an active Supplier for a new Order link")


def create_order(database: Session, payload: OrderCreate) -> Order:
    _supplier(database, payload.supplier_id)
    order = Order()
    _assign(order, payload)
    database.add(order)
    database.flush()
    return order


def update_order(database: Session, order_id: UUID, patch: OrderUpdate) -> Order:
    order = get_order(database, order_id, lock=True)
    values = write_state(order).model_dump()
    values.update(patch.model_dump(exclude_unset=True))
    try:
        payload = OrderWrite.model_validate(values)
    except ValidationError as error:
        raise OrderError("invalid_order", str(error), 422) from error
    _supplier(database, payload.supplier_id, previous=order.supplier_id)
    if payload.supplier_id is not None and database.scalar(
        select(SeedLot.id)
        .where(
            SeedLot.order_id == order.id,
            SeedLot.supplier_id.is_not(None),
            SeedLot.supplier_id != payload.supplier_id,
        )
        .limit(1)
    ):
        raise OrderError(
            "order_supplier_conflict",
            "Order Supplier conflicts with a linked SeedLot. Correct or unlink that lot first.",
        )
    _assign(order, payload)
    order.updated_at = datetime.now(UTC)
    database.flush()
    return order


def delete_order(database: Session, order_id: UUID) -> None:
    order = get_order(database, order_id, lock=True)
    if database.scalar(select(SeedLot.id).where(SeedLot.order_id == order.id).limit(1)):
        raise OrderError(
            "order_in_use",
            "This Order has linked SeedLots. Unlink them explicitly before deleting it.",
        )
    database.delete(order)
    database.flush()


def _statement() -> Select[tuple[Order, Supplier, int]]:
    count = (
        select(func.count())
        .select_from(SeedLot)
        .where(SeedLot.order_id == Order.id)
        .scalar_subquery()
    )
    return select(Order, Supplier, count).outerjoin(Supplier, Supplier.id == Order.supplier_id)


def response(order: Order, supplier: Supplier | None, count: int) -> OrderResponse:
    return OrderResponse(
        **write_state(order).model_dump(),
        id=order.id,
        supplier=SupplierSummary(id=supplier.id, name=supplier.name) if supplier else None,
        seed_lot_count=count,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


def list_orders(
    database: Session,
    *,
    q: str = "",
    supplier_id: UUID | None = None,
    offset: int = 0,
    limit: int = 50,
) -> OrderPage:
    statement = _statement()
    if q:
        statement = statement.where(
            or_(
                *(
                    column.icontains(q, autoescape=True)
                    for column in (Order.order_reference, Supplier.name, Order.notes)
                )
            )
        )
    if supplier_id is not None:
        statement = statement.where(Order.supplier_id == supplier_id)
    total = int(database.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = database.execute(
        statement.order_by(
            Order.ordered_on_year.desc().nulls_last(),
            Order.ordered_on_month.desc().nulls_last(),
            Order.ordered_on_day.desc().nulls_last(),
            Order.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    )
    return OrderPage(
        items=[response(*row) for row in rows], total=total, offset=offset, limit=limit
    )


def get_detail(
    database: Session, order_id: UUID, *, offset: int = 0, limit: int = 50
) -> OrderDetailResponse:
    get_order(database, order_id)
    row = database.execute(_statement().where(Order.id == order_id)).one()
    summary = response(*row)
    lots = database.execute(
        select(SeedLot, BotanicalIdentity)
        .join(BotanicalIdentity, BotanicalIdentity.id == SeedLot.botanical_identity_id)
        .where(SeedLot.order_id == order_id)
        .order_by(SeedLot.id)
        .offset(offset)
        .limit(limit)
    )
    return OrderDetailResponse(
        **summary.model_dump(),
        seed_lots=[
            SupplierSeedLotLink(
                id=lot.id,
                label=lot.label,
                lifecycle=lot.lifecycle,
                botanical_identity=SupplierBotanicalIdentitySummary(
                    id=identity.id,
                    display_label=BotanicalIdentityResponse.from_model(identity).display_label,
                ),
                acquisition_date=PartialDate.model_validate(
                    {
                        "precision": lot.acquisition_date_precision,
                        "year": lot.acquisition_date_year,
                        "month": lot.acquisition_date_month,
                        "day": lot.acquisition_date_day,
                    }
                )
                if lot.acquisition_date_precision
                else None,
            )
            for lot, identity in lots
        ],
        seed_lots_total=summary.seed_lot_count,
        seed_lots_offset=offset,
        seed_lots_limit=limit,
    )
