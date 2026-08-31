import io
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from florabase.auth.bootstrap import main
from florabase.auth.service import BootstrapError


def session_context() -> tuple[MagicMock, MagicMock]:
    session_class = MagicMock()
    database = MagicMock()
    session_class.return_value.__enter__.return_value = database
    database.begin.return_value.__enter__.return_value = None
    return session_class, database


def test_bootstrap_cli_interactive_success(capsys: pytest.CaptureFixture[str]) -> None:
    session_class, database = session_context()
    owner = SimpleNamespace(login_name="owner")
    with (
        patch.object(sys, "argv", ["bootstrap", "OWNER"]),
        patch("florabase.auth.bootstrap.getpass.getpass", return_value="secret password"),
        patch("florabase.auth.bootstrap.get_engine"),
        patch("florabase.auth.bootstrap.Session", session_class),
        patch("florabase.auth.bootstrap.bootstrap_owner", return_value=owner) as create,
    ):
        result = main()

    assert result == 0
    create.assert_called_once_with(database, "OWNER", "secret password", None)
    assert "Owner created: owner" in capsys.readouterr().out


def test_bootstrap_cli_stdin_failure(capsys: pytest.CaptureFixture[str]) -> None:
    session_class, _ = session_context()
    with (
        patch.object(sys, "argv", ["bootstrap", "owner", "--password-stdin"]),
        patch.object(sys, "stdin", io.StringIO("secret password\n")),
        patch("florabase.auth.bootstrap.get_engine"),
        patch("florabase.auth.bootstrap.Session", session_class),
        patch(
            "florabase.auth.bootstrap.bootstrap_owner",
            side_effect=BootstrapError("An owner account already exists"),
        ),
    ):
        result = main()

    assert result == 1
    captured = capsys.readouterr()
    assert "already exists" in captured.err
    assert "secret password" not in captured.out + captured.err
