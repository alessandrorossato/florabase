import unicodedata
from datetime import datetime
from typing import TYPE_CHECKING, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from florabase.botanical_identities.model import BotanicalIdentity


def _collapse_whitespace(value: str) -> str:
    return " ".join(value.split())


def _contains_control_character(value: str) -> bool:
    return any(unicodedata.category(character) == "Cc" for character in value)


def _normalize_required(value: str) -> str:
    normalized = _collapse_whitespace(value)
    if not normalized:
        raise ValueError("Value must not be blank")
    if _contains_control_character(normalized):
        raise ValueError("Value must not contain control characters")
    return normalized


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _collapse_whitespace(value)
    if not normalized:
        return None
    if _contains_control_character(normalized):
        raise ValueError("Value must not contain control characters")
    return normalized


def _normalize_cultivar(value: str | None) -> str | None:
    normalized = _normalize_optional(value)
    if normalized is None or len(normalized) < 2:
        return normalized
    quote_pairs = {
        ("'", "'"),
        ('"', '"'),
        ("\u2018", "\u2019"),
        ("\u201c", "\u201d"),
    }
    if (normalized[0], normalized[-1]) in quote_pairs:
        return _normalize_optional(normalized[1:-1])
    return normalized


class BotanicalIdentityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scientific_name: str = Field(max_length=255)
    cultivar_name: str | None = Field(default=None, max_length=120)
    common_name: str | None = Field(default=None, max_length=160)

    @field_validator("scientific_name", mode="before")
    @classmethod
    def normalize_scientific_name(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return _normalize_required(value)

    @field_validator("cultivar_name", mode="before")
    @classmethod
    def normalize_cultivar_name(cls, value: object) -> object:
        if value is not None and not isinstance(value, str):
            return value
        return _normalize_cultivar(value)

    @field_validator("common_name", mode="before")
    @classmethod
    def normalize_common_name(cls, value: object) -> object:
        if value is not None and not isinstance(value, str):
            return value
        return _normalize_optional(value)


class BotanicalIdentityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scientific_name: str
    cultivar_name: str | None
    common_name: str | None
    created_at: datetime
    updated_at: datetime
    display_label: str

    @classmethod
    def from_model(cls, botanical_identity: BotanicalIdentity) -> Self:
        display_label = botanical_identity.scientific_name
        if botanical_identity.cultivar_name is not None:
            display_label = (
                f"{botanical_identity.scientific_name} "
                f"\u2018{botanical_identity.cultivar_name}\u2019"
            )
        return cls.model_validate(
            {
                "id": botanical_identity.id,
                "scientific_name": botanical_identity.scientific_name,
                "cultivar_name": botanical_identity.cultivar_name,
                "common_name": botanical_identity.common_name,
                "created_at": botanical_identity.created_at,
                "updated_at": botanical_identity.updated_at,
                "display_label": display_label,
            }
        )
