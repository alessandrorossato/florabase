import argparse
import getpass
import sys

from sqlalchemy.orm import Session

from florabase.auth.service import BootstrapError, bootstrap_owner
from florabase.db.session import get_engine


def main() -> int:
    parser = argparse.ArgumentParser(description="Create Florabase's first and only local owner")
    parser.add_argument("login_name")
    parser.add_argument("--display-name")
    parser.add_argument(
        "--password-stdin",
        action="store_true",
        help="read one password line from standard input instead of a terminal",
    )
    args = parser.parse_args()
    password = sys.stdin.readline().rstrip("\r\n") if args.password_stdin else getpass.getpass()
    try:
        with Session(get_engine()) as database, database.begin():
            owner = bootstrap_owner(database, args.login_name, password, args.display_name)
            created_login = owner.login_name
    except (BootstrapError, ValueError) as exc:
        sys.stderr.write(f"Owner bootstrap failed: {exc}\n")
        return 1
    sys.stdout.write(f"Owner created: {created_login}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
