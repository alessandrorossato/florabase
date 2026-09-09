from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from florabase.db.base import Base

PROFILE_FIELDS = (
    "description",
    "origin_distribution",
    "cultivation",
    "uses",
    "warnings",
)
MAX_PROFILE_SECTION_LENGTH = 20_000


class BotanicalProfile(Base):
    __tablename__ = "botanical_profiles"

    botanical_identity_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "botanical_identities.id",
            name="fk_botanical_profiles_identity",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    origin_distribution: Mapped[str | None] = mapped_column(Text(), nullable=True)
    cultivation: Mapped[str | None] = mapped_column(Text(), nullable=True)
    uses: Mapped[str | None] = mapped_column(Text(), nullable=True)
    warnings: Mapped[str | None] = mapped_column(Text(), nullable=True)


def utc_now() -> datetime:
    return datetime.now(UTC)


class BotanicalProfileNativeRange(Base):
    __tablename__ = "botanical_profile_native_ranges"

    botanical_profile_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "botanical_profiles.botanical_identity_id",
            name="fk_botanical_profile_native_ranges_profile",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    geographic_place_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "geographic_places.id",
            name="fk_botanical_profile_native_ranges_place",
            ondelete="RESTRICT",
        ),
        primary_key=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
