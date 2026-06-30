"""Append chat/voice turns into the Supabase `messages` table.

Best-effort. One row per turn; voice turns reuse the same table with the audio
metadata columns populated. A message references an existing session (FK), so
upsert the session before adding its messages.
"""

from __future__ import annotations

import logging

from db.client import execute_query, get_client

log = logging.getLogger(__name__)


def add_message(
    session_id: str,
    role: str,
    content: str | None = None,
    *,
    channel: str | None = None,
    model_used: str | None = None,
    tool_name: str | None = None,
    tool_calls=None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    audio_duration_ms: int | None = None,
    stt_confidence: float | None = None,
) -> str | None:
    """Insert one message row. Returns the new row id, or None on failure."""
    client = get_client()
    if client is None:
        return None
    row = {
        "session_id": session_id,
        "role": role,
        "content": content,
        "channel": channel,
        "model_used": model_used,
        "tool_name": tool_name,
        "tool_calls": tool_calls,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "audio_duration_ms": audio_duration_ms,
        "stt_confidence": stt_confidence,
    }
    # Drop None values so DB defaults/nullables apply cleanly.
    row = {k: v for k, v in row.items() if v is not None}
    try:
        res = execute_query(client.table("messages").insert(row))
        return res.data[0]["id"] if res.data else None
    except Exception as exc:
        log.warning("Supabase message insert failed (%s/%s): %s", session_id, role, exc)
        return None
