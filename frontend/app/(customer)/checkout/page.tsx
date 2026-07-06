"use client";

import {
  ArrowLeft,
  Bike,
  Check,
  CreditCard,
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
import { useAuthStore } from "@/lib/auth-store";
import { toPayload, useMenuStore } from "@/lib/menu-store";
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
  {
    id: "card",
    label: "Credit / Debit Card",
    desc: "Visa, Mastercard, RuPay",
    mode: "2",
    icon: CreditCard,
  },
] as const;

export default function CheckoutPage() {
  const router = useRouter();
  const { cart, totals, reprice, clearCart } = useMenuStore();
  const user = useAuthStore((s) => s.user);
  const addresses = useMemo(() => user?.address ?? [], [user]);

  const [name, setName] = useState(user?.name ?? "");
  const [phone, setPhone] = useState(user?.phone ?? "");
  const [addressId, setAddressId] = useState(
    addresses.find((a) => a.isDefault)?.id ?? addresses[0]?.id
  );
  const [methodId, setMethodId] = useState<(typeof METHODS)[number]["id"]>("cod");
  const [editingContact, setEditingContact] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cardNumber, setCardNumber] = useState("");
  const [cardExpiry, setCardExpiry] = useState("");
  const [cardCvv, setCardCvv] = useState("");

  useEffect(() => {
    void reprice();
  }, [reprice]);

  const nameOk = /^[A-Za-z ]{2,40}$/.test(name.trim());
  const phoneOk = /^[6-9]\d{9}$/.test(phone.trim());
  // Show inputs when the user opts to edit, or when a prefilled value is invalid.
  const showContactEditor = editingContact || !nameOk || !phoneOk;
  const method = METHODS.find((m) => m.id === methodId)!;
  const address = useMemo(
    () => addresses.find((a) => a.id === addressId),
    [addresses, addressId]
  );
  // "Cash at Store" is pickup — no address needed. Every other method
  // (COD/UPI/Card) is delivery and requires a saved address.
  const needsAddress = method.id !== "cash";
  const cardOk =
    method.id !== "card" ||
    (/^\d{16}$/.test(cardNumber.replace(/\s/g, "")) &&
      /^\d{2}\/\d{2}$/.test(cardExpiry) &&
      /^\d{3,4}$/.test(cardCvv));
  const canPlace =
    nameOk &&
    phoneOk &&
    cardOk &&
    cart.length > 0 &&
    !processing &&
    (!needsAddress || !!address);

  const place = async () => {
    if (!canPlace) return;
    setError(null);
    setProcessing(true);

    // Simulated payment step for UPI/Card (no real gateway).
    if (method.id === "upi" || method.id === "card") {
      await new Promise((r) => setTimeout(r, 1600));
    }

    try {
      const res = await checkoutCart({
        user_id: user?.id ?? "",
        name: name.trim(),
        phone: phone.trim(),
        payment_mode: method.mode,
        address: needsAddress && address ? `${address.label}: ${address.line}` : "",
        type: needsAddress ? "online" : "takeaway",
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
            <h2 className="text-sm font-semibold">
              {needsAddress ? "Deliver to" : "Pickup"}
            </h2>
            {!needsAddress ? (
              <div className="rounded-xl border border-border bg-surface-2 p-3.5 text-sm text-muted-foreground">
                <span className="font-medium text-foreground">
                  SliceMatic, New Ashok Nagar
                </span>{" "}
                — pay at the counter and collect your order.
              </div>
            ) : addresses.length === 0 ? (
              <div
                role="alert"
                className="space-y-2 rounded-xl border border-destructive/40 bg-destructive/10 p-3.5"
              >
                <p className="text-sm text-destructive">
                  No delivery address saved — add one to your profile before
                  placing a delivery order.
                </p>
                <Button asChild size="sm" variant="secondary">
                  <Link href="/profile">Add an address</Link>
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                {addresses.map((a) => (
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
            )}
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

            {methodId === "card" && (
              <div className="space-y-3 rounded-xl border border-border bg-surface-2 p-3.5">
                <div>
                  <label
                    htmlFor="co-card-number"
                    className="mb-1 block text-xs text-muted-foreground"
                  >
                    Card number
                  </label>
                  <Input
                    id="co-card-number"
                    className="bg-card"
                    inputMode="numeric"
                    placeholder="1234 5678 9012 3456"
                    maxLength={16}
                    value={cardNumber}
                    onChange={(e) => setCardNumber(e.target.value.replace(/\D/g, ""))}
                  />
                </div>
                <div className="flex gap-3">
                  <div className="flex-1">
                    <label
                      htmlFor="co-card-expiry"
                      className="mb-1 block text-xs text-muted-foreground"
                    >
                      MM/YY
                    </label>
                    <Input
                      id="co-card-expiry"
                      className="bg-card"
                      placeholder="MM/YY"
                      maxLength={5}
                      value={cardExpiry}
                      onChange={(e) => {
                        const digits = e.target.value.replace(/\D/g, "").slice(0, 4);
                        setCardExpiry(
                          digits.length > 2 ? `${digits.slice(0, 2)}/${digits.slice(2)}` : digits
                        );
                      }}
                    />
                  </div>
                  <div className="flex-1">
                    <label
                      htmlFor="co-card-cvv"
                      className="mb-1 block text-xs text-muted-foreground"
                    >
                      CVV
                    </label>
                    <Input
                      id="co-card-cvv"
                      className="bg-card"
                      type="password"
                      inputMode="numeric"
                      placeholder="123"
                      maxLength={4}
                      value={cardCvv}
                      onChange={(e) => setCardCvv(e.target.value.replace(/\D/g, ""))}
                    />
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  Simulated payment — no real card is charged.
                </p>
              </div>
            )}
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
              : method.id === "upi" || method.id === "card"
                ? `Pay ${totals ? formatINR(totals.total) : ""}`
                : "Place order"}
          </Button>
        </div>
      </div>

      {/* Simulated UPI/Card payment overlay */}
      {processing && (method.id === "upi" || method.id === "card") && (
        <div className="absolute inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-background/90 backdrop-blur-sm">
          <Loader2 className="size-10 animate-spin text-primary" />
          <div className="text-center">
            <p className="font-heading text-lg font-semibold">
              {method.id === "upi" ? "Processing UPI payment" : "Processing card payment"}
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
