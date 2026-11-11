import asyncio
import json
from collections.abc import Iterator, Mapping
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from queue import Queue
from time import monotonic, sleep
from typing import Any, cast
from uuid import UUID, uuid7

import pytest
from sqlalchemy import Connection, Engine, func, select, text
from sqlalchemy.orm import Session
from starlette.types import Message, Receive, Scope, Send

from florabase.auth.dependencies import AuthenticatedActor, require_csrf
from florabase.auth.model import AuthSession, User
from florabase.auth.service import bootstrap_owner
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_identities.schemas import OperatorSynonymCreate
from florabase.botanical_identities.service import (
    SynonymValidationError,
    add_operator_synonym,
    list_identity_synonyms,
)
from florabase.core.config import CookieMode, Environment, Settings, get_settings
from florabase.db.session import get_database_session
from florabase.main import app

pytestmark = pytest.mark.integration

PASSWORD = "correct horse battery staple"
ORIGIN = "https://florabase.example"


def settings() -> Settings:
    return Settings.model_validate(
        {
            "environment": Environment.TEST,
            "database_url": "postgresql+psycopg://unused",
            "canonical_origin": ORIGIN,
            "cookie_mode": CookieMode.SECURE,
        }
    )


def override_database(connection: Connection) -> Iterator[Session]:
    with Session(bind=connection, join_transaction_mode="create_savepoint") as database:
        try:
            yield database
            database.commit()
        except Exception:
            database.rollback()
            raise


async def asgi_request(
    method: str,
    path: str,
    *,
    body: Mapping[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], Any]:
    raw_body = json.dumps(body).encode() if body is not None else b""
    raw_headers = [(b"content-type", b"application/json")]
    raw_headers.extend(
        (name.lower().encode("ascii"), value.encode("ascii"))
        for name, value in (headers or {}).items()
    )
    response_status = 0
    response_headers: dict[str, str] = {}
    response_body = bytearray()
    request_sent = False

    async def receive() -> Message:
        nonlocal request_sent
        if request_sent:
            return {"type": "http.disconnect"}
        request_sent = True
        return {"type": "http.request", "body": raw_body, "more_body": False}

    async def send(message: Message) -> None:
        nonlocal response_status
        if message["type"] == "http.response.start":
            response_status = cast(int, message["status"])
            response_headers.update(
                (name.decode("latin-1"), value.decode("latin-1"))
                for name, value in message["headers"]
            )
        elif message["type"] == "http.response.body":
            response_body.extend(message.get("body", b""))

    path_only, _, query_str = path.partition("?")
    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "https",
        "path": path_only,
        "raw_path": path_only.encode("ascii"),
        "query_string": query_str.encode("ascii"),
        "headers": raw_headers,
        "client": ("127.0.0.1", 1234),
        "server": ("florabase.example", 443),
    }
    await app(scope, cast(Receive, receive), cast(Send, send))
    decoded = json.loads(response_body) if response_body else None
    return response_status, response_headers, decoded


def request(
    method: str,
    path: str,
    *,
    body: Mapping[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], Any]:
    return asyncio.run(asgi_request(method, path, body=body, headers=headers))


@pytest.fixture
def authenticated_browser(database_connection: Connection) -> Iterator[tuple[str, str]]:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        bootstrap_owner(database, "owner", PASSWORD, "Florabase Owner")
        database.commit()

    def database_override() -> Iterator[Session]:
        yield from override_database(database_connection)

    app.dependency_overrides[get_database_session] = database_override
    app.dependency_overrides[get_settings] = settings
    status_code, response_headers, body = request(
        "POST",
        "/api/v1/auth/login",
        body={"login_name": "owner", "password": PASSWORD},
        headers={"origin": ORIGIN},
    )
    assert status_code == 200
    cookie = response_headers["set-cookie"].split(";", 1)[0]
    try:
        yield cookie, body["csrf_token"]
    finally:
        app.dependency_overrides.clear()


def create_identity(
    browser: tuple[str, str], payload: Mapping[str, object]
) -> tuple[int, dict[str, str], Any]:
    cookie, csrf_token = browser
    return request(
        "POST",
        "/api/v1/botanical-identities",
        body=payload,
        headers={"cookie": cookie, "origin": ORIGIN, "x-csrf-token": csrf_token},
    )


def test_csrf_recovery_endpoint_rotates_only_csrf_and_enforces_session_origin(
    authenticated_browser: tuple[str, str], database_connection: Connection
) -> None:
    cookie, previous_csrf = authenticated_browser
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        persisted_before = database.scalars(select(AuthSession)).one()
        session_id = persisted_before.id
        session_digest = persisted_before.token_digest

    status_code, headers, body = request(
        "POST",
        "/api/v1/auth/csrf",
        headers={"cookie": cookie, "origin": ORIGIN},
    )
    assert status_code == 200
    assert headers["cache-control"] == "no-store"
    assert "set-cookie" not in headers
    assert set(body) == {"csrf_token"}
    new_csrf = body["csrf_token"]
    assert new_csrf != previous_csrf

    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        persisted_after = database.get(AuthSession, session_id)
        assert persisted_after is not None
        assert persisted_after.token_digest == session_digest

    old_status, _, _ = request(
        "POST",
        "/api/v1/botanical-identities",
        body={"scientific_name": "Acer palmatum"},
        headers={"cookie": cookie, "origin": ORIGIN, "x-csrf-token": previous_csrf},
    )
    assert old_status == 403
    new_status, _, _ = request(
        "POST",
        "/api/v1/botanical-identities",
        body={"scientific_name": "Acer palmatum"},
        headers={"cookie": cookie, "origin": ORIGIN, "x-csrf-token": new_csrf},
    )
    assert new_status == 201

    for invalid_cookie in (None, "__Host-florabase-session=invalid"):
        request_headers = {"origin": ORIGIN}
        if invalid_cookie is not None:
            request_headers["cookie"] = invalid_cookie
        invalid_status, _, invalid_body = request(
            "POST", "/api/v1/auth/csrf", headers=request_headers
        )
        assert invalid_status == 401
        assert invalid_body["detail"] == "Authentication required"

    for invalid_origin in (None, "https://evil.example"):
        request_headers = {"cookie": cookie}
        if invalid_origin is not None:
            request_headers["origin"] = invalid_origin
        invalid_status, _, invalid_body = request(
            "POST", "/api/v1/auth/csrf", headers=request_headers
        )
        assert invalid_status == 403
        assert invalid_body["detail"] == "Request forbidden"


def test_authenticated_owner_creates_and_reads_normalized_identity(
    authenticated_browser: tuple[str, str],
) -> None:
    status_code, headers, body = create_identity(
        authenticated_browser,
        {
            "scientific_name": "  Acer\tpalmatum ",
            "cultivar_name": " “Bloodgood” ",
            "common_name": " Japanese   maple ",
        },
    )

    identity_id = UUID(body["id"])
    assert status_code == 201
    assert identity_id.version == 7
    assert headers["location"] == f"/api/v1/botanical-identities/{identity_id}"
    assert body["scientific_name"] == "Acer palmatum"
    assert body["cultivar_name"] == "Bloodgood"
    assert body["common_name"] == "Japanese maple"
    assert body["display_label"] == "Acer palmatum \u2018Bloodgood\u2019"
    assert datetime.fromisoformat(body["created_at"]).utcoffset() is not None
    assert datetime.fromisoformat(body["updated_at"]).utcoffset() is not None

    cookie, _ = authenticated_browser
    read_status, _, read_body = request(
        "GET", f"/api/v1/botanical-identities/{identity_id}", headers={"cookie": cookie}
    )
    assert read_status == 200
    assert read_body == body


def test_optional_blanks_normalize_to_null(
    authenticated_browser: tuple[str, str],
) -> None:
    status_code, _, body = create_identity(
        authenticated_browser,
        {"scientific_name": "Solanum quitoense", "cultivar_name": " ", "common_name": "\t"},
    )
    assert status_code == 201
    assert body["cultivar_name"] is None
    assert body["common_name"] is None
    assert body["display_label"] == "Solanum quitoense"


def test_identity_update_and_guarded_delete_preserve_collection_records(
    authenticated_browser: tuple[str, str],
) -> None:
    cookie, csrf_token = authenticated_browser
    headers = {"cookie": cookie, "origin": ORIGIN, "x-csrf-token": csrf_token}
    _, _, unused = create_identity(authenticated_browser, {"scientific_name": "Acer japonicum"})
    _, _, referenced = create_identity(authenticated_browser, {"scientific_name": "Acer palmatum"})

    update_status, _, updated = request(
        "PUT",
        f"/api/v1/botanical-identities/{unused['id']}",
        body={
            "scientific_name": "Acer japonicum",
            "cultivar_name": "Aconitifolium",
            "common_name": "Fullmoon maple",
        },
        headers=headers,
    )
    assert update_status == 200
    assert updated["display_label"] == "Acer japonicum \u2018Aconitifolium\u2019"

    seed_status, _, seed_lot = request(
        "POST",
        "/api/v1/seed-lots",
        body={"botanical_identity_id": referenced["id"]},
        headers=headers,
    )
    assert seed_status == 201
    referenced_status, _, conflict = request(
        "DELETE",
        f"/api/v1/botanical-identities/{referenced['id']}",
        headers=headers,
    )
    assert referenced_status == 409
    assert conflict["detail"]["code"] == "botanical_identity_referenced"
    assert (
        request("GET", f"/api/v1/seed-lots/{seed_lot['id']}", headers={"cookie": cookie})[0] == 200
    )

    assert (
        request(
            "DELETE",
            f"/api/v1/botanical-identities/{unused['id']}",
            headers=headers,
        )[0]
        == 204
    )
    assert (
        request("GET", f"/api/v1/botanical-identities/{unused['id']}", headers={"cookie": cookie})[
            0
        ]
        == 404
    )


def test_authenticated_directory_is_empty_safe_and_does_not_mutate(
    authenticated_browser: tuple[str, str], database_connection: Connection
) -> None:
    cookie, _ = authenticated_browser
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        count_before = database.scalar(select(func.count()).select_from(BotanicalIdentity))

    status_code, _, body = request(
        "GET", "/api/v1/botanical-identities", headers={"cookie": cookie}
    )

    assert status_code == 200
    assert body == []
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        count_after = database.scalar(select(func.count()).select_from(BotanicalIdentity))
    assert count_after == count_before == 0

    unauthenticated_status, _, unauthenticated_body = request("GET", "/api/v1/botanical-identities")
    assert unauthenticated_status == 401
    assert unauthenticated_body["detail"] == "Authentication required"


def test_directory_returns_created_identities_in_deterministic_botanical_order(
    authenticated_browser: tuple[str, str], database_connection: Connection
) -> None:
    created = {}
    for payload in (
        {"scientific_name": "Solanum quitoense", "cultivar_name": "Zulu"},
        {"scientific_name": "acer palmatum", "common_name": "Japanese maple"},
        {"scientific_name": "Solanum quitoense", "cultivar_name": "alba"},
        {"scientific_name": "Solanum quitoense"},
        {"scientific_name": "Annona cherimola"},
    ):
        status_code, _, body = create_identity(authenticated_browser, payload)
        assert status_code == 201
        created[body["display_label"]] = body["id"]

    cookie, _ = authenticated_browser
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        persisted_before = list(database.scalars(select(BotanicalIdentity)))
    status_code, _, body = request(
        "GET", "/api/v1/botanical-identities", headers={"cookie": cookie}
    )

    assert status_code == 200
    assert [item["display_label"] for item in body] == [
        "acer palmatum",
        "Annona cherimola",
        "Solanum quitoense",
        "Solanum quitoense \u2018alba\u2019",
        "Solanum quitoense \u2018Zulu\u2019",
    ]
    assert [item["id"] for item in body] == [created[item["display_label"]] for item in body]
    assert body[0]["common_name"] == "Japanese maple"
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        persisted_after = list(database.scalars(select(BotanicalIdentity)))
    assert [(item.id, item.updated_at) for item in persisted_after] == [
        (item.id, item.updated_at) for item in persisted_before
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {"scientific_name": "   "},
        {"scientific_name": "x" * 256},
        {"scientific_name": "Acer palmatum", "cultivar_name": "x" * 121},
        {"scientific_name": "Acer palmatum", "common_name": "x" * 161},
        {"scientific_name": "Acer\x00palmatum"},
        {"scientific_name": "Acer palmatum", "unknown": "value"},
        {"scientific_name": "Acer palmatum", "id": str(UUID(int=0))},
        {"scientific_name": "Acer palmatum", "created_at": "2026-08-28T00:00:00Z"},
    ],
)
def test_create_validation_rejects_invalid_or_read_only_input(
    authenticated_browser: tuple[str, str], payload: dict[str, object]
) -> None:
    status_code, _, _ = create_identity(authenticated_browser, payload)
    assert status_code == 422


def test_duplicate_conflicts_are_case_insensitive_and_qualified_identity_is_distinct(
    authenticated_browser: tuple[str, str],
) -> None:
    _, _, unqualified = create_identity(authenticated_browser, {"scientific_name": "Acer palmatum"})
    status_code, _, conflict = create_identity(
        authenticated_browser, {"scientific_name": "acer palmatum"}
    )
    assert status_code == 409
    assert conflict["detail"] == {
        "code": "botanical_identity_conflict",
        "message": "Botanical identity already exists",
        "existing_id": unqualified["id"],
    }

    status_code, _, qualified = create_identity(
        authenticated_browser,
        {"scientific_name": "Acer palmatum", "cultivar_name": "Bloodgood"},
    )
    assert status_code == 201
    assert qualified["id"] != unqualified["id"]
    for scientific_name, cultivar_name in (
        ("Acer palmatum", "Bloodgood"),
        ("acer palmatum", "bloodGOOD"),
    ):
        status_code, _, conflict = create_identity(
            authenticated_browser,
            {"scientific_name": scientific_name, "cultivar_name": cultivar_name},
        )
        assert status_code == 409
        assert conflict["detail"]["existing_id"] == qualified["id"]


def test_read_not_found_malformed_and_authentication_behavior(
    authenticated_browser: tuple[str, str],
) -> None:
    cookie, _ = authenticated_browser
    missing_id = uuid7()
    status_code, _, body = request(
        "GET", f"/api/v1/botanical-identities/{missing_id}", headers={"cookie": cookie}
    )
    assert status_code == 404
    assert body["detail"]["code"] == "botanical_identity_not_found"

    status_code, _, _ = request(
        "GET", "/api/v1/botanical-identities/not-a-uuid", headers={"cookie": cookie}
    )
    assert status_code == 422

    status_code, _, body = request("GET", f"/api/v1/botanical-identities/{missing_id}")
    assert status_code == 401
    assert body["detail"] == "Authentication required"


def test_create_requires_authentication_origin_csrf_and_owner(
    authenticated_browser: tuple[str, str], database_connection: Connection
) -> None:
    cookie, csrf_token = authenticated_browser
    path = "/api/v1/botanical-identities"
    payload = {"scientific_name": "Acer palmatum"}

    status_code, _, _ = request(
        "POST", path, body=payload, headers={"origin": ORIGIN, "x-csrf-token": csrf_token}
    )
    assert status_code == 401
    for headers in (
        {"cookie": cookie, "origin": ORIGIN},
        {"cookie": cookie, "origin": ORIGIN, "x-csrf-token": "wrong"},
        {"cookie": cookie, "x-csrf-token": csrf_token},
        {"cookie": cookie, "origin": "https://evil.example", "x-csrf-token": csrf_token},
    ):
        status_code, _, body = request("POST", path, body=payload, headers=headers)
        assert status_code == 403
        assert body["detail"] == "Request forbidden"

    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        owner = database.scalars(select(User)).one()
        auth_session = database.scalars(select(AuthSession)).one()
        member_actor = AuthenticatedActor(
            user_id=owner.id,
            login_name=owner.login_name,
            display_name=owner.display_name,
            owner=False,
            session=auth_session,
        )
    app.dependency_overrides[require_csrf] = lambda: member_actor
    status_code, _, body = request(
        "POST",
        path,
        body=payload,
    )
    assert status_code == 403
    assert body["detail"] == "Request forbidden"


def test_directory_counts_active_records_without_join_multiplication(
    authenticated_browser: tuple[str, str], database_connection: Connection
) -> None:
    from sqlalchemy import event

    from florabase.plants.model import Plant, PlantGroup
    from florabase.seed_lots.model import SeedLot
    from florabase.sowings.model import Sowing

    _, _, first = create_identity(authenticated_browser, {"scientific_name": "Counted identity"})
    _, _, second = create_identity(authenticated_browser, {"scientific_name": "Empty identity"})
    identity_id = UUID(first["id"])
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        lots = [SeedLot(botanical_identity_id=identity_id) for _ in range(2)]
        lots.append(SeedLot(botanical_identity_id=identity_id, lifecycle="discarded"))
        database.add_all(lots)
        database.flush()
        database.add_all(
            [
                Sowing(seed_lot_id=lots[0].id),
                Sowing(seed_lot_id=lots[1].id),
                Sowing(seed_lot_id=lots[0].id, lifecycle="completed"),
                Plant(botanical_identity_id=identity_id, direct_origin_kind="unknown"),
                Plant(
                    botanical_identity_id=identity_id,
                    direct_origin_kind="unknown",
                    lifecycle="dead",
                ),
                PlantGroup(botanical_identity_id=identity_id, direct_origin_kind="unknown"),
            ]
        )
        database.commit()

    statements: list[str] = []

    def capture(*args: Any) -> None:
        statements.append(str(args[2]))

    event.listen(database_connection, "before_cursor_execute", capture)
    try:
        code, _, body = request(
            "GET", "/api/v1/botanical-identities", headers={"cookie": authenticated_browser[0]}
        )
    finally:
        event.remove(database_connection, "before_cursor_execute", capture)
    assert code == 200
    by_id = {item["id"]: item for item in body}
    assert by_id[first["id"]]["collection_counts"] == {
        "seed_lots": 2,
        "sowings": 2,
        "plants": 1,
        "plant_groups": 1,
        "vegetative_lots": 0,
        "propagation_attempts": 0,
    }
    assert by_id[second["id"]]["collection_counts"] == {
        "seed_lots": 0,
        "sowings": 0,
        "plants": 0,
        "plant_groups": 0,
        "vegetative_lots": 0,
        "propagation_attempts": 0,
    }
    assert by_id[first["id"]]["compact_external_cover_url"] is None
    assert by_id[second["id"]]["compact_external_cover_url"] is None
    directory_queries = [sql for sql in statements if "botanical_identities.scientific_name" in sql]
    assert len(directory_queries) == 1


def test_reconciliation_inspects_sources_conflicts_and_corrects_accepted_name_in_place(
    authenticated_browser: tuple[str, str],
    database_connection: Connection,
    tmp_path: Any,
) -> None:
    from datetime import UTC

    from florabase.botanical_identities.api import (
        wcvp_v15_source_dependency,
        wcvp_v16_source_dependency,
        wfo_source_dependency,
    )
    from florabase.external_botany.model import ExternalTaxonLink
    from florabase.native_range_enrichment.snapshot import (
        DISTRIBUTION_FIELDS,
        NAMES_FIELDS,
    )
    from florabase.native_range_enrichment.snapshot import (
        build_index as build_wcvp_index,
    )
    from florabase.native_range_enrichment.source import (
        SourceMetadata as WcvpSourceMetadata,
    )
    from florabase.native_range_enrichment.source import (
        WcvpSource,
    )
    from florabase.plants.model import Plant, PlantGroup
    from florabase.seed_lots.model import SeedLot
    from florabase.taxonomy import service as taxonomy_service
    from florabase.taxonomy.schemas import TaxonomyLinkWrite
    from florabase.taxonomy.snapshot import build_index as build_wfo_index
    from florabase.taxonomy.source import CODE, ROOT, WfoMetadata, WfoSource

    cookie, csrf_token = authenticated_browser
    headers = {"cookie": cookie, "origin": ORIGIN, "x-csrf-token": csrf_token}

    # Build WFO snapshot where "Lycopersicon esculentum" is a synonym of "Solanum lycopersicum"
    wfo_path = tmp_path / "wfo.sqlite"
    wfo_meta = WfoMetadata(retrieved_at="2026-10-09T14:48:29Z")
    wfo_names = [
        {"ID": ROOT, "scientificName": "Plantae", "authorship": "", "rank": "kingdom"},
        {
            "ID": "wfo-4000000001",
            "scientificName": "Solanaceae",
            "authorship": "",
            "rank": "family",
        },
        {"ID": "wfo-4000000002", "scientificName": "Solanum", "authorship": "L.", "rank": "genus"},
        {
            "ID": "wfo-0001020304",
            "scientificName": "Solanum lycopersicum",
            "authorship": "L.",
            "rank": "species",
        },
        {
            "ID": "wfo-0009999999",
            "scientificName": "Lycopersicon esculentum",
            "authorship": "Mill.",
            "rank": "species",
        },
    ]
    wfo_concepts = [
        {"ID": ROOT, "nameID": ROOT, "parentID": CODE},
        {"ID": "wfo-4000000001", "nameID": "wfo-4000000001", "parentID": ROOT},
        {"ID": "wfo-4000000002", "nameID": "wfo-4000000002", "parentID": "wfo-4000000001"},
        {"ID": "wfo-0001020304", "nameID": "wfo-0001020304", "parentID": "wfo-4000000002"},
    ]
    wfo_synonyms = [
        {"ID": "wfo-0009999999-2026-06", "nameID": "wfo-0009999999", "taxonID": "wfo-0001020304"}
    ]
    build_wfo_index(wfo_path, wfo_names, wfo_concepts, wfo_synonyms, wfo_meta)
    wfo_source = WfoSource(wfo_path)

    # Build WCVP v15 (synonym -> Solanum lycopersicum) and WCVP v16 (conflicting)
    wcvp_v15_path = tmp_path / "wcvp_v15.sqlite"
    build_wcvp_index(
        wcvp_v15_path,
        [
            dict.fromkeys(NAMES_FIELDS, "")
            | {
                "plant_name_id": "10",
                "taxon_name": "Lycopersicon esculentum",
                "taxon_authors": "Mill.",
                "taxon_rank": "Species",
                "taxon_status": "Synonym",
                "accepted_plant_name_id": "20",
            },
            dict.fromkeys(NAMES_FIELDS, "")
            | {
                "plant_name_id": "20",
                "taxon_name": "Solanum lycopersicum",
                "taxon_authors": "L.",
                "taxon_rank": "Species",
                "taxon_status": "Accepted",
                "accepted_plant_name_id": "20",
            },
        ],
        [
            dict.fromkeys(DISTRIBUTION_FIELDS, "")
            | {
                "plant_locality_id": "1",
                "plant_name_id": "20",
                "area_code_l3": "PER",
                "introduced": "0",
                "extinct": "0",
                "location_doubtful": "0",
            }
        ],
        WcvpSourceMetadata.for_release("15", "2026-10-09T00:00:00Z"),
    )
    wcvp_v15 = WcvpSource(wcvp_v15_path, "15")

    wcvp_v16_path = tmp_path / "wcvp_v16.sqlite"
    build_wcvp_index(
        wcvp_v16_path,
        [
            dict.fromkeys(NAMES_FIELDS, "")
            | {
                "plant_name_id": "10",
                "taxon_name": "Lycopersicon esculentum",
                "taxon_authors": "Mill.",
                "taxon_rank": "Species",
                "taxon_status": "Synonym",
                "accepted_plant_name_id": "30",
            },
            dict.fromkeys(NAMES_FIELDS, "")
            | {
                "plant_name_id": "30",
                "taxon_name": "Solanum pimpinellifolium",
                "taxon_authors": "L.",
                "taxon_rank": "Species",
                "taxon_status": "Accepted",
                "accepted_plant_name_id": "30",
            },
        ],
        [
            dict.fromkeys(DISTRIBUTION_FIELDS, "")
            | {
                "plant_locality_id": "1",
                "plant_name_id": "30",
                "area_code_l3": "PER",
                "introduced": "0",
                "extinct": "0",
                "location_doubtful": "0",
            }
        ],
        WcvpSourceMetadata.for_release("16", "2026-10-09T00:00:00Z"),
    )
    wcvp_v16 = WcvpSource(wcvp_v16_path, "16")

    app.dependency_overrides[wfo_source_dependency] = lambda: wfo_source
    app.dependency_overrides[wcvp_v15_source_dependency] = lambda: wcvp_v15
    app.dependency_overrides[wcvp_v16_source_dependency] = lambda: wcvp_v16

    _, _, created = create_identity(
        authenticated_browser,
        {
            "scientific_name": "Lycopersicon esculentum",
            "cultivar_name": "San Marzano",
            "common_name": "Plum tomato",
        },
    )
    identity_id = UUID(created["id"])

    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        seed_lot = SeedLot(botanical_identity_id=identity_id)
        plant = Plant(botanical_identity_id=identity_id, direct_origin_kind="unknown")
        group = PlantGroup(botanical_identity_id=identity_id, direct_origin_kind="unknown")
        now = datetime.now(UTC)
        taxonomy_service.confirm(
            database,
            identity_id,
            TaxonomyLinkWrite(
                source_taxon_id="wfo-0009999999",
                checksum=wfo_meta.checksum,
                expected_version=None,
                identity_updated_at=datetime.fromisoformat(created["updated_at"]),
            ),
            wfo_source,
        )
        gbif_link = ExternalTaxonLink(
            botanical_identity_id=identity_id,
            provider="gbif",
            external_id="2930137",
            scientific_name="Lycopersicon esculentum Mill.",
            canonical_name="Lycopersicon esculentum",
            authorship="Mill.",
            rank="SPECIES",
            taxonomic_status="SYNONYM",
            accepted_external_id="2930136",
            accepted_name="Solanum lycopersicum L.",
            linked_at=now,
            last_refreshed_at=now,
            last_refresh_attempt_at=now,
        )
        database.add_all([seed_lot, plant, group, gbif_link])
        database.commit()
        seed_lot_id = str(seed_lot.id)
        plant_id = str(plant.id)
        group_id = str(group.id)

    status_code, _, recon = request(
        "GET",
        f"/api/v1/botanical-identities/{identity_id}/reconciliation",
        headers={"cookie": cookie},
    )
    assert status_code == 200
    assert recon["original_scientific_name"] == "Lycopersicon esculentum"
    assert recon["original_display_label"] == "Lycopersicon esculentum \u2018San Marzano\u2019"
    assert recon["former_names"] == []
    assert recon["has_source_conflict"] is True
    conflict_kinds = {c["kind"] for c in recon["conflicts"]}
    assert "wcvp_version_conflict" in conflict_kinds
    assert "cross_source_conflict" in conflict_kinds

    wfo_suggestion = next(s for s in recon["suggestions"] if s["source_provider"] == "wfo")
    assert wfo_suggestion["accepted_scientific_name"] == "Solanum lycopersicum"
    gbif_suggestion = next(s for s in recon["suggestions"] if s["source_provider"] == "gbif")
    assert gbif_suggestion["accepted_scientific_name"] == "Solanum lycopersicum"
    assert gbif_suggestion["accepted_authorship"] == "L."

    # Unacknowledged conflict is refused with 409
    refused_code, _, refused_body = request(
        "POST",
        f"/api/v1/botanical-identities/{identity_id}/reconciliation/correct-name",
        headers=headers,
        body={
            "scientific_name": "Solanum lycopersicum",
            "cultivar_name": "San Marzano",
            "common_name": "Plum tomato",
            "source_provider": "wfo",
            "source_version": wfo_suggestion["source_version"],
            "source_checksum": wfo_suggestion["source_checksum"],
            "link_version": wfo_suggestion["link_version"],
            "matched_taxon_id": wfo_suggestion["matched_taxon_id"],
            "accepted_taxon_id": wfo_suggestion["accepted_taxon_id"],
            "accepted_authorship": wfo_suggestion["accepted_authorship"],
            "acknowledge_conflict": False,
            "notes": "Confirming accepted WFO name",
            "identity_updated_at": recon["identity"]["updated_at"],
        },
    )
    assert refused_code == 409
    assert refused_body["detail"]["code"] == "reconciliation_conflict_unacknowledged"

    # Acknowledged correction succeeds in place and preserves identity UUID and holdings
    ok_code, _, corrected = request(
        "POST",
        f"/api/v1/botanical-identities/{identity_id}/reconciliation/correct-name",
        headers=headers,
        body={
            "scientific_name": "Solanum lycopersicum",
            "cultivar_name": "San Marzano",
            "common_name": "Plum tomato",
            "source_provider": "wfo",
            "source_version": wfo_suggestion["source_version"],
            "source_checksum": wfo_suggestion["source_checksum"],
            "link_version": wfo_suggestion["link_version"],
            "matched_taxon_id": wfo_suggestion["matched_taxon_id"],
            "accepted_taxon_id": wfo_suggestion["accepted_taxon_id"],
            "accepted_authorship": wfo_suggestion["accepted_authorship"],
            "acknowledge_conflict": True,
            "notes": "Confirmed WFO accepted name despite WCVP v16 split",
            "identity_updated_at": recon["identity"]["updated_at"],
        },
    )
    assert ok_code == 200, corrected
    assert corrected["identity"]["id"] == str(identity_id)
    assert corrected["identity"]["scientific_name"] == "Solanum lycopersicum"
    assert corrected["identity"]["display_label"] == "Solanum lycopersicum \u2018San Marzano\u2019"
    assert corrected["original_scientific_name"] == "Lycopersicon esculentum"
    assert corrected["original_display_label"] == "Lycopersicon esculentum \u2018San Marzano\u2019"
    assert len(corrected["former_names"]) == 1
    assert corrected["former_names"][0]["scientific_name"] == "Lycopersicon esculentum"
    assert corrected["former_names"][0]["status_kind"] == "initial_recorded"
    assert corrected["former_names"][0]["source_provider"] == "wfo"
    assert len(corrected["reconciliations"]) == 1
    assert corrected["reconciliations"][0]["kind"] == "accepted_name_correction"
    assert (
        corrected["reconciliations"][0]["evidence"]["notes"]
        == "Confirmed WFO accepted name despite WCVP v16 split"
    )

    # Collection holdings remain attached to the exact same BotanicalIdentity UUID
    assert request("GET", f"/api/v1/seed-lots/{seed_lot_id}", headers={"cookie": cookie})[2][
        "botanical_identity"
    ]["id"] == str(identity_id)
    assert request("GET", f"/api/v1/plants/{plant_id}", headers={"cookie": cookie})[2][
        "botanical_identity"
    ]["id"] == str(identity_id)
    assert request("GET", f"/api/v1/plant-groups/{group_id}", headers={"cookie": cookie})[2][
        "botanical_identity"
    ]["id"] == str(identity_id)

    # Search finds the corrected identity by its historical acquisition name
    search_code, _, search_body = request(
        "GET", "/api/v1/search?q=Lycopersicon", headers={"cookie": cookie}
    )
    assert search_code == 200
    identity_hits = [
        item
        for grp in search_body["groups"]
        if grp["kind"] == "botanical_identity"
        for item in grp["items"]
    ]
    assert len(identity_hits) == 1
    assert identity_hits[0]["id"] == str(identity_id)
    assert identity_hits[0]["title"] == "Solanum lycopersicum San Marzano"
    assert "Formerly Lycopersicon esculentum" in identity_hits[0]["context"]


def test_reconciliation_refuses_silent_merge_and_merges_duplicate_into_explicit_survivor(
    authenticated_browser: tuple[str, str],
    database_connection: Connection,
) -> None:
    from datetime import UTC, date

    from florabase.botanical_profiles.model import BotanicalProfile, BotanicalProfileNativeRange
    from florabase.collection_photos.model import BotanicalIdentityCoverImage, MediaAsset
    from florabase.external_botany.model import ExternalTaxonLink
    from florabase.geographic_places.model import GeographicPlace
    from florabase.native_range_enrichment.model import (
        NativeRangeApplication,
        NativeRangeProposal,
    )
    from florabase.plants.model import Plant, PlantGroup
    from florabase.schedule.model import ScheduledActivity
    from florabase.seed_lots.model import SeedLot

    cookie, csrf_token = authenticated_browser
    headers = {"cookie": cookie, "origin": ORIGIN, "x-csrf-token": csrf_token}

    _, _, duplicate = create_identity(
        authenticated_browser,
        {"scientific_name": "Lycopersicon esculentum", "common_name": "Old tomato"},
    )
    _, _, survivor = create_identity(
        authenticated_browser,
        {"scientific_name": "Solanum lycopersicum", "common_name": "Garden tomato"},
    )
    dup_id = UUID(duplicate["id"])
    surv_id = UUID(survivor["id"])

    # In-place correction onto an existing identity is refused with 409 duplicate_botanical_identity
    collision_code, _, collision_body = request(
        "POST",
        f"/api/v1/botanical-identities/{dup_id}/reconciliation/correct-name",
        headers=headers,
        body={
            "scientific_name": "Solanum lycopersicum",
            "cultivar_name": None,
            "common_name": "Garden tomato",
            "source_provider": "operator",
            "acknowledge_conflict": True,
            "identity_updated_at": duplicate["updated_at"],
        },
    )
    assert collision_code == 409
    assert collision_body["detail"]["code"] == "duplicate_botanical_identity"
    assert collision_body["detail"]["existing_id"] == str(surv_id)

    # Populate holdings, profiles, native ranges, cover image, external link, and receipt
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        now = datetime.now(UTC)
        places = list(
            database.scalars(select(GeographicPlace).order_by(GeographicPlace.id).limit(2))
        )
        assert len(places) == 2

        dup_profile = BotanicalProfile(
            botanical_identity_id=dup_id,
            description="Duplicate description text",
            uses="Culinary fruit",
        )
        surv_profile = BotanicalProfile(
            botanical_identity_id=surv_id,
            description="Survivor description text",
            uses=None,
        )
        database.add_all([dup_profile, surv_profile])
        database.flush()

        database.add_all(
            [
                BotanicalProfileNativeRange(
                    botanical_profile_id=dup_id,
                    geographic_place_id=places[0].id,
                    created_at=now,
                ),
                BotanicalProfileNativeRange(
                    botanical_profile_id=dup_id,
                    geographic_place_id=places[1].id,
                    created_at=now,
                ),
                BotanicalProfileNativeRange(
                    botanical_profile_id=surv_id,
                    geographic_place_id=places[0].id,
                    created_at=now,
                ),
            ]
        )

        lot = SeedLot(botanical_identity_id=dup_id)
        plant = Plant(botanical_identity_id=dup_id, direct_origin_kind="unknown")
        group = PlantGroup(botanical_identity_id=dup_id, direct_origin_kind="unknown")
        activity = ScheduledActivity(
            title="Inspect foliage",
            activity_kind="inspect",
            status="planned",
            due_on=date(2026, 6, 1),
            botanical_identity_id=dup_id,
        )
        asset = MediaAsset(
            kind="external",
            image_url="https://example.test/cover.jpg",
            source_url="https://example.test/page",
            attribution="Photo author",
        )
        database.add_all([lot, plant, group, activity, asset])
        database.flush()

        cover = BotanicalIdentityCoverImage(
            botanical_identity_id=dup_id,
            media_asset_id=asset.id,
            source_mode="external",
        )
        ext_link = ExternalTaxonLink(
            botanical_identity_id=dup_id,
            provider="gbif",
            external_id="2930137",
            scientific_name="Lycopersicon esculentum Mill.",
            canonical_name="Lycopersicon esculentum",
            linked_at=now,
            last_refreshed_at=now,
            last_refresh_attempt_at=now,
        )
        proposal = NativeRangeProposal(
            id=uuid7(),
            identity_id=dup_id,
            evidence={"format_version": "1"},
        )
        database.add_all([cover, ext_link, proposal])
        database.flush()

        application = NativeRangeApplication(
            proposal_id=proposal.id,
            identity_id=dup_id,
            evidence={"format_version": "1"},
        )
        database.add(application)
        database.commit()
        lot_id = str(lot.id)
        plant_id = str(plant.id)
        group_id = str(group.id)
        activity_id = str(activity.id)
        proposal_id = proposal.id

    # Merge refuses conflicting BotanicalProfile text unless profile_resolution='keep_survivor'
    prof_conflict_code, _, prof_conflict_body = request(
        "POST",
        f"/api/v1/botanical-identities/{dup_id}/reconciliation/merge-duplicate",
        headers=headers,
        body={
            "survivor_identity_id": str(surv_id),
            "profile_resolution": "fail_on_conflict",
            "duplicate_updated_at": duplicate["updated_at"],
            "survivor_updated_at": survivor["updated_at"],
        },
    )
    assert prof_conflict_code == 409
    assert prof_conflict_body["detail"]["code"] == "botanical_profile_conflict"
    assert prof_conflict_body["detail"]["conflicting_fields"] == ["description"]

    # Merge succeeds transactionally with profile_resolution='keep_survivor'
    merge_code, _, merged_recon = request(
        "POST",
        f"/api/v1/botanical-identities/{dup_id}/reconciliation/merge-duplicate",
        headers=headers,
        body={
            "survivor_identity_id": str(surv_id),
            "profile_resolution": "keep_survivor",
            "notes": "Merged synonym identity into accepted Solanum lycopersicum",
            "duplicate_updated_at": duplicate["updated_at"],
            "survivor_updated_at": survivor["updated_at"],
        },
    )
    assert merge_code == 200
    assert merged_recon["identity"]["id"] == str(surv_id)
    assert len(merged_recon["former_names"]) == 1
    assert merged_recon["former_names"][0]["scientific_name"] == "Lycopersicon esculentum"
    assert merged_recon["former_names"][0]["status_kind"] == "merged_duplicate"
    assert merged_recon["former_names"][0]["origin_identity_id"] == str(dup_id)
    assert len(merged_recon["reconciliations"]) == 1
    event_rec = merged_recon["reconciliations"][0]
    assert event_rec["kind"] == "duplicate_identity_merge"
    assert event_rec["duplicate_identity_id"] == str(dup_id)
    assert event_rec["evidence"]["repointed_records"] == {
        "seed_lot_ids": [lot_id],
        "plant_ids": [plant_id],
        "plant_group_ids": [group_id],
        "scheduled_activity_ids": [activity_id],
        "vegetative_lot_ids": [],
    }
    assert event_rec["evidence"]["copied_profile_fields"] == ["uses"]

    # Verify holdings were repointed to survivor
    assert request("GET", f"/api/v1/seed-lots/{lot_id}", headers={"cookie": cookie})[2][
        "botanical_identity"
    ]["id"] == str(surv_id)
    assert request("GET", f"/api/v1/plants/{plant_id}", headers={"cookie": cookie})[2][
        "botanical_identity"
    ]["id"] == str(surv_id)
    assert request("GET", f"/api/v1/plant-groups/{group_id}", headers={"cookie": cookie})[2][
        "botanical_identity"
    ]["id"] == str(surv_id)

    # Verify survivor profile kept description, copied missing 'uses', and unioned ranges
    _, _, surv_prof_body = request(
        "GET", f"/api/v1/botanical-identities/{surv_id}/profile", headers={"cookie": cookie}
    )
    assert surv_prof_body["description"] == "Survivor description text"
    assert surv_prof_body["uses"] == "Culinary fruit"
    _, _, surv_ranges_body = request(
        "GET",
        f"/api/v1/botanical-identities/{surv_id}/profile/native-ranges",
        headers={"cookie": cookie},
    )
    assert len(surv_ranges_body) == 2

    # Verify retired tombstone is excluded from directory and search, but readable by ID
    _, _, directory_body = request(
        "GET", "/api/v1/botanical-identities", headers={"cookie": cookie}
    )
    assert [item["id"] for item in directory_body] == [str(surv_id)]

    _, _, tombstone_body = request(
        "GET", f"/api/v1/botanical-identities/{dup_id}", headers={"cookie": cookie}
    )
    assert tombstone_body["merged_into_id"] == str(surv_id)
    assert tombstone_body["merged_at"] is not None

    # Search for the retired duplicate's scientific name returns only the active survivor
    _, _, search_body = request("GET", "/api/v1/search?q=Lycopersicon", headers={"cookie": cookie})
    identity_hits = [
        item
        for grp in search_body["groups"]
        if grp["kind"] == "botanical_identity"
        for item in grp["items"]
    ]
    assert [item["id"] for item in identity_hits] == [str(surv_id)]

    # Further edits or new seed lots on the retired tombstone are refused with 409
    assert (
        request(
            "PUT",
            f"/api/v1/botanical-identities/{dup_id}",
            headers=headers,
            body={"scientific_name": "Lycopersicon esculentum", "common_name": "Mutated"},
        )[0]
        == 409
    )
    assert (
        request(
            "POST",
            "/api/v1/seed-lots",
            headers=headers,
            body={"botanical_identity_id": str(dup_id)},
        )[0]
        == 404
    )

    # Retained native range enrichment audit rows remain intact on the tombstone
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        assert database.get(NativeRangeProposal, proposal_id) is not None
        assert database.get(NativeRangeApplication, proposal_id) is not None


def test_merge_duplicate_identity_preserves_plant_measurements_and_correction_history(
    authenticated_browser: tuple[str, str],
    database_connection: Connection,
) -> None:
    from florabase.plants.model import Plant

    cookie, csrf_token = authenticated_browser
    headers = {"cookie": cookie, "origin": ORIGIN, "x-csrf-token": csrf_token}

    _, _, duplicate = create_identity(
        authenticated_browser,
        {"scientific_name": "Echinocactus williamsii", "common_name": "Old peyote"},
    )
    _, _, survivor = create_identity(
        authenticated_browser,
        {"scientific_name": "Lophophora williamsii", "common_name": "Peyote"},
    )
    dup_id = UUID(duplicate["id"])
    surv_id = UUID(survivor["id"])

    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        plant = Plant(botanical_identity_id=dup_id, direct_origin_kind="unknown")
        database.add(plant)
        database.commit()
        plant_id = str(plant.id)

    # Record initial measurement event on the plant under duplicate identity
    status, _, first_event = request(
        "POST",
        f"/api/v1/plants/{plant_id}/events",
        headers=headers,
        body={
            "kind": "measurement",
            "occurred_on": {"precision": "day", "year": 2026, "month": 4, "day": 1},
            "measurement": {
                "quantity": "height",
                "value": "12.50",
                "unit": "cm",
                "is_approximate": False,
            },
        },
    )
    assert status == 201
    event_id = first_event["id"]

    # Record a measurement correction
    status, _, corrected_event = request(
        "PUT",
        f"/api/v1/events/{event_id}",
        headers=headers,
        body={
            "kind": "measurement",
            "occurred_on": {"precision": "day", "year": 2026, "month": 4, "day": 1},
            "measurement": {
                "quantity": "height",
                "value": "125",
                "unit": "mm",
                "is_approximate": False,
            },
        },
    )
    assert status == 200
    assert corrected_event["measurement"]["value"] == "125"
    assert len(corrected_event["measurement_corrections"]) == 1
    assert corrected_event["measurement_corrections"][0]["measurement"]["value"] == "12.50"

    # Merge duplicate identity into survivor
    status, _, merge_body = request(
        "POST",
        f"/api/v1/botanical-identities/{dup_id}/reconciliation/merge-duplicate",
        headers=headers,
        body={
            "survivor_identity_id": str(surv_id),
            "profile_resolution": "fail_on_conflict",
            "duplicate_updated_at": duplicate["updated_at"],
            "survivor_updated_at": survivor["updated_at"],
        },
    )
    assert status == 200
    assert merge_body["identity"]["id"] == str(surv_id)
    event_rec = merge_body["reconciliations"][0]
    assert event_rec["kind"] == "duplicate_identity_merge"
    assert event_rec["evidence"]["repointed_records"]["plant_ids"] == [plant_id]

    # Plant's botanical identity now points to the active survivor
    status, _, plant_body = request("GET", f"/api/v1/plants/{plant_id}", headers={"cookie": cookie})
    assert status == 200
    assert plant_body["botanical_identity"]["id"] == str(surv_id)

    # Measurement events and correction history on the plant are completely preserved
    status, _, plant_events = request(
        "GET", f"/api/v1/plants/{plant_id}/events", headers={"cookie": cookie}
    )
    assert status == 200
    assert len(plant_events) == 1
    retained_event = plant_events[0]
    assert retained_event["id"] == event_id
    assert retained_event["measurement"]["value"] == "125"
    assert retained_event["measurement"]["unit"] == "mm"
    assert len(retained_event["measurement_corrections"]) == 1
    assert retained_event["measurement_corrections"][0]["measurement"]["value"] == "12.50"
    assert retained_event["measurement_corrections"][0]["measurement"]["unit"] == "cm"


def test_concurrent_operator_synonym_additions_reject_the_duplicate(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as database, database.begin():
        identity = BotanicalIdentity(scientific_name=f"Synonym concurrency {uuid7()}")
        database.add(identity)
        database.flush()
        identity_id = identity.id

    worker_pids: Queue[int] = Queue()

    def add_duplicate() -> str:
        try:
            with Session(database_engine) as database, database.begin():
                database.execute(text("SET LOCAL lock_timeout = '10s'"))
                worker_pids.put(database.execute(text("SELECT pg_backend_pid()")).scalar_one())
                add_operator_synonym(
                    database, identity_id, OperatorSynonymCreate(scientific_name="SALVIA ARIDA")
                )
        except SynonymValidationError as error:
            return error.code
        return "created"

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            with Session(database_engine) as database, database.begin():
                add_operator_synonym(
                    database, identity_id, OperatorSynonymCreate(scientific_name="Salvia arida")
                )
                duplicate = executor.submit(add_duplicate)
                worker_pid = worker_pids.get(timeout=5)
                deadline = monotonic() + 5
                while not database.execute(
                    text("SELECT cardinality(pg_blocking_pids(:pid))"), {"pid": worker_pid}
                ).scalar_one():
                    assert monotonic() < deadline, "The competing write did not wait for the lock"
                    sleep(0.02)
            assert duplicate.result(timeout=5) == "duplicate_identity_name"
        with Session(database_engine) as database:
            entries = list_identity_synonyms(database, identity_id)
            assert [entry.scientific_name for entry in entries] == ["Salvia arida"]
    finally:
        with Session(database_engine) as database, database.begin():
            created_identity = database.get(BotanicalIdentity, identity_id)
            assert created_identity is not None
            database.delete(created_identity)


def test_operator_synonyms_crud_validation_and_search_integration(
    authenticated_browser: tuple[str, str],
    database_connection: Connection,
) -> None:
    from florabase.botanical_identities.model import BotanicalIdentityName

    cookie, csrf_token = authenticated_browser
    headers = {"cookie": cookie, "origin": ORIGIN, "x-csrf-token": csrf_token}

    # 1. Create two active botanical identities
    _, _, ident_1 = create_identity(
        authenticated_browser,
        {"scientific_name": "Trichocereus bridgesii", "common_name": "Bolivian torch"},
    )
    _, _, ident_2 = create_identity(
        authenticated_browser,
        {"scientific_name": "Echinopsis pachanoi", "common_name": "San Pedro"},
    )
    ident_1_id = ident_1["id"]
    ident_2_id = ident_2["id"]

    # 2. Add an operator-managed synonym
    syn_create_status, syn_create_headers, syn_data = request(
        "POST",
        f"/api/v1/botanical-identities/{ident_1_id}/synonyms",
        headers=headers,
        body={
            "scientific_name": "  Echinopsis lageniformis ",
            "cultivar_name": " \u2018Monstrose\u2019 ",
            "common_name": " Penis cactus ",
            "authorship": " (M.Frohlich) Friedrich & Rowley ",
            "source_citation": " Hortus Third ",
        },
    )
    assert syn_create_status == 201
    assert syn_data["scientific_name"] == "Echinopsis lageniformis"
    assert syn_data["cultivar_name"] == "Monstrose"
    assert syn_data["common_name"] == "Penis cactus"
    assert syn_data["authorship"] == "(M.Frohlich) Friedrich & Rowley"
    assert syn_data["source_version"] == "Hortus Third"
    assert syn_data["status_kind"] == "operator_synonym"
    assert syn_data["source_provider"] == "operator"
    syn_id = syn_data["id"]
    assert syn_create_headers["location"].endswith(f"/synonyms/{syn_id}")

    # 3. Reject proposed synonym matching current accepted name
    eq_status, _, eq_body = request(
        "POST",
        f"/api/v1/botanical-identities/{ident_1_id}/synonyms",
        headers=headers,
        body={"scientific_name": "Trichocereus bridgesii"},
    )
    assert eq_status == 409
    assert eq_body["detail"]["code"] == "synonym_equals_accepted_name"

    # 4. Reject duplicate synonym on same identity
    dup_status, _, dup_body = request(
        "POST",
        f"/api/v1/botanical-identities/{ident_1_id}/synonyms",
        headers=headers,
        body={"scientific_name": "Echinopsis lageniformis", "cultivar_name": "Monstrose"},
    )
    assert dup_status == 409
    assert dup_body["detail"]["code"] == "duplicate_identity_name"

    # 5. Reject synonym colliding with another active collection identity
    coll_status, _, coll_body = request(
        "POST",
        f"/api/v1/botanical-identities/{ident_1_id}/synonyms",
        headers=headers,
        body={"scientific_name": "Echinopsis pachanoi"},
    )
    assert coll_status == 409
    assert coll_body["detail"]["code"] == "duplicate_botanical_identity"
    assert coll_body["detail"]["existing_id"] == ident_2_id

    # 6. List synonyms
    list_status, _, list_body = request(
        "GET",
        f"/api/v1/botanical-identities/{ident_1_id}/synonyms",
        headers={"cookie": cookie},
    )
    assert list_status == 200
    assert len(list_body) == 1
    assert list_body[0]["id"] == syn_id
    assert list_body[0]["status_kind"] == "operator_synonym"

    # Filter by status_kind
    _, _, empty_filter = request(
        "GET",
        f"/api/v1/botanical-identities/{ident_1_id}/synonyms?status_kind=former_accepted",
        headers={"cookie": cookie},
    )
    assert len(empty_filter) == 0

    # 7. Global search finds active identity via operator synonym
    search_status, _, search_body = request(
        "GET",
        "/api/v1/search?q=lageniformis",
        headers={"cookie": cookie},
    )
    assert search_status == 200
    hits = [
        item
        for grp in search_body["groups"]
        if grp["kind"] == "botanical_identity"
        for item in grp["items"]
    ]
    assert len(hits) == 1
    assert hits[0]["id"] == ident_1_id
    assert "Synonym Echinopsis lageniformis" in hits[0]["context"]

    # 8. GET /api/v1/botanical-identities/{id} exposes synonyms
    read_status, _, read_body = request(
        "GET",
        f"/api/v1/botanical-identities/{ident_1_id}",
        headers={"cookie": cookie},
    )
    assert read_status == 200
    assert "Echinopsis lageniformis" in read_body["synonyms"]

    # 9. Update operator synonym
    up_status, _, up_body = request(
        "PUT",
        f"/api/v1/botanical-identities/{ident_1_id}/synonyms/{syn_id}",
        headers=headers,
        body={
            "scientific_name": "Echinopsis lageniformis",
            "cultivar_name": "Inermis",
            "common_name": "Smooth Bolivian torch",
            "authorship": "(M.Frohlich) Friedrich",
            "source_citation": "RHS Index 2026",
        },
    )
    assert up_status == 200
    assert up_body["cultivar_name"] == "Inermis"
    assert up_body["common_name"] == "Smooth Bolivian torch"
    assert up_body["source_version"] == "RHS Index 2026"

    # 10. Immutability guard: initial_recorded or former_accepted rows cannot be modified or deleted
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        now = datetime.now(UTC)
        initial_name = BotanicalIdentityName(
            botanical_identity_id=UUID(ident_1_id),
            scientific_name="Trichocereus bridgesii",
            status_kind="initial_recorded",
            source_provider="operator",
            effective_from=now,
            superseded_at=now,
            created_at=now,
        )
        database.add(initial_name)
        database.commit()
        initial_name_id = str(initial_name.id)

    guard_put_status, _, guard_put_body = request(
        "PUT",
        f"/api/v1/botanical-identities/{ident_1_id}/synonyms/{initial_name_id}",
        headers=headers,
        body={"scientific_name": "Mutated initial name"},
    )
    assert guard_put_status == 409
    assert guard_put_body["detail"]["code"] == "immutable_historical_name"

    guard_del_status, _, guard_del_body = request(
        "DELETE",
        f"/api/v1/botanical-identities/{ident_1_id}/synonyms/{initial_name_id}",
        headers=headers,
    )
    assert guard_del_status == 409
    assert guard_del_body["detail"]["code"] == "immutable_historical_name"

    # 11. Delete operator synonym
    del_status, _, _ = request(
        "DELETE",
        f"/api/v1/botanical-identities/{ident_1_id}/synonyms/{syn_id}",
        headers=headers,
    )
    assert del_status == 204

    # Verify synonym was deleted
    _, _, list_after = request(
        "GET",
        f"/api/v1/botanical-identities/{ident_1_id}/synonyms?status_kind=operator_synonym",
        headers={"cookie": cookie},
    )
    assert len(list_after) == 0

    # Search for deleted synonym returns no results
    _, _, search_after = request(
        "GET",
        "/api/v1/search?q=lageniformis",
        headers={"cookie": cookie},
    )
    hits_after = [
        item
        for grp in search_after["groups"]
        if grp["kind"] == "botanical_identity"
        for item in grp["items"]
    ]
    assert len(hits_after) == 0


def test_lineage_preserves_references_across_synonyms_correction_and_merge(
    authenticated_browser: tuple[str, str],
    database_connection: Connection,
) -> None:
    from florabase.propagation.schemas import (
        PlantFromSowingCreate,
        SeedLotSowingTransitionCreate,
    )
    from florabase.propagation.service import (
        create_plant_from_sowing,
        create_sowing_from_seed_lot,
    )
    from florabase.seed_lots.schemas import SeedLotCreate
    from florabase.seed_lots.service import create_seed_lot

    cookie, csrf_token = authenticated_browser
    headers = {"cookie": cookie, "origin": ORIGIN, "x-csrf-token": csrf_token}

    _, _, dup = create_identity(
        authenticated_browser,
        {"scientific_name": "Cereus bridgesii", "common_name": "Old bridgesii"},
    )
    _, _, surv = create_identity(
        authenticated_browser,
        {"scientific_name": "Trichocereus bridgesii", "common_name": "Bolivian torch"},
    )
    dup_id = dup["id"]
    surv_id = surv["id"]

    # Add operator synonyms on both duplicate and survivor before reconciliation
    dup_syn_status, _, _ = request(
        "POST",
        f"/api/v1/botanical-identities/{dup_id}/synonyms",
        headers=headers,
        body={"scientific_name": "Cereus lagenaeformis"},
    )
    assert dup_syn_status == 201
    surv_syn_status, _, _ = request(
        "POST",
        f"/api/v1/botanical-identities/{surv_id}/synonyms",
        headers=headers,
        body={"scientific_name": "Trichocereus lageniformis"},
    )
    assert surv_syn_status == 201

    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        lot = create_seed_lot(
            database,
            SeedLotCreate.model_validate(
                {
                    "botanical_identity_id": UUID(dup_id),
                    "quantity": {"kind": "seed_count", "value": 50, "is_approximate": False},
                }
            ),
        )
        sowing, _ = create_sowing_from_seed_lot(
            database,
            lot.id,
            SeedLotSowingTransitionCreate.model_validate(
                {
                    "sowing": {
                        "quantity": {"kind": "seed_count", "value": 10, "is_approximate": False}
                    },
                    "source_adjustment": {"mode": "partial"},
                }
            ),
        )
        plant, _ = create_plant_from_sowing(
            database,
            sowing.id,
            PlantFromSowingCreate(botanical_identity_id=UUID(dup_id), label="Bridgesii seedling 1"),
            "active",
        )
        database.commit()
        lot_id = str(lot.id)
        plant_id = str(plant.id)

    # Verify lineage before merge points to dup_id
    lin_status, _, lin_before = request(
        "GET", f"/api/v1/plants/{plant_id}/lineage", headers={"cookie": cookie}
    )
    assert lin_status == 200
    assert lin_before["subject"]["botanical_identity"]["id"] == dup_id
    assert [
        node["botanical_identity"]["id"]
        for node in lin_before["ancestors"]
        if "botanical_identity" in node
    ] == [dup_id]

    _, _, dup_after_syn = request(
        "GET", f"/api/v1/botanical-identities/{dup_id}", headers={"cookie": cookie}
    )
    _, _, surv_after_syn = request(
        "GET", f"/api/v1/botanical-identities/{surv_id}", headers={"cookie": cookie}
    )

    # Correct survivor accepted name in place (preserves surv_id UUID & existing synonym)
    corr_status, _, corr_body = request(
        "POST",
        f"/api/v1/botanical-identities/{surv_id}/reconciliation/correct-name",
        headers=headers,
        body={
            "scientific_name": "Echinopsis lageniformis",
            "cultivar_name": None,
            "common_name": "Bolivian torch",
            "source_provider": "operator",
            "acknowledge_conflict": False,
            "identity_updated_at": surv_after_syn["updated_at"],
        },
    )
    assert corr_status == 200
    surv_updated_at = corr_body["identity"]["updated_at"]

    # Merge duplicate into survivor: repoints SeedLot + Plant lineage to surv_id
    merge_status, _, merged_recon = request(
        "POST",
        f"/api/v1/botanical-identities/{dup_id}/reconciliation/merge-duplicate",
        headers=headers,
        body={
            "survivor_identity_id": surv_id,
            "profile_resolution": "fail_on_conflict",
            "duplicate_updated_at": dup_after_syn["updated_at"],
            "survivor_updated_at": surv_updated_at,
        },
    )
    assert merge_status == 200

    # Lineage endpoints for both Plant and SeedLot reflect survivor UUID & updated accepted name
    lin_after_status, _, lin_after = request(
        "GET", f"/api/v1/plants/{plant_id}/lineage", headers={"cookie": cookie}
    )
    assert lin_after_status == 200
    expected_identity_summary = {
        "id": surv_id,
        "display_label": "Echinopsis lageniformis",
    }
    assert lin_after["subject"]["botanical_identity"] == expected_identity_summary
    assert [
        node["botanical_identity"]
        for node in lin_after["ancestors"]
        if "botanical_identity" in node
    ] == [expected_identity_summary]

    lot_lin_status, _, lot_lin = request(
        "GET", f"/api/v1/seed-lots/{lot_id}/lineage", headers={"cookie": cookie}
    )
    assert lot_lin_status == 200
    assert lot_lin["subject"]["botanical_identity"] == expected_identity_summary
    assert lot_lin["ancestors"] == []

    # Survivor retains operator synonym, former accepted name, and merged duplicate provenance
    syn_names = {entry["scientific_name"] for entry in merged_recon["former_names"]}
    assert {
        "Trichocereus lageniformis",
        "Trichocereus bridgesii",
        "Cereus bridgesii",
        "Cereus lagenaeformis",
    }.issubset(syn_names)


def test_synonyms_enforce_auth_csrf_owner_tombstone_and_edit_cleanup(
    authenticated_browser: tuple[str, str],
    database_connection: Connection,
) -> None:
    cookie, csrf_token = authenticated_browser
    headers = {"cookie": cookie, "origin": ORIGIN, "x-csrf-token": csrf_token}

    _, _, ident = create_identity(
        authenticated_browser,
        {"scientific_name": "Cereus bridgesii", "common_name": "Torch"},
    )
    ident_id = ident["id"]

    # Create operator synonym for later cleanup verification
    create_st, _, syn = request(
        "POST",
        f"/api/v1/botanical-identities/{ident_id}/synonyms",
        headers=headers,
        body={"scientific_name": "Trichocereus bridgesii"},
    )
    assert create_st == 201
    syn_id = syn["id"]

    # Unauthenticated GET / POST / PUT / DELETE are rejected with 401
    assert request("GET", f"/api/v1/botanical-identities/{ident_id}/synonyms")[0] == 401
    assert (
        request(
            "POST",
            f"/api/v1/botanical-identities/{ident_id}/synonyms",
            headers={"origin": ORIGIN, "x-csrf-token": csrf_token},
            body={"scientific_name": "Echinopsis bridgesii"},
        )[0]
        == 401
    )

    # Missing / bad origin or CSRF token on POST / PUT / DELETE are rejected with 403
    for bad_headers in (
        {"cookie": cookie, "origin": ORIGIN},
        {"cookie": cookie, "origin": ORIGIN, "x-csrf-token": "wrong"},
        {"cookie": cookie, "x-csrf-token": csrf_token},
        {"cookie": cookie, "origin": "https://evil.example", "x-csrf-token": csrf_token},
    ):
        assert (
            request(
                "POST",
                f"/api/v1/botanical-identities/{ident_id}/synonyms",
                headers=bad_headers,
                body={"scientific_name": "Echinopsis bridgesii"},
            )[0]
            == 403
        )
        assert (
            request(
                "PUT",
                f"/api/v1/botanical-identities/{ident_id}/synonyms/{syn_id}",
                headers=bad_headers,
                body={"scientific_name": "Echinopsis bridgesii"},
            )[0]
            == 403
        )
        assert (
            request(
                "DELETE",
                f"/api/v1/botanical-identities/{ident_id}/synonyms/{syn_id}",
                headers=bad_headers,
            )[0]
            == 403
        )

    # Non-owner authenticated actor is refused with 403
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as database:
        owner = database.scalars(select(User)).one()
        auth_session = database.scalars(select(AuthSession)).one()
        member_actor = AuthenticatedActor(
            user_id=owner.id,
            login_name=owner.login_name,
            display_name=owner.display_name,
            owner=False,
            session=auth_session,
        )
    previous_override = app.dependency_overrides.get(require_csrf)
    app.dependency_overrides[require_csrf] = lambda: member_actor
    try:
        assert (
            request(
                "POST",
                f"/api/v1/botanical-identities/{ident_id}/synonyms",
                body={"scientific_name": "Echinopsis bridgesii"},
            )[0]
            == 403
        )
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(require_csrf, None)
        else:
            app.dependency_overrides[require_csrf] = previous_override

    # Standard PUT rename to match existing operator_synonym cleans up the duplicate
    # synonym and omits the active name from BotanicalIdentityResponse.synonyms
    put_st, _, put_body = request(
        "PUT",
        f"/api/v1/botanical-identities/{ident_id}",
        headers=headers,
        body={"scientific_name": "Trichocereus bridgesii", "common_name": "Torch"},
    )
    assert put_st == 200
    assert put_body["scientific_name"] == "Trichocereus bridgesii"
    assert "Cereus bridgesii" in put_body["synonyms"]
    assert "Trichocereus bridgesii" not in put_body["synonyms"]
    _, _, op_syns_after_put = request(
        "GET",
        f"/api/v1/botanical-identities/{ident_id}/synonyms?status_kind=operator_synonym",
        headers={"cookie": cookie},
    )
    assert len(op_syns_after_put) == 0

    # Correct accepted name in place onto an operator_synonym cleans it up as well
    add_2_st, _, _syn_2 = request(
        "POST",
        f"/api/v1/botanical-identities/{ident_id}/synonyms",
        headers=headers,
        body={"scientific_name": "Echinopsis lageniformis"},
    )
    assert add_2_st == 201
    _, _, fresh_ident = request(
        "GET", f"/api/v1/botanical-identities/{ident_id}", headers={"cookie": cookie}
    )
    corr_st, _, corr_body = request(
        "POST",
        f"/api/v1/botanical-identities/{ident_id}/reconciliation/correct-name",
        headers=headers,
        body={
            "scientific_name": "Echinopsis lageniformis",
            "cultivar_name": None,
            "common_name": "Torch",
            "source_provider": "operator",
            "acknowledge_conflict": False,
            "identity_updated_at": fresh_ident["updated_at"],
        },
    )
    assert corr_st == 200
    assert not any(
        row["status_kind"] == "operator_synonym"
        and row["scientific_name"] == "Echinopsis lageniformis"
        for row in corr_body["former_names"]
    )

    # Merged tombstone rejects POST / PUT / DELETE /synonyms with 409 botanical_identity_merged
    _, _, tombstone = create_identity(
        authenticated_browser,
        {"scientific_name": "Echinopsis bridgesii", "common_name": "Alias"},
    )
    tomb_id = tombstone["id"]
    _, _, tomb_syn = request(
        "POST",
        f"/api/v1/botanical-identities/{tomb_id}/synonyms",
        headers=headers,
        body={"scientific_name": "Cactus bridgesii"},
    )
    _, _, fresh_tomb = request(
        "GET", f"/api/v1/botanical-identities/{tomb_id}", headers={"cookie": cookie}
    )
    _, _, fresh_surv = request(
        "GET", f"/api/v1/botanical-identities/{ident_id}", headers={"cookie": cookie}
    )
    merge_st, _, _ = request(
        "POST",
        f"/api/v1/botanical-identities/{tomb_id}/reconciliation/merge-duplicate",
        headers=headers,
        body={
            "survivor_identity_id": ident_id,
            "profile_resolution": "keep_survivor",
            "duplicate_updated_at": fresh_tomb["updated_at"],
            "survivor_updated_at": fresh_surv["updated_at"],
        },
    )
    assert merge_st == 200

    for method, url, payload in (
        (
            "POST",
            f"/api/v1/botanical-identities/{tomb_id}/synonyms",
            {"scientific_name": "New syn"},
        ),
        (
            "PUT",
            f"/api/v1/botanical-identities/{tomb_id}/synonyms/{tomb_syn['id']}",
            {"scientific_name": "New syn"},
        ),
        ("DELETE", f"/api/v1/botanical-identities/{tomb_id}/synonyms/{tomb_syn['id']}", None),
    ):
        m_st, _, m_body = request(method, url, headers=headers, body=payload)
        assert m_st == 409
        assert m_body["detail"]["code"] == "botanical_identity_merged"
        assert m_body["detail"]["existing_id"] == ident_id
