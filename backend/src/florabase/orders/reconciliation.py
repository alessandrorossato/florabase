"""One reviewed acquisition-context contract for both purchase-link directions."""

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.lineage.service import lock_lineage_writes
from florabase.orders.purchase_schemas import (
    AcquisitionContext,
    PurchaseApplyRequest,
    PurchasePreview,
    PurchasePreviewRequest,
    PurchaseResolution,
    PurchaseSeedChoice,
    PurchaseSeedLotCreate,
    PurchaseSeedPage,
)
from florabase.orders.service import OrderError, get_detail, get_order, ordered_on
from florabase.seed_lots import service as seeds
from florabase.seed_lots.model import SeedLot, SeedLotSourceKind
from florabase.seed_lots.schemas import (
    PartialDate,
    SeedLotCreate,
    SeedLotResponse,
    SeedLotUpdate,
    SupplierSummary,
)
from florabase.suppliers.model import Supplier

ELIGIBLE = ("unknown", "purchased", "purchased_fruit")


def lot_context(lot: SeedLot) -> AcquisitionContext:
    date = (
        PartialDate.model_validate(
            {
                "precision": lot.acquisition_date_precision,
                "year": lot.acquisition_date_year,
                "month": lot.acquisition_date_month,
                "day": lot.acquisition_date_day,
            }
        )
        if lot.acquisition_date_precision
        else None
    )
    return AcquisitionContext(
        source_kind=lot.source_kind,
        supplier_id=lot.supplier_id,
        acquisition_date=date,
        order_id=lot.order_id,
    )


def _lot(database: Session, lot_id: UUID, *, lock: bool = False) -> SeedLot:
    lot = (
        database.scalar(
            select(SeedLot)
            .where(SeedLot.id == lot_id)
            .execution_options(populate_existing=True)
            .with_for_update()
        )
        if lock
        else database.get(SeedLot, lot_id, populate_existing=True)
    )
    if lot is None:
        raise OrderError("seed_lot_not_found", "Seed lot no longer exists.", 404)
    return lot


def preview(database: Session, order_id: UUID, payload: PurchasePreviewRequest) -> PurchasePreview:
    lot = _lot(database, payload.seed_lot_id) if payload.seed_lot_id else None
    if (
        lot
        and payload.expected_seed_lot_updated_at
        and lot.updated_at != payload.expected_seed_lot_updated_at
    ):
        raise OrderError("stale_purchase_context", "Seed lot changed. Reload it and preview again.")
    current = payload.context or (lot_context(lot) if lot else AcquisitionContext())
    stored = lot_context(lot) if lot else None
    # Linking never erases a known Supplier because a draft cleared it. A normal saved
    # correction can clear that knowledge first; known replacements still require confirmation.
    if stored and stored.supplier_id and current.supplier_id is None:
        current = current.model_copy(update={"supplier_id": stored.supplier_id})
    order = get_detail(database, order_id)
    stored_supplier = (
        database.get(Supplier, stored.supplier_id) if stored and stored.supplier_id else None
    )
    supplier = database.get(Supplier, current.supplier_id) if current.supplier_id else None
    if current.supplier_id and not supplier:
        raise OrderError("supplier_not_found", "Selected SeedLot Supplier no longer exists.", 404)
    compatible = current.source_kind.value in ELIGIBLE and (
        not lot or (lot.lifecycle != "reversed" and lot.source_kind in ELIGIBLE)
    )
    return PurchasePreview(
        order=order,
        seed_lot_id=lot.id if lot else None,
        seed_lot_updated_at=lot.updated_at if lot else None,
        current=current,
        stored=stored,
        stored_supplier=SupplierSummary(id=stored_supplier.id, name=stored_supplier.name)
        if stored_supplier
        else None,
        current_supplier=SupplierSummary(id=supplier.id, name=supplier.name) if supplier else None,
        proposed_source=SeedLotSourceKind.PURCHASED
        if current.source_kind == SeedLotSourceKind.UNKNOWN
        else current.source_kind,
        supplier_action="keep"
        if not order.supplier_id
        else "replace"
        if (stored and stored.supplier_id and stored.supplier_id != order.supplier_id)
        or (current.supplier_id and current.supplier_id != order.supplier_id)
        else "keep"
        if current.supplier_id == order.supplier_id
        else "fill",
        date_action="keep"
        if not order.ordered_on or current.acquisition_date == order.ordered_on
        else "replace"
        if current.acquisition_date
        else "copy",
        can_apply=compatible,
        conflict=None
        if compatible
        else (
            "This source cannot link to a purchase. Correct its source explicitly in normal "
            "SeedLot edit first; converted or reversed material remains protected."
        ),
    )


def resolve(database: Session, order_id: UUID, payload: PurchaseApplyRequest) -> PurchaseResolution:
    # Creation and correction share lineage -> SeedLot (when existing) -> Order.
    # Taking lineage first also prevents new-lot creation from inverting the lock order.
    lock_lineage_writes(database)
    lot = _lot(database, payload.seed_lot_id, lock=True) if payload.seed_lot_id else None
    order = get_order(database, order_id, lock=True)
    if order.updated_at != payload.expected_order_updated_at or (
        lot and lot.updated_at != payload.expected_seed_lot_updated_at
    ):
        raise OrderError(
            "stale_purchase_context",
            "Order or SeedLot changed. Nothing applied; refresh and preview again.",
        )
    review = preview(
        database,
        order_id,
        PurchasePreviewRequest(
            seed_lot_id=payload.seed_lot_id,
            context=payload.context,
            expected_seed_lot_updated_at=payload.expected_seed_lot_updated_at,
        ),
    )
    if not review.can_apply:
        raise OrderError("order_source_conflict", review.conflict or "Incompatible source")
    if review.supplier_action == "replace" and not payload.use_order_supplier:
        raise OrderError(
            "order_supplier_conflict",
            "Confirm Use Order supplier before replacing a known Supplier.",
        )
    if payload.use_order_date and order.ordered_on_precision is None:
        raise OrderError("order_date_unknown", "This Order has no date to copy.")
    context = AcquisitionContext(
        order_id=order.id,
        source_kind=review.proposed_source,
        supplier_id=order.supplier_id
        if payload.use_order_supplier and order.supplier_id
        else review.current.supplier_id,
        acquisition_date=ordered_on(order)
        if payload.use_order_date
        else payload.context.acquisition_date,
    )
    return PurchaseResolution(
        order=review.order, context=context, confirmation=payload, seed_lot=None
    )


def _response(database: Session, lot: SeedLot) -> SeedLotResponse:
    projection = seeds.get_seed_lot(database, lot.id)
    assert projection is not None
    return seeds.responses(database, [projection])[0]


def apply(database: Session, order_id: UUID, payload: PurchaseApplyRequest) -> PurchaseResolution:
    result = resolve(database, order_id, payload)
    if payload.seed_lot_id:
        lot = _lot(database, payload.seed_lot_id, lock=True)
        response = _response(database, lot)
        values = {
            key: value
            for key, value in response.model_dump().items()
            if key in SeedLotUpdate.model_fields
        }
        values.update(result.context.model_dump())
        try:
            seeds.update_seed_lot(database, lot, SeedLotUpdate.model_validate(values))
        except (seeds.SeedLotDomainConflictError, seeds.SeedLotReferenceNotFoundError) as error:
            raise OrderError(error.code, error.message) from error
        result.seed_lot = _response(database, lot)
    return result


def create(database: Session, order_id: UUID, payload: PurchaseSeedLotCreate) -> SeedLotResponse:
    if payload.confirmation.seed_lot_id is not None:
        raise OrderError("invalid_purchase_context", "Creation requires a new-lot preview.")
    result = resolve(database, order_id, payload.confirmation)
    draft = payload.seed_lot
    if (
        AcquisitionContext.model_validate(
            draft.model_dump(include=set(AcquisitionContext.model_fields))
        )
        != result.context
    ):
        raise OrderError(
            "purchase_context_changed",
            "Acquisition fields changed after confirmation. Preview again before creating.",
        )
    try:
        lot = seeds.create_seed_lot(database, SeedLotCreate.model_validate(draft.model_dump()))
    except (seeds.SeedLotDomainConflictError, seeds.SeedLotReferenceNotFoundError) as error:
        raise OrderError(error.code, error.message) from error
    return _response(database, lot)


def choices(database: Session, order_id: UUID, q: str, offset: int, limit: int) -> PurchaseSeedPage:
    get_order(database, order_id)
    statement = (
        select(SeedLot, BotanicalIdentity, Supplier)
        .join(BotanicalIdentity, BotanicalIdentity.id == SeedLot.botanical_identity_id)
        .outerjoin(Supplier, Supplier.id == SeedLot.supplier_id)
        .where(SeedLot.source_kind.in_(ELIGIBLE), SeedLot.lifecycle != "reversed")
    )
    if q:
        statement = statement.where(
            or_(
                *(
                    column.icontains(q, autoescape=True)
                    for column in (SeedLot.label, BotanicalIdentity.scientific_name, Supplier.name)
                )
            )
        )
    total = int(database.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = database.execute(statement.order_by(SeedLot.id).offset(offset).limit(limit))
    return PurchaseSeedPage(
        items=[
            PurchaseSeedChoice(
                id=lot.id,
                label=lot.label or identity.scientific_name,
                source_kind=lot.source_kind,
                supplier=SupplierSummary(id=supplier.id, name=supplier.name) if supplier else None,
                order_id=lot.order_id,
            )
            for lot, identity, supplier in rows
        ],
        total=total,
        offset=offset,
        limit=limit,
    )
