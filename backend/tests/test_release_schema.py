import sys
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
