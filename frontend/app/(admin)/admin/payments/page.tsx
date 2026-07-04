"use client";

import { CheckCircle, CreditCard, RotateCcw, XCircle } from "lucide-react";
import { useEffect, useState } from "react";

import {
  decideAdminRefund,
  getAdminOrders,
  getAdminPayments,
  requestAdminRefund,
  type AdminOrder,
  type AdminPayment,
  type AdminRefund,
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

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | {
      status: "ready";
      payments: AdminPayment[];
      refunds: AdminRefund[];
      orders: AdminOrder[];
    };

export default function AdminPaymentsPage() {
  const [state, setState] = useState<State>({ status: "loading" });

  async function load() {
    setState({ status: "loading" });
    try {
      const [payments, orders] = await Promise.all([
        getAdminPayments(),
        getAdminOrders(),
      ]);
      setState({
        status: "ready",
        payments: payments.payments,
        refunds: payments.refunds,
        orders: orders.orders,
      });
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof Error ? error.message : "Payments load failed.",
      });
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (state.status === "loading") return <AdminLoading label="Loading payments" />;
  if (state.status === "error") {
    return <AdminError message={state.message} onRetry={() => void load()} />;
  }

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8">
      <AdminPageHeader
        title="Payments And Refunds"
        subtitle="View payment status and initiate refund requests with deterministic validation."
      />
      <RefundBox orders={state.orders} onCreated={load} />
      <section className="grid gap-5 lg:grid-cols-2">
        <DataTable title="Payments" rows={state.payments} kind="payment" />
        <RefundTable rows={state.refunds} onDecided={load} />
      </section>
    </main>
  );
}

function RefundBox({
  orders,
  onCreated,
}: {
  orders: AdminOrder[];
  onCreated: () => Promise<void>;
}) {
  const paidOrders = orders.filter((order) => order.payment_status === "Paid");
  const [orderId, setOrderId] = useState(paidOrders[0]?.id ?? "");
  const [amount, setAmount] = useState(paidOrders[0]?.amount_paid ?? 0);
  const [reason, setReason] = useState("Customer refund request");
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      await requestAdminRefund(orderId, amount, reason);
      await onCreated();
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="rounded-lg border border-border bg-card p-4">
      <h2 className="font-heading text-lg font-semibold">Initiate Refund</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-[1fr_160px_1fr_auto]">
        <select
          className="h-11 rounded-lg border border-border bg-surface-2 px-3 text-sm"
          value={orderId}
          onChange={(event) => {
            const next = paidOrders.find((order) => order.id === event.target.value);
            setOrderId(event.target.value);
            setAmount(next?.amount_paid ?? 0);
          }}
        >
          {paidOrders.map((order) => (
            <option key={order.id} value={order.id}>
              {order.order_no} - {formatINR(order.amount_paid)}
            </option>
          ))}
        </select>
        <Input
          type="number"
          min={1}
          value={amount}
          onChange={(event) => setAmount(Number(event.target.value))}
        />
        <Input value={reason} onChange={(event) => setReason(event.target.value)} />
        <Button disabled={!orderId || saving} onClick={() => void save()}>
          <RotateCcw />
          Request
        </Button>
      </div>
    </section>
  );
}

function RefundTable({
  rows,
  onDecided,
}: {
  rows: AdminRefund[];
  onDecided: () => Promise<void>;
}) {
  const [saving, setSaving] = useState<string | null>(null);
  const [pendingDecision, setPendingDecision] = useState<{
    refund: AdminRefund;
    status: "Approved" | "Rejected" | "Paid";
  } | null>(null);

  async function decide(refundId: string, status: "Approved" | "Rejected" | "Paid") {
    setSaving(refundId);
    try {
      await decideAdminRefund(
        refundId,
        status,
        `Stage 3B refund ${status.toLowerCase()}`
      );
      await onDecided();
    } finally {
      setSaving(null);
      setPendingDecision(null);
    }
  }

  return (
    <section className="overflow-hidden rounded-lg border border-border bg-card">
      <div className="border-b border-border p-4">
        <h2 className="font-heading text-lg font-semibold">Refund Requests</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="bg-surface-2 text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-4 py-3">Order</th>
              <th className="px-4 py-3">Customer</th>
              <th className="px-4 py-3">Amount</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {rows.length ? (
              rows.map((refund) => (
                <tr key={refund.id} className="border-t border-border">
                  <td className="px-4 py-3 font-medium">{refund.order_no}</td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {refund.customer_name}
                  </td>
                  <td className="px-4 py-3">{formatINR(refund.amount)}</td>
                  <td className="px-4 py-3">
                    <Badge variant={statusVariant("refund", refund)}>
                      {refund.status}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <RefundActions
                      refund={refund}
                      saving={saving === refund.id}
                      onDecide={(status) => setPendingDecision({ refund, status })}
                    />
                  </td>
                </tr>
              ))
            ) : (
              <AdminEmptyTableRow
                colSpan={5}
                title="No refund requests"
                description="Refund requests created from paid orders will appear here for approval, rejection, or payout."
              />
            )}
          </tbody>
        </table>
      </div>
      <AdminConfirmDialog
        open={Boolean(pendingDecision)}
        title="Confirm refund decision?"
        description={
          pendingDecision
            ? `${pendingDecision.refund.order_no} refund will be marked ${pendingDecision.status} for ${formatINR(pendingDecision.refund.amount)}.`
            : ""
        }
        confirmLabel={pendingDecision?.status ?? "Confirm"}
        variant={pendingDecision?.status === "Rejected" ? "destructive" : "secondary"}
        busy={Boolean(pendingDecision && saving === pendingDecision.refund.id)}
        onCancel={() => setPendingDecision(null)}
        onConfirm={() => {
          if (pendingDecision) {
            void decide(pendingDecision.refund.id, pendingDecision.status);
          }
        }}
      />
    </section>
  );
}

function RefundActions({
  refund,
  saving,
  onDecide,
}: {
  refund: AdminRefund;
  saving: boolean;
  onDecide: (status: "Approved" | "Rejected" | "Paid") => void;
}) {
  if (refund.status === "Requested") {
    return (
      <div className="flex justify-end gap-2">
        <Button
          size="sm"
          variant="secondary"
          disabled={saving}
          onClick={() => onDecide("Approved")}
        >
          <CheckCircle />
          Approve
        </Button>
        <Button
          size="sm"
          variant="destructive"
          disabled={saving}
          onClick={() => onDecide("Rejected")}
        >
          <XCircle />
          Reject
        </Button>
      </div>
    );
  }
  if (refund.status === "Approved") {
    return (
      <Button
        size="sm"
        variant="secondary"
        disabled={saving}
        onClick={() => onDecide("Paid")}
      >
        <CreditCard />
        Paid
      </Button>
    );
  }
  return <span className="text-xs text-muted-foreground">Closed</span>;
}

function DataTable({
  title,
  rows,
  kind,
}: {
  title: string;
  rows: AdminPayment[] | AdminRefund[];
  kind: "payment" | "refund";
}) {
  return (
    <section className="overflow-hidden rounded-lg border border-border bg-card">
      <div className="border-b border-border p-4">
        <h2 className="font-heading text-lg font-semibold">{title}</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[560px] text-left text-sm">
          <thead className="bg-surface-2 text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-4 py-3">Order</th>
              <th className="px-4 py-3">Customer</th>
              <th className="px-4 py-3">Amount</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.length ? (
              rows.map((row) => (
                <tr key={row.id} className="border-t border-border">
                  <td className="px-4 py-3 font-medium">{row.order_no}</td>
                  <td className="px-4 py-3 text-muted-foreground">{row.customer_name}</td>
                  <td className="px-4 py-3">
                    {formatINR(kind === "payment" ? (row as AdminPayment).amount_paid : (row as AdminRefund).amount)}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={statusVariant(kind, row)}>{statusText(kind, row)}</Badge>
                  </td>
                </tr>
              ))
            ) : (
              <AdminEmptyTableRow
                colSpan={4}
                title={kind === "payment" ? "No payments recorded" : "No refunds recorded"}
                description={
                  kind === "payment"
                    ? "Paid and pending order payment records will appear here."
                    : "Refund records will appear here after requests are created."
                }
              />
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function statusText(kind: "payment" | "refund", row: AdminPayment | AdminRefund) {
  return kind === "payment"
    ? (row as AdminPayment).payment_status
    : (row as AdminRefund).status;
}

function statusVariant(kind: "payment" | "refund", row: AdminPayment | AdminRefund) {
  const status = statusText(kind, row);
  if (["Paid", "Approved"].includes(status)) return "success";
  if (["Failed", "Rejected"].includes(status)) return "destructive";
  return "default";
}
