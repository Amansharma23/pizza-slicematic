"""SliceMatic ordering app — Gradio UI mounted on FastAPI (single process).

Run locally:   uv run python app.py        (serves UI at / and API docs at /docs)
The Gradio handlers call core/ directly (in-process). The FastAPI routes expose
the same core/ functions for /docs and external callers — the UI never goes
over HTTP. See CLAUDE.md "Process model & API wiring".
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime

import gradio as gr
from fastapi import FastAPI

from core import menu as menu_mod
from core import validation as v
from core import pricing, persistence
from core.menu import MenuError
from api.routes import router as api_router

MENU_DIR = os.environ.get("MENU_DIR", "menu_data")
BRAND = "SliceMatic"

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


def bill_html(bill) -> str:
    disc = (
        f'<div class="bl"><span>Discount (10%)</span><span>− INR {bill.discount:.2f}</span></div>'
        if bill.discount > 0
        else '<div class="bl muted"><span>Discount (10%)</span><span>INR 0.00</span></div>'
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
    primary_hue=gr.themes.colors.orange,
    secondary_hue=gr.themes.colors.amber,
    neutral_hue=gr.themes.colors.gray,
    font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui"],
).set(
    body_background_fill="#fff8f2",
    body_background_fill_dark="#fff8f2",
    block_background_fill="#ffffff",
    background_fill_secondary="#ffffff",
    border_color_primary="#f3e3d5",
    input_background_fill="#ffffff",
    input_border_color="#f0ddca",
    button_primary_background_fill="#ea580c",
    button_primary_background_fill_hover="#c2410c",
    button_primary_text_color="white",
    button_secondary_background_fill="#fff3e9",
    button_secondary_background_fill_hover="#ffe6d2",
    button_secondary_text_color="#9a3412",
    block_radius="12px",
    block_shadow="none",
)

CSS = """
.gradio-container {max-width: 1140px !important; width:100% !important; margin: auto !important;}
.gradio-container .main, .gradio-container .wrap, .gradio-container .contain {width:100% !important;}
.gradio-container, body {background:#fff8f2 !important;}
input, textarea, select {color:#1f2937 !important;}
label span {color:#374151 !important; font-weight:600 !important;}

/* Hide radio circle indicators — selection is shown by the highlighted pill */
.page-card input[type="radio"] {display:none !important;}
.page-card label > input[type="radio"] + span {margin-left:0 !important;}

/* Upload buttons: one full-width button per row (Base / Pizza / Toppings) */
.up-btn {width:100% !important; background:#fff7ed !important; border:1.5px dashed #f59e0b !important;
         color:#9a3412 !important; font-weight:600 !important; border-radius:10px !important;
         padding:13px 16px !important; justify-content:flex-start !important; margin-top:8px !important;
         box-shadow:none !important;}
.up-btn:hover {background:#ffedd5 !important; border-color:#ea580c !important;}
.up-status p {margin:2px 0 0 4px !important; color:#15803d !important; font-size:13px !important; font-weight:600;}

/* Hero */
#hero {background: linear-gradient(120deg,#fb923c 0%,#f97316 55%,#ea580c 100%);
       border-radius:18px; padding:26px 30px; margin-bottom:4px;
       box-shadow:0 8px 22px rgba(234,88,12,.18);}
#hero h1 {margin:0; font-size:26px; font-weight:800; letter-spacing:.2px; color:#ffffff !important;}
#hero p {margin:6px 0 0; font-size:14px; color:#fff3e9 !important;}

/* Step pills */
.steps {display:flex; gap:8px; margin:16px 0 8px; flex-wrap:wrap;}
.pill {background:#fff; color:#9a3412; border:1px solid #fcd9bd; border-radius:999px;
       padding:6px 16px; font-size:13px; font-weight:600;}
.pill.active {background:#ea580c; color:#fff; border-color:#ea580c;
       box-shadow:0 3px 10px rgba(234,88,12,.25);}

/* One clean white card wrapping the active step; flatten Gradio's inner blocks */
.page-card {background:#fff !important; border:1px solid #f3e3d5 !important;
       border-radius:18px !important; padding:24px 30px !important;
       box-shadow:0 4px 16px rgba(124,69,30,.07) !important;
       width:100% !important; max-width:100% !important;   /* same width on every step */
       min-height:560px !important;                        /* same height on every step */
       justify-content:flex-start !important;}             /* top-align (no gap above content) */
.page-card > .block, .page-card .form {align-self:stretch !important;}

/* Build step: selection on the left, order summary (checkout) pinned on the right */
.build-row {gap:24px !important; flex-wrap:nowrap !important;}
.build-left {flex:1 1 auto !important; min-width:0 !important;}
.checkout-col {flex:0 0 330px !important; max-width:330px !important;
       background:#fffaf6 !important; border:1px solid #f3e3d5 !important;
       border-radius:14px !important; padding:16px 18px !important; align-self:flex-start !important;}
.checkout-col h4 {margin:0 0 8px !important; color:#9a3412 !important; font-size:15px;}
.checkout-col .bill-card {background:transparent !important; border:none !important; padding:0 !important;}
.bill-empty {color:#a8a29e; font-size:13.5px; line-height:1.5; padding:6px 0;}
.page-card .block, .page-card .form, .page-card fieldset,
.page-card .styler, .page-card .gr-group, .page-card .wrap {
       background:transparent !important; border:none !important; box-shadow:none !important;}
.page-card .block {padding:0 !important;}
.page-card h3 {margin:2px 0 2px !important; font-size:18px; font-weight:700; color:#1f2937;}
/* keep real inputs readable after the flatten */
.page-card input, .page-card textarea {background:#fff !important; border:1px solid #f0ddca !important;}
.styler {background:transparent !important;}

/* Menu numbered list */
.menu-list {display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; margin:8px 0 2px; width:100%;}
.ml-cat {background:#fffaf6; border:1px solid #f3e3d5; border-radius:12px; padding:10px 11px; min-width:0;}
.ml-cat-title {font-weight:700; color:#9a3412; margin-bottom:8px; font-size:11px;
               text-transform:uppercase; letter-spacing:.5px;}
.ml-row {display:grid; grid-template-columns:auto 1fr auto; align-items:start; column-gap:7px;
         padding:5px 0; font-size:12.5px; color:#374151; border-bottom:1px solid #f6ebe1;}
.ml-row:last-child {border-bottom:none;}
.ml-num {background:#fff3e9; color:#ea580c; border-radius:5px; min-width:20px; text-align:center;
         font-weight:700; padding:1px 4px; font-size:11px; margin-top:1px;}
.ml-name {color:#1f2937; min-width:0; line-height:1.3; overflow-wrap:anywhere;}
.ml-price {color:#78716c; font-size:11.5px; white-space:nowrap; text-align:right;}

/* Bill */
.bill-card {background:#fffaf6; border:1px solid #f3e3d5; border-radius:12px; padding:18px 22px;}
.bl {display:flex; justify-content:space-between; padding:9px 0; font-size:15px; color:#374151;
     border-bottom:1px solid #f6ebe1;}
.bl.muted {color:#a8a29e;}
.bl.total {border-bottom:none; font-weight:800; font-size:19px; color:#ea580c; padding-top:14px;}
.err {color:#c2410c; font-weight:600;}
footer {visibility:hidden;}
@media (max-width:680px){.menu-list{grid-template-columns:1fr;}}
"""


def step_pills(active: int) -> str:
    labels = ["Menu", "Details", "Customize", "Pay"]
    spans = "".join(
        f'<span class="pill{" active" if i + 1 == active else ""}">{lbl}</span>'
        for i, lbl in enumerate(labels)
    )
    return f'<div class="steps">{spans}</div>'


# --------------------------------------------------------------------------- #
# Gradio app
# --------------------------------------------------------------------------- #

def build_demo() -> gr.Blocks:
    try:
        default_menu = menu_mod.load_menu(MENU_DIR)
        default_menu_err = ""
    except MenuError as exc:
        default_menu = None
        default_menu_err = str(exc)

    show = lambda visible: gr.update(visible=visible)

    with gr.Blocks(title=f"{BRAND} · Order") as demo:
        menu_state = gr.State(default_menu)
        order_state = gr.State({})
        up_base_fp = gr.State(None)
        up_pizza_fp = gr.State(None)
        up_topping_fp = gr.State(None)

        gr.HTML(f'<div id="hero"><h1>🍕 {BRAND}</h1>'
                f'<p>Fresh, fast, fairly priced — order in four quick steps.</p></div>')
        pills = gr.HTML(step_pills(1))

        with gr.Column(elem_classes="page-card"):
            # ---------- Screen 1: Menu ----------
            with gr.Group(visible=True) as s1:
                gr.Markdown("### Choose your menu")
                menu_mode = gr.Radio(
                    ["Use SliceMatic default menu", "Upload my own menu files"],
                    value="Use SliceMatic default menu", label="Menu source",
                )
                with gr.Group(visible=False) as upload_group:
                    up_base = gr.UploadButton("⬆  Upload Base menu  (.txt)",
                                              file_types=[".txt"], elem_classes="up-btn")
                    up_base_status = gr.Markdown("", elem_classes="up-status")
                    up_pizza = gr.UploadButton("⬆  Upload Pizza menu  (.txt)",
                                               file_types=[".txt"], elem_classes="up-btn")
                    up_pizza_status = gr.Markdown("", elem_classes="up-status")
                    up_topping = gr.UploadButton("⬆  Upload Toppings menu  (.txt)",
                                                 file_types=[".txt"], elem_classes="up-btn")
                    up_topping_status = gr.Markdown("", elem_classes="up-status")
                    up_btn = gr.Button("Continue →", variant="primary")
                s1_msg = gr.HTML("" if default_menu else f'<p class="err">{default_menu_err}</p>')
                s1_next = gr.Button("Start ordering →", variant="primary")

            # ---------- Screen 2: Customer ----------
            with gr.Group(visible=False) as s2:
                gr.Markdown("### Fill customer details")
                name_in = gr.Textbox(label="Name", placeholder="e.g. Rajan Sharma")
                phone_in = gr.Textbox(label="Phone", placeholder="10 digits, starts 6/7/8/9")
                s2_msg = gr.HTML("")
                with gr.Row():
                    s2_back = gr.Button("← Back")
                    s2_next = gr.Button("Continue →", variant="primary")

            # ---------- Screen 3: Build & Bill ----------
            with gr.Group(visible=False) as s3:
                gr.Markdown("### Build your pizza")
                with gr.Row(elem_classes="build-row", equal_height=False):
                    with gr.Column(scale=3, elem_classes="build-left"):
                        gr.Markdown("Pick by **item number** from the lists below.")
                        menu_list = gr.HTML(render_menu_html(default_menu))
                        with gr.Row():
                            base_num = gr.Textbox(label="Enter base", placeholder="item number, e.g. 3")
                            pizza_num = gr.Textbox(label="Enter pizza", placeholder="item number, e.g. 7")
                            topping_num = gr.Textbox(label="Enter topping", placeholder="item number, e.g. 2")
                        qty_in = gr.Textbox(label="Quantity (1–10)", placeholder="whole number 1–10")
                        s3_msg = gr.HTML("")
                        s3_calc = gr.Button("View bill", variant="primary")
                    with gr.Column(scale=2, elem_classes="checkout-col"):
                        gr.Markdown("#### Order summary")
                        bill_box = gr.HTML(
                            '<div class="bill-empty">Pick a base, pizza, topping and quantity, '
                            'then tap <b>View bill</b> to see your order summary here.</div>'
                        )
                with gr.Row():
                    s3_back = gr.Button("← Back")
                    s3_next = gr.Button("Proceed to payment →", variant="primary", visible=False)

            # ---------- Screen 4: Payment ----------
            with gr.Group(visible=False) as s4:
                gr.Markdown("### Payment")
                pay_mode = gr.Radio(["Cash", "Card", "UPI"], label="Payment mode", value="UPI")
                s4_msg = gr.HTML("")
                with gr.Row():
                    s4_back = gr.Button("← Back")
                    s4_pay = gr.Button("Pay & confirm order", variant="primary")
                confirm_box = gr.HTML(visible=False)
                s4_new = gr.Button("Place another order", visible=False)

        screens = [s1, s2, s3, s4]

        def goto(n: int):
            return [show(i + 1 == n) for i in range(4)] + [step_pills(n)]

        # --- Screen 1 logic ---
        def toggle_upload(mode):
            up = mode == "Upload my own menu files"
            # Show the 3 uploaders + Upload button in upload mode; hide the default
            # "Start ordering" button (each mode has exactly one primary action).
            return gr.update(visible=up), gr.update(visible=not up)

        menu_mode.change(toggle_upload, menu_mode, [upload_group, s1_next])

        def _took(f):
            path = f.name if hasattr(f, "name") else f
            return path, f"✓ {os.path.basename(path)}"

        up_base.upload(_took, up_base, [up_base_fp, up_base_status])
        up_pizza.upload(_took, up_pizza, [up_pizza_fp, up_pizza_status])
        up_topping.upload(_took, up_topping, [up_topping_fp, up_topping_status])

        def start_order(mode, fb, fp, ft, order, current_menu):
            if mode == "Upload my own menu files":
                missing = [n for n, f in (("Base", fb), ("Pizza", fp), ("Toppings", ft)) if not f]
                if missing:
                    msg = f'<p class="err">Please upload all three files. Missing: {", ".join(missing)}.</p>'
                    return ([current_menu, order, gr.update(value=msg)] + goto(1)
                            + [gr.update(value=render_menu_html(current_menu))])
                tmpdir = tempfile.mkdtemp(prefix="slicematic_menu_")
                for src, dest in ((fb, menu_mod.BASE_FILE), (fp, menu_mod.PIZZA_FILE), (ft, menu_mod.TOPPING_FILE)):
                    src_path = src.name if hasattr(src, "name") else src
                    with open(src_path, "r", encoding="utf-8", errors="replace") as r:
                        data = r.read()
                    with open(os.path.join(tmpdir, dest), "w", encoding="utf-8") as w:
                        w.write(data)
                load_dir = tmpdir
            else:
                load_dir = MENU_DIR
            try:
                m = menu_mod.load_menu(load_dir)
            except MenuError as exc:
                msg = f'<p class="err">{exc}</p>'
                return ([current_menu, order, gr.update(value=msg)] + goto(1)
                        + [gr.update(value=render_menu_html(current_menu))])
            order = dict(order)
            order["status"] = "started"
            return ([m, order, gr.update(value="")] + goto(2)
                    + [gr.update(value=render_menu_html(m))])

        start_inputs = [menu_mode, up_base_fp, up_pizza_fp, up_topping_fp, order_state, menu_state]
        start_outputs = [menu_state, order_state, s1_msg, *screens, pills, menu_list]
        s1_next.click(start_order, start_inputs, start_outputs)
        up_btn.click(start_order, start_inputs, start_outputs)

        # --- Screen 2 logic ---
        def submit_customer(name, phone, order):
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

        s2_next.click(submit_customer, [name_in, phone_in, order_state],
                      [order_state, s2_msg, *screens, pills])
        s2_back.click(lambda: goto(1), None, [*screens, pills])

        # --- Screen 3 logic ---
        def view_bill(base_raw, pizza_raw, topping_raw, qty_raw, m, order):
            if not m:
                return (order, gr.update(value='<span class="err">Menu not loaded — go back to step 1.</span>'),
                        gr.update(), gr.update(visible=False))
            ok_b, b = v.validate_selection(base_raw, len(m.bases))
            ok_p, p = v.validate_selection(pizza_raw, len(m.pizzas))
            ok_t, t = v.validate_selection(topping_raw, len(m.toppings))
            ok_q, q = v.validate_quantity(qty_raw)
            errs = []
            if not ok_b:
                errs.append(f"Base — {b}")
            if not ok_p:
                errs.append(f"Pizza — {p}")
            if not ok_t:
                errs.append(f"Topping — {t}")
            if not ok_q:
                errs.append(q)
            if errs:
                msg = "<br>".join(f'<span class="err">• {e}</span>' for e in errs)
                return (order, gr.update(value=msg), gr.update(), gr.update(visible=False))
            base, pizza, topping = m.bases[b - 1], m.pizzas[p - 1], m.toppings[t - 1]
            bill = pricing.compute_bill(base, pizza, topping, q)
            order = dict(order)
            order.update(base=base, pizza=pizza, topping=topping, quantity=q,
                         bill=bill, status="menu_selected")
            return (order, gr.update(value=""),
                    gr.update(value=bill_html(bill), visible=True),
                    gr.update(visible=True))

        s3_calc.click(view_bill, [base_num, pizza_num, topping_num, qty_in, menu_state, order_state],
                      [order_state, s3_msg, bill_box, s3_next])
        s3_back.click(lambda: goto(2), None, [*screens, pills])

        def to_payment(order):
            order = dict(order)
            order["status"] = "payment_selected"
            return [order] + goto(4)

        s3_next.click(to_payment, order_state, [order_state, *screens, pills])
        s4_back.click(lambda: goto(3), None, [*screens, pills])

        # --- Screen 4 logic ---
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
            html = (f'<div class="bill-card" style="text-align:center">'
                    f'<div style="font-size:40px;line-height:1">✅</div>'
                    f'<div style="font-size:20px;font-weight:700;color:#1e8e4e;margin-top:4px">Order confirmed</div>'
                    f'<div style="color:#7a6a62;margin:2px 0 12px">Order no. <b>{order_no}</b></div>'
                    f'<div class="bl"><span>Paying via {mode_v}</span><span>INR {bill.total:.2f}</span></div>'
                    f'<div class="bl muted"><span>{note}</span><span></span></div>'
                    f'<div class="bl total" style="justify-content:center;border:none;padding-top:14px">'
                    f'<span>Thanks, {order["name"]}! 🍕</span></div></div>')
            return (order, gr.update(value=""), gr.update(value=html, visible=True),
                    gr.update(visible=True), gr.update(visible=False))

        s4_pay.click(pay, [pay_mode, order_state],
                     [order_state, s4_msg, confirm_box, s4_new, s4_pay])

        bill_placeholder = ('<div class="bill-empty">Pick a base, pizza, topping and quantity, '
                            'then tap <b>View bill</b> to see your order summary here.</div>')

        def new_order():
            return ([{}, gr.update(value=""), gr.update(value="", visible=False),
                     gr.update(visible=False), gr.update(visible=True),
                     gr.update(value=""), gr.update(value=bill_placeholder, visible=True), gr.update(visible=False),
                     gr.update(value=""), gr.update(value=""), gr.update(value=""), gr.update(value="")]
                    + goto(2))

        s4_new.click(
            new_order, None,
            [order_state, s4_msg, confirm_box, s4_new, s4_pay,
             s3_msg, bill_box, s3_next, base_num, pizza_num, topping_num, qty_in, *screens, pills],
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
