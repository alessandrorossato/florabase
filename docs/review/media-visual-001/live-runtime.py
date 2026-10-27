"""Explicit additive layout/relationship fixtures for the exact Media-owned Review."""
# ruff: noqa: T201 -- Explicit Review runner reports synthetic evidence, never credentials.

from __future__ import annotations

import asyncio
import fcntl
import hashlib
import io
import json
import os
import sys
from pathlib import Path
from uuid import UUID

import review_dataset_v5 as v5
import uat_fixture as v4
from fastapi import UploadFile
from PIL import Image, ImageDraw
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.datastructures import Headers

from florabase.attachments.model import Attachment
from florabase.attachments.storage import AttachmentStorage
from florabase.auth.model import User
from florabase.auth.service import bootstrap_owner
from florabase.collection_photos.model import BotanicalIdentityCoverImage
from florabase.collection_photos.service import set_local_identity_cover
from florabase.media.schemas import AssetMetadataWrite, LinkWrite
from florabase.seed_lots.model import SeedLot

LEDGER = ".media-visual-001.json"


def upload(data: bytes, filename: str, mime: str) -> UploadFile:
    return UploadFile(
        filename=filename, file=io.BytesIO(data), headers=Headers({"content-type": mime})
    )


def validate(db: Session, root: Path, ledger: dict) -> None:
    assert ledger["state"] == "ready"
    assert ledger["version"] == 1
    for key, value in ledger["assets"].items():
        asset = db.get(v4.MediaAsset, UUID(value))
        assert asset is not None, f"Missing managed asset: {key}; no repair"
        attachment = db.get(Attachment, asset.attachment_id)
        assert attachment is not None
        assert (
            hashlib.sha256((root / attachment.storage_key).read_bytes()).hexdigest()
            == attachment.sha256
        )
    for value in ledger["links"]:
        assert db.get(v4.RecordMediaLink, UUID(value)) is not None
    for value in ledger["covers"]:
        assert db.get(BotanicalIdentityCoverImage, UUID(value)) is not None


def check_refusals(db: Session) -> None:
    from unittest.mock import patch

    settings = v4.get_settings()
    for values in (
        {"FLORABASE_WORKFLOW_MODE": "dev"},
        {"FLORABASE_REVIEW_PROJECT": "florabase-feature-review"},
        {"FLORABASE_REVIEW_PROJECT": "florabase-ui-audit-bc88"},
        {"FLORABASE_REVIEW_SOURCE": "/foreign-worktree"},
    ):
        with patch.dict(os.environ, values):
            try:
                v4.require_identity(settings, db)
            except v4.FixtureError:
                continue
            raise AssertionError(f"Foreign runtime accepted: {values}")
    for values in (
        {"canonical_origin": "http://localhost:15279"},
        {"database_url": "postgresql+psycopg://florabase_review:x@db:5432/florabase_review"},
    ):
        try:
            v4.require_identity(settings.model_copy(update=values), db)
        except v4.FixtureError:
            continue
        raise AssertionError(f"Foreign configuration accepted: {values}")


def enhance(db: Session, root: Path, extended: dict) -> dict:
    path = root / LEDGER
    if path.exists():
        ledger = json.loads(path.read_text())
        validate(db, root, ledger)
        return ledger
    ledger = {"version": 1, "state": "building", "assets": {}, "links": [], "covers": []}
    path.write_text(json.dumps(ledger))
    storage = AttachmentStorage(root)
    refs = extended["records"]
    photos = json.loads((v5.ASSETS / "media-manifest.json").read_text())
    # Cover uploads create independent assets; they do not add unique photographs.
    for n in (0, 1):
        photo = photos[n]
        seed = db.get(SeedLot, UUID(refs[f"seed:photo:{n}"]))
        assert seed is not None
        result = asyncio.run(
            set_local_identity_cover(
                db,
                storage,
                seed.botanical_identity_id,
                upload((v5.ASSETS / photo["file"]).read_bytes(), photo["file"], "image/jpeg"),
            )
        )
        asset = v4.media.update_asset(
            db,
            result.media_asset_id,
            AssetMetadataWrite(
                title=f"Media Review — {photo['species']} — explicit Identity cover upload",
                attribution=f"{photo['creator']}; {photo['source_url']}; {photo['changes']}",
                licence_label=photo["licence"],
                licence_url=photo["licence_url"],
            ),
        )
        ledger["assets"][f"cover:{n}"] = str(asset.id)
        cover = db.scalar(
            select(BotanicalIdentityCoverImage).where(
                BotanicalIdentityCoverImage.media_asset_id == asset.id
            )
        )
        assert cover is not None
        ledger["covers"].append(str(cover.id))
        if n == 0:
            link = v4.media.create_link(
                db,
                "seed_lot",
                seed.id,
                asset.id,
                LinkWrite(
                    caption=(
                        "Synthetic species illustration reuse; not evidence of the owned specimen."
                    ),
                    display_order=4,
                ),
            )
            ledger["links"].append(str(link.id))
    # Reuse one original Aloe asset on another actual same-identity synthetic SeedLot.
    seed = db.get(SeedLot, UUID(refs["seed:photo:0"]))
    assert seed is not None
    other = db.scalar(
        select(SeedLot)
        .where(SeedLot.botanical_identity_id == seed.botanical_identity_id, SeedLot.id != seed.id)
        .order_by(SeedLot.id)
    )
    assert other is not None
    link = v4.media.create_link(
        db,
        "seed_lot",
        other.id,
        UUID(refs["asset:local:0"]),
        LinkWrite(
            caption=(
                "Synthetic shared species illustration. "
                "This caption is specific to this second record."
            ),
            display_order=2,
        ),
    )
    ledger["links"].append(str(link.id))
    # Calibration drawings test pagination/framing and are never counted as botanical photos.
    for n in range(16):
        w, h = [(640, 480), (480, 640), (512, 512)][n % 3]
        image = Image.new("RGB", (w, h), (210 + n, 225 - n, 205 + n))
        draw = ImageDraw.Draw(image)
        draw.rectangle((8, 8, w - 9, h - 9), outline=(40, 70, 50), width=6)
        draw.line((0, 0, w, h), fill=(40, 70, 50), width=3)
        draw.text(
            (24, 30),
            f"SYNTHETIC LAYOUT {n + 1:02}\n{w} x {h}\nNot a botanical photograph",
            fill=(20, 40, 25),
        )
        data = io.BytesIO()
        image.save(data, format="PNG")
        asset = asyncio.run(
            v4.media.upload_asset(
                db,
                storage,
                upload(data.getvalue(), f"synthetic-layout-{n + 1:02}.png", "image/png"),
                AssetMetadataWrite(
                    title=f"Media Review — synthetic layout {n + 1:02}"
                    + (
                        " — deliberately long title for checking wrapping, "
                        "card geometry and accessible full labels"
                        if n == 0
                        else ""
                    ),
                    attribution=(
                        "Florabase generated calibration drawing; "
                        "no specimen, identification or biological provenance."
                    ),
                    licence_label="CC0-1.0",
                    licence_url="https://creativecommons.org/publicdomain/zero/1.0/",
                ),
            )
        )
        ledger["assets"][f"calibration:{n}"] = str(asset.id)
    ledger["state"] = "ready"
    temporary = root / (LEDGER + ".tmp")
    temporary.write_text(json.dumps(ledger, indent=2))
    temporary.replace(path)
    validate(db, root, ledger)
    return ledger


def main() -> None:
    action = sys.argv[1]
    with Session(v4.get_engine()) as db:
        root = v4.require_identity(v4.get_settings(), db, require_marker=False)
        with (root / ".review-fixture.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            marker = root / ".review-identity.json"
            if action == "seed":
                credentials = json.load(sys.stdin)
                users = list(db.scalars(select(User)))
                if not users:
                    v4.require_empty_review_collection(db)
                    bootstrap_owner(
                        db,
                        credentials["login"],
                        credentials["password"],
                        "Media Review (synthetic)",
                    )
                    db.commit()
                else:
                    assert len(users) == 1
                    assert users[0].login_name == credentials["login"]
                identity = {
                    "project": "florabase-media-review-1d44",
                    "source": os.environ["FLORABASE_REVIEW_SOURCE"],
                    "database": "florabase_media_review",
                    "origin": "http://localhost:15280",
                }
                if not marker.exists():
                    marker.write_text(json.dumps(identity))
                v4.require_identity(v4.get_settings(), db)
                baseline = v4.seed(db, root)
                extended = v5.seed(db, root, baseline)
                ledger = enhance(db, root, extended)
            else:
                v4.require_identity(v4.get_settings(), db)
                baseline = v4.read_manifest(root)
                assert baseline
                v4.validate_manifest(db, root, baseline)
                extended = json.loads((root / v5.LEDGER).read_text())
                v5.validate(db, root, extended, v5.inputs()[2])
                ledger = json.loads((root / LEDGER).read_text())
                validate(db, root, ledger)
                check_refusals(db)
            counts = {
                "media_assets": db.scalar(select(func.count()).select_from(v4.MediaAsset)),
                "record_links": db.scalar(select(func.count()).select_from(v4.RecordMediaLink)),
                "identity_covers": db.scalar(
                    select(func.count()).select_from(BotanicalIdentityCoverImage)
                ),
            }
            report = {
                "baseline_references": len(baseline["records"]),
                "v5_references": len(extended["records"]),
                "extension": ledger,
                "counts": counts,
            }
            if action == "check":
                report["assets"] = [
                    v4.media.asset_detail(db, asset.id).model_dump(mode="json")
                    for asset in db.scalars(select(v4.MediaAsset).order_by(v4.MediaAsset.id))
                ]
                report["foreign_runtime_refusals"] = 6
            print(json.dumps(report))


if __name__ == "__main__":
    main()
