"use client";

import { Check, Palette } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { useTheme } from "@/components/theme-provider";
import { Button } from "@/components/ui/button";
import { THEMES } from "@/lib/themes";
import { cn } from "@/lib/utils";

/** Compact palette picker — proves the "configurable colors" requirement live. */
export function ThemeSwitcher() {
  const { theme, setTheme } = useTheme();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  return (
    <div className="relative" ref={ref}>
      <Button
        variant="ghost"
        size="icon-sm"
        aria-label="Change color theme"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <Palette />
      </Button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-11 z-50 w-56 animate-bubble-in rounded-xl border border-border bg-card p-1.5 shadow-lg"
        >
          {THEMES.map((t) => (
            <button
              key={t.id}
              role="menuitemradio"
              aria-checked={theme === t.id}
              onClick={() => {
                setTheme(t.id);
                setOpen(false);
              }}
              className={cn(
                "flex w-full cursor-pointer items-center gap-3 rounded-lg px-2.5 py-2 text-left transition-colors hover:bg-surface-2",
                theme === t.id && "bg-surface-2"
              )}
            >
              <span className="flex shrink-0 -space-x-1">
                <span
                  className="size-4 rounded-full border border-black/10"
                  style={{ background: t.swatch.primary }}
                />
                <span
                  className="size-4 rounded-full border border-black/10"
                  style={{ background: t.swatch.accent }}
                />
              </span>
              <span className="flex-1">
                <span className="block text-sm font-medium text-foreground">
                  {t.label}
                </span>
                <span className="block text-xs text-muted-foreground">
                  {t.description}
                </span>
              </span>
              {theme === t.id && (
                <Check className="size-4 shrink-0 text-primary" />
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
