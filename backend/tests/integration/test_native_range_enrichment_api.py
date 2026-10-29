import json
import sqlite3
from pathlib import Path
from typing import Any
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


@pytest.mark.parametrize("installed", [(), ("15",), ("16",), ("15", "16")])
def test_explicit_release_http_configuration(
    authenticated_browser: tuple[str, str],
    identity_id: object,
    source: WcvpSource,
    tmp_path: Path,
    installed: tuple[str, ...],
) -> None:
    import asyncio

    import httpx

    from florabase.core.config import get_settings
    from florabase.native_range_enrichment.snapshot import (
        DISTRIBUTION_FIELDS,
        NAMES_FIELDS,
        build_index,
    )
    from florabase.native_range_enrichment.source import RELEASES, SourceMetadata

    from .test_botanical_profile_api import settings

    def release_request(
        method: str, url: str, *, headers: dict[str, str], body: dict[str, str] | None = None
    ) -> tuple[int, httpx.Headers, Any]:
        async def send() -> tuple[int, httpx.Headers, Any]:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="https://florabase.example"
            ) as client:
                response = await client.request(method, url, headers=headers, json=body)
                return response.status_code, response.headers, response.json()

        return asyncio.run(send())

    path16 = tmp_path / "v16.sqlite"
    names = [
        dict.fromkeys(NAMES_FIELDS, "")
        | {
            "plant_name_id": "100",
            "taxon_name": "Fixture species",
            "taxon_rank": "Species",
            "taxon_status": "Accepted",
            "accepted_plant_name_id": "100",
        }
    ]
    rows = [
        dict.fromkeys(DISTRIBUTION_FIELDS, "")
        | {
            "plant_locality_id": "1",
            "plant_name_id": "100",
            "area_code_l3": "BOL",
            "introduced": "0",
            "extinct": "0",
            "location_doubtful": "0",
        }
    ]
    build_index(path16, names, rows, SourceMetadata.for_release("16", "2026-10-28T00:00:00Z"))
    chosen = settings().model_copy(
        update={
            "wcvp_snapshot_path": source.path if "15" in installed else None,
            "wcvp_v16_snapshot_path": path16 if "16" in installed else None,
        }
    )
    app.dependency_overrides[get_settings] = lambda: chosen
    path = f"/api/v1/botanical-identities/{identity_id}/native-range-enrichment"
    cookie, csrf = authenticated_browser
    headers = {"cookie": cookie, "origin": "https://florabase.example", "x-csrf-token": csrf}
    assert release_request("GET", path + "/source", headers=headers)[2]["available"] == (
        "15" in installed
    )
    assert release_request("GET", path + "/source?version=17", headers=headers)[0] == 422
    for version in ("15", "16"):
        query = f"?version={version}"
        status = release_request("GET", path + "/source" + query, headers=headers)[2]
        assert status["available"] == (version in installed)
        code, _, candidates = release_request(
            "GET", path + f"/taxa?q=Fixture&version={version}", headers=headers
        )
        assert code == (200 if version in installed else 503)
        if version not in installed:
            continue
        assert candidates[0]["external_id"] == "100"
        assert (
            release_request(
                "PUT",
                path + "/link" + query,
                headers=headers,
                body={
                    "external_id": "100",
                    "checksum": RELEASES[version].checksum,
                },
            )[2]["source"]["version"]
            == version
        )
        code, _, proposal = release_request("POST", path + "/proposals" + query, headers=headers)
        assert code == 201
        assert proposal["source"]["version"] == version
        assert proposal["crosswalk_version"] == RELEASES[version].crosswalk_version
