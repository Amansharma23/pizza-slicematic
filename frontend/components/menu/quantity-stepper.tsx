"use client";

import { Minus, Plus } from "lucide-react";

import { cn } from "@/lib/utils";

export function QuantityStepper({
  value,
  onChange,
  min = 1,
  max = 10,
  size = "md",
}: {
  value: number;
  onChange: (next: number) => void;
  min?: number;
  max?: number;
  size?: "sm" | "md";
}) {
  const btn =
    "grid place-items-center rounded-full border border-border bg-surface-2 text-foreground transition-colors hover:border-primary hover:text-primary disabled:pointer-events-none disabled:opacity-40 cursor-pointer";
  const dim = size === "sm" ? "size-7 [&_svg]:size-3.5" : "size-9 [&_svg]:size-4";

  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        aria-label="Decrease quantity"
        className={cn(btn, dim)}
        disabled={value <= min}
        onClick={() => onChange(value - 1)}
      >
        <Minus />
      </button>
      <span
        aria-live="polite"
        className={cn(
          "min-w-6 text-center font-semibold tabular-nums",
          size === "sm" ? "text-sm" : "text-base"
        )}
      >
        {value}
      </span>
      <button
        type="button"
        aria-label="Increase quantity"
        className={cn(btn, dim)}
        disabled={value >= max}
        onClick={() => onChange(value + 1)}
      >
        <Plus />
      </button>
    </div>
  );
}
