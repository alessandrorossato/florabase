from florabase.core.config import Environment, Settings


def require_disposable_test_database(settings: Settings) -> None:
    if settings.environment is not Environment.TEST or not settings.database_disposable:
        raise RuntimeError(
            "Integration tests require both FLORABASE_ENVIRONMENT=test and "
            "FLORABASE_DATABASE_DISPOSABLE=true"
        )
