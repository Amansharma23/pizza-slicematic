"""SliceMatic ordering app — Gradio UI mounted on FastAPI (single process).

Run locally:   uv run python app.py        (serves UI at / and API docs at /docs)
The Gradio handlers call core/ directly (in-process). The FastAPI routes expose
the same core/ functions for /docs and external callers — the UI never goes
over HTTP. See CLAUDE.md "Process model & API wiring".
"""

from __future__ import annotations

import os
import shutil
import tempfile
import html
from datetime import datetime

import gradio as gr
from fastapi import FastAPI

from core import menu as menu_mod
from core import validation as v
from core import pricing, persistence, analytics
from core.menu import MenuError
from api.routes import router as api_router

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

# --------------------------------------------------------------------------- #
# Rendering helpers (shared by UI + API)
# --------------------------------------------------------------------------- #

def render_menu_html(menu) -> str:
    """The menu as a numbered list per category, names + INR prices (FR-2.2)."""
    def block(title: str, items) -> str:
        rows = "".join(
            f'<div class="ml-row"><span class="ml-num">{i + 1}</span>'
            f'<span class="ml-name">{it.name}</span>'
            f'<span class="ml-price">₹{it.price:,.0f}</span></div>'
            for i, it in enumerate(items)
        )
        return f'<div class="ml-cat"><div class="ml-cat-title">{title}</div>{rows}</div>'

    if not menu:
        return ""
    return (
        '<div class="menu-list">'
        + block("Base", menu.bases)
        + block("Pizza", menu.pizzas)
        + block("Topping", menu.toppings)
        + "</div>"
    )


def render_menu_compare_html(previous_menu, new_menu=None) -> str:
    current = render_menu_html(previous_menu) or '<p class="bill-empty">No menu loaded.</p>'
    if new_menu is None:
        return f"<h4>Current menu</h4>{current}"
    updated = render_menu_html(new_menu) or '<p class="bill-empty">No menu loaded.</p>'
    return (
        '<div class="df-row" style="align-items:flex-start;">'
        f'<div style="flex:1;min-width:280px;"><h4>Previous menu</h4>{current}</div>'
        f'<div style="flex:1;min-width:280px;"><h4>New menu</h4>{updated}</div>'
        '</div>'
    )


def _item_signature(item) -> tuple[str, str, float]:
    return (item.id, item.name, item.price)


def _changed_ids(previous_items, new_items) -> set[str]:
    old = {item.id: _item_signature(item) for item in previous_items}
    changed = set()
    for item in new_items:
        if old.get(item.id) != _item_signature(item):
            changed.add(item.id)
    return changed


def render_menu_diff_html(previous_menu, new_menu) -> str:
    def previous_block(title: str, old_items, new_items) -> str:
        new_by_id = {item.id: _item_signature(item) for item in new_items}
        removed = {item.id for item in old_items if item.id not in new_by_id}
        rows = "".join(
            f'<div class="ml-row" style="{"background:#FEF2F2;border:1px solid #DC2626;" if it.id in removed else ""}">'
            f'<span class="ml-num">{i + 1}</span>'
            f'<span class="ml-name">{it.name}</span>'
            f'<span class="ml-price">₹{it.price:,.0f}</span></div>'
            for i, it in enumerate(old_items)
        )
        return f'<div class="ml-cat"><div class="ml-cat-title">{title}</div>{rows}</div>'

    def new_block(title: str, old_items, new_items) -> str:
        changed = _changed_ids(old_items, new_items)
        rows = "".join(
            f'<div class="ml-row" style="{"background:#ECFDF5;border:1px solid #10B981;" if it.id in changed else ""}">'
            f'<span class="ml-num">{i + 1}</span>'
            f'<span class="ml-name">{it.name}</span>'
            f'<span class="ml-price">₹{it.price:,.0f}</span></div>'
            for i, it in enumerate(new_items)
        )
        return f'<div class="ml-cat"><div class="ml-cat-title">{title}</div>{rows}</div>'

    previous = (
        '<div class="menu-list">'
        + previous_block("Base", previous_menu.bases if previous_menu else [], new_menu.bases)
        + previous_block("Pizza", previous_menu.pizzas if previous_menu else [], new_menu.pizzas)
        + previous_block("Topping", previous_menu.toppings if previous_menu else [], new_menu.toppings)
        + "</div>"
    )
    updated = (
        '<div class="menu-list">'
        + new_block("Base", previous_menu.bases if previous_menu else [], new_menu.bases)
        + new_block("Pizza", previous_menu.pizzas if previous_menu else [], new_menu.pizzas)
        + new_block("Topping", previous_menu.toppings if previous_menu else [], new_menu.toppings)
        + "</div>"
    )
    return (
        '<div class="df-row" style="align-items:flex-start;">'
        f'<div style="flex:1;min-width:280px;"><h4>Previous menu</h4>{previous}</div>'
        f'<div style="flex:1;min-width:280px;"><h4>New menu</h4>{updated}</div>'
        '</div>'
    )


def render_payment_html() -> str:
    rows = "".join(
        f'<div class="ml-row"><span class="ml-num">{num}</span>'
        f'<span class="ml-name">{mode}</span></div>'
        for num, mode in (("1", "Cash"), ("2", "Card"), ("3", "UPI"))
    )
    return f'<div class="menu-list payment-list"><div class="ml-cat"><div class="ml-cat-title">Payment</div>{rows}</div></div>'


def _menu_file_paths(menu_dir: str) -> dict[str, str]:
    return {
        menu_mod.BASE_FILE: os.path.join(menu_dir, menu_mod.BASE_FILE),
        menu_mod.PIZZA_FILE: os.path.join(menu_dir, menu_mod.PIZZA_FILE),
        menu_mod.TOPPING_FILE: os.path.join(menu_dir, menu_mod.TOPPING_FILE),
    }


def _has_complete_menu_files(menu_dir: str) -> bool:
    return all(os.path.isfile(path) for path in _menu_file_paths(menu_dir).values())


def _write_menu_file(path: str, items) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for item in items:
            fh.write(f"{item.id};{item.name};{item.price:.2f}\n")


def _persist_menu(menu) -> None:
    os.makedirs(CUSTOM_MENU_DIR, exist_ok=True)
    _write_menu_file(os.path.join(CUSTOM_MENU_DIR, menu_mod.BASE_FILE), menu.bases)
    _write_menu_file(os.path.join(CUSTOM_MENU_DIR, menu_mod.PIZZA_FILE), menu.pizzas)
    _write_menu_file(os.path.join(CUSTOM_MENU_DIR, menu_mod.TOPPING_FILE), menu.toppings)


def _save_menu_source(mode: str) -> None:
    os.makedirs(DATABASE_DIR, exist_ok=True)
    with open(MENU_SOURCE_FILE, "w", encoding="utf-8") as fh:
        fh.write(mode)


def _load_menu_source() -> str:
    try:
        with open(MENU_SOURCE_FILE, "r", encoding="utf-8") as fh:
            mode = fh.read().strip()
    except OSError:
        return DEFAULT_MENU_MODE
    return mode if mode in {DEFAULT_MENU_MODE, CUSTOM_MENU_MODE} else DEFAULT_MENU_MODE


def _load_custom_menu():
    if not _has_complete_menu_files(CUSTOM_MENU_DIR):
        raise MenuError("No updated menu has been saved yet.")
    return menu_mod.load_menu(CUSTOM_MENU_DIR)


def bill_html(bill) -> str:
    rate_pct = int(pricing.get_discount_rate() * 100)
    disc = (
        f'<div class="bl"><span>Discount ({rate_pct}%)</span><span style="color:#10B981">− INR {bill.discount:.2f}</span></div>'
        if bill.discount > 0
        else f'<div class="bl muted"><span>Discount ({rate_pct}%)</span><span>INR 0.00</span></div>'
    )
    return f"""
    <div class="bill-card">
      <div class="bl"><span>Unit price ({bill.base.name} + {bill.pizza.name} + {bill.topping.name})</span>
        <span>INR {bill.unit_price:.2f}</span></div>
      <div class="bl"><span>Quantity</span><span>× {bill.quantity}</span></div>
      <div class="bl"><span>Subtotal</span><span>INR {bill.subtotal:.2f}</span></div>
      {disc}
      <div class="bl"><span>GST (18%)</span><span>INR {bill.gst:.2f}</span></div>
      <div class="bl total"><span>Total payable</span><span>INR {bill.total:.2f}</span></div>
    </div>
    """


def _money(value: float) -> str:
    return f"{value:,.2f}"


def _display_timestamp(value: str | None) -> str:
    if not value:
        return datetime.now().strftime("%Y-%m-%d - %H:%M:%S")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d - %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d - %H:%M:%S")
        except ValueError:
            continue
    return value


def bill_html(bill, *, compact: bool = False, order: dict | None = None, show_promo: bool = True) -> str:
    rate_pct = int(pricing.get_discount_rate() * 100)
    threshold = pricing.get_discount_threshold()
    promo = (
        f'<div class="promo-strip">Order {threshold} or more pizzas and unlock {rate_pct}% off your subtotal.</div>'
        if show_promo and rate_pct > 0
        else ""
    )
    discount_row = (
        f'<div class="bill-row discount"><span>Discount ({rate_pct}%)</span><span>-{_money(bill.discount)}</span></div>'
        if bill.discount > 0
        else ""
    )
    meta = ""
    if order:
        order_no = html.escape(str(order.get("order_no", "")))
        order_ts = html.escape(_display_timestamp(order.get("order_timestamp") or order.get("timestamp")))
        meta = (
            '<div class="receipt-meta">'
            f'<span>Order ID <b>{order_no}</b></span>'
            f'<span>Date - time <b>{order_ts}</b></span>'
            '</div>'
        )
    card_class = "bill-card compact" if compact else "bill-card"
    return f"""
    <div class="{card_class}">
      {meta}
      {promo}
      <div class="bill-section">
        <div class="bill-row"><span>{html.escape(bill.base.name)}</span><span>{_money(bill.base.price)}</span></div>
        <div class="bill-row"><span>{html.escape(bill.pizza.name)}</span><span>{_money(bill.pizza.price)}</span></div>
        <div class="bill-row"><span>{html.escape(bill.topping.name)}</span><span>{_money(bill.topping.price)}</span></div>
      </div>
      <div class="bill-row"><span>Unit price</span><span>{_money(bill.unit_price)}</span></div>
      <div class="bill-row"><span>Quantity</span><span>x {bill.quantity}</span></div>
      <div class="bill-row"><span>Subtotal</span><span>{_money(bill.subtotal)}</span></div>
      {discount_row}
      <div class="bill-row"><span>GST (18%)</span><span>{_money(bill.gst)}</span></div>
      <div class="bill-row total"><span>Total payable</span><span>₹{_money(bill.total)}</span></div>
    </div>
    """


def receipt_text(order: dict) -> str:
    bill = order["bill"]
    return "\n".join(
        [
            "SliceMatic Order Receipt",
            f"Order ID: {order.get('order_no', '')}",
            f"Date - time: {_display_timestamp(order.get('order_timestamp') or order.get('timestamp'))}",
            f"Customer: {order.get('name', '')}",
            f"Phone: {order.get('phone', '')}",
            f"Payment: {order.get('payment_mode', '')}",
            "",
            f"{bill.base.name}: {bill.base.price:.2f}",
            f"{bill.pizza.name}: {bill.pizza.price:.2f}",
            f"{bill.topping.name}: {bill.topping.price:.2f}",
            f"Unit price: {bill.unit_price:.2f}",
            f"Quantity: {bill.quantity}",
            f"Subtotal: {bill.subtotal:.2f}",
            f"Discount: {bill.discount:.2f}",
            f"GST: {bill.gst:.2f}",
            f"Total payable: ₹{bill.total:.2f}",
            "",
        ]
    )


# --------------------------------------------------------------------------- #
# FastAPI surface — same shared router the HTML frontend uses (api/routes.py).
# Exposed for /docs + Stage 3; the Gradio UI calls core/ directly, not these.
# --------------------------------------------------------------------------- #

api = FastAPI(title="SliceMatic API", version="0.1.0")
api.include_router(api_router)


# --------------------------------------------------------------------------- #
# Theme + CSS
# --------------------------------------------------------------------------- #

theme = gr.themes.Soft(
    primary_hue=gr.themes.colors.emerald,
    secondary_hue=gr.themes.colors.slate,
    neutral_hue=gr.themes.colors.gray,
    font=[gr.themes.GoogleFont("Outfit"), gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"],
).set(
    body_background_fill="#FEFAE0",
    body_background_fill_dark="#FEFAE0",
    block_background_fill="rgba(255, 255, 255, 0.8)",
    background_fill_secondary="rgba(255, 255, 255, 0.9)",
    border_color_primary="#DDA15E",
    input_background_fill="#FFFFFF",
    input_border_color="#CCD5AE",
    button_primary_background_fill="#606C38",
    button_primary_background_fill_hover="#283618",
    button_primary_text_color="white",
    button_secondary_background_fill="#E9EDC9",
    button_secondary_background_fill_hover="#DDA15E",
    button_secondary_text_color="#283618",
    block_radius="16px",
    block_shadow="none",
)

CSS = """
.hide .back-btn-custom, .hide .icon-wrap { display: none !important; }
.gradio-container {max-width: 1040px !important; width:100% !important; margin: auto !important;}
body {
    background: radial-gradient(circle at 18% 18%, rgba(255, 214, 102, 0.34), transparent 24%),
                radial-gradient(circle at 82% 8%, rgba(220, 38, 38, 0.10), transparent 22%),
                #FFF8E7 !important;
}
input, textarea, select {color:#1f2937 !important; transition: all 0.2s ease !important;}
input:focus, textarea:focus {border-color: #606C38 !important; box-shadow: 0 0 0 3px rgba(96, 108, 56, 0.15) !important;}
label span {color:#4B5563 !important; font-weight:600 !important;}

/* Hide radio circle indicators & spin buttons */
.page-card input[type="radio"] {display:none !important;}
.page-card label > input[type="radio"] + span {margin-left:0 !important;}
input[type=number]::-webkit-inner-spin-button, 
input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
textarea { resize: none !important; }

/* Upload buttons */
.up-btn {width:100% !important; background:#E9EDC9 !important; border:2px dashed #606C38 !important;
         color:#283618 !important; font-weight:600 !important; border-radius:12px !important;
         padding:14px 18px !important; justify-content:flex-start !important; margin-top:10px !important;
         transition: all 0.2s ease !important; box-shadow:none !important;}
.up-btn:hover {background:#CCD5AE !important; border-color:#283618 !important; transform: translateY(-1px);}
.up-status p {margin:4px 0 0 6px !important; color:#606C38 !important; font-size:13px !important; font-weight:600;}

/* Hero */
#hero {
    background: linear-gradient(135deg, #5F6F2E 0%, #263915 100%);
    border-radius:20px; padding:22px 36px; margin:0 auto !important;
    box-shadow: 0 10px 30px rgba(40, 54, 24, 0.2);
    position: relative; overflow: hidden;
    width:100% !important; max-width:100% !important;
}
#hero::after {
    content: '🍕'; position: absolute; right: 20px; top: -10px; font-size: 100px; opacity: 0.15;
    animation: float 6s ease-in-out infinite;
}
@keyframes float { 0% {transform: translateY(0px) rotate(0deg);} 50% {transform: translateY(-15px) rotate(5deg);} 100% {transform: translateY(0px) rotate(0deg);} }
#hero h1 {margin:0; font-size:32px; font-weight:800; letter-spacing:-0.5px; color:#ffffff !important;}
#hero p {margin:8px 0 0; font-size:16px; color:#E9EDC9 !important; font-weight: 500;}
#view-row {
    width:100% !important;
    max-width:100% !important;
    margin:-72px auto 34px !important;
    height:42px !important;
    min-height:42px !important;
    position:relative !important;
    z-index:5 !important;
    justify-content:flex-end !important;
    pointer-events:none !important;
}
#view-row > .block,
#view-row .form,
#view-row .wrap,
#view-row .styler {
    background:transparent !important;
    border:none !important;
    box-shadow:none !important;
    padding:0 !important;
    margin:0 !important;
}
#view-row > .block:first-child {display:none !important;}
.view-switch {
    width:236px !important;
    max-width:236px !important;
    margin-left:auto !important;
    margin-right:36px !important;
    pointer-events:auto !important;
}
.view-switch select,
.view-switch input {
    height:42px !important;
    border-radius:10px !important;
    border:1px solid rgba(255,255,255,.65) !important;
    background:rgba(255,255,255,.92) !important;
    color:#1F2937 !important;
    font-weight:700 !important;
}

/* Buttons animation */
button { transition: all 0.2s ease !important; }
button.primary:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(96, 108, 56, 0.3) !important; }
button.secondary:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important; }

/* Connected Step pills */
.steps {display:flex; align-items: center; justify-content: space-between; margin:4px 20px 8px; position: relative;}
.steps::before { content: ''; position: absolute; left: 10%; right: 10%; top: 50%; height: 3px; background: #F97316; opacity:.35; z-index: 0; }
.pill {
    background:#FFFDF7; color:#6B7280; border:2px solid #F6C36D; border-radius:999px;
    padding:8px 20px; font-size:14px; font-weight:600; z-index: 1; transition: all 0.3s ease;
}
.pill.active {
    background: #6A7A32; color:#ffffff; border-color:#6A7A32;
    box-shadow:0 5px 18px rgba(96, 108, 56, 0.32); transform: scale(1.05);
}

/* Glassmorphism card & Header */
.page-card {
    background: #FFFDF7 !important; 
    backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
    border:1px solid #F3C677 !important;
    border-radius:24px !important; padding:20px 24px !important;
    box-shadow: 0 20px 42px rgba(146, 64, 14, 0.08), inset 0 1px 0 rgba(255, 255, 255, 1) !important;
    width:100% !important; max-width:100% !important;
    justify-content:flex-start !important;
}
.page-card > .block, .page-card .form {align-self:stretch !important; margin: 0 !important; padding: 0 !important;}

.header-row { align-items: center !important; margin-bottom: 4px !important; flex-wrap: nowrap !important; display: flex; gap: 12px !important; }
.header-row-right { align-items: center !important; margin-bottom: 4px !important; flex-wrap: nowrap !important; display: flex; gap: 12px !important; justify-content: flex-end !important; }
.header-row > .block, .header-row-right > .block { padding:0 !important; margin:0 !important; border:none !important; box-shadow:none !important; background:transparent !important; }
.icon-btn button, .icon-btn a { min-width: 40px !important; width: 40px !important; max-width: 40px !important; height: 40px !important; padding: 0 !important; border-radius: 12px !important; border: none !important; background: linear-gradient(135deg, #10B981, #059669) !important; color: transparent !important; font-size: 0 !important; display: flex; align-items: center !important; justify-content: center !important; cursor: pointer; flex-shrink: 0 !important; box-sizing: border-box !important; box-shadow: 0 4px 10px rgba(16, 185, 129, 0.3) !important; transition: all 0.2s ease !important; position: relative !important; margin: 0 !important; }
.icon-btn button:hover, .icon-btn a:hover { background: linear-gradient(135deg, #34D399, #10B981) !important; transform: translateY(-2px) scale(1.05) !important; box-shadow: 0 6px 15px rgba(16, 185, 129, 0.4) !important; }
.icon-btn button::after, .icon-btn a::after { content: ''; position: absolute; top: 10px; left: 10px; width: 20px; height: 20px; background-color: white; -webkit-mask-size: contain; mask-size: contain; -webkit-mask-repeat: no-repeat; mask-repeat: no-repeat; -webkit-mask-position: center; mask-position: center; pointer-events: none; }
.simple-back { background: transparent !important; border: 1px solid #E5E7EB !important; color: #4B5563 !important; box-shadow: none !important; }
.simple-back:hover { background: #F3F4F6 !important; }
button.back-btn-custom { min-width: 40px !important; width: 40px !important; max-width: 40px !important; height: 40px !important; padding: 0 !important; border-radius: 50% !important; border: none !important; background: linear-gradient(135deg, #10B981, #059669) !important; color: transparent !important; font-size: 0 !important; display: flex; align-items: center !important; justify-content: center !important; cursor: pointer; flex-shrink: 0 !important; box-sizing: border-box !important; box-shadow: 0 4px 10px rgba(16, 185, 129, 0.3) !important; transition: all 0.2s ease !important; position: relative !important; margin: 0 !important; }
button.back-btn-custom:hover { background: linear-gradient(135deg, #34D399, #10B981) !important; transform: translateY(-2px) scale(1.05) !important; box-shadow: 0 6px 15px rgba(16, 185, 129, 0.4) !important; }
button.back-btn-custom::after { content: ''; position: absolute; top: 10px; left: 10px; width: 20px; height: 20px; background-color: white; -webkit-mask-size: contain; mask-size: contain; -webkit-mask-repeat: no-repeat; mask-repeat: no-repeat; -webkit-mask-position: center; mask-position: center; pointer-events: none; -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='currentColor'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M10 19l-7-7m0 0l7-7m-7 7h18'/%3E%3C/svg%3E"); mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='currentColor'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M10 19l-7-7m0 0l7-7m-7 7h18'/%3E%3C/svg%3E"); }
button.icon-btn, a.icon-btn, .icon-btn button, .icon-btn a { min-width: 40px !important; width: 40px !important; max-width: 40px !important; height: 40px !important; padding: 0 !important; border-radius: 12px !important; border: none !important; background: linear-gradient(135deg, #10B981, #059669) !important; color: transparent !important; font-size: 0 !important; display: flex; align-items: center !important; justify-content: center !important; cursor: pointer; flex-shrink: 0 !important; box-sizing: border-box !important; box-shadow: 0 4px 10px rgba(16, 185, 129, 0.3) !important; transition: all 0.2s ease !important; position: relative !important; margin: 0 !important; }
button.icon-btn:hover, a.icon-btn:hover, .icon-btn button:hover, .icon-btn a:hover { background: linear-gradient(135deg, #34D399, #10B981) !important; transform: translateY(-2px) scale(1.05) !important; box-shadow: 0 6px 15px rgba(16, 185, 129, 0.4) !important; }
button.icon-btn::after, a.icon-btn::after, .icon-btn button::after, .icon-btn a::after { content: ''; position: absolute; top: 10px; left: 10px; width: 20px; height: 20px; background-color: white; -webkit-mask-size: contain; mask-size: contain; -webkit-mask-repeat: no-repeat; mask-repeat: no-repeat; -webkit-mask-position: center; mask-position: center; pointer-events: none; }
button.btn-refresh::after, a.btn-refresh::after, .btn-refresh button::after, .btn-refresh a::after { -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='black'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15'/%3E%3C/svg%3E"); mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='black'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15'/%3E%3C/svg%3E"); }
button.btn-download::after, a.btn-download::after, .btn-download button::after, .btn-download a::after { -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='black'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4'/%3E%3C/svg%3E"); mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='black'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4'/%3E%3C/svg%3E"); }
button.btn-filter::after, a.btn-filter::after, .btn-filter button::after, .btn-filter a::after { -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='black'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z'/%3E%3C/svg%3E"); mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='black'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z'/%3E%3C/svg%3E"); }
.icon-wrap { padding: 0 !important; margin: 0 !important; width: 40px !important; min-width: 40px !important; max-width: 40px !important; flex: 0 0 40px !important; display: flex; align-items: center !important; justify-content: center !important; }
.header-row h3 { margin: 0 auto 0 0 !important; font-size: 22px; font-weight: 700; color: #111827; letter-spacing: -0.3px; display:inline-block !important; white-space: nowrap; flex-grow: 1 !important; text-align: left !important; }
.kpi-table { background: rgba(255,255,255,0.6); border: 1px solid rgba(255,255,255,0.9); border-radius: 12px; padding: 16px; flex: 1; box-shadow: 0 4px 15px rgba(0,0,0,0.02); }
.kpi-table h4 { margin: 0 0 12px 0; font-size: 14px; color: #6B7280; text-transform: uppercase; letter-spacing: 0.5px; }
.clean-table { width: 100%; border-collapse: collapse; text-align: left; font-size: 14px; }
.clean-table th { padding: 8px 12px; border-bottom: 2px solid #E5E7EB; color: #374151; font-weight: 600; white-space: nowrap; }
.clean-table td { padding: 8px 12px; border-bottom: 1px solid #F3F4F6; color: #4B5563; }
.clean-table tr:last-child td { border-bottom: none; }
.df-row { gap: 24px !important; flex-wrap: wrap !important; }
.filter-row { align-items: flex-end !important; margin-bottom: 16px !important; gap: 12px !important; flex-wrap: nowrap !important; }

/* Build step */
.build-row {gap:32px !important; flex-wrap:nowrap !important;}
.build-left {flex:1 1 auto !important; min-width:0 !important;}
.checkout-col {
    flex:0 0 350px !important; max-width:350px !important;
    background:#ffffff !important; border:1px solid #F3F4F6 !important;
    border-radius:16px !important; padding:20px 24px !important; align-self:flex-start !important;
    box-shadow: 0 10px 25px rgba(0,0,0,0.03) !important;
}
.checkout-col h4 {margin:0 0 12px !important; color:#1F2937 !important; font-size:16px; font-weight: 700;}
.checkout-col .bill-card {background:transparent !important; border:none !important; padding:0 !important; border-radius: 0; box-shadow:none !important;}
.bill-empty {color:#9CA3AF; font-size:14px; line-height:1.6; padding:10px 0; text-align: center; width: 100%;}
.page-card .block, .page-card .form, .page-card fieldset,
.page-card .styler, .page-card .gr-group, .page-card .wrap {
       background:transparent !important; border:none !important; box-shadow:none !important;}
.page-card .block {padding:0 !important;}
.page-card h3 {margin:0 0 16px !important; font-size:22px; font-weight:700; color:#111827; letter-spacing: -0.3px;}

/* inputs */
.page-card input, .page-card textarea {background:#fff !important; border:1px solid #D1D5DB !important; font-size:15px !important;}
.page-card label span {background:#D1FAE5 !important; color:#334155 !important; border-radius:7px !important; padding:4px 7px !important; font-weight:800 !important;}
.styler {background:transparent !important;}

/* Menu numbered list */
.menu-list {display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:12px; margin:8px 0 16px; width:100%;}
.ml-cat {background:#ffffff; border:1px solid #F3F4F6; border-radius:14px; padding:10px 12px; min-width:0; box-shadow: 0 4px 6px rgba(0,0,0,0.02);}
.ml-cat-title {font-weight:700; color:#606C38; margin-bottom:8px; font-size:12px;
               text-transform:uppercase; letter-spacing:1px; border-bottom: 1px solid #F3F4F6; padding-bottom: 6px;}
.ml-row {display:grid; grid-template-columns:auto 1fr auto; align-items:center; column-gap:10px;
         padding:4px 6px; font-size:13px; color:#374151; border-radius: 6px; transition: all 0.2s;}
.ml-row:hover { background: #FEFAE0; transform: translateX(2px); }
.ml-num {background:#E9EDC9; color:#283618; border-radius:6px; min-width:24px; text-align:center;
         font-weight:700; padding:2px 6px; font-size:12px;}
.ml-name {color:#1F2937; min-width:0; line-height:1.4; font-weight: 500;}
.ml-price {color:#6B7280; font-size:12px; white-space:nowrap; text-align:right;}

/* Receipt / Bill */
.bill-card {
    background:#ffffff; border:1px solid #E5E7EB; border-radius:12px; padding:20px !important;
    position: relative; max-width: 450px; margin: 0 auto; box-shadow: 0 8px 20px rgba(0,0,0,0.03);
}
.bl {display:flex; justify-content:space-between; padding:8px 0; font-size:14px; color:#4B5563;
     border-bottom:1px dashed #E5E7EB; align-items: center;}
.bl:last-child { border-bottom: none; }
.bl.muted {color:#9CA3AF;}
.bl.total {border-bottom:none; font-weight:800; font-size:20px; color:#111827; padding-top:12px; margin-top: 4px; border-top: 2px solid #111827;}
.err {color:#DC2626; font-weight:600; background: #FEF2F2; padding: 12px 16px; border-radius: 8px; border-left: 4px solid #DC2626; display: inline-block; width: 100%; box-sizing: border-box;}

/* Checkmark Animation */
.check-wrapper { display: flex; justify-content: center; margin: 20px 0; }
.checkmark { width: 64px; height: 64px; border-radius: 50%; display: block; stroke-width: 3; stroke: #10B981; stroke-miterlimit: 10; margin: 0 auto; box-shadow: inset 0px 0px 0px #10B981; animation: fill .4s ease-in-out .4s forwards, scale .3s ease-in-out .9s both; }
.checkmark__circle { stroke-dasharray: 166; stroke-dashoffset: 166; stroke-width: 3; stroke-miterlimit: 10; stroke: #10B981; fill: none; animation: stroke 0.6s cubic-bezier(0.65, 0, 0.45, 1) forwards; }
.checkmark__check { transform-origin: 50% 50%; stroke-dasharray: 48; stroke-dashoffset: 48; animation: stroke 0.3s cubic-bezier(0.65, 0, 0.45, 1) 0.6s forwards; }
@keyframes stroke { 100% { stroke-dashoffset: 0; } }
@keyframes scale { 0%, 100% { transform: none; } 50% { transform: scale3d(1.1, 1.1, 1); } }
@keyframes fill { 100% { box-shadow: inset 0px 0px 0px 30px #D1FAE5; } }

footer {visibility:hidden;}
@media (max-width:768px){.build-row{flex-direction: column !important;} .checkout-col{max-width: 100% !important;}}

/* Stage 2 polish pass */
.gradio-container {max-width: 1280px !important; padding: 18px 24px 26px !important;}
#hero {border-radius:18px; padding:22px 36px; margin:0 auto !important;}
#hero h1 {font-size:32px;}
#hero p {margin-top:6px; font-size:15px;}
.tabs {margin-top:0 !important;}
.tab-nav, .tabitem > .label-wrap {justify-content:flex-end !important;}
.steps {margin:14px 42px 24px !important;}
.page-card {padding:34px 38px !important; border-radius:22px !important; min-height:0 !important;}
.page-card h3 {font-size:24px !important;}
.menu-list {grid-template-columns: repeat(3, minmax(220px, 1fr)); gap:14px; margin:14px 0 18px;}
.ml-cat {padding:14px 16px; border-color:#E5E7EB; box-shadow:0 8px 22px rgba(17,24,39,.04);}
.ml-row {padding:6px 8px; font-size:14px;}
.ml-price, .bill-row span:last-child {font-variant-numeric: tabular-nums; font-feature-settings:"tnum"; text-align:right;}
.payment-list {grid-template-columns:minmax(260px, 420px); max-width:460px;}
.payment-list .ml-row {grid-template-columns:auto 1fr; font-size:15px;}
.bill-card {max-width:560px; padding:18px 22px !important; border-radius:14px; box-shadow:0 14px 34px rgba(17,24,39,.06);}
.bill-card.compact {max-width:620px;}
.promo-strip {background:#FFF7D6; color:#5F4B00; border:1px solid #FDE68A; border-radius:10px; padding:10px 12px; margin-bottom:12px; font-weight:700; text-align:center;}
.bill-section {border:1px solid #EEF2F7; border-radius:10px; padding:6px 10px; margin-bottom:8px; background:#FCFCFA;}
.bill-row {display:grid; grid-template-columns:minmax(0, 1fr) 132px; gap:18px; align-items:start; padding:8px 0; border-bottom:1px dashed #E5E7EB; color:#273244; font-size:15px;}
.bill-row span:first-child {min-width:0; line-height:1.35;}
.bill-row span:last-child {white-space:nowrap;}
.bill-row.discount {color:#059669; font-weight:700;}
.bill-row.total {border-bottom:none; border-top:2px solid #111827; margin-top:8px; padding-top:12px; font-size:21px; font-weight:800;}
.bill-row.total span:last-child {font-size:24px;}
.confirmation-card {max-width:620px; margin:0 auto; text-align:center;}
.confirmation-actions {display:flex; gap:12px; justify-content:center; flex-wrap:wrap; margin-top:16px;}
@media (max-width: 900px) {
  .gradio-container {padding:12px !important;}
  .menu-list {grid-template-columns:1fr;}
  .bill-row {grid-template-columns:minmax(0, 1fr) 112px;}
}

/* Final outlet-style layer: pizza tracker + clean ordering surface */
#hero {
  display:flex !important;
  align-items:center !important;
  justify-content:space-between !important;
  gap:28px !important;
  min-height:132px !important;
  width:100% !important;
  max-width:100% !important;
  padding:24px 38px !important;
  margin:0 auto 20px !important;
  border-radius:22px !important;
  background:
    radial-gradient(circle at 82% 50%, rgba(255, 217, 102, .16), transparent 18%),
    linear-gradient(135deg, #263916 0%, #5E7330 48%, #21310F 100%) !important;
  border:1px solid rgba(255,255,255,.14) !important;
  box-shadow:0 22px 52px rgba(37, 42, 16, .22) !important;
  overflow:hidden !important;
}
#hero > .block,
#hero .form,
#hero .wrap,
#hero .styler {
  background:transparent !important;
  border:none !important;
  box-shadow:none !important;
  padding:0 !important;
  margin:0 !important;
}
#hero > .block:first-child {
  flex:1 1 auto !important;
  min-width:0 !important;
}
#hero::after {
  right:270px !important;
  top:-18px !important;
  opacity:.11 !important;
  filter:saturate(.9) !important;
}
.hero-copy h1 {
  margin:0 !important;
  color:#FFFFFF !important;
  font-size:34px !important;
  font-weight:900 !important;
  letter-spacing:0 !important;
}
.hero-copy p {
  margin:8px 0 0 !important;
  color:#FFF3C4 !important;
  font-size:16px !important;
  font-weight:700 !important;
}
#hero .view-switch {
  width:260px !important;
  max-width:260px !important;
  margin:0 !important;
  flex:0 0 260px !important;
  z-index:2 !important;
}
#hero .view-switch select,
#hero .view-switch input {
  height:46px !important;
  border-radius:13px !important;
  border:1px solid rgba(255,255,255,.72) !important;
  background:rgba(255,255,255,.96) !important;
  color:#172033 !important;
  font-size:15px !important;
  font-weight:850 !important;
  box-shadow:0 12px 28px rgba(0,0,0,.12) !important;
}
#main-tabs {
  background:transparent !important;
  border:none !important;
  box-shadow:none !important;
  padding:0 !important;
  margin:0 !important;
}
#main-tabs > * {
  background:transparent !important;
  border:none !important;
  box-shadow:none !important;
}
.steps {
  background:#FFFDF7 !important;
  border:1px solid #FED7AA !important;
  border-radius:22px !important;
  padding:18px 28px !important;
  margin:4px 0 20px !important;
  box-shadow:0 18px 40px rgba(154, 52, 18, .08) !important;
}
.steps::before {
  left:8% !important;
  right:8% !important;
  height:4px !important;
  background:linear-gradient(90deg, #C2410C, #F97316, #FACC15) !important;
  opacity:.28 !important;
}
.pill {
  min-width:118px !important;
  text-align:center !important;
  background:#FFFFFF !important;
  color:#475569 !important;
  border:2px solid #FDBA74 !important;
  font-size:15px !important;
  font-weight:850 !important;
  padding:10px 20px !important;
}
.pill.active {
  background:#B91C1C !important;
  color:#FFFFFF !important;
  border-color:#B91C1C !important;
  box-shadow:0 12px 24px rgba(185, 28, 28, .22) !important;
}
.page-card {
  background:#FFFFFF !important;
  border:1px solid #FED7AA !important;
  border-radius:24px !important;
  padding:34px 38px !important;
  box-shadow:0 22px 48px rgba(154, 52, 18, .09) !important;
}
.page-card h3 {
  color:#101827 !important;
  font-size:26px !important;
  font-weight:900 !important;
}
.page-card label span {
  background:#FFE7B8 !important;
  color:#7C2D12 !important;
  border-radius:8px !important;
  padding:5px 8px !important;
  font-weight:900 !important;
}
.page-card input,
.page-card textarea {
  border:1px solid #CBD5E1 !important;
  border-radius:8px !important;
  color:#111827 !important;
}
button.primary,
.primary button {
  background:#B91C1C !important;
  border-color:#B91C1C !important;
  color:#FFFFFF !important;
}
button.primary:hover,
.primary button:hover {
  background:#991B1B !important;
  border-color:#991B1B !important;
  box-shadow:0 12px 26px rgba(185, 28, 28, .24) !important;
}
@media (max-width: 760px) {
  #hero {
    flex-direction:column !important;
    align-items:flex-start !important;
    min-height:auto !important;
    padding:22px !important;
  }
  #hero .view-switch {
    width:100% !important;
    max-width:100% !important;
    flex:1 1 auto !important;
  }
  .steps {
    padding:14px !important;
    gap:8px !important;
    overflow-x:auto !important;
  }
  .pill {
    min-width:104px !important;
  }
}

/* Judge-demo UI reset: one clean checkout surface after older style layers. */
.gradio-container {
  max-width:1320px !important;
  padding:28px 30px 36px !important;
}
body {
  background:
    radial-gradient(circle at 12% 10%, rgba(255, 198, 92, .26), transparent 28%),
    radial-gradient(circle at 88% 14%, rgba(199, 32, 32, .10), transparent 24%),
    linear-gradient(180deg, #FFF9DC 0%, #FFF6CB 100%) !important;
}
#hero {
  display:flex !important;
  flex-wrap:nowrap !important;
  align-items:center !important;
  justify-content:space-between !important;
  gap:28px !important;
  min-height:132px !important;
  max-width:100% !important;
  width:100% !important;
  margin:0 auto 24px !important;
  padding:26px 42px !important;
  border-radius:18px !important;
  border:1px solid rgba(255,255,255,.16) !important;
  background:
    linear-gradient(90deg, rgba(20, 45, 13, .95) 0%, rgba(77, 100, 35, .96) 56%, rgba(32, 54, 16, .98) 100%) !important;
  box-shadow:0 22px 52px rgba(46, 53, 18, .22) !important;
  overflow:hidden !important;
}
#hero::after {
  content:"" !important;
  position:absolute !important;
  right:330px !important;
  top:2px !important;
  width:150px !important;
  height:150px !important;
  background:
    radial-gradient(circle at 58% 35%, #8B2F22 0 9px, transparent 10px),
    radial-gradient(circle at 50% 60%, #8B2F22 0 7px, transparent 8px),
    radial-gradient(circle at 74% 66%, #8B2F22 0 7px, transparent 8px),
    linear-gradient(135deg, #FFD36B 0%, #EAA33A 100%) !important;
  clip-path:polygon(10% 8%, 96% 50%, 10% 92%) !important;
  transform:rotate(-8deg) !important;
  opacity:.15 !important;
  filter:none !important;
  animation:none !important;
  pointer-events:none !important;
}
#hero .hero-copy-wrap,
#hero .hero-switch-wrap,
#hero .hero-copy-wrap > *,
#hero .hero-switch-wrap > *,
#hero .hero-copy-wrap .form,
#hero .hero-switch-wrap .form,
#hero .hero-copy-wrap .wrap,
#hero .hero-switch-wrap .wrap {
  background:transparent !important;
  border:none !important;
  box-shadow:none !important;
  padding:0 !important;
  margin:0 !important;
}
#hero .hero-copy-wrap {
  flex:1 1 0 !important;
  min-width:0 !important;
  width:auto !important;
}
#hero .hero-switch-wrap {
  flex:0 0 280px !important;
  min-width:280px !important;
  max-width:280px !important;
  width:280px !important;
  align-self:center !important;
  margin-left:auto !important;
  z-index:2 !important;
}
.hero-copy h1 {
  margin:0 !important;
  color:#FFFFFF !important;
  font-size:34px !important;
  line-height:1.08 !important;
  font-weight:900 !important;
  letter-spacing:0 !important;
}
.hero-copy p {
  margin:10px 0 0 !important;
  color:#FFF2B8 !important;
  font-size:16px !important;
  line-height:1.35 !important;
  font-weight:750 !important;
  letter-spacing:0 !important;
}
#hero .view-switch {
  width:100% !important;
  max-width:100% !important;
  margin:0 !important;
}
#hero .view-switch select,
#hero .view-switch input {
  width:100% !important;
  height:48px !important;
  border-radius:8px !important;
  border:1px solid rgba(255,255,255,.82) !important;
  background:#FFFDF7 !important;
  color:#111827 !important;
  font-size:15px !important;
  font-weight:850 !important;
  box-shadow:0 12px 26px rgba(0,0,0,.13) !important;
}
#view-row {
  display:flex !important;
  align-items:center !important;
  justify-content:flex-end !important;
  width:100% !important;
  max-width:100% !important;
  height:48px !important;
  min-height:48px !important;
  margin:-114px auto 66px !important;
  padding:0 42px !important;
  position:relative !important;
  z-index:20 !important;
  background:transparent !important;
  border:none !important;
  box-shadow:none !important;
  pointer-events:none !important;
  box-sizing:border-box !important;
  overflow:visible !important;
}
#view-row > *,
#view-row .form,
#view-row .wrap,
#view-row .styler {
  background:transparent !important;
  border:none !important;
  box-shadow:none !important;
  padding:0 !important;
  margin:0 !important;
}
#view-row .view-switch {
  width:280px !important;
  max-width:280px !important;
  min-width:280px !important;
  margin:0 !important;
  position:absolute !important;
  right:42px !important;
  top:0 !important;
  pointer-events:auto !important;
  height:48px !important;
  border:1px solid rgba(255,255,255,.82) !important;
  border-radius:8px !important;
  background:#FFFDF7 !important;
  box-shadow:0 12px 26px rgba(0,0,0,.13) !important;
  overflow:visible !important;
}
#view-row .view-switch label {
  display:none !important;
}
#view-row .view-switch *,
#view-row .view-switch button {
  color:#111827 !important;
  font-weight:850 !important;
}
#view-row .view-switch .wrap,
#view-row .view-switch [role="combobox"] {
  min-height:48px !important;
  height:48px !important;
  display:flex !important;
  align-items:center !important;
}
#view-row .view-switch select,
#view-row .view-switch input {
  width:100% !important;
  height:48px !important;
  min-height:48px !important;
  line-height:48px !important;
  padding-top:0 !important;
  padding-bottom:0 !important;
  border-radius:8px !important;
  border:none !important;
  background:transparent !important;
  color:#111827 !important;
  font-size:15px !important;
  font-weight:850 !important;
  box-shadow:none !important;
}
#main-tabs,
#main-tabs > .block,
#main-tabs > .form,
#main-tabs > .wrap,
#main-tabs > .styler,
#main-tabs > div {
  background:transparent !important;
  border:none !important;
  box-shadow:none !important;
  padding:0 !important;
  margin-left:auto !important;
  margin-right:auto !important;
  width:100% !important;
  max-width:100% !important;
}
.checkout-tracker {
  position:relative !important;
  display:grid !important;
  grid-template-columns:repeat(4, minmax(0, 1fr)) !important;
  align-items:center !important;
  gap:10px !important;
  margin:0 0 18px !important;
  padding:14px 20px !important;
  min-height:74px !important;
  background:#FFFDF7 !important;
  border:1px solid #FFD08A !important;
  border-radius:12px !important;
  box-shadow:0 14px 30px rgba(149, 68, 13, .10) !important;
}
.checkout-tracker::before {
  content:"" !important;
  position:absolute !important;
  left:11% !important;
  right:11% !important;
  top:50% !important;
  height:4px !important;
  transform:translateY(-50%) !important;
  background:linear-gradient(90deg, #FFD08A, #F97316, #FFD08A) !important;
  opacity:.55 !important;
  z-index:0 !important;
}
.tracker-step {
  position:relative !important;
  z-index:1 !important;
  display:flex !important;
  align-items:center !important;
  justify-content:center !important;
  gap:9px !important;
  min-width:0 !important;
  color:#475569 !important;
  font-weight:850 !important;
}
.tracker-dot {
  width:34px !important;
  height:34px !important;
  min-width:34px !important;
  border-radius:50% !important;
  display:flex !important;
  align-items:center !important;
  justify-content:center !important;
  background:#FFFFFF !important;
  border:2px solid #F59E0B !important;
  color:#7C2D12 !important;
  font-size:14px !important;
  font-weight:900 !important;
  box-shadow:0 4px 10px rgba(146, 64, 14, .10) !important;
}
.tracker-label {
  overflow:hidden !important;
  text-overflow:ellipsis !important;
  white-space:nowrap !important;
  font-size:15px !important;
  letter-spacing:0 !important;
  background:#FFFDF7 !important;
  border-radius:6px !important;
  padding:0 6px !important;
}
.tracker-step.is-done .tracker-dot {
  background:#61722F !important;
  border-color:#61722F !important;
  color:#FFFFFF !important;
}
.tracker-step.is-active .tracker-dot {
  background:#C81E1E !important;
  border-color:#C81E1E !important;
  color:#FFFFFF !important;
  box-shadow:0 10px 22px rgba(200, 30, 30, .24) !important;
}
.tracker-step.is-active .tracker-label {
  color:#111827 !important;
}
.page-card {
  background:#FFFDF7 !important;
  border:1px solid #FFD08A !important;
  border-radius:12px !important;
  padding:34px 38px !important;
  min-height:0 !important;
  box-shadow:0 18px 42px rgba(149, 68, 13, .11) !important;
}
.page-card > .block,
.page-card .form,
.page-card .styler,
.page-card .wrap,
.page-card fieldset {
  background:transparent !important;
  border:none !important;
  box-shadow:none !important;
}
.page-card h3 {
  margin:0 0 26px !important;
  color:#101827 !important;
  font-size:28px !important;
  line-height:1.16 !important;
  font-weight:900 !important;
  letter-spacing:0 !important;
}
.page-card label span {
  background:#FFE2A8 !important;
  color:#9A3412 !important;
  border-radius:7px !important;
  padding:5px 8px !important;
  font-weight:900 !important;
  letter-spacing:0 !important;
}
.page-card input,
.page-card textarea,
.page-card select {
  min-height:48px !important;
  border:1px solid #D4B483 !important;
  border-radius:8px !important;
  background:#FFFFFF !important;
  color:#111827 !important;
  font-size:15px !important;
  font-weight:650 !important;
}
.page-card input::placeholder,
.page-card textarea::placeholder {
  color:#8B95A7 !important;
}
button.primary,
.primary button {
  min-height:50px !important;
  border-radius:8px !important;
  background:#C81E1E !important;
  border-color:#C81E1E !important;
  color:#FFFFFF !important;
  font-weight:900 !important;
  letter-spacing:0 !important;
}
button.primary:hover,
.primary button:hover {
  background:#A91414 !important;
  border-color:#A91414 !important;
  transform:translateY(-1px) !important;
  box-shadow:0 12px 26px rgba(200, 30, 30, .22) !important;
}
.menu-list {
  grid-template-columns:repeat(3, minmax(210px, 1fr)) !important;
  gap:14px !important;
}
.ml-cat {
  border:1px solid #F2D3A1 !important;
  border-radius:10px !important;
  background:#FFFFFF !important;
  box-shadow:0 8px 20px rgba(149, 68, 13, .06) !important;
}
.ml-cat-title {
  color:#61722F !important;
  border-bottom:1px solid #F5E3C5 !important;
}
.ml-row {
  min-height:34px !important;
  color:#1F2937 !important;
}
.ml-num {
  background:#FFE2A8 !important;
  color:#7C2D12 !important;
}
.ml-price,
.bill-row span:last-child {
  font-variant-numeric:tabular-nums !important;
  font-feature-settings:"tnum" !important;
  text-align:right !important;
}
.payment-list {
  grid-template-columns:minmax(260px, 440px) !important;
  max-width:470px !important;
}
.bill-card {
  max-width:620px !important;
  border:1px solid #E7C98E !important;
  border-radius:10px !important;
  background:#FFFFFF !important;
  box-shadow:0 14px 34px rgba(17,24,39,.07) !important;
}
.promo-strip {
  background:#FFF2B8 !important;
  border:1px solid #F6C453 !important;
  color:#7C2D12 !important;
  border-radius:8px !important;
}
.bill-section {
  background:#FFFDF7 !important;
  border:1px solid #F1E0C5 !important;
}
.bill-row {
  grid-template-columns:minmax(0, 1fr) 134px !important;
}
.bill-row.total {
  color:#101827 !important;
}
.confirmation-card {
  max-width:620px !important;
}
.err {
  border-radius:8px !important;
  border-left-color:#C81E1E !important;
}
#hero {
  margin-bottom:8px !important;
}
#view-row {
  margin:-104px auto 44px !important;
}
.checkout-tracker {
  margin-bottom:14px !important;
}
.page-card {
  padding-top:28px !important;
}
.header-row {
  align-items:flex-start !important;
  margin-bottom:18px !important;
}
.header-row h3 {
  line-height:44px !important;
}
.icon-wrap {
  padding-top:0 !important;
}
button.back-btn-custom {
  margin-top:0 !important;
}
#view-row,
#view-row *,
#view-row .view-switch,
#view-row .view-switch *,
#view-row .view-switch input,
#view-row .view-switch button {
  cursor:pointer !important;
  caret-color:transparent !important;
}
#view-row .view-switch {
  height:46px !important;
  max-height:46px !important;
}
#view-row .view-switch .wrap,
#view-row .view-switch [role="combobox"],
#view-row .view-switch input {
  height:46px !important;
  min-height:46px !important;
  line-height:46px !important;
}
.payment-grid {
  display:grid !important;
  grid-template-columns:minmax(280px, 420px) minmax(360px, 1fr) !important;
  gap:28px !important;
  align-items:start !important;
}
.payment-left,
.payment-right,
.payment-left > *,
.payment-right > * {
  min-width:0 !important;
}
.payment-right {
  background:#FFFFFF !important;
  border:1px solid #F2D3A1 !important;
  border-radius:12px !important;
  padding:18px !important;
  box-shadow:0 10px 24px rgba(149, 68, 13, .06) !important;
}
.payment-list {
  max-width:100% !important;
}
.qr-box {
  display:flex !important;
  align-items:center !important;
  gap:18px !important;
  padding:12px !important;
  border:1px dashed #DDA15E !important;
  border-radius:10px !important;
  background:#FFFDF7 !important;
}
.qr-box img {
  width:150px !important;
  height:150px !important;
  border-radius:8px !important;
  background:#FFFFFF !important;
  padding:8px !important;
  border:1px solid #F1E0C5 !important;
}
.qr-box p,
.pay-hint {
  color:#64748B !important;
  font-weight:700 !important;
  margin:0 !important;
}
.pay-hint {
  padding:18px !important;
  background:#FFF7D6 !important;
  border:1px solid #F6C453 !important;
  border-radius:10px !important;
}
.pay-hint.warn {
  color:#991B1B !important;
  background:#FEF2F2 !important;
  border-color:#FCA5A5 !important;
}
.cash-return {
  display:flex !important;
  justify-content:space-between !important;
  align-items:center !important;
  padding:16px 18px !important;
  background:#ECFDF5 !important;
  border:1px solid #10B981 !important;
  border-radius:10px !important;
  color:#065F46 !important;
}
.cash-return span {
  font-weight:850 !important;
}
.cash-return b {
  font-size:22px !important;
  font-variant-numeric:tabular-nums !important;
}
.final-grid {
  display:grid !important;
  grid-template-columns:minmax(420px, 1fr) minmax(340px, 420px) !important;
  gap:24px !important;
  align-items:start !important;
}
.final-grid:not(:has(.confirmation-card)) {
  display:none !important;
}
.final-grid:has(.confirmation-card) {
  display:grid !important;
  margin-top:0 !important;
}
.page-card:has(.final-grid .confirmation-card) {
  padding-top:12px !important;
}
.final-left,
.final-actions {
  min-width:0 !important;
}
.final-actions {
  background:#FFFFFF !important;
  border:1px solid #F2D3A1 !important;
  border-radius:12px !important;
  padding:16px !important;
  box-shadow:0 10px 24px rgba(149, 68, 13, .06) !important;
}
.final-actions button,
.final-actions a {
  width:100% !important;
  margin:0 0 12px !important;
}
.final-actions .bill-card {
  width:100% !important;
  max-width:none !important;
  margin:14px 0 0 !important;
  padding:14px !important;
  box-shadow:none !important;
}
.final-actions .receipt-meta {
  flex-direction:column !important;
  gap:4px !important;
  font-size:12px !important;
}
.final-actions .bill-row {
  grid-template-columns:minmax(0, 1fr) 84px !important;
  gap:10px !important;
  font-size:13px !important;
}
.final-actions .bill-row.total {
  font-size:16px !important;
}
.final-actions .bill-row.total span:last-child {
  font-size:18px !important;
}
.confirmation-card {
  padding:28px !important;
  text-align:center !important;
}
.receipt-meta {
  display:flex !important;
  justify-content:space-between !important;
  gap:16px !important;
  padding:0 0 14px !important;
  margin-bottom:14px !important;
  border-bottom:1px dashed #E5E7EB !important;
  color:#475569 !important;
  font-size:14px !important;
}
.receipt-meta b {
  color:#101827 !important;
}
.discount-grid {
  display:grid !important;
  grid-template-columns:repeat(2, minmax(220px, 1fr)) !important;
  gap:18px !important;
  align-items:end !important;
  margin:18px 0 !important;
}
#hero {
  height:150px !important;
  min-height:150px !important;
  max-height:150px !important;
  position:relative !important;
}
#hero .hero-copy-wrap,
#hero .hero-switch-wrap {
  min-height:0 !important;
  height:auto !important;
  display:flex !important;
  flex-direction:column !important;
  justify-content:center !important;
}
#hero .hero-copy-wrap {
  align-items:flex-start !important;
  padding-right:340px !important;
}
#hero .hero-switch-wrap {
  align-items:stretch !important;
  position:absolute !important;
  right:42px !important;
  top:50% !important;
  transform:translateY(-50%) !important;
  height:48px !important;
  min-height:48px !important;
  max-height:48px !important;
}
#main-tabs > *,
#main-tabs > * > *,
#main-tabs > * > * > *,
#main-tabs [class*="group"],
#main-tabs [class*="panel"],
#main-tabs [class*="tabs"] {
  background:transparent !important;
  border:none !important;
  box-shadow:none !important;
}
#main-tabs .checkout-tracker {
  background:#FFFDF7 !important;
  border:1px solid #FFD08A !important;
  box-shadow:0 14px 30px rgba(149, 68, 13, .10) !important;
}
#main-tabs .page-card {
  background:#FFFDF7 !important;
  border:1px solid #FFD08A !important;
  box-shadow:0 18px 42px rgba(149, 68, 13, .11) !important;
}
#main-tabs .ml-cat,
#main-tabs .bill-card,
#main-tabs .kpi-table {
  background:#FFFFFF !important;
}

/* Final Stage 2 visual pass */
#view-row .view-switch {
  width:340px !important;
  max-width:340px !important;
  min-width:340px !important;
  height:56px !important;
  max-height:56px !important;
  right:42px !important;
  top:50% !important;
  transform:translateY(-50%) !important;
  background:#B7F34A !important;
  border:2px solid #8FD42E !important;
  border-radius:10px !important;
  box-shadow:0 14px 28px rgba(57, 93, 20, .24) !important;
  overflow:hidden !important;
}
#view-row .view-switch .wrap,
#view-row .view-switch [role="combobox"],
#view-row .view-switch input,
#view-row .view-switch select {
  height:56px !important;
  min-height:56px !important;
  line-height:56px !important;
  background:#B7F34A !important;
  border:none !important;
  box-shadow:none !important;
  color:#101827 !important;
  font-size:16px !important;
  font-weight:900 !important;
  text-align:center !important;
  cursor:pointer !important;
}
#view-row .view-switch input,
#view-row .view-switch select {
  padding:0 58px 0 58px !important;
}
#view-row .view-switch button {
  position:absolute !important;
  right:14px !important;
  top:50% !important;
  transform:translateY(-50%) !important;
  width:36px !important;
  height:36px !important;
  min-width:36px !important;
  margin:0 !important;
  background:transparent !important;
  border:none !important;
  box-shadow:none !important;
  cursor:pointer !important;
}
#view-row .view-switch svg {
  width:24px !important;
  height:24px !important;
  color:#101827 !important;
  stroke-width:3px !important;
}

.customer-field-row {
  display:grid !important;
  grid-template-columns:260px minmax(0, 1fr) !important;
  gap:20px !important;
  align-items:center !important;
  margin:14px 0 !important;
}
.customer-field-row > *,
.customer-field-row .form,
.customer-field-row .block,
.customer-field-row .wrap {
  min-width:0 !important;
}
.customer-field-label {
  width:100% !important;
  color:#2E4B17 !important;
  font-size:16px !important;
  font-weight:900 !important;
  line-height:1.25 !important;
  text-align:right !important;
}
.customer-field-row label span {
  background:#DDFCC0 !important;
  color:#2E4B17 !important;
}

#main-tabs .checkout-tracker {
  background:#FFFDF7 !important;
  border:1px solid #CFE8A6 !important;
  border-radius:12px !important;
  box-shadow:0 12px 28px rgba(77, 107, 41, .12) !important;
}
#main-tabs .checkout-tracker::before {
  background:#DCE9C5 !important;
  opacity:1 !important;
}
.tracker-dot {
  background:#FFFFFF !important;
  border-color:#D4DEC0 !important;
  color:#52606D !important;
}
.tracker-step.is-done .tracker-dot {
  background:#8FDB3B !important;
  border-color:#8FDB3B !important;
  color:#172033 !important;
}
.tracker-step.is-active .tracker-dot {
  background:#F6C343 !important;
  border-color:#F6C343 !important;
  color:#172033 !important;
  box-shadow:0 10px 22px rgba(246, 195, 67, .32) !important;
}
.tracker-step.is-active .tracker-label {
  color:#172033 !important;
  font-weight:900 !important;
}

button.primary,
.primary button {
  background:#F6C343 !important;
  border-color:#F6C343 !important;
  color:#172033 !important;
  box-shadow:0 10px 22px rgba(246, 195, 67, .18) !important;
}
button.primary:hover,
.primary button:hover {
  background:#E7B230 !important;
  border-color:#E7B230 !important;
  box-shadow:0 12px 26px rgba(231, 178, 48, .24) !important;
}

/* Hero and details form final layout */
#hero {
  display:grid !important;
  grid-template-columns:minmax(0, 1fr) 320px !important;
  align-items:center !important;
  gap:32px !important;
  height:auto !important;
  min-height:142px !important;
  max-height:none !important;
  margin:0 auto 18px !important;
  padding:26px 40px !important;
  border-radius:18px !important;
  background:
    radial-gradient(circle at 73% 48%, rgba(246, 195, 67, .16), transparent 17%),
    linear-gradient(105deg, #183613 0%, #31531B 48%, #1F3A13 100%) !important;
  box-shadow:0 18px 42px rgba(24, 54, 19, .20) !important;
  position:relative !important;
  z-index:50 !important;
  overflow:visible !important;
}
#hero::after {
  right:290px !important;
  top:-4px !important;
  width:132px !important;
  height:132px !important;
  opacity:.12 !important;
}
#hero .hero-copy-wrap,
#hero .hero-switch-wrap {
  position:relative !important;
  right:auto !important;
  top:auto !important;
  transform:none !important;
  min-height:0 !important;
  height:auto !important;
  max-height:none !important;
  width:auto !important;
  max-width:none !important;
  padding:0 !important;
  margin:0 !important;
  background:transparent !important;
  border:none !important;
  box-shadow:none !important;
}
#hero .hero-copy-wrap {
  align-items:flex-start !important;
}
#hero .hero-switch-wrap {
  align-items:stretch !important;
  justify-content:center !important;
  z-index:3 !important;
}
#hero .view-switch {
  width:100% !important;
  max-width:320px !important;
  min-width:0 !important;
  margin:0 !important;
  height:52px !important;
  background:#FFF7E6 !important;
  border:1px solid rgba(255, 211, 138, .95) !important;
  border-radius:12px !important;
  box-shadow:0 12px 28px rgba(0, 0, 0, .18) !important;
  overflow:visible !important;
  z-index:60 !important;
  cursor:pointer !important;
}
#hero .view-switch label {
  display:none !important;
}
#hero .view-switch .wrap,
#hero .view-switch [role="combobox"],
#hero .view-switch input,
#hero .view-switch select {
  height:52px !important;
  min-height:52px !important;
  line-height:52px !important;
  background:#FFF7E6 !important;
  border:none !important;
  box-shadow:none !important;
  color:#101827 !important;
  font-size:16px !important;
  font-weight:900 !important;
  cursor:pointer !important;
}
#hero .view-switch input,
#hero .view-switch select {
  text-align:center !important;
  padding:0 52px 0 24px !important;
  caret-color:transparent !important;
}
#hero .view-switch button {
  position:absolute !important;
  right:12px !important;
  top:50% !important;
  transform:translateY(-50%) !important;
  width:34px !important;
  height:34px !important;
  min-width:34px !important;
  margin:0 !important;
  padding:0 !important;
  background:transparent !important;
  border:none !important;
  box-shadow:none !important;
  cursor:pointer !important;
}
#hero .view-switch svg {
  color:#27421A !important;
  stroke-width:3px !important;
}

#main-tabs .page-card {
  padding:28px 38px 30px !important;
}
.page-card .header-row {
  margin-bottom:12px !important;
}
.page-card .header-row h3 {
  line-height:1.18 !important;
  margin-bottom:0 !important;
}
.customer-field-row {
  grid-template-columns:260px minmax(0, 1fr) !important;
  gap:18px !important;
  margin:10px 0 14px !important;
}
.customer-field-row label {
  display:none !important;
}
.customer-field-row input {
  min-height:50px !important;
}
.customer-field-label {
  text-align:right !important;
}

@media (max-width: 820px) {
  html,
  body,
  gradio-app,
  .gradio-container {
    width:100% !important;
    max-width:100% !important;
    min-width:0 !important;
    overflow-x:hidden !important;
    box-sizing:border-box !important;
  }
  .gradio-container {
    padding:14px 10px 24px !important;
    margin:0 !important;
  }
  #hero {
    flex-direction:column !important;
    align-items:stretch !important;
    min-height:0 !important;
    width:100% !important;
    max-width:100% !important;
    margin:0 0 16px !important;
    padding:22px !important;
    gap:18px !important;
    box-sizing:border-box !important;
  }
  #hero::after {
    display:none !important;
  }
  #hero .hero-copy-wrap,
  #hero .hero-switch-wrap {
    flex:1 1 auto !important;
    width:100% !important;
    min-width:0 !important;
    max-width:100% !important;
    position:static !important;
    transform:none !important;
    height:auto !important;
    padding-right:0 !important;
  }
  #view-row {
    width:100% !important;
    max-width:100% !important;
    height:auto !important;
    min-height:0 !important;
    margin:-4px auto 16px !important;
    padding:0 !important;
    justify-content:stretch !important;
    box-sizing:border-box !important;
  }
  #view-row .view-switch {
    width:100% !important;
    max-width:100% !important;
    min-width:0 !important;
    position:static !important;
  }
  .hero-copy h1 {
    font-size:28px !important;
  }
  .checkout-tracker {
    width:100% !important;
    max-width:100% !important;
    box-sizing:border-box !important;
    grid-template-columns:repeat(2, minmax(0, 1fr)) !important;
    padding:14px !important;
  }
  .checkout-tracker::before {
    display:none !important;
  }
  .tracker-step {
    justify-content:flex-start !important;
  }
  .menu-list {
    grid-template-columns:1fr !important;
  }
  .page-card {
    width:100% !important;
    max-width:100% !important;
    padding:24px 18px !important;
    box-sizing:border-box !important;
  }
  .page-card h3 {
    font-size:24px !important;
  }
  .payment-grid,
  .final-grid,
  .discount-grid {
    grid-template-columns:1fr !important;
  }
  .payment-right,
  .final-actions {
    padding:14px !important;
  }
  .qr-box {
    flex-direction:column !important;
    text-align:center !important;
  }
  .receipt-meta {
    flex-direction:column !important;
    gap:6px !important;
  }
  .bill-row {
    grid-template-columns:minmax(0, 1fr) 112px !important;
  }
}

/* Stage 2 scoped repair: keep only the intended hero/dropdown/details behavior. */
.gradio-container {
  max-width:1280px !important;
  padding:24px 28px 36px !important;
}
#hero {
  display:flex !important;
  flex-direction:row !important;
  align-items:center !important;
  justify-content:space-between !important;
  gap:32px !important;
  width:100% !important;
  min-height:132px !important;
  height:auto !important;
  max-height:none !important;
  margin:0 auto 18px !important;
  padding:26px 38px !important;
  border-radius:18px !important;
  background:
    radial-gradient(circle at 72% 50%, rgba(252, 211, 77, .15), transparent 18%),
    linear-gradient(105deg, #193713 0%, #33551D 52%, #1C3512 100%) !important;
  border:1px solid rgba(255,255,255,.14) !important;
  box-shadow:0 18px 42px rgba(24, 54, 19, .18) !important;
  overflow:visible !important;
}
#hero::after {
  right:350px !important;
  top:0 !important;
  width:128px !important;
  height:128px !important;
  opacity:.12 !important;
  pointer-events:none !important;
}
#hero .hero-copy-wrap,
#hero .hero-switch-wrap,
#hero .hero-copy-wrap > *,
#hero .hero-switch-wrap > *,
#hero .hero-copy-wrap .form,
#hero .hero-switch-wrap .form,
#hero .hero-copy-wrap .wrap,
#hero .hero-switch-wrap .wrap {
  position:static !important;
  transform:none !important;
  right:auto !important;
  top:auto !important;
  width:auto !important;
  height:auto !important;
  min-height:0 !important;
  max-height:none !important;
  padding:0 !important;
  margin:0 !important;
  background:transparent !important;
  border:none !important;
  box-shadow:none !important;
  overflow:visible !important;
}
#hero .hero-copy-wrap {
  flex:1 1 auto !important;
  min-width:0 !important;
}
#hero .hero-switch-wrap {
  flex:0 0 310px !important;
  max-width:310px !important;
  min-width:310px !important;
  display:flex !important;
  align-items:center !important;
  justify-content:center !important;
  z-index:10 !important;
}
#hero .view-switch,
#hero .view-switch > *,
#hero .view-switch .wrap,
#hero .view-switch [role="combobox"] {
  width:100% !important;
  height:auto !important;
  min-height:0 !important;
  max-height:none !important;
  margin:0 !important;
  padding:0 !important;
  background:transparent !important;
  border:none !important;
  box-shadow:none !important;
  overflow:visible !important;
}
#hero .view-switch input,
#hero .view-switch select {
  display:block !important;
  width:100% !important;
  height:50px !important;
  min-height:50px !important;
  line-height:50px !important;
  padding:0 52px 0 18px !important;
  border:1px solid #F0D49B !important;
  border-radius:12px !important;
  background:#FFF8E8 !important;
  color:#101827 !important;
  font-size:16px !important;
  font-weight:900 !important;
  text-align:center !important;
  box-shadow:0 12px 24px rgba(0,0,0,.16) !important;
  cursor:pointer !important;
  caret-color:transparent !important;
}
#hero .view-switch button {
  position:absolute !important;
  right:12px !important;
  top:50% !important;
  transform:translateY(-50%) !important;
  width:32px !important;
  height:32px !important;
  min-width:32px !important;
  padding:0 !important;
  margin:0 !important;
  background:transparent !important;
  border:none !important;
  box-shadow:none !important;
  cursor:pointer !important;
}

#main-tabs {
  margin-top:0 !important;
}
#main-tabs .page-card {
  padding:28px 38px 34px !important;
}
#main-tabs .page-card .header-row {
  margin-bottom:18px !important;
}
#main-tabs .page-card .header-row h3 {
  line-height:1.15 !important;
  margin:0 !important;
}
.customer-field-row {
  display:flex !important;
  align-items:center !important;
  gap:18px !important;
  margin:8px 0 14px !important;
  width:100% !important;
}
.customer-label-col,
.customer-label-col > *,
.customer-control-col,
.customer-control-col > *,
.customer-control-col .form,
.customer-control-col .wrap {
  background:transparent !important;
  border:none !important;
  box-shadow:none !important;
  padding:0 !important;
  margin:0 !important;
  min-height:0 !important;
}
.customer-label-col {
  flex:0 0 260px !important;
  max-width:260px !important;
}
.customer-control-col {
  flex:1 1 auto !important;
  min-width:0 !important;
}
.customer-field-label {
  color:#29491B !important;
  font-size:16px !important;
  font-weight:900 !important;
  text-align:right !important;
  line-height:1.2 !important;
}
.customer-control-col label {
  display:block !important;
  width:100% !important;
  margin:0 !important;
  padding:0 !important;
}
.customer-control-col label > span {
  display:none !important;
}
.customer-control-col input {
  display:block !important;
  width:100% !important;
  min-height:50px !important;
  border:1px solid #DDA15E !important;
  border-radius:8px !important;
  background:#FFFFFF !important;
  color:#101827 !important;
  font-size:15px !important;
  font-weight:700 !important;
  box-shadow:none !important;
}
.customer-control-col input::placeholder {
  color:#8792A3 !important;
}
.page-card > .gr-group:has(.header-row.hide):not(:has(.final-grid)) {
  display:none !important;
  height:0 !important;
  min-height:0 !important;
  margin:0 !important;
  padding:0 !important;
  overflow:hidden !important;
}

#hero .hero-switch-wrap,
#hero .hero-switch-wrap > *,
#hero .hero-switch-wrap .form,
#hero .hero-switch-wrap .wrap,
#hero .view-switch,
#hero .view-switch > *,
#hero .view-switch .wrap,
#hero .view-switch [role="combobox"] {
  height:52px !important;
  min-height:52px !important;
  max-height:52px !important;
}
#hero .hero-switch-wrap {
  align-self:center !important;
}
#hero .view-switch {
  position:relative !important;
}
#hero .view-switch > .hide {
  display:none !important;
  height:0 !important;
  min-height:0 !important;
  max-height:0 !important;
  padding:0 !important;
  margin:0 !important;
  overflow:hidden !important;
}
#hero .view-switch .wrap-inner {
  height:52px !important;
  min-height:52px !important;
  max-height:52px !important;
  padding:6px 12px !important;
  border:1px solid #F0D49B !important;
  border-radius:12px !important;
  background:#FFF8E8 !important;
  box-shadow:0 12px 24px rgba(0,0,0,.16) !important;
}
#hero .view-switch .secondary-wrap {
  height:40px !important;
  min-height:40px !important;
  align-items:center !important;
}
#hero .view-switch input {
  background:transparent !important;
  border:none !important;
  box-shadow:none !important;
  height:40px !important;
  min-height:40px !important;
  line-height:40px !important;
  padding:0 42px 0 12px !important;
}

#main-tabs .page-card:has(.final-grid .confirmation-card) {
  padding-top:12px !important;
}
#main-tabs .page-card:has(.final-grid .confirmation-card) .styler:has(> .final-grid) > .gr-group:first-child,
#main-tabs .page-card:has(.final-grid .confirmation-card) .styler:has(> .final-grid) > .block.hide-container {
  display:none !important;
  height:0 !important;
  min-height:0 !important;
  margin:0 !important;
  padding:0 !important;
  overflow:hidden !important;
}

@media (max-width: 820px) {
  #hero {
    flex-direction:column !important;
    align-items:stretch !important;
    gap:18px !important;
    padding:22px !important;
  }
  #hero::after {
    display:none !important;
  }
  #hero .hero-switch-wrap {
    flex:1 1 auto !important;
    min-width:0 !important;
    max-width:100% !important;
  }
  .customer-field-row {
    flex-direction:column !important;
    align-items:stretch !important;
    gap:8px !important;
  }
  .customer-label-col {
    flex:1 1 auto !important;
    max-width:100% !important;
  }
  .customer-field-label {
    text-align:left !important;
  }
}
"""


def step_pills(active: int) -> str:
    labels = ["Details", "Customize", "Summary", "Pay"]
    steps = []
    for i, label in enumerate(labels):
        step_num = i + 1
        screen_num = i + 2
        state = "is-active" if screen_num == active else "is-done" if screen_num < active else ""
        steps.append(
            f'<div class="tracker-step {state}">'
            f'<span class="tracker-dot">{step_num}</span>'
            f'<span class="tracker-label">{label}</span>'
            f'</div>'
        )
    return f'<div class="checkout-tracker">{"".join(steps)}</div>'


def generate_kpis_html(orders, qty, rev, gst, disc):
    return f"""
    <div style="display: flex; flex-wrap: wrap; gap: 16px; margin-bottom: 24px;">
        <div style="background: rgba(255,255,255,0.7); border: 1px solid rgba(255,255,255,0.9); border-radius: 16px; padding: 16px 20px; flex: 1; min-width: 140px; box-shadow: 0 10px 25px rgba(0,0,0,0.03);">
            <div style="color: #6B7280; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Orders</div>
            <div style="color: #111827; font-size: 28px; font-weight: 700; margin-top: 4px;">{orders}</div>
        </div>
        <div style="background: rgba(255,255,255,0.7); border: 1px solid rgba(255,255,255,0.9); border-radius: 16px; padding: 16px 20px; flex: 1; min-width: 140px; box-shadow: 0 10px 25px rgba(0,0,0,0.03);">
            <div style="color: #6B7280; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Pizzas Sold</div>
            <div style="color: #111827; font-size: 28px; font-weight: 700; margin-top: 4px;">{qty}</div>
        </div>
        <div style="background: rgba(255,255,255,0.7); border: 1px solid rgba(255,255,255,0.9); border-radius: 16px; padding: 16px 20px; flex: 1; min-width: 140px; box-shadow: 0 10px 25px rgba(0,0,0,0.03);">
            <div style="color: #6B7280; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Revenue</div>
            <div style="color: #111827; font-size: 28px; font-weight: 700; margin-top: 4px;">₹{float(rev):,.2f}</div>
        </div>
        <div style="background: rgba(255,255,255,0.7); border: 1px solid rgba(255,255,255,0.9); border-radius: 16px; padding: 16px 20px; flex: 1; min-width: 140px; box-shadow: 0 10px 25px rgba(0,0,0,0.03);">
            <div style="color: #6B7280; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">GST Collected</div>
            <div style="color: #111827; font-size: 28px; font-weight: 700; margin-top: 4px;">₹{float(gst):,.2f}</div>
        </div>
        <div style="background: rgba(255,255,255,0.7); border: 1px solid rgba(255,255,255,0.9); border-radius: 16px; padding: 16px 20px; flex: 1; min-width: 140px; box-shadow: 0 10px 25px rgba(0,0,0,0.03);">
            <div style="color: #6B7280; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Discounts Given</div>
            <div style="color: #111827; font-size: 28px; font-weight: 700; margin-top: 4px;">₹{float(disc):,.2f}</div>
        </div>
    </div>
    """

def df_to_html(df, title=None, scrollable=False):
    title_html = f"<h4>{title}</h4>" if title else ""
    if df.empty:
        return f"<div class='kpi-table'>{title_html}<p>No data</p></div>"
    table_html = df.to_html(index=False, classes="clean-table", border=0)
    scroll_style = "max-height: 400px; overflow-y: auto;" if scrollable else ""
    return f"<div class='kpi-table' style='{scroll_style}'>{title_html}{table_html}</div>"


# --------------------------------------------------------------------------- #
# Gradio app
# --------------------------------------------------------------------------- #

def build_demo() -> gr.Blocks:
    saved_menu_mode = _load_menu_source()
    try:
        if saved_menu_mode == CUSTOM_MENU_MODE:
            default_menu = _load_custom_menu()
        else:
            default_menu = menu_mod.load_menu(MENU_DIR)
        default_menu_err = ""
        initial_menu_mode = saved_menu_mode
    except MenuError:
        try:
            default_menu = menu_mod.load_menu(MENU_DIR)
            default_menu_err = ""
            initial_menu_mode = DEFAULT_MENU_MODE
            _save_menu_source(DEFAULT_MENU_MODE)
        except MenuError as fallback_exc:
            default_menu = None
            default_menu_err = str(fallback_exc)
            initial_menu_mode = DEFAULT_MENU_MODE

    upload_mode_initial = initial_menu_mode == CUSTOM_MENU_MODE

    show = lambda visible: gr.update(visible=visible)

    with gr.Blocks(title=f"{BRAND} · Order") as demo:
        menu_state = gr.State(default_menu)
        order_state = gr.State({})
        up_base_fp = gr.State(None)
        up_pizza_fp = gr.State(None)
        up_topping_fp = gr.State(None)

        with gr.Row(elem_id="hero"):
            with gr.Column(scale=1, min_width=360, elem_classes="hero-copy-wrap"):
                gr.HTML(
                    f'<div class="hero-copy"><h1>&#127829; {BRAND}</h1>'
                    f'<p>Fresh, fast, fairly priced &mdash; order in four quick steps.</p></div>'
                )
            with gr.Column(scale=0, min_width=300, elem_classes="hero-switch-wrap"):
                app_view = gr.Dropdown(
                    ["Customer Ordering", "Admin Dashboard"],
                    value="Customer Ordering",
                    label=None,
                    show_label=False,
                    container=False,
                    filterable=False,
                    elem_classes="view-switch",
                )

        with gr.Column(elem_id="main-tabs"):
            with gr.Group(visible=True) as customer_panel:
                pills = gr.HTML(step_pills(2))

                with gr.Column(elem_classes="page-card"):
                    # ---------- Screen 2: Customer ----------
                    with gr.Group(visible=True) as s2:
                        with gr.Row(elem_classes="header-row"):
                            gr.HTML("<h3>Enter Customer Data</h3>")
                        s2_menu_msg = gr.HTML(
                            "" if default_menu else f'<p class="err">{default_menu_err}</p>',
                            visible=default_menu is None,
                        )
                        with gr.Row(elem_classes="customer-field-row"):
                            with gr.Column(scale=0, min_width=260, elem_classes="customer-label-col"):
                                gr.HTML("<div class='customer-field-label'>Customer's Name :</div>")
                            with gr.Column(scale=1, min_width=360, elem_classes="customer-control-col"):
                                name_in = gr.Textbox(
                                    label="Enter Customer's Name",
                                    show_label=False,
                                    placeholder="Enter Customer's Name",
                                    max_lines=1,
                                )
                        with gr.Row(elem_classes="customer-field-row"):
                            with gr.Column(scale=0, min_width=260, elem_classes="customer-label-col"):
                                gr.HTML("<div class='customer-field-label'>Customer's Phone Number :</div>")
                            with gr.Column(scale=1, min_width=360, elem_classes="customer-control-col"):
                                phone_in = gr.Textbox(
                                    label="Enter Customer's Phone Number",
                                    show_label=False,
                                    placeholder="Enter Customer's Phone Number",
                                    max_lines=1,
                                )
                        s2_msg = gr.HTML("")
                        s2_next = gr.Button("Continue →", variant="primary", interactive=default_menu is not None)

                    # ---------- Screen 3: Customize ----------
                    with gr.Group(visible=False) as s3:
                        with gr.Row(elem_classes="header-row"):
                            with gr.Column(scale=0, min_width=40, elem_classes="icon-wrap"):
                                s3_back = gr.Button("", elem_classes="back-btn-custom")
                            gr.HTML("<h3>Customize your Pizza</h3>")
                        gr.Markdown("Pick by **item number** from the lists below.")
                        menu_list = gr.HTML(render_menu_html(default_menu))
                        with gr.Row():
                            base_num = gr.Textbox(label="Enter base", placeholder="item number, e.g. 3", max_lines=1)
                            pizza_num = gr.Textbox(label="Enter pizza", placeholder="item number, e.g. 7", max_lines=1)
                            topping_num = gr.Textbox(label="Enter topping", placeholder="item number, e.g. 2", max_lines=1)
                            qty_in = gr.Textbox(label="Quantity (1–10)", placeholder="whole number 1–10", max_lines=1)
                        s3_msg = gr.HTML("")
                        s3_calc = gr.Button("Review Order →", variant="primary")

                    # ---------- Screen 4: Summary ----------
                    with gr.Group(visible=False) as s4:
                        with gr.Row(elem_classes="header-row"):
                            with gr.Column(scale=0, min_width=40, elem_classes="icon-wrap"):
                                s4_back = gr.Button("", elem_classes="back-btn-custom")
                            gr.HTML("<h3>Order Summary</h3>")
                        bill_box = gr.HTML(
                            '<div class="bill-empty">Your order summary will appear here.</div>'
                        )
                        s4_next = gr.Button("Proceed to payment →", variant="primary")

                    # ---------- Screen 5: Payment ----------
                    with gr.Group(visible=False) as s5:
                        with gr.Group() as s5_inputs:
                            with gr.Row(elem_classes="header-row"):
                                with gr.Column(scale=0, min_width=40, elem_classes="icon-wrap"):
                                    s5_back = gr.Button("", elem_classes="back-btn-custom")
                                gr.HTML("<h3>Payment</h3>")
                            with gr.Row(elem_classes="payment-grid"):
                                with gr.Column(elem_classes="payment-left"):
                                    gr.Markdown("Pick by **payment number** from the list below.")
                                    gr.HTML(render_payment_html())
                                    pay_mode = gr.Textbox(label="Enter payment mode", placeholder="1, 2, or 3", max_lines=1)

                                with gr.Column(elem_classes="payment-right"):
                                    with gr.Group(visible=False) as cash_details:
                                        gr.Markdown("#### Cash collection")
                                        cash_collected = gr.Textbox(label="Collected cash", placeholder="amount customer gave", max_lines=1)
                                        cash_return = gr.HTML('<div class="pay-hint">Enter collected cash to calculate return.</div>')

                                    with gr.Group(visible=False) as card_details:
                                        gr.Markdown("#### Secure Card Payment")
                                        gr.Textbox(label="Card Number", placeholder="0000 0000 0000 0000", max_lines=1)
                                        with gr.Row():
                                            gr.Textbox(label="Expiry Date", placeholder="MM/YY", max_lines=1)
                                            gr.Textbox(label="CVV", placeholder="123", type="password")

                                    with gr.Group(visible=False) as upi_details:
                                        gr.Markdown("#### UPI Payment")
                                        gr.HTML('<div class="qr-box"><img src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=upi://pay?pa=slicematic@upi&pn=SliceMatic" alt="UPI QR Code"/><p>Scan using Google Pay, PhonePe, or Paytm</p></div>')

                                    payment_hint = gr.HTML('<div class="pay-hint">Select 1 Cash, 2 Card, or 3 UPI to continue.</div>')

                            s5_msg = gr.HTML("")
                            s5_pay = gr.Button("Pay & confirm order", variant="primary")
                        
                        with gr.Row(elem_classes="final-grid") as final_group:
                            with gr.Column(elem_classes="final-left"):
                                confirm_box = gr.HTML("")
                            with gr.Column(elem_classes="final-actions"):
                                s5_view_bill = gr.Button("View bill summary")
                                final_download = gr.DownloadButton("Download bill")
                                s5_new = gr.Button("Place another order")
                                final_bill_box = gr.HTML("")

            with gr.Group(visible=False) as admin_panel:
                with gr.Column(elem_classes="page-card"):
                    with gr.Group(visible=True) as admin_login_group:
                        with gr.Row(elem_classes="header-row"):
                            gr.HTML("<h3>Admin Authentication</h3>")
                        admin_pin = gr.Textbox(type="password", label="Enter Admin PIN to access")
                        pin_btn = gr.Button("Login", variant="primary")
                        pin_msg = gr.HTML("")
                
                    with gr.Group(visible=False) as admin_content_group:
                        with gr.Tabs():
                            with gr.Tab("Menu Configuration"):
                                gr.Markdown("### Choose your menu")
                                menu_mode = gr.Radio(
                                    [DEFAULT_MENU_MODE, CUSTOM_MENU_MODE],
                                    value=initial_menu_mode, label="Menu source",
                                )
                                with gr.Group(visible=upload_mode_initial) as upload_group:
                                    up_base = gr.UploadButton("⬆  Upload Base menu  (.txt)", file_types=[".txt"], elem_classes="up-btn")
                                    up_base_status = gr.Markdown("", elem_classes="up-status")
                                    up_pizza = gr.UploadButton("⬆  Upload Pizza menu  (.txt)", file_types=[".txt"], elem_classes="up-btn")
                                    up_pizza_status = gr.Markdown("", elem_classes="up-status")
                                    up_topping = gr.UploadButton("⬆  Upload Toppings menu  (.txt)", file_types=[".txt"], elem_classes="up-btn")
                                    up_topping_status = gr.Markdown("", elem_classes="up-status")
                                s1_msg = gr.HTML("" if default_menu else f'<p class="err">{default_menu_err}</p>')
                                admin_menu_preview = gr.HTML(render_menu_compare_html(default_menu))
                                s1_next = gr.Button("Update Menu", variant="primary", visible=upload_mode_initial)
                            
                            with gr.Tab("Discount Settings"):
                                gr.Markdown("### Global Discount Rate")
                                with gr.Row(elem_classes="discount-grid"):
                                    discount_in = gr.Number(
                                        value=pricing.get_discount_rate() * 100,
                                        precision=0,
                                        label="Discount %",
                                    )
                                    threshold_in = gr.Number(
                                        value=pricing.get_discount_threshold(),
                                        precision=0,
                                        label="Minimum pizza quantity",
                                    )
                                disc_btn = gr.Button("Save Discount Settings", variant="primary")
                                disc_msg = gr.HTML("")
                                
                            with gr.Tab("Analytics") as tab_analytics:
                                with gr.Row(elem_classes="header-row"):
                                    gr.HTML("<h3>Analytics Dashboard</h3>")
                                    with gr.Column(scale=0, min_width=40, elem_classes="icon-wrap"):
                                        filter_toggle_btn = gr.Button("", elem_classes="icon-btn btn-filter")
                                    with gr.Column(scale=0, min_width=40, elem_classes="icon-wrap"):
                                        analytics_btn = gr.Button("", elem_classes="icon-btn btn-refresh")
                                
                                filter_state = gr.State(False)
                                with gr.Row(elem_classes="filter-row", visible=False) as filter_group:
                                    time_filter = gr.Dropdown(
                                        ["Specific Date", "This Month", "This Year", "All Time"], 
                                        value="All Time", label="Filter Analytics"
                                    )
                                    date_filter = gr.DateTime(include_time=False, label="Select Date (if Specific Date)")
                                
                                kpis_html = gr.HTML(generate_kpis_html(0, 0, 0, 0, 0))
                                
                                top_combos = gr.HTML()
                                
                                gr.Markdown("### Top Sellers")
                                with gr.Row(elem_classes="df-row"):
                                    top_bases = gr.HTML()
                                    top_pizzas = gr.HTML()
                                    top_toppings = gr.HTML()
                                
                            with gr.Tab("Orders Log") as tab_orders:
                                with gr.Row(elem_classes="header-row-right"):
                                    with gr.Column(scale=0, min_width=40, elem_classes="icon-wrap"):
                                        download_btn = gr.DownloadButton("", elem_classes="icon-btn btn-download")
                                raw_orders = gr.HTML()

        screens = [s2, s3, s4, s5]

        def goto(n: int):
            return [show(i + 2 == n) for i in range(4)] + [step_pills(n)]

        bill_placeholder = '<div class="bill-empty">Your order summary will appear here.</div>'
        cash_hint = '<div class="pay-hint">Enter collected cash to calculate return.</div>'
        payment_hint_default = '<div class="pay-hint">Select 1 Cash, 2 Card, or 3 UPI to continue.</div>'

        def switch_main_view(choice):
            show_admin = choice == "Admin Dashboard"
            if show_admin:
                return (
                    gr.update(visible=False),
                    gr.update(visible=True),
                    gr.update(visible=True),
                    gr.update(visible=False),
                    gr.update(value=""),
                    gr.update(value=""),
                    *[gr.update() for _ in range(25)],
                    *[gr.update(visible=False) for _ in screens],
                    gr.update(value=step_pills(2)),
                )
            return (
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(value=""),
                gr.update(value=""),
                {},
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=bill_placeholder),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=cash_hint),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=True, value=payment_hint_default),
                gr.update(visible=True),
                gr.update(visible=True),
                gr.update(value="", visible=True),
                gr.update(visible=True),
                gr.update(value="View bill summary", visible=True),
                gr.update(value="", visible=True),
                gr.update(value=None, visible=True),
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(value=step_pills(2)),
            )

        app_view.change(
            switch_main_view,
            app_view,
            [
                customer_panel, admin_panel,
                admin_login_group, admin_content_group, admin_pin, pin_msg,
                order_state, name_in, phone_in, s2_msg, s3_msg, s5_msg, bill_box,
                base_num, pizza_num, topping_num, qty_in, pay_mode,
                cash_collected, cash_return, cash_details, card_details, upi_details, payment_hint,
                final_group, s5_inputs, confirm_box, s5_new, s5_view_bill, final_bill_box, final_download,
                *screens, pills,
            ],
        )

        def toggle_upload(mode):
            if mode == DEFAULT_MENU_MODE:
                _save_menu_source(DEFAULT_MENU_MODE)
                try:
                    m = menu_mod.load_menu(MENU_DIR)
                    msg = ""
                    can_order = True
                except MenuError as exc:
                    m = None
                    msg = f'<p class="err">{exc}</p>'
                    can_order = False
                return [
                    m,
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(value=msg),
                    gr.update(value=render_menu_compare_html(m)),
                    gr.update(value=render_menu_html(m)),
                gr.update(value=msg, visible=bool(msg)),
                gr.update(interactive=can_order),
            ]
            _save_menu_source(CUSTOM_MENU_MODE)
            try:
                m = _load_custom_menu()
                msg = ""
                can_order = True
            except MenuError:
                try:
                    m = menu_mod.load_menu(MENU_DIR)
                    msg = "<p class='err'>No updated menu saved yet. Upload one or more menu files and click Update Menu.</p>"
                    can_order = True
                except MenuError as exc:
                    m = None
                    msg = f'<p class="err">{exc}</p>'
                    can_order = False
            return [
                m,
                gr.update(visible=True),
                gr.update(visible=True),
                gr.update(value=msg),
                gr.update(value=render_menu_compare_html(m)),
                gr.update(value=render_menu_html(m)),
                gr.update(value="" if can_order else msg, visible=not can_order),
                gr.update(interactive=can_order),
            ]

        menu_mode.change(
            toggle_upload,
            menu_mode,
            [menu_state, upload_group, s1_next, s1_msg, admin_menu_preview, menu_list, s2_menu_msg, s2_next],
        )

        def _took(f):
            path = f.name if hasattr(f, "name") else f
            return path, f"✓ {os.path.basename(path)}"

        up_base.upload(_took, up_base, [up_base_fp, up_base_status])
        up_pizza.upload(_took, up_pizza, [up_pizza_fp, up_pizza_status])
        up_topping.upload(_took, up_topping, [up_topping_fp, up_topping_status])

        def update_menu(mode, fb, fp, ft, current_menu):
            previous_menu = current_menu
            if mode == CUSTOM_MENU_MODE:
                uploads = {
                    menu_mod.BASE_FILE: fb,
                    menu_mod.PIZZA_FILE: fp,
                    menu_mod.TOPPING_FILE: ft,
                }
                if not any(uploads.values()):
                    msg = '<p class="err">Upload at least one menu file to update, or choose the default menu.</p>'
                    customer_msg = "" if current_menu else msg
                    return [
                        current_menu,
                        gr.update(value=msg),
                        gr.update(value=render_menu_html(current_menu)),
                        gr.update(value=render_menu_compare_html(current_menu)),
                        gr.update(value=customer_msg, visible=bool(customer_msg)),
                        gr.update(interactive=current_menu is not None),
                    ]
                tmpdir = tempfile.mkdtemp(prefix="slicematic_menu_")
                if current_menu:
                    _write_menu_file(os.path.join(tmpdir, menu_mod.BASE_FILE), current_menu.bases)
                    _write_menu_file(os.path.join(tmpdir, menu_mod.PIZZA_FILE), current_menu.pizzas)
                    _write_menu_file(os.path.join(tmpdir, menu_mod.TOPPING_FILE), current_menu.toppings)
                else:
                    for filename, src_path in _menu_file_paths(MENU_DIR).items():
                        shutil.copyfile(src_path, os.path.join(tmpdir, filename))
                for dest, src in uploads.items():
                    if not src:
                        continue
                    src_path = src.name if hasattr(src, "name") else src
                    shutil.copyfile(src_path, os.path.join(tmpdir, dest))
                load_dir = tmpdir
            else:
                load_dir = MENU_DIR
            try:
                m = menu_mod.load_menu(load_dir)
            except MenuError as exc:
                msg = f'<p class="err">{exc}</p>'
                customer_msg = "" if current_menu else msg
                return [
                    current_menu,
                    gr.update(value=msg),
                    gr.update(value=render_menu_html(current_menu)),
                    gr.update(value=render_menu_compare_html(current_menu)),
                    gr.update(value=customer_msg, visible=bool(customer_msg)),
                    gr.update(interactive=current_menu is not None),
                ]
            if mode == CUSTOM_MENU_MODE:
                _persist_menu(m)
                _save_menu_source(CUSTOM_MENU_MODE)
            return [
                m,
                gr.update(value="<p style='color:#10B981;font-weight:bold;'>Menu updated successfully!</p>"),
                gr.update(value=render_menu_html(m)),
                gr.update(value=render_menu_diff_html(previous_menu, m)),
                gr.update(value="", visible=False),
                gr.update(interactive=True),
            ]

        admin_menu_inputs = [menu_mode, up_base_fp, up_pizza_fp, up_topping_fp, menu_state]
        s1_next.click(update_menu, admin_menu_inputs, [menu_state, s1_msg, menu_list, admin_menu_preview, s2_menu_msg, s2_next])

        # --- Screen 2 logic ---
        def submit_customer(name, phone, order, m):
            if not m:
                msg = '<span class="err">Menu not loaded. Please ask admin to upload valid Base, Pizza, and Topping menu files.</span>'
                return [order, gr.update(value=msg)] + goto(2)
            ok_n, name_v = v.validate_name(name)
            ok_p, phone_v = v.validate_phone(phone)
            if not (ok_n and ok_p):
                errs = [m for ok, m in ((ok_n, name_v), (ok_p, phone_v)) if not ok]
                msg = "<br>".join(f'<span class="err">• {e}</span>' for e in errs)
                return [order, gr.update(value=msg)] + goto(2)
            order = dict(order)
            order.update(name=name_v, phone=phone_v, status="started",
                         timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            return [order, gr.update(value="")] + goto(3)

        s2_next.click(submit_customer, [name_in, phone_in, order_state, menu_state],
                      [order_state, s2_msg, *screens, pills])
        
        # --- Admin Logic ---
        def admin_login(pin):
            if pin == "123456":
                return gr.update(visible=False), gr.update(visible=True), gr.update(value="")
            return gr.update(visible=True), gr.update(visible=False), gr.update(value='<p class="err">Invalid PIN</p>')
        
        def update_discount(rate, threshold):
            try:
                rate_f = float(rate)
                threshold_i = int(threshold)
                if rate_f < 0 or rate_f > 100:
                    raise ValueError("Discount % must be between 0 and 100.")
                pricing.set_discount_rate(rate_f / 100.0)
                pricing.set_discount_threshold(threshold_i)
            except (TypeError, ValueError) as exc:
                return f'<p class="err">{exc}</p>'
            return (
                "<p style='color:#10B981;font-weight:bold;'>"
                f"Discount updated to {rate_f:.0f}% for orders with {threshold_i}+ pizzas."
                "</p>"
            )
            
        disc_btn.click(update_discount, [discount_in, threshold_in], disc_msg)
        disc_btn.click(update_discount, [discount_in, threshold_in], disc_msg)
        
        def refresh_analytics(f_type, f_date):
            data = analytics.get_analytics(f_type, f_date)
            csv_path = os.path.join(tempfile.gettempdir(), "slicematic_orders_export.csv")
            data["orders_df"].to_csv(csv_path, index=False)
            kpi_html = generate_kpis_html(
                data["total_orders"], data["total_qty"], data["revenue"], data["gst"], data["discount"]
            )
            return (
                kpi_html,
                df_to_html(data["top_bases"], "Top Bases"),
                df_to_html(data["top_pizzas"], "Top Pizzas"),
                df_to_html(data["top_toppings"], "Top Toppings"),
                df_to_html(data["top_combos"], "Top Combos"),
                df_to_html(data["orders_df"], scrollable=True),
                csv_path
            )
            
        pin_btn.click(
            admin_login, admin_pin, [admin_login_group, admin_content_group, pin_msg]
        ).success(
            refresh_analytics, [time_filter, date_filter], 
            [kpis_html, top_bases, top_pizzas, top_toppings, top_combos, raw_orders, download_btn]
        )
            
        def toggle_vis(vis):
            return not vis, gr.update(visible=not vis)
            
        filter_toggle_btn.click(toggle_vis, filter_state, [filter_state, filter_group])
            
        analytics_btn.click(
            refresh_analytics, [time_filter, date_filter], 
            [kpis_html, top_bases, top_pizzas, top_toppings, top_combos, raw_orders, download_btn]
        )
        tab_analytics.select(
            refresh_analytics, [time_filter, date_filter], 
            [kpis_html, top_bases, top_pizzas, top_toppings, top_combos, raw_orders, download_btn]
        )
        tab_orders.select(
            refresh_analytics, [time_filter, date_filter], 
            [kpis_html, top_bases, top_pizzas, top_toppings, top_combos, raw_orders, download_btn]
        )

        # --- Screen 3 logic ---
        def view_bill(base_raw, pizza_raw, topping_raw, qty_raw, m, order):
            if not m:
                return [order, gr.update(value='<span class="err">Menu not loaded — go back to step 1.</span>'), gr.update()] + goto(3)
            ok_b, b = v.validate_selection(base_raw, len(m.bases))
            ok_p, p = v.validate_selection(pizza_raw, len(m.pizzas))
            ok_t, t = v.validate_selection(topping_raw, len(m.toppings))
            ok_q, q = v.validate_quantity(qty_raw)
            errs = []
            if not ok_b: errs.append(f"Base — {b}")
            if not ok_p: errs.append(f"Pizza — {p}")
            if not ok_t: errs.append(f"Topping — {t}")
            if not ok_q: errs.append(q)
            if errs:
                msg = "<br>".join(f'<span class="err">• {e}</span>' for e in errs)
                return [order, gr.update(value=msg), gr.update()] + goto(3)
            base, pizza, topping = m.bases[b - 1], m.pizzas[p - 1], m.toppings[t - 1]
            bill = pricing.compute_bill(base, pizza, topping, q)
            order = dict(order)
            order.update(base=base, pizza=pizza, topping=topping, quantity=q, bill=bill, status="menu_selected")
            return [order, gr.update(value=""), gr.update(value=bill_html(bill))] + goto(4)

        s3_calc.click(view_bill, [base_num, pizza_num, topping_num, qty_in, menu_state, order_state],
                      [order_state, s3_msg, bill_box, *screens, pills])
        s3_back.click(lambda: goto(2), None, [*screens, pills])

        # --- Screen 4 logic ---
        def to_payment(order):
            order = dict(order)
            order["status"] = "payment_selected"
            order["bill_visible"] = False
            return (
                [order]
                + goto(5)
                + [
                    gr.update(visible=True),
                    gr.update(visible=True),
                    gr.update(value="", visible=True),
                    gr.update(visible=True),
                    gr.update(value="View bill summary", visible=True),
                    gr.update(value="", visible=True),
                    gr.update(value=None, visible=True),
                    gr.update(value=""),
                    gr.update(value=""),
                    gr.update(value=cash_hint),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=True, value=payment_hint_default),
                    gr.update(value=""),
                ]
            )

        s4_next.click(
            to_payment,
            order_state,
            [
                order_state, *screens, pills,
                s5_inputs, final_group, confirm_box, s5_new, s5_view_bill,
                final_bill_box, final_download, pay_mode, cash_collected, cash_return,
                cash_details, card_details, upi_details, payment_hint, s5_msg,
            ],
        )
        s4_back.click(lambda: goto(3), None, [*screens, pills])

        # --- Screen 5 logic ---
        def cash_return_html(collected_raw, order):
            bill = (order or {}).get("bill")
            if not bill:
                return '<div class="pay-hint">Build an order before calculating cash return.</div>'
            try:
                collected = float(str(collected_raw).replace(",", "").strip())
            except (TypeError, ValueError):
                return '<div class="pay-hint">Enter collected cash to calculate return.</div>'
            change = collected - bill.total
            if change < 0:
                return (
                    '<div class="pay-hint warn">'
                    f"Short by ₹{_money(abs(change))}. Collect at least ₹{_money(bill.total)}."
                    "</div>"
                )
            return f'<div class="cash-return"><span>Return cash</span><b>₹{_money(change)}</b></div>'

        def toggle_payment_ui(mode):
            ok, mode_v = v.validate_payment(mode)
            if not ok:
                return (
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=True, value='<div class="pay-hint">Select 1 Cash, 2 Card, or 3 UPI to continue.</div>'),
                    gr.update(value='<div class="pay-hint">Enter collected cash to calculate return.</div>'),
                )
            return (
                gr.update(visible=(mode_v == "Cash")),
                gr.update(visible=(mode_v == "Card")),
                gr.update(visible=(mode_v == "UPI")),
                gr.update(visible=False),
                gr.update(value='<div class="pay-hint">Enter collected cash to calculate return.</div>'),
            )
            
        pay_mode.change(
            toggle_payment_ui,
            inputs=[pay_mode],
            outputs=[cash_details, card_details, upi_details, payment_hint, cash_return],
        )
        cash_collected.change(cash_return_html, [cash_collected, order_state], cash_return)
        s5_back.click(lambda: goto(4), None, [*screens, pills])

        def pay(mode, collected_raw, order):
            def pay_error(message):
                return (
                    order,
                    gr.update(value=message),
                    gr.update(value="", visible=True),
                    gr.update(visible=True),
                    gr.update(visible=True),
                    gr.update(visible=True),
                    gr.update(value="View bill summary", visible=True),
                    gr.update(value="", visible=True),
                    gr.update(value=None, visible=True),
                    gr.update(value=step_pills(5)),
                )

            ok, mode_v = v.validate_payment(mode)
            if not ok:
                return pay_error(f'<span class="err">{mode_v}</span>')
            bill = order.get("bill")
            if not bill:
                return pay_error('<span class="err">No bill found — please rebuild your order.</span>')
            order = dict(order)
            collected = None
            change = None
            if mode_v == "Cash":
                try:
                    collected = float(str(collected_raw).replace(",", "").strip())
                except (TypeError, ValueError):
                    return pay_error('<span class="err">Enter collected cash amount.</span>')
                change = collected - bill.total
                if change < 0:
                    return pay_error(f'<span class="err">Collected cash is short by ₹{_money(abs(change))}.</span>')
            order["status"] = "payment_in_progress"
            ts, order_no = persistence.append_order(
                name=order["name"], phone=order["phone"], bill=bill,
                payment_mode=mode_v, timestamp=order.get("timestamp"),
            )
            order.update(
                status="ordered",
                order_no=order_no,
                order_timestamp=ts,
                payment_mode=mode_v,
                cash_collected=collected,
                cash_return=change,
                bill_visible=False,
            )
            receipt_path = os.path.join(tempfile.gettempdir(), f"slicematic_{order_no}_receipt.txt")
            with open(receipt_path, "w", encoding="utf-8") as fh:
                fh.write(receipt_text(order))
            order["receipt_path"] = receipt_path
            note = {"Cash": "Cash collected at counter.", "Card": "Card payment confirmed.",
                    "UPI": "UPI payment confirmed."}[mode_v]
            cash_line = (
                f'<div class="bill-row"><span>Collected cash</span><span>₹{_money(collected)}</span></div>'
                f'<div class="bill-row"><span>Return cash</span><span>₹{_money(change)}</span></div>'
                if mode_v == "Cash"
                else ""
            )
            html = (f'<div class="bill-card confirmation-card">'
                    f'<div class="check-wrapper"><svg class="checkmark" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 52"><circle class="checkmark__circle" cx="26" cy="26" r="25" fill="none"/><path class="checkmark__check" fill="none" d="M14.1 27.2l7.1 7.2 16.7-16.8"/></svg></div>'
                    f'<div style="font-size:24px;font-weight:800;color:#10B981;margin-top:16px">Order confirmed</div>'
                    f'<div style="color:#6B7280;margin:8px 0 20px;font-size:15px">Order ID <b>{order_no}</b></div>'
                    f'<div class="bill-row"><span>Paying via {mode_v}</span><span style="font-weight:600;color:#111827">₹{_money(bill.total)}</span></div>'
                    f'{cash_line}'
                    f'<div class="bl muted"><span>{note}</span><span></span></div>'
                    f'<div class="bl total" style="justify-content:center;border:none;padding-top:20px;margin-top:10px">'
                    f'<span>Thanks, {order["name"]}! 🍕</span></div></div>')
            return (order, gr.update(value=""), gr.update(value=html, visible=True),
                    gr.update(visible=True), gr.update(visible=False), gr.update(visible=True),
                    gr.update(value="View bill summary", visible=True), gr.update(value="", visible=True),
                    gr.update(value=receipt_path, visible=True),
                    gr.update(value=step_pills(6)))

        s5_pay.click(pay, [pay_mode, cash_collected, order_state],
                     [order_state, s5_msg, confirm_box, s5_new, s5_inputs, final_group,
                      s5_view_bill, final_bill_box, final_download, pills])

        def show_final_bill(order):
            order = dict(order or {})
            bill = order.get("bill")
            if not bill:
                return (
                    order,
                    gr.update(value="View bill summary", visible=True),
                    gr.update(value='<span class="err">No bill found.</span>', visible=True),
                )
            if order.get("bill_visible"):
                order["bill_visible"] = False
                return (
                    order,
                    gr.update(value="View bill summary", visible=True),
                    gr.update(value="", visible=True),
                )
            order["bill_visible"] = True
            return (
                order,
                gr.update(value="Hide bill summary", visible=True),
                gr.update(value=bill_html(bill, compact=True, order=order, show_promo=False), visible=True),
            )

        s5_view_bill.click(show_final_bill, order_state, [order_state, s5_view_bill, final_bill_box])

        bill_placeholder = ('<div class="bill-empty">Your order summary will appear here.</div>')

        def new_order():
            return ([{}, gr.update(value=""), gr.update(value="", visible=True),
                     gr.update(visible=True), gr.update(visible=True), gr.update(visible=True),
                     gr.update(value="View bill summary", visible=True), gr.update(value="", visible=True),
                     gr.update(value=None, visible=True),
                     gr.update(value=""), gr.update(value=bill_placeholder),
                     gr.update(value=""), gr.update(value=""),
                     gr.update(value=""), gr.update(value=""), gr.update(value=""), gr.update(value=""),
                     gr.update(value=""),
                     gr.update(value=""),
                     gr.update(value='<div class="pay-hint">Enter collected cash to calculate return.</div>'),
                     gr.update(visible=False), gr.update(visible=False), gr.update(visible=False),
                     gr.update(visible=True, value='<div class="pay-hint">Select 1 Cash, 2 Card, or 3 UPI to continue.</div>')]
                    + goto(2))

        s5_new.click(
            new_order, None,
             [order_state, s5_msg, confirm_box, s5_new, s5_inputs,
             final_group, s5_view_bill, final_bill_box, final_download,
             s3_msg, bill_box, name_in, phone_in, base_num, pizza_num, topping_num, qty_in, pay_mode,
             cash_collected, cash_return, cash_details, card_details, upi_details, payment_hint,
             *screens, pills],
        )

    return demo


demo = build_demo()

# Force light mode: the orange theme is designed for light. Without this, a user
# whose OS/browser is in dark mode gets Gradio's dark palette and our bill text
# ends up light-on-light. This pins ?__theme=light on first load.
FORCE_LIGHT = (
    "<script>(function(){var u=new URL(window.location.href);"
    "if(u.searchParams.get('__theme')!=='light'){"
    "u.searchParams.set('__theme','light');window.location.replace(u.href);}})();</script>"
)

# ssr_mode=False: server-side rendering can leave dynamically-toggled columns
# blank when mounted on FastAPI without a Node SSR server. Force client render.
app = gr.mount_gradio_app(api, demo, path="/", theme=theme, css=CSS, ssr_mode=False, head=FORCE_LIGHT)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
