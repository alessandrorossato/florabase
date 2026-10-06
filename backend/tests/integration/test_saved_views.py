from collections.abc import Iterator
from typing import Any
from uuid import UUID, uuid7

import pytest
from sqlalchemy import Connection, event, text
from sqlalchemy.orm import Session

from florabase.auth.model import User
from florabase.auth.security import password_hasher
from florabase.saved_views import service
from florabase.saved_views.model import SavedView
from florabase.saved_views.schemas import SavedViewCreate, SavedViewResponse, SavedViewUpdate
from florabase.saved_views.state import SavedViewSurface

from .test_search import _api_get
from .test_supplier_api import (
    ORIGIN,
    mutate,
    request,
)
from .test_supplier_api import (
    authenticated_browser as authenticated_browser,
)

pytestmark = pytest.mark.integration


def payload(
    name: str = "Basil", surface: str = "global_search", state: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {"name": name, "surface": surface, "state_version": 1, "state": state or {"q": "basil"}}


@pytest.fixture
def db(database_connection: Connection) -> Iterator[Session]:
    with Session(bind=database_connection, join_transaction_mode="create_savepoint") as session:
        yield session


def test_persisted_crud_name_conflicts_and_jsonb(
    authenticated_browser: tuple[str, str], db: Session
) -> None:
    status, _, created = mutate(
        authenticated_browser, "POST", "/api/v1/saved-views", payload("  葉っぱ Basil  ")
    )
    assert status == 201
    view_id = UUID(created["id"])
    assert view_id.version == 7
    assert created["name"] == "葉っぱ Basil"
    assert created["compatibility"] == "supported"
    assert "+00:00" in created["created_at"] or created["created_at"].endswith("Z")
    record = db.get(SavedView, view_id)
    assert record is not None
    assert record.state == {"q": "basil"}
    assert (
        db.scalar(text("SELECT jsonb_typeof(state) FROM saved_views WHERE id=:id"), {"id": view_id})
        == "object"
    )
    assert (
        mutate(authenticated_browser, "POST", "/api/v1/saved-views", payload("葉っぱ basil"))[0]
        == 409
    )
    assert (
        mutate(
            authenticated_browser,
            "POST",
            "/api/v1/saved-views",
            payload("葉っぱ basil", "suppliers"),
        )[0]
        == 201
    )
    _, _, other = mutate(authenticated_browser, "POST", "/api/v1/saved-views", payload("Other"))
    path = f"/api/v1/saved-views/{view_id}"
    assert mutate(authenticated_browser, "PATCH", path, {"name": "other"})[0] == 409
    renamed = mutate(authenticated_browser, "PATCH", path, {"name": "  My plants  "})[2]
    assert renamed["name"] == "My plants"
    assert renamed["state"] == created["state"]
    updated = mutate(
        authenticated_browser,
        "PATCH",
        path,
        {"state_version": 1, "state": {"q": "  mint ", "kind": ["plant", "plant"]}},
    )[2]
    assert updated["id"] == str(view_id)
    assert updated["name"] == "My plants"
    assert updated["state"] == {"q": "mint", "kind": ["plant"]}
    assert updated["created_at"] == created["created_at"]
    assert updated["updated_at"] > created["updated_at"]
    assert mutate(authenticated_browser, "PATCH", path, {"surface": "plants"})[0] == 422
    assert (
        mutate(authenticated_browser, "PATCH", path, {"state_version": 2, "state": {"q": "mint"}})[
            0
        ]
        == 422
    )
    assert mutate(authenticated_browser, "DELETE", path)[0] == 204
    assert mutate(authenticated_browser, "DELETE", path)[0] == 404
    db.expire_all()
    assert db.get(SavedView, view_id) is None
    assert db.get(SavedView, UUID(other["id"])) is not None


def test_owner_scope_with_second_real_user(
    authenticated_browser: tuple[str, str], db: Session
) -> None:
    _, _, created = mutate(authenticated_browser, "POST", "/api/v1/saved-views", payload())
    owner = db.scalar(text("SELECT id FROM users WHERE login_name='owner'"))
    second = User(
        login_name="second",
        password_hash=password_hasher().hash("correct horse battery staple"),
        owner=True,
    )
    db.add(second)
    db.flush()
    foreign = service.create_view(db, second.id, SavedViewCreate.model_validate(payload()))
    db.commit()
    cookie, _ = authenticated_browser
    rows = request("GET", "/api/v1/saved-views", headers={"cookie": cookie})[2]
    assert [row["id"] for row in rows] == [created["id"]]
    updates: list[dict[str, Any]] = [
        {"name": "Intruder"},
        {"state_version": 1, "state": {"q": "mint"}},
    ]
    for body in updates:
        assert (
            mutate(authenticated_browser, "PATCH", f"/api/v1/saved-views/{foreign.id}", body)[0]
            == 404
        )
    assert mutate(authenticated_browser, "DELETE", f"/api/v1/saved-views/{foreign.id}")[0] == 404
    assert owner is not None
    assert service.get_view(db, second.id, UUID(created["id"])) is None
    assert service.get_view(db, second.id, foreign.id) is not None
    assert [row.id for row in service.list_views(db, second.id, None)] == [foreign.id]
    status, headers, login = request(
        "POST",
        "/api/v1/auth/login",
        body={"login_name": "second", "password": "correct horse battery staple"},
        headers={"origin": ORIGIN},
    )
    assert status == 200
    second_browser = (headers["set-cookie"].split(";", 1)[0], login["csrf_token"])
    rows = request("GET", "/api/v1/saved-views", headers={"cookie": second_browser[0]})[2]
    assert [row["id"] for row in rows] == [str(foreign.id)]
    for body in updates:
        assert (
            mutate(second_browser, "PATCH", f"/api/v1/saved-views/{created['id']}", body)[0] == 404
        )
    assert mutate(second_browser, "DELETE", f"/api/v1/saved-views/{created['id']}")[0] == 404
    service.update_view(db, foreign, SavedViewUpdate(name="Mine"))
    db.commit()
    assert foreign.name == "Mine"


def test_listing_is_deterministic_filtered_and_one_query(
    authenticated_browser: tuple[str, str], db: Session
) -> None:
    owner = db.scalar(text("SELECT id FROM users WHERE login_name='owner'"))
    for name, surface in [
        ("Zoo", "global_search"),
        ("apple", "global_search"),
        ("Other", "suppliers"),
    ]:
        mutate(authenticated_browser, "POST", "/api/v1/saved-views", payload(name, surface))
    statements: list[str] = []

    def capture(
        _conn: Any, _cursor: Any, statement: str, _params: Any, _context: Any, _many: Any
    ) -> None:
        statements.append(statement)

    event.listen(db.bind, "before_cursor_execute", capture)
    try:
        rows = service.list_views(db, owner, SavedViewSurface.GLOBAL_SEARCH)
        responses = [SavedViewResponse.from_model(row) for row in rows]
    finally:
        event.remove(db.bind, "before_cursor_execute", capture)
    assert [row.name for row in responses] == ["apple", "Zoo"]
    assert len(statements) == 1
    assert len(service.list_views(db, owner, None)) == 3


def test_unknown_version_and_stale_uuid_read_rename_replace_delete(
    authenticated_browser: tuple[str, str], db: Session
) -> None:
    missing = str(uuid7())
    _, _, created = mutate(
        authenticated_browser,
        "POST",
        "/api/v1/saved-views",
        payload(state={"identity_id": missing}),
    )
    record = db.get(SavedView, UUID(created["id"]))
    assert record is not None
    record.state_version = 9
    record.state = {"future": True}
    db.commit()
    cookie, _ = authenticated_browser
    listed = request("GET", "/api/v1/saved-views", headers={"cookie": cookie})[2]
    assert listed[0]["compatibility"] == "unsupported_version"
    path = f"/api/v1/saved-views/{record.id}"
    renamed = mutate(authenticated_browser, "PATCH", path, {"name": "Retained future"})[2]
    assert renamed["state_version"] == 9
    assert renamed["state"] == {"future": True}
    restored = mutate(
        authenticated_browser,
        "PATCH",
        path,
        {"state_version": 1, "state": {"identity_id": missing}},
    )[2]
    assert restored["state"] == {"identity_id": missing}
    assert restored["compatibility"] == "supported"
    assert mutate(authenticated_browser, "DELETE", path)[0] == 204


@pytest.mark.parametrize(
    "changes",
    [
        {"name": " "},
        {"surface": "unknown"},
        {"state_version": 2},
        {"state": {"q": "mint", "offset": 40}},
        {"state": {"kind": ["harvest"], "lifecycle": "active"}},
        {"state": {"location_id": "wrong"}},
    ],
)
def test_api_validation(authenticated_browser: tuple[str, str], changes: dict[str, Any]) -> None:
    assert (
        mutate(authenticated_browser, "POST", "/api/v1/saved-views", {**payload(), **changes})[0]
        == 422
    )


def test_anonymous_and_origin_csrf_protection(authenticated_browser: tuple[str, str]) -> None:
    assert request("GET", "/api/v1/saved-views")[0] == 401
    assert request("POST", "/api/v1/saved-views", body=payload())[0] == 401
    cookie, csrf = authenticated_browser
    assert (
        request(
            "POST",
            "/api/v1/saved-views",
            body=payload(),
            headers={"cookie": cookie, "origin": ORIGIN},
        )[0]
        == 403
    )
    assert (
        request(
            "POST",
            "/api/v1/saved-views",
            body=payload(),
            headers={"cookie": cookie, "origin": "https://foreign.invalid", "x-csrf-token": csrf},
        )[0]
        == 403
    )
    assert (
        request(
            "POST",
            "/api/v1/saved-views",
            body=payload(),
            headers={"cookie": cookie, "origin": ORIGIN, "x-csrf-token": "invalid"},
        )[0]
        == 403
    )


def test_list_surface_api_and_bounded_pages(
    authenticated_browser: tuple[str, str], db: Session
) -> None:
    owner = db.scalar(text("SELECT id FROM users WHERE login_name='owner'"))
    db.add_all(
        [
            SavedView(
                owner_id=owner,
                name=f"View {i:03}",
                surface="plants",
                state_version=1,
                state={"q": "basil"},
            )
            for i in range(105)
        ]
    )
    db.add(
        SavedView(
            owner_id=owner,
            name="Elsewhere",
            surface="suppliers",
            state_version=1,
            state={"q": "basil"},
        )
    )
    db.commit()
    cookie, _ = authenticated_browser
    status, first = _api_get("/api/v1/saved-views?surface=plants", cookie)
    status_next, next_page = _api_get("/api/v1/saved-views?surface=plants&offset=100", cookie)
    assert status == status_next == 200
    assert isinstance(first, list)
    assert isinstance(next_page, list)
    assert len(first) == 100
    assert len(next_page) == 5
    assert first[0]["name"] == "View 000"
    assert next_page[0]["name"] == "View 100"
    assert _api_get("/api/v1/saved-views?surface=unknown", cookie)[0] == 422
    assert _api_get("/api/v1/saved-views?offset=-1", cookie)[0] == 422
