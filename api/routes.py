"""Shared API routes — the same core/ logic exposed over HTTP.

Both the Gradio app (app.py) and the custom HTML frontend (server.py) mount this
router, so validation, pricing, and persistence are identical everywhere. The
HTML/JS frontend never computes money or trusts client input — it calls these
endpoints; core/ remains the single source of truth.
"""

from __future__ import annotations

import os
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from core import menu as menu_mod
from core import validation as v
from core import pricing, persistence
from core.menu import MenuError

MENU_DIR = os.environ.get("MENU_DIR", "menu_data")
BRAND = "SliceMatic"

router = APIRouter(prefix="/api")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _cat(items):
    return [{"id": i.id, "name": i.name, "price": i.price} for i in items]


def _find(items, _id):
    return next((i for i in items if i.id == _id), None)


def _bill_dict(bill):
    return {
        "base": {"name": bill.base.name, "price": bill.base.price},
        "pizza": {"name": bill.pizza.name, "price": bill.pizza.price},
        "topping": {"name": bill.topping.name, "price": bill.topping.price},
        "quantity": bill.quantity,
        "unit_price": bill.unit_price,
        "subtotal": bill.subtotal,
        "discount": bill.discount,
        "taxable": bill.taxable,
        "gst": bill.gst,
        "total": bill.total,
    }


def _resolve(req):
    """Validate quantity + resolve menu items. Returns (bill, error_dict)."""
    try:
        m = menu_mod.load_menu(MENU_DIR)
    except MenuError as exc:
        return None, {"menu": str(exc)}
    ok_q, qty = v.validate_quantity(req.quantity)
    if not ok_q:
        return None, {"quantity": qty}
    base = _find(m.bases, req.base_id)
    pizza = _find(m.pizzas, req.pizza_id)
    topping = _find(m.toppings, req.topping_id)
    missing = [n for n, val in (("base", base), ("pizza", pizza), ("topping", topping)) if val is None]
    if missing:
        return None, {"selection": f"Please choose a {', '.join(missing)}."}
    return pricing.compute_bill(base, pizza, topping, qty), None


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #

class CustomerReq(BaseModel):
    name: str = ""
    phone: str = ""


class SummaryReq(BaseModel):
    base_id: str = ""
    pizza_id: str = ""
    topping_id: str = ""
    quantity: str | int = ""


class OrderReq(CustomerReq, SummaryReq):
    payment_mode: str = ""


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #

@router.get("/health")
def health():
    return {"status": "ok", "brand": BRAND}


@router.get("/menu")
def get_menu():
    try:
        m = menu_mod.load_menu(MENU_DIR)
    except MenuError as exc:
        return {"error": str(exc)}
    return {"bases": _cat(m.bases), "pizzas": _cat(m.pizzas), "toppings": _cat(m.toppings)}


@router.post("/validate/customer")
def validate_customer(req: CustomerReq):
    ok_n, name = v.validate_name(req.name)
    ok_p, phone = v.validate_phone(req.phone)
    errors = {}
    if not ok_n:
        errors["name"] = name
    if not ok_p:
        errors["phone"] = phone
    return {
        "ok": not errors,
        "errors": errors,
        "name": name if ok_n else None,
        "phone": phone if ok_p else None,
    }


@router.post("/summary")
def summary(req: SummaryReq):
    bill, err = _resolve(req)
    if err:
        return {"ok": False, "errors": err}
    return {"ok": True, "bill": _bill_dict(bill)}


@router.post("/order")
def place_order(req: OrderReq):
    # Re-validate everything server-side — never trust the client.
    ok_n, name = v.validate_name(req.name)
    ok_p, phone = v.validate_phone(req.phone)
    ok_pay, mode = v.validate_payment(req.payment_mode)
    bill, err = _resolve(req)
    errors = dict(err or {})
    if not ok_n:
        errors["name"] = name
    if not ok_p:
        errors["phone"] = phone
    if not ok_pay:
        errors["payment_mode"] = mode
    if errors:
        return {"ok": False, "errors": errors}

    ts = persistence.append_order(name=name, phone=phone, bill=bill, payment_mode=mode)
    order_no = f"SM-{datetime.now().strftime('%Y%m%d')}-{abs(hash((phone, ts))) % 10000:04d}"
    return {
        "ok": True,
        "order_no": order_no,
        "timestamp": ts,
        "payment_mode": mode,
        "name": name,
        "bill": _bill_dict(bill),
    }
