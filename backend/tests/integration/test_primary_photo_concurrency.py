import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid7

import pytest
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from florabase.attachments.storage import AttachmentStorage
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.collection_photos.model import (
    CollectionPrimaryPhoto,
    ExternalImageReference,
    MediaAsset,
)
from florabase.collection_photos.primary import clear_photo_primary, set_primary
from florabase.collection_photos.schemas import PrimaryPhotoResponse, PrimaryPhotoSelection
from florabase.plants.model import Plant
from florabase.provenance_sites.model import ProvenanceSite  # noqa: F401

pytestmark = pytest.mark.integration


def test_replacement_waits_for_concurrent_primary_photo_deletion(
    database_engine: Engine, tmp_path: Path
) -> None:
    storage = AttachmentStorage(tmp_path)
    with Session(database_engine) as database:
        identity = BotanicalIdentity(scientific_name=f"Primary race {uuid7()}")
        database.add(identity)
        database.flush()
        plant = Plant(botanical_identity_id=identity.id, direct_origin_kind="unknown")
        database.add(plant)
        database.flush()
        old_reference = ExternalImageReference(
            plant_id=plant.id,
            image_url="https://images.example.test/old.jpg",
            source_url="https://example.test/old",
            attribution="Old photo",
        )
        next_reference = ExternalImageReference(
            plant_id=plant.id,
            image_url="https://images.example.test/new.jpg",
            source_url="https://example.test/new",
            attribution="New photo",
        )
        database.add_all([old_reference, next_reference])
        database.flush()
        database.add(
            CollectionPrimaryPhoto(plant_id=plant.id, external_image_reference_id=old_reference.id)
        )
        database.commit()
        identity_id = identity.id
        plant_id = plant.id
        old_reference_id = old_reference.id
        next_reference_id = next_reference.id
        asset_ids = [old_reference.media_asset_id, next_reference.media_asset_id]

    # Hold the same source and designation locks as external-photo deletion through
    # its atomic clear/delete/commit sequence.
    deletion = Session(database_engine)
    try:
        locked_reference = deletion.scalar(
            select(ExternalImageReference)
            .where(ExternalImageReference.id == old_reference_id)
            .with_for_update(of=ExternalImageReference)
        )
        assert locked_reference is not None
        clear_photo_primary(deletion, "external", old_reference_id)
        deletion.delete(locked_reference)
        deletion.flush()

        started = threading.Event()
        worker_pid: dict[str, int] = {}
        with ThreadPoolExecutor(max_workers=1) as executor:

            def replace() -> tuple[PrimaryPhotoResponse, int]:
                with Session(database_engine) as database:
                    backend_pid = database.scalar(text("SELECT pg_backend_pid()"))
                    assert backend_pid is not None
                    worker_pid["pid"] = backend_pid
                    started.set()
                    result = set_primary(
                        database,
                        storage,
                        "plant",
                        plant_id,
                        PrimaryPhotoSelection(kind="external", photo_id=next_reference_id),
                    )
                    return result, backend_pid

            future = executor.submit(replace)
            assert started.wait(timeout=5), "replacement request did not start"
            deadline = time.monotonic() + 5
            waiting_for_lock = False
            while time.monotonic() < deadline and not future.done():
                with database_engine.connect() as observer:
                    wait_event = observer.scalar(
                        text("SELECT wait_event_type FROM pg_stat_activity WHERE pid = :pid"),
                        {"pid": worker_pid["pid"]},
                    )
                if wait_event == "Lock":
                    waiting_for_lock = True
                    break
            assert waiting_for_lock, "replacement did not wait for the designation deletion"
            deletion.commit()
            result, _pid = future.result(timeout=5)
            assert result.photo_id == next_reference_id
    finally:
        deletion.rollback()
        deletion.close()

    with Session(database_engine) as database:
        designation = database.scalar(
            select(CollectionPrimaryPhoto).where(CollectionPrimaryPhoto.plant_id == plant_id)
        )
        assert designation is not None
        assert designation.external_image_reference_id == next_reference_id
        assert database.get(ExternalImageReference, old_reference_id) is None
        database.delete(designation)
        remaining_reference = database.get(ExternalImageReference, next_reference_id)
        remaining_plant = database.get(Plant, plant_id)
        remaining_identity = database.get(BotanicalIdentity, identity_id)
        assert remaining_reference is not None
        assert remaining_plant is not None
        assert remaining_identity is not None
        database.delete(remaining_reference)
        database.flush()
        database.delete(remaining_plant)
        database.flush()
        database.delete(remaining_identity)
        for asset_id in asset_ids:
            asset = database.get(MediaAsset, asset_id)
            assert asset is not None
            database.delete(asset)
        database.commit()
