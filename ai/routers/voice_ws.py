"""WS /voice/call — the real-time voice call endpoint. Thin by design: all the
orchestration lives in ai/voice_call.CallSession. Additive alongside the
existing REST voice endpoints in ai/routers/voice.py (unmodified).
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket

from ai.voice_call import CallSession

router = APIRouter()


@router.websocket("/voice/call")
async def voice_call(websocket: WebSocket) -> None:
    await CallSession(websocket).run()
