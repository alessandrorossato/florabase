import getpass
import io
import json
import warnings
from unittest.mock import MagicMock

import pytest

from florabase.auth import reset_password


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
    else:
        tx.__exit__.side_effect = RuntimeError("credential-canary")
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
    assert reset_password.main() == 1
    output = capsys.readouterr()
    assert expected in output.err
    assert "credential-canary" not in output.err
    assert output.out == ""


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
