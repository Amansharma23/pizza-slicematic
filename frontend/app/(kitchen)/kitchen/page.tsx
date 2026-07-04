"use client";

import { ChefHat, Clock, Package, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { getRecentOrders, updateOrderStatus, type UserOrder } from "@/lib/api";
import { useRoleUser } from "@/lib/auth-store";

/**
 * Kitchen ticket queue: every order not yet ready (no type filter — food gets
 * prepared regardless of channel), with one action per card advancing it
 * through received -> preparing -> ready_for_pickup (db/orders.py's status
 * state machine; delivery picks up from ready_for_pickup onward).
 */
export default function KitchenHomePage() {
  const { token } = useRoleUser("kitchen_staff");
  const [orders, setOrders] = useState<UserOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyOrder, setBusyOrder] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [received, preparing] = await Promise.all([
        getRecentOrders({ status: "received" }),
        getRecentOrders({ status: "preparing" }),
      ]);
      const combined = [...(received.orders ?? []), ...(preparing.orders ?? [])];
      if (received.ok || preparing.ok) {
        combined.sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );
        setOrders(combined);
      } else {
        const first = received.errors ?? preparing.errors;
        setError(first ? Object.values(first)[0] : "Couldn't load orders.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't load orders.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const t = setInterval(() => void load(), 15000);
    return () => clearInterval(t);
  }, [load]);

  const advance = async (order: UserOrder, nextStatus: string) => {
    if (!token || busyOrder) return;
    setBusyOrder(order.order_no);
    try {
      const res = await updateOrderStatus(order.order_no, nextStatus, token);
      if (res.ok) {
        await load();
      } else {
        const first = res.errors ? Object.values(res.errors)[0] : null;
        setError(first ?? "Couldn't update that order.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't update that order.");
    } finally {
      setBusyOrder(null);
    }
  };

  return (
    <div className="slick-scroll h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-4 px-6 py-6">
        <div className="flex items-center justify-between">
          <h1 className="flex items-center gap-2 font-heading text-xl font-bold">
            <ChefHat className="size-6 text-primary" />
            Kitchen Queue
          </h1>
          <button
            type="button"
            onClick={() => void load()}
            aria-label="Refresh orders"
            className="grid size-10 cursor-pointer place-items-center rounded-full text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
          >
            <RefreshCw className="size-5" />
          </button>
        </div>

        {error && (
          <div
            role="alert"
            className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
          >
            {error}
          </div>
        )}

        {loading && orders.length === 0 && (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="h-40 animate-pulse rounded-xl border border-border bg-surface-2"
              />
            ))}
          </div>
        )}

        {!loading && !error && orders.length === 0 && (
          <div className="flex flex-col items-center gap-3 py-20 text-center">
            <Package className="size-10 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              No tickets right now — new orders appear here automatically.
            </p>
          </div>
        )}

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {orders.map((o) => (
            <TicketCard
              key={o.order_no}
              order={o}
              busy={busyOrder === o.order_no}
              onAdvance={advance}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function TicketCard({
  order,
  busy,
  onAdvance,
}: {
  order: UserOrder;
  busy: boolean;
  onAdvance: (order: UserOrder, nextStatus: string) => void;
}) {
  const placed = new Date(order.created_at);
  const items = order.items ?? [];
  const isPreparing = order.status === "preparing";

  return (
    <Card className="space-y-3 p-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-heading text-sm font-bold">{order.order_no}</p>
          <p className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="size-3" />
            {Number.isNaN(placed.getTime())
              ? "—"
              : placed.toLocaleString("en-IN", {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
          </p>
        </div>
        <Badge variant={isPreparing ? "primary" : "default"}>
          {isPreparing ? "Preparing" : "New"}
        </Badge>
      </div>

      <div className="space-y-1 text-sm">
        {items.map((it, i) => (
          <p key={i} className="text-muted-foreground">
            <span className="font-medium text-foreground">
              {it.quantity}× {it.pizza}
            </span>{" "}
            · {it.base}
            {it.toppings.length > 0 ? ` · ${it.toppings.join(", ")}` : ""}
          </p>
        ))}
      </div>

      <Button
        className="w-full"
        disabled={busy}
        onClick={() =>
          onAdvance(order, isPreparing ? "ready_for_pickup" : "preparing")
        }
      >
        {isPreparing ? "Mark ready for pickup" : "Start preparing"}
      </Button>
    </Card>
  );
}
