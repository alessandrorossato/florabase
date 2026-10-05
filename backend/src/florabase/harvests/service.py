from datetime import UTC, datetime
from uuid import UUID, uuid7

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.schemas import BotanicalIdentityResponse
from florabase.collection_photos.model import RecordMediaLink
from florabase.collection_photos.primary import primary_summaries
from florabase.events.model import Event
from florabase.events.service import EventDomainConflictError, _partial_date_values
from florabase.harvests.inventory_model import HarvestMaterialInventory
from florabase.harvests.model import Harvest, HarvestItem
from florabase.harvests.schemas import (
    HarvestItemResponse,
    HarvestQuantity,
    HarvestResponse,
    HarvestSource,
    HarvestWrite,
)
from florabase.plants.model import Plant, PlantGroup
from florabase.plants.schemas import BotanicalIdentitySummary
from florabase.seed_lots.schemas import PartialDate

MATERIAL_LABELS = {
    "fruit": "Fruit",
    "flower": "Flowers",
    "leaf": "Leaves",
    "root": "Roots",
    "seed": "Seeds",
    "stem_or_shoot": "Stem / shoot",
    "whole_plant": "Whole plant",
    "other": "Other",
}


def require_harvest(database: Session, harvest_id: UUID, *, lock: bool = False) -> Harvest:
    statement = select(Harvest).where(Harvest.id == harvest_id)
    if lock:
        statement = statement.with_for_update()
    result = database.scalar(statement.execution_options(populate_existing=True))
    if result is None:
        raise LookupError("Harvest not found")
    return result


def write_harvest(
    database: Session, payload: HarvestWrite, harvest_id: UUID | None = None
) -> Harvest:
    harvest = require_harvest(database, harvest_id, lock=True) if harvest_id else None
    if harvest and (harvest.plant_id, harvest.plant_group_id) != (
        payload.plant_id,
        payload.plant_group_id,
    ):
        from florabase.harvests.conversion_model import HarvestSeedLotConversion

        if database.scalar(
            select(HarvestSeedLotConversion.id)
            .join(
                HarvestMaterialInventory,
                HarvestMaterialInventory.id == HarvestSeedLotConversion.inventory_id,
            )
            .where(HarvestMaterialInventory.harvest_id == harvest.id)
            .limit(1)
        ):
            raise EventDomainConflictError(
                "harvest_conversion_source_immutable",
                "Harvest source is protected by retained Seed lot conversions",
            )
    model = Plant if payload.plant_id else PlantGroup
    source_id = payload.plant_id or payload.plant_group_id
    source = database.scalar(select(model).where(model.id == source_id).with_for_update())
    if source is None:
        raise LookupError("Harvest source not found")
    # No source-state side effects: even historical and inactive sources remain selectable.
    if harvest is None:
        if any(item.id for item in payload.items):
            raise EventDomainConflictError(
                "invalid_harvest_item", "New material lines must not have existing IDs"
            )
        event = Event(id=uuid7(), kind="harvest")
        database.add(event)
        event.plant_id, event.plant_group_id = payload.plant_id, payload.plant_group_id
        event.notes = payload.notes
        for field, value in _partial_date_values(payload.occurred_on).items():
            setattr(event, field, value)
        database.flush()
        harvest = Harvest(
            id=uuid7(),
            event_id=event.id,
            plant_id=payload.plant_id,
            plant_group_id=payload.plant_group_id,
        )
        database.add(harvest)
    else:
        owned_event = database.scalar(
            select(Event).where(Event.id == harvest.event_id).with_for_update()
        )
        if owned_event is None:
            raise RuntimeError("Owned Harvest Event is missing")
        event = owned_event
    old_items = list(
        database.scalars(select(HarvestItem).where(HarvestItem.harvest_id == harvest.id))
    )
    old_ids = {item.id for item in old_items}
    if any(item.id is not None and item.id not in old_ids for item in payload.items):
        raise EventDomainConflictError(
            "invalid_harvest_item", "A material line belongs to another Harvest"
        )
    tracked = (
        set(
            database.scalars(
                select(HarvestMaterialInventory.harvest_item_id).where(
                    HarvestMaterialInventory.harvest_item_id.in_(old_ids)
                )
            )
        )
        if old_ids
        else set()
    )
    submitted = {item.id: item for item in payload.items if item.id is not None}
    for old in old_items:
        if old.id in tracked and (
            old.id not in submitted or submitted[old.id].material_kind != old.material_kind
        ):
            raise EventDomainConflictError(
                "harvest_item_has_inventory",
                "Tracked material lines must retain their identity and material kind. "
                "Remove never-used tracking explicitly before removing a line; "
                "disposition history is retained",
            )
    # Retain referenced rows. Move existing ordering out of the final range before resequencing.
    offset = max((item.display_order for item in old_items), default=0) + 101
    for old in old_items:
        old.display_order += offset
    database.flush()
    for old in old_items:
        if old.id not in submitted:
            database.delete(old)
    database.flush()
    for field in ("plant_id", "plant_group_id", "label", "notes"):
        setattr(harvest, field, getattr(payload, field))
    for field, value in _partial_date_values(payload.occurred_on).items():
        setattr(harvest, field, value)
        setattr(event, field, value)
    event.plant_id, event.plant_group_id = payload.plant_id, payload.plant_group_id
    event.notes = payload.notes
    harvest.updated_at = event.updated_at = datetime.now(UTC)
    database.flush()
    retained = {item.id: item for item in old_items}
    for order, item in enumerate(payload.items):
        quantity = item.quantity
        line = retained[item.id] if item.id else HarvestItem(id=uuid7(), harvest_id=harvest.id)
        line.display_order = order
        line.material_kind = item.material_kind.value
        line.description = item.description
        line.quantity_kind = quantity.kind if quantity else None
        line.quantity_value = quantity.value if quantity else None
        line.quantity_unit = quantity.unit if quantity else None
        line.quantity_is_approximate = quantity.is_approximate if quantity else None
        database.add(line)
    database.flush()
    return harvest


def delete_harvest(database: Session, harvest_id: UUID) -> None:
    harvest = require_harvest(database, harvest_id, lock=True)
    if database.scalar(
        select(HarvestMaterialInventory.id)
        .join(HarvestItem, HarvestItem.id == HarvestMaterialInventory.harvest_item_id)
        .where(HarvestItem.harvest_id == harvest.id)
        .limit(1)
    ):
        raise EventDomainConflictError(
            "harvest_has_inventory",
            "Stored material depends on this Harvest. Remove never-used "
            "tracking explicitly first; material with disposition history must remain retained",
        )
    # Shared assets remain in the library. CASCADE clears only this target's designation.
    database.execute(delete(RecordMediaLink).where(RecordMediaLink.harvest_id == harvest.id))
    # Ordinary Event media are independent; preserve the established explicit-unlink guard.
    if database.scalar(
        select(RecordMediaLink.id).where(RecordMediaLink.event_id == harvest.event_id).limit(1)
    ):
        raise EventDomainConflictError(
            "event_has_photos", "Unlink the owned Event's media before deleting the Harvest"
        )
    event = database.get(Event, harvest.event_id)
    database.delete(harvest)
    database.flush()
    if event is not None:
        database.delete(event)
    database.flush()


def list_harvests(
    database: Session,
    *,
    botanical_identity_id: UUID | None = None,
    plant_id: UUID | None = None,
    plant_group_id: UUID | None = None,
    harvest_id: UUID | None = None,
    harvest_ids: list[UUID] | None = None,
    event_ids: list[UUID] | None = None,
    query: str = "",
    material_kind: str | None = None,
    source_type: str | None = None,
) -> list[HarvestResponse]:
    statement = (
        select(Harvest, Plant, PlantGroup, BotanicalIdentity)
        .outerjoin(Plant, Plant.id == Harvest.plant_id)
        .outerjoin(PlantGroup, PlantGroup.id == Harvest.plant_group_id)
        .join(
            BotanicalIdentity,
            (BotanicalIdentity.id == Plant.botanical_identity_id)
            | (BotanicalIdentity.id == PlantGroup.botanical_identity_id),
        )
    )
    if harvest_id:
        statement = statement.where(Harvest.id == harvest_id)
    if harvest_ids is not None:
        statement = statement.where(Harvest.id.in_(harvest_ids))
    if event_ids is not None:
        statement = statement.where(Harvest.event_id.in_(event_ids))
    if source_type:
        statement = statement.where(
            (Harvest.plant_id if source_type == "plant" else Harvest.plant_group_id).is_not(None)
        )
    if material_kind:
        statement = statement.where(
            select(HarvestItem.id)
            .where(HarvestItem.harvest_id == Harvest.id, HarvestItem.material_kind == material_kind)
            .exists()
        )
    if query.strip():
        needle = (
            "%" + query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        )
        statement = statement.where(
            or_(
                *[
                    column.ilike(needle, escape="\\")
                    for column in (
                        Harvest.label,
                        Plant.label,
                        PlantGroup.label,
                        BotanicalIdentity.scientific_name,
                        BotanicalIdentity.common_name,
                        BotanicalIdentity.cultivar_name,
                    )
                ]
            )
        )
    if botanical_identity_id:
        statement = statement.where(BotanicalIdentity.id == botanical_identity_id)
    if plant_id:
        statement = statement.where(Harvest.plant_id == plant_id)
    if plant_group_id:
        statement = statement.where(Harvest.plant_group_id == plant_group_id)
    rows = database.execute(
        statement.order_by(
            Harvest.occurred_on_year.desc().nulls_last(),
            Harvest.occurred_on_month.desc().nulls_last(),
            Harvest.occurred_on_day.desc().nulls_last(),
            Harvest.created_at.desc(),
            Harvest.id.desc(),
        )
    ).all()
    if not rows:
        return []
    ids = [row[0].id for row in rows]
    lines: dict[UUID, list[HarvestItemResponse]] = {key: [] for key in ids}
    for item in database.scalars(
        select(HarvestItem)
        .where(HarvestItem.harvest_id.in_(ids))
        .order_by(HarvestItem.display_order)
    ):
        lines[item.harvest_id].append(
            HarvestItemResponse(
                id=item.id,
                display_order=item.display_order,
                material_kind=item.material_kind,
                description=item.description,
                quantity=HarvestQuantity(
                    kind=item.quantity_kind,
                    value=item.quantity_value,
                    unit=item.quantity_unit,
                    is_approximate=item.quantity_is_approximate,
                )
                if item.quantity_kind
                else None,
            )
        )
    photos = primary_summaries(database, "harvest", ids)
    plant_photos = primary_summaries(
        database, "plant", list({plant.id for _, plant, _, _ in rows if plant})
    )
    group_photos = primary_summaries(
        database, "plant_group", list({group.id for _, _, group, _ in rows if group})
    )
    result = []
    for harvest, plant, group, identity in rows:
        source = plant or group
        name = (
            source.label
            or identity.common_name
            or identity.cultivar_name
            or identity.scientific_name
        )
        materials = list(
            dict.fromkeys(MATERIAL_LABELS[item.material_kind] for item in lines[harvest.id])
        )
        summary = " + ".join(materials[:2]) + (" + more" if len(materials) > 2 else "")
        result.append(
            HarvestResponse(
                id=harvest.id,
                plant_id=harvest.plant_id,
                plant_group_id=harvest.plant_group_id,
                label=harvest.label,
                display_title=harvest.label or f"{name} — {summary} harvest",
                source=HarvestSource(
                    type="plant" if plant else "plant_group",
                    id=source.id,
                    label=source.label,
                    display_name=name,
                    lifecycle=source.lifecycle,
                    botanical_identity=BotanicalIdentitySummary(
                        id=identity.id,
                        display_label=BotanicalIdentityResponse.from_model(identity).display_label,
                    ),
                    primary_photo=(plant_photos if plant else group_photos).get(source.id),
                ),
                occurred_on=PartialDate(
                    precision=harvest.occurred_on_precision,
                    year=harvest.occurred_on_year,
                    month=harvest.occurred_on_month,
                    day=harvest.occurred_on_day,
                )
                if harvest.occurred_on_precision
                else None,
                notes=harvest.notes,
                items=lines[harvest.id],
                event_id=harvest.event_id,
                primary_photo=photos.get(harvest.id),
                created_at=harvest.created_at,
                updated_at=harvest.updated_at,
            )
        )
    return result


def read_harvest(database: Session, harvest_id: UUID) -> HarvestResponse:
    # Filter the shared batched projection at SQL level for detail reads.
    require_harvest(database, harvest_id)
    return list_harvests(database, harvest_id=harvest_id)[0]
