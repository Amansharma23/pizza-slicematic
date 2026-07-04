"""The pricing engine. The ONLY place money is computed.

Order of operations (PRD FR-5) — do not reorder:
    unit_price = base + pizza + topping
    subtotal   = unit_price * quantity
    discount   = configured discount % of subtotal if quantity meets threshold
    taxable    = subtotal - discount
    gst        = 18% of taxable          (on the post-discount amount)
    total      = taxable + gst
All money values rounded to 2 decimals.
"""

from __future__ import annotations

from core.models import Bill, MenuItem

_discount_threshold = 999999  # legacy auto-discount disabled; use coupons.
_discount_rate = 0.0
_gst_rate = 0.18  # 18%
GST_RATE = 0.18  # Backward-compatible constant for old imports.


def get_discount_rate() -> float:
    return _discount_rate


def set_discount_rate(rate: float):
    global _discount_rate
    rate = float(rate)
    if rate < 0 or rate > 1:
        raise ValueError("Discount rate must be between 0 and 1.")
    _discount_rate = rate


def get_discount_threshold() -> int:
    return _discount_threshold


def set_discount_threshold(threshold: int):
    global _discount_threshold
    threshold = int(threshold)
    if threshold < 1:
        raise ValueError("Discount threshold must be at least 1.")
    _discount_threshold = threshold


def get_gst_rate() -> float:
    return _gst_rate


def set_gst_rate(rate: float):
    global _gst_rate, GST_RATE
    rate = float(rate)
    if rate < 0 or rate > 0.5:
        raise ValueError("GST rate must be between 0 and 0.5.")
    _gst_rate = rate
    GST_RATE = rate


def _money(value: float) -> float:
    return round(value, 2)


def compute_bill(
    base: MenuItem,
    pizza: MenuItem,
    topping: MenuItem,
    quantity: int,
) -> Bill:
    """Compute the itemised bill for one configuration × quantity."""
    unit_price = _money(base.price + pizza.price + topping.price)
    subtotal = _money(unit_price * quantity)
    discount = (
        _money(get_discount_rate() * subtotal)
        if quantity >= get_discount_threshold()
        else 0.0
    )
    taxable = _money(subtotal - discount)
    gst = _money(get_gst_rate() * taxable)
    total = _money(taxable + gst)
    return Bill(
        base=base,
        pizza=pizza,
        topping=topping,
        quantity=quantity,
        unit_price=unit_price,
        subtotal=subtotal,
        discount=discount,
        taxable=taxable,
        gst=gst,
        total=total,
    )
