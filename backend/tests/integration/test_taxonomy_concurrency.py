from collections.abc import Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, date, datetime
from queue import Queue
from threading import Barrier, Event
from time import monotonic, sleep
from unittest.mock import patch
from uuid import UUID, uuid7

import pytest
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

import florabase.main  # noqa: F401
from florabase.botanical_identities.model import BotanicalIdentity, BotanicalIdentityName
from florabase.botanical_identities.reconciliation import (
    ReconciliationConflictError,
    correct_accepted_name,
    merge_duplicate_identity,
)
from florabase.botanical_identities.schemas import (
    AcceptedNameCorrectionWrite,
    BotanicalIdentityCreate,
    BotanicalIdentityUpdate,
    DuplicateIdentityMergeWrite,
    OperatorSynonymCreate,
)
from florabase.botanical_identities.service import (
    BotanicalIdentityConflictError,
    BotanicalIdentityMergedError,
    add_operator_synonym,
    create_botanical_identity,
    find_duplicate,
    update_botanical_identity,
)
from florabase.plants.model import DirectOriginKind, Plant, PlantLifecycle
from florabase.plants.schemas import PlantCreate, PlantUpdate
from florabase.plants.service import (
    PlantReferenceNotFoundError,
    create_plant,
    get_plant,
    update_plant,
)
from florabase.schedule.model import ScheduledActivity
from florabase.schedule.schemas import ScheduleTarget, ScheduleUpdate
from florabase.schedule.service import ScheduleError
from florabase.schedule.service import update as update_scheduled_activity

pytestmark = pytest.mark.integration

_CLEANUP_TABLES = (
    "scheduled_activities",
    "events",
    "plants",
    "operation_receipts",
    "botanical_identity_reconciliations",
    "botanical_identity_names",
    "botanical_identities",
)
_IMMUTABLE_CLEANUP_TABLES = frozenset(
    {"events", "operation_receipts", "botanical_identity_reconciliations"}
)


@pytest.fixture(autouse=True)
def _cleanup_concurrency_rows(database_engine: Engine) -> Iterator[None]:
    """Remove committed two-session test rows so later migration tests see a clean database."""
    preexisting: dict[str, set[UUID]] = {}
    with database_engine.begin() as conn:
        for table in _CLEANUP_TABLES:
            preexisting[table] = set(conn.execute(text(f"SELECT id FROM {table}")).scalars().all())
    try:
        yield
    finally:
        with database_engine.begin() as conn:
            for table in _CLEANUP_TABLES:
                current = set(conn.execute(text(f"SELECT id FROM {table}")).scalars().all())
                created_ids = list(current - preexisting[table])
                if not created_ids:
                    continue
                if table == "botanical_identities":
                    conn.execute(
                        text(
                            "DELETE FROM botanical_identities "
                            "WHERE id = ANY(:ids) AND merged_into_id IS NOT NULL"
                        ),
                        {"ids": created_ids},
                    )
                if table in _IMMUTABLE_CLEANUP_TABLES:
                    conn.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER USER"))
                try:
                    conn.execute(
                        text(f"DELETE FROM {table} WHERE id = ANY(:ids)"),
                        {"ids": created_ids},
                    )
                finally:
                    if table in _IMMUTABLE_CLEANUP_TABLES:
                        conn.execute(text(f"ALTER TABLE {table} ENABLE TRIGGER USER"))


def _wait_until_blocked(
    session_a: Session, worker_pid: int, done_check: Future[tuple[str, str]]
) -> bool:
    deadline = monotonic() + 5.0
    while monotonic() < deadline and not done_check.done():
        blocking = session_a.execute(
            text("SELECT cardinality(pg_blocking_pids(:pid))"), {"pid": worker_pid}
        ).scalar_one()
        if blocking:
            return True
        sleep(0.02)
    return False


def _assert_no_records_point_to_retired_identity(
    database: Session, retired_identity_id: UUID
) -> None:
    for table in ("plants", "plant_groups", "seed_lots", "vegetative_lots", "scheduled_activities"):
        count = database.execute(
            text(f"SELECT count(*) FROM {table} WHERE botanical_identity_id = :id"),
            {"id": retired_identity_id},
        ).scalar_one()
        assert count == 0, (
            f"{table} still has {count} rows pointing to retired {retired_identity_id}"
        )


def test_scenario1_stale_identity_map_in_plant_update_concurrent_with_merge(
    database_engine: Engine,
) -> None:
    """Scenario 1: concurrent merge commits after projection load; Plant update must fail closed."""
    with Session(database_engine) as database, database.begin():
        duplicate = BotanicalIdentity(scientific_name=f"Echinopsis dup {uuid7()}")
        survivor = BotanicalIdentity(scientific_name=f"Trichocereus surv {uuid7()}")
        database.add_all([duplicate, survivor])
        database.flush()
        plant = Plant(
            botanical_identity_id=duplicate.id,
            direct_origin_kind=DirectOriginKind.UNKNOWN.value,
            label="Specimen 1",
        )
        database.add(plant)
        database.flush()
        dup_id, surv_id, plant_id = duplicate.id, survivor.id, plant.id
        dup_updated_at, surv_updated_at = duplicate.updated_at, survivor.updated_at

    # Session A mirrors update_one_plant: _require_plant loads Plant + BotanicalIdentity first.
    with Session(database_engine) as session_a, session_a.begin():
        projection = get_plant(session_a, plant_id)
        assert projection is not None

        # Session B concurrently merges duplicate -> survivor and commits.
        with Session(database_engine) as session_b, session_b.begin():
            merge_duplicate_identity(
                session_b,
                dup_id,
                DuplicateIdentityMergeWrite(
                    survivor_identity_id=surv_id,
                    duplicate_updated_at=dup_updated_at,
                    survivor_updated_at=surv_updated_at,
                ),
            )

        # Session A now runs update_plant using projection.plant and payload targeting dup_id.
        with pytest.raises(PlantReferenceNotFoundError) as caught:
            update_plant(
                session_a,
                projection.plant,
                PlantUpdate(
                    botanical_identity_id=dup_id,
                    direct_origin_kind=DirectOriginKind.UNKNOWN,
                    label="Edited concurrently",
                    lifecycle=PlantLifecycle.ACTIVE,
                ),
            )
        assert caught.value.code == "botanical_identity_not_found"
        session_a.rollback()

    with Session(database_engine) as check_db:
        persisted_plant = check_db.get(Plant, plant_id)
        assert persisted_plant is not None
        assert persisted_plant.botanical_identity_id == surv_id
        _assert_no_records_point_to_retired_identity(check_db, dup_id)


@pytest.mark.parametrize("commit_merge", [True, False])
def test_scenario1_concurrent_plant_create_waits_for_merge_transaction(
    database_engine: Engine, commit_merge: bool
) -> None:
    """Scenario 1: concurrent Plant create blocks on uncommitted merge and follows its outcome."""
    with Session(database_engine) as database, database.begin():
        duplicate = BotanicalIdentity(scientific_name=f"Echinopsis create {uuid7()}")
        survivor = BotanicalIdentity(scientific_name=f"Trichocereus create {uuid7()}")
        database.add_all([duplicate, survivor])
        database.flush()
        dup_id, surv_id = duplicate.id, survivor.id
        dup_updated_at, surv_updated_at = duplicate.updated_at, survivor.updated_at

    worker_pids: Queue[int] = Queue()
    with ThreadPoolExecutor(max_workers=1) as executor:
        with Session(database_engine) as session_a:
            session_a.begin()
            merge_duplicate_identity(
                session_a,
                dup_id,
                DuplicateIdentityMergeWrite(
                    survivor_identity_id=surv_id,
                    duplicate_updated_at=dup_updated_at,
                    survivor_updated_at=surv_updated_at,
                ),
            )

            def create_plant_worker() -> tuple[str, str]:
                with Session(database_engine) as session_b:
                    session_b.begin()
                    session_b.execute(text("SET LOCAL lock_timeout = '10s'"))
                    worker_pids.put(session_b.execute(text("SELECT pg_backend_pid()")).scalar_one())
                    try:
                        plant = create_plant(
                            session_b,
                            PlantCreate(
                                botanical_identity_id=dup_id,
                                direct_origin_kind=DirectOriginKind.UNKNOWN,
                                label="Concurrent Specimen",
                            ),
                        )
                        session_b.commit()
                        return ("created", str(plant.id))
                    except PlantReferenceNotFoundError as error:
                        session_b.rollback()
                        return ("rejected", error.code)

            future = executor.submit(create_plant_worker)
            worker_pid = worker_pids.get(timeout=5)
            blocked = _wait_until_blocked(session_a, worker_pid, future)
            assert blocked, "create_plant did not block on uncommitted merge"

            if commit_merge:
                session_a.commit()
            else:
                session_a.rollback()

        kind, detail = future.result(timeout=5)
        if commit_merge:
            assert (kind, detail) == ("rejected", "botanical_identity_not_found")
            with Session(database_engine) as check_db:
                _assert_no_records_point_to_retired_identity(check_db, dup_id)
        else:
            assert kind == "created"
            with Session(database_engine) as check_db:
                created_plant = check_db.get(Plant, UUID(detail))
                assert created_plant is not None
                assert created_plant.botanical_identity_id == dup_id


def test_scenario1_schedule_update_concurrent_with_merge_no_deadlock_or_retired_target(
    database_engine: Engine,
) -> None:
    """Scenario 1: concurrent schedule update waits without deadlock and rejects retired target."""
    with Session(database_engine) as database, database.begin():
        duplicate = BotanicalIdentity(scientific_name=f"Echinopsis sched {uuid7()}")
        survivor = BotanicalIdentity(scientific_name=f"Trichocereus sched {uuid7()}")
        database.add_all([duplicate, survivor])
        database.flush()
        activity = ScheduledActivity(
            title="Inspect specimen",
            activity_kind="inspect",
            status="planned",
            due_on=date(2026, 7, 1),
            botanical_identity_id=duplicate.id,
        )
        database.add(activity)
        database.flush()
        dup_id, surv_id, activity_id = duplicate.id, survivor.id, activity.id
        dup_updated_at, surv_updated_at = duplicate.updated_at, survivor.updated_at
        activity_version = activity.version

    worker_pids: Queue[int] = Queue()
    with ThreadPoolExecutor(max_workers=1) as executor:
        with Session(database_engine) as session_a, session_a.begin():
            merge_duplicate_identity(
                session_a,
                dup_id,
                DuplicateIdentityMergeWrite(
                    survivor_identity_id=surv_id,
                    duplicate_updated_at=dup_updated_at,
                    survivor_updated_at=surv_updated_at,
                ),
            )

            def update_schedule_worker() -> tuple[str, str]:
                with Session(database_engine) as session_b:
                    session_b.begin()
                    session_b.execute(text("SET LOCAL lock_timeout = '10s'"))
                    worker_pids.put(session_b.execute(text("SELECT pg_backend_pid()")).scalar_one())
                    try:
                        update_scheduled_activity(
                            session_b,
                            activity_id,
                            ScheduleUpdate(
                                activity_kind="inspect",
                                title="Updated concurrently",
                                due_on=date(2026, 7, 2),
                                target=ScheduleTarget(kind="botanical_identity", id=dup_id),
                                expected_version=activity_version,
                            ),
                        )
                        session_b.commit()
                        return ("updated", "")
                    except ScheduleError as error:
                        session_b.rollback()
                        return ("rejected", error.code)

            future = executor.submit(update_schedule_worker)
            worker_pid = worker_pids.get(timeout=5)
            blocked = _wait_until_blocked(session_a, worker_pid, future)
            assert blocked, "schedule.update did not synchronize on uncommitted merge"

        kind, detail = future.result(timeout=5)
        assert (kind, detail) == ("rejected", "schedule_target_missing")

    with Session(database_engine) as check_db:
        persisted_activity = check_db.get(ScheduledActivity, activity_id)
        assert persisted_activity is not None
        assert persisted_activity.botanical_identity_id == surv_id
        _assert_no_records_point_to_retired_identity(check_db, dup_id)


@pytest.mark.parametrize("commit_merge", [True, False])
def test_scenario2_create_identity_concurrent_with_uncommitted_merge(
    database_engine: Engine, commit_merge: bool
) -> None:
    """Scenario 2: create_botanical_identity blocks on uncommitted merge and follows its outcome."""
    dup_name = f"Echinopsis race {uuid7()}"
    surv_name = f"Trichocereus race {uuid7()}"
    with Session(database_engine) as database, database.begin():
        duplicate = BotanicalIdentity(scientific_name=dup_name)
        survivor = BotanicalIdentity(scientific_name=surv_name)
        database.add_all([duplicate, survivor])
        database.flush()
        dup_id, surv_id = duplicate.id, survivor.id
        dup_updated_at, surv_updated_at = duplicate.updated_at, survivor.updated_at

    worker_pids: Queue[int] = Queue()
    with ThreadPoolExecutor(max_workers=1) as executor:
        with Session(database_engine) as session_a:
            session_a.begin()
            merge_duplicate_identity(
                session_a,
                dup_id,
                DuplicateIdentityMergeWrite(
                    survivor_identity_id=surv_id,
                    duplicate_updated_at=dup_updated_at,
                    survivor_updated_at=surv_updated_at,
                ),
            )

            def create_worker() -> tuple[str, str]:
                with Session(database_engine) as session_b:
                    session_b.begin()
                    session_b.execute(text("SET LOCAL lock_timeout = '10s'"))
                    worker_pids.put(session_b.execute(text("SELECT pg_backend_pid()")).scalar_one())
                    try:
                        created = create_botanical_identity(
                            session_b,
                            BotanicalIdentityCreate(scientific_name=dup_name),
                        )
                        session_b.commit()
                        return ("created", str(created.id))
                    except BotanicalIdentityConflictError as error:
                        session_b.rollback()
                        return ("conflict", str(error.existing_id))

            future = executor.submit(create_worker)
            worker_pid = worker_pids.get(timeout=5)
            blocked = _wait_until_blocked(session_a, worker_pid, future)
            assert blocked, "create_botanical_identity did not wait on uncommitted merge"

            if commit_merge:
                session_a.commit()
            else:
                session_a.rollback()

        kind, detail = future.result(timeout=5)
        with Session(database_engine) as check_db:
            if commit_merge:
                assert kind == "created"
                new_id = UUID(detail)
                assert new_id != dup_id
                created_row = check_db.get(BotanicalIdentity, new_id)
                retired_row = check_db.get(BotanicalIdentity, dup_id)
                assert created_row is not None
                assert created_row.merged_into_id is None
                assert retired_row is not None
                assert retired_row.merged_into_id == surv_id
            else:
                assert (kind, detail) == ("conflict", str(dup_id))
                still_active = check_db.scalar(
                    select(BotanicalIdentity).where(BotanicalIdentity.id == dup_id)
                )
                assert still_active is not None
                assert still_active.merged_into_id is None


def test_scenario2_update_identity_concurrent_with_uncommitted_merge_commits(
    database_engine: Engine,
) -> None:
    """Scenario 2 companion: update_botanical_identity waits on merge and raises MergedError."""
    dup_name = f"Echinopsis upd {uuid7()}"
    surv_name = f"Trichocereus upd {uuid7()}"
    with Session(database_engine) as database, database.begin():
        duplicate = BotanicalIdentity(scientific_name=dup_name)
        survivor = BotanicalIdentity(scientific_name=surv_name)
        database.add_all([duplicate, survivor])
        database.flush()
        dup_id, surv_id = duplicate.id, survivor.id
        dup_updated_at, surv_updated_at = duplicate.updated_at, survivor.updated_at

    worker_pids: Queue[int] = Queue()
    preloaded = Event()
    merge_started = Event()
    with ThreadPoolExecutor(max_workers=1) as executor:
        with Session(database_engine) as session_a:

            def update_worker() -> tuple[str, str]:
                with Session(database_engine) as session_b:
                    session_b.begin()
                    session_b.execute(text("SET LOCAL lock_timeout = '10s'"))
                    worker_pids.put(session_b.execute(text("SELECT pg_backend_pid()")).scalar_one())
                    loaded = session_b.get(BotanicalIdentity, dup_id)
                    assert loaded is not None
                    preloaded.set()
                    assert merge_started.wait(timeout=5)
                    try:
                        update_botanical_identity(
                            session_b,
                            loaded,
                            BotanicalIdentityUpdate(scientific_name=f"{dup_name} edited"),
                        )
                        session_b.commit()
                        return ("updated", "")
                    except BotanicalIdentityMergedError as error:
                        session_b.rollback()
                        return ("merged", str(error.merged_into_id))

            future = executor.submit(update_worker)
            worker_pid = worker_pids.get(timeout=5)
            assert preloaded.wait(timeout=5)

            session_a.begin()
            merge_duplicate_identity(
                session_a,
                dup_id,
                DuplicateIdentityMergeWrite(
                    survivor_identity_id=surv_id,
                    duplicate_updated_at=dup_updated_at,
                    survivor_updated_at=surv_updated_at,
                ),
            )
            merge_started.set()
            blocked = _wait_until_blocked(session_a, worker_pid, future)
            assert blocked, "update_botanical_identity did not wait on uncommitted merge"
            session_a.commit()

        kind, detail = future.result(timeout=5)
        assert (kind, detail) == ("merged", str(surv_id))


@pytest.mark.parametrize("via_reconciliation", [False, True])
def test_scenario2_merge_and_rename_onto_ordered_survivor_no_deadlock(
    database_engine: Engine, via_reconciliation: bool
) -> None:
    """Deadlock regression: id_1 < id_2 merge vs id_2 rename onto id_1 name never deadlocks."""
    with Session(database_engine) as database, database.begin():
        first_id = uuid7()
        second_id = uuid7()
        assert first_id < second_id
        alpha_name = f"Alpha surv {first_id}"
        beta_name = f"Beta dup {second_id}"
        survivor = BotanicalIdentity(id=first_id, scientific_name=alpha_name)
        duplicate = BotanicalIdentity(id=second_id, scientific_name=beta_name)
        database.add_all([survivor, duplicate])
        database.flush()
        dup_updated_at, surv_updated_at = duplicate.updated_at, survivor.updated_at

    worker_pids: Queue[int] = Queue()
    with ThreadPoolExecutor(max_workers=1) as executor:
        with Session(database_engine) as session_a, session_a.begin():
            merge_duplicate_identity(
                session_a,
                second_id,
                DuplicateIdentityMergeWrite(
                    survivor_identity_id=first_id,
                    duplicate_updated_at=dup_updated_at,
                    survivor_updated_at=surv_updated_at,
                ),
            )

            def rename_worker() -> tuple[str, str]:
                with Session(database_engine) as session_b:
                    session_b.begin()
                    session_b.execute(text("SET LOCAL lock_timeout = '10s'"))
                    worker_pids.put(session_b.execute(text("SELECT pg_backend_pid()")).scalar_one())
                    loaded = session_b.get(BotanicalIdentity, second_id)
                    assert loaded is not None
                    try:
                        if via_reconciliation:
                            correct_accepted_name(
                                session_b,
                                second_id,
                                AcceptedNameCorrectionWrite(
                                    scientific_name=alpha_name,
                                    source_provider="operator",
                                    identity_updated_at=dup_updated_at,
                                ),
                            )
                        else:
                            update_botanical_identity(
                                session_b,
                                loaded,
                                BotanicalIdentityUpdate(scientific_name=alpha_name),
                            )
                        session_b.commit()
                        return ("updated", "")
                    except BotanicalIdentityMergedError as error:
                        session_b.rollback()
                        return ("merged", str(error.merged_into_id))
                    except ReconciliationConflictError as error:
                        session_b.rollback()
                        return (error.code, str(error.existing_id))

            future = executor.submit(rename_worker)
            worker_pid = worker_pids.get(timeout=5)
            blocked = _wait_until_blocked(session_a, worker_pid, future)
            assert blocked, "identity mutation did not synchronize on uncommitted merge"

        kind, detail = future.result(timeout=5)
        expected_kind = "botanical_identity_merged" if via_reconciliation else "merged"
        assert (kind, detail) == (expected_kind, str(first_id))


@pytest.mark.parametrize("commit_merge", [True, False])
def test_scenario2_correct_accepted_name_claiming_merging_name_follows_merge(
    database_engine: Engine, commit_merge: bool
) -> None:
    """Scenario 2: correct_accepted_name waits on uncommitted merge and follows its outcome."""
    dup_name = f"Echinopsis corr {uuid7()}"
    surv_name = f"Trichocereus corr {uuid7()}"
    other_name = f"Cereus corr {uuid7()}"
    with Session(database_engine) as database, database.begin():
        duplicate = BotanicalIdentity(scientific_name=dup_name)
        survivor = BotanicalIdentity(scientific_name=surv_name)
        other = BotanicalIdentity(scientific_name=other_name)
        database.add_all([duplicate, survivor, other])
        database.flush()
        dup_id, surv_id, other_id = duplicate.id, survivor.id, other.id
        dup_updated_at = duplicate.updated_at
        surv_updated_at = survivor.updated_at
        other_updated_at = other.updated_at

    worker_pids: Queue[int] = Queue()
    with ThreadPoolExecutor(max_workers=1) as executor:
        with Session(database_engine) as session_a:
            session_a.begin()
            merge_duplicate_identity(
                session_a,
                dup_id,
                DuplicateIdentityMergeWrite(
                    survivor_identity_id=surv_id,
                    duplicate_updated_at=dup_updated_at,
                    survivor_updated_at=surv_updated_at,
                ),
            )

            def correct_worker() -> tuple[str, str]:
                with Session(database_engine) as session_b:
                    session_b.begin()
                    session_b.execute(text("SET LOCAL lock_timeout = '10s'"))
                    worker_pids.put(session_b.execute(text("SELECT pg_backend_pid()")).scalar_one())
                    try:
                        correct_accepted_name(
                            session_b,
                            other_id,
                            AcceptedNameCorrectionWrite(
                                scientific_name=dup_name,
                                source_provider="operator",
                                identity_updated_at=other_updated_at,
                            ),
                        )
                        session_b.commit()
                        return ("corrected", dup_name)
                    except ReconciliationConflictError as error:
                        session_b.rollback()
                        return (error.code, str(error.existing_id))

            future = executor.submit(correct_worker)
            worker_pid = worker_pids.get(timeout=5)
            blocked = _wait_until_blocked(session_a, worker_pid, future)
            assert blocked, "correct_accepted_name did not wait on uncommitted merge"

            if commit_merge:
                session_a.commit()
            else:
                session_a.rollback()

        kind, detail = future.result(timeout=5)
        with Session(database_engine) as check_db:
            persisted_other = check_db.get(BotanicalIdentity, other_id)
            assert persisted_other is not None
            if commit_merge:
                assert (kind, detail) == ("corrected", dup_name)
                assert persisted_other.scientific_name == dup_name
            else:
                assert (kind, detail) == ("duplicate_botanical_identity", str(dup_id))
                assert persisted_other.scientific_name == other_name


def test_scenario2_concurrent_name_swap_updates_no_deadlock(database_engine: Engine) -> None:
    """Two concurrent updates targeting each other's names serialize without deadlock."""
    name_a = f"Swap Alpha {uuid7()}"
    name_b = f"Swap Beta {uuid7()}"
    with Session(database_engine) as database, database.begin():
        first = BotanicalIdentity(scientific_name=name_a)
        second = BotanicalIdentity(scientific_name=name_b)
        database.add_all([first, second])
        database.flush()
        first_id, second_id = first.id, second.id

    barrier = Barrier(2)

    def swap_worker(source_id: UUID, target_name: str) -> str:
        with Session(database_engine) as session:
            session.begin()
            session.execute(text("SET LOCAL lock_timeout = '10s'"))
            loaded = session.get(BotanicalIdentity, source_id)
            assert loaded is not None
            barrier.wait(timeout=5)
            try:
                update_botanical_identity(
                    session,
                    loaded,
                    BotanicalIdentityUpdate(scientific_name=target_name),
                )
                session.commit()
                return "updated"
            except BotanicalIdentityConflictError:
                session.rollback()
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(swap_worker, first_id, name_b)
        second_future = executor.submit(swap_worker, second_id, name_a)
        results = sorted([first_future.result(timeout=5), second_future.result(timeout=5)])

    assert results == ["conflict", "conflict"]


def test_correct_accepted_name_savepoint_rolls_back_synonym_cleanup_on_unique_error(
    database_engine: Engine,
) -> None:
    """Savepoint rollback restores operator synonyms and in-memory state after UniqueViolation."""
    target_name = f"Rollback Target {uuid7()}"
    existing_name = f"Rollback Colliding {uuid7()}"
    with Session(database_engine) as database, database.begin():
        target = BotanicalIdentity(scientific_name=target_name)
        database.add(target)
        database.flush()
        add_operator_synonym(
            database,
            target.id,
            OperatorSynonymCreate(scientific_name=existing_name),
        )
        colliding = BotanicalIdentity(scientific_name=existing_name)
        database.add(colliding)
        database.flush()
        target_id = target.id
        target_updated_at = target.updated_at

    with Session(database_engine) as session:
        session.begin()
        calls = 0

        def bypass_precheck(
            db: Session,
            scientific_name: str,
            cultivar_name: str | None,
            *,
            for_share: bool = False,
        ) -> BotanicalIdentity | None:
            nonlocal calls
            calls += 1
            if calls == 1:
                return None
            return find_duplicate(db, scientific_name, cultivar_name, for_share=for_share)

        with (
            patch(
                "florabase.botanical_identities.reconciliation.find_duplicate",
                side_effect=bypass_precheck,
            ),
            pytest.raises(ReconciliationConflictError) as caught,
        ):
            correct_accepted_name(
                session,
                target_id,
                AcceptedNameCorrectionWrite(
                    scientific_name=existing_name,
                    source_provider="operator",
                    identity_updated_at=target_updated_at,
                ),
            )

        assert caught.value.code == "duplicate_botanical_identity"
        loaded_target = session.get(BotanicalIdentity, target_id)
        assert loaded_target is not None
        assert loaded_target.scientific_name == target_name
        # Confirm operator_synonym deleted inside begin_nested() was rolled back cleanly.
        synonym_count = (
            session.execute(
                select(BotanicalIdentityName).where(
                    BotanicalIdentityName.botanical_identity_id == target_id,
                    BotanicalIdentityName.status_kind == "operator_synonym",
                )
            )
            .scalars()
            .all()
        )
        assert len(synonym_count) == 1
        assert synonym_count[0].scientific_name == existing_name
        assert isinstance(caught.value.existing_id, UUID)
        assert datetime.now(UTC) >= loaded_target.created_at
        session.rollback()
