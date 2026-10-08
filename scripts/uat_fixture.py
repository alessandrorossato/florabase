"""PREVIEW-001 fixture v4. Mounted explicitly by the guarded host UAT workflow only."""

from __future__ import annotations

import argparse
import asyncio
import fcntl
import hashlib
import io
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, TypeVar, cast
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from fastapi import UploadFile
from PIL import Image, ImageDraw
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from starlette.datastructures import Headers

import florabase.main  # noqa: F401 -- register the current application model graph
from florabase.attachments.model import Attachment
from florabase.attachments.storage import AttachmentStorage
from florabase.auth.model import User
from florabase.auth.security import password_hasher
from florabase.auth.service import bootstrap_owner
from florabase.botanical_identities import service as identities
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.schemas import BotanicalIdentityCreate
from florabase.botanical_profiles.schemas import BotanicalProfilePut
from florabase.botanical_profiles.service import (
    add_botanical_native_range,
    put_botanical_profile,
)
from florabase.collection_photos import primary
from florabase.collection_photos.model import MediaAsset, RecordMediaLink
from florabase.collection_photos.schemas import PrimaryPhotoSelection
from florabase.core.config import CookieMode, Environment, Settings, get_settings
from florabase.db.base import Base
from florabase.db.session import get_engine
from florabase.events import service as events
from florabase.events.model import Event
from florabase.events.schemas import EventCreate
from florabase.external_botany.model import ExternalTaxonLink
from florabase.external_botany.provider import GbifBotanicalProvider
from florabase.external_botany.service import confirm_link
from florabase.geographic_places import service as places
from florabase.geographic_places.model import GeographicPlace
from florabase.geographic_places.schemas import GeographicPlaceCreate
from florabase.harvests import service as harvests
from florabase.harvests.inventory_model import HarvestMaterialInventory
from florabase.harvests.inventory_schemas import InventoryWrite
from florabase.harvests.inventory_service import track as initialize_inventory
from florabase.harvests.model import Harvest, HarvestItem
from florabase.harvests.schemas import HarvestWrite
from florabase.locations import service as locations
from florabase.locations.model import Location
from florabase.locations.schemas import LocationCreate
from florabase.media import service as media
from florabase.media.schemas import AssetMetadataWrite, ExternalAssetCreate, LinkWrite
from florabase.orders import service as orders
from florabase.orders.model import Order
from florabase.orders.schemas import OrderCreate
from florabase.plants import service as plants
from florabase.plants.model import Plant, PlantGroup
from florabase.plants.schemas import PlantCreate, PlantGroupCreate
from florabase.provenance_sites import service as sites
from florabase.provenance_sites.model import ProvenanceSite
from florabase.provenance_sites.schemas import ProvenanceSiteCreate
from florabase.seed_lots import service as seeds
from florabase.seed_lots.model import SeedLot
from florabase.seed_lots.schemas import SeedLotCreate
from florabase.sowings import service as sowings
from florabase.sowings.model import Sowing
from florabase.sowings.schemas import SowingCreate
from florabase.suppliers import service as suppliers
from florabase.suppliers.model import Supplier
from florabase.suppliers.schemas import SupplierCreate

VERSION = 4
NOTE = "Synthetic UAT Preview data; no real collection or provenance claims."
MODELS: dict[str, type[Base]] = {
    "external_taxon": ExternalTaxonLink,
    "owner": User,
    "identity": BotanicalIdentity,
    "supplier": Supplier,
    "order": Order,
    "location": Location,
    "place": GeographicPlace,
    "site": ProvenanceSite,
    "seed": SeedLot,
    "sowing": Sowing,
    "plant": Plant,
    "group": PlantGroup,
    "event": Event,
    "harvest": Harvest,
    "item": HarvestItem,
    "inventory": HarvestMaterialInventory,
    "asset": MediaAsset,
    "link": RecordMediaLink,
}
T = TypeVar("T", bound=Base)


class FixtureError(RuntimeError):
    pass


def require_identity(settings: Settings, database: Session, *, require_marker: bool = True) -> Path:
    url = make_url(settings.database_url)
    project = os.environ.get("FLORABASE_UAT_PROJECT", "")
    source = os.environ.get("FLORABASE_UAT_SOURCE", "")
    if not (
        os.environ.get("FLORABASE_WORKFLOW_MODE") == "uat"
        and re.fullmatch(r"florabase-uat-preview(?:-smoke-[0-9a-f]{12})?", project)
        and Path(source).is_absolute()
        and settings.environment == Environment.DEVELOPMENT
        and settings.cookie_mode == CookieMode.LOOPBACK_DEVELOPMENT
        and (
            settings.canonical_origin == "http://localhost:15174"
            or (
                project.startswith("florabase-uat-preview-smoke-")
                and urlsplit(settings.canonical_origin or "").hostname == "localhost"
                and urlsplit(settings.canonical_origin or "").scheme == "http"
                and 20000 <= (urlsplit(settings.canonical_origin or "").port or 0) <= 60000
            )
        )
        and settings.attachment_storage_root == Path("/var/lib/florabase/attachments")
        and url.host == "db"
        and url.port == 5432
        and url.database == "florabase_uat"
        and url.username == "florabase_uat"
    ):
        raise FixtureError("UAT environment identity refused; no data changed")
    root = cast(Path, settings.attachment_storage_root)
    marker = root / ".uat-identity.json"
    expected = {
        "project": project,
        "source": source,
        "database": "florabase_uat",
        "origin": settings.canonical_origin,
    }
    if (require_marker and not marker.is_file()) or (
        marker.is_file() and json.loads(marker.read_text()) != expected
    ):
        raise FixtureError(
            "Missing/mismatched guarded UAT resource marker; use make uat-preview-seed"
        )
    actual = database.execute(text("SELECT current_database(), current_user")).one()
    if tuple(actual) != ("florabase_uat", "florabase_uat"):
        raise FixtureError("Connected database identity refused; no data changed")
    return root


def read_manifest(root: Path) -> dict[str, Any] | None:
    path = root / ".uat-fixture.json"
    if not path.exists():
        return None
    try:
        value: dict[str, Any] = json.loads(path.read_text())
        if (
            not isinstance(value, dict)
            or value.get("version") != VERSION
            or value.get("state") != "ready"
            or not isinstance(value.get("records"), dict)
        ):
            raise ValueError
        return value
    except (ValueError, TypeError) as error:
        raise FixtureError(
            "Preview fixture baseline is inconsistent/version incompatible; run guarded uat-preview-reset"
        ) from error


def write_manifest(root: Path, value: dict[str, Any]) -> None:
    temporary = root / ".uat-fixture.tmp"
    with temporary.open("w") as stream:
        json.dump(value, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(root / ".uat-fixture.json")


def validate_manifest(database: Session, root: Path, manifest: dict[str, Any]) -> None:
    expected = {
        "owner:preview",
        "identity:Ocimum basilicum",
        "identity:Lavandula angustifolia",
        "identity:Aloe vera",
        "identity:Raphanus sativus",
        "identity:Viola tricolor",
        "identity:Salvia officinalis",
        "seed:unranged",
        "place:native",
        "seed:historical",
        "external_taxon:basil",
        "supplier:nursery",
        "supplier:exchange",
        "order:exact",
        "order:partial",
        "seed:3",
        "location:root",
        "location:Indoor seed shelf",
        "location:Greenhouse bench",
        "location:Outdoor herb bed",
        "place:garden",
        "site:herbs",
        "seed:0",
        "seed:1",
        "seed:2",
        "sowing:basil",
        "sowing:historical",
        "plant:direct",
        "plant:derived",
        "group:basil",
        "event:0",
        "event:1",
        "event:harvest",
        "harvest:basil",
        "item:basil",
        "asset:local",
        "asset:external",
        "link:external",
        "link:supplier",
        "link:seed_lot",
        "link:plant",
    }
    # Additive EXPLORE-002 fixture extension; original v4 manifests remain readable.
    if "inventory:basil" in manifest["records"]:
        expected.add("inventory:basil")
    if set(manifest["records"]) != expected:
        raise FixtureError(
            "Preview fixture baseline has missing records; run guarded uat-preview-reset"
        )
    for key, value in manifest["records"].items():
        model = MODELS.get(key.split(":")[0])
        if model is None or database.get(model, UUID(value)) is None:
            raise FixtureError(
                "Preview fixture baseline has missing records; run guarded uat-preview-reset"
            )
    for value in manifest["records"].values():
        asset = database.get(MediaAsset, UUID(value))
        if asset is not None and asset.attachment_id is not None:
            attachment = database.get(Attachment, asset.attachment_id)
            if attachment is None:
                raise FixtureError(
                    "Preview media metadata is missing; run guarded uat-preview-reset"
                )
            path = root / attachment.storage_key
            if (
                not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != attachment.sha256
            ):
                raise FixtureError(
                    "Preview media content is missing/inconsistent; run guarded uat-preview-reset"
                )


def image_upload() -> UploadFile:
    buffer = io.BytesIO()
    image = Image.new("RGB", (96, 96), "#eef2db")
    drawing = ImageDraw.Draw(image)
    drawing.line([(48, 83), (48, 25)], fill="#47663a", width=4)
    drawing.ellipse((18, 29, 49, 51), fill="#789454")
    drawing.ellipse((48, 16, 78, 39), fill="#597c45")
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return UploadFile(
        file=buffer,
        filename="uat-preview-synthetic-leaf.png",
        headers=Headers({"content-type": "image/png"}),
    )


def ensure_stored_material(database: Session, root: Path, manifest: dict[str, Any]) -> None:
    if "inventory:basil" in manifest["records"]:
        return
    item_id = UUID(manifest["records"]["item:basil"])
    inventory = database.scalar(
        select(HarvestMaterialInventory).where(HarvestMaterialInventory.harvest_item_id == item_id)
    )
    # Preserve any operator-managed inventory already attached to this fixture item.
    if inventory is None:
        inventory = initialize_inventory(
            database, item_id, InventoryWrite(state="active", quantity=None)
        )
    database.commit()
    manifest["records"]["inventory:basil"] = str(inventory.id)
    write_manifest(root, manifest)


def seed(database: Session, root: Path) -> dict[str, Any]:
    existing = read_manifest(root)
    if existing is not None:
        validate_manifest(database, root, existing)
        ensure_stored_material(database, root, existing)
        return existing
    if (
        database.scalar(select(User.id).limit(1)) is not None
        or database.scalar(select(BotanicalIdentity.id).limit(1)) is not None
    ):
        raise FixtureError("Unrecognized populated UAT baseline; use guarded uat-preview-reset")
    manifest: dict[str, Any] = {"version": VERSION, "state": "building", "records": {}}
    # A crash or error remains explicitly inconsistent. Ordinary seed never guesses ownership.
    write_manifest(root, manifest)

    def remember(key: str, result: T) -> T:
        manifest["records"][key] = str(result.id)
        return result

    owner = remember(
        "owner:preview",
        bootstrap_owner(database, "preview", "uat-bootstrap-only-password", "UAT Preview"),
    )
    # Deliberately short public fixture password, ONLY after host + runtime + DB identity guards.
    # Normal bootstrap validation and authenticate()/Argon2/session behavior remain unchanged.
    owner.password_hash = password_hasher().hash("preview")
    identity = [
        remember(
            f"identity:{name}",
            identities.create_botanical_identity(
                database,
                BotanicalIdentityCreate(scientific_name=name, common_name=f"Preview — {common}"),
            ),
        )
        for name, common in [
            ("Ocimum basilicum", "Basil"),
            ("Lavandula angustifolia", "Lavender"),
            ("Aloe vera", "Aloe"),
        ]
    ]
    # Exact CoL XR usage verified through the existing provider on 2026-10-08.
    # Offline confirmation keeps synthetic seeding network independent.
    # Only taxonomy/link metadata is seeded; occurrence evidence is never fabricated.
    basil_snapshot = {
        "usage": {
            "key": "48GBK",
            "name": "Ocimum basilicum L.",
            "canonicalName": "Ocimum basilicum",
            "authorship": "L.",
            "rank": "SPECIES",
            "status": "ACCEPTED",
        },
        "classification": [
            {"name": "Plantae", "rank": "KINGDOM"},
            {"name": "Lamiaceae", "rank": "FAMILY"},
            {"name": "Ocimum", "rank": "GENUS"},
        ],
        "diagnostics": {"matchType": "EXACT", "confidence": 98},
    }

    def offline_taxon(request: httpx.Request) -> httpx.Response:
        if (
            request.url.host != "api.gbif.org"
            or request.url.path != "/v2/species/match"
            or request.url.params.get("scientificName") != "Ocimum basilicum L."
        ):
            raise FixtureError("Unexpected synthetic taxon request")
        return httpx.Response(200, json=basil_snapshot)

    remember(
        "external_taxon:basil",
        asyncio.run(
            confirm_link(
                database,
                GbifBotanicalProvider(get_settings(), transport=httpx.MockTransport(offline_taxon)),
                identity[0].id,
                "48GBK",
                "Ocimum basilicum L.",
                86400,
            )
        ),
    )
    historical = remember(
        "identity:Raphanus sativus",
        identities.create_botanical_identity(
            database,
            BotanicalIdentityCreate(
                scientific_name="Raphanus sativus",
                cultivar_name="Preview long cultivar for responsive historical collection review",
                common_name="Preview — Historical radish",
            ),
        ),
    )
    remember(
        "seed:historical",
        seeds.create_seed_lot(
            database,
            SeedLotCreate.model_validate(
                {
                    "botanical_identity_id": historical.id,
                    "label": "Preview — Exhausted radish packet",
                    "lifecycle": "exhausted",
                    "source_kind": "unknown",
                    "notes": NOTE,
                }
            ),
        ),
    )
    remember(
        "identity:Viola tricolor",
        identities.create_botanical_identity(
            database,
            BotanicalIdentityCreate(
                scientific_name="Viola tricolor", common_name="Preview — Reference only"
            ),
        ),
    )
    unranged = remember(
        "identity:Salvia officinalis",
        identities.create_botanical_identity(
            database,
            BotanicalIdentityCreate(
                scientific_name="Salvia officinalis", common_name="Preview — No recorded range"
            ),
        ),
    )
    remember(
        "seed:unranged",
        seeds.create_seed_lot(
            database,
            SeedLotCreate.model_validate(
                {
                    "botanical_identity_id": unranged.id,
                    "label": "Preview — Sage packet without native-range reference knowledge",
                    "source_kind": "unknown",
                    "notes": NOTE,
                }
            ),
        ),
    )
    # Synthetic *recorded* assertions for UI acceptance, never botanical evidence or inference.
    # Kept separate from the existing material-provenance garden and provider snapshot.
    codes = {row.source_code: row for row in database.scalars(select(GeographicPlace))}
    custom_range = remember(
        "place:native",
        places.create_geographic_place(
            database,
            GeographicPlaceCreate(
                name="Preview uncharted native area with a deliberately long display label",
                parent_id=codes["BR"].id,
                place_type="other_named_area",
            ),
        ),
    )
    for taxon, range_places in (
        (identity[0], [codes["005"], codes["BR"]]),
        (identity[2], [codes["IT"], codes["TH"]]),
        (identity[1], [codes["IT"], custom_range]),
        (historical, [codes["035"]]),
    ):
        put_botanical_profile(
            database,
            taxon.id,
            BotanicalProfilePut(
                origin_distribution=(
                    "Synthetic UAT native-range demonstration; not botanical evidence."
                )
            ),
        )
        for range_place in range_places:
            add_botanical_native_range(database, taxon.id, range_place.id)
    seller = remember(
        "supplier:nursery",
        suppliers.create_supplier(
            database,
            SupplierCreate(name="Preview — Greenhouse Nursery", kind="nursery", notes=NOTE),
        ),
    )
    exchange = remember(
        "supplier:exchange",
        suppliers.create_supplier(
            database,
            SupplierCreate(name="Preview — Garden Seed Exchange", kind="exchange", notes=NOTE),
        ),
    )
    collection = remember(
        "location:root",
        locations.create_location(database, LocationCreate(name="Preview collection")),
    )
    indoor, greenhouse, outdoor = [
        remember(
            f"location:{name}",
            locations.create_location(database, LocationCreate(name=name, parent_id=collection.id)),
        )
        for name in ("Indoor seed shelf", "Greenhouse bench", "Outdoor herb bed")
    ]
    country = database.scalar(select(GeographicPlace).where(GeographicPlace.source_code == "IT"))
    if country is None:
        raise FixtureError("Canonical Italy geography is missing; reset/migrate UAT")
    place = remember(
        "place:garden",
        places.create_geographic_place(
            database,
            GeographicPlaceCreate(
                name="Preview demonstration garden",
                parent_id=country.id,
                place_type="locality",
            ),
        ),
    )
    site = remember(
        "site:herbs",
        sites.create_provenance_site(
            database,
            ProvenanceSiteCreate(
                name="Preview herb garden (synthetic coordinates)",
                geographic_place_id=place.id,
                latitude="45.0",
                longitude="11.0",
                notes=NOTE,
            ),
        ),
    )
    purchase = remember(
        "order:exact",
        orders.create_order(
            database,
            OrderCreate.model_validate(
                {
                    "supplier_id": seller.id,
                    "ordered_on": {"precision": "day", "year": 2026, "month": 10, "day": 8},
                    "order_reference": "Preview — PO-2026-001",
                    "total_price": "42.50",
                    "currency": "EUR",
                    "notes": NOTE,
                }
            ),
        ),
    )
    remember(
        "order:partial",
        orders.create_order(
            database,
            OrderCreate.model_validate(
                {
                    "ordered_on": {"precision": "month", "year": 2026, "month": 9},
                    "order_reference": "Preview — Historical purchase",
                    "notes": NOTE,
                }
            ),
        ),
    )
    lots = [
        remember(
            f"seed:{i}",
            seeds.create_seed_lot(
                database,
                SeedLotCreate.model_validate(
                    {
                        "botanical_identity_id": identity[i].id,
                        "label": [
                            "Preview — Basil counted packet",
                            "Preview — Lavender approximate stock",
                            "Preview — Aloe unknown stock",
                        ][i],
                        "source_kind": ["purchased", "gift_exchange", "unknown"][i],
                        "supplier_id": [seller.id, exchange.id, None][i],
                        "order_id": purchase.id if i == 0 else None,
                        "location_id": indoor.id,
                        "quantity": {
                            "kind": "seed_count",
                            "value": [48, 80][i],
                            "is_approximate": i == 1,
                        }
                        if i < 2
                        else None,
                        "provenance_site_id": site.id if i == 1 else None,
                        "notes": NOTE,
                    }
                ),
            ),
        )
        for i in range(3)
    ]
    remember(
        "seed:3",
        seeds.create_seed_lot(
            database,
            SeedLotCreate.model_validate(
                {
                    "botanical_identity_id": identity[0].id,
                    "label": "Preview — Basil second physical packet",
                    "source_kind": "purchased",
                    "supplier_id": seller.id,
                    "order_id": purchase.id,
                    "location_id": indoor.id,
                    "notes": NOTE,
                }
            ),
        ),
    )

    sowing = remember(
        "sowing:basil",
        sowings.create_sowing(
            database,
            SowingCreate.model_validate(
                {
                    "seed_lot_id": lots[0].id,
                    "label": "Preview — Spring basil tray",
                    "sowing_date": {
                        "precision": "day",
                        "year": 2026,
                        "month": 3,
                        "day": 15,
                    },
                    "quantity": {
                        "kind": "seed_count",
                        "value": 12,
                        "is_approximate": False,
                    },
                    "germinated_count": 8,
                    "location_id": greenhouse.id,
                    "substrate": "Seed compost",
                    "notes": NOTE,
                }
            ),
        ),
    )
    remember(
        "sowing:historical",
        sowings.create_sowing(
            database,
            SowingCreate.model_validate(
                {
                    "seed_lot_id": lots[1].id,
                    "label": "Preview — Previous lavender trial",
                    "lifecycle": "completed",
                    "notes": NOTE,
                }
            ),
        ),
    )
    direct = remember(
        "plant:direct",
        plants.create_plant(
            database,
            PlantCreate.model_validate(
                {
                    "botanical_identity_id": identity[2].id,
                    "label": "Preview — Nursery aloe",
                    "direct_origin_kind": "purchased",
                    "supplier_id": seller.id,
                    "location_id": greenhouse.id,
                    "notes": NOTE,
                }
            ),
        ),
    )
    derived = remember(
        "plant:derived",
        plants.create_plant(
            database,
            PlantCreate.model_validate(
                {
                    "botanical_identity_id": identity[0].id,
                    "label": "Preview — Basil mother plant",
                    "originating_sowing_id": sowing.id,
                    "location_id": outdoor.id,
                    "notes": NOTE,
                }
            ),
        ),
    )
    remember(
        "group:basil",
        plants.create_plant_group(
            database,
            PlantGroupCreate.model_validate(
                {
                    "botanical_identity_id": identity[0].id,
                    "label": "Preview — Basil seedlings",
                    "originating_sowing_id": sowing.id,
                    "quantity": {"value": 6, "is_approximate": False},
                    "location_id": greenhouse.id,
                    "notes": NOTE,
                }
            ),
        ),
    )
    for i, plant in enumerate((direct, derived)):
        remember(
            f"event:{i}",
            events.create_event(
                database,
                "plant",
                plant.id,
                EventCreate(kind="observation", notes=f"{NOTE} Healthy new leaves observed."),
            ),
        )
    harvest = remember(
        "harvest:basil",
        harvests.write_harvest(
            database,
            HarvestWrite.model_validate(
                {
                    "plant_id": derived.id,
                    "label": "Preview — Basil seed collection",
                    "occurred_on": {"precision": "month", "year": 2026, "month": 9},
                    "notes": NOTE,
                    "items": [
                        {
                            "material_kind": "seed",
                            "description": "Dried basil seeds",
                            "quantity": {
                                "kind": "item_count",
                                "value": 30,
                                "is_approximate": False,
                            },
                        }
                    ],
                }
            ),
        ),
    )
    manifest["records"]["event:harvest"] = str(harvest.event_id)
    for item in database.scalars(select(HarvestItem).where(HarvestItem.harvest_id == harvest.id)):
        manifest["records"]["item:basil"] = str(item.id)
    storage = AttachmentStorage(root)
    local = remember(
        "asset:local",
        asyncio.run(
            media.upload_asset(
                database,
                storage,
                image_upload(),
                AssetMetadataWrite(
                    title="Preview — Synthetic leaf illustration",
                    attribution="Repository-generated geometric fixture",
                    licence_label="CC0",
                ),
                commit=False,
            )
        ),
    )
    remember(
        "asset:external",
        media.create_external_asset(
            database,
            ExternalAssetCreate(
                image_url="https://example.invalid/preview-leaf.png",
                source_url="https://example.invalid/preview",
                attribution="Synthetic reference-only UAT example",
                title="Preview — External reference (intentionally offline)",
            ),
            target="plant",
            target_id=direct.id,
            commit=False,
        ),
    )
    # Ledger also owns the link created by the external-asset service.
    external_link = database.scalars(
        select(RecordMediaLink).where(RecordMediaLink.plant_id == direct.id)
    ).one()
    manifest["records"]["link:external"] = str(external_link.id)
    targets: list[tuple[primary.PrimaryTarget, UUID]] = [
        ("supplier", seller.id),
        ("seed_lot", lots[0].id),
        ("plant", derived.id),
    ]
    for target, identifier in targets:
        link = remember(
            f"link:{target}",
            media.create_link(
                database,
                target,
                identifier,
                local.id,
                LinkWrite(caption="Preview shared leaf illustration"),
                commit=False,
            ),
        )
        # Normal primary service commits. Building marker protects any interrupted partial seed.
        primary.set_primary(
            database,
            storage,
            target,
            identifier,
            PrimaryPhotoSelection(kind="local", photo_id=link.id),
        )
    database.commit()
    ensure_stored_material(database, root, manifest)
    manifest["state"] = "ready"
    write_manifest(root, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["seed", "status"])
    args = parser.parse_args()
    try:
        settings = get_settings()
        with Session(get_engine()) as database:
            root = require_identity(settings, database, require_marker=args.action == "seed")
            # Shared-volume process lock spans service commits and manifest writes.
            with (root / ".uat-fixture.lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                manifest = seed(database, root) if args.action == "seed" else read_manifest(root)
                if manifest is not None:
                    validate_manifest(database, root, manifest)
                owner = database.scalar(select(User).where(User.login_name == "preview"))
                print(f"Fixture initialized: {'yes' if manifest else 'no'}; version: {VERSION}")
                print(f"Preview owner initialized: {'yes' if owner else 'no'}")
                if manifest:
                    print(f"Baseline records: {len(manifest['records'])}; existing edits preserved")
                else:
                    print("Preview dataset not initialized. Run: make uat-preview-seed")
    except (FixtureError, ValueError, OSError) as error:
        print(f"UAT fixture: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
