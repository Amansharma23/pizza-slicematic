"use client";

import {
  ArrowLeft,
  Bike,
  Check,
  Loader2,
  MapPin,
  Phone,
  ShoppingBag,
  Smartphone,
  Store,
  User,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { checkoutCart } from "@/lib/api";
import { toPayload, useMenuStore } from "@/lib/menu-store";
import { CURRENT_USER } from "@/lib/user";
import { cn, formatINR } from "@/lib/utils";

const METHODS = [
  {
    id: "cod",
    label: "Cash on Delivery",
    desc: "Pay cash when it arrives",
    mode: "1",
    icon: Bike,
  },
  {
    id: "cash",
    label: "Cash at Store",
    desc: "Pay at the counter on pickup",
    mode: "1",
    icon: Store,
  },
  {
    id: "upi",
    label: "UPI",
    desc: "Pay now — GPay, PhonePe, Paytm",
    mode: "3",
    icon: Smartphone,
  },
] as const;

export default function CheckoutPage() {
  const router = useRouter();
  const { cart, totals, reprice, clearCart } = useMenuStore();

  const [name, setName] = useState(CURRENT_USER.name);
  const [phone, setPhone] = useState(CURRENT_USER.phone);
  const [addressId, setAddressId] = useState(
    CURRENT_USER.addresses.find((a) => a.isDefault)?.id ??
      CURRENT_USER.addresses[0]?.id
  );
  const [methodId, setMethodId] = useState<(typeof METHODS)[number]["id"]>("cod");
  const [editingContact, setEditingContact] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void reprice();
  }, [reprice]);

  const nameOk = /^[A-Za-z ]{2,40}$/.test(name.trim());
  const phoneOk = /^[6-9]\d{9}$/.test(phone.trim());
  // Show inputs when the user opts to edit, or when a prefilled value is invalid.
  const showContactEditor = editingContact || !nameOk || !phoneOk;
  const method = METHODS.find((m) => m.id === methodId)!;
  const address = useMemo(
    () => CURRENT_USER.addresses.find((a) => a.id === addressId),
    [addressId]
  );
  const canPlace = nameOk && phoneOk && cart.length > 0 && !processing;

  const place = async () => {
    if (!canPlace || !address) return;
    setError(null);
    setProcessing(true);

    // Simulated payment step for UPI (no real gateway).
    if (method.id === "upi") {
      await new Promise((r) => setTimeout(r, 1600));
    }

    try {
      const res = await checkoutCart({
        user_id: CURRENT_USER.id,
        name: name.trim(),
        phone: phone.trim(),
        payment_mode: method.mode,
        lines: cart.map(toPayload),
      });
      if (!res.ok || !res.order_no) {
        const first = res.errors ? Object.values(res.errors)[0] : null;
        setError(first ?? "Couldn't place your order. Please try again.");
        setProcessing(false);
        return;
      }
      clearCart();
      // Order is now in the DB (source of truth); the Orders tab loads it.
      router.push(`/orders?placed=${encodeURIComponent(res.order_no)}`);
    } catch {
      setError("Can't reach SliceMatic right now. Please try again.");
      setProcessing(false);
    }
  };

  if (cart.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 px-8 text-center">
        <ShoppingBag className="size-9 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">
          Your order is empty — add a pizza first.
        </p>
        <Button asChild>
          <Link href="/menu">Browse the menu</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="relative flex h-full flex-col">
      {/* Dedicated screen header */}
      <div className="flex h-12 shrink-0 items-center gap-2 border-b border-border px-2">
        <button
          type="button"
          onClick={() => router.back()}
          aria-label="Go back"
          className="grid size-9 cursor-pointer place-items-center rounded-full text-foreground transition-colors hover:bg-surface-2 [&_svg]:size-5"
        >
          <ArrowLeft />
        </button>
        <h1 className="font-heading text-lg font-bold">Checkout</h1>
      </div>

      <div className="slick-scroll flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-2xl space-y-6 px-4 py-5">
          {/* Delivery contact — compact display, edit inline (saves scroll) */}
          <section className="space-y-2">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold">Delivery contact</h2>
              {!showContactEditor && (
                <button
                  type="button"
                  onClick={() => setEditingContact(true)}
                  className="cursor-pointer text-xs font-medium text-primary hover:underline"
                >
                  Edit
                </button>
              )}
            </div>

            {showContactEditor ? (
              <div className="space-y-3 rounded-xl border border-border bg-surface-2 p-3.5">
                <div>
                  <label htmlFor="co-name" className="mb-1 block text-xs text-muted-foreground">
                    Name
                  </label>
                  <Input
                    id="co-name"
                    className="bg-card"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    aria-invalid={!nameOk}
                  />
                  {!nameOk && (
                    <p className="mt-1 text-xs text-destructive">
                      Use letters only, 2–40 characters.
                    </p>
                  )}
                </div>
                <div>
                  <label htmlFor="co-phone" className="mb-1 block text-xs text-muted-foreground">
                    Phone
                  </label>
                  <Input
                    id="co-phone"
                    type="tel"
                    inputMode="numeric"
                    className="bg-card"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    aria-invalid={!phoneOk}
                  />
                  {!phoneOk && (
                    <p className="mt-1 text-xs text-destructive">
                      Enter a 10-digit number starting 6–9.
                    </p>
                  )}
                </div>
                {nameOk && phoneOk && (
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => setEditingContact(false)}
                  >
                    Done
                  </Button>
                )}
              </div>
            ) : (
              <div className="space-y-2.5 rounded-xl border border-border bg-surface-2 p-3.5">
                <div className="flex items-center gap-3 text-sm">
                  <User className="size-4 shrink-0 text-muted-foreground" />
                  <span className="font-medium">{name}</span>
                </div>
                <div className="flex items-center gap-3 text-sm">
                  <Phone className="size-4 shrink-0 text-muted-foreground" />
                  <span className="font-medium">{phone}</span>
                </div>
              </div>
            )}
          </section>

          {/* Address */}
          <section className="space-y-3">
            <h2 className="text-sm font-semibold">Deliver to</h2>
            <div className="space-y-2">
              {CURRENT_USER.addresses.map((a) => (
                <button
                  key={a.id}
                  type="button"
                  onClick={() => setAddressId(a.id)}
                  className={cn(
                    "flex w-full cursor-pointer items-start gap-3 rounded-xl border p-3.5 text-left transition-colors",
                    addressId === a.id
                      ? "border-primary bg-primary/10"
                      : "border-border bg-surface-2 hover:border-primary/50"
                  )}
                >
                  <MapPin className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-medium">{a.label}</span>
                    <span className="block text-sm text-muted-foreground">
                      {a.line}
                    </span>
                  </span>
                  {addressId === a.id && (
                    <Check className="size-4 shrink-0 text-primary" />
                  )}
                </button>
              ))}
            </div>
          </section>

          {/* Payment */}
          <section className="space-y-3">
            <h2 className="text-sm font-semibold">Payment method</h2>
            <div className="space-y-2">
              {METHODS.map((m) => {
                const Icon = m.icon;
                const active = methodId === m.id;
                return (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => setMethodId(m.id)}
                    className={cn(
                      "flex w-full cursor-pointer items-center gap-3 rounded-xl border p-3.5 text-left transition-colors",
                      active
                        ? "border-primary bg-primary/10"
                        : "border-border bg-surface-2 hover:border-primary/50"
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
                      <span className="block text-sm font-medium">{m.label}</span>
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

          {/* Summary */}
          <section className="space-y-3">
            <h2 className="text-sm font-semibold">Order summary</h2>
            <ul className="space-y-2 rounded-xl border border-border bg-surface-2 p-3.5">
              {cart.map((l) => (
                <li key={l.id} className="flex justify-between gap-3 text-sm">
                  <span className="min-w-0">
                    <span className="font-medium">{l.quantity}× {l.pizza.name}</span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {l.base.name} · {l.toppings.map((t) => t.name).join(", ")}
                    </span>
                  </span>
                </li>
              ))}
              <li className="flex justify-between border-t border-border pt-2 text-sm text-muted-foreground">
                <span>GST (18%) included</span>
                <span className="tabular-nums">{totals ? formatINR(totals.gst) : "…"}</span>
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

      {/* Sticky place-order footer */}
      <div className="shrink-0 border-t border-border bg-surface px-4 pb-[max(1rem,env(safe-area-inset-bottom))] pt-3">
        <div className="mx-auto flex w-full max-w-2xl items-center gap-3">
          <div className="min-w-0">
            <span className="block text-xs text-muted-foreground">Total payable</span>
            <span className="font-heading text-xl font-bold tabular-nums">
              {totals ? formatINR(totals.total) : "…"}
            </span>
          </div>
          <Button
            className="flex-1"
            size="lg"
            disabled={!canPlace}
            onClick={place}
          >
            {processing
              ? "Placing…"
              : method.id === "upi"
                ? `Pay ${totals ? formatINR(totals.total) : ""}`
                : "Place order"}
          </Button>
        </div>
      </div>

      {/* Simulated UPI payment overlay */}
      {processing && method.id === "upi" && (
        <div className="absolute inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-background/90 backdrop-blur-sm">
          <Loader2 className="size-10 animate-spin text-primary" />
          <div className="text-center">
            <p className="font-heading text-lg font-semibold">
              Processing UPI payment
            </p>
            <p className="text-sm text-muted-foreground">
              {totals ? formatINR(totals.total) : ""} · do not close this screen
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
