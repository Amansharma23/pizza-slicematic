"""Shared API routes — the same core/ logic exposed over HTTP.

The Gradio app (app.py) mounts this router, and the Stage-3 conversational AI
layer reuses the same core/ functions, so validation, pricing, and persistence
are identical everywhere. core/ remains the single source of truth — no caller
computes money or trusts client input.
"""

from __future__ import annotations

import os

from fastapi import APIRouter
from pydantic import BaseModel

from core import analytics
from core import menu as menu_mod
from core import persistence, pricing
from core import validation as v
from core.menu import MenuError
from core.models import MenuItem

# Additive Supabase mirror — optional. The graded path must work without it.
try:
    from db import orders as db_orders
except Exception:
    db_orders = None

MENU_DIR = os.environ.get("MENU_DIR", "menu_data")
if os.environ.get("SPACE_ID"):
    DATABASE_DIR = os.environ.get("DATABASE_DIR", "/data")
else:
    DATABASE_DIR = os.environ.get("DATABASE_DIR", "database")
CUSTOM_MENU_DIR = os.path.join(DATABASE_DIR, "menu")
MENU_SOURCE_FILE = os.path.join(DATABASE_DIR, "menu_source.txt")
BRAND = "SliceMatic"
DEFAULT_MENU_MODE = "Use SliceMatic default menu"
CUSTOM_MENU_MODE = "Upload my own menu files"

router = APIRouter(prefix="/api")

# Additive auth/account routes (/api/auth/*). Guarded import so the graded
# Gradio path still boots even if the auth extras (bcrypt/jwt/DB) are absent.
try:
    from api.auth import router as auth_router

    router.include_router(auth_router)
except Exception:  # pragma: no cover - only without optional deps
    pass


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _cat(items):
    return [{"id": i.id, "name": i.name, "price": i.price} for i in items]


def _find(items, _id):
    return next((i for i in items if i.id == _id), None)


def _menu_file_paths(menu_dir: str) -> dict[str, str]:
    return {
        menu_mod.BASE_FILE: os.path.join(menu_dir, menu_mod.BASE_FILE),
        menu_mod.PIZZA_FILE: os.path.join(menu_dir, menu_mod.PIZZA_FILE),
        menu_mod.TOPPING_FILE: os.path.join(menu_dir, menu_mod.TOPPING_FILE),
    }


def _has_complete_menu_files(menu_dir: str) -> bool:
    return all(os.path.isfile(path) for path in _menu_file_paths(menu_dir).values())


def _load_menu_source() -> str:
    try:
        with open(MENU_SOURCE_FILE, "r", encoding="utf-8") as fh:
            mode = fh.read().strip()
    except OSError:
        return DEFAULT_MENU_MODE
    return mode if mode in {DEFAULT_MENU_MODE, CUSTOM_MENU_MODE} else DEFAULT_MENU_MODE


def _load_active_menu():
    mode = _load_menu_source()
    if mode == CUSTOM_MENU_MODE:
        if not _has_complete_menu_files(CUSTOM_MENU_DIR):
            raise MenuError("No updated menu has been saved yet.")
        return menu_mod.load_menu(CUSTOM_MENU_DIR)
    return menu_mod.load_menu(MENU_DIR)


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
        m = _load_active_menu()
    except MenuError as exc:
        return None, {"menu": str(exc)}
    ok_q, qty = v.validate_quantity(req.quantity)
    if not ok_q:
        return None, {"quantity": qty}
    base = _find(m.bases, req.base_id)
    pizza = _find(m.pizzas, req.pizza_id)
    topping = _find(m.toppings, req.topping_id)
    missing = [
        n
        for n, val in (("base", base), ("pizza", pizza), ("topping", topping))
        if val is None
    ]
    if missing:
        return None, {"selection": f"Please choose a {', '.join(missing)}."}
    return pricing.compute_bill(base, pizza, topping, qty), None


def _combined_topping(toppings: list[MenuItem]) -> MenuItem:
    """Fuse 1..3 resolved toppings into one MenuItem for core.compute_bill.

    Summing the toppings' menu prices is data aggregation of menu-provided
    values — the bill formula (subtotal/discount/GST/total) still lives solely
    in core.pricing. The combined name lands in the single `topping` log field.
    """
    return MenuItem(
        id="+".join(t.id for t in toppings),
        name=" + ".join(t.name for t in toppings),
        price=round(sum(t.price for t in toppings), 2),
    )


def _resolve_cart_line(m, line: CartLineReq):
    """Validate + resolve one multi-topping line. Returns (bill, toppings, err)."""
    ok_q, qty = v.validate_quantity(line.quantity)
    if not ok_q:
        return None, None, {"quantity": qty}
    base = _find(m.bases, line.base_id)
    pizza = _find(m.pizzas, line.pizza_id)
    missing = [n for n, val in (("base", base), ("pizza", pizza)) if val is None]
    if missing:
        return None, None, {"selection": f"Please choose a {', '.join(missing)}."}
    ids = [t for t in (line.topping_ids or []) if t]
    if not ids:
        return None, None, {"toppings": "Pick at least one topping."}
    if len(ids) > MAX_TOPPINGS:
        return None, None, {"toppings": f"Choose up to {MAX_TOPPINGS} toppings."}
    toppings = [_find(m.toppings, tid) for tid in ids]
    if any(t is None for t in toppings):
        return None, None, {"toppings": "One or more toppings are not on the menu."}
    return (
        pricing.compute_bill(base, pizza, _combined_topping(toppings), qty),
        toppings,
        None,
    )


def _cart_line_dict(bill, toppings: list[MenuItem]) -> dict:
    return {
        "base": {"id": bill.base.id, "name": bill.base.name, "price": bill.base.price},
        "pizza": {
            "id": bill.pizza.id,
            "name": bill.pizza.name,
            "price": bill.pizza.price,
        },
        "toppings": [{"id": t.id, "name": t.name, "price": t.price} for t in toppings],
        "quantity": bill.quantity,
        "unit_price": bill.unit_price,
        "subtotal": bill.subtotal,
        "discount": bill.discount,
        "taxable": bill.taxable,
        "gst": bill.gst,
        "total": bill.total,
    }


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


MAX_TOPPINGS = 3


class CartLineReq(BaseModel):
    base_id: str = ""
    pizza_id: str = ""
    topping_ids: list[str] = []
    quantity: str | int = ""


class CartReq(BaseModel):
    lines: list[CartLineReq] = []


class CheckoutReq(BaseModel):
    user_id: str = ""
    name: str = ""
    phone: str = ""
    payment_mode: str = ""
    # Delivery address chosen at checkout (shown on the rider's screen). The
    # frontend requires it for delivery orders; server-side enforcement lands
    # with the authorization step (address then comes from the authed profile).
    address: str = ""
    type: str = "online"
    lines: list[CartLineReq] = []


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
        m = _load_active_menu()
    except MenuError as exc:
        return {"error": str(exc)}
    return {
        "bases": _cat(m.bases),
        "pizzas": _cat(m.pizzas),
        "toppings": _cat(m.toppings),
    }


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

    ts, order_no = persistence.append_order(
        name=name, phone=phone, bill=bill, payment_mode=mode
    )
    if db_orders:  # best-effort mirror; never affects the .txt log above
        db_orders.mirror_order(
            name=name,
            phone=phone,
            bill=bill,
            payment_mode=mode,
            order_no=order_no,
            timestamp=ts,
            source="api",
        )
    return {
        "ok": True,
        "order_no": order_no,
        "timestamp": ts,
        "payment_mode": mode,
        "name": name,
        "bill": _bill_dict(bill),
    }


@router.post("/cart/price")
def price_cart(req: CartReq):
    """Price a multi-line, multi-topping cart. Additive — core is untouched.

    Each line: base + pizza + 1..3 toppings × quantity, priced by
    core.compute_bill via a combined topping. Cart totals are the wrapper-level
    sum of the per-line core results (no money computed client-side)."""
    try:
        m = _load_active_menu()
    except MenuError as exc:
        return {"ok": False, "errors": {"menu": str(exc)}}
    if not req.lines:
        return {"ok": False, "errors": {"lines": "Your order is empty."}}

    out_lines = []
    totals = {
        "subtotal": 0.0,
        "discount": 0.0,
        "taxable": 0.0,
        "gst": 0.0,
        "total": 0.0,
    }
    for idx, line in enumerate(req.lines):
        bill, toppings, err = _resolve_cart_line(m, line)
        if err:
            return {"ok": False, "line_index": idx, "errors": err}
        out_lines.append(_cart_line_dict(bill, toppings))
        for k in totals:
            totals[k] = round(totals[k] + getattr(bill, k), 2)

    return {"ok": True, "lines": out_lines, "cart": totals}


@router.post("/cart/checkout")
def checkout_cart(req: CheckoutReq):
    """Place a multi-line, multi-topping cart through the API.

    API/frontend orders are written to the DB ONLY (NOT orders_log.txt — the
    graded Gradio app owns the .txt). The DB is the source of truth here, so a
    DB failure is surfaced, not swallowed. One order row per cart (line breakdown
    in items jsonb); each line is still priced by core.compute_bill, cart totals
    are the wrapper-level sum. order_no is generated by the DB (SM-YYYYMMDD-NNNN)."""
    try:
        m = _load_active_menu()
    except MenuError as exc:
        return {"ok": False, "errors": {"menu": str(exc)}}

    ok_n, name = v.validate_name(req.name)
    ok_p, phone = v.validate_phone(req.phone)
    ok_pay, mode = v.validate_payment(req.payment_mode)
    errors: dict[str, str] = {}
    if not ok_n:
        errors["name"] = name
    if not ok_p:
        errors["phone"] = phone
    if not ok_pay:
        errors["payment_mode"] = mode
    if not req.lines:
        errors["lines"] = "Your order is empty."

    # Resolve + price every line up front — never write a partial order.
    items, totals = [], {"subtotal": 0.0, "discount": 0.0, "gst": 0.0, "total": 0.0}
    for idx, line in enumerate(req.lines):
        bill, toppings, err = _resolve_cart_line(m, line)
        if err:
            return {"ok": False, "line_index": idx, "errors": err}
        items.append(
            {
                "pizza": bill.pizza.name,
                "base": bill.base.name,
                "toppings": [t.name for t in toppings],
                "quantity": bill.quantity,
                "unit_price": bill.unit_price,
                "line_total": bill.total,
            }
        )
        for k in totals:
            totals[k] = round(totals[k] + getattr(bill, k), 2)

    if errors:
        return {"ok": False, "errors": errors}

    if db_orders is None:
        return {"ok": False, "errors": {"db": "Order database is unavailable."}}
    try:
        order_no = db_orders.create_order(
            user_id=req.user_id or None,
            name=name,
            phone=phone,
            items=items,
            subtotal=totals["subtotal"],
            discount=totals["discount"],
            gst=totals["gst"],
            total=totals["total"],
            payment_mode=mode,
            source="api",
            delivery_address=req.address.strip() or None,
            type=req.type,
        )
    except Exception as exc:  # DB is source of truth — surface the failure
        return {"ok": False, "errors": {"db": f"Could not save the order: {exc}"}}

    return {
        "ok": True,
        "order_no": order_no,
        "total": totals["total"],
        "name": name,
        "payment_mode": mode,
        "line_count": len(items),
    }


@router.get("/orders/recent")
def list_recent_orders(type: str = "", status: str = ""):
    """ALL recent orders (newest first) — the delivery rider's work queue.

    Interim scope: every rider sees every order, per the current requirement;
    per-rider assignment + role enforcement arrive with the authorization step."""
    if db_orders is None:
        return {"ok": False, "errors": {"db": "Order database is unavailable."}}
    try:
        return {
            "ok": True,
            "orders": db_orders.list_recent_orders(
                type=type or None, status=status or None
            ),
        }
    except Exception as exc:
        return {"ok": False, "errors": {"db": str(exc)}}


@router.get("/orders")
def list_orders(user_id: str = "", phone: str = "", type: str = "", status: str = ""):
    """List a user's orders (newest first) from the DB — the API source of truth.

    Filter by phone (interim, until real auth) or user_id; phone wins if both
    are sent. The frontend currently passes the profile's phone."""
    if not user_id and not phone:
        return {"ok": False, "errors": {"filter": "phone or user_id is required."}}
    if db_orders is None:
        return {"ok": False, "errors": {"db": "Order database is unavailable."}}
    try:
        if phone:
            orders = db_orders.list_orders_by_phone(
                phone, type=type or None, status=status or None
            )
        else:
            orders = db_orders.list_orders_by_user(
                user_id, type=type or None, status=status or None
            )
    except Exception as exc:
        return {"ok": False, "errors": {"db": str(exc)}}
    return {"ok": True, "orders": orders}


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
def get_analytics(
    filter_type: str = "All Time",
    start_date: str | None = None,
    end_date: str | None = None,
):
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
