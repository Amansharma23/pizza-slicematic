"use client";

import { UtensilsCrossed } from "lucide-react";
import { useEffect, useState } from "react";

import { CustomerDetails } from "@/components/staff/customer-details";
import { OrderTicket } from "@/components/staff/order-ticket";
import { PosConfirmation } from "@/components/staff/pos-confirmation";
import {
  PosCustomize,
  type PosCustomizationResult,
} from "@/components/staff/pos-customize";
import { PosMenu } from "@/components/staff/pos-menu";
import { PosPayment } from "@/components/staff/pos-payment";
import type { MenuItem } from "@/lib/api";
import { useStaffPos } from "@/lib/staff-store";

/**
 * Staff kiosk POS â€” desktop-wide, touch-first. Two panes: the flow pane
 * (details â†’ menu/customize â†’ payment â†’ done) and a persistent order-ticket
 * sidebar. While no order is in progress (the details step), the sidebar
 * shows recent orders instead of an empty state (see order-ticket.tsx +
 * recent-orders.tsx). Flow modelled on the staff POS ordering path;
 * pricing and checkout go through the same /api/cart/* endpoints as the
 * customer app.
 */
export default function StaffPosPage() {
  const { step, menu, menuStatus, menuError, loadMenu, addLine } =
    useStaffPos();
  const [selectedPizza, setSelectedPizza] = useState<MenuItem | null>(null);

  useEffect(() => {
    void loadMenu();
  }, [loadMenu]);

  // Leaving the build step always closes the customize panel.
  useEffect(() => {
    if (step !== "build") setSelectedPizza(null);
  }, [step]);

  const handleAdd = (result: PosCustomizationResult) => {
    addLine(result);
    setSelectedPizza(null); // back to the grid for the next pizza
  };

  const flowPane = () => {
    if (step === "details") return <CustomerDetails />;
    if (step === "payment") return <PosPayment />;
    if (step === "done") return <PosConfirmation />;

    // step === "build" â€” menu grid, or the customize panel for the tapped pizza.
    if (menuStatus === "loading" || menuStatus === "idle") {
      return (
        <div className="grid h-full grid-cols-3 gap-4 p-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-56 animate-pulse rounded-xl border border-border bg-surface-2"
            />
          ))}
        </div>
      );
    }
    if (menuStatus === "error" || !menu) {
      return (
        <div className="flex h-full flex-col items-center justify-center gap-3 px-8 text-center">
          <UtensilsCrossed className="size-9 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            {menuError ?? "Couldn't load the menu."}
          </p>
          <button
            onClick={() => void loadMenu()}
            className="cursor-pointer text-sm font-medium text-primary hover:underline"
          >
            Try again
          </button>
        </div>
      );
    }
    return selectedPizza ? (
      <PosCustomize
        pizza={selectedPizza}
        menu={menu}
        onAdd={handleAdd}
        onBack={() => setSelectedPizza(null)}
      />
    ) : (
      <PosMenu menu={menu} onSelect={setSelectedPizza} />
    );
  };

  return (
    <div className="flex h-full min-h-0">
      <main className="min-w-0 flex-1">{flowPane()}</main>
      {/* Fixed width â€” the kiosk frame is capped at tablet size (max-w-5xl),
          so viewport breakpoints would misfire here. */}
      {step !== "done" && (
        <div className="w-[340px] shrink-0">
          <OrderTicket />
        </div>
      )}
    </div>
  );
}
