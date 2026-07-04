"use client";

import {
  AlertTriangle,
  Brain,
  CalendarDays,
  Clock3 as ClockIcon,
  Calculator,
  MessageSquareText,
  Package,
  RefreshCw,
  TicketPercent,
  TrendingUp,
  Users,
} from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";

import {
  createAdminForecast,
  getAdminAiBusinessIntelligence,
  getAdminAiInsights,
  getAdminAiInsightLogs,
  recordAdminRecommendationEvent,
  simulateAdminRevenueScenario,
  type AdminAiBusinessIntelligence,
  type AdminAiInsight,
  type AdminAiInsightLog,
  type AdminForecast,
  type AdminRevenueScenario,
} from "@/lib/admin-api";
import { formatINR } from "@/lib/utils";
import {
  AdminEmptyState,
  AdminEmptyTableRow,
  AdminError,
  AdminLoading,
  AdminPageHeader,
} from "@/components/admin/admin-table-shell";
import { AdminBarChart, AdminLineChart, AdminPieChart } from "@/components/admin/admin-charts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | {
      status: "ready";
      provider: string;
      fallbackUsed: boolean;
      providerError?: string;
      insights: AdminAiInsight[];
      logs: AdminAiInsightLog[];
      forecast: AdminForecast | null;
      ai: AdminAiBusinessIntelligence;
    };

type ScenarioDraft = {
  menu_price_adjustment_percent: number;
  ingredient_price_increase_percent: number;
  rent_increase_amount: number;
  other_fixed_cost_increase_amount: number;
  discount_change_percent: number;
};

type AiTab =
  | "overview"
  | "suggestions"
  | "forecast"
  | "operations"
  | "customers"
  | "simulator"
  | "logs";

export default function AdminAiInsightsPage() {
  const [state, setState] = useState<State>({ status: "loading" });
  const [forecasting, setForecasting] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [decisionSaving, setDecisionSaving] = useState<string | null>(null);
  const [logFilters, setLogFilters] = useState({ provider: "", insight_type: "", limit: 50 });
  const [scenario, setScenario] = useState<AdminRevenueScenario | null>(null);
  const [activeTab, setActiveTab] = useState<AiTab>("overview");
  const [scenarioDraft, setScenarioDraft] = useState({
    menu_price_adjustment_percent: 5,
    ingredient_price_increase_percent: 8,
    rent_increase_amount: 0,
    other_fixed_cost_increase_amount: 0,
    discount_change_percent: 0,
  });

  async function load() {
    setState({ status: "loading" });
    try {
      const [data, intelligence] = await Promise.all([
        getAdminAiInsights(),
        getAdminAiBusinessIntelligence(7),
      ]);
      setState({
        status: "ready",
        provider: data.provider,
        fallbackUsed: data.fallback_used,
        providerError: data.provider_error,
        insights: data.insights,
        logs: data.logs,
        forecast: intelligence.ai.demand_forecast,
        ai: intelligence.ai,
      });
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof Error ? error.message : "AI insights load failed.",
      });
    }
  }

  async function forecast() {
    setForecasting(true);
    try {
      const data = await createAdminForecast(7);
      setState((current) =>
        current.status === "ready"
          ? { ...current, forecast: data.forecast }
          : current
      );
    } finally {
      setForecasting(false);
    }
  }

  async function simulate() {
    setSimulating(true);
    try {
      const data = await simulateAdminRevenueScenario(scenarioDraft);
      setScenario(data.scenario);
    } finally {
      setSimulating(false);
    }
  }

  async function refreshLogs() {
    const data = await getAdminAiInsightLogs(logFilters);
    setState((current) =>
      current.status === "ready" ? { ...current, logs: data.logs } : current
    );
  }

  async function decideRecommendation(
    payload: Parameters<typeof recordAdminRecommendationEvent>[0]
  ) {
    setDecisionSaving(`${payload.recommendation_type}:${payload.recommendation_key}:${payload.status}`);
    try {
      await recordAdminRecommendationEvent(payload);
      const intelligence = await getAdminAiBusinessIntelligence(7);
      setState((current) =>
        current.status === "ready"
          ? { ...current, ai: intelligence.ai, forecast: intelligence.ai.demand_forecast }
          : current
      );
    } finally {
      setDecisionSaving(null);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (state.status === "loading") return <AdminLoading label="Loading AI insights" />;
  if (state.status === "error") {
    return <AdminError message={state.message} onRetry={() => void load()} />;
  }

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8">
      <AdminPageHeader
        title="AI Insights"
        subtitle="Demand, rush, inventory, revenue, staff, coupon, churn, and upsell intelligence from local metrics."
      />

      <section className="rounded-lg border border-border bg-card p-4">
        <div className="flex gap-2 overflow-x-auto">
          <AiTabButton active={activeTab === "overview"} onClick={() => setActiveTab("overview")}>
            Overview
          </AiTabButton>
          <AiTabButton active={activeTab === "suggestions"} onClick={() => setActiveTab("suggestions")}>
            AI Suggestions
          </AiTabButton>
          <AiTabButton active={activeTab === "forecast"} onClick={() => setActiveTab("forecast")}>
            Demand Forecast
          </AiTabButton>
          <AiTabButton active={activeTab === "operations"} onClick={() => setActiveTab("operations")}>
            Operations
          </AiTabButton>
          <AiTabButton active={activeTab === "customers"} onClick={() => setActiveTab("customers")}>
            Customers
          </AiTabButton>
          <AiTabButton active={activeTab === "simulator"} onClick={() => setActiveTab("simulator")}>
            Simulator
          </AiTabButton>
          <AiTabButton active={activeTab === "logs"} onClick={() => setActiveTab("logs")}>
            Logs
          </AiTabButton>
        </div>
      </section>

      {activeTab === "overview" ? (
      <section className="rounded-lg border border-border bg-card p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="font-heading text-lg font-semibold">Admin AI Provider</h2>
            <p className="text-sm text-muted-foreground">
              Current provider: {state.provider}. Source metrics remain local Postgres.
            </p>
            {state.providerError ? (
              <p className="mt-1 text-sm text-destructive">{state.providerError}</p>
            ) : null}
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant={state.provider === "mock" ? "default" : "primary"}>
              {state.provider}
            </Badge>
            <Badge variant={state.fallbackUsed ? "destructive" : "success"}>
              {state.fallbackUsed ? "Fallback active" : "Configured"}
            </Badge>
          </div>
        </div>
      </section>
      ) : null}

      {activeTab === "overview" ? (
      <section className="grid gap-4 lg:grid-cols-2">
        {state.insights.length ? (
          state.insights.map((insight) => (
            <article key={insight.type} className="rounded-lg border border-border bg-card p-4">
              <div className="mb-3 flex items-center justify-between">
                <Brain className="size-5 text-primary" />
                <Badge variant="primary">{insight.type}</Badge>
              </div>
              <p className="text-sm leading-6">{insight.text}</p>
              <p className="mt-3 rounded-md bg-surface-2 px-3 py-2 text-sm">
                <span className="font-medium">AI Next Step:</span>{" "}
                {nextStepForInsight(insight.type)}
              </p>
            </article>
          ))
        ) : (
          <section className="rounded-lg border border-border bg-card lg:col-span-2">
            <AdminEmptyState
              title="No AI insights"
              description="Refresh the insights source after local orders, payments, and inventory activity are available."
            />
          </section>
        )}
      </section>
      ) : null}

      {activeTab === "overview" ? (
      <section className="grid gap-4 lg:grid-cols-3">
        <MetricPanel
          icon={<TrendingUp />}
          title="Peak Rush"
          value={state.ai.peak_rush.rush_window ?? "No rush data"}
          description={state.ai.peak_rush.recommendation}
        />
        <MetricPanel
          icon={<Package />}
          title="Inventory Risk"
          value={`${state.ai.inventory_forecast.filter((row) => row.risk !== "low").length} items`}
          description="Medium and high stockout risks in the forecast window."
        />
        <MetricPanel
          icon={<Users />}
          title="Staff Suggestions"
          value={`${state.ai.staff_scheduling.length} windows`}
          description="Suggested staffing windows based on peak order hours."
        />
      </section>
      ) : null}

      {activeTab === "overview" ? (
      <section className="grid gap-4 lg:grid-cols-3">
        <MetricPanel
          icon={<TicketPercent />}
          title="Recommendation Decisions"
          value={`${state.ai.recommendation_impact.totals.total} tracked`}
          description={`${state.ai.recommendation_impact.totals.acceptance_rate}% acceptance rate.`}
        />
        <MetricPanel
          icon={<TrendingUp />}
          title="Accepted Estimate"
          value={formatINR(state.ai.recommendation_impact.totals.accepted_estimated_value)}
          description="Estimated value from accepted AI recommendations."
        />
        <MetricPanel
          icon={<Brain />}
          title="Accepted / Rejected"
          value={`${state.ai.recommendation_impact.totals.accepted} / ${state.ai.recommendation_impact.totals.rejected}`}
          description="Track which AI suggestions are useful for the business."
        />
      </section>
      ) : null}

      {activeTab === "overview" ? (
        <section className="grid gap-5 xl:grid-cols-2">
          <AdminPieChart
            title="Recommendation Decision Mix"
            rows={[
              { name: "Accepted", value: state.ai.recommendation_impact.totals.accepted },
              { name: "Rejected", value: state.ai.recommendation_impact.totals.rejected },
              {
                name: "Presented",
                value: Math.max(
                  0,
                  state.ai.recommendation_impact.totals.total -
                    state.ai.recommendation_impact.totals.accepted -
                    state.ai.recommendation_impact.totals.rejected
                ),
              },
            ]}
            nameKey="name"
            valueKey="value"
          />
          <AdminBarChart
            title="Accepted AI Value By Type"
            rows={state.ai.recommendation_impact.by_type}
            xKey="recommendation_type"
            yKey="accepted_estimated_value"
            money
          />
        </section>
      ) : null}

      {activeTab === "suggestions" ? <OwnerSuggestionsPanel ai={state.ai} /> : null}

      {activeTab === "forecast" ? (
      <>
      {state.forecast ? (
        <section className="grid gap-5 xl:grid-cols-2">
          <AdminLineChart
            title="Predicted Revenue Trend"
            rows={state.forecast.forecast.map((row) => ({
              forecast_date: row.forecast_date,
              predicted_revenue: row.predicted_revenue,
            }))}
            xKey="forecast_date"
            yKey="predicted_revenue"
            money
          />
          <AdminBarChart
            title="Predicted Orders"
            rows={state.forecast.forecast.map((row) => ({
              forecast_date: row.forecast_date,
              predicted_orders: row.predicted_orders,
            }))}
            xKey="forecast_date"
            yKey="predicted_orders"
          />
        </section>
      ) : null}
      <section className="rounded-lg border border-border bg-card p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="font-heading text-lg font-semibold">Demand Forecast</h2>
            <p className="text-sm text-muted-foreground">
              Rule-based 7-day forecast using recent order averages and weekend uplift.
            </p>
          </div>
          <Button disabled={forecasting} onClick={() => void forecast()}>
            <CalendarDays />
            Generate
          </Button>
        </div>
        {state.forecast ? (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[620px] text-left text-sm">
              <thead className="bg-surface-2 text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Orders</th>
                  <th className="px-4 py-3">Revenue</th>
                  <th className="px-4 py-3">Weekend</th>
                  <th className="px-4 py-3">Holiday</th>
                  <th className="px-4 py-3">Confidence</th>
                  <th className="px-4 py-3">Rationale</th>
                </tr>
              </thead>
              <tbody>
                {state.forecast.forecast.length ? (
                  state.forecast.forecast.map((row) => (
                    <tr key={row.forecast_date} className="border-t border-border">
                      <td className="px-4 py-3">{row.forecast_date}</td>
                      <td className="px-4 py-3">{row.predicted_orders.toFixed(1)}</td>
                      <td className="px-4 py-3">{formatINR(row.predicted_revenue)}</td>
                      <td className="px-4 py-3">
                        <Badge variant={row.weekend_flag ? "accent" : "default"}>
                          {row.weekend_flag ? "Yes" : "No"}
                        </Badge>
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={row.holiday_flag ? "accent" : "default"}>
                          {row.holiday_flag ? "Yes" : "No"}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {row.confidence ?? "low"}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {row.rationale ?? "-"}
                      </td>
                    </tr>
                  ))
                ) : (
                  <AdminEmptyTableRow
                    colSpan={7}
                    title="No forecast rows"
                    description="Generate a forecast after local order history has been seeded or recorded."
                  />
                )}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="mt-4 flex items-center gap-2 text-sm text-muted-foreground">
            <RefreshCw className="size-4" />
            Generate a forecast to store forecast results locally.
          </p>
        )}
      </section>
      </>
      ) : null}

      {activeTab === "forecast" ? (
      <section className="grid gap-5 xl:grid-cols-2">
        <SimpleAiTable
          icon={<CalendarDays />}
          title="Forecast Weekday Profile"
          rows={(state.forecast?.weekday_profile ?? []).map((row) => ({
            main: row.weekday,
            meta: `${row.avg_orders.toFixed(1)} avg orders / ${formatINR(row.avg_revenue)} avg revenue`,
            badge: `Day ${row.weekday_no}`,
          }))}
          empty="No weekday forecast profile"
        />
        <SimpleAiTable
          icon={<ClockIcon />}
          title="Forecast Hourly Profile"
          rows={(state.forecast?.hourly_profile ?? []).map((row) => ({
            main: `${row.hour.toString().padStart(2, "0")}:00`,
            meta: `${row.orders} orders / ${formatINR(row.revenue)}`,
            badge: "Hour",
          }))}
          empty="No hourly forecast profile"
        />
      </section>
      ) : null}

      {activeTab === "operations" ? (
      <>
      <section className="grid gap-5 xl:grid-cols-2">
        <AdminBarChart
          title="Inventory Risk Projection"
          rows={state.ai.inventory_forecast.map((row) => ({
            name: row.name,
            projected_stock: row.projected_stock,
          }))}
          xKey="name"
          yKey="projected_stock"
        />
        <AdminBarChart
          title="Staff Demand Windows"
          rows={state.ai.staff_scheduling.map((row) => ({
            window: row.window,
            orders: row.orders,
          }))}
          xKey="window"
          yKey="orders"
        />
      </section>
      <section className="grid gap-5 xl:grid-cols-2">
        <SimpleAiTable
          icon={<AlertTriangle />}
          title="Inventory Forecast"
          rows={state.ai.inventory_forecast.map((row) => ({
            main: row.name,
            meta: `${row.projected_stock} ${row.unit} projected / reorder ${row.suggested_reorder_quantity} ${row.unit}`,
            badge: row.risk,
            nextStep:
              row.risk === "high"
                ? "Create a purchase request before the next rush window."
                : "Monitor stock after today's sales close.",
          }))}
          empty="No ingredient forecast yet"
        />
        <SimpleAiTable
          icon={<Users />}
          title="Staff Scheduling"
          rows={state.ai.staff_scheduling.map((row) => ({
            main: row.window,
            meta: `${row.suggested_staff} staff / ${row.role_mix}`,
            badge: `${row.orders} orders`,
            nextStep: "Confirm staff coverage for this window before shift planning.",
          }))}
          empty="No staff windows yet"
        />
        <SimpleAiTable
          icon={<TicketPercent />}
          title="Coupon Recommendations"
          rows={state.ai.coupon_recommendations.map((row) => ({
            main: `${row.coupon} / ${row.discount_percent}%`,
            meta: `${formatINR(row.threshold_amount)} threshold / ${row.reason}`,
            badge: row.name,
            nextStep: "Review margin impact, then create or update the matching coupon.",
            recommendation: {
              type: "coupon",
              key: row.recommendation_key,
              title: `${row.coupon} coupon`,
              detail: row.reason,
              estimatedValue: row.estimated_value,
              sourceMetrics: row.source_metrics,
            },
          }))}
          empty="No coupon recommendations yet"
          savingKey={decisionSaving}
          onDecision={decideRecommendation}
        />
        <SimpleAiTable
          icon={<Brain />}
          title="Smart Upsells"
          rows={state.ai.smart_upsells.map((row) => ({
            main: row.recommendation,
            meta: row.reason,
            badge: row.trigger_item,
            nextStep: "Enable this upsell in staff prompts or customer ordering flow.",
            recommendation: {
              type: "upsell",
              key: row.recommendation_key,
              title: row.recommendation,
              detail: row.reason,
              estimatedValue: row.estimated_value,
              sourceMetrics: row.source_metrics,
            },
          }))}
          empty="No upsells yet"
          savingKey={decisionSaving}
          onDecision={decideRecommendation}
        />
      </section>
      </>
      ) : null}

      {activeTab === "customers" ? (
      <>
      <section className="grid gap-5 xl:grid-cols-2">
        <AdminPieChart
          title="Sentiment Split"
          rows={[
            { name: "Positive", value: state.ai.sentiment_analysis.totals.positive },
            { name: "Neutral", value: state.ai.sentiment_analysis.totals.neutral },
            { name: "Negative", value: state.ai.sentiment_analysis.totals.negative },
          ]}
          nameKey="name"
          valueKey="value"
        />
        <AdminBarChart
          title="Feedback Topics"
          rows={state.ai.sentiment_analysis.top_topics.map((topic) => ({
            topic: topic.topic,
            mentions: topic.mentions,
          }))}
          xKey="topic"
          yKey="mentions"
        />
      </section>
      <SimpleAiTable
        icon={<AlertTriangle />}
        title="Churn / Inactive Customer Risk"
        rows={state.ai.churn_risks.map((row) => ({
          main: row.customer_name,
          meta: `${row.days_since_last_order} days inactive / ${row.suggested_action}`,
          badge: row.risk,
          nextStep: "Send a controlled win-back offer and review response after 48 hours.",
        }))}
        empty="No churn risks detected yet"
      />

      <section className="grid gap-5 xl:grid-cols-2">
        <SimpleAiTable
          icon={<TicketPercent />}
          title="Short-Term Loss Vs LTV"
          rows={state.ai.ltv_recommendations.map((row) => ({
            main: row.customer_name,
            meta: `${formatINR(row.estimated_ltv)} estimated LTV / ${row.recommended_discount_percent}% controlled offer. ${row.short_term_loss_note}`,
            badge: row.customer_phone,
            nextStep: "Use coupon limits so the short-term discount does not leak to all users.",
          }))}
          empty="No LTV recommendations yet"
        />
        <section className="rounded-lg border border-border bg-card p-4">
          <h2 className="font-heading text-lg font-semibold">Sentiment And Voice Readiness</h2>
          <div className="mt-4 grid gap-3">
            <div className="rounded-lg border border-border p-3">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <MessageSquareText className="h-4 w-4 text-primary" />
                  <p className="text-sm font-medium">Customer sentiment</p>
                </div>
                <Badge>{state.ai.sentiment_analysis.status}</Badge>
              </div>
              <div className="mt-3 grid gap-2 sm:grid-cols-3">
                <MetricPill
                  label="Reviews"
                  value={`${state.ai.sentiment_analysis.totals.total}`}
                />
                <MetricPill
                  label="Avg rating"
                  value={`${state.ai.sentiment_analysis.totals.average_rating}/5`}
                />
                <MetricPill
                  label="Positive"
                  value={`${state.ai.sentiment_analysis.totals.positive_rate}%`}
                />
              </div>
              <p className="mt-3 text-sm text-muted-foreground">
                {state.ai.sentiment_analysis.recommendation}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {state.ai.sentiment_analysis.top_topics.map((topic) => (
                  <Badge key={topic.topic}>
                    {topic.topic}: {topic.mentions}
                  </Badge>
                ))}
                {!state.ai.sentiment_analysis.top_topics.length ? (
                  <span className="text-xs text-muted-foreground">No topics detected yet.</span>
                ) : null}
              </div>
              <div className="mt-3 space-y-2">
                {state.ai.sentiment_analysis.recent.slice(0, 3).map((feedback) => (
                  <div key={feedback.id} className="rounded-md bg-muted/40 p-2">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-medium">
                        {feedback.customer_name || feedback.channel}
                      </span>
                      <Badge
                        variant={
                          feedback.sentiment_label === "positive"
                            ? "success"
                            : feedback.sentiment_label === "negative"
                              ? "destructive"
                              : "default"
                        }
                      >
                        {feedback.rating}/5 {feedback.sentiment_label}
                      </Badge>
                    </div>
                    <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                      {feedback.feedback_text}
                    </p>
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-lg border border-border p-3">
              <Badge variant="success">{state.ai.voice_ordering_readiness.status}</Badge>
              <p className="mt-2 text-sm font-medium">Voice ordering readiness</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Source tracked as {state.ai.voice_ordering_readiness.tracked_order_source}.
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {state.ai.voice_ordering_readiness.notes.join(" ")}
              </p>
            </div>
          </div>
        </section>
      </section>
      </>
      ) : null}

      {activeTab === "simulator" ? (
      <RevenueScenarioPanel
        draft={scenarioDraft}
        scenario={scenario}
        saving={simulating}
        onChange={setScenarioDraft}
        onSimulate={() => void simulate()}
      />
      ) : null}

      {activeTab === "logs" ? (
      <section className="rounded-lg border border-border bg-card">
        <div className="flex flex-col gap-3 border-b border-border p-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="font-heading text-lg font-semibold">Insight Log</h2>
            <p className="text-sm text-muted-foreground">Filter historical AI insight logs.</p>
          </div>
          <div className="grid gap-2 sm:grid-cols-[130px_160px_90px_auto]">
            <Input
              placeholder="Provider"
              value={logFilters.provider}
              onChange={(event) => setLogFilters({ ...logFilters, provider: event.target.value })}
            />
            <Input
              placeholder="Insight type"
              value={logFilters.insight_type}
              onChange={(event) => setLogFilters({ ...logFilters, insight_type: event.target.value })}
            />
            <Input
              type="number"
              min={1}
              max={200}
              value={logFilters.limit}
              onChange={(event) => setLogFilters({ ...logFilters, limit: Number(event.target.value) })}
            />
            <Button variant="secondary" onClick={() => void refreshLogs()}>
              <RefreshCw />
              Logs
            </Button>
          </div>
        </div>
        <div className="divide-y divide-border">
          {state.logs.length ? (
            state.logs.map((log) => (
              <div key={log.id} className="p-4 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <Badge>{log.provider}</Badge>
                  <span className="text-xs text-muted-foreground">
                    {new Date(log.created_at).toLocaleString("en-IN")}
                  </span>
                </div>
                <p className="mt-2">{log.insight_text}</p>
              </div>
            ))
          ) : (
            <AdminEmptyState
              title="No insight logs"
              description="Generated or refreshed AI insights will be logged here for admin review."
            />
          )}
        </div>
      </section>
      ) : null}
    </main>
  );
}

function AiTabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
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

function nextStepForInsight(type: string) {
  const normalized = type.toLowerCase();
  if (normalized.includes("demand")) return "Check forecast tab and prep stock for the next two demand days.";
  if (normalized.includes("inventory")) return "Create replenishment requests for high-risk ingredients.";
  if (normalized.includes("staff")) return "Match staff roster to peak windows before publishing shifts.";
  if (normalized.includes("coupon")) return "Convert the best idea into one active coupon campaign.";
  if (normalized.includes("sentiment")) return "Review recent feedback themes and assign one service fix.";
  return "Review the related tab and accept or reject the recommendation so impact can be tracked.";
}

function OwnerSuggestionsPanel({ ai }: { ai: AdminAiBusinessIntelligence }) {
  const suggestions = buildOwnerSuggestions(ai);
  return (
    <section className="rounded-lg border border-border bg-card">
      <div className="border-b border-border p-4">
        <h2 className="font-heading text-lg font-semibold">Owner Action Summary</h2>
        <p className="text-sm text-muted-foreground">
          Prioritized AI suggestions to increase sales, protect margins, and fix risk areas.
        </p>
      </div>
      <div className="divide-y divide-border">
        {suggestions.map((suggestion, index) => (
          <article key={`${suggestion.title}-${index}`} className="grid gap-3 p-4 lg:grid-cols-[150px_1fr_220px]">
            <div>
              <Badge
                variant={
                  suggestion.priority === "Needs Review"
                    ? "destructive"
                    : suggestion.priority === "Growth"
                      ? "primary"
                      : "success"
                }
              >
                {suggestion.priority}
              </Badge>
            </div>
            <div>
              <h3 className="font-heading text-base font-semibold">{suggestion.title}</h3>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">{suggestion.summary}</p>
            </div>
            <p className="rounded-md bg-surface-2 px-3 py-2 text-sm">
              <span className="font-medium">Next Step:</span> {suggestion.nextStep}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}

function buildOwnerSuggestions(ai: AdminAiBusinessIntelligence) {
  const highRiskStock = ai.inventory_forecast.filter((row) => row.risk === "high");
  const mediumRiskStock = ai.inventory_forecast.filter((row) => row.risk === "medium");
  const topUpsell = ai.smart_upsells[0];
  const topCoupon = ai.coupon_recommendations[0];
  const topStaff = ai.staff_scheduling[0];
  const churn = ai.churn_risks[0];
  const ltv = ai.ltv_recommendations[0];
  const negativeRate = ai.sentiment_analysis.totals.negative_rate;
  const acceptedValue = ai.recommendation_impact.totals.accepted_estimated_value;

  return [
    {
      priority: highRiskStock.length ? "Needs Review" : "Stable",
      title: highRiskStock.length ? "Stock risk can block sales" : "Inventory risk is controlled",
      summary: highRiskStock.length
        ? `${highRiskStock.length} ingredients are high risk. The busiest windows should not start with weak stock.`
        : `${mediumRiskStock.length} ingredients need monitoring, but no high-risk stockout is visible right now.`,
      nextStep: highRiskStock.length
        ? "Create purchase requests for high-risk ingredients today."
        : "Review medium-risk ingredients after closing stock count.",
    },
    {
      priority: "Growth",
      title: topCoupon ? `Run a focused coupon: ${topCoupon.coupon}` : "Create one focused coupon",
      summary: topCoupon
        ? `${topCoupon.discount_percent}% above ${formatINR(topCoupon.threshold_amount)} can lift demand without making discounts too open.`
        : "No coupon recommendation is available yet, so use a controlled AOV booster coupon.",
      nextStep: "Create one active coupon and compare revenue after 48 hours.",
    },
    {
      priority: "Growth",
      title: topUpsell ? `Push upsell: ${topUpsell.recommendation}` : "Add one staff upsell prompt",
      summary: topUpsell
        ? topUpsell.reason
        : "Upsell data is still thin; start with extra cheese, dip, or beverage prompts.",
      nextStep: "Add this upsell to staff/POS prompts and track acceptance.",
    },
    {
      priority: topStaff ? "Needs Review" : "Stable",
      title: topStaff ? `Protect rush window ${topStaff.window}` : "Rush staffing looks normal",
      summary: topStaff
        ? `${topStaff.orders} orders are expected in this window with ${topStaff.suggested_staff} suggested staff.`
        : "No heavy rush window is detected from current data.",
      nextStep: topStaff ? "Confirm staff coverage before shift starts." : "Keep current roster and review after weekend data.",
    },
    {
      priority: negativeRate >= 25 ? "Needs Review" : "Stable",
      title: negativeRate >= 25 ? "Customer feedback needs attention" : "Sentiment is healthy",
      summary: `${ai.sentiment_analysis.totals.total} reviews, ${ai.sentiment_analysis.totals.positive_rate}% positive, ${negativeRate}% negative.`,
      nextStep: negativeRate >= 25
        ? "Pick the top complaint topic and assign one fix today."
        : "Keep asking for reviews and monitor negative topics weekly.",
    },
    {
      priority: churn ? "Growth" : "Stable",
      title: churn ? `Win back ${churn.customer_name}` : "No major churn signal",
      summary: churn
        ? `${churn.customer_name} is ${churn.days_since_last_order} days inactive after ${churn.orders} orders.`
        : "No inactive high-value customer is currently flagged.",
      nextStep: churn ? "Send a limited comeback coupon." : "Keep checking weekly churn list.",
    },
    {
      priority: ltv ? "Growth" : "Stable",
      title: ltv ? "Use LTV-based discounting" : "LTV data is still building",
      summary: ltv
        ? `${ltv.customer_name} has estimated LTV of ${formatINR(ltv.estimated_ltv)}; use controlled discounts, not blanket discounts.`
        : "More repeat orders are needed before strong LTV recommendations appear.",
      nextStep: ltv ? "Apply coupon limits by customer segment." : "Collect more repeat customer data.",
    },
    {
      priority: acceptedValue > 0 ? "Growth" : "Needs Review",
      title: "Track AI decision value",
      summary: `${formatINR(acceptedValue)} estimated value is attached to accepted AI recommendations.`,
      nextStep: "Accept or reject each AI suggestion so future analytics show what worked.",
    },
  ].slice(0, 10);
}

function MetricPanel({
  icon,
  title,
  value,
  description,
}: {
  icon: ReactNode;
  title: string;
  value: string;
  description: string;
}) {
  return (
    <section className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-center justify-between">
        <div className="text-primary [&_svg]:size-5">{icon}</div>
        <Badge variant="primary">AI</Badge>
      </div>
      <h2 className="mt-4 font-heading text-lg font-semibold">{value}</h2>
      <p className="mt-1 text-xs uppercase text-muted-foreground">{title}</p>
      <p className="mt-3 text-sm leading-6 text-muted-foreground">{description}</p>
    </section>
  );
}

function MetricPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-muted/40 px-3 py-2">
      <p className="text-xs uppercase text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </div>
  );
}

function SimpleAiTable({
  icon,
  title,
  rows,
  empty,
  savingKey,
  onDecision,
}: {
  icon: ReactNode;
  title: string;
  rows: Array<{
    main: string;
    meta: string;
    badge: string;
    nextStep?: string;
    recommendation?: {
      type: "upsell" | "coupon";
      key: string;
      title: string;
      detail: string;
      estimatedValue: number;
      sourceMetrics: Record<string, unknown>;
    };
  }>;
  empty: string;
  savingKey?: string | null;
  onDecision?: (payload: Parameters<typeof recordAdminRecommendationEvent>[0]) => Promise<void>;
}) {
  return (
    <section className="rounded-lg border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border p-4">
        <h2 className="flex items-center gap-2 font-heading text-lg font-semibold">
          <span className="text-primary [&_svg]:size-5">{icon}</span>
          {title}
        </h2>
        <Badge>{rows.length}</Badge>
      </div>
      <div className="divide-y divide-border">
        {rows.length ? (
          rows.map((row, index) => (
            <div key={`${row.main}-${index}`} className="flex items-start justify-between gap-4 p-4 text-sm">
              <div>
                <p className="font-medium">{row.main}</p>
                <p className="mt-1 text-muted-foreground">{row.meta}</p>
                {row.nextStep ? (
                  <p className="mt-2 rounded-md bg-surface-2 px-3 py-2 text-xs">
                    <span className="font-medium">AI Next Step:</span> {row.nextStep}
                  </p>
                ) : null}
                {row.recommendation ? (
                  <div className="mt-3 flex gap-2">
                    <Button
                      size="sm"
                      variant="secondary"
                      disabled={
                        savingKey === `${row.recommendation.type}:${row.recommendation.key}:accepted`
                      }
                      onClick={() =>
                        onDecision?.({
                          recommendation_type: row.recommendation!.type,
                          recommendation_key: row.recommendation!.key,
                          title: row.recommendation!.title,
                          detail: row.recommendation!.detail,
                          status: "accepted",
                          estimated_value: row.recommendation!.estimatedValue,
                          source_metrics: row.recommendation!.sourceMetrics,
                        })
                      }
                    >
                      Accept
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      disabled={
                        savingKey === `${row.recommendation.type}:${row.recommendation.key}:rejected`
                      }
                      onClick={() =>
                        onDecision?.({
                          recommendation_type: row.recommendation!.type,
                          recommendation_key: row.recommendation!.key,
                          title: row.recommendation!.title,
                          detail: row.recommendation!.detail,
                          status: "rejected",
                          estimated_value: row.recommendation!.estimatedValue,
                          source_metrics: row.recommendation!.sourceMetrics,
                        })
                      }
                    >
                      Reject
                    </Button>
                  </div>
                ) : null}
              </div>
              <Badge>{row.badge}</Badge>
            </div>
          ))
        ) : (
          <AdminEmptyState title={empty} description="Seed local demo data or wait for more orders to improve this signal." />
        )}
      </div>
    </section>
  );
}

function RevenueScenarioPanel({
  draft,
  scenario,
  saving,
  onChange,
  onSimulate,
}: {
  draft: ScenarioDraft;
  scenario: AdminRevenueScenario | null;
  saving: boolean;
  onChange: (draft: ScenarioDraft) => void;
  onSimulate: () => void;
}) {
  return (
    <section className="rounded-lg border border-border bg-card p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="flex items-center gap-2 font-heading text-lg font-semibold">
            <Calculator className="size-5 text-primary" />
            Revenue Scenario Simulator
          </h2>
          <p className="text-sm text-muted-foreground">
            Deterministic margin math before any AI explanation.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            disabled={saving}
            onClick={() =>
              onChange({
                menu_price_adjustment_percent: 6,
                ingredient_price_increase_percent: 8,
                rent_increase_amount: 5000,
                other_fixed_cost_increase_amount: 2500,
                discount_change_percent: -10,
              })
            }
          >
            Inflation Preset
          </Button>
          <Button disabled={saving} onClick={onSimulate}>
            <Calculator />
            Simulate
          </Button>
        </div>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-5">
        <ScenarioInput label="Menu %" value={draft.menu_price_adjustment_percent} onChange={(value) => onChange({ ...draft, menu_price_adjustment_percent: value })} />
        <ScenarioInput label="Ingredient %" value={draft.ingredient_price_increase_percent} onChange={(value) => onChange({ ...draft, ingredient_price_increase_percent: value })} />
        <ScenarioInput label="Rent +₹" value={draft.rent_increase_amount} onChange={(value) => onChange({ ...draft, rent_increase_amount: value })} />
        <ScenarioInput label="Fixed +₹" value={draft.other_fixed_cost_increase_amount} onChange={(value) => onChange({ ...draft, other_fixed_cost_increase_amount: value })} />
        <ScenarioInput label="Discount %" value={draft.discount_change_percent} onChange={(value) => onChange({ ...draft, discount_change_percent: value })} />
      </div>
      {scenario ? (
        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          <MetricPanel
            icon={<TrendingUp />}
            title="Projected Revenue"
            value={formatINR(scenario.projected.revenue)}
            description={`Baseline ${formatINR(scenario.baseline.revenue)}`}
          />
          <MetricPanel
            icon={<Calculator />}
            title="Margin Delta"
            value={formatINR(scenario.projected.margin_delta)}
            description={scenario.safety_note}
          />
          <section className="rounded-lg border border-border bg-surface-2 p-4">
            <h3 className="font-heading text-sm font-semibold">Suggested Actions</h3>
            <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
              {scenario.recommended_actions.map((action) => (
                <li key={action}>{action}</li>
              ))}
            </ul>
          </section>
        </div>
      ) : null}
    </section>
  );
}

function ScenarioInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="space-y-2">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      <Input
        type="number"
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}
