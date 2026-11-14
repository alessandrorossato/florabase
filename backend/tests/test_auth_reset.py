import getpass
import io
import json
import warnings
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import DBAPIError

from florabase.auth import reset_password
from florabase.auth.service import PasswordResetRefusedError
from florabase.db.release_schema import SchemaError


@pytest.mark.parametrize(
    "document", [b'["invalid"]', b'"too short"', b'"\\ud800invalid utf8"', b'"" 0', b" " * 16385]
)
def test_invalid_json_password_input(monkeypatch: pytest.MonkeyPatch, document: bytes) -> None:
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(document)))
    with pytest.raises((ValueError, reset_password.InputError)):
        reset_password.read_password("owner", True)


def test_private_pipe_preserves_exact_password(monkeypatch: pytest.MonkeyPatch) -> None:
    password = "  🌿 exact credential\n "
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(json.dumps(password).encode())))
    assert reset_password.read_password("owner", True) == password
    with pytest.raises(reset_password.InputError):
        reset_password.read_password("owner", False)


def test_interactive_echo_fallback_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    stdin = MagicMock()
    stdin.isatty.return_value = True
    monkeypatch.setattr("sys.stdin", stdin)
    monkeypatch.setattr("florabase.auth.reset_password.os.open", lambda *_: 9)
    monkeypatch.setattr("florabase.auth.reset_password.os.isatty", lambda *_: True)
    monkeypatch.setattr("florabase.auth.reset_password.os.close", lambda *_: None)

    def echo_fallback(_: str) -> str:
        warnings.warn("Can not control echo", getpass.GetPassWarning, stacklevel=2)
        pytest.fail("The echoing input path must never run")

    monkeypatch.setattr(getpass, "getpass", echo_fallback)
    with pytest.raises(getpass.GetPassWarning):
        reset_password.read_password("owner", False)
    with pytest.raises(reset_password.InputError):
        reset_password.read_password("owner", True)


@pytest.mark.parametrize(
    ("stage", "expected"),
    [
        ("flush", "failed"),
        ("commit", "could not be confirmed"),
        ("server_rejected", "failed"),
        ("transport_lost", "could not be confirmed"),
        ("invalidated", "could not be confirmed"),
        ("interrupt_before_commit", "interrupted"),
        ("interrupt_during_commit", "could not be confirmed"),
        ("wrong_schema", "installed database revision"),
        ("wrong_owner", "single enabled owner"),
        ("success", ""),
    ],
)
def test_reset_reports_failure_without_details(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], stage: str, expected: str
) -> None:
    database = MagicMock()
    tx = MagicMock()
    database.begin.return_value = tx
    if stage == "flush":
        database.flush.side_effect = RuntimeError("credential-canary")
    elif stage == "commit":
        tx.__exit__.side_effect = RuntimeError("credential-canary")
    elif stage in {"server_rejected", "transport_lost", "invalidated"}:
        driver = type(
            "DriverError",
            (Exception,),
            {
                "sqlstate": "08006" if stage == "transport_lost" else "23514",
            },
        )
        tx.__exit__.side_effect = DBAPIError(
            None, None, driver("credential-canary"), connection_invalidated=stage == "invalidated"
        )
    elif stage == "interrupt_before_commit":
        database.flush.side_effect = KeyboardInterrupt
    elif stage == "interrupt_during_commit":
        tx.__exit__.side_effect = KeyboardInterrupt
    database_class = MagicMock()
    database_class.return_value.__enter__.return_value = database
    monkeypatch.setattr("sys.argv", ["reset_password", "owner", "--password-json-stdin"])
    monkeypatch.setattr(reset_password, "read_password", lambda *_: "synthetic passphrase")
    monkeypatch.setattr("florabase.auth.reset_password.get_settings", lambda: MagicMock())
    monkeypatch.setattr("florabase.auth.reset_password.create_engine", lambda *a, **k: MagicMock())
    monkeypatch.setattr("florabase.auth.reset_password.Session", database_class)
    monkeypatch.setattr(reset_password, "image_schema", lambda: (None, None, "head"))
    monkeypatch.setattr(reset_password, "require_image_head", lambda *_: None)
    monkeypatch.setattr(reset_password, "reset_owner_password", lambda *_: None)
    if stage == "wrong_schema":
        monkeypatch.setattr(
            reset_password, "require_image_head", MagicMock(side_effect=SchemaError)
        )
    if stage == "wrong_owner":
        monkeypatch.setattr(
            reset_password,
            "reset_owner_password",
            MagicMock(side_effect=PasswordResetRefusedError),
        )
    status = 0 if stage == "success" else 130 if stage.startswith("interrupt") else 1
    assert reset_password.main() == status
    output = capsys.readouterr()
    assert expected in output.err
    assert "credential-canary" not in output.err
    assert output.out == (
        "Owner password reset committed. Sign in again.\n" if stage == "success" else ""
    )


def test_interactive_uses_controlling_tty_without_echo() -> None:
    import errno
    import os
    import pty
    import select
    import signal
    import sys
    from time import monotonic

    password = b"synthetic terminal credential"
    pid, master = pty.fork()
    if pid == 0:
        try:
            sys.stdin = os.fdopen(0, encoding="utf-8")
            expected = password.decode()
            os._exit(0 if reset_password.read_password("owner", False) == expected else 1)
        except BaseException:
            os._exit(2)
    transcript = bytearray()
    entered = 0
    finished = False
    try:
        deadline = monotonic() + 8
        while monotonic() < deadline:
            readable, _, _ = select.select([master], [], [], max(0, deadline - monotonic()))
            if not readable:
                break
            try:
                transcript.extend(os.read(master, 4096))
            except OSError as error:
                if error.errno != errno.EIO:
                    raise
                finished = True
                break
            if entered == 0 and b"New password: " in transcript:
                os.write(master, password + b"\n")
                entered = 1
            elif entered == 1 and b"Confirm new password: " in transcript:
                os.write(master, password + b"\n")
                entered = 2
        assert finished
        assert entered == 2
        assert password not in transcript
    finally:
        os.close(master)
        if not finished:
            os.kill(pid, signal.SIGKILL)
        _, status = os.waitpid(pid, 0)
    assert os.waitstatus_to_exitcode(status) == 0


@pytest.mark.parametrize(
    "condition", ["mismatch", "eof", "interrupt", "not_a_tty", "extra_argument"]
)
def test_reset_refuses_unsafe_interactive_input(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    condition: str,
) -> None:
    argv = ["reset_password", "owner"]
    if condition == "extra_argument":
        argv += ["unexpected-input-canary"]
    monkeypatch.setattr("sys.argv", argv)
    stdin = MagicMock()
    stdin.isatty.return_value = True
    monkeypatch.setattr("sys.stdin", stdin)
    close = MagicMock()
    monkeypatch.setattr("florabase.auth.reset_password.os.open", lambda *_: 9)
    monkeypatch.setattr(
        "florabase.auth.reset_password.os.isatty", lambda *_: condition != "not_a_tty"
    )
    monkeypatch.setattr("florabase.auth.reset_password.os.close", close)
    prompt = MagicMock(
        side_effect={
            "eof": EOFError,
            "interrupt": KeyboardInterrupt,
        }.get(condition, ["synthetic first value", "synthetic second value"])
    )
    monkeypatch.setattr(getpass, "getpass", prompt)
    engine = MagicMock()
    monkeypatch.setattr("florabase.auth.reset_password.create_engine", engine)
    if condition == "extra_argument":
        with pytest.raises(SystemExit) as error:
            reset_password.main()
        assert error.value.code == 2
        prompt.assert_not_called()
        close.assert_not_called()
    else:
        assert reset_password.main() == (130 if condition == "interrupt" else 1)
        close.assert_called_once_with(9)
    if condition == "not_a_tty":
        prompt.assert_not_called()
    engine.assert_not_called()
    output = capsys.readouterr()
    assert "unexpected-input-canary" not in output.err
    assert "synthetic" not in output.err
    assert output.out == ""
