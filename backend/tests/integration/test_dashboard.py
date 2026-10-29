from datetime import UTC, date, datetime, timedelta
from uuid import uuid7

import pytest
from sqlalchemy import Connection, delete, event, select, text
from sqlalchemy.orm import Session

from florabase.attachments.model import Attachment
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_profiles.model import BotanicalProfile, BotanicalProfileNativeRange
from florabase.collection_photos.model import (
    BotanicalIdentityCoverImage,
    CollectionPrimaryPhoto,
    LocalCollectionPhoto,
    MediaAsset,
)
from florabase.collection_views.dashboard import photographs
from florabase.collection_views.service import dashboard
from florabase.events.schemas import EventCreate
from florabase.events.service import create_event
from florabase.geographic_places.model import GeographicPlace
from florabase.harvests.inventory_schemas import DispositionCreate
from florabase.harvests.inventory_service import record_disposition
from florabase.harvests.model import Harvest
from florabase.orders.model import Order
from florabase.plants.model import Plant, PlantGroup
from florabase.schedule.model import ScheduledActivity
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import GerminationObservation, Sowing
from florabase.taxonomy.model import WfoLink

from .test_harvest_inventory import setup as inventory_fixture
from .test_search import _api_get
from .test_supplier_api import authenticated_browser as authenticated_browser
from .test_supplier_api import request

pytestmark = pytest.mark.integration
DAY = date(2026, 10, 11)


def test_empty_and_lifecycle_coverage_sourcing_and_propagation(
    database_connection: Connection,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        empty = dashboard(db, DAY)
        assert not any(empty.counts.model_dump().values())
        assert empty.overview.current_identities == 0
        assert empty.overview.upcoming == []
        assert empty.overview.recent_activity == []
        current, historical, reference, sowing_only = [
            BotanicalIdentity(scientific_name=name)
            for name in ("Current", "Historical", "Reference", "Sowing only")
        ]
        db.add_all([current, historical, reference, sowing_only])
        db.flush()
        order = Order()
        db.add(order)
        db.flush()
        lots = [
            SeedLot(botanical_identity_id=current.id, lifecycle=state, source_kind="purchased")
            for state in ("active", "exhausted", "discarded", "lost", "reversed")
        ]
        lots.extend(
            [
                SeedLot(botanical_identity_id=current.id, source_kind="purchased_fruit"),
                SeedLot(
                    botanical_identity_id=current.id, source_kind="purchased", order_id=order.id
                ),
                SeedLot(botanical_identity_id=current.id, source_kind="unknown"),
                SeedLot(botanical_identity_id=sowing_only.id, lifecycle="exhausted"),
            ]
        )
        db.add_all(lots)
        db.flush()
        db.add_all(
            [
                Plant(
                    botanical_identity_id=current.id, direct_origin_kind="unknown", lifecycle=state
                )
                for state in (
                    "active",
                    "transferred",
                    "dead",
                    "lost",
                    "discarded",
                    "reversed",
                    "reintegrated",
                )
            ]
        )
        db.add_all(
            [
                PlantGroup(
                    botanical_identity_id=current.id, direct_origin_kind="unknown", lifecycle=state
                )
                for state in (
                    "active",
                    "completed",
                    "transferred",
                    "dead",
                    "lost",
                    "discarded",
                    "reversed",
                )
            ]
        )
        db.add(
            Plant(
                botanical_identity_id=historical.id, direct_origin_kind="unknown", lifecycle="dead"
            )
        )
        db.add_all(
            [Sowing(seed_lot_id=lots[-1].id, germinated_count=count) for count in (None, 0, 3)]
        )
        db.add_all(
            [
                Sowing(seed_lot_id=lots[0].id, lifecycle=state)
                for state in ("completed", "failed", "abandoned", "reversed")
            ]
        )
        db.add_all(
            [
                BotanicalProfile(botanical_identity_id=current.id, cultivation="Operator notes"),
                BotanicalProfile(botanical_identity_id=sowing_only.id),
                BotanicalProfile(botanical_identity_id=reference.id, description="Reference only"),
                WfoLink(identity_id=current.id, external_id="wfo-0000000001", evidence={}),
                WfoLink(identity_id=historical.id, external_id="wfo-0000000002", evidence={}),
            ]
        )
        db.flush()
        result = dashboard(db, DAY)
        assert result.counts.active_plants == result.counts.active_plant_groups == 1
        assert result.counts.active_seed_lots == 4
        assert result.counts.active_sowings == 3
        overview = result.overview
        assert overview.current_identities == 2  # active sowing on exhausted packet still current
        assert overview.identities_with_wfo == overview.identities_with_profile == 1
        assert overview.purchase_packets_without_order == 2
        assert overview.sowings_unknown_germination == 1
        assert overview.sowings_with_germination == overview.sowings_zero_germination == 1


def test_schedule_windows_bounded_lists_history_sources_and_query_bound(
    database_connection: Connection,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity = BotanicalIdentity(scientific_name="Dashboard plant")
        db.add(identity)
        db.flush()
        plant = Plant(
            botanical_identity_id=identity.id, direct_origin_kind="unknown", label="Specimen"
        )
        lot = SeedLot(botanical_identity_id=identity.id)
        db.add_all([plant, lot])
        db.flush()
        sowing = Sowing(seed_lot_id=lot.id)
        db.add(sowing)
        db.flush()
        # Tied timestamps test the stable UUID tie-break; no fake dates for partial/unknown facts.
        stamp = datetime(2026, 10, 10, tzinfo=UTC)
        for index in range(8):
            record = create_event(
                db, "plant", plant.id, EventCreate(kind="observation", notes=str(index))
            )
            record.created_at = stamp
        db.add(
            GerminationObservation(sowing_id=sowing.id, observed_on=DAY, newly_germinated_count=2)
        )
        planned = []
        for delta in (-2, -1, 0, 1, 7, 8, 30):
            activity = ScheduledActivity(
                activity_kind="inspect",
                title=f"Plan {delta}",
                due_on=DAY + timedelta(days=delta),
                plant_id=plant.id,
            )
            db.add(activity)
            planned.append(activity)
        for state in ("completed", "cancelled"):
            # Complete explicitly; cancelled and planned work remain outside recent History.
            from florabase.schedule import service
            from florabase.schedule.schemas import ScheduleComplete, ScheduleWrite

            activity = service.create(
                db,
                ScheduleWrite(activity_kind="inspect", title=state, due_on=DAY - timedelta(days=1)),
            )
            if state == "completed":
                service.complete(db, activity.id, ScheduleComplete(expected_version=1))
                activity.completed_at = datetime(2026, 10, 12, tzinfo=UTC)
            else:
                service.cancel(db, activity.id, 1)
        db.flush()
        statements: list[str] = []

        def capture(
            _c: object, _cursor: object, statement: str, _p: object, _ctx: object, _many: object
        ) -> None:
            statements.append(statement)

        event.listen(database_connection, "before_cursor_execute", capture)
        try:
            result = dashboard(db, DAY).overview
        finally:
            event.remove(database_connection, "before_cursor_execute", capture)
        assert (result.overdue, result.due_today, result.next_seven_days) == (2, 1, 2)
        assert [a.id for a in result.upcoming] == [a.id for a in planned[:5]]
        assert len(result.recent_activity) == 6
        assert {row.source_kind for row in result.recent_activity} == {
            "event",
            "germination",
            "scheduled_activity",
        }
        assert not any(row.title.startswith("Plan") for row in result.recent_activity)
        assert result.recent_activity[0].source_kind == "scheduled_activity"
        assert result.recent_activity[0].primary.label == "completed"
        assert result.recent_activity[0].occurred_at == datetime(2026, 10, 12, tzinfo=UTC)
        assert result.recent_activity[1].source_kind == "germination"
        assert all(
            row.date_basis == "recorded" and row.occurred_on is None
            for row in result.recent_activity[2:]
        )
        assert [r.key for r in result.recent_activity] == [
            r.key for r in dashboard(db, DAY).overview.recent_activity
        ]
        # Includes compatibility Event/photo enrichment; independent of collection/list cardinality.
        assert len(statements) <= 25
        next_day = dashboard(db, DAY + timedelta(days=1)).overview
        assert (next_day.overdue, next_day.due_today, next_day.next_seven_days) == (3, 1, 2)


def test_dashboard_auth_and_calendar_validation(authenticated_browser: tuple[str, str]) -> None:
    assert request("GET", "/api/v1/dashboard")[0] == 401
    cookie, _ = authenticated_browser
    assert _api_get("/api/v1/dashboard?today=2026-02-30", cookie)[0] == 422
    assert _api_get("/api/v1/dashboard?today=2026-10-11T00:00:00Z", cookie)[0] == 422
    status, body = _api_get("/api/v1/dashboard?today=2026-10-11", cookie)
    assert status == 200
    assert isinstance(body["overview"], dict)
    assert body["overview"]["today"] == "2026-10-11"


def test_stored_material_and_native_range_only_profile_are_current(
    database_connection: Connection,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        inventory, _ = inventory_fixture(db, unknown=True)
        harvest = db.get(Harvest, inventory.harvest_id)
        assert harvest is not None
        plant = db.get(Plant, harvest.plant_id)
        assert plant is not None
        assert plant.lifecycle == "dead"
        identity_id = plant.botanical_identity_id
        for group in db.scalars(
            select(PlantGroup).where(PlantGroup.botanical_identity_id == identity_id)
        ):
            group.lifecycle = "dead"
        place = db.scalar(select(GeographicPlace).limit(1))
        assert place is not None
        db.add(BotanicalProfile(botanical_identity_id=identity_id))
        db.flush()
        db.add(
            BotanicalProfileNativeRange(
                botanical_profile_id=identity_id, geographic_place_id=place.id
            )
        )
        db.flush()
        active = dashboard(db, DAY)
        assert active.counts.active_plants == 0
        assert active.overview.current_identities == active.overview.identities_with_profile == 1
        record_disposition(db, inventory.id, DispositionCreate(kind="consumed", mode="use_all"))
        depleted = dashboard(db, DAY).overview
        assert depleted.current_identities == depleted.identities_with_profile == 0


def test_photographs_sample_actual_plants_with_explicit_primary_and_reference_fallbacks(
    database_connection: Connection,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        assert photographs(db) == []
        identity = BotanicalIdentity(scientific_name="Aloe vera")
        db.add(identity)
        db.flush()
        plants = [
            Plant(
                botanical_identity_id=identity.id, direct_origin_kind="unknown", label=f"Plant {i}"
            )
            for i in range(3)
        ]
        db.add_all(plants)
        db.add(
            Plant(botanical_identity_id=identity.id, direct_origin_kind="unknown", lifecycle="dead")
        )
        db.add(PlantGroup(botanical_identity_id=identity.id, direct_origin_kind="unknown"))
        db.flush()

        def asset(index: int) -> MediaAsset:
            attachment_id = uuid7()
            attachment = Attachment(
                id=attachment_id,
                storage_key=f"objects/{attachment_id.hex[:2]}/{attachment_id.hex}",
                original_filename=f"photo-{index}.jpg",
                media_type="image/jpeg",
                byte_size=100,
                sha256=f"{index:064x}",
                state="active",
            )
            db.add(attachment)
            db.flush()
            image = MediaAsset(
                kind="local",
                attachment_id=attachment.id,
                attribution="Recorded creator",
                state="active",
            )
            db.add(image)
            db.flush()
            return image

        primary, cover = asset(1), asset(2)
        link = LocalCollectionPhoto(plant_id=plants[0].id, media_asset_id=primary.id)
        db.add(link)
        db.flush()
        db.add(CollectionPrimaryPhoto(plant_id=plants[0].id, local_collection_photo_id=link.id))
        db.add(
            BotanicalIdentityCoverImage(
                botanical_identity_id=identity.id, media_asset_id=cover.id, source_mode="local"
            )
        )
        db.flush()
        statements: list[str] = []

        def capture(
            _c: object, _cursor: object, statement: str, _p: object, _ctx: object, _many: object
        ) -> None:
            statements.append(statement)

        event.listen(database_connection, "before_cursor_execute", capture)
        try:
            result = photographs(db)
        finally:
            event.remove(database_connection, "before_cursor_execute", capture)
        assert {item.id for item in result} == {plant.id for plant in plants}
        assert len(statements) == 5
        chosen = next(item for item in result if item.id == plants[0].id)
        assert chosen.image is not None
        assert str(primary.id) in chosen.image.thumbnail_url
        assert chosen.image.attribution == "Recorded creator"
        assert all(
            item.reference_image and str(cover.id) in item.reference_image.thumbnail_url
            for item in result
        )
        db.execute(
            delete(CollectionPrimaryPhoto).where(CollectionPrimaryPhoto.plant_id == plants[0].id)
        )
        db.delete(link)
        db.execute(
            delete(BotanicalIdentityCoverImage).where(
                BotanicalIdentityCoverImage.botanical_identity_id == identity.id
            )
        )
        db.flush()
        primary.state = "pending_delete"
        cover.state = "pending_delete"
        db.flush()
        assert all(item.image is None and item.reference_image is None for item in photographs(db))


def test_dashboard_sampling_is_not_first_page_biased_and_is_seed_testable(
    database_connection: Connection,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity = BotanicalIdentity(scientific_name="Sampling population")
        db.add(identity)
        db.flush()
        plants = [
            Plant(
                botanical_identity_id=identity.id,
                direct_origin_kind="unknown",
                label=f"Plant {i:03}",
            )
            for i in range(200)
        ]
        db.add_all(plants)
        db.flush()
        db.execute(text("SELECT setseed(0.42)"))
        first = photographs(db)
        db.execute(text("SELECT setseed(0.42)"))
        assert [item.id for item in photographs(db)] == [item.id for item in first]
        assert len({item.id for item in first}) == 8
        assert any(item.id in {plant.id for plant in plants[100:]} for item in first)


def test_dashboard_remote_only_reference_is_never_a_thumbnail(
    database_connection: Connection,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as db:
        identity = BotanicalIdentity(scientific_name="Aloe vera", cultivar_name="Gold")
        db.add(identity)
        db.flush()
        plant = Plant(botanical_identity_id=identity.id, direct_origin_kind="unknown")
        remote = MediaAsset(
            kind="external",
            state="active",
            attribution="Recorded reference creator",
            image_url="https://example.invalid/never-fetch.jpg",
            source_url="https://example.invalid/source",
        )
        db.add_all([plant, remote])
        db.flush()
        db.add(
            BotanicalIdentityCoverImage(
                botanical_identity_id=identity.id, media_asset_id=remote.id, source_mode="external"
            )
        )
        db.flush()
        result = photographs(db)
        assert len(result) == 1
        assert result[0].id == plant.id
        assert result[0].title == "Aloe vera \u2018Gold\u2019"
        assert result[0].image is None
        assert result[0].reference_image is None
        assert "never-fetch" not in result[0].model_dump_json()
