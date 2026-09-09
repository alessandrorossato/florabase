from enum import StrEnum
from functools import lru_cache
from typing import Self
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class LogFormat(StrEnum):
    TEXT = "text"
    JSON = "json"


class CookieMode(StrEnum):
    SECURE = "secure"
    LOOPBACK_DEVELOPMENT = "loopback-development"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FLORABASE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Environment = Environment.PRODUCTION
    database_url: str = Field(min_length=1)
    database_disposable: bool = False
    cors_origins: list[str] = Field(default_factory=list)
    canonical_origin: str | None = None
    cookie_mode: CookieMode = CookieMode.SECURE
    session_idle_seconds: int = Field(default=86_400, ge=900, le=86_400)
    session_absolute_seconds: int = Field(default=2_592_000, ge=86_400, le=2_592_000)
    session_touch_interval_seconds: int = Field(default=300, ge=60, le=3_600)
    login_failure_threshold: int = Field(default=5, ge=3, le=10)
    login_backoff_base_seconds: int = Field(default=5, ge=1, le=60)
    login_backoff_max_seconds: int = Field(default=900, ge=60, le=3_600)
    login_throttle_retention_seconds: int = Field(default=86_400, ge=3_600, le=604_800)
    log_level: str = "INFO"
    log_format: LogFormat = LogFormat.JSON
    botanical_cache_ttl_seconds: int = Field(default=86_400, ge=300, le=2_592_000)
    botanical_provider_connect_timeout_seconds: float = Field(default=3.0, ge=0.1, le=30)
    botanical_provider_read_timeout_seconds: float = Field(default=8.0, ge=0.1, le=60)

    @model_validator(mode="after")
    def validate_secure_production_settings(self) -> Self:
        if self.session_absolute_seconds <= self.session_idle_seconds:
            raise ValueError("Absolute session lifetime must exceed idle session lifetime")

        if self.canonical_origin is not None:
            parsed = urlsplit(self.canonical_origin)
            if (
                not parsed.scheme
                or not parsed.netloc
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("Canonical origin must contain only a scheme and authority")
            self.canonical_origin = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"

        if self.environment is Environment.PRODUCTION:
            if "*" in self.cors_origins:
                raise ValueError("Wildcard CORS origins are forbidden in production")
            if self.canonical_origin is None:
                raise ValueError("Canonical public origin is required in production")
            if not self.canonical_origin.startswith("https://"):
                raise ValueError("Canonical public origin must use HTTPS in production")
            if self.cookie_mode is not CookieMode.SECURE:
                raise ValueError("Production requires secure session cookies")
            if self.cors_origins:
                raise ValueError(
                    "Production authentication requires same-origin CORS configuration"
                )
        elif self.cookie_mode is CookieMode.LOOPBACK_DEVELOPMENT:
            if self.environment is not Environment.DEVELOPMENT:
                raise ValueError("Development cookie mode is only permitted in development")
            if self.canonical_origin is None:
                raise ValueError("Development cookie mode requires a canonical origin")
            parsed = urlsplit(self.canonical_origin)
            if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
                raise ValueError("Development cookie mode requires an HTTP loopback origin")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings.model_validate({})
