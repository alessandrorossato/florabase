import unicodedata
from datetime import datetime
from ipaddress import ip_address
from typing import Annotated, Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return None
    if any(
        unicodedata.category(character) == "Cc" and character not in {"\n", "\t"}
        for character in normalized
    ):
        raise ValueError("Value must not contain unsupported control characters")
    return normalized


def validate_https_url(value: str) -> str:
    normalized = value.strip()
    if len(normalized) > 2048:
        raise ValueError("URL must contain at most 2048 characters")
    try:
        parsed = urlsplit(normalized)
        port = parsed.port
    except ValueError as error:
        raise ValueError("URL must be an absolute HTTPS URL") from error
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or any(character.isspace() for character in normalized)
        or (port is not None and not 1 <= port <= 65535)
    ):
        raise ValueError("URL must be an absolute HTTPS URL without credentials")
    return normalized


def validate_external_cover_url(value: str) -> str:
    normalized = validate_https_url(value)
    hostname = urlsplit(normalized).hostname
    if hostname is None:
        raise ValueError("URL must have a public host")
    canonical_host = hostname.rstrip(".").lower()
    internal_suffixes = (".localhost", ".local", ".localdomain", ".internal", ".lan")
    try:
        address = ip_address(canonical_host)
    except ValueError:
        if (
            canonical_host == "localhost"
            or canonical_host.endswith(internal_suffixes)
            or "." not in canonical_host
        ):
            raise ValueError("External cover URLs must not use a local or internal host") from None
        return normalized
    if not address.is_global:
        raise ValueError("External cover URLs must not use a local or internal address")
    return normalized


class PhotoMetadataWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    caption: str | None = Field(default=None, max_length=2000)
    attribution: str | None = Field(default=None, max_length=2000)

    @field_validator("caption", "attribution", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: object) -> object:
        if value is not None and not isinstance(value, str):
            return value
        return normalize_text(value)


class LocalPhotoUpdate(PhotoMetadataWrite):
    pass


class ExternalImageWrite(PhotoMetadataWrite):
    image_url: str = Field(max_length=2048)
    source_url: str = Field(max_length=2048)
    attribution: str = Field(min_length=1, max_length=2000)

    @field_validator("image_url", "source_url", mode="before")
    @classmethod
    def normalize_url(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return validate_https_url(value)

    @field_validator("attribution", mode="before")
    @classmethod
    def require_attribution(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = normalize_text(value)
        if normalized is None:
            raise ValueError("External image attribution is required")
        return normalized


class ExternalImageCreate(ExternalImageWrite):
    pass


class ExternalImageUpdate(ExternalImageWrite):
    pass


class ExternalCoverWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_url: str = Field(max_length=2048)
    source_url: str = Field(max_length=2048)
    attribution: str = Field(min_length=1, max_length=2000)
    licence_label: str | None = Field(default=None, max_length=2000)
    licence_url: str | None = Field(default=None, max_length=2048)
    privacy_acknowledged: Literal[True]

    @field_validator("image_url", "source_url", mode="before")
    @classmethod
    def normalize_required_url(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return validate_external_cover_url(value)

    @field_validator("licence_url", mode="before")
    @classmethod
    def normalize_optional_url(cls, value: object) -> object:
        if value is None or not isinstance(value, str):
            return value
        normalized = normalize_text(value)
        return None if normalized is None else validate_external_cover_url(normalized)

    @field_validator("attribution", mode="before")
    @classmethod
    def require_attribution(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = normalize_text(value)
        if normalized is None:
            raise ValueError("External cover attribution is required")
        return normalized

    @field_validator("licence_label", mode="before")
    @classmethod
    def normalize_licence_label(cls, value: object) -> object:
        if value is not None and not isinstance(value, str):
            return value
        return normalize_text(value)


class LocalPhotoResponse(BaseModel):
    kind: Literal["local"] = "local"
    id: UUID
    attachment_id: UUID
    original_filename: str
    media_type: Literal["image/jpeg", "image/png", "image/webp"]
    caption: str | None
    attribution: str | None
    deletion_pending: bool
    content_url: str | None
    created_at: datetime
    updated_at: datetime


class ExternalImageResponse(BaseModel):
    kind: Literal["external"] = "external"
    id: UUID
    image_url: str
    source_url: str
    attribution: str
    caption: str | None
    created_at: datetime
    updated_at: datetime


class LocalCoverResponse(BaseModel):
    kind: Literal["local"] = "local"
    id: UUID
    attachment_id: UUID
    original_filename: str
    media_type: Literal["image/jpeg", "image/png", "image/webp"]
    deletion_pending: bool
    content_url: str | None
    created_at: datetime
    updated_at: datetime


class ExternalCoverResponse(BaseModel):
    kind: Literal["external"] = "external"
    id: UUID
    image_url: str
    source_url: str
    attribution: str
    licence_label: str | None
    licence_url: str | None
    created_at: datetime
    updated_at: datetime


CollectionPhotoResponse = Annotated[
    LocalPhotoResponse | ExternalImageResponse, Field(discriminator="kind")
]

BotanicalIdentityCoverResponse = Annotated[
    LocalCoverResponse | ExternalCoverResponse, Field(discriminator="kind")
]
