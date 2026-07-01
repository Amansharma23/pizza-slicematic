"use client";

import { create } from "zustand";

import { getUserOrders, type UserOrder } from "@/lib/api";

/**
 * Orders for the Orders tab, loaded from the DB (source of truth for API
 * orders) via GET /api/orders?user_id=. There is no backend order-status yet,
 * so the status shown is *simulated* client-side from `created_at` (see
 * orderStatus). Refetched on tab mount.
 */

export const ORDER_STEPS = [
  "Received",
  "Preparing",
  "Out for delivery",
  "Delivered",
] as const;

export type OrderStep = (typeof ORDER_STEPS)[number];

/** Simulated status from elapsed minutes — compressed so a demo progresses. */
export function orderStatus(placedAtMs: number, now: number = Date.now()) {
  const mins = (now - placedAtMs) / 60000;
  const index = mins < 0.5 ? 0 : mins < 2 ? 1 : mins < 4 ? 2 : 3;
  return { index, step: ORDER_STEPS[index] };
}

interface OrdersState {
  orders: UserOrder[];
  loading: boolean;
  error: string | null;
  load: (userId: string) => Promise<void>;
}

export const useOrdersStore = create<OrdersState>((set) => ({
  orders: [],
  loading: false,
  error: null,

  load: async (userId: string) => {
    set({ loading: true, error: null });
    try {
      const res = await getUserOrders(userId);
      if (res.ok && res.orders) {
        set({ orders: res.orders, loading: false });
      } else {
        const msg = res.errors ? Object.values(res.errors)[0] : null;
        set({ loading: false, error: msg ?? "Couldn't load your orders." });
      }
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : "Couldn't load your orders.",
      });
    }
  },
}));
