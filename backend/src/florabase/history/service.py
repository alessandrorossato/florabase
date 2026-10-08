"""One bounded SQL projection, with deduplication before global filtering/pagination."""

from typing import Any

from sqlalchemy import Integer, Select, String, case, cast, func, literal, select, true, union_all
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session, aliased

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.events.model import Event
from florabase.harvests.conversion_model import HarvestSeedLotConversion as Conversion
from florabase.harvests.inventory_model import HarvestMaterialDisposition as Disposition
from florabase.harvests.inventory_model import HarvestMaterialInventory as Inventory
from florabase.harvests.model import Harvest, HarvestItem
from florabase.history.schemas import (
    HistoryCategory,
    HistoryEntry,
    HistoryResponse,
    HistorySubjectKind,
)
from florabase.locations.model import Location
from florabase.plants.model import Plant, PlantGroup
from florabase.reversals.model import OperationKind
from florabase.reversals.model import OperationReceipt as Receipt
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import GerminationObservation as Germination
from florabase.sowings.model import Sowing


def _label(record: Any, fallback: str, identity: Any = BotanicalIdentity) -> Any:
    return _display_label(record.label, fallback, identity)


def _identity_id(model: Any) -> Any:
    return model.botanical_identity_id


def _display_label(label: Any, fallback: str, identity: Any = BotanicalIdentity) -> Any:
    # Same priority as recordPresentation: explicit, common, cultivar, scientific.
    return func.coalesce(
        label,
        func.nullif(identity.common_name, ""),
        func.nullif(identity.cultivar_name, ""),
        identity.scientific_name,
        fallback,
    )


def _ref(kind: Any, record_id: Any, label: Any, harvest_id: Any = None) -> Any:
    return cast(
        func.jsonb_build_object(
            "kind", kind, "id", record_id, "label", label, "harvest_id", harvest_id
        ),
        JSONB,
    )


def _branch(
    source: str,
    record: Any,
    category: str,
    subtype: Any,
    title: Any,
    primary: Any,
    *,
    date: Any = None,
    instant: Any = None,
    context: Any = "",
    related: Any = None,
    status: Any = None,
    suffix: str = "",
) -> Select[Any]:
    stamp = instant if instant is not None else record.created_at
    # Cast NULLs explicitly so each UNION column has one PostgreSQL type.
    precision = date.occurred_on_precision if date is not None else literal(None, String)
    year = date.occurred_on_year if date is not None else None
    month = date.occurred_on_month if date is not None else None
    day = date.occurred_on_day if date is not None else None
    if instant is not None:
        precision = literal("day")
        utc = func.timezone("UTC", instant)
        year, month, day = (func.extract(part, utc) for part in ("year", "month", "day"))
    return select(
        (literal(f"{source}:") + cast(record.id, String) + literal(suffix)).label("key"),
        literal(source).label("source_kind"),
        record.id.label("source_id"),
        literal(category).label("category"),
        cast(subtype, String).label("subtype"),
        precision.label("precision"),
        cast(year, String).label("year"),
        cast(month, String).label("month"),
        cast(day, String).label("day"),
        (instant if instant is not None else cast(None, Receipt.created_at.type)).label(
            "occurred_at"
        ),
        record.created_at.label("recorded_at"),
        stamp.label("sort_stamp"),
        cast(title, String).label("title"),
        cast(context, String).label("context"),
        primary.label("primary"),
        (related if related is not None else func.jsonb_build_array()).label("related"),
        cast(status, String).label("status"),
    )


def candidates() -> Any:
    target_kind = case((Event.plant_id.is_not(None), "plant"), else_="plant_group")
    target_id = func.coalesce(Event.plant_id, Event.plant_group_id)
    target_label = func.coalesce(Plant.label, PlantGroup.label)
    target = _ref(target_kind, target_id, _display_label(target_label, "Unlabelled record"))
    result = aliased(Plant)
    result_identity = aliased(BotanicalIdentity)
    event_refs = case(
        (
            Event.destination_location_id.is_not(None),
            func.jsonb_build_array(_ref("location", Location.id, Location.name)),
        ),
        (
            Event.resulting_plant_id.is_not(None),
            func.jsonb_build_array(
                _ref("plant", result.id, _label(result, "Unlabelled plant", result_identity))
            ),
        ),
        else_=func.jsonb_build_array(),
    )
    events = (
        _branch(
            "event",
            Event,
            "event",
            Event.kind,
            func.initcap(Event.kind),
            target,
            date=Event,
            context=case(
                (Event.recipient.is_not(None), func.concat("Recipient: ", Event.recipient)),
                else_="",
            ),
            related=event_refs,
            status=Receipt.status,
        )
        .select_from(Event)
        .outerjoin(Plant, Plant.id == Event.plant_id)
        .outerjoin(PlantGroup, PlantGroup.id == Event.plant_group_id)
        .join(
            BotanicalIdentity,
            BotanicalIdentity.id
            == func.coalesce(Plant.botanical_identity_id, PlantGroup.botanical_identity_id),
        )
        .outerjoin(Location, Location.id == Event.destination_location_id)
        .outerjoin(result, result.id == Event.resulting_plant_id)
        .outerjoin(result_identity, result_identity.id == result.botanical_identity_id)
        .outerjoin(Receipt, Receipt.event_id == Event.id)
        .where(~select(Harvest.id).where(Harvest.event_id == Event.id).exists())
    )
    source_kind = case((Harvest.plant_id.is_not(None), "plant"), else_="plant_group")
    source = _ref(
        source_kind,
        func.coalesce(Harvest.plant_id, Harvest.plant_group_id),
        _display_label(func.coalesce(Plant.label, PlantGroup.label), "Unlabelled source"),
    )
    materials = (
        select(HarvestItem.harvest_id, func.count().label("count"))
        .group_by(HarvestItem.harvest_id)
        .subquery()
    )
    harvests = (
        _branch(
            "harvest",
            Harvest,
            "harvest",
            literal("harvest"),
            literal("Harvest recorded"),
            _ref("harvest", Harvest.id, func.coalesce(Harvest.label, "Harvest")),
            date=Harvest,
            context=func.concat(
                materials.c.count,
                case((materials.c.count == 1, " material line"), else_=" material lines"),
            ),
            related=func.jsonb_build_array(source),
        )
        .select_from(Harvest)
        .join(materials, materials.c.harvest_id == Harvest.id)
        .outerjoin(Plant, Plant.id == Harvest.plant_id)
        .outerjoin(PlantGroup, PlantGroup.id == Harvest.plant_group_id)
        .join(
            BotanicalIdentity,
            BotanicalIdentity.id
            == func.coalesce(Plant.botanical_identity_id, PlantGroup.botanical_identity_id),
        )
    )
    germination = (
        _branch(
            "germination",
            Germination,
            "germination",
            literal("observation"),
            literal("Germination observed"),
            _ref("sowing", Sowing.id, _label(Sowing, "Sowing")),
            instant=None,
            context=func.concat(Germination.newly_germinated_count, " newly germinated"),
        )
        .select_from(Germination)
        .join(Sowing, Sowing.id == Germination.sowing_id)
        .join(SeedLot, SeedLot.id == Sowing.seed_lot_id)
        .join(BotanicalIdentity, BotanicalIdentity.id == SeedLot.botanical_identity_id)
    )
    # observed_on is an exact domain date, not created_at.
    germination = germination.with_only_columns(
        *[
            literal("day").label("precision")
            if c.key == "precision"
            else cast(func.extract(c.key, Germination.observed_on), String).label(c.key)
            if c.key in {"year", "month", "day"}
            else c
            for c in germination.selected_columns
        ]
    )
    receipts: list[Select[Any]] = []
    for kind, model, result_id, subject_kind, title in (
        (
            OperationKind.SEED_LOT_TO_SOWING,
            Sowing,
            Receipt.sowing_id,
            "sowing",
            "Sowing created from Seed lot",
        ),
        (
            OperationKind.SOWING_TO_PLANT,
            Plant,
            Receipt.plant_id,
            "plant",
            "Plant created from Sowing",
        ),
        (
            OperationKind.SOWING_TO_PLANT_GROUP,
            PlantGroup,
            Receipt.plant_group_id,
            "plant_group",
            "Plant group created from Sowing",
        ),
    ):
        parent = SeedLot if kind == OperationKind.SEED_LOT_TO_SOWING else Sowing
        parent_id = Receipt.seed_lot_id if parent is SeedLot else Receipt.sowing_id
        parent_kind = "seed_lot" if parent is SeedLot else "sowing"
        parent_identity = aliased(BotanicalIdentity)
        statement = (
            _branch(
                "operation_receipt",
                Receipt,
                "propagation",
                Receipt.kind,
                literal(title),
                _ref(
                    subject_kind,
                    result_id,
                    _label(model, subject_kind.replace("_", " ").capitalize()),
                ),
                status=Receipt.status,
                related=func.jsonb_build_array(
                    _ref(
                        parent_kind,
                        parent_id,
                        _label(parent, parent_kind.replace("_", " ").capitalize(), parent_identity),
                    )
                ),
            )
            .select_from(Receipt)
            .join(model, model.id == result_id)
        )
        if model is Sowing:
            statement = statement.join(SeedLot, SeedLot.id == Receipt.seed_lot_id)
        else:
            statement = statement.join(Sowing, Sowing.id == Receipt.sowing_id).join(
                SeedLot, SeedLot.id == Sowing.seed_lot_id
            )
        statement = statement.join(
            parent_identity, parent_identity.id == SeedLot.botanical_identity_id
        )
        statement = statement.join(
            BotanicalIdentity,
            BotanicalIdentity.id
            == (SeedLot.botanical_identity_id if model is Sowing else _identity_id(model)),
        )
        receipts.append(statement.where(Receipt.kind == kind.value, Receipt.event_id.is_(None)))
    inventory_label = func.concat(
        func.initcap(func.replace(Inventory.material_kind, "_", " ")),
        " · ",
        func.coalesce(HarvestItem.description, Harvest.label, "Stored material"),
    )
    inventory_ref = _ref(
        "harvest_inventory", Inventory.id, func.left(inventory_label, 180), Inventory.harvest_id
    )
    amount = case(
        (Disposition.quantity_kind.is_(None), "Amount unknown"),
        else_=func.concat(
            case((Disposition.quantity_is_approximate.is_(True), "Approximately "), else_=""),
            Disposition.quantity_value,
            " ",
            func.coalesce(Disposition.quantity_unit, "items"),
        ),
    )
    dispositions = (
        _branch(
            "disposition",
            Disposition,
            "material",
            Disposition.kind,
            func.concat("Material ", func.replace(Disposition.kind, "_", " ")),
            inventory_ref,
            date=Disposition,
            context=func.concat(
                case((Disposition.mode == "use_all", "Use all"), else_="Partial use"), " · ", amount
            ),
            related=func.jsonb_build_array(
                _ref("harvest", Harvest.id, func.coalesce(Harvest.label, "Harvest"))
            ),
        )
        .select_from(Disposition)
        .join(Inventory, Inventory.id == Disposition.inventory_id)
        .join(HarvestItem, HarvestItem.id == Inventory.harvest_item_id)
        .join(Harvest, Harvest.id == Inventory.harvest_id)
        .where(~select(Conversion.id).where(Conversion.disposition_id == Disposition.id).exists())
    )
    conversions: list[Select[Any]] = []
    for reversed_entry in (False, True):
        statement = (
            _branch(
                "conversion",
                Conversion,
                "material",
                literal("reversed" if reversed_entry else "applied"),
                literal(
                    "Seed conversion reversed"
                    if reversed_entry
                    else "Seed lot created from stored seeds"
                ),
                _ref("seed_lot", SeedLot.id, _label(SeedLot, "Seed lot")),
                instant=Conversion.reversed_at if reversed_entry else None,
                related=func.jsonb_build_array(inventory_ref),
                status=Conversion.status,
                suffix=":reversed" if reversed_entry else ":applied",
            )
            .select_from(Conversion)
            .join(Inventory, Inventory.id == Conversion.inventory_id)
            .join(HarvestItem, HarvestItem.id == Inventory.harvest_item_id)
            .join(Harvest, Harvest.id == Inventory.harvest_id)
            .join(SeedLot, SeedLot.id == Conversion.seed_lot_id)
            .join(BotanicalIdentity, BotanicalIdentity.id == SeedLot.botanical_identity_id)
        )
        conversions.append(
            statement.where(Conversion.reversed_at.is_not(None)) if reversed_entry else statement
        )
    return union_all(
        events, harvests, germination, *receipts, dispositions, *conversions
    ).subquery()


def history_statement(
    *,
    categories: tuple[HistoryCategory, ...] = (),
    subject_kind: HistorySubjectKind | None = None,
    year: int | None = None,
    offset: int = 0,
    limit: int = 50,
) -> Select[Any]:
    rows = candidates()
    utc = func.timezone("UTC", rows.c.sort_stamp)
    displayed_year = func.coalesce(
        cast(rows.c.year, String), cast(func.extract("year", utc), String)
    )
    filtered = select(rows)
    if categories:
        filtered = filtered.where(rows.c.category.in_([c.value for c in categories]))
    if subject_kind:
        filtered = filtered.where(rows.c.primary["kind"].astext == subject_kind.value)
    if year is not None:
        filtered = filtered.where(cast(displayed_year, Integer) == year)
    data = filtered.cte("history_candidates")
    total = select(func.count().label("total")).select_from(data).subquery()
    page = select(data).order_by(*_ordering(data)).offset(offset).limit(limit).subquery()
    # Outer-join a scalar count so empty pages still carry the correct total.
    return (
        select(total.c.total, page)
        .select_from(total.outerjoin(page, true()))
        .order_by(*_ordering(page))
    )


def _ordering(rows: Any) -> list[Any]:
    stamp = func.timezone("UTC", rows.c.sort_stamp)
    return [
        func.coalesce(cast(rows.c.year, Integer), func.extract("year", stamp)).desc().nulls_last(),
        case(
            (rows.c.precision.is_not(None), cast(rows.c.month, Integer)),
            else_=func.extract("month", stamp),
        )
        .desc()
        .nulls_last(),
        case(
            (rows.c.precision.is_not(None), cast(rows.c.day, Integer)),
            else_=func.extract("day", stamp),
        )
        .desc()
        .nulls_last(),
        rows.c.sort_stamp.desc(),
        rows.c.key.asc(),
    ]


def list_history(
    database: Session,
    *,
    categories: tuple[HistoryCategory, ...] = (),
    subject_kind: HistorySubjectKind | None = None,
    year: int | None = None,
    offset: int = 0,
    limit: int = 50,
) -> HistoryResponse:
    rows = (
        database.execute(
            history_statement(
                categories=categories,
                subject_kind=subject_kind,
                year=year,
                offset=offset,
                limit=limit,
            )
        )
        .mappings()
        .all()
    )
    items = []
    for row in rows:
        if row["key"] is None:
            continue
        occurred_on = (
            {
                "precision": row["precision"],
                **{
                    part: int(row[part]) if row[part] is not None else None
                    for part in ("year", "month", "day")
                },
            }
            if row["precision"]
            else None
        )
        items.append(
            HistoryEntry.model_validate(
                {
                    **row,
                    "occurred_on": occurred_on,
                    "date_basis": "occurred" if occurred_on else "recorded",
                }
            )
        )
    return HistoryResponse(items=items, total=rows[0]["total"], offset=offset, limit=limit)
