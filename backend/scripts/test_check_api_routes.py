import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Annotated
from unittest.mock import MagicMock
from uuid import uuid7

import pytest
from check_api_routes import Access, InventoryError, Operation, inventory, run_check
from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.testclient import TestClient
from starlette.convertors import CONVERTOR_TYPES, StringConvertor
from starlette.responses import Response
from starlette.staticfiles import StaticFiles

from florabase.auth.dependencies import (
    AuthenticatedActor,
    require_authenticated_actor,
    require_owner,
)
from florabase.auth.model import AuthSession
from florabase.core.config import CookieMode, Environment, Settings, get_settings
from florabase.db.session import get_database_session


def endpoint() -> None:
    return None


def app_with_public_baseline() -> FastAPI:
    app = FastAPI(openapi_url=None)
    app.post("/api/v1/auth/login")(endpoint)
    app.get("/api/v1/health")(endpoint)
    app.get("/api/v1/ready")(endpoint)
    return app


def unexpected_public_app() -> FastAPI:
    app = app_with_public_baseline()
    app.get("/unreviewed", include_in_schema=False)(endpoint)
    return app


def test_public_baseline_passes_and_output_is_deterministic(
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = app_with_public_baseline()
    app.get("/private", dependencies=[Depends(require_authenticated_actor)])(endpoint)
    assert run_check(lambda: app, output_format="json") == 0
    first = capsys.readouterr().out
    app.router.routes.reverse()
    assert run_check(lambda: app, output_format="json") == 0
    assert capsys.readouterr().out == first
    report = json.loads(first)
    assert report["status"] == "pass"
    assert report["counts"] == {"total": 4, "public": 3, "authenticated": 1, "owner-restricted": 0}
    assert report["unexpected_public"] == report["stale_allowlist"] == []


def test_stale_public_entries_include_removed_and_now_authenticated_operations(
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = FastAPI(openapi_url=None)
    app.get("/api/v1/health")(endpoint)
    app.get("/api/v1/ready", dependencies=[Depends(require_authenticated_actor)])(endpoint)
    assert run_check(lambda: app, output_format="json") == 1
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "fail"
    assert report["unexpected_public"] == []
    assert report["stale_allowlist"] == [
        {"method": "GET", "path": "/api/v1/ready"},
        {"method": "POST", "path": "/api/v1/auth/login"},
    ]


@pytest.mark.parametrize("flags", [[], ["-O"]], ids=["normal", "optimized"])
def test_unexpected_public_route_exits_nonzero(flags: list[str]) -> None:
    result = subprocess.run(
        [
            sys.executable,
            *flags,
            "-c",
            "from test_check_api_routes import run_check, unexpected_public_app; "
            "raise SystemExit(run_check(unexpected_public_app, output_format='json'))",
        ],
        cwd=Path(__file__).resolve().parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "fail"
    assert report["unexpected_public"] == [{"method": "GET", "path": "/unreviewed"}]
    assert report["stale_allowlist"] == []


def owner_gate(actor: Annotated[AuthenticatedActor, Depends(require_authenticated_actor)]) -> None:
    require_owner(actor)


def test_nested_router_and_include_dependencies() -> None:
    app = FastAPI(openapi_url=None)
    router = APIRouter(prefix="/outer", dependencies=[Depends(owner_gate)])
    child = APIRouter(prefix="/inner")
    child.add_api_route("/{item_id:int}/", endpoint, methods=["GET", "POST"])
    router.include_router(child)
    app.include_router(router)
    included = APIRouter()
    included.get("/included")(endpoint)
    app.include_router(included, dependencies=[Depends(require_authenticated_actor)])

    assert inventory(app) == [
        Operation("GET", "/included", Access.AUTHENTICATED),
        Operation("GET", "/outer/inner/{item_id:int}/", Access.AUTHENTICATED),
        Operation("POST", "/outer/inner/{item_id:int}/", Access.AUTHENTICATED),
    ]


def test_application_authentication_and_declared_owner_dependency() -> None:
    app = FastAPI(openapi_url=None, dependencies=[Depends(require_authenticated_actor)])
    app.get("/owner", dependencies=[Depends(require_owner)])(endpoint)
    app.get("/app-only")(endpoint)
    assert inventory(app) == [
        Operation("GET", "/app-only", Access.AUTHENTICATED),
        Operation("GET", "/owner", Access.OWNER_RESTRICTED),
    ]


def test_mount_uses_child_dependencies_and_starlette_implicit_head() -> None:
    root = FastAPI(openapi_url=None, dependencies=[Depends(require_authenticated_actor)])
    mid = FastAPI(openapi_url=None)
    child = FastAPI(openapi_url=None)
    child.get("/open")(endpoint)
    child.get("/private", dependencies=[Depends(owner_gate)])(endpoint)

    async def starlette_endpoint(_: Request) -> Response:
        return Response()

    child.add_route("/plain", starlette_endpoint)
    mid.mount("/child", child)
    root.mount("/mounted", mid)
    assert inventory(root) == [
        Operation("GET", "/mounted/child/open", Access.PUBLIC),
        Operation("GET", "/mounted/child/plain", Access.PUBLIC),
        Operation("GET", "/mounted/child/private", Access.AUTHENTICATED),
        Operation("HEAD", "/mounted/child/plain", Access.PUBLIC),
    ]


def test_dependency_names_and_openapi_security_are_not_authentication() -> None:
    def fake_auth() -> None:
        return None

    fake_auth.__name__ = require_authenticated_actor.__name__
    app = FastAPI(openapi_url=None)
    app.get(
        "/pretender",
        dependencies=[Depends(fake_auth)],
        openapi_extra={"security": [{"session": []}]},
    )(endpoint)
    assert inventory(app) == [Operation("GET", "/pretender", Access.PUBLIC)]


@pytest.mark.parametrize("second_path", ["/items/{id}", "/items/{name}", "/items/{name:int}"])
def test_repeated_matching_shapes_refuse_an_inventory(second_path: str) -> None:
    app = FastAPI(openapi_url=None)
    app.get("/items/{id}")(endpoint)
    app.get(second_path)(endpoint)
    with pytest.raises(InventoryError, match="duplicate or ambiguous operation"):
        inventory(app)


def test_inventory_fails_closed_for_opaque_mount_and_overrides(
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = app_with_public_baseline()
    app.mount("/static", StaticFiles())
    assert run_check(lambda: app, output_format="json") == 2
    assert json.loads(capsys.readouterr().out) == {
        "status": "error",
        "error": "opaque mount at /static",
    }

    app = app_with_public_baseline()
    app.dependency_overrides[require_authenticated_actor] = endpoint
    assert run_check(lambda: app, output_format="text") == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "dependency overrides at /" in output.err


def first_handler() -> str:
    return "first"


def second_handler() -> str:
    return "second"


def shadowed_allowlist_app() -> FastAPI:
    router = APIRouter(prefix="/api/v1")
    router.get("/{name}")(first_handler)
    app = FastAPI(openapi_url=None)
    app.include_router(router)
    app.get("/api/v1/health")(second_handler)
    return app


def test_earlier_included_parameter_route_shadows_public_static_operation() -> None:
    app = shadowed_allowlist_app()
    assert TestClient(app).get("/api/v1/health").json() == "first"
    with pytest.raises(InventoryError, match=r"GET /api/v1/health.*earlier /api/v1/\{name\}"):
        inventory(app)


@pytest.mark.parametrize("flags", [[], ["-O"]], ids=["normal", "optimized"])
def test_shadowed_allowlist_exits_incomplete(flags: list[str]) -> None:
    result = subprocess.run(
        [
            sys.executable,
            *flags,
            "-c",
            "from test_check_api_routes import run_check, shadowed_allowlist_app; "
            "raise SystemExit(run_check(shadowed_allowlist_app, output_format='json'))",
        ],
        cwd=Path(__file__).resolve().parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "error"
    assert "GET /api/v1/health" in report["error"]
    assert "operations" not in report


def test_public_parameter_route_overlaps_protected_operation() -> None:
    app = FastAPI(openapi_url=None)
    app.get("/items/{name}")(first_handler)
    app.get("/items/{item_id:int}", dependencies=[Depends(require_authenticated_actor)])(
        second_handler
    )
    assert TestClient(app).get("/items/42").json() == "first"
    with pytest.raises(InventoryError, match="may be shadowed"):
        inventory(app)


@pytest.mark.parametrize(
    ("static_path", "template_path"),
    [
        ("/events/rooting-observations", "/events/{event_id}"),
        ("/provenance-sites/map", "/provenance-sites/{site_id}"),
    ],
)
def test_earlier_static_route_reserves_url(static_path: str, template_path: str) -> None:
    app = FastAPI(openapi_url=None)
    app.get(static_path)(first_handler)
    app.get(template_path)(second_handler)
    assert TestClient(app).get(static_path).json() == "first"
    assert len(inventory(app)) == 2


def test_partial_method_match_does_not_shadow_later_route() -> None:
    app = FastAPI(openapi_url=None)
    app.post("/items/{name}")(first_handler)
    app.get("/items/static")(second_handler)
    client = TestClient(app)
    assert client.get("/items/static").json() == "second"
    assert client.post("/items/static").json() == "first"
    assert len(inventory(app)) == 2


def test_locked_integer_and_uuid_converters_overlap() -> None:
    app = FastAPI(openapi_url=None)
    app.get("/items/{item_id:int}")(first_handler)
    app.get("/items/{item_id:uuid}")(second_handler)
    client = TestClient(app)
    assert client.get("/items/" + "1" * 32).json() == "first"
    assert client.get("/items/" + str(uuid7())).json() == "second"
    with pytest.raises(InventoryError, match="may be shadowed"):
        inventory(app)


def test_converter_excludes_literal_in_another_template() -> None:
    app = FastAPI(openapi_url=None)
    app.get("/items/{item_id:int}/{part}")(first_handler)
    app.get("/items/latest/{part}")(second_handler)
    client = TestClient(app)
    assert client.get("/items/42/detail").json() == "first"
    assert client.get("/items/latest/detail").json() == "second"
    assert len(inventory(app)) == 2


def test_catch_all_shadows_deeper_route_but_keeps_disjoint_prefix() -> None:
    app = FastAPI(openapi_url=None)
    app.get("/items/{rest:path}")(first_handler)
    app.get("/other/{name}/detail")(second_handler)
    assert len(inventory(app)) == 2
    app.get("/items/{name}/detail")(second_handler)
    assert TestClient(app).get("/items/example/detail").json() == "first"
    with pytest.raises(InventoryError, match="may be shadowed"):
        inventory(app)


def test_mount_owns_prefix_even_when_child_returns_404() -> None:
    app = FastAPI(openapi_url=None)
    app.mount("/api/v1", FastAPI(openapi_url=None))
    app.get("/api/v1/health")(second_handler)
    assert TestClient(app).get("/api/v1/health").status_code == 404
    with pytest.raises(InventoryError, match=r"earlier /api/v1/\{path:path\}"):
        inventory(app)


def test_earlier_parent_route_shadows_mounted_operation() -> None:
    app = FastAPI(openapi_url=None)
    app.get("/api/{rest:path}")(first_handler)
    child = FastAPI(openapi_url=None)
    child.get("/health")(second_handler)
    app.mount("/api/v1", child)
    assert TestClient(app).get("/api/v1/health").json() == "first"
    with pytest.raises(InventoryError, match=r"GET /api/v1/health.*earlier /api/\{rest:path\}"):
        inventory(app)


def test_unreviewed_converter_refuses_inventory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(CONVERTOR_TYPES, "custom", StringConvertor())
    app = FastAPI(openapi_url=None)
    app.get("/items/{name:custom}")(first_handler)
    assert TestClient(app).get("/items/example").json() == "first"
    with pytest.raises(InventoryError, match="unsupported path converter"):
        inventory(app)


def test_initialization_failure_suppresses_exception_values(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail() -> FastAPI:
        raise RuntimeError("synthetic settings canary")

    assert run_check(fail, output_format="json") == 2
    assert json.loads(capsys.readouterr().out) == {"status": "error", "error": "RuntimeError"}


def test_declared_dependencies_deny_missing_session_and_non_owner_at_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with monkeypatch.context() as settings_env:
        for name in tuple(os.environ):
            if name.upper().startswith("FLORABASE_"):
                settings_env.delenv(name)
        settings = Settings(
            _env_file=None,
            environment=Environment.TEST,
            database_url="postgresql+psycopg://test:test@db/test",
            canonical_origin="https://florabase.example",
            cookie_mode=CookieMode.SECURE,
        )

    app = FastAPI(openapi_url=None)
    app.get("/private", dependencies=[Depends(require_owner)])(endpoint)
    # Supply the test database dependency without adding query parameters or connecting to it.
    app.dependency_overrides[get_database_session] = lambda: MagicMock()
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        assert client.get("/private").status_code == 401
        non_owner = AuthenticatedActor(uuid7(), "member", None, False, MagicMock(spec=AuthSession))
        app.dependency_overrides[require_authenticated_actor] = lambda: non_owner
        assert client.get("/private").status_code == 403
