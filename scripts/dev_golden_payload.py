"""Fixed-purpose snapshot helpers inside the disposable or networkless snapshot container."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

import golden_dataset as golden
import golden_plan
from sqlalchemy import delete, inspect, select, text, update
from sqlalchemy.orm import Session

from florabase.application_settings.model import ApplicationSettings
from florabase.attachments.model import Attachment
from florabase.attachments.storage import AttachmentStorage
from florabase.auth.model import AuthSession, LoginThrottle, User
from florabase.auth.security import password_hasher
from florabase.collection_photos.model import MediaAsset
from florabase.core.config import get_settings
from florabase.db.base import Base
from florabase.db.session import get_engine
from florabase.media.service import asset_thumbnail

sys.path.insert(0, "/app/scripts")
import attachment_artifacts as attachments  # noqa: E402

STAGE_COPY = "golden_dev_stage"
LIVE_ROOT = Path("/var/lib/florabase/attachments")
LEDGER = golden.LEDGER
AUTH_FIELDS = ("login_name", "display_name", "password_hash")


def existing_owner(database: Session) -> User:
    owner = database.scalars(select(User)).one()
    if not owner.owner or not owner.enabled:
        raise RuntimeError("An enabled DEV owner is required")
    return owner


def require_private_password(encoded: str) -> None:
    hasher = password_hasher()
    if any(hasher.verify(password, encoded) for password in (golden.OWNER_PASSWORD, "preview")):
        raise RuntimeError("Set a private DEV owner password before promotion")


def media_root(live: bool) -> Path:
    if live:
        return LIVE_ROOT
    os.environ.update(golden.copy_environment(STAGE_COPY, get_settings()))
    get_settings.cache_clear()
    get_engine.cache_clear()
    if golden.configured_copy(get_settings()) != STAGE_COPY:
        raise RuntimeError("unexpected staging target")
    return golden.COPY_ROOT / STAGE_COPY


def ledger(root: Path, action: str) -> None:
    path = root / LEDGER
    if path.is_symlink():
        raise RuntimeError("unexpected media ledger link")
    if action == "read-ledger":
        if path.is_file():
            sys.stdout.buffer.write(path.read_bytes())
        return
    temporary = root / (LEDGER + ".tmp")
    temporary.unlink(missing_ok=True)
    raw = sys.stdin.buffer.read(4 * 1024 * 1024 + 1)
    if raw:
        if len(raw) > 4 * 1024 * 1024:
            raise RuntimeError("oversized media ledger")
        report = json.loads(raw)
        if not isinstance(report, dict):
            raise RuntimeError("invalid media ledger")
        with temporary.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    else:
        path.unlink(missing_ok=True)
    attachments.sync_directory(root)


def collection_state(database: Session, root: Path) -> str:
    if (root / LEDGER).exists():
        return "golden"
    if golden.media_files(root):
        return "occupied"
    tables = inspect(database.connection()).get_table_names()
    if set(tables) - set(Base.metadata.tables) - {"alembic_version", "app_metadata"}:
        return "occupied"
    if database.execute(text("SELECT key, value FROM app_metadata")).all() != [
        ("schema_initialized", "true")
    ]:
        return "occupied"
    if set(golden.table_counts(database)) - {"users", "application_settings"}:
        return "occupied"
    settings = database.get(ApplicationSettings, 1)
    if settings is None or settings.public_qr_base_url or settings.default_label_preset != "medium":
        return "occupied"
    return "empty"


def set_owner_profile(database: Session, owner: User, profile: dict[str, Any]) -> None:
    database.execute(
        update(User)
        .where(User.id == owner.id)
        .values(
            **profile,
            updated_at=User.updated_at,
        )
    )


def verify_promoted(database: Session, root: Path) -> dict[str, Any]:
    # Normalize the two operator-facing fields in this isolated transaction only.
    # The password is already excluded from the baseline, and the fixture UUID stays
    # stable so ownership references still resolve.
    owner = existing_owner(database)
    plan = golden_plan.build_plan("comprehensive")
    fixture = next(node["payload"] for node in plan["nodes"] if node["kind"] == "owner")
    set_owner_profile(
        database,
        owner,
        {
            "login_name": fixture["login_name"],
            "display_name": fixture.get("display_name"),
        },
    )
    # Backups contain original objects. Rebuild only the plan's pinned derivatives in scratch.
    records = (golden.read_ledger(root) or {}).get("records", {})
    copied = golden.planned_copy_ids(plan, records)
    storage = AttachmentStorage(root)
    for asset in database.scalars(select(MediaAsset).where(MediaAsset.attachment_id.is_not(None))):
        if str(asset.id) in copied:
            attachment = database.get(Attachment, asset.attachment_id)
            if attachment is not None:
                asset_thumbnail(storage, asset, attachment)
    return golden.verify_baseline(database, root, plan)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "archive",
            "read-ledger",
            "write-ledger",
            "stage-media",
            "restore-media",
            "verify-media",
            "state",
            "owner-export",
            "owner-import",
            "verify-promoted",
        ),
    )
    parser.add_argument("--live-media", action="store_true")
    args = parser.parse_args()
    root = media_root(args.live_media)
    if args.live_media and args.action not in {
        "archive",
        "read-ledger",
        "write-ledger",
        "restore-media",
    }:
        raise RuntimeError("live media helper has no database operations")
    if args.action == "archive":
        known = {"objects", ".tmp", ".thumbnails", LEDGER}
        for entry in root.iterdir():
            # Keep interrupted restore evidence in place for a subsequent guarded recovery.
            recovery_file = entry.name.startswith((".previous-", ".restore-"))
            if entry.is_symlink() or (entry.name not in known and not recovery_file):
                raise RuntimeError("unexpected entry in DEV attachment storage")
        attachments.archive(root)
    elif args.action in {"read-ledger", "write-ledger"}:
        if args.action == "write-ledger":
            root.mkdir(mode=0o700, parents=True, exist_ok=True)
        ledger(root, args.action)
    elif args.action in {"stage-media", "restore-media"}:
        if args.action == "stage-media":
            if root.exists():
                shutil.rmtree(root)
            root.mkdir(mode=0o700, parents=True)
        attachments.restore()
        # Derived thumbnails may point to earlier objects. The app rebuilds them.
        shutil.rmtree(root / ".thumbnails", ignore_errors=True)
    elif args.action == "verify-media":
        attachments.verify()
    else:
        with Session(get_engine()) as database:
            golden.require_target(get_settings(), database)
            if args.action == "state":
                print(collection_state(database, root))
            elif args.action == "owner-export":
                owner = existing_owner(database)
                require_private_password(owner.password_hash)
                print(json.dumps({field: getattr(owner, field) for field in AUTH_FIELDS}))
            elif args.action == "owner-import":
                owner = existing_owner(database)
                profile = json.load(sys.stdin)
                require_private_password(profile["password_hash"])
                set_owner_profile(database, owner, {field: profile[field] for field in AUTH_FIELDS})
                database.execute(delete(AuthSession))
                database.execute(delete(LoginThrottle))
                database.commit()
            elif args.action == "verify-promoted":
                print(json.dumps(verify_promoted(database, root), sort_keys=True))


if __name__ == "__main__":
    main()
