"use client";

import { useEffect, useRef, useState } from "react";

import { startVoiceCall, synthesizeSpeech, transcribeVoice } from "@/lib/api";
import { useChatStore } from "@/lib/store";

/**
 * Hands-free voice CALL for the chat (Claude-app style). Tap to start a call:
 * the mic listens continuously, voice-activity detection (Web Audio analyser)
 * auto-ends your turn on silence → /voice/transcribe → the transcript enters the
 * SAME chat thread (store.sendVoice) → /voice/synthesize the reply → speak it →
 * listen again. Loops until you hang up or the 3-minute cap is hit. The whole
 * exchange also shows as chat bubbles.
 */

const CAP_MS = 180_000; // 3-minute call cap
const SILENCE_MS = 1200; // trailing silence that ends a spoken turn
const MAX_SEG_MS = 15_000; // hard cap on a single utterance
const SPEECH_LEVEL = 0.02; // RMS threshold that counts as speech

// Spoken the instant a call connects — hardcoded so there's no LLM latency.
const CALL_GREETING = "Hey! Welcome to SliceMatic. What are you craving today?";

export type VoiceState =
  | "idle"
  | "connecting"
  | "listening"
  | "thinking"
  | "speaking"
  | "ended"
  | "denied"
  | "unsupported";

function isSupported(): boolean {
  return (
    typeof navigator !== "undefined" &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof MediaRecorder !== "undefined" &&
    (typeof AudioContext !== "undefined" ||
      typeof (window as unknown as { webkitAudioContext?: unknown })
        .webkitAudioContext !== "undefined")
  );
}

function recorderOpts(): MediaRecorderOptions {
  for (const mimeType of ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"]) {
    if (MediaRecorder.isTypeSupported(mimeType)) return { mimeType };
  }
  return {};
}

interface Setters {
  setState: (s: VoiceState) => void;
  setError: (e: string | null) => void;
  setRemainingMs: (ms: number | null) => void;
  setMuted: (m: boolean) => void;
}

/** Imperative call machine — built once, drives its own audio via closures to
 *  avoid React stale-closure issues in the listen/respond/speak loop. */
function createCallMachine({ setState, setError, setRemainingMs, setMuted }: Setters) {
  let stream: MediaStream | null = null;
  let audioCtx: AudioContext | null = null;
  let analyser: AnalyserNode | null = null;
  let recorder: MediaRecorder | null = null;
  let chunks: Blob[] = [];
  let audioEl: HTMLAudioElement | null = null;
  let raf = 0;
  let active = false;
  let muted = false;
  let hasSpoken = false;
  let lastSpeech = 0;
  let segStart = 0;
  let startedAt = 0;

  function cleanup() {
    cancelAnimationFrame(raf);
    if (recorder && recorder.state !== "inactive") {
      recorder.onstop = null;
      try {
        recorder.stop();
      } catch {
        /* ignore */
      }
    }
    recorder = null;
    stream?.getTracks().forEach((t) => t.stop());
    stream = null;
    audioCtx?.close().catch(() => {});
    audioCtx = null;
    analyser = null;
    if (audioEl) {
      audioEl.pause();
      audioEl = null;
    }
  }

  function endCall(reason: "user" | "ended" = "user") {
    active = false;
    cleanup();
    setRemainingMs(null);
    setState(reason === "ended" ? "ended" : "idle");
  }

  function rms(): number {
    if (!analyser) return 0;
    const buf = new Uint8Array(analyser.fftSize);
    analyser.getByteTimeDomainData(buf);
    let sum = 0;
    for (let i = 0; i < buf.length; i++) {
      const v = (buf[i] - 128) / 128;
      sum += v * v;
    }
    return Math.sqrt(sum / buf.length);
  }

  function monitor() {
    if (!active) return;
    const now = Date.now();
    const rem = Math.max(0, CAP_MS - (now - startedAt));
    setRemainingMs(rem);
    if (rem <= 0) {
      endCall("ended");
      return;
    }
    if (!muted) {
      if (rms() > SPEECH_LEVEL) {
        hasSpoken = true;
        lastSpeech = now;
      }
      const endedTurn = hasSpoken && now - lastSpeech > SILENCE_MS;
      const tooLong = hasSpoken && now - segStart > MAX_SEG_MS;
      if (endedTurn || tooLong) {
        stopSegment();
        return;
      }
    }
    raf = requestAnimationFrame(monitor);
  }

  function beginListening() {
    if (!active) return;
    setState("listening");
    chunks = [];
    hasSpoken = false;
    lastSpeech = Date.now();
    segStart = Date.now();
    try {
      recorder = new MediaRecorder(stream!, recorderOpts());
    } catch {
      recorder = new MediaRecorder(stream!);
    }
    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.push(e.data);
    };
    recorder.onstop = () => void processSegment();
    recorder.start();
    raf = requestAnimationFrame(monitor);
  }

  function stopSegment() {
    cancelAnimationFrame(raf);
    if (recorder && recorder.state !== "inactive") recorder.stop();
  }

  async function processSegment() {
    if (!active) return;
    if (!hasSpoken) {
      beginListening(); // no speech captured — keep listening
      return;
    }
    setState("thinking");
    const blob = new Blob(chunks, { type: chunks[0]?.type || "audio/webm" });
    const sessionId = useChatStore.getState().ensureSessionId();

    let transcript = "";
    try {
      const tr = await transcribeVoice(blob, sessionId);
      if (!active) return;
      if (tr.call_ended) {
        endCall("ended");
        return;
      }
      if (tr.error || !tr.transcript?.trim()) {
        beginListening();
        return;
      }
      transcript = tr.transcript;
    } catch {
      if (active) beginListening();
      return;
    }

    // Run the agent, then speak the reply. (No filler phrases — brevity is
    // handled by the voice system prompt instead.)
    const reply = await useChatStore.getState().sendVoice(transcript);
    if (!active) return;
    if (reply) {
      setState("speaking");
      await playTts(reply);
    }
    if (active) beginListening();
  }

  /** Synthesize + play; resolves when playback ends (so turns can be sequenced). */
  async function playTts(text: string): Promise<void> {
    if (!active) return;
    let blob: Blob;
    try {
      blob = await synthesizeSpeech(text);
    } catch {
      return; // TTS failed — reply still visible as text
    }
    if (!active) return;
    await new Promise<void>((resolve) => {
      const url = URL.createObjectURL(blob);
      audioEl = new Audio(url);
      const done = () => {
        URL.revokeObjectURL(url);
        audioEl = null;
        resolve();
      };
      audioEl.onended = done;
      audioEl.onerror = done;
      audioEl.play().catch(() => done());
    });
  }

  async function start() {
    setError(null);
    if (!isSupported()) {
      setState("unsupported");
      return;
    }
    setState("connecting");
    try {
      // Reset the per-call budget and grab the mic in parallel (less latency).
      const sessionId = useChatStore.getState().ensureSessionId();
      const [, micStream] = await Promise.all([
        startVoiceCall(sessionId),
        navigator.mediaDevices.getUserMedia({ audio: true }),
      ]);
      stream = micStream;
      const AC =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext })
          .webkitAudioContext;
      audioCtx = new AC();
      await audioCtx.resume().catch(() => {});
      const src = audioCtx.createMediaStreamSource(stream);
      analyser = audioCtx.createAnalyser();
      analyser.fftSize = 1024;
      src.connect(analyser);
      active = true;
      muted = false;
      setMuted(false);
      startedAt = Date.now();
      // SliceMatic greets first (hardcoded → instant), then starts listening.
      setState("speaking");
      await playTts(CALL_GREETING);
      if (active) beginListening();
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
    if (muted) {
      cancelAnimationFrame(raf);
      if (recorder && recorder.state !== "inactive") {
        recorder.onstop = null;
        try {
          recorder.stop();
        } catch {
          /* ignore */
        }
      }
      setState("listening");
    } else {
      beginListening();
    }
  }

  return { start, end: () => endCall("user"), toggleMute };
}

export function useVoiceCall() {
  const [state, setState] = useState<VoiceState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [remainingMs, setRemainingMs] = useState<number | null>(null);
  const [muted, setMuted] = useState(false);
  const [mounted, setMounted] = useState(false);

  const machineRef = useRef<ReturnType<typeof createCallMachine> | null>(null);
  if (machineRef.current === null && typeof window !== "undefined") {
    machineRef.current = createCallMachine({
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
