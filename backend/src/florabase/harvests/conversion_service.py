from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from florabase.events.model import utc_now
from florabase.harvests import inventory_service as stock
from florabase.harvests.conversion_model import HarvestSeedLotConversion as Conversion
from florabase.harvests.conversion_schemas import (
    ConversionCreate,
    ConversionEligibility,
    ConversionResponse,
)
from florabase.harvests.inventory_model import HarvestMaterialDisposition as Disposition
from florabase.harvests.inventory_model import HarvestMaterialInventory as Inventory
from florabase.harvests.inventory_schemas import DispositionCreate, InventorySnapshot
from florabase.harvests.model import Harvest
from florabase.harvests.schemas import HarvestQuantity
from florabase.lineage.service import lock_lineage_writes
from florabase.plants.model import Plant, PlantGroup
from florabase.reversals.model import OperationReceipt
from florabase.seed_lots.model import SeedLot
from florabase.seed_lots.schemas import PartialDate, SeedLotCreate, SeedQuantity
from florabase.seed_lots.service import _quantity, _quantity_values, create_seed_lot
from florabase.sowings.model import Sowing


def snapshot_quantity(row: Conversion) -> SeedQuantity | None:
    if row.quantity_kind is None:
        return None
    return SeedQuantity.model_validate(
        {
            "kind": row.quantity_kind,
            "value": row.quantity_value,
            "unit": row.quantity_unit,
            "is_approximate": row.quantity_is_approximate,
        }
    )


def material_quantity(value: SeedQuantity | None) -> HarvestQuantity | None:
    return (
        HarvestQuantity.model_validate(
            {**value.model_dump(), "kind": "item_count" if value.kind == "seed_count" else "weight"}
        )
        if value
        else None
    )


def create(database: Session, inventory_id: UUID, payload: ConversionCreate) -> Conversion:
    # Shared lineage serialization comes before owner/stock locks. Ordinary stock writers
    # never acquire lineage locks; Harvest corrections use owner -> source, as here.
    lock_lineage_writes(database)
    inventory = stock.locked_inventory(database, inventory_id)
    if inventory.material_kind != "seed":
        raise stock.conflict(
            "seed_material_required", "Only tracked seed material can create a Seed lot"
        )
    if inventory.state != "active":
        raise stock.conflict("inventory_depleted", "Depleted material cannot create a Seed lot")
    before = stock.quantity(inventory)
    target = material_quantity(payload.quantity)
    if before and before.unit == "kg":
        raise stock.conflict(
            "seed_weight_unit_required",
            (
                "Record a current measurement in g or mg before creating a Seed lot; units "
                "are not converted"
            ),
        )
    if target and target.value == 0:
        raise stock.conflict(
            "positive_seed_quantity_required", "Transferred seed quantity must be positive"
        )
    if payload.mode == "use_all":
        if payload.resulting_quantity is not None:
            raise stock.conflict("use_all_remainder", "Use all leaves no source remainder")
        if before and not before.is_approximate and target != before:
            raise stock.conflict(
                "exact_transfer_mismatch",
                "Use all of exact stock requires the same exact target quantity",
            )
        if before and target:
            stock.compatible(before, target)
        disposition_payload = DispositionCreate(kind="used_for_propagation", mode="use_all")
    else:
        disposition_payload = DispositionCreate(
            kind="used_for_propagation",
            mode="partial",
            quantity=target,
            resulting_quantity=payload.resulting_quantity,
        )
    # Validate quantity accounting before creating any rows.
    stock.disposition_result(before, disposition_payload)
    harvest = database.get(Harvest, inventory.harvest_id)
    assert harvest is not None
    source = database.get(
        Plant if harvest.plant_id else PlantGroup, harvest.plant_id or harvest.plant_group_id
    )
    assert isinstance(source, (Plant, PlantGroup))
    harvest_date = (
        PartialDate(
            precision=harvest.occurred_on_precision,
            year=harvest.occurred_on_year,
            month=harvest.occurred_on_month,
            day=harvest.occurred_on_day,
        )
        if harvest.occurred_on_precision
        else None
    )
    lot = create_seed_lot(
        database,
        SeedLotCreate(
            botanical_identity_id=payload.botanical_identity_id or source.botanical_identity_id,
            source_kind="collection_produced",
            producer_plant_id=harvest.plant_id,
            producer_plant_group_id=harvest.plant_group_id,
            label=payload.label,
            quantity=payload.quantity,
            location_id=payload.location_id,
            harvest_date=harvest_date,
            expected_viability_until=payload.expected_viability_until,
            notes=payload.notes,
        ),
    )
    disposition = stock.record_disposition(database, inventory.id, disposition_payload)
    conversion = Conversion(
        inventory_id=inventory.id,
        disposition_id=disposition.id,
        seed_lot_id=lot.id,
        source_correction_version=inventory.correction_version,
        **_quantity_values(payload.quantity),
    )
    database.add(conversion)
    database.flush()
    return conversion


def list_conversions(
    database: Session, *, inventory_id: UUID | None = None, seed_lot_id: UUID | None = None
) -> list[ConversionResponse]:
    query = (
        select(Conversion, Inventory, Disposition, SeedLot)
        .join(Inventory, Inventory.id == Conversion.inventory_id)
        .join(Disposition, Disposition.id == Conversion.disposition_id)
        .join(SeedLot, SeedLot.id == Conversion.seed_lot_id)
    )
    if inventory_id is not None:
        query = query.where(Conversion.inventory_id == inventory_id)
    if seed_lot_id is not None:
        query = query.where(Conversion.seed_lot_id == seed_lot_id)
    return [
        ConversionResponse(
            id=c.id,
            inventory_id=c.inventory_id,
            harvest_id=i.harvest_id,
            harvest_item_id=i.harvest_item_id,
            disposition_id=c.disposition_id,
            seed_lot_id=c.seed_lot_id,
            seed_lot_label=lot.label,
            status=c.status,
            quantity=snapshot_quantity(c),
            before=InventorySnapshot(
                state=d.before_state, quantity=stock.quantity(d, "before_quantity")
            ),
            after=InventorySnapshot(
                state=d.after_state, quantity=stock.quantity(d, "after_quantity")
            ),
            created_at=c.created_at,
            reversed_at=c.reversed_at,
        )
        for c, i, d, lot in database.execute(query.order_by(Conversion.id.desc()))
    ]


def evaluate(
    database: Session, conversion_id: UUID, *, lock: bool = False
) -> tuple[Conversion, Inventory, SeedLot, Disposition, ConversionEligibility]:
    if lock:
        lock_lineage_writes(database)
    initial = database.get(Conversion, conversion_id)
    if initial is None:
        raise LookupError("Seed lot conversion not found")
    # Owner -> inventory -> conversion -> result; producer is not mutated on reversal.
    inventory = (
        stock.locked_inventory(database, initial.inventory_id)
        if lock
        else database.get(Inventory, initial.inventory_id)
    )
    query = (
        select(Conversion)
        .where(Conversion.id == conversion_id)
        .execution_options(populate_existing=True)
    )
    if lock:
        query = query.with_for_update()
    conversion = database.scalar(query)
    assert conversion is not None
    assert inventory is not None
    lot_query = (
        select(SeedLot)
        .where(SeedLot.id == conversion.seed_lot_id)
        .execution_options(populate_existing=True)
    )
    if lock:
        lot_query = lot_query.with_for_update()
    lot = database.scalar(lot_query)
    disposition = database.get(Disposition, conversion.disposition_id)
    assert lot is not None
    assert disposition is not None
    reasons: list[str] = []
    if conversion.status != "applied":
        reasons.append("This Seed lot creation has already been undone.")
    if (
        inventory.state != disposition.after_state
        or stock.quantity(inventory) != stock.quantity(disposition, "after_quantity")
        or inventory.correction_version != conversion.source_correction_version
    ):
        reasons.append(
            "Source inventory changed or was corrected after this conversion; restoring "
            "the old stock would erase later work."
        )
    # Retained later conversions whose reversal was completed are resolved history. An
    # ordinary disposition is never resolved by age, depletion or matching quantities.
    later = database.scalar(
        select(Disposition.id)
        .outerjoin(Conversion, Conversion.disposition_id == Disposition.id)
        .where(
            Disposition.inventory_id == inventory.id,
            Disposition.id > disposition.id,
            or_(Conversion.id.is_(None), Conversion.status == "applied"),
        )
        .limit(1)
    )
    if later:
        reasons.append("Later material disposition or Seed lot conversion must be resolved first.")
    harvest = database.get(Harvest, inventory.harvest_id)
    assert harvest is not None
    if lot.source_kind != "collection_produced" or (
        lot.producer_plant_id,
        lot.producer_plant_group_id,
    ) != (harvest.plant_id, harvest.plant_group_id):
        reasons.append("The Seed lot production origin no longer matches this conversion.")
    if lot.lifecycle != "active" or _quantity(lot) != snapshot_quantity(conversion):
        reasons.append("The Seed lot quantity or lifecycle changed after creation.")
    applied = database.scalar(
        select(OperationReceipt.id)
        .where(OperationReceipt.seed_lot_id == lot.id, OperationReceipt.status == "applied")
        .limit(1)
    )
    resolved = (
        select(OperationReceipt.id)
        .where(
            OperationReceipt.kind == "seed_lot_to_sowing",
            OperationReceipt.seed_lot_id == lot.id,
            OperationReceipt.sowing_id == Sowing.id,
            OperationReceipt.status == "reversed",
        )
        .exists()
    )
    unresolved = database.scalar(
        select(Sowing.id)
        .where(Sowing.seed_lot_id == lot.id, or_(Sowing.lifecycle != "reversed", ~resolved))
        .limit(1)
    )
    if applied or unresolved:
        reasons.append(
            "The Seed lot has unresolved Sowing or descendant use. Undo that dependent work first."
        )
    eligibility = ConversionEligibility(status="blocked" if reasons else "safe", reasons=reasons)
    return conversion, inventory, lot, disposition, eligibility


def reverse(database: Session, conversion_id: UUID) -> Conversion:
    conversion, inventory, lot, disposition, eligibility = evaluate(
        database, conversion_id, lock=True
    )
    if eligibility.status == "blocked":
        raise stock.conflict("harvest_conversion_reversal_blocked", " ".join(eligibility.reasons))
    inventory.state = disposition.before_state
    stock.set_quantity(inventory, stock.quantity(disposition, "before_quantity"))
    inventory.updated_at = utc_now()
    lot.lifecycle = "reversed"
    lot.updated_at = utc_now()
    conversion.status, conversion.reversed_at = "reversed", utc_now()
    database.flush()
    return conversion
