"""TX-001: a successful HTTP write is sent only after its PostgreSQL transaction commits.

These tests deliberately use a real uvicorn server, the production ``get_database_session``
dependency and genuine commits, because rolled-back fixture transactions cannot show what another
database connection observes. Every committed row is removed again and table counts are compared.

Against the unmodified request-scoped base (``fbce3c4``) three tests fail deterministically for the
transaction-ordering defect: success visibility, commit failure and login cookie ordering. A fourth,
``test_application_exception_after_flush_rolls_back``, can also fail there (timing-dependent) only
because the ``browser`` fixture's own login commit still lands after its response, inside the armed
window; with a pause after that login it passes on the base. The request under test returned 500 and
persisted nothing, so base rollback behavior was already correct. This is not a fourth defect.
"""

import socket
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
import uvicorn
from sqlalchemy import Engine, delete, event, func, select, text
from sqlalchemy.orm import Session, UOWTransaction

from florabase.auth.model import AuthSession, LoginThrottle, User
from florabase.auth.service import bootstrap_owner
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.core.config import CookieMode, Environment, Settings, get_settings
from florabase.db.base import Base
from florabase.db.session import get_database_session, get_engine
from florabase.harvests.model import Harvest
from florabase.locations.model import Location
from florabase.main import app
from florabase.plants.model import Plant
from florabase.schedule.model import ScheduledActivity
from florabase.seed_lots.model import SeedLot

pytestmark = pytest.mark.integration

ORIGIN = "https://florabase.example"
OWNER = "tx001-owner"
PASSWORD = "correct horse battery staple"
COMMIT_DELAY_SECONDS = 0.4


class InjectedFailureError(RuntimeError):
    pass


@dataclass
class CommitProbe:
    """Opt-in SQLAlchemy hooks; inert unless a test arms exactly one request."""

    mode: str | None = None
    committed_at: list[float] = field(default_factory=list)

    def before_commit(self, _session: Session) -> None:
        if self.mode == "delay":
            time.sleep(COMMIT_DELAY_SECONDS)
        elif self.mode == "fail-commit":
            raise InjectedFailureError("injected commit failure")

    def after_commit(self, _session: Session) -> None:
        if self.mode is not None:
            self.committed_at.append(time.monotonic())

    def after_flush(self, _session: Session, _flush: UOWTransaction) -> None:
        if self.mode == "fail-after-flush":
            raise InjectedFailureError("injected application failure after flush")

    def arm(self, mode: str) -> None:
        self.mode = mode
        self.committed_at.clear()


@dataclass
class LiveApi:
    base_url: str
    engine: Engine
    probe: CommitProbe

    def client(self) -> httpx.Client:
        return httpx.Client(base_url=self.base_url, headers={"Origin": ORIGIN}, timeout=30)

    def scalar(self, statement: Any) -> Any:
        """Read through a separate pooled connection, never the server's request session."""
        with Session(self.engine) as observer:
            return observer.scalar(statement)


@dataclass
class Browser:
    client: httpx.Client
    cookie: str
    csrf: str

    def headers(self, csrf: str | None = None) -> dict[str, str]:
        return {"Cookie": self.cookie, "X-CSRF-Token": csrf or self.csrf}

    def get(self, path: str) -> httpx.Response:
        return self.client.get(path, headers={"Cookie": self.cookie})

    def send(
        self, method: str, path: str, body: object = None, csrf: str | None = None
    ) -> httpx.Response:
        return self.client.request(method, path, json=body, headers=self.headers(csrf))


def _table_counts(engine: Engine) -> dict[str, int]:
    with engine.connect() as connection:
        return {
            table.name: int(connection.scalar(select(func.count()).select_from(table)) or 0)
            for table in Base.metadata.tables.values()
        }


def _remove_committed_rows(engine: Engine) -> None:
    with Session(engine) as database:
        database.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        owner_ids = select(User.id).where(User.login_name == OWNER)
        identity_ids = select(BotanicalIdentity.id).where(
            BotanicalIdentity.scientific_name.like("TX001 %")
        )
        database.execute(delete(ScheduledActivity).where(ScheduledActivity.title.like("TX001 %")))
        database.execute(delete(SeedLot).where(SeedLot.botanical_identity_id.in_(identity_ids)))
        database.execute(delete(Plant).where(Plant.botanical_identity_id.in_(identity_ids)))
        database.execute(delete(Location).where(Location.name.like("TX001 %")))
        database.execute(delete(BotanicalIdentity).where(BotanicalIdentity.id.in_(identity_ids)))
        database.execute(delete(AuthSession).where(AuthSession.user_id.in_(owner_ids)))
        database.execute(delete(LoginThrottle).where(LoginThrottle.login_name == OWNER))
        database.execute(delete(User).where(User.login_name == OWNER))
        database.commit()


@pytest.fixture(scope="module")
def live_api(integration_settings: Settings) -> Iterator[LiveApi]:
    assert get_database_session not in app.dependency_overrides
    database_engine = get_engine()
    request_settings = Settings.model_validate(
        {
            "environment": Environment.TEST,
            "database_url": integration_settings.database_url,
            "database_disposable": True,
            "canonical_origin": ORIGIN,
            "cookie_mode": CookieMode.SECURE,
        }
    )
    previous_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_settings] = lambda: request_settings
    probe = CommitProbe()
    hooks: list[tuple[str, Callable[..., None]]] = [
        ("before_commit", probe.before_commit),
        ("after_commit", probe.after_commit),
        ("after_flush", probe.after_flush),
    ]
    for name, hook in hooks:
        event.listen(Session, name, hook)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning", lifespan="off"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            assert time.monotonic() < deadline, "uvicorn did not start"
            time.sleep(0.05)
        yield LiveApi(f"http://127.0.0.1:{port}/api/v1", database_engine, probe)
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()
        for name, hook in hooks:
            event.remove(Session, name, hook)
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


@pytest.fixture
def browser(live_api: LiveApi) -> Iterator[Browser]:
    before = _table_counts(live_api.engine)
    assert before["users"] == 0, "real-commit tests require a disposable database without users"
    with Session(live_api.engine) as database:
        bootstrap_owner(database, OWNER, PASSWORD, "TX001 Owner")
        database.commit()
    client = live_api.client()
    try:
        login = client.post("/auth/login", json={"login_name": OWNER, "password": PASSWORD})
        assert login.status_code == 200
        cookie = login.headers["set-cookie"].split(";", 1)[0]
        yield Browser(client, cookie, login.json()["csrf_token"])
    finally:
        live_api.probe.mode = None
        client.close()
        _remove_committed_rows(live_api.engine)
        assert _table_counts(live_api.engine) == before


def _identity(live_api: LiveApi) -> UUID:
    with Session(live_api.engine) as database:
        identity = BotanicalIdentity(scientific_name=f"TX001 {uuid4().hex[:8]}")
        database.add(identity)
        database.commit()
        return identity.id


def _plant(live_api: LiveApi) -> UUID:
    identity_id = _identity(live_api)
    with Session(live_api.engine) as database:
        location = Location(name=f"TX001 bench {uuid4().hex[:8]}")
        database.add(location)
        database.flush()
        plant = Plant(
            botanical_identity_id=identity_id,
            direct_origin_kind="unknown",
            lifecycle="dead",
            location_id=location.id,
        )
        database.add(plant)
        database.commit()
        return plant.id


def _location_exists(live_api: LiveApi, name: str) -> bool:
    return bool(live_api.scalar(select(func.count()).where(Location.name == name)))


def test_success_is_sent_only_after_commit_is_visible_elsewhere(
    live_api: LiveApi, browser: Browser
) -> None:
    name = f"TX001 delayed {uuid4().hex[:8]}"
    live_api.probe.arm("delay")
    started = time.monotonic()
    response = browser.send("POST", "/locations", {"name": name})
    received = time.monotonic()
    live_api.probe.mode = None

    assert response.status_code == 201
    assert _location_exists(live_api, name)
    assert live_api.probe.committed_at, "the request did not commit"
    assert max(live_api.probe.committed_at) <= received
    assert received - started >= COMMIT_DELAY_SECONDS


def test_commit_failure_is_an_error_response_and_persists_nothing(
    live_api: LiveApi, browser: Browser
) -> None:
    name = f"TX001 failed {uuid4().hex[:8]}"
    live_api.probe.arm("fail-commit")
    response = browser.send("POST", "/locations", {"name": name})
    live_api.probe.mode = None

    assert response.status_code == 500
    assert name not in response.text
    assert not _location_exists(live_api, name)


def test_application_exception_after_flush_rolls_back(live_api: LiveApi, browser: Browser) -> None:
    """Rollback was already correct before TX-001; this guards it under function scope.

    ``committed_at == []`` also requires that no earlier request's commit is still in flight. On the
    request-scoped base that last assertion can fail (timing-dependent) because the fixture login
    commits after its response, not because this request's rollback is wrong.
    """
    name = f"TX001 flushed {uuid4().hex[:8]}"
    live_api.probe.arm("fail-after-flush")
    response = browser.send("POST", "/locations", {"name": name})
    live_api.probe.mode = None

    assert response.status_code == 500
    assert not _location_exists(live_api, name)
    assert live_api.probe.committed_at == []


def test_domain_conflict_after_read_leaves_schedule_unchanged(
    live_api: LiveApi, browser: Browser
) -> None:
    created = browser.send(
        "POST",
        "/schedule",
        {"activity_kind": "water", "title": "TX001 water", "due_on": "2026-11-02"},
    )
    assert created.status_code == 201
    identifier = UUID(created.json()["id"])
    assert live_api.scalar(
        select(ScheduledActivity.title).where(ScheduledActivity.id == identifier)
    ) == ("TX001 water")

    updated = browser.send(
        "PUT",
        f"/schedule/{identifier}",
        {
            "activity_kind": "water",
            "title": "TX001 watered",
            "due_on": "2026-11-03",
            "expected_version": created.json()["version"],
        },
    )
    assert updated.status_code == 200
    assert live_api.scalar(
        select(ScheduledActivity.title).where(ScheduledActivity.id == identifier)
    ) == ("TX001 watered")

    stale = browser.send(
        "PUT",
        f"/schedule/{identifier}",
        {
            "activity_kind": "water",
            "title": "TX001 stale",
            "due_on": "2026-11-04",
            "expected_version": created.json()["version"],
        },
    )
    assert stale.status_code == 409
    assert live_api.scalar(
        select(ScheduledActivity.title).where(ScheduledActivity.id == identifier)
    ) == ("TX001 watered")


def test_seed_lot_create_is_visible_when_response_arrives(
    live_api: LiveApi, browser: Browser
) -> None:
    identity_id = _identity(live_api)
    response = browser.send(
        "POST", "/seed-lots", {"botanical_identity_id": str(identity_id), "label": "TX001 lot"}
    )
    assert response.status_code == 201
    assert live_api.scalar(select(SeedLot.label).where(SeedLot.id == UUID(response.json()["id"])))


def test_explicit_commit_harvest_endpoints_remain_atomic_and_visible(
    live_api: LiveApi, browser: Browser
) -> None:
    plant_id = _plant(live_api)
    created = browser.send(
        "POST",
        "/harvests",
        {"plant_id": str(plant_id), "label": "TX001", "items": [{"material_kind": "fruit"}]},
    )
    assert created.status_code == 201
    harvest_id = UUID(created.json()["id"])
    assert live_api.scalar(select(func.count()).where(Harvest.id == harvest_id)) == 1

    deleted = browser.send("DELETE", f"/harvests/{harvest_id}")
    assert deleted.status_code == 204
    assert live_api.scalar(select(func.count()).where(Harvest.id == harvest_id)) == 0


def test_failed_login_explicit_commit_survives_error_response(
    live_api: LiveApi, browser: Browser
) -> None:
    response = browser.client.post(
        "/auth/login", json={"login_name": OWNER, "password": "wrong password value"}
    )
    assert response.status_code == 401
    assert (
        live_api.scalar(
            select(LoginThrottle.failed_attempts).where(LoginThrottle.login_name == OWNER)
        )
        == 1
    )


def test_login_session_is_committed_before_cookie_is_returned(
    live_api: LiveApi, browser: Browser
) -> None:
    sessions = (
        select(func.count())
        .select_from(AuthSession)
        .join(User)
        .where(User.login_name == OWNER, AuthSession.revoked_at.is_(None))
    )
    assert live_api.scalar(sessions) == 1
    live_api.probe.arm("delay")
    login = browser.client.post("/auth/login", json={"login_name": OWNER, "password": PASSWORD})
    received = time.monotonic()
    live_api.probe.mode = None

    assert login.status_code == 200
    assert live_api.probe.committed_at
    assert max(live_api.probe.committed_at) <= received
    assert live_api.scalar(sessions) == 2
    cookie = login.headers["set-cookie"].split(";", 1)[0]
    assert browser.client.get("/auth/session", headers={"Cookie": cookie}).status_code == 200


def test_session_and_csrf_changes_are_usable_by_the_next_request(
    live_api: LiveApi, browser: Browser
) -> None:
    session = browser.get("/auth/session")
    assert session.status_code == 200
    assert session.json()["login_name"] == OWNER
    assert (
        live_api.scalar(
            select(func.count())
            .select_from(AuthSession)
            .join(User)
            .where(User.login_name == OWNER, AuthSession.revoked_at.is_(None))
        )
        == 1
    )

    rotated = browser.client.post("/auth/csrf", headers={"Cookie": browser.cookie})
    assert rotated.status_code == 200
    new_csrf = rotated.json()["csrf_token"]
    rejected = browser.send("POST", "/locations", {"name": "TX001 stale csrf"}, csrf=browser.csrf)
    assert rejected.status_code == 403
    accepted = browser.send("POST", "/locations", {"name": "TX001 fresh csrf"}, csrf=new_csrf)
    assert accepted.status_code == 201
    assert _location_exists(live_api, "TX001 fresh csrf")

    logout = browser.send("POST", "/auth/logout", csrf=new_csrf)
    assert logout.status_code == 200
    assert browser.get("/auth/session").status_code == 401
    assert live_api.scalar(
        select(AuthSession.revoked_at).join(User).where(User.login_name == OWNER)
    ) <= datetime.now(UTC)
