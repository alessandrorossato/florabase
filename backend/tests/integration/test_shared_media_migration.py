"""Upgrade real legacy rows; shared metadata requires paired-backup rollback."""

import hashlib
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import uuid7

import pytest
from alembic.config import Config
from PIL import Image
from sqlalchemy import Engine, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from alembic import command
from florabase.attachments.model import Attachment
from florabase.attachments.storage import AttachmentStorage
from florabase.collection_photos.model import MediaAsset
from florabase.media.service import asset_thumbnail

pytestmark = pytest.mark.integration


def test_upgrade_preserves_originals_links_primary_covers_and_standalone(
    database_engine: Engine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import http.client
    import urllib.request
    from unittest.mock import MagicMock

    network = MagicMock(
        side_effect=AssertionError("migration must never resolve or fetch external images")
    )
    monkeypatch.setattr(http.client.HTTPConnection, "request", network)
    monkeypatch.setattr(urllib.request, "urlopen", network)
    config = Config("alembic.ini")
    command.downgrade(config, "20260925_0026")
    ids = {
        key: uuid7()
        for key in (
            "identity",
            "other_identity",
            "plant",
            "empty_plant",
            "file",
            "cover_file",
            "standalone",
            "local",
            "external",
            "cover",
            "external_cover",
            "primary",
        )
    }
    now = datetime(2026, 9, 1, tzinfo=UTC)
    storage = AttachmentStorage(tmp_path)
    content = BytesIO()
    Image.new("RGB", (640, 320), "green").save(content, "PNG")
    binary = content.getvalue()
    file_keys = {}
    try:
        with database_engine.begin() as connection:
            for key in ("identity", "other_identity"):
                connection.execute(
                    text(
                        "INSERT INTO botanical_identities (id, scientific_name, "
                        "created_at, updated_at) "
                        "VALUES (:id, :name, :now, :now)"
                    ),
                    {"id": ids[key], "name": key, "now": now},
                )
            for key in ("plant", "empty_plant"):
                connection.execute(
                    text(
                        "INSERT INTO plants (id, botanical_identity_id, "
                        "direct_origin_kind, lifecycle, "
                        "created_at, updated_at) VALUES (:id, :identity, 'unknown', "
                        "'active', :now, :now)"
                    ),
                    {"id": ids[key], "identity": ids["identity"], "now": now},
                )
            for key in ("file", "cover_file", "standalone"):
                file_keys[key] = f"objects/{ids[key].hex[:2]}/{ids[key].hex}"
                path = storage.objects / ids[key].hex[:2] / ids[key].hex
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(binary)
                connection.execute(
                    text(
                        "INSERT INTO attachments (id, storage_key, original_filename, media_type, "
                        "byte_size, sha256, state, created_at) "
                        "VALUES (:id, :key, 'leaf.png', 'image/png', :size, :sha, "
                        "'active', :now)"
                    ),
                    {
                        "id": ids[key],
                        "key": file_keys[key],
                        "size": len(binary),
                        "sha": hashlib.sha256(binary).hexdigest(),
                        "now": now,
                    },
                )
            connection.execute(
                text(
                    "INSERT INTO local_collection_photos (id, attachment_id, plant_id, caption, "
                    "attribution, created_at, updated_at) VALUES (:id, :file, :plant, "
                    "'Local context', 'Local credit', :now, :now)"
                ),
                {"id": ids["local"], "file": ids["file"], "plant": ids["plant"], "now": now},
            )
            connection.execute(
                text(
                    "INSERT INTO external_image_references (id, plant_id, image_url, source_url, "
                    "caption, attribution, created_at, updated_at) "
                    "VALUES (:id, :plant, 'https://images.example.test/leaf.jpg', "
                    "'https://example.test/source', 'External context', 'Author', "
                    ":now + interval '1 day', :now + "
                    "interval '1 day')"
                ),
                {"id": ids["external"], "plant": ids["plant"], "now": now},
            )
            connection.execute(
                text(
                    "INSERT INTO botanical_identity_cover_images (id, botanical_identity_id, "
                    "source_mode, attachment_id, created_at, updated_at) "
                    "VALUES (:id, :identity, 'local', :file, :now, :now)"
                ),
                {
                    "id": ids["cover"],
                    "identity": ids["identity"],
                    "file": ids["cover_file"],
                    "now": now,
                },
            )
            connection.execute(
                text(
                    "INSERT INTO botanical_identity_cover_images (id, botanical_identity_id, "
                    "source_mode, image_url, source_url, attribution, licence_label, "
                    "licence_url, created_at, updated_at) "
                    "VALUES (:id, :identity, 'external', 'https://images.example.test/cover.jpg', "
                    "'https://example.test/source', 'Cover credit', 'CC0', "
                    "'https://example.test/licence', :now, :now)"
                ),
                {"id": ids["external_cover"], "identity": ids["other_identity"], "now": now},
            )
            connection.execute(
                text(
                    "INSERT INTO collection_primary_photos (id, plant_id, "
                    "local_collection_photo_id, "
                    "created_at, updated_at) VALUES (:id, :plant, :photo, :now, :now)"
                ),
                {"id": ids["primary"], "plant": ids["plant"], "photo": ids["local"], "now": now},
            )
            original_files = (
                connection.execute(text("SELECT * FROM attachments ORDER BY id")).mappings().all()
            )
            original_primary = (
                connection.execute(text("SELECT * FROM collection_primary_photos")).mappings().one()
            )
        command.upgrade(config, "head")
        with database_engine.connect() as connection:
            assert (
                connection.execute(text("SELECT * FROM attachments ORDER BY id")).mappings().all()
                == original_files
            )
            assert connection.execute(
                text("SELECT * FROM collection_primary_photos")
            ).mappings().one() == {**original_primary, "harvest_id": None, "supplier_id": None}
            links = (
                connection.execute(
                    text(
                        "SELECT * FROM record_media_links WHERE plant_id = :id ORDER BY "
                        "display_order"
                    ),
                    {"id": ids["plant"]},
                )
                .mappings()
                .all()
            )
            assert [row["id"] for row in links] == [ids["local"], ids["external"]]
            assert [row["caption"] for row in links] == ["Local context", "External context"]
            assert [row["display_order"] for row in links] == [0, 1]
            assert links[0]["media_asset_id"] == ids["file"]
            external = (
                connection.execute(
                    text("SELECT * FROM media_assets WHERE id = :id"), {"id": ids["external"]}
                )
                .mappings()
                .one()
            )
            assert external["attachment_id"] is None
            assert external["fetched_at"] is None
            assert external["copy_cleanup_attachment_id"] is None
            network.assert_not_called()
            assert external["attribution"] == "Author"
            assert external["image_url"] == "https://images.example.test/leaf.jpg"
            assert external["licence_label"] is None
            assert external["licence_url"] is None
            assert external["updated_at"] == links[1]["updated_at"]
            assert (
                connection.scalar(
                    text("SELECT attribution FROM media_assets WHERE id = :id"), {"id": ids["file"]}
                )
                == "Local credit"
            )
            covers = (
                connection.execute(text("SELECT * FROM botanical_identity_cover_images"))
                .mappings()
                .all()
            )
            assert {(row["id"], row["media_asset_id"], row["source_mode"]) for row in covers} == {
                (ids["cover"], ids["cover_file"], "local"),
                (ids["external_cover"], ids["external_cover"], "external"),
            }
            assert (
                connection.scalar(
                    text("SELECT count(*) FROM record_media_links WHERE plant_id = :id"),
                    {"id": ids["empty_plant"]},
                )
                == 0
            )
            assert connection.scalar(text("SELECT count(*) FROM media_assets")) == 5
            assert connection.scalar(text("SELECT count(*) FROM record_media_links")) == 2
        with Session(database_engine) as database:
            asset = database.get(MediaAsset, ids["file"])
            attachment = database.get(Attachment, ids["file"])
            assert asset is not None
            assert attachment is not None
            assert (
                storage.active_path(attachment.storage_key, attachment.byte_size).read_bytes()
                == binary
            )
            with Image.open(BytesIO(asset_thumbnail(storage, asset, attachment))) as image:
                assert image.size == (320, 160)
        with pytest.raises(ProgrammingError, match="paired pre-upgrade backup"):
            command.downgrade(config, "20260925_0026")
    finally:
        # Delete only named fixtures, in dependency order, then test the empty downgrade cycle.
        with database_engine.begin() as connection:
            for table in (
                "collection_primary_photos",
                "botanical_identity_cover_images",
                "record_media_links",
                "media_assets",
                "attachments",
                "plants",
                "botanical_identities",
            ):
                connection.execute(
                    text(f"DELETE FROM {table} WHERE id = ANY(:ids)"), {"ids": list(ids.values())}
                )
        command.downgrade(config, "20260925_0026")
        command.upgrade(config, "head")
