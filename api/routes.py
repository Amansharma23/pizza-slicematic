"""Shared API routes exposed over HTTP.

The Stage 3 FastAPI app mounts this router, so validation, pricing, and
persistence stay centralized. core/ remains the single source of truth; no
caller computes money or trusts client input.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api import security
from core import analytics
from core import menu as menu_mod
from core import persistence, pricing
from core import validation as v
from core.menu import MenuError
from core.models import MenuItem

# Optional database layer. Public menu/pricing routes still import in reduced
# local environments, while checkout surfaces database setup problems clearly.
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

# Auth/account routes (/api/auth/*). Guarded import keeps public API routes
# usable in reduced local environments if auth extras are absent.
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


_cached_menu = None
_cached_version = None

def _load_active_menu():
    global _cached_menu, _cached_version
    from db import postgres as local_postgres
    from core.models import Menu, MenuItem

    current_version = 1
    if local_postgres.is_enabled():
        from db import postgres
        try:
            with postgres.connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("select value from public.app_settings where id = 'menu_version'")
                    row = cur.fetchone()
                    if row:
                        current_version = int(row[0].get("value", 1))
                    else:
                        cur.execute(
                            "insert into public.app_settings (id, value, updated_at) values ('menu_version', '{\"value\": 1}', now())"
                        )
                        current_version = 1
        except Exception:
            current_version = 1
    else:
        from db import client
        client_instance = client.get_client()
        if client_instance is not None:
            try:
                resp = client.execute_query(
                    client_instance.table("app_settings").select("value").eq("id", "menu_version").limit(1)
                )
                rows = getattr(resp, "data", None) or []
                if rows:
                    current_version = int(rows[0].get("value", {}).get("value", 1))
                else:
                    client.execute_query(
                        client_instance.table("app_settings").insert({"id": "menu_version", "value": {"value": 1}})
                    )
                    current_version = 1
            except Exception:
                current_version = 1

    if _cached_menu is not None and _cached_version == current_version:
        return _cached_menu

    bases = []
    pizzas = []
    toppings = []
    
    if local_postgres.is_enabled():
        from db import postgres
        try:
            with postgres.connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        select i.item_code, i.name, i.price, c.code
                        from public.menu_items i
                        join public.menu_categories c on i.category_id = c.id
                        where i.is_available = true and i.is_deleted = false
                        """
                    )
                    rows = cur.fetchall()
                    for item_code, name, price, cat_code in rows:
                        item = MenuItem(id=item_code, name=name, price=float(price))
                        if cat_code == "base":
                            bases.append(item)
                        elif cat_code == "pizza":
                            pizzas.append(item)
                        elif cat_code == "topping":
                            toppings.append(item)
        except Exception:
            pass
    else:
        from db import client
        client_instance = client.get_client()
        if client_instance is not None:
            try:
                resp_cats = client.execute_query(client_instance.table("menu_categories").select("*"))
                cats = getattr(resp_cats, "data", None) or []
                cat_map = {c["id"]: c["code"] for c in cats}
                
                resp_items = client.execute_query(
                    client_instance.table("menu_items")
                    .select("*")
                    .eq("is_available", True)
                    .eq("is_deleted", False)
                )
                items = getattr(resp_items, "data", None) or []
                for item in items:
                    cat_code = cat_map.get(item["category_id"])
                    m_item = MenuItem(id=item["item_code"], name=item["name"], price=float(item["price"]))
                    if cat_code == "base":
                        bases.append(m_item)
                    elif cat_code == "pizza":
                        pizzas.append(m_item)
                    elif cat_code == "topping":
                        toppings.append(m_item)
            except Exception:
                pass

    if not bases or not pizzas or not toppings:
        mode = _load_menu_source()
        fallback_menu = None
        if mode == CUSTOM_MENU_MODE:
            if _has_complete_menu_files(CUSTOM_MENU_DIR):
                fallback_menu = menu_mod.load_menu(CUSTOM_MENU_DIR)
        if fallback_menu is None:
            fallback_menu = menu_mod.load_menu(MENU_DIR)
        _cached_menu = fallback_menu
        _cached_version = current_version
        return _cached_menu

    _cached_menu = Menu(bases=bases, pizzas=pizzas, toppings=toppings)
    _cached_version = current_version
    return _cached_menu


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
    values â€” the bill formula (subtotal/discount/GST/total) still lives solely
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


def _cart_line_numbers(bill, cart_qualifies: bool) -> dict:
    """Money fields for one cart line under the CART-level bulk-discount rule.

    For API carts the discount applies when the TOTAL quantity across lines
    meets the threshold (decided 2026-07-04), while core.compute_bill only
    knows one line. Lines core already discounted (their own qty qualifies)
    keep core's numbers unchanged; the remaining lines of a qualifying cart
    get the identical formula re-applied here using core's own rate/GST
    constants in core's exact order (discount -> taxable -> GST -> total).
    A non-qualifying cart can't contain a qualifying line, so it always
    passes through core's numbers untouched.
    """
    if not cart_qualifies or bill.discount > 0:
        return {
            "subtotal": bill.subtotal,
            "discount": bill.discount,
            "taxable": bill.taxable,
            "gst": bill.gst,
            "total": bill.total,
        }
    discount = round(pricing.get_discount_rate() * bill.subtotal, 2)
    taxable = round(bill.subtotal - discount, 2)
    gst = round(pricing.GST_RATE * taxable, 2)
    return {
        "subtotal": bill.subtotal,
        "discount": discount,
        "taxable": taxable,
        "gst": gst,
        "total": round(taxable + gst, 2),
    }


def _cart_line_dict(bill, toppings: list[MenuItem], nums: dict) -> dict:
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
        **nums,
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


# The only three order channels: "online" (customer app, the default),
# "dine_in"/"takeaway" (staff kiosk â€” see pos-payment.tsx). Enforced below in
# checkout_cart, not as a Pydantic Literal, so a bad value comes back as a
# normal {"ok": false, "errors": {...}} business error like every other field
# here, instead of a raw FastAPI 422.
_VALID_ORDER_TYPES = {"online", "dine_in", "takeaway"}


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
    coupon_code: str = ""


class ConfigReq(BaseModel):
    discount_rate: float
    discount_threshold: int = 5
    gst_rate: float | None = None


class OrderStatusReq(BaseModel):
    status: str


# Kitchen advances received->preparing->ready_for_pickup; delivery advances
# ready_for_pickup->out_for_delivery->delivered. Both share one endpoint (the
# sequence itself is enforced by db/orders.py's state machine), but the
# sequence check alone doesn't stop kitchen from also setting delivery's
# statuses (or vice versa) â€” e.g. a kitchen token can legally advance
# ready_for_pickup -> out_for_delivery since that IS the correct next step,
# just not kitchen's job. This maps each role to the statuses it may actually
# set; admin may set any of them.
_ROLE_ALLOWED_STATUSES = {
    "kitchen_staff": {"preparing", "ready_for_pickup"},
    "delivery": {"out_for_delivery", "delivered"},
}
_kitchen_or_delivery = Depends(
    security.require_role("kitchen_staff", "delivery", "admin")
)
_delivery = Depends(security.require_role("delivery", "admin"))


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
    # Re-validate everything server-side â€” never trust the client.
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


# --------------------------------------------------------------------------- #
# Coupon routes
# --------------------------------------------------------------------------- #


class CouponValidateReq(BaseModel):
    code: str = ""
    cart_total: float = 0.0


@router.get("/coupons/available")
def list_available_coupons():
    """Return all active coupons valid today — for the coupon picker popup in checkout."""
    from db import postgres as local_postgres
    if not local_postgres.is_enabled():
        return {"ok": True, "coupons": []}
    try:
        with local_postgres.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    select id, name, coupon_code, description,
                           discount_percent, threshold_amount,
                           start_date, end_date
                    from public.discount_rules
                    where is_active = true
                      and coupon_code is not null
                      and (start_date is null or start_date <= current_date)
                      and (end_date is null or end_date >= current_date)
                    order by discount_percent desc, name
                """)
                cols = [d.name for d in cur.description]
                rows = []
                for row in cur.fetchall():
                    r = dict(zip(cols, row))
                    from decimal import Decimal
                    from datetime import date as _d
                    rows.append({
                        k: (float(v) if isinstance(v, Decimal) else
                            v.isoformat() if isinstance(v, _d) else v)
                        for k, v in r.items()
                    })
        return {"ok": True, "coupons": rows}
    except Exception as exc:
        return {"ok": False, "errors": {"db": str(exc)}, "coupons": []}


@router.post("/coupons/validate")
def validate_coupon_code(req: CouponValidateReq):
    """Validate a coupon code against the current cart total. All checks server-side.

    Returns the discount amount and new total if valid; error message if not.
    The client only renders — money is computed here, never client-side.
    """
    code = req.code.strip().upper()
    if not code:
        return {"ok": False, "errors": {"code": "Please enter a coupon code."}}

    from db import postgres as local_postgres
    if not local_postgres.is_enabled():
        return {"ok": False, "errors": {"db": "Database unavailable."}}

    try:
        with local_postgres.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    select id, name, coupon_code, description,
                           discount_percent, threshold_amount,
                           start_date, end_date, is_active
                    from public.discount_rules
                    where upper(coupon_code) = %s
                    limit 1
                """, (code,))
                cols = [d.name for d in cur.description]
                row = cur.fetchone()
    except Exception as exc:
        return {"ok": False, "errors": {"db": str(exc)}}

    if not row:
        return {"ok": False, "errors": {"code": f"Coupon '{code}' not found."}}

    from decimal import Decimal
    from datetime import date as _d2
    rule = dict(zip(cols, row))
    rule = {k: (float(v) if isinstance(v, Decimal) else v) for k, v in rule.items()}

    if not rule.get("is_active"):
        return {"ok": False, "errors": {"code": "This coupon is no longer active."}}

    today = _d2.today()
    start = rule.get("start_date")
    end = rule.get("end_date")
    if start and today < start:
        return {"ok": False, "errors": {"code": f"Coupon valid from {start}."}}
    if end and today > end:
        return {"ok": False, "errors": {"code": "This coupon has expired."}}

    threshold = float(rule.get("threshold_amount") or 0)
    if threshold > 0 and req.cart_total < threshold:
        return {
            "ok": False,
            "errors": {
                "code": (
                    f"Minimum order \u20b9{threshold:.0f} required "
                    f"(cart: \u20b9{req.cart_total:.0f})."
                )
            },
        }

    discount_pct = float(rule.get("discount_percent") or 0)
    # Coupon reduces the pre-GST subtotal; GST is re-applied after the discount.
    gst_rate = 0.18
    subtotal = round(req.cart_total / (1 + gst_rate), 2)
    discount_amount = round(subtotal * discount_pct / 100.0, 2)
    new_subtotal = round(subtotal - discount_amount, 2)
    new_gst = round(new_subtotal * gst_rate, 2)
    new_total = round(new_subtotal + new_gst, 2)

    return {
        "ok": True,
        "coupon_code": rule["coupon_code"],
        "coupon_name": rule["name"],
        "description": rule.get("description"),
        "discount_percent": discount_pct,
        "discount_amount": discount_amount,
        "original_total": req.cart_total,
        "new_total": new_total,
        "savings": round(req.cart_total - new_total, 2),
    }


@router.post("/cart/price")
def price_cart(req: CartReq):
    """Price a multi-line, multi-topping cart. Additive â€” core is untouched.

    Each line: base + pizza + 1..3 toppings Ã— quantity, priced by
    core.compute_bill via a combined topping. Cart totals are the wrapper-level
    sum of the per-line core results (no money computed client-side)."""
    try:
        m = _load_active_menu()
    except MenuError as exc:
        return {"ok": False, "errors": {"menu": str(exc)}}
    if not req.lines:
        return {"ok": False, "errors": {"lines": "Your order is empty."}}

    # Pass 1: resolve every line so the discount can consider the WHOLE cart.
    resolved = []
    for idx, line in enumerate(req.lines):
        bill, toppings, err = _resolve_cart_line(m, line)
        if err:
            return {"ok": False, "line_index": idx, "errors": err}
        resolved.append((bill, toppings))

    # Cart-level bulk discount: total pizzas across lines vs the threshold.
    total_qty = sum(bill.quantity for bill, _ in resolved)
    cart_qualifies = total_qty >= pricing.get_discount_threshold()

    out_lines = []
    totals = {
        "subtotal": 0.0,
        "discount": 0.0,
        "taxable": 0.0,
        "gst": 0.0,
        "total": 0.0,
    }
    for bill, toppings in resolved:
        nums = _cart_line_numbers(bill, cart_qualifies)
        out_lines.append(_cart_line_dict(bill, toppings, nums))
        for k in totals:
            totals[k] = round(totals[k] + nums[k], 2)

    return {"ok": True, "lines": out_lines, "cart": totals}


def _fetch_order_by_no(order_no: str) -> dict | None:
    from db import postgres as local_postgres
    if local_postgres.is_enabled():
        with local_postgres.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("select * from public.orders where order_no = %s", (order_no,))
                cols = [desc.name for desc in cur.description]
                row = cur.fetchone()
                if row:
                    return local_postgres._serialize(dict(zip(cols, row)))
    else:
        from db import client
        client_instance = client.get_client()
        if client_instance is not None:
            resp = client.execute_query(
                client_instance.table("orders").select("*").eq("order_no", order_no).limit(1)
            )
            rows = getattr(resp, "data", None) or []
            if rows:
                return rows[0]
    return None


@router.post("/cart/checkout")
def checkout_cart(req: CheckoutReq):
    """Place a multi-line, multi-topping cart through the API.

    API/frontend orders are written to the DB only, not orders_log.txt. The DB is the source of truth here, so a
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
    if req.type not in _VALID_ORDER_TYPES:
        errors["type"] = (
            f"Order type must be one of: {', '.join(sorted(_VALID_ORDER_TYPES))}."
        )
    if not req.lines:
        errors["lines"] = "Your order is empty."

    # Resolve + price every line up front â€” never write a partial order.
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

    if req.coupon_code:
        coupon_err = None
        code = req.coupon_code.strip().upper()
        from db import postgres as local_postgres
        if local_postgres.is_enabled():
            try:
                with local_postgres.connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            select discount_percent, threshold_amount, start_date, end_date, is_active
                            from public.discount_rules where upper(coupon_code) = %s limit 1
                        """, (code,))
                        row = cur.fetchone()
                if not row:
                    coupon_err = f"Coupon '{code}' not found."
                else:
                    d_pct, t_amt, s_date, e_date, is_act = row
                    from datetime import date as _d2
                    today = _d2.today()
                    if not is_act:
                        coupon_err = "This coupon is no longer active."
                    elif s_date and today < s_date:
                        coupon_err = f"Coupon valid from {s_date}."
                    elif e_date and today > e_date:
                        coupon_err = "This coupon has expired."
                    elif t_amt and t_amt > 0 and totals["total"] < t_amt:
                        coupon_err = f"Minimum order \u20b9{float(t_amt):.0f} required."
                    else:
                        gst_rate = 0.18
                        # Replace bulk discount with coupon discount
                        subtotal = totals["subtotal"]
                        discount_amount = round(subtotal * float(d_pct) / 100.0, 2)
                        new_subtotal = round(subtotal - discount_amount, 2)
                        new_gst = round(new_subtotal * gst_rate, 2)
                        new_total = round(new_subtotal + new_gst, 2)
                        totals["discount"] = discount_amount
                        totals["gst"] = new_gst
                        totals["total"] = new_total
            except Exception as exc:
                coupon_err = f"Coupon check failed: {exc}"
        if coupon_err:
            return {"ok": False, "errors": {"coupon_code": coupon_err}}

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
        try:
            full_order = _fetch_order_by_no(order_no)
            if full_order:
                from ai.realtime import broadcast_event
                broadcast_event("order_created", full_order)
        except Exception as ws_exc:
            import logging
            logging.getLogger(__name__).warning("Failed to broadcast order_created: %s", ws_exc)
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
    """ALL recent orders (newest first) â€” the delivery rider's work queue.

    Interim scope: every rider sees every order, per the current requirement;
    per-rider assignment + role enforcement arrive with the authorization step."""
    if db_orders is None:
        return {"ok": False, "errors": {"db": "Order database is unavailable."}}
    try:
        return {
            "ok": True,
            "orders": db_orders.list_recent_orders(
                order_type=type or None, status=status or None
            ),
        }
    except Exception as exc:
        return {"ok": False, "errors": {"db": str(exc)}}


@router.get("/orders")
def list_orders(user_id: str = "", phone: str = "", type: str = "", status: str = ""):
    """List a user's orders (newest first) from the DB â€” the API source of truth.

    Filter by phone (interim, until real auth) or user_id; phone wins if both
    are sent. The frontend currently passes the profile's phone."""
    if not user_id and not phone:
        return {"ok": False, "errors": {"filter": "phone or user_id is required."}}
    if db_orders is None:
        return {"ok": False, "errors": {"db": "Order database is unavailable."}}
    try:
        if phone:
            orders = db_orders.list_orders_by_phone(
                phone, order_type=type or None, status=status or None
            )
        else:
            orders = db_orders.list_orders_by_user(
                user_id, order_type=type or None, status=status or None
            )
    except Exception as exc:
        return {"ok": False, "errors": {"db": str(exc)}}
    return {"ok": True, "orders": orders}


@router.post("/orders/{order_no}/status")
def update_order_status(
    order_no: str, req: OrderStatusReq, claims: dict = _kitchen_or_delivery
):
    """Advance one order one step (kitchen: preparing/ready_for_pickup;
    delivery: out_for_delivery/delivered). db_orders.update_order_status
    enforces the legal-transition SEQUENCE; _ROLE_ALLOWED_STATUSES enforces
    which role may set which status (the sequence check alone would let
    kitchen legally set delivery's statuses and vice versa)."""
    role = claims.get("role")
    allowed = _ROLE_ALLOWED_STATUSES.get(role)
    if allowed is not None and req.status not in allowed:
        return {
            "ok": False,
            "errors": {"status": f"Your role can't set status '{req.status}'."},
        }
    if db_orders is None:
        return {"ok": False, "errors": {"db": "Order database is unavailable."}}
    try:
        rider_id = claims.get("sub") or claims.get("user_id") or claims.get("id") if role == "delivery" else None
        order = db_orders.update_order_status(order_no, req.status, performed_by=rider_id)
        try:
            from ai.realtime import broadcast_event
            broadcast_event("order_status_updated", order)
        except Exception as ws_exc:
            import logging
            logging.getLogger(__name__).warning("Failed to broadcast order_status_updated: %s", ws_exc)
    except ValueError as exc:
        return {"ok": False, "errors": {"status": str(exc)}}
    except Exception as exc:
        return {"ok": False, "errors": {"db": str(exc)}}
    return {"ok": True, "order": order}


@router.post("/orders/{order_no}/accept")
def accept_order(order_no: str, claims: dict = _delivery):
    """Assign the logged-in rider (delivery role) to the order.
    Forces atomic check to prevent multiple assignment races."""
    rider_id = claims.get("sub") or claims.get("user_id") or claims.get("id")
    if not rider_id:
        return {"ok": False, "errors": {"auth": "Rider ID not found in token."}}

    if db_orders is None:
        return {"ok": False, "errors": {"db": "Order database is unavailable."}}

    try:
        order = db_orders.accept_delivery_order(order_no, rider_id)
        if not order:
            return {
                "ok": False,
                "errors": {"order": "This order is no longer available or already accepted by another rider."},
            }
        try:
            from ai.realtime import broadcast_event
            broadcast_event("order_status_updated", order)
        except Exception as ws_exc:
            import logging
            logging.getLogger(__name__).warning("Failed to broadcast order_status_updated: %s", ws_exc)
        return {"ok": True, "order": order}
    except Exception as exc:
        return {"ok": False, "errors": {"db": str(exc)}}


@router.get("/orders/delivery-stats")
def delivery_stats(claims: dict = _delivery):
    """Today's delivered count + each delivered order's pickup->delivered
    minutes, for the delivery Profile tab."""
    if db_orders is None:
        return {"ok": False, "errors": {"db": "Order database is unavailable."}}
    try:
        return {"ok": True, **db_orders.get_delivery_stats()}
    except Exception as exc:
        return {"ok": False, "errors": {"db": str(exc)}}


# --------------------------------------------------------------------------- #
# Order feedback (rating + review) — writes to customer_feedback
# --------------------------------------------------------------------------- #


class FeedbackReq(BaseModel):
    rating: int = 0           # 1–5 stars
    feedback_text: str = ""   # optional text review


@router.get("/orders/{order_no}/feedback")
def get_order_feedback(order_no: str):
    """Check whether feedback has already been submitted for this order.

    Returns has_feedback=True/False and the existing row if present.
    Used by the frontend to decide whether to show the rating prompt or a
    'Thanks for your review' banner.
    """
    from db import postgres as local_postgres
    if not local_postgres.is_enabled():
        return {"ok": True, "has_feedback": False}
    try:
        with local_postgres.connect() as conn:
            with conn.cursor() as cur:
                # Look up the order uuid from order_no first
                cur.execute(
                    "SELECT id FROM public.orders WHERE order_no = %s LIMIT 1",
                    (order_no,),
                )
                row = cur.fetchone()
                if not row:
                    return {"ok": False, "errors": {"order": "Order not found."}}
                order_id = row[0]

                cur.execute(
                    """
                    SELECT id, rating, feedback_text, created_at
                    FROM public.customer_feedback
                    WHERE order_id = %s
                    LIMIT 1
                    """,
                    (str(order_id),),
                )
                fb = cur.fetchone()
                if fb:
                    from datetime import datetime, timezone
                    created = fb[3]
                    return {
                        "ok": True,
                        "has_feedback": True,
                        "rating": fb[1],
                        "feedback_text": fb[2],
                        "created_at": created.isoformat() if hasattr(created, "isoformat") else str(created),
                    }
    except Exception as exc:
        return {"ok": False, "errors": {"db": str(exc)}}
    return {"ok": True, "has_feedback": False}


@router.post("/orders/{order_no}/feedback")
def submit_order_feedback(order_no: str, req: FeedbackReq):
    """Submit a star rating (1–5) and optional text review for a delivered order.

    Rules enforced server-side:
    - Order must exist and have status 'delivered'
    - Rating must be 1–5
    - Exactly one feedback per order (duplicate returns the existing row)
    - feedback_text is optional; if blank we store an empty string
    """
    if req.rating < 1 or req.rating > 5:
        return {"ok": False, "errors": {"rating": "Rating must be between 1 and 5."}}

    from db import postgres as local_postgres
    if not local_postgres.is_enabled():
        return {"ok": False, "errors": {"db": "Database unavailable."}}

    try:
        with local_postgres.connect() as conn:
            with conn.cursor() as cur:
                # Fetch the order
                cur.execute(
                    """
                    SELECT id, status, customer_name, customer_phone
                    FROM public.orders
                    WHERE order_no = %s
                    LIMIT 1
                    """,
                    (order_no,),
                )
                row = cur.fetchone()
                if not row:
                    return {"ok": False, "errors": {"order": "Order not found."}}
                order_id, status, cust_name, cust_phone = row

                if status != "delivered":
                    return {
                        "ok": False,
                        "errors": {"order": "Feedback can only be submitted after delivery."},
                    }

                # Check for duplicate
                cur.execute(
                    "SELECT id, rating FROM public.customer_feedback WHERE order_id = %s LIMIT 1",
                    (str(order_id),),
                )
                existing = cur.fetchone()
                if existing:
                    return {
                        "ok": True,
                        "already_submitted": True,
                        "rating": existing[1],
                        "message": "Feedback already recorded. Thank you!",
                    }

                # Determine sentiment from rating
                if req.rating >= 4:
                    sentiment_label = "positive"
                    sentiment_score = 0.8 if req.rating == 4 else 1.0
                elif req.rating == 3:
                    sentiment_label = "neutral"
                    sentiment_score = 0.5
                else:
                    sentiment_label = "negative"
                    sentiment_score = 0.1 if req.rating == 2 else 0.0

                cur.execute(
                    """
                    INSERT INTO public.customer_feedback
                        (order_id, customer_name, customer_phone, channel,
                         rating, feedback_text, sentiment_label, sentiment_score,
                         topics, source_metadata)
                    VALUES (%s, %s, %s, 'app', %s, %s, %s, %s, '[]'::jsonb,
                            jsonb_build_object('order_no', %s::text))
                    RETURNING id, created_at
                    """,
                    (
                        str(order_id),
                        cust_name or "",
                        cust_phone or "",
                        req.rating,
                        req.feedback_text.strip() or "",
                        sentiment_label,
                        sentiment_score,
                        order_no,
                    ),
                )
                new_row = cur.fetchone()
    except Exception as exc:
        return {"ok": False, "errors": {"db": str(exc)}}

    return {
        "ok": True,
        "already_submitted": False,
        "feedback_id": str(new_row[0]),
        "rating": req.rating,
        "message": "Thank you for your feedback!",
    }


@router.get("/config")
def get_config():
    return {
        "discount_rate": pricing.get_discount_rate(),
        "discount_threshold": pricing.get_discount_threshold(),
        "gst_rate": pricing.get_gst_rate(),
    }


@router.post("/config")
def update_config(req: ConfigReq):
    pricing.set_discount_rate(req.discount_rate)
    pricing.set_discount_threshold(req.discount_threshold)
    if req.gst_rate is not None:
        pricing.set_gst_rate(req.gst_rate)
    return {
        "ok": True,
        "discount_rate": pricing.get_discount_rate(),
        "discount_threshold": pricing.get_discount_threshold(),
        "gst_rate": pricing.get_gst_rate(),
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
