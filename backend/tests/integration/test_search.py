import asyncio
from uuid import UUID

import httpx
import pytest
from sqlalchemy import Connection, select
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_profiles.model import BotanicalProfile
from florabase.events.model import Event
from florabase.geographic_places.model import GeographicPlace
from florabase.locations.model import Location
from florabase.main import app
from florabase.plants.model import Plant, PlantGroup
from florabase.provenance_sites.model import ProvenanceSite
from florabase.search.schemas import SearchKind
from florabase.search.service import SearchFilters, search
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing
from florabase.suppliers.model import Supplier
from integration.test_seed_lot_api import request

pytestmark = pytest.mark.integration
pytest_plugins = ["integration.test_seed_lot_api"]


@pytest.fixture
def records(database_connection: Connection) -> dict[str, UUID]:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        root = database.scalar(select(GeographicPlace).where(GeographicPlace.parent_id.is_(None)))
        assert root is not None
        identity = BotanicalIdentity(
            scientific_name="Acmella oleracea", common_name="Toothache plant"
        )
        supplier = Supplier(name="Cercatoridisemì", kind="seller")
        parent = Location(name="Glasshouse")
        database.add_all([identity, supplier, parent])
        database.flush()
        child = Location(name="Warm bench", parent_id=parent.id)
        place = GeographicPlace(name="Alta valley", parent_id=root.id, place_kind="custom")
        database.add_all([child, place])
        database.flush()
        site = ProvenanceSite(name="Riverside site", geographic_place_id=place.id)
        profile = BotanicalProfile(botanical_identity_id=identity.id, description="Edible flowers")
        database.add_all([site, profile])
        database.flush()
        seed = SeedLot(
            botanical_identity_id=identity.id,
            label="Summer packet",
            supplier_id=supplier.id,
            location_id=child.id,
            material_provenance_place_id=place.id,
            provenance_site_id=site.id,
            acquisition_date_precision="year",
            acquisition_date_year=2024,
        )
        database.add(seed)
        database.flush()
        sowing = Sowing(seed_lot_id=seed.id, label="Tray one", location_id=child.id)
        plant = Plant(
            botanical_identity_id=identity.id,
            direct_origin_kind="unknown",
            label="North plant",
            location_id=child.id,
        )
        group = PlantGroup(
            botanical_identity_id=identity.id,
            direct_origin_kind="unknown",
            label="South group",
            location_id=child.id,
        )
        database.add_all([sowing, plant, group])
        database.flush()
        event = Event(plant_id=plant.id, kind="observation", notes="Bright flowers")
        database.add(event)
        database.commit()
        return {
            "identity": identity.id,
            "supplier": supplier.id,
            "parent": parent.id,
            "child": child.id,
            "place": place.id,
            "site": site.id,
            "seed": seed.id,
            "sowing": sowing.id,
            "plant": plant.id,
            "group": group.id,
            "event": event.id,
        }


def _ids(result: object, kind: SearchKind) -> list[UUID]:
    from florabase.search.schemas import SearchResponse

    assert isinstance(result, SearchResponse)
    return [item.id for group in result.groups if group.kind == kind for item in group.items]


def test_search_is_authenticated_and_empty_request_does_not_scan(
    authenticated_browser: tuple[str, str],
    database_connection: Connection,
) -> None:
    assert request("GET", "/api/v1/search")[0] == 401
    assert request("GET", "/api/v1/search", headers={"cookie": authenticated_browser[0]})[2] == {
        "query": "",
        "total": 0,
        "offset": 0,
        "limit": 20,
        "groups": [],
    }
    with Session(bind=database_connection) as database:
        assert search(database, "", SearchFilters()).groups == []


def _api_get(path: str, cookie: str) -> tuple[int, dict[str, object]]:
    async def execute() -> tuple[int, dict[str, object]]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://florabase.example"
        ) as client:
            response = await client.get(path, headers={"cookie": cookie})
            return response.status_code, response.json()

    return asyncio.run(execute())


def test_search_api_validates_filters_and_returns_typed_results(
    records: dict[str, UUID],
    authenticated_browser: tuple[str, str],
) -> None:
    cookie, _ = authenticated_browser
    status, result = _api_get("/api/v1/search?q=%20Toothache%20&kind=seed_lot", cookie)
    assert status == 200
    assert result["query"] == "Toothache"
    assert result["total"] == 1
    groups = result["groups"]
    assert isinstance(groups, list)
    assert groups[0]["kind"] == "seed_lot"
    assert groups[0]["items"][0]["id"] == str(records["seed"])
    assert _api_get("/api/v1/search?kind=plant&lifecycle=exhausted", cookie)[0] == 422
    assert _api_get("/api/v1/search?year=2024", cookie)[0] == 422
    assert _api_get("/api/v1/search?kind=event&event_kind=observation", cookie)[0] == 200


def test_search_groups_relationships_filters_partial_dates_and_pagination(
    records: dict[str, UUID],
    database_connection: Connection,
) -> None:
    with Session(bind=database_connection) as database:
        result = search(database, "  toothache  ".strip(), SearchFilters())
        assert _ids(result, SearchKind.BOTANICAL_IDENTITY) == [records["identity"]]
        for kind, key in (
            (SearchKind.SEED_LOT, "seed"),
            (SearchKind.SOWING, "sowing"),
            (SearchKind.PLANT, "plant"),
            (SearchKind.PLANT_GROUP, "group"),
            (SearchKind.EVENT, "event"),
        ):
            assert _ids(result, kind) == [records[key]]
        supplier = search(database, "cercatoridisemì", SearchFilters())
        assert _ids(supplier, SearchKind.SUPPLIER) == [records["supplier"]]
        assert _ids(supplier, SearchKind.SEED_LOT) == [records["seed"]]
        assert _ids(supplier, SearchKind.SOWING) == [records["sowing"]]
        location = search(database, "glasshouse", SearchFilters())
        assert records["seed"] in _ids(location, SearchKind.SEED_LOT)
        assert records["plant"] in _ids(location, SearchKind.PLANT)
        knowledge = search(database, "edible flowers", SearchFilters())
        assert _ids(knowledge, SearchKind.BOTANICAL_PROFILE) == [records["identity"]]
        assert _ids(knowledge, SearchKind.EVENT) == []
        observation = search(database, "bright flowers", SearchFilters())
        assert _ids(observation, SearchKind.EVENT) == [records["event"]]
        assert _ids(observation, SearchKind.BOTANICAL_PROFILE) == []

        scoped = search(
            database,
            "",
            SearchFilters(
                kinds=(SearchKind.SEED_LOT,),
                identity_id=records["identity"],
                location_id=records["parent"],
                supplier_id=records["supplier"],
                provenance_place_id=records["place"],
                provenance_site_id=records["site"],
                lifecycle="active",
                year=2024,
            ),
        )
        assert _ids(scoped, SearchKind.SEED_LOT) == [records["seed"]]
        assert scoped.total == 1
        assert _ids(
            search(
                database,
                "",
                SearchFilters(kinds=(SearchKind.SEED_LOT,), provenance_place_id=records["place"]),
            ),
            SearchKind.SEED_LOT,
        ) == [records["seed"]]
        assert (
            _ids(
                search(
                    database,
                    "",
                    SearchFilters(kinds=(SearchKind.PLANT,), provenance_place_id=records["place"]),
                ),
                SearchKind.PLANT,
            )
            == []
        )
        assert (
            _ids(
                search(database, "", SearchFilters(kinds=(SearchKind.SEED_LOT,), year=2023)),
                SearchKind.SEED_LOT,
            )
            == []
        )

        for number in range(25):
            database.add(
                SeedLot(botanical_identity_id=records["identity"], label=f"Packet {number:02}")
            )
        database.flush()
        filters = SearchFilters(kinds=(SearchKind.SEED_LOT,))
        first = search(database, "packet", filters, limit=10)
        second = search(database, "packet", filters, offset=10, limit=10)
        assert first.total == second.total == 26
        assert len(_ids(first, SearchKind.SEED_LOT)) == len(_ids(second, SearchKind.SEED_LOT)) == 10
        assert not set(_ids(first, SearchKind.SEED_LOT)) & set(_ids(second, SearchKind.SEED_LOT))
        third = search(database, "packet", filters, offset=20, limit=10)
        all_ids = (
            _ids(first, SearchKind.SEED_LOT)
            + _ids(second, SearchKind.SEED_LOT)
            + _ids(third, SearchKind.SEED_LOT)
        )
        assert len(all_ids) == len(set(all_ids)) == 26
        assert _ids(first, SearchKind.SEED_LOT) == _ids(
            search(database, "packet", filters, limit=10), SearchKind.SEED_LOT
        )


def test_search_keeps_one_hit_per_record_and_minimizes_payloads(
    records: dict[str, UUID],
    database_connection: Connection,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        plant = database.get(Plant, records["plant"])
        group = database.get(PlantGroup, records["group"])
        assert plant is not None
        assert group is not None
        database.add_all(
            [
                Event(plant_id=plant.id, kind="flowering", notes="Private plant note"),
                Event(plant_group_id=group.id, kind="observation", notes="Private group note"),
            ]
        )
        database.flush()

        matching_identity = search(
            database,
            "toothache",
            SearchFilters(kinds=(SearchKind.PLANT, SearchKind.PLANT_GROUP)),
        )
        assert _ids(matching_identity, SearchKind.PLANT) == [records["plant"]]
        assert _ids(matching_identity, SearchKind.PLANT_GROUP) == [records["group"]]

        plant_event = search(
            database,
            "private plant note",
            SearchFilters(kinds=(SearchKind.EVENT,)),
        )
        group_event = search(
            database,
            "private group note",
            SearchFilters(kinds=(SearchKind.EVENT,)),
        )
        plant_hit = next(item for group_result in plant_event.groups for item in group_result.items)
        group_hit = next(item for group_result in group_event.groups for item in group_result.items)
        assert plant_hit.href == f"#/plants/{plant.id}?tab=events"
        assert group_hit.href == f"#/plant-groups/{group.id}?tab=events"
        assert "Private" not in plant_hit.model_dump_json()
        assert "Private" not in group_hit.model_dump_json()
        assert plant_hit.context == "Acmella oleracea"
        assert group_hit.context == "Acmella oleracea"

        related_events = search(database, "toothache", SearchFilters(kinds=(SearchKind.EVENT,)))
        event_ids = _ids(related_events, SearchKind.EVENT)
        assert len(event_ids) == len(set(event_ids)) == 3

        plant.label = None
        group.label = None
        database.flush()
        unlabeled_plant_event = search(
            database, "private plant note", SearchFilters(kinds=(SearchKind.EVENT,))
        )
        unlabeled_group_event = search(
            database, "private group note", SearchFilters(kinds=(SearchKind.EVENT,))
        )
        unlabeled_plant_hit = unlabeled_plant_event.groups[0].items[0]
        unlabeled_group_hit = unlabeled_group_event.groups[0].items[0]
        assert unlabeled_plant_hit.title == "Flowering · Acmella oleracea"
        assert unlabeled_group_hit.title == "Observation · Acmella oleracea"
        assert unlabeled_plant_hit.context == unlabeled_group_hit.context == "Acmella oleracea"


def test_search_combined_filters_use_recorded_semantics_and_stable_order(
    records: dict[str, UUID],
    database_connection: Connection,
) -> None:
    with Session(bind=database_connection) as database:
        filters = SearchFilters(
            kinds=(SearchKind.SEED_LOT,),
            identity_id=records["identity"],
            location_id=records["parent"],
            supplier_id=records["supplier"],
            provenance_place_id=records["place"],
            provenance_site_id=records["site"],
            year=2024,
        )
        first = search(database, "summer", filters)
        repeated = search(database, "summer", filters)
        assert _ids(first, SearchKind.SEED_LOT) == [records["seed"]]
        assert first.model_dump() == repeated.model_dump()
        assert first.total == 1

        # The Location filter matches the exact selected node and its descendants.
        child_location = search(
            database,
            "",
            SearchFilters(kinds=(SearchKind.SEED_LOT,), location_id=records["child"]),
        )
        assert _ids(child_location, SearchKind.SEED_LOT) == [records["seed"]]
