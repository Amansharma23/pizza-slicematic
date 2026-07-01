import type { ChatMessage } from "@/lib/store";
import { cn } from "@/lib/utils";

import { TypingIndicator } from "./typing-indicator";

export function ChatBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "flex w-full animate-bubble-in",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <div
        className={cn(
          "max-w-[82%] rounded-2xl px-3.5 py-2 text-sm leading-snug shadow-sm",
          isUser
            ? "rounded-br-md bg-bubble-user text-bubble-user-foreground"
            : "rounded-bl-md border border-border bg-bubble-ai text-card-foreground",
          message.blocked && "border-destructive/40 bg-destructive/10"
        )}
      >
        {message.pending ? (
          <TypingIndicator />
        ) : (
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        )}
      </div>
    </div>
  );
}
