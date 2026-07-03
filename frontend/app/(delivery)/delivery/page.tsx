"use client";

import {
  Banknote,
  MapPin,
  Package,
  Phone,
  RefreshCw,
  Smartphone,
  Store,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { getRecentOrders, type UserOrder } from "@/lib/api";
import { cn, formatINR } from "@/lib/utils";

/**
 * Delivery work queue — ALL recent orders from every user (interim scope;
 * per-rider assignment + rider status updates land with the authorization
 * step). Newest first, with the delivery address front and center.
 */
export default function DeliveryOrdersPage() {
  const [orders, setOrders] = useState<UserOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const res = await getRecentOrders();
      if (res.ok && res.orders) {
        setOrders(res.orders);
      } else {
        const first = res.errors ? Object.values(res.errors)[0] : null;
        setError(first ?? "Couldn't load orders.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't load orders.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const t = setInterval(() => void load(), 30000); // keep the queue fresh
    return () => clearInterval(t);
  }, [load]);

  return (
    <div className="slick-scroll h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-2xl space-y-3 px-4 py-4">
        <div className="flex items-center justify-between">
          <h1 className="font-heading text-lg font-bold">Orders</h1>
          <button
            type="button"
            onClick={() => void load()}
            aria-label="Refresh orders"
            className="grid size-9 cursor-pointer place-items-center rounded-full text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
          >
            <RefreshCw className="size-4" />
          </button>
        </div>

        {loading && orders.length === 0 && (
          <>
            {Array.from({ length: 3 }).map((_, i) => (
              <div
                key={i}
                className="h-32 animate-pulse rounded-xl border border-border bg-surface-2"
              />
            ))}
          </>
        )}

        {error && (
          <div
            role="alert"
            className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
          >
            {error}
          </div>
        )}

        {!loading && !error && orders.length === 0 && (
          <div className="flex flex-col items-center gap-3 py-16 text-center">
            <Package className="size-9 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              No orders yet — new ones appear here automatically.
            </p>
          </div>
        )}

        {orders.map((o) => (
          <OrderCard key={o.order_no} order={o} />
        ))}
      </div>
    </div>
  );
}

function OrderCard({ order }: { order: UserOrder }) {
  const isDelivery = !!order.delivery_address;
  const placed = new Date(order.created_at);
  const items = order.items ?? [];

  return (
    <Card className="space-y-3 p-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-heading text-sm font-bold">{order.order_no}</p>
          <p className="text-xs text-muted-foreground">
            {Number.isNaN(placed.getTime())
              ? "—"
              : placed.toLocaleString("en-IN", {
                  day: "numeric",
                  month: "short",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
          </p>
        </div>
        <Badge variant={isDelivery ? "primary" : "default"}>
          {isDelivery ? "Delivery" : "Pickup"}
        </Badge>
      </div>

      {/* Where to go — the rider's main need */}
      <div
        className={cn(
          "flex items-start gap-2 rounded-lg p-2.5 text-sm",
          isDelivery ? "bg-primary/10" : "bg-surface-2 text-muted-foreground"
        )}
      >
        {isDelivery ? (
          <>
            <MapPin className="mt-0.5 size-4 shrink-0 text-primary" />
            <span className="min-w-0 font-medium">{order.delivery_address}</span>
          </>
        ) : (
          <>
            <Store className="mt-0.5 size-4 shrink-0" />
            <span>Store pickup — no delivery needed.</span>
          </>
        )}
      </div>

      <div className="space-y-1 text-sm">
        {items.map((it, i) => (
          <p key={i} className="text-muted-foreground">
            <span className="font-medium text-foreground">
              {it.quantity}× {it.pizza}
            </span>{" "}
            · {it.base}
          </p>
        ))}
      </div>

      <div className="flex items-center justify-between border-t border-border pt-2.5 text-sm">
        <span className="flex items-center gap-2 text-muted-foreground">
          <Phone className="size-3.5" />
          {order.customer_name}
          {order.customer_phone ? ` · ${order.customer_phone}` : ""}
        </span>
        <span className="flex items-center gap-1.5 font-semibold tabular-nums">
          {order.payment_mode === "UPI" ? (
            <Smartphone className="size-3.5 text-muted-foreground" />
          ) : (
            <Banknote className="size-3.5 text-muted-foreground" />
          )}
          {formatINR(order.total)}
        </span>
      </div>
    </Card>
  );
}
