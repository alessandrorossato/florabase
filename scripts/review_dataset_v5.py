"""Additive Extended Botanical Review Dataset v5; guarded Review only, never UAT."""

from __future__ import annotations

import argparse
import asyncio
import fcntl
import hashlib
import io
import json
import os
import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import UUID

import uat_fixture as v4
from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.datastructures import Headers

from florabase.attachments.model import Attachment
from florabase.attachments.storage import AttachmentStorage
from florabase.botanical_profiles.model import (
    BotanicalProfile,
    BotanicalProfileNativeRange,
)
from florabase.collection_photos.model import (
    CollectionPrimaryPhoto,
    MediaAsset,
    RecordMediaLink,
)
from florabase.collection_photos.schemas import PrimaryPhotoSelection
from florabase.plants.schemas import PlantExtractionCreate
from florabase.sowings import germination_service
from florabase.sowings.germination_schemas import GerminationObservationWrite
from florabase.sowings.model import GerminationObservation

VERSION = 5
ASSETS = Path(__file__).resolve().parent / "fixtures" / "botanical-v5"
LEDGER = ".review-dataset-v5.json"
MODELS = {**v4.MODELS, "profile": BotanicalProfile, "observation": GerminationObservation}


def inputs() -> tuple[dict[str, Any], dict[str, dict[str, Any]], str]:
    plan = json.loads((ASSETS / "plan.json").read_text())
    photos = json.loads((ASSETS / "media-manifest.json").read_text())
    if plan.get("version") != VERSION:
        raise v4.FixtureError("Unsupported extended dataset plan")
    for photo in photos:
        path = ASSETS / photo["file"]
        if (
            path.parent != ASSETS
            or hashlib.sha256(path.read_bytes()).hexdigest() != photo["sha256"]
        ):
            raise v4.FixtureError("Packaged photo digest/path mismatch")
        if photo["licence"] not in {"CC0-1.0", "CC-BY-2.0", "CC-BY-3.0", "CC-BY-4.0"}:
            raise v4.FixtureError("Unreviewed media licence")
    digest = hashlib.sha256(json.dumps([plan, photos], sort_keys=True).encode()).hexdigest()
    keys = [node["key"] for node in plan["nodes"]]
    if len(keys) != len(set(keys)):
        raise v4.FixtureError("Duplicate deterministic logical key")
    return plan, {photo["key"]: photo for photo in photos}, digest


def write(root: Path, manifest: dict[str, Any]) -> None:
    temporary = root / (LEDGER + ".tmp")
    with temporary.open("w") as stream:
        json.dump(manifest, stream, sort_keys=True, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(root / LEDGER)


def require_review(database: Session) -> tuple[Path, dict[str, Any]]:
    if os.environ.get("FLORABASE_WORKFLOW_MODE") != "review":
        raise v4.FixtureError("Extended dataset is Review-only; no data changed")
    root = v4.require_identity(v4.get_settings(), database)
    baseline = v4.read_manifest(root)
    if baseline is None:
        raise v4.FixtureError("A ready v4 Review baseline is required")
    v4.validate_manifest(database, root, baseline)
    return root, baseline


def resolve(value: Any, refs: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        if set(value) == {"$ref"}:
            return refs[value["$ref"]]
        return {key: resolve(item, refs) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve(item, refs) for item in value]
    return value


def expected_keys(plan: dict[str, Any]) -> set[str]:
    keys = {node["key"] for node in plan["nodes"]}
    keys.update("item:" + node["key"] for node in plan["nodes"] if node["kind"] == "harvest")
    keys.add("event:extraction")
    return keys


def validate(database: Session, root: Path, manifest: dict[str, Any], digest: str) -> None:
    plan, _, _ = inputs()
    if manifest.get("version") != VERSION or manifest.get("plan_sha256") != digest:
        raise v4.FixtureError(
            "v5 plan/version changed; inspect instead of overwriting the extension"
        )
    baseline = v4.read_manifest(root)
    if baseline is None or manifest.get("baseline_records") != baseline["records"]:
        raise v4.FixtureError("v4 baseline references changed; v5 completion refused")
    if manifest.get("owner_id") != str(v4.review_owner(database).id):
        raise v4.FixtureError("v5 owner mismatch")
    if set(manifest["records"]) != expected_keys(plan):
        raise v4.FixtureError("v5 references incomplete; completion refused")
    for key, value in manifest["records"].items():
        if key.startswith("range:"):
            row = database.get(
                BotanicalProfileNativeRange, (UUID(value["identity"]), UUID(value["place"]))
            )
        else:
            row = database.get(MODELS[key.split(":", 1)[0]], UUID(value))
        if row is None:
            raise v4.FixtureError(f"v5 managed reference missing: {key}; no repair/overwrite")
        if isinstance(row, MediaAsset) and row.attachment_id:
            attachment = database.get(Attachment, row.attachment_id)
            if attachment is None or not (root / attachment.storage_key).is_file():
                raise v4.FixtureError(f"v5 protected content missing: {key}")
            if (
                hashlib.sha256((root / attachment.storage_key).read_bytes()).hexdigest()
                != attachment.sha256
            ):
                raise v4.FixtureError(f"v5 protected content differs: {key}")


def counts(database: Session) -> dict[str, int]:
    return {
        name: int(database.scalar(select(func.count()).select_from(model)) or 0)
        for name, model in MODELS.items()
        if name
        not in {"owner", "external_taxon", "link", "place", "item", "profile", "observation"}
    } | {
        "record_media_links": int(
            database.scalar(select(func.count()).select_from(RecordMediaLink)) or 0
        ),
        "germination_observations": int(
            database.scalar(select(func.count()).select_from(GerminationObservation)) or 0
        ),
        "harvest_items": int(
            database.scalar(select(func.count()).select_from(v4.HarvestItem)) or 0
        ),
        "protected_attachments": int(
            database.scalar(select(func.count()).select_from(Attachment)) or 0
        ),
        "custom_geographic_places": int(
            database.scalar(
                select(func.count())
                .select_from(v4.GeographicPlace)
                .where(v4.GeographicPlace.place_kind == "custom")
            )
            or 0
        ),
        "profiles": int(database.scalar(select(func.count()).select_from(BotanicalProfile)) or 0),
        "identities_with_ranges": int(
            database.scalar(
                select(func.count(func.distinct(BotanicalProfileNativeRange.botanical_profile_id)))
            )
            or 0
        ),
        "local_media": int(
            database.scalar(
                select(func.count()).select_from(MediaAsset).where(MediaAsset.kind == "local")
            )
            or 0
        ),
        "external_media": int(
            database.scalar(
                select(func.count()).select_from(MediaAsset).where(MediaAsset.kind == "external")
            )
            or 0
        ),
    }


def create_graph(
    database: Session,
    root: Path,
    baseline: dict[str, Any],
    manifest: dict[str, Any],
    *,
    fail_after: int | None = None,
) -> None:
    """All owning services flush in one transaction; media ingestion explicitly uses commit=False."""
    plan, photos, _ = inputs()
    refs: dict[str, Any] = {
        "baseline:" + key: UUID(value) for key, value in baseline["records"].items()
    }
    for place in database.scalars(
        select(v4.GeographicPlace).where(v4.GeographicPlace.place_kind == "canonical")
    ):
        refs["country:" + str(place.source_code)] = place.id
    storage = AttachmentStorage(root)
    records = manifest["records"]
    creators: dict[str, tuple[Callable[..., Any], Any]] = {
        "identity": (v4.identities.create_botanical_identity, v4.BotanicalIdentityCreate),
        "location": (v4.locations.create_location, v4.LocationCreate),
        "place": (v4.places.create_geographic_place, v4.GeographicPlaceCreate),
        "site": (v4.sites.create_provenance_site, v4.ProvenanceSiteCreate),
        "supplier": (v4.suppliers.create_supplier, v4.SupplierCreate),
        "order": (v4.orders.create_order, v4.OrderCreate),
        "seed": (v4.seeds.create_seed_lot, v4.SeedLotCreate),
        "sowing": (v4.sowings.create_sowing, v4.SowingCreate),
        "plant": (v4.plants.create_plant, v4.PlantCreate),
        "group": (v4.plants.create_plant_group, v4.PlantGroupCreate),
        "harvest": (v4.harvests.write_harvest, v4.HarvestWrite),
        "schedule": (v4.schedule.create, v4.ScheduleWrite),
    }
    for index, node in enumerate(plan["nodes"]):
        if fail_after is not None and index == fail_after:
            raise v4.FixtureError("Injected failure before fixture completion")
        key, kind = node["key"], node["kind"]
        payload = resolve(node["payload"], refs)
        if kind in creators:
            create, schema = creators[kind]
            row = create(database, schema.model_validate(payload))
        elif kind == "profile":
            identifier = payload.pop("identity_id")
            v4.put_botanical_profile(
                database, identifier, v4.BotanicalProfilePut.model_validate(payload)
            )
            refs[key] = identifier
            records[key] = str(identifier)
            continue
        elif kind == "range":
            identifier, place_id = payload["identity_id"], payload["place_id"]
            v4.add_botanical_native_range(database, identifier, place_id)
            records[key] = {"identity": str(identifier), "place": str(place_id)}
            continue
        elif kind == "extract":
            group_id = payload.pop("plant_group_id")
            row, _, event = v4.plants.extract_plant(
                database, group_id, PlantExtractionCreate.model_validate(payload)
            )
            records["event:extraction"] = str(event.id)
        elif kind == "event":
            target = payload.pop("plant_id")
            row = v4.events.create_event(
                database, "plant", target, v4.EventCreate.model_validate(payload)
            )
        elif kind == "observation":
            target = payload.pop("sowing_id")
            row = germination_service.create_observation(
                database, target, GerminationObservationWrite.model_validate(payload)
            )
        elif kind == "inventory":
            target = payload.pop("item_id")
            row = v4.initialize_inventory(
                database, target, v4.InventoryWrite.model_validate(payload)
            )
        elif kind == "asset":
            photo = photos[payload["media_key"]]
            metadata = dict(
                title=f"Review v5 — {photo['species']} — "
                + ("external reference" if payload["external"] else "protected local illustration"),
                attribution=f"{photo['creator']}; {photo['source_url']}; {photo['changes']}",
                licence_label=photo["licence"],
                licence_url=photo["licence_url"],
            )
            if payload["external"]:
                row = v4.media.create_external_asset(
                    database,
                    v4.ExternalAssetCreate(
                        **metadata, image_url=photo["image_url"], source_url=photo["source_url"]
                    ),
                    commit=False,
                )
            else:
                upload = UploadFile(
                    file=io.BytesIO((ASSETS / photo["file"]).read_bytes()),
                    filename=photo["file"],
                    headers=Headers({"content-type": "image/jpeg"}),
                )
                row = asyncio.run(
                    v4.media.upload_asset(
                        database, storage, upload, v4.AssetMetadataWrite(**metadata), commit=False
                    )
                )
                attachment = database.get(Attachment, row.attachment_id)
                assert attachment is not None
                manifest["created_files"].append(attachment.storage_key)
        elif kind == "link":
            row = v4.media.create_link(
                database,
                payload["target_type"],
                payload["target_id"],
                payload["asset_id"],
                v4.LinkWrite(caption=payload["caption"]),
                commit=False,
            )
        else:
            raise v4.FixtureError(f"Unknown plan node: {kind}")
        refs[key] = row.id
        records[key] = str(row.id)
        if kind == "harvest":
            item = database.scalar(
                select(v4.HarvestItem).where(v4.HarvestItem.harvest_id == row.id)
            )
            assert item is not None
            refs["item:" + key] = item.id
            records["item:" + key] = str(item.id)
    retiring = database.get(v4.Supplier, refs[plan["retire_supplier"]])
    assert retiring is not None
    v4.suppliers.set_supplier_retired(database, retiring, retired=True)
    manifest["counts_at_creation"] = counts(database)
    manifest["logical_category_counts"] = dict(Counter(node["kind"] for node in plan["nodes"]))


def primary_photos(database: Session, root: Path, manifest: dict[str, Any]) -> None:
    """Only previously undesignated new fixture targets; never replace an operator's choice."""
    storage = AttachmentStorage(root)
    for key, value in manifest["records"].items():
        if not key.startswith("link:local:"):
            continue
        link = database.get(RecordMediaLink, UUID(value))
        assert link is not None and link.seed_lot_id is not None
        current = database.scalar(
            select(CollectionPrimaryPhoto).where(
                CollectionPrimaryPhoto.seed_lot_id == link.seed_lot_id
            )
        )
        if current is None:
            v4.primary.set_primary(
                database,
                storage,
                "seed_lot",
                link.seed_lot_id,
                PrimaryPhotoSelection(kind="local", photo_id=link.id),
            )


def seed(database: Session, root: Path, baseline: dict[str, Any]) -> dict[str, Any]:
    plan, _, digest = inputs()
    owner_id = str(v4.review_owner(database).id)
    path = root / LEDGER
    if path.is_file():
        manifest: dict[str, Any] = json.loads(path.read_text())
        if (
            manifest.get("version") != VERSION
            or manifest.get("owner_id") != owner_id
            or manifest.get("plan_sha256") != digest
        ):
            raise v4.FixtureError("v5 plan/owner/version mismatch; no data changed")
        if manifest["state"] == "ready":
            validate(database, root, manifest, digest)
            return manifest
        # A prepared graph may have committed before the final filesystem rename.
        if manifest["state"] == "prepared":
            validate(database, root, manifest, digest)
            primary_photos(database, root, manifest)
            manifest["state"] = "ready"
            manifest.pop("diagnostic", None)
            write(root, manifest)
            return manifest
        raise v4.FixtureError(
            "v5 incomplete/failed seed; inspect its diagnostic before recovery; no completion claimed"
        )
    manifest = {
        "version": VERSION,
        "name": plan["name"],
        "state": "building",
        "plan_sha256": digest,
        "owner_id": owner_id,
        "baseline_records": baseline["records"],
        "records": {},
        "created_files": [],
    }
    write(root, manifest)
    try:
        create_graph(database, root, baseline, manifest)
        manifest["state"] = "prepared"
        write(root, manifest)
        database.commit()
        validate(database, root, manifest, digest)
        primary_photos(database, root, manifest)
        manifest["state"] = "ready"
        write(root, manifest)
    except Exception as error:
        database.rollback()
        # Keep committed prepared graphs recoverable; never call them ready after an error.
        manifest["diagnostic"] = f"{type(error).__name__}: {error}"
        if manifest["state"] != "prepared":
            manifest["state"] = "failed"
        write(root, manifest)
        raise
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["seed", "status"])
    args = parser.parse_args()
    try:
        with Session(v4.get_engine()) as database:
            root, baseline = require_review(database)
            with (root / ".review-fixture.lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                if args.action == "seed":
                    manifest = seed(database, root, baseline)
                elif (root / LEDGER).is_file():
                    manifest = json.loads((root / LEDGER).read_text())
                    validate(database, root, manifest, inputs()[2])
                    if manifest["state"] != "ready":
                        raise v4.FixtureError("v5 is incomplete; not ready")
                else:
                    raise v4.FixtureError("v5 not initialized; v4 remains unchanged")
                print(
                    json.dumps(
                        {
                            "dataset": manifest["name"],
                            "version": VERSION,
                            "state": manifest["state"],
                            "managed_references": len(manifest["records"]),
                            "counts": counts(database),
                            "owner_login": v4.review_owner(database).login_name,
                            "existing_edits_preserved": True,
                        },
                        sort_keys=True,
                    )
                )
    except Exception as error:
        print(f"Extended Review seed refused/failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
