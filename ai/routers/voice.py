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

from fastapi import APIRouter, BackgroundTasks, File, Form, Header, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from ai import agent, deepgram, guardrails, sarvam
from ai import session as sess
from ai.config import get_settings
from ai.language import detect
from ai.profile import attach_user
from ai.routers.chat import _persist_turn

log = logging.getLogger(__name__)
router = APIRouter()

VOICE_CAP_SECONDS = 180  # 3-minute call cap


@router.post("/voice/start")
def voice_start(session_id: str = Form(...)) -> dict:
    """Begin a new voice call: reset the per-call 3-minute budget.

    The cap timer (``voice_started_at``) is otherwise set on the first transcribe
    and never cleared, so a reused session would carry an expired budget into the
    next call. Resetting here gives each call a fresh 3 minutes."""
    session = sess.get_or_create(session_id, channel="voice")
    session.channel = "voice"
    session.voice_started_at = None
    return {"session_id": session_id, "ok": True}


@router.post("/voice/transcribe")
def transcribe(session_id: str = Form(...), audio: UploadFile = File(...)) -> dict:
    session = sess.get_or_create(session_id, channel="voice")
    session.channel = "voice"
    now = time.time()
    if session.voice_started_at is None:
        session.voice_started_at = now
        sess.mirror(session)
    elif now - session.voice_started_at > VOICE_CAP_SECONDS:
        return {"session_id": session_id, "transcript": "", "call_ended": True}

    data = audio.file.read()
    ctype = audio.content_type or "audio/webm"
    fname = audio.filename or "audio.webm"
    bare = ctype.split(";")[0].strip()  # Deepgram wants the bare container
    s = get_settings()

    # STT: Sarvam Saarika primary (native Hindi + Indian English, auto-detects
    # language, accepts webm). Deepgram Nova-2 is the fallback.
    t0 = time.perf_counter()
    transcript, provider = "", "deepgram"
    if s.sarvam_enabled:
        try:
            transcript, _lang = sarvam.transcribe(data, ctype, fname)
            provider = "sarvam"
        except Exception as exc:
            log.warning("Sarvam STT failed (%s); trying Deepgram fallback", exc)
            provider = "deepgram(fallback)"
    if provider != "sarvam":
        try:
            transcript, _conf = deepgram.transcribe(data, bare)
        except Exception as exc:
            log.warning("STT failed: %s", exc)
            return {
                "session_id": session_id,
                "transcript": "",
                "error": "transcription_failed",
            }
    log.info(
        "[timing] STT %s %.2fs (%d bytes -> %d chars): %r",
        provider,
        time.perf_counter() - t0,
        len(data),
        len(transcript),
        transcript[:80],
    )
    return {
        "session_id": session_id,
        "transcript": transcript,
        "call_ended": False,
    }


class VoiceRespondRequest(BaseModel):
    transcript: str
    session_id: str | None = None


@router.post("/voice/respond")
def respond(
    req: VoiceRespondRequest,
    background: BackgroundTasks,
    authorization: str | None = Header(default=None),
) -> dict:
    session_id = req.session_id or uuid.uuid4().hex
    session = sess.get_or_create(session_id, channel="voice")
    session.channel = "voice"
    session.language = detect(req.transcript)
    # Signed-in customer (JWT) → real profile for get_customer_profile.
    attach_user(session, authorization)

    with sess.lock_for(session_id):
        check = guardrails.check_input(req.transcript)
        if check.ok:
            t0 = time.perf_counter()
            reply = agent.run_turn(session, req.transcript)
            log.info(
                "[timing] AGENT(voice) %.2fs (lang=%s -> %d chars)",
                time.perf_counter() - t0,
                session.language,
                len(reply),
            )
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
    # TTS: Sarvam Bulbul for both — native Hindi + Indian-accented English.
    # Deepgram Aura (US English) is the fallback if Sarvam errors/unconfigured.
    lang_code = "hi-IN" if detect(req.text) == "hi" else "en-IN"
    if get_settings().sarvam_enabled:
        try:
            t0 = time.perf_counter()
            audio = sarvam.synthesize(req.text, language_code=lang_code)
            log.info(
                "[timing] TTS sarvam(%s) %.2fs (%d chars -> %d bytes)",
                lang_code,
                time.perf_counter() - t0,
                len(req.text),
                len(audio),
            )
            return Response(content=audio, media_type="audio/wav")
        except Exception as exc:
            log.warning("Sarvam TTS failed, falling back to Deepgram: %s", exc)
    t0 = time.perf_counter()
    audio = deepgram.synthesize(req.text)
    log.info(
        "[timing] TTS deepgram(en) %.2fs (%d chars -> %d bytes)",
        time.perf_counter() - t0,
        len(req.text),
        len(audio),
    )
    return Response(content=audio, media_type="audio/mpeg")
