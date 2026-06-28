"""Append completed orders to orders_log.txt in the graded, parseable format.

One order per block, pipe-separated fields within a single line, a blank line
between orders (NFR-4 / FR-8.3). Field order is fixed:

    timestamp | name | phone | base | pizza | topping | unit_price |
    quantity | subtotal | discount | gst | total | payment_mode
"""

from __future__ import annotations

import os
from datetime import datetime

from core.models import Bill

if os.environ.get("SPACE_ID"):
    LOG_FILE = "/data/orders_log.txt"
else:
    LOG_FILE = "orders_log.txt"
SEP = " | "

FIELD_ORDER = [
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


def format_order_line(
    *,
    timestamp: str,
    name: str,
    phone: str,
    bill: Bill,
    payment_mode: str,
) -> str:
    """Build the single pipe-separated line for one order."""
    fields = [
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
    path: str = LOG_FILE,
) -> str:
    """Append one completed order block. Returns the timestamp written."""
    timestamp = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = format_order_line(
        timestamp=timestamp,
        name=name,
        phone=phone,
        bill=bill,
        payment_mode=payment_mode,
    )
    # One order per block + a blank line between orders.
    needs_gap = os.path.isfile(path) and os.path.getsize(path) > 0
    with open(path, "a", encoding="utf-8") as fh:
        if needs_gap:
            fh.write("\n")
        fh.write(line + "\n")
    return timestamp
