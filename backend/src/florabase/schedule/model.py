from datetime import UTC, date, datetime
from uuid import UUID, uuid7

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from florabase.db.base import Base

KINDS = (
    "repot",
    "water",
    "fertilize",
    "move",
    "check_germination",
    "inspect",
    "harvest",
    "follow_up",
)
TARGETS = {
    "botanical_identity": "botanical_identities",
    "seed_lot": "seed_lots",
    "sowing": "sowings",
    "plant": "plants",
    "plant_group": "plant_groups",
    "location": "locations",
}


def utc_now() -> datetime:
    return datetime.now(UTC)


class ScheduledActivity(Base):
    __tablename__ = "scheduled_activities"
    __table_args__ = (
        CheckConstraint(
            "activity_kind IN (" + ", ".join(f"'{kind}'" for kind in KINDS) + ")",
            name="ck_schedule_kind",
        ),
        CheckConstraint(
            "status IN ('planned', 'completed', 'cancelled')", name="ck_schedule_status"
        ),
        CheckConstraint("version >= 1", name="ck_schedule_version"),
        CheckConstraint(
            "char_length(title) BETWEEN 1 AND 255 AND title = btrim(title) "
            "AND title !~ '[[:cntrl:]]'",
            name="ck_schedule_title",
        ),
        CheckConstraint(
            "notes IS NULL OR char_length(notes) BETWEEN 1 AND 20000", name="ck_schedule_notes"
        ),
        CheckConstraint(
            "due_on BETWEEN DATE '0001-01-01' AND DATE '9999-12-31'", name="ck_schedule_due"
        ),
        CheckConstraint(
            (
                "num_nonnulls(botanical_identity_id, seed_lot_id, sowing_id, plant_id, "
                "plant_group_id, location_id) <= 1"
            ),
            name="ck_schedule_target",
        ),
        CheckConstraint(
            (
                "(status = 'planned' AND completed_at IS NULL AND cancelled_at IS NULL AND "
                "completion_fingerprint IS NULL AND linked_event_id IS NULL) OR (status = "
                "'completed' AND completed_at IS NOT NULL AND cancelled_at IS NULL AND "
                "completion_fingerprint IS NOT NULL) OR (status = 'cancelled' AND "
                "cancelled_at IS NOT NULL AND completed_at IS NULL AND "
                "completion_fingerprint IS NULL AND linked_event_id IS NULL)"
            ),
            name="ck_schedule_transition",
        ),
        CheckConstraint(
            "linked_event_id IS NULL OR num_nonnulls(plant_id, plant_group_id) = 1",
            name="ck_schedule_event_target",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    activity_kind: Mapped[str] = mapped_column(String(24))
    title: Mapped[str] = mapped_column(String(255))
    due_on: Mapped[date] = mapped_column(Date(), index=True)
    notes: Mapped[str | None] = mapped_column(Text())
    status: Mapped[str] = mapped_column(String(16), default="planned", index=True)
    version: Mapped[int] = mapped_column(Integer(), default=1)
    botanical_identity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("botanical_identities.id", ondelete="RESTRICT"), index=True
    )
    seed_lot_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("seed_lots.id", ondelete="RESTRICT"), index=True
    )
    sowing_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("sowings.id", ondelete="RESTRICT"), index=True
    )
    plant_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("plants.id", ondelete="RESTRICT"), index=True
    )
    plant_group_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("plant_groups.id", ondelete="RESTRICT"), index=True
    )
    location_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"), index=True
    )
    linked_event_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("events.id", ondelete="RESTRICT"), unique=True
    )
    completion_fingerprint: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
