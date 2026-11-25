from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, TypeAdapter, field_validator

from florabase.collection_photos.schemas import normalize_text, validate_https_url

LabelPreset = Literal["small", "medium", "large"]


class ApplicationSettingsValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    public_qr_base_url: str | None
    default_label_preset: LabelPreset
    # Pre-checks "Save a local copy"; each fetch still needs the owner's explicit save.
    media_save_local_copy_default: bool
    # Prefill only for the owner's own uploads; external images keep their author's credit.
    media_default_attribution: str | None = Field(max_length=2000)
    media_default_licence_label: str | None = Field(max_length=2000)
    media_default_licence_url: str | None = Field(max_length=2048)

    @field_validator("media_default_attribution", "media_default_licence_label", mode="before")
    @classmethod
    def optional_text(cls, value: object) -> object:
        return normalize_text(value) if isinstance(value, str) else value

    @field_validator("media_default_licence_url", mode="before")
    @classmethod
    def optional_licence_url(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = normalize_text(value)
            return validate_https_url(normalized) if normalized else None
        return value

    @field_validator("public_qr_base_url")
    @classmethod
    def validate_public_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value or len(value) > 200 or any(c.isspace() or ord(c) < 32 for c in value):
            raise ValueError(
                "Public QR base URL must be an HTTP(S) origin of at most 200 characters"
            )
        parsed = urlsplit(value)
        if (
            not parsed.netloc
            or "\\" in value
            or parsed.path not in {"", "/"}
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise ValueError("Public QR base URL requires a scheme and authority")
        url = TypeAdapter(HttpUrl).validate_python(value)
        if (
            "://" not in value
            or url.username is not None
            or url.password is not None
            or url.path not in {None, "/"}
            or "?" in value
            or "#" in value
        ):
            raise ValueError(
                "Use only a scheme and authority, without credentials, path, query or fragment"
            )
        normalized = str(url).removesuffix("/")
        if len(normalized) > 200:
            raise ValueError("Public QR base URL is too long")
        return normalized
