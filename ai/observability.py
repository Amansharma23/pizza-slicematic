"""Langfuse tracing — entirely best-effort.

Tracing must never affect the customer. We use Langfuse's OpenAI drop-in
(ai/llm.py) for automatic per-call traces; this module just initialises the
client, supplies optional per-turn trace metadata, and flushes. Every function
degrades to a no-op if Langfuse is disabled or errors.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from ai.config import get_settings

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_langfuse():
    """Return a configured Langfuse client, or None if disabled/unavailable."""
    try:
        s = get_settings()
        if not s.langfuse_enabled:
            return None
        from langfuse import Langfuse

        return Langfuse(
            public_key=s.langfuse_public_key,
            secret_key=s.langfuse_secret_key,
            host=s.langfuse_host,
        )
    except Exception as exc:
        log.warning("Langfuse init failed (tracing disabled): %s", exc)
        return None


def enabled() -> bool:
    return get_langfuse() is not None


def trace_kwargs(session_id: str, name: str, **metadata) -> dict:
    """Extra create() kwargs that tag the trace. Empty when tracing is off.

    Only returned when Langfuse is active, so the plain OpenAI client (no
    Langfuse) never receives kwargs it doesn't understand.
    """
    if not enabled():
        return {}
    meta = {"langfuse_session_id": session_id}
    meta.update(metadata)
    return {"name": name, "metadata": meta}


def flush() -> None:
    """Best-effort flush so traces are sent before the process moves on."""
    client = get_langfuse()
    if client is None:
        return
    try:
        client.flush()
    except Exception as exc:
        log.debug("Langfuse flush failed: %s", exc)


def score_session(
    session_id: str,
    name: str,
    value,
    *,
    data_type: str | None = None,
    comment: str | None = None,
) -> None:
    """Attach an eval score to every trace in a session (auto-scoring: the
    first building block for the eval dashboard). Session-level rather than
    trace-level on purpose — turns run through a FastAPI threadpool (chat) or
    asyncio.to_thread (voice), where chasing an OTel "current trace" context
    is fragile; the session_id tagging every turn already gets via
    trace_kwargs() is a stable handle regardless of which thread scored it."""
    client = get_langfuse()
    if client is None:
        return
    try:
        client.create_score(
            session_id=session_id,
            name=name,
            value=value,
            data_type=data_type,
            comment=comment,
        )
    except Exception as exc:
        log.debug("Langfuse score '%s' failed: %s", name, exc)
