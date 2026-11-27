"""Synthetic source adapter and fixtures for the independently owned Taxonomy Review only."""
# ruff: noqa: T201 -- This explicit Review CLI reports its actions on stdout.

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from florabase.auth.model import User
from florabase.auth.service import bootstrap_owner
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.schemas import BotanicalIdentityCreate, BotanicalIdentityUpdate
from florabase.botanical_identities.service import (
    create_botanical_identity,
    update_botanical_identity,
)
from florabase.db.session import get_engine
from florabase.harvests import inventory_service
from florabase.harvests import service as harvests
from florabase.harvests.inventory_schemas import InventoryWrite
from florabase.harvests.model import HarvestItem
from florabase.harvests.schemas import HarvestItemWrite, HarvestWrite
from florabase.main import app
from florabase.plants.model import Plant, PlantGroup
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing
from florabase.taxonomy import service
from florabase.taxonomy.api import source_dependency
from florabase.taxonomy.schemas import TaxonomyLinkWrite
from florabase.taxonomy.snapshot import build_index
from florabase.taxonomy.source import CODE, ROOT, WfoMetadata, WfoSource

FIXTURE = json.loads(Path(__file__).with_name("fixture.json").read_text())
INDEX = Path("/tmp/taxonomy-review.sqlite")
STORAGE = Path("/var/lib/florabase/attachments")
LEDGER = STORAGE / ".taxonomy-review-fixture.json"
STATE = STORAGE / ".taxonomy-review-source.json"


def validate_runtime(environment: dict[str, str]) -> None:
    if (
        environment.get("FLORABASE_WORKFLOW_MODE") != "taxonomy-review"
        or not environment.get("FLORABASE_TAXONOMY_REVIEW_PROJECT", "").startswith(
            "florabase-taxonomy-review-"
        )
        or not environment.get("FLORABASE_TAXONOMY_REVIEW_SOURCE")
        or environment.get("FLORABASE_ENVIRONMENT") != "development"
        or environment.get("FLORABASE_CANONICAL_ORIGIN") != "http://localhost:15278"
        or environment.get("FLORABASE_ATTACHMENT_STORAGE_ROOT") != str(STORAGE)
    ):
        raise RuntimeError("Taxonomy fixture refuses every other runtime")


def identifier(number: int) -> str:
    return ROOT if number == 0 else f"wfo-{9000000000 + number}"


class FixtureSource(WfoSource):
    def metadata(self) -> WfoMetadata:
        return (
            super()
            .metadata()
            .model_copy(
                update={
                    "version": "2026-06 · synthetic Review fixture",
                    "citation": FIXTURE["notice"],
                }
            )
        )


def build_source() -> FixtureSource:
    names = [
        {"ID": identifier(n), "scientificName": name, "rank": rank, "authorship": author}
        for n, name, rank, parent, author in FIXTURE["taxa"]
    ]
    concepts = [
        {
            "ID": identifier(n),
            "nameID": identifier(n),
            "parentID": CODE if n == 0 else identifier(parent),
        }
        for n, name, rank, parent, author in FIXTURE["taxa"]
        if n == 0 or parent is not None
    ]
    synonyms = [
        {
            "ID": identifier(name) + "-2026-06",
            "nameID": identifier(name),
            "taxonID": identifier(accepted),
        }
        for name, accepted in FIXTURE["synonyms"]
    ]
    build_index(INDEX, names, concepts, synonyms, WfoMetadata(retrieved_at="2026-10-25T12:00:00Z"))
    return FixtureSource(INDEX)


def source_available() -> bool:
    return not STATE.exists() or json.loads(STATE.read_text())["available"]


def marker() -> dict[str, object]:
    return {
        "project": os.environ["FLORABASE_TAXONOMY_REVIEW_PROJECT"],
        "source": os.environ["FLORABASE_TAXONOMY_REVIEW_SOURCE"],
        "version": 1,
    }


def read_ledger() -> dict:
    result = json.loads(LEDGER.read_text())
    if any(result.get(key) != value for key, value in marker().items()):
        raise RuntimeError("Foreign or incompatible Taxonomy fixture; refusing mutation")
    return result


def seed() -> None:
    credentials = json.load(sys.stdin)
    source = build_source()
    with Session(get_engine()) as database:
        if database.scalar(text("SELECT current_database()")) != "florabase_review":
            raise RuntimeError("Unexpected database; fixture refused")
        if LEDGER.exists():
            ledger = read_ledger()
            if any(
                database.get(BotanicalIdentity, UUID(value)) is None
                for value in ledger["identities"].values()
            ):
                raise RuntimeError(
                    "Managed fixture identity missing; inspect rather than reseeding"
                )
            print(
                "Fixture retained; no names, relationships, credentials "
                "or operator edits overwritten."
            )
            return
        if database.scalar(select(func.count()).select_from(BotanicalIdentity)):
            raise RuntimeError("Nonempty unrecognized collection; fixture refused")
        if database.scalar(select(User.id).limit(1)) is None:
            bootstrap_owner(
                database,
                credentials["login"],
                credentials["password"],
                "Taxonomy Review (synthetic)",
            )
        ledger = {**marker(), "identities": {}}
        for name, cultivar, common, taxon, records, stale in FIXTURE["identities"]:
            identity = create_botanical_identity(
                database,
                BotanicalIdentityCreate(
                    scientific_name=name, cultivar_name=cultivar, common_name=common
                ),
            )
            ledger["identities"][name] = str(identity.id)
            seed_lot = None
            plant = None
            for category, active in records:
                if category == "seed_lot":
                    seed_lot = SeedLot(
                        botanical_identity_id=identity.id,
                        lifecycle="active" if active else "exhausted",
                        label="Taxonomy Review fixture",
                    )
                    database.add(seed_lot)
                elif category == "plant":
                    plant = Plant(botanical_identity_id=identity.id, direct_origin_kind="unknown")
                    database.add(plant)
                elif category == "plant_group":
                    database.add(
                        PlantGroup(botanical_identity_id=identity.id, direct_origin_kind="unknown")
                    )
                elif category == "sowing":
                    assert seed_lot is not None
                    database.flush()
                    database.add(Sowing(seed_lot_id=seed_lot.id, label="Taxonomy Review fixture"))
                elif category == "stored_material":
                    assert plant is not None
                    database.flush()
                    harvest = harvests.write_harvest(
                        database,
                        HarvestWrite(
                            plant_id=plant.id,
                            label="Taxonomy Review fixture",
                            items=[HarvestItemWrite(material_kind="leaf")],
                        ),
                    )
                    item_id = database.scalar(
                        select(HarvestItem.id).where(HarvestItem.harvest_id == harvest.id)
                    )
                    assert item_id is not None
                    inventory_service.track(
                        database, item_id, InventoryWrite(state="active", quantity=None)
                    )
            database.flush()
            if taxon is not None:
                service.confirm(
                    database,
                    identity.id,
                    TaxonomyLinkWrite(
                        source_taxon_id=identifier(taxon),
                        checksum=source.metadata().checksum,
                        expected_version=None,
                        identity_updated_at=identity.updated_at,
                    ),
                    source,
                )
                if stale:
                    identity.updated_at = datetime.now(UTC)
                    database.flush()
        projection = service.tree(database, source)
        assert projection.counts.model_dump() == {
            "represented": 8,
            "living": 5,
            "current": 7,
            "historical": 1,
        }
        assert projection.unresolved == 2
        assert any(identity.synonym_of == "Salvia rosmarinus" for identity in projection.identities)
        database.commit()
        LEDGER.write_text(json.dumps(ledger))
        print(
            "Seeded 8 synthetic identities, 6 placed, 2 unresolved; "
            "real PostgreSQL and source APIs."
        )


def main() -> None:
    validate_runtime(dict(os.environ))
    action = sys.argv[1]
    if action == "serve":
        source = build_source()
        app.dependency_overrides[source_dependency] = lambda: (
            source if source_available() else WfoSource(None)
        )
        import uvicorn

        uvicorn.run(app, host="0.0.0.0", port=8000)
    elif action == "seed":
        seed()
    elif action == "source":
        read_ledger()
        STATE.write_text(json.dumps({"available": sys.argv[2] == "available"}))
        print("Synthetic source:", "available" if source_available() else "unavailable")
    elif action == "conflict":
        ledger = read_ledger()
        with Session(get_engine()) as database:
            identity = database.get(
                BotanicalIdentity, UUID(ledger["identities"]["Lavandula angustifolia"])
            )
            assert identity is not None
            update_botanical_identity(
                database,
                identity,
                BotanicalIdentityUpdate(
                    scientific_name=identity.scientific_name,
                    cultivar_name=identity.cultivar_name,
                    common_name="Lavender · edited in another Review session",
                ),
            )
            database.commit()
        print(
            "Edited only the synthetic Lavender identity; "
            "a previously loaded timestamp is now stale."
        )
    elif action == "check":
        source = build_source()
        assert source.search("Rosmarinus")[0].taxon.taxonomic_status == "synonym"
        assert not source.search("Ocimum unplaced")[0].classification
        assert "synthetic" in source.metadata().version
        rejected = 0
        for field in [
            "FLORABASE_WORKFLOW_MODE",
            "FLORABASE_TAXONOMY_REVIEW_PROJECT",
            "FLORABASE_ENVIRONMENT",
            "FLORABASE_CANONICAL_ORIGIN",
            "FLORABASE_ATTACHMENT_STORAGE_ROOT",
        ]:
            try:
                validate_runtime({**dict(os.environ), field: "foreign"})
            except RuntimeError:
                rejected += 1
        assert rejected == 5
        print("Fixture source, synonym, unplaced name and five foreign-runtime guards passed.")
    elif action == "status":
        print("Synthetic source:", "available" if source_available() else "unavailable")
        print("Fixture:", "seeded" if LEDGER.exists() else "not seeded")
        print(FIXTURE["notice"])
    else:
        raise RuntimeError("Unsupported Review action")


if __name__ == "__main__":
    main()
