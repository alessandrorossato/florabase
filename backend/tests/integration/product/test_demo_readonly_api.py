from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, func, select
from sqlalchemy.orm import Session

from florabase.auth.demo_readonly import DEMO_READONLY_CODE
from florabase.auth.model import AuthSession
from florabase.auth.service import bootstrap_owner
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.core.config import CookieMode, Environment, Settings, get_settings
from florabase.db.session import get_database_session
from florabase.main import create_app

pytestmark = pytest.mark.integration

ORIGIN = "https://demo.florabase.eu"
PASSWORD = "correct horse battery staple"


def _demo_settings() -> Settings:
    return Settings.model_validate(
        {
            "environment": Environment.PRODUCTION,
            "database_url": "postgresql+psycopg://unused",
            "canonical_origin": ORIGIN,
            "cors_origins": [],
            "cookie_mode": CookieMode.SECURE,
            "demo_readonly": True,
        }
    )


def test_demo_readonly_allows_unauthenticated_reads_and_blocks_all_writes(
    database_connection: Connection,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        bootstrap_owner(database, "demo", PASSWORD, "Demo Collection")
        database.add(
            BotanicalIdentity(
                scientific_name="Aloe dichotoma",
                common_name="Quiver tree",
            )
        )
        database.flush()

        settings = _demo_settings()
        with patch("florabase.main.get_settings", return_value=settings):
            app = create_app()
        app.dependency_overrides[get_settings] = lambda: settings
        app.dependency_overrides[get_database_session] = lambda: database

        with TestClient(app, base_url=ORIGIN) as client:
            session_resp = client.get("/api/v1/auth/session")
            assert session_resp.status_code == 200
            assert session_resp.json()["demo_readonly"] is True
            assert session_resp.json()["login_name"] == "demo"

            identities_resp = client.get("/api/v1/botanical-identities")
            assert identities_resp.status_code == 200
            names = [item["scientific_name"] for item in identities_resp.json()]
            assert "Aloe dichotoma" in names

            # No auth_sessions rows created by browsing the demo.
            session_count = database.scalar(select(func.count()).select_from(AuthSession))
            assert session_count == 0

            # Mutating API calls are blocked with 403 demo_read_only.
            for method, path, payload in (
                (
                    "POST",
                    "/api/v1/botanical-identities",
                    {"scientific_name": "Agave americana"},
                ),
                (
                    "POST",
                    "/api/v1/auth/password",
                    {"current_password": PASSWORD, "new_password": "new password 12345"},
                ),
                (
                    "POST",
                    "/api/v1/auth/device-sessions",
                    {"login_name": "demo", "password": PASSWORD, "device_label": "Phone"},
                ),
            ):
                blocked = client.request(
                    method,
                    path,
                    json=payload,
                    headers={"Origin": ORIGIN},
                )
                assert blocked.status_code == 403
                assert blocked.json()["detail"]["code"] == DEMO_READONLY_CODE

            # Verify no identity was created.
            identity_count = database.scalar(select(func.count()).select_from(BotanicalIdentity))
            assert identity_count == 1
