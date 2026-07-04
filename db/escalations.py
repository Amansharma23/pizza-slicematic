"""Record human-escalation events into the Supabase `escalations` table.

Best-effort, like the other db/ helpers. An escalation references a session
(FK), so the caller upserts the session first. Admins triage from this table:
the transcript lives in `messages` (same session_id) and the LLM trace in
Langfuse (langfuse_url / langfuse_session_id).
"""

from __future__ import annotations

import logging

from db.client import execute_query, get_client

log = logging.getLogger(__name__)


def add_escalation(
    *,
    session_id: str,
    reason: str | None = None,
    channel: str | None = None,
    language: str | None = None,
    customer_name: str | None = None,
    customer_phone: str | None = None,
    langfuse_session_id: str | None = None,
    langfuse_url: str | None = None,
) -> str | None:
    """Insert one escalation row. Returns the new row id, or None on failure."""
    client = get_client()
    if client is None:
        return None
    row = {
        "session_id": session_id,
        "reason": reason,
        "channel": channel,
        "language": language,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "langfuse_session_id": langfuse_session_id,
        "langfuse_url": langfuse_url,
    }
    row = {k: v for k, v in row.items() if v is not None}
    try:
        res = execute_query(client.table("escalations").insert(row))
        return res.data[0]["id"] if res.data else None
    except Exception as exc:
        log.warning("Supabase escalation insert failed (%s): %s", session_id, exc)
        return None


def get_escalations(limit: int = 50) -> list[dict]:
    """Fetch recent human-escalation events, sorted by created_at descending."""
    client = get_client()
    if client is None:
        return []
    try:
        res = execute_query(
            client.table("escalations")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
        )
        return res.data or []
    except Exception as exc:
        log.warning("Supabase escalations select failed: %s", exc)
        return []
