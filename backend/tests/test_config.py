import pytest
from pydantic import ValidationError

from florabase.core.config import CookieMode, Environment, Settings
from florabase.db.testing import require_disposable_test_database


def test_production_rejects_wildcard_cors() -> None:
    with pytest.raises(ValidationError, match="Wildcard CORS"):
        Settings.model_validate(
            {
                "environment": Environment.PRODUCTION,
                "database_url": "postgresql+psycopg://user:pass@db/database",
                "cors_origins": ["*"],
                "cookie_mode": CookieMode.SECURE,
            }
        )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({}, "Canonical public origin"),
        ({"canonical_origin": "http://florabase.example"}, "must use HTTPS"),
        (
            {
                "canonical_origin": "https://florabase.example",
                "cookie_mode": CookieMode.LOOPBACK_DEVELOPMENT,
            },
            "secure session cookies",
        ),
        (
            {
                "canonical_origin": "https://florabase.example",
                "cors_origins": ["https://other.example"],
            },
            "same-origin CORS",
        ),
    ],
)
def test_production_authentication_configuration_fails_closed(
    overrides: dict[str, object], message: str
) -> None:
    values: dict[str, object] = {
        "environment": Environment.PRODUCTION,
        "database_url": "postgresql+psycopg://user:pass@db/database",
        "cookie_mode": CookieMode.SECURE,
    }
    values.update(overrides)
    with pytest.raises(ValidationError, match=message):
        Settings.model_validate(values)


def test_loopback_development_cookie_configuration_is_explicit() -> None:
    settings = Settings.model_validate(
        {
            "environment": Environment.DEVELOPMENT,
            "database_url": "postgresql+psycopg://user:pass@db/database",
            "canonical_origin": "http://LOCALHOST:5173/",
            "cookie_mode": CookieMode.LOOPBACK_DEVELOPMENT,
        }
    )

    assert settings.canonical_origin == "http://localhost:5173"


def test_development_cookie_mode_rejects_non_loopback_origin() -> None:
    with pytest.raises(ValidationError, match="HTTP loopback"):
        Settings.model_validate(
            {
                "environment": Environment.DEVELOPMENT,
                "database_url": "postgresql+psycopg://user:pass@db/database",
                "canonical_origin": "http://dev.example",
                "cookie_mode": CookieMode.LOOPBACK_DEVELOPMENT,
            }
        )


def test_integration_guard_rejects_normal_database_configuration() -> None:
    settings = Settings.model_validate(
        {
            "environment": Environment.DEVELOPMENT,
            "database_url": "postgresql+psycopg://florabase:secret@db/florabase",
            "database_disposable": False,
            "cookie_mode": CookieMode.SECURE,
        }
    )

    with pytest.raises(RuntimeError, match="FLORABASE_DATABASE_DISPOSABLE=true"):
        require_disposable_test_database(settings)


def test_integration_guard_requires_both_safety_markers() -> None:
    test_environment_only = Settings.model_validate(
        {
            "environment": Environment.TEST,
            "database_url": "postgresql+psycopg://florabase:secret@db/florabase",
            "database_disposable": False,
            "cookie_mode": CookieMode.SECURE,
        }
    )
    disposable_only = Settings.model_validate(
        {
            "environment": Environment.DEVELOPMENT,
            "database_url": "postgresql+psycopg://florabase:secret@db/florabase",
            "database_disposable": True,
            "cookie_mode": CookieMode.SECURE,
        }
    )

    with pytest.raises(RuntimeError):
        require_disposable_test_database(test_environment_only)
    with pytest.raises(RuntimeError):
        require_disposable_test_database(disposable_only)
