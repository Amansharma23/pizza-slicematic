"use client";

import { CheckCircle2, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useStaffPos } from "@/lib/staff-store";
import { formatINR } from "@/lib/utils";

/**
 * POS step 4 — order placed. Shows the DB-generated order number so staff can
 * call it out / write it on the box, then resets for the next walk-in.
 */
const ORDER_TYPE_LABEL = { dine_in: "Dine In", takeaway: "Takeaway" } as const;

export function PosConfirmation() {
  const { customerName, orderType, placedOrderNo, placedTotal, newOrder } =
    useStaffPos();

  return (
    <div className="flex h-full items-center justify-center px-8">
      <div className="w-full max-w-lg space-y-8 text-center">
        <div className="flex flex-col items-center gap-4">
          <CheckCircle2 className="size-20 text-success" />
          <div>
            <h2 className="font-heading text-3xl font-bold">Order placed</h2>
            <p className="mt-2 text-base text-muted-foreground">
              Sent to the kitchen for {customerName || "the customer"}.
            </p>
          </div>
        </div>

        <div className="space-y-3 rounded-xl border border-border bg-surface-2 p-6">
          <div className="flex items-center justify-between text-base">
            <span className="text-muted-foreground">Order number</span>
            <span className="font-heading text-xl font-bold">
              {placedOrderNo}
            </span>
          </div>
          <div className="flex items-center justify-between border-t border-border pt-3 text-base">
            <span className="text-muted-foreground">Order type</span>
            <span className="font-semibold">{ORDER_TYPE_LABEL[orderType]}</span>
          </div>
          <div className="flex items-center justify-between border-t border-border pt-3 text-base">
            <span className="text-muted-foreground">Amount collected</span>
            <span className="font-heading text-xl font-bold tabular-nums">
              {placedTotal !== null ? formatINR(placedTotal) : "—"}
            </span>
          </div>
        </div>

        <Button size="lg" className="h-14 w-full text-base" onClick={newOrder}>
          <Plus />
          New order
        </Button>
      </div>
    </div>
  );
}
