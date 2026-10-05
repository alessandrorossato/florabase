from decimal import localcontext
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from florabase.events.model import utc_now
from florabase.events.service import EventDomainConflictError, _partial_date_values
from florabase.harvests.inventory_model import HarvestMaterialDisposition as Disposition
from florabase.harvests.inventory_model import HarvestMaterialInventory as Inventory
from florabase.harvests.inventory_schemas import (
    DispositionCreate,
    DispositionResponse,
    InventoryLocation,
    InventoryResponse,
    InventorySnapshot,
    InventoryWrite,
)
from florabase.harvests.model import HarvestItem
from florabase.harvests.schemas import HarvestQuantity
from florabase.harvests.service import list_harvests, require_harvest
from florabase.locations.schemas import LocationUsageScope
from florabase.locations.service import display_path, list_locations, require_location_for_scope


def conflict(code: str, message: str) -> EventDomainConflictError:
    return EventDomainConflictError(code, message)


def quantity(row: object, prefix: str = "quantity") -> HarvestQuantity | None:
    if getattr(row, f"{prefix}_kind") is None:
        return None
    return HarvestQuantity(
        kind=getattr(row, f"{prefix}_kind"),
        value=getattr(row, f"{prefix}_value"),
        unit=getattr(row, f"{prefix}_unit"),
        is_approximate=getattr(row, f"{prefix}_is_approximate"),
    )


def set_quantity(row: object, value: HarvestQuantity | None, prefix: str = "quantity") -> None:
    for part in ("kind", "value", "unit", "is_approximate"):
        setattr(row, f"{prefix}_{part}", getattr(value, part) if value else None)


def compatible(left: HarvestQuantity, right: HarvestQuantity) -> None:
    if (left.kind, left.unit) != (right.kind, right.unit):
        raise conflict(
            "incompatible_inventory_quantity",
            "Use the same quantity dimension and unit; units are not converted",
        )


def track(database: Session, item_id: UUID, payload: InventoryWrite) -> Inventory:
    item = database.get(HarvestItem, item_id)
    if item is None:
        raise LookupError("Harvest material line not found")
    # Shared owner-first order also used by Harvest corrections and tracking removal.
    require_harvest(database, item.harvest_id, lock=True)
    item = database.scalar(
        select(HarvestItem)
        .where(HarvestItem.id == item_id)
        .execution_options(populate_existing=True)
    )
    if item is None:
        raise LookupError("Harvest material line not found")
    if database.scalar(select(Inventory.id).where(Inventory.harvest_item_id == item_id)):
        raise conflict("inventory_already_tracked", "This material line is already tracked")
    original, current = quantity(item), payload.quantity
    if original and current:
        compatible(original, current)
        if (
            not original.is_approximate
            and not current.is_approximate
            and current.value > original.value
        ):
            raise conflict(
                "initial_inventory_quantity_exceeded",
                "Exact remaining quantity cannot exceed the exact collected amount",
            )
    require_location_for_scope(database, payload.location_id, LocationUsageScope.HARVEST_INVENTORY)
    inventory = Inventory(
        harvest_item_id=item_id,
        harvest_id=item.harvest_id,
        material_kind=item.material_kind,
        state=payload.state,
        location_id=payload.location_id,
    )
    set_quantity(inventory, payload.quantity)
    database.add(inventory)
    database.flush()
    return inventory


def locked_inventory(database: Session, inventory_id: UUID) -> Inventory:
    owner_id = database.scalar(
        select(HarvestItem.harvest_id)
        .join(Inventory, Inventory.harvest_item_id == HarvestItem.id)
        .where(Inventory.id == inventory_id)
    )
    if owner_id is None:
        raise LookupError("Stored material not found")
    require_harvest(database, owner_id, lock=True)
    inventory = database.scalar(
        select(Inventory)
        .where(Inventory.id == inventory_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if inventory is None:
        raise LookupError("Stored material not found")
    return inventory


def correct(database: Session, inventory_id: UUID, payload: InventoryWrite) -> Inventory:
    inventory = locked_inventory(database, inventory_id)
    require_location_for_scope(database, payload.location_id, LocationUsageScope.HARVEST_INVENTORY)
    if inventory.state != payload.state or quantity(inventory) != payload.quantity:
        inventory.correction_version += 1
    inventory.state, inventory.location_id = payload.state, payload.location_id
    set_quantity(inventory, payload.quantity)
    inventory.updated_at = utc_now()
    database.flush()
    return inventory


def remove_tracking(database: Session, inventory_id: UUID) -> None:
    inventory = locked_inventory(database, inventory_id)
    if database.scalar(
        select(Disposition.id).where(Disposition.inventory_id == inventory.id).limit(1)
    ):
        raise conflict(
            "inventory_has_dispositions",
            (
                "Disposition history is retained. Correct current stored material "
                "instead of removing tracking"
            ),
        )
    database.delete(inventory)
    database.flush()


def disposition_result(
    before: HarvestQuantity | None, payload: DispositionCreate
) -> tuple[HarvestQuantity | None, HarvestQuantity | None]:
    if payload.mode == "use_all":
        return before, None
    used, after = payload.quantity, payload.resulting_quantity
    if before is None:
        if after is not None:
            raise conflict(
                "unknown_inventory_remainder",
                (
                    "Unknown stock remains unknown after partial use; use "
                    "current-state correction to record a new measurement"
                ),
            )
        return used, None
    if used:
        compatible(before, used)
    if before.is_approximate:
        if after is None or not after.is_approximate:
            raise conflict(
                "approximate_remainder_required",
                "Confirm an approximate remaining quantity for partial use of approximate stock",
            )
        compatible(before, after)
        return used, after
    if used is None or used.is_approximate:
        raise conflict(
            "exact_disposition_quantity_required",
            "Partial use of exact stock requires an exact amount used",
        )
    if after is not None:
        raise conflict(
            "exact_remainder_derived",
            "Exact remaining quantity is calculated from the current balance and amount used",
        )
    if used.value >= before.value:
        raise conflict(
            "inventory_quantity_exceeded",
            (
                "Partial usage must be smaller than the exact balance; choose Use "
                "all remaining for the whole balance"
            ),
        )
    # NUMERIC is unbounded. Avoid Decimal's default 28-digit rounding on exact subtraction.
    before_exponent = before.value.as_tuple().exponent
    used_exponent = used.value.as_tuple().exponent
    assert isinstance(before_exponent, int)
    assert isinstance(used_exponent, int)
    with localcontext() as context:
        context.prec = (
            max(before.value.adjusted(), used.value.adjusted())
            - min(before_exponent, used_exponent)
            + 2
        )
        remainder = before.value - used.value
    return used, HarvestQuantity(
        kind=before.kind, value=remainder, unit=before.unit, is_approximate=False
    )


def record_disposition(
    database: Session, inventory_id: UUID, payload: DispositionCreate
) -> Disposition:
    inventory = locked_inventory(database, inventory_id)
    if inventory.state == "depleted":
        raise conflict(
            "inventory_depleted",
            (
                "Depleted material cannot receive another disposition; correct "
                "current state first if needed"
            ),
        )
    before = quantity(inventory)
    used, after = disposition_result(before, payload)
    result = Disposition(
        inventory_id=inventory.id,
        kind=payload.kind,
        mode=payload.mode,
        before_state=inventory.state,
        after_state="depleted" if payload.mode == "use_all" else "active",
        notes=payload.notes,
        **_partial_date_values(payload.occurred_on),
    )
    set_quantity(result, before, "before_quantity")
    set_quantity(result, after, "after_quantity")
    set_quantity(result, used)
    inventory.state = result.after_state
    inventory.updated_at = utc_now()
    set_quantity(inventory, after)
    database.add(result)
    database.flush()
    return result


def history(database: Session, inventory_id: UUID) -> list[DispositionResponse]:
    if database.get(Inventory, inventory_id) is None:
        raise LookupError("Stored material not found")
    from florabase.seed_lots.schemas import PartialDate

    return [
        DispositionResponse(
            id=row.id,
            inventory_id=row.inventory_id,
            kind=row.kind,
            mode=row.mode,
            occurred_on=PartialDate(
                precision=row.occurred_on_precision,
                year=row.occurred_on_year,
                month=row.occurred_on_month,
                day=row.occurred_on_day,
            )
            if row.occurred_on_precision
            else None,
            quantity=quantity(row),
            before=InventorySnapshot(
                state=row.before_state, quantity=quantity(row, "before_quantity")
            ),
            after=InventorySnapshot(
                state=row.after_state, quantity=quantity(row, "after_quantity")
            ),
            notes=row.notes,
            created_at=row.created_at,
        )
        for row in database.scalars(
            select(Disposition)
            .where(Disposition.inventory_id == inventory_id)
            .order_by(Disposition.created_at.desc(), Disposition.id.desc())
        )
    ]


def list_inventory(
    database: Session,
    *,
    harvest_id: UUID | None = None,
    inventory_id: UUID | None = None,
    state: str | None = None,
    material_kind: str | None = None,
    location_id: UUID | None = None,
) -> list[InventoryResponse]:
    statement = select(
        Inventory,
        HarvestItem,
        select(Disposition.id).where(Disposition.inventory_id == Inventory.id).exists(),
    ).join(HarvestItem, HarvestItem.id == Inventory.harvest_item_id)
    if harvest_id:
        statement = statement.where(HarvestItem.harvest_id == harvest_id)
    if inventory_id:
        statement = statement.where(Inventory.id == inventory_id)
    if state:
        statement = statement.where(Inventory.state == state)
    if material_kind:
        statement = statement.where(HarvestItem.material_kind == material_kind)
    if location_id:
        statement = statement.where(Inventory.location_id == location_id)
    rows = database.execute(
        statement.order_by(Inventory.created_at.desc(), Inventory.id.desc())
    ).all()
    if not rows:
        return []
    harvests = {
        row.id: row
        for row in list_harvests(
            database, harvest_ids=list({item.harvest_id for _, item, _ in rows})
        )
    }
    locations = list_locations(database) if any(row.location_id for row, _, _ in rows) else []
    paths = {location.id: display_path(location, locations) for location in locations}
    return [
        InventoryResponse(
            id=row.id,
            harvest_item_id=item.id,
            harvest_id=item.harvest_id,
            harvest_title=harvests[item.harvest_id].display_title,
            source=harvests[item.harvest_id].source,
            material_kind=item.material_kind,
            description=item.description,
            state=row.state,
            quantity=quantity(row),
            location=InventoryLocation(id=row.location_id, display_path=paths[row.location_id])
            if row.location_id
            else None,
            has_dispositions=has_history,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row, item, has_history in rows
    ]


def read_inventory(database: Session, inventory_id: UUID) -> InventoryResponse:
    rows = list_inventory(database, inventory_id=inventory_id)
    if not rows:
        raise LookupError("Stored material not found")
    return rows[0]
