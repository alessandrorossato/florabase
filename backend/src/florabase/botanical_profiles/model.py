from uuid import UUID

from sqlalchemy import ForeignKey, Text, Uuid
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
