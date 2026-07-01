"use client";

import { create } from "zustand";

/**
 * Placed-order history for the Orders tab. There is no backend order-status
 * endpoint yet, so status is *simulated* client-side from the elapsed time
 * since placement (see orderStatus below). Persisted to localStorage so the
 * Orders tab survives reloads.
 */

const KEY = "slicematic-orders";

export interface PlacedOrderItem {
  pizza: string;
  base: string;
  toppings: string[];
  quantity: number;
}

export interface PlacedOrder {
  id: string;
  orderNos: string[];
  items: PlacedOrderItem[];
  total: number;
  paymentMode: string; // canonical: "Cash" | "UPI"
  paymentLabel: string; // UI label: "Cash on Delivery" | "Cash at Store" | "UPI"
  address: string;
  placedAt: number; // epoch ms
}

export const ORDER_STEPS = [
  "Received",
  "Preparing",
  "Out for delivery",
  "Delivered",
] as const;

export type OrderStep = (typeof ORDER_STEPS)[number];

/** Simulated status from elapsed minutes — compressed so a demo progresses. */
export function orderStatus(placedAt: number, now: number = Date.now()) {
  const mins = (now - placedAt) / 60000;
  const index = mins < 0.5 ? 0 : mins < 2 ? 1 : mins < 4 ? 2 : 3;
  return { index, step: ORDER_STEPS[index] };
}

function newId() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);
}

interface OrdersState {
  orders: PlacedOrder[];
  hydrated: boolean;
  init: () => void;
  addOrder: (
    order: Omit<PlacedOrder, "id" | "placedAt">
  ) => PlacedOrder;
}

export const useOrdersStore = create<OrdersState>((set, get) => ({
  orders: [],
  hydrated: false,

  init: () => {
    if (get().hydrated) return;
    try {
      const raw = window.localStorage.getItem(KEY);
      const orders = raw ? (JSON.parse(raw) as PlacedOrder[]) : [];
      set({ orders, hydrated: true });
    } catch {
      set({ hydrated: true });
    }
  },

  addOrder: (order) => {
    const placed: PlacedOrder = { ...order, id: newId(), placedAt: Date.now() };
    set((s) => {
      const orders = [placed, ...s.orders];
      try {
        window.localStorage.setItem(KEY, JSON.stringify(orders));
      } catch {
        /* ignore quota errors */
      }
      return { orders };
    });
    return placed;
  },
}));
