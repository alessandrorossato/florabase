import asyncio
import base64
import csv
import io
from collections.abc import Iterator
from typing import cast

import httpx
import pytest
from sqlalchemy import Connection, func, select
from sqlalchemy.orm import Session

from florabase.auth.service import bootstrap_owner
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.core.config import CookieMode, Environment, Settings, get_settings
from florabase.db.session import get_database_session
from florabase.import_export.service import COLUMNS, IMPORT_COLUMNS, example_csv
from florabase.locations.model import Location
from florabase.main import app
from florabase.seed_lots.model import SeedLot
from florabase.suppliers.model import Supplier
from florabase.suppliers.schemas import SupplierCreate
from florabase.suppliers.service import create_supplier as real_create_supplier

pytestmark = pytest.mark.integration
ORIGIN = "https://florabase.example"
PASSWORD = "correct horse battery staple"


def _csv(kind: str, rows: list[dict[str, str]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=COLUMNS[kind], lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode()


def _normal_csv(kind: str, rows: list[dict[str, str]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=IMPORT_COLUMNS[kind], lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode()


def _reviewed_body(data: bytes, decisions: dict[str, dict[str, str]]) -> dict[str, object]:
    return {"csv_base64": base64.b64encode(data).decode(), "decisions": decisions}


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


def test_preview_auth_csrf_exact_payload_and_create(
    configured_app: None, database_connection: Connection
) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
            data = _csv(
                "botanical-identities",
                [{"scientific_name": "Phaseolus vulgaris", "common_name": "Bean"}],
            )
            path = "/api/v1/imports/botanical-identities"
            assert (await client.post(path + "/preview", content=data)).status_code == 401
            csrf = await _login(client)
            preview = await client.post(path + "/preview", content=data)
            assert preview.status_code == 200
            body = preview.json()
            assert body["ready"] == 1
            assert body["rows"][0]["outcome"] == "ready"
            with Session(
                bind=database_connection, join_transaction_mode="create_savepoint"
            ) as database:
                assert database.scalar(select(func.count()).select_from(BotanicalIdentity)) == 0
            token = body["confirmation_token"]
            assert (
                await client.post(
                    path + "/apply", content=data, headers={"X-Import-Confirmation": token}
                )
            ).status_code == 403
            headers = {"Origin": ORIGIN, "X-CSRF-Token": csrf, "X-Import-Confirmation": token}
            changed = data.replace(b"Bean", b"Other")
            assert (
                await client.post(path + "/apply", content=changed, headers=headers)
            ).status_code == 409
            applied = await client.post(path + "/apply", content=data, headers=headers)
            assert applied.status_code == 200
            assert applied.json() == {"created": 1, "already_exists": 0, "updated": 0}
            again = await client.post(path + "/preview", content=data)
            assert again.json()["rows"][0]["outcome"] == "needs_choice"
            assert again.json()["rows"][0]["options"][0]["action"] == "use_existing"
            export = await client.get("/api/v1/exports/botanical-identities.csv")
            assert export.status_code == 200
            assert "Phaseolus vulgaris" in export.text
            assert export.headers["cache-control"] == "no-store"

    asyncio.run(scenario())


def test_location_hierarchy_seed_lot_precision_and_reference_diagnostics(
    configured_app: None, database_connection: Connection
) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
            csrf = await _login(client)
            headers = {"Origin": ORIGIN, "X-CSRF-Token": csrf}
            locations = _csv(
                "locations",
                [
                    {
                        "import_key": "drawer",
                        "name": "Drawer 3",
                        "parent_ref": "@cabinet",
                        "usage_scopes": "seed_lots",
                    },
                    {
                        "import_key": "cabinet",
                        "name": "Seed cabinet",
                        "usage_scopes": "seed_lots|plants",
                    },
                ],
            )
            path = "/api/v1/imports/locations"
            check = (await client.post(path + "/preview", content=locations)).json()
            assert check["ready"] == 2
            assert any("@cabinet" in item for item in check["rows"][0]["references"])
            result = await client.post(
                path + "/apply",
                content=locations,
                headers={**headers, "X-Import-Confirmation": check["confirmation_token"]},
            )
            assert result.status_code == 200
            with Session(
                bind=database_connection, join_transaction_mode="create_savepoint"
            ) as database:
                cabinet = database.scalars(
                    select(Location).where(Location.name == "Seed cabinet")
                ).one()
                drawer = database.scalars(select(Location).where(Location.name == "Drawer 3")).one()
                assert drawer.parent_id == cabinet.id
                drawer_id = drawer.id
                database.add(BotanicalIdentity(scientific_name="Phaseolus vulgaris"))
                database.commit()
            seed_lots = _csv(
                "seed-lots",
                [
                    {
                        "identity_ref": "Phaseolus vulgaris",
                        "label": "INCREASE P12",
                        "source_kind": "gift_exchange",
                        "acquisition_date": "2024-05",
                        "quantity_kind": "seed_count",
                        "quantity_value": "120",
                        "quantity_certainty": "approximate",
                        "location_ref": str(drawer_id),
                    }
                ],
            )
            path = "/api/v1/imports/seed-lots"
            check = (await client.post(path + "/preview", content=seed_lots)).json()
            assert check["ready"] == 1
            result = await client.post(
                path + "/apply",
                content=seed_lots,
                headers={**headers, "X-Import-Confirmation": check["confirmation_token"]},
            )
            assert result.status_code == 200
            with Session(
                bind=database_connection, join_transaction_mode="create_savepoint"
            ) as database:
                lot = database.scalars(select(SeedLot).where(SeedLot.label == "INCREASE P12")).one()
                assert lot.acquisition_date_precision == "month"
                assert lot.acquisition_date_year == 2024
                assert lot.acquisition_date_month == 5
                assert lot.acquisition_date_day is None
                assert lot.quantity_is_approximate is True
            export = await client.get("/api/v1/exports/seed-lots.csv")
            export_row = next(csv.DictReader(io.StringIO(export.text.lstrip("\ufeff"))))
            assert export_row["identity_label"] == "Phaseolus vulgaris"
            assert export_row["location_path"] == "Seed cabinet → Drawer 3"
            assert export_row["acquisition_date"] == "2024-05"
            assert export_row["quantity_certainty"] == "approximate"
            missing = seed_lots.replace(b"Phaseolus vulgaris", b"Unknown identity")
            report = (await client.post(path + "/preview", content=missing)).json()
            assert report["needs_attention"] == 1
            assert report["rows"][0]["outcome"] == "unresolved_reference"

    asyncio.run(scenario())


def test_invalid_file_is_atomic_and_supplier_names_are_ambiguous(
    configured_app: None, database_connection: Connection
) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
            csrf = await _login(client)
            data = _csv(
                "suppliers",
                [
                    {"name": "ABC Seeds", "kind": "seller"},
                    {"name": "ABC Seeds", "kind": "nursery"},
                ],
            )
            path = "/api/v1/imports/suppliers"
            check = (await client.post(path + "/preview", content=data)).json()
            assert check["needs_attention"] == 2
            assert all(row["outcome"] == "ambiguous_reference" for row in check["rows"])
            applied = await client.post(
                path + "/apply",
                content=data,
                headers={
                    "Origin": ORIGIN,
                    "X-CSRF-Token": csrf,
                    "X-Import-Confirmation": check["confirmation_token"],
                },
            )
            assert applied.status_code == 409
            with Session(
                bind=database_connection, join_transaction_mode="create_savepoint"
            ) as database:
                assert database.scalar(select(func.count()).select_from(Supplier)) == 0

    asyncio.run(scenario())


def test_location_preview_reports_cycles_duplicate_keys_and_invalid_scopes(
    configured_app: None, database_connection: Connection
) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
            await _login(client)
            path = "/api/v1/imports/locations/preview"
            cases = [
                (
                    [
                        {
                            "import_key": "a",
                            "name": "A",
                            "parent_ref": "@b",
                            "usage_scopes": "plants",
                        },
                        {
                            "import_key": "b",
                            "name": "B",
                            "parent_ref": "@a",
                            "usage_scopes": "plants",
                        },
                    ],
                    ["conflict", "conflict"],
                ),
                (
                    [
                        {"import_key": "same", "name": "A", "usage_scopes": "plants"},
                        {"import_key": "same", "name": "B", "usage_scopes": "plants"},
                        {"name": "C", "parent_ref": "@same", "usage_scopes": "plants"},
                    ],
                    ["ambiguous_reference"] * 3,
                ),
                (
                    [
                        {"name": "A", "usage_scopes": "flowers"},
                        {"name": "B", "parent_ref": "@missing", "usage_scopes": "plants"},
                    ],
                    ["invalid", "unresolved_reference"],
                ),
            ]
            for rows, outcomes in cases:
                response = await client.post(path, content=_csv("locations", rows))
                assert response.status_code == 200
                report = response.json()
                assert report["ready"] == 0
                assert [row["outcome"] for row in report["rows"]] == outcomes
            with Session(
                bind=database_connection, join_transaction_mode="create_savepoint"
            ) as database:
                assert database.scalar(select(func.count()).select_from(Location)) == 0

    asyncio.run(scenario())


def test_apply_rolls_back_if_service_fails_mid_batch(
    configured_app: None, database_connection: Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0

    def fail_on_second(database: Session, payload: SupplierCreate) -> Supplier:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("simulated storage failure")
        return real_create_supplier(database, payload)

    monkeypatch.setattr("florabase.import_export.service.create_supplier", fail_on_second)

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
            csrf = await _login(client)
            data = _csv(
                "suppliers",
                [
                    {"name": "First supplier", "kind": "seller"},
                    {"name": "Second supplier", "kind": "nursery"},
                ],
            )
            path = "/api/v1/imports/suppliers"
            check = (await client.post(path + "/preview", content=data)).json()
            assert check["ready"] == 2
            response = await client.post(
                path + "/apply",
                content=data,
                headers={
                    "Origin": ORIGIN,
                    "X-CSRF-Token": csrf,
                    "X-Import-Confirmation": check["confirmation_token"],
                },
            )
            assert response.status_code == 500
            with Session(
                bind=database_connection, join_transaction_mode="create_savepoint"
            ) as database:
                assert database.scalar(select(func.count()).select_from(Supplier)) == 0

    asyncio.run(scenario())


def test_export_formula_safety_unicode_and_determinism(
    configured_app: None, database_connection: Connection
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        database.add(Supplier(name="=SUM(A1)", kind="seller", notes="Échange,\nsemences"))
        database.commit()

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
            assert (await client.get("/api/v1/exports/suppliers.csv")).status_code == 401
            await _login(client)
            first = await client.get("/api/v1/exports/suppliers.csv")
            second = await client.get("/api/v1/exports/suppliers.csv")
            assert first.content == second.content
            assert first.content.startswith(b"\xef\xbb\xbf")
            rows = list(csv.DictReader(io.StringIO(first.text.lstrip("\ufeff"))))
            assert rows[0]["name"] == "'=SUM(A1)"
            assert rows[0]["notes"] == "Échange,\nsemences"

    asyncio.run(scenario())


def test_direct_origin_plant_and_group_import_preserves_distinction(
    configured_app: None, database_connection: Connection
) -> None:
    from florabase.plants.model import Plant, PlantGroup

    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        identity = BotanicalIdentity(scientific_name="Citrus limon")
        database.add(identity)
        database.commit()
        identity_id = str(identity.id)

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
            csrf = await _login(client)
            headers = {"Origin": ORIGIN, "X-CSRF-Token": csrf}
            cases = [
                (
                    "plants",
                    {
                        "identity_ref": identity_id,
                        "label": "Lemon 1",
                        "direct_origin_kind": "purchased",
                        "collection_entry_date": "2020",
                    },
                ),
                (
                    "plant-groups",
                    {
                        "identity_ref": identity_id,
                        "label": "Lemon seedlings",
                        "quantity_value": "8",
                        "quantity_certainty": "approximate",
                        "collection_entry_date": "2024-06",
                    },
                ),
            ]
            for kind, row in cases:
                data = _csv(kind, [row])
                path = f"/api/v1/imports/{kind}"
                check = (await client.post(path + "/preview", content=data)).json()
                assert check["ready"] == 1
                result = await client.post(
                    path + "/apply",
                    content=data,
                    headers={**headers, "X-Import-Confirmation": check["confirmation_token"]},
                )
                assert result.status_code == 200
            with Session(
                bind=database_connection, join_transaction_mode="create_savepoint"
            ) as database:
                plant = database.scalars(select(Plant).where(Plant.label == "Lemon 1")).one()
                group = database.scalars(
                    select(PlantGroup).where(PlantGroup.label == "Lemon seedlings")
                ).one()
                assert plant.originating_sowing_id is None
                assert plant.collection_entry_date_precision == "year"
                assert group.quantity_value == 8
                assert group.quantity_is_approximate is True
                assert group.collection_entry_date_precision == "month"

    asyncio.run(scenario())


def test_normal_identity_template_resolves_existing_without_uuid(
    configured_app: None, database_connection: Connection
) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
            csrf = await _login(client)
            path = "/api/v1/imports/botanical-identities"
            data = _normal_csv(
                "botanical-identities",
                [
                    {"scientific_name": "Acmella oleracea", "common_name": "Paracress"},
                    {"scientific_name": "Allium fistulosum"},
                ],
            )
            check = (await client.post(path + "/preview", content=data)).json()
            assert check["ready"] == 2
            result = await client.post(
                path + "/apply",
                content=data,
                headers={
                    "Origin": ORIGIN,
                    "X-CSRF-Token": csrf,
                    "X-Import-Confirmation": check["confirmation_token"],
                },
            )
            assert result.status_code == 200
            changed = _normal_csv(
                "botanical-identities",
                [
                    {"scientific_name": "Acmella oleracea", "common_name": "Different name"},
                ],
            )
            report = (await client.post(path + "/preview", content=changed)).json()
            row = report["rows"][0]
            assert row["outcome"] == "needs_choice"
            assert [option["action"] for option in row["options"]] == ["use_existing"]
            assert row["options"][0]["changes"][0]["field"] == "common_name"
            with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
                assert db.scalar(select(func.count()).select_from(BotanicalIdentity)) == 2
            selected = {"2": {"record": row["options"][0]["token"]}}
            applied = await client.post(
                path + "/apply",
                json=_reviewed_body(changed, selected),
                headers={
                    "Origin": ORIGIN,
                    "X-CSRF-Token": csrf,
                    "X-Import-Confirmation": report["confirmation_token"],
                },
            )
            assert applied.status_code == 200
            assert applied.json() == {"created": 0, "already_exists": 1, "updated": 0}
            with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
                item = db.scalars(
                    select(BotanicalIdentity).where(
                        BotanicalIdentity.scientific_name == "Acmella oleracea"
                    )
                ).one()
                assert item.common_name == "Paracress"

    asyncio.run(scenario())


def test_supplier_choices_normalization_update_blank_and_stale_state(
    configured_app: None, database_connection: Connection
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        supplier = Supplier(
            name="Cercatoridisemì",
            kind="nursery",
            website="https://old.example",
            notes="Rare seed seller",
        )
        db.add(supplier)
        db.commit()
        supplier_id = supplier.id

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
            csrf = await _login(client)
            path = "/api/v1/imports/suppliers"
            data = _normal_csv(
                "suppliers",
                [
                    {
                        "name": "Cercatoridisemì",
                        "kind": " Nursery ",
                        "website": "https://new.example",
                        "notes": "",
                    }
                ],
            )
            report = (await client.post(path + "/preview", content=data)).json()
            row = report["rows"][0]
            assert row["outcome"] == "needs_choice"
            assert any("nursery" in note for note in row["normalized"])
            assert {option["action"] for option in row["options"]} == {
                "use_existing",
                "update_existing",
                "create_separate",
            }
            update = next(
                option for option in row["options"] if option["action"] == "update_existing"
            )
            assert update["changes"] == [
                {
                    "field": "website",
                    "before": "https://old.example",
                    "after": "https://new.example",
                }
            ]
            with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
                current = db.get(Supplier, supplier_id)
                assert current is not None
                assert current.website == "https://old.example"
            applied = await client.post(
                path + "/apply",
                json=_reviewed_body(data, {"2": {"record": update["token"]}}),
                headers={
                    "Origin": ORIGIN,
                    "X-CSRF-Token": csrf,
                    "X-Import-Confirmation": report["confirmation_token"],
                },
            )
            assert applied.status_code == 200
            assert applied.json()["updated"] == 1
            with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
                current = db.get(Supplier, supplier_id)
                assert current is not None
                assert current.website == "https://new.example"
                assert current.notes == "Rare seed seller"
                assert current.kind == "nursery"
            stale = (await client.post(path + "/preview", content=data)).json()
            use = next(
                option
                for option in stale["rows"][0]["options"]
                if option["action"] == "use_existing"
            )
            with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
                current = db.get(Supplier, supplier_id)
                assert current is not None
                current.phone = "+39 123"
                db.commit()
            rejected = await client.post(
                path + "/apply",
                json=_reviewed_body(data, {"2": {"record": use["token"]}}),
                headers={
                    "Origin": ORIGIN,
                    "X-CSRF-Token": csrf,
                    "X-Import-Confirmation": stale["confirmation_token"],
                },
            )
            assert rejected.status_code == 409
            fresh = (await client.post(path + "/preview", content=data)).json()
            create = next(
                option
                for option in fresh["rows"][0]["options"]
                if option["action"] == "create_separate"
            )
            separate = await client.post(
                path + "/apply",
                json=_reviewed_body(data, {"2": {"record": create["token"]}}),
                headers={
                    "Origin": ORIGIN,
                    "X-CSRF-Token": csrf,
                    "X-Import-Confirmation": fresh["confirmation_token"],
                },
            )
            assert separate.status_code == 200
            assert separate.json()["created"] == 1
            with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
                assert db.scalar(select(func.count()).select_from(Supplier)) == 2
            repeated = (await client.post(path + "/preview", content=data)).json()
            assert (
                len(
                    [
                        option
                        for option in repeated["rows"][0]["options"]
                        if option["action"] == "use_existing"
                    ]
                )
                == 2
            )
            chosen = next(
                option
                for option in repeated["rows"][0]["options"]
                if option["action"] == "use_existing" and option["candidate_id"] == str(supplier_id)
            )
            used = await client.post(
                path + "/apply",
                json=_reviewed_body(data, {"2": {"record": chosen["token"]}}),
                headers={
                    "Origin": ORIGIN,
                    "X-CSRF-Token": csrf,
                    "X-Import-Confirmation": repeated["confirmation_token"],
                },
            )
            assert used.status_code == 200
            assert used.json()["already_exists"] == 1

    asyncio.run(scenario())


def test_downloadable_examples_validate_in_documented_order(configured_app: None) -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
            csrf = await _login(client)
            for kind in IMPORT_COLUMNS:
                example = await client.get(f"/api/v1/imports/examples/{kind}.csv")
                template = await client.get(f"/api/v1/imports/templates/{kind}.csv")
                guide = await client.get(f"/api/v1/imports/formats/{kind}")
                assert example.status_code == template.status_code == guide.status_code == 200
                assert [item["field"] for item in guide.json()["fields"]] == list(
                    IMPORT_COLUMNS[kind]
                )
                assert next(csv.reader(io.StringIO(template.text.lstrip("\ufeff")))) == list(
                    IMPORT_COLUMNS[kind]
                )
                data = example_csv(kind).encode()
                path = f"/api/v1/imports/{kind}"
                report = (await client.post(path + "/preview", content=data)).json()
                assert report["ready"] == len(report["rows"]), (kind, report)
                result = await client.post(
                    path + "/apply",
                    content=data,
                    headers={
                        "Origin": ORIGIN,
                        "X-CSRF-Token": csrf,
                        "X-Import-Confirmation": report["confirmation_token"],
                    },
                )
                assert result.status_code == 200, (kind, result.text)

    asyncio.run(scenario())


def test_location_batch_key_can_use_existing_parent_without_uuid(
    configured_app: None, database_connection: Connection
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        cabinet = Location(
            name="Seed cabinet",
            supports_plants=True,
            supports_sowings=False,
            supports_seed_lots=True,
        )
        db.add(cabinet)
        db.commit()
        cabinet_id = cabinet.id

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
            csrf = await _login(client)
            data = _normal_csv(
                "locations",
                [
                    {
                        "import_key": "cabinet",
                        "name": "Seed cabinet",
                        "usage_scopes": "plants|seed_lots",
                    },
                    {
                        "import_key": "drawer",
                        "name": "Drawer 3",
                        "parent_ref": "@cabinet",
                        "usage_scopes": "seed_lots",
                    },
                ],
            )
            path = "/api/v1/imports/locations"
            report = (await client.post(path + "/preview", content=data)).json()
            assert report["rows"][0]["outcome"] == "needs_choice"
            assert report["rows"][1]["hard_blocker"] is False
            assert any("requires a choice" in value for value in report["rows"][1]["references"])
            use = next(
                option
                for option in report["rows"][0]["options"]
                if option["action"] == "use_existing"
            )
            result = await client.post(
                path + "/apply",
                json=_reviewed_body(data, {"2": {"record": use["token"]}}),
                headers={
                    "Origin": ORIGIN,
                    "X-CSRF-Token": csrf,
                    "X-Import-Confirmation": report["confirmation_token"],
                },
            )
            assert result.status_code == 200, result.text
            with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
                drawer = db.scalars(select(Location).where(Location.name == "Drawer 3")).one()
                assert drawer.parent_id == cabinet_id
                assert db.scalar(select(func.count()).select_from(Location)) == 2

    asyncio.run(scenario())


def test_ambiguous_supplier_reference_requires_exact_candidate_choice(
    configured_app: None, database_connection: Connection
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity = BotanicalIdentity(scientific_name="Acmella oleracea")
        first = Supplier(name="Twin Seeds", kind="nursery", website="https://one.example")
        second = Supplier(name="Twin Seeds", kind="seller", website="https://two.example")
        db.add_all([identity, first, second])
        db.commit()
        second_id = second.id

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
            csrf = await _login(client)
            path = "/api/v1/imports/seed-lots"
            data = _normal_csv(
                "seed-lots",
                [
                    {
                        "identity_ref": "Acmella oleracea",
                        "label": "Chosen source",
                        "source_kind": "gift_exchange",
                        "supplier_ref": "Twin Seeds",
                    }
                ],
            )
            report = (await client.post(path + "/preview", content=data)).json()
            row = report["rows"][0]
            assert row["outcome"] == "ambiguous_reference"
            assert row["hard_blocker"] is False
            assert len(row["options"]) == 2
            assert any("https://one.example" in item["details"] for item in row["options"])
            assert any("https://two.example" in item["details"] for item in row["options"])
            assert all(item["label"] == "Twin Seeds" for item in row["options"])
            with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
                assert db.scalar(select(func.count()).select_from(SeedLot)) == 0
            selected = next(
                option for option in row["options"] if option["candidate_id"] == str(second_id)
            )
            wrong = await client.post(
                path + "/apply",
                json=_reviewed_body(data, {"2": {"supplier_ref": "tampered"}}),
                headers={
                    "Origin": ORIGIN,
                    "X-CSRF-Token": csrf,
                    "X-Import-Confirmation": report["confirmation_token"],
                },
            )
            assert wrong.status_code == 409
            applied = await client.post(
                path + "/apply",
                json=_reviewed_body(data, {"2": {"supplier_ref": selected["token"]}}),
                headers={
                    "Origin": ORIGIN,
                    "X-CSRF-Token": csrf,
                    "X-Import-Confirmation": report["confirmation_token"],
                },
            )
            assert applied.status_code == 200
            with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
                lot = db.scalars(select(SeedLot).where(SeedLot.label == "Chosen source")).one()
                assert lot.supplier_id == second_id
            missing = data.replace(b"Twin Seeds", b"No Supplier")
            missing_report = (await client.post(path + "/preview", content=missing)).json()
            assert missing_report["rows"][0]["outcome"] == "unresolved_reference"
            assert missing_report["rows"][0]["hard_blocker"] is True

    asyncio.run(scenario())


def test_supplier_update_rolls_back_with_later_create_failure(
    configured_app: None, database_connection: Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        existing = Supplier(name="Existing", kind="seller", website="https://old.example")
        db.add(existing)
        db.commit()
        existing_id = existing.id

    def fail_create(_database: Session, _payload: SupplierCreate) -> Supplier:
        raise RuntimeError("simulated later failure")

    monkeypatch.setattr("florabase.import_export.service.create_supplier", fail_create)

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
            csrf = await _login(client)
            data = _normal_csv(
                "suppliers",
                [
                    {"name": "Existing", "kind": "seller", "website": "https://new.example"},
                    {"name": "New", "kind": "nursery"},
                ],
            )
            path = "/api/v1/imports/suppliers"
            report = (await client.post(path + "/preview", content=data)).json()
            update = next(
                option
                for option in report["rows"][0]["options"]
                if option["action"] == "update_existing"
            )
            result = await client.post(
                path + "/apply",
                json=_reviewed_body(data, {"2": {"record": update["token"]}}),
                headers={
                    "Origin": ORIGIN,
                    "X-CSRF-Token": csrf,
                    "X-Import-Confirmation": report["confirmation_token"],
                },
            )
            assert result.status_code == 500
            with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
                current = db.get(Supplier, existing_id)
                assert current is not None
                assert current.website == "https://old.example"
                assert db.scalar(select(func.count()).select_from(Supplier)) == 1

    asyncio.run(scenario())
