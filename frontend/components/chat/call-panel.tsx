"use client";

import { Loader2, Mic, MicOff, PhoneOff, Volume2 } from "lucide-react";

import type { VoiceState } from "@/lib/use-voice";
import { cn } from "@/lib/utils";

function fmt(ms: number) {
  const s = Math.ceil(ms / 1000);
  return `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, "0")}`;
}

/** In-call controls (replaces the composer while a voice call is active). The
 *  conversation itself streams into the chat thread above as bubbles. */
export function CallPanel({
  state,
  muted,
  remainingMs,
  onToggleMute,
  onEnd,
}: {
  state: VoiceState;
  muted: boolean;
  remainingMs: number | null;
  onToggleMute: () => void;
  onEnd: () => void;
}) {
  const listening = state === "listening" && !muted;
  const label =
    state === "connecting"
      ? "Connecting…"
      : muted
        ? "Muted — tap the mic to talk"
        : state === "thinking"
          ? "Thinking…"
          : state === "speaking"
            ? "Speaking…"
            : "Listening…";

  const OrbIcon =
    state === "thinking"
      ? Loader2
      : state === "speaking"
        ? Volume2
        : muted
          ? MicOff
          : Mic;

  return (
    <div className="flex flex-col items-center gap-3 border-t border-border bg-surface px-4 pb-[max(1rem,env(safe-area-inset-bottom))] pt-4">
      {/* Animated orb */}
      <div className="relative grid place-items-center">
        {(listening || state === "speaking") && (
          <span className="absolute inline-flex size-20 animate-ping rounded-full bg-primary/25" />
        )}
        <span
          className={cn(
            "relative grid size-16 place-items-center rounded-full bg-primary text-primary-foreground shadow-lg [&_svg]:size-6",
            state === "speaking" && "animate-pulse"
          )}
        >
          <OrbIcon className={cn(state === "thinking" && "animate-spin")} />
        </span>
      </div>

      <div className="text-center">
        <p className="text-sm font-medium text-foreground">{label}</p>
        {remainingMs != null && (
          <p className="text-xs text-muted-foreground tabular-nums">
            {fmt(remainingMs)} left
          </p>
        )}
      </div>

      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={onToggleMute}
          aria-label={muted ? "Unmute" : "Mute"}
          className={cn(
            "grid size-12 cursor-pointer place-items-center rounded-full border transition-colors [&_svg]:size-5",
            muted
              ? "border-transparent bg-surface-2 text-muted-foreground"
              : "border-border text-foreground hover:bg-surface-2"
          )}
        >
          {muted ? <MicOff /> : <Mic />}
        </button>
        <button
          type="button"
          onClick={onEnd}
          aria-label="End call"
          className="grid size-14 cursor-pointer place-items-center rounded-full bg-destructive text-destructive-foreground shadow-md transition-transform hover:scale-105 [&_svg]:size-6"
        >
          <PhoneOff />
        </button>
      </div>
    </div>
  );
}
