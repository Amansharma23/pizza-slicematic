"""Shared OpenRouter client (OpenAI-compatible).

One cached client for the whole AI layer — used by the agent loop and the
guardrail classifier. When Langfuse is enabled we return its OpenAI drop-in,
which auto-traces every call; otherwise the plain OpenAI client. Both share the
identical interface, so callers make standard create() calls either way.

Importing this triggers config's fail-fast on a missing OPENROUTER_API_KEY, so
only the AI service depends on it, never core/.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from ai.config import get_settings

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_client():
    s = get_settings()
    openai_cls = None
    if s.langfuse_enabled:
        try:
            from ai import observability

            observability.get_langfuse()  # configure the global Langfuse client first
            from langfuse.openai import OpenAI as openai_cls  # auto-tracing drop-in
        except Exception as exc:
            log.warning(
                "Langfuse OpenAI drop-in unavailable, using plain client: %s", exc
            )
            openai_cls = None
    if openai_cls is None:
        from openai import OpenAI as openai_cls

    return openai_cls(
        api_key=s.openrouter_api_key,
        base_url=s.openrouter_base_url,
        default_headers={"X-Title": s.brand},
    )
