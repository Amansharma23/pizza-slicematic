"use client";

import { Search, UtensilsCrossed } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { CartBar } from "@/components/menu/cart-bar";
import {
  CustomizationSheet,
  type CustomizationResult,
} from "@/components/menu/customization-sheet";
import { MenuItemCard } from "@/components/menu/menu-item-card";
import { Input } from "@/components/ui/input";
import type { MenuItem } from "@/lib/api";
import { useMenuStore } from "@/lib/menu-store";

export default function MenuPage() {
  const { menu, status, error, loadMenu, addLine } = useMenuStore();
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<MenuItem | null>(null);
  const [customizeOpen, setCustomizeOpen] = useState(false);

  useEffect(() => {
    void loadMenu();
  }, [loadMenu]);

  const pizzas = useMemo(() => {
    if (!menu) return [];
    const q = query.trim().toLowerCase();
    return q
      ? menu.pizzas.filter((p) => p.name.toLowerCase().includes(q))
      : menu.pizzas;
  }, [menu, query]);

  const openCustomize = (pizza: MenuItem) => {
    setSelected(pizza);
    setCustomizeOpen(true);
  };

  const handleAdd = (result: CustomizationResult) => {
    addLine(result);
  };

  return (
    <div className="flex h-full flex-col">
      {/* Search */}
      <div className="shrink-0 border-b border-border bg-surface px-4 py-3">
        <div className="mx-auto flex w-full max-w-2xl items-center gap-2 rounded-lg border border-input bg-surface-2 px-3">
          <Search className="size-4 shrink-0 text-muted-foreground" />
          <label htmlFor="menu-search" className="sr-only">
            Search pizzas
          </label>
          <Input
            id="menu-search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search pizzas…"
            className="h-11 border-0 bg-transparent px-1 shadow-none focus-visible:ring-0"
          />
        </div>
      </div>

      {/* List */}
      <div className="slick-scroll flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-2xl px-4 py-4">
          {status === "loading" && (
            <ul className="grid grid-cols-2 gap-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <li
                  key={i}
                  className="h-[168px] animate-pulse rounded-xl border border-border bg-surface-2"
                />
              ))}
            </ul>
          )}

          {status === "error" && (
            <div className="flex flex-col items-center gap-3 py-16 text-center">
              <UtensilsCrossed className="size-8 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                {error ?? "Couldn't load the menu."}
              </p>
              <button
                onClick={() => void loadMenu()}
                className="cursor-pointer text-sm font-medium text-primary hover:underline"
              >
                Try again
              </button>
            </div>
          )}

          {status === "ready" && (
            <>
              <h1 className="mb-3 font-heading text-xl font-bold">
                Build your pizza
              </h1>
              {pizzas.length === 0 ? (
                <p className="py-10 text-center text-sm text-muted-foreground">
                  No pizzas match “{query}”.
                </p>
              ) : (
                <ul className="grid grid-cols-2 gap-3 pb-4">
                  {pizzas.map((pizza) => (
                    <li key={pizza.id} className="flex">
                      <MenuItemCard pizza={pizza} onSelect={openCustomize} />
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </div>
      </div>

      <CartBar />

      {menu && (
        <CustomizationSheet
          pizza={selected}
          menu={menu}
          open={customizeOpen}
          onOpenChange={setCustomizeOpen}
          onAdd={handleAdd}
        />
      )}
    </div>
  );
}
