"""Shared OpenRouter client (OpenAI-compatible).

One cached client for the whole AI layer — used by the agent loop and the
guardrail classifier. Importing this triggers config's fail-fast on a missing
OPENROUTER_API_KEY, so only the AI service depends on it, never core/.
"""

from __future__ import annotations

from functools import lru_cache

from openai import OpenAI

from ai.config import get_settings


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    s = get_settings()
    return OpenAI(
        api_key=s.openrouter_api_key,
        base_url=s.openrouter_base_url,
        default_headers={"X-Title": s.brand},
    )
