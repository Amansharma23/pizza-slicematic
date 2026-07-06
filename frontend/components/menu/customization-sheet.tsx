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
  item: MenuItem;
  size_code: string | null;
  crust: MenuItem | null;
  toppings: MenuItem[];
  quantity: number;
}

export function CustomizationSheet({
  item,
  menu,
  open,
  onOpenChange,
  onAdd,
}: {
  item: MenuItem | null;
  menu: Menu;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAdd: (result: CustomizationResult) => void;
}) {
  const [sizeCode, setSizeCode] = useState<string | null>(null);
  const [crustId, setCrustId] = useState<string | null>(null);
  const [toppingIds, setToppingIds] = useState<string[]>([]);
  const [quantity, setQuantity] = useState(1);
  const [line, setLine] = useState<PricedLine | null>(null);
  const [pricing, setPricing] = useState(false);

  const hasSizes = item?.sizes && item.sizes.length > 0;
  const isPizza = item?.category_code?.includes("pizza");

  // Reset the builder each time a new item opens.
  useEffect(() => {
    if (open && item) {
      setSizeCode(hasSizes ? item.sizes[0].size_code : null);
      
      const crusts = menu.categories["crust"];
      setCrustId(isPizza && crusts && crusts.length > 0 ? crusts[0].id : null);
      
      setToppingIds([]);
      setQuantity(1);
      setLine(null);
    }
  }, [open, item?.id, hasSizes, isPizza, menu.categories]);

  // A pizza is ready if it doesn't need sizes OR it has a size selected, and it has a crust selected.
  // Wait, some pizzas might not strictly require crusts? Actually, if it's a pizza, crust is required.
  const ready = Boolean(
    item &&
    (!hasSizes || sizeCode) &&
    (!isPizza || crustId)
  );

  // Live line price — server-computed (never client-side math).
  useEffect(() => {
    if (!item || !ready) {
      setLine(null);
      return;
    }
    let cancelled = false;
    setPricing(true);
    priceCart([
      {
        item_id: item.id,
        item_type: item.item_type || "generic",
        size_code: sizeCode,
        crust_id: crustId,
        topping_ids: toppingIds,
        quantity,
      },
    ])
      .then((res) => {
        if (!cancelled) setLine(res.ok && res.lines ? res.lines[0] : null);
      })
      .catch(() => !cancelled && setLine(null))
      .finally(() => !cancelled && setPricing(false));
    return () => {
      cancelled = true;
    };
  }, [item, sizeCode, crustId, toppingIds, quantity, ready]);

  const allToppings = useMemo(() => {
    return [
      ...(menu.categories["veg_topping"] || []),
      ...(menu.categories["non_veg_topping"] || []),
    ];
  }, [menu.categories]);

  const selectedToppings = useMemo(
    () => allToppings.filter((t) => toppingIds.includes(t.id)),
    [allToppings, toppingIds]
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
    if (!item) return;
    
    let crust = null;
    if (crustId) {
      const allCrusts = menu.categories["crust"] || [];
      crust = allCrusts.find((c) => c.id === crustId) || null;
    }

    onAdd({
      item,
      size_code: sizeCode,
      crust,
      toppings: selectedToppings,
      quantity,
    });
    onOpenChange(false);
  };

  if (!item) return null;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent title={item.name} description={isPizza ? "Build it your way" : "Choose your options"}>
        <div className="slick-scroll flex-1 space-y-6 overflow-y-auto px-5 py-5">
          
          {/* Step 1: Size */}
          {hasSizes && (
            <section>
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
                <StepDot n={1} done={!!sizeCode} />
                Choose Size
              </h3>
              <div className="grid grid-cols-2 gap-2">
                {item.sizes.map((s) => {
                  const sizeName = menu.sizes.find(sz => sz.code === s.size_code)?.name || s.size_code;
                  return (
                    <OptionButton
                      key={s.size_code}
                      selected={sizeCode === s.size_code}
                      onClick={() => setSizeCode(s.size_code)}
                      label={sizeName}
                      sub={formatINR(s.price)}
                    />
                  );
                })}
              </div>
            </section>
          )}

          {/* Step 2: Crust (only for pizzas) */}
          {isPizza && (
            <section>
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
                <StepDot n={hasSizes ? 2 : 1} done={!!crustId} />
                Choose Crust
              </h3>
              <div className="grid grid-cols-2 gap-2">
                {(menu.categories["crust"] || []).map((c) => {
                  const priceInfo = c.sizes?.find(s => s.size_code === sizeCode)?.price || c.price || 0;
                  return (
                    <OptionButton
                      key={c.id}
                      selected={crustId === c.id}
                      onClick={() => setCrustId(c.id)}
                      label={c.name}
                      sub={priceInfo > 0 ? `+${formatINR(priceInfo)}` : "Free"}
                    />
                  );
                })}
              </div>
            </section>
          )}

          {/* Step 3: Toppings */}
          {isPizza && (
            <section>
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
                <StepDot n={hasSizes ? 3 : 2} done={toppingIds.length > 0} />
                Add toppings
                <Badge variant={toppingIds.length ? "primary" : "default"}>
                  {toppingIds.length}/{MAX_TOPPINGS}
                </Badge>
              </h3>
              <div className="flex flex-wrap gap-2">
                {allToppings.map((t) => {
                  const active = toppingIds.includes(t.id);
                  const disabled = !active && toppingIds.length >= MAX_TOPPINGS;
                  const priceInfo = t.sizes?.find(s => s.size_code === sizeCode)?.price || t.price || 0;
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
                        +{formatINR(priceInfo)}
                      </span>
                    </button>
                  );
                })}
              </div>
            </section>
          )}

          {/* Step Last: quantity */}
          <section>
            <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
              <StepDot n={isPizza ? (hasSizes ? 4 : 3) : (hasSizes ? 2 : 1)} done />
              Quantity
            </h3>
            <div className="flex items-center justify-between">
              <QuantityStepper value={quantity} onChange={setQuantity} />
            </div>
          </section>
        </div>

        {/* Footer: live total + add */}
        <div className="shrink-0 border-t border-border bg-surface px-5 pb-[max(1.25rem,env(safe-area-inset-bottom))] pt-4">
          <div className="mb-3 flex items-end justify-between">
            <div>
              <span className="block text-xs text-muted-foreground">
                {ready ? "Line total (incl. GST)" : "Complete your selection"}
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
