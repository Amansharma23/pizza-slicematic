"use client";

import { Plus } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { MenuItem } from "@/lib/api";
import { cn, formatINR } from "@/lib/utils";

const PIZZA_DESCRIPTIONS: Record<string, string> = {
  "Margherita": "Classic Italian delight with signature tomato sauce, fresh basil, and bubbling mozzarella.",
  "Double Cheese Margherita": "Extra loaded with melted golden mozzarella cheese over a crispy hand-tossed crust.",
  "Peppy Paneer": "Spiced paneer cubes, crisp capsicum, and spicy red paprika, dressed in hot schezwan drizzle.",
  "Mexican Green Wave": "A loaded vegetarian feast of crunchy onions, capsicum, juicy tomatoes, and jalapenos.",
  "Deluxe Veggie": "Overloaded with onions, capsicum, sweet corn, mushrooms, and tender paneer cubes.",
  "Veg Extravaganza": "Black olives, crunchy onions, capsicum, mushrooms, sweet corn, tomatoes, and jalapenos.",
  "Cheese n Tomato": "A sweet and tangy combination of juicy tomatoes and thick layers of premium mozzarella.",
  "Indi Tandoori Paneer": "Tandoori-spiced paneer chunks, crisp coriander, and tangy mint mayo on our signature crust.",
  "Pepper Barbecue Chicken": "Smoky barbecue chicken shreds, caramelized onions, and premium mozzarella cheese.",
  "Chicken Sausage": "Mildly spiced chicken sausages with herb-infused tomato sauce and golden mozzarella.",
  "Golden Corn": "Sweet golden corn kernels layered with bubbling mozzarella and a buttery garlic glaze.",
};

export function MenuItemCard({
  pizza,
  onSelect,
}: {
  pizza: MenuItem;
  onSelect: (pizza: MenuItem) => void;
}) {
  const desc = PIZZA_DESCRIPTIONS[pizza.name] || "Freshly baked pizza with premium toppings, aromatic herbs, and bubbling cheese.";
  const isNonVeg =
    pizza.name.toLowerCase().includes("chicken") ||
    pizza.name.toLowerCase().includes("sausage") ||
    pizza.name.toLowerCase().includes("barbecue");
  const isBestSeller =
    pizza.name.includes("Margherita") ||
    pizza.name.includes("Paneer") ||
    pizza.name.includes("Extravaganza");

  return (
    <button
      type="button"
      onClick={() => onSelect(pizza)}
      className="group flex h-full w-full cursor-pointer flex-col rounded-2xl border border-border bg-card/60 backdrop-blur-md p-4 text-left transition-all hover:border-primary/60 hover:shadow-lg hover:bg-card/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      {/* Visual Header */}
      <div className="relative mb-3.5 flex aspect-[16/10] w-full items-center justify-center overflow-hidden rounded-xl bg-gradient-to-tr from-amber-500/10 via-orange-500/15 to-red-500/10 border border-border/50">
        <span className="text-5xl filter drop-shadow-md select-none transition-transform duration-500 group-hover:scale-115 group-hover:rotate-12">
          🍕
        </span>
        
        {/* Veg/Non-Veg Indicator */}
        <div className="absolute top-2.5 left-2.5 flex items-center justify-center p-0.5 rounded border border-border bg-background/90">
          <span className={cn("size-2 rounded-full", isNonVeg ? "bg-red-600" : "bg-green-600")} />
        </div>

        {/* Best Seller Tag */}
        {isBestSeller && (
          <Badge className="absolute top-2.5 right-2.5 bg-amber-500 hover:bg-amber-600 text-[9px] font-bold text-white uppercase px-1.5 py-0.5 border-none leading-none h-4">
            Bestseller
          </Badge>
        )}
      </div>

      <div className="space-y-1 w-full">
        <h3 className="line-clamp-1 font-heading text-sm font-bold text-foreground group-hover:text-primary transition-colors">
          {pizza.name}
        </h3>
        <p className="line-clamp-2 text-[11px] leading-normal text-muted-foreground min-h-[2rem]">
          {desc}
        </p>
      </div>

      <div className="mt-auto w-full flex items-center justify-between pt-2.5 border-t border-border/40">
        <div className="flex flex-col">
          <span className="text-sm font-bold text-foreground tabular-nums">{formatINR(pizza.price)}</span>
          <span className="text-[9px] text-muted-foreground">
            + base & toppings
          </span>
        </div>
        <span className="grid size-8 shrink-0 place-items-center rounded-full bg-primary hover:bg-primary/95 text-primary-foreground transition-transform group-hover:scale-105 shadow-sm">
          <Plus className="size-4.5" />
        </span>
      </div>
    </button>
  );
}
