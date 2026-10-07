from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.bulk.schemas import (
    BulkKind,
    BulkLocationApplyRequest,
    BulkLocationPreview,
    BulkLocationPreviewRequest,
    BulkLocationResult,
    BulkLocationRow,
    BulkReference,
)
from florabase.events.model import EventKind
from florabase.events.schemas import EventCreate
from florabase.events.service import create_event
from florabase.harvests.inventory_model import HarvestMaterialInventory as Inventory
from florabase.harvests.inventory_service import assign_location as assign_inventory_location
from florabase.harvests.model import Harvest, HarvestItem
from florabase.lineage.service import lock_lineage_writes
from florabase.locations.model import Location
from florabase.locations.schemas import LocationUsageScope
from florabase.locations.service import (
    LocationIntegrityError,
    display_path,
    list_locations,
    validate_location_scope,
)
from florabase.plants.model import Plant, PlantGroup
from florabase.seed_lots.model import SeedLot
from florabase.seed_lots.service import assign_location as assign_seed_location
from florabase.sowings.model import Sowing
from florabase.sowings.service import assign_location as assign_sowing_location

Record = SeedLot | Sowing | Plant | PlantGroup | Inventory
MODELS: dict[
    BulkKind, type[SeedLot] | type[Sowing] | type[Plant] | type[PlantGroup] | type[Inventory]
] = {
    "seed_lot": SeedLot,
    "sowing": Sowing,
    "plant": Plant,
    "plant_group": PlantGroup,
    "harvest_inventory": Inventory,
}
SCOPES: dict[BulkKind, LocationUsageScope] = {
    "seed_lot": LocationUsageScope.SEED_LOTS,
    "sowing": LocationUsageScope.SOWINGS,
    "plant": LocationUsageScope.PLANTS,
    "plant_group": LocationUsageScope.PLANTS,
    "harvest_inventory": LocationUsageScope.HARVEST_INVENTORY,
}


@dataclass(frozen=True)
class BulkConflictError(Exception):
    code: str
    message: str
    rows: tuple[BulkLocationRow, ...] = ()


def _records(
    database: Session, references: list[BulkReference], *, lock: bool
) -> dict[tuple[BulkKind, UUID], tuple[Record, str]]:
    result: dict[tuple[BulkKind, UUID], tuple[Record, str]] = {}
    # Inventory always locks its Harvest owner before the inventory rows, like normal correction.
    inventory_ids = [row.id for row in references if row.kind == "harvest_inventory"]
    if lock and inventory_ids:
        list(
            database.scalars(
                select(Harvest)
                .where(
                    Harvest.id.in_(
                        select(Inventory.harvest_id).where(Inventory.id.in_(inventory_ids))
                    )
                )
                .order_by(Harvest.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        )
    for kind, model in MODELS.items():
        ids = [row.id for row in references if row.kind == kind]
        if not ids:
            continue
        statement: Select[Any]
        if model is Inventory:
            statement = (
                select(Inventory, func.coalesce(HarvestItem.description, Harvest.label))
                .join(HarvestItem, HarvestItem.id == Inventory.harvest_item_id)
                .join(Harvest, Harvest.id == Inventory.harvest_id)
                .where(Inventory.id.in_(ids))
            )
        elif model is Sowing:
            statement = (
                select(Sowing, BotanicalIdentity.scientific_name)
                .join(SeedLot, SeedLot.id == Sowing.seed_lot_id)
                .join(BotanicalIdentity, BotanicalIdentity.id == SeedLot.botanical_identity_id)
                .where(Sowing.id.in_(ids))
            )
        else:
            statement = (
                select(model, BotanicalIdentity.scientific_name)
                .join(
                    BotanicalIdentity,
                    BotanicalIdentity.id
                    == cast(
                        type[SeedLot] | type[Plant] | type[PlantGroup], model
                    ).botanical_identity_id,
                )
                .where(model.id.in_(ids))
            )
        statement = statement.order_by(model.id).execution_options(populate_existing=True)
        if lock:
            statement = statement.with_for_update(of=model)
        for row, context in database.execute(statement):
            record = cast(Record, row)
            label = (
                f"Stored {record.material_kind.replace('_', ' ')} · "
                f"{context or 'Unlabelled harvest item'}"
                if isinstance(record, Inventory)
                else f"{record.label or kind.replace('_', ' ').title()} · {context}"
            )
            result[kind, record.id] = record, label
    return result


def _preview(
    database: Session,
    references: list[BulkReference],
    target_id: UUID,
    *,
    lock: bool = False,
) -> tuple[BulkLocationPreview, dict[tuple[BulkKind, UUID], tuple[Record, str]], Location]:
    if lock:
        lock_lineage_writes(database)
    records = _records(database, references, lock=lock)
    target = database.get(Location, target_id, with_for_update=lock, populate_existing=True)
    if target is None:
        raise BulkConflictError(
            "target_location_not_found", "The target Location no longer exists."
        )
    locations = list_locations(database)
    paths = {row.id: display_path(row, locations) for row in locations}
    rows: list[BulkLocationRow] = []
    for ref in references:
        found = records.get((ref.kind, ref.id))
        record, label = found if found else (None, f"{ref.kind.replace('_', ' ')} · {ref.id}")
        code = message = None
        if record is None:
            code, message = "record_not_found", "Selected record no longer exists in this domain."
        elif (record.state if isinstance(record, Inventory) else record.lifecycle) != "active":
            code, message = "record_not_active", "Only current active records can be moved."
        else:
            try:
                validate_location_scope(target, SCOPES[ref.kind])
            except LocationIntegrityError as error:
                code, message = error.code, error.message
        rows.append(
            BulkLocationRow(
                kind=ref.kind,
                id=ref.id,
                label=label,
                current_location_id=record.location_id if record else None,
                current_location=paths.get(record.location_id)
                if record and record.location_id
                else None,
                updated_at=record.updated_at if record else None,
                status="conflict"
                if code
                else "unchanged"
                if record and record.location_id == target_id
                else "move",
                code=code,
                message=message,
            )
        )
    moves = sum(row.status == "move" for row in rows)
    return (
        BulkLocationPreview(
            target_location_id=target.id,
            target_location=paths[target.id],
            target_updated_at=target.updated_at,
            selected_count=len(rows),
            move_count=moves,
            unchanged_count=sum(row.status == "unchanged" for row in rows),
            can_apply=moves > 0 and all(row.status != "conflict" for row in rows),
            rows=rows,
        ),
        records,
        target,
    )


def preview(database: Session, payload: BulkLocationPreviewRequest) -> BulkLocationPreview:
    return _preview(database, payload.records, payload.target_location_id)[0]


def apply(database: Session, payload: BulkLocationApplyRequest) -> BulkLocationResult:
    # Lock and re-read every selected record before any domain mutation.
    references = [BulkReference(kind=row.kind, id=row.id) for row in payload.records]
    result, records, target = _preview(database, references, payload.target_location_id, lock=True)
    conflicts = tuple(row for row in result.rows if row.status == "conflict")
    if conflicts:
        raise BulkConflictError(
            "selection_conflict", "No records moved. Review the selection again.", conflicts
        )
    expected = {(row.kind, row.id): row.expected_updated_at for row in payload.records}
    stale = tuple(row for row in result.rows if row.updated_at != expected[row.kind, row.id])
    if stale or target.updated_at != payload.expected_target_updated_at:
        raise BulkConflictError(
            "stale_preview", "No records moved. Records or target changed; preview again.", stale
        )
    if not result.move_count:
        raise BulkConflictError(
            "all_unchanged", "All selected records are already at this Location."
        )
    for row in result.rows:
        if row.status == "unchanged":
            continue
        record = records[row.kind, row.id][0]
        if isinstance(record, SeedLot):
            assign_seed_location(record, target)
        elif isinstance(record, Sowing):
            assign_sowing_location(record, target)
        elif isinstance(record, Inventory):
            assign_inventory_location(record, target)
        else:
            create_event(
                database,
                "plant" if isinstance(record, Plant) else "plant_group",
                record.id,
                EventCreate(kind=EventKind.MOVEMENT, destination_location_id=target.id),
            )
    database.flush()
    return BulkLocationResult(moved_count=result.move_count, unchanged_count=result.unchanged_count)
