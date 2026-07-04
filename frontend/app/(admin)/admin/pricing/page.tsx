"use client";

import { CalendarDays, RefreshCw, Save, Sparkles } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import {
  getAdminPriceHistory,
  getAdminPricing,
  getFestivalCouponSuggestions,
  upsertAdminDiscount,
  updateAdminPricing,
  type AdminFestivalCouponSuggestion,
  type AdminPriceHistoryEntry,
  type AdminPricing,
} from "@/lib/admin-api";
import { formatINR } from "@/lib/utils";
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
      pricing: AdminPricing;
      priceHistory: AdminPriceHistoryEntry[];
      festivalSuggestions: AdminFestivalCouponSuggestion[];
    };

type PricingTab = "coupons" | "gst" | "history";

export default function AdminPricingPage() {
  const [state, setState] = useState<State>({ status: "loading" });
  const [activeTab, setActiveTab] = useState<PricingTab>("coupons");
  const [saving, setSaving] = useState(false);
  const [discountSaving, setDiscountSaving] = useState<string | null>(null);
  const [historySaving, setHistorySaving] = useState(false);
  const [historyLimit, setHistoryLimit] = useState(100);
  const [suggestionYear, setSuggestionYear] = useState(new Date().getFullYear());
  const [couponFilters, setCouponFilters] = useState({
    search: "",
    status: "all" as "all" | "active" | "inactive",
  });
  const [historySearch, setHistorySearch] = useState("");
  const [newRule, setNewRule] = useState(emptyCoupon());

  const load = useCallback(async () => {
    setState({ status: "loading" });
    try {
      const [data, history, festival] = await Promise.all([
        getAdminPricing(),
        getAdminPriceHistory(100),
        getFestivalCouponSuggestions(8, suggestionYear),
      ]);
      setState({
        status: "ready",
        pricing: data.pricing,
        priceHistory: history.price_history,
        festivalSuggestions: festival.suggestions,
      });
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof Error ? error.message : "Pricing load failed.",
      });
    }
  }, [suggestionYear]);

  async function saveGst(pricing: AdminPricing) {
    setSaving(true);
    try {
      const data = await updateAdminPricing({
        gst_rate_percent: Number(pricing.gst_rate_percent),
        discount_rate_percent: 0,
        discount_quantity_threshold: 999999,
        reason: "Admin GST update; discounts are coupon-only",
      });
      setState((current) =>
        current.status === "ready" ? { ...current, pricing: data.pricing } : current
      );
    } finally {
      setSaving(false);
    }
  }

  async function refreshPriceHistory(limit = historyLimit) {
    setHistorySaving(true);
    try {
      const history = await getAdminPriceHistory(limit);
      setState((current) =>
        current.status === "ready"
          ? { ...current, priceHistory: history.price_history }
          : current
      );
    } finally {
      setHistorySaving(false);
    }
  }

  async function saveRule(rule: AdminPricing["discount_rules"][number]) {
    setDiscountSaving(rule.id);
    try {
      await upsertAdminDiscount({ ...rule, reason: "Admin coupon update" });
      await load();
    } finally {
      setDiscountSaving(null);
    }
  }

  async function createRule() {
    setDiscountSaving("new");
    try {
      await upsertAdminDiscount({ ...newRule, reason: "Admin coupon create" });
      setNewRule(emptyCoupon());
      await load();
    } finally {
      setDiscountSaving(null);
    }
  }

  function useFestivalSuggestion(suggestion: AdminFestivalCouponSuggestion) {
    setNewRule({
      name: `${suggestion.name} Offer`,
      coupon_code: suggestion.suggested_coupon_code,
      description: suggestion.suggestion,
      discount_percent: suggestion.suggested_discount_percent,
      threshold_amount: suggestion.suggested_threshold_amount,
      min_quantity: 1,
      no_min_quantity: true,
      no_min_value: false,
      start_date: suggestion.festival_date,
      end_date: suggestion.festival_date,
      is_active: true,
    });
    setActiveTab("coupons");
  }

  useEffect(() => {
    void load();
  }, [load]);

  if (state.status === "loading") return <AdminLoading label="Loading pricing" />;
  if (state.status === "error") {
    return <AdminError message={state.message} onRetry={() => void load()} />;
  }

  const { pricing, priceHistory, festivalSuggestions } = state;
  const filteredRules = pricing.discount_rules.filter((rule) => {
    const query = couponFilters.search.trim().toLowerCase();
    const matchesSearch =
      !query ||
      rule.name.toLowerCase().includes(query) ||
      (rule.coupon_code ?? "").toLowerCase().includes(query);
    const matchesStatus =
      couponFilters.status === "all" ||
      (couponFilters.status === "active" && rule.is_active) ||
      (couponFilters.status === "inactive" && !rule.is_active);
    return matchesSearch && matchesStatus;
  });
  const filteredHistory = priceHistory.filter((row) => {
    const query = historySearch.trim().toLowerCase();
    return (
      !query ||
      row.menu_item_name.toLowerCase().includes(query) ||
      row.item_code.toLowerCase().includes(query) ||
      row.category_name.toLowerCase().includes(query) ||
      (row.reason ?? "").toLowerCase().includes(query)
    );
  });

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8">
      <AdminPageHeader
        title="Pricing-Discount Dashboard"
        subtitle="GST is deterministic. Customer discounts are coupon campaigns only; one coupon is applied per order."
      />

      <section className="rounded-lg border border-border bg-card p-4">
        <div className="flex gap-2 overflow-x-auto">
          <TabButton active={activeTab === "coupons"} onClick={() => setActiveTab("coupons")}>
            Coupons
          </TabButton>
          <TabButton active={activeTab === "gst"} onClick={() => setActiveTab("gst")}>
            GST Settings
          </TabButton>
          <TabButton active={activeTab === "history"} onClick={() => setActiveTab("history")}>
            Price History
          </TabButton>
        </div>
      </section>

      {activeTab === "coupons" ? (
        <CouponsModule
          newRule={newRule}
          rules={filteredRules}
          festivalSuggestions={festivalSuggestions}
          suggestionYear={suggestionYear}
          filters={couponFilters}
          saving={discountSaving}
          onNewRuleChange={setNewRule}
          onFiltersChange={setCouponFilters}
          onCreate={() => void createRule()}
          onUseFestival={useFestivalSuggestion}
          onSuggestionYearChange={setSuggestionYear}
          onSaveRule={saveRule}
          onRuleChange={(rule) =>
            setState((current) =>
              current.status === "ready"
                ? {
                    ...current,
                    pricing: {
                      ...current.pricing,
                      discount_rules: current.pricing.discount_rules.map((item) =>
                        item.id === rule.id ? rule : item
                      ),
                    },
                  }
                : current
            )
          }
        />
      ) : null}

      {activeTab === "gst" ? (
        <GstModule
          pricing={pricing}
          saving={saving}
          onChange={(gst_rate_percent) =>
            setState((current) =>
              current.status === "ready"
                ? {
                    ...current,
                    pricing: { ...current.pricing, gst_rate_percent },
                  }
                : current
            )
          }
          onSave={() => void saveGst(pricing)}
        />
      ) : null}

      {activeTab === "history" ? (
        <PriceHistorySection
          rows={filteredHistory}
          limit={historyLimit}
          saving={historySaving}
          search={historySearch}
          onSearchChange={setHistorySearch}
          onLimitChange={setHistoryLimit}
          onRefresh={() => void refreshPriceHistory()}
        />
      ) : null}
    </main>
  );
}

function emptyCoupon() {
  return {
    name: "",
    coupon_code: "",
    description: "",
    discount_percent: 10,
    threshold_amount: 499,
    min_quantity: 1,
    no_min_quantity: true,
    no_min_value: false,
    start_date: "",
    end_date: "",
    is_active: true,
  };
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

function CouponsModule({
  newRule,
  rules,
  festivalSuggestions,
  suggestionYear,
  filters,
  saving,
  onNewRuleChange,
  onFiltersChange,
  onCreate,
  onUseFestival,
  onSuggestionYearChange,
  onSaveRule,
  onRuleChange,
}: {
  newRule: ReturnType<typeof emptyCoupon>;
  rules: AdminPricing["discount_rules"];
  festivalSuggestions: AdminFestivalCouponSuggestion[];
  suggestionYear: number;
  filters: { search: string; status: "all" | "active" | "inactive" };
  saving: string | null;
  onNewRuleChange: (rule: ReturnType<typeof emptyCoupon>) => void;
  onFiltersChange: (filters: { search: string; status: "all" | "active" | "inactive" }) => void;
  onCreate: () => void;
  onUseFestival: (suggestion: AdminFestivalCouponSuggestion) => void;
  onSuggestionYearChange: (year: number) => void;
  onSaveRule: (rule: AdminPricing["discount_rules"][number]) => Promise<void>;
  onRuleChange: (rule: AdminPricing["discount_rules"][number]) => void;
}) {
  return (
    <section className="grid gap-5">
      <section className="rounded-lg border border-border bg-card p-4">
        <h2 className="font-heading text-lg font-semibold">Create Coupon Campaign</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          One coupon can be applied to one order at a time. No automatic quantity discount is used.
        </p>
        <div className="mt-4 grid gap-3 xl:grid-cols-[1.2fr_150px_120px_140px_130px_150px_150px_auto]">
          <LabeledInput
            label="Campaign name"
            placeholder="Diwali Family Combo"
            value={newRule.name}
            onChange={(value) => onNewRuleChange({ ...newRule, name: value })}
          />
          <LabeledInput
            label="Coupon code"
            placeholder="DIWALI18"
            value={newRule.coupon_code}
            onChange={(value) => onNewRuleChange({ ...newRule, coupon_code: value })}
          />
          <LabeledInput
            label="Discount %"
            type="number"
            value={newRule.discount_percent}
            onChange={(value) =>
              onNewRuleChange({ ...newRule, discount_percent: Number(value) })
            }
          />
          <LabeledInput
            label="Min order value"
            type="number"
            value={newRule.no_min_value ? "" : newRule.threshold_amount}
            disabled={newRule.no_min_value}
            onChange={(value) =>
              onNewRuleChange({ ...newRule, threshold_amount: Number(value) })
            }
          />
          <LabeledInput
            label="Min quantity"
            type="number"
            value={newRule.no_min_quantity ? "" : newRule.min_quantity}
            disabled={newRule.no_min_quantity}
            onChange={(value) =>
              onNewRuleChange({ ...newRule, min_quantity: Number(value) })
            }
          />
          <LabeledInput
            label="Start date"
            type="date"
            value={newRule.start_date}
            onChange={(value) => onNewRuleChange({ ...newRule, start_date: value })}
          />
          <LabeledInput
            label="End date"
            title="Last date when this coupon remains valid. Leave empty for no planned end date."
            type="date"
            value={newRule.end_date}
            onChange={(value) => onNewRuleChange({ ...newRule, end_date: value })}
          />
          <div className="flex items-end">
            <Button disabled={saving === "new" || !newRule.name || !newRule.coupon_code} onClick={onCreate}>
              <Save />
              Create
            </Button>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap gap-4">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={newRule.no_min_value}
              onChange={(event) =>
                onNewRuleChange({ ...newRule, no_min_value: event.target.checked })
              }
            />
            No minimum value
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={newRule.no_min_quantity}
              onChange={(event) =>
                onNewRuleChange({ ...newRule, no_min_quantity: event.target.checked })
              }
            />
            No minimum quantity
          </label>
        </div>
      </section>

      <section className="rounded-lg border border-border bg-card">
        <div className="flex flex-col gap-3 border-b border-border p-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="font-heading text-lg font-semibold">Coupon Rules</h2>
            <p className="text-xs text-muted-foreground">Search and manage coupon campaigns.</p>
          </div>
          <div className="grid gap-2 sm:grid-cols-[260px_150px]">
            <Input
              placeholder="Search coupon or campaign"
              value={filters.search}
              onChange={(event) => onFiltersChange({ ...filters, search: event.target.value })}
            />
            <select
              className="h-11 rounded-lg border border-border bg-surface-2 px-3 text-sm"
              value={filters.status}
              onChange={(event) =>
                onFiltersChange({
                  ...filters,
                  status: event.target.value as typeof filters.status,
                })
              }
            >
              <option value="all">All status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1120px] text-left text-sm">
            <thead className="bg-surface-2 text-xs uppercase text-muted-foreground">
              <tr>
                <th className="px-4 py-3">Campaign</th>
                <th className="px-4 py-3">Coupon</th>
                <th className="px-4 py-3">Discount</th>
                <th className="px-4 py-3">Min Value</th>
                <th className="px-4 py-3">Min Qty</th>
                <th className="px-4 py-3">Dates</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {rules.length ? (
                rules.map((rule) => (
                  <tr key={rule.id} className="border-t border-border">
                    <td className="px-4 py-3">
                      <Input
                        value={rule.name}
                        onChange={(event) => onRuleChange({ ...rule, name: event.target.value })}
                      />
                    </td>
                    <td className="px-4 py-3">
                      <Input
                        value={rule.coupon_code ?? ""}
                        onChange={(event) =>
                          onRuleChange({ ...rule, coupon_code: event.target.value })
                        }
                      />
                    </td>
                    <td className="px-4 py-3">
                      <Input
                        type="number"
                        min={0}
                        max={100}
                        value={rule.discount_percent}
                        onChange={(event) =>
                          onRuleChange({ ...rule, discount_percent: Number(event.target.value) })
                        }
                      />
                    </td>
                    <td className="px-4 py-3">
                      <div className="grid min-w-[150px] gap-2">
                        <Input
                          type="number"
                          min={0}
                          disabled={rule.no_min_value}
                          value={rule.no_min_value ? "" : rule.threshold_amount}
                          onChange={(event) =>
                            onRuleChange({
                              ...rule,
                              threshold_amount: Number(event.target.value),
                            })
                          }
                        />
                        <label className="flex items-center gap-2 text-xs text-muted-foreground">
                          <input
                            type="checkbox"
                            checked={Boolean(rule.no_min_value)}
                            onChange={(event) =>
                              onRuleChange({ ...rule, no_min_value: event.target.checked })
                            }
                          />
                          No min value
                        </label>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="grid min-w-[150px] gap-2">
                        <Input
                          type="number"
                          min={1}
                          disabled={rule.no_min_quantity}
                          value={rule.no_min_quantity ? "" : rule.min_quantity ?? 1}
                          onChange={(event) =>
                            onRuleChange({ ...rule, min_quantity: Number(event.target.value) })
                          }
                        />
                        <label className="flex items-center gap-2 text-xs text-muted-foreground">
                          <input
                            type="checkbox"
                            checked={Boolean(rule.no_min_quantity)}
                            onChange={(event) =>
                              onRuleChange({
                                ...rule,
                                no_min_quantity: event.target.checked,
                              })
                            }
                          />
                          No min qty
                        </label>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="grid min-w-[170px] gap-2">
                        <Input
                          type="date"
                          value={rule.start_date ?? ""}
                          onChange={(event) =>
                            onRuleChange({ ...rule, start_date: event.target.value })
                          }
                        />
                        <Input
                          type="date"
                          title="Last date when this coupon remains valid."
                          value={rule.end_date ?? ""}
                          onChange={(event) =>
                            onRuleChange({ ...rule, end_date: event.target.value })
                          }
                        />
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <button onClick={() => onRuleChange({ ...rule, is_active: !rule.is_active })}>
                        <Badge variant={rule.is_active ? "success" : "default"}>
                          {rule.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </button>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={saving === rule.id}
                        onClick={() => void onSaveRule(rule)}
                      >
                        <Save />
                        Save
                      </Button>
                    </td>
                  </tr>
                ))
              ) : (
                <AdminEmptyTableRow
                  colSpan={8}
                  title="No coupons match"
                  description="Create a coupon campaign or adjust filters."
                />
              )}
            </tbody>
          </table>
        </div>
      </section>

      <SuggestionModule
        suggestions={festivalSuggestions}
        year={suggestionYear}
        onYearChange={onSuggestionYearChange}
        onUse={onUseFestival}
      />
    </section>
  );
}

function SuggestionModule({
  suggestions,
  year,
  onYearChange,
  onUse,
}: {
  suggestions: AdminFestivalCouponSuggestion[];
  year: number;
  onYearChange: (year: number) => void;
  onUse: (suggestion: AdminFestivalCouponSuggestion) => void;
}) {
  const currentYear = new Date().getFullYear();
  return (
    <section className="rounded-lg border border-border bg-card">
      <div className="flex flex-col gap-3 border-b border-border p-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="flex items-center gap-2 font-heading text-lg font-semibold">
            <Sparkles className="size-5 text-primary" />
            Coupon Growth Ideas
          </h2>
          <p className="text-sm text-muted-foreground">
            Mix of calendar moments and analytics-based offers for customer interest.
          </p>
        </div>
        <select
          className="h-11 rounded-lg border border-border bg-surface-2 px-3 text-sm"
          value={year}
          onChange={(event) => onYearChange(Number(event.target.value))}
        >
          <option value={currentYear}>{currentYear}</option>
          <option value={currentYear + 1}>{currentYear + 1}</option>
        </select>
      </div>
      <div className="grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-3">
        {suggestions.map((suggestion) => (
          <article key={`${suggestion.festival_date}-${suggestion.name}`} className="rounded-lg border border-border bg-surface-2 p-4">
            <div className="flex items-center justify-between gap-3">
              <h3 className="font-heading text-base font-semibold">{suggestion.name}</h3>
              <Badge>{suggestion.source_type === "analytics" ? "Analytics" : suggestion.festival_date}</Badge>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">{suggestion.suggestion}</p>
            <p className="mt-2 text-xs text-muted-foreground">
              Suggested code: {suggestion.suggested_coupon_code}
            </p>
            <Button className="mt-4" variant="secondary" onClick={() => onUse(suggestion)}>
              <CalendarDays />
              Use Idea
            </Button>
          </article>
        ))}
      </div>
    </section>
  );
}

function GstModule({
  pricing,
  saving,
  onChange,
  onSave,
}: {
  pricing: AdminPricing;
  saving: boolean;
  onChange: (value: number) => void;
  onSave: () => void;
}) {
  return (
    <section className="rounded-lg border border-border bg-card p-4">
      <h2 className="font-heading text-lg font-semibold">GST Settings</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        GST stays deterministic. Discounts are managed only through coupon campaigns.
      </p>
      <div className="mt-4 grid gap-3 sm:grid-cols-[220px_auto]">
        <LabeledInput
          label="GST percentage"
          type="number"
          value={pricing.gst_rate_percent}
          onChange={(value) => onChange(Number(value))}
        />
        <div className="flex items-end">
          <Button disabled={saving} onClick={onSave}>
            <Save />
            Save GST
          </Button>
        </div>
      </div>
    </section>
  );
}

function PriceHistorySection({
  rows,
  limit,
  saving,
  search,
  onSearchChange,
  onLimitChange,
  onRefresh,
}: {
  rows: AdminPriceHistoryEntry[];
  limit: number;
  saving: boolean;
  search: string;
  onSearchChange: (search: string) => void;
  onLimitChange: (limit: number) => void;
  onRefresh: () => void;
}) {
  return (
    <section className="rounded-lg border border-border bg-card">
      <div className="flex flex-col justify-between gap-3 border-b border-border p-4 sm:flex-row sm:items-center">
        <div>
          <h2 className="font-heading text-lg font-semibold">Price History</h2>
          <p className="text-xs text-muted-foreground">
            Recent menu price changes with reason and admin attribution.
          </p>
        </div>
        <div className="grid gap-2 sm:grid-cols-[260px_90px_auto]">
          <Input
            placeholder="Search item, code, reason"
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
          />
          <Input
            type="number"
            min={1}
            max={500}
            value={limit}
            onChange={(event) => onLimitChange(Number(event.target.value))}
          />
          <Button variant="secondary" disabled={saving} onClick={onRefresh}>
            <RefreshCw />
            Refresh
          </Button>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[860px] text-left text-sm">
          <thead className="bg-surface-2 text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-4 py-3">Item</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3">Old</th>
              <th className="px-4 py-3">New</th>
              <th className="px-4 py-3">Changed By</th>
              <th className="px-4 py-3">Reason</th>
              <th className="px-4 py-3">Changed At</th>
            </tr>
          </thead>
          <tbody>
            {rows.length ? (
              rows.map((row) => (
                <tr key={row.id} className="border-t border-border">
                  <td className="px-4 py-3">
                    <p className="font-medium">{row.menu_item_name}</p>
                    <p className="text-xs text-muted-foreground">{row.item_code}</p>
                  </td>
                  <td className="px-4 py-3">
                    <Badge>{row.category_name}</Badge>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {row.old_price == null ? "New item" : formatINR(row.old_price)}
                  </td>
                  <td className="px-4 py-3 font-semibold">{formatINR(row.new_price)}</td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {row.changed_by_name ?? "System"}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{row.reason ?? "-"}</td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {new Date(row.changed_at).toLocaleString("en-IN")}
                  </td>
                </tr>
              ))
            ) : (
              <AdminEmptyTableRow
                colSpan={7}
                title="No price changes"
                description="Menu price changes and new item prices will appear here."
              />
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function LabeledInput({
  label,
  value,
  onChange,
  placeholder,
  type = "text",
  title,
  disabled,
}: {
  label: string;
  value: string | number;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
  title?: string;
  disabled?: boolean;
}) {
  return (
    <label className="space-y-2" title={title}>
      <span className="text-sm font-medium">{label}</span>
      <Input
        type={type}
        min={type === "number" ? 0 : undefined}
        placeholder={placeholder}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}
