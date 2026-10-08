from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid7

import pytest
from pydantic import JsonValue, ValidationError

from florabase.orders.model import Order
from florabase.orders.schemas import OrderCreate, OrderUpdate, OrderWrite
from florabase.orders.service import (
    OrderError,
    create_order,
    delete_order,
    get_order,
    update_order,
    write_state,
)
from florabase.saved_views.state import SavedViewSurface, canonical_state
from florabase.seed_lots.schemas import PartialDate
from florabase.suppliers.model import Supplier


def test_minimal_and_normalized_order() -> None:
    assert OrderCreate().model_dump() == dict.fromkeys(
        ["supplier_id", "ordered_on", "order_reference", "total_price", "currency", "notes"]
    )
    payload = OrderCreate(
        order_reference="  Réf #123  ",
        total_price="0.0000",
        currency="EUR",
        notes="\r\nKnown total\r\nIncludes shipping \r\n",
    )
    assert payload.order_reference == "Réf #123"
    assert payload.notes == "Known total\nIncludes shipping"
    assert payload.model_dump(mode="json")["total_price"] == "0.0000"
    assert OrderCreate(order_reference="  ", notes="  ").order_reference is None


@pytest.mark.parametrize(
    "date",
    [
        {"precision": "year", "year": 2026},
        {"precision": "month", "year": 2026, "month": 10},
        {"precision": "day", "year": 2024, "month": 2, "day": 29},
    ],
)
def test_date_precision(date: dict[str, object]) -> None:
    payload = OrderCreate.model_validate({"ordered_on": date})
    assert payload.ordered_on == PartialDate.model_validate(date)


@pytest.mark.parametrize(
    "values",
    [
        {"total_price": "10"},
        {"currency": "EUR"},
        {"total_price": "-1", "currency": "EUR"},
        {"total_price": "NaN", "currency": "EUR"},
        {"total_price": "Infinity", "currency": "EUR"},
        {"total_price": 10.2, "currency": "EUR"},
        {"total_price": 10, "currency": "EUR"},
        {"total_price": "1e3", "currency": "EUR"},
        {"total_price": "1", "currency": "eur"},
        {"total_price": "1", "currency": "EURO"},
        {"total_price": "1", "currency": "12X"},
        {"total_price": "1" * 25, "currency": "EUR"},
        {"order_reference": "bad\x00ref"},
        {"order_reference": "x" * 256},
        {"notes": "x" * 20001},
        {"notes": "bad\x07note"},
        {"ordered_on": {"precision": "day", "year": 2026, "month": 2, "day": 30}},
        {"ordered_on": {"precision": "year", "year": 2026, "month": 1}},
        {"payment_method": "card"},
    ],
)
def test_invalid_order(values: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        OrderCreate.model_validate(values)


def model() -> Order:
    now = datetime.now(UTC)
    return Order(
        id=uuid7(),
        supplier_id=None,
        order_reference="A",
        total_price=Decimal("12.3450"),
        currency="EUR",
        notes="Known",
        created_at=now,
        updated_at=now,
    )


def test_patch_validates_merged_state_and_preserves_unknowns() -> None:
    order = model()
    database = MagicMock()
    database.scalar.return_value = order
    result = update_order(database, order.id, OrderUpdate(notes=" new "))
    assert result.notes == "new"
    assert result.order_reference == "A"
    assert write_state(result).total_price == Decimal("12.3450")
    assert result.ordered_on_precision is None
    with pytest.raises(OrderError, match="Total price and currency"):
        update_order(database, order.id, OrderUpdate(total_price=None))
    update_order(
        database, order.id, OrderUpdate(total_price=None, currency=None, order_reference=None)
    )
    assert order.total_price is None
    assert order.currency is None
    assert order.order_reference is None


def test_order_errors_and_safe_delete() -> None:
    database = MagicMock()
    database.scalar.return_value = None
    database.get.return_value = None
    with pytest.raises(OrderError, match="Order not found"):
        get_order(database, uuid7())
    with pytest.raises(OrderError, match="Supplier not found"):
        create_order(database, OrderCreate(supplier_id=uuid7()))
    retired = Supplier(id=uuid7(), name="Retired", kind="seller", retired_at=datetime.now(UTC))
    database.get.return_value = retired
    with pytest.raises(OrderError, match="active Supplier"):
        create_order(database, OrderCreate(supplier_id=retired.id))
    order = model()
    database.scalar.side_effect = [order, uuid7()]
    with pytest.raises(OrderError, match="linked SeedLots"):
        delete_order(database, order.id)
    database.scalar.side_effect = [order, None]
    delete_order(database, order.id)
    database.delete.assert_called_once_with(order)


def test_order_saved_view_state() -> None:
    supplier = uuid7()
    assert canonical_state(
        SavedViewSurface.ORDERS, 1, {"q": "  nursery ", "supplier_id": str(supplier).upper()}
    ) == {"q": "nursery", "supplier_id": str(supplier)}
    invalid_states: list[dict[str, JsonValue]] = [
        {},
        {"offset": 50},
        {"selected_order": str(supplier)},
        {"supplier_id": "bad"},
    ]
    for state in invalid_states:
        with pytest.raises(ValueError, match=r"Choose a search|validation error"):
            canonical_state(SavedViewSurface.ORDERS, 1, state)
    with pytest.raises(ValueError, match="version"):
        canonical_state(SavedViewSurface.ORDERS, 2, {"q": "x"})


def test_decimal_objects_must_be_finite() -> None:
    with pytest.raises(ValidationError):
        OrderWrite(total_price=Decimal("Infinity"), currency="EUR")


def test_order_projection_is_bounded_and_preserves_date_and_lot_identity() -> None:
    from florabase.botanical_identities.model import BotanicalIdentity
    from florabase.orders.service import get_detail, list_orders, response
    from florabase.seed_lots.model import SeedLot

    order = model()
    order.ordered_on_precision, order.ordered_on_year, order.ordered_on_month = "month", 2026, 10
    supplier = Supplier(id=uuid7(), name="Nursery", kind="nursery")
    order.supplier_id = supplier.id
    summary = response(order, supplier, 2)
    assert summary.ordered_on == PartialDate(precision="month", year=2026, month=10)
    assert summary.model_dump(mode="json")["total_price"] == "12.3450"
    database = MagicMock()
    database.scalar.return_value = 2
    database.execute.return_value = [(order, supplier, 2)]
    page = list_orders(database, q="%_", supplier_id=supplier.id, offset=10, limit=1)
    assert page.total == 2
    assert page.offset == 10
    assert page.limit == 1
    assert page.items[0].seed_lot_count == 2
    assert list_orders(database).total == 2
    database.scalar.return_value = 0
    database.execute.return_value = []
    assert list_orders(database).items == []

    now = datetime.now(UTC)
    identity = BotanicalIdentity(
        id=uuid7(), scientific_name="Ocimum basilicum", created_at=now, updated_at=now
    )
    a = SeedLot(
        id=uuid7(),
        label="Packet A",
        lifecycle="active",
        acquisition_date_precision="year",
        acquisition_date_year=2025,
    )
    b = SeedLot(id=uuid7(), label="Packet B", lifecycle="exhausted")
    database.scalar.return_value = order
    first = MagicMock()
    first.one.return_value = (order, supplier, 2)
    database.execute.side_effect = [first, [(a, identity), (b, identity)]]
    detail = get_detail(database, order.id)
    assert [lot.id for lot in detail.seed_lots] == [a.id, b.id]
    assert detail.seed_lots[0].acquisition_date == PartialDate(precision="year", year=2025)
    assert detail.seed_lots[1].acquisition_date is None
    assert detail.seed_lots_total == 2


def test_create_and_supplier_change_domain_rules() -> None:
    database = MagicMock()
    supplier = Supplier(id=uuid7(), name="Active", kind="seller")
    database.get.return_value = supplier
    created = create_order(
        database,
        OrderCreate(supplier_id=supplier.id, ordered_on=PartialDate(precision="year", year=2026)),
    )
    assert created.supplier_id == supplier.id
    assert created.ordered_on_year == 2026
    database.add.assert_called_once_with(created)
    created.id = uuid7()
    created.created_at = datetime.now(UTC)
    created.updated_at = datetime.now(UTC)
    created.total_price = None
    database.scalar.side_effect = [created, uuid7()]
    with pytest.raises(OrderError, match="conflicts with a linked SeedLot"):
        update_order(database, created.id, OrderUpdate(supplier_id=supplier.id))
    supplier.retired_at = datetime.now(UTC)
    database.scalar.side_effect = [created, None]
    update_order(database, created.id, OrderUpdate(notes=" Historical link retained "))
    assert created.notes == "Historical link retained"
    assert created.supplier_id == supplier.id


def test_order_api_routes_and_typed_domain_errors() -> None:
    from collections.abc import Callable
    from typing import cast
    from unittest.mock import patch

    from fastapi import HTTPException, Response

    from florabase.auth.dependencies import AuthenticatedActor
    from florabase.orders import api
    from florabase.orders import service as order_service
    from florabase.orders.schemas import OrderDetailResponse, OrderPage

    order = model()
    detail = OrderDetailResponse(
        **write_state(order).model_dump(),
        id=order.id,
        supplier=None,
        seed_lot_count=0,
        created_at=order.created_at,
        updated_at=order.updated_at,
        seed_lots=[],
        seed_lots_total=0,
        seed_lots_offset=0,
        seed_lots_limit=50,
    )
    database = MagicMock()
    actor = cast(AuthenticatedActor, MagicMock())
    page = OrderPage(items=[detail], total=1, offset=0, limit=50)
    with (
        patch.object(api, "require_owner"),
        patch.object(order_service, "list_orders", return_value=page),
        patch.object(order_service, "get_detail", return_value=detail),
        patch.object(order_service, "create_order", return_value=order),
        patch.object(order_service, "update_order", return_value=order),
        patch.object(order_service, "delete_order"),
    ):
        assert api.list_all(actor, database) is page
        assert api.read(order.id, actor, database) is detail
        response = Response()
        assert api.create(OrderCreate(), response, actor, database) is detail
        assert response.headers["Location"].endswith(str(order.id))
        assert api.update(order.id, OrderUpdate(), actor, database) is detail
        assert api.delete(order.id, actor, database).status_code == 204
    actions: list[tuple[str, Callable[[], object]]] = [
        ("get_detail", lambda: api.read(order.id, actor, database)),
        ("create_order", lambda: api.create(OrderCreate(), Response(), actor, database)),
        ("update_order", lambda: api.update(order.id, OrderUpdate(), actor, database)),
        ("delete_order", lambda: api.delete(order.id, actor, database)),
    ]
    for target, action in actions:
        with (
            patch.object(api, "require_owner"),
            patch.object(
                order_service, target, side_effect=OrderError("order_in_use", "Referenced", 409)
            ),
            pytest.raises(HTTPException) as raised,
        ):
            action()
        assert raised.value.status_code == 409
        assert cast(object, raised.value.detail) == {
            "code": "order_in_use",
            "message": "Referenced",
        }
