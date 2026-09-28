"""PERF-001 fixture v1; execute inside the isolated runtime after Alembic upgrade."""

import hashlib
import io
import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import florabase.main  # noqa: F401 -- register the existing model graph
from florabase.attachments.model import Attachment
from florabase.auth.service import bootstrap_owner
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_profiles.model import (
    BotanicalProfile,
    BotanicalProfileNativeRange,
)
from florabase.collection_photos.model import (
    BotanicalIdentityCoverImage,
    CollectionPrimaryPhoto,
    ExternalImageReference,
    LocalCollectionPhoto,
)
from florabase.core.config import get_settings
from florabase.db.session import get_engine
from florabase.events.model import Event
from florabase.external_botany.model import ExternalTaxonLink
from florabase.geographic_places.model import GeographicPlace
from florabase.locations.model import Location
from florabase.plants.model import Plant, PlantGroup
from florabase.provenance_sites.model import ProvenanceSite
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import GerminationObservation, Sowing
from florabase.suppliers.model import Supplier
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

STAMP = datetime(2026, 9, 1, tzinfo=UTC)


def identifier(kind: int, number: int) -> UUID:
    # Fixed fixture-only UUIDv7-shaped values, distinct from application-generated IDs.
    return UUID(f"0198f000-0000-7000-8000-{kind:04x}{number:08x}")


def record(model: type[Any], category: int, number: int, **fields: Any) -> Any:
    return model(
        id=identifier(category, number), created_at=STAMP, updated_at=STAMP, **fields
    )


settings = get_settings()
url = make_url(settings.database_url)
if not (
    settings.database_disposable
    and url.database == "florabase_perf"
    and url.host == "db"
    and settings.canonical_origin == "http://localhost:18080"
):
    raise RuntimeError("Fixture requires the fixed isolated PERF-001 environment")

with Session(get_engine()) as db, db.begin():
    if db.scalar(select(func.count()).select_from(BotanicalIdentity)):
        raise RuntimeError(
            "Fixture refuses a populated collection; recreate only perf containers"
        )
    bootstrap_owner(db, "perf-owner", "disposable-perf-owner-password", "PERF fixture")
    country = db.scalar(
        select(GeographicPlace).where(GeographicPlace.source_code == "IT")
    )
    assert country is not None
    locality = record(GeographicPlace, 1, 0, name="PERF locality", parent_id=country.id)
    db.add(locality)
    suppliers = [
        record(Supplier, 2, i, name=f"Supplier {i:02}", kind="nursery")
        for i in range(8)
    ]
    db.add_all(suppliers)
    root = record(Location, 3, 0, name="Collection")
    db.add(root)
    db.flush()
    locations = [root] + [
        record(Location, 3, i, name=f"Shelf {i:02}", parent_id=root.id)
        for i in range(1, 12)
    ]
    db.add_all(locations[1:])
    sites = [
        record(
            ProvenanceSite,
            4,
            i,
            name=f"Site {i:02}",
            geographic_place_id=locality.id,
            latitude=40 + i / 10,
            longitude=12 + i / 10,
        )
        for i in range(8)
    ]
    db.add_all(sites)
    identities = [
        record(BotanicalIdentity, 5, i, scientific_name=f"Perfplant species{i:03}")
        for i in range(80)
    ]
    db.add_all(identities)
    db.flush()
    for identity in identities:
        db.add(
            BotanicalProfile(
                botanical_identity_id=identity.id,
                description="Personal collection reference fixture.",
            )
        )
    db.flush()
    for identity in identities:
        db.add(
            BotanicalProfileNativeRange(
                botanical_profile_id=identity.id,
                geographic_place_id=country.id,
                created_at=STAMP,
            )
        )
    db.add(
        ExternalTaxonLink(
            id=identifier(6, 0),
            botanical_identity_id=identities[0].id,
            provider="gbif",
            external_id="6SHN2",
            scientific_name="Aloe vera",
            canonical_name="Aloe vera",
            rank="SPECIES",
            taxonomic_status="ACCEPTED",
            linked_at=STAMP,
            last_refreshed_at=STAMP,
            last_refresh_attempt_at=STAMP,
        )
    )
    seeds = [
        record(
            SeedLot,
            7,
            i,
            botanical_identity_id=identities[i % 80].id,
            label=f"Seeds {i:03}",
            source_kind="purchased",
            supplier_id=suppliers[i % 8].id,
            location_id=locations[i % 12].id,
            material_provenance_place_id=locality.id,
            provenance_site_id=sites[i % 8].id,
            quantity_kind="seed_count",
            quantity_value=100,
            quantity_is_approximate=False,
        )
        for i in range(160)
    ]
    db.add_all(seeds)
    db.flush()
    sowings = [
        record(
            Sowing,
            8,
            i,
            seed_lot_id=seeds[i].id,
            label=f"Sowing {i:03}",
            location_id=locations[i % 12].id,
            sowing_date_precision="day",
            sowing_date_year=2026,
            sowing_date_month=8,
            sowing_date_day=1,
            quantity_kind="seed_count",
            quantity_value=20,
            quantity_is_approximate=False,
            germinated_count=8,
        )
        for i in range(120)
    ]
    db.add_all(sowings)
    db.flush()
    for i, sowing in enumerate(sowings):
        for day in (3, 5):
            db.add(
                record(
                    GerminationObservation,
                    9,
                    i * 2 + (0 if day == 3 else 1),
                    sowing_id=sowing.id,
                    observed_on=date(2026, 8, day),
                    newly_germinated_count=5,
                )
            )
    plants = []
    for i in range(160):
        origin = (
            {"originating_sowing_id": sowings[i].id}
            if i < 120
            else {
                "direct_origin_kind": "purchased",
                "supplier_id": suppliers[i % 8].id,
                "material_provenance_place_id": locality.id,
                "provenance_site_id": sites[i % 8].id,
            }
        )
        plants.append(
            record(
                Plant,
                10,
                i,
                botanical_identity_id=identities[i % 80].id,
                label=f"Plant {i:03}",
                location_id=locations[i % 12].id,
                **origin,
            )
        )
    groups = [
        record(
            PlantGroup,
            11,
            i,
            botanical_identity_id=identities[i].id,
            originating_sowing_id=sowings[i].id,
            label=f"Group {i:03}",
            location_id=locations[i % 12].id,
            quantity_value=5,
            quantity_is_approximate=False,
        )
        for i in range(80)
    ]
    db.add_all(plants + groups)
    db.flush()
    for i in range(960):
        target = (
            {"plant_id": plants[i % 160].id}
            if i % 2
            else {"plant_group_id": groups[i % 80].id}
        )
        db.add(
            record(
                Event,
                12,
                i,
                kind="observation",
                occurred_on_precision="day",
                occurred_on_year=2026,
                occurred_on_month=8,
                occurred_on_day=1 + i % 28,
                notes=f"Fixture observation {i:04}",
                **target,
            )
        )
    image = Image.frombytes(
        "RGB", (900, 600), bytes((i * 17 + i // 71) % 256 for i in range(900 * 600 * 3))
    )
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=85)
    binary = output.getvalue()
    for i in range(12):
        attachment_id = identifier(13, i)
        key = f"objects/{attachment_id.hex[:2]}/{attachment_id.hex}"
        path = settings.attachment_storage_root / key
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.write_bytes(binary)
        db.add(
            Attachment(
                id=attachment_id,
                storage_key=key,
                original_filename=f"fixture-{i}.jpg",
                media_type="image/jpeg",
                byte_size=len(binary),
                sha256=hashlib.sha256(binary).hexdigest(),
                created_at=STAMP,
            )
        )
        db.flush()
        if i == 11:
            db.add(
                record(
                    BotanicalIdentityCoverImage,
                    14,
                    i,
                    botanical_identity_id=identities[0].id,
                    source_mode="local",
                    attachment_id=attachment_id,
                )
            )
        else:
            target = (
                {"seed_lot_id": seeds[i].id}
                if i < 4
                else {"plant_id": plants[i].id}
                if i < 8
                else {"plant_group_id": groups[i].id}
            )
            db.add(
                record(
                    LocalCollectionPhoto,
                    14,
                    i,
                    attachment_id=attachment_id,
                    caption="Fixture photo",
                    **target,
                )
            )
            db.flush()
            db.add(
                record(
                    CollectionPrimaryPhoto,
                    15,
                    i,
                    local_collection_photo_id=identifier(14, i),
                    **target,
                )
            )
    db.add(
        record(
            ExternalImageReference,
            16,
            0,
            seed_lot_id=seeds[0].id,
            image_url="https://images.example.invalid/perf.jpg",
            source_url="https://example.invalid/source",
            attribution="Deterministic external opt-in fixture",
        )
    )
    db.flush()
    manifest = {
        "identity": identities[0].id,
        "seed": seeds[0].id,
        "sowing": sowings[0].id,
        "plant": plants[0].id,
        "group": groups[0].id,
        "supplier": suppliers[0].id,
        "location": locations[0].id,
        "site": sites[0].id,
        "place": locality.id,
        "attachment": identifier(13, 0),
        "photo": identifier(14, 0),
    }
    Path("/tmp/perf-manifest.json").write_text(json.dumps(manifest, default=str))
print(json.dumps(manifest, default=str))
