"use client";

import { useEffect, useRef, useState } from "react";

import { voiceCallWsUrl } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { useChatStore } from "@/lib/store";
import { StreamingAudioPlayer } from "@/lib/voice/audio-player";
import { startMicCapture } from "@/lib/voice/mic-capture";
import { useRestVoiceCall } from "@/lib/voice/rest-call-machine";

export type VoiceState =
  | "idle"
  | "connecting"
  | "listening"
  | "thinking"
  | "speaking"
  | "ended"
  | "denied"
  | "unsupported";

/**
 * Realtime, full-duplex voice call: continuous mic streaming over one
 * WebSocket to /voice/call, server-side turn detection (VAD), streaming TTS
 * playback, and barge-in. Replaces the old record-on-silence -> upload ->
 * batch STT/LLM/TTS -> download -> play pipeline. See
 * reference/VOICE_PIPELINE_ARCHITECTURE.md for the general pattern and why
 * each piece is built this way.
 *
 * Set NEXT_PUBLIC_VOICE_MODE=rest to fall back to the original REST
 * implementation (lib/voice/rest-call-machine.ts, preserved verbatim)
 * without a code rollback — a safety net for a rewrite this size.
 */

const CAP_MS = 180_000; // matches the server's 3-minute cap (authoritative server-side)

function isSupported(): boolean {
  return (
    typeof navigator !== "undefined" &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof WebSocket !== "undefined" &&
    (typeof AudioContext !== "undefined" ||
      typeof (window as unknown as { webkitAudioContext?: unknown })
        .webkitAudioContext !== "undefined")
  );
}

function endReasonMessage(reason: string): string {
  switch (reason) {
    case "cap_reached":
      return "Call ended (3-minute limit). Start a new call or keep typing.";
    case "stt_unavailable":
      return "Voice service is temporarily unavailable. Please try again shortly.";
    case "connection_lost":
      return "Connection lost. Start a new call when you're ready.";
    default:
      return "Something went wrong with the call. Please try again.";
  }
}

interface Setters {
  setState: (s: VoiceState) => void;
  setError: (e: string | null) => void;
  setRemainingMs: (ms: number | null) => void;
  setMuted: (m: boolean) => void;
}

/** Imperative call machine, mirroring the REST version's shape (built once
 *  via closures) but driving the realtime WS protocol instead. */
function createRealtimeCallMachine({
  setState,
  setError,
  setRemainingMs,
  setMuted,
}: Setters) {
  let ws: WebSocket | null = null;
  let stream: MediaStream | null = null;
  let micStop: (() => void) | null = null;
  let player: StreamingAudioPlayer | null = null;
  let active = false;
  let muted = false;
  let startedAt = 0;
  let capTimer: ReturnType<typeof setInterval> | null = null;

  function cleanup() {
    if (capTimer) {
      clearInterval(capTimer);
      capTimer = null;
    }
    micStop?.();
    micStop = null;
    stream?.getTracks().forEach((t) => t.stop());
    stream = null;
    player?.close();
    player = null;
    if (ws) {
      ws.onmessage = null;
      ws.onclose = null;
      ws.onerror = null;
      try {
        ws.close();
      } catch {
        /* ignore */
      }
      ws = null;
    }
  }

  function startCapTimer() {
    // setInterval (not requestAnimationFrame) so the countdown keeps ticking
    // in a backgrounded tab — cosmetic only, since the server enforces the
    // real cap regardless of what the client displays.
    capTimer = setInterval(() => {
      const rem = Math.max(0, CAP_MS - (Date.now() - startedAt));
      setRemainingMs(rem);
      if (rem <= 0 && capTimer) {
        clearInterval(capTimer);
        capTimer = null;
      }
    }, 250);
  }

  function handleControl(msg: Record<string, unknown>) {
    const store = useChatStore.getState();
    switch (msg.type) {
      case "vad":
        break; // informational only — the mic never stops in realtime mode
      case "barge_in":
        player?.stopAll();
        if (active) setState("listening");
        break;
      case "user_transcript":
        store.appendUserMessage(String(msg.text ?? ""));
        if (active) setState("thinking");
        break;
      case "assistant_text":
        store.appendAssistantMessage(String(msg.text ?? ""), {
          blocked: Boolean(msg.blocked),
          escalated: Boolean(msg.escalated),
        });
        if (active) setState("speaking");
        break;
      case "assistant_audio_end":
        player?.markEnd(() => {
          if (active) setState("listening");
        });
        break;
      case "tts_failed":
        if (active) setState("listening");
        break;
      case "call_ended": {
        const reason = String(msg.reason ?? "server_error");
        if (reason !== "user") setError(endReasonMessage(reason));
        active = false;
        cleanup();
        setRemainingMs(null);
        setState(reason === "user" ? "idle" : "ended");
        break;
      }
      default:
        break;
    }
  }

  function endCall(reason: "user" | "ended" = "user") {
    if (active && ws && ws.readyState === WebSocket.OPEN) {
      try {
        ws.send(JSON.stringify({ type: "end_call" }));
      } catch {
        /* ignore */
      }
    }
    active = false;
    cleanup();
    setRemainingMs(null);
    setState(reason === "ended" ? "ended" : "idle");
  }

  async function start() {
    setError(null);
    if (!isSupported()) {
      setState("unsupported");
      return;
    }
    setState("connecting");
    try {
      const sessionId = useChatStore.getState().ensureSessionId();
      const token = useAuthStore.getState().token;

      // Echo cancellation matters here: the mic stays open while the
      // assistant's own voice plays through the speakers.
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });

      await new Promise<void>((resolve, reject) => {
        const socket = new WebSocket(voiceCallWsUrl());
        socket.binaryType = "arraybuffer";
        ws = socket;
        let resolvedReady = false;

        socket.addEventListener("open", () => {
          socket.send(JSON.stringify({ type: "auth", session_id: sessionId, token }));
        });

        socket.onmessage = (ev) => {
          if (typeof ev.data !== "string") {
            if (resolvedReady) {
              player?.enqueue(ev.data as ArrayBuffer);
              if (active) setState("speaking");
            }
            return;
          }
          let msg: Record<string, unknown>;
          try {
            msg = JSON.parse(ev.data);
          } catch {
            return;
          }
          if (!resolvedReady) {
            if (msg.type === "ready") {
              resolvedReady = true;
              player = new StreamingAudioPlayer(Number(msg.audio_sample_rate) || 22050);
              resolve();
            } else if (msg.type === "call_ended") {
              reject(new Error(String(msg.reason ?? "connect_failed")));
            }
            return;
          }
          handleControl(msg);
        };
        socket.onerror = () => {
          if (!resolvedReady) reject(new Error("ws_error"));
        };
        socket.onclose = () => {
          if (!resolvedReady) {
            reject(new Error("ws_closed"));
          } else if (active) {
            active = false;
            cleanup();
            setRemainingMs(null);
            setError(endReasonMessage("connection_lost"));
            setState("ended");
          }
        };
      });

      await player!.resume();
      const capture = await startMicCapture(stream, (chunk) => {
        if (!muted && ws && ws.readyState === WebSocket.OPEN) {
          ws.send(chunk);
        }
      });
      micStop = capture.stop;

      active = true;
      muted = false;
      setMuted(false);
      startedAt = Date.now();
      setRemainingMs(CAP_MS);
      startCapTimer();
      setState("listening");
    } catch {
      cleanup();
      setState("denied");
      setError("Microphone blocked. Allow mic access to start a voice call.");
    }
  }

  function toggleMute() {
    if (!active) return;
    muted = !muted;
    setMuted(muted);
    try {
      ws?.send(JSON.stringify({ type: muted ? "mute" : "unmute" }));
    } catch {
      /* ignore */
    }
  }

  return { start, end: () => endCall("user"), toggleMute };
}

function useRealtimeVoiceCall() {
  const [state, setState] = useState<VoiceState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [remainingMs, setRemainingMs] = useState<number | null>(null);
  const [muted, setMuted] = useState(false);
  const [mounted, setMounted] = useState(false);

  const machineRef = useRef<ReturnType<typeof createRealtimeCallMachine> | null>(
    null
  );
  if (machineRef.current === null && typeof window !== "undefined") {
    machineRef.current = createRealtimeCallMachine({
      setState,
      setError,
      setRemainingMs,
      setMuted,
    });
  }

  useEffect(() => setMounted(true), []);
  useEffect(() => () => machineRef.current?.end(), []);

  const supported = mounted && isSupported();
  const isActive = ["connecting", "listening", "thinking", "speaking"].includes(
    state
  );

  return {
    state,
    error,
    remainingMs,
    muted,
    supported,
    isActive,
    startCall: () => machineRef.current?.start(),
    endCall: () => machineRef.current?.end(),
    toggleMute: () => machineRef.current?.toggleMute(),
  };
}

// NEXT_PUBLIC_* env vars are inlined at build time — this is a fixed choice
// for the whole app's lifetime, not a per-render conditional, so aliasing
// useVoiceCall to one hook or the other here never violates rules-of-hooks.
export const useVoiceCall =
  process.env.NEXT_PUBLIC_VOICE_MODE === "rest" ? useRestVoiceCall : useRealtimeVoiceCall;
