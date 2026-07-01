"use client";

import { CartSheet } from "@/components/menu/cart-sheet";
import { useMenuStore } from "@/lib/menu-store";

/** Hosts the cart sheet at the customer-layout level so the header cart icon
 *  can open it from any screen (chat, menu, orders, profile). */
export function GlobalCart() {
  const cartOpen = useMenuStore((s) => s.cartOpen);
  const openCart = useMenuStore((s) => s.openCart);
  const closeCart = useMenuStore((s) => s.closeCart);

  return (
    <CartSheet
      open={cartOpen}
      onOpenChange={(open) => (open ? openCart() : closeCart())}
    />
  );
}
