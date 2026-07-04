"""Regression tests for the instant "umm..."/"hmm..." filler (ai/voice_call.py,
_maybe_send_filler / _run_turn): it fires immediately for every turn (not
gated behind a delay — see ai/voice_fillers.py for why a bare interjection
makes that safe), but must never overlap with the real reply's own audio, and
must never fire at all once a turn has been superseded (barge-in) or the LLM
has already answered.

Same conventions as tests/test_voice_call.py: plain asyncio.run() inside sync
tests, no pytest-asyncio dependency, fakes for the Sarvam TTS/STT calls.
"""

import asyncio
import time

from ai import agent, guardrails
from ai import session as sess
from ai import voice_call
from ai.sarvam_stream import TtsChunk


class _FakeWebSocket:
    """Never actually used directly — outbound messages go through
    CallSession._out_q, drained here without a real writer task."""


class _FakeTtsSession:
    """Yields one recognizable "real reply" audio chunk, unlike
    test_voice_call.py's empty fake — needed here to tell filler bytes and
    real-reply bytes apart in the drained queue."""

    async def speak(self, text: str):
        yield TtsChunk(kind="audio", audio=b"REAL_REPLY_AUDIO")
        yield TtsChunk(kind="final")


async def _fake_open_tts_session(target_language_code: str, speaker: str | None = None):
    async def _noop_close() -> None:
        return None

    return _FakeTtsSession(), _noop_close


async def _fake_get_filler_audio(lang: str) -> list[bytes]:
    return [b"FILLER_CHUNK_1", b"FILLER_CHUNK_2"]


def _drain_bytes(call: voice_call.CallSession) -> list[bytes]:
    """Pull every queued outbound BYTES message off _out_q, in order."""
    out = []
    while not call._out_q.empty():
        kind, payload = call._out_q.get_nowait()
        if kind == "bytes":
            out.append(payload)
    return out


def _make_call(monkeypatch, session, llm_delay: float):
    """Shared setup: a fake run_turn that sleeps `llm_delay` before replying."""

    def fake_run_turn(sess_obj, transcript: str) -> str:
        if llm_delay:
            time.sleep(llm_delay)
        sess_obj.add("user", transcript)
        sess_obj.add("assistant", "the real reply")
        return "the real reply"

    monkeypatch.setattr(agent, "run_turn", fake_run_turn)
    monkeypatch.setattr(
        guardrails,
        "check_input",
        lambda text: guardrails.InputCheck(ok=True, category="SAFE"),
    )
    monkeypatch.setattr(voice_call, "_persist_turn", lambda *a, **k: None)
    monkeypatch.setattr(
        voice_call.sarvam_stream, "open_tts_session", _fake_open_tts_session
    )
    monkeypatch.setattr(
        voice_call.voice_fillers, "get_filler_audio", _fake_get_filler_audio
    )

    call = voice_call.CallSession(_FakeWebSocket())
    call.session = session
    call.turn_id = 1
    return call


def test_filler_always_fires_then_real_reply_follows(monkeypatch):
    """The filler is a bare interjection fired immediately for every turn
    (not gated behind an LLM-speed check) — even a fast LLM should still get
    the filler first, then its own reply right after, never interleaved."""
    session = sess.get_or_create("filler-test-fast", channel="voice")
    session.history = [{"role": "system", "content": "sys"}]
    call = _make_call(monkeypatch, session, llm_delay=0.0)

    asyncio.run(call._run_turn(1, "hello"))
    sent = _drain_bytes(call)

    assert sent == [
        b"FILLER_CHUNK_1",
        b"FILLER_CHUNK_2",
        b"REAL_REPLY_AUDIO",
    ], "filler must play in full, then the real reply — never interleaved or duplicated"


def test_slow_llm_also_gets_filler_first(monkeypatch):
    session = sess.get_or_create("filler-test-slow", channel="voice")
    session.history = [{"role": "system", "content": "sys"}]
    call = _make_call(monkeypatch, session, llm_delay=0.4)

    asyncio.run(call._run_turn(1, "hello"))
    sent = _drain_bytes(call)

    assert sent == [b"FILLER_CHUNK_1", b"FILLER_CHUNK_2", b"REAL_REPLY_AUDIO"]


def test_maybe_send_filler_returns_immediately_when_llm_already_done(monkeypatch):
    """If the LLM has already answered by the time the filler task actually
    runs (e.g. a superseded/stale turn getting cleaned up), it must send
    nothing — never talk over or duplicate the real reply."""
    session = sess.get_or_create("filler-test-already-done", channel="voice")
    monkeypatch.setattr(
        voice_call.voice_fillers, "get_filler_audio", _fake_get_filler_audio
    )

    async def scenario():
        call = voice_call.CallSession(_FakeWebSocket())
        call.session = session
        call.turn_id = 1
        llm_done = asyncio.Event()
        llm_done.set()  # LLM "already answered" before the filler task even runs
        await call._maybe_send_filler(1, "en", llm_done)
        return call

    call = asyncio.run(scenario())
    assert (
        _drain_bytes(call) == []
    ), "an already-finished LLM must never trigger a filler"


def test_maybe_send_filler_respects_barge_in(monkeypatch):
    """A superseded turn_id (barge-in happened) must silence the filler too,
    same guard the real reply's own TTS loop uses."""
    session = sess.get_or_create("filler-test-bargein", channel="voice")
    monkeypatch.setattr(
        voice_call.voice_fillers, "get_filler_audio", _fake_get_filler_audio
    )

    async def scenario():
        call = voice_call.CallSession(_FakeWebSocket())
        call.session = session
        call.turn_id = 2  # a newer turn has already superseded turn_id=1
        llm_done = asyncio.Event()
        await call._maybe_send_filler(1, "en", llm_done)
        return call

    call = asyncio.run(scenario())
    assert _drain_bytes(call) == [], "a superseded turn must never speak a filler"
