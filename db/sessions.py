"""Mirror conversation sessions into the Supabase `sessions` table.

Best-effort, like db/orders.py: a failure is logged and swallowed. The
in-memory session store (ai/session.py) is the runtime source of truth; this
table is for analytics and cross-session history.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from db.client import execute_query, get_client

log = logging.getLogger(__name__)

# Columns the `sessions` table accepts (id is the PK / session_id).
_ALLOWED = {
    "channel",
    "language",
    "customer_name",
    "customer_phone",
    "status",
    "human_escalated",
    "voice_started_at",
    "metadata",
    "ended_at",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_session(session_id: str, **fields) -> bool:
    """Insert or update a session row, refreshing last_activity_at.

    Only known columns in **fields are written; unknown keys are ignored so the
    in-memory Session can pass extra attributes harmlessly.
    """
    client = get_client()
    if client is None:
        return False
    row = {k: v for k, v in fields.items() if k in _ALLOWED and v is not None}
    row["id"] = session_id
    row["last_activity_at"] = _now()
    try:
        execute_query(client.table("sessions").upsert(row))
        return True
    except Exception as exc:
        log.warning("Supabase session upsert failed (%s): %s", session_id, exc)
        return False
