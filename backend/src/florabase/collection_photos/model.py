"""Assets are reusable; links and covers own only their record context."""

from datetime import UTC, datetime
from uuid import UUID, uuid7

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    select,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import SQLColumnExpression

from florabase.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


TARGET_COLUMNS = (
    "seed_lot_id",
    "sowing_id",
    "plant_id",
    "plant_group_id",
    "event_id",
    "harvest_id",
)


def _optional_text_constraint(table: str, column: str) -> CheckConstraint:
    return CheckConstraint(
        f"{column} IS NULL OR (char_length({column}) BETWEEN 1 AND 2000 "
        f"AND {column} = btrim({column}) "
        f"AND regexp_replace({column}, E'[\\n\\t]', '', 'g') !~ '[[:cntrl:]]')",
        name=f"ck_{table}_{column}",
    )


class MediaAsset(Base):
    __tablename__ = "media_assets"
    __table_args__ = (
        CheckConstraint("kind IN ('local', 'external')", name="ck_media_assets_kind"),
        CheckConstraint("state IN ('active', 'pending_delete')", name="ck_media_assets_state"),
        CheckConstraint(
            "(kind = 'local' AND attachment_id IS NOT NULL AND image_url IS NULL AND "
            "source_url IS NULL) OR (kind = 'external' AND "
            "image_url IS NOT NULL AND source_url IS NOT NULL AND attribution IS NOT NULL)",
            name="ck_media_assets_source",
        ),
        CheckConstraint(
            "(kind = 'local' AND fetched_at IS NULL AND copy_cleanup_attachment_id IS NULL) OR "
            "(kind = 'external' AND ((attachment_id IS NULL AND fetched_at IS NULL) OR "
            "(attachment_id IS NOT NULL AND fetched_at IS NOT NULL)))",
            name="ck_media_assets_local_copy",
        ),
        CheckConstraint(
            "copy_cleanup_attachment_id IS NULL OR copy_cleanup_attachment_id <> attachment_id",
            name="ck_media_assets_distinct_copy_cleanup",
        ),
        CheckConstraint("width IS NULL OR width > 0", name="ck_media_assets_width"),
        CheckConstraint("height IS NULL OR height > 0", name="ck_media_assets_height"),
        _optional_text_constraint("media_assets", "title"),
        _optional_text_constraint("media_assets", "attribution"),
        _optional_text_constraint("media_assets", "licence_label"),
        *[
            CheckConstraint(
                f"{column} IS NULL OR (char_length({column}) BETWEEN 1 AND 2048 "
                f"AND {column} ~ '^https://[^[:space:]]+$')",
                name=f"ck_media_assets_{column}",
            )
            for column in ("image_url", "source_url", "licence_url")
        ],
        UniqueConstraint("id", "kind", name="uq_media_assets_id_kind"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    kind: Mapped[str] = mapped_column(String(16))
    attachment_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("attachments.id", ondelete="RESTRICT"), unique=True, nullable=True
    )
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    copy_cleanup_attachment_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("attachments.id", ondelete="RESTRICT"), unique=True, nullable=True
    )
    title: Mapped[str | None] = mapped_column(Text(), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    attribution: Mapped[str | None] = mapped_column(Text(), nullable=True)
    licence_label: Mapped[str | None] = mapped_column(Text(), nullable=True)
    licence_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    height: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    state: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class AssetMetadataMixin:
    """Compatibility attributes for existing photo/cover helpers; persisted on the asset."""

    media_asset: Mapped[MediaAsset]
    media_asset_id: Mapped[UUID]

    def _asset(self) -> MediaAsset:
        if self.media_asset is None:
            self.media_asset = MediaAsset(
                id=uuid7(),
                kind=getattr(self, "source_kind", None) or getattr(self, "source_mode", "local"),
                state="active",
            )
        return self.media_asset

    @hybrid_property
    def attachment_id(self) -> UUID | None:
        return self._asset().attachment_id

    @attachment_id.inplace.setter
    def _set_attachment_id(self, value: UUID | None) -> None:
        self._asset().attachment_id = value

    @attachment_id.inplace.expression
    @classmethod
    def _attachment_expression(cls) -> SQLColumnExpression[UUID | None]:
        return (
            select(MediaAsset.attachment_id)
            .where(MediaAsset.id == cls.media_asset_id)
            .scalar_subquery()
        )

    @property
    def content_url(self) -> str | None:
        asset = self._asset()
        return (
            f"/api/v1/attachments/{asset.attachment_id}/content"
            if asset.attachment_id and asset.state == "active"
            else None
        )

    @property
    def thumbnail_url(self) -> str | None:
        asset = self._asset()
        return (
            f"/api/v1/media-assets/{asset.id}/thumbnail"
            + (f"?v={asset.fetched_at.isoformat()}" if asset.fetched_at else "")
            if asset.attachment_id and asset.state == "active"
            else None
        )

    @property
    def fetched_at(self) -> datetime | None:
        return self._asset().fetched_at

    @property
    def attribution(self) -> str | None:
        return self._asset().attribution

    @attribution.setter
    def attribution(self, value: str | None) -> None:
        self._asset().attribution = value

    @property
    def image_url(self) -> str | None:
        return self._asset().image_url

    @image_url.setter
    def image_url(self, value: str | None) -> None:
        self._asset().image_url = value

    @property
    def source_url(self) -> str | None:
        return self._asset().source_url

    @source_url.setter
    def source_url(self, value: str | None) -> None:
        self._asset().source_url = value

    @property
    def licence_label(self) -> str | None:
        return self._asset().licence_label

    @licence_label.setter
    def licence_label(self, value: str | None) -> None:
        self._asset().licence_label = value

    @property
    def licence_url(self) -> str | None:
        return self._asset().licence_url

    @licence_url.setter
    def licence_url(self, value: str | None) -> None:
        self._asset().licence_url = value


class RecordMediaLink(AssetMetadataMixin, Base):
    __tablename__ = "record_media_links"
    __table_args__ = (
        CheckConstraint(
            f"num_nonnulls({', '.join(TARGET_COLUMNS)}) = 1",
            name="ck_record_media_links_exactly_one_target",
        ),
        CheckConstraint("source_kind IN ('local', 'external')", name="ck_record_media_links_kind"),
        CheckConstraint("display_order >= 0", name="ck_record_media_links_order"),
        _optional_text_constraint("record_media_links", "caption"),
        ForeignKeyConstraint(
            ["media_asset_id", "source_kind"],
            ["media_assets.id", "media_assets.kind"],
            ondelete="RESTRICT",
            name="fk_record_media_links_asset_kind",
        ),
        *[
            UniqueConstraint("media_asset_id", column, name=f"uq_record_media_links_asset_{column}")
            for column in TARGET_COLUMNS
        ],
        *[
            UniqueConstraint("id", column, name=f"uq_record_media_links_id_{column}")
            for column in TARGET_COLUMNS
        ],
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    media_asset_id: Mapped[UUID] = mapped_column(Uuid(), index=True)
    source_kind: Mapped[str] = mapped_column(String(16))
    seed_lot_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("seed_lots.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    sowing_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("sowings.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    plant_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("plants.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    plant_group_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("plant_groups.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    event_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("events.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    harvest_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("harvests.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    caption: Mapped[str | None] = mapped_column(Text(), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer(), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    media_asset: Mapped[MediaAsset] = relationship(lazy="joined")
    __mapper_args__ = {"polymorphic_on": source_kind}  # noqa: RUF012 - SQLAlchemy mapper configuration


class LocalCollectionPhoto(RecordMediaLink):
    """Compatibility local-photo view of a RecordMediaLink, not a separate owner."""

    __mapper_args__ = {"polymorphic_identity": "local"}  # noqa: RUF012 - SQLAlchemy mapper configuration


class ExternalImageReference(RecordMediaLink):
    """Compatibility external-photo view of a RecordMediaLink."""

    __mapper_args__ = {"polymorphic_identity": "external"}  # noqa: RUF012 - SQLAlchemy mapper configuration


class CollectionPrimaryPhoto(Base):
    __tablename__ = "collection_primary_photos"
    __table_args__ = (
        CheckConstraint(
            "num_nonnulls(seed_lot_id, plant_id, plant_group_id, harvest_id) = 1",
            name="ck_collection_primary_photos_exactly_one_target",
        ),
        CheckConstraint(
            "num_nonnulls(local_collection_photo_id, external_image_reference_id) = 1",
            name="ck_collection_primary_photos_exactly_one_source",
        ),
        *[
            UniqueConstraint(column, name=f"uq_collection_primary_photos_{column}")
            for column in (
                "seed_lot_id",
                "plant_id",
                "plant_group_id",
                "harvest_id",
                "local_collection_photo_id",
                "external_image_reference_id",
            )
        ],
        *[
            ForeignKeyConstraint(
                [source, target],
                ["record_media_links.id", f"record_media_links.{target}"],
                ondelete="CASCADE",
                name=f"fk_primary_{source}_{target}",
            )
            for source in ("local_collection_photo_id", "external_image_reference_id")
            for target in ("seed_lot_id", "plant_id", "plant_group_id", "harvest_id")
        ],
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    seed_lot_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("seed_lots.id", ondelete="RESTRICT"), nullable=True
    )
    plant_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("plants.id", ondelete="RESTRICT"), nullable=True
    )
    plant_group_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("plant_groups.id", ondelete="RESTRICT"), nullable=True
    )
    harvest_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("harvests.id", ondelete="RESTRICT"), nullable=True
    )
    local_collection_photo_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("record_media_links.id", ondelete="CASCADE"), nullable=True
    )
    external_image_reference_id: Mapped[UUID | None] = mapped_column(
        Uuid(), ForeignKey("record_media_links.id", ondelete="CASCADE"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class BotanicalIdentityCoverImage(AssetMetadataMixin, Base):
    __tablename__ = "botanical_identity_cover_images"
    __table_args__ = (
        ForeignKeyConstraint(
            ["media_asset_id", "source_mode"],
            ["media_assets.id", "media_assets.kind"],
            ondelete="RESTRICT",
            name="fk_identity_cover_asset_kind",
        ),
        CheckConstraint(
            "source_mode IN ('local', 'external')",
            name="ck_botanical_identity_cover_images_source_mode",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True, default=uuid7)
    botanical_identity_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey("botanical_identities.id", ondelete="RESTRICT"), unique=True
    )
    media_asset_id: Mapped[UUID] = mapped_column(Uuid(), index=True)
    source_mode: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    media_asset: Mapped[MediaAsset] = relationship(lazy="joined")


Index("ix_media_assets_created_at_id", MediaAsset.created_at, MediaAsset.id)
