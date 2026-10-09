from datetime import UTC, datetime
from uuid import UUID, uuid7

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from florabase.db.base import Base


class WcvpLink(Base):
    __tablename__ = "wcvp_links"
    __table_args__ = (
        CheckConstraint(
            "char_length(external_id) BETWEEN 1 AND 255", name="ck_wcvp_link_external_id"
        ),
    )
    identity_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("botanical_identities.id", ondelete="CASCADE"), primary_key=True
    )
    version: Mapped[UUID] = mapped_column(Uuid(), default=uuid7, nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    taxon: Mapped[dict[str, object]] = mapped_column(JSONB(), nullable=False)
    source: Mapped[dict[str, object]] = mapped_column(JSONB(), nullable=False)
    identity_snapshot: Mapped[dict[str, object]] = mapped_column(JSONB(), nullable=False)
    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class NativeRangeRevision(Base):
    __tablename__ = "native_range_revisions"
    __table_args__ = (CheckConstraint("version >= 0", name="ck_native_range_revision_nonnegative"),)
    identity_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("botanical_identities.id", ondelete="CASCADE"), primary_key=True
    )
    version: Mapped[int] = mapped_column(BigInteger(), nullable=False, default=0)


class NativeRangeProposal(Base):
    __tablename__ = "native_range_proposals"
    __table_args__ = (
        CheckConstraint(
            "jsonb_typeof(evidence) = 'object' AND "
            "evidence->>'format_version' IS NOT DISTINCT FROM '1'",
            name="ck_native_range_proposal_format",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    identity_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("botanical_identities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    evidence: Mapped[dict[str, object]] = mapped_column(JSONB(), nullable=False)


class NativeRangeApplication(Base):
    __tablename__ = "native_range_applications"
    __table_args__ = (
        CheckConstraint(
            "jsonb_typeof(evidence) = 'object'", name="ck_native_range_application_evidence"
        ),
    )
    # One application per frozen proposal, including an explicit keep-only application.
    proposal_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("native_range_proposals.id", ondelete="RESTRICT"), primary_key=True
    )
    identity_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("botanical_identities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    evidence: Mapped[dict[str, object]] = mapped_column(JSONB(), nullable=False)
