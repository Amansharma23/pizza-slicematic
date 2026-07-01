"use client";

import { useEffect, useRef } from "react";

import { useChatStore } from "@/lib/store";

import { ChatBubble } from "./chat-bubble";
import { Composer } from "./composer";
import { QuickReplies } from "./quick-replies";

export function ChatThread() {
  const { messages, isSending, error, init, send } = useChatStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    init();
  }, [init]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Show starter chips only before the customer has said anything.
  const showQuickReplies = !messages.some((m) => m.role === "user");

  return (
    <div className="flex h-full flex-col">
      <div className="slick-scroll flex-1 overflow-y-auto px-4 py-3">
        <div className="mx-auto flex w-full max-w-2xl flex-col gap-2">
          {messages.map((m) => (
            <ChatBubble key={m.id} message={m} />
          ))}

          {showQuickReplies && (
            <div className="mt-2 pl-1">
              <QuickReplies onPick={send} disabled={isSending} />
            </div>
          )}

          {error && (
            <div
              role="alert"
              className="self-start rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
            >
              {error}
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      <div className="mx-auto w-full max-w-2xl">
        <Composer onSend={send} disabled={isSending} />
      </div>
    </div>
  );
}
