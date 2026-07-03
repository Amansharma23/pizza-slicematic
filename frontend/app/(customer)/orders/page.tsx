"use client";

import {
  Bike,
  Check,
  ChefHat,
  ClipboardList,
  PackageCheck,
  PartyPopper,
  Receipt,
} from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { UserOrder } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { ORDER_STEPS, orderStatus, useOrdersStore } from "@/lib/orders-store";
import { cn, formatINR } from "@/lib/utils";

const STEP_ICONS = [Check, ChefHat, Bike, PackageCheck];

export default function OrdersPage() {
  return (
    <Suspense fallback={null}>
      <OrdersContent />
    </Suspense>
  );
}

function OrdersContent() {
  const { orders, loading, error, load } = useOrdersStore();
  const phone = useAuthStore((s) => s.user?.phone);
  const placed = useSearchParams().get("placed");
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    // Per-user filter by the signed-in account's phone (chat/voice + checkout
    // orders all carry it); swapping to user_id is part of the authz step.
    if (phone) void load(phone);
  }, [load, phone]);

  // Tick so the simulated status advances live while the tab is open.
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 10000);
    return () => clearInterval(t);
  }, []);

  if (loading && orders.length === 0) {
    return (
      <div className="slick-scroll h-full overflow-y-auto">
        <div className="mx-auto w-full max-w-2xl space-y-4 px-4 py-5">
          {Array.from({ length: 2 }).map((_, i) => (
            <div
              key={i}
              className="h-40 animate-pulse rounded-xl border border-border bg-surface-2"
            />
          ))}
        </div>
      </div>
    );
  }

  if (orders.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 px-8 text-center">
        <span className="grid size-16 place-items-center rounded-2xl bg-surface-2 text-primary">
          <ClipboardList className="size-8" />
        </span>
        <div className="space-y-1">
          <h2 className="font-heading text-xl font-semibold">No orders yet</h2>
          <p className="max-w-xs text-sm text-muted-foreground">
            {error ?? "Your placed orders and live tracking show up here."}
          </p>
        </div>
        <Button asChild>
          <Link href="/menu">Start an order</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="slick-scroll h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-2xl space-y-4 px-4 py-5">
        {placed && orders.some((o) => o.order_no === placed) && (
          <div className="flex items-center gap-3 rounded-xl border border-success/40 bg-success/10 px-4 py-3 text-success">
            <PartyPopper className="size-5 shrink-0" />
            <p className="text-sm font-medium">
              Order placed! We&apos;re on it — track it below.
            </p>
          </div>
        )}

        <h1 className="font-heading text-xl font-bold">Your orders</h1>

        {orders.map((order) => (
          <OrderCard
            key={order.order_no}
            order={order}
            now={now}
            highlight={order.order_no === placed}
          />
        ))}
      </div>
    </div>
  );
}

function OrderCard({
  order,
  now,
  highlight,
}: {
  order: UserOrder;
  now: number;
  highlight?: boolean;
}) {
  const placedMs = Date.parse(order.created_at);
  const { index, step } = orderStatus(placedMs, now);
  const placedTime = Number.isNaN(placedMs)
    ? ""
    : new Date(placedMs).toLocaleString([], {
        hour: "2-digit",
        minute: "2-digit",
        day: "2-digit",
        month: "short",
      });
  const items = order.items ?? [];

  return (
    <Card className={cn("overflow-hidden p-0", highlight && "border-primary/60")}>
      <div className="flex items-start justify-between gap-3 border-b border-border p-4">
        <div className="min-w-0">
          <p className="flex items-center gap-2 font-medium">
            <Receipt className="size-4 text-muted-foreground" />
            {order.order_no}
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {placedTime} · {order.payment_mode}
          </p>
        </div>
        <Badge variant={index === 3 ? "success" : "primary"}>{step}</Badge>
      </div>

      {/* Status stepper */}
      <div className="flex items-center px-4 py-4">
        {ORDER_STEPS.map((label, i) => {
          const Icon = STEP_ICONS[i];
          const done = i <= index;
          return (
            <div key={label} className="flex flex-1 items-center last:flex-none">
              <div className="flex flex-col items-center gap-1">
                <span
                  className={cn(
                    "grid size-8 place-items-center rounded-full border-2 transition-colors [&_svg]:size-4",
                    done
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-border bg-surface-2 text-muted-foreground"
                  )}
                >
                  <Icon />
                </span>
                <span
                  className={cn(
                    "w-14 text-center text-[10px] leading-tight",
                    done ? "text-foreground" : "text-muted-foreground"
                  )}
                >
                  {label}
                </span>
              </div>
              {i < ORDER_STEPS.length - 1 && (
                <span
                  className={cn(
                    "-mt-4 h-0.5 flex-1 rounded",
                    i < index ? "bg-primary" : "bg-border"
                  )}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Items + total */}
      <div className="space-y-1 border-t border-border p-4">
        {items.map((item, i) => (
          <div key={i} className="flex justify-between gap-3 text-sm">
            <span className="min-w-0 truncate text-muted-foreground">
              {item.quantity}× {item.pizza}
              <span className="text-xs"> · {item.base}</span>
            </span>
            <span className="shrink-0 tabular-nums text-muted-foreground">
              {formatINR(item.line_total)}
            </span>
          </div>
        ))}
        <div className="flex justify-between border-t border-border pt-2 text-sm font-semibold">
          <span>Total</span>
          <span className="tabular-nums">{formatINR(order.total)}</span>
        </div>
      </div>
    </Card>
  );
}
