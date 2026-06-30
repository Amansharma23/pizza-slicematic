"""In-memory conversation sessions, keyed by session_id.

Runtime source of truth for a conversation: the LLM message `history`, the
fields extracted so far, and status flags. One process holds them in a dict;
this is fine for the demo. For production, swap `_SESSIONS` for Redis (and/or
rehydrate `history` from the messages table) — see CLAUDE.md.

Mirroring to Supabase is explicit (`mirror()`), so this module stays pure and
unit-testable without a database.
"""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone

from db import sessions as db_sessions

# Guards the module-level dicts (cheap; the GIL covers the rest).
_GUARD = threading.Lock()
_SESSIONS: dict[str, "Session"] = {}
_LOCKS: dict[str, asyncio.Lock] = {}


@dataclass
class Session:
    """One conversation's full runtime state."""

    id: str
    channel: str = "chat"  # "chat" | "voice"
    language: str = "en"  # "en" | "hi"
    status: str = "active"  # active | ordered | escalated | abandoned
    history: list[dict] = field(default_factory=list)  # OpenAI-shaped messages
    name: str | None = None
    phone: str | None = None
    items: list = field(default_factory=list)
    pricing: dict | None = None  # set after calculate_order_price
    confirmed: bool = False
    human_escalated: bool = False
    voice_started_at: float | None = None  # epoch seconds, for the 3-min cap

    def add(self, role: str, content: str | None = None, **extra) -> dict:
        """Append one message to the LLM history and return it."""
        msg: dict = {"role": role}
        if content is not None:
            msg["content"] = content
        msg.update(extra)  # e.g. tool_calls=..., tool_call_id=...
        self.history.append(msg)
        return msg


def get_or_create(session_id: str, *, channel: str = "chat") -> Session:
    """Return the existing Session for this id, or create a fresh one."""
    with _GUARD:
        sess = _SESSIONS.get(session_id)
        if sess is None:
            sess = Session(id=session_id, channel=channel)
            _SESSIONS[session_id] = sess
        return sess


def get(session_id: str) -> Session | None:
    return _SESSIONS.get(session_id)


def reset(session_id: str) -> None:
    """Drop a session (e.g. 'start a new order' / cancel)."""
    with _GUARD:
        _SESSIONS.pop(session_id, None)


def lock_for(session_id: str) -> asyncio.Lock:
    """Per-session async lock so one session processes one turn at a time."""
    with _GUARD:
        lock = _LOCKS.get(session_id)
        if lock is None:
            lock = asyncio.Lock()
            _LOCKS[session_id] = lock
        return lock


def _iso(epoch: float | None) -> str | None:
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def mirror(session: Session) -> bool:
    """Best-effort upsert of the session's persistable fields to Supabase."""
    return db_sessions.upsert_session(
        session.id,
        channel=session.channel,
        language=session.language,
        status=session.status,
        customer_name=session.name,
        customer_phone=session.phone,
        human_escalated=session.human_escalated,
        voice_started_at=_iso(session.voice_started_at),
    )
