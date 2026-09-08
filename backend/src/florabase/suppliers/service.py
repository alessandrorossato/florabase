from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, case, desc, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.selectable import ScalarSelect

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.schemas import BotanicalIdentityResponse
from florabase.plants.model import Plant, PlantGroup
from florabase.seed_lots.model import SeedLot
from florabase.seed_lots.schemas import PartialDate
from florabase.suppliers.model import Supplier
from florabase.suppliers.schemas import (
    SupplierBotanicalIdentitySummary,
    SupplierCreate,
    SupplierDetailResponse,
    SupplierListResponse,
    SupplierPlantGroupLink,
    SupplierPlantLink,
    SupplierRecentAcquisition,
    SupplierResponse,
    SupplierSeedLotLink,
    SupplierUpdate,
    SupplierUsageCounts,
)


@dataclass(frozen=True)
class SupplierCountExpressions:
    seed_lots_active: ScalarSelect[int]
    seed_lots_total: ScalarSelect[int]
    plants_active: ScalarSelect[int]
    plants_total: ScalarSelect[int]
    plant_groups_active: ScalarSelect[int]
    plant_groups_total: ScalarSelect[int]


def _count_expressions() -> SupplierCountExpressions:
    def count(
        model: type[SeedLot] | type[Plant] | type[PlantGroup], *, active: bool
    ) -> ScalarSelect[int]:
        statement = select(func.count()).select_from(model).where(model.supplier_id == Supplier.id)
        if active:
            statement = statement.where(model.lifecycle == "active")
        return statement.scalar_subquery()

    return SupplierCountExpressions(
        seed_lots_active=count(SeedLot, active=True),
        seed_lots_total=count(SeedLot, active=False),
        plants_active=count(Plant, active=True),
        plants_total=count(Plant, active=False),
        plant_groups_active=count(PlantGroup, active=True),
        plant_groups_total=count(PlantGroup, active=False),
    )


def _usage_counts(values: tuple[int, int, int, int, int, int]) -> SupplierUsageCounts:
    seed_active, seed_total, plant_active, plant_total, group_active, group_total = values
    return SupplierUsageCounts(
        seed_lots_active=seed_active,
        seed_lots_total=seed_total,
        plants_active=plant_active,
        plants_total=plant_total,
        plant_groups_active=group_active,
        plant_groups_total=group_total,
        direct_records_active=seed_active + plant_active + group_active,
        direct_records_total=seed_total + plant_total + group_total,
    )


def _list_statement() -> Select[tuple[Supplier, int, int, int, int, int, int]]:
    counts = _count_expressions()
    return select(
        Supplier,
        counts.seed_lots_active,
        counts.seed_lots_total,
        counts.plants_active,
        counts.plants_total,
        counts.plant_groups_active,
        counts.plant_groups_total,
    ).order_by(
        case((Supplier.retired_at.is_(None), 0), else_=1),
        func.lower(Supplier.name),
        Supplier.kind,
        Supplier.id,
    )


def create_supplier(database: Session, payload: SupplierCreate) -> Supplier:
    supplier = Supplier(**payload.model_dump(mode="json"))
    database.add(supplier)
    database.flush()
    return supplier


def get_supplier(database: Session, supplier_id: UUID) -> Supplier | None:
    return database.get(Supplier, supplier_id)


def list_suppliers(database: Session) -> list[SupplierListResponse]:
    return [
        SupplierListResponse(
            **SupplierResponse.from_model(supplier).model_dump(),
            usage_counts=_usage_counts(
                (
                    seed_active,
                    seed_total,
                    plant_active,
                    plant_total,
                    group_active,
                    group_total,
                )
            ),
        )
        for (
            supplier,
            seed_active,
            seed_total,
            plant_active,
            plant_total,
            group_active,
            group_total,
        ) in database.execute(_list_statement()).tuples()
    ]


def _partial_date(record: SeedLot | Plant | PlantGroup, prefix: str) -> PartialDate | None:
    precision = getattr(record, f"{prefix}_precision")
    if precision is None:
        return None
    return PartialDate(
        precision=precision,
        year=getattr(record, f"{prefix}_year"),
        month=getattr(record, f"{prefix}_month"),
        day=getattr(record, f"{prefix}_day"),
    )


def _identity_summary(identity: BotanicalIdentity) -> SupplierBotanicalIdentitySummary:
    return SupplierBotanicalIdentitySummary(
        id=identity.id,
        display_label=BotanicalIdentityResponse.from_model(identity).display_label,
    )


def _linked_seed_lots_statement() -> Select[tuple[SeedLot, BotanicalIdentity]]:
    return (
        select(SeedLot, BotanicalIdentity)
        .join(BotanicalIdentity, BotanicalIdentity.id == SeedLot.botanical_identity_id)
        .order_by(
            case((SeedLot.lifecycle == "active", 0), else_=1),
            desc(SeedLot.acquisition_date_year).nulls_last(),
            desc(SeedLot.acquisition_date_month).nulls_last(),
            desc(SeedLot.acquisition_date_day).nulls_last(),
            func.lower(BotanicalIdentity.scientific_name),
            SeedLot.id,
        )
    )


def _linked_plants_statement() -> Select[tuple[Plant, BotanicalIdentity]]:
    return (
        select(Plant, BotanicalIdentity)
        .join(BotanicalIdentity, BotanicalIdentity.id == Plant.botanical_identity_id)
        .order_by(
            case((Plant.lifecycle == "active", 0), else_=1),
            desc(Plant.collection_entry_date_year).nulls_last(),
            desc(Plant.collection_entry_date_month).nulls_last(),
            desc(Plant.collection_entry_date_day).nulls_last(),
            func.lower(BotanicalIdentity.scientific_name),
            Plant.id,
        )
    )


def _linked_plant_groups_statement() -> Select[tuple[PlantGroup, BotanicalIdentity]]:
    return (
        select(PlantGroup, BotanicalIdentity)
        .join(BotanicalIdentity, BotanicalIdentity.id == PlantGroup.botanical_identity_id)
        .order_by(
            case((PlantGroup.lifecycle == "active", 0), else_=1),
            desc(PlantGroup.collection_entry_date_year).nulls_last(),
            desc(PlantGroup.collection_entry_date_month).nulls_last(),
            desc(PlantGroup.collection_entry_date_day).nulls_last(),
            func.lower(BotanicalIdentity.scientific_name),
            PlantGroup.id,
        )
    )


def get_supplier_detail(database: Session, supplier: Supplier) -> SupplierDetailResponse:
    counts = _count_expressions()
    count_row = database.execute(
        select(
            counts.seed_lots_active,
            counts.seed_lots_total,
            counts.plants_active,
            counts.plants_total,
            counts.plant_groups_active,
            counts.plant_groups_total,
        ).where(Supplier.id == supplier.id)
    ).one()
    seed_rows = database.execute(
        _linked_seed_lots_statement().where(SeedLot.supplier_id == supplier.id)
    ).tuples()
    plant_rows = database.execute(
        _linked_plants_statement().where(Plant.supplier_id == supplier.id)
    ).tuples()
    group_rows = database.execute(
        _linked_plant_groups_statement().where(PlantGroup.supplier_id == supplier.id)
    ).tuples()

    seed_lots = [
        SupplierSeedLotLink(
            id=record.id,
            label=record.label,
            botanical_identity=_identity_summary(identity),
            lifecycle=record.lifecycle,
            acquisition_date=_partial_date(record, "acquisition_date"),
        )
        for record, identity in seed_rows
    ]
    plants = [
        SupplierPlantLink(
            id=record.id,
            label=record.label,
            botanical_identity=_identity_summary(identity),
            lifecycle=record.lifecycle,
            collection_entry_date=_partial_date(record, "collection_entry_date"),
        )
        for record, identity in plant_rows
    ]
    plant_groups = [
        SupplierPlantGroupLink(
            id=record.id,
            label=record.label,
            botanical_identity=_identity_summary(identity),
            lifecycle=record.lifecycle,
            collection_entry_date=_partial_date(record, "collection_entry_date"),
        )
        for record, identity in group_rows
    ]

    recent: list[SupplierRecentAcquisition] = []
    for record_type, links, date_field in (
        ("seed_lot", seed_lots, "acquisition_date"),
        ("plant", plants, "collection_entry_date"),
        ("plant_group", plant_groups, "collection_entry_date"),
    ):
        for link in links:
            acquired_on = getattr(link, date_field)
            if acquired_on is not None:
                recent.append(
                    SupplierRecentAcquisition(
                        record_type=record_type,
                        id=link.id,
                        label=link.label,
                        botanical_identity=link.botanical_identity,
                        lifecycle=link.lifecycle,
                        acquired_on=acquired_on,
                    )
                )
    recent.sort(
        key=lambda item: (
            -item.acquired_on.year,
            -(item.acquired_on.month or 0),
            -(item.acquired_on.day or 0),
            item.record_type,
            str(item.id),
        )
    )
    return SupplierDetailResponse(
        **SupplierResponse.from_model(supplier).model_dump(),
        usage_counts=_usage_counts(tuple(count_row)),
        seed_lots=seed_lots,
        plants=plants,
        plant_groups=plant_groups,
        recent_acquisitions=recent[:5],
    )


def update_supplier(database: Session, supplier: Supplier, payload: SupplierUpdate) -> Supplier:
    for field, value in payload.model_dump(mode="json").items():
        setattr(supplier, field, value)
    supplier.updated_at = datetime.now(UTC)
    database.flush()
    return supplier


def set_supplier_retired(database: Session, supplier: Supplier, *, retired: bool) -> Supplier:
    now = datetime.now(UTC)
    supplier.retired_at = now if retired else None
    supplier.updated_at = now
    database.flush()
    return supplier
