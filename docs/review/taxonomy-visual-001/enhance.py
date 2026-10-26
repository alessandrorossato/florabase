"""Additive, owned Review-only identities and attributed local cover photographs."""

# ruff: noqa: T201 -- Explicit fixture CLI output.
from __future__ import annotations

import asyncio
import io
import json
import os
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from runtime import LEDGER, build_source, read_ledger, validate_runtime
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.datastructures import Headers

from florabase.attachments.api import get_attachment_storage
from florabase.botanical_identities.schemas import BotanicalIdentityCreate
from florabase.botanical_identities.service import create_botanical_identity, find_duplicate
from florabase.collection_photos.model import BotanicalIdentityCoverImage, MediaAsset
from florabase.collection_photos.service import get_identity_cover, set_local_identity_cover
from florabase.core.config import get_settings
from florabase.db.session import get_engine
from florabase.seed_lots.model import SeedLot
from florabase.taxonomy.model import WfoLink
from florabase.taxonomy.schemas import TaxonomyLinkWrite
from florabase.taxonomy.service import confirm, tree


def main() -> None:
    validate_runtime(dict(os.environ))
    ledger = read_ledger()
    if ledger.get("tree_explorer"):
        print("Tree fixture retained; no identity, media or operator edit overwritten.")
        return
    source = build_source()
    with Session(get_engine()) as db:
        assert db.scalar(text("SELECT current_database()")) == "florabase_review"
        added = []
        for cultivar, lifecycle in [(None, "active"), ("Thai", "exhausted")]:
            existing = find_duplicate(db, "Ocimum basilicum", cultivar)
            if existing is not None:
                assert existing.common_name == "Basil · synthetic Tree Review", (
                    "Existing non-fixture identity; refusing modification"
                )
                saved = db.get(WfoLink, existing.id)
                assert saved is not None
                assert saved.external_id == "wfo-9000000008"
            identity = existing or create_botanical_identity(
                db,
                BotanicalIdentityCreate(
                    scientific_name="Ocimum basilicum",
                    cultivar_name=cultivar,
                    common_name="Basil · synthetic Tree Review",
                ),
            )
            if existing is None:
                db.add(
                    SeedLot(
                        botanical_identity_id=identity.id,
                        lifecycle=lifecycle,
                        label="Synthetic Tree Explorer fixture",
                    )
                )
            db.flush()
            if existing is None:
                confirm(
                    db,
                    identity.id,
                    TaxonomyLinkWrite(
                        source_taxon_id="wfo-9000000008",
                        checksum=source.metadata().checksum,
                        expected_version=None,
                        identity_updated_at=identity.updated_at,
                    ),
                    source,
                )
            ledger["identities"]["Tree Basil " + (cultivar or "species")] = str(identity.id)
            added.append(identity)
        for name, lifecycle in [("Mentha spicata", "active"), ("Melissa officinalis", "exhausted")]:
            ident = find_duplicate(db, name, None)
            if ident is None:
                ident = create_botanical_identity(
                    db,
                    BotanicalIdentityCreate(
                        scientific_name=name, common_name="Unlinked · synthetic Tree Review"
                    ),
                )
                db.add(
                    SeedLot(
                        botanical_identity_id=ident.id,
                        lifecycle=lifecycle,
                        label="Synthetic unresolved Tree fixture",
                    )
                )
            else:
                assert ident.common_name == "Unlinked · synthetic Tree Review", (
                    "Non-fixture identity; refusing modification"
                )
            ledger["identities"]["Tree unresolved " + name] = str(ident.id)
        db.commit()
        LEDGER.write_text(json.dumps(ledger))
        storage = get_attachment_storage(get_settings())
        photo_credits = [
            (
                "Ocimum basilicum",
                "basil.jpg",
                "Garitzko / Wikimedia Commons · synthetic Review representative",
                "Public domain",
                "https://creativecommons.org/publicdomain/mark/1.0/",
                "https://commons.wikimedia.org/wiki/File:Genoveser_Basilikum.jpg",
            ),
            (
                "Aloe vera",
                "aloe.jpg",
                "Divya Chinnasamy / Wikimedia Commons · synthetic Review representative",
                "CC0 1.0",
                "https://creativecommons.org/publicdomain/zero/1.0/",
                "https://commons.wikimedia.org/wiki/File:ALOE_VERA.jpg",
            ),
        ]
        for name, filename, author, licence, licence_url, source_url in photo_credits:
            identity_id = UUID(ledger["identities"][name])
            existing_cover = get_identity_cover(db, identity_id)
            if existing_cover is not None:
                existing_asset = db.get(MediaAsset, existing_cover[0].media_asset_id)
                if existing_asset is not None and existing_asset.title == filename:
                    existing_asset.attribution = author + " · " + source_url
                    existing_asset.licence_label, existing_asset.licence_url = licence, licence_url
                    existing_asset.title = "Synthetic Review representative photograph: " + name
                    db.commit()
                continue
            data = Path(__file__).with_name("media").joinpath(filename).read_bytes()
            result = asyncio.run(
                set_local_identity_cover(
                    db,
                    storage,
                    identity_id,
                    UploadFile(
                        filename=filename,
                        file=io.BytesIO(data),
                        headers=Headers({"content-type": "image/jpeg"}),
                    ),
                )
            )
            asset = db.get(MediaAsset, result.media_asset_id)
            assert asset is not None
            asset.attribution, asset.licence_label, asset.licence_url = (
                author + " · " + source_url,
                licence,
                licence_url,
            )
            asset.title = "Synthetic Review representative photograph: " + name
            db.commit()
        representative = get_identity_cover(db, UUID(ledger["identities"]["Ocimum basilicum"]))
        assert representative is not None
        cover = representative[0]
        if get_identity_cover(db, added[0].id) is None:
            db.add(
                BotanicalIdentityCoverImage(
                    botanical_identity_id=added[0].id,
                    source_mode=cover.source_mode,
                    media_asset_id=cover.media_asset_id,
                )
            )
        db.commit()
        result = tree(db, source, include_covers=True)
        assert result.counts.model_dump() == {
            "represented": 12,
            "living": 5,
            "current": 9,
            "historical": 3,
        }
        projected = {str(identity.id): identity for identity in result.identities}
        for name in ("Mentha spicata", "Melissa officinalis"):
            assert (
                projected[ledger["identities"]["Tree unresolved " + name]].source_taxon_id is None
            )
        assert sum(i.cover is not None for i in result.identities) >= 3
        ledger["tree_explorer"] = {"version": 1, "identities": [str(i.id) for i in added]}
        LEDGER.write_text(json.dumps(ledger))
        print(
            "Additive Tree fixture ready: 12 identities, 3 Basil identities, "
            "3 covers sharing 2 attributed assets; original source links preserved."
        )


if __name__ == "__main__":
    main()
