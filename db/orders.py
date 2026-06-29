"""Mirror completed orders into the Supabase `orders` table.

Best-effort parallel write to core/persistence.append_order. A failure here is
logged and swallowed — it must never affect the order flow or the .txt log.
"""

from __future__ import annotations

import logging

from db.client import get_client

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
        client.table("orders").insert(row).execute()
        return order_no
    except Exception as exc:
        log.warning("Supabase order mirror failed (order %s): %s", order_no, exc)
        return None
