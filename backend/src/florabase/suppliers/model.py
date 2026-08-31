from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid7

from sqlalchemy import CheckConstraint, DateTime, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from florabase.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class SupplierKind(StrEnum):
    SELLER = "seller"
    NURSERY = "nursery"
    SUPERMARKET = "supermarket"
    PERSON = "person"
    EXCHANGE = "exchange"
    OTHER = "other"


class Supplier(Base):
    __tablename__ = "suppliers"
    __table_args__ = (
        CheckConstraint(
            "char_length(name) BETWEEN 1 AND 255",
            name="ck_suppliers_name_length",
        ),
        CheckConstraint(
            "name = regexp_replace(btrim(name), '[[:space:]]+', ' ', 'g')",
            name="ck_suppliers_name_normalized",
        ),
        CheckConstraint("name !~ '[[:cntrl:]]'", name="ck_suppliers_name_no_control"),
        CheckConstraint(
            "kind IN ('seller', 'nursery', 'supermarket', 'person', 'exchange', 'other')",
            name="ck_suppliers_kind",
        ),
        CheckConstraint(
            "website IS NULL OR (char_length(website) BETWEEN 1 AND 2048 "
            "AND website ~ '^https?://')",
            name="ck_suppliers_website",
        ),
        CheckConstraint(
            "email IS NULL OR (char_length(email) BETWEEN 3 AND 320 "
            "AND email = btrim(email) AND email !~ '[[:space:][:cntrl:]]' "
            "AND email ~ '^[^@]+@[^@]+$')",
            name="ck_suppliers_email",
        ),
        CheckConstraint(
            "phone IS NULL OR (char_length(phone) BETWEEN 1 AND 120 "
            "AND phone = regexp_replace(btrim(phone), '[[:space:]]+', ' ', 'g') "
            "AND phone !~ '[[:cntrl:]]')",
            name="ck_suppliers_phone",
        ),
        CheckConstraint(
            "notes IS NULL OR (char_length(notes) BETWEEN 1 AND 20000 "
            "AND notes = btrim(notes) "
            "AND regexp_replace(notes, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]')",
            name="ck_suppliers_notes",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(32))
    website: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
