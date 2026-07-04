"""Regression test for the realtime voice call's barge-in race (ai/voice_call.py,
documented in reference/VOICE_PIPELINE_ARCHITECTURE.md §07): cancelling the
asyncio task awaiting a blocking agent.run_turn() call does NOT stop the
underlying thread once it has started running, so a stale turn can keep
running in the background after a new one starts. This asserts the turn_id
guard discards the stale reply and the per-session lock keeps session.history
from being corrupted by the two overlapping calls.

No pytest-asyncio dependency needed — plain asyncio.run() inside a sync test,
matching this repo's "no new deps for one test" convention.
"""

import asyncio
import time

from ai import agent, guardrails
from ai import session as sess
from ai import voice_call


class _FakeWebSocket:
    """Never actually used by _run_turn directly (outbound messages go
    through CallSession._out_q, drained here without a real writer task) —
    just satisfies CallSession's constructor."""


class _FakeTtsSession:
    async def speak(self, text: str):
        return
        yield  # pragma: no cover - unreachable; marks this an async generator


async def _fake_open_tts_session(target_language_code: str, speaker: str | None = None):
    async def _noop_close() -> None:
        return None

    return _FakeTtsSession(), _noop_close


def _drain(call: voice_call.CallSession) -> list[dict]:
    """Pull every queued outbound message off _out_q (no _write_browser task
    runs in this test) and return the JSON ones."""
    out = []
    while not call._out_q.empty():
        kind, payload = call._out_q.get_nowait()
        if kind == "json":
            out.append(payload)
    return out


def test_barge_in_discards_stale_reply_and_preserves_history_order(monkeypatch):
    session = sess.get_or_create("barge-in-race-test", channel="voice")
    session.history = [{"role": "system", "content": "sys"}]

    def fake_run_turn(sess_obj, transcript: str) -> str:
        if transcript == "first (stale)":
            time.sleep(0.3)  # simulate a slow LLM call that outlives cancellation
        sess_obj.add("user", transcript)
        sess_obj.add("assistant", f"reply to: {transcript}")
        return f"reply to: {transcript}"

    monkeypatch.setattr(agent, "run_turn", fake_run_turn)
    monkeypatch.setattr(
        guardrails,
        "check_input",
        lambda text, session_id=None: guardrails.InputCheck(ok=True, category="SAFE"),
    )
    monkeypatch.setattr(voice_call, "_persist_turn", lambda *a, **k: None)
    monkeypatch.setattr(
        voice_call.sarvam_stream, "open_tts_session", _fake_open_tts_session
    )

    async def scenario():
        call = voice_call.CallSession(_FakeWebSocket())
        call.session = session

        call.turn_id = 1
        first_task = asyncio.create_task(call._run_turn(1, "first (stale)"))
        call.turn_task = first_task
        await asyncio.sleep(0.05)  # let it start and enter the blocking call

        # Barge-in, exactly as _consume_stt_events does on a new final
        # transcript: cancel (may or may not take effect — the executor
        # thread may already be running) and start a new turn.
        first_task.cancel()
        call.turn_id = 2
        second_task = asyncio.create_task(call._run_turn(2, "second"))
        call.turn_task = second_task
        await second_task

        try:
            await asyncio.gather(first_task, return_exceptions=True)
        except asyncio.CancelledError:
            pass

        return call

    call = asyncio.run(scenario())
    sent = _drain(call)

    assistant_texts = [m["text"] for m in sent if m.get("type") == "assistant_text"]
    assert assistant_texts == [
        "reply to: second"
    ], "the stale (barged-in-over) turn's reply must never reach the client"

    entries = [(m["role"], m.get("content")) for m in session.history]
    assert ("user", "first (stale)") in entries
    assert ("user", "second") in entries
    assert entries.index(("user", "first (stale)")) < entries.index(
        ("user", "second")
    ), (
        "the per-session lock must serialize the stale call before the new one "
        "starts — never interleaved"
    )
