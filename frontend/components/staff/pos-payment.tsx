"use client";

import {
  ArrowLeft,
  Banknote,
  Check,
  CreditCard,
  Loader2,
  Phone,
  ShoppingBag,
  Smartphone,
  User,
  UtensilsCrossed,
} from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { checkoutCart } from "@/lib/api";
import { toPayload, useStaffPos } from "@/lib/staff-store";
import { cn, formatINR } from "@/lib/utils";

/**
 * POS step 3 — take payment at the counter. Mirrors the customer checkout
 * screen section-for-section (contact, payment method, order summary, sticky
 * total footer, simulated UPI overlay), staffed for in-store: Cash or UPI
 * only, no delivery address, order `type` = store.
 */
const METHODS = [
  {
    id: "cash",
    label: "Cash",
    desc: "Collect cash at the counter",
    mode: "1",
    icon: Banknote,
  },
  {
    id: "card",
    label: "Card",
    desc: "Swipe or tap on the card machine",
    mode: "2",
    icon: CreditCard,
  },
  {
    id: "upi",
    label: "UPI",
    desc: "Customer scans the counter QR — GPay, PhonePe, Paytm",
    mode: "3",
    icon: Smartphone,
  },
] as const;

const ORDER_TYPE_LABEL = { dine_in: "Dine In", takeaway: "Takeaway" } as const;
const ORDER_TYPE_ICON = { dine_in: UtensilsCrossed, takeaway: ShoppingBag } as const;

export function PosPayment() {
  const {
    customerName,
    customerPhone,
    orderType,
    ticket,
    totals,
    reprice,
    setStep,
    setPlaced,
    clearTicket,
  } = useStaffPos();
  const OrderTypeIcon = ORDER_TYPE_ICON[orderType];

  const [methodId, setMethodId] =
    useState<(typeof METHODS)[number]["id"]>("cash");
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Re-price on entry so the totals are always the server's latest numbers
  // (same safeguard as the customer checkout).
  useEffect(() => {
    void reprice();
  }, [reprice]);

  const method = METHODS.find((m) => m.id === methodId)!;
  const canPlace = ticket.length > 0 && !processing;

  const place = async () => {
    if (!canPlace) return;
    setError(null);
    setProcessing(true);

    // Simulated payment step for UPI/card (no real gateway) — same as customer.
    if (method.id === "upi" || method.id === "card") {
      await new Promise((r) => setTimeout(r, 1600));
    }

    try {
      const res = await checkoutCart({
        user_id: "", // walk-in customer — no account
        name: customerName,
        phone: customerPhone,
        payment_mode: method.mode,
        address: "", // in-store order — no delivery
        // Real seating type, not a generic "store" tag — lets the queue
        // filter by Dine In / Takeaway on actual saved orders.
        type: orderType,
        lines: ticket.map(toPayload),
      });
      if (!res.ok || !res.order_no) {
        const first = res.errors ? Object.values(res.errors)[0] : null;
        setError(first ?? "Couldn't place the order. Please try again.");
        setProcessing(false);
        return;
      }
      const placedTotal = res.total ?? totals?.total ?? 0;
      clearTicket();
      setPlaced(res.order_no, placedTotal);
    } catch {
      setError("Can't reach SliceMatic right now. Please try again.");
      setProcessing(false);
    }
  };

  return (
    <div className="relative flex h-full flex-col">
      {/* Panel header */}
      <div className="flex shrink-0 items-center gap-3 border-b border-border bg-surface px-6 py-4">
        <button
          type="button"
          onClick={() => setStep("build")}
          disabled={processing}
          aria-label="Back to the order"
          className="grid size-11 cursor-pointer place-items-center rounded-full text-foreground transition-colors hover:bg-surface-2 disabled:pointer-events-none disabled:opacity-40 [&_svg]:size-5"
        >
          <ArrowLeft />
        </button>
        <h2 className="font-heading text-xl font-bold">Payment</h2>
      </div>

      <div className="slick-scroll flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-xl space-y-6 px-6 py-6">
          {/* Customer — compact contact card, like the customer checkout */}
          <section className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold">Customer</h3>
              {!processing && (
                <button
                  type="button"
                  onClick={() => setStep("details")}
                  className="cursor-pointer text-xs font-medium text-primary hover:underline"
                >
                  Edit
                </button>
              )}
            </div>
            <div className="space-y-2.5 rounded-xl border border-border bg-surface-2 p-3.5">
              <div className="flex items-center gap-3 text-sm">
                <User className="size-4 shrink-0 text-muted-foreground" />
                <span className="font-medium">{customerName}</span>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <Phone className="size-4 shrink-0 text-muted-foreground" />
                <span className="font-medium">{customerPhone}</span>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <OrderTypeIcon className="size-4 shrink-0 text-muted-foreground" />
                <span className="font-medium">{ORDER_TYPE_LABEL[orderType]}</span>
              </div>
            </div>
          </section>

          {/* Payment method */}
          <section className="space-y-3">
            <h3 className="text-sm font-semibold">Payment method</h3>
            <div className="space-y-2">
              {METHODS.map((m) => {
                const Icon = m.icon;
                const active = methodId === m.id;
                return (
                  <button
                    key={m.id}
                    type="button"
                    disabled={processing}
                    onClick={() => setMethodId(m.id)}
                    className={cn(
                      "flex w-full cursor-pointer items-center gap-3 rounded-xl border p-3.5 text-left transition-colors",
                      active
                        ? "border-primary bg-primary/10"
                        : "border-border bg-surface-2 hover:border-primary/50",
                      processing && "pointer-events-none opacity-60"
                    )}
                  >
                    <span
                      className={cn(
                        "grid size-9 shrink-0 place-items-center rounded-lg [&_svg]:size-5",
                        active
                          ? "bg-primary text-primary-foreground"
                          : "bg-card text-muted-foreground"
                      )}
                    >
                      <Icon />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-medium">
                        {m.label}
                      </span>
                      <span className="block text-xs text-muted-foreground">
                        {m.desc}
                      </span>
                    </span>
                    <span
                      className={cn(
                        "grid size-5 shrink-0 place-items-center rounded-full border",
                        active ? "border-primary bg-primary" : "border-border"
                      )}
                    >
                      {active && (
                        <Check className="size-3 text-primary-foreground" />
                      )}
                    </span>
                  </button>
                );
              })}
            </div>
          </section>

          {/* Order summary — same rows as the customer checkout */}
          <section className="space-y-3">
            <h3 className="text-sm font-semibold">Order summary</h3>
            <ul className="space-y-2 rounded-xl border border-border bg-surface-2 p-3.5">
              {ticket.map((l) => (
                <li key={l.id} className="flex justify-between gap-3 text-sm">
                  <span className="min-w-0">
                    <span className="font-medium">
                      {l.quantity}× {l.pizza.name}
                    </span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {l.base.name} · {l.toppings.map((t) => t.name).join(", ")}
                    </span>
                  </span>
                </li>
              ))}
              {totals && totals.discount > 0 && (
                <li className="flex justify-between border-t border-border pt-2 text-sm text-success">
                  <span>Bulk discount</span>
                  <span className="tabular-nums">
                    −{formatINR(totals.discount)}
                  </span>
                </li>
              )}
              <li
                className={cn(
                  "flex justify-between text-sm text-muted-foreground",
                  !(totals && totals.discount > 0) &&
                    "border-t border-border pt-2"
                )}
              >
                <span>GST (18%) included</span>
                <span className="tabular-nums">
                  {totals ? formatINR(totals.gst) : "…"}
                </span>
              </li>
            </ul>
          </section>

          {error && (
            <div
              role="alert"
              className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
            >
              {error}
            </div>
          )}
        </div>
      </div>

      {/* Sticky place-order footer — same as the customer checkout */}
      <div className="shrink-0 border-t border-border bg-surface px-6 py-4">
        <div className="mx-auto flex w-full max-w-xl items-center gap-3">
          <div className="min-w-0">
            <span className="block text-xs text-muted-foreground">
              Total payable
            </span>
            <span className="font-heading text-xl font-bold tabular-nums">
              {totals ? formatINR(totals.total) : "…"}
            </span>
          </div>
          <Button
            size="lg"
            className="h-14 flex-1 text-base"
            disabled={!canPlace}
            onClick={place}
          >
            {processing
              ? "Placing…"
              : method.id === "cash"
                ? "Place order"
                : `Pay ${totals ? formatINR(totals.total) : ""}`}
          </Button>
        </div>
      </div>

      {/* Simulated UPI/card processing overlay — mirrors the customer checkout. */}
      {processing && method.id !== "cash" && (
        <div className="absolute inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-background/90 backdrop-blur-sm">
          <Loader2 className="size-12 animate-spin text-primary" />
          <div className="text-center">
            <p className="font-heading text-xl font-semibold">
              {method.id === "card"
                ? "Processing card payment"
                : "Waiting for UPI payment"}
            </p>
            <p className="text-sm text-muted-foreground">
              {totals ? formatINR(totals.total) : ""} ·{" "}
              {method.id === "card"
                ? "complete on the card machine"
                : "ask the customer to approve"}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
