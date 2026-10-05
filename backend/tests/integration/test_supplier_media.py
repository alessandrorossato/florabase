"""Supplier media is explicit, reusable and bounded; acquisitions never inherit imagery."""

import asyncio
from io import BytesIO
from pathlib import Path
from uuid import uuid7

import pytest
from fastapi import UploadFile
from PIL import Image
from sqlalchemy import Connection, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.datastructures import Headers

from florabase.attachments.storage import AttachmentStorage
from florabase.collection_photos.model import CollectionPrimaryPhoto, MediaAsset, RecordMediaLink
from florabase.collection_photos.primary import clear_primary, primary_summaries, set_primary
from florabase.collection_photos.schemas import PrimaryPhotoSelection
from florabase.collection_photos.service import list_photos
from florabase.media import service
from florabase.media.schemas import AssetMetadataWrite, LinkWrite, MediaTargetFilter
from florabase.suppliers.model import Supplier
from florabase.suppliers.service import get_supplier_detail, list_suppliers, set_supplier_retired

from .test_shared_media import external, fixture

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("kind", ["local", "external"])
def test_supplier_media_explicit_primary_retention_and_no_inheritance(
    database_connection: Connection, tmp_path: Path, kind: str
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        plant, _, _ = fixture(db)
        supplier = Supplier(name="Media nursery", kind="nursery")
        other = Supplier(name="Other supplier", kind="seller")
        db.add_all([supplier, other])
        db.flush()
        plant.direct_origin_kind = "purchased"
        plant.supplier_id = supplier.id
        db.flush()
        storage = AttachmentStorage(tmp_path)
        if kind == "local":
            stream = BytesIO()
            Image.new("RGB", (640, 320), "green").save(stream, "PNG")
            asset = asyncio.run(
                service.upload_asset(
                    db,
                    storage,
                    UploadFile(
                        filename="source.png",
                        file=BytesIO(stream.getvalue()),
                        headers=Headers({"content-type": "image/png"}),
                    ),
                    AssetMetadataWrite(),
                )
            )
        else:
            asset = external(db)
        asset_id, supplier_id, plant_id = asset.id, supplier.id, plant.id
        link = service.create_link(
            db, "supplier", supplier_id, asset_id, LinkWrite(caption="Source", display_order=3)
        )
        link_id = link.id
        assert list_photos(db, "plant", plant_id) == []
        assert primary_summaries(db, "plant", [plant_id]) == {}
        set_primary(
            db, storage, "supplier", supplier_id, PrimaryPhotoSelection(kind=kind, photo_id=link_id)
        )
        assert primary_summaries(db, "supplier", [supplier_id])[supplier_id].photo_id == link_id
        summary = next(row for row in list_suppliers(db) if row.id == supplier_id)
        assert summary.primary_photo is not None
        assert summary.primary_photo.photo_id == link_id
        assert bool(summary.primary_photo.thumbnail_url) == (kind == "local")
        assert get_supplier_detail(db, supplier).primary_photo == summary.primary_photo
        assert service.list_assets(db, target="collection").total == 0
        assert service.list_assets(db, target="supplier").total == 1
        plant_link = service.create_link(db, "plant", plant_id, asset_id, LinkWrite())
        set_primary(
            db, storage, "plant", plant_id, PrimaryPhotoSelection(kind=kind, photo_id=plant_link.id)
        )
        replacement = external(db)
        next_link = service.create_link(db, "supplier", supplier_id, replacement.id, LinkWrite())
        set_primary(
            db,
            storage,
            "supplier",
            supplier_id,
            PrimaryPhotoSelection(kind="external", photo_id=next_link.id),
        )
        assert primary_summaries(db, "plant", [plant_id])[plant_id].photo_id == plant_link.id
        assert (
            len(
                db.scalars(
                    select(CollectionPrimaryPhoto).where(
                        CollectionPrimaryPhoto.supplier_id == supplier_id
                    )
                ).all()
            )
            == 1
        )
        clear_primary(db, "supplier", supplier_id)
        assert not primary_summaries(db, "supplier", [supplier_id])
        set_primary(
            db, storage, "supplier", supplier_id, PrimaryPhotoSelection(kind=kind, photo_id=link_id)
        )
        detail = service.asset_detail(db, asset_id)
        supplier_link = next(row for row in detail.links if row.target_type == "supplier")
        assert supplier_link.target_label == "Media nursery"
        assert supplier_link.target_url == f"#/suppliers/{supplier_id}"
        assert supplier_link.is_primary
        assert service.list_assets(db, target="collection").total == 1
        with pytest.raises(service.MediaError, match="already links"):
            service.create_link(db, "supplier", supplier_id, asset_id, LinkWrite())
        with pytest.raises(service.MediaError) as missing:
            service.create_link(db, "supplier", uuid7(), asset_id, LinkWrite())
        assert missing.value.status == 404
        with pytest.raises(service.MediaError, match="does not belong"):
            set_primary(
                db,
                storage,
                "supplier",
                other.id,
                PrimaryPhotoSelection(kind=kind, photo_id=link_id),
            )
        with pytest.raises(service.MediaError, match="reference"):
            service.delete_asset(db, storage, asset_id)
        set_supplier_retired(db, supplier, retired=True)
        db.commit()
        assert primary_summaries(db, "supplier", [supplier_id])[supplier_id].photo_id == link_id
        assert service.unlink(db, link_id)
        assert not primary_summaries(db, "supplier", [supplier_id])
        assert primary_summaries(db, "plant", [plant_id])[plant_id].photo_id == plant_link.id
        assert db.get(MediaAsset, asset_id) is not None


def test_supplier_constraint_integrity(database_connection: Connection) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        plant, _, _ = fixture(db)
        a, b = Supplier(name="A", kind="seller"), Supplier(name="B", kind="seller")
        db.add_all([a, b])
        db.flush()
        asset = external(db)
        link = service.create_link(db, "supplier", a.id, asset.id, LinkWrite())
        for kwargs in (
            {"supplier_id": a.id, "plant_id": plant.id},
            {"supplier_id": uuid7()},
            {"supplier_id": a.id},
        ):
            with db.begin_nested() as savepoint:
                db.add(RecordMediaLink(media_asset_id=asset.id, source_kind="external", **kwargs))
                with pytest.raises(IntegrityError):
                    db.flush()
                savepoint.rollback()
        with db.begin_nested() as savepoint:
            link.supplier_id = b.id
            with pytest.raises(IntegrityError):
                db.flush()
            savepoint.rollback()
        with db.begin_nested() as savepoint:
            db.add(CollectionPrimaryPhoto(supplier_id=b.id, external_image_reference_id=link.id))
            with pytest.raises(IntegrityError):
                db.flush()
            savepoint.rollback()
        with db.begin_nested() as savepoint:
            db.delete(a)
            with pytest.raises(IntegrityError):
                db.flush()
            savepoint.rollback()


def test_supplier_filters_unique_paginated_composed_and_bounded(
    database_connection: Connection,
    tmp_path: Path,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        plant, second, _ = fixture(db)
        suppliers = [Supplier(name=f"Filter nursery {i}", kind="nursery") for i in range(30)]
        db.add_all(suppliers)
        db.flush()
        for i, supplier in enumerate(suppliers):
            asset = external(db)
            asset.title = f"Supplier filtering {i:02}"
            service.create_link(db, "supplier", supplier.id, asset.id, LinkWrite())
            if i % 2:
                service.create_link(db, "plant", plant.id, asset.id, LinkWrite())
                service.create_link(db, "plant", second.id, asset.id, LinkWrite())
            set_primary(
                db,
                AttachmentStorage(tmp_path),
                "supplier",
                supplier.id,
                PrimaryPhotoSelection(
                    kind="external",
                    photo_id=next(
                        row.id
                        for row in db.scalars(
                            select(RecordMediaLink).where(
                                RecordMediaLink.supplier_id == supplier.id
                            )
                        )
                    ),
                ),
            )
        # Mixed local/external primaries exercise the maximum four-query directory path.
        stream = BytesIO()
        Image.new("RGB", (640, 320), "green").save(stream, "PNG")
        local = asyncio.run(
            service.upload_asset(
                db,
                AttachmentStorage(tmp_path),
                UploadFile(
                    filename="local-primary.png",
                    file=BytesIO(stream.getvalue()),
                    headers=Headers({"content-type": "image/png"}),
                ),
                AssetMetadataWrite(title="Local representative"),
            )
        )
        local_link = service.create_link(db, "supplier", suppliers[0].id, local.id, LinkWrite())
        set_primary(
            db,
            AttachmentStorage(tmp_path),
            "supplier",
            suppliers[0].id,
            PrimaryPhotoSelection(kind="local", photo_id=local_link.id),
        )
        statements: list[str] = []

        def record(
            _conn: object,
            _cursor: object,
            statement: str,
            _params: object,
            _ctx: object,
            _many: bool,
        ) -> None:
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        event.listen(database_connection, "before_cursor_execute", record)
        try:
            presets: tuple[tuple[MediaTargetFilter | None, int], ...] = (
                (None, 30),
                ("supplier", 30),
                ("collection", 15),
                ("plant", 15),
                ("seed_lot", 0),
                ("sowing", 0),
                ("plant_group", 0),
                ("event", 0),
                ("harvest", 0),
            )
            for target, total in presets:
                statements.clear()
                first = service.list_assets(
                    db,
                    target=target,
                    query="Supplier filtering",
                    kind="external",
                    association="linked",
                    limit=7,
                )
                assert first.total == total
                assert len(first.items) == min(7, total)
                assert len({row.id for row in first.items}) == len(first.items)
                assert len(statements) == 2
                second_page = service.list_assets(
                    db, target=target, query="Supplier filtering", limit=7, offset=7
                )
                assert {row.id for row in first.items}.isdisjoint(
                    row.id for row in second_page.items
                )
                assert [row.id for row in first.items] == [
                    row.id
                    for row in service.list_assets(
                        db, target=target, query="Supplier filtering", limit=7
                    ).items
                ]
            assert service.list_assets(db, target="supplier", kind="local").total == 1
            assert service.list_assets(db, target="supplier", association="unlinked").total == 0
            statements.clear()
            summaries = list_suppliers(db)
            assert len(summaries) == 30
            assert (
                sum(
                    row.primary_photo is not None and row.primary_photo.kind == "local"
                    for row in summaries
                )
                == 1
            )
            assert (
                sum(
                    row.primary_photo is not None and row.primary_photo.kind == "external"
                    for row in summaries
                )
                == 29
            )
            assert len(statements) == 4  # supplier counts + designations + local + external assets
            statements.clear()
            choices = service.target_choices(db, "supplier", "Filter nursery", 7, 7)
            assert choices.total == 30
            assert len(choices.items) == 7
            assert len(statements) == 2
            assert all(row.label.startswith("Filter nursery") for row in choices.items)
            assert service.target_choices(db, "supplier", "%", 20, 0).total == 0
        finally:
            event.remove(database_connection, "before_cursor_execute", record)
