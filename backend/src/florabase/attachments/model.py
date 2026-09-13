from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid7

from sqlalchemy import BigInteger, CheckConstraint, DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from florabase.db.base import Base

ATTACHMENT_MAX_BYTES = 25 * 1024 * 1024
SUPPORTED_MEDIA_TYPES = ("image/jpeg", "image/png", "image/webp")


class AttachmentState(StrEnum):
    ACTIVE = "active"
    PENDING_DELETE = "pending_delete"


def utc_now() -> datetime:
    return datetime.now(UTC)


class Attachment(Base):
    __tablename__ = "attachments"
    __table_args__ = (
        CheckConstraint(
            "storage_key ~ '^objects/[0-9a-f]{2}/[0-9a-f]{32}$'",
            name="ck_attachments_storage_key",
        ),
        CheckConstraint(
            "char_length(original_filename) BETWEEN 1 AND 255 "
            "AND original_filename = btrim(original_filename) "
            "AND original_filename !~ '[[:cntrl:]/\\\\]'",
            name="ck_attachments_original_filename",
        ),
        CheckConstraint(
            "media_type IN ('image/jpeg', 'image/png', 'image/webp')",
            name="ck_attachments_media_type",
        ),
        CheckConstraint(
            f"byte_size BETWEEN 1 AND {ATTACHMENT_MAX_BYTES}",
            name="ck_attachments_byte_size",
        ),
        CheckConstraint(
            "sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_attachments_sha256",
        ),
        CheckConstraint(
            "state IN ('active', 'pending_delete')",
            name="ck_attachments_state",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    media_type: Mapped[str] = mapped_column(String(32))
    byte_size: Mapped[int] = mapped_column(BigInteger())
    sha256: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(32), default=AttachmentState.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
