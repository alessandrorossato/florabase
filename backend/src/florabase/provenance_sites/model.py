from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid7

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from florabase.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class ProvenanceSite(Base):
    __tablename__ = "provenance_sites"
    __table_args__ = (
        CheckConstraint(
            "char_length(name) BETWEEN 1 AND 255 AND "
            "name = regexp_replace(btrim(name), '[[:space:]]+', ' ', 'g') AND "
            "name !~ '[[:cntrl:]]'",
            name="ck_provenance_sites_name",
        ),
        CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL) OR "
            "(latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180) IS TRUE",
            name="ck_provenance_sites_coordinates",
        ),
        CheckConstraint(
            "coordinate_accuracy_m IS NULL OR "
            "(latitude IS NOT NULL AND longitude IS NOT NULL AND coordinate_accuracy_m >= 0)",
            name="ck_provenance_sites_accuracy",
        ),
        CheckConstraint(
            "notes IS NULL OR (char_length(notes) BETWEEN 1 AND 20000 AND notes = btrim(notes) "
            "AND regexp_replace(notes, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]')",
            name="ck_provenance_sites_notes",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(String(255))
    geographic_place_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("geographic_places.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    coordinate_accuracy_m: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
