from collections.abc import Sequence
from uuid import uuid7

import pytest
from sqlalchemy import Connection, event, select
from sqlalchemy.orm import Session

from florabase.botanical_identities.model import BotanicalIdentity
from florabase.geographic_places.model import GeographicPlace
from florabase.plants.model import Plant, PlantGroup
from florabase.plants.schemas import PlantGroupResponse, PlantResponse
from florabase.plants.service import (
    list_plant_groups,
    list_plants,
    plant_group_responses,
    plant_responses,
)
from florabase.provenance_sites.model import ProvenanceSite
from florabase.seed_lots.model import SeedLot
from florabase.seed_lots.schemas import SeedLotResponse
from florabase.seed_lots.service import list_seed_lots, responses

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("kind", ["seed", "plant", "group"])
def test_geography_is_loaded_once_at_both_directory_sizes(
    database_connection: Connection, kind: str
) -> None:
    with Session(bind=database_connection) as database:
        root = database.scalar(select(GeographicPlace).where(GeographicPlace.parent_id.is_(None)))
        assert root is not None
        place = GeographicPlace(
            id=uuid7(),
            name="Perf locality",
            parent_id=root.id,
            place_kind="custom",
            place_type="locality",
        )
        identity = BotanicalIdentity(id=uuid7(), scientific_name="Perf testplant")
        database.add_all([place, identity])
        database.flush()
        site = ProvenanceSite(id=uuid7(), name="Perf site", geographic_place_id=place.id)
        database.add(site)
        database.flush()
        model = {"seed": SeedLot, "plant": Plant, "group": PlantGroup}[kind]
        results: Sequence[SeedLotResponse | PlantResponse | PlantGroupResponse]
        for size in (1, 20):
            for number in range(1 if size == 1 else 19):
                fields = (
                    {"source_kind": "purchased"}
                    if kind == "seed"
                    else {"direct_origin_kind": "purchased"}
                )
                database.add(
                    model(
                        botanical_identity_id=identity.id,
                        label=f"Record {size}-{number}",
                        material_provenance_place_id=place.id,
                        provenance_site_id=site.id,
                        **fields,
                    )
                )
            database.flush()
            statements: list[str] = []

            def capture(*args: object, captured: list[str] = statements) -> None:
                captured.append(str(args[2]))

            event.listen(database_connection, "before_cursor_execute", capture)
            try:
                if kind == "seed":
                    results = responses(database, list_seed_lots(database, identity.id))
                elif kind == "plant":
                    results = plant_responses(database, list_plants(database, identity.id))
                else:
                    results = plant_group_responses(
                        database, list_plant_groups(database, identity.id)
                    )
            finally:
                event.remove(database_connection, "before_cursor_execute", capture)
            assert len(results) == size
            geography_queries = [
                sql for sql in statements if sql.startswith("SELECT geographic_places.id")
            ]
            assert len(geography_queries) == 1
            # SeedLot also batches nullable conversion IDs for Harvest cross-navigation.
            # Projection, geography, three site-usage queries and primary designation.
            assert len(statements) == (7 if kind == "seed" else 6)
            assert all(
                item.material_provenance is not None
                and item.material_provenance.display_path == f"{root.name} → Perf locality"
                for item in results
            )
            assert all(
                item.provenance_site is not None
                and item.provenance_site.geographic_place_path == f"{root.name} → Perf locality"
                for item in results
            )
