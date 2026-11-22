"""Read-only production startup guard and explicit release schema maintenance."""

import argparse
import json
import os
import posixpath
import re
import stat
import subprocess
import sys
import time
import uuid
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Connection, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from alembic import command
from florabase.auth.model import User
from florabase.auth.security import normalize_login_name, validate_password
from florabase.auth.service import bootstrap_owner, lock_bootstrap
from florabase.core.config import get_settings
from florabase.db.session import get_engine, get_readiness_engine

# Serialize schema maintenance commands from this image in the selected database.
SCHEMA_LOCK = 721669727
USER_OBJECTS = text("""
    SELECT EXISTS (
        SELECT FROM pg_namespace
        WHERE nspname NOT IN ('public', 'information_schema')
          AND nspname !~ '^pg_'
        UNION ALL
        SELECT FROM pg_depend
        WHERE refclassid = 'pg_namespace'::regclass
          AND refobjid = 'public'::regnamespace
    )
""")


# Mount points of the production compose.yaml backend service (ADR 0008 / ADR 0009).
UPGRADE_FROM = Path("/app/alembic/release-upgrade-from.json")
DATA_DIR = Path("/var/lib/florabase/data")
MEDIA_DIR = DATA_DIR / "media"
STATE_DIR = DATA_DIR / "state"
BACKUP_ROOT = Path("/var/lib/florabase/backup")
BACKUP_DIR = BACKUP_ROOT / "pre-upgrade"
MARKER_NAME = "installation.env"
# Written right before initial schema creation so an interrupted first deploy can retry.
PENDING_NAME = "installation.pending"
# Written if an upgrade fails after dumping so restart loops never write repeated dumps.
UPGRADE_FAILED_NAME = "upgrade-failed.env"
MARKER_KEYS = ("FLORABASE_INSTALLATION_ID", "FLORABASE_PG_MAJOR", "FLORABASE_PG_SYSTEM_ID")
PLACEHOLDER_DB_PASSWORD = "change-me"
PLACEHOLDER_CANONICAL_ORIGIN = "https://florabase.example.org"
MOUNTINFO_PATH = Path("/proc/self/mountinfo")


class SchemaError(Exception):
    pass


Dump = Callable[[Path, str], Path]


def current_heads(connection: Connection) -> tuple[str, ...]:
    return MigrationContext.configure(connection).get_current_heads()


def image_schema(config: Config | None = None) -> tuple[Config, ScriptDirectory, str]:
    if config is None:
        config = Config("/app/alembic.ini")
        config.set_main_option("script_location", "/app/alembic")
    scripts = ScriptDirectory.from_config(config)
    heads = scripts.get_heads()
    if len(heads) != 1:
        raise SchemaError(f"expected a single Alembic head in the image, found {heads}")
    return config, scripts, heads[0]


def require_image_head(connection: Connection, head: str) -> None:
    current = current_heads(connection)
    if current != (head,):
        raise SchemaError(
            f"database revision {current or 'empty'} differs from image head {head}; "
            "use the documented initialization, upgrade or recovery procedure"
        )


def maintain(config: Config, scripts: ScriptDirectory, head: str, previous: str | None) -> None:
    with get_readiness_engine().begin() as connection:
        connection.execute(text("SET LOCAL statement_timeout = 0"))
        connection.execute(text("SET LOCAL lock_timeout = '10s'"))
        connection.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": SCHEMA_LOCK})
        current = current_heads(connection)
        if previous is None:
            if current or connection.scalar(USER_OBJECTS):
                raise SchemaError("initialization requires an empty, unversioned database")
        elif current != (previous,) or previous not in {
            revision.revision for revision in scripts.walk_revisions()
        }:
            raise SchemaError(
                f"upgrade requires the exact previous release head {previous!r} "
                f"in this image's migration history; found {current or 'empty'}"
            )
        config.attributes["connection"] = connection
        command.upgrade(config, head)
        if current_heads(connection) != (head,):
            raise SchemaError(f"migration did not reach image head {head}")


def previous_release_head(path: Path = UPGRADE_FROM) -> str | None:
    """The exact previous release head this image upgrades from, if it declares one."""
    if not path.exists():
        return None
    try:
        head = json.loads(path.read_text())["alembic_head"]
    except ValueError, KeyError, TypeError:
        head = None
    if not isinstance(head, str) or not re.fullmatch(r"[A-Za-z0-9_]+", head):
        raise SchemaError("the image's upgrade declaration is malformed")
    return head


def owner_from_environment(environ: Mapping[str, str]) -> tuple[str, str] | None:
    """Validate the one-time owner variables before anything changes; never echo the password."""
    login = environ.get("FLORABASE_OWNER_LOGIN", "")
    password = environ.get("FLORABASE_OWNER_PASSWORD", "")
    if not login and not password:
        return None
    if not login or not password:
        raise SchemaError(
            "set both FLORABASE_OWNER_LOGIN and FLORABASE_OWNER_PASSWORD, or neither; "
            "nothing was changed"
        )
    try:
        return normalize_login_name(login), validate_password(password)
    except ValueError as error:
        raise SchemaError(f"first owner refused before any change: {error}") from None


def cluster_identity(connection: Connection) -> dict[str, str]:
    major = int(connection.scalar(text("SHOW server_version_num"))) // 10_000
    system = connection.scalar(text("SELECT system_identifier FROM pg_control_system()"))
    return {"FLORABASE_PG_MAJOR": str(major), "FLORABASE_PG_SYSTEM_ID": str(system)}


def read_marker(state_dir: Path) -> dict[str, str] | None:
    path = state_dir / MARKER_NAME
    if path.is_symlink():
        raise SchemaError("the installation marker is malformed; nothing was changed")
    if not path.exists():
        return None
    if not path.is_file():
        raise SchemaError("the installation marker is malformed; nothing was changed")
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        key, separator, value = line.partition("=")
        if not separator or key in values or not re.fullmatch(r"[0-9a-f]+", value):
            raise SchemaError("the installation marker is malformed; nothing was changed")
        values[key] = value
    if set(values) != set(MARKER_KEYS):
        raise SchemaError("the installation marker is malformed; nothing was changed")
    return values


def sync_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_marker(state_dir: Path, identity: dict[str, str]) -> None:
    """Atomically create the installation marker once its cluster and schema both exist.

    A concurrent first deployment may have created it first; it must then describe this cluster.
    """
    values = {"FLORABASE_INSTALLATION_ID": uuid.uuid4().hex, **identity}
    temporary = state_dir / f".{MARKER_NAME}.{values['FLORABASE_INSTALLATION_ID']}.tmp"
    with temporary.open("w") as marker:
        marker.write("".join(f"{key}={values[key]}\n" for key in MARKER_KEYS))
        marker.flush()
        os.fsync(marker.fileno())
    try:
        os.link(temporary, state_dir / MARKER_NAME)  # Exclusive: never replaces a marker.
    except FileExistsError:
        existing = read_marker(state_dir)
        if existing is None or {key: existing[key] for key in identity} != identity:
            raise SchemaError(
                "another installation marker appeared for a different PostgreSQL cluster"
            ) from None
    finally:
        temporary.unlink()
    sync_directory(state_dir)


def reject_placeholder_config(environ: Mapping[str, str]) -> None:
    """Refuse compose.yaml placeholder password or origin before touching disk or PostgreSQL."""
    if (
        environ.get("FLORABASE_DB_PASSWORD") == PLACEHOLDER_DB_PASSWORD
        or environ.get("PGPASSWORD") == PLACEHOLDER_DB_PASSWORD
    ):
        raise SchemaError(
            "FLORABASE_DB_PASSWORD is still the placeholder 'change-me'; "
            "set a strong password (see docs/installation.md)"
        )
    origin = environ.get("FLORABASE_CANONICAL_ORIGIN", "").strip().rstrip("/")
    if origin == PLACEHOLDER_CANONICAL_ORIGIN:
        raise SchemaError(
            "FLORABASE_CANONICAL_ORIGIN is still the placeholder "
            f"{PLACEHOLDER_CANONICAL_ORIGIN!r}; "
            "set your real HTTPS origin (see docs/installation.md)"
        )


def _decode_mountinfo_field(value: str) -> str:
    return re.sub(r"\\([0-7]{3})", lambda match: chr(int(match.group(1), 8)), value)


def _parse_mountinfo_line(line: str) -> tuple[str, str, str, str, str] | None:
    """Return (major_minor, root, mount_point, fstype, source) or None if malformed."""
    left, separator, right = line.partition(" - ")
    if not separator:
        return None
    left_fields = left.split()
    right_fields = right.split()
    if len(left_fields) < 6 or len(right_fields) < 2:
        return None
    dev = left_fields[2]
    root = posixpath.normpath(_decode_mountinfo_field(left_fields[3]))
    mount_point = posixpath.normpath(_decode_mountinfo_field(left_fields[4]))
    fstype = _decode_mountinfo_field(right_fields[0])
    source = _decode_mountinfo_field(right_fields[1])
    if not root.startswith("/") or not mount_point.startswith("/"):
        return None
    return dev, root, mount_point, fstype, source


def _is_nested_path(child: str, parent: str) -> bool:
    if parent == "/":
        return child != "/"
    return child.startswith(parent + "/")


def check_mountinfo_nesting(
    data_dir: Path,
    backup_root: Path,
    mountinfo_path: Path = MOUNTINFO_PATH,
) -> None:
    """Detect identical or nested bind mounts via mountinfo; warn and continue if indeterminate."""
    try:
        text_content = mountinfo_path.read_text()
    except OSError:
        sys.stderr.write(
            "schema-guard: warning: could not read mountinfo to verify data/backup mount nesting; "
            "continuing\n"
        )
        return
    data_target = posixpath.normpath(str(data_dir))
    backup_target = posixpath.normpath(str(backup_root))
    mounts: dict[str, tuple[str, str, str, str]] = {}
    malformed = False
    for raw_line in text_content.splitlines():
        if not raw_line.strip():
            continue
        parsed = _parse_mountinfo_line(raw_line)
        if parsed is None:
            malformed = True
            continue
        dev, root, mount_point, fstype, source = parsed
        if mount_point in (data_target, backup_target):
            mounts[mount_point] = (dev, root, fstype, source)
    if data_target not in mounts or backup_target not in mounts:
        reason = "malformed mountinfo" if malformed else "data/backup mount entries not found"
        sys.stderr.write(
            f"schema-guard: warning: mount nesting check indeterminate ({reason}); continuing\n"
        )
        return
    data_dev, data_root, data_fs, data_src = mounts[data_target]
    backup_dev, backup_root_path, backup_fs, backup_src = mounts[backup_target]
    same_fs = data_dev == backup_dev or (
        data_fs == "btrfs" and backup_fs == "btrfs" and bool(data_src) and data_src == backup_src
    )
    if not same_fs:
        return
    if data_root == backup_root_path:
        raise SchemaError("the data and backup folders are the same")
    if _is_nested_path(data_root, backup_root_path):
        raise SchemaError("the data folder is inside the backup folder")
    if _is_nested_path(backup_root_path, data_root):
        raise SchemaError("the backup folder is inside the data folder")


def validate_host_paths(
    data_dir: Path | None,
    backup_root: Path | None,
    *,
    mountinfo_path: Path = MOUNTINFO_PATH,
) -> None:
    """Refuse identical or nested data and backup folders before any migration."""
    if data_dir is not None and backup_root is not None:
        try:
            data_stat = os.stat(data_dir)
            backup_stat = os.stat(backup_root)
        except OSError:
            return
        if (data_stat.st_dev, data_stat.st_ino) == (backup_stat.st_dev, backup_stat.st_ino):
            raise SchemaError("the data and backup folders are the same")
        check_mountinfo_nesting(data_dir, backup_root, mountinfo_path=mountinfo_path)


def _require_writable_dir(path: Path, label: str, *, require_private_owner: bool = False) -> None:
    if path.is_symlink() or not path.is_dir() or not os.access(path, os.R_OK | os.W_OK | os.X_OK):
        raise SchemaError(
            f"{label} {path} is missing or not writable; "
            "run the folder setup commands in docs/installation.md"
        )
    if require_private_owner:
        info = path.stat()
        if info.st_uid != os.geteuid() or (stat.S_IMODE(info.st_mode) & 0o077) != 0:
            raise SchemaError(
                f"{label} {path} has unsafe owner or mode; "
                "run the folder setup commands in docs/installation.md"
            )


def check_upgrade_failed(state_dir: Path) -> None:
    """Refuse restarts after a failed upgrade so no repeated dumps or retries occur."""
    path = state_dir / UPGRADE_FAILED_NAME
    if not path.exists() and not path.is_symlink():
        return
    values: dict[str, str] = {}
    if not path.is_symlink() and path.is_file():
        try:
            for line in path.read_text().splitlines():
                key, separator, value = line.partition("=")
                if separator and key:
                    values[key] = value
        except OSError:
            pass
    source = values.get("FLORABASE_UPGRADE_FROM", "unknown")
    target = values.get("FLORABASE_UPGRADE_TO", "unknown")
    dump_name = values.get("FLORABASE_UPGRADE_DUMP", "unknown")
    raise SchemaError(
        f"previous upgrade from {source} to {target} failed (pre-upgrade backup: {dump_name}); "
        f"resolve the cause and remove state/{UPGRADE_FAILED_NAME} before redeploying"
    )


def write_upgrade_failed(
    state_dir: Path, previous: str, head: str, dump_name: str, detail: str
) -> None:
    payload = (
        f"FLORABASE_UPGRADE_FROM={previous}\n"
        f"FLORABASE_UPGRADE_TO={head}\n"
        f"FLORABASE_UPGRADE_DUMP={dump_name}\n"
        f"FLORABASE_UPGRADE_ERROR={detail}\n"
    )
    temporary = state_dir / f".{UPGRADE_FAILED_NAME}.{uuid.uuid4().hex}.tmp"
    try:
        with temporary.open("w") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, state_dir / UPGRADE_FAILED_NAME)
        sync_directory(state_dir)
    except OSError:
        temporary.unlink(missing_ok=True)
        sys.stderr.write(f"schema-guard: warning: could not write state/{UPGRADE_FAILED_NAME}\n")


def _error_summary(error: Exception) -> str:
    sqlstate = getattr(error.orig, "sqlstate", None) if isinstance(error, DBAPIError) else None
    return f"{type(error).__name__}, SQLSTATE {sqlstate}" if sqlstate else type(error).__name__


def wait_for_database(*, timeout_seconds: float = 60.0, interval_seconds: float = 1.0) -> None:
    """Wait for PostgreSQL to accept connections with a bounded pg_isready retry loop."""
    url = make_url(get_settings().database_url)
    probe = [
        "pg_isready",
        f"--host={url.host or 'localhost'}",
        f"--port={url.port or 5432}",
        f"--username={url.username or ''}",
        f"--dbname={url.database or ''}",
    ]
    deadline = time.monotonic() + timeout_seconds
    while True:
        result = subprocess.run(probe, check=False, capture_output=True)
        if result.returncode == 0:
            return
        if time.monotonic() >= deadline:
            raise SchemaError("database is not ready; check db logs and configuration")
        time.sleep(min(interval_seconds, max(0.0, deadline - time.monotonic())))


def dump_database(backup_dir: Path, name: str) -> Path:
    """Write and verify a custom-format dump; any failure refuses the upgrade."""
    if not backup_dir.is_dir() or not os.access(backup_dir, os.W_OK | os.X_OK):
        raise SchemaError(
            f"backup directory {backup_dir} is missing or not writable; nothing was migrated"
        )
    url = make_url(get_settings().database_url)
    environment = dict(os.environ)
    environment.pop("FLORABASE_OWNER_LOGIN", None)
    environment.pop("FLORABASE_OWNER_PASSWORD", None)
    if url.password:
        environment["PGPASSWORD"] = str(url.password)
    elif not environment.get("PGPASSWORD") and environment.get("FLORABASE_DB_PASSWORD"):
        environment["PGPASSWORD"] = environment["FLORABASE_DB_PASSWORD"]
    connection = [
        f"--host={url.host or 'localhost'}",
        f"--port={url.port or 5432}",
        f"--username={url.username or ''}",
        f"--dbname={url.database or ''}",
    ]
    partial, target = backup_dir / f".{name}.partial", backup_dir / name
    try:
        subprocess.run(
            ["pg_dump", "--format=custom", f"--file={partial}", *connection],
            check=True,
            env=environment,
        )
        listing = subprocess.run(
            ["pg_restore", "--list", str(partial)], check=True, capture_output=True, text=True
        ).stdout
        if not any(line and not line.startswith(";") for line in listing.splitlines()):
            raise SchemaError("the pre-upgrade backup has an empty table of contents")
        os.replace(partial, target)
        sync_directory(backup_dir)
    except (OSError, subprocess.CalledProcessError, SchemaError) as error:
        partial.unlink(missing_ok=True)
        detail = str(error) if isinstance(error, SchemaError) else type(error).__name__
        raise SchemaError(f"pre-upgrade backup failed ({detail}); nothing was migrated") from None
    return target


def deploy(
    config: Config,
    scripts: ScriptDirectory,
    head: str,
    previous: str | None,
    *,
    state_dir: Path = STATE_DIR,
    backup_dir: Path = BACKUP_DIR,
    media_dir: Path | None = None,
    data_dir: Path | None = None,
    backup_root: Path | None = None,
    mountinfo_path: Path = MOUNTINFO_PATH,
    strict_backup_permissions: bool = False,
    dump: Dump = dump_database,
) -> None:
    """Initialize, keep, or back up and upgrade the schema; refuse anything else (ADR 0008/0009)."""
    validate_host_paths(data_dir, backup_root, mountinfo_path=mountinfo_path)
    _require_writable_dir(state_dir, "state directory")
    check_upgrade_failed(state_dir)
    marker = read_marker(state_dir)
    pending = (state_dir / PENDING_NAME).exists()
    if media_dir is not None:
        _require_writable_dir(media_dir, "media directory")
        if marker is None and not pending and any(media_dir.iterdir()):
            raise SchemaError(
                f"{media_dir} is not empty and there is no installation marker; "
                "use an empty data folder"
            )
    _require_writable_dir(
        backup_dir, "backup directory", require_private_owner=strict_backup_permissions
    )
    upgrading_dump: str | None = None
    try:
        with get_readiness_engine().begin() as connection:
            connection.execute(text("SET LOCAL statement_timeout = 0"))
            connection.execute(text("SET LOCAL lock_timeout = '10s'"))
            connection.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": SCHEMA_LOCK})
            identity = cluster_identity(connection)
            if marker is not None and {key: marker[key] for key in identity} != identity:
                raise SchemaError(
                    "the installation marker does not match this PostgreSQL cluster; "
                    "nothing was changed"
                )
            current = current_heads(connection)
            empty = not current and not connection.scalar(USER_OBJECTS)
            if marker is not None and empty:
                raise SchemaError(
                    "the installation marker exists but the database is empty; restore it instead "
                    "of initializing a new one"
                )
            if marker is None and not empty and not (pending and current == (head,)):
                raise SchemaError(
                    "the database has data but no installation marker; restore into a new data "
                    "directory instead"
                )
            history = {revision.revision for revision in scripts.walk_revisions()}
            upgrade = (
                previous is not None
                and previous != head
                and previous in history
                and current == (previous,)
            )
            if not empty and current != (head,) and not upgrade:
                raise SchemaError(
                    f"database revision {current or 'unknown'} is neither image head {head} "
                    f"nor the previous release head {previous}; nothing was changed"
                )
            if upgrade:
                stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
                dump_path = dump(backup_dir, f"florabase-{previous}-to-{head}-{stamp}.dump")
                sys.stdout.write(f"schema-guard: pre-upgrade backup verified: {dump_path.name}\n")
                upgrading_dump = dump_path.name
            if empty and marker is None and not pending:
                (state_dir / PENDING_NAME).touch(exist_ok=True)
                sync_directory(state_dir)
            if empty or upgrade:
                config.attributes["connection"] = connection
                command.upgrade(config, head)
                if current_heads(connection) != (head,):
                    raise SchemaError(f"migration did not reach image head {head}")
    except Exception as error:
        if upgrading_dump is not None and previous is not None:
            write_upgrade_failed(state_dir, previous, head, upgrading_dump, _error_summary(error))
        raise
    if marker is None:
        write_marker(state_dir, identity)
        (state_dir / PENDING_NAME).unlink(missing_ok=True)


def create_first_owner(owner: tuple[str, str] | None) -> None:
    """Create the owner once, only while no user exists (ADR 0005 single-owner lock)."""
    if owner is None:
        return
    with Session(get_engine()) as database, database.begin():
        lock_bootstrap(database)
        if database.scalar(select(User.id).limit(1)) is not None:
            sys.stdout.write(
                "schema-guard: users already exist; FLORABASE_OWNER_LOGIN and "
                "FLORABASE_OWNER_PASSWORD were ignored and can be removed\n"
            )
            return
        bootstrap_owner(database, *owner)
    sys.stdout.write(
        f"schema-guard: first owner {owner[0]} created; remove FLORABASE_OWNER_PASSWORD from "
        "the stack environment and change the password at first sign-in\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("serve")
    actions.add_parser("deploy")
    actions.add_parser("wait-db")
    actions.add_parser("init")
    upgrade = actions.add_parser("upgrade")
    upgrade.add_argument("previous_head")
    args = parser.parse_args()
    try:
        if args.action == "wait-db":
            reject_placeholder_config(os.environ)
            wait_for_database()
            return 0
        config, scripts, head = image_schema()
        if args.action == "serve":
            reject_placeholder_config(os.environ)
            with get_readiness_engine().connect() as connection:
                require_image_head(connection, head)
        elif args.action == "deploy":
            reject_placeholder_config(os.environ)
            owner = owner_from_environment(os.environ)
            deploy(
                config,
                scripts,
                head,
                previous_release_head(),
                media_dir=MEDIA_DIR,
                data_dir=DATA_DIR,
                backup_root=BACKUP_ROOT,
                strict_backup_permissions=True,
            )
            create_first_owner(owner)
        else:
            previous = args.previous_head if args.action == "upgrade" else None
            maintain(config, scripts, head, previous)
    except SchemaError as error:
        sys.stderr.write(f"schema-guard: {error}\n")
        return 1
    except Exception as error:
        # Settings and driver exceptions can include submitted credentials.
        sqlstate = getattr(error.orig, "sqlstate", None) if isinstance(error, DBAPIError) else None
        detail = f", SQLSTATE {sqlstate}" if sqlstate else ""
        sys.stderr.write(
            f"schema-guard: {args.action} failed ({type(error).__name__}{detail}); "
            "check database connectivity, configuration and migration prerequisites\n"
        )
        return 1
    if args.action == "serve":
        os.execvp(
            "uvicorn",
            [
                "uvicorn",
                "florabase.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
                "--no-server-header",
                "--no-proxy-headers",
            ],
        )
    sys.stdout.write(f"schema-guard: database at image head {head}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
