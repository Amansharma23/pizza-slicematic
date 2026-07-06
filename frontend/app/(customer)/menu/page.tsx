"use client";

import { Flame, Leaf, Search, UtensilsCrossed } from "lucide-react";
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
import { cn } from "@/lib/utils";

type MenuTab = "all" | "veg" | "non_veg" | "bestseller";

export default function MenuPage() {
  const { menu, status, error, loadMenu, addLine } = useMenuStore();
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<MenuItem | null>(null);
  const [customizeOpen, setCustomizeOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<MenuTab>("all");

  useEffect(() => {
    void loadMenu();
  }, [loadMenu]);

  const pizzas = useMemo(() => {
    if (!menu) return [];

    let filtered = menu.pizzas;
    const q = query.trim().toLowerCase();
    if (q) {
      filtered = filtered.filter((p) => p.name.toLowerCase().includes(q));
    }

    if (activeTab === "veg") {
      filtered = filtered.filter((p) => {
        const name = p.name.toLowerCase();
        return !name.includes("chicken") && !name.includes("sausage") && !name.includes("barbecue");
      });
    } else if (activeTab === "non_veg") {
      filtered = filtered.filter((p) => {
        const name = p.name.toLowerCase();
        return name.includes("chicken") || name.includes("sausage") || name.includes("barbecue");
      });
    } else if (activeTab === "bestseller") {
      filtered = filtered.filter((p) => {
        return (
          p.name.includes("Margherita") ||
          p.name.includes("Paneer") ||
          p.name.includes("Extravaganza")
        );
      });
    }

    return filtered;
  }, [menu, query, activeTab]);

  const openCustomize = (pizza: MenuItem) => {
    setSelected(pizza);
    setCustomizeOpen(true);
  };

  const handleAdd = (result: CustomizationResult) => {
    addLine(result);
  };

  return (
    <div className="flex h-full flex-col bg-background">
      {/* Search & Categories */}
      <div className="shrink-0 border-b border-border bg-card/60 backdrop-blur-md px-4 py-4 space-y-4">
        {/* Search */}
        <div className="mx-auto flex w-full max-w-2xl items-center gap-2 rounded-2xl border border-input bg-surface-2/40 px-3 shadow-inner focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary transition-all">
          <Search className="size-4 shrink-0 text-muted-foreground" />
          <label htmlFor="menu-search" className="sr-only">
            Search pizzas
          </label>
          <Input
            id="menu-search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search our gourmet pizzas..."
            className="h-11 border-0 bg-transparent px-1 shadow-none focus-visible:ring-0 text-sm font-medium"
          />
        </div>

        {/* Category Selector Tabs */}
        <div className="mx-auto flex w-full max-w-2xl items-center gap-2 overflow-x-auto pb-1 justify-center scrollbar-none">
          <TabButton active={activeTab === "all"} onClick={() => setActiveTab("all")}>
            🍕 All
          </TabButton>
          <TabButton active={activeTab === "veg"} onClick={() => setActiveTab("veg")}>
            <Leaf className="size-3.5 text-green-600 dark:text-green-400" /> Veg
          </TabButton>
          <TabButton active={activeTab === "non_veg"} onClick={() => setActiveTab("non_veg")}>
            <Flame className="size-3.5 text-red-500" /> Non-Veg
          </TabButton>
          <TabButton active={activeTab === "bestseller"} onClick={() => setActiveTab("bestseller")}>
            ✨ Bestsellers
          </TabButton>
        </div>
      </div>

      {/* List */}
      <div className="slick-scroll flex-1 overflow-y-auto bg-surface-1/5">
        <div className="mx-auto w-full max-w-2xl px-4 py-6">
          {status === "loading" && (
            <ul className="grid grid-cols-2 gap-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <li
                  key={i}
                  className="h-[210px] animate-pulse rounded-2xl border border-border bg-surface-2"
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
              <h1 className="mb-4 font-heading text-lg font-bold text-foreground px-1">
                {activeTab === "all" && "Craving something special?"}
                {activeTab === "veg" && "Fresh Garden Vegetarian"}
                {activeTab === "non_veg" && "Fiery Protein Carnivore"}
                {activeTab === "bestseller" && "Gourmet Best Sellers"}
              </h1>
              {pizzas.length === 0 ? (
                <p className="py-16 text-center text-sm text-muted-foreground">
                  No pizzas found matching your filter.
                </p>
              ) : (
                <ul className="grid grid-cols-2 gap-4 pb-4">
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

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex h-8 cursor-pointer items-center gap-1.5 rounded-full border px-4 text-xs font-semibold transition-all shadow-sm shrink-0",
        active
          ? "border-primary bg-primary text-primary-foreground"
          : "border-border bg-background text-muted-foreground hover:border-primary/40 hover:text-foreground"
      )}
    >
      {children}
    </button>
  );
}
