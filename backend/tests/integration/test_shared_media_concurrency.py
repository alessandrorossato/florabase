import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Literal
from uuid import uuid7

import pytest
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from florabase.attachments.storage import AttachmentStorage
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.collection_photos.model import RecordMediaLink
from florabase.media import service
from florabase.media.schemas import ExternalAssetCreate, LinkWrite
from florabase.plants.model import Plant
from florabase.suppliers.model import Supplier

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("target", ["plant", "supplier"])
@pytest.mark.parametrize("race", ["delete_then_link", "link_then_delete", "duplicate_link"])
def test_asset_reference_races_serialize_and_fail_closed(
    database_engine: Engine,
    tmp_path: Path,
    race: str,
    target: Literal["plant", "supplier"],
) -> None:
    with Session(database_engine) as database:
        identity = BotanicalIdentity(scientific_name=f"Media race {uuid7()}")
        database.add(identity)
        database.flush()
        plant = (
            Plant(botanical_identity_id=identity.id, direct_origin_kind="unknown")
            if target == "plant"
            else Supplier(name="Race supplier", kind="seller")
        )
        database.add(plant)
        database.flush()
        asset = service.create_external_asset(
            database,
            ExternalAssetCreate(
                image_url="https://images.example.test/race.jpg",
                source_url="https://example.test/source",
                attribution="Author",
            ),
        )
        identity_id, plant_id, asset_id = identity.id, plant.id, asset.id
    holder = Session(database_engine)
    worker_pid: dict[str, int] = {}
    started = threading.Event()
    try:
        if race == "delete_then_link":
            locked = service.require_asset(holder, asset_id, lock=True)
            locked.state = "pending_delete"
            holder.flush()
        else:
            service.create_link(holder, target, plant_id, asset_id, LinkWrite(), commit=False)
        with ThreadPoolExecutor(max_workers=1) as executor:

            def work() -> str:
                with Session(database_engine) as database:
                    pid = database.scalar(text("SELECT pg_backend_pid()"))
                    assert pid is not None
                    worker_pid["pid"] = pid
                    started.set()
                    try:
                        if race == "link_then_delete":
                            service.delete_asset(database, AttachmentStorage(tmp_path), asset_id)
                        else:
                            service.create_link(database, target, plant_id, asset_id, LinkWrite())
                    except service.MediaError as error:
                        return error.code
                    return "unexpected_success"

            future = executor.submit(work)
            try:
                assert started.wait(timeout=5)
                deadline = time.monotonic() + 5
                waiting = False
                while time.monotonic() < deadline and not future.done():
                    with database_engine.connect() as observer:
                        waiting = (
                            observer.scalar(
                                text(
                                    "SELECT wait_event_type FROM pg_stat_activity WHERE pid = :pid"
                                ),
                                {"pid": worker_pid["pid"]},
                            )
                            == "Lock"
                        )
                    if waiting:
                        break
                assert waiting, "conflicting request did not wait for the held transaction"
            finally:
                holder.commit()
            code = future.result(timeout=5)
            assert (
                code
                == {
                    "delete_then_link": "media_deletion_pending",
                    "link_then_delete": "media_asset_referenced",
                    "duplicate_link": "duplicate_media_link",
                }[race]
            )
        with Session(database_engine) as database:
            links = database.scalars(
                select(RecordMediaLink).where(RecordMediaLink.media_asset_id == asset_id)
            ).all()
            assert len(links) == (0 if race == "delete_then_link" else 1)
    finally:
        holder.rollback()
        holder.close()
        with database_engine.begin() as connection:
            connection.execute(
                text("DELETE FROM record_media_links WHERE media_asset_id = :id"), {"id": asset_id}
            )
            connection.execute(text("DELETE FROM media_assets WHERE id = :id"), {"id": asset_id})
            connection.execute(
                text(
                    f"DELETE FROM {'plants' if target == 'plant' else 'suppliers'} WHERE id = :id"
                ),
                {"id": plant_id},
            )
            connection.execute(
                text("DELETE FROM botanical_identities WHERE id = :id"), {"id": identity_id}
            )
