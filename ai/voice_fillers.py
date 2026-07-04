"""Instant "thinking" filler pause-words for the realtime voice call — masks
whatever gap there is before the LLM answers, the way a real person says
"umm..." or "hmm..." reflexively rather than answering in dead silence.
Deliberately bare interjections, NOT full sentences like "let me check that
for you": a full sentence makes a specific promise the LLM's own reply (which
has no idea a filler was even spoken) can't coherently follow up on — e.g.
filler "let me check that for you" + reply "Sure! ..." reads as two
disconnected utterances. A bare "Hmm..." flows into literally any reply the
same way real hesitation does. See ai/voice_call.py:_run_turn for playback
(fires immediately, not gated behind a delay — it's short enough that timing
it against the LLM isn't worth the complexity).

Each phrase's audio is synthesized once per process lifetime and cached —
callers never pay a live Sarvam TTS call after the first use of a given
phrase (ai/main.py's warmup pre-populates the common case).
"""

from __future__ import annotations

import asyncio
import random

from ai import sarvam_stream

FILLERS_EN = ["Hmm...", "Umm...", "Ah, okay..."]
FILLERS_HI = ["Hmm...", "Achha...", "Umm..."]

_cache: dict[tuple[str, str], list[bytes]] = {}
_lock = asyncio.Lock()


async def _synthesize(lang_code: str, text: str) -> list[bytes]:
    chunks: list[bytes] = []
    async with sarvam_stream.tts_session(lang_code) as tts:
        async for chunk in tts.speak(text):
            if chunk.kind == "audio" and chunk.audio:
                chunks.append(chunk.audio)
    return chunks


async def get_filler_audio(lang: str) -> list[bytes]:
    """Random filler phrase's PCM chunks for lang ("hi" or "en"; anything else
    falls back to English). Synthesizes and caches on first use per phrase,
    reused for every call thereafter."""
    phrases = FILLERS_HI if lang == "hi" else FILLERS_EN
    lang_code = "hi-IN" if lang == "hi" else "en-IN"
    text = random.choice(
        phrases
    )  # nosec B311 - picking a filler phrase, not security-sensitive
    key = (lang_code, text)

    cached = _cache.get(key)
    if cached is not None:
        return cached

    async with _lock:
        cached = _cache.get(key)  # re-check: another caller may have won the race
        if cached is not None:
            return cached
        chunks = await _synthesize(lang_code, text)
        _cache[key] = chunks
        return chunks
