"""Reset an existing owner from a trusted deployment host."""

import argparse
import getpass
import json
import os
import sys
import termios
import warnings

from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from florabase.auth.security import normalize_login_name, validate_password
from florabase.auth.service import (
    PasswordResetRefusedError,
    reset_owner_password,
    set_auth_timeouts,
)
from florabase.core.config import get_settings
from florabase.db.release_schema import SCHEMA_LOCK, SchemaError, image_schema, require_image_head

MAX_JSON_INPUT = 16 * 1024


class InputError(Exception):
    pass


def read_password(login: str, json_stdin: bool) -> str:
    if json_stdin:
        if sys.stdin.isatty():
            raise InputError
        data = sys.stdin.buffer.read(MAX_JSON_INPUT + 1)
        if len(data) > MAX_JSON_INPUT:
            raise InputError
        value = json.loads(data.decode("utf-8"))
        if not isinstance(value, str):
            raise InputError
        return validate_password(value)

    if not sys.stdin.isatty():
        raise InputError
    tty = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
    try:
        if not os.isatty(tty):
            raise InputError
    finally:
        os.close(tty)
    sys.stderr.write(f"Reset password for {login}. All sessions will be signed out.\n")
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        password = getpass.getpass("New password: ")
        confirmation = getpass.getpass("Confirm new password: ")
    if password != confirmation:
        raise InputError
    return validate_password(password)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("login_name")
    parser.add_argument(
        "--password-json-stdin",
        action="store_true",
        help="read one JSON string from a private pipe",
    )
    # argparse ordinarily prints unrecognized arguments verbatim.
    args, unexpected = parser.parse_known_args()
    if unexpected:
        parser.error("Unexpected arguments")
    try:
        login = normalize_login_name(args.login_name)
        password = read_password(login, args.password_json_stdin)
    except KeyboardInterrupt:
        sys.stderr.write("Owner password reset interrupted.\n")
        return 130
    except (
        InputError,
        ValueError,
        OSError,
        EOFError,
        getpass.GetPassWarning,
        RecursionError,
        termios.error,
    ):
        sys.stderr.write(
            "Owner password reset refused. Check the login and protected password input.\n"
        )
        return 1

    committing = False
    try:
        engine = create_engine(
            get_settings().database_url,
            poolclass=NullPool,
            hide_parameters=True,
            connect_args={"connect_timeout": 5},
        )
        with Session(engine) as database, database.begin():
            set_auth_timeouts(database)
            database.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": SCHEMA_LOCK})
            require_image_head(database.connection(), image_schema()[2])
            reset_owner_password(database, login, password)
            database.flush()
            committing = True
    except KeyboardInterrupt:
        message = (
            "Owner password reset outcome could not be confirmed."
            if committing
            else "Owner password reset interrupted."
        )
        sys.stderr.write(message + "\n")
        return 130
    except PasswordResetRefusedError:
        sys.stderr.write("Owner password reset requires the single enabled owner.\n")
        return 1
    except SchemaError:
        sys.stderr.write("Owner password reset requires the installed database revision.\n")
        return 1
    except Exception as error:
        sqlstate = getattr(error.orig, "sqlstate", None) if isinstance(error, DBAPIError) else None
        if committing and (
            not sqlstate
            or sqlstate.startswith("08")
            or (isinstance(error, DBAPIError) and error.connection_invalidated)
        ):
            sys.stderr.write("Owner password reset outcome could not be confirmed.\n")
        else:
            sys.stderr.write(
                "Owner password reset failed. Check database health and configuration.\n"
            )
        return 1
    sys.stdout.write("Owner password reset committed. Sign in again.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
