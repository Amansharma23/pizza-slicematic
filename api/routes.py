"""Shared API routes — the same core/ logic exposed over HTTP.

Both the Gradio app (app.py) and the custom HTML frontend (server.py) mount this
router, so validation, pricing, and persistence are identical everywhere. The
HTML/JS frontend never computes money or trusts client input — it calls these
endpoints; core/ remains the single source of truth.
"""

from __future__ import annotations

import os

from fastapi import APIRouter
from pydantic import BaseModel

from core import menu as menu_mod
from core import validation as v
from core import pricing, persistence, analytics
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


class ConfigReq(BaseModel):
    discount_rate: float
    discount_threshold: int = 5


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

    ts, order_no = persistence.append_order(name=name, phone=phone, bill=bill, payment_mode=mode)
    return {
        "ok": True,
        "order_no": order_no,
        "timestamp": ts,
        "payment_mode": mode,
        "name": name,
        "bill": _bill_dict(bill),
    }


@router.get("/config")
def get_config():
    return {
        "discount_rate": pricing.get_discount_rate(),
        "discount_threshold": pricing.get_discount_threshold(),
    }


@router.post("/config")
def update_config(req: ConfigReq):
    pricing.set_discount_rate(req.discount_rate)
    pricing.set_discount_threshold(req.discount_threshold)
    return {
        "ok": True,
        "discount_rate": pricing.get_discount_rate(),
        "discount_threshold": pricing.get_discount_threshold(),
    }


@router.get("/analytics")
def get_analytics(filter_type: str = "All Time", start_date: str | None = None, end_date: str | None = None):
    data = analytics.get_analytics(filter_type, start_date, end_date)
    # Convert pandas DataFrames to dicts for JSON serialization
    return {
        "total_orders": data["total_orders"],
        "total_qty": data["total_qty"],
        "revenue": data["revenue"],
        "gst": data["gst"],
        "discount": data["discount"],
        "top_bases": data["top_bases"].to_dict(orient="records"),
        "top_pizzas": data["top_pizzas"].to_dict(orient="records"),
        "top_toppings": data["top_toppings"].to_dict(orient="records"),
        "top_combos": data["top_combos"].to_dict(orient="records"),
        "orders_df": data["orders_df"].to_dict(orient="records"),
    }
