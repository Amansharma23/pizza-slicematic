"""POST /chat — the text conversation endpoint the frontend calls.

Per turn: resolve the session, detect language, persist the user message, run the
input guardrail (return a redirect without the LLM if blocked), otherwise run the
agent, persist the reply, and mirror session state. A per-session lock serialises
turns for the same session. The route is synchronous so FastAPI runs it in a
threadpool — the blocking LLM call doesn't stall the event loop.
"""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import APIRouter, BackgroundTasks, Header
from pydantic import BaseModel

from ai import agent, guardrails
from ai import session as sess
from ai.language import detect
from ai.profile import attach_user
from db import messages as db_messages

log = logging.getLogger(__name__)
router = APIRouter()


def _persist_turn(session, user_text: str, reply: str, channel: str) -> None:
    """Best-effort persistence, run in the background after the response is sent.

    Mirror the session first (FK parent), then store both messages. Never raises.
    """
    try:
        sess.mirror(session)
        db_messages.add_message(session.id, "user", user_text, channel=channel)
        db_messages.add_message(session.id, "assistant", reply, channel=channel)
    except Exception as exc:
        log.warning("Background persist failed (%s): %s", session.id, exc)


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    escalated: bool = False
    blocked: bool = False


@router.post("/chat", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    background: BackgroundTasks,
    authorization: str | None = Header(default=None),
) -> ChatResponse:
    session_id = req.session_id or uuid.uuid4().hex
    session = sess.get_or_create(session_id, channel="chat")
    session.channel = "chat"
    session.language = detect(req.message)
    # Signed-in customer (JWT) → real profile for get_customer_profile.
    attach_user(session, authorization)

    with sess.lock_for(session_id):
        check = guardrails.check_input(req.message, session.id)
        if check.ok:
            t0 = time.perf_counter()
            reply = agent.run_turn(session, req.message)
            log.info(
                "[timing] AGENT(chat) %.2fs (lang=%s -> %d chars)",
                time.perf_counter() - t0,
                session.language,
                len(reply),
            )
            blocked = False
        else:
            reply = check.message
            blocked = True

    # Persist off the response path — runs after the response is sent.
    background.add_task(_persist_turn, session, req.message, reply, "chat")

    return ChatResponse(
        reply=reply,
        session_id=session_id,
        escalated=session.human_escalated,
        blocked=blocked,
    )
