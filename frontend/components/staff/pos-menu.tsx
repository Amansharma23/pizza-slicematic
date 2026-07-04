"use client";

import { Plus, Search, UtensilsCrossed } from "lucide-react";
import { useMemo, useState } from "react";

import { Input } from "@/components/ui/input";
import type { Menu, MenuItem } from "@/lib/api";
import { formatINR } from "@/lib/utils";

/**
 * POS step 2a — the pizza grid. Kiosk-wide (3–4 tiles per row, big tap
 * targets); tapping a tile opens the customize panel. Staff-surface copy of
 * the customer menu idea — deliberately not imported from components/menu
 * (surfaces stay isolated, per CLAUDE.md).
 */
export function PosMenu({
  menu,
  onSelect,
}: {
  menu: Menu;
  onSelect: (pizza: MenuItem) => void;
}) {
  const [query, setQuery] = useState("");

  const pizzas = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q
      ? menu.pizzas.filter((p) => p.name.toLowerCase().includes(q))
      : menu.pizzas;
  }, [menu.pizzas, query]);

  return (
    <div className="flex h-full flex-col">
      <div className="shrink-0 border-b border-border bg-surface px-6 py-4">
        <div className="flex items-center justify-between gap-4">
          <h2 className="font-heading text-xl font-bold">Menu</h2>
          <div className="flex w-72 items-center gap-2 rounded-lg border border-input bg-surface-2 px-3">
            <Search className="size-4 shrink-0 text-muted-foreground" />
            <label htmlFor="pos-search" className="sr-only">
              Search pizzas
            </label>
            <Input
              id="pos-search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search pizzas…"
              className="h-11 border-0 bg-transparent px-1 shadow-none focus-visible:ring-0"
            />
          </div>
        </div>
      </div>

      <div className="slick-scroll flex-1 overflow-y-auto px-6 py-5">
        {pizzas.length === 0 ? (
          <div className="flex flex-col items-center gap-3 py-16 text-center">
            <UtensilsCrossed className="size-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              No pizzas match &ldquo;{query}&rdquo;.
            </p>
          </div>
        ) : (
          <ul className="grid grid-cols-2 gap-4 lg:grid-cols-3">
            {pizzas.map((pizza) => (
              <li key={pizza.id} className="flex">
                <button
                  type="button"
                  onClick={() => onSelect(pizza)}
                  className="group flex h-full w-full cursor-pointer flex-col rounded-xl border border-border bg-card p-3 text-left transition-all hover:border-primary/60 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <span
                    aria-hidden
                    className="mb-2 grid aspect-[4/3] w-full place-items-center rounded-lg bg-surface-2 text-5xl"
                  >
                    🍕
                  </span>
                  <span className="line-clamp-2 min-h-[2.6rem] text-base font-medium leading-tight text-foreground">
                    {pizza.name}
                  </span>
                  <span className="mt-auto flex items-center justify-between pt-2">
                    <span className="flex flex-col">
                      <span className="text-base font-semibold">
                        {formatINR(pizza.price)}
                      </span>
                      <span className="text-[11px] text-muted-foreground">
                        + base &amp; toppings
                      </span>
                    </span>
                    <span className="grid size-10 shrink-0 place-items-center rounded-full bg-primary text-primary-foreground transition-transform group-hover:scale-105 [&_svg]:size-5">
                      <Plus />
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
