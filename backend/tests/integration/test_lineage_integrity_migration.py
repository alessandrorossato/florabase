"""PostgreSQL graph-write safety, migration preservation, and receipt reference guards."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Event as ThreadEvent
from time import monotonic, sleep
from uuid import UUID, uuid7

import pytest
from alembic.config import Config
from psycopg.errors import CheckViolation
from sqlalchemy import Connection, Engine, delete, insert, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.events.schemas import TransferCreate
from florabase.events.service import transfer_target
from florabase.plants.model import Plant
from florabase.plants.schemas import PlantExtractionCreate
from florabase.plants.service import extract_plant
from florabase.propagation.schemas import PlantFromSowingCreate, PlantGroupFromSowingCreate
from florabase.propagation.service import create_plant_from_sowing, create_plant_group_from_sowing
from florabase.reversals.model import OperationReceipt
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing
from integration.test_lineage_integrity import path, root

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("kind", ["plant", "plant_group"])
def test_cached_origin_cannot_reattach_result_to_concurrently_reversed_sowing(
    database_engine: Engine, kind: str
) -> None:
    from florabase.plants.model import PlantGroup
    from florabase.plants.schemas import (
        PlantCreate,
        PlantGroupCreate,
        PlantGroupUpdate,
        PlantUpdate,
    )
    from florabase.plants.service import (
        PlantDomainConflictError,
        create_plant,
        create_plant_group,
        update_plant,
        update_plant_group,
    )
    from florabase.propagation.reversal import reverse

    ids: dict[str, UUID] = {}
    model = Plant if kind == "plant" else PlantGroup
    try:
        with Session(database_engine) as db:
            identity, lot, sowing = root(db)
            other = Sowing(seed_lot_id=lot.id)
            db.add(other)
            db.flush()
            values = {"botanical_identity_id": identity.id, "originating_sowing_id": sowing.id}
            result = (
                create_plant(db, PlantCreate.model_validate(values))
                if kind == "plant"
                else create_plant_group(db, PlantGroupCreate.model_validate(values))
            )
            ids = {
                "identity": identity.id,
                "lot": lot.id,
                "sowing": sowing.id,
                "other": other.id,
                "result": result.id,
            }
            db.commit()
        with Session(database_engine) as stale:
            cached = stale.get(model, ids["result"])
            assert isinstance(cached, (Plant, PlantGroup))
            assert cached.originating_sowing_id == ids["sowing"]
            with Session(database_engine) as winner:
                current = winner.get(model, ids["result"])
                assert isinstance(current, (Plant, PlantGroup))
                values = {
                    "botanical_identity_id": ids["identity"],
                    "originating_sowing_id": ids["other"],
                }
                if isinstance(current, Plant):
                    update_plant(winner, current, PlantUpdate.model_validate(values))
                else:
                    update_plant_group(winner, current, PlantGroupUpdate.model_validate(values))
                reverse(winner, "sowing", ids["sowing"], confirm=False)
                winner.commit()
            values["originating_sowing_id"] = ids["sowing"]
            if isinstance(cached, Plant):
                with pytest.raises(PlantDomainConflictError) as rejected:
                    update_plant(stale, cached, PlantUpdate.model_validate(values))
            else:
                with pytest.raises(PlantDomainConflictError) as rejected:
                    update_plant_group(stale, cached, PlantGroupUpdate.model_validate(values))
            assert rejected.value.code == "reversed_sowing_is_historical"
            stale.rollback()
        with Session(database_engine) as db:
            retained = db.get(model, ids["result"])
            historical = db.get(Sowing, ids["sowing"])
            assert isinstance(retained, (Plant, PlantGroup))
            assert retained.originating_sowing_id == ids["other"]
            assert historical is not None
            assert historical.lifecycle == "reversed"
    finally:
        if ids:
            with database_engine.begin() as conn:
                conn.execute(
                    delete(OperationReceipt).where(OperationReceipt.sowing_id == ids["sowing"])
                )
                conn.execute(delete(model).where(model.id == ids["result"]))
                conn.execute(delete(Sowing).where(Sowing.id.in_([ids["sowing"], ids["other"]])))
                conn.execute(delete(SeedLot).where(SeedLot.id == ids["lot"]))
                conn.execute(
                    delete(BotanicalIdentity).where(BotanicalIdentity.id == ids["identity"])
                )


def constraint_name(error: IntegrityError) -> str | None:
    if not isinstance(error.orig, CheckViolation):
        raise error
    return error.orig.diag.constraint_name


@pytest.mark.parametrize(
    "edge", ["producer_plant", "producer_group", "sowing", "plant", "group", "extraction"]
)
def test_database_rejects_cycles_on_every_concrete_edge(
    database_connection: Connection, edge: str
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity, lot, sowing = root(db)
        group, _ = create_plant_group_from_sowing(
            db, sowing.id, PlantGroupFromSowingCreate(botanical_identity_id=identity.id), "active"
        )
        plant, _ = create_plant_from_sowing(
            db, sowing.id, PlantFromSowingCreate(botanical_identity_id=identity.id), "active"
        )
        if edge.startswith("producer"):
            column = "producer_plant_id" if edge == "producer_plant" else "producer_plant_group_id"
            table, item_id, source_id = (
                "seed_lots",
                lot.id,
                plant.id if edge == "producer_plant" else group.id,
            )
            assignments = f"{column}=:source, source_kind='collection_produced'"
        else:
            produced = SeedLot(
                botanical_identity_id=identity.id,
                source_kind="collection_produced",
                producer_plant_id=plant.id if edge in {"plant", "extraction"} else None,
                producer_plant_group_id=group.id if edge in {"sowing", "group"} else None,
            )
            db.add(produced)
            db.flush()
            descendant = Sowing(seed_lot_id=produced.id)
            db.add(descendant)
            db.flush()
            if edge == "sowing":
                table, item_id, source_id = "sowings", sowing.id, produced.id
                assignments = "seed_lot_id=:source"
            elif edge == "group":
                table, item_id, source_id = "plant_groups", group.id, descendant.id
                assignments = "originating_sowing_id=:source"
            elif edge == "plant":
                table, item_id, source_id = "plants", plant.id, descendant.id
                assignments = "originating_sowing_id=:source"
            else:
                child_group, _ = create_plant_group_from_sowing(
                    db,
                    descendant.id,
                    PlantGroupFromSowingCreate(botanical_identity_id=identity.id),
                    "active",
                )
                table, item_id, source_id = "plants", plant.id, child_group.id
                assignments = "originating_sowing_id=NULL, originating_plant_group_id=:source"
        before = path(db, ("plant", plant.id))
        with pytest.raises(IntegrityError) as rejected, db.begin_nested():
            db.execute(
                text(f"UPDATE {table} SET {assignments} WHERE id=:id"),
                {"id": item_id, "source": source_id},
            )
        assert constraint_name(rejected.value) == "ck_collection_lineage_acyclic"
        assert path(db, ("plant", plant.id)) == before


@pytest.mark.parametrize(
    "kind",
    [
        "seed_lot_to_sowing",
        "sowing_to_plant",
        "sowing_to_plant_group",
        "plant_group_extraction",
        "plant_transfer",
        "plant_group_transfer",
    ],
)
def test_new_receipt_cannot_reference_unrelated_source_result_or_event(
    database_connection: Connection, kind: str
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity, _, sowing = root(db)
        _, unrelated_lot, unrelated_sowing = root(db)
        plant, _ = create_plant_from_sowing(
            db, sowing.id, PlantFromSowingCreate(botanical_identity_id=identity.id), "active"
        )
        group, _ = create_plant_group_from_sowing(
            db, sowing.id, PlantGroupFromSowingCreate(botanical_identity_id=identity.id), "active"
        )
        extracted, _, _ = extract_plant(db, group.id, PlantExtractionCreate())
        transfer_target(db, "plant", plant.id, TransferCreate())
        transfer_target(db, "plant_group", group.id, TransferCreate())
        receipt = db.scalars(select(OperationReceipt).where(OperationReceipt.kind == kind)).first()
        assert receipt is not None
        values = {
            column.name: getattr(receipt, column.name)
            for column in OperationReceipt.__table__.columns
        }
        values["id"] = uuid7()
        if kind == "seed_lot_to_sowing":
            values["seed_lot_id"] = unrelated_lot.id
        elif kind in {"sowing_to_plant", "sowing_to_plant_group"}:
            values["sowing_id"] = unrelated_sowing.id
        elif kind == "plant_group_transfer":
            values["event_id"] = db.scalar(
                select(OperationReceipt.event_id).where(OperationReceipt.kind == "plant_transfer")
            )
        elif kind == "plant_transfer":
            values["plant_id"] = extracted.id
        else:
            values["plant_id"] = plant.id
        with pytest.raises(IntegrityError) as rejected, db.begin_nested():
            db.execute(insert(OperationReceipt).values(**values))
        assert constraint_name(rejected.value) == "ck_operation_receipts_relationships"
        assert db.get(OperationReceipt, receipt.id) is receipt


def test_lineage_migration_preserves_records_and_refuses_existing_cycles(
    database_engine: Engine,
) -> None:
    config = Config("alembic.ini")
    ids: dict[str, UUID] = {}
    try:
        with Session(database_engine) as db:
            identity, lot, sowing = root(db)
            plant, _ = create_plant_from_sowing(
                db, sowing.id, PlantFromSowingCreate(botanical_identity_id=identity.id), "active"
            )
            ids = {"identity": identity.id, "lot": lot.id, "sowing": sowing.id, "plant": plant.id}
            before = path(db, ("plant", plant.id))
            snapshots = [
                tuple(getattr(r, c.name) for c in OperationReceipt.__table__.columns)
                for r in db.scalars(select(OperationReceipt).order_by(OperationReceipt.id))
            ]
            db.commit()
        command.downgrade(config, "20261001_0029")
        command.upgrade(config, "head")
        with Session(database_engine) as db:
            assert path(db, ("plant", ids["plant"])) == before
            assert [
                tuple(getattr(r, c.name) for c in OperationReceipt.__table__.columns)
                for r in db.scalars(select(OperationReceipt).order_by(OperationReceipt.id))
            ] == snapshots
        command.downgrade(config, "20261001_0029")
        with database_engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE seed_lots SET source_kind='collection_produced', "
                    "producer_plant_id=:plant WHERE id=:lot"
                ),
                ids,
            )
        with pytest.raises(Exception, match="existing collection lineage contains a cycle"):
            command.upgrade(config, "head")
        with database_engine.begin() as conn:
            assert (
                conn.execute(
                    text("SELECT producer_plant_id FROM seed_lots WHERE id=:lot"), ids
                ).scalar_one()
                == ids["plant"]
            )
            conn.execute(text("UPDATE seed_lots SET producer_plant_id=NULL WHERE id=:lot"), ids)
        command.upgrade(config, "head")
    finally:
        # Remove only this fixture's committed data, using the existing disposable DB contract.
        command.upgrade(config, "head")
        if ids:
            with database_engine.begin() as conn:
                conn.execute(
                    delete(OperationReceipt).where(OperationReceipt.sowing_id == ids["sowing"])
                )
                conn.execute(delete(Plant).where(Plant.id == ids["plant"]))
                conn.execute(delete(Sowing).where(Sowing.id == ids["sowing"]))
                conn.execute(delete(SeedLot).where(SeedLot.id == ids["lot"]))
                conn.execute(
                    delete(BotanicalIdentity).where(BotanicalIdentity.id == ids["identity"])
                )


def test_competing_producer_assignments_serialize_before_cycle_check(
    database_engine: Engine,
) -> None:
    ids: list[tuple[UUID, UUID, UUID, UUID]] = []
    try:
        with Session(database_engine) as db:
            for _ in range(2):
                identity, lot, sowing = root(db)
                plant, _ = create_plant_from_sowing(
                    db,
                    sowing.id,
                    PlantFromSowingCreate(botanical_identity_id=identity.id),
                    "active",
                )
                ids.append((identity.id, lot.id, sowing.id, plant.id))
            db.commit()
        begun = ThreadEvent()

        def competitor() -> str:
            try:
                with database_engine.begin() as conn:
                    conn.execute(text("SET LOCAL lock_timeout = '5s'"))
                    begun.set()
                    conn.execute(
                        text(
                            "UPDATE seed_lots SET source_kind='collection_produced', "
                            "producer_plant_id=:plant WHERE id=:lot"
                        ),
                        {"lot": ids[1][1], "plant": ids[0][3]},
                    )
                return "applied"
            except IntegrityError as error:
                return constraint_name(error) or "unknown_constraint"

        with ThreadPoolExecutor(max_workers=1) as pool:
            with database_engine.begin() as conn:
                conn.execute(
                    text(
                        "UPDATE seed_lots SET source_kind='collection_produced', "
                        "producer_plant_id=:plant WHERE id=:lot"
                    ),
                    {"lot": ids[0][1], "plant": ids[1][3]},
                )
                future = pool.submit(competitor)
                assert begun.wait(3)
                # Observe the second backend waiting on the graph lock, not a timing guess.
                waiting = False
                deadline = monotonic() + 2
                while monotonic() < deadline:
                    conn.execute(text("SELECT pg_stat_clear_snapshot()"))
                    waiting = bool(
                        conn.execute(
                            text(
                                "SELECT count(*) FROM pg_stat_activity "
                                "WHERE datname=current_database() AND wait_event='advisory' "
                                "AND pid<>pg_backend_pid()"
                            )
                        ).scalar_one()
                    )
                    if waiting:
                        break
                    sleep(0.01)
                assert waiting
            assert future.result(timeout=6) == "ck_collection_lineage_acyclic"
        with Session(database_engine) as db:
            assert path(db, ("plant", ids[0][3])) == [
                ("sowing", ids[0][2]),
                ("seed_lot", ids[0][1]),
                ("plant", ids[1][3]),
                ("sowing", ids[1][2]),
                ("seed_lot", ids[1][1]),
            ]
    finally:
        if ids:
            with database_engine.begin() as conn:
                conn.execute(
                    text("UPDATE seed_lots SET producer_plant_id=NULL WHERE id IN (:a,:b)"),
                    {"a": ids[0][1], "b": ids[-1][1]},
                )
                for identity_id, lot_id, sowing_id, plant_id in ids:
                    conn.execute(
                        delete(OperationReceipt).where(OperationReceipt.sowing_id == sowing_id)
                    )
                    conn.execute(delete(Plant).where(Plant.id == plant_id))
                    conn.execute(delete(Sowing).where(Sowing.id == sowing_id))
                    conn.execute(delete(SeedLot).where(SeedLot.id == lot_id))
                    conn.execute(
                        delete(BotanicalIdentity).where(BotanicalIdentity.id == identity_id)
                    )


@pytest.mark.parametrize("isolation", ["REPEATABLE READ", "SERIALIZABLE"])
def test_graph_writes_refuse_stale_snapshot_isolation(
    database_engine: Engine, isolation: str
) -> None:
    with (
        database_engine.connect().execution_options(isolation_level=isolation) as conn,
        pytest.raises(DBAPIError, match="require READ COMMITTED"),
        conn.begin(),
    ):
        conn.execute(text("UPDATE sowings SET seed_lot_id=seed_lot_id WHERE false"))


@pytest.mark.parametrize("operation", ["extraction", "reintegration", "seed_use"])
def test_locked_operations_refresh_records_loaded_before_a_competing_commit(
    database_engine: Engine, operation: str
) -> None:
    from florabase.events.model import Event
    from florabase.plants.model import PlantGroup
    from florabase.plants.service import PlantDomainConflictError, evaluate_reintegration
    from florabase.propagation.schemas import SeedLotSowingTransitionCreate
    from florabase.propagation.service import PropagationConflictError, create_sowing_from_seed_lot

    ids: dict[str, UUID] = {}
    try:
        with Session(database_engine) as db:
            identity, lot, sowing = root(db)
            group, _ = create_plant_group_from_sowing(
                db,
                sowing.id,
                PlantGroupFromSowingCreate.model_validate(
                    {
                        "botanical_identity_id": identity.id,
                        "quantity": {"value": 1, "is_approximate": False},
                    }
                ),
                "active",
            )
            ids = {"identity": identity.id, "lot": lot.id, "sowing": sowing.id, "group": group.id}
            if operation == "reintegration":
                extracted, _, _ = extract_plant(db, group.id, PlantExtractionCreate())
                ids["plant"] = extracted.id
            db.commit()
        with Session(database_engine) as stale:
            loaded_group = stale.get(PlantGroup, ids["group"])
            loaded_lot = stale.get(SeedLot, ids["lot"])
            assert loaded_group is not None
            assert loaded_lot is not None
            if operation == "reintegration":
                loaded_plant = stale.get(Plant, ids["plant"])
                assert loaded_plant is not None
            with Session(database_engine) as winner:
                if operation == "extraction":
                    extracted, _, _ = extract_plant(winner, ids["group"], PlantExtractionCreate())
                    ids["plant"] = extracted.id
                elif operation == "reintegration":
                    current = winner.get(PlantGroup, ids["group"])
                    assert current is not None
                    current.lifecycle, current.quantity_value = "active", 3
                else:
                    current_lot = winner.get(SeedLot, ids["lot"])
                    assert current_lot is not None
                    current_lot.quantity_value = Decimal(30)
                winner.commit()
            if operation == "extraction":
                with pytest.raises(PlantDomainConflictError) as rejected:
                    extract_plant(stale, ids["group"], PlantExtractionCreate())
                assert rejected.value.code == "plant_group_not_active"
            elif operation == "reintegration":
                evaluation = evaluate_reintegration(stale, ids["plant"], lock=True)
                assert evaluation.status == "blocked"
                assert any(reason.code == "source_group_changed" for reason in evaluation.reasons)
            else:
                with pytest.raises(PropagationConflictError) as rejected_use:
                    create_sowing_from_seed_lot(
                        stale,
                        ids["lot"],
                        SeedLotSowingTransitionCreate.model_validate(
                            {
                                "sowing": {
                                    "quantity": {
                                        "kind": "seed_count",
                                        "value": 40,
                                        "is_approximate": False,
                                    }
                                },
                                "source_adjustment": {"mode": "partial"},
                            }
                        ),
                    )
                assert rejected_use.value.code == "seed_lot_quantity_exceeded"
            stale.rollback()
    finally:
        if ids:
            with database_engine.begin() as conn:
                conn.execute(
                    delete(OperationReceipt).where(OperationReceipt.sowing_id == ids["sowing"])
                )
                conn.execute(
                    delete(OperationReceipt).where(OperationReceipt.plant_group_id == ids["group"])
                )
                conn.execute(delete(Event).where(Event.plant_group_id == ids["group"]))
                conn.execute(delete(Plant).where(Plant.originating_plant_group_id == ids["group"]))
                conn.execute(delete(PlantGroup).where(PlantGroup.id == ids["group"]))
                conn.execute(delete(Sowing).where(Sowing.id == ids["sowing"]))
                conn.execute(delete(SeedLot).where(SeedLot.id == ids["lot"]))
                conn.execute(
                    delete(BotanicalIdentity).where(BotanicalIdentity.id == ids["identity"])
                )
