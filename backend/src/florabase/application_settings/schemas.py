from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, HttpUrl, TypeAdapter, field_validator

LabelPreset = Literal["small", "medium", "large"]


class ApplicationSettingsValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    public_qr_base_url: str | None
    default_label_preset: LabelPreset

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
