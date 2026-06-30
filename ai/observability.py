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
