"use client";

import { Mic } from "lucide-react";

import { Button } from "@/components/ui/button";

/**
 * Voice input trigger. Voice is an input modality into the SAME chat pipeline
 * as typed text (transcribe → feed as a user turn), not a separate mode. The
 * MediaRecorder wiring lands in the voice milestone; this is the placeholder
 * seam so the composer layout is final.
 */
export function MicButton() {
  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      disabled
      aria-label="Voice input (coming soon)"
      title="Voice input — coming soon"
    >
      <Mic />
    </Button>
  );
}
