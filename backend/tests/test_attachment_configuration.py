from pathlib import Path

import pytest
from pydantic import ValidationError

from florabase.core.config import CookieMode, Environment, Settings


def configured_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "environment": Environment.TEST,
        "database_url": "postgresql+psycopg://unused",
        "attachment_storage_root": "/var/lib/florabase/attachments",
        "canonical_origin": None,
        "cookie_mode": CookieMode.SECURE,
        "cors_origins": [],
    }
    values.update(overrides)
    return Settings.model_validate(values)


def test_attachment_configuration_is_absolute_bounded_and_not_root() -> None:
    settings = configured_settings()
    assert settings.attachment_max_bytes == 25 * 1024 * 1024
    assert settings.attachment_storage_root == Path("/var/lib/florabase/attachments")
    for root in ("relative/attachments", "/", "/safe/../escape"):
        with pytest.raises(ValidationError, match="Attachment storage root"):
            configured_settings(attachment_storage_root=root)
    with pytest.raises(ValidationError):
        configured_settings(attachment_max_bytes=25 * 1024 * 1024 + 1)
