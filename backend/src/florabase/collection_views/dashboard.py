"""Operational Dashboard projections. Read-only, bounded, and provider independent."""

from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from florabase.botanical_profiles.model import (
    PROFILE_FIELDS,
    BotanicalProfile,
    BotanicalProfileNativeRange,
)
from florabase.collection_views.schemas import DashboardOverview
from florabase.explore.service import collection_records
from florabase.history.service import list_history
from florabase.schedule.model import ScheduledActivity
from florabase.schedule.service import responses as schedule_responses
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing
from florabase.taxonomy.model import WfoLink


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
