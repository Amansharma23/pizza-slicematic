"""POST /chat — the text conversation endpoint the frontend calls.

Per turn: resolve the session, detect language, persist the user message, run the
input guardrail (return a redirect without the LLM if blocked), otherwise run the
agent, persist the reply, and mirror session state. A per-session lock serialises
turns for the same session. The route is synchronous so FastAPI runs it in a
threadpool — the blocking LLM call doesn't stall the event loop.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from ai import agent, guardrails
from ai import session as sess
from ai.language import detect
from db import messages as db_messages

log = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    escalated: bool = False
    blocked: bool = False


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    session_id = req.session_id or uuid.uuid4().hex
    session = sess.get_or_create(session_id, channel="chat")
    session.language = detect(req.message)

    with sess.lock_for(session_id):
        sess.mirror(session)  # ensure the session row exists (FK parent)
        db_messages.add_message(session_id, "user", req.message, channel="chat")

        check = guardrails.check_input(req.message)
        if not check.ok:
            db_messages.add_message(
                session_id, "assistant", check.message, channel="chat"
            )
            return ChatResponse(
                reply=check.message, session_id=session_id, blocked=True
            )

        reply = agent.run_turn(session, req.message)
        db_messages.add_message(session_id, "assistant", reply, channel="chat")
        sess.mirror(session)  # status may have changed (ordered / escalated)

    return ChatResponse(
        reply=reply, session_id=session_id, escalated=session.human_escalated
    )
