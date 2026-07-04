"use client";

import { CheckCircle, ClipboardList, PackagePlus, Plus, Trash2, XCircle } from "lucide-react";
import { useEffect, useState } from "react";

import {
  adjustAdminStock,
  createAdminIngredient,
  createAdminInventoryRequest,
  deleteAdminRecipeMapping,
  decideAdminInventoryRequest,
  getAdminInventory,
  updateAdminIngredient,
  upsertAdminRecipeMapping,
  type AdminIngredient,
  type AdminInventoryRequest,
  type AdminMenuRecipe,
  type AdminRecipeCoverage,
  type AdminStockTransaction,
} from "@/lib/admin-api";
import {
  AdminEmptyState,
  AdminEmptyTableRow,
  AdminError,
  AdminLoading,
  AdminPageHeader,
} from "@/components/admin/admin-table-shell";
import { AdminConfirmDialog } from "@/components/admin/admin-confirm-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | {
      status: "ready";
      ingredients: AdminIngredient[];
      transactions: AdminStockTransaction[];
      requests: AdminInventoryRequest[];
      recipes: AdminMenuRecipe[];
      recipeCoverage: AdminRecipeCoverage;
    };

type InventoryTab = "stock" | "requests" | "recipes" | "moves";

export default function AdminInventoryPage() {
  const [state, setState] = useState<State>({ status: "loading" });
  const [activeTab, setActiveTab] = useState<InventoryTab>("stock");
  const [filters, setFilters] = useState({
    search: "",
    stock: "all" as "all" | "low" | "active" | "inactive",
    request: "all",
    move: "all",
  });

  async function load() {
    setState({ status: "loading" });
    try {
      const data = await getAdminInventory();
      setState({
        status: "ready",
        ingredients: data.inventory.ingredients,
        transactions: data.inventory.transactions,
        requests: data.inventory.requests,
        recipes: data.inventory.recipes,
        recipeCoverage: data.inventory.recipe_coverage,
      });
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof Error ? error.message : "Inventory load failed.",
      });
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (state.status === "loading") return <AdminLoading label="Loading inventory" />;
  if (state.status === "error") {
    return <AdminError message={state.message} onRetry={() => void load()} />;
  }

  const query = filters.search.trim().toLowerCase();
  const filteredIngredients = state.ingredients.filter((ingredient) => {
    const matchesSearch =
      !query ||
      ingredient.name.toLowerCase().includes(query) ||
      ingredient.unit.toLowerCase().includes(query);
    const matchesStock =
      filters.stock === "all" ||
      (filters.stock === "low" && ingredient.is_low_stock) ||
      (filters.stock === "active" && ingredient.is_active) ||
      (filters.stock === "inactive" && !ingredient.is_active);
    return matchesSearch && matchesStock;
  });
  const filteredRequests = state.requests.filter((request) => {
    const matchesSearch =
      !query ||
      request.ingredient_name.toLowerCase().includes(query) ||
      (request.reason ?? "").toLowerCase().includes(query);
    const matchesStatus = filters.request === "all" || request.status === filters.request;
    return matchesSearch && matchesStatus;
  });
  const filteredTransactions = state.transactions.filter((txn) => {
    const matchesSearch =
      !query ||
      txn.ingredient_name.toLowerCase().includes(query) ||
      (txn.reason ?? "").toLowerCase().includes(query);
    const matchesType = filters.move === "all" || txn.transaction_type === filters.move;
    return matchesSearch && matchesType;
  });
  const filteredRecipes = state.recipes.filter((recipe) => {
    return (
      !query ||
      recipe.menu_item_name.toLowerCase().includes(query) ||
      recipe.item_code.toLowerCase().includes(query) ||
      recipe.category_name.toLowerCase().includes(query) ||
      recipe.ingredients.some((ingredient) =>
        ingredient.ingredient_name.toLowerCase().includes(query)
      )
    );
  });

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8">
      <AdminPageHeader
        title="Inventory"
        subtitle="Track ingredient stock, low-stock alerts, stock in, stock out, and wastage."
      />

      <section className="rounded-lg border border-border bg-card p-4">
        <div className="flex gap-2 overflow-x-auto">
          <TabButton active={activeTab === "stock"} onClick={() => setActiveTab("stock")}>
            Stock
          </TabButton>
          <TabButton
            active={activeTab === "requests"}
            onClick={() => setActiveTab("requests")}
          >
            Requests
          </TabButton>
          <TabButton active={activeTab === "recipes"} onClick={() => setActiveTab("recipes")}>
            Recipes
          </TabButton>
          <TabButton active={activeTab === "moves"} onClick={() => setActiveTab("moves")}>
            Stock Moves
          </TabButton>
        </div>
      </section>

      <InventoryFilters
        activeTab={activeTab}
        filters={filters}
        onChange={setFilters}
      />

      {activeTab === "stock" ? (
        <>
          <IngredientCreateBox onCreated={load} />
          <div className="overflow-hidden rounded-lg border border-border bg-card">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-surface-2 text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">Ingredient</th>
                  <th className="px-4 py-3">Stock</th>
                  <th className="px-4 py-3">Threshold</th>
                  <th className="px-4 py-3">Adjust</th>
                </tr>
              </thead>
              <tbody>
                {filteredIngredients.length ? (
                  filteredIngredients.map((ingredient) => (
                    <InventoryRow
                      key={ingredient.id}
                      ingredient={ingredient}
                      onUpdated={load}
                    />
                  ))
                ) : (
                  <AdminEmptyTableRow
                    colSpan={4}
                    title="No ingredients"
                    description="Create ingredients before mapping recipes or tracking stock movements."
                  />
                )}
              </tbody>
            </table>
          </div>
        </div>
        </>
      ) : null}

      {activeTab === "requests" ? (
        <>
          <InventoryRequestBox ingredients={state.ingredients} onCreated={load} />
          <InventoryRequestQueue requests={filteredRequests} onDecided={load} />
        </>
      ) : null}

      {activeTab === "recipes" ? (
        <RecipeMappingPanel
          recipes={filteredRecipes}
          ingredients={state.ingredients}
          coverage={state.recipeCoverage}
          onUpdated={load}
        />
      ) : null}

      {activeTab === "moves" ? (
        <StockMovesPanel transactions={filteredTransactions} />
      ) : null}
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

function InventoryFilters({
  activeTab,
  filters,
  onChange,
}: {
  activeTab: InventoryTab;
  filters: {
    search: string;
    stock: "all" | "low" | "active" | "inactive";
    request: string;
    move: string;
  };
  onChange: (filters: {
    search: string;
    stock: "all" | "low" | "active" | "inactive";
    request: string;
    move: string;
  }) => void;
}) {
  return (
    <section className="rounded-lg border border-border bg-card p-4">
      <div className="grid gap-3 lg:grid-cols-[1fr_180px]">
        <Input
          placeholder="Search ingredient, recipe, request, or reason"
          value={filters.search}
          onChange={(event) => onChange({ ...filters, search: event.target.value })}
        />
        {activeTab === "stock" ? (
          <select
            className="h-11 rounded-lg border border-border bg-surface-2 px-3 text-sm"
            value={filters.stock}
            onChange={(event) =>
              onChange({
                ...filters,
                stock: event.target.value as typeof filters.stock,
              })
            }
          >
            <option value="all">All stock</option>
            <option value="low">Low stock</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        ) : null}
        {activeTab === "requests" ? (
          <select
            className="h-11 rounded-lg border border-border bg-surface-2 px-3 text-sm"
            value={filters.request}
            onChange={(event) => onChange({ ...filters, request: event.target.value })}
          >
            <option value="all">All requests</option>
            <option value="Requested">Requested</option>
            <option value="Approved">Approved</option>
            <option value="Rejected">Rejected</option>
          </select>
        ) : null}
        {activeTab === "moves" ? (
          <select
            className="h-11 rounded-lg border border-border bg-surface-2 px-3 text-sm"
            value={filters.move}
            onChange={(event) => onChange({ ...filters, move: event.target.value })}
          >
            <option value="all">All moves</option>
            <option value="StockIn">Stock In</option>
            <option value="StockOut">Stock Out</option>
            <option value="Wastage">Wastage</option>
          </select>
        ) : null}
      </div>
    </section>
  );
}

function StockMovesPanel({ transactions }: { transactions: AdminStockTransaction[] }) {
  return (
    <section className="rounded-lg border border-border bg-card">
      <div className="border-b border-border p-4">
        <h2 className="font-heading text-lg font-semibold">Recent Stock Moves</h2>
      </div>
      <div className="divide-y divide-border">
        {transactions.length ? (
          transactions.map((txn) => (
            <div key={txn.id} className="p-4 text-sm">
              <div className="flex items-center justify-between gap-3">
                <p className="font-medium">{txn.ingredient_name}</p>
                <Badge variant={txn.transaction_type === "StockIn" ? "success" : "default"}>
                  {txn.transaction_type}
                </Badge>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                {txn.old_quantity} to {txn.new_quantity} / {txn.reason ?? "No reason"}
              </p>
            </div>
          ))
        ) : (
          <AdminEmptyState
            title="No stock moves"
            description="Stock in, stock out, wastage, and automatic recipe deductions will appear here."
          />
        )}
      </div>
    </section>
  );
}

function IngredientCreateBox({ onCreated }: { onCreated: () => Promise<void> }) {
  const [draft, setDraft] = useState({
    name: "",
    unit: "kg",
    stock_quantity: 0,
    reorder_threshold: 0,
  });
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      await createAdminIngredient({
        ...draft,
        reason: "Admin ingredient create",
      });
      setDraft({
        name: "",
        unit: "kg",
        stock_quantity: 0,
        reorder_threshold: 0,
      });
      await onCreated();
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="rounded-lg border border-border bg-card p-4">
      <h2 className="font-heading text-lg font-semibold">Create Ingredient</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-[1fr_120px_150px_150px_auto]">
        <Input
          placeholder="Ingredient name"
          value={draft.name}
          onChange={(event) => setDraft({ ...draft, name: event.target.value })}
        />
        <Input
          placeholder="Unit"
          value={draft.unit}
          onChange={(event) => setDraft({ ...draft, unit: event.target.value })}
        />
        <Input
          type="number"
          min={0}
          value={draft.stock_quantity}
          onChange={(event) =>
            setDraft({ ...draft, stock_quantity: Number(event.target.value) })
          }
        />
        <Input
          type="number"
          min={0}
          value={draft.reorder_threshold}
          onChange={(event) =>
            setDraft({ ...draft, reorder_threshold: Number(event.target.value) })
          }
        />
        <Button disabled={!draft.name || saving} onClick={() => void save()}>
          <Plus />
          Add
        </Button>
      </div>
    </section>
  );
}

function RecipeMappingPanel({
  recipes,
  ingredients,
  coverage,
  onUpdated,
}: {
  recipes: AdminMenuRecipe[];
  ingredients: AdminIngredient[];
  coverage: AdminRecipeCoverage;
  onUpdated: () => Promise<void>;
}) {
  const [menuItemId, setMenuItemId] = useState(recipes[0]?.menu_item_id ?? "");
  const [ingredientId, setIngredientId] = useState(ingredients[0]?.id ?? "");
  const [quantity, setQuantity] = useState(1);
  const [saving, setSaving] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<{
    id: string;
    name: string;
    menuItem: string;
  } | null>(null);

  async function save() {
    setSaving(true);
    try {
      await upsertAdminRecipeMapping({
        menu_item_id: menuItemId,
        ingredient_id: ingredientId,
        quantity_per_unit: quantity,
        reason: "Admin recipe mapping update",
      });
      await onUpdated();
    } finally {
      setSaving(false);
      setPendingDelete(null);
    }
  }

  async function remove(recipeId: string) {
    setSaving(true);
    try {
      await deleteAdminRecipeMapping(recipeId);
      await onUpdated();
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="rounded-lg border border-border bg-card">
      <div className="flex flex-col justify-between gap-3 border-b border-border p-4 md:flex-row md:items-center">
        <div>
          <h2 className="font-heading text-lg font-semibold">Recipe Mapping</h2>
          <p className="text-xs text-muted-foreground">
            {coverage.mapped_menu_items}/{coverage.total_menu_items} mapped /{" "}
            {coverage.coverage_percent}% coverage
          </p>
        </div>
        <Badge variant={coverage.unmapped_menu_items ? "destructive" : "success"}>
          {coverage.unmapped_menu_items} unmapped
        </Badge>
      </div>
      <div className="grid gap-3 p-4 md:grid-cols-[1fr_1fr_120px_auto]">
        <select
          className="h-11 rounded-lg border border-border bg-surface-2 px-3 text-sm"
          value={menuItemId}
          onChange={(event) => setMenuItemId(event.target.value)}
        >
          {recipes.map((recipe) => (
            <option key={recipe.menu_item_id} value={recipe.menu_item_id}>
              {recipe.item_code} - {recipe.menu_item_name}
            </option>
          ))}
        </select>
        <select
          className="h-11 rounded-lg border border-border bg-surface-2 px-3 text-sm"
          value={ingredientId}
          onChange={(event) => setIngredientId(event.target.value)}
        >
          {ingredients.map((ingredient) => (
            <option key={ingredient.id} value={ingredient.id}>
              {ingredient.name} ({ingredient.unit})
            </option>
          ))}
        </select>
        <Input
          type="number"
          min={0.001}
          step={0.001}
          value={quantity}
          onChange={(event) => setQuantity(Number(event.target.value))}
        />
        <Button disabled={!menuItemId || !ingredientId || saving} onClick={() => void save()}>
          <Plus />
          Map
        </Button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[860px] text-left text-sm">
          <thead className="bg-surface-2 text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-4 py-3">Menu Item</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3">Ingredients Per Unit</th>
            </tr>
          </thead>
          <tbody>
            {recipes.length ? (
              recipes.map((recipe) => (
                <tr key={recipe.menu_item_id} className="border-t border-border align-top">
                  <td className="px-4 py-3 font-medium">
                    {recipe.item_code} - {recipe.menu_item_name}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {recipe.category_name}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      {recipe.ingredients.length ? (
                        recipe.ingredients.map((ingredient) => (
                          <span
                            key={ingredient.id}
                            className="inline-flex items-center gap-2 rounded-full border border-border px-3 py-1 text-xs"
                          >
                            {ingredient.ingredient_name}: {ingredient.quantity_per_unit}{" "}
                            {ingredient.unit}
                            <button
                              aria-label={`Remove ${ingredient.ingredient_name}`}
                              className="text-destructive"
                              disabled={saving}
                              onClick={() =>
                                setPendingDelete({
                                  id: ingredient.id,
                                  name: ingredient.ingredient_name,
                                  menuItem: recipe.menu_item_name,
                                })
                              }
                            >
                              <Trash2 className="size-3.5" />
                            </button>
                          </span>
                        ))
                      ) : (
                        <span className="text-xs text-muted-foreground">
                          No recipe mapped
                        </span>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            ) : (
              <AdminEmptyTableRow
                colSpan={3}
                title="No menu recipes"
                description="Create menu items first, then map ingredients for automatic stock deduction."
              />
            )}
          </tbody>
        </table>
      </div>
      <AdminConfirmDialog
        open={Boolean(pendingDelete)}
        title="Remove recipe ingredient?"
        description={
          pendingDelete
            ? `${pendingDelete.name} will no longer be auto-deducted when ${pendingDelete.menuItem} is prepared.`
            : ""
        }
        confirmLabel="Remove"
        busy={saving}
        onCancel={() => setPendingDelete(null)}
        onConfirm={() => {
          if (pendingDelete) void remove(pendingDelete.id);
        }}
      />
    </section>
  );
}

function InventoryRequestBox({
  ingredients,
  onCreated,
}: {
  ingredients: AdminIngredient[];
  onCreated: () => Promise<void>;
}) {
  const [ingredientId, setIngredientId] = useState(ingredients[0]?.id ?? "");
  const [quantity, setQuantity] = useState(1);
  const [reason, setReason] = useState("Stock replenishment request");
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      await createAdminInventoryRequest({
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
      <h2 className="font-heading text-lg font-semibold">Create Stock Request</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-[1fr_120px_1fr_auto]">
        <select
          className="h-11 rounded-lg border border-border bg-surface-2 px-3 text-sm"
          value={ingredientId}
          onChange={(event) => setIngredientId(event.target.value)}
        >
          {ingredients.map((ingredient) => (
            <option key={ingredient.id} value={ingredient.id}>
              {ingredient.name} ({ingredient.unit})
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

function InventoryRequestQueue({
  requests,
  onDecided,
}: {
  requests: AdminInventoryRequest[];
  onDecided: () => Promise<void>;
}) {
  const [saving, setSaving] = useState<string | null>(null);
  const [pendingDecision, setPendingDecision] = useState<{
    request: AdminInventoryRequest;
    status: "Approved" | "Rejected";
  } | null>(null);

  async function decide(requestId: string, status: "Approved" | "Rejected") {
    setSaving(requestId);
    try {
      await decideAdminInventoryRequest(
        requestId,
        status,
        `Stage 3B inventory request ${status.toLowerCase()}`
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
        <h2 className="font-heading text-lg font-semibold">Stock Request Queue</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="bg-surface-2 text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-4 py-3">Ingredient</th>
              <th className="px-4 py-3">Quantity</th>
              <th className="px-4 py-3">Reason</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {requests.length ? (
              requests.map((request) => (
                <tr key={request.id} className="border-t border-border">
                  <td className="px-4 py-3 font-medium">{request.ingredient_name}</td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {request.requested_quantity} {request.unit ?? ""}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {request.reason ?? "No reason"}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={requestVariant(request.status)}>{request.status}</Badge>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {request.status === "Requested" ? (
                      <div className="flex justify-end gap-2">
                        <Button
                          size="sm"
                          variant="secondary"
                          disabled={saving === request.id}
                          onClick={() =>
                            setPendingDecision({ request, status: "Approved" })
                          }
                        >
                          <CheckCircle />
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          disabled={saving === request.id}
                          onClick={() =>
                            setPendingDecision({ request, status: "Rejected" })
                          }
                        >
                          <XCircle />
                          Reject
                        </Button>
                      </div>
                    ) : (
                      <span className="text-xs text-muted-foreground">
                        {request.decided_at ? "Decision recorded" : "Closed"}
                      </span>
                    )}
                  </td>
                </tr>
              ))
            ) : (
              <AdminEmptyTableRow
                colSpan={5}
                title="No stock requests"
                description="Ingredient replenishment requests from Admin or Staff will appear here."
              />
            )}
          </tbody>
        </table>
      </div>
      <AdminConfirmDialog
        open={Boolean(pendingDecision)}
        title="Confirm stock request decision?"
        description={
          pendingDecision
            ? `${pendingDecision.request.ingredient_name} request for ${pendingDecision.request.requested_quantity} ${pendingDecision.request.unit ?? ""} will be marked ${pendingDecision.status}.`
            : ""
        }
        confirmLabel={pendingDecision?.status ?? "Confirm"}
        variant={pendingDecision?.status === "Rejected" ? "destructive" : "secondary"}
        busy={Boolean(pendingDecision && saving === pendingDecision.request.id)}
        onCancel={() => setPendingDecision(null)}
        onConfirm={() => {
          if (pendingDecision) {
            void decide(pendingDecision.request.id, pendingDecision.status);
          }
        }}
      />
    </section>
  );
}

function InventoryRow({
  ingredient,
  onUpdated,
}: {
  ingredient: AdminIngredient;
  onUpdated: () => Promise<void>;
}) {
  const [quantity, setQuantity] = useState(1);
  const [transactionType, setTransactionType] = useState("StockIn");
  const [draft, setDraft] = useState({
    name: ingredient.name,
    unit: ingredient.unit,
    reorder_threshold: ingredient.reorder_threshold,
    is_active: ingredient.is_active,
  });
  const [saving, setSaving] = useState(false);
  const [confirmDeactivate, setConfirmDeactivate] = useState(false);

  async function save() {
    setSaving(true);
    try {
      await adjustAdminStock(
        ingredient.id,
        transactionType,
        quantity,
        `Stage 3A ${transactionType}`
      );
      await onUpdated();
    } finally {
      setSaving(false);
    }
  }

  async function saveDetails() {
    setSaving(true);
    try {
      await updateAdminIngredient(ingredient.id, {
        ...draft,
        reason: "Admin ingredient update",
      });
      await onUpdated();
    } finally {
      setSaving(false);
      setConfirmDeactivate(false);
    }
  }

  function requestSaveDetails() {
    if (ingredient.is_active && !draft.is_active) {
      setConfirmDeactivate(true);
      return;
    }
    void saveDetails();
  }

  return (
    <>
      <tr className={ingredient.is_active ? "border-t border-border" : "border-t border-border opacity-60"}>
      <td className="px-4 py-3">
        <div className="grid min-w-[220px] gap-2">
          <Input
            value={draft.name}
            onChange={(event) => setDraft({ ...draft, name: event.target.value })}
          />
          <Input
            value={draft.unit}
            onChange={(event) => setDraft({ ...draft, unit: event.target.value })}
          />
        </div>
      </td>
      <td className="px-4 py-3">
        <Badge variant={ingredient.is_low_stock ? "destructive" : "success"}>
          {ingredient.stock_quantity}
        </Badge>
      </td>
      <td className="px-4 py-3 text-muted-foreground">
        <Input
          className="w-24"
          type="number"
          min={0}
          value={draft.reorder_threshold}
          onChange={(event) =>
            setDraft({ ...draft, reorder_threshold: Number(event.target.value) })
          }
        />
      </td>
      <td className="px-4 py-3">
        <div className="flex min-w-[420px] flex-wrap items-center gap-2">
          <select
            className="h-10 rounded-lg border border-border bg-surface-2 px-2 text-sm"
            value={transactionType}
            onChange={(event) => setTransactionType(event.target.value)}
          >
            <option value="StockIn">Stock In</option>
            <option value="StockOut">Stock Out</option>
            <option value="Wastage">Wastage</option>
          </select>
          <Input
            className="w-20"
            type="number"
            min={1}
            value={quantity}
            onChange={(event) => setQuantity(Number(event.target.value))}
          />
          <Button size="sm" variant="secondary" disabled={saving} onClick={() => void save()}>
            <PackagePlus />
            Apply
          </Button>
          <Button size="sm" variant="secondary" disabled={saving} onClick={requestSaveDetails}>
            Save
          </Button>
          <button
            className="flex h-9 items-center rounded-lg border border-border px-3 text-sm"
            onClick={() => setDraft({ ...draft, is_active: !draft.is_active })}
          >
            <Badge variant={draft.is_active ? "success" : "destructive"}>
              {draft.is_active ? "Active" : "Inactive"}
            </Badge>
          </button>
        </div>
      </td>
      </tr>
      <tr>
        <td colSpan={4} className="p-0">
          <AdminConfirmDialog
            open={confirmDeactivate}
            title="Deactivate ingredient?"
            description={`${ingredient.name} will be hidden from staff inventory and new recipe mappings until it is reactivated.`}
            confirmLabel="Deactivate"
            busy={saving}
            onCancel={() => setConfirmDeactivate(false)}
            onConfirm={saveDetails}
          />
        </td>
      </tr>
    </>
  );
}

function requestVariant(status: string) {
  if (status === "Approved") return "success";
  if (status === "Rejected") return "destructive";
  return "default";
}
