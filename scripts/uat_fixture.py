"""PREVIEW-001 fixture v4, explicitly mounted by guarded UAT or Feature Review workflows."""

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
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol, TypeVar, cast
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
from florabase.schedule import service as schedule
from florabase.schedule.model import ScheduledActivity
from florabase.schedule.schemas import (
    ActivityKind,
    ScheduleComplete,
    ScheduleEvent,
    ScheduleTarget,
    ScheduleWrite,
    TargetKind,
)
from florabase.seed_lots import service as seeds
from florabase.seed_lots.model import SeedLot
from florabase.seed_lots.schemas import SeedLotCreate
from florabase.sowings import service as sowings
from florabase.sowings.model import Sowing
from florabase.sowings.schemas import SowingCreate
from florabase.suppliers import service as suppliers
from florabase.suppliers.model import Supplier
from florabase.suppliers.schemas import SupplierCreate
from florabase.taxonomy import service as taxonomy
from florabase.taxonomy.schemas import TaxonomyLinkWrite
from florabase.taxonomy.source import CHECKSUM as WFO_CHECKSUM
from florabase.taxonomy.source import WfoSource

VERSION = 4
NOTE = {
    "review": "Synthetic Feature Review data; no real collection or provenance claims.",
    "sourcing": "Synthetic Sourcing Preview data; no real collection or provenance claims.",
}.get(
    os.environ.get("FLORABASE_WORKFLOW_MODE", ""),
    "Synthetic UAT Preview data; no real collection or provenance claims.",
)
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
    "schedule": ScheduledActivity,
    "harvest": Harvest,
    "item": HarvestItem,
    "inventory": HarvestMaterialInventory,
    "asset": MediaAsset,
    "link": RecordMediaLink,
}


class FixtureRecord(Protocol):
    id: UUID


T = TypeVar("T", bound=FixtureRecord)


class FixtureError(RuntimeError):
    pass


def fixture_prefix() -> str:
    mode = os.environ.get("FLORABASE_WORKFLOW_MODE", "")
    return mode if mode in {"review", "sourcing"} else "uat"


def repair_hint() -> str:
    if fixture_prefix() == "review":
        return "inspect Review state; ordinary seed will not repair it"
    if fixture_prefix() == "sourcing":
        return "inspect Sourcing Preview state; ordinary seed will not repair it"
    return "run guarded uat-preview-reset"


def review_owner(database: Session) -> User:
    owners = list(database.scalars(select(User)))
    if len(owners) != 1 or not owners[0].owner or not owners[0].enabled:
        raise FixtureError(
            "Review needs exactly one enabled owner; use feature-review-bootstrap-owner"
        )
    return owners[0]


def sourcing_owner(database: Session) -> User:
    owners = list(database.scalars(select(User)))
    if len(owners) != 1 or not owners[0].owner or not owners[0].enabled:
        raise FixtureError(
            "Sourcing Preview needs exactly one enabled owner; use sourcing-preview-bootstrap-owner"
        )
    return owners[0]


def fixture_owner(database: Session) -> User:
    """The pre-bootstrapped owner of a persistent synthetic preview (Review or Sourcing)."""
    return review_owner(database) if fixture_prefix() == "review" else sourcing_owner(database)


def persistent_owner_key() -> str:
    prefix = fixture_prefix()
    return "owner:preview" if prefix == "uat" else f"owner:{prefix}"


def environment_label() -> str:
    return {"review": "Review", "sourcing": "Sourcing Preview"}.get(fixture_prefix(), "UAT Preview")


def require_empty_review_collection(database: Session) -> None:
    for model in MODELS.values():
        if model is User:
            continue
        query = select(model)
        # Canonical CLDR geography is installed by Alembic in every fresh database.
        if model is GeographicPlace:
            query = query.where(GeographicPlace.place_kind == "custom")
        if database.scalar(query.limit(1)) is not None:
            raise FixtureError(
                f"Unrecognized populated {environment_label()} baseline; no data changed"
            )


def require_identity(settings: Settings, database: Session, *, require_marker: bool = True) -> Path:
    url = make_url(settings.database_url)
    role = fixture_prefix()
    project = os.environ.get(f"FLORABASE_{role.upper()}_PROJECT", "")
    source = os.environ.get(f"FLORABASE_{role.upper()}_SOURCE", "")
    database_name = {
        "review": "florabase_review",
        "sourcing": "florabase_sourcing",
    }.get(role, "florabase_uat")
    project_pattern = {
        "review": r"florabase-feature-review",
        "sourcing": r"florabase-sourcing-preview(?:-smoke-[0-9a-f]{12})?",
    }.get(role, r"florabase-uat-preview(?:-smoke-[0-9a-f]{12})?")
    expected_origin = {
        "review": "http://localhost:15174",
        "sourcing": "http://localhost:15175",
    }.get(role, "http://localhost:15174")
    if not (
        os.environ.get("FLORABASE_WORKFLOW_MODE") == role
        and re.fullmatch(project_pattern, project)
        and Path(source).is_absolute()
        and settings.environment == Environment.DEVELOPMENT
        and settings.cookie_mode == CookieMode.LOOPBACK_DEVELOPMENT
        and (
            settings.canonical_origin == expected_origin
            or (
                project.startswith(
                    ("florabase-uat-preview-smoke-", "florabase-sourcing-preview-smoke-")
                )
                and urlsplit(settings.canonical_origin or "").hostname == "localhost"
                and urlsplit(settings.canonical_origin or "").scheme == "http"
                and 20000 <= (urlsplit(settings.canonical_origin or "").port or 0) <= 60000
            )
        )
        and settings.attachment_storage_root == Path("/var/lib/florabase/attachments")
        and url.host == "db"
        and url.port == 5432
        and url.database == database_name
        and url.username == database_name
    ):
        raise FixtureError(f"{role.upper()} environment identity refused; no data changed")
    root = cast(Path, settings.attachment_storage_root)
    if role in {"review", "sourcing"} and any(
        (root / name).exists() for name in (".uat-identity.json", ".uat-fixture.json")
    ):
        raise FixtureError("UAT bookkeeping in this preview media root; refused")
    marker = root / f".{role}-identity.json"
    expected = {
        "project": project,
        "source": source,
        "database": database_name,
        "origin": settings.canonical_origin,
    }
    if (require_marker and not marker.is_file()) or (
        marker.is_file() and json.loads(marker.read_text()) != expected
    ):
        raise FixtureError(
            f"Missing/mismatched guarded {role.upper()} resource marker; use the guarded seed action"
        )
    actual = database.execute(text("SELECT current_database(), current_user")).one()
    if tuple(actual) != (database_name, database_name):
        raise FixtureError("Connected database identity refused; no data changed")
    return root


def read_manifest(root: Path) -> dict[str, Any] | None:
    path = root / f".{fixture_prefix()}-fixture.json"
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
            "Preview fixture baseline is inconsistent/version incompatible; " + repair_hint()
        ) from error


def write_manifest(root: Path, value: dict[str, Any]) -> None:
    temporary = root / f".{fixture_prefix()}-fixture.tmp"
    with temporary.open("w") as stream:
        json.dump(value, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(root / f".{fixture_prefix()}-fixture.json")


def validate_manifest(database: Session, root: Path, manifest: dict[str, Any]) -> None:
    expected = {
        persistent_owner_key(),
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
    if manifest.get("taxonomy_extension") == 1:
        expected.update({"identity:Ocimum tenuiflorum", "seed:holy_basil"})
    if manifest.get("schedule_extension") == 1:
        expected.update(
            "schedule:" + key
            for key in (
                "overdue",
                "today",
                "seed",
                "sowing",
                "later",
                "repot",
                "location",
                "identity",
                "completed",
                "linked",
                "cancelled",
            )
        )
    if manifest.get("schedule_calendar_extension") == 1:
        expected.update(
            "schedule:calendar_" + key
            for key in (
                "density_1",
                "density_2",
                "density_3",
                "density_4",
                "density_5",
                "month_end",
                "next_month",
            )
        )
    if manifest.get("dashboard_extension") == 1:
        expected.update(
            {"seed:dashboard_unlinked", "sowing:dashboard_unknown", "sowing:dashboard_zero"}
        )
    if manifest.get("manual_review_extension") == 1:
        expected.update({"identity:genovese", "seed:genovese", "schedule:collection"})
    if fixture_prefix() == "review" and manifest.get("collection_visual_extension") == 1:
        expected.update(COLLECTION_VISUAL_KEYS)
    if fixture_prefix() == "sourcing" and manifest.get("sourcing_suppliers_extension") == 1:
        expected.update(SOURCING_SUPPLIER_RECORDS)
    if set(manifest["records"]) != expected:
        raise FixtureError("Preview fixture baseline has missing records; " + repair_hint())
    for key, value in manifest["records"].items():
        model = MODELS.get(key.split(":")[0])
        if model is None or database.get(model, UUID(value)) is None:
            raise FixtureError("Preview fixture baseline has missing records; " + repair_hint())
    if fixture_prefix() in {"review", "sourcing"} and (
        str(fixture_owner(database).id) != manifest["records"][persistent_owner_key()]
    ):
        raise FixtureError(f"{environment_label()} fixture owner mismatch; no data changed")
    for value in manifest["records"].values():
        asset = database.get(MediaAsset, UUID(value))
        if asset is not None and asset.attachment_id is not None:
            attachment = database.get(Attachment, asset.attachment_id)
            if attachment is None:
                raise FixtureError("Preview media metadata is missing; " + repair_hint())
            path = root / attachment.storage_key
            if (
                not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != attachment.sha256
            ):
                raise FixtureError(
                    "Preview media content is missing/inconsistent; " + repair_hint()
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
        filename=f"{fixture_prefix()}-preview-synthetic-leaf.png",
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


def ensure_taxonomy(database: Session, root: Path, manifest: dict[str, Any]) -> None:
    """Explicit synthetic UAT link confirmations; repeat seeding preserves operator changes."""
    if manifest.get("taxonomy_extension") == 1:
        return
    source_path = get_settings().wfo_snapshot_path
    if source_path is None or not source_path.is_file():
        return
    source = WfoSource(source_path)
    source.metadata()  # Corrupt configured sources fail before creating fixture records.
    ready = manifest["state"] == "ready"
    manifest["state"] = "building"
    write_manifest(root, manifest)
    holy = identities.create_botanical_identity(
        database,
        BotanicalIdentityCreate(
            scientific_name="Ocimum tenuiflorum", common_name="Preview — Holy basil"
        ),
    )
    packet = seeds.create_seed_lot(
        database,
        SeedLotCreate(
            botanical_identity_id=holy.id, label="Preview — Holy basil packet", notes=NOTE
        ),
    )
    manifest["records"]["identity:Ocimum tenuiflorum"] = str(holy.id)
    manifest["records"]["seed:holy_basil"] = str(packet.id)
    # Exact accepted IDs and authorships inspected in the approved official 2026-06 archive.
    # This explicit fixture association is not an automatic production name match/crosswalk.
    for name, external in (
        ("Ocimum basilicum", "wfo-0000253230"),
        ("Ocimum tenuiflorum", "wfo-0000253537"),
        ("Salvia officinalis", "wfo-0000301765"),
        ("Aloe vera", "wfo-0000758976"),
        ("Raphanus sativus", "wfo-0000402430"),
    ):
        record = database.get(BotanicalIdentity, UUID(manifest["records"]["identity:" + name]))
        if record is None:
            raise FixtureError("Missing taxonomy fixture identity")
        taxonomy.confirm(
            database,
            record.id,
            TaxonomyLinkWrite(
                source_taxon_id=external,
                checksum=WFO_CHECKSUM,
                expected_version=None,
                identity_updated_at=record.updated_at,
            ),
            source,
        )
    database.commit()
    manifest["taxonomy_extension"] = 1
    if ready:
        manifest["state"] = "ready"
    write_manifest(root, manifest)


def ensure_schedule(database: Session, root: Path, manifest: dict[str, Any]) -> None:
    """One explicit synthetic extension; repeating seed never reschedules operator edits."""
    if manifest.get("schedule_extension") == 1:
        return
    ready = manifest["state"] == "ready"
    manifest["state"] = "building"
    write_manifest(root, manifest)
    today = datetime.now(UTC).date()
    samples: tuple[tuple[str, ActivityKind, int, TargetKind, str, str], ...] = (
        ("overdue", "inspect", -3, "plant", "plant:direct", "Inspect nursery aloe leaves"),
        ("today", "water", 0, "plant", "plant:derived", "Water basil mother plant"),
        ("seed", "inspect", 3, "seed_lot", "seed:0", "Check seed packet storage"),
        ("sowing", "check_germination", 5, "sowing", "sowing:basil", "Check basil germination"),
        ("later", "repot", 21, "plant_group", "group:basil", "Repot basil group"),
        (
            "repot",
            "repot",
            2,
            "plant",
            "plant:direct",
            "Repot nursery aloe — optional Journal Event",
        ),
        (
            "location",
            "follow_up",
            7,
            "location",
            "location:Greenhouse bench",
            "Inspect greenhouse bench",
        ),
        (
            "identity",
            "follow_up",
            14,
            "botanical_identity",
            "identity:Ocimum basilicum",
            "Review basil cultivation plan",
        ),
        ("completed", "inspect", -2, "plant", "plant:direct", "Completed inspection without Event"),
        ("linked", "repot", -1, "plant", "plant:derived", "Completed repot with explicit Event"),
        ("cancelled", "follow_up", 10, "sowing", "sowing:basil", "Cancelled sowing follow-up"),
    )
    # A single transaction makes the extension atomic. Persist the marker only after commit.
    for key, kind, delta, target_kind, ref, title in samples:
        activity = schedule.create(
            database,
            ScheduleWrite(
                activity_kind=kind,
                title="Preview — " + title,
                due_on=today + timedelta(days=delta),
                target=ScheduleTarget(kind=target_kind, id=UUID(manifest["records"][ref])),
                notes=NOTE,
            ),
        )
        if key == "completed":
            schedule.complete(database, activity.id, ScheduleComplete(expected_version=1))
        elif key == "linked":
            schedule.complete(
                database,
                activity.id,
                ScheduleComplete(
                    expected_version=1,
                    event=ScheduleEvent(kind="repotting", occurred_on=today, notes=NOTE),
                ),
            )
        elif key == "cancelled":
            schedule.cancel(database, activity.id, 1)
        manifest["records"]["schedule:" + key] = str(activity.id)
    database.commit()
    manifest["schedule_extension"] = 1
    if ready:
        manifest["state"] = "ready"
    write_manifest(root, manifest)


def ensure_schedule_calendar(database: Session, root: Path, manifest: dict[str, Any]) -> None:
    """Add Calendar density once; never reschedule existing synthetic/operator work."""
    if manifest.get("schedule_calendar_extension") == 1:
        return
    ready = manifest["state"] == "ready"
    manifest["state"] = "building"
    write_manifest(root, manifest)
    today = datetime.now(UTC).date()
    next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
    month_end = next_month - timedelta(days=1)
    samples: tuple[tuple[str, ActivityKind, date, TargetKind, str, str], ...] = (
        ("density_1", "inspect", today, "plant", "plant:direct", "Check aloe roots"),
        ("density_2", "fertilize", today, "plant_group", "group:basil", "Feed basil group"),
        ("density_3", "inspect", today, "seed_lot", "seed:0", "Inspect seed packets"),
        (
            "density_4",
            "follow_up",
            today,
            "location",
            "location:Greenhouse bench",
            "Plan bench space",
        ),
        ("density_5", "check_germination", today, "sowing", "sowing:basil", "Review basil sowing"),
        ("month_end", "inspect", month_end, "plant", "plant:direct", "Month-end aloe inspection"),
        (
            "next_month",
            "repot",
            next_month + timedelta(days=4),
            "plant_group",
            "group:basil",
            "Next-month basil repot",
        ),
    )
    for key, kind, due, target_kind, ref, title in samples:
        activity = schedule.create(
            database,
            ScheduleWrite(
                activity_kind=kind,
                title="Preview — " + title,
                due_on=due,
                target=ScheduleTarget(kind=target_kind, id=UUID(manifest["records"][ref])),
                notes=NOTE,
            ),
        )
        manifest["records"]["schedule:calendar_" + key] = str(activity.id)
    database.commit()
    manifest["schedule_calendar_extension"] = 1
    if ready:
        manifest["state"] = "ready"
    write_manifest(root, manifest)


def ensure_dashboard(database: Session, root: Path, manifest: dict[str, Any]) -> None:
    """Add explicit sourcing/unknown-outcome examples once; never repair operator edits."""
    if manifest.get("dashboard_extension") == 1:
        return
    ready = manifest["state"] == "ready"
    manifest["state"] = "building"
    write_manifest(root, manifest)
    lot = seeds.create_seed_lot(
        database,
        SeedLotCreate(
            botanical_identity_id=UUID(manifest["records"]["identity:Ocimum basilicum"]),
            label="Preview — Purchased basil without Order link",
            source_kind="purchased",
            notes=NOTE,
        ),
    )
    manifest["records"]["seed:dashboard_unlinked"] = str(lot.id)
    for key, count in (("unknown", None), ("zero", 0)):
        sowing = sowings.create_sowing(
            database,
            SowingCreate(
                seed_lot_id=lot.id,
                label=f"Preview — Basil germination {key}",
                germinated_count=count,
                notes=NOTE,
            ),
        )
        manifest["records"]["sowing:dashboard_" + key] = str(sowing.id)
    database.commit()
    manifest["dashboard_extension"] = 1
    if ready:
        manifest["state"] = "ready"
    write_manifest(root, manifest)


def ensure_manual_review(database: Session, root: Path, manifest: dict[str, Any]) -> None:
    """Add only missing review examples once; never rewrite an existing v4 collection."""
    if manifest.get("manual_review_extension") == 1:
        return
    ready = manifest["state"] == "ready"
    manifest["state"] = "building"
    write_manifest(root, manifest)
    cultivar = identities.create_botanical_identity(
        database,
        BotanicalIdentityCreate(
            scientific_name="Ocimum basilicum",
            cultivar_name="Genovese",
            common_name="Preview — Genovese basil",
        ),
    )
    put_botanical_profile(
        database,
        cultivar.id,
        BotanicalProfilePut(
            description=f"{NOTE} Cultivar typography and profile editor example.",
            cultivation=f"{NOTE} Review watering and repotting notes here; not cultivation advice.",
        ),
    )
    packet = seeds.create_seed_lot(
        database,
        SeedLotCreate(
            botanical_identity_id=cultivar.id,
            label="Preview — Genovese packet with unknown quantity",
            source_kind="purchased",
            order_id=UUID(manifest["records"]["order:partial"]),
            location_id=UUID(manifest["records"]["location:Indoor seed shelf"]),
            notes=NOTE,
        ),
    )
    activity = schedule.create(
        database,
        ScheduleWrite(
            activity_kind="follow_up",
            title="Preview — Review whole collection plan",
            due_on=datetime.now(UTC).date(),
            target=None,
            notes=NOTE,
        ),
    )
    manifest["records"].update(
        {
            "identity:genovese": str(cultivar.id),
            "seed:genovese": str(packet.id),
            "schedule:collection": str(activity.id),
        }
    )
    database.commit()
    manifest["manual_review_extension"] = 1
    if ready:
        manifest["state"] = "ready"
    write_manifest(root, manifest)


COLLECTION_VISUAL_KEYS = {
    "harvest:group_materials",
    "event:group_materials",
    "link:harvest",
    *{f"item:group_materials_{index}" for index in range(4)},
    *{f"location:deep_{index}" for index in range(6)},
    "location:retired_empty",
}


def ensure_collection_visual(database: Session, root: Path, manifest: dict[str, Any]) -> None:
    """Review-only additive historical-material/deep-hierarchy examples; preserve all repeats."""
    if fixture_prefix() != "review" or manifest.get("collection_visual_extension") == 1:
        return
    ready = manifest["state"] == "ready"
    manifest["state"] = "building"
    write_manifest(root, manifest)
    collected = harvests.write_harvest(
        database,
        HarvestWrite.model_validate(
            {
                "plant_group_id": manifest["records"]["group:basil"],
                "label": "Preview — Mixed group collection",
                "occurred_on": None,
                "notes": NOTE,
                "items": [
                    {
                        "material_kind": "leaf",
                        "description": "Fresh leaves",
                        "quantity": {
                            "kind": "weight",
                            "value": "15",
                            "unit": "g",
                            "is_approximate": True,
                        },
                    },
                    {"material_kind": "flower", "description": "Quantity not recorded"},
                    {
                        "material_kind": "seed",
                        "quantity": {"kind": "item_count", "value": "120", "is_approximate": False},
                    },
                    {"material_kind": "stem_or_shoot"},
                ],
            }
        ),
    )
    manifest["records"]["harvest:group_materials"] = str(collected.id)
    manifest["records"]["event:group_materials"] = str(collected.event_id)
    for index, item in enumerate(
        database.scalars(
            select(HarvestItem)
            .where(HarvestItem.harvest_id == collected.id)
            .order_by(HarvestItem.display_order)
        )
    ):
        manifest["records"][f"item:group_materials_{index}"] = str(item.id)
    link = media.create_link(
        database,
        "harvest",
        collected.id,
        UUID(manifest["records"]["asset:local"]),
        LinkWrite(caption="Preview — explicit Harvest primary"),
        commit=False,
    )
    manifest["records"]["link:harvest"] = str(link.id)
    primary.set_primary(
        database,
        AttachmentStorage(root),
        "harvest",
        collected.id,
        PrimaryPhotoSelection(kind="local", photo_id=link.id),
    )
    parent_id = UUID(manifest["records"]["location:Greenhouse bench"])
    for index in range(6):
        location = locations.create_location(
            database,
            LocationCreate(
                name=f"Preview — Propagation shelf level {index + 1}",
                parent_id=parent_id,
                usage_scopes=["plants", "sowings", "seed_lots", "harvest_inventory"],
            ),
        )
        manifest["records"][f"location:deep_{index}"] = str(location.id)
        parent_id = location.id
    retired = locations.create_location(
        database, LocationCreate(name="Preview — Retired empty cabinet", usage_scopes=["seed_lots"])
    )
    locations.set_location_retired(database, retired.id, retired=True)
    manifest["records"]["location:retired_empty"] = str(retired.id)
    database.commit()
    manifest["collection_visual_extension"] = 1
    if ready:
        manifest["state"] = "ready"
    write_manifest(root, manifest)


SOURCING_SUPPLIER_RECORDS = {
    "supplier:online_seed_shop",
    "supplier:swap_group",
    "supplier:neighbour",
    "supplier:community_orchard",
    "supplier:wholesale_grower",
    "supplier:local_market",
    "supplier:retired_market",
    "order:shop",
    "order:grower",
    "seed:sourcing_shop",
    "seed:sourcing_swap",
    "seed:sourcing_grower",
    "link:supplier_shop",
}


def ensure_sourcing_suppliers(database: Session, root: Path, manifest: dict[str, Any]) -> None:
    """Sourcing Preview only: broaden the supplier/order/acquisition directory for visual review.

    Uses only existing Supplier/Order/SeedLot services and grounded fields; no invented metrics.
    """
    if fixture_prefix() != "sourcing" or manifest.get("sourcing_suppliers_extension") == 1:
        return
    ready = manifest["state"] == "ready"
    manifest["state"] = "building"
    write_manifest(root, manifest)
    records = manifest["records"]
    basil = UUID(records["identity:Ocimum basilicum"])
    lavender = UUID(records["identity:Lavandula angustifolia"])
    aloe = UUID(records["identity:Aloe vera"])
    indoor_id = UUID(records["location:Indoor seed shelf"])

    def add(key: str, value: FixtureRecord) -> None:
        records[key] = str(value.id)

    shop = suppliers.create_supplier(
        database,
        SupplierCreate(
            name="Preview — Northwind online seeds",
            kind="seller",
            website="https://example.invalid/northwind-seeds",
            email="orders@example.invalid",
            phone="+39 011 555 0100",
            notes=NOTE,
        ),
    )
    add("supplier:online_seed_shop", shop)
    swap = suppliers.create_supplier(
        database,
        SupplierCreate(
            name="Preview — Allotment seed swap",
            kind="exchange",
            website="https://example.invalid/seed-swap",
            notes=NOTE,
        ),
    )
    add("supplier:swap_group", swap)
    neighbour = suppliers.create_supplier(
        database,
        SupplierCreate(
            name="Preview — Neighbour with spare seedlings", kind="person", phone="+39 333 555 0111"
        ),
    )
    add("supplier:neighbour", neighbour)
    orchard = suppliers.create_supplier(
        database,
        SupplierCreate(
            name="Preview — Community orchard",
            kind="seller",
            email="hello@example.invalid",
            notes=NOTE,
        ),
    )
    add("supplier:community_orchard", orchard)
    grower = suppliers.create_supplier(
        database,
        SupplierCreate(
            name="Preview — Regional wholesale grower with a deliberately long trading name",
            kind="nursery",
            website="https://example.invalid/regional-grower",
            email="trade@example.invalid",
            phone="+39 02 555 0122",
            notes=NOTE,
        ),
    )
    add("supplier:wholesale_grower", grower)
    # Name-and-kind-only record exercises the restrained icon fallback and empty contact facts.
    market = suppliers.create_supplier(
        database, SupplierCreate(name="Preview — Saturday market stall", kind="other")
    )
    add("supplier:local_market", market)
    retired = suppliers.create_supplier(
        database,
        SupplierCreate(
            name="Preview — Retired supermarket chain",
            kind="supermarket",
            website="https://example.invalid/retired-chain",
            notes=NOTE,
        ),
    )
    add("supplier:retired_market", retired)
    suppliers.set_supplier_retired(database, retired, retired=True)

    shop_order = orders.create_order(
        database,
        OrderCreate.model_validate(
            {
                "supplier_id": shop.id,
                "ordered_on": {"precision": "day", "year": 2026, "month": 4, "day": 12},
                "order_reference": "Preview — NW-2026-0042",
                "total_price": "23.90",
                "currency": "EUR",
                "notes": NOTE,
            }
        ),
    )
    add("order:shop", shop_order)
    grower_order = orders.create_order(
        database,
        OrderCreate.model_validate(
            {
                "supplier_id": grower.id,
                "ordered_on": {"precision": "month", "year": 2026, "month": 3},
                "order_reference": "Preview — Trade order",
                "total_price": "180.00",
                "currency": "EUR",
                "notes": NOTE,
            }
        ),
    )
    add("order:grower", grower_order)

    add(
        "seed:sourcing_shop",
        seeds.create_seed_lot(
            database,
            SeedLotCreate.model_validate(
                {
                    "botanical_identity_id": basil,
                    "label": "Preview — Basil packet from online order",
                    "source_kind": "purchased",
                    "supplier_id": shop.id,
                    "order_id": shop_order.id,
                    "location_id": indoor_id,
                    "quantity": {"kind": "seed_count", "value": 120, "is_approximate": False},
                    "notes": NOTE,
                }
            ),
        ),
    )
    add(
        "seed:sourcing_swap",
        seeds.create_seed_lot(
            database,
            SeedLotCreate.model_validate(
                {
                    "botanical_identity_id": lavender,
                    "label": "Preview — Lavender seeds from a swap",
                    "source_kind": "gift_exchange",
                    "supplier_id": swap.id,
                    "location_id": indoor_id,
                    "notes": NOTE,
                }
            ),
        ),
    )
    add(
        "seed:sourcing_grower",
        seeds.create_seed_lot(
            database,
            SeedLotCreate.model_validate(
                {
                    "botanical_identity_id": aloe,
                    "label": "Preview — Aloe offsets from the wholesale grower",
                    "source_kind": "purchased",
                    "supplier_id": grower.id,
                    "order_id": grower_order.id,
                    "location_id": indoor_id,
                    "quantity": {"kind": "seed_count", "value": 6, "is_approximate": False},
                    "notes": NOTE,
                }
            ),
        ),
    )
    # Give the online shop a real primary photo so the directory mixes thumbnails and fallbacks.
    link = media.create_link(
        database,
        "supplier",
        shop.id,
        UUID(records["asset:local"]),
        LinkWrite(caption="Preview supplier leaf illustration"),
        commit=False,
    )
    add("link:supplier_shop", link)
    primary.set_primary(
        database,
        AttachmentStorage(root),
        "supplier",
        shop.id,
        PrimaryPhotoSelection(kind="local", photo_id=link.id),
    )
    database.commit()
    ensure_stored_material(database, root, manifest)
    manifest["sourcing_suppliers_extension"] = 1
    if ready:
        manifest["state"] = "ready"
    write_manifest(root, manifest)


def seed(database: Session, root: Path) -> dict[str, Any]:
    existing = read_manifest(root)
    if existing is not None:
        validate_manifest(database, root, existing)
        ensure_stored_material(database, root, existing)
        ensure_taxonomy(database, root, existing)
        ensure_schedule(database, root, existing)
        ensure_schedule_calendar(database, root, existing)
        ensure_dashboard(database, root, existing)
        ensure_manual_review(database, root, existing)
        ensure_collection_visual(database, root, existing)
        ensure_sourcing_suppliers(database, root, existing)
        return existing
    owner = fixture_owner(database) if fixture_prefix() in {"review", "sourcing"} else None
    if owner is not None:
        require_empty_review_collection(database)
    elif (
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

    if owner is not None:
        remember(persistent_owner_key(), owner)
    else:
        owner = remember(
            "owner:preview",
            bootstrap_owner(database, "preview", "uat-bootstrap-only-password", "UAT Preview"),
        )
        # Public password is restricted to guarded UAT; Review retains the existing account.
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
                attribution=f"Synthetic reference-only {fixture_prefix().upper()} example",
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
    ensure_taxonomy(database, root, manifest)
    ensure_schedule(database, root, manifest)
    ensure_schedule_calendar(database, root, manifest)
    ensure_dashboard(database, root, manifest)
    ensure_manual_review(database, root, manifest)
    ensure_collection_visual(database, root, manifest)
    ensure_sourcing_suppliers(database, root, manifest)
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
            with (root / f".{fixture_prefix()}-fixture.lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                manifest = seed(database, root) if args.action == "seed" else read_manifest(root)
                if manifest is not None:
                    validate_manifest(database, root, manifest)
                owner = (
                    fixture_owner(database)
                    if fixture_prefix() in {"review", "sourcing"}
                    else database.scalar(select(User).where(User.login_name == "preview"))
                )
                print(f"Fixture initialized: {'yes' if manifest else 'no'}; version: {VERSION}")
                print(f"Preview owner initialized: {'yes' if owner else 'no'}")
                if manifest:
                    print(f"Baseline records: {len(manifest['records'])}; existing edits preserved")
                else:
                    print(
                        "Preview dataset not initialized. Run the guarded environment seed action."
                    )
    except (FixtureError, ValueError, OSError) as error:
        print(f"{fixture_prefix().upper()} fixture: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
