from datetime import UTC, datetime
from uuid import UUID, uuid7

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from florabase.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class Location(Base):
    __tablename__ = "locations"
    __table_args__ = (
        CheckConstraint("char_length(name) BETWEEN 1 AND 255", name="ck_locations_name_length"),
        CheckConstraint(
            "name = regexp_replace(btrim(name), '[[:space:]]+', ' ', 'g')",
            name="ck_locations_name_normalized",
        ),
        CheckConstraint("name !~ '[[:cntrl:]]'", name="ck_locations_name_no_control"),
        CheckConstraint(
            "parent_id IS NULL OR parent_id <> id", name="ck_locations_not_self_parent"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(String(255))
    parent_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("locations.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
