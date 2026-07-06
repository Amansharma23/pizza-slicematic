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
 * Staff kiosk POS — desktop-wide, touch-first.
 * Three-pane layout:
 *   Left   = category nav + menu grid (persistent while building)
 *   Middle = customization panel (appears when item is tapped)
 *   Right  = order ticket sidebar
 */
export default function StaffPosPage() {
  const { step, menu, menuStatus, menuError, loadMenu, addLine } =
    useStaffPos();
  const [selectedItem, setSelectedItem] = useState<MenuItem | null>(null);

  useEffect(() => {
    void loadMenu();
  }, [loadMenu]);

  // Clear selection when leaving the build step
  useEffect(() => {
    if (step !== "build") setSelectedItem(null);
  }, [step]);

  const handleAdd = (result: PosCustomizationResult) => {
    addLine(result);
    setSelectedItem(null); // back to grid for next item
  };

  // Non-build steps take the full pane
  if (step === "details") {
    return (
      <div className="flex h-full min-h-0">
        <main className="min-w-0 flex-1"><CustomerDetails /></main>
        <div className="w-[340px] shrink-0"><OrderTicket /></div>
      </div>
    );
  }
  if (step === "payment") {
    return (
      <div className="flex h-full min-h-0">
        <main className="min-w-0 flex-1"><PosPayment /></main>
        <div className="w-[340px] shrink-0"><OrderTicket /></div>
      </div>
    );
  }
  if (step === "done") {
    return <div className="flex h-full min-h-0"><main className="min-w-0 flex-1"><PosConfirmation /></main></div>;
  }

  // step === "build" — three-column layout
  if (menuStatus === "loading" || menuStatus === "idle") {
    return (
      <div className="flex h-full min-h-0">
        <main className="min-w-0 flex-1">
          <div className="grid h-full grid-cols-3 gap-4 p-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-56 animate-pulse rounded-xl border border-border bg-surface-2" />
            ))}
          </div>
        </main>
        <div className="w-[340px] shrink-0"><OrderTicket /></div>
      </div>
    );
  }

  if (menuStatus === "error" || !menu) {
    return (
      <div className="flex h-full min-h-0">
        <main className="min-w-0 flex-1 flex flex-col items-center justify-center gap-3 px-8 text-center">
          <UtensilsCrossed className="size-9 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">{menuError ?? "Couldn't load the menu."}</p>
          <button
            onClick={() => void loadMenu()}
            className="cursor-pointer text-sm font-medium text-primary hover:underline"
          >
            Try again
          </button>
        </main>
        <div className="w-[340px] shrink-0"><OrderTicket /></div>
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0">
      {/* Left: Menu grid — always visible while building */}
      <div className={`min-w-0 border-r border-border transition-all duration-300 ${selectedItem ? "w-[52%]" : "flex-1"}`}>
        <PosMenu menu={menu} onSelect={setSelectedItem} selectedId={selectedItem?.id ?? null} />
      </div>

      {/* Middle: Customization panel — slides in when item selected */}
      {selectedItem && (
        <div className="w-[40%] shrink-0 border-r border-border">
          <PosCustomize
            item={selectedItem}
            menu={menu}
            onAdd={handleAdd}
            onBack={() => setSelectedItem(null)}
          />
        </div>
      )}

      {/* Right: Order ticket */}
      <div className="w-[300px] shrink-0">
        <OrderTicket />
      </div>
    </div>
  );
}
