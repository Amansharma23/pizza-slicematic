"use client";

import { ArrowDown, ArrowUp, Download, Eye, Filter, RotateCcw, Save, X } from "lucide-react";
import { useCallback, useEffect, useState, useMemo } from "react";

import {
  getAdminOrderDetail,
  getAdminOrders,
  updateAdminOrderStatus,
  type AdminOrderFilters,
  type AdminOrderDetail,
  type AdminOrder,
} from "@/lib/admin-api";
import { formatINR } from "@/lib/utils";
import { AdminConfirmDialog } from "@/components/admin/admin-confirm-dialog";
import {
  AdminEmptyTableRow,
  AdminError,
  AdminLoading,
  AdminPageHeader,
} from "@/components/admin/admin-table-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const statuses = [
  "Created",
  "PaymentPending",
  "Confirmed",
  "Preparing",
  "Ready",
  "Delivered",
  "Completed",
  "Cancelled",
  "RefundRequested",
  "Refunded",
];

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; orders: AdminOrder[] };

export default function AdminOrdersPage() {
  const [state, setState] = useState<State>({ status: "loading" });
  const [saving, setSaving] = useState<string | null>(null);
  const [pendingStatusSave, setPendingStatusSave] = useState<AdminOrder | null>(null);
  const [filters, setFilters] = useState<AdminOrderFilters>({ limit: 100 });
  const [detail, setDetail] = useState<
    | { status: "idle" }
    | { status: "loading"; orderNo?: string }
    | { status: "error"; message: string }
    | { status: "ready"; data: AdminOrderDetail }
  >({ status: "idle" });
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: "asc" | "desc" } | null>(null);

  const requestSort = (key: string) => {
    let direction: "asc" | "desc" = "asc";
    if (sortConfig && sortConfig.key === key && sortConfig.direction === "asc") {
      direction = "desc";
    }
    setSortConfig({ key, direction });
  };

  const sortedOrders = useMemo(() => {
    if (state.status !== "ready") return [];
    let sortableItems = [...state.orders];
    if (sortConfig !== null) {
      sortableItems.sort((a, b) => {
        let aValue = (a as any)[sortConfig.key];
        let bValue = (b as any)[sortConfig.key];
        
        if (aValue === null || aValue === undefined) aValue = "";
        if (bValue === null || bValue === undefined) bValue = "";

        if (aValue < bValue) {
          return sortConfig.direction === "asc" ? -1 : 1;
        }
        if (aValue > bValue) {
          return sortConfig.direction === "asc" ? 1 : -1;
        }
        return 0;
      });
    }
    return sortableItems;
  }, [state, sortConfig]);

  const load = useCallback(async (nextFilters: AdminOrderFilters) => {
    setState({ status: "loading" });
    try {
      const data = await getAdminOrders(nextFilters);
      setState({ status: "ready", orders: data.orders });
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof Error ? error.message : "Orders load failed.",
      });
    }
  }, []);

  function updateFilter<K extends keyof AdminOrderFilters>(
    key: K,
    value: AdminOrderFilters[K]
  ) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  function resetFilters() {
    const next = { limit: 100 };
    setFilters(next);
    void load(next);
  }

  function exportCsv() {
    if (state.status !== "ready") return;
    const rows = state.orders;
    const header = [
      "Order No",
      "Customer",
      "Phone",
      "Status",
      "Payment Mode",
      "Payment Status",
      "Subtotal",
      "Discount",
      "GST",
      "Total",
      "Source",
      "Created At",
    ];
    const csv = [
      header,
      ...rows.map((order) => [
        order.order_no,
        order.customer_name,
        order.customer_phone,
        order.status,
        order.payment_mode,
        order.payment_status,
        order.subtotal,
        order.discount,
        order.gst,
        order.total,
        order.source,
        order.created_at,
      ]),
    ]
      .map((row) => row.map(csvCell).join(","))
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `slicematic-orders-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function save(order: AdminOrder) {
    setSaving(order.id);
    try {
      const res = await updateAdminOrderStatus(
        order.id,
        order.status,
        "Stage 3A admin status update"
      );
      setState((current) =>
        current.status === "ready"
          ? {
              status: "ready",
              orders: current.orders.map((o) =>
                o.id === order.id ? { ...o, status: res.order.status } : o
              ),
            }
          : current
      );
    } finally {
      setSaving(null);
      setPendingStatusSave(null);
    }
  }

  async function openDetail(order: AdminOrder) {
    setDetail({ status: "loading", orderNo: order.order_no });
    try {
      const data = await getAdminOrderDetail(order.id);
      setDetail({ status: "ready", data });
    } catch (error) {
      setDetail({
        status: "error",
        message:
          error instanceof Error ? error.message : "Order detail load failed.",
      });
    }
  }

  useEffect(() => {
    void load({ limit: 100 });
  }, [load]);

  if (state.status === "loading") return <AdminLoading label="Loading orders" />;
  if (state.status === "error") {
    return <AdminError message={state.message} onRetry={() => void load(filters)} />;
  }

  const SortIcon = ({ columnKey }: { columnKey: string }) => {
    if (!sortConfig || sortConfig.key !== columnKey) {
      return <ArrowDown className="ml-1 inline-block h-3 w-3 opacity-20" />;
    }
    return sortConfig.direction === "asc" ? (
      <ArrowUp className="ml-1 inline-block h-3 w-3" />
    ) : (
      <ArrowDown className="ml-1 inline-block h-3 w-3" />
    );
  };

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8">
      <AdminPageHeader
        title="Order Management"
        subtitle="View orders, itemized bills, payment status, and controlled status transitions."
      />
      <section className="rounded-lg border border-border bg-card p-4">
        <div className="grid gap-3 xl:grid-cols-[1.4fr_150px_150px_150px_150px]">
          <Input
            placeholder="Search order no, customer name, or phone"
            value={filters.customer_search ?? ""}
            onChange={(event) => updateFilter("customer_search", event.target.value)}
          />
          <select
            className="h-11 rounded-lg border border-border bg-surface-2 px-3 text-sm"
            value={filters.status_filter ?? ""}
            onChange={(event) => updateFilter("status_filter", event.target.value)}
          >
            <option value="">All statuses</option>
            {statuses.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
          <select
            className="h-11 rounded-lg border border-border bg-surface-2 px-3 text-sm"
            value={filters.payment_status ?? ""}
            onChange={(event) => updateFilter("payment_status", event.target.value)}
          >
            <option value="">All payment status</option>
            <option value="Paid">Paid</option>
            <option value="Pending">Pending</option>
            <option value="Refunded">Refunded</option>
            <option value="Failed">Failed</option>
          </select>
          <select
            className="h-11 rounded-lg border border-border bg-surface-2 px-3 text-sm"
            value={filters.payment_mode ?? ""}
            onChange={(event) => updateFilter("payment_mode", event.target.value)}
          >
            <option value="">All modes</option>
            <option value="Cash">Cash</option>
            <option value="Card">Card</option>
            <option value="UPI">UPI</option>
          </select>
          <select
            className="h-11 rounded-lg border border-border bg-surface-2 px-3 text-sm"
            value={filters.source ?? ""}
            onChange={(event) => updateFilter("source", event.target.value)}
          >
            <option value="">All sources</option>
            <option value="api">Customer Web</option>
            <option value="staff_pos">Staff POS</option>
            <option value="ai">AI Chat</option>
            <option value="voice">Voice</option>
            <option value="app">App</option>
          </select>
        </div>
        <div className="mt-3 grid gap-3 lg:grid-cols-[150px_150px_140px_140px_100px_auto_auto_auto]">
          <Input
            type="date"
            value={filters.date_from ?? ""}
            onChange={(event) => updateFilter("date_from", event.target.value)}
          />
          <Input
            type="date"
            value={filters.date_to ?? ""}
            onChange={(event) => updateFilter("date_to", event.target.value)}
          />
          <Input
            type="number"
            min={0}
            placeholder="Min bill"
            value={filters.total_min ?? ""}
            onChange={(event) =>
              updateFilter(
                "total_min",
                event.target.value ? Number(event.target.value) : undefined
              )
            }
          />
          <Input
            type="number"
            min={0}
            placeholder="Max bill"
            value={filters.total_max ?? ""}
            onChange={(event) =>
              updateFilter(
                "total_max",
                event.target.value ? Number(event.target.value) : undefined
              )
            }
          />
          <Input
            type="number"
            min={1}
            max={500}
            aria-label="Result limit"
            value={filters.limit ?? 100}
            onChange={(event) => updateFilter("limit", Number(event.target.value))}
          />
          <Button variant="secondary" onClick={() => void load(filters)}>
            <Filter />
            Apply
          </Button>
          <Button variant="secondary" onClick={resetFilters}>
            <RotateCcw />
            Reset
          </Button>
          <Button
            variant="secondary"
            disabled={state.status !== "ready" || !state.orders.length}
            onClick={exportCsv}
          >
            <Download />
            CSV
          </Button>
        </div>
      </section>
      <section className="overflow-hidden rounded-lg border border-border bg-card">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1100px] text-left text-sm">
            <thead className="bg-surface-2 text-xs uppercase text-muted-foreground">
              <tr>
                <th className="cursor-pointer px-4 py-3 hover:bg-surface-3 transition-colors" onClick={() => requestSort("order_no")}>Order <SortIcon columnKey="order_no" /></th>
                <th className="cursor-pointer px-4 py-3 hover:bg-surface-3 transition-colors" onClick={() => requestSort("customer_name")}>Customer <SortIcon columnKey="customer_name" /></th>
                <th className="px-4 py-3">Items</th>
                <th className="cursor-pointer px-4 py-3 hover:bg-surface-3 transition-colors" onClick={() => requestSort("payment_mode")}>Payment <SortIcon columnKey="payment_mode" /></th>
                <th className="cursor-pointer px-4 py-3 hover:bg-surface-3 transition-colors" onClick={() => requestSort("total")}>Bill <SortIcon columnKey="total" /></th>
                <th className="cursor-pointer px-4 py-3 hover:bg-surface-3 transition-colors" onClick={() => requestSort("status")}>Status <SortIcon columnKey="status" /></th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {sortedOrders.length ? (
                sortedOrders.map((order) => (
                  <OrderRow
                    key={order.id}
                    order={order}
                    saving={saving === order.id}
                    onChange={(next) =>
                      setState((current) =>
                        current.status === "ready"
                          ? {
                              status: "ready",
                              orders: current.orders.map((o) =>
                                o.id === next.id ? next : o
                              ),
                            }
                          : current
                      )
                    }
                    onSave={setPendingStatusSave}
                    onView={openDetail}
                  />
                ))
              ) : (
                <AdminEmptyTableRow
                  colSpan={7}
                  title="No orders match"
                  description="Adjust filters or reset them to view recent customer, staff POS, AI, voice, or app orders."
                />
              )}
            </tbody>
          </table>
        </div>
      </section>
      <OrderDetailPanel detail={detail} onClose={() => setDetail({ status: "idle" })} />
      <AdminConfirmDialog
        open={Boolean(pendingStatusSave)}
        title="Update order status?"
        description={
          pendingStatusSave
            ? `${pendingStatusSave.order_no} will be changed to ${pendingStatusSave.status}. Preparing orders may deduct mapped inventory.`
            : ""
        }
        confirmLabel="Update status"
        variant="secondary"
        busy={Boolean(pendingStatusSave && saving === pendingStatusSave.id)}
        onCancel={() => setPendingStatusSave(null)}
        onConfirm={() => {
          if (pendingStatusSave) void save(pendingStatusSave);
        }}
      />
    </main>
  );
}

function csvCell(value: string | number) {
  const text = String(value ?? "");
  return `"${text.replace(/"/g, '""')}"`;
}

function OrderRow({
  order,
  saving,
  onChange,
  onSave,
  onView,
}: {
  order: AdminOrder;
  saving: boolean;
  onChange: (order: AdminOrder) => void;
  onSave: (order: AdminOrder) => void;
  onView: (order: AdminOrder) => Promise<void>;
}) {
  return (
    <tr className="border-t border-border align-top">
      <td className="px-4 py-3">
        <p className="font-medium">{order.order_no}</p>
        <p className="text-xs text-muted-foreground">
          {new Date(order.created_at).toLocaleString("en-IN")}
        </p>
      </td>
      <td className="px-4 py-3">
        <p>{order.customer_name}</p>
        <p className="text-xs text-muted-foreground">{order.customer_phone}</p>
      </td>
      <td className="px-4 py-3">
        <div className="max-w-xs space-y-1">
          {(order.items ?? []).map((item, index) => (
            <p key={`${order.id}-${index}`} className="text-xs text-muted-foreground">
              {item.quantity}x {item.pizza} / {item.base}
            </p>
          ))}
        </div>
      </td>
      <td className="px-4 py-3">
        <Badge variant={order.payment_status === "Paid" ? "success" : "default"}>
          {order.payment_status}
        </Badge>
        <p className="mt-1 text-xs text-muted-foreground">{order.payment_mode}</p>
      </td>
      <td className="px-4 py-3">
        <p className="font-semibold">{formatINR(order.total)}</p>
        <p className="text-xs text-muted-foreground">
          GST {formatINR(order.gst)} / Discount {formatINR(order.discount)}
        </p>
      </td>
      <td className="px-4 py-3">
        <select
          className="h-10 rounded-lg border border-border bg-surface-2 px-3 text-sm"
          value={order.status}
          onChange={(event) => onChange({ ...order, status: event.target.value })}
        >
          {statuses.map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
          {!statuses.includes(order.status) ? (
            <option value={order.status}>{order.status}</option>
          ) : null}
        </select>
      </td>
      <td className="px-4 py-3 text-right">
        <div className="flex justify-end gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => void onView(order)}
          >
            <Eye />
            Details
          </Button>
          <Button
            variant="secondary"
            size="sm"
            disabled={saving}
            onClick={() => onSave(order)}
          >
            <Save />
            Save
          </Button>
        </div>
      </td>
    </tr>
  );
}

function OrderDetailPanel({
  detail,
  onClose,
}: {
  detail:
    | { status: "idle" }
    | { status: "loading"; orderNo?: string }
    | { status: "error"; message: string }
    | { status: "ready"; data: AdminOrderDetail };
  onClose: () => void;
}) {
  if (detail.status === "idle") return null;

  return (
    <section className="fixed inset-y-0 right-0 z-40 flex w-full max-w-2xl flex-col border-l border-border bg-background shadow-xl">
      <div className="flex items-start justify-between gap-4 border-b border-border p-4">
        <div>
          <p className="text-xs uppercase text-muted-foreground">Order Detail</p>
          <h2 className="font-heading text-xl font-semibold">
            {detail.status === "ready"
              ? detail.data.order.order_no
              : detail.status === "loading"
                ? detail.orderNo ?? "Loading"
                : "Unavailable"}
          </h2>
        </div>
        <Button size="icon-sm" variant="ghost" aria-label="Close" onClick={onClose}>
          <X />
        </Button>
      </div>
      {detail.status === "loading" ? (
        <p className="p-4 text-sm text-muted-foreground">Loading order detail</p>
      ) : null}
      {detail.status === "error" ? (
        <p className="p-4 text-sm text-destructive">{detail.message}</p>
      ) : null}
      {detail.status === "ready" ? <OrderDetailBody data={detail.data} /> : null}
    </section>
  );
}

function OrderDetailBody({ data }: { data: AdminOrderDetail }) {
  const order = data.order;
  return (
    <div className="slick-scroll flex-1 overflow-y-auto p-4">
      <div className="grid gap-4">
        <section className="rounded-lg border border-border bg-card p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="font-medium">{order.customer_name}</p>
              <p className="text-xs text-muted-foreground">{order.customer_phone}</p>
            </div>
            <div className="flex gap-2">
              <Badge>{order.status}</Badge>
              <Badge variant={order.payment_status === "Paid" ? "success" : "default"}>
                {order.payment_status}
              </Badge>
            </div>
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            {order.source} / {new Date(order.created_at).toLocaleString("en-IN")}
          </p>
        </section>

        <section className="rounded-lg border border-border bg-card">
          <h3 className="border-b border-border p-4 font-heading text-lg font-semibold">
            Itemized Bill
          </h3>
          <div className="divide-y divide-border">
            {(order.items ?? []).map((item, index) => (
              <div key={`${order.id}-${index}`} className="p-4 text-sm">
                <div className="flex justify-between gap-3">
                  <div>
                    <p className="font-medium">
                      {item.quantity}x {item.pizza}
                    </p>
                    <p className="text-muted-foreground">{item.base}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {item.toppings?.length ? item.toppings.join(", ") : "No toppings"}
                    </p>
                  </div>
                  <p className="font-semibold">{formatINR(item.line_total)}</p>
                </div>
              </div>
            ))}
          </div>
          <div className="space-y-2 border-t border-border p-4 text-sm">
            <BillLine label="Subtotal" value={order.subtotal} />
            <BillLine label="Discount" value={order.discount} />
            <BillLine label="GST" value={order.gst} />
            <BillLine label="Total" value={order.total} strong />
          </div>
        </section>

        <Timeline
          title="Status History"
          rows={data.status_history.map((row) => ({
            id: row.id,
            title: `${row.old_status ?? "New"} -> ${row.new_status}`,
            meta: `${new Date(row.changed_at).toLocaleString("en-IN")} / ${
              row.changed_by_name ?? "System"
            }`,
            note: row.reason,
          }))}
        />

        <Timeline
          title="Payments"
          rows={data.payments.map((row) => ({
            id: row.id,
            title: `${row.payment_mode} / ${row.payment_status} / ${formatINR(
              row.amount_paid
            )}`,
            meta: row.paid_at
              ? new Date(row.paid_at).toLocaleString("en-IN")
              : new Date(row.created_at).toLocaleString("en-IN"),
            note: row.transaction_reference,
          }))}
        />

        <Timeline
          title="Refunds"
          rows={data.refunds.map((row) => ({
            id: row.id,
            title: `${row.status} / ${formatINR(row.amount)}`,
            meta: new Date(row.requested_at).toLocaleString("en-IN"),
            note: row.reason,
          }))}
          empty="No refunds for this order"
        />

        <Timeline
          title="Inventory Deductions"
          rows={data.inventory_deductions.map((row) => ({
            id: row.id,
            title: `${row.ingredient_name}: ${row.quantity} ${row.unit}`,
            meta: `${new Date(row.deducted_at).toLocaleString("en-IN")} / ${
              row.deducted_by_name ?? "System"
            }`,
          }))}
          empty="No inventory deducted yet"
        />
      </div>
    </div>
  );
}

function BillLine({
  label,
  value,
  strong,
}: {
  label: string;
  value: number;
  strong?: boolean;
}) {
  return (
    <div className={strong ? "flex justify-between font-semibold" : "flex justify-between"}>
      <span>{label}</span>
      <span>{formatINR(value)}</span>
    </div>
  );
}

function Timeline({
  title,
  rows,
  empty = "Nothing recorded yet",
}: {
  title: string;
  rows: Array<{ id: string; title: string; meta: string; note?: string }>;
  empty?: string;
}) {
  return (
    <section className="rounded-lg border border-border bg-card">
      <h3 className="border-b border-border p-4 font-heading text-lg font-semibold">
        {title}
      </h3>
      <div className="divide-y divide-border">
        {rows.length ? (
          rows.map((row) => (
            <div key={row.id} className="p-4 text-sm">
              <p className="font-medium">{row.title}</p>
              <p className="mt-1 text-xs text-muted-foreground">{row.meta}</p>
              {row.note ? (
                <p className="mt-2 text-xs text-muted-foreground">{row.note}</p>
              ) : null}
            </div>
          ))
        ) : (
          <p className="p-4 text-sm text-muted-foreground">{empty}</p>
        )}
      </div>
    </section>
  );
}
