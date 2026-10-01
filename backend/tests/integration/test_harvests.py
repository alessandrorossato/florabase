"""Real PostgreSQL aggregate, retention, media, ownership and no-state-mutation proofs."""

from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import Connection, delete, event, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from florabase.attachments.storage import AttachmentStorage
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.collection_photos.model import CollectionPrimaryPhoto, MediaAsset, RecordMediaLink
from florabase.collection_photos.primary import primary_summaries, set_primary
from florabase.collection_photos.schemas import PrimaryPhotoSelection
from florabase.events.model import Event
from florabase.events.schemas import EventCreate, EventUpdate
from florabase.events.service import (
    EventDomainConflictError,
    create_event,
    delete_event,
    event_responses,
    list_all_events,
    update_event,
)
from florabase.harvests.model import Harvest, HarvestItem
from florabase.harvests.schemas import HarvestWrite
from florabase.harvests.service import delete_harvest, list_harvests, read_harvest, write_harvest
from florabase.locations.model import Location
from florabase.main import app  # noqa: F401
from florabase.media import service as media
from florabase.media.schemas import ExternalAssetCreate, LinkWrite
from florabase.plants.model import Plant, PlantGroup
from florabase.seed_lots.model import SeedLot

from .test_attachment_api import authenticated_browser as browser_fixture
from .test_attachment_api import request

harvest_browser = browser_fixture
pytestmark = pytest.mark.integration


def fixtures(db: Session) -> tuple[Plant, PlantGroup, BotanicalIdentity]:
    identity = BotanicalIdentity(scientific_name="Harvest test species", common_name="Okra")
    location = Location(name="Harvest bench")
    db.add_all([identity, location])
    db.flush()
    plant = Plant(
        botanical_identity_id=identity.id,
        direct_origin_kind="unknown",
        lifecycle="dead",
        location_id=location.id,
    )
    group = PlantGroup(
        botanical_identity_id=identity.id,
        direct_origin_kind="unknown",
        lifecycle="active",
        quantity_value=12,
        quantity_is_approximate=True,
        location_id=location.id,
    )
    db.add_all([plant, group])
    db.flush()
    return plant, group, identity


def data(source: Plant | PlantGroup, **values: object) -> HarvestWrite:
    return HarvestWrite.model_validate(
        {
            "plant_id" if isinstance(source, Plant) else "plant_group_id": source.id,
            "items": [{"material_kind": "fruit"}],
            **values,
        }
    )


def enforce(db: Session) -> None:
    db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    db.execute(text("SET CONSTRAINTS ALL DEFERRED"))


@pytest.mark.parametrize("group", [False, True])
def test_create_correct_delete_no_source_or_inventory_mutation(
    database_connection: Connection, group: bool
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        plant, plant_group, identity = fixtures(db)
        source = plant_group if group else plant
        source_values = (
            source.lifecycle,
            source.location_id,
            plant_group.quantity_value,
            plant_group.quantity_is_approximate,
        )
        seed_ids = list(db.scalars(select(SeedLot.id)))
        old_event = create_event(
            db, "plant", plant.id, EventCreate(kind="harvest", notes="Historical free-form")
        )
        harvest = write_harvest(
            db,
            data(
                source,
                occurred_on={"precision": "month", "year": 2026, "month": 8},
                items=[
                    {
                        "material_kind": "fruit",
                        "quantity": {"kind": "item_count", "value": "18", "is_approximate": False},
                    },
                    {
                        "material_kind": "seed",
                        "quantity": {
                            "kind": "weight",
                            "value": "42",
                            "unit": "g",
                            "is_approximate": True,
                        },
                    },
                ],
            ),
        )
        enforce(db)
        result = read_harvest(db, harvest.id)
        assert len(result.items) == 2
        assert result.items[1].quantity is not None
        assert result.items[1].quantity.is_approximate
        owned = db.get(Event, harvest.event_id)
        assert owned is not None
        assert owned.kind == "harvest"
        assert owned.plant_id == harvest.plant_id
        assert owned.plant_group_id == harvest.plant_group_id
        assert owned.occurred_on_month == 8
        for action in (
            lambda: update_event(db, owned, EventUpdate(kind="harvest")),
            lambda: delete_event(db, owned),
        ):
            with pytest.raises(EventDomainConflictError):
                action()
        # Corrections can switch source types and retain the line UUID.
        replacement = plant if group else plant_group
        write_harvest(
            db,
            data(
                replacement,
                occurred_on={"precision": "year", "year": 2025},
                notes="Correction",
                items=[
                    {"id": result.items[0].id, "material_kind": "whole_plant"},
                    {"material_kind": "root"},
                ],
            ),
            harvest.id,
        )
        enforce(db)
        db.refresh(owned)
        assert owned.plant_id == harvest.plant_id
        assert owned.plant_group_id == harvest.plant_group_id
        assert owned.occurred_on_month is None
        assert owned.notes == "Correction"
        assert (
            list_harvests(db, botanical_identity_id=identity.id)[0].items[0].id
            == result.items[0].id
        )
        assert list_harvests(db, query="okra", material_kind="whole_plant")
        assert not list_harvests(db, query="missing")
        summaries = event_responses(db, list_all_events(db))
        assert next(item for item in summaries if item.id == owned.id).harvest_id == harvest.id
        assert next(item for item in summaries if item.id == old_event.id).harvest_id is None
        harvest_id, event_id = harvest.id, owned.id
        delete_harvest(db, harvest_id)
        enforce(db)
        assert db.get(Harvest, harvest_id) is None
        assert db.get(Event, event_id) is None
        retained_event = db.get(Event, old_event.id)
        assert retained_event is not None
        assert retained_event.notes == "Historical free-form"
        db.refresh(source)
        db.refresh(plant_group)
        assert (
            source.lifecycle,
            source.location_id,
            plant_group.quantity_value,
            plant_group.quantity_is_approximate,
        ) == source_values
        assert list(db.scalars(select(SeedLot.id))) == seed_ids


@pytest.mark.parametrize(
    "corruption",
    [
        "zero_items",
        "xor",
        "kind",
        "target",
        "date",
        "notes",
        "quantity",
        "material",
        "source_delete",
    ],
)
def test_relational_guards_and_rollback(database_connection: Connection, corruption: str) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        plant, group, _ = fixtures(db)
        harvest = write_harvest(db, data(plant))
        enforce(db)
        with pytest.raises(IntegrityError), db.begin_nested():  # noqa: PT012 - atomic savepoint proof
            if corruption == "zero_items":
                db.execute(delete(HarvestItem).where(HarvestItem.harvest_id == harvest.id))
            elif corruption == "xor":
                db.execute(
                    text("UPDATE harvests SET plant_group_id = :id WHERE id = :harvest"),
                    {"id": group.id, "harvest": harvest.id},
                )
            elif corruption == "kind":
                db.execute(
                    text("UPDATE events SET kind = 'flowering' WHERE id = :id"),
                    {"id": harvest.event_id},
                )
            elif corruption == "target":
                db.execute(
                    text(
                        "UPDATE events SET plant_id = NULL, plant_group_id = :group WHERE id = :id"
                    ),
                    {"group": group.id, "id": harvest.event_id},
                )
            elif corruption == "date":
                db.execute(
                    text(
                        "UPDATE events SET occurred_on_precision = 'year', "
                        "occurred_on_year = 2024 WHERE id = :id"
                    ),
                    {"id": harvest.event_id},
                )
            elif corruption == "notes":
                db.execute(
                    text("UPDATE events SET notes = 'Diverged' WHERE id = :id"),
                    {"id": harvest.event_id},
                )
            elif corruption == "quantity":
                db.execute(
                    text(
                        "UPDATE harvest_items SET quantity_kind = 'weight', "
                        "quantity_value = -1 WHERE harvest_id = :id"
                    ),
                    {"id": harvest.id},
                )
            elif corruption == "material":
                db.execute(
                    text(
                        "UPDATE harvest_items SET material_kind = 'fabricated' "
                        "WHERE harvest_id = :id"
                    ),
                    {"id": harvest.id},
                )
            else:
                db.execute(delete(Plant).where(Plant.id == plant.id))
            enforce(db)
        assert len(read_harvest(db, harvest.id).items) == 1
        retained = db.get(Event, harvest.event_id)
        assert retained is not None
        assert retained.kind == "harvest"


def test_empty_create_is_rejected_at_transaction_boundary(database_connection: Connection) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        plant, _, _ = fixtures(db)
        with pytest.raises(IntegrityError), db.begin_nested():  # noqa: PT012 - atomic savepoint proof
            journal = create_event(db, "plant", plant.id, EventCreate(kind="harvest"))
            db.add(Harvest(plant_id=plant.id, event_id=journal.id))
            db.flush()
            enforce(db)
        assert not list_harvests(db)
        with pytest.raises(ValidationError):
            data(
                plant,
                items=[
                    {"material_kind": "fruit"},
                    {
                        "material_kind": "leaf",
                        "quantity": {
                            "kind": "weight",
                            "value": "-4",
                            "unit": "g",
                            "is_approximate": False,
                        },
                    },
                ],
            )
        assert not list_harvests(db)


def test_media_reuse_primary_unlink_delete_retention_and_bounded_queries(
    database_connection: Connection, tmp_path: Path
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        plant, group, _ = fixtures(db)
        harvest = write_harvest(db, data(plant))
        db.commit()
        asset = media.create_external_asset(
            db,
            ExternalAssetCreate(
                image_url="https://images.example.test/fruit.jpg",
                source_url="https://example.test",
                attribution="Gardener",
            ),
        )
        plant_link = media.create_link(db, "plant", plant.id, asset.id, LinkWrite())
        with pytest.raises(IntegrityError), db.begin_nested():  # noqa: PT012 - relational membership
            db.add(
                CollectionPrimaryPhoto(
                    harvest_id=harvest.id, external_image_reference_id=plant_link.id
                )
            )
            db.flush()
        link = media.create_link(
            db, "harvest", harvest.id, asset.id, LinkWrite(caption="Fruit", display_order=1)
        )
        storage = AttachmentStorage(tmp_path)
        set_primary(
            db,
            storage,
            "harvest",
            harvest.id,
            PrimaryPhotoSelection(kind="external", photo_id=link.id),
        )
        set_primary(
            db,
            storage,
            "plant",
            plant.id,
            PrimaryPhotoSelection(kind="external", photo_id=plant_link.id),
        )
        assert primary_summaries(db, "harvest", [harvest.id])[harvest.id].photo_id == link.id
        assert len(media.asset_detail(db, asset.id).links) == 2
        assert media.target_choices(db, "harvest", "Okra", 20, 0).total == 1
        assert media.asset_detail(db, asset.id).links[-1].target_label.endswith("Fruit harvest")
        with pytest.raises(media.MediaError):
            media.create_link(db, "harvest", harvest.id, asset.id, LinkWrite())
        assert media.unlink(db, link.id)
        assert primary_summaries(db, "harvest", [harvest.id]) == {}
        assert db.get(MediaAsset, asset.id) is not None
        assert primary_summaries(db, "plant", [plant.id])
        link = media.create_link(db, "harvest", harvest.id, asset.id, LinkWrite())
        set_primary(
            db,
            storage,
            "harvest",
            harvest.id,
            PrimaryPhotoSelection(kind="external", photo_id=link.id),
        )
        for _ in range(15):
            write_harvest(
                db, data(group, items=[{"material_kind": "leaf"}, {"material_kind": "flower"}])
            )
        enforce(db)
        statements: list[str] = []

        def capture(_conn: object, _cursor: object, statement: str, *_args: object) -> None:
            statements.append(statement)

        event.listen(database_connection, "before_cursor_execute", capture)
        try:
            rows = list_harvests(db)
        finally:
            event.remove(database_connection, "before_cursor_execute", capture)
        assert len(rows) == 16
        assert len(statements) <= 8
        delete_harvest(db, harvest.id)
        db.commit()
        assert db.get(MediaAsset, asset.id) is not None
        assert db.get(RecordMediaLink, plant_link.id) is not None
        assert not list(
            db.scalars(
                select(CollectionPrimaryPhoto).where(
                    CollectionPrimaryPhoto.harvest_id == harvest.id
                )
            )
        )


def test_invalid_later_item_rolls_back_complete_create_and_correction(
    database_connection: Connection,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        plant, group, _ = fixtures(db)
        before_events = set(db.scalars(select(Event.id)))
        with pytest.raises(IntegrityError), db.begin_nested():  # noqa: PT012 - aggregate rollback
            created = write_harvest(
                db, data(plant, items=[{"material_kind": "fruit"}, {"material_kind": "seed"}])
            )
            db.execute(
                text(
                    "UPDATE harvest_items SET material_kind = 'invalid' "
                    "WHERE harvest_id = :id AND display_order = 1"
                ),
                {"id": created.id},
            )
        assert not list_harvests(db)
        assert set(db.scalars(select(Event.id))) == before_events
        retained = write_harvest(db, data(plant, notes="Original"))
        enforce(db)
        with pytest.raises(IntegrityError), db.begin_nested():  # noqa: PT012 - aggregate rollback
            write_harvest(
                db,
                data(
                    group,
                    notes="Correction",
                    items=[{"material_kind": "root"}, {"material_kind": "whole_plant"}],
                ),
                retained.id,
            )
            db.execute(
                text(
                    "UPDATE harvest_items SET quantity_kind = 'weight' "
                    "WHERE harvest_id = :id AND display_order = 1"
                ),
                {"id": retained.id},
            )
        restored = read_harvest(db, retained.id)
        assert restored.plant_id == plant.id
        assert restored.notes == "Original"
        assert [item.material_kind for item in restored.items] == ["fruit"]
        restored_event = db.get(Event, retained.event_id)
        assert restored_event is not None
        db.refresh(restored_event)
        assert restored_event.plant_id == plant.id
        assert restored_event.notes == "Original"


def test_http_auth_atomic_aggregate_and_owned_event_protection(
    database_connection: Connection, harvest_browser: tuple[str, str]
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        plant, _, _ = fixtures(db)
        db.commit()
        plant_id = plant.id
    body = {"plant_id": str(plant_id), "items": [{"material_kind": "fruit"}]}
    assert request("GET", "/api/v1/harvests").status_code == 401
    assert (
        request("POST", "/api/v1/harvests", browser=harvest_browser, body=body).status_code == 403
    )
    invalid = request(
        "POST",
        "/api/v1/harvests",
        browser=harvest_browser,
        mutation_headers=True,
        body={**body, "items": []},
    )
    assert invalid.status_code == 422
    response = request(
        "POST", "/api/v1/harvests", browser=harvest_browser, mutation_headers=True, body=body
    )
    assert response.status_code == 201, response.text
    result = response.json()
    assert len(result["items"]) == 1
    assert (
        request(
            "PUT",
            f"/api/v1/events/{result['event_id']}",
            browser=harvest_browser,
            mutation_headers=True,
            body={"kind": "flowering"},
        ).status_code
        == 409
    )
    assert (
        request(
            "DELETE",
            f"/api/v1/events/{result['event_id']}",
            browser=harvest_browser,
            mutation_headers=True,
        ).status_code
        == 409
    )
    assert (
        request(
            "GET",
            f"/api/v1/harvests/{result['id']}",
            browser=harvest_browser,
            mutation_headers=True,
        ).status_code
        == 200
    )
    assert (
        request(
            "DELETE",
            f"/api/v1/harvests/{result['id']}",
            browser=harvest_browser,
            mutation_headers=True,
        ).status_code
        == 204
    )
