"""Supabase access for `app_users` — accounts for every role.

Unlike the best-effort order mirror, authentication REQUIRES the DB: these
functions raise when Supabase is unconfigured or the query fails, and the auth
router surfaces that as a clear service error. Secrets never reach this module
in plaintext — callers pass bcrypt hashes only.
"""

from __future__ import annotations

from db.client import execute_query, get_client

# Roles that sign in with emp_id + PIN and are created from the admin panel.
EMPLOYEE_ROLES = ("staff", "kitchen_staff", "delivery")
ALL_ROLES = ("user", "admin", *EMPLOYEE_ROLES)

_TABLE = "app_users"

# Columns safe to hand to routers/clients — never secret_hash.
_PUBLIC_COLS = "id, role, name, phone, email, emp_id, address, is_active, created_at"


def _require_client():
    client = get_client()
    if client is None:
        raise RuntimeError("Account database is not configured.")
    return client


def _one(resp) -> dict | None:
    data = getattr(resp, "data", None)
    return data[0] if data else None


def create_user(
    *,
    role: str,
    name: str,
    secret_hash: str,
    phone: str | None = None,
    email: str | None = None,
    address: list[dict] | None = None,
    emp_id: str | None = None,
) -> dict:
    """Insert one account. Returns the public row.

    emp_id is normally left None so the DB trigger assigns the next SMEMPnnn;
    seeds pass an explicit one for deterministic demo credentials. Raises on
    failure — including unique violations (duplicate phone/email), which the
    router turns into "already registered" errors.
    """
    client = _require_client()
    row = {
        "role": role,
        "name": name,
        "secret_hash": secret_hash,
        "phone": phone,
        "email": email,
        "address": address,
        "emp_id": emp_id,
    }
    resp = execute_query(client.table(_TABLE).insert(row))
    created = _one(resp)
    if not created:
        raise RuntimeError("Account insert returned no row.")
    created.pop("secret_hash", None)
    return created


def get_by_login(field: str, value: str) -> dict | None:
    """Fetch the FULL row (incl. secret_hash + lockout state) by a login key.

    `field` must be one of phone / email / emp_id — the router picks it from
    the requested role, never from client input.
    """
    if field not in ("phone", "email", "emp_id"):
        raise ValueError(f"Invalid login field: {field}")
    client = _require_client()
    resp = execute_query(client.table(_TABLE).select("*").eq(field, value).limit(1))
    return _one(resp)


def get_by_id(user_id: str) -> dict | None:
    """Public row by id (for token → user resolution). No secret_hash."""
    client = _require_client()
    resp = execute_query(
        client.table(_TABLE).select(_PUBLIC_COLS).eq("id", user_id).limit(1)
    )
    return _one(resp)


def update_user(user_id: str, fields: dict) -> dict | None:
    """Update arbitrary columns on one account; returns the public row."""
    client = _require_client()
    resp = execute_query(client.table(_TABLE).update(fields).eq("id", user_id))
    row = _one(resp)
    if row:
        row.pop("secret_hash", None)
    return row


def record_login_failure(
    user_id: str, failed_attempts: int, locked_until: str | None
) -> None:
    """Persist the incremented failure count (and lock, once over the limit)."""
    client = _require_client()
    execute_query(
        client.table(_TABLE)
        .update({"failed_attempts": failed_attempts, "locked_until": locked_until})
        .eq("id", user_id)
    )


def record_login_success(user_id: str) -> None:
    """Reset the lockout counters after a correct secret."""
    client = _require_client()
    execute_query(
        client.table(_TABLE)
        .update({"failed_attempts": 0, "locked_until": None})
        .eq("id", user_id)
    )


def list_employees() -> list[dict]:
    """All employee accounts (staff / kitchen_staff / delivery), newest first."""
    client = _require_client()
    resp = execute_query(
        client.table(_TABLE)
        .select(_PUBLIC_COLS)
        .in_("role", list(EMPLOYEE_ROLES))
        .order("created_at", desc=True)
    )
    return getattr(resp, "data", None) or []
