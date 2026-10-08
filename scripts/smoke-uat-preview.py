#!/usr/bin/env python3
"""Unique disposable UAT: real auth, seed, source, persistence, reset and isolation."""

from __future__ import annotations

import hashlib
import http.cookiejar
import json
import shutil
import socket
import tempfile
import uuid
from pathlib import Path
from typing import Any, cast
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

from uat_preview import UATPreview
from workflow_environment import (
    Environment,
    Repository,
    WorkflowError,
    code_heads,
    migration_graph,
    run,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise WorkflowError(f"UAT smoke: {message}")


def operator_snapshot(repo: Repository) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "git": Environment(repo, "dev").repo.identity(),
        "projects": {},
    }
    for project in (
        "florabase",
        "florabase-feature-review",
        "florabase-preview",
        "florabase-prod",
        "florabase-uat-preview",
    ):
        ids = run(
            [
                "docker",
                "ps",
                "-aq",
                "--filter",
                f"label=com.docker.compose.project={project}",
            ],
            capture=True,
        ).splitlines()
        volumes = run(
            [
                "docker",
                "volume",
                "ls",
                "-q",
                "--filter",
                f"label=com.docker.compose.project={project}",
            ],
            capture=True,
        ).splitlines()
        containers = json.loads(run(["docker", "inspect", *ids], capture=True)) if ids else []
        result: dict[str, Any] = {
            "containers": [
                (
                    item["Id"],
                    item["State"]["StartedAt"],
                    item["State"]["Running"],
                    item["Mounts"],
                )
                for item in containers
            ],
            "volumes": json.loads(run(["docker", "volume", "inspect", *volumes], capture=True))
            if volumes
            else [],
        }
        for item in containers:
            if (
                item["State"].get("Running")
                and item["Config"]["Labels"].get("com.docker.compose.service") == "db"
            ):
                data = run(
                    [
                        "docker",
                        "exec",
                        item["Id"],
                        "sh",
                        "-ec",
                        'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --data-only --inserts --no-owner --no-privileges',
                    ],
                    capture=True,
                )
                # PostgreSQL dump restriction tokens are random; exclude them from the checksum.
                data = "\n".join(
                    line
                    for line in data.splitlines()
                    if not line.startswith(("\\restrict", "\\unrestrict"))
                )
                result["database_digest"] = hashlib.sha256(data.encode()).hexdigest()
        snapshot["projects"][project] = result
    return snapshot


class SmokeUAT(UATPreview):
    def __init__(self, repo: Repository) -> None:
        super().__init__(repo)
        self.project += "-smoke-" + uuid.uuid4().hex[:12]
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        require(20000 <= port <= 60000, "ephemeral port outside fixture range; retry")
        self.url = f"http://localhost:{port}"

    def environment(self) -> dict[str, str]:
        environment = super().environment()
        environment["FRONTEND_PORT"] = self.url.rsplit(":", 1)[1]
        return environment

    def python(self, program: str) -> str:
        return self.compose("exec", "-T", "backend", "python", "-c", program, capture=True)

    def state(self) -> dict[str, Any]:
        program = """
import hashlib,json
from pathlib import Path
from sqlalchemy import select,func
from sqlalchemy.orm import Session
import florabase.main
from florabase.db.base import Base
from florabase.db.session import get_engine
root=Path('/var/lib/florabase/attachments')
with Session(get_engine()) as db:
    counts={t.name:db.scalar(select(func.count()).select_from(t)) for t in Base.metadata.tables.values()}
manifest=json.loads((root/'.uat-fixture.json').read_text())
files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob('objects/**/*') if p.is_file()}
print(json.dumps({'counts':counts,'manifest':manifest,'media':files},sort_keys=True))
"""
        return cast(dict[str, Any], json.loads(self.python(program)))

    def cleanup(self) -> None:
        self.remove(self.project)


def login(preview: SmokeUAT, *, expected: int = 200) -> None:
    opener = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
    request = Request(
        preview.url + "/api/v1/auth/login",
        data=json.dumps({"login_name": "preview", "password": "preview"}).encode(),
        headers={"Content-Type": "application/json", "Origin": preview.url},
    )
    try:
        with opener.open(request, timeout=10) as response:
            require(response.status == expected, "login status")
            require(bool(response.headers.get("Set-Cookie")), "real session cookie")
        with opener.open(preview.url + "/api/v1/seed-lots", timeout=10) as response:
            require(response.status == 200, "normal session can read private collection")
    except HTTPError as error:
        require(error.code == expected, f"login unexpectedly returned {error.code}")


def ownership_transition(preview: SmokeUAT, previous: dict[str, Any]) -> None:
    """Real old-owner removal -> new linked-source up/seed on the same disposable project."""
    with tempfile.TemporaryDirectory(prefix="florabase-uat-transition-") as directory:
        primary = Path(directory) / "primary"
        source = Path(directory) / "next-feature"
        primary.mkdir()
        run(["git", "-C", str(primary), "init", "--initial-branch=main"], capture=True)
        run(
            [
                "git",
                "-C",
                str(primary),
                "-c",
                "user.name=UAT Test",
                "-c",
                "user.email=uat@example.invalid",
                "commit",
                "--allow-empty",
                "-m",
                "UAT fixture",
            ],
            capture=True,
        )
        run(
            [
                "git",
                "-C",
                str(primary),
                "remote",
                "add",
                "origin",
                "https://github.com/alessandrorossato/florabase.git",
            ]
        )
        run(["git", "-C", str(primary), "update-ref", "refs/remotes/origin/main", "HEAD"])
        run(
            ["git", "-C", str(primary), "worktree", "add", "-b", "feat/next-uat", str(source)],
            capture=True,
        )
        # Copy only Git-listed source, including dirty/untracked work; never .env or caches.
        for name in preview.repository.git(
            "ls-files", "--cached", "--others", "--exclude-standard", "-z"
        ).split("\0"):
            if not name or ".env" in Path(name).parts or ".git" in Path(name).parts:
                continue
            original = preview.source / name
            if original.is_file() and not original.is_symlink():
                target = source / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original, target)
        next_preview = SmokeUAT(Repository(source))
        next_preview.project = preview.project
        next_preview.url = preview.url
        for action in (next_preview.up, lambda: next_preview.remove(next_preview.project)):
            try:
                action()
            except WorkflowError as error:
                require("belongs to" in str(error), "non-owner must refuse before retirement")
            else:
                raise WorkflowError("UAT smoke: next source adopted old UAT")
        require(preview.state() == previous, "non-owner refusals preserve old state")
        preview.remove(preview.project)
        require(not preview.containers() and not preview.resource_volumes(), "old owner retired")
        try:
            next_preview.up()
            login(next_preview, expected=401)
            next_preview.seed()
            fresh = next_preview.state()
            require(
                fresh["counts"]["users"] == 1 and fresh["counts"]["suppliers"] == 2,
                "new source freshly seeds owner and baseline",
            )
            require(len(fresh["media"]) == 1, "new source freshly seeds media")
            require(
                fresh["manifest"]["records"] != previous["manifest"]["records"],
                "new source gets fresh fixture IDs",
            )
            require(
                all(
                    (item["Labels"] or {}).get("io.florabase.source") == str(source)
                    for item in next_preview.resource_volumes()
                ),
                "new volume ownership",
            )
            marker = json.loads(
                next_preview.python(
                    "from pathlib import Path; print(Path('/var/lib/florabase/attachments/.uat-identity.json').read_text())"
                )
            )
            require(marker["source"] == str(source), "new media marker ownership")
            login(next_preview)
            next_preview.status()
        finally:
            next_preview.cleanup()
        require(
            not next_preview.containers() and not next_preview.resource_volumes(), "new UAT retired"
        )


def main() -> None:
    repo = Repository(Path.cwd())
    preview = SmokeUAT(repo)
    before = operator_snapshot(repo)
    require(
        not preview.containers() and not preview.resource_volumes(),
        "disposable project must be absent",
    )
    migration = repo.source / "backend/alembic/versions/uat_smoke_marker.py"
    require(not migration.exists(), "source marker already exists")
    base_head = code_heads(migration_graph(repo.source))[0]
    migration.write_text(
        f"revision = 'uat_smoke_marker'\ndown_revision = {base_head!r}\nbranch_labels = None\ndepends_on = None\ndef upgrade():\n    pass\ndef downgrade():\n    pass\n"
    )
    try:
        preview.up()
        require(
            preview.current() == ["uat_smoke_marker"],
            "current untracked migration source used",
        )
        login(preview, expected=401)
        preview.seed()
        baseline = preview.state()
        require(baseline["counts"]["users"] == 1, "one real owner")
        require(
            baseline["counts"]["botanical_identities"] == 3,
            "three botanical identities",
        )
        require(len(baseline["media"]) == 1, "one tiny binary media asset")
        login(preview)
        # Runtime guard tests run against this disposable real DB, never operator resources.
        preview.compose(
            "run",
            "--rm",
            "-T",
            "--no-deps",
            "--volume",
            f"{repo.source / 'scripts'}:/uat:ro",
            "-e",
            "PYTHONPATH=/app/src:/uat",
            "backend",
            "pytest",
            "/uat/test-uat-fixture.py",
            "--no-cov",
            "-q",
        )
        # Model/service relationship evidence and one ordinary operator edit/new record.
        preview.python("""
import json
import shutil
from pathlib import Path
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
import florabase.main
from florabase.db.session import get_engine
from florabase.suppliers.model import Supplier
from florabase.suppliers.service import update_supplier,create_supplier
from florabase.suppliers.schemas import SupplierUpdate,SupplierCreate
from florabase.plants.model import Plant,PlantGroup
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing
from florabase.harvests.model import Harvest,HarvestItem
from florabase.collection_photos.model import RecordMediaLink,CollectionPrimaryPhoto
m=json.loads(Path('/var/lib/florabase/attachments/.uat-fixture.json').read_text())['records']
with Session(get_engine()) as db:
    row=lambda key,model:db.get(model,UUID(m[key]))
    assert row('plant:derived',Plant).originating_sowing_id==row('sowing:basil',Sowing).id
    assert row('group:basil',PlantGroup).originating_sowing_id==row('sowing:basil',Sowing).id
    assert row('sowing:basil',Sowing).seed_lot_id==row('seed:0',SeedLot).id
    assert row('harvest:basil',Harvest).plant_id==row('plant:derived',Plant).id
    assert row('item:basil',HarvestItem).harvest_id==row('harvest:basil',Harvest).id
    links=[row('link:'+kind,RecordMediaLink) for kind in ('supplier','plant','seed_lot')]
    assert len({link.media_asset_id for link in links})==1
    assert len(list(db.scalars(select(CollectionPrimaryPhoto))))==3
    supplier=row('supplier:nursery',Supplier)
    update_supplier(db,supplier,SupplierUpdate(name='Operator-edited nursery',kind='nursery',notes='UAT edit must persist'))
    create_supplier(db,SupplierCreate(name='Operator-only UAT supplier',kind='exchange'))
    db.commit()
""")
        edited = preview.state()
        preview.seed()
        preview.seed()
        require(
            preview.state() == edited,
            "repeated seed preserves IDs/counts/media/operator edits",
        )
        preview.compose(
            "exec",
            "-T",
            "frontend",
            "sh",
            "-ec",
            "printf retained > /app/node_modules/.uat-smoke",
        )
        preview.stop()
        preview.up()
        require(
            preview.state() == edited,
            "stop/start retains fixture, owner, operator changes and media",
        )
        preview.compose(
            "exec",
            "-T",
            "frontend",
            "sh",
            "-ec",
            "test $(cat /app/node_modules/.uat-smoke) = retained",
        )
        login(preview)
        edited = preview.state()
        # Remove only the temporary source marker: ahead DB must refuse without downgrade.
        migration.unlink()
        try:
            preview.up()
        except WorkflowError as error:
            require("AHEAD OF OR INCOMPATIBLE" in str(error), "ahead refusal")
        else:
            raise WorkflowError("UAT smoke: ahead DB unexpectedly accepted")
        require(preview.current() == ["uat_smoke_marker"], "ahead refusal never downgrades")
        for token in ("", "wrong", "florabase", "florabase-preview"):
            try:
                preview.reset(token)
            except WorkflowError:
                pass
            else:
                raise WorkflowError("UAT smoke: reset without correct token succeeded")
        require(preview.state() == edited, "wrong reset leaves data/media unchanged")
        preview.reset(preview.project)
        reset = preview.state()
        require(reset["counts"]["suppliers"] == 2, "reset removes operator-only UAT record")
        require(
            reset["counts"]["users"] == 1 and len(reset["media"]) == 1,
            "reset recreates owner and media",
        )
        require(reset["manifest"]["version"] == 2, "fixture version")
        login(preview)
        reset = preview.state()
        preview.seed()
        require(preview.state() == reset, "reset baseline remains idempotent")
        require(
            operator_snapshot(repo) == before,
            "DEV/Review/Stable Preview/PROD/operator UAT and primary unchanged",
        )
        ownership_transition(preview, reset)
        print(
            "REAL UAT COMPOSE SMOKE PASSED: first startup/empty auth; dirty untracked source; real Argon2/session login; runtime guard tests; fixture relationships; triple seed/operator edits; DB/media/dependency stop-start persistence; ahead refusal; guarded reset/owner/media rebuild; old-owner remove/new linked-source up/fresh seed/login; unchanged operator environments"
        )
    except Exception:
        preview.compose("logs", "--no-color", "--tail", "80", "frontend", "backend")
        raise
    finally:
        migration.unlink(missing_ok=True)
        preview.cleanup()
    require(
        operator_snapshot(repo) == before,
        "disposable cleanup leaves operator state unchanged",
    )
    require(
        not preview.containers() and not preview.resource_volumes(),
        "disposable resources cleaned",
    )


if __name__ == "__main__":
    main()
