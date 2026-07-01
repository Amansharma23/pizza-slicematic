"use client";

export const QUICK_REPLIES = [
  "Show me the menu",
  "Build a veggie pizza",
  "What are today's deals?",
  "I want to order for 5 people",
];

export function QuickReplies({
  onPick,
  disabled,
}: {
  onPick: (text: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {QUICK_REPLIES.map((text) => (
        <button
          key={text}
          type="button"
          disabled={disabled}
          onClick={() => onPick(text)}
          className="cursor-pointer rounded-full border border-border bg-surface-2 px-3.5 py-1.5 text-sm text-foreground transition-colors hover:border-primary hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50"
        >
          {text}
        </button>
      ))}
    </div>
  );
}
