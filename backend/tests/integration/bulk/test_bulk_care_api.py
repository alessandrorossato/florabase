"""PostgreSQL integration tests for CARE-BULK-001 + FN-03 (bulk care, undo, reversal, journal)."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import Connection, func, select
from sqlalchemy.orm import Session

from florabase.auth.dependencies import AuthenticatedActor, require_csrf
from florabase.auth.model import AuthSession
from florabase.auth.service import bootstrap_owner
from florabase.botanical_identities.schemas import BotanicalIdentityCreate
from florabase.botanical_identities.service import create_botanical_identity
from florabase.core.config import CookieMode, Environment, Settings, get_settings
from florabase.db.session import get_database_session
from florabase.events.model import Event, EventKind
from florabase.events.schemas import EventCreate
from florabase.events.service import EventDomainConflictError, create_event
from florabase.locations.schemas import LocationCreate
from florabase.locations.service import create_location
from florabase.main import app
from florabase.plants.model import Plant, PlantLifecycle
from florabase.plants.schemas import (
    PlantCreate,
    PlantExtractionCreate,
    PlantGroupCreate,
    PlantGroupQuantity,
    ReintegrationEligibilityStatus,
)
from florabase.plants.service import (
    create_plant,
    create_plant_group,
    evaluate_reintegration,
    extract_plant,
)
from florabase.propagation.reversal import evaluate as evaluate_propagation_reversal
from florabase.propagation.schemas import PlantFromSowingCreate
from florabase.propagation.service import create_plant_from_sowing
from florabase.seed_lots.schemas import SeedLotCreate
from florabase.seed_lots.service import create_seed_lot
from florabase.sowings.schemas import SowingCreate
from florabase.sowings.service import create_sowing

pytestmark = pytest.mark.integration
ORIGIN = "https://florabase.example"
PASSWORD = "correct horse battery staple"


@pytest.fixture
def configured_app(database_connection: Connection) -> Iterator[None]:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        bootstrap_owner(database, "owner", PASSWORD, "Florabase Owner")
        database.commit()

    def database_override() -> Iterator[Session]:
        with Session(
            bind=database_connection, join_transaction_mode="create_savepoint"
        ) as database:
            try:
                yield database
                database.commit()
            except Exception:
                database.rollback()
                raise

    settings = Settings.model_validate(
        {
            "environment": Environment.TEST,
            "database_url": "postgresql+psycopg://unused",
            "canonical_origin": ORIGIN,
            "cookie_mode": CookieMode.SECURE,
        }
    )
    app.dependency_overrides[get_database_session] = database_override
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        yield
    finally:
        app.dependency_overrides.clear()


async def _login(client: httpx.AsyncClient) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"login_name": "owner", "password": PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 200
    return cast(str, response.json()["csrf_token"])


def test_bulk_care_selection_apply_and_partial_undo_and_full_undo(
    configured_app: None, database_connection: Connection
) -> None:
    """Acceptance #1: 3 plants + 1 group -> 4 events with same batch_id; undo removes unedited."""
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity = create_botanical_identity(
            db, BotanicalIdentityCreate(scientific_name="Hoya carnosa")
        )
        loc = create_location(db, LocationCreate(name="Bench 2"))
        plants = [
            create_plant(
                db,
                PlantCreate(
                    botanical_identity_id=identity.id, label=f"Hoya {i}", location_id=loc.id
                ),
            )
            for i in range(1, 4)
        ]
        group = create_plant_group(
            db,
            PlantGroupCreate(
                botanical_identity_id=identity.id,
                label="Hoya tray",
                location_id=loc.id,
                quantity=PlantGroupQuantity(value=6, is_approximate=False),
            ),
        )
        plant_ids = [str(p.id) for p in plants]
        group_id = str(group.id)
        db.commit()

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
            csrf = await _login(client)
            headers = {"Origin": ORIGIN, "X-CSRF-Token": csrf}
            records = [
                {"kind": "plant", "id": plant_ids[0]},
                {"kind": "plant", "id": plant_ids[1]},
                {"kind": "plant", "id": plant_ids[2]},
                {"kind": "plant_group", "id": group_id},
            ]
            body = {
                "targets": {"records": records},
                "kind": "watering",
                "occurred_on": {"precision": "day", "year": 2026, "month": 11, "day": 25},
                "notes": "Rainwater",
            }
            preview = await client.post("/api/v1/bulk/care/preview", json=body, headers=headers)
            assert preview.status_code == 200
            pjson = preview.json()
            assert pjson["log_count"] == 4
            assert pjson["plant_count"] == 3
            assert pjson["plant_group_count"] == 1
            assert pjson["can_apply"] is True

            applied = await client.post(
                "/api/v1/bulk/care/apply",
                json={**body, "target_signature": pjson["target_signature"]},
                headers=headers,
            )
            assert applied.status_code == 200
            ajson = applied.json()
            assert ajson["logged_count"] == 4
            batch_id = ajson["batch_id"]

            # Verify 4 events share batch_id.
            with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
                batch_events = list(
                    db.scalars(select(Event).where(Event.batch_id == UUID(batch_id)))
                )
                assert len(batch_events) == 4
                assert all(ev.kind == "watering" for ev in batch_events)
                assert all(ev.created_at == ev.updated_at for ev in batch_events)

            # Full undo removes all 4 events.
            undone = await client.delete(f"/api/v1/bulk/care/batches/{batch_id}", headers=headers)
            assert undone.status_code == 200
            assert undone.json()["deleted_count"] == 4
            assert undone.json()["kept_count"] == 0
            with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
                assert db.scalar(select(func.count()).select_from(Event)) == 0

            # Log again, edit 1 event via single-event API, then undo: 3 deleted, 1 edited kept.
            preview2 = await client.post("/api/v1/bulk/care/preview", json=body, headers=headers)
            applied2 = await client.post(
                "/api/v1/bulk/care/apply",
                json={**body, "target_signature": preview2.json()["target_signature"]},
                headers=headers,
            )
            batch2 = applied2.json()["batch_id"]
            with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
                edited_event_id = str(
                    db.scalars(
                        select(Event.id).where(Event.batch_id == UUID(batch2)).order_by(Event.id)
                    ).first()
                )
            patched = await client.put(
                f"/api/v1/events/{edited_event_id}",
                json={
                    "kind": "watering",
                    "occurred_on": {"precision": "day", "year": 2026, "month": 11, "day": 25},
                    "notes": "Rainwater + extra flush",
                },
                headers=headers,
            )
            assert patched.status_code == 200

            partial_undo = await client.delete(
                f"/api/v1/bulk/care/batches/{batch2}", headers=headers
            )
            assert partial_undo.status_code == 200
            ujson = partial_undo.json()
            assert ujson["deleted_count"] == 3
            assert ujson["kept_count"] == 1
            assert ujson["kept"][0]["id"] == edited_event_id
            assert ujson["kept"][0]["reason"] == "edited"

    asyncio.run(scenario())


def test_bulk_care_location_subtree_inactive_skip_and_empty_location(
    configured_app: None, database_connection: Connection
) -> None:
    """Acceptance #2: location subtree logs active, skips inactive, empty -> 422."""
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity = create_botanical_identity(
            db, BotanicalIdentityCreate(scientific_name="Haworthia attenuata")
        )
        greenhouse = create_location(db, LocationCreate(name="Greenhouse"))
        bench = create_location(db, LocationCreate(name="Bench 2", parent_id=greenhouse.id))
        shelf = create_location(db, LocationCreate(name="Upper Shelf", parent_id=bench.id))
        empty_loc = create_location(db, LocationCreate(name="Empty Shed"))

        create_plant(
            db,
            PlantCreate(
                botanical_identity_id=identity.id, label="Direct active", location_id=greenhouse.id
            ),
        )
        create_plant(
            db,
            PlantCreate(
                botanical_identity_id=identity.id, label="Bench active", location_id=bench.id
            ),
        )
        create_plant(
            db,
            PlantCreate(
                botanical_identity_id=identity.id,
                label="Bench dead",
                location_id=bench.id,
                lifecycle=PlantLifecycle.DEAD,
            ),
        )
        create_plant_group(
            db,
            PlantGroupCreate(
                botanical_identity_id=identity.id,
                label="Shelf group",
                location_id=shelf.id,
                quantity=PlantGroupQuantity(value=5, is_approximate=True),
            ),
        )
        gh_id = str(greenhouse.id)
        empty_id = str(empty_loc.id)
        db.commit()

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
            csrf = await _login(client)
            headers = {"Origin": ORIGIN, "X-CSRF-Token": csrf}

            # Include sublocations: 3 active (2 plants + 1 group), 1 dead skipped, 2 sub-locations.
            body = {
                "targets": {"location_id": gh_id, "include_sublocations": True},
                "kind": "feeding",
                "occurred_on": {"precision": "month", "year": 2026, "month": 11},
                "notes": "Half-strength cactus feed",
            }
            preview = await client.post("/api/v1/bulk/care/preview", json=body, headers=headers)
            assert preview.status_code == 200
            pjson = preview.json()
            assert pjson["sublocation_count"] == 2
            assert pjson["log_count"] == 3
            assert pjson["plant_count"] == 2
            assert pjson["plant_group_count"] == 1
            assert pjson["skipped_count"] == 1

            applied = await client.post(
                "/api/v1/bulk/care/apply",
                json={**body, "target_signature": pjson["target_signature"]},
                headers=headers,
            )
            assert applied.status_code == 200
            assert applied.json()["logged_count"] == 3

            # Exclude sublocations: only the 1 direct plant in Greenhouse.
            direct_body = {
                "targets": {"location_id": gh_id, "include_sublocations": False},
                "kind": "watering",
            }
            direct_preview = await client.post(
                "/api/v1/bulk/care/preview", json=direct_body, headers=headers
            )
            assert direct_preview.status_code == 200
            assert direct_preview.json()["log_count"] == 1
            assert direct_preview.json()["sublocation_count"] == 0

            # Empty location: can_apply=False; apply -> 422 nothing_to_log.
            empty_body = {
                "targets": {"location_id": empty_id, "include_sublocations": True},
                "kind": "watering",
            }
            empty_preview = await client.post(
                "/api/v1/bulk/care/preview", json=empty_body, headers=headers
            )
            assert empty_preview.status_code == 200
            assert empty_preview.json()["can_apply"] is False
            empty_apply = await client.post(
                "/api/v1/bulk/care/apply",
                json={**empty_body, "target_signature": empty_preview.json()["target_signature"]},
                headers=headers,
            )
            assert empty_apply.status_code == 422
            assert empty_apply.json()["detail"]["code"] == "nothing_to_log"

    asyncio.run(scenario())


def test_bulk_care_stale_signature_atomicity_authz_csrf_and_single_journal(
    configured_app: None,
    database_connection: Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity = create_botanical_identity(
            db, BotanicalIdentityCreate(scientific_name="Echeveria elegans")
        )
        p1 = create_plant(db, PlantCreate(botanical_identity_id=identity.id, label="E-1"))
        p2 = create_plant(db, PlantCreate(botanical_identity_id=identity.id, label="E-2"))
        p1_id, p2_id = str(p1.id), str(p2.id)
        db.commit()

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
            body = {
                "targets": {
                    "records": [
                        {"kind": "plant", "id": p1_id},
                        {"kind": "plant", "id": p2_id},
                    ]
                },
                "kind": "watering",
            }
            # Unauthenticated -> 401
            assert (await client.post("/api/v1/bulk/care/preview", json=body)).status_code == 401

            # Non-owner -> 403
            non_owner = AuthenticatedActor(
                user_id=uuid4(),
                login_name="viewer",
                display_name="Viewer",
                owner=False,
                session=AuthSession(id=uuid4(), token_digest=b"v" * 32),
            )
            app.dependency_overrides[require_csrf] = lambda: non_owner
            try:
                assert (
                    await client.post("/api/v1/bulk/care/preview", json=body)
                ).status_code == 403
            finally:
                app.dependency_overrides.pop(require_csrf, None)

            csrf = await _login(client)
            # Missing CSRF -> 403
            assert (await client.post("/api/v1/bulk/care/preview", json=body)).status_code == 403

            headers = {"Origin": ORIGIN, "X-CSRF-Token": csrf}
            preview = await client.post("/api/v1/bulk/care/preview", json=body, headers=headers)
            sig = preview.json()["target_signature"]

            # Atomicity: failure on second event rolls back first event too.
            real_create_event = create_event
            calls = 0

            def fail_second(
                db: Session,
                target_type: str,
                target_id: UUID,
                payload: EventCreate,
                *,
                batch_id: UUID | None = None,
            ) -> Event:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise EventDomainConflictError("simulated", "boom on 2")
                return real_create_event(db, target_type, target_id, payload, batch_id=batch_id)  # type: ignore[arg-type]

            monkeypatch.setattr("florabase.bulk.care_service.create_event", fail_second)
            failed = await client.post(
                "/api/v1/bulk/care/apply",
                json={**body, "target_signature": sig},
                headers=headers,
            )
            assert failed.status_code == 409
            monkeypatch.setattr("florabase.bulk.care_service.create_event", real_create_event)
            with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
                assert db.scalar(select(func.count()).select_from(Event)) == 0

            # Stale preview: mutate p1 updated_at before apply -> 409 stale_preview.
            with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
                row = db.get(Plant, UUID(p1_id))
                assert row is not None
                row.notes = "Edited concurrently"
                row.updated_at = datetime.now(UTC)
                db.commit()
            stale = await client.post(
                "/api/v1/bulk/care/apply",
                json={**body, "target_signature": sig},
                headers=headers,
            )
            assert stale.status_code == 409
            assert stale.json()["detail"]["code"] == "stale_preview"

            # Single Journal entry accepts watering and feeding (FN-03).
            for kind in ("watering", "feeding"):
                single = await client.post(
                    f"/api/v1/plants/{p1_id}/events",
                    json={
                        "kind": kind,
                        "occurred_on": {"precision": "day", "year": 2026, "month": 11, "day": 25},
                        "notes": f"Single {kind}",
                    },
                    headers=headers,
                )
                assert single.status_code == 201
                assert single.json()["kind"] == kind

    asyncio.run(scenario())


def test_watering_and_feeding_are_informational_for_sowing_reversal_and_reintegration(
    database_connection: Connection,
) -> None:
    """Owner decision #3: watering/feeding keep reversal & reintegration confirmation_required."""
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity = create_botanical_identity(
            db, BotanicalIdentityCreate(scientific_name="Phaseolus vulgaris")
        )
        seed_lot = create_seed_lot(
            db,
            SeedLotCreate(botanical_identity_id=identity.id, label="Bean lot"),
        )
        sowing = create_sowing(
            db,
            SowingCreate(
                seed_lot_id=seed_lot.id,
                label="Spring tray",
            ),
        )
        sowing_plant, _ = create_plant_from_sowing(
            db,
            sowing.id,
            PlantFromSowingCreate(
                botanical_identity_id=identity.id,
                label="Seedling 1",
            ),
            "active",
        )
        # Watering on a sowing-derived plant keeps reversal confirmation_required, not blocked.
        create_event(db, "plant", sowing_plant.id, EventCreate(kind=EventKind.WATERING))
        ev_sowing = evaluate_propagation_reversal(db, "plant", sowing_plant.id)
        assert ev_sowing.eligibility.status == "confirmation_required"
        assert len(ev_sowing.eligibility.retained_observation_ids) == 1

        # Treatment still blocks reversal.
        create_event(db, "plant", sowing_plant.id, EventCreate(kind=EventKind.TREATMENT))
        ev_blocked = evaluate_propagation_reversal(db, "plant", sowing_plant.id)
        assert ev_blocked.eligibility.status == "blocked"

        # PLANT-006 reintegration: extracted plant with watering/feeding stays confirmable.
        group = create_plant_group(
            db,
            PlantGroupCreate(
                botanical_identity_id=identity.id,
                label="Clump",
                quantity=PlantGroupQuantity(value=5, is_approximate=False),
            ),
        )
        extracted, _, _ = extract_plant(
            db,
            group.id,
            PlantExtractionCreate(label="Extracted 1"),
        )
        create_event(db, "plant", extracted.id, EventCreate(kind=EventKind.WATERING))
        create_event(db, "plant", extracted.id, EventCreate(kind=EventKind.FEEDING))
        reint = evaluate_reintegration(db, extracted.id)
        assert reint.status == ReintegrationEligibilityStatus.CONFIRMATION_REQUIRED
        assert {obs.kind for obs in reint.retained_observations} == {
            "watering",
            "feeding",
        }


def test_bulk_care_undo_keeps_event_with_photo_and_deletes_others(
    configured_app: None, database_connection: Connection
) -> None:
    """M1: batch of 3 with 1 photo -> undo deletes 2 and keeps 1 with reason has_photos."""
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity = create_botanical_identity(
            db, BotanicalIdentityCreate(scientific_name="Philodendron hederaceum")
        )
        plants = [
            create_plant(
                db,
                PlantCreate(botanical_identity_id=identity.id, label=f"Philo {i}"),
            )
            for i in range(1, 4)
        ]
        plant_ids = [str(p.id) for p in plants]
        db.commit()

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
            csrf = await _login(client)
            headers = {"Origin": ORIGIN, "X-CSRF-Token": csrf}
            body = {
                "targets": {"records": [{"kind": "plant", "id": pid} for pid in plant_ids]},
                "kind": "watering",
                "occurred_on": {"precision": "day", "year": 2026, "month": 11, "day": 25},
                "notes": "Morning mist",
            }
            preview = await client.post("/api/v1/bulk/care/preview", json=body, headers=headers)
            assert preview.status_code == 200
            applied = await client.post(
                "/api/v1/bulk/care/apply",
                json={**body, "target_signature": preview.json()["target_signature"]},
                headers=headers,
            )
            assert applied.status_code == 200
            batch_id = applied.json()["batch_id"]

            with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
                batch_event_ids = list(
                    db.scalars(
                        select(Event.id).where(Event.batch_id == UUID(batch_id)).order_by(Event.id)
                    )
                )
            assert len(batch_event_ids) == 3
            photo_event_id = str(batch_event_ids[0])

            attached = await client.post(
                f"/api/v1/collection-records/event/{photo_event_id}/photos/external",
                json={
                    "image_url": "https://images.example.test/philo-watered.jpg",
                    "source_url": "https://example.test/source",
                    "attribution": "Owner",
                    "caption": "After watering",
                },
                headers=headers,
            )
            assert attached.status_code == 201

            undone = await client.delete(f"/api/v1/bulk/care/batches/{batch_id}", headers=headers)
            assert undone.status_code == 200
            ujson = undone.json()
            assert ujson["deleted_count"] == 2
            assert ujson["kept_count"] == 1
            assert len(ujson["kept"]) == 1
            assert ujson["kept"][0]["id"] == photo_event_id
            assert ujson["kept"][0]["reason"] == "has_photos"

            with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
                remaining_ids = list(
                    db.scalars(select(Event.id).where(Event.batch_id == UUID(batch_id)))
                )
            assert remaining_ids == [UUID(photo_event_id)]

    asyncio.run(scenario())
