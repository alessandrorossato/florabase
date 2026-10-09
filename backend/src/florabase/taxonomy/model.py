from datetime import UTC, datetime
from uuid import UUID, uuid7

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from florabase.db.base import Base


class WfoLink(Base):
    __tablename__ = "wfo_links"
    __table_args__ = (
        CheckConstraint("external_id ~ '^wfo-[0-9]{10}$'", name="ck_wfo_link_external_id"),
        CheckConstraint("jsonb_typeof(evidence) = 'object'", name="ck_wfo_link_evidence"),
    )
    identity_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("botanical_identities.id", ondelete="CASCADE"), primary_key=True
    )
    version: Mapped[UUID] = mapped_column(Uuid(), default=uuid7, nullable=False)
    external_id: Mapped[str] = mapped_column(String(14), nullable=False)
    evidence: Mapped[dict[str, object]] = mapped_column(JSONB(), nullable=False)
    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
