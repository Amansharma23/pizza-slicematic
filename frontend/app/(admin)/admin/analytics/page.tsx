"use client";

import { BarChart3, CalendarDays, CreditCard, Percent, RotateCcw, ShoppingBag } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { getAdminAnalytics, type AdminAnalytics } from "@/lib/admin-api";
import { formatINR } from "@/lib/utils";
import {
  AdminEmptyTableRow,
  AdminError,
  AdminLoading,
  AdminPageHeader,
} from "@/components/admin/admin-table-shell";
import { AdminBarChart, AdminLineChart, AdminPieChart } from "@/components/admin/admin-charts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; analytics: AdminAnalytics };

export default function AdminAnalyticsPage() {
  const [state, setState] = useState<State>({ status: "loading" });
  const [activeTab, setActiveTab] = useState<
    "revenue" | "items" | "customers" | "ai"
  >("revenue");
  const [filters, setFilters] = useState({ date_from: "", date_to: "" });

  const load = useCallback(async () => {
    setState({ status: "loading" });
    try {
      const data = await getAdminAnalytics(filters);
      setState({ status: "ready", analytics: data.analytics });
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof Error ? error.message : "Analytics load failed.",
      });
    }
  }, [filters]);

  useEffect(() => {
    void load();
  }, [load]);

  if (state.status === "loading") return <AdminLoading label="Loading analytics" />;
  if (state.status === "error") {
    return <AdminError message={state.message} onRetry={() => void load()} />;
  }

  const { analytics } = state;

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8">
      <AdminPageHeader
        title="Analytics"
        subtitle="Live revenue, order, item, payment, source, customer, and refund metrics."
      />
      <AnalyticsFilters
        filters={filters}
        onChange={setFilters}
        onApply={() => void load()}
      />
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <Metric label="Orders" value={analytics.totals.total_orders} icon={ShoppingBag} />
        <Metric label="Revenue" value={formatINR(analytics.totals.revenue)} icon={BarChart3} />
        <Metric label="AOV" value={formatINR(analytics.totals.average_order_value)} icon={CreditCard} />
        <Metric label="Refund Rate" value={`${analytics.refund_rate}%`} icon={RotateCcw} />
        <Metric label="Discount Impact" value={`${analytics.discount_impact.discount_to_revenue_percent}%`} icon={Percent} />
      </section>
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric
          label="AI Decisions"
          value={analytics.recommendation_impact.totals.total}
          icon={BarChart3}
        />
        <Metric
          label="AI Acceptance"
          value={`${analytics.recommendation_impact.totals.acceptance_rate}%`}
          icon={Percent}
        />
        <Metric
          label="AI Accepted Value"
          value={formatINR(analytics.recommendation_impact.totals.accepted_estimated_value)}
          icon={CreditCard}
        />
        <Metric
          label="Accepted / Rejected"
          value={`${analytics.recommendation_impact.totals.accepted} / ${analytics.recommendation_impact.totals.rejected}`}
          icon={ShoppingBag}
        />
      </section>

      <section className="rounded-lg border border-border bg-card p-4">
        <div className="flex gap-2 overflow-x-auto">
          <TabButton active={activeTab === "revenue"} onClick={() => setActiveTab("revenue")}>
            Revenue
          </TabButton>
          <TabButton active={activeTab === "items"} onClick={() => setActiveTab("items")}>
            Items
          </TabButton>
          <TabButton active={activeTab === "customers"} onClick={() => setActiveTab("customers")}>
            Customers
          </TabButton>
          <TabButton active={activeTab === "ai"} onClick={() => setActiveTab("ai")}>
            AI Impact
          </TabButton>
        </div>
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        {activeTab === "revenue" ? (
          <>
            <AdminLineChart title="Daily Revenue Trend" rows={analytics.daily_revenue} xKey="date" yKey="revenue" money />
            <AdminBarChart title="Hourly Orders" rows={analytics.hourly_revenue} xKey="hour" yKey="orders" />
            <AdminPieChart title="Payment Mode Revenue Split" rows={analytics.revenue_by_payment_mode} nameKey="payment_mode" valueKey="revenue" money />
            <AdminPieChart title="Order Source Split" rows={analytics.orders_by_source} nameKey="source" valueKey="orders" />
            <SimpleTable
              title="Payment Mode Split"
              rows={analytics.revenue_by_payment_mode}
              columns={[
                ["payment_mode", "Mode"],
                ["orders", "Orders"],
                ["revenue", "Revenue"],
              ]}
            />
            <SimpleTable
              title="Orders By Source"
              rows={analytics.orders_by_source}
              columns={[
                ["source", "Source"],
                ["orders", "Orders"],
                ["revenue", "Revenue"],
              ]}
            />
          </>
        ) : null}
        {activeTab === "items" ? (
          <>
            <AdminBarChart title="Top Items By Revenue" rows={analytics.top_items} xKey="name" yKey="revenue" money />
            <AdminPieChart title="Top Items Quantity Split" rows={analytics.top_items} nameKey="name" valueKey="quantity" />
            <SimpleTable
              title="Top Items"
              rows={analytics.top_items}
              columns={[
                ["name", "Item"],
                ["quantity", "Qty"],
                ["revenue", "Revenue"],
              ]}
            />
          </>
        ) : null}
        {activeTab === "customers" ? (
          <>
            <AdminBarChart title="Repeat Customer Revenue" rows={analytics.repeat_customers} xKey="customer_name" yKey="revenue" money />
            <SimpleTable
              title="Repeat Customers"
              rows={analytics.repeat_customers}
              columns={[
                ["customer_name", "Customer"],
                ["orders", "Orders"],
                ["revenue", "Revenue"],
              ]}
            />
          </>
        ) : null}
        {activeTab === "ai" ? (
          <>
            <AdminBarChart title="AI Accepted Value By Type" rows={analytics.recommendation_impact.by_type} xKey="recommendation_type" yKey="accepted_estimated_value" money />
            <AdminPieChart title="AI Decision Mix" rows={[
              { name: "Accepted", value: analytics.recommendation_impact.totals.accepted },
              { name: "Rejected", value: analytics.recommendation_impact.totals.rejected },
              {
                name: "Presented",
                value: Math.max(
                  0,
                  analytics.recommendation_impact.totals.total -
                    analytics.recommendation_impact.totals.accepted -
                    analytics.recommendation_impact.totals.rejected
                ),
              },
            ]} nameKey="name" valueKey="value" />
            <SimpleTable
              title="AI Recommendation Impact"
              rows={analytics.recommendation_impact.by_type.map((row) => ({
                ...row,
                next_step:
                  row.total > 0 && (row.accepted / row.total) * 100 >= 60
                    ? "Scale accepted recommendations"
                    : "Review rejected patterns before using more",
              }))}
              columns={[
                ["recommendation_type", "Type"],
                ["total", "Total"],
                ["accepted", "Accepted"],
                ["accepted_estimated_value", "Accepted Value"],
                ["next_step", "AI Next Step"],
              ]}
            />
          </>
        ) : null}
      </section>
    </main>
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
      className={
        active
          ? "h-10 shrink-0 rounded-lg bg-primary px-4 text-sm font-medium text-primary-foreground"
          : "h-10 shrink-0 rounded-lg border border-border bg-surface-2 px-4 text-sm font-medium"
      }
      onClick={onClick}
    >
      {children}
    </button>
  );
}

function AnalyticsFilters({
  filters,
  onChange,
  onApply,
}: {
  filters: { date_from: string; date_to: string };
  onChange: (filters: { date_from: string; date_to: string }) => void;
  onApply: () => void;
}) {
  function setQuick(range: "week" | "month" | "quarter" | "year") {
    const today = new Date();
    const start = new Date(today);
    if (range === "week") {
      start.setDate(today.getDate() - 6);
    } else if (range === "month") {
      start.setDate(1);
    } else if (range === "quarter") {
      start.setMonth(today.getMonth() - 3);
      start.setDate(today.getDate() + 1);
    } else {
      start.setMonth(0);
      start.setDate(1);
    }
    onChange({ date_from: toDateInput(start), date_to: toDateInput(today) });
  }

  return (
    <section className="rounded-lg border border-border bg-card p-4">
      <div className="grid gap-3 lg:grid-cols-[160px_160px_auto] lg:items-end">
        <label className="space-y-2">
          <span className="text-sm font-medium">From date</span>
          <Input
            type="date"
            value={filters.date_from}
            onChange={(event) => onChange({ ...filters, date_from: event.target.value })}
          />
        </label>
        <label className="space-y-2">
          <span className="text-sm font-medium">To date</span>
          <Input
            type="date"
            value={filters.date_to}
            onChange={(event) => onChange({ ...filters, date_to: event.target.value })}
          />
        </label>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => setQuick("week")}>
            This Week
          </Button>
          <Button variant="secondary" onClick={() => setQuick("month")}>
            This Month
          </Button>
          <Button variant="secondary" onClick={() => setQuick("quarter")}>
            Last Quarter
          </Button>
          <Button variant="secondary" onClick={() => setQuick("year")}>
            This Year
          </Button>
          <Button onClick={onApply}>
            <CalendarDays />
            Apply
          </Button>
        </div>
      </div>
    </section>
  );
}

function toDateInput(date: Date) {
  return date.toISOString().slice(0, 10);
}

function Metric({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <Card className="rounded-lg">
      <CardContent className="flex items-center justify-between gap-3 p-4">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase text-muted-foreground">{label}</p>
          <p className="mt-1 truncate text-xl font-semibold">{value}</p>
        </div>
        <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-surface-2 text-primary">
          <Icon className="size-5" />
        </span>
      </CardContent>
    </Card>
  );
}

function SimpleTable({
  title,
  rows,
  columns,
}: {
  title: string;
  rows: Array<Record<string, string | number>>;
  columns: Array<[string, string]>;
}) {
  return (
    <section className="overflow-hidden rounded-lg border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border p-4">
        <h2 className="font-heading text-lg font-semibold">{title}</h2>
        <Badge>{rows.length}</Badge>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[520px] text-left text-sm">
          <thead className="bg-surface-2 text-xs uppercase text-muted-foreground">
            <tr>
              {columns.map(([, label]) => (
                <th key={label} className="px-4 py-3">
                  {label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length ? (
              rows.map((row, index) => (
                <tr key={index} className="border-t border-border">
                  {columns.map(([key]) => (
                    <td key={key} className="px-4 py-3">
                      {["revenue", "accepted_estimated_value"].includes(key)
                        ? formatINR(Number(row[key]))
                        : row[key]}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <AdminEmptyTableRow
                colSpan={columns.length}
                title="No analytics rows"
                description="Analytics will populate after local orders, payments, discounts, or refunds exist."
              />
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
