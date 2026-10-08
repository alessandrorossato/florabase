"""The same purchase reconciliation contract serves both link directions and creation."""

from datetime import timedelta

import pytest
from sqlalchemy import Connection, func, select
from sqlalchemy.orm import Session

from florabase.orders import reconciliation as purchase
from florabase.orders import service as orders
from florabase.orders.purchase_schemas import (
    AcquisitionContext,
    PurchaseApplyRequest,
    PurchasePreview,
    PurchasePreviewRequest,
    PurchaseSeedLotCreate,
)
from florabase.orders.schemas import OrderCreate, OrderUpdate
from florabase.seed_lots import service as seeds
from florabase.seed_lots.model import SeedLot
from florabase.seed_lots.schemas import PartialDate, SeedLotCreate, SeedLotUpdate

from .test_orders import setup_records
from .test_supplier_api import ORIGIN, mutate, request
from .test_supplier_api import authenticated_browser as authenticated_browser

pytestmark = pytest.mark.integration
MONTH = PartialDate(precision="month", year=2026, month=10)
YEAR = PartialDate(precision="year", year=2025)


def confirmation(review: PurchasePreview, **choices: bool) -> PurchaseApplyRequest:
    return PurchaseApplyRequest(
        seed_lot_id=review.seed_lot_id,
        expected_seed_lot_updated_at=review.seed_lot_updated_at,
        expected_order_updated_at=review.order.updated_at,
        context=review.current,
        **choices,
    )


@pytest.mark.parametrize("source", ["unknown", "purchased", "purchased_fruit"])
@pytest.mark.parametrize("direction", ["seed_draft", "order_existing"])
def test_both_link_directions_preserve_material_and_partial_dates(
    database_connection: Connection, source: str, direction: str
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity, supplier, _ = setup_records(db)
        order = orders.create_order(
            db,
            OrderCreate(
                supplier_id=supplier.id, ordered_on=MONTH, total_price="32.5000", currency="EUR"
            ),
        )
        lot = seeds.create_seed_lot(
            db,
            SeedLotCreate.model_validate(
                {
                    "botanical_identity_id": identity.id,
                    "source_kind": source,
                    "label": "Physical packet",
                    "notes": "Keep this draft-independent knowledge",
                    "harvest_date": YEAR.model_dump(),
                    "quantity": {"kind": "seed_count", "value": "17", "is_approximate": False},
                }
            ),
        )
        before = purchase._response(db, lot).model_dump(
            exclude={
                "updated_at",
                "source_kind",
                "supplier",
                "supplier_id",
                "order_id",
                "order",
                "acquisition_date",
            }
        )
        context = purchase.lot_context(lot) if direction == "seed_draft" else None
        review = purchase.preview(
            db,
            order.id,
            PurchasePreviewRequest(
                seed_lot_id=lot.id,
                context=context,
                expected_seed_lot_updated_at=lot.updated_at if context else None,
            ),
        )
        assert lot.order_id is None
        assert lot.source_kind == source
        assert lot.supplier_id is None
        assert review.supplier_action == "fill"
        assert review.date_action == "copy"
        assert review.order.total_price == order.total_price
        result = purchase.apply(
            db, order.id, confirmation(review, use_order_supplier=True, use_order_date=True)
        )
        assert result.seed_lot is not None
        assert result.seed_lot.source_kind == ("purchased" if source == "unknown" else source)
        assert result.seed_lot.supplier_id == supplier.id
        assert result.seed_lot.acquisition_date == MONTH
        assert result.seed_lot.order_id == order.id
        assert (
            result.seed_lot.model_dump(
                exclude={
                    "updated_at",
                    "source_kind",
                    "supplier",
                    "supplier_id",
                    "order_id",
                    "order",
                    "acquisition_date",
                }
            )
            == before
        )
        assert "total_price" not in result.seed_lot.model_dump()
        # Unlink retains every confirmed acquisition value.
        values = {
            key: value
            for key, value in result.seed_lot.model_dump().items()
            if key in SeedLotUpdate.model_fields
        }
        seeds.update_seed_lot(db, lot, SeedLotUpdate.model_validate({**values, "order_id": None}))
        assert purchase.lot_context(lot) == result.context.model_copy(update={"order_id": None})


@pytest.mark.parametrize("supplier_case", ["blank", "matching", "conflict", "order_unknown"])
@pytest.mark.parametrize("date_case", ["unknown", "matching", "different"])
def test_supplier_confirmation_and_date_preservation(
    database_connection: Connection, supplier_case: str, date_case: str
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity, supplier, other = setup_records(db)
        order = orders.create_order(
            db,
            OrderCreate(
                supplier_id=None if supplier_case == "order_unknown" else supplier.id,
                ordered_on=MONTH,
            ),
        )
        lot = seeds.create_seed_lot(
            db,
            SeedLotCreate(
                botanical_identity_id=identity.id,
                source_kind="purchased_fruit",
                supplier_id=None
                if supplier_case == "blank"
                else supplier.id
                if supplier_case == "matching"
                else other.id,
                acquisition_date=None
                if date_case == "unknown"
                else MONTH
                if date_case == "matching"
                else YEAR,
            ),
        )
        initial = purchase.lot_context(lot)
        review = purchase.preview(db, order.id, PurchasePreviewRequest(seed_lot_id=lot.id))
        assert (
            review.supplier_action
            == {
                "blank": "fill",
                "matching": "keep",
                "conflict": "replace",
                "order_unknown": "keep",
            }[supplier_case]
        )
        assert (
            review.date_action
            == {"unknown": "copy", "matching": "keep", "different": "replace"}[date_case]
        )
        if supplier_case == "conflict":
            with pytest.raises(orders.OrderError, match="Confirm"):
                purchase.apply(db, order.id, confirmation(review))
            assert purchase.lot_context(lot) == initial
        result = purchase.apply(
            db,
            order.id,
            confirmation(review, use_order_supplier=supplier_case in ("blank", "conflict")),
        )
        assert result.context.acquisition_date == initial.acquisition_date
        assert result.context.supplier_id == (
            supplier.id if supplier_case in ("blank", "conflict", "matching") else other.id
        )
        assert result.context.source_kind == "purchased_fruit"
        if supplier_case != "order_unknown":
            with pytest.raises(orders.OrderError, match="conflicts"):
                orders.update_order(db, order.id, OrderUpdate(supplier_id=other.id))
            assert order.supplier_id == supplier.id


@pytest.mark.parametrize(
    "source", ["gift_exchange", "self_collected", "other", "collection_produced"]
)
def test_incompatible_sources_are_never_silently_converted(
    database_connection: Connection, source: str
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity, _, _ = setup_records(db)
        order = orders.create_order(db, OrderCreate())
        lot = seeds.create_seed_lot(
            db,
            SeedLotCreate.model_validate(
                {
                    "botanical_identity_id": identity.id,
                    "source_kind": source,
                    "source_detail": "Explicit context" if source == "other" else None,
                }
            ),
        )
        review = purchase.preview(db, order.id, PurchasePreviewRequest(seed_lot_id=lot.id))
        assert not review.can_apply
        assert review.conflict
        with pytest.raises(orders.OrderError, match="Correct its source"):
            purchase.apply(db, order.id, confirmation(review))
        assert lot.order_id is None
        assert lot.source_kind == source
        assert lot.id not in {
            choice.id for choice in purchase.choices(db, order.id, "", 0, 50).items
        }


@pytest.mark.parametrize("changed", ["seed", "order"])
def test_stale_apply_refuses_every_mutation(database_connection: Connection, changed: str) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity, supplier, _ = setup_records(db)
        order = orders.create_order(db, OrderCreate(supplier_id=supplier.id, ordered_on=MONTH))
        lot = seeds.create_seed_lot(db, SeedLotCreate(botanical_identity_id=identity.id))
        review = purchase.preview(db, order.id, PurchasePreviewRequest(seed_lot_id=lot.id))
        if changed == "seed":
            lot.source_kind = "purchased_fruit"
            lot.updated_at += timedelta(seconds=1)
            db.flush()
        else:
            orders.update_order(db, order.id, OrderUpdate(notes="Changed after preview"))
        current = purchase.lot_context(lot)
        with pytest.raises(orders.OrderError, match="Nothing applied"):
            purchase.apply(
                db, order.id, confirmation(review, use_order_supplier=True, use_order_date=True)
            )
        assert purchase.lot_context(lot) == current
        assert lot.order_id is None
        if changed == "seed":
            with pytest.raises(orders.OrderError, match="Seed lot changed"):
                purchase.preview(
                    db,
                    order.id,
                    PurchasePreviewRequest(
                        seed_lot_id=lot.id,
                        context=review.current,
                        expected_seed_lot_updated_at=review.seed_lot_updated_at,
                    ),
                )


def test_new_lot_prefill_creation_revalidation_and_bounded_choices(
    database_connection: Connection,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity, supplier, _ = setup_records(db)
        order = orders.create_order(db, OrderCreate(supplier_id=supplier.id, ordered_on=MONTH))
        review = purchase.preview(db, order.id, PurchasePreviewRequest())
        approved = confirmation(review, use_order_supplier=True)
        count = db.scalar(select(func.count()).select_from(SeedLot))
        result = purchase.apply(db, order.id, approved)
        assert db.scalar(select(func.count()).select_from(SeedLot)) == count
        assert result.context == AcquisitionContext(
            source_kind="purchased", supplier_id=supplier.id, order_id=order.id
        )
        assert result.seed_lot is None
        assert review.date_action == "copy"
        draft = SeedLotCreate(
            botanical_identity_id=identity.id, label="Packet %_", **result.context.model_dump()
        )
        with pytest.raises(orders.OrderError, match="fields changed"):
            purchase.create(
                db,
                order.id,
                PurchaseSeedLotCreate(
                    seed_lot=draft.model_copy(update={"acquisition_date": YEAR}),
                    confirmation=approved,
                ),
            )
        first = purchase.create(
            db, order.id, PurchaseSeedLotCreate(seed_lot=draft, confirmation=approved)
        )
        second = purchase.create(
            db, order.id, PurchaseSeedLotCreate(seed_lot=draft, confirmation=approved)
        )
        assert first.id != second.id
        for lot in (first, second):
            assert lot.location_id is None
            assert lot.provenance_site_id is None
            assert lot.quantity is None
            assert lot.harvest_date is None
            assert lot.acquisition_date is None
            assert lot.botanical_identity_id == identity.id
        assert orders.get_detail(db, order.id).seed_lot_count == 2
        choices = purchase.choices(db, order.id, "%_", 0, 1)
        assert choices.total == 2
        assert len(choices.items) == 1
        assert purchase.choices(db, order.id, "%_", 1, 1).items[0].id != choices.items[0].id
        orders.update_order(db, order.id, OrderUpdate(notes="Changed before creation"))
        with pytest.raises(orders.OrderError, match="Nothing applied"):
            purchase.create(
                db, order.id, PurchaseSeedLotCreate(seed_lot=draft, confirmation=approved)
            )
        assert orders.get_detail(db, order.id).seed_lot_count == 2


def test_reconciliation_api_requires_auth_csrf_and_returns_typed_conflict(
    authenticated_browser: tuple[str, str],
) -> None:
    status, _, order = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/orders",
        {"ordered_on": MONTH.model_dump(mode="json")},
    )
    assert status == 201
    path = f"/api/v1/orders/{order['id']}"
    assert request("POST", path + "/purchase-context/preview", body={})[0] == 401
    cookie, _ = authenticated_browser
    status, _, review = request(
        "POST", path + "/purchase-context/preview", body={}, headers={"cookie": cookie}
    )
    assert status == 200
    assert review["proposed_source"] == "purchased"
    payload = {"context": review["current"], "expected_order_updated_at": order["updated_at"]}
    assert (
        request(
            "POST",
            path + "/purchase-context/apply",
            body=payload,
            headers={"cookie": cookie, "origin": ORIGIN},
        )[0]
        == 403
    )
    assert (
        mutate(authenticated_browser, "POST", path + "/purchase-context/apply", payload)[0] == 200
    )
    mutate(authenticated_browser, "PATCH", path, {"notes": "New version"})
    status, _, failure = mutate(
        authenticated_browser, "POST", path + "/purchase-context/apply", payload
    )
    assert status == 409
    assert failure["detail"]["code"] == "stale_purchase_context"
    assert request("GET", path + "/seed-lot-choices", headers={"cookie": cookie})[2]["items"] == []
    assert mutate(authenticated_browser, "DELETE", path)[0] == 204


def test_unsaved_supplier_clear_or_replacement_cannot_hide_known_conflict(
    database_connection: Connection,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity, supplier, other = setup_records(db)
        order = orders.create_order(db, OrderCreate(supplier_id=supplier.id))
        lot = seeds.create_seed_lot(
            db, SeedLotCreate(botanical_identity_id=identity.id, supplier_id=other.id)
        )
        for draft_supplier in (None, supplier.id):
            draft = purchase.lot_context(lot).model_copy(update={"supplier_id": draft_supplier})
            review = purchase.preview(
                db,
                order.id,
                PurchasePreviewRequest(
                    seed_lot_id=lot.id, context=draft, expected_seed_lot_updated_at=lot.updated_at
                ),
            )
            assert review.stored is not None
            assert review.stored.supplier_id == other.id
            assert review.supplier_action == "replace"
            with pytest.raises(orders.OrderError, match="Confirm"):
                purchase.apply(db, order.id, confirmation(review))
            assert lot.supplier_id == other.id
            assert lot.order_id is None
        unknown = orders.create_order(db, OrderCreate())
        review = purchase.preview(
            db,
            unknown.id,
            PurchasePreviewRequest(
                seed_lot_id=lot.id,
                context=draft.model_copy(update={"supplier_id": None}),
                expected_seed_lot_updated_at=lot.updated_at,
            ),
        )
        result = purchase.apply(db, unknown.id, confirmation(review))
        assert result.context.supplier_id == other.id
