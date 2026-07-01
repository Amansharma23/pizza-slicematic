"use client";

import { Check } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import type { Menu, MenuItem, PricedLine } from "@/lib/api";
import { priceCart } from "@/lib/api";
import { MAX_TOPPINGS } from "@/lib/menu-store";
import { cn, formatINR } from "@/lib/utils";

import { QuantityStepper } from "./quantity-stepper";

export interface CustomizationResult {
  pizza: MenuItem;
  base: MenuItem;
  toppings: MenuItem[];
  quantity: number;
}

export function CustomizationSheet({
  pizza,
  menu,
  open,
  onOpenChange,
  onAdd,
}: {
  pizza: MenuItem | null;
  menu: Menu;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAdd: (result: CustomizationResult) => void;
}) {
  const [baseId, setBaseId] = useState<string>("");
  const [toppingIds, setToppingIds] = useState<string[]>([]);
  const [quantity, setQuantity] = useState(1);
  const [line, setLine] = useState<PricedLine | null>(null);
  const [pricing, setPricing] = useState(false);

  // Reset the builder each time a new pizza opens.
  useEffect(() => {
    if (open) {
      setBaseId("");
      setToppingIds([]);
      setQuantity(1);
      setLine(null);
    }
  }, [open, pizza?.id]);

  const ready = Boolean(pizza && baseId && toppingIds.length >= 1);

  // Live line price — server-computed (never client-side math).
  useEffect(() => {
    if (!pizza || !ready) {
      setLine(null);
      return;
    }
    let cancelled = false;
    setPricing(true);
    priceCart([
      { base_id: baseId, pizza_id: pizza.id, topping_ids: toppingIds, quantity },
    ])
      .then((res) => {
        if (!cancelled) setLine(res.ok && res.lines ? res.lines[0] : null);
      })
      .catch(() => !cancelled && setLine(null))
      .finally(() => !cancelled && setPricing(false));
    return () => {
      cancelled = true;
    };
  }, [pizza, baseId, toppingIds, quantity, ready]);

  const selectedToppings = useMemo(
    () => menu.toppings.filter((t) => toppingIds.includes(t.id)),
    [menu.toppings, toppingIds]
  );

  const toggleTopping = (id: string) => {
    setToppingIds((prev) =>
      prev.includes(id)
        ? prev.filter((t) => t !== id)
        : prev.length >= MAX_TOPPINGS
          ? prev
          : [...prev, id]
    );
  };

  const handleAdd = () => {
    const base = menu.bases.find((b) => b.id === baseId);
    if (!pizza || !base) return;
    onAdd({ pizza, base, toppings: selectedToppings, quantity });
    onOpenChange(false);
  };

  if (!pizza) return null;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent title={pizza.name} description="Build it your way">
        <div className="slick-scroll flex-1 space-y-6 overflow-y-auto px-5 py-5">
          {/* Step 1: base */}
          <section>
            <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
              <StepDot n={1} done={!!baseId} />
              Choose your base
            </h3>
            <div className="grid grid-cols-2 gap-2">
              {menu.bases.map((base) => (
                <OptionButton
                  key={base.id}
                  selected={baseId === base.id}
                  onClick={() => setBaseId(base.id)}
                  label={base.name}
                  sub={formatINR(base.price)}
                />
              ))}
            </div>
          </section>

          {/* Step 2: toppings */}
          <section>
            <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
              <StepDot n={2} done={toppingIds.length > 0} />
              Add toppings
              <Badge variant={toppingIds.length ? "primary" : "default"}>
                {toppingIds.length}/{MAX_TOPPINGS}
              </Badge>
            </h3>
            <div className="flex flex-wrap gap-2">
              {menu.toppings.map((t) => {
                const active = toppingIds.includes(t.id);
                const disabled = !active && toppingIds.length >= MAX_TOPPINGS;
                return (
                  <button
                    key={t.id}
                    type="button"
                    disabled={disabled}
                    onClick={() => toggleTopping(t.id)}
                    className={cn(
                      "flex cursor-pointer items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm transition-colors",
                      active
                        ? "border-primary bg-primary/15 text-primary"
                        : "border-border bg-surface-2 text-foreground hover:border-primary/50",
                      disabled && "cursor-not-allowed opacity-40 hover:border-border"
                    )}
                  >
                    {active && <Check className="size-3.5" />}
                    {t.name}
                    <span className="text-xs text-muted-foreground">
                      +{formatINR(t.price)}
                    </span>
                  </button>
                );
              })}
            </div>
          </section>

          {/* Step 3: quantity */}
          <section>
            <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
              <StepDot n={3} done />
              Quantity
            </h3>
            <div className="flex items-center justify-between">
              <QuantityStepper value={quantity} onChange={setQuantity} />
              {quantity >= 5 ? (
                <Badge variant="success">10% bulk discount applied</Badge>
              ) : (
                <span className="text-xs text-muted-foreground">
                  Order 5+ for 10% off
                </span>
              )}
            </div>
          </section>
        </div>

        {/* Footer: live total + add */}
        <div className="shrink-0 border-t border-border bg-surface px-5 pb-[max(1.25rem,env(safe-area-inset-bottom))] pt-4">
          <div className="mb-3 flex items-end justify-between">
            <div>
              <span className="block text-xs text-muted-foreground">
                {ready ? "Line total (incl. GST)" : "Pick a base & topping"}
              </span>
              <span className="font-heading text-2xl font-bold tabular-nums">
                {line ? formatINR(line.total) : "—"}
              </span>
            </div>
            {line && line.discount > 0 && (
              <span className="text-sm text-success">
                saved {formatINR(line.discount)}
              </span>
            )}
          </div>
          <Button
            className="w-full"
            size="lg"
            disabled={!ready || pricing || !line}
            onClick={handleAdd}
          >
            {pricing ? "Pricing…" : "Add to order"}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function StepDot({ n, done }: { n: number; done?: boolean }) {
  return (
    <span
      className={cn(
        "grid size-5 place-items-center rounded-full text-xs font-bold",
        done
          ? "bg-primary text-primary-foreground"
          : "bg-surface-2 text-muted-foreground"
      )}
    >
      {done ? <Check className="size-3" /> : n}
    </span>
  );
}

function OptionButton({
  selected,
  onClick,
  label,
  sub,
}: {
  selected: boolean;
  onClick: () => void;
  label: string;
  sub: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex cursor-pointer flex-col items-start rounded-lg border px-3 py-2.5 text-left transition-colors",
        selected
          ? "border-primary bg-primary/10"
          : "border-border bg-surface-2 hover:border-primary/50"
      )}
    >
      <span className="text-sm font-medium text-foreground">{label}</span>
      <span className="text-xs text-muted-foreground">{sub}</span>
    </button>
  );
}
