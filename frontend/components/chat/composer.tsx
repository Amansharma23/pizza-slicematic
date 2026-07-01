"use client";

import { SendHorizontal } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";

import { MicButton } from "./mic-button";

export function Composer({
  onSend,
  disabled,
}: {
  onSend: (text: string) => void;
  disabled?: boolean;
}) {
  const [value, setValue] = useState("");

  const submit = () => {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue("");
  };

  return (
    <div className="border-t border-border bg-surface px-3 pb-[max(0.6rem,env(safe-area-inset-bottom))] pt-2">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="flex items-end gap-2"
      >
        <MicButton />
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
