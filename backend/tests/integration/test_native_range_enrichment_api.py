import json
import sqlite3
from pathlib import Path
from uuid import uuid7

import pytest
from sqlalchemy import Connection, select
from sqlalchemy.orm import Session

from florabase.main import app
from florabase.native_range_enrichment.api import source_dependency
from florabase.native_range_enrichment.model import NativeRangeApplication
from florabase.native_range_enrichment.source import ARCHIVE_SHA256, WcvpSource

from .test_botanical_profile_api import authenticated_browser as authenticated_browser
from .test_botanical_profile_api import identity_id as identity_id
from .test_botanical_profile_api import request
from .test_native_range_enrichment import source as source

pytestmark = pytest.mark.integration


def test_authenticated_proposal_flow_and_security(
    authenticated_browser: tuple[str, str],
    identity_id: object,
    source: WcvpSource,
    database_connection: Connection,
) -> None:
    path = f"/api/v1/botanical-identities/{identity_id}/native-range-enrichment"
    cookie, csrf = authenticated_browser
    headers = {"cookie": cookie, "origin": "https://florabase.example", "x-csrf-token": csrf}
    app.dependency_overrides[source_dependency] = lambda: source
    assert request("GET", path + "/source")[0] == 401
    assert request("GET", path + "/source", headers={"cookie": cookie})[2]["available"]
    for missing in (
        {},
        {"cookie": cookie},
        {"cookie": cookie, "origin": "https://evil.example", "x-csrf-token": csrf},
    ):
        assert request(
            "PUT",
            path + "/link",
            headers=missing,
            body={"external_id": "100", "checksum": ARCHIVE_SHA256},
        )[0] in {401, 403}
    assert (
        request(
            "PUT",
            path + "/link",
            headers=headers,
            body={"external_id": "100", "checksum": "0" * 64},
        )[0]
        == 409
    )
    assert (
        request(
            "PUT",
            path + "/link",
            headers=headers,
            body={"external_id": "100", "checksum": ARCHIVE_SHA256},
        )[0]
        == 200
    )
    code, _, proposal = request("POST", path + "/proposals", headers=headers)
    assert code == 201
    assert len(request("GET", path + "/proposals", headers={"cookie": cookie})[2]) == 1
    selected = next(c["place_id"] for c in proposal["choices"] if c["code"] == "BO")
    apply_path = path + f"/proposals/{proposal['id']}/apply"
    assert (
        request(
            "POST", apply_path, headers=headers, body={"selected_place_ids": [selected, selected]}
        )[0]
        == 422
    )
    assert request("POST", apply_path, headers=headers, body={"selected_place_ids": []})[0] == 422
    assert (
        request(
            "POST",
            apply_path,
            headers=headers,
            body={"selected_place_ids": [selected], "remove": [selected]},
        )[0]
        == 422
    )
    assert (
        request("POST", apply_path, headers=headers, body={"selected_place_ids": [selected]})[0]
        == 200
    )
    assert (
        request("POST", apply_path, headers=headers, body={"selected_place_ids": [selected]})[0]
        == 409
    )
    assert request("GET", path + "/proposals/" + str(uuid7()), headers={"cookie": cookie})[0] == 404
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        assert len(list(database.scalars(select(NativeRangeApplication)))) == 1


def test_missing_snapshot_status_is_retryable(
    authenticated_browser: tuple[str, str], identity_id: object, tmp_path: Path
) -> None:
    path = f"/api/v1/botanical-identities/{identity_id}/native-range-enrichment"
    app.dependency_overrides[source_dependency] = lambda: WcvpSource(tmp_path / "missing")
    cookie, csrf = authenticated_browser
    assert request("GET", path + "/source", headers={"cookie": cookie})[2]["available"] is False
    assert (
        request(
            "POST",
            path + "/proposals",
            headers={"cookie": cookie, "origin": "https://florabase.example", "x-csrf-token": csrf},
        )[0]
        == 503
    )


def test_reprovisioned_source_marks_confirmed_link_stale(
    authenticated_browser: tuple[str, str], identity_id: object, source: WcvpSource
) -> None:
    path = f"/api/v1/botanical-identities/{identity_id}/native-range-enrichment"
    cookie, csrf = authenticated_browser
    headers = {"cookie": cookie, "origin": "https://florabase.example", "x-csrf-token": csrf}
    app.dependency_overrides[source_dependency] = lambda: source
    assert (
        request(
            "PUT",
            path + "/link",
            headers=headers,
            body={"external_id": "100", "checksum": ARCHIVE_SHA256},
        )[0]
        == 200
    )
    assert source.path is not None
    metadata = source.metadata().model_dump()
    metadata["retrieved_at"] = "2026-10-10T00:00:00Z"
    with sqlite3.connect(source.path) as connection:
        connection.execute("UPDATE metadata SET payload=?", (json.dumps(metadata),))
    status = request("GET", path + "/source", headers={"cookie": cookie})[2]
    assert status["available"] is True
    assert status["link"]["stale"] is True
    assert request("POST", path + "/proposals", headers=headers)[0] == 409
