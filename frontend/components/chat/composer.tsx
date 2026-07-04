"use client";

import { Phone, SendHorizontal } from "lucide-react";
import { useState, useEffect } from "react";

import { Button } from "@/components/ui/button";
import { useVoiceCall } from "@/lib/use-voice";

import { CallPanel } from "./call-panel";

// Voice is DISABLED for this release: hides the call button/panel only. The
// backend /voice/* routes and use-voice hook stay intact — flip to true to
// re-enable the whole voice UI.
const VOICE_ENABLED = true;

export function Composer({
  onSend,
  disabled,
}: {
  onSend: (text: string) => void;
  disabled?: boolean;
}) {
  const [value, setValue] = useState("");
  const call = useVoiceCall();

  useEffect(() => {
    const handleInsert = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (typeof detail === "string") {
        setValue(detail);
        document.getElementById("chat-input")?.focus();
      }
    };
    window.addEventListener("insert-chat", handleInsert);
    return () => window.removeEventListener("insert-chat", handleInsert);
  }, []);

  const submit = () => {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue("");
  };

  // While a call is active, the composer becomes the call controls; the
  // conversation still appears as bubbles in the thread above.
  if (VOICE_ENABLED && call.isActive) {
    return (
      <CallPanel
        state={call.state}
        muted={call.muted}
        remainingMs={call.remainingMs}
        onToggleMute={call.toggleMute}
        onEnd={call.endCall}
      />
    );
  }

  const notice = !VOICE_ENABLED
    ? null
    : call.state === "ended"
      ? (call.error ?? "Call ended. Start a new call or keep typing.")
      : call.state === "denied" ||
          call.state === "unsupported" ||
          call.state === "unreachable"
        ? (call.error ?? "Voice calls aren't available in this browser.")
        : null;

  return (
    <div className="border-t border-border bg-surface px-3 pb-[max(0.6rem,env(safe-area-inset-bottom))] pt-2">
      {notice && (
        <div className="mb-2 rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-1.5 text-xs text-destructive">
          {notice}
        </div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="flex items-end gap-2"
      >
        {VOICE_ENABLED && call.supported && (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label="Start voice call"
            title="Start voice call"
            onClick={call.startCall}
          >
            <Phone />
          </Button>
        )}
        <div className="flex flex-1 items-center rounded-2xl border border-input bg-surface-2 px-2">
          <label htmlFor="chat-input" className="sr-only">
            Message SliceMatic
          </label>
          <textarea
            id="chat-input"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            rows={1}
            placeholder="Type your order…"
            className="slick-scroll max-h-24 flex-1 resize-none bg-transparent px-2 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
          />
        </div>
        <Button
          type="submit"
          size="icon"
          aria-label="Send message"
          disabled={disabled || !value.trim()}
        >
          <SendHorizontal />
        </Button>
      </form>
    </div>
  );
}
