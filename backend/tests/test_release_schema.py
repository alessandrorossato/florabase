import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from psycopg.errors import DuplicateTable
from sqlalchemy.exc import ProgrammingError

from florabase.db import release_schema

HEAD = "image_head"
PREVIOUS = "previous_head"


@pytest.fixture
def schema(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    scripts = MagicMock()
    scripts.get_heads.return_value = [HEAD]
    scripts.walk_revisions.return_value = [SimpleNamespace(revision=PREVIOUS)]
    monkeypatch.setattr(
        "florabase.db.release_schema.ScriptDirectory.from_config", lambda _: scripts
    )

    engine = MagicMock()
    connection = MagicMock()
    connection.scalar.return_value = False
    engine.connect.return_value.__enter__.return_value = connection
    engine.begin.return_value.__enter__.return_value = connection
    monkeypatch.setattr(release_schema, "get_readiness_engine", lambda: engine)
    context = MagicMock()
    context.get_current_heads.return_value = (HEAD,)
    monkeypatch.setattr("florabase.db.release_schema.MigrationContext.configure", lambda _: context)

    upgrade = MagicMock()
    exec_server = MagicMock()
    monkeypatch.setattr("florabase.db.release_schema.command.upgrade", upgrade)
    monkeypatch.setattr("florabase.db.release_schema.os.execvp", exec_server)
    return SimpleNamespace(
        scripts=scripts,
        engine=engine,
        connection=connection,
        current=context.get_current_heads,
        upgrade=upgrade,
        exec_server=exec_server,
    )


def invoke(monkeypatch: pytest.MonkeyPatch, *args: str) -> int:
    monkeypatch.setattr(sys, "argv", ["release_schema", *args])
    return release_schema.main()


def test_serve_only_checks_schema_and_launches_server(
    schema: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert invoke(monkeypatch, "serve") == 0

    schema.engine.connect.assert_called_once_with()
    schema.engine.begin.assert_not_called()
    schema.connection.execute.assert_not_called()
    schema.upgrade.assert_not_called()
    program, arguments = schema.exec_server.call_args.args
    assert program == "uvicorn"
    assert "florabase.main:app" in arguments
    assert "--no-proxy-headers" in arguments


@pytest.mark.parametrize("current", [(), (PREVIOUS,), ("foreign",), (HEAD, "other_head")])
def test_serve_refuses_any_schema_other_than_image_head(
    schema: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    current: tuple[str, ...],
) -> None:
    schema.current.return_value = current

    assert invoke(monkeypatch, "serve") == 1

    assert "differs from image head" in capsys.readouterr().err
    schema.exec_server.assert_not_called()
    schema.upgrade.assert_not_called()


def test_serve_refuses_image_with_multiple_heads(
    schema: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    schema.scripts.get_heads.return_value = [HEAD, "other_head"]

    assert invoke(monkeypatch, "serve") == 1

    assert "expected a single Alembic head" in capsys.readouterr().err
    schema.engine.connect.assert_not_called()


@pytest.mark.parametrize(("current", "user_objects"), [((PREVIOUS,), False), ((), True)])
def test_init_refuses_an_existing_database(
    schema: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    current: tuple[str, ...],
    user_objects: bool,
) -> None:
    schema.current.return_value = current
    schema.connection.scalar.return_value = user_objects

    assert invoke(monkeypatch, "init") == 1

    assert "requires an empty, unversioned database" in capsys.readouterr().err
    schema.upgrade.assert_not_called()


@pytest.mark.parametrize("args", [("init",), ("upgrade", PREVIOUS)])
def test_maintenance_uses_one_transaction_and_checks_the_result(
    schema: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, args: tuple[str, ...]
) -> None:
    schema.current.side_effect = [() if args == ("init",) else (PREVIOUS,), (HEAD,)]

    assert invoke(monkeypatch, *args) == 0

    schema.engine.begin.assert_called_once_with()
    lock = schema.connection.execute.call_args_list[-1]
    assert "pg_advisory_xact_lock" in str(lock.args[0])
    assert lock.args[1] == {"key": release_schema.SCHEMA_LOCK}
    schema.exec_server.assert_not_called()
    config, target = schema.upgrade.call_args.args
    assert target == HEAD
    assert config.attributes["connection"] is schema.connection


@pytest.mark.parametrize("current", [(), (HEAD,), ("foreign",)])
def test_upgrade_refuses_a_wrong_or_unknown_previous_head(
    schema: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    current: tuple[str, ...],
) -> None:
    schema.current.return_value = current
    previous = "foreign" if current == ("foreign",) else PREVIOUS

    assert invoke(monkeypatch, "upgrade", previous) == 1

    assert "migration history" in capsys.readouterr().err
    schema.upgrade.assert_not_called()


def test_maintenance_refuses_a_missing_result_revision(
    schema: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    schema.current.return_value = (PREVIOUS,)

    assert invoke(monkeypatch, "upgrade", PREVIOUS) == 1

    assert "migration did not reach image head" in capsys.readouterr().err


def test_driver_error_reports_sqlstate_without_exception_details(
    schema: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    schema.current.return_value = (PREVIOUS,)
    detail = "sensitive connection details"
    schema.upgrade.side_effect = ProgrammingError(detail, None, DuplicateTable(detail))

    assert invoke(monkeypatch, "upgrade", PREVIOUS) == 1

    message = capsys.readouterr().err
    assert "SQLSTATE 42P07" in message
    assert detail not in message
    schema.exec_server.assert_not_called()


IDENTITY = {"FLORABASE_PG_MAJOR": "18", "FLORABASE_PG_SYSTEM_ID": "7710579520300167193"}


def cluster(schema: SimpleNamespace, *, user_objects: bool = False) -> None:
    def scalar(statement: object, *_: object) -> object:
        sql = str(statement)
        if "server_version_num" in sql:
            return "180006"
        if "pg_control_system" in sql:
            return int(IDENTITY["FLORABASE_PG_SYSTEM_ID"])
        return user_objects

    schema.connection.scalar.side_effect = scalar


def marked(state: Path, **override: str) -> Path:
    values = {"FLORABASE_INSTALLATION_ID": "ab12", **IDENTITY, **override}
    (state / release_schema.MARKER_NAME).write_text(
        "".join(f"{key}={values[key]}\n" for key in release_schema.MARKER_KEYS)
    )
    return state


def deploy(
    schema: SimpleNamespace,
    state: Path,
    previous: str | None = PREVIOUS,
    dump: MagicMock | None = None,
) -> MagicMock:
    dump = dump or MagicMock(side_effect=lambda directory, name: directory / name)
    release_schema.deploy(
        MagicMock(attributes={}),
        schema.scripts,
        HEAD,
        previous,
        state_dir=state,
        backup_dir=state,
        dump=dump,
    )
    return dump


def test_deploy_initializes_an_empty_database_then_writes_the_marker(
    schema: SimpleNamespace, tmp_path: Path
) -> None:
    cluster(schema)
    schema.current.side_effect = [(), (HEAD,)]

    dump = deploy(schema, tmp_path)

    dump.assert_not_called()
    assert schema.upgrade.call_args.args[1] == HEAD
    marker = release_schema.read_marker(tmp_path)
    assert marker is not None
    assert {key: marker[key] for key in IDENTITY} == IDENTITY
    assert not list(tmp_path.glob(".*.tmp"))


def test_deploy_keeps_an_at_head_database_unchanged(
    schema: SimpleNamespace, tmp_path: Path
) -> None:
    cluster(schema, user_objects=True)
    before = marked(tmp_path).joinpath(release_schema.MARKER_NAME).read_text()

    dump = deploy(schema, tmp_path, previous=HEAD)

    dump.assert_not_called()
    schema.upgrade.assert_not_called()
    assert (tmp_path / release_schema.MARKER_NAME).read_text() == before


def test_deploy_dumps_before_upgrading_from_the_previous_release_head(
    schema: SimpleNamespace, tmp_path: Path
) -> None:
    cluster(schema, user_objects=True)
    schema.current.side_effect = [(PREVIOUS,), (HEAD,)]
    order: list[str] = []

    def record_dump(directory: Path, name: str) -> Path:
        order.append("dump")
        return directory / name

    dump = MagicMock(side_effect=record_dump)
    schema.upgrade.side_effect = lambda *_: order.append("upgrade")

    deploy(schema, marked(tmp_path), dump=dump)

    assert order == ["dump", "upgrade"]
    name = dump.call_args.args[1]
    assert name.startswith(f"florabase-{PREVIOUS}-to-{HEAD}-")
    assert name.endswith(".dump")


def test_deploy_refuses_the_upgrade_when_the_backup_fails(
    schema: SimpleNamespace, tmp_path: Path
) -> None:
    cluster(schema, user_objects=True)
    schema.current.return_value = (PREVIOUS,)
    dump = MagicMock(side_effect=release_schema.SchemaError("pre-upgrade backup failed"))

    with pytest.raises(release_schema.SchemaError, match="backup failed"):
        deploy(schema, marked(tmp_path), dump=dump)

    schema.upgrade.assert_not_called()


@pytest.mark.parametrize(
    ("current", "marker", "message"),
    [
        ((HEAD,), None, "no installation marker"),
        ((HEAD,), {"FLORABASE_PG_SYSTEM_ID": "1"}, "does not match"),
        ((HEAD,), {"FLORABASE_PG_MAJOR": "17"}, "does not match"),
        (("foreign",), {}, "neither image head"),
        (("newer",), {}, "neither image head"),
    ],
)
def test_deploy_refuses_unknown_states_without_changes(
    schema: SimpleNamespace,
    tmp_path: Path,
    current: tuple[str, ...],
    marker: dict[str, str] | None,
    message: str,
) -> None:
    cluster(schema, user_objects=True)
    schema.current.return_value = current
    if marker is not None:
        marked(tmp_path, **marker)
    dump = MagicMock()

    with pytest.raises(release_schema.SchemaError, match=message):
        deploy(schema, tmp_path, dump=dump)

    dump.assert_not_called()
    schema.upgrade.assert_not_called()


def test_deploy_refuses_an_unwritable_state_directory_before_connecting(
    schema: SimpleNamespace, tmp_path: Path
) -> None:
    tmp_path.chmod(0o500)
    try:
        with pytest.raises(release_schema.SchemaError, match="not writable"):
            deploy(schema, tmp_path)
    finally:
        tmp_path.chmod(0o700)
    schema.engine.begin.assert_not_called()


@pytest.mark.parametrize(
    "content", ["", "FLORABASE_PG_MAJOR=18\n", "garbage\n", "FLORABASE_PG_MAJOR=$(id)\n"]
)
def test_malformed_marker_is_refused(tmp_path: Path, content: str) -> None:
    (tmp_path / release_schema.MARKER_NAME).write_text(content)

    with pytest.raises(release_schema.SchemaError, match="malformed"):
        release_schema.read_marker(tmp_path)


def test_owner_variables_are_validated_without_echoing_the_password() -> None:
    secret = "short-secret"[:8]
    assert release_schema.owner_from_environment({}) is None
    assert release_schema.owner_from_environment(
        {"FLORABASE_OWNER_LOGIN": " Owner ", "FLORABASE_OWNER_PASSWORD": "correct horse battery"}
    ) == ("owner", "correct horse battery")
    for environ in (
        {"FLORABASE_OWNER_LOGIN": "owner"},
        {"FLORABASE_OWNER_PASSWORD": secret},
        {"FLORABASE_OWNER_LOGIN": "owner", "FLORABASE_OWNER_PASSWORD": secret},
    ):
        with pytest.raises(release_schema.SchemaError) as refused:
            release_schema.owner_from_environment(environ)
        assert secret not in str(refused.value)


def test_deploy_command_refuses_partial_owner_variables_before_any_change(
    schema: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("FLORABASE_OWNER_LOGIN", "owner")
    monkeypatch.delenv("FLORABASE_OWNER_PASSWORD", raising=False)

    assert invoke(monkeypatch, "deploy") == 1

    assert "or neither" in capsys.readouterr().err
    schema.engine.begin.assert_not_called()


def test_dump_refuses_a_missing_backup_directory(tmp_path: Path) -> None:
    with pytest.raises(release_schema.SchemaError, match="missing or not writable"):
        release_schema.dump_database(tmp_path / "absent", "florabase.dump")


def test_dump_refuses_an_unwritable_backup_directory(tmp_path: Path) -> None:
    tmp_path.chmod(0o500)
    try:
        with pytest.raises(release_schema.SchemaError, match="missing or not writable"):
            release_schema.dump_database(tmp_path, "florabase.dump")
    finally:
        tmp_path.chmod(0o700)


def test_failed_dump_leaves_no_partial_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def failing(command: list[str], **_: object) -> None:
        Path(command[2].removeprefix("--file=")).write_bytes(b"partial")
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(subprocess, "run", failing)

    with pytest.raises(release_schema.SchemaError, match="nothing was migrated"):
        release_schema.dump_database(tmp_path, "florabase.dump")

    assert list(tmp_path.iterdir()) == []


def test_previous_release_head_declaration(tmp_path: Path) -> None:
    assert release_schema.previous_release_head(tmp_path / "absent.json") is None
    declared = Path(__file__).parents[1] / "alembic/release-upgrade-from.json"
    assert (
        release_schema.previous_release_head(declared)
        == json.loads(declared.read_text())["alembic_head"]
    )
    (tmp_path / "bad.json").write_text('{"alembic_head": "../x"}')
    with pytest.raises(release_schema.SchemaError, match="malformed"):
        release_schema.previous_release_head(tmp_path / "bad.json")


def test_deploy_resumes_a_pending_first_installation_at_head(
    schema: SimpleNamespace, tmp_path: Path
) -> None:
    cluster(schema, user_objects=True)
    (tmp_path / release_schema.PENDING_NAME).touch()

    deploy(schema, tmp_path)

    schema.upgrade.assert_not_called()
    assert release_schema.read_marker(tmp_path) is not None
    assert not (tmp_path / release_schema.PENDING_NAME).exists()


def test_pending_installation_still_refuses_a_foreign_revision(
    schema: SimpleNamespace, tmp_path: Path
) -> None:
    cluster(schema, user_objects=True)
    schema.current.return_value = ("foreign",)
    (tmp_path / release_schema.PENDING_NAME).touch()

    with pytest.raises(release_schema.SchemaError, match="no installation marker"):
        deploy(schema, tmp_path)

    assert release_schema.read_marker(tmp_path) is None


def test_deploy_refuses_an_empty_database_of_a_recorded_installation(
    schema: SimpleNamespace, tmp_path: Path
) -> None:
    cluster(schema)
    schema.current.return_value = ()

    with pytest.raises(release_schema.SchemaError, match="database is empty"):
        deploy(schema, marked(tmp_path))

    schema.upgrade.assert_not_called()


def test_marker_is_created_exclusively_and_a_concurrent_one_must_match(tmp_path: Path) -> None:
    release_schema.write_marker(tmp_path, IDENTITY)
    first = (tmp_path / release_schema.MARKER_NAME).read_text()

    release_schema.write_marker(tmp_path, IDENTITY)
    assert (tmp_path / release_schema.MARKER_NAME).read_text() == first

    with pytest.raises(release_schema.SchemaError, match="different PostgreSQL cluster"):
        release_schema.write_marker(tmp_path, {**IDENTITY, "FLORABASE_PG_SYSTEM_ID": "1"})
    assert sorted(path.name for path in tmp_path.iterdir()) == [release_schema.MARKER_NAME]


def test_validate_host_paths_refuses_same_inode(tmp_path: Path) -> None:
    data = tmp_path / "data"
    backup = tmp_path / "backup"
    data.mkdir()
    backup.mkdir()
    mountinfo = tmp_path / "mountinfo"
    mountinfo.write_text(
        f"101 50 8:1 /srv/data {data} rw - ext4 /dev/sda1 rw\n"
        f"102 50 8:1 /srv/backup {backup} rw - ext4 /dev/sda1 rw\n"
    )
    release_schema.validate_host_paths(data, backup, mountinfo_path=mountinfo)
    with pytest.raises(release_schema.SchemaError, match="same"):
        release_schema.validate_host_paths(data, data, mountinfo_path=mountinfo)


def test_read_marker_refuses_symlinks_and_directories(tmp_path: Path) -> None:
    target = tmp_path / "other"
    target.write_text("FLORABASE_INSTALLATION_ID=ab12\n")
    (tmp_path / release_schema.MARKER_NAME).symlink_to(target)
    with pytest.raises(release_schema.SchemaError, match="malformed"):
        release_schema.read_marker(tmp_path)
    (tmp_path / release_schema.MARKER_NAME).unlink()
    (tmp_path / release_schema.MARKER_NAME).mkdir()
    with pytest.raises(release_schema.SchemaError, match="malformed"):
        release_schema.read_marker(tmp_path)


def test_deploy_refuses_non_private_backup_mode_when_strict(
    schema: SimpleNamespace, tmp_path: Path
) -> None:
    state = tmp_path / "state"
    backup = tmp_path / "backup"
    state.mkdir(mode=0o755)
    backup.mkdir(mode=0o755)
    backup.chmod(0o755)

    with pytest.raises(release_schema.SchemaError, match=r"unsafe owner or mode.*installation\.md"):
        release_schema.deploy(
            MagicMock(attributes={}),
            schema.scripts,
            HEAD,
            PREVIOUS,
            state_dir=state,
            backup_dir=backup,
            strict_backup_permissions=True,
        )
    schema.engine.begin.assert_not_called()


def test_dump_database_strips_owner_variables_from_subprocess_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen_env: dict[str, str] = {}

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        if command[0] == "pg_dump":
            env = kwargs.get("env")
            assert isinstance(env, dict)
            seen_env.update(env)
            Path(command[2].removeprefix("--file=")).write_bytes(b"PGDMP")
            return SimpleNamespace(stdout="")
        return SimpleNamespace(stdout="1; 0 0 TABLE public users\n")

    monkeypatch.setattr(
        release_schema,
        "get_settings",
        lambda: SimpleNamespace(database_url="postgresql+psycopg://florabase@db:5432/florabase"),
    )
    monkeypatch.setenv("FLORABASE_OWNER_LOGIN", "owner")
    monkeypatch.setenv("FLORABASE_OWNER_PASSWORD", "secret-owner-pw")
    monkeypatch.setenv("FLORABASE_DB_PASSWORD", "db-secret")
    monkeypatch.delenv("PGPASSWORD", raising=False)
    monkeypatch.setattr(subprocess, "run", fake_run)

    path = release_schema.dump_database(tmp_path, "test.dump")
    assert path.exists()
    assert seen_env["PGPASSWORD"] == "db-secret"
    assert "FLORABASE_OWNER_LOGIN" not in seen_env
    assert "FLORABASE_OWNER_PASSWORD" not in seen_env


def test_deploy_refuses_non_empty_media_without_marker(
    schema: SimpleNamespace, tmp_path: Path
) -> None:
    state = tmp_path / "state"
    media = tmp_path / "media"
    backup = tmp_path / "backup"
    for folder in (state, media, backup):
        folder.mkdir()
    (media / "stray").write_text("data")

    with pytest.raises(release_schema.SchemaError, match="not empty and there is no installation"):
        release_schema.deploy(
            MagicMock(attributes={}),
            schema.scripts,
            HEAD,
            PREVIOUS,
            state_dir=state,
            backup_dir=backup,
            media_dir=media,
        )
    schema.engine.begin.assert_not_called()


def test_deploy_refuses_missing_or_unwritable_backup_dir_before_connecting(
    schema: SimpleNamespace, tmp_path: Path
) -> None:
    state = tmp_path / "state"
    state.mkdir()

    with pytest.raises(release_schema.SchemaError, match=r"docs/installation\.md"):
        release_schema.deploy(
            MagicMock(attributes={}),
            schema.scripts,
            HEAD,
            PREVIOUS,
            state_dir=state,
            backup_dir=tmp_path / "missing-backup",
        )
    schema.engine.begin.assert_not_called()


def test_failed_upgrade_latches_upgrade_failed_env_and_blocks_repeated_dumps(
    schema: SimpleNamespace, tmp_path: Path
) -> None:
    cluster(schema, user_objects=True)
    schema.current.return_value = (PREVIOUS,)
    schema.upgrade.side_effect = ProgrammingError("boom", None, DuplicateTable("dup"))
    marked(tmp_path)
    dump = MagicMock(side_effect=lambda directory, name: directory / name)

    with pytest.raises(ProgrammingError):
        deploy(schema, tmp_path, dump=dump)

    latch = tmp_path / release_schema.UPGRADE_FAILED_NAME
    assert latch.is_file()
    text = latch.read_text()
    assert f"FLORABASE_UPGRADE_FROM={PREVIOUS}\n" in text
    assert f"FLORABASE_UPGRADE_TO={HEAD}\n" in text
    assert "SQLSTATE 42P07" in text
    assert dump.call_count == 1

    # Simulated container restart: refuses immediately and performs zero additional dumps.
    with pytest.raises(release_schema.SchemaError, match=r"remove state/upgrade-failed\.env"):
        deploy(schema, tmp_path, dump=dump)
    assert dump.call_count == 1

    # After operator fixes cause and removes latch, retry succeeds cleanly.
    latch.unlink()
    schema.upgrade.side_effect = None
    schema.current.side_effect = [(PREVIOUS,), (HEAD,)]
    deploy(schema, tmp_path, dump=dump)
    assert dump.call_count == 2


def test_wait_for_database_retries_until_ready_or_times_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("florabase.db.release_schema.time.sleep", lambda _: None)
    results = iter([SimpleNamespace(returncode=1), SimpleNamespace(returncode=0)])
    monkeypatch.setattr(subprocess, "run", lambda *_, **__: next(results))
    release_schema.wait_for_database(timeout_seconds=5.0, interval_seconds=0.1)

    monkeypatch.setattr(subprocess, "run", lambda *_, **__: SimpleNamespace(returncode=1))
    with pytest.raises(release_schema.SchemaError, match="database is not ready"):
        release_schema.wait_for_database(timeout_seconds=0.0, interval_seconds=0.0)


def test_database_connect_args_pins_utc_and_falls_back_to_db_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from florabase.db.session import database_connect_args

    monkeypatch.delenv("PGPASSWORD", raising=False)
    monkeypatch.setenv("FLORABASE_DB_PASSWORD", "s3cr3t@:%")
    args = database_connect_args("postgresql+psycopg://florabase@db:5432/florabase")
    assert args == {"options": "-c timezone=UTC", "password": "s3cr3t@:%"}

    args_with_timeout = database_connect_args(
        "postgresql+psycopg://florabase:embedded@db:5432/florabase",
        options="-c statement_timeout=2000",
    )
    assert args_with_timeout == {"options": "-c statement_timeout=2000 -c timezone=UTC"}


@pytest.mark.parametrize("action", ["wait-db", "deploy", "serve"])
@pytest.mark.parametrize(
    ("var", "value", "expected"),
    [
        ("FLORABASE_DB_PASSWORD", "change-me", "placeholder 'change-me'"),
        ("PGPASSWORD", "change-me", "placeholder 'change-me'"),
        (
            "FLORABASE_CANONICAL_ORIGIN",
            "https://florabase.example.org",
            "placeholder 'https://florabase.example.org'",
        ),
        (
            "FLORABASE_CANONICAL_ORIGIN",
            "https://florabase.example.org/",
            "placeholder 'https://florabase.example.org'",
        ),
    ],
)
def test_refuses_placeholder_config(
    schema: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    action: str,
    var: str,
    value: str,
    expected: str,
) -> None:
    monkeypatch.delenv("FLORABASE_DB_PASSWORD", raising=False)
    monkeypatch.delenv("PGPASSWORD", raising=False)
    monkeypatch.delenv("FLORABASE_CANONICAL_ORIGIN", raising=False)
    monkeypatch.setenv(var, value)

    assert invoke(monkeypatch, action) == 1

    err = capsys.readouterr().err
    assert expected in err
    assert "docs/installation.md" in err
    schema.engine.connect.assert_not_called()
    schema.engine.begin.assert_not_called()
    schema.exec_server.assert_not_called()


def test_mountinfo_nesting_refuses_same_or_nested_ext4_mounts(tmp_path: Path) -> None:
    data = Path("/var/lib/florabase/data")
    backup = Path("/var/lib/florabase/backup")
    cases = [
        (
            "101 50 8:1 /srv/florabase/data /var/lib/florabase/data rw - ext4 /dev/sda1 rw\n"
            "102 50 8:1 /srv/florabase/data /var/lib/florabase/backup rw - ext4 /dev/sda1 rw\n",
            "same",
        ),
        (
            "101 50 8:1 /srv/florabase/data /var/lib/florabase/data rw - ext4 /dev/sda1 rw\n"
            "102 50 8:1 /srv/florabase/data/backup /var/lib/florabase/backup rw"
            " - ext4 /dev/sda1 rw\n",
            "backup folder is inside the data folder",
        ),
        (
            "101 50 8:1 /srv/florabase/backup/data /var/lib/florabase/data rw"
            " - ext4 /dev/sda1 rw\n"
            "102 50 8:1 /srv/florabase/backup /var/lib/florabase/backup rw - ext4 /dev/sda1 rw\n",
            "data folder is inside the backup folder",
        ),
    ]
    for content, pattern in cases:
        mountinfo = tmp_path / "mountinfo"
        mountinfo.write_text(content)
        with pytest.raises(release_schema.SchemaError, match=pattern):
            release_schema.check_mountinfo_nesting(data, backup, mountinfo_path=mountinfo)


def test_mountinfo_nesting_handles_btrfs_subvolumes_and_escapes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = Path("/var/lib/florabase/data")
    backup = Path("/var/lib/florabase/backup")
    mountinfo = tmp_path / "mountinfo"

    # Distinct Synology-style btrfs subvolumes on the same device: allowed, no warning.
    mountinfo.write_text(
        "210 50 0:36 /@docker/florabase/data /var/lib/florabase/data rw,noatime master:1 - "
        "btrfs /dev/vg1000/lv rw,ssd,subvolid=258,subvol=/@docker/florabase/data\n"
        "211 50 0:37 /@backup/florabase /var/lib/florabase/backup rw,noatime master:1 - "
        "btrfs /dev/vg1000/lv rw,ssd,subvolid=259,subvol=/@backup/florabase\n"
    )
    release_schema.check_mountinfo_nesting(data, backup, mountinfo_path=mountinfo)
    assert capsys.readouterr().err == ""

    # Nested btrfs paths across distinct subvolumes on the same source, with space escape.
    mountinfo.write_text(
        "210 50 0:36 /@docker/my\\040florabase/data /var/lib/florabase/data rw,noatime - "
        "btrfs /dev/vg1000/lv rw,subvolid=258,subvol=/@docker\n"
        "211 50 0:37 /@docker/my\\040florabase/data/backups /var/lib/florabase/backup rw,noatime - "
        "btrfs /dev/vg1000/lv rw,subvolid=260,subvol=/@docker/my\\040florabase/data/backups\n"
    )
    with pytest.raises(release_schema.SchemaError, match="backup folder is inside the data folder"):
        release_schema.check_mountinfo_nesting(data, backup, mountinfo_path=mountinfo)


def test_mountinfo_nesting_warns_and_continues_when_indeterminate(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = Path("/var/lib/florabase/data")
    backup = Path("/var/lib/florabase/backup")

    # Missing mountinfo file.
    release_schema.check_mountinfo_nesting(data, backup, mountinfo_path=tmp_path / "missing")
    assert "warning:" in capsys.readouterr().err

    # Mount entries absent.
    mountinfo = tmp_path / "mountinfo"
    mountinfo.write_text("10 1 8:1 / / rw - ext4 /dev/sda1 rw\n")
    release_schema.check_mountinfo_nesting(data, backup, mountinfo_path=mountinfo)
    assert "indeterminate" in capsys.readouterr().err

    # Malformed line without separator.
    mountinfo.write_text("garbage line without separator\n")
    release_schema.check_mountinfo_nesting(data, backup, mountinfo_path=mountinfo)
    assert "malformed mountinfo" in capsys.readouterr().err
