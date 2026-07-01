"""Mirror completed orders into the Supabase `orders` table.

Best-effort parallel write to core/persistence.append_order. A failure here is
logged and swallowed — it must never affect the order flow or the .txt log.
"""

from __future__ import annotations

import logging

from db.client import execute_query, get_client

log = logging.getLogger(__name__)


def mirror_order(
    *,
    name: str,
    phone: str,
    bill,
    payment_mode: str,
    order_no: str,
    timestamp: str,
    source: str = "gradio",
    session_id: str | None = None,
    language: str | None = None,
) -> str | None:
    """Insert one order row mirroring the .txt log. Returns order_no or None."""
    client = get_client()
    if client is None:
        return None
    row = {
        "order_no": order_no,
        "session_id": session_id,
        "source": source,
        "customer_name": name,
        "customer_phone": phone,
        "base_name": bill.base.name,
        "pizza_name": bill.pizza.name,
        "topping_name": bill.topping.name,
        "unit_price": bill.unit_price,
        "quantity": bill.quantity,
        "subtotal": bill.subtotal,
        "discount": bill.discount,
        "gst": bill.gst,
        "total": bill.total,
        "payment_mode": payment_mode,
        "language": language,
        "logged_at": timestamp,
    }
    try:
        execute_query(client.table("orders").insert(row))
        return order_no
    except Exception as exc:
        log.warning("Supabase order mirror failed (order %s): %s", order_no, exc)
        return None


def create_order(
    *,
    user_id: str | None,
    name: str,
    phone: str,
    items: list[dict],
    subtotal: float,
    discount: float,
    gst: float,
    total: float,
    payment_mode: str,
    source: str = "api",
    session_id: str | None = None,
    language: str | None = None,
    status: str = "received",
) -> str:
    """Create ONE order row for an API/frontend cart (DB is the source of truth
    for these — they are NOT written to orders_log.txt).

    One row per checkout; the per-line breakdown lives in `items` (jsonb) and the
    money fields are the cart totals (each line still priced by core/pricing).
    `order_no` is omitted so the DB default generates it (SM-YYYYMMDD-NNNN).
    Unlike the best-effort mirror, this RAISES on failure — the caller must
    surface it, since there is no .txt fallback for API orders.
    """
    client = get_client()
    if client is None:
        raise RuntimeError("Order database is not configured.")
    row = {
        "user_id": user_id,
        "session_id": session_id,
        "source": source,
        "customer_name": name,
        "customer_phone": phone,
        "items": items,
        "subtotal": subtotal,
        "discount": discount,
        "gst": gst,
        "total": total,
        "payment_mode": payment_mode,
        "language": language,
        "status": status,
    }
    resp = execute_query(client.table("orders").insert(row))
    data = getattr(resp, "data", None)
    if not data:
        raise RuntimeError("Order insert returned no row.")
    return data[0].get("order_no")


def list_orders_by_user(user_id: str, limit: int = 50) -> list[dict]:
    """Return a user's orders, newest first. Empty list if the DB is absent."""
    client = get_client()
    if client is None:
        return []
    resp = execute_query(
        client.table("orders")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
    )
    return getattr(resp, "data", None) or []
