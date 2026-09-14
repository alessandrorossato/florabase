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
from sqlalchemy.orm import Mapped, mapped_column

from florabase.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


TARGET_COLUMNS = (
    "seed_lot_id",
    "sowing_id",
    "plant_id",
    "plant_group_id",
    "event_id",
)


def _target_constraint(table: str) -> CheckConstraint:
    return CheckConstraint(
        f"num_nonnulls({', '.join(TARGET_COLUMNS)}) = 1",
        name=f"ck_{table}_exactly_one_target",
    )


def _optional_text_constraint(table: str, column: str) -> CheckConstraint:
    return CheckConstraint(
        f"{column} IS NULL OR (char_length({column}) BETWEEN 1 AND 2000 "
        f"AND {column} = btrim({column}) "
        f"AND regexp_replace({column}, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]')",
        name=f"ck_{table}_{column}",
    )


class CollectionPhotoTargetMixin:
    seed_lot_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("seed_lots.id", ondelete="RESTRICT"), nullable=True
    )
    sowing_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("sowings.id", ondelete="RESTRICT"), nullable=True
    )
    plant_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("plants.id", ondelete="RESTRICT"), nullable=True
    )
    plant_group_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("plant_groups.id", ondelete="RESTRICT"), nullable=True
    )
    event_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("events.id", ondelete="RESTRICT"), nullable=True
    )


class LocalCollectionPhoto(CollectionPhotoTargetMixin, Base):
    __tablename__ = "local_collection_photos"
    __table_args__ = (
        _target_constraint("local_collection_photos"),
        _optional_text_constraint("local_collection_photos", "caption"),
        _optional_text_constraint("local_collection_photos", "attribution"),
        UniqueConstraint("attachment_id", name="uq_local_collection_photos_attachment_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    attachment_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("attachments.id", ondelete="RESTRICT"),
    )
    caption: Mapped[str | None] = mapped_column(Text(), nullable=True)
    attribution: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class ExternalImageReference(CollectionPhotoTargetMixin, Base):
    __tablename__ = "external_image_references"
    __table_args__ = (
        _target_constraint("external_image_references"),
        _optional_text_constraint("external_image_references", "caption"),
        CheckConstraint(
            "char_length(attribution) BETWEEN 1 AND 2000 AND attribution = btrim(attribution) "
            "AND regexp_replace(attribution, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]'",
            name="ck_external_image_references_attribution",
        ),
        CheckConstraint(
            "char_length(image_url) BETWEEN 1 AND 2048 AND image_url ~ '^https://[^[:space:]]+$'",
            name="ck_external_image_references_image_url",
        ),
        CheckConstraint(
            "char_length(source_url) BETWEEN 1 AND 2048 AND source_url ~ '^https://[^[:space:]]+$'",
            name="ck_external_image_references_source_url",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    image_url: Mapped[str] = mapped_column(String(2048))
    source_url: Mapped[str] = mapped_column(String(2048))
    attribution: Mapped[str] = mapped_column(Text())
    caption: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class BotanicalIdentityCoverImage(Base):
    __tablename__ = "botanical_identity_cover_images"
    __table_args__ = (
        CheckConstraint(
            "source_mode IN ('local', 'external')",
            name="ck_botanical_identity_cover_images_source_mode",
        ),
        CheckConstraint(
            "(source_mode = 'local' AND attachment_id IS NOT NULL "
            "AND image_url IS NULL AND source_url IS NULL AND attribution IS NULL "
            "AND licence_label IS NULL AND licence_url IS NULL) OR "
            "(source_mode = 'external' AND attachment_id IS NULL "
            "AND image_url IS NOT NULL AND source_url IS NOT NULL "
            "AND attribution IS NOT NULL)",
            name="ck_botanical_identity_cover_images_source_fields",
        ),
        CheckConstraint(
            "attribution IS NULL OR (char_length(attribution) BETWEEN 1 AND 2000 "
            "AND attribution = btrim(attribution) "
            "AND regexp_replace(attribution, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]')",
            name="ck_botanical_identity_cover_images_attribution",
        ),
        _optional_text_constraint("botanical_identity_cover_images", "licence_label"),
        CheckConstraint(
            "image_url IS NULL OR (char_length(image_url) BETWEEN 1 AND 2048 "
            "AND image_url ~ '^https://[^[:space:]]+$')",
            name="ck_botanical_identity_cover_images_image_url",
        ),
        CheckConstraint(
            "source_url IS NULL OR (char_length(source_url) BETWEEN 1 AND 2048 "
            "AND source_url ~ '^https://[^[:space:]]+$')",
            name="ck_botanical_identity_cover_images_source_url",
        ),
        CheckConstraint(
            "licence_url IS NULL OR (char_length(licence_url) BETWEEN 1 AND 2048 "
            "AND licence_url ~ '^https://[^[:space:]]+$')",
            name="ck_botanical_identity_cover_images_licence_url",
        ),
        UniqueConstraint(
            "botanical_identity_id",
            name="uq_botanical_identity_cover_images_botanical_identity_id",
        ),
        UniqueConstraint("attachment_id", name="uq_botanical_identity_cover_images_attachment_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    botanical_identity_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("botanical_identities.id", ondelete="RESTRICT")
    )
    source_mode: Mapped[str] = mapped_column(String(16))
    attachment_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("attachments.id", ondelete="RESTRICT"), nullable=True
    )
    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    attribution: Mapped[str | None] = mapped_column(Text(), nullable=True)
    licence_label: Mapped[str | None] = mapped_column(Text(), nullable=True)
    licence_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


for model in (LocalCollectionPhoto, ExternalImageReference):
    for column in TARGET_COLUMNS:
        Index(f"ix_{model.__tablename__}_{column}", getattr(model, column))

Index(
    "ix_local_collection_photos_attachment_id",
    LocalCollectionPhoto.attachment_id,
)
Index(
    "ix_botanical_identity_cover_images_botanical_identity_id",
    BotanicalIdentityCoverImage.botanical_identity_id,
)
Index(
    "ix_botanical_identity_cover_images_attachment_id",
    BotanicalIdentityCoverImage.attachment_id,
)
