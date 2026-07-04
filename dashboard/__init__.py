"""Observability dashboard — a separate, maintainable package for the read-side
of the AI layer's Langfuse data (cost, sessions, tool usage). `ai/observability.py`
owns the write side (scores, spans, flush); this package only ever queries
Langfuse back out and exposes it as REST endpoints for the standalone
frontend dashboard screen (`frontend/app/(dashboard)/`) to call.

No dependency on ai/ internals beyond `ai.config.get_settings()` (same
Langfuse credentials already in .env) and `api.security` for the admin-only
auth guard, so this stays cleanly separable.
"""
