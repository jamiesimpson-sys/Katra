"""Admin CLI. Usage: python -m katra.cli create-admin --email you@example.com"""

import argparse
import getpass
import sys

from katra.db.session import get_sessionmaker
from katra.services.users import create_staff_user


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="katra")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create-admin", help="Create a staff user who can create projects")
    create.add_argument("--email", required=True)
    create.add_argument("--name", default="")
    args = parser.parse_args(argv)

    if args.command == "create-admin":
        password = getpass.getpass("Password: ")
        if password != getpass.getpass("Repeat password: "):
            print("Passwords don't match", file=sys.stderr)
            return 1
        with get_sessionmaker()() as db:
            try:
                user = create_staff_user(db, args.email, password, args.name)
            except ValueError as e:
                print(e, file=sys.stderr)
                return 1
            db.commit()
            print(f"Created staff user {user.email}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
