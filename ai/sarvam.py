"""Sarvam AI (Bulbul) — native Hindi text-to-speech over plain HTTP.

Used for Hindi replies on voice calls (Deepgram Aura is English-only). Returns
WAV bytes. Speaker/model are configurable (SARVAM_SPEAKER / SARVAM_MODEL) since
Bulbul's available voices differ between model versions.
"""

from __future__ import annotations

import base64
import logging

import httpx

from ai.config import get_settings

log = logging.getLogger(__name__)

_TTS_URL = "https://api.sarvam.ai/text-to-speech"
_STT_URL = "https://api.sarvam.ai/speech-to-text"
# Bulbul caps input length per call; voice replies are short, but guard anyway.
_MAX_CHARS = 1500


def transcribe(
    audio: bytes, content_type: str = "audio/webm", filename: str = "audio.webm"
) -> tuple[str, str]:
    """Audio bytes -> (transcript, detected language_code). Saarika auto-detects
    the language (Hindi / Indian English / code-mixed). Accepts webm/opus, wav,
    mp3. Raises on HTTP error so the caller can fall back to Deepgram."""
    s = get_settings()
    if not s.sarvam_api_key:
        raise RuntimeError("Sarvam not configured (SARVAM_API_KEY missing).")
    ctype = (content_type or "audio/webm").split(";")[0].strip()
    resp = httpx.post(
        _STT_URL,
        headers={"api-subscription-key": s.sarvam_api_key},
        files={"file": (filename, audio, ctype)},
        data={"model": s.sarvam_stt_model, "language_code": "unknown"},
        timeout=60,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Sarvam STT {resp.status_code}: {resp.text[:300]}")
    body = resp.json()
    return body.get("transcript", ""), body.get("language_code", "")


def synthesize(text: str, language_code: str = "hi-IN") -> bytes:
    """Hindi text -> WAV audio bytes. Raises on HTTP/empty-audio error."""
    s = get_settings()
    if not s.sarvam_api_key:
        raise RuntimeError("Sarvam not configured (SARVAM_API_KEY missing).")
    resp = httpx.post(
        _TTS_URL,
        headers={
            "api-subscription-key": s.sarvam_api_key,
            "Content-Type": "application/json",
        },
        json={
            "inputs": [text[:_MAX_CHARS]],
            "target_language_code": language_code,
            "speaker": s.sarvam_speaker,
            "model": s.sarvam_model,
            "enable_preprocessing": True,
            "speech_sample_rate": 22050,
        },
        timeout=60,
    )
    if resp.status_code != 200:
        # Surface Sarvam's message (e.g. bad speaker/language) instead of a bare 400.
        raise RuntimeError(f"Sarvam {resp.status_code}: {resp.text[:300]}")
    audios = resp.json().get("audios") or []
    if not audios:
        raise RuntimeError("Sarvam returned no audio.")
    return base64.b64decode(audios[0])
