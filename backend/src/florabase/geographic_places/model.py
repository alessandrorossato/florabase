from datetime import UTC, datetime
from uuid import UUID, uuid7

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from florabase.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class GeographicPlace(Base):
    __tablename__ = "geographic_places"
    __table_args__ = (
        CheckConstraint(
            "char_length(name) BETWEEN 1 AND 255", name="ck_geographic_places_name_length"
        ),
        CheckConstraint(
            "name = regexp_replace(btrim(name), '[[:space:]]+', ' ', 'g')",
            name="ck_geographic_places_name_normalized",
        ),
        CheckConstraint("name !~ '[[:cntrl:]]'", name="ck_geographic_places_name_no_control"),
        CheckConstraint(
            "parent_id IS NULL OR parent_id <> id",
            name="ck_geographic_places_not_self_parent",
        ),
        CheckConstraint(
            "place_kind IN ('canonical', 'custom')",
            name="ck_geographic_places_kind",
        ),
        CheckConstraint(
            "(place_kind = 'canonical' AND source_name IS NOT NULL "
            "AND source_version IS NOT NULL AND source_code_type IS NOT NULL "
            "AND source_code IS NOT NULL AND retired_at IS NULL) OR "
            "(place_kind = 'custom' AND source_name IS NULL AND source_version IS NULL "
            "AND source_code_type IS NULL AND source_code IS NULL)",
            name="ck_geographic_places_source_metadata",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(String(255))
    parent_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("geographic_places.id", ondelete="RESTRICT"), index=True
    )
    place_kind: Mapped[str] = mapped_column(String(16), default="custom")
    source_name: Mapped[str | None] = mapped_column(String(64))
    source_version: Mapped[str | None] = mapped_column(String(32))
    source_code_type: Mapped[str | None] = mapped_column(String(32))
    source_code: Mapped[str | None] = mapped_column(String(16))
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
