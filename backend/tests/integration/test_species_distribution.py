import asyncio
from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch
from uuid import uuid7

import httpx
import pytest
from sqlalchemy import Connection, event, text
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.explore.service import get_identity, list_identities
from florabase.external_botany.model import ExternalTaxonLink
from florabase.harvests.inventory_schemas import InventoryWrite
from florabase.harvests.inventory_service import correct
from florabase.main import app
from florabase.plants.model import Plant, PlantGroup, PlantGroupLifecycle, PlantLifecycle
from florabase.seed_lots.model import SeedLot, SeedLotLifecycle
from florabase.sowings.model import Sowing, SowingLifecycle

from .test_harvest_inventory import setup as inventory_setup
from .test_supplier_api import ORIGIN, request
from .test_supplier_api import authenticated_browser as authenticated_browser

pytestmark = pytest.mark.integration


def identity(db: Session, label: str = "Species") -> BotanicalIdentity:
    result = BotanicalIdentity(scientific_name=f"{label} {uuid7().hex}")
    db.add(result)
    db.flush()
    return result


@pytest.mark.parametrize(
    ("model", "states"),
    [(SeedLot, SeedLotLifecycle), (Plant, PlantLifecycle), (PlantGroup, PlantGroupLifecycle)],
)
def test_every_direct_lifecycle(database_connection: Connection, model: Any, states: Any) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        for state in states:
            taxon = identity(db)
            record = model(botanical_identity_id=taxon.id, lifecycle=state.value)
            if model in (Plant, PlantGroup):
                record.direct_origin_kind = "unknown"
            db.add(record)
            db.flush()
            value = get_identity(db, taxon.id, "all")
            assert value is not None
            living = model in (Plant, PlantGroup) and state.value == "active"
            current = state.value == "active"
            assert value.representation == (
                "living" if living else "current" if current else "historical"
            )
            assert value.current_records == int(current)
            assert value.living_records == int(living)
            assert value.retained_records == 1
            for scope in ("living", "current", "historical"):
                selected = get_identity(db, taxon.id, scope)
                assert selected is not None
                assert (
                    selected.matches_scope
                    == {"living": living, "current": current, "historical": not current}[scope]
                )


@pytest.mark.parametrize("state", list(SowingLifecycle))
def test_sowing_uses_exact_seedlot_identity(
    database_connection: Connection, state: SowingLifecycle
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        taxon = identity(db)
        seed = SeedLot(botanical_identity_id=taxon.id, lifecycle="exhausted")
        db.add(seed)
        db.flush()
        db.add(Sowing(seed_lot_id=seed.id, lifecycle=state.value))
        db.flush()
        value = get_identity(db, taxon.id, "all")
        assert value is not None
        assert value.retained_records == 2
        assert value.current_records == int(state == SowingLifecycle.ACTIVE)
        assert value.living_records == 0


@pytest.mark.parametrize("unknown", [False, True])
@pytest.mark.parametrize("group", [False, True])
def test_inventory_active_unknown_depleted_and_harvest_only(
    database_connection: Connection, unknown: bool, group: bool
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        inventory, _ = inventory_setup(db, unknown=unknown, group=group)
        # Both retained sources are made terminal so inventory is the only current material.
        db.execute(text("UPDATE plant_groups SET lifecycle='dead'"))
        value = list_identities(db).items[0]
        assert value.representation == "current"
        assert value.current_records == 1
        assert value.living_records == 0
        assert value.retained_records == 3
        correct(db, inventory.id, InventoryWrite(state="depleted", quantity=None))
        assert list_identities(db).items[0].representation == "historical"
        db.delete(inventory)
        db.flush()
        value = list_identities(db).items[0]
        assert value.representation == "historical"
        assert value.retained_records == 2


def test_scopes_counts_links_search_pagination_constant_queries(
    database_connection: Connection,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        reference = identity(db, "Reference")
        a, b, c = [identity(db, name) for name in ("Aloe", "Basil", "Cress")]
        a.common_name = "Local %_ name"
        a.cultivar_name = "Long cultivar"
        seed = SeedLot(botanical_identity_id=a.id)
        db.add_all(
            [
                seed,
                SeedLot(botanical_identity_id=a.id),
                Plant(botanical_identity_id=a.id, direct_origin_kind="unknown"),
                PlantGroup(botanical_identity_id=a.id, direct_origin_kind="unknown"),
                SeedLot(botanical_identity_id=b.id),
                Plant(botanical_identity_id=c.id, direct_origin_kind="unknown", lifecycle="dead"),
            ]
        )
        db.flush()
        db.add(Sowing(seed_lot_id=seed.id, lifecycle="completed"))
        now = datetime.now(UTC)
        for taxon, provider in ((a, "gbif"), (b, "unsupported")):
            db.add(
                ExternalTaxonLink(
                    botanical_identity_id=taxon.id,
                    provider=provider,
                    external_id="opaque-Q2M4",
                    scientific_name=taxon.scientific_name,
                    linked_at=now,
                    last_refreshed_at=now,
                    last_refresh_attempt_at=now,
                    refresh_error="provider_unavailable",
                )
            )
        db.flush()
        selects: list[str] = []

        def count(
            _conn: Any, _cursor: Any, statement: str, _params: Any, _context: Any, _many: Any
        ) -> None:
            if statement.lstrip().upper().startswith("SELECT"):
                selects.append(statement)

        event.listen(database_connection, "before_cursor_execute", count)
        try:
            for limit in (1, 50):
                selects.clear()
                page = list_identities(db, limit=limit)
                assert len(selects) == 2
                assert page.total == 3
                assert page.occurrence_ready == 1
                assert len(page.items) == min(limit, 3)
            assert [v.id for v in page.items] == [a.id, b.id, c.id]
            assert page.items[0].retained_records == 5
            assert page.items[0].current_records == 4
            assert page.items[0].living_records == 2
            assert [v.occurrence_eligibility for v in page.items] == [
                "available",
                "incompatible",
                "not_linked",
            ]
            assert list_identities(db, scope="living").total == 1
            assert list_identities(db, scope="current").total == 2
            assert list_identities(db, scope="historical").items[0].id == c.id
            assert list_identities(db, offset=1, limit=1).items[0].id == b.id
            assert list_identities(db, offset=9).total == 3
            assert get_identity(db, reference.id, "all") is None
            for query in (
                "aLOe",
                "%_",
                "Long CULTIVAR",
                f"{a.scientific_name} \u2018Long cultivar\u2019",
            ):
                assert list_identities(db, q=query).items[0].id == a.id
            assert list_identities(db, q="not present").total == 0
        finally:
            event.remove(database_connection, "before_cursor_execute", count)


def test_own_identity_overrides_produced_lineage_and_names_do_not_merge(
    database_connection: Connection,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        producer_identity = identity(db)
        child_identity = identity(db)
        child_identity.scientific_name = producer_identity.scientific_name
        child_identity.cultivar_name = "Different identity"
        plant = Plant(
            botanical_identity_id=producer_identity.id,
            direct_origin_kind="unknown",
            lifecycle="dead",
        )
        db.add(plant)
        db.flush()
        db.add(
            SeedLot(
                botanical_identity_id=child_identity.id,
                source_kind="collection_produced",
                producer_plant_id=plant.id,
            )
        )
        db.flush()
        assert list_identities(db, scope="historical").items[0].id == producer_identity.id
        assert list_identities(db, scope="current").items[0].id == child_identity.id
        assert list_identities(db).total == 2


def test_authenticated_local_api_bounds_and_no_provider_calls(
    authenticated_browser: tuple[str, str],
) -> None:
    cookie, _ = authenticated_browser
    endpoint = "/api/v1/explore/species-distribution/identities"
    assert request("GET", endpoint)[0] == 401
    with patch(
        "florabase.external_botany.provider.GbifBotanicalProvider.occurrence_count",
        side_effect=AssertionError("no provider fanout"),
    ):
        assert request("GET", endpoint, headers={"Cookie": cookie, "Origin": ORIGIN})[0] == 200
        for query in ("scope=dead", "limit=101", "offset=-1", "q=" + "x" * 201):

            async def query_request(value: str) -> int:
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url=ORIGIN
                ) as client:
                    return (
                        await client.get(endpoint + "?" + value, headers={"Cookie": cookie})
                    ).status_code

            assert asyncio.run(query_request(query)) == 422
        assert request("GET", endpoint + f"/{uuid7()}", headers={"Cookie": cookie})[0] == 404
