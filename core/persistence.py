"""Append completed orders to database/orders_log.txt in the parseable format.

One order per block, pipe-separated fields within a single line, a blank line
between orders (NFR-4 / FR-8.3). Field order is fixed:

    order_id | timestamp | name | phone | base | pizza | topping |
    unit_price | quantity | subtotal | discount | gst | total | payment_mode
"""

from __future__ import annotations

import os
from datetime import datetime

from core.models import Bill

if os.environ.get("SPACE_ID"):
    LOG_FILE = "/data/orders_log.txt"
else:
    LOG_FILE = os.path.join(os.environ.get("DATABASE_DIR", "database"), "orders_log.txt")
SEP = " | "

FIELD_ORDER = [
    "order_id",
    "timestamp",
    "name",
    "phone",
    "base",
    "pizza",
    "topping",
    "unit_price",
    "quantity",
    "subtotal",
    "discount",
    "gst",
    "total",
    "payment_mode",
]


def _order_number(order_id: str) -> int | None:
    if not order_id.startswith("SM-"):
        return None
    number = order_id[3:]
    return int(number) if number.isdigit() else None


def next_order_id(path: str = LOG_FILE) -> str:
    """Return the next sequential order id, accounting for old logs."""
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        return "SM-000001"

    max_seen = 0
    legacy_records = 0
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            parts = line.split(SEP)
            if len(parts) == len(FIELD_ORDER):
                parsed = _order_number(parts[0].strip())
                if parsed:
                    max_seen = max(max_seen, parsed)
            else:
                legacy_records += 1
    return f"SM-{max(max_seen, legacy_records) + 1:06d}"


def format_order_line(
    *,
    order_id: str,
    timestamp: str,
    name: str,
    phone: str,
    bill: Bill,
    payment_mode: str,
) -> str:
    """Build the single pipe-separated line for one order."""
    fields = [
        order_id,
        timestamp,
        name,
        phone,
        bill.base.name,
        bill.pizza.name,
        bill.topping.name,
        f"{bill.unit_price:.2f}",
        str(bill.quantity),
        f"{bill.subtotal:.2f}",
        f"{bill.discount:.2f}",
        f"{bill.gst:.2f}",
        f"{bill.total:.2f}",
        payment_mode,
    ]
    # Defensive: never let a stray separator corrupt the record.
    fields = [str(f).replace("|", "/").replace("\n", " ").strip() for f in fields]
    return SEP.join(fields)


def append_order(
    *,
    name: str,
    phone: str,
    bill: Bill,
    payment_mode: str,
    timestamp: str | None = None,
    order_id: str | None = None,
    path: str = LOG_FILE,
) -> tuple[str, str]:
    """Append one completed order block. Returns ``(timestamp, order_id)``."""
    timestamp = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    order_id = order_id or next_order_id(path)
    line = format_order_line(
        order_id=order_id,
        timestamp=timestamp,
        name=name,
        phone=phone,
        bill=bill,
        payment_mode=payment_mode,
    )
    # One order per block + a blank line between orders.
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    needs_gap = os.path.isfile(path) and os.path.getsize(path) > 0
    with open(path, "a", encoding="utf-8") as fh:
        if needs_gap:
            fh.write("\n")
        fh.write(line + "\n")
    return timestamp, order_id
