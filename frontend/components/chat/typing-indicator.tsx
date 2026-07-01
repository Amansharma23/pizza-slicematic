export function TypingIndicator() {
  return (
    <div
      className="flex items-center gap-1.5 px-1 py-1"
      role="status"
      aria-label="SliceMatic is typing"
    >
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="size-2 rounded-full bg-muted-foreground"
          style={{
            animation: "typing-dot 1.2s infinite ease-in-out",
            animationDelay: `${i * 0.18}s`,
          }}
        />
      ))}
    </div>
  );
}
