from datetime import UTC, datetime
from uuid import UUID, uuid7

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from florabase.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class ExternalTaxonLink(Base):
    __tablename__ = "external_taxon_links"
    __table_args__ = (
        UniqueConstraint(
            "botanical_identity_id", "provider", name="uq_external_taxon_links_identity_provider"
        ),
        CheckConstraint(
            "provider = lower(provider) AND char_length(provider) BETWEEN 1 AND 32",
            name="ck_external_taxon_links_provider",
        ),
        CheckConstraint(
            "char_length(external_id) BETWEEN 1 AND 255", name="ck_external_taxon_links_external_id"
        ),
        Index("ix_external_taxon_links_identity", "botanical_identity_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    botanical_identity_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "botanical_identities.id", name="fk_external_taxon_links_identity", ondelete="CASCADE"
        ),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    scientific_name: Mapped[str] = mapped_column(String(500), nullable=False)
    canonical_name: Mapped[str | None] = mapped_column(String(500))
    authorship: Mapped[str | None] = mapped_column(String(255))
    rank: Mapped[str | None] = mapped_column(String(64))
    taxonomic_status: Mapped[str | None] = mapped_column(String(64))
    accepted_external_id: Mapped[str | None] = mapped_column(String(255))
    accepted_name: Mapped[str | None] = mapped_column(String(500))
    kingdom: Mapped[str | None] = mapped_column(String(255))
    phylum: Mapped[str | None] = mapped_column(String(255))
    class_name: Mapped[str | None] = mapped_column(String(255))
    order_name: Mapped[str | None] = mapped_column(String(255))
    family: Mapped[str | None] = mapped_column(String(255))
    genus: Mapped[str | None] = mapped_column(String(255))
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    last_refreshed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_refresh_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    refresh_error: Mapped[str | None] = mapped_column(Text())


class ExternalProviderCache(Base):
    __tablename__ = "external_provider_cache"
    __table_args__ = (
        CheckConstraint(
            "provider = lower(provider) AND char_length(provider) BETWEEN 1 AND 32",
            name="ck_external_provider_cache_provider",
        ),
        CheckConstraint(
            "char_length(resource_key) BETWEEN 1 AND 255",
            name="ck_external_provider_cache_resource_key",
        ),
    )

    provider: Mapped[str] = mapped_column(String(32), primary_key=True)
    resource_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB(), nullable=False)
