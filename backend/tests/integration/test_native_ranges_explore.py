import asyncio
from typing import Any
from unittest.mock import patch
from uuid import uuid7

import httpx
import pytest
from sqlalchemy import Connection, event, select, text
from sqlalchemy.orm import Session

from florabase.botanical_profiles.service import add_botanical_native_range
from florabase.explore import native_ranges, service
from florabase.geographic_places.model import GeographicPlace
from florabase.geographic_places.schemas import GeographicPlaceCreate, GeographicPlaceUpdate
from florabase.geographic_places.service import create_geographic_place, update_geographic_place
from florabase.harvests.inventory_schemas import InventoryWrite
from florabase.harvests.inventory_service import correct
from florabase.main import app
from florabase.plants.model import Plant, PlantGroup, PlantGroupLifecycle, PlantLifecycle
from florabase.seed_lots.model import SeedLot, SeedLotLifecycle
from florabase.sowings.model import Sowing, SowingLifecycle

from .test_harvest_inventory import setup as inventory_setup
from .test_species_distribution import identity
from .test_supplier_api import ORIGIN, request
from .test_supplier_api import authenticated_browser as authenticated_browser

pytestmark = pytest.mark.integration


def place(db: Session, code: str) -> GeographicPlace:
    result = db.scalar(select(GeographicPlace).where(GeographicPlace.source_code == code))
    assert result is not None
    return result


def test_exact_ranges_union_before_count_and_query_bounds(database_connection: Connection) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        a, b, c, d, e, no_range, historical, reference = [
            identity(db, name) for name in ("A", "B", "C", "D", "E", "F", "H", "Reference")
        ]
        a.common_name = "Literal %_ local"
        a.cultivar_name = "Broad and precise"
        for taxon in (a, c, d):
            db.add(Plant(botanical_identity_id=taxon.id, direct_origin_kind="unknown"))
        db.add_all(
            [
                Plant(botanical_identity_id=a.id, direct_origin_kind="unknown"),
                SeedLot(botanical_identity_id=b.id),
                SeedLot(botanical_identity_id=no_range.id),
                SeedLot(botanical_identity_id=e.id, lifecycle="exhausted"),
                SeedLot(botanical_identity_id=historical.id, lifecycle="exhausted"),
            ]
        )
        db.flush()
        custom = create_geographic_place(
            db,
            GeographicPlaceCreate(name="An exact long custom place", parent_id=place(db, "IT").id),
        )
        for taxon, codes in (
            (a, ["005"]),
            (b, ["BR"]),
            (c, ["005", "BR"]),
            (d, ["IT", "TH"]),
            (historical, ["TH"]),
            (reference, ["BR"]),
        ):
            for code in codes:
                add_botanical_native_range(db, taxon.id, place(db, code).id)
        add_botanical_native_range(db, e.id, custom.id)
        selects: list[str] = []

        def count(_conn: Any, _cursor: Any, sql: str, _params: Any, _ctx: Any, _many: Any) -> None:
            if sql.lstrip().upper().startswith(("SELECT", "WITH")):
                selects.append(sql)

        event.listen(database_connection, "before_cursor_execute", count)
        try:
            for limit in (1, 50):
                selects.clear()
                page = native_ranges.list_identities(db, limit=limit)
                assert len(selects) == 2
                assert page.total == 7
                assert len(page.items) == min(7, limit)
                selects.clear()
                overview = native_ranges.overview(db, limit=limit)
                assert len(selects) == 4
                assert (overview.represented, overview.with_range, overview.without_range) == (
                    7,
                    6,
                    1,
                )
                assert overview.places_total == 5
                assert len(overview.places) == min(5, limit)
                units = {unit.source_code: unit.identity_count for unit in overview.territories}
                assert units["BR"] == 3  # A broad, B precise, C broad+precise: never four.
                assert units["AR"] == 2  # A and C's broad stored South America.
                assert units["IT"] == 1  # Custom under Italy does NOT shade Italy.
                assert units["TH"] == 2
                selects.clear()
                selected = native_ranges.selected(db, c.id, limit=limit)
                assert len(selects) == 4
                assert selected is not None
                assert selected.total == 2
                assert all(unit.identity_count == 1 for unit in selected.territories)
            assert {p.name: p.identity_count for p in overview.places}["South America"] == 2
            assert page.items[5].native_range_count == 0
            assert native_ranges.selected(db, reference.id) is None
            assert native_ranges.selected(db, uuid7()) is None
            assert native_ranges.overview(db, scope="living").with_range == 3
            assert native_ranges.overview(db, scope="current").represented == 5
            assert native_ranges.overview(db, scope="historical").with_range == 2
            assert native_ranges.overview(db, with_range=True).without_range == 0
            assert native_ranges.overview(db, q="%_").represented == 1
            assert native_ranges.list_identities(db, q="broad AND precise").items[0].id == a.id
            assert native_ranges.list_identities(db, offset=1, limit=1).items[0].id == b.id
            assert native_ranges.overview(db, offset=99).places == []
            empty = native_ranges.selected(db, no_range.id)
            assert empty is not None
            assert empty.total == 0
            assert empty.ranges == []
            assert empty.territories == []
            custom_selection = native_ranges.selected(db, e.id, "living")
            assert custom_selection is not None
            assert not custom_selection.identity.matches_scope
            assert custom_selection.ranges[0].display_path.endswith(
                "Italy → An exact long custom place"
            )
            assert custom_selection.territories == []
            update_geographic_place(
                db, custom.id, GeographicPlaceUpdate(name="Renamed", parent_id=place(db, "BR").id)
            )
            updated = native_ranges.selected(db, e.id)
            assert updated is not None
            assert updated.ranges[0].display_path.endswith("Brazil → Renamed")
            assert updated.territories == []
        finally:
            event.remove(database_connection, "before_cursor_execute", count)


def test_all_lifecycles_have_exact_distribution_parity(database_connection: Connection) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        for model, states in (
            (SeedLot, SeedLotLifecycle),
            (Plant, PlantLifecycle),
            (PlantGroup, PlantGroupLifecycle),
        ):
            for state in states:
                taxon = identity(db)
                record = model(botanical_identity_id=taxon.id, lifecycle=state.value)
                if isinstance(record, (Plant, PlantGroup)):
                    record.direct_origin_kind = "unknown"
                db.add(record)
        for sowing_state in SowingLifecycle:
            taxon = identity(db)
            seed = SeedLot(botanical_identity_id=taxon.id, lifecycle="exhausted")
            db.add(seed)
            db.flush()
            db.add(Sowing(seed_lot_id=seed.id, lifecycle=sowing_state.value))
        db.flush()
        for scope in ("all", "living", "current", "historical"):
            distribution = service.list_identities(db, scope=scope, limit=100)
            ranges = native_ranges.list_identities(db, scope=scope, limit=100)
            assert ranges.total == distribution.total
            assert [v.id for v in ranges.items] == [v.id for v in distribution.items]
            for native, occurrence in zip(ranges.items, distribution.items, strict=True):
                assert native.model_dump(
                    exclude={"native_range_count", "matches_filters"}
                ) == occurrence.model_dump(exclude={"occurrence_eligibility", "external_taxon_id"})


@pytest.mark.parametrize("unknown", [False, True])
@pytest.mark.parametrize("group", [False, True])
def test_inventory_representation_parity(
    database_connection: Connection, unknown: bool, group: bool
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        inventory, _ = inventory_setup(db, unknown=unknown, group=group)
        db.execute(text("UPDATE plant_groups SET lifecycle='dead'"))
        assert native_ranges.list_identities(db).items[0].representation == "current"
        correct(db, inventory.id, InventoryWrite(state="depleted", quantity=None))
        assert native_ranges.list_identities(db).items[0].representation == "historical"
        db.delete(inventory)
        db.flush()
        assert native_ranges.list_identities(db).items[0].representation == "historical"


def test_world_through_cldr_grouping_and_unmapped_codes(database_connection: Connection) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        taxon = identity(db)
        db.add(SeedLot(botanical_identity_id=taxon.id))
        db.flush()
        add_botanical_native_range(db, taxon.id, place(db, "001").id)
        overview = native_ranges.overview(db)
        assert len(overview.territories) == 250
        assert "AQ" in {unit.source_code for unit in overview.territories}
        other = identity(db)
        db.add(SeedLot(botanical_identity_id=other.id))
        db.flush()
        add_botanical_native_range(db, other.id, place(db, "QO").id)
        selected = native_ranges.selected(db, other.id)
        assert selected is not None
        assert selected.total == 1
        assert selected.ranges[0].source_code_type == "cldr_territory"
        assert selected.territories == []


@patch(
    "florabase.external_botany.provider.GbifBotanicalProvider.occurrence_count",
    side_effect=AssertionError("No provider calls"),
)
def test_authenticated_api_bounds_and_no_provider(
    provider: Any, authenticated_browser: tuple[str, str]
) -> None:
    cookie, _ = authenticated_browser
    base = "/api/v1/explore/native-ranges"
    for path in ("/identities", "/overview", "/selection", f"/identities/{uuid7()}"):
        assert request("GET", base + path)[0] == 401
    for path in ("/identities", "/overview"):
        assert request("GET", base + path, headers={"Cookie": cookie})[0] == 200
        for query in (
            "scope=dead",
            "q=" + "x" * 201,
            "offset=-1",
            "limit=101",
            "with_range=bad",
            "record=event",
        ):

            async def query_status(value: str) -> int:
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url=ORIGIN
                ) as client:
                    return (await client.get(base + value, headers={"Cookie": cookie})).status_code

            assert asyncio.run(query_status(path + "?" + query)) == 422
    assert request("GET", base + f"/identities/{uuid7()}", headers={"Cookie": cookie})[0] == 404

    async def selection_status(query: str) -> int:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=ORIGIN
        ) as client:
            return (
                await client.get(base + "/selection?" + query, headers={"Cookie": cookie})
            ).status_code

    assert asyncio.run(selection_status("identity=" + str(uuid7()))) == 200
    assert asyncio.run(selection_status("identity=bad")) == 422
    assert (
        asyncio.run(selection_status("&".join("identity=" + str(uuid7()) for _ in range(21))))
        == 422
    )
    assert asyncio.run(selection_status("identity=" + str(uuid7()) + "&record=bad")) == 422
    provider.assert_not_called()


def test_category_or_status_selection_and_constant_queries(database_connection: Connection) -> None:
    from itertools import combinations

    from florabase.explore.schemas import CollectionRecordCategory as Category

    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        both, seed_only, dormant, sown, grouped = [
            identity(db, name) for name in ("Both", "Seed", "Dormant", "Sown", "Grouped")
        ]
        db.add_all(
            [
                Plant(botanical_identity_id=both.id, direct_origin_kind="unknown"),
                SeedLot(botanical_identity_id=both.id, lifecycle="exhausted"),
                SeedLot(botanical_identity_id=seed_only.id),
                SeedLot(botanical_identity_id=dormant.id, lifecycle="exhausted"),
                PlantGroup(botanical_identity_id=grouped.id, direct_origin_kind="unknown"),
            ]
        )
        sowing_seed = SeedLot(botanical_identity_id=sown.id, lifecycle="exhausted")
        db.add(sowing_seed)
        db.flush()
        db.add(Sowing(seed_lot_id=sowing_seed.id))
        inventory, _ = inventory_setup(db)
        db.flush()
        inventory_identity = service.list_identities(db).items
        stored_id = next(
            item.id
            for item in inventory_identity
            if item.id not in {both.id, seed_only.id, dormant.id, sown.id, grouped.id}
        )
        for taxon_id in (both.id, seed_only.id, dormant.id, sown.id, grouped.id, stored_id):
            add_botanical_native_range(db, taxon_id, place(db, "BR").id)
        add_botanical_native_range(db, both.id, place(db, "005").id)
        add_botanical_native_range(db, seed_only.id, place(db, "IT").id)
        all_sets = {
            Category.SEED_LOT: {both.id, seed_only.id, dormant.id, sown.id},
            Category.SOWING: {sown.id},
            Category.PLANT: {both.id, stored_id},
            Category.PLANT_GROUP: {grouped.id, stored_id},
            Category.STORED_MATERIAL: {stored_id},
        }
        # Every single type and every OR pair uses identical directory/overview eligibility.
        for size in (1, 2, 5):
            for categories in combinations(Category, size):
                expected = set().union(*(all_sets[category] for category in categories))
                result = native_ranges.list_identities(db, record=categories)
                assert {item.id for item in result.items} == expected
                assert native_ranges.overview(db, record=categories).represented == len(expected)
        assert native_ranges.overview(db, record=[]).represented == 6
        assert (
            native_ranges.overview(db, scope="living", record=[Category.SEED_LOT]).represented == 0
        )
        assert {
            item.id
            for item in native_ranges.list_identities(
                db, scope="current", record=[Category.SEED_LOT]
            ).items
        } == {seed_only.id}
        assert {
            item.id
            for item in native_ranges.list_identities(
                db, scope="historical", record=[Category.SEED_LOT]
            ).items
        } == {dormant.id}
        assert (
            native_ranges.overview(
                db, q="Both", record=[Category.PLANT], with_range=True
            ).represented
            == 1
        )
        assert (
            native_ranges.overview(
                db, q="Both", record=[Category.SEED_LOT], scope="current"
            ).represented
            == 0
        )
        missing = uuid7()
        statements: list[str] = []

        def count(_conn: Any, _cursor: Any, sql: str, _params: Any, _ctx: Any, _many: Any) -> None:
            if sql.lstrip().upper().startswith(("SELECT", "WITH")):
                statements.append(sql)

        event.listen(database_connection, "before_cursor_execute", count)
        try:
            for ids in ([both.id], [both.id, seed_only.id, missing, both.id]):
                statements.clear()
                selected = native_ranges.selection(db, ids)
                assert len(statements) == 2
                units = {unit.source_code: unit for unit in selected.territories}
                assert units["BR"].identity_count == len(set(ids) - {missing})
                assert set(units["BR"].identity_ids) == set(ids) - {missing}
                assert units["AR"].identity_ids == [both.id]
            assert selected.missing_ids == [missing]
            statements.clear()
            bounded = native_ranges.selection(
                db, [both.id, seed_only.id, *[uuid7() for _ in range(18)]]
            )
            assert len(statements) == 2
            assert len(bounded.missing_ids) == 18
            filtered = native_ranges.selection(
                db, [both.id, seed_only.id], scope="current", record=[Category.SEED_LOT]
            )
            assert {item.id for item in filtered.identities if item.matches_filters} == {
                seed_only.id
            }
            assert all(unit.identity_ids == [seed_only.id] for unit in filtered.territories)
            exact = native_ranges.selected(db, both.id, "current", record=[Category.SEED_LOT])
            assert exact is not None
            assert not exact.identity.matches_filters
            assert exact.territories == []
            assert native_ranges.selection(db, [both.id], q="unmatched").territories == []
            assert native_ranges.selection(db, []).territories == []
        finally:
            event.remove(database_connection, "before_cursor_execute", count)
        correct(db, inventory.id, InventoryWrite(state="depleted", quantity=None))
        assert (
            native_ranges.overview(
                db, scope="current", record=[Category.STORED_MATERIAL]
            ).represented
            == 0
        )
        assert (
            native_ranges.overview(db, scope="all", record=[Category.STORED_MATERIAL]).represented
            == 1
        )
