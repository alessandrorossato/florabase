from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from florabase.collection_photos.schemas import normalize_text, validate_https_url

MediaTarget = Literal["seed_lot", "sowing", "plant", "plant_group", "event"]


class AssetMetadataWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, max_length=2000)
    attribution: str | None = Field(default=None, max_length=2000)
    licence_label: str | None = Field(default=None, max_length=2000)
    licence_url: str | None = Field(default=None, max_length=2048)

    @field_validator("title", "attribution", "licence_label", mode="before")
    @classmethod
    def optional_text(cls, value: object) -> object:
        return normalize_text(value) if isinstance(value, str) else value

    @field_validator("licence_url", mode="before")
    @classmethod
    def optional_url(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = normalize_text(value)
            return validate_https_url(normalized) if normalized else None
        return value


class ExternalAssetCreate(AssetMetadataWrite):
    image_url: str = Field(max_length=2048)
    source_url: str = Field(max_length=2048)
    attribution: str = Field(min_length=1, max_length=2000)

    @field_validator("image_url", "source_url", mode="before")
    @classmethod
    def required_url(cls, value: object) -> object:
        return validate_https_url(value) if isinstance(value, str) else value


class LinkWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    caption: str | None = Field(default=None, max_length=2000)
    display_order: int = Field(default=0, ge=0, le=2147483647)

    @field_validator("caption", mode="before")
    @classmethod
    def caption_text(cls, value: object) -> object:
        return normalize_text(value) if isinstance(value, str) else value


class LinkCreate(LinkWrite):
    media_asset_id: UUID


class AssetResponse(BaseModel):
    id: UUID
    kind: Literal["local", "external"]
    title: str | None
    attribution: str | None
    licence_label: str | None
    licence_url: str | None
    image_url: str | None
    source_url: str | None
    original_filename: str | None
    media_type: str | None
    byte_size: int | None
    width: int | None
    height: int | None
    fetched_at: datetime | None = None
    local_copy_cleanup_pending: bool = False
    deletion_pending: bool
    content_url: str | None
    thumbnail_url: str | None
    collection_link_count: int
    cover_reference_count: int
    can_delete: bool
    created_at: datetime
    updated_at: datetime


class LinkResponse(LinkWrite):
    id: UUID
    media_asset_id: UUID
    target_type: MediaTarget
    target_id: UUID
    target_label: str
    target_url: str
    is_primary: bool
    created_at: datetime
    updated_at: datetime


class CoverReferenceResponse(BaseModel):
    id: UUID
    botanical_identity_id: UUID
    label: str
    url: str


class AssetDetailResponse(AssetResponse):
    links: list[LinkResponse]
    covers: list[CoverReferenceResponse]


class AssetPageResponse(BaseModel):
    items: list[AssetResponse]
    total: int
    limit: int
    offset: int


class TargetChoiceResponse(BaseModel):
    id: UUID
    label: str


class TargetPageResponse(BaseModel):
    items: list[TargetChoiceResponse]
    total: int
    limit: int
    offset: int
