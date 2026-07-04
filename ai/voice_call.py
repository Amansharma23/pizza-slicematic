"""Real-time voice call orchestrator (`CallSession`) — bridges one browser
WebSocket to Sarvam's streaming STT (held open for the whole call) and TTS (a
fresh connection per assistant turn), running the existing blocking chat agent
loop in between. See reference/VOICE_PIPELINE_ARCHITECTURE.md for the general
pattern this implements (task topology, barge-in, the stale-thread race).

Additive: `ai/routers/voice.py` (REST) and the agent/guardrails/tools it calls
into are untouched. This module only changes the audio transport.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time

from ai import agent, guardrails, observability, sarvam_stream
from ai import session as sess
from ai import voice_fillers
from ai.language import detect
from ai.profile import attach_user
from ai.routers.chat import _persist_turn

log = logging.getLogger(__name__)

VOICE_CAP_SECONDS = 180  # matches the REST /voice/transcribe cap
STT_CONNECT_ATTEMPTS = 2
STT_RETRY_BACKOFF_S = 0.3

# The voice payment stage (ai/agent.py:_stage_instruction) embeds the same
# [UPI_QR]/[CARD_FORM] tags chat uses, so the chat thread (visible on screen
# during a call) renders the real payment UI. These must never be spoken.
_PAYMENT_TAG_RE = re.compile(r"\[(?:UPI(?:_QR)?|CARD(?:_FORM)?)\]")
_UPI_RE = re.compile(r"\[UPI(?:_QR)?\]")
_UPI_FALLBACK_SPEECH = "You'll see a QR code on your screen — please scan it to pay."
_CARD_FALLBACK_SPEECH = (
    "You'll see a card payment form on your screen — please fill that in to pay."
)


def _speech_text(reply: str) -> str:
    """What to actually speak for a reply that may embed a payment UI tag: the
    tag itself stripped (never spoken), falling back to a canned sentence only
    if the model left no surrounding natural text of its own."""
    has_upi = bool(_UPI_RE.search(reply))
    stripped = _PAYMENT_TAG_RE.sub("", reply).strip()
    if stripped:
        return stripped
    return _UPI_FALLBACK_SPEECH if has_upi else _CARD_FALLBACK_SPEECH


def _discard_prewarm(task: asyncio.Task) -> None:
    """Close a speculatively-opened TTS connection (see _run_turn) whose turn
    got superseded before it was ever used. If the connect+configure hadn't
    finished yet, cancelling it is enough; if it already finished, we have to
    explicitly await it to get the close() and call that instead."""
    if task.cancel():
        return

    async def _close_it() -> None:
        try:
            _, close = await task
            await close()
        except Exception:
            pass

    asyncio.create_task(_close_it())


def _process_turn_sync(session, transcript: str) -> tuple[str, bool]:
    """The synchronous body run via `asyncio.to_thread` — identical to what the
    REST `/voice/respond` endpoint already does (guardrail + agent.run_turn
    under the session's lock). Kept as one function so the per-session
    threading.Lock is the thing that makes a stale, still-running call from a
    cancelled turn safe against a new turn's concurrent history mutation."""
    # Re-assert "voice" in case a payment-form tap on the chat thread (POST
    # /chat, same session_id) flipped it to "chat" for that one turn — this
    # session is live on a voice call, so every turn WE process must build a
    # voice-shaped prompt regardless of what the other channel last set.
    session.channel = "voice"
    session.language = detect(transcript)
    with sess.lock_for(session.id):
        check = guardrails.check_input(transcript, session.id)
        if check.ok:
            return agent.run_turn(session, transcript), False
        return check.message, True


class CallSession:
    """One real-time voice call. Construct with a FastAPI WebSocket, then
    `await run()`. All the tricky concurrency lives here; `ai/sarvam_stream.py`
    only wraps the provider SDK, and `ai/routers/voice_ws.py` is a one-liner."""

    def __init__(self, websocket) -> None:
        self.ws = websocket
        self.session = None
        self.stt: sarvam_stream.SttSession | None = None
        self.turn_id = 0
        self.turn_task: asyncio.Task | None = None
        self._out_q: asyncio.Queue = asyncio.Queue()
        self._background_tasks: set[asyncio.Task] = set()
        self._end_reason: str | None = None
        self._sent_ready = False

    # ------------------------------------------------------------------ #
    # outbound — every sender goes through one queue drained by one writer
    # ------------------------------------------------------------------ #
    async def _send_json(self, payload: dict) -> None:
        await self._out_q.put(("json", payload))

    async def _send_bytes(self, data: bytes) -> None:
        await self._out_q.put(("bytes", data))

    async def _write_browser(self) -> None:
        while True:
            kind, payload = await self._out_q.get()
            try:
                if kind == "json":
                    await self.ws.send_json(payload)
                else:
                    await self.ws.send_bytes(payload)
            except Exception:
                return  # socket's gone; asyncio.wait(FIRST_COMPLETED) unwinds teardown

    async def _end_call(self, reason: str) -> None:
        if self._end_reason is not None:
            return
        self._end_reason = reason
        await self._send_json({"type": "call_ended", "reason": reason})

    # ------------------------------------------------------------------ #
    # inbound — the ONLY task calling ws.receive()
    # ------------------------------------------------------------------ #
    async def _read_browser(self) -> None:
        while True:
            message = await self.ws.receive()
            if message["type"] == "websocket.disconnect":
                await self._end_call("connection_lost")
                return
            data = message.get("bytes")
            if data is not None:
                if self.stt is not None:
                    try:
                        await self.stt.send_audio(data)
                    except Exception:
                        pass  # transient; _stt_lifecycle owns reconnect/failure
                continue
            text = message.get("text")
            if text is not None and await self._handle_control(text):
                return

    async def _handle_control(self, text: str) -> bool:
        """Returns True if the reader loop should stop (graceful hangup)."""
        try:
            msg = json.loads(text)
        except ValueError:
            return False
        if msg.get("type") == "end_call":
            await self._end_call("user")
            return True
        return False  # mute/unmute are advisory-only (client stops sending audio)

    # ------------------------------------------------------------------ #
    # STT connection lifecycle: connect (with retry), consume events for the
    # whole call, one reconnect attempt if it drops mid-call.
    # ------------------------------------------------------------------ #
    async def _stt_lifecycle(self) -> None:
        for attempt in range(1, STT_CONNECT_ATTEMPTS + 1):
            try:
                async with sarvam_stream.stt_session() as stt:
                    self.stt = stt
                    if not self._sent_ready:
                        await self._send_json(
                            {
                                "type": "ready",
                                "audio_sample_rate": sarvam_stream.AUDIO_SAMPLE_RATE,
                            }
                        )
                        self._sent_ready = True
                        # If this is a fresh voice call (no user messages in history yet), speak greeting first.
                        has_user_msgs = any(
                            m.get("role") == "user" for m in self.session.history
                        )
                        if not has_user_msgs:
                            greeting_text = "Namaste! Welcome to SliceMatic. आज आप कौन सा पिज़्ज़ा ऑर्डर करना चाहेंगे?"
                            self.turn_id += 1
                            self.turn_task = asyncio.create_task(
                                self._speak_greeting(self.turn_id, greeting_text)
                            )
                    await self._consume_stt_events(stt)
                    return  # call ending for some other reason; clean exit
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.stt = None
                log.warning(
                    "Sarvam STT connection failed (attempt %d/%d): %s",
                    attempt,
                    STT_CONNECT_ATTEMPTS,
                    exc,
                )
                if attempt >= STT_CONNECT_ATTEMPTS:
                    if self.session is not None:
                        observability.score_session(
                            self.session.id,
                            "stt_failed",
                            True,
                            data_type="BOOLEAN",
                            comment=str(exc),
                        )
                    await self._end_call("stt_unavailable")
                    return
                await asyncio.sleep(STT_RETRY_BACKOFF_S)

    async def _consume_stt_events(self, stt: sarvam_stream.SttSession) -> None:
        async for event in stt:
            if event.kind == "vad_start":
                await self._send_json({"type": "vad", "signal": "start"})
                # Cheap and idempotent: the frontend just clears its playback
                # queue, a harmless no-op if nothing was playing. Avoids the
                # server needing to track "is TTS currently active" itself.
                await self._send_json({"type": "barge_in"})
            elif event.kind == "vad_end":
                await self._send_json({"type": "vad", "signal": "end"})
            elif event.kind == "transcript":
                text = (event.text or "").strip()
                if not text:
                    continue  # Sarvam can emit empty finals on pure noise
                if self.turn_task and not self.turn_task.done():
                    self.turn_task.cancel()  # barge-in, or a rapid double-final
                self.turn_id += 1
                self.turn_task = asyncio.create_task(self._run_turn(self.turn_id, text))
            # "error" events are already logged inside sarvam_stream.

    async def _speak_greeting(self, turn_id: int, text: str) -> None:
        self.session.add("assistant", text)
        await self._send_json(
            {
                "type": "assistant_text",
                "text": text,
                "blocked": False,
                "escalated": False,
            }
        )
        self._spawn_persist("Call Started", text)
        try:
            tts, close_tts = await sarvam_stream.open_tts_session("hi-IN")
            try:
                async for chunk in tts.speak(text):
                    if turn_id != self.turn_id:
                        return
                    if chunk.kind == "audio":
                        await self._send_bytes(chunk.audio)
                    else:
                        await self._send_json({"type": "assistant_audio_end"})
            finally:
                await close_tts()
        except Exception:
            log.exception("voice greeting failed")
            if self.session is not None:
                observability.score_session(
                    self.session.id, "tts_failed", True, data_type="BOOLEAN"
                )
            await self._send_json({"type": "tts_failed"})

    # ------------------------------------------------------------------ #
    # one assistant turn
    # ------------------------------------------------------------------ #
    async def _maybe_send_filler(
        self, turn_id: int, lang: str, llm_done: asyncio.Event
    ) -> None:
        """Speak a short "umm..."/"hmm..." pause-word immediately, the moment
        the turn starts — not gated behind a delay. It's a bare interjection
        (see ai/voice_fillers.py for why), short enough that timing it against
        the LLM isn't worth the complexity: if the LLM is fast, the filler
        just finishes and the real reply follows right after, same as a human
        saying "umm" reflexively even before an easy question. `llm_done` is
        still checked before every chunk so a genuinely instant reply cuts the
        filler short rather than talking over it.
        """
        if turn_id != self.turn_id or llm_done.is_set():
            return

        try:
            chunks = await voice_fillers.get_filler_audio(lang)
        except Exception:
            log.warning("filler audio unavailable", exc_info=True)
            return

        for chunk in chunks:
            if turn_id != self.turn_id or llm_done.is_set():
                return
            await self._send_bytes(chunk)
        # No assistant_audio_end here — that signal stays reserved for the
        # real reply's completion, so the frontend keeps waiting for it.

    async def _run_turn(self, turn_id: int, transcript: str) -> None:
        await self._send_json({"type": "user_transcript", "text": transcript})

        # Guess the reply's language from the user's own utterance and start
        # opening + configuring a TTS connection for it RIGHT NOW, in parallel
        # with the (much slower, 1-7s) LLM call — otherwise that ~100-300ms+
        # handshake happens entirely AFTER assistant_text is already on
        # screen, which is exactly the "text is fast, voice lags" gap this
        # closes. The guess is usually right: the assistant is instructed to
        # mirror the customer's language, so a mismatch is rare — and costs
        # nothing worse than today's behavior when it happens (see below).
        guessed_lang = "hi-IN" if detect(transcript) == "hi" else "en-IN"
        prewarm_task = asyncio.create_task(sarvam_stream.open_tts_session(guessed_lang))

        # Concurrently: an instant "umm..."/"hmm..." filler (see
        # _maybe_send_filler for why it's a bare interjection, fired
        # immediately, and how llm_done keeps it safe against an instant reply).
        llm_done = asyncio.Event()
        filler_lang = "hi" if guessed_lang == "hi-IN" else "en"
        filler_task = asyncio.create_task(
            self._maybe_send_filler(turn_id, filler_lang, llm_done)
        )

        await asyncio.sleep(0)

        t0 = time.perf_counter()
        try:
            reply, blocked = await asyncio.to_thread(
                _process_turn_sync, self.session, transcript
            )
        except Exception:
            log.exception("voice turn failed")
            reply, blocked = agent._apology(self.session.language), False
        finally:
            llm_done.set()
        filler_task.cancel()  # no-op if it already fired or finished
        log.info("[timing] AGENT(voice-rt) %.2fs", time.perf_counter() - t0)

        if turn_id != self.turn_id:
            _discard_prewarm(prewarm_task)
            return  # superseded by a newer turn (barge-in) — discard silently

        await self._send_json(
            {
                "type": "assistant_text",
                "text": reply,
                "blocked": blocked,
                "escalated": self.session.human_escalated,
            }
        )
        self._spawn_persist(transcript, reply)

        # Speak the natural-language text only — [UPI_QR]/[CARD_FORM] (if
        # present) render as the real payment UI in the chat thread above the
        # call, but must never be read aloud.
        speech = _speech_text(reply)
        actual_lang = "hi-IN" if detect(speech) == "hi" else "en-IN"

        tts = close_tts = None
        try:
            prewarmed_tts, prewarmed_close = await prewarm_task
            if actual_lang == guessed_lang:
                tts, close_tts = prewarmed_tts, prewarmed_close
            else:
                await prewarmed_close()  # rare: guessed wrong language, discard
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.warning("TTS prewarm failed, opening fresh: %s", exc)

        t_tts = time.perf_counter()
        try:
            if tts is None:
                tts, close_tts = await sarvam_stream.open_tts_session(actual_lang)
            async for chunk in tts.speak(speech):
                if turn_id != self.turn_id:
                    return
                if chunk.kind == "audio":
                    await self._send_bytes(chunk.audio)
                else:
                    await self._send_json({"type": "assistant_audio_end"})
            tts_seconds = time.perf_counter() - t_tts
            log.info("[timing] TTS(voice-rt) %.2fs", tts_seconds)
            observability.score_session(
                self.session.id, "tts_latency_seconds", tts_seconds, data_type="NUMERIC"
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("voice TTS failed")
            observability.score_session(
                self.session.id, "tts_failed", True, data_type="BOOLEAN"
            )
            await self._send_json({"type": "tts_failed"})
        finally:
            if close_tts is not None:
                await close_tts()

    def _spawn_persist(self, transcript: str, reply: str) -> None:
        t = asyncio.create_task(
            asyncio.to_thread(_persist_turn, self.session, transcript, reply, "voice")
        )
        self._background_tasks.add(t)
        t.add_done_callback(self._background_tasks.discard)

    # ------------------------------------------------------------------ #
    # lifecycle
    # ------------------------------------------------------------------ #
    async def run(self) -> None:
        await self.ws.accept()
        pending: set[asyncio.Task] = set()
        try:
            try:
                auth = await asyncio.wait_for(self.ws.receive_json(), timeout=5)
            except Exception:
                await self._safe_close(1008)
                return
            if auth.get("type") != "auth" or not auth.get("session_id"):
                await self._safe_close(1008)
                return

            session_id = str(auth["session_id"])
            self.session = sess.get_or_create(session_id, channel="voice")
            self.session.channel = "voice"
            token = auth.get("token")
            attach_user(self.session, f"Bearer {token}" if token else None)

            now = time.time()
            if self.session.voice_started_at is None:
                self.session.voice_started_at = now
            remaining = VOICE_CAP_SECONDS - (now - self.session.voice_started_at)
            if remaining <= 0:
                await self._end_call("cap_reached")
                await self._drain_queue()
                await self._safe_close(1000)
                return

            writer = asyncio.create_task(self._write_browser())
            reader = asyncio.create_task(self._read_browser())
            stt_life = asyncio.create_task(self._stt_lifecycle())
            cap = asyncio.create_task(asyncio.sleep(remaining))
            pending = {writer, reader, stt_life, cap}

            done, pending = await asyncio.wait(
                pending, return_when=asyncio.FIRST_COMPLETED
            )

            if self._end_reason is None:
                # None of the specific handlers claimed it — infer a reason.
                if cap in done:
                    await self._end_call("cap_reached")
                else:
                    await self._end_call("connection_lost")
            await self._drain_queue()
        except Exception:
            log.exception("voice call crashed")
            try:
                await self._end_call("server_error")
                await self._drain_queue()
            except Exception:
                pass
        finally:
            if hasattr(self, "session") and self.session:
                self.session.ended_at = time.time()
                sess.mirror(self.session)
            await self._teardown(pending)

    async def _drain_queue(self) -> None:
        """Best-effort: give the writer task a moment to flush the final
        call_ended message before teardown cancels it."""
        for _ in range(20):
            if self._out_q.empty():
                return
            await asyncio.sleep(0.02)

    async def _safe_close(self, code: int) -> None:
        try:
            await self.ws.close(code=code)
        except Exception:
            pass

    async def _teardown(self, pending: set[asyncio.Task]) -> None:
        if self.turn_task and not self.turn_task.done():
            self.turn_task.cancel()
        for t in pending:
            t.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        if self.turn_task:
            await asyncio.gather(self.turn_task, return_exceptions=True)
        await self._safe_close(1000)
