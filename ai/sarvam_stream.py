"""Sarvam streaming STT/TTS (real-time voice call) — the only module that imports
`sarvamai`. ai/sarvam.py (batch REST, bulbul:v2) is separate and untouched.

Wraps both streaming websocket connections behind small async context managers so
`ai/voice_call.py` never touches SDK types directly. Every kwarg value here was
verified against the INSTALLED sarvamai==0.1.28 package (signatures + a live call
with real credentials), not just documentation — see reference/VOICE_PIPELINE_
ARCHITECTURE.md for what was checked and why. Notably:
  - `high_vad_sensitivity` / `vad_signals` / `send_completion_event` are the STRING
    literals "true"/"false", not Python bools.
  - `output_audio_codec="linear16"` really does return headerless raw PCM
    (content_type "audio/pcm" in the response) — confirmed live, despite the
    installed SDK's own docstring claiming "currently supports MP3 only".
  - bulbul:v3 has its own speaker roster; v2 speakers (e.g. "abhilash") are invalid.
"""

from __future__ import annotations

import base64
import logging
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from functools import lru_cache
from typing import AsyncIterator, Awaitable, Callable, Literal

from ai.config import get_settings

log = logging.getLogger(__name__)

# bulbul:v3 native sample rate is 24kHz. Setting this prevents sample rate mismatch.
AUDIO_SAMPLE_RATE = 24000
MIC_SAMPLE_RATE = 16000


@lru_cache(maxsize=1)
def _client():
    from sarvamai import AsyncSarvamAI

    return AsyncSarvamAI(api_subscription_key=get_settings().sarvam_api_key)


# --------------------------------------------------------------------------- #
# STT streaming
# --------------------------------------------------------------------------- #


@dataclass
class SttEvent:
    kind: Literal["vad_start", "vad_end", "transcript", "error"]
    text: str | None = None
    language_code: str | None = None


class SttSession:
    """One live STT connection for the whole call. Feed it audio continuously;
    read events out of it via `async for`."""

    def __init__(self, ws) -> None:
        self._ws = ws

    async def send_audio(self, pcm16_bytes: bytes) -> None:
        await self._ws.transcribe(
            audio=base64.b64encode(pcm16_bytes).decode(),
            encoding="audio/wav",
            sample_rate=MIC_SAMPLE_RATE,
        )

    async def __aiter__(self) -> AsyncIterator[SttEvent]:
        async for message in self._ws:
            if message.type == "events":
                signal = message.data.signal_type
                if signal == "START_SPEECH":
                    yield SttEvent(kind="vad_start")
                elif signal == "END_SPEECH":
                    yield SttEvent(kind="vad_end")
            elif message.type == "data":
                # Check for finality. Only yield when transcription is final (is_final is True)
                # to prevent launching new LLM turns on partial/interim transcripts.
                data = message.data
                is_final = True
                if hasattr(data, "model_extra") and data.model_extra:
                    is_final = data.model_extra.get("is_final", True)
                elif hasattr(data, "__dict__"):
                    is_final = data.__dict__.get("is_final", True)

                if is_final is True:
                    if hasattr(message, "model_extra") and message.model_extra:
                        is_final = message.model_extra.get("is_final", True)
                    elif hasattr(message, "__dict__"):
                        is_final = message.__dict__.get("is_final", True)

                if is_final:
                    yield SttEvent(
                        kind="transcript",
                        text=data.transcript,
                        language_code=data.language_code,
                    )
            elif message.type == "error":
                log.warning("Sarvam STT error: %s", message.data)
                yield SttEvent(kind="error")


@asynccontextmanager
async def stt_session(language_code: str = "unknown"):
    # high_vad_sensitivity alone already fires fast — live calibration showed
    # END_SPEECH triggering on ordinary mid-sentence pauses, before any
    # trailing silence even started. Tightening the fine-grained frame-count
    # params further risks cutting people off mid-thought rather than helping,
    # and their exact semantics aren't reliably documented — not worth
    # guessing at without a way to validate the change is a net improvement.
    async with _client().speech_to_text_streaming.connect(
        model="saaras:v3",
        mode="transcribe",
        language_code=language_code,
        high_vad_sensitivity="true",
        vad_signals="true",
        input_audio_codec="pcm_s16le",
        sample_rate=str(MIC_SAMPLE_RATE),
    ) as ws:
        yield SttSession(ws)


# --------------------------------------------------------------------------- #
# TTS streaming
# --------------------------------------------------------------------------- #


@dataclass
class TtsChunk:
    kind: Literal["audio", "final"]
    audio: bytes | None = None


class TtsSession:
    """One TTS connection for ONE assistant turn — opened fresh per turn and
    closed on completion or cancellation (see reference doc §07: Sarvam's
    protocol has no documented "cancel this synthesis" message, so a shared
    long-lived connection risks stale audio leaking into the next turn)."""

    def __init__(self, ws) -> None:
        self._ws = ws

    async def speak(self, text: str) -> AsyncIterator[TtsChunk]:
        await self._ws.convert(text[:2500])
        await self._ws.flush()
        async for message in self._ws:
            if message.type == "audio":
                yield TtsChunk(kind="audio", audio=base64.b64decode(message.data.audio))
            elif message.type == "event" and message.data.event_type == "final":
                yield TtsChunk(kind="final")
                return
            elif message.type == "error":
                log.warning("Sarvam TTS error: %s", message.data)
                return


async def open_tts_session(
    target_language_code: str, speaker: str | None = None
) -> tuple[TtsSession, Callable[[], Awaitable[None]]]:
    """Connect + configure a TTS session and hand it back already-open, plus
    its own close(). Lets a caller START the (~100-300ms) connect+configure
    handshake speculatively BEFORE the text to speak is known — e.g. in
    parallel with the LLM call — instead of paying for it only after the
    reply is ready. `tts_session()` below is the simple wrapper for when that
    doesn't matter."""
    s = get_settings()
    stack = AsyncExitStack()
    ws = await stack.enter_async_context(
        _client().text_to_speech_streaming.connect(
            model="bulbul:v3", send_completion_event="true"
        )
    )
    await ws.configure(
        target_language_code=target_language_code,
        speaker=speaker or s.sarvam_v3_speaker,
        output_audio_codec="linear16",
        speech_sample_rate=AUDIO_SAMPLE_RATE,
        pace=1.2,  # Speed up pacing to sound natural and conversational
    )
    return TtsSession(ws), stack.aclose


@asynccontextmanager
async def tts_session(target_language_code: str, speaker: str | None = None):
    session, close = await open_tts_session(target_language_code, speaker)
    try:
        yield session
    finally:
        await close()
