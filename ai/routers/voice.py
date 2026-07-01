"""Voice endpoints — browser mic in, AI speech out. Same agent as chat.

  POST /voice/transcribe  audio + session_id -> transcript (enforces 3-min cap)
  POST /voice/respond     transcript + session_id -> text reply (agent, channel=voice)
  POST /voice/synthesize  text -> audio/mpeg (Deepgram Aura; Hindi is Phase 2)

No telephony — the browser captures and plays audio.
"""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from ai import agent, deepgram, guardrails
from ai import session as sess
from ai.language import detect
from ai.routers.chat import _persist_turn

log = logging.getLogger(__name__)
router = APIRouter()

VOICE_CAP_SECONDS = 180  # 3-minute call cap


@router.post("/voice/transcribe")
def transcribe(session_id: str = Form(...), audio: UploadFile = File(...)) -> dict:
    session = sess.get_or_create(session_id, channel="voice")
    now = time.time()
    if session.voice_started_at is None:
        session.voice_started_at = now
        sess.mirror(session)
    elif now - session.voice_started_at > VOICE_CAP_SECONDS:
        return {"session_id": session_id, "transcript": "", "call_ended": True}

    data = audio.file.read()
    try:
        transcript, confidence = deepgram.transcribe(
            data, audio.content_type or "audio/webm"
        )
    except Exception as exc:
        log.warning("STT failed: %s", exc)
        return {
            "session_id": session_id,
            "transcript": "",
            "error": "transcription_failed",
        }
    return {
        "session_id": session_id,
        "transcript": transcript,
        "confidence": confidence,
        "call_ended": False,
    }


class VoiceRespondRequest(BaseModel):
    transcript: str
    session_id: str | None = None


@router.post("/voice/respond")
def respond(req: VoiceRespondRequest, background: BackgroundTasks) -> dict:
    session_id = req.session_id or uuid.uuid4().hex
    session = sess.get_or_create(session_id, channel="voice")
    session.language = detect(req.transcript)

    with sess.lock_for(session_id):
        check = guardrails.check_input(req.transcript)
        if check.ok:
            reply = agent.run_turn(session, req.transcript)
            blocked = False
        else:
            reply = check.message
            blocked = True

    background.add_task(_persist_turn, session, req.transcript, reply, "voice")

    return {
        "reply": reply,
        "session_id": session_id,
        "escalated": session.human_escalated,
        "blocked": blocked,
    }


class SynthesizeRequest(BaseModel):
    text: str
    language: str = "en"


@router.post("/voice/synthesize")
def synthesize(req: SynthesizeRequest) -> Response:
    audio = deepgram.synthesize(req.text, language=req.language)
    return Response(content=audio, media_type="audio/mpeg")
