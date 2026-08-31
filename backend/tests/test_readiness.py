from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import OperationalError

from florabase.api.health import database_readiness


def test_readiness_reports_database_failure_without_leaking_details() -> None:
    error = OperationalError("SELECT 1", {}, RuntimeError("secret connection detail"))
    with (
        patch("florabase.api.health.check_database", side_effect=error),
        pytest.raises(HTTPException) as raised,
    ):
        database_readiness()

    assert raised.value.status_code == 503
    assert raised.value.detail == "Database unavailable"
