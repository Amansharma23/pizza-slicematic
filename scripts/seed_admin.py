"""Seed (or update) the single admin account from env vars.

There is deliberately NO public admin signup — the admin signs in with
email + password at /admin, and this script is the only way an admin account
is created. Run it once after applying migration 0004:

    uv run python scripts/seed_admin.py

Reads from .env / environment:
    ADMIN_EMAIL      (required)
    ADMIN_PASSWORD   (required, min 8 chars)
    ADMIN_NAME       (optional, default "SliceMatic Admin")

Idempotent: if the admin (by email) already exists, its password/name are
updated in place.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

from api import security  # noqa: E402
from db import users as db_users  # noqa: E402


def main() -> int:
    email = (os.environ.get("ADMIN_EMAIL") or "").strip().lower()
    password = os.environ.get("ADMIN_PASSWORD") or ""
    name = (os.environ.get("ADMIN_NAME") or "").strip() or "SliceMatic Admin"

    if not email or "@" not in email:
        print("ADMIN_EMAIL is missing/invalid. Set it in .env and re-run.")
        return 1
    if len(password) < 8:
        print("ADMIN_PASSWORD must be at least 8 characters. Set it in .env.")
        return 1

    secret_hash = security.hash_secret(password)
    existing = db_users.get_by_login("email", email)
    if existing:
        db_users.update_user(
            str(existing["id"]),
            {"name": name, "secret_hash": secret_hash, "is_active": True},
        )
        print(f"Admin {email} already existed — password/name updated.")
    else:
        db_users.create_user(
            role="admin", name=name, email=email, secret_hash=secret_hash
        )
        print(f"Admin {email} created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
