"""GET /api/dashboard/* — admin-only REST layer over dashboard/langfuse_query.py.

Note the prefix is /api/dashboard, not /api/analytics — api/routes.py already
owns GET /api/analytics for core/analytics.py's order/business analytics
(revenue, order counts from orders_log.txt), a different concern from this
package's LLM-cost/session/tool-usage observability data. Keeping them under
distinct prefixes avoids any ambiguity between the two.

Mounted additively in ai/main.py alongside the other routers. Depends only on
api.security for the auth guard (same require_role pattern every other
admin/role-gated endpoint in this repo uses) — no import of ai/ internals
beyond config, so this package stays cleanly separable.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api import security
from dashboard import langfuse_query as lfq
from db import escalations as db_esc

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

_admin = Depends(security.require_role("admin"))


@router.get("/summary")
def summary(days: int = 7, claims: dict = _admin) -> dict:
    return lfq.summary(days=days)


@router.get("/sessions")
def sessions(
    days: int = 7, page: int = 1, limit: int = 25, claims: dict = _admin
) -> dict:
    return lfq.sessions_table(days=days, page=page, limit=limit)


@router.get("/sessions/{session_id}")
def session_detail(session_id: str, claims: dict = _admin) -> dict:
    detail = lfq.session_detail(session_id)
    if detail is None:
        raise HTTPException(
            status_code=503, detail="Analytics unavailable (Langfuse not configured)."
        )
    return detail


@router.get("/escalations")
def escalations(limit: int = 50, claims: dict = _admin) -> list[dict]:
    return db_esc.get_escalations(limit=limit)


@router.get("/scores")
def scores(days: int = 7, claims: dict = _admin) -> list[dict]:
    return lfq.scores(days=days)
