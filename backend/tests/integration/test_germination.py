from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from threading import Event
from uuid import uuid7

import pytest
from alembic.config import Config
from sqlalchemy import Connection, Engine, delete, inspect, select, text
from sqlalchemy.orm import Session

from alembic import command
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.seed_lots.model import SeedLot
from florabase.sowings.germination_schemas import GerminationObservationWrite
from florabase.sowings.germination_service import (
    GerminationConflictError,
    create_observation,
    germination_detail,
)
from florabase.sowings.model import GerminationObservation, Sowing
from florabase.sowings.schemas import SowingUpdate
from florabase.sowings.service import SowingDomainConflictError, update_sowing

pytestmark = pytest.mark.integration


def test_germination_migration_upgrade_downgrade_reupgrade(database_engine: Engine) -> None:
    config = Config("alembic.ini")
    try:
        command.downgrade(config, "20260913_0024")
        assert not inspect(database_engine).has_table("germination_observations")
        command.upgrade(config, "head")
        inspector = inspect(database_engine)
        assert inspector.has_table("germination_observations")
        assert {
            item["name"] for item in inspector.get_unique_constraints("germination_observations")
        } == {"uq_germination_observations_sowing_date"}
        command.downgrade(config, "20260913_0024")
        assert not inspect(database_engine).has_table("germination_observations")
    finally:
        command.upgrade(config, "head")


def test_observation_bound_and_sowing_edit_use_same_parent_lock(
    database_connection: Connection,
) -> None:
    identity_id, lot_id, sowing_id = uuid7(), uuid7(), uuid7()
    database_connection.execute(
        text(
            "INSERT INTO botanical_identities "
            "(id, scientific_name, created_at, updated_at) "
            "VALUES (:id, 'Germination test', now(), now())"
        ),
        {"id": identity_id},
    )
    database_connection.execute(
        text(
            "INSERT INTO seed_lots "
            "(id, botanical_identity_id, created_at, updated_at) "
            "VALUES (:id, :lot, now(), now())"
        ),
        {"id": lot_id, "lot": identity_id},
    )
    database_connection.execute(
        text(
            "INSERT INTO sowings (id, seed_lot_id, sowing_date_precision, "
            "sowing_date_year, sowing_date_month, sowing_date_day, quantity_kind, "
            "quantity_value, quantity_is_approximate, germinated_count, "
            "lifecycle, created_at, updated_at) VALUES (:id, :lot, 'day', "
            "2026, 4, 10, 'seed_count', 20, false, 12, 'active', now(), now())"
        ),
        {"id": sowing_id, "lot": lot_id},
    )
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        observation = create_observation(
            database,
            sowing_id,
            GerminationObservationWrite(observed_on=date(2026, 4, 14), newly_germinated_count=12),
        )
        assert observation is not None
        assert germination_detail(database, sowing_id).summary.observed_cumulative_count == 12  # type: ignore[union-attr]
        with pytest.raises(GerminationConflictError, match="exceed"):
            create_observation(
                database,
                sowing_id,
                GerminationObservationWrite(
                    observed_on=date(2026, 4, 15), newly_germinated_count=9
                ),
            )
        sowing = database.get(Sowing, sowing_id)
        assert sowing is not None
        with pytest.raises(SowingDomainConflictError, match="exceed"):
            update_sowing(
                database,
                sowing,
                SowingUpdate(
                    seed_lot_id=lot_id,
                    sowing_date={"precision": "day", "year": 2026, "month": 4, "day": 10},
                    quantity={
                        "kind": "seed_count",
                        "value": Decimal("10"),
                        "is_approximate": False,
                    },
                    germinated_count=10,
                ),
            )


def test_concurrent_observation_writes_serialize_on_sowing_row(database_engine: Engine) -> None:
    identity_id, lot_id, sowing_id = uuid7(), uuid7(), uuid7()
    first_observation_id = uuid7()
    with Session(database_engine) as database:
        identity = BotanicalIdentity(id=identity_id, scientific_name="Concurrent germination test")
        lot = SeedLot(id=lot_id, botanical_identity_id=identity_id)
        sowing = Sowing(
            id=sowing_id,
            seed_lot_id=lot_id,
            sowing_date_precision="day",
            sowing_date_year=2026,
            sowing_date_month=4,
            sowing_date_day=10,
            quantity_kind="seed_count",
            quantity_value=Decimal("10"),
            quantity_is_approximate=False,
            lifecycle="active",
        )
        database.add(identity)
        database.flush()
        database.add(lot)
        database.flush()
        database.add(sowing)
        database.flush()
        database.add(
            GerminationObservation(
                id=first_observation_id,
                sowing_id=sowing_id,
                observed_on=date(2026, 4, 11),
                newly_germinated_count=8,
            )
        )
        database.commit()

    first_has_written = Event()
    release_first = Event()
    second_started = Event()

    def first_write() -> None:
        with Session(database_engine) as database, database.begin():
            create_observation(
                database,
                sowing_id,
                GerminationObservationWrite(
                    observed_on=date(2026, 4, 12), newly_germinated_count=2
                ),
            )
            first_has_written.set()
            assert release_first.wait(timeout=10)

    def second_write() -> GerminationConflictError | None:
        second_started.set()
        with Session(database_engine) as database, database.begin():
            try:
                create_observation(
                    database,
                    sowing_id,
                    GerminationObservationWrite(
                        observed_on=date(2026, 4, 13), newly_germinated_count=2
                    ),
                )
            except GerminationConflictError as error:
                return error
        return None

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(first_write)
            assert first_has_written.wait(timeout=10)
            second = executor.submit(second_write)
            assert second_started.wait(timeout=10)
            release_first.set()
            first.result(timeout=10)
            conflict = second.result(timeout=10)
        assert conflict is not None
        assert conflict.code == "observations_exceed_seeds"
        with Session(database_engine) as database:
            observations = list(
                database.scalars(
                    select(GerminationObservation)
                    .where(GerminationObservation.sowing_id == sowing_id)
                    .order_by(GerminationObservation.observed_on)
                )
            )
        assert [item.newly_germinated_count for item in observations] == [8, 2]
    finally:
        with Session(database_engine) as database:
            database.execute(
                delete(GerminationObservation).where(GerminationObservation.sowing_id == sowing_id)
            )
            database.execute(delete(Sowing).where(Sowing.id == sowing_id))
            database.execute(delete(SeedLot).where(SeedLot.id == lot_id))
            database.execute(delete(BotanicalIdentity).where(BotanicalIdentity.id == identity_id))
            database.commit()
