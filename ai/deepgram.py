"""Deepgram STT/TTS over plain HTTP (no extra SDK).

STT: Nova-2 with language=multi for English + Hindi.
TTS: Aura (English). Hindi TTS is the marked Phase-2 swap — Aura is English-only,
so for Hindi we'd route to Google Cloud / Azure TTS here.
"""

from __future__ import annotations

import logging

import httpx

from ai.config import get_settings

log = logging.getLogger(__name__)

_STT_URL = "https://api.deepgram.com/v1/listen"
_TTS_URL = "https://api.deepgram.com/v1/speak"
_TTS_MODEL_EN = "aura-asteria-en"


def transcribe(audio: bytes, content_type: str = "audio/webm") -> tuple[str, float]:
    """Audio bytes -> (transcript, confidence). Raises on HTTP error."""
    key = get_settings().deepgram_api_key
    resp = httpx.post(
        _STT_URL,
        params={"model": "nova-2", "language": "multi", "smart_format": "true"},
        content=audio,
        headers={"Authorization": f"Token {key}", "Content-Type": content_type},
        timeout=60,
    )
    resp.raise_for_status()
    alt = resp.json()["results"]["channels"][0]["alternatives"][0]
    return alt.get("transcript", ""), float(alt.get("confidence", 0.0))


def synthesize(text: str, language: str = "en") -> bytes:
    """Text -> MP3 audio bytes. English via Aura; Hindi is the Phase-2 swap point."""
    key = get_settings().deepgram_api_key
    # PHASE 2: if language == "hi", call Google Cloud / Azure TTS instead of Aura.
    resp = httpx.post(
        _TTS_URL,
        params={"model": _TTS_MODEL_EN},
        json={"text": text},
        headers={"Authorization": f"Token {key}", "Content-Type": "application/json"},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.content
