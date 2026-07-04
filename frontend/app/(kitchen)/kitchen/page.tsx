"use client";

import {
  ChefHat,
  Check,
  Clock,
  Filter,
  Package,
  RefreshCw,
  ShoppingBag,
  Smartphone,
  UtensilsCrossed,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  getRecentOrders,
  type OrderChannel,
  updateOrderStatus,
  type UserOrder,
} from "@/lib/api";
import { useRoleUser } from "@/lib/auth-store";
import { cn } from "@/lib/utils";

const TYPE_BADGE: Record<OrderChannel, { label: string; icon: typeof Smartphone }> = {
  online: { label: "Online", icon: Smartphone },
  dine_in: { label: "Dine In", icon: UtensilsCrossed },
  takeaway: { label: "Takeaway", icon: ShoppingBag },
};

type TypeFilter = "all" | OrderChannel;

const TYPE_FILTER_OPTIONS: { id: TypeFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "online", label: "Online" },
  { id: "dine_in", label: "Dine In" },
  { id: "takeaway", label: "Takeaway" },
];

/** order.type may be missing, null, or (for orders predating this field) an
 *  empty string — none of those are a recognized channel, so treat them as
 *  "online" everywhere (badge + filter) for a consistent result. */
function normalizedOrderType(order: UserOrder): OrderChannel {
  return order.type && order.type in TYPE_BADGE ? order.type : "online";
}

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
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all");
  const [filterMenuOpen, setFilterMenuOpen] = useState(false);
  const filterMenuRef = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    if (!filterMenuOpen) return;
    const onClick = (e: MouseEvent) => {
      if (!filterMenuRef.current?.contains(e.target as Node)) {
        setFilterMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [filterMenuOpen]);

  const visibleOrders =
    typeFilter === "all"
      ? orders
      : orders.filter((o) => normalizedOrderType(o) === typeFilter);

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
          <div className="flex items-center gap-1.5">
            <div ref={filterMenuRef} className="relative">
              <button
                type="button"
                onClick={() => setFilterMenuOpen((o) => !o)}
                aria-haspopup="true"
                aria-expanded={filterMenuOpen}
                aria-label={`Filter by order type (${
                  TYPE_FILTER_OPTIONS.find((o) => o.id === typeFilter)?.label ?? "All"
                })`}
                className={cn(
                  "grid size-10 cursor-pointer place-items-center rounded-full transition-colors",
                  typeFilter !== "all"
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-surface-2 hover:text-foreground"
                )}
              >
                <Filter className="size-5" />
              </button>

              {filterMenuOpen && (
                <div
                  role="menu"
                  aria-label="Filter by order type"
                  className="absolute top-full right-0 z-20 mt-2 w-40 overflow-hidden rounded-lg border border-border bg-card shadow-lg"
                >
                  {TYPE_FILTER_OPTIONS.map((opt) => {
                    const active = typeFilter === opt.id;
                    return (
                      <button
                        key={opt.id}
                        type="button"
                        role="menuitemradio"
                        aria-checked={active}
                        onClick={() => {
                          setTypeFilter(opt.id);
                          setFilterMenuOpen(false);
                        }}
                        className="flex h-10 w-full cursor-pointer items-center justify-between px-3 text-sm font-medium text-foreground transition-colors hover:bg-surface-2"
                      >
                        {opt.label}
                        <span
                          className={cn(
                            "grid size-4 shrink-0 place-items-center rounded border",
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
              )}
            </div>

            <button
              type="button"
              onClick={() => void load()}
              aria-label="Refresh orders"
              className="grid size-10 cursor-pointer place-items-center rounded-full text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
            >
              <RefreshCw className="size-5" />
            </button>
          </div>
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

        {!loading && !error && visibleOrders.length === 0 && (
          <div className="flex flex-col items-center gap-3 py-20 text-center">
            <Package className="size-10 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              {typeFilter === "all"
                ? "No tickets right now — new orders appear here automatically."
                : "No tickets match this filter."}
            </p>
          </div>
        )}

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {visibleOrders.map((o) => (
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
  const typeBadge = TYPE_BADGE[normalizedOrderType(order)];
  const TypeIcon = typeBadge.icon;

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
        <div className="flex shrink-0 items-center gap-1.5">
          <Badge variant={isPreparing ? "primary" : "default"}>
            {isPreparing ? "Preparing" : "New"}
          </Badge>
          <Badge variant="default">
            <TypeIcon className="size-3" />
            {typeBadge.label}
          </Badge>
        </div>
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
