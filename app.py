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
from datetime import datetime

import gradio as gr
from fastapi import FastAPI

from core import menu as menu_mod
from core import validation as v
from core import pricing, persistence, analytics
from core.menu import MenuError
from api.routes import router as api_router

MENU_DIR = os.environ.get("MENU_DIR", "menu_data")
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
    return f'<div class="menu-list"><div class="ml-cat"><div class="ml-cat-title">Payment</div>{rows}</div></div>'


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
    background: radial-gradient(circle at 15% 50%, rgba(204, 213, 174, 0.6), transparent 25%),
                radial-gradient(circle at 85% 30%, rgba(233, 237, 201, 0.6), transparent 25%),
                #FEFAE0 !important;
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
    background: linear-gradient(135deg, #606C38 0%, #283618 100%);
    border-radius:20px; padding:20px 30px; margin-bottom:0 !important;
    box-shadow: 0 10px 30px rgba(40, 54, 24, 0.2);
    position: relative; overflow: hidden;
}
#hero::after {
    content: '🍕'; position: absolute; right: 20px; top: -10px; font-size: 100px; opacity: 0.15;
    animation: float 6s ease-in-out infinite;
}
@keyframes float { 0% {transform: translateY(0px) rotate(0deg);} 50% {transform: translateY(-15px) rotate(5deg);} 100% {transform: translateY(0px) rotate(0deg);} }
#hero h1 {margin:0; font-size:32px; font-weight:800; letter-spacing:-0.5px; color:#ffffff !important;}
#hero p {margin:8px 0 0; font-size:16px; color:#E9EDC9 !important; font-weight: 500;}

/* Buttons animation */
button { transition: all 0.2s ease !important; }
button.primary:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(96, 108, 56, 0.3) !important; }
button.secondary:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important; }

/* Connected Step pills */
.steps {display:flex; align-items: center; justify-content: space-between; margin:4px 20px 8px; position: relative;}
.steps::before { content: ''; position: absolute; left: 10%; right: 10%; top: 50%; height: 2px; background: #E5E7EB; z-index: 0; }
.pill {
    background:#ffffff; color:#9CA3AF; border:2px solid #E5E7EB; border-radius:999px;
    padding:8px 20px; font-size:14px; font-weight:600; z-index: 1; transition: all 0.3s ease;
}
.pill.active {
    background: #606C38; color:#ffffff; border-color:#606C38;
    box-shadow:0 4px 15px rgba(96, 108, 56, 0.3); transform: scale(1.05);
}

/* Glassmorphism card & Header */
.page-card {
    background: rgba(255, 255, 255, 0.7) !important; 
    backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
    border:1px solid rgba(255, 255, 255, 0.8) !important;
    border-radius:24px !important; padding:20px 24px !important;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.04), inset 0 1px 0 rgba(255, 255, 255, 1) !important;
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
.page-card input, .page-card textarea {background:#fff !important; border:1px solid #D1D5DB !important;}
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
"""


def step_pills(active: int) -> str:
    labels = ["Details", "Customize", "Summary", "Pay"]
    spans = "".join(
        f'<span class="pill{" active" if i + 2 == active else ""}">{lbl}</span>'
        for i, lbl in enumerate(labels)
    )
    return f'<div class="steps">{spans}</div>'


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

        gr.HTML(f'<div id="hero"><h1>🍕 {BRAND}</h1>'
                f'<p>Fresh, fast, fairly priced — order in four quick steps.</p></div>')
        
        with gr.Tabs():
            with gr.Tab("Customer Ordering"):
                pills = gr.HTML(step_pills(2))

                with gr.Column(elem_classes="page-card"):
                    # ---------- Screen 2: Customer ----------
                    with gr.Group(visible=True) as s2:
                        with gr.Row(elem_classes="header-row"):
                            gr.HTML("<h3>Fill customer details</h3>")
                        s2_menu_msg = gr.HTML("" if default_menu else f'<p class="err">{default_menu_err}</p>')
                        name_in = gr.Textbox(label="Name", placeholder="e.g. Rajan Sharma", max_lines=1)
                        phone_in = gr.Textbox(label="Phone", placeholder="10 digits, starts 6/7/8/9", max_lines=1)
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
                            gr.Markdown("Pick by **payment number** from the list below.")
                            gr.HTML(render_payment_html())
                            pay_mode = gr.Textbox(label="Enter payment mode", placeholder="1, 2, or 3", max_lines=1)
                            
                            with gr.Group(visible=False) as card_details:
                                gr.Markdown("#### Secure Card Payment")
                                gr.Textbox(label="Card Number", placeholder="0000 0000 0000 0000", max_lines=1)
                                with gr.Row():
                                    gr.Textbox(label="Expiry Date", placeholder="MM/YY", max_lines=1)
                                    gr.Textbox(label="CVV", placeholder="123", type="password")
                                    
                            with gr.Group(visible=False) as upi_details:
                                gr.HTML('<div style="text-align: center; margin: 10px 0;"><img src="https://api.qrserver.com/v1/create-qr-code/?size=130x130&data=upi://pay?pa=slicematic@upi&pn=SliceMatic" alt="UPI QR Code" style="display: inline-block; border-radius: 8px; border: 1px solid #E5E7EB; padding: 10px; background: white;"/><p style="color: #6B7280; font-size: 13px; margin-top: 8px;">Scan using Google Pay, PhonePe, or Paytm</p></div>')
                            
                            s5_msg = gr.HTML("")
                            s5_pay = gr.Button("Pay & confirm order", variant="primary")
                        
                        confirm_box = gr.HTML(visible=False)
                        s5_new = gr.Button("Place another order", visible=False)

            with gr.Tab("Admin Dashboard"):
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
                                discount_in = gr.Slider(0, 100, value=pricing.get_discount_rate() * 100, step=1, label="Discount % (applied to all orders >= 5 items)")
                                disc_btn = gr.Button("Save Discount Rate", variant="primary")
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
                gr.update(value=msg),
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
                gr.update(value="" if can_order else msg),
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
                        gr.update(value=customer_msg),
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
                    gr.update(value=customer_msg),
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
                gr.update(value=""),
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
        
        def update_discount(rate):
            pricing.set_discount_rate(rate / 100.0)
            return f"<p style='color:#10B981;font-weight:bold;'>Discount rate updated to {rate}%</p>"
            
        disc_btn.click(update_discount, discount_in, disc_msg)
        
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
            return [order] + goto(5)

        s4_next.click(to_payment, order_state, [order_state, *screens, pills])
        s4_back.click(lambda: goto(3), None, [*screens, pills])

        # --- Screen 5 logic ---
        def toggle_payment_ui(mode):
            ok, mode_v = v.validate_payment(mode)
            if not ok:
                return gr.update(visible=False), gr.update(visible=False)
            return gr.update(visible=(mode_v == "Card")), gr.update(visible=(mode_v == "UPI"))
            
        pay_mode.change(toggle_payment_ui, inputs=[pay_mode], outputs=[card_details, upi_details])
        s5_back.click(lambda: goto(4), None, [*screens, pills])

        def pay(mode, order):
            ok, mode_v = v.validate_payment(mode)
            if not ok:
                return (order, gr.update(value=f'<span class="err">{mode_v}</span>'),
                        gr.update(visible=False), gr.update(visible=False), gr.update(visible=True))
            bill = order.get("bill")
            if not bill:
                return (order, gr.update(value='<span class="err">No bill found — please rebuild your order.</span>'),
                        gr.update(visible=False), gr.update(visible=False), gr.update(visible=True))
            order = dict(order)
            order["status"] = "payment_in_progress"
            ts = persistence.append_order(
                name=order["name"], phone=order["phone"], bill=bill,
                payment_mode=mode_v, timestamp=order.get("timestamp"),
            )
            order_no = f"SM-{datetime.now().strftime('%Y%m%d')}-{abs(hash((order['phone'], ts))) % 10000:04d}"
            order.update(status="ordered", order_no=order_no, payment_mode=mode_v)
            note = {"Cash": "Pay cash on delivery.", "Card": "Card payment confirmed.",
                    "UPI": "UPI payment confirmed."}[mode_v]
            html = (f'<div class="bill-card" style="text-align:center; padding: 30px;">'
                    f'<div class="check-wrapper"><svg class="checkmark" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 52"><circle class="checkmark__circle" cx="26" cy="26" r="25" fill="none"/><path class="checkmark__check" fill="none" d="M14.1 27.2l7.1 7.2 16.7-16.8"/></svg></div>'
                    f'<div style="font-size:24px;font-weight:800;color:#10B981;margin-top:16px">Order confirmed</div>'
                    f'<div style="color:#6B7280;margin:8px 0 20px;font-size:15px">Order no. <b>{order_no}</b></div>'
                    f'<div class="bl"><span>Paying via {mode_v}</span><span style="font-weight:600;color:#111827">INR {bill.total:.2f}</span></div>'
                    f'<div class="bl muted"><span>{note}</span><span></span></div>'
                    f'<div class="bl total" style="justify-content:center;border:none;padding-top:20px;margin-top:10px">'
                    f'<span>Thanks, {order["name"]}! 🍕</span></div></div>')
            return (order, gr.update(value=""), gr.update(value=html, visible=True),
                    gr.update(visible=True), gr.update(visible=False))

        s5_pay.click(pay, [pay_mode, order_state],
                     [order_state, s5_msg, confirm_box, s5_new, s5_inputs])

        bill_placeholder = ('<div class="bill-empty">Your order summary will appear here.</div>')

        def new_order():
            return ([{}, gr.update(value=""), gr.update(value="", visible=False),
                     gr.update(visible=False), gr.update(visible=True),
                     gr.update(value=""), gr.update(value=bill_placeholder),
                     gr.update(value=""), gr.update(value=""), gr.update(value=""), gr.update(value=""),
                     gr.update(value="")]
                    + goto(2))

        s5_new.click(
            new_order, None,
            [order_state, s5_msg, confirm_box, s5_new, s5_inputs,
             s3_msg, bill_box, base_num, pizza_num, topping_num, qty_in, pay_mode, *screens, pills],
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
