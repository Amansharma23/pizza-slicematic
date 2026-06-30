"""LLM tool definitions + executor. The only AI code that touches core/.

Each tool returns a plain string for the LLM to read. All money is computed by
core/pricing.py; the menu comes from core/menu.py; orders are saved by
core/persistence.py (primary, .txt log) plus the best-effort Supabase mirror.
The LLM never computes prices and may only use item IDs that exist in the menu.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

from ai import guardrails
from api.routes import _load_active_menu  # shared live-menu resolver (default/custom)
from core import persistence, pricing
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


# --------------------------------------------------------------------------- #
# OpenAI-compatible tool schemas (OpenRouter accepts the same format)
# --------------------------------------------------------------------------- #

_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "base_id": {"type": "string", "description": "Base ID from the menu"},
        "pizza_id": {"type": "string", "description": "Pizza ID from the menu"},
        "topping_id": {"type": "string", "description": "Topping ID from the menu"},
        "quantity": {"type": "integer", "description": "Quantity, 1-10"},
    },
    "required": ["base_id", "pizza_id", "topping_id", "quantity"],
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
            "name": "calculate_order_price",
            "description": "Compute the itemised bill (subtotal, 10% discount at qty>=5, "
            "18% GST, total) for one or more order lines. Read the result back to the "
            "customer and ask them to confirm before saving.",
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
            "description": "Save the order. Call ONLY after the customer confirms the bill "
            "and has given name, phone, and payment mode. Re-validates everything.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "customer_phone": {"type": "string"},
                    "items": {"type": "array", "items": _ITEM_SCHEMA},
                    "payment_mode": {
                        "type": "string",
                        "description": "Cash, Card, or UPI (or 1/2/3)",
                    },
                },
                "required": [
                    "customer_name",
                    "customer_phone",
                    "items",
                    "payment_mode",
                ],
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


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _find(items: list[MenuItem], _id) -> MenuItem | None:
    return next((i for i in items if i.id == _id), None)


def _resolve_lines(items) -> tuple[list[Bill], list[str]]:
    """Validate + price each order line. Returns (bills, error_messages)."""
    bills: list[Bill] = []
    errors: list[str] = []
    if not items:
        return bills, ["The order has no items."]
    menu = _load_active_menu()  # may raise MenuError
    for idx, line in enumerate(items, 1):
        base = _find(menu.bases, line.get("base_id"))
        pizza = _find(menu.pizzas, line.get("pizza_id"))
        topping = _find(menu.toppings, line.get("topping_id"))
        missing = [
            n
            for n, val in (("base", base), ("pizza", pizza), ("topping", topping))
            if val is None
        ]
        if missing:
            errors.append(
                f"Item {idx}: unknown {', '.join(missing)} — not on the menu."
            )
            continue
        ok_q, qty = v.validate_quantity(line.get("quantity"))
        if not ok_q:
            errors.append(f"Item {idx}: {qty}")
            continue
        bills.append(pricing.compute_bill(base, pizza, topping, qty))
    return bills, errors


def _bill_str(b: Bill) -> str:
    disc = f", discount INR {b.discount:.2f}" if b.discount else ""
    return (
        f"{b.quantity}x {b.base.name} + {b.pizza.name} + {b.topping.name} "
        f"(unit INR {b.unit_price:.2f}): subtotal INR {b.subtotal:.2f}{disc}, "
        f"GST INR {b.gst:.2f}, line total INR {b.total:.2f}"
    )


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


def _calculate_order_price(args, session) -> str:
    try:
        bills, errors = _resolve_lines(args.get("items") or [])
    except MenuError as exc:
        return f"Menu unavailable: {exc}"
    if errors:
        return "Could not price the order:\n- " + "\n- ".join(errors)
    grand = round(sum(b.total for b in bills), 2)
    if session is not None:
        session.pricing = {"grand_total": grand, "n_lines": len(bills)}
    lines = "\n".join(f"- {_bill_str(b)}" for b in bills)
    return f"{lines}\nGrand total payable: INR {grand:.2f}"


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
    # Output guardrail: deterministic customer-field validation.
    errors, clean = guardrails.check_customer(
        args.get("customer_name", ""),
        args.get("customer_phone", ""),
        args.get("payment_mode", ""),
    )
    try:
        bills, line_errors = _resolve_lines(args.get("items") or [])
    except MenuError as exc:
        return f"Menu unavailable: {exc}"
    errors.extend(line_errors)
    if errors:
        return "Cannot place the order yet:\n- " + "\n- ".join(errors)
    name, phone, mode = clean["name"], clean["phone"], clean["payment_mode"]

    source = (
        args.get("order_source") or (session.channel if session else "chat")
    ).strip()
    language = session.language if session else None
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    order_no = None

    for bill in bills:
        _written_ts, oid = persistence.append_order(
            name=name,
            phone=phone,
            bill=bill,
            payment_mode=mode,
            timestamp=ts,
            order_id=order_no,  # share one id across all lines of a multi-line order
        )
        if order_no is None:
            order_no = oid
        if db_orders:
            db_orders.mirror_order(
                name=name,
                phone=phone,
                bill=bill,
                payment_mode=mode,
                order_no=order_no,
                timestamp=ts,
                source=source,
                session_id=(session.id if session else None),
                language=language,
            )

    grand = round(sum(b.total for b in bills), 2)
    if session is not None:
        session.name, session.phone = name, phone
        session.confirmed, session.status = True, "ordered"
    return (
        f"Order confirmed! Order number {order_no}. "
        f"Total payable INR {grand:.2f} via {mode}."
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
