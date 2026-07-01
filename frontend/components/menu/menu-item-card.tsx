"use client";

import { Plus } from "lucide-react";

import type { MenuItem } from "@/lib/api";
import { formatINR } from "@/lib/utils";

/** A pizza tile (2-per-row grid). Tapping it starts the build flow. */
export function MenuItemCard({
  pizza,
  onSelect,
}: {
  pizza: MenuItem;
  onSelect: (pizza: MenuItem) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(pizza)}
      className="group flex h-full w-full cursor-pointer flex-col rounded-xl border border-border bg-card p-2.5 text-left transition-all hover:border-primary/60 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <span
        aria-hidden
        className="mb-2 grid aspect-[4/3] w-full place-items-center rounded-lg bg-surface-2 text-4xl"
      >
        🍕
      </span>
      <span className="line-clamp-2 min-h-[2.4rem] text-sm font-medium leading-tight text-foreground">
        {pizza.name}
      </span>
      <span className="mt-auto flex items-center justify-between pt-2">
        <span className="flex flex-col">
          <span className="text-sm font-semibold">{formatINR(pizza.price)}</span>
          <span className="text-[10px] text-muted-foreground">
            + base &amp; toppings
          </span>
        </span>
        <span className="grid size-8 shrink-0 place-items-center rounded-full bg-primary text-primary-foreground transition-transform group-hover:scale-105 [&_svg]:size-4">
          <Plus />
        </span>
      </span>
    </button>
  );
}
