from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid7

import pytest
from alembic.config import Config
from sqlalchemy import Connection, Engine, event, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from alembic import command
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.orders import service as orders
from florabase.orders.model import Order
from florabase.orders.schemas import OrderCreate, OrderUpdate
from florabase.search.schemas import SearchKind
from florabase.search.service import SearchFilters, search
from florabase.seed_lots import service as seeds
from florabase.seed_lots.schemas import SeedLotCreate, SeedLotUpdate
from florabase.suppliers.model import Supplier

from .test_supplier_api import (
    ORIGIN,
    mutate,
    request,
)
from .test_supplier_api import (
    authenticated_browser as authenticated_browser,
)

pytestmark = pytest.mark.integration


def setup_records(db: Session) -> tuple[BotanicalIdentity, Supplier, Supplier]:
    identity = BotanicalIdentity(scientific_name=f"Orderus {uuid7().hex}")
    first = Supplier(name="Purchase Nursery %_", kind="nursery")
    other = Supplier(name="Another Nursery", kind="nursery")
    db.add_all([identity, first, other])
    db.flush()
    return identity, first, other


def test_order_domain_links_money_precision_and_retention(database_connection: Connection) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity, first, other = setup_records(db)
        order = orders.create_order(
            db,
            OrderCreate.model_validate(
                {
                    "supplier_id": first.id,
                    "ordered_on": {"precision": "month", "year": 2026, "month": 10},
                    "order_reference": "  REF-%_  ",
                    "total_price": "12.340000000000000001",
                    "currency": "EUR",
                }
            ),
        )
        assert order.id.version == 7
        db.expire(order)
        assert order.total_price == Decimal("12.340000000000000001")
        payload = {
            "botanical_identity_id": identity.id,
            "supplier_id": first.id,
            "order_id": order.id,
            "source_kind": "purchased",
        }
        lot_a = seeds.create_seed_lot(db, SeedLotCreate.model_validate(payload))
        lot_b = seeds.create_seed_lot(
            db, SeedLotCreate.model_validate({**payload, "source_kind": "purchased_fruit"})
        )
        assert lot_a.id != lot_b.id
        assert lot_a.location_id is None
        assert lot_a.provenance_site_id is None
        assert lot_a.acquisition_date_year is None
        detail = orders.get_detail(db, order.id, limit=1)
        assert detail.seed_lot_count == detail.seed_lots_total == 2
        assert len(detail.seed_lots) == 1
        assert (
            orders.get_detail(db, order.id, offset=1, limit=1).seed_lots[0].id
            != detail.seed_lots[0].id
        )
        for change in ({"source_kind": "gift_exchange"}, {"supplier_id": other.id}):
            with pytest.raises(seeds.SeedLotDomainConflictError):
                seeds.update_seed_lot(
                    db, lot_a, SeedLotUpdate.model_validate({**payload, **change})
                )
        with pytest.raises(orders.OrderError, match="conflicts"):
            orders.update_order(db, order.id, OrderUpdate(supplier_id=other.id))
        with pytest.raises(orders.OrderError, match="linked SeedLots"):
            orders.delete_order(db, order.id)
        first.retired_at = datetime.now(UTC)
        db.flush()
        orders.update_order(db, order.id, OrderUpdate(notes="Retained historical source"))
        assert orders.get_detail(db, order.id).supplier is not None
        assert orders.list_orders(db, q="%_").total == 1
        assert orders.list_orders(db, q="purchase nursery").total == 1
        assert orders.list_orders(db, supplier_id=other.id).total == 0
        seeds.update_seed_lot(
            db, lot_a, SeedLotUpdate.model_validate({**payload, "order_id": None})
        )
        assert lot_a.order_id is None
        seeds.update_seed_lot(db, lot_a, SeedLotUpdate.model_validate(payload))
        orders.update_order(db, order.id, OrderUpdate(supplier_id=None))
        seeds.update_seed_lot(
            db, lot_a, SeedLotUpdate.model_validate({**payload, "supplier_id": other.id})
        )
        assert lot_a.supplier_id == other.id
        seeds.update_seed_lot(
            db, lot_a, SeedLotUpdate.model_validate({**payload, "order_id": None})
        )
        seeds.update_seed_lot(
            db, lot_b, SeedLotUpdate.model_validate({**payload, "order_id": None})
        )
        orders.delete_order(db, order.id)
        assert db.get(Order, order.id) is None


@pytest.mark.parametrize(
    "kind", ["gift_exchange", "self_collected", "collection_produced", "other", "unknown"]
)
def test_incompatible_purchase_source(database_connection: Connection, kind: str) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity, _, _ = setup_records(db)
        order = orders.create_order(db, OrderCreate())
        with pytest.raises(seeds.SeedLotDomainConflictError, match="purchased"):
            seeds.create_seed_lot(
                db,
                SeedLotCreate.model_validate(
                    {
                        "botanical_identity_id": identity.id,
                        "source_kind": kind,
                        "order_id": order.id,
                    }
                ),
            )
        unlinked = seeds.create_seed_lot(db, SeedLotCreate(botanical_identity_id=identity.id))
        assert unlinked.order_id is None


@pytest.mark.parametrize(
    "values",
    [
        {"total_price": "NaN", "currency": "EUR"},
        {"total_price": "Infinity", "currency": "EUR"},
        {"total_price": "-1", "currency": "EUR"},
        {"total_price": "1", "currency": None},
        {"currency": "EUR"},
        {"total_price": "1", "currency": "eur"},
        {"supplier_id": uuid7()},
        {"ordered_on_precision": "month", "ordered_on_year": 2026},
        {
            "ordered_on_precision": "day",
            "ordered_on_year": 2026,
            "ordered_on_month": 2,
            "ordered_on_day": 30,
        },
        {"ordered_on_year": 2026},
    ],
)
def test_database_order_constraints(
    database_connection: Connection, values: dict[str, object]
) -> None:
    row = {
        "id": uuid7(),
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        **values,
    }
    with pytest.raises(DBAPIError), database_connection.begin_nested():
        database_connection.execute(
            text(
                f"INSERT INTO orders ({', '.join(row)}) "
                f"VALUES ({', '.join(':' + key for key in row)})"
            ),
            row,
        )


def test_seed_order_fk_source_and_supplier_retention(database_connection: Connection) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity, supplier, _ = setup_records(db)
        order = orders.create_order(db, OrderCreate(supplier_id=supplier.id))
        lot = seeds.create_seed_lot(
            db,
            SeedLotCreate(
                botanical_identity_id=identity.id, source_kind="purchased", order_id=order.id
            ),
        )
        for sql, params in [
            ("DELETE FROM orders WHERE id=:id", {"id": order.id}),
            ("DELETE FROM suppliers WHERE id=:id", {"id": supplier.id}),
            ("UPDATE seed_lots SET order_id=:id WHERE id=:lot", {"id": uuid7(), "lot": lot.id}),
            ("UPDATE seed_lots SET source_kind='unknown' WHERE id=:id", {"id": lot.id}),
        ]:
            with pytest.raises(DBAPIError), database_connection.begin_nested():
                database_connection.execute(text(sql), params)


def test_authenticated_order_api_and_saved_views(authenticated_browser: tuple[str, str]) -> None:
    assert request("GET", "/api/v1/orders")[0] == 401
    status, headers, created = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/orders",
        {
            "order_reference": "ABC",
            "total_price": "0.00",
            "currency": "EUR",
            "ordered_on": {"precision": "year", "year": 2026},
        },
    )
    assert status == 201
    assert UUID(created["id"]).version == 7
    path = headers["location"]
    cookie, _ = authenticated_browser
    assert (
        request("PATCH", path, body={"notes": "bad"}, headers={"cookie": cookie, "origin": ORIGIN})[
            0
        ]
        == 403
    )
    assert (
        request(
            "DELETE",
            path,
            headers={
                "cookie": cookie,
                "origin": "https://evil.example",
                "x-csrf-token": authenticated_browser[1],
            },
        )[0]
        == 403
    )
    assert request("GET", path, headers={"cookie": cookie})[2]["total_price"] == "0.00"
    assert (
        mutate(authenticated_browser, "PATCH", path, {"notes": "Updated"})[2]["order_reference"]
        == "ABC"
    )
    assert mutate(authenticated_browser, "PATCH", path, {"currency": None})[0] == 422
    assert mutate(authenticated_browser, "POST", "/api/v1/orders", {"currency": "EUR"})[0] == 422
    status, _, view = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/saved-views",
        {"name": "Purchases", "surface": "orders", "state_version": 1, "state": {"q": " ABC "}},
    )
    assert status == 201
    assert view["state"] == {"q": "ABC"}
    view_path = f"/api/v1/saved-views/{view['id']}"
    assert mutate(authenticated_browser, "PATCH", view_path, {"name": "Renamed"})[0] == 200
    assert (
        mutate(
            authenticated_browser,
            "PATCH",
            view_path,
            {"state_version": 1, "state": {"q": "Updated"}},
        )[0]
        == 200
    )
    assert mutate(authenticated_browser, "DELETE", view_path)[0] == 204
    assert mutate(authenticated_browser, "DELETE", path)[0] == 204
    assert request("GET", path, headers={"cookie": cookie})[0] == 404


def test_order_search_is_direct_literal_bounded_and_deterministic(
    database_connection: Connection,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity, supplier, _ = setup_records(db)
        first = orders.create_order(
            db,
            OrderCreate(
                supplier_id=supplier.id,
                order_reference="REF%_",
                total_price="20.00",
                currency="USD",
            ),
        )
        second = orders.create_order(
            db, OrderCreate(supplier_id=supplier.id, order_reference="REF%_")
        )
        for _ in range(3):
            seeds.create_seed_lot(
                db,
                SeedLotCreate(
                    botanical_identity_id=identity.id, source_kind="purchased", order_id=first.id
                ),
            )
        db.flush()
        statements: list[str] = []

        def capture(
            _connection: object,
            _cursor: object,
            statement: str,
            _parameters: object,
            _context: object,
            _many: object,
        ) -> None:
            statements.append(statement)

        event.listen(database_connection, "before_cursor_execute", capture)
        try:
            result = search(db, "rEf%_", SearchFilters(kinds=(SearchKind.ORDER,)), limit=1)
            assert len(statements) == 4  # two shared paths + count/page for Orders
        finally:
            event.remove(database_connection, "before_cursor_execute", capture)
        assert result.total == 2
        assert result.groups[0].items[0].href == f"#/orders/{min(first.id, second.id)}"
        page2 = search(db, "REF%_", SearchFilters(kinds=(SearchKind.ORDER,)), offset=1, limit=1)
        assert page2.groups[0].items[0].id != result.groups[0].items[0].id
        assert search(db, "purchase nursery", SearchFilters(kinds=(SearchKind.ORDER,))).total == 2
        assert (
            search(db, identity.scientific_name, SearchFilters(kinds=(SearchKind.ORDER,))).total
            == 0
        )
        assert (
            search(db, "REF%_", SearchFilters(kinds=(SearchKind.ORDER, SearchKind.SUPPLIER))).total
            == 2
        )
        assert (
            search(
                db, "REF%_", SearchFilters(kinds=(SearchKind.ORDER,), identity_id=identity.id)
            ).total
            == 0
        )


def test_order_migration_preserves_data_and_refuses_populated_downgrade(
    database_engine: Engine,
) -> None:
    config = Config("alembic.ini")
    identity, lot, order = uuid7(), uuid7(), uuid7()
    command.downgrade(config, "20261007_0035")
    try:
        with database_engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO botanical_identities (id, scientific_name, created_at, "
                    "updated_at) VALUES (:id, 'Migration Orderus', now(), now())"
                ),
                {"id": identity},
            )
            connection.execute(
                text(
                    "INSERT INTO seed_lots (id, botanical_identity_id, created_at, "
                    "updated_at) VALUES (:id, :identity, now(), now())"
                ),
                {"id": lot, "identity": identity},
            )
        command.upgrade(config, "head")
        with database_engine.begin() as connection:
            assert (
                connection.scalar(
                    text("SELECT id FROM seed_lots WHERE id=:id AND order_id IS NULL"), {"id": lot}
                )
                == lot
            )
            connection.execute(
                text(
                    "INSERT INTO orders (id, total_price, currency, created_at, updated_at) "
                    "VALUES (:id, 12.3400, 'EUR', now(), now())"
                ),
                {"id": order},
            )
        with pytest.raises(RuntimeError, match="Orders or Order Saved Views"):
            command.downgrade(config, "20261007_0035")
        with database_engine.begin() as connection:
            assert connection.scalar(
                text("SELECT total_price FROM orders WHERE id=:id"), {"id": order}
            ) == Decimal("12.3400")
            connection.execute(text("DELETE FROM orders WHERE id=:id"), {"id": order})
        command.downgrade(config, "20261007_0035")
        command.upgrade(config, "head")
        with database_engine.connect() as connection:
            assert (
                connection.scalar(text("SELECT id FROM seed_lots WHERE id=:id"), {"id": lot}) == lot
            )
    finally:
        command.upgrade(config, "head")
        with database_engine.begin() as connection:
            connection.execute(text("DELETE FROM orders WHERE id=:id"), {"id": order})
            connection.execute(text("DELETE FROM seed_lots WHERE id=:id"), {"id": lot})
            connection.execute(
                text("DELETE FROM botanical_identities WHERE id=:id"), {"id": identity}
            )


def test_order_saved_view_blocks_downgrade_without_orders(database_engine: Engine) -> None:
    config = Config("alembic.ini")
    owner, view = uuid7(), uuid7()
    with database_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (id, login_name, password_hash, enabled, owner, "
                "password_changed_at, created_at, updated_at) "
                "VALUES (:id, :login, 'unused', true, true, now(), now(), now())"
            ),
            {"id": owner, "login": str(owner)},
        )
        connection.execute(
            text(
                "INSERT INTO saved_views (id, owner_id, name, surface, state_version, "
                "state, created_at, updated_at) VALUES (:id, :owner, 'Orders', 'orders', "
                '1, \'{"q": "purchase"}\', now(), now())'
            ),
            {"id": view, "owner": owner},
        )
    try:
        with pytest.raises(RuntimeError, match="Order Saved Views exist"):
            command.downgrade(config, "20261007_0035")
        with database_engine.begin() as connection:
            assert (
                connection.scalar(
                    text("SELECT count(*) FROM saved_views WHERE id=:id"), {"id": view}
                )
                == 1
            )
            connection.execute(text("DELETE FROM saved_views WHERE id=:id"), {"id": view})
        command.downgrade(config, "20261007_0035")
        command.upgrade(config, "head")
    finally:
        command.upgrade(config, "head")
        with database_engine.begin() as connection:
            connection.execute(text("DELETE FROM saved_views WHERE id=:id"), {"id": view})
            connection.execute(text("DELETE FROM users WHERE id=:id"), {"id": owner})
