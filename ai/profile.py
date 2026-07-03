"""Resolve the signed-in customer onto a chat/voice session.

The frontend sends its auth JWT (Authorization: Bearer …) with /chat and
/voice/respond. Each turn we decode it and load the account from app_users so
the get_customer_profile tool serves REAL data — no hardcoded profile. All
best-effort: a missing/invalid token or DB hiccup just leaves the session
anonymous (the agent then asks for name/phone), it never breaks the turn.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def _default_address(address: list | None) -> str | None:
    """The default (or first) saved address as one display line."""
    if not address:
        return None
    chosen = next((a for a in address if a.get("isDefault")), address[0])
    line = str(chosen.get("line") or "").strip()
    if not line:
        return None
    label = str(chosen.get("label") or "").strip()
    return f"{line} ({label})" if label else line


def attach_user(session, authorization: str | None) -> None:
    """Populate session.user_id/name/phone/address from the request's JWT.

    Refreshed every turn so a profile edit (e.g. adding an address mid-chat)
    is picked up on the customer's next message.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        return
    token = authorization.split(" ", 1)[1].strip()
    try:
        from api.security import decode_token
        from db import users as db_users

        claims = decode_token(token)
        if claims.get("role") != "user":
            return  # only customer accounts order through chat/voice
        user = db_users.get_by_id(claims["sub"])
        if not user or not user.get("is_active", True):
            return
        session.user_id = str(user["id"])
        session.name = user.get("name") or session.name
        session.phone = user.get("phone") or session.phone
        session.address = _default_address(user.get("address"))
    except Exception as exc:  # expired token, DB down, ... — stay anonymous
        log.info("Session %s: could not attach user (%s)", session.id, exc)
