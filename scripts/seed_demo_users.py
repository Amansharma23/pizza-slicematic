"""Seed one demo account per role for testing. Idempotent.

    uv run python scripts/seed_demo_users.py

Reads credentials from .env (see the "Demo accounts" block there; defaults
below match it). Existing accounts (matched by their login key) get their
name/PIN/active flag updated in place, so .env stays the single source of
truth for what signs in.

Roles seeded:
    user           phone + PIN         customer app        /
    admin          email + password    admin dashboard     /admin
    staff          SMEMP001 + PIN      staff kiosk         /staff
    kitchen_staff  SMEMP002 + PIN      kitchen kiosk       /kitchen
    delivery       SMEMP003 + PIN      rider app           /delivery
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


def _env(name: str, default: str) -> str:
    return (os.environ.get(name) or "").strip() or default


DEMO_ADDRESS = [
    {
        "id": "home",
        "label": "Home",
        "line": "D-42, New Ashok Nagar, New Delhi 110096",
        "isDefault": True,
    }
]

SEEDS = [
    {
        "role": "user",
        "name": _env("DEMO_USER_NAME", "Aarav Sharma"),
        "login_field": "phone",
        "phone": _env("DEMO_USER_PHONE", "9876543210"),
        "secret": _env("DEMO_USER_PIN", "123456"),
        "address": DEMO_ADDRESS,
    },
    {
        "role": "admin",
        "name": _env("ADMIN_NAME", "SliceMatic Admin"),
        "login_field": "email",
        "email": _env("ADMIN_EMAIL", "admin@slicematic.in").lower(),
        "secret": _env("ADMIN_PASSWORD", "SliceMatic@Admin1"),
    },
    {
        "role": "staff",
        "name": _env("DEMO_STAFF_NAME", "Rohan Verma"),
        "login_field": "emp_id",
        "emp_id": "SMEMP001",
        "phone": _env("DEMO_STAFF_PHONE", "9811111111"),
        "secret": _env("DEMO_STAFF_PIN", "111111"),
    },
    {
        "role": "kitchen_staff",
        "name": _env("DEMO_KITCHEN_NAME", "Priya Nair"),
        "login_field": "emp_id",
        "emp_id": "SMEMP002",
        "phone": _env("DEMO_KITCHEN_PHONE", "9822222222"),
        "secret": _env("DEMO_KITCHEN_PIN", "222222"),
    },
    {
        "role": "delivery",
        "name": _env("DEMO_DELIVERY_NAME", "Vikram Singh"),
        "login_field": "emp_id",
        "emp_id": "SMEMP003",
        "phone": _env("DEMO_DELIVERY_PHONE", "9833333333"),
        "secret": _env("DEMO_DELIVERY_PIN", "333333"),
    },
]


def main() -> int:
    for seed in SEEDS:
        login_field = seed["login_field"]
        login_value = seed[login_field]
        secret_hash = security.hash_secret(seed["secret"])
        existing = db_users.get_by_login(login_field, login_value)
        if existing:
            db_users.update_user(
                str(existing["id"]),
                {
                    "name": seed["name"],
                    "secret_hash": secret_hash,
                    "is_active": True,
                    "failed_attempts": 0,
                    "locked_until": None,
                },
            )
            action = "updated"
        else:
            db_users.create_user(
                role=seed["role"],
                name=seed["name"],
                secret_hash=secret_hash,
                phone=seed.get("phone"),
                email=seed.get("email"),
                emp_id=seed.get("emp_id"),
                address=seed.get("address"),
            )
            action = "created"
        print(f"[{action}] {seed['role']:<14} {login_field}={login_value}")
    print("\nDone — credentials are listed in .env under 'Demo accounts'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
