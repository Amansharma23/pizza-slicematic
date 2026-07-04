"use client";

import {
  Banknote,
  Bike,
  CheckCircle2,
  Clock,
  ListChecks,
  MapPin,
  Package,
  Phone,
  RefreshCw,
  Smartphone,
  User as UserIcon,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  getDeliveryStats,
  getRecentOrders,
  updateOrderStatus,
  type DeliveryStatsResponse,
  type UserOrder,
} from "@/lib/api";
import { useAuthStore, useRoleUser } from "@/lib/auth-store";
import { cn, formatINR } from "@/lib/utils";

/** Ideas surfaced for later prioritization — not built, just kept visible on
 *  the screen the rider actually uses, per the ask to "keep in profile". */
const SUGGESTED_FEATURES = [
  "Per-rider order assignment (today every rider sees every order)",
  "One-tap call or WhatsApp to the customer",
  "Maps link straight to the delivery address",
  "Sound/push alert when a new order becomes ready for pickup",
  "COD cash-collected reconciliation",
  "Proof of delivery — photo or OTP on handoff",
  "Shift clock-in / clock-out log",
  "Daily earnings & incentive summary",
];

type Tab = "queue" | "profile";

export default function DeliveryOrdersPage() {
  const [tab, setTab] = useState<Tab>("queue");

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex shrink-0 gap-1 border-b border-border bg-surface px-3 pt-2">
        <TabButton active={tab === "queue"} onClick={() => setTab("queue")}>
          <ListChecks className="size-4" /> Queue
        </TabButton>
        <TabButton active={tab === "profile"} onClick={() => setTab("profile")}>
          <UserIcon className="size-4" /> Profile
        </TabButton>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {tab === "queue" ? <QueueTab /> : <ProfileTab />}
      </div>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex cursor-pointer items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-medium transition-colors",
        active
          ? "border-primary text-primary"
          : "border-transparent text-muted-foreground hover:text-foreground"
      )}
    >
      {children}
    </button>
  );
}

/**
 * Delivery work queue — online delivery orders only (type="online" AND a
 * delivery_address is set; pickup orders end at ready_for_pickup, no rider
 * needed) that are ready_for_pickup or already out_for_delivery. One action
 * per card advancing the order (db/orders.py's status state machine).
 */
function QueueTab() {
  const { token } = useRoleUser("delivery");
  const [orders, setOrders] = useState<UserOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyOrder, setBusyOrder] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [ready, outForDelivery] = await Promise.all([
        getRecentOrders({ type: "online", status: "ready_for_pickup" }),
        getRecentOrders({ type: "online", status: "out_for_delivery" }),
      ]);
      if (ready.ok || outForDelivery.ok) {
        const combined = [...(ready.orders ?? []), ...(outForDelivery.orders ?? [])]
          .filter((o) => !!o.delivery_address)
          .sort(
            (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
          );
        setOrders(combined);
      } else {
        const first = ready.errors ?? outForDelivery.errors;
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

      {error && (
        <div
          role="alert"
          className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
        >
          {error}
        </div>
      )}

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

      {!loading && !error && orders.length === 0 && (
        <div className="flex flex-col items-center gap-3 py-16 text-center">
          <Package className="size-9 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            Nothing to deliver right now — orders show up here once the
            kitchen marks them ready.
          </p>
        </div>
      )}

      {orders.map((o) => (
        <OrderCard
          key={o.order_no}
          order={o}
          busy={busyOrder === o.order_no}
          onAdvance={advance}
        />
      ))}
    </div>
  );
}

function OrderCard({
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
  const isOutForDelivery = order.status === "out_for_delivery";

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
        <Badge variant={isOutForDelivery ? "primary" : "default"}>
          {isOutForDelivery ? "Out for delivery" : "Ready for pickup"}
        </Badge>
      </div>

      <div className="flex items-start gap-2 rounded-lg bg-primary/10 p-2.5 text-sm">
        <MapPin className="mt-0.5 size-4 shrink-0 text-primary" />
        <span className="min-w-0 font-medium">{order.delivery_address}</span>
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

      <Button
        className="w-full"
        disabled={busy}
        onClick={() =>
          onAdvance(order, isOutForDelivery ? "delivered" : "out_for_delivery")
        }
      >
        {isOutForDelivery ? "Mark delivered" : "Mark picked up"}
      </Button>
    </Card>
  );
}

function ProfileTab() {
  const { user, token } = useRoleUser("delivery");
  const signOut = useAuthStore((s) => s.signOut);
  const [stats, setStats] = useState<DeliveryStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    getDeliveryStats(token)
      .then((res) => {
        if (!cancelled) setStats(res);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <div className="mx-auto w-full max-w-2xl space-y-4 px-4 py-4">
      <Card className="flex items-center gap-3 p-4">
        <span className="grid size-12 place-items-center rounded-2xl bg-primary text-primary-foreground">
          <Bike className="size-6" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-heading font-bold">{user?.name ?? "Rider"}</p>
          <p className="text-xs text-muted-foreground">{user?.emp_id}</p>
        </div>
        <Button variant="ghost" size="sm" onClick={signOut}>
          Sign out
        </Button>
      </Card>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Card className="flex items-center gap-3 p-4">
          <span className="grid size-10 place-items-center rounded-xl bg-success/15 text-success">
            <CheckCircle2 className="size-5" />
          </span>
          <div>
            <p className="text-2xl font-bold tabular-nums">
              {loading ? "—" : (stats?.delivered_today ?? 0)}
            </p>
            <p className="text-xs text-muted-foreground">Delivered today</p>
          </div>
        </Card>
        <Card className="flex items-center gap-3 p-4">
          <span className="grid size-10 place-items-center rounded-xl bg-primary/15 text-primary">
            <Clock className="size-5" />
          </span>
          <div>
            <p className="text-2xl font-bold tabular-nums">
              {loading || !stats?.orders?.length
                ? "—"
                : `${Math.round(
                    stats.orders.reduce(
                      (sum, o) => sum + (o.pickup_to_delivered_minutes ?? 0),
                      0
                    ) / stats.orders.length
                  )}m`}
            </p>
            <p className="text-xs text-muted-foreground">Avg pickup → delivered</p>
          </div>
        </Card>
      </div>

      {!loading && (stats?.orders?.length ?? 0) > 0 && (
        <Card className="p-4">
          <p className="mb-2 text-sm font-semibold">Today&apos;s deliveries</p>
          <div className="space-y-1.5">
            {stats!.orders!.map((o) => (
              <div
                key={o.order_no}
                className="flex items-center justify-between text-sm"
              >
                <span className="text-muted-foreground">{o.order_no}</span>
                <span className="font-medium tabular-nums">
                  {o.pickup_to_delivered_minutes != null
                    ? `${o.pickup_to_delivered_minutes}m`
                    : "—"}
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card className="p-4">
        <p className="mb-2 text-sm font-semibold">Suggested for later</p>
        <ul className="space-y-1.5 text-sm text-muted-foreground">
          {SUGGESTED_FEATURES.map((f) => (
            <li key={f} className="flex gap-2">
              <span className="text-primary">·</span>
              {f}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
