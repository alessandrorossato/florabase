"""Operational Dashboard projections. Read-only, bounded, and provider independent."""

from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from florabase.attachments.model import Attachment, AttachmentState
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_profiles.model import (
    PROFILE_FIELDS,
    BotanicalProfile,
    BotanicalProfileNativeRange,
)
from florabase.collection_photos.model import (
    BotanicalIdentityCoverImage,
    CollectionPrimaryPhoto,
    ExternalImageReference,
    LocalCollectionPhoto,
    MediaAsset,
)
from florabase.collection_views.schemas import DashboardImage, DashboardOverview, DashboardPhoto
from florabase.explore.service import collection_records
from florabase.history.service import list_history
from florabase.plants.model import Plant
from florabase.schedule.model import ScheduledActivity
from florabase.schedule.service import responses as schedule_responses
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing
from florabase.taxonomy.model import WfoLink


def photographs(database: Session) -> list[DashboardPhoto]:
    """Uniform DB sampling over all active individuals, before bounded visual lookups.

    PostgreSQL random() is evaluated per eligible row: no first-page bias. A response is
    a visit snapshot; the client retains it through ordinary rerenders/day refreshes.
    """
    rows = database.execute(
        select(Plant, BotanicalIdentity)
        .join(BotanicalIdentity, BotanicalIdentity.id == Plant.botanical_identity_id)
        .where(Plant.lifecycle == "active")
        .order_by(func.random())
        .limit(8)
    ).all()
    if not rows:
        return []
    ids = [plant.id for plant, _identity in rows]
    identity_ids = [identity.id for _plant, identity in rows]
    # Resolve explicit primary links and identity covers separately; never fetch remote URLs.
    local = dict(
        database.execute(
            select(CollectionPrimaryPhoto.plant_id, LocalCollectionPhoto.media_asset_id)
            .join(
                LocalCollectionPhoto,
                LocalCollectionPhoto.id == CollectionPrimaryPhoto.local_collection_photo_id,
            )
            .where(
                CollectionPrimaryPhoto.plant_id.in_(ids),
                LocalCollectionPhoto.plant_id == CollectionPrimaryPhoto.plant_id,
            )
        )
        .tuples()
        .all()
    )
    external = dict(
        database.execute(
            select(CollectionPrimaryPhoto.plant_id, ExternalImageReference.media_asset_id)
            .join(
                ExternalImageReference,
                ExternalImageReference.id == CollectionPrimaryPhoto.external_image_reference_id,
            )
            .where(
                CollectionPrimaryPhoto.plant_id.in_(ids),
                ExternalImageReference.plant_id == CollectionPrimaryPhoto.plant_id,
            )
        )
        .tuples()
        .all()
    )
    covers = dict(
        database.execute(
            select(
                BotanicalIdentityCoverImage.botanical_identity_id,
                BotanicalIdentityCoverImage.media_asset_id,
            ).where(BotanicalIdentityCoverImage.botanical_identity_id.in_(identity_ids))
        )
        .tuples()
        .all()
    )
    asset_ids = set(local.values()) | set(external.values()) | set(covers.values())
    images = (
        {
            asset.id: DashboardImage(
                thumbnail_url=f"/api/v1/media-assets/{asset.id}/thumbnail"
                + (f"?v={attachment.sha256}" if asset.kind == "external" else ""),
                attribution=asset.attribution,
                licence_label=asset.licence_label,
                licence_url=asset.licence_url,
                source_url=asset.source_url,
            )
            for asset, attachment in database.execute(
                select(MediaAsset, Attachment)
                .join(Attachment, Attachment.id == MediaAsset.attachment_id)
                .where(
                    MediaAsset.id.in_(asset_ids),
                    MediaAsset.state == "active",
                    Attachment.state == AttachmentState.ACTIVE,
                )
            )
        }
        if asset_ids
        else {}
    )
    return [
        DashboardPhoto(
            id=plant.id,
            title=plant.label
            or (
                identity.scientific_name
                + (f" \u2018{identity.cultivar_name}\u2019" if identity.cultivar_name else "")
            ),
            scientific_name=identity.scientific_name,
            image=images.get(local.get(plant.id) or external.get(plant.id)),
            reference_image=images.get(covers.get(identity.id)),
        )
        for plant, identity in rows
    ]


def overview(database: Session, today: date) -> DashboardOverview:
    records = collection_records()
    current = (
        select(records.c.identity_id).where(records.c.current == 1).distinct().cte("current_ids")
    )
    profile_content = or_(
        *[getattr(BotanicalProfile, field).is_not(None) for field in PROFILE_FIELDS],
        select(BotanicalProfileNativeRange.botanical_profile_id)
        .where(
            BotanicalProfileNativeRange.botanical_profile_id
            == BotanicalProfile.botanical_identity_id
        )
        .exists(),
    )
    coverage = database.execute(
        select(
            select(func.count()).select_from(current).scalar_subquery(),
            select(func.count())
            .select_from(WfoLink)
            .where(WfoLink.identity_id.in_(select(current.c.identity_id)))
            .scalar_subquery(),
            select(func.count())
            .select_from(BotanicalProfile)
            .where(
                BotanicalProfile.botanical_identity_id.in_(select(current.c.identity_id)),
                profile_content,
            )
            .scalar_subquery(),
        )
    ).one()
    propagation = database.execute(
        select(
            func.count().filter(Sowing.germinated_count.is_(None)),
            func.count().filter(Sowing.germinated_count > 0),
            func.count().filter(Sowing.germinated_count == 0),
        ).where(Sowing.lifecycle == "active")
    ).one()
    unlinked = database.scalar(
        select(func.count())
        .select_from(SeedLot)
        .where(
            SeedLot.lifecycle == "active",
            SeedLot.source_kind.in_(("purchased", "purchased_fruit")),
            SeedLot.order_id.is_(None),
        )
    )
    week_end = date.fromordinal(min(today.toordinal() + 7, date.max.toordinal()))
    schedule = database.execute(
        select(
            func.count().filter(ScheduledActivity.due_on < today),
            func.count().filter(ScheduledActivity.due_on == today),
            func.count().filter(
                ScheduledActivity.due_on > today, ScheduledActivity.due_on <= week_end
            ),
        ).where(ScheduledActivity.status == "planned")
    ).one()
    upcoming = list(
        database.scalars(
            select(ScheduledActivity)
            .where(ScheduledActivity.status == "planned")
            .order_by(ScheduledActivity.due_on, ScheduledActivity.id)
            .limit(5)
        )
    )
    return DashboardOverview(
        today=today,
        current_identities=coverage[0],
        identities_with_wfo=coverage[1],
        identities_with_profile=coverage[2],
        sowings_unknown_germination=propagation[0],
        sowings_with_germination=propagation[1],
        sowings_zero_germination=propagation[2],
        purchase_packets_without_order=unlinked or 0,
        overdue=schedule[0],
        due_today=schedule[1],
        next_seven_days=schedule[2],
        upcoming=schedule_responses(database, upcoming, today),
        recent_activity=list_history(database, limit=6).items,
    )
