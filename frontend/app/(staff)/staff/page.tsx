"use client";

import { CheckCircle2, ClipboardList, RefreshCw, Utensils } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";

import {
  advanceStaffOrder,
  checkoutStaffOrder,
  createStaffInventoryRequest,
  getStaffInventory,
  getStaffOrders,
  type StaffCartLinePayload,
  type StaffIngredient,
  type StaffInventoryRequest,
  type StaffOrder,
} from "@/lib/staff-api";
import { getMenu, type Menu, type MenuItem } from "@/lib/api";
import { formatINR } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | {
      status: "ready";
      orders: StaffOrder[];
      ingredients: StaffIngredient[];
      requests: StaffInventoryRequest[];
      menu: Menu;
    };

export default function StaffHomePage() {
  const [state, setState] = useState<State>({ status: "loading" });
  const [saving, setSaving] = useState<string | null>(null);

  async function load() {
    setState({ status: "loading" });
    try {
      const [orders, inventory, menu] = await Promise.all([
        getStaffOrders(),
        getStaffInventory(),
        getMenu(),
      ]);
      if (menu.error) {
        throw new Error(menu.error);
      }
      setState({
        status: "ready",
        orders: orders.orders,
        ingredients: inventory.inventory.ingredients,
        requests: inventory.inventory.requests,
        menu,
      });
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof Error ? error.message : "Staff queue load failed.",
      });
    }
  }

  async function advance(order: StaffOrder) {
    setSaving(order.id);
    try {
      await advanceStaffOrder(order.id, "Kitchen staff advance");
      await load();
    } finally {
      setSaving(null);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (state.status === "loading") {
    return <StaffFrame label="Loading kitchen queue" onRefresh={load} />;
  }
  if (state.status === "error") {
    return (
      <StaffFrame label={state.message} onRefresh={load}>
        <Button variant="secondary" onClick={() => void load()}>
          <RefreshCw />
          Retry
        </Button>
      </StaffFrame>
    );
  }

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-7xl flex-col gap-5 px-4 py-5 sm:px-6 lg:px-8">
      <header className="flex flex-col justify-between gap-4 border-b border-border pb-4 md:flex-row md:items-center">
        <div>
          <p className="text-xs font-medium uppercase text-muted-foreground">
            SliceMatic Staff
          </p>
          <h1 className="font-heading text-2xl font-bold">Kitchen Queue</h1>
        </div>
        <Button variant="secondary" onClick={() => void load()}>
          <RefreshCw />
          Refresh
        </Button>
      </header>

      <section className="grid gap-5 lg:grid-cols-[1.4fr_0.8fr]">
        <div className="grid gap-3">
          <StaffPosPanel menu={state.menu} onCreated={load} />
          {state.orders.length ? (
            state.orders.map((order) => (
              <OrderTicket
                key={order.id}
                order={order}
                saving={saving === order.id}
                onAdvance={advance}
              />
            ))
          ) : (
            <div className="rounded-lg border border-border bg-card p-8 text-center">
              <Utensils className="mx-auto size-8 text-muted-foreground" />
              <p className="mt-3 font-medium">No active kitchen orders</p>
            </div>
          )}
        </div>
        <aside className="flex flex-col gap-5">
          <StockRequestBox ingredients={state.ingredients} onCreated={load} />
          <RecentRequests requests={state.requests} />
        </aside>
      </section>
    </main>
  );
}

function StaffPosPanel({
  menu,
  onCreated,
}: {
  menu: Menu;
  onCreated: () => Promise<void>;
}) {
  const [name, setName] = useState("Walk In Guest");
  const [phone, setPhone] = useState("9876543210");
  const [paymentMode, setPaymentMode] = useState("Cash");
  const [baseId, setBaseId] = useState(menu.bases[0]?.id ?? "");
  const [pizzaId, setPizzaId] = useState(menu.pizzas[0]?.id ?? "");
  const [toppingIds, setToppingIds] = useState<string[]>(
    menu.toppings[0] ? [menu.toppings[0].id] : []
  );
  const [quantity, setQuantity] = useState(1);
  const [lines, setLines] = useState<StaffCartLinePayload[]>([]);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  function addLine() {
    if (!baseId || !pizzaId || !toppingIds.length) return;
    setLines((current) => [
      ...current,
      {
        base_id: baseId,
        pizza_id: pizzaId,
        topping_ids: toppingIds,
        quantity,
      },
    ]);
  }

  async function checkout() {
    setSaving(true);
    setMessage(null);
    try {
      const res = await checkoutStaffOrder({
        name,
        phone,
        payment_mode: paymentMode,
        lines,
      });
      if (!res.ok || !res.order) {
        const first = res.errors ? Object.values(res.errors)[0] : null;
        setMessage(first ?? "Could not create the staff order.");
        return;
      }
      setLines([]);
      setMessage(`Created ${res.order.order_no}`);
      await onCreated();
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="rounded-lg border border-border bg-card p-4">
      <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
        <div>
          <h2 className="font-heading text-lg font-semibold">Counter POS</h2>
          <p className="text-xs text-muted-foreground">
            Build an in-store order and send it to the kitchen queue.
          </p>
        </div>
        <Badge>{lines.length} lines</Badge>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <Input value={name} onChange={(event) => setName(event.target.value)} />
        <Input value={phone} onChange={(event) => setPhone(event.target.value)} />
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-[1fr_1fr_1fr_90px_auto]">
        <MenuSelect
          value={baseId}
          items={menu.bases}
          onChange={setBaseId}
          label="Base"
        />
        <MenuSelect
          value={pizzaId}
          items={menu.pizzas}
          onChange={setPizzaId}
          label="Pizza"
        />
        <ToppingSelect
          toppings={menu.toppings}
          selected={toppingIds}
          onChange={setToppingIds}
        />
        <Input
          type="number"
          min={1}
          max={10}
          value={quantity}
          onChange={(event) => setQuantity(Number(event.target.value))}
        />
        <Button variant="secondary" onClick={addLine}>
          Add
        </Button>
      </div>
      {lines.length ? (
        <div className="mt-4 divide-y divide-border rounded-lg border border-border">
          {lines.map((line, index) => (
            <div key={`${line.pizza_id}-${index}`} className="p-3 text-sm">
              <div className="flex items-center justify-between gap-3">
                <p className="font-medium">
                  {line.quantity}x {nameFor(menu.pizzas, line.pizza_id)}
                </p>
                <button
                  className="text-xs font-medium text-destructive"
                  onClick={() =>
                    setLines((current) => current.filter((_, i) => i !== index))
                  }
                >
                  Remove
                </button>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                {nameFor(menu.bases, line.base_id)} /{" "}
                {line.topping_ids.map((id) => nameFor(menu.toppings, id)).join(", ")}
              </p>
            </div>
          ))}
        </div>
      ) : null}
      <div className="mt-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <select
          className="h-11 rounded-lg border border-border bg-surface-2 px-3 text-sm"
          value={paymentMode}
          onChange={(event) => setPaymentMode(event.target.value)}
        >
          <option value="Cash">Cash</option>
          <option value="Card">Card</option>
          <option value="UPI">UPI</option>
        </select>
        <div className="flex items-center gap-3">
          {message ? <p className="text-sm text-muted-foreground">{message}</p> : null}
          <Button disabled={!lines.length || saving} onClick={() => void checkout()}>
            Send To Kitchen
          </Button>
        </div>
      </div>
    </section>
  );
}

function MenuSelect({
  value,
  items,
  onChange,
  label,
}: {
  value: string;
  items: MenuItem[];
  onChange: (value: string) => void;
  label: string;
}) {
  return (
    <select
      aria-label={label}
      className="h-11 rounded-lg border border-border bg-surface-2 px-3 text-sm"
      value={value}
      onChange={(event) => onChange(event.target.value)}
    >
      {items.map((item) => (
        <option key={item.id} value={item.id}>
          {item.name} / {formatINR(item.price)}
        </option>
      ))}
    </select>
  );
}

function ToppingSelect({
  toppings,
  selected,
  onChange,
}: {
  toppings: MenuItem[];
  selected: string[];
  onChange: (value: string[]) => void;
}) {
  return (
    <select
      aria-label="Topping"
      className="h-11 rounded-lg border border-border bg-surface-2 px-3 text-sm"
      value={selected[0] ?? ""}
      onChange={(event) => onChange(event.target.value ? [event.target.value] : [])}
    >
      {toppings.map((item) => (
        <option key={item.id} value={item.id}>
          {item.name} / {formatINR(item.price)}
        </option>
      ))}
    </select>
  );
}

function nameFor(items: MenuItem[], id: string) {
  return items.find((item) => item.id === id)?.name ?? id;
}

function StaffFrame({
  label,
  onRefresh,
  children,
}: {
  label: string;
  onRefresh: () => Promise<void>;
  children?: ReactNode;
}) {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-4 px-6 text-center">
      <span className="grid size-16 place-items-center rounded-lg bg-surface-2 text-primary">
        <Utensils className="size-8" />
      </span>
      <p className="text-sm text-muted-foreground">{label}</p>
      {children ?? (
        <Button variant="secondary" onClick={() => void onRefresh()}>
          <RefreshCw />
          Refresh
        </Button>
      )}
    </main>
  );
}

function OrderTicket({
  order,
  saving,
  onAdvance,
}: {
  order: StaffOrder;
  saving: boolean;
  onAdvance: (order: StaffOrder) => Promise<void>;
}) {
  const action = nextAction(order.status);
  return (
    <article className="rounded-lg border border-border bg-card p-4">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-heading text-xl font-semibold">{order.order_no}</h2>
            <Badge variant={statusVariant(order.status)}>{order.status}</Badge>
            <Badge variant={order.payment_status === "Paid" ? "success" : "default"}>
              {order.payment_status}
            </Badge>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {order.customer_name} / {order.customer_phone} /{" "}
            {new Date(order.created_at).toLocaleString("en-IN")}
          </p>
        </div>
        <Button
          variant="secondary"
          disabled={!action || saving}
          onClick={() => void onAdvance(order)}
        >
          <CheckCircle2 />
          {action ?? "Closed"}
        </Button>
      </div>
      <div className="mt-4 grid gap-2">
        {(order.items ?? []).map((item, index) => (
          <div
            key={`${order.id}-${index}`}
            className="rounded-lg border border-border bg-surface-2 p-3"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-medium">
                  {item.quantity}x {item.pizza}
                </p>
                <p className="text-sm text-muted-foreground">{item.base}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {item.toppings?.length ? item.toppings.join(", ") : "No toppings"}
                </p>
              </div>
              <p className="font-semibold">{formatINR(item.line_total)}</p>
            </div>
          </div>
        ))}
      </div>
      <p className="mt-3 text-right font-heading text-lg font-semibold">
        {formatINR(order.total)}
      </p>
    </article>
  );
}

function StockRequestBox({
  ingredients,
  onCreated,
}: {
  ingredients: StaffIngredient[];
  onCreated: () => Promise<void>;
}) {
  const lowStock = useMemo(
    () => ingredients.filter((ingredient) => ingredient.is_low_stock),
    [ingredients]
  );
  const source = lowStock.length ? lowStock : ingredients;
  const [ingredientId, setIngredientId] = useState(source[0]?.id ?? "");
  const [quantity, setQuantity] = useState(1);
  const [reason, setReason] = useState("Kitchen stock request");
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      await createStaffInventoryRequest({
        ingredient_id: ingredientId,
        requested_quantity: quantity,
        reason,
      });
      await onCreated();
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="rounded-lg border border-border bg-card p-4">
      <h2 className="font-heading text-lg font-semibold">Stock Request</h2>
      <div className="mt-4 grid gap-3">
        <select
          className="h-11 rounded-lg border border-border bg-surface-2 px-3 text-sm"
          value={ingredientId}
          onChange={(event) => setIngredientId(event.target.value)}
        >
          {source.map((ingredient) => (
            <option key={ingredient.id} value={ingredient.id}>
              {ingredient.name} ({ingredient.stock_quantity} {ingredient.unit})
            </option>
          ))}
        </select>
        <Input
          type="number"
          min={1}
          value={quantity}
          onChange={(event) => setQuantity(Number(event.target.value))}
        />
        <Input value={reason} onChange={(event) => setReason(event.target.value)} />
        <Button disabled={!ingredientId || saving} onClick={() => void save()}>
          <ClipboardList />
          Request
        </Button>
      </div>
    </section>
  );
}

function RecentRequests({ requests }: { requests: StaffInventoryRequest[] }) {
  return (
    <section className="rounded-lg border border-border bg-card">
      <div className="border-b border-border p-4">
        <h2 className="font-heading text-lg font-semibold">Recent Requests</h2>
      </div>
      <div className="divide-y divide-border">
        {requests.slice(0, 6).map((request) => (
          <div key={request.id} className="p-4 text-sm">
            <div className="flex items-center justify-between gap-3">
              <p className="font-medium">{request.ingredient_name}</p>
              <Badge variant={statusVariant(request.status)}>{request.status}</Badge>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {request.requested_quantity} / {request.reason ?? "No reason"}
            </p>
          </div>
        ))}
        {!requests.length ? (
          <p className="p-4 text-sm text-muted-foreground">No requests yet</p>
        ) : null}
      </div>
    </section>
  );
}

function nextAction(status: string) {
  const labels: Record<string, string> = {
    Created: "Accept",
    PaymentPending: "Confirm",
    Confirmed: "Start",
    Preparing: "Ready",
    Ready: "Deliver",
    received: "Accept",
    confirmed: "Start",
  };
  return labels[status];
}

function statusVariant(status: string) {
  if (["Ready", "Approved", "Paid", "Delivered"].includes(status)) return "success";
  if (["Cancelled", "Rejected", "Refunded"].includes(status)) return "destructive";
  return "default";
}
