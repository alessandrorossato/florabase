"""PostgreSQL integration tests for single-sheet CSV/XLSX import endpoints."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator
from pathlib import Path
from typing import cast
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import Connection, func, select
from sqlalchemy.orm import Session

from florabase.auth.dependencies import (
    AuthenticatedActor,
    require_authenticated_actor,
    require_csrf,
)
from florabase.auth.model import AuthSession
from florabase.auth.service import bootstrap_owner
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.core.config import CookieMode, Environment, Settings, get_settings
from florabase.db.session import get_database_session
from florabase.import_wizard.service import SheetImportConflictError
from florabase.locations.model import Location
from florabase.locations.schemas import LocationCreate, LocationUsageScope
from florabase.locations.service import create_location
from florabase.main import app
from florabase.plants.model import Plant, PlantGroup
from florabase.plants.service import PlantDomainConflictError
from florabase.plants.service import create_plant as real_create_plant
from florabase.seed_lots.model import SeedLot
from florabase.suppliers.model import Supplier, SupplierKind

pytestmark = pytest.mark.integration
ORIGIN = "https://florabase.example"
PASSWORD = "correct horse battery staple"
FIXTURES = Path(__file__).parent.parent / "fixtures" / "sheet"


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


async def _login(client: httpx.AsyncClient, login_name: str = "owner") -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"login_name": login_name, "password": PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 200
    return cast(str, response.json()["csrf_token"])


def _snapshot_collection(connection: Connection) -> dict[str, object]:
    with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
        identities = sorted(
            (i.scientific_name, i.cultivar_name, i.common_name)
            for i in db.scalars(select(BotanicalIdentity))
        )
        suppliers = sorted((s.name, s.kind) for s in db.scalars(select(Supplier)))
        locations = sorted(
            (loc.name, loc.supports_plants, loc.supports_seed_lots)
            for loc in db.scalars(select(Location))
        )
        id_names = {
            i.id: (i.scientific_name, i.cultivar_name)
            for i in db.scalars(select(BotanicalIdentity))
        }
        loc_names = {loc.id: loc.name for loc in db.scalars(select(Location))}
        sup_names = {s.id: s.name for s in db.scalars(select(Supplier))}
        plants = sorted(
            (
                id_names[p.botanical_identity_id],
                p.label,
                loc_names.get(p.location_id) if p.location_id else None,
                sup_names.get(p.supplier_id) if p.supplier_id else None,
                p.collection_entry_date_precision,
                p.collection_entry_date_year,
                p.collection_entry_date_month,
                p.collection_entry_date_day,
                p.notes,
            )
            for p in db.scalars(select(Plant))
        )
        groups = sorted(
            (
                id_names[g.botanical_identity_id],
                g.label,
                loc_names.get(g.location_id) if g.location_id else None,
                g.quantity_value,
                g.quantity_is_approximate,
                g.collection_entry_date_precision,
                g.collection_entry_date_year,
                g.collection_entry_date_month,
                g.collection_entry_date_day,
                g.notes,
            )
            for g in db.scalars(select(PlantGroup))
        )
        seed_lots = sorted(
            (
                id_names[s.botanical_identity_id],
                s.label,
                loc_names.get(s.location_id) if s.location_id else None,
                sup_names.get(s.supplier_id) if s.supplier_id else None,
                s.harvest_date_precision,
                s.harvest_date_year,
                s.quantity_kind,
                str(s.quantity_value) if s.quantity_value is not None else None,
                s.quantity_is_approximate,
                s.notes,
            )
            for s in db.scalars(select(SeedLot))
        )
    return {
        "identities": identities,
        "suppliers": suppliers,
        "locations": locations,
        "plants": plants,
        "groups": groups,
        "seed_lots": seed_lots,
    }


def _wipe_collection(connection: Connection) -> None:
    with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
        for model in (Plant, PlantGroup, SeedLot, Location, Supplier, BotanicalIdentity):
            for obj in db.scalars(select(model)):
                db.delete(obj)
        db.commit()


def test_routes_do_not_collide_with_import_001(configured_app: None) -> None:
    """Review Rule #1: both /imports/{kind}/* and /sheet-imports/* must resolve cleanly."""

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
            await _login(client)
            # IMPORT-001 route still resolves and validates canonical CSV.
            csv_001 = b"scientific_name,cultivar_name,common_name\nAcmella oleracea,,Paracress\n"
            r_old = await client.post(
                "/api/v1/imports/botanical-identities/preview",
                content=csv_001,
                headers={"Content-Type": "text/csv"},
            )
            assert r_old.status_code == 200
            assert r_old.json()["ready"] == 1

            # New IMPORT-002 routes resolve under /api/v1/sheet-imports/*.
            data = (FIXTURES / "plants.csv").read_bytes()
            r_inspect = await client.post(
                "/api/v1/sheet-imports/inspect",
                files={"file": ("plants.csv", data, "text/csv")},
                data={"record_type": "plants"},
            )
            assert r_inspect.status_code == 200
            mapping = {col["key"]: col["suggested_field"] for col in r_inspect.json()["columns"]}
            options = json.dumps({"record_type": "plants", "mapping": {"columns": mapping}})
            r_preview = await client.post(
                "/api/v1/sheet-imports/preview",
                files={"file": ("plants.csv", data, "text/csv")},
                data={"options": options},
            )
            assert r_preview.status_code == 200
            assert r_preview.json()["can_apply"] is True

    asyncio.run(scenario())


@pytest.mark.parametrize("record_type", ["plants", "plant-groups", "seed-lots"])
def test_csv_and_xlsx_end_to_end_apply_equivalence(
    configured_app: None, database_connection: Connection, record_type: str
) -> None:
    async def run_import(filename: str) -> dict[str, object]:
        data = (FIXTURES / filename).read_bytes()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
            csrf = await _login(client)
            inspected = await client.post(
                "/api/v1/sheet-imports/inspect",
                files={"file": (filename, data, "application/octet-stream")},
                data={"record_type": record_type},
            )
            assert inspected.status_code == 200
            mapping = {col["key"]: col["suggested_field"] for col in inspected.json()["columns"]}
            options = json.dumps({"record_type": record_type, "mapping": {"columns": mapping}})
            previewed = await client.post(
                "/api/v1/sheet-imports/preview",
                files={"file": (filename, data, "application/octet-stream")},
                data={"options": options},
            )
            assert previewed.status_code == 200
            preview_body = previewed.json()
            assert preview_body["can_apply"] is True
            token = preview_body["confirmation_token"]

            applied = await client.post(
                "/api/v1/sheet-imports/apply",
                files={"file": (filename, data, "application/octet-stream")},
                data={"options": options},
                headers={
                    "Origin": ORIGIN,
                    "X-CSRF-Token": csrf,
                    "X-Import-Confirmation": token,
                },
            )
            assert applied.status_code == 200
            apply_body = applied.json()
            assert apply_body["records_created"] == 2
            assert len(apply_body["created_records"]) == 2
            return _snapshot_collection(database_connection)

    async def scenario() -> None:
        csv_snapshot = await run_import(f"{record_type}.csv")
        _wipe_collection(database_connection)
        xlsx_snapshot = await run_import(f"{record_type}.xlsx")
        assert csv_snapshot == xlsx_snapshot

    asyncio.run(scenario())


def test_it_edge_cases_apply_with_parent_location_supplier_kind_and_skip(
    configured_app: None, database_connection: Connection
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        parent = create_location(db, LocationCreate(name="Main Greenhouse"))
        parent_id = str(parent.id)
        db.commit()

    async def scenario() -> None:
        data = (FIXTURES / "it-edge-cases.xlsx").read_bytes()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
            csrf = await _login(client)
            inspected = await client.post(
                "/api/v1/sheet-imports/inspect",
                files={"file": ("it-edge-cases.xlsx", data, "application/octet-stream")},
                data={"record_type": "plants", "sheet_name": "Piante"},
            )
            assert inspected.status_code == 200
            body = inspected.json()
            assert body["header_row"] == 2
            mapping = {col["key"]: col["suggested_field"] for col in body["columns"]}
            options = json.dumps(
                {
                    "record_type": "plants",
                    "sheet_name": "Piante",
                    "header_row": 2,
                    "mapping": {"columns": mapping, "append_unmapped_to_notes": True},
                    "choices": {
                        "locations": {
                            "Serra / Bancale 2": {
                                "action": "create",
                                "name": "Bancale 2",
                                "parent_id": parent_id,
                            },
                            "Davanzale": {"action": "skip"},
                        },
                        "suppliers": {
                            "Vivaio Verde": {"action": "create", "kind": SupplierKind.NURSERY.value}
                        },
                    },
                }
            )
            previewed = await client.post(
                "/api/v1/sheet-imports/preview",
                files={"file": ("it-edge-cases.xlsx", data, "application/octet-stream")},
                data={"options": options},
            )
            assert previewed.status_code == 200
            pbody = previewed.json()
            assert pbody["can_apply"] is True
            assert any(
                "location will be left empty" in ref for ref in pbody["rows"][1]["references"]
            )

            applied = await client.post(
                "/api/v1/sheet-imports/apply",
                files={"file": ("it-edge-cases.xlsx", data, "application/octet-stream")},
                data={"options": options},
                headers={
                    "Origin": ORIGIN,
                    "X-CSRF-Token": csrf,
                    "X-Import-Confirmation": pbody["confirmation_token"],
                },
            )
            assert applied.status_code == 200
            abody = applied.json()
            assert abody["records_created"] == 2
            assert abody["identities_created"] == 2
            assert abody["locations_created"] == 1
            assert abody["suppliers_created"] == 1

        with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
            plants = {p.label: p for p in db.scalars(select(Plant))}
            assert plants["HOY-K-01"].location_id is not None
            assert plants["HAW-01"].location_id is None
            assert "Prezzo: 12.5" in (plants["HOY-K-01"].notes or "")
            assert plants["HAW-01"].notes == "Prezzo come formula"
            supplier = db.scalar(select(Supplier).where(Supplier.name == "Vivaio Verde"))
            assert supplier is not None
            assert supplier.kind == SupplierKind.NURSERY.value

    asyncio.run(scenario())


def test_auth_csrf_confirmation_mismatch_and_atomic_rollback(
    configured_app: None,
    database_connection: Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = (FIXTURES / "plants.csv").read_bytes()

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
            # 1. Unauthenticated rejected (401)
            assert (
                await client.post(
                    "/api/v1/sheet-imports/inspect",
                    files={"file": ("plants.csv", data, "text/csv")},
                )
            ).status_code == 401

            # 2. Non-owner rejected (403) on inspect, preview, and apply
            non_owner = AuthenticatedActor(
                user_id=uuid4(),
                login_name="viewer",
                display_name="Viewer",
                owner=False,
                session=AuthSession(id=uuid4(), token_digest=b"v" * 32),
            )
            app.dependency_overrides[require_authenticated_actor] = lambda: non_owner
            app.dependency_overrides[require_csrf] = lambda: non_owner
            try:
                assert (
                    await client.post(
                        "/api/v1/sheet-imports/inspect",
                        files={"file": ("plants.csv", data, "text/csv")},
                    )
                ).status_code == 403
                assert (
                    await client.post(
                        "/api/v1/sheet-imports/preview",
                        files={"file": ("plants.csv", data, "text/csv")},
                        data={"options": "{}"},
                    )
                ).status_code == 403
                assert (
                    await client.post(
                        "/api/v1/sheet-imports/apply",
                        files={"file": ("plants.csv", data, "text/csv")},
                        data={"options": "{}"},
                    )
                ).status_code == 403
            finally:
                app.dependency_overrides.pop(require_authenticated_actor, None)
                app.dependency_overrides.pop(require_csrf, None)

            # 3. Owner inspect + preview
            csrf = await _login(client, "owner")
            inspected = await client.post(
                "/api/v1/sheet-imports/inspect",
                files={"file": ("plants.csv", data, "text/csv")},
                data={"record_type": "plants"},
            )
            mapping = {col["key"]: col["suggested_field"] for col in inspected.json()["columns"]}
            options = json.dumps({"record_type": "plants", "mapping": {"columns": mapping}})
            previewed = await client.post(
                "/api/v1/sheet-imports/preview",
                files={"file": ("plants.csv", data, "text/csv")},
                data={"options": options},
            )
            token = previewed.json()["confirmation_token"]

            # 4. Missing CSRF rejected (403)
            assert (
                await client.post(
                    "/api/v1/sheet-imports/apply",
                    files={"file": ("plants.csv", data, "text/csv")},
                    data={"options": options},
                    headers={"X-Import-Confirmation": token},
                )
            ).status_code == 403

            # 5. Altered bytes or missing token rejected (409)
            assert (
                await client.post(
                    "/api/v1/sheet-imports/apply",
                    files={"file": ("plants.csv", data + b"\n", "text/csv")},
                    data={"options": options},
                    headers={
                        "Origin": ORIGIN,
                        "X-CSRF-Token": csrf,
                        "X-Import-Confirmation": token,
                    },
                )
            ).status_code == 409

            # 6. Atomic rollback when row k=2 fails in create_plant
            calls = 0

            def fail_on_second(db: Session, payload: object) -> object:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise PlantDomainConflictError(
                        "simulated_conflict", "Simulated failure on row 2"
                    )
                return real_create_plant(db, payload)  # type: ignore[arg-type]

            monkeypatch.setattr("florabase.import_wizard.service.create_plant", fail_on_second)
            failed = await client.post(
                "/api/v1/sheet-imports/apply",
                files={"file": ("plants.csv", data, "text/csv")},
                data={"options": options},
                headers={
                    "Origin": ORIGIN,
                    "X-CSRF-Token": csrf,
                    "X-Import-Confirmation": token,
                },
            )
            assert failed.status_code == 409
            monkeypatch.setattr("florabase.import_wizard.service.create_plant", real_create_plant)

            # Nothing must be committed (0 identities, 0 locations, 0 suppliers, 0 plants).
            with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
                assert db.scalar(select(func.count()).select_from(BotanicalIdentity)) == 0
                assert db.scalar(select(func.count()).select_from(Supplier)) == 0
                assert db.scalar(select(func.count()).select_from(Location)) == 0
                assert db.scalar(select(func.count()).select_from(Plant)) == 0

            # 7. Concurrent scope/state change between preview and apply rolls back with 409
            with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
                loc = create_location(
                    db,
                    LocationCreate(
                        name="Windowsill",
                        usage_scopes={
                            LocationUsageScope.PLANTS,
                            LocationUsageScope.SEED_LOTS,
                        },
                    ),
                )
                loc_id = loc.id
                db.commit()

            previewed2 = await client.post(
                "/api/v1/sheet-imports/preview",
                files={"file": ("plants.csv", data, "text/csv")},
                data={"options": options},
            )
            assert previewed2.json()["can_apply"] is True
            token2 = previewed2.json()["confirmation_token"]

            # Remove plants scope from Windowsill before apply.
            with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
                target = db.get(Location, loc_id)
                assert target is not None
                target.supports_plants = False
                db.commit()

            conflict = await client.post(
                "/api/v1/sheet-imports/apply",
                files={"file": ("plants.csv", data, "text/csv")},
                data={"options": options},
                headers={
                    "Origin": ORIGIN,
                    "X-CSRF-Token": csrf,
                    "X-Import-Confirmation": token2,
                },
            )
            assert conflict.status_code == 409
            # Still zero identities/plants created.
            with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
                assert db.scalar(select(func.count()).select_from(BotanicalIdentity)) == 0
                assert db.scalar(select(func.count()).select_from(Plant)) == 0

    _ = SheetImportConflictError
    asyncio.run(scenario())
