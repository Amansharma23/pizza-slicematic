"use client";

import { ArrowLeft, Check, Minus, Plus } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Menu, MenuItem, PricedLine } from "@/lib/api";
import { priceCart } from "@/lib/api";
import { MAX_TOPPINGS, useStaffPos } from "@/lib/staff-store";
import { cn, formatINR } from "@/lib/utils";

export interface PosCustomizationResult {
  pizza: MenuItem;
  base: MenuItem;
  toppings: MenuItem[];
  quantity: number;
}

/**
 * POS step 2b — build the selected pizza: base → 1–3 toppings → quantity,
 * with the line live-priced by /api/cart/price (never client-side math).
 * Same flow as the customer customization sheet, laid out as a full kiosk
 * panel instead of a bottom sheet.
 */
export function PosCustomize({
  pizza,
  menu,
  onAdd,
  onBack,
}: {
  pizza: MenuItem;
  menu: Menu;
  onAdd: (result: PosCustomizationResult) => void;
  onBack: () => void;
}) {
  const [baseId, setBaseId] = useState<string>("");
  const [toppingIds, setToppingIds] = useState<string[]>([]);
  const [quantity, setQuantity] = useState(1);
  const [line, setLine] = useState<PricedLine | null>(null);
  const [pricing, setPricing] = useState(false);
  // Live bulk-discount rule from /api/config — never a hardcoded 10%/5.
  const discountRate = useStaffPos((s) => s.discountRate);
  const discountThreshold = useStaffPos((s) => s.discountThreshold);
  // Cart-level rule: pizzas already on the ticket count toward the threshold.
  const ticketQty = useStaffPos((s) =>
    s.ticket.reduce((n, l) => n + l.quantity, 0)
  );
  const ratePct = Math.round(discountRate * 100);

  // Reset the builder whenever a different pizza is opened.
  useEffect(() => {
    setBaseId("");
    setToppingIds([]);
    setQuantity(1);
    setLine(null);
  }, [pizza.id]);

  const ready = Boolean(baseId && toppingIds.length >= 1);

  // Live line price — server-computed.
  useEffect(() => {
    if (!ready) {
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
  }, [pizza.id, baseId, toppingIds, quantity, ready]);

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
    if (!base) return;
    onAdd({ pizza, base, toppings: selectedToppings, quantity });
  };

  return (
    <div className="flex h-full flex-col">
      {/* Panel header */}
      <div className="flex shrink-0 items-center gap-3 border-b border-border bg-surface px-6 py-4">
        <button
          type="button"
          onClick={onBack}
          aria-label="Back to menu"
          className="grid size-11 cursor-pointer place-items-center rounded-full text-foreground transition-colors hover:bg-surface-2 [&_svg]:size-5"
        >
          <ArrowLeft />
        </button>
        <div className="min-w-0">
          <h2 className="truncate font-heading text-xl font-bold">
            {pizza.name}
          </h2>
          <p className="text-sm text-muted-foreground">
            {formatINR(pizza.price)} · build it for the customer
          </p>
        </div>
      </div>

      <div className="slick-scroll flex-1 space-y-8 overflow-y-auto px-6 py-6">
        {/* Step 1: base */}
        <section>
          <h3 className="mb-3 flex items-center gap-2 text-base font-semibold">
            <StepDot n={1} done={!!baseId} />
            Choose the base
          </h3>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
            {menu.bases.map((base) => (
              <button
                key={base.id}
                type="button"
                onClick={() => setBaseId(base.id)}
                className={cn(
                  "flex cursor-pointer flex-col items-start rounded-lg border px-4 py-3.5 text-left transition-colors",
                  baseId === base.id
                    ? "border-primary bg-primary/10"
                    : "border-border bg-surface-2 hover:border-primary/50"
                )}
              >
                <span className="text-base font-medium text-foreground">
                  {base.name}
                </span>
                <span className="text-sm text-muted-foreground">
                  {formatINR(base.price)}
                </span>
              </button>
            ))}
          </div>
        </section>

        {/* Step 2: toppings */}
        <section>
          <h3 className="mb-3 flex items-center gap-2 text-base font-semibold">
            <StepDot n={2} done={toppingIds.length > 0} />
            Add toppings
            <Badge variant={toppingIds.length ? "primary" : "default"}>
              {toppingIds.length}/{MAX_TOPPINGS}
            </Badge>
          </h3>
          <div className="flex flex-wrap gap-2.5">
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
                    "flex cursor-pointer items-center gap-1.5 rounded-full border px-4 py-2.5 text-base transition-colors",
                    active
                      ? "border-primary bg-primary/15 text-primary"
                      : "border-border bg-surface-2 text-foreground hover:border-primary/50",
                    disabled && "cursor-not-allowed opacity-40 hover:border-border"
                  )}
                >
                  {active && <Check className="size-4" />}
                  {t.name}
                  <span className="text-sm text-muted-foreground">
                    +{formatINR(t.price)}
                  </span>
                </button>
              );
            })}
          </div>
        </section>

        {/* Step 3: quantity */}
        <section>
          <h3 className="mb-3 flex items-center gap-2 text-base font-semibold">
            <StepDot n={3} done />
            Quantity
          </h3>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <QtyButton
                label="Decrease quantity"
                disabled={quantity <= 1}
                onClick={() => setQuantity(quantity - 1)}
              >
                <Minus />
              </QtyButton>
              <span
                aria-live="polite"
                className="min-w-8 text-center text-xl font-semibold tabular-nums"
              >
                {quantity}
              </span>
              <QtyButton
                label="Increase quantity"
                disabled={quantity >= 10}
                onClick={() => setQuantity(quantity + 1)}
              >
                <Plus />
              </QtyButton>
            </div>
            {ticketQty + quantity >= discountThreshold ? (
              <Badge variant="success">
                {ratePct}% off — order has {discountThreshold}+ pizzas
              </Badge>
            ) : (
              <span className="text-sm text-muted-foreground">
                Order {discountThreshold}+ pizzas in total for {ratePct}% off
              </span>
            )}
          </div>
        </section>
      </div>

      {/* Footer: live total + add — same structure as the customer sheet. */}
      <div className="shrink-0 border-t border-border bg-surface px-6 py-4">
        <div className="mb-3 flex items-end justify-between">
          <div>
            <span className="block text-sm text-muted-foreground">
              {ready ? "Line total (incl. GST)" : "Pick a base & topping"}
            </span>
            <span className="font-heading text-3xl font-bold tabular-nums">
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
          size="lg"
          className="h-14 w-full text-base"
          disabled={!ready || pricing || !line}
          onClick={handleAdd}
        >
          {pricing ? "Pricing…" : "Add to ticket"}
        </Button>
      </div>
    </div>
  );
}

function StepDot({ n, done }: { n: number; done?: boolean }) {
  return (
    <span
      className={cn(
        "grid size-6 place-items-center rounded-full text-xs font-bold",
        done
          ? "bg-primary text-primary-foreground"
          : "bg-surface-2 text-muted-foreground"
      )}
    >
      {done ? <Check className="size-3.5" /> : n}
    </span>
  );
}

function QtyButton({
  label,
  disabled,
  onClick,
  children,
}: {
  label: string;
  disabled: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      disabled={disabled}
      onClick={onClick}
      className="grid size-12 cursor-pointer place-items-center rounded-full border border-border bg-surface-2 text-foreground transition-colors hover:border-primary hover:text-primary disabled:pointer-events-none disabled:opacity-40 [&_svg]:size-5"
    >
      {children}
    </button>
  );
}
