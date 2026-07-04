"""LLM tool definitions + executor. The only AI code that touches core/.

Each tool returns a string for the LLM (JSON on deterministic successes the
agent injects verbatim). All money is computed by core/pricing.py; the menu
comes from core/menu.py. Chat/voice orders are saved to Supabase ONLY
(db.orders.create_order — same DECIDED path as /api/cart/checkout, DB-generated
order_no, user_id-stamped); orders_log.txt belongs to the graded Gradio app.
The LLM never computes prices and may only use item IDs that exist in the menu.
"""

from __future__ import annotations

import json
import logging
import os

from ai import guardrails

# Shared live-menu resolver (default/custom) + the multi-topping fuser the cart
# endpoints already use — one MenuItem with summed menu prices for compute_bill.
from api.routes import _combined_topping, _load_active_menu
from core import pricing
from core import validation as v
from core.menu import MenuError
from core.models import Bill, MenuItem

try:
    from db import escalations as db_escalations
    from db import orders as db_orders
    from db import sessions as db_sessions
except Exception:  # additive layer optional
    db_orders = db_sessions = db_escalations = None

log = logging.getLogger(__name__)

# The customer profile comes from the SESSION: ai/profile.attach_user decodes
# the request's JWT and loads the app_users row onto session.user_id/name/
# phone/address each turn. No hardcoded profile remains.


# --------------------------------------------------------------------------- #
# OpenAI-compatible tool schemas (OpenRouter accepts the same format)
# --------------------------------------------------------------------------- #

_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "base_id": {"type": "string", "description": "Base ID from the menu"},
        "pizza_id": {"type": "string", "description": "Pizza ID from the menu"},
        "topping_ids": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Array of Topping IDs from the menu (up to 3)",
        },
        "quantity": {"type": "integer", "description": "Quantity, 1-10"},
    },
    "required": ["base_id", "pizza_id", "topping_ids", "quantity"],
}

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_menu",
            "description": "Get the live menu (bases, pizzas, toppings with IDs and prices). "
            "Call before suggesting or pricing items.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_profile",
            "description": "Fetch the signed-in customer's saved profile (name, phone, "
            "delivery address). Call this instead of ever asking the customer to type "
            "their details.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_order_price",
            "description": "Compute the itemised bill (subtotal, "
            "18% GST, total) for one or more order lines (1-3 toppings each). In chat "
            "the bill is shown to the customer automatically — do not repeat its "
            "numbers. On a voice call, read back only the total.",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {"type": "array", "items": _ITEM_SCHEMA},
                },
                "required": ["items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "validate_customer",
            "description": "Validate customer details (name and/or phone and/or payment) the "
            "moment the customer gives them, so you can re-prompt immediately if something is "
            "wrong. Pass only the fields you have so far. Call before confirm_and_save_order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "customer_phone": {"type": "string"},
                    "payment_mode": {
                        "type": "string",
                        "description": "Cash, Card, or UPI (or 1/2/3)",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_and_save_order",
            "description": "Save the order. Call ONLY once payment is settled: the "
            "customer chose Cash/COD, said they paid via UPI, or provided card "
            "details. Re-validates everything before writing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {
                        "type": "string",
                        "description": "Omit to use the saved profile.",
                    },
                    "customer_phone": {
                        "type": "string",
                        "description": "Omit to use the saved profile.",
                    },
                    "items": {"type": "array", "items": _ITEM_SCHEMA},
                    "payment_mode": {
                        "type": "string",
                        "description": "Cash, Card, or UPI (or 1/2/3)",
                    },
                },
                "required": ["items", "payment_mode"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Hand off to a human when the customer asks for one, is upset, "
            "or the request can't be resolved.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "A 1-2 sentence summary of the conversation so far "
                        "and why a human is needed (the admin reads this at a glance).",
                    }
                },
                "required": ["reason"],
            },
        },
    },
]


# Tools the LLM may always call. get_menu is never exposed (the live menu is
# embedded in the system prompt every turn) and validate_customer is subsumed by
# get_customer_profile + the confirm guardrail; both stay in _DISPATCH for
# internal/back-compat use.
_EXPOSED_ALWAYS = frozenset(
    {"get_customer_profile", "calculate_order_price", "escalate_to_human"}
)


def tools_for(session) -> list[dict]:
    """The tool schemas legal for this turn (stage gating).

    confirm_and_save_order only exists once a bill has been priced and not yet
    saved — the model mechanically cannot save an order early, no prompt rule
    needed. Repricing (calculate_order_price) reopens a confirmed session.
    """
    names = set(_EXPOSED_ALWAYS)
    if session is None or (session.pricing and not session.confirmed):
        names.add("confirm_and_save_order")
    return [t for t in TOOL_DEFINITIONS if t["function"]["name"] in names]


def menu_names() -> dict[str, list[str]]:
    """A few live item names per category, for prompt few-shot examples.

    Never hardcode names in the prompt — the grader swaps menu files. Empty
    lists when the menu is unavailable (the caller then skips the examples).
    """
    try:
        m = _load_active_menu()
    except MenuError:
        return {"bases": [], "pizzas": [], "toppings": []}
    return {
        "bases": [i.name for i in m.bases[:2]],
        "pizzas": [i.name for i in m.pizzas[:3]],
        "toppings": [i.name for i in m.toppings[:3]],
    }


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _find(items: list[MenuItem], _id) -> MenuItem | None:
    return next((i for i in items if i.id == _id), None)


def _resolve_lines(items) -> tuple[list[tuple[Bill, list[MenuItem]]], list[str]]:
    """Validate + price each order line. Returns (bills_data, error_messages)."""
    bills_data: list[tuple[Bill, list[MenuItem]]] = []
    errors: list[str] = []
    if not items:
        return bills_data, ["The order has no items."]
    menu = _load_active_menu()  # may raise MenuError
    for idx, line in enumerate(items, 1):
        base = _find(menu.bases, line.get("base_id"))
        pizza = _find(menu.pizzas, line.get("pizza_id"))
        missing = [n for n, val in (("base", base), ("pizza", pizza)) if val is None]

        topping_ids = line.get("topping_ids") or []
        toppings = []
        for tid in topping_ids:
            t = _find(menu.toppings, tid)
            if t:
                toppings.append(t)
            else:
                missing.append(f"topping:{tid}")

        if missing:
            errors.append(
                f"Item {idx}: unknown {', '.join(missing)} — not on the menu."
            )
            continue
        if not topping_ids:
            errors.append(f"Item {idx}: please pick at least one topping (up to 3).")
            continue
        ok_q, qty = v.validate_quantity(line.get("quantity"))
        if not ok_q:
            errors.append(f"Item {idx}: {qty}")
            continue

        combined_t = _combined_topping(toppings)
        bills_data.append(
            (pricing.compute_bill(base, pizza, combined_t, qty), toppings)
        )
    return bills_data, errors


# --------------------------------------------------------------------------- #
# Tool implementations  (each returns a string for the LLM)
# --------------------------------------------------------------------------- #


def _get_menu(args, session) -> str:
    try:
        menu = _load_active_menu()
    except MenuError as exc:
        return f"Menu unavailable: {exc}"

    def block(title, items):
        rows = "\n".join(f"  {i.id} — {i.name} — INR {i.price:.2f}" for i in items)
        return f"{title}:\n{rows}"

    return "\n".join(
        [
            block("Bases", menu.bases),
            block("Pizzas", menu.pizzas),
            block("Toppings", menu.toppings),
        ]
    )


def _get_customer_profile(args, session) -> str:
    """The signed-in customer's profile, resolved from app_users onto the
    session by ai/profile.attach_user (JWT sent by the frontend each turn)."""
    if session is None or not (session.name and session.phone):
        return (
            "No signed-in profile found. Ask the customer for their name and "
            "10-digit phone number before saving any order."
        )
    address = session.address or (
        "NONE SAVED — a delivery address is required before the order can be "
        "placed; ask the customer to add one in the Profile tab, then continue."
    )
    return (
        f"Saved profile — name: {session.name}, phone: {session.phone}, "
        f"delivery address: {address}. Use these; never ask the customer "
        "to type them."
    )


def _calculate_order_price(args, session) -> str:
    try:
        bills_data, errors = _resolve_lines(args.get("items") or [])
    except MenuError as exc:
        return f"Menu unavailable: {exc}"
    if errors:
        return "Could not price the order:\n- " + "\n- ".join(errors)

    out_lines = []
    totals = {
        "subtotal": 0.0,
        "discount": 0.0,
        "taxable": 0.0,
        "gst": 0.0,
        "total": 0.0,
    }

    for bill, toppings in bills_data:
        out_lines.append(
            {
                "base": {
                    "id": bill.base.id,
                    "name": bill.base.name,
                    "price": bill.base.price,
                },
                "pizza": {
                    "id": bill.pizza.id,
                    "name": bill.pizza.name,
                    "price": bill.pizza.price,
                },
                "toppings": [
                    {"id": t.id, "name": t.name, "price": t.price} for t in toppings
                ],
                "quantity": bill.quantity,
                "unit_price": bill.unit_price,
                "subtotal": bill.subtotal,
                "discount": bill.discount,
                "taxable": bill.taxable,
                "gst": bill.gst,
                "total": bill.total,
            }
        )
        for k in totals:
            totals[k] = round(totals[k] + getattr(bill, k), 2)

    if session is not None:
        session.pricing = {"grand_total": totals["total"], "n_lines": len(bills_data)}
        # A (re)priced bill reopens the flow: the next legal save is for THIS
        # bill. Lets a customer order again after a completed order.
        session.confirmed = False

    payload = {"ok": True, "lines": out_lines, "cart": totals}
    return json.dumps(payload)


def _validate_customer(args, session) -> str:
    """Validate whichever customer fields are present; store valid ones on session."""
    checks = (
        ("name", args.get("customer_name"), v.validate_name),
        ("phone", args.get("customer_phone"), v.validate_phone),
        ("payment_mode", args.get("payment_mode"), v.validate_payment),
    )
    valid: list[str] = []
    errors: list[str] = []
    provided = 0
    for field_name, raw, validator in checks:
        if raw is None or str(raw).strip() == "":
            continue
        provided += 1
        ok, value_or_msg = validator(raw)
        if ok:
            valid.append(field_name)
            if session is not None and field_name == "name":
                session.name = value_or_msg
            elif session is not None and field_name == "phone":
                session.phone = value_or_msg
        else:
            errors.append(f"{field_name}: {value_or_msg}")
    if provided == 0:
        return "No customer details were provided to validate."
    if errors:
        return "Some details need fixing:\n- " + "\n- ".join(errors)
    return f"Valid: {', '.join(valid)}. You can proceed."


def _confirm_and_save_order(args, session) -> str:
    """Save the order to Supabase ONLY — one row per order, line breakdown in
    `items` jsonb, DB-generated order_no (SM-YYYYMMDD-NNNN), stamped with the
    profile's user_id. Same DECIDED path as /api/cart/checkout: no .txt write
    (the graded Gradio app owns orders_log.txt) and a DB failure is surfaced,
    never swallowed."""
    # Output guardrail: deterministic customer-field validation. Name/phone fall
    # back to the saved profile (primed on the session by get_customer_profile).
    errors, clean = guardrails.check_customer(
        args.get("customer_name") or (session.name if session else "") or "",
        args.get("customer_phone") or (session.phone if session else "") or "",
        args.get("payment_mode", ""),
    )
    try:
        bills_data, line_errors = _resolve_lines(args.get("items") or [])
    except MenuError as exc:
        return f"Menu unavailable: {exc}"
    errors.extend(line_errors)
    # Signed-in customers must have a saved delivery address before any chat/
    # voice order is placed (chat orders are delivered; there is no pickup flow).
    if session is not None and session.user_id and not session.address:
        errors.append(
            "No delivery address saved on the profile. Ask the customer to add "
            "one in the Profile tab, then confirm again."
        )
    if errors:
        return "Cannot place the order yet:\n- " + "\n- ".join(errors)
    name, phone, mode = clean["name"], clean["phone"], clean["payment_mode"]

    source = (
        args.get("order_source") or (session.channel if session else "chat")
    ).strip()

    # Same items/totals shape as /api/cart/checkout so the Orders tab renders
    # chat and checkout orders identically.
    items = []
    totals = {"subtotal": 0.0, "discount": 0.0, "gst": 0.0, "total": 0.0}
    for bill, toppings in bills_data:
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

    if db_orders is None:
        return (
            "Could not save the order: the order database is unavailable. "
            "Apologize and offer to escalate to a human."
        )
    try:
        order_no = db_orders.create_order(
            user_id=(session.user_id if session else None),
            name=name,
            phone=phone,
            items=items,
            subtotal=totals["subtotal"],
            discount=totals["discount"],
            gst=totals["gst"],
            total=totals["total"],
            payment_mode=mode,
            source=source,
            session_id=(session.id if session else None),
            language=(session.language if session else None),
            delivery_address=(session.address if session else None),
        )
    except Exception as exc:  # DB is the source of truth — surface, don't swallow
        log.warning("Order save failed: %s", exc)
        return (
            f"Could not save the order (database error: {exc}). The order is NOT "
            "placed. Apologize and offer to try again or escalate to a human."
        )

    if session is not None:
        session.name, session.phone = name, phone
        session.confirmed, session.status = True, "ordered"
    # Success is JSON so the agent can inject a deterministic, localized
    # confirmation without a second LLM pass (error paths stay plain strings).
    return json.dumps(
        {
            "ok": True,
            "order_no": order_no,
            "total": totals["total"],
            "payment_mode": mode,
        }
    )


def _langfuse_session_url(session_id: str) -> str | None:
    """Build a clickable Langfuse session URL if a project id is configured."""
    host = os.environ.get("LANGFUSE_BASE_URL") or os.environ.get("LANGFUSE_HOST")
    project = os.environ.get("LANGFUSE_PROJECT_ID")
    if host and project:
        return f"{host.rstrip('/')}/project/{project}/sessions/{session_id}"
    return None


def _escalate_to_human(args, session) -> str:
    reason = (args.get("reason") or "unspecified").strip()
    if session is not None:
        session.human_escalated, session.status = True, "escalated"
        # Ensure the session row exists (FK parent), then record the escalation.
        if db_sessions is not None:
            db_sessions.upsert_session(
                session.id,
                status="escalated",
                channel=session.channel,
                language=session.language,
                human_escalated=True,
                customer_name=session.name,
                customer_phone=session.phone,
            )
        if db_escalations is not None:
            db_escalations.add_escalation(
                session_id=session.id,
                reason=reason,
                channel=session.channel,
                language=session.language,
                customer_name=session.name,
                customer_phone=session.phone,
                langfuse_session_id=session.id,
                langfuse_url=_langfuse_session_url(session.id),
            )
    log.info("Escalation requested: %s", reason)
    return (
        "I've flagged this for a team member — someone will reach out shortly. "
        "Is there anything else I can help with in the meantime?"
    )


_DISPATCH = {
    "get_menu": _get_menu,
    "get_customer_profile": _get_customer_profile,
    "calculate_order_price": _calculate_order_price,
    "validate_customer": _validate_customer,
    "confirm_and_save_order": _confirm_and_save_order,
    "escalate_to_human": _escalate_to_human,
}


def execute_tool(name: str, args: dict | None, session=None) -> str:
    """Run a tool by name, returning a string for the LLM. Never raises."""
    fn = _DISPATCH.get(name)
    if fn is None:
        return f"Unknown tool: {name}"
    try:
        return fn(args or {}, session)
    except Exception as exc:  # surface as text, never crash the agent loop
        log.warning("Tool '%s' failed: %s", name, exc)
        return f"Tool '{name}' encountered an error: {exc}"
