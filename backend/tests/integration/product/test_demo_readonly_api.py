from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid7

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, func, select
from sqlalchemy.orm import Session

from florabase.auth.demo_readonly import (
    DEMO_EXTERNAL_LOOKUP_DISABLED_CODE,
    DEMO_MARKER_FILENAME,
    DEMO_MARKER_TOKEN,
    DEMO_READONLY_CODE,
    DEMO_VISITOR_DISPLAY_NAME,
    EPHEMERAL_DEMO_SESSION_ID,
    DemoMarkerError,
)
from florabase.auth.model import AuthSession
from florabase.auth.service import bootstrap_owner
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.core.config import CookieMode, Environment, Settings, get_settings
from florabase.db.session import get_database_session
from florabase.external_botany.api import get_provider
from florabase.external_botany.model import ExternalProviderCache, ExternalTaxonLink
from florabase.main import create_app

pytestmark = pytest.mark.integration

ORIGIN = "https://demo.example.org"
PASSWORD = "correct horse battery staple"


def _demo_settings(storage_root: Path) -> Settings:
    return Settings.model_validate(
        {
            "environment": Environment.PRODUCTION,
            "database_url": "postgresql+psycopg://unused",
            "canonical_origin": ORIGIN,
            "cors_origins": [],
            "cookie_mode": CookieMode.SECURE,
            "attachment_storage_root": str(storage_root),
            "references_setup": "off",
            "demo_readonly": True,
        }
    )


def test_demo_readonly_allows_unauthenticated_reads_and_blocks_all_writes(
    database_connection: Connection,
    tmp_path: Path,
) -> None:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        bootstrap_owner(database, "golden-owner", PASSWORD, "Golden Owner")
        identity = BotanicalIdentity(
            scientific_name="Aloe dichotoma",
            common_name="Quiver tree",
        )
        database.add(identity)
        database.flush()
        now = datetime.now(UTC)
        database.add(
            ExternalTaxonLink(
                id=uuid7(),
                botanical_identity_id=identity.id,
                provider="gbif",
                external_id="2777724",
                scientific_name="Aloe dichotoma",
                canonical_name="Aloe dichotoma",
                rank="SPECIES",
                taxonomic_status="ACCEPTED",
                last_refreshed_at=now,
                last_refresh_attempt_at=now,
            )
        )
        database.flush()

        settings = _demo_settings(tmp_path)
        with patch("florabase.main.get_settings", return_value=settings):
            app = create_app()
        app.dependency_overrides[get_settings] = lambda: settings
        app.dependency_overrides[get_database_session] = lambda: database

        # Without the explicit demo marker, startup must refuse.
        with pytest.raises(DemoMarkerError), TestClient(app, base_url=ORIGIN):
            pass

        # Write the explicit demo marker and verify full read-only + cache-only guarantees.
        (tmp_path / DEMO_MARKER_FILENAME).write_text(f"{DEMO_MARKER_TOKEN}\n", encoding="ascii")

        provider = MagicMock()
        provider.provider_id = "gbif"
        provider.search_payload = AsyncMock()
        provider.occurrence_summary = AsyncMock()
        provider.occurrence_tile = AsyncMock()
        app.dependency_overrides[get_provider] = lambda: provider

        with TestClient(app, base_url=ORIGIN) as client:
            session_resp = client.get("/api/v1/auth/session")
            assert session_resp.status_code == 200
            assert session_resp.json() == {
                "user_id": str(EPHEMERAL_DEMO_SESSION_ID),
                "login_name": "",
                "display_name": DEMO_VISITOR_DISPLAY_NAME,
                "owner": False,
                "canonical_origin": ORIGIN,
                "demo_readonly": True,
            }

            devices_resp = client.get("/api/v1/auth/device-sessions")
            assert devices_resp.status_code == 200
            assert devices_resp.json() == {"items": []}

            identities_resp = client.get("/api/v1/botanical-identities")
            assert identities_resp.status_code == 200
            names = [item["scientific_name"] for item in identities_resp.json()]
            assert "Aloe dichotoma" in names

            # External GET routes are cache-only: zero outbound GBIF calls, zero DB/disk writes.
            search_resp = client.get(
                f"/api/v1/botanical-identities/{identity.id}/external-taxa/search?query=Aloe"
            )
            assert search_resp.status_code == 403
            assert search_resp.json()["detail"]["code"] == DEMO_EXTERNAL_LOOKUP_DISABLED_CODE
            provider.search_payload.assert_not_awaited()

            summary_resp = client.get(
                f"/api/v1/botanical-identities/{identity.id}/occurrence-map/summary"
            )
            assert summary_resp.status_code == 403
            assert summary_resp.json()["detail"]["code"] == DEMO_EXTERNAL_LOOKUP_DISABLED_CODE
            provider.occurrence_summary.assert_not_awaited()

            tile_resp = client.get(
                f"/api/v1/botanical-identities/{identity.id}/occurrence-map/tiles/2/1/1.png"
            )
            assert tile_resp.status_code == 404
            assert tile_resp.json()["detail"]["code"] == "occurrence_tile_not_cached"
            provider.occurrence_tile.assert_not_awaited()

            assert database.scalar(select(func.count()).select_from(ExternalProviderCache)) == 0
            assert database.scalar(select(func.count()).select_from(AuthSession)) == 0
            assert sorted(path for path in tmp_path.rglob("*") if path.is_file()) == [
                tmp_path / DEMO_MARKER_FILENAME
            ]

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
                    {"login_name": "golden-owner", "password": PASSWORD, "device_label": "Phone"},
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

            assert database.scalar(select(func.count()).select_from(BotanicalIdentity)) == 1
