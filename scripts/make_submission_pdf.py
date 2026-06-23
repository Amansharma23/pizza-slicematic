# -*- coding: utf-8 -*-
"""Combine Stage 1 Part A (PRD) + Part B (Business Economics) into one
submission-ready PDF, with the user-flows rendered as diagram images.

Styling: Segoe UI (professional), olive-green accent, page index, author block.
"""
import re
from PIL import Image, ImageDraw, ImageFont
from fpdf import FPDF
from fpdf.fonts import FontFace

OUT = "M:/mouli-projects/pizzaflow/docs/SliceMatic_Stage1_Submission.pdf"
PART_A = "M:/mouli-projects/pizzaflow/docs/Stage1_PartA_PRD.md"
PART_B = "M:/mouli-projects/pizzaflow/docs/Stage1_PartB_BusinessEconomics.md"

# ---- author block (edit member names here) ---------------------------------
GROUP = "Group 3"
MEMBERS = ["Mouli Murakambattu", "Shaik Mohammed Pasha", "Aman Sharma",
           "Saurabh Sekhar", "Sushant Kumar"]

# ---- palette ----------------------------------------------------------------
OLIVE = (94, 113, 52)        # primary accent (rules, banners, table headers)
OLIVE_DK = (70, 86, 38)      # deeper olive for cover subtitle
OLIVE_TINT = (242, 244, 233) # alternating table rows
CALLOUT = (239, 242, 229)    # light-olive callout box
DARK = (40, 44, 38)
GREY = (110, 110, 110)
CODEBG = (244, 245, 240)

FONTDIR = "C:/Windows/Fonts/"

# ----------------------------------------------------------------------------
# Flowchart rendering with PIL
# ----------------------------------------------------------------------------
S = 2  # supersample for crisp text
def PF(path, size):
    try:
        return ImageFont.truetype(path, size * S)
    except Exception:
        return ImageFont.load_default()

FONT = PF(FONTDIR + "segoeui.ttf", 15)
FONT_SM = PF(FONTDIR + "segoeui.ttf", 11)
FONT_BADGE = PF(FONTDIR + "segoeuib.ttf", 12)

COL = {
    "start": ((226, 232, 209), OLIVE),
    "end":   ((226, 232, 209), OLIVE),
    "process": ((234, 242, 248), (44, 62, 80)),
    "validate": ((255, 242, 204), (183, 121, 31)),
    "decision": ((255, 242, 204), (183, 121, 31)),
    "exit":  ((235, 226, 220), (120, 95, 80)),
}


def wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def rrect(draw, box, r, fill, outline, width=2):
    draw.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width * S)


def arrow(draw, x1, y1, x2, y2, color=(80, 80, 80)):
    import math
    draw.line((x1, y1, x2, y2), fill=color, width=2 * S)
    ang = math.atan2(y2 - y1, x2 - x1)
    L = 7 * S
    for da in (math.radians(150), math.radians(-150)):
        draw.line((x2, y2, x2 + L * math.cos(ang + da), y2 + L * math.sin(ang + da)),
                  fill=color, width=2 * S)


def _text_centered(d, x, ycen, w, text, font, fill):
    lines = wrap(d, text, font, w)
    lh = (font.getbbox("Ag")[3] - font.getbbox("Ag")[1]) + 5 * S
    ty = ycen - (len(lines) * lh) // 2
    for ln in lines:
        tw = d.textlength(ln, font=font)
        d.text((x - tw / 2, ty), ln, fill=fill, font=font); ty += lh


def _badge(d, cx_left, cy_top, num):
    r = 12 * S
    x, y = cx_left + 12 * S, cy_top + 12 * S
    d.ellipse((x - r, y - r, x + r, y + r), fill=OLIVE, outline="white", width=2 * S)
    t = str(num); tw = d.textlength(t, font=FONT_BADGE)
    bb = FONT_BADGE.getbbox(t)
    d.text((x - tw / 2, y - (bb[3] + bb[1]) / 2), t, fill="white", font=FONT_BADGE)


def _loop(d, x, ycen, NW, NH, side):
    col = (150, 120, 40)
    if side == "right":
        e = x + NW // 2; o = e + 34 * S
        d.line((e, ycen, o, ycen), fill=col, width=2 * S)
        d.line((o, ycen, o, ycen - NH // 2 - 12 * S), fill=col, width=2 * S)
        arrow(d, o, ycen - NH // 2 - 12 * S, x + NW // 4, ycen - NH // 2, col)
    else:
        e = x - NW // 2; o = e - 34 * S
        d.line((e, ycen, o, ycen), fill=col, width=2 * S)
        d.line((o, ycen, o, ycen - NH // 2 - 12 * S), fill=col, width=2 * S)
        arrow(d, o, ycen - NH // 2 - 12 * S, x - NW // 4, ycen - NH // 2, col)


def _branch(d, branch, x, ycen, NW, NH, side):
    label, btext = branch
    bw, bh = 64 * S, 44 * S
    ef, eo = COL["exit"]
    if side == "left":
        e = x - NW // 2; bx = e - 40 * S - bw // 2
        arrow(d, e, ycen, bx + bw // 2, ycen, (120, 95, 80))
    else:
        e = x + NW // 2; bx = e + 40 * S + bw // 2
        arrow(d, e, ycen, bx - bw // 2, ycen, (120, 95, 80))
    rrect(d, (bx - bw // 2, ycen - bh // 2, bx + bw // 2, ycen + bh // 2), 10 * S, ef, eo)
    _text_centered(d, bx, ycen, bw - 14 * S, btext, FONT, DARK)


def _legend(d, x0, y0, font, nodes):
    kinds = set(nd["kind"] for nd in nodes)
    if any(nd.get("branch") for nd in nodes):
        kinds.add("exit")
    items = []
    if kinds & {"start", "end"}:
        items.append(("Start / End", COL["start"]))
    if "process" in kinds:
        items.append(("Process step", COL["process"]))
    if kinds & {"validate", "decision"}:
        items.append(("Validation (re-prompts)", COL["validate"]))
    if "exit" in kinds:
        items.append(("Error exit", COL["exit"]))
    x = x0
    sw, sh = 26 * S, 17 * S
    for label, (fill, outline) in items:
        rrect(d, (x, y0, x + sw, y0 + sh), 4 * S, fill, outline, width=1)
        d.text((x + sw + 7 * S, y0 + 1 * S), label, fill=(80, 80, 80), font=font)
        x += sw + 12 * S + d.textlength(label, font=font) + 26 * S


def render_flow(nodes, path, cols=1):
    NW, NH, VGAP, M, LEG = 300 * S, 60 * S, 42 * S, 24 * S, 58 * S
    n = len(nodes)
    if cols == 2:
        half = (n + 1) // 2
        groups = [list(range(half)), list(range(half, n))]
        left_pad, right_pad, gap = 100 * S, 58 * S, 96 * S
    else:
        groups = [list(range(n))]
        left_pad, right_pad, gap = 30 * S, 70 * S, 0
    rows = max(len(g) for g in groups)

    col_cx = [M + left_pad + NW // 2 + c * (NW + gap) for c in range(cols)]
    canvas_w = M + left_pad + cols * NW + (cols - 1) * gap + right_pad + M
    canvas_h = LEG + M + rows * NH + (rows - 1) * VGAP + M
    img = Image.new("RGB", (canvas_w, canvas_h), "white")
    d = ImageDraw.Draw(img)

    _legend(d, M, 16 * S, FONT_SM, nodes)

    pos, y0 = {}, LEG + M
    for c, g in enumerate(groups):
        y = y0
        for gi in g:
            pos[gi] = (col_cx[c], y + NH // 2); y += NH + VGAP

    for g in groups:                                   # in-column arrows
        for k in range(len(g) - 1):
            x0, ya = pos[g[k]]; x1, yb = pos[g[k + 1]]
            arrow(d, x0, ya + NH // 2, x1, yb - NH // 2)

    if cols == 2 and groups[1]:                        # column-to-column connector
        xa, ya = pos[groups[0][-1]]; xb, yb = pos[groups[1][0]]
        ch = (col_cx[0] + NW // 2 + col_cx[1] - NW // 2) // 2
        ab, bt = ya + NH // 2, yb - NH // 2
        d.line((xa, ab, xa, ab + 20 * S), fill=(80, 80, 80), width=2 * S)
        d.line((xa, ab + 20 * S, ch, ab + 20 * S), fill=(80, 80, 80), width=2 * S)
        d.line((ch, ab + 20 * S, ch, bt - 20 * S), fill=(80, 80, 80), width=2 * S)
        d.line((ch, bt - 20 * S, xb, bt - 20 * S), fill=(80, 80, 80), width=2 * S)
        arrow(d, xb, bt - 20 * S, xb, bt)

    for c, g in enumerate(groups):
        side = "left" if (cols == 2 and c == 0) else "right"
        for gi in g:
            nd = nodes[gi]; x, ycen = pos[gi]
            fill, outline = COL[nd["kind"]]
            radius = NH // 2 if nd["kind"] in ("start", "end") else 12 * S
            rrect(d, (x - NW // 2, ycen - NH // 2, x + NW // 2, ycen + NH // 2),
                  radius, fill, outline)
            _text_centered(d, x, ycen, NW - 62 * S, nd["text"], FONT, DARK)
            _badge(d, x - NW // 2, ycen - NH // 2, gi + 1)
            if nd.get("loop"):
                _loop(d, x, ycen, NW, NH, side)
            if nd.get("branch"):
                _branch(d, nd["branch"], x, ycen, NW, NH, side)

    img.save(path, "PNG")
    return path


CUSTOMER = [
    {"text": "Launch app", "kind": "start"},
    {"text": "Load 3 menu files - all valid?", "kind": "decision",
     "branch": ("files invalid", "Exit")},
    {"text": "Start session + log timestamp", "kind": "process"},
    {"text": "Collect & validate name (alpha+space, 2-40)", "kind": "validate",
     "loop": "invalid -> re-prompt"},
    {"text": "Collect & validate phone (10 digits, 6/7/8/9)", "kind": "validate",
     "loop": "invalid -> re-prompt"},
    {"text": "Select Base by number", "kind": "validate", "loop": "reject invalid"},
    {"text": "Select Pizza by number", "kind": "validate", "loop": "reject invalid"},
    {"text": "Select Topping by number", "kind": "validate", "loop": "reject invalid"},
    {"text": "Enter quantity (integer 1-10)", "kind": "validate", "loop": "invalid -> re-prompt"},
    {"text": "Compute bill (subtotal, discount, GST, total)", "kind": "process"},
    {"text": "Display itemised bill table", "kind": "process"},
    {"text": "Select payment mode (Cash / Card / UPI)", "kind": "validate", "loop": "reject invalid"},
    {"text": "Show payment confirmation", "kind": "process"},
    {"text": "Append order to orders_log.txt", "kind": "process"},
    {"text": "Order confirmed", "kind": "end"},
]
ADMIN = [
    {"text": "Open admin portal", "kind": "start"},
    {"text": "Show login page", "kind": "process"},
    {"text": "Authenticate (Supabase Auth)", "kind": "validate", "loop": "invalid -> retry"},
    {"text": "Load dashboard + fetch all orders", "kind": "process"},
    {"text": "View orders + metrics (revenue, top pizza, busiest hour)", "kind": "process"},
    {"text": "Filter by date / payment, or export CSV", "kind": "validate", "loop": "refine view"},
    {"text": "Logout", "kind": "process"},
    {"text": "Return to login", "kind": "end"},
]
cust_png = render_flow(CUSTOMER, "M:/mouli-projects/pizzaflow/_flow_customer.png", cols=2)
admin_png = render_flow(ADMIN, "M:/mouli-projects/pizzaflow/_flow_admin.png")
DIAGRAMS = [(cust_png, "Figure 4.1 - Customer Ordering Flow (MVP)"),
            (admin_png, "Figure 4.2 - Admin Flow (Stage 3 scope)")]

# ----------------------------------------------------------------------------
# PDF — fonts
# ----------------------------------------------------------------------------
class PDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font(FAMILY, "I", 8)
        self.set_text_color(*GREY)
        self.cell(0, 8, "SliceMatic - Stage 1 Submission", align="L")
        self.cell(0, 8, "PRD + Business Unit Economics", align="R",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(225, 228, 215)
        self.line(18, self.get_y(), 192, self.get_y())
        self.ln(3)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-15)
        self.set_font(FAMILY, "I", 8)
        self.set_text_color(*GREY)
        self.cell(0, 10, f"Page {self.page_no()} of {{nb}}", align="C")


pdf = PDF(orientation="P", unit="mm", format="A4")
pdf.set_auto_page_break(auto=True, margin=18)
pdf.set_margins(18, 18, 18)

# register professional fonts (fallback to core fonts if unavailable)
try:
    pdf.add_font("Segoe", "", FONTDIR + "segoeui.ttf")
    pdf.add_font("Segoe", "B", FONTDIR + "segoeuib.ttf")
    pdf.add_font("Segoe", "I", FONTDIR + "segoeuii.ttf")
    pdf.add_font("Segoe", "BI", FONTDIR + "segoeuiz.ttf")
    pdf.add_font("Mono", "", FONTDIR + "consola.ttf")
    pdf.add_font("Mono", "B", FONTDIR + "consolab.ttf")
    FAMILY, MONO, USE_TTF = "Segoe", "Mono", True
except Exception:
    FAMILY, MONO, USE_TTF = "Helvetica", "Courier", False

if USE_TTF:
    def clean(s):
        return s.replace("∈", " in ").replace(" ", " ")
else:
    REPL = {"’": "'", "‘": "'", "“": '"', "”": '"', "—": "-", "–": "-",
            "→": "->", "≈": "~", "₹": "Rs.", "×": "x", "…": "...", "•": "-",
            "≥": ">=", "≤": "<=", "∈": " in ", "−": "-", "·": "-", "✓": "-",
            "★": "*", "⚠": "[!]", "≠": "!="}
    def clean(s):
        for k, v in REPL.items():
            s = s.replace(k, v)
        return s.encode("latin-1", "replace").decode("latin-1")

pdf.set_title("SliceMatic - Stage 1 Submission")
pdf.set_author(f"{GROUP} - " + ", ".join(MEMBERS))
pdf.alias_nb_pages()
CW = 174

# ---- cover ----
pdf.add_page()
pdf.ln(36)
pdf.set_font(FAMILY, "B", 30)
pdf.set_text_color(*DARK)
pdf.multi_cell(0, 14, "SliceMatic", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font(FAMILY, "B", 16)
pdf.set_text_color(*OLIVE_DK)
pdf.multi_cell(0, 9, "Stage 1 Submission", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(2)
pdf.set_font(FAMILY, "", 13)
pdf.set_text_color(*DARK)
pdf.multi_cell(0, 7, clean("Product Requirements Document\n& Business Unit Economics"),
               align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(8)
pdf.set_draw_color(*OLIVE)
pdf.set_line_width(0.6)
pdf.line(75, pdf.get_y(), 135, pdf.get_y())
pdf.ln(9)
pdf.set_font(FAMILY, "I", 10.5)
pdf.set_text_color(*GREY)
pdf.multi_cell(0, 6, clean(
    "FDE Academy Programme - PizzaFlow Applied Project\n"
    "Digital Ordering System for SliceMatic, New Ashok Nagar, Delhi"),
    align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(12)
# author block
pdf.set_font(FAMILY, "B", 11)
pdf.set_text_color(*OLIVE_DK)
pdf.multi_cell(0, 6, f"Prepared by  -  {GROUP}", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font(FAMILY, "", 10)
pdf.set_text_color(*DARK)
pdf.multi_cell(0, 6, clean("   ·   ".join(MEMBERS)), align="C", new_x="LMARGIN", new_y="NEXT")


# ---- markdown rendering ------------------------------------------------------
def inline_clean(text):
    text = text.replace("**", "\x00").replace("*", "").replace("\x00", "**")
    text = text.replace("`", "")
    return clean(text)


def is_sep(line):
    return bool(re.match(r"^\s*\|?\s*:?-{2,}.*$", line)) and set(line) <= set("-|: ")


def heading(txt, level):
    if pdf.get_y() > 250:
        pdf.add_page()
    if level == 1:
        pdf.ln(2); pdf.set_font(FAMILY, "B", 17); pdf.set_text_color(*DARK)
        pdf.multi_cell(0, 9, inline_clean(txt), new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(*OLIVE); pdf.set_line_width(0.7)
        pdf.line(18, pdf.get_y() + 1, 192, pdf.get_y() + 1); pdf.ln(5)
    elif level == 2:
        pdf.ln(3); pdf.set_font(FAMILY, "B", 13); pdf.set_text_color(*DARK)
        pdf.multi_cell(0, 7, inline_clean(txt), new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(*OLIVE); pdf.set_line_width(0.4)
        pdf.line(18, pdf.get_y() + 0.5, 192, pdf.get_y() + 0.5); pdf.ln(3)
    else:
        pdf.ln(2); pdf.set_font(FAMILY, "B", 11); pdf.set_text_color(60, 66, 50)
        pdf.multi_cell(0, 6, inline_clean(txt), new_x="LMARGIN", new_y="NEXT"); pdf.ln(1)


def para(txt):
    pdf.set_font(FAMILY, "", 10); pdf.set_text_color(*DARK)
    pdf.multi_cell(0, 5.4, inline_clean(txt), markdown=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1.5)


def bullet(txt, ordered=None):
    pdf.set_font(FAMILY, "", 10); pdf.set_text_color(*DARK)
    pdf.set_x(20); pdf.cell(6, 5.4, ordered if ordered else "-")
    pdf.set_x(26)
    pdf.multi_cell(0, 5.4, inline_clean(txt), markdown=True, new_x="LMARGIN", new_y="NEXT")


def quote(lines):
    pdf.ln(1); pdf.set_fill_color(*CALLOUT); pdf.set_font(FAMILY, "I", 9.5)
    pdf.set_text_color(*DARK); pdf.set_x(20)
    pdf.multi_cell(CW - 4, 5.2, inline_clean(" ".join(lines)), fill=True,
                   border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def code_block(lines):
    pdf.ln(1); pdf.set_fill_color(*CODEBG); pdf.set_font(MONO, "", 8.5)
    pdf.set_text_color(*DARK)
    for ln in lines:
        pdf.multi_cell(0, 4.6, clean(ln) if ln.strip() else " ", fill=True,
                       new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def table_block(rows):
    pdf.ln(1)
    head = FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=OLIVE)
    pdf.set_font(FAMILY, "", 8.3); pdf.set_text_color(*DARK)
    pdf.set_draw_color(205, 208, 195)
    with pdf.table(width=CW, markdown=True, headings_style=head,
                   text_align="LEFT", line_height=4.8,
                   cell_fill_color=OLIVE_TINT, cell_fill_mode="ROWS") as table:
        for r in rows:
            row = table.row()
            for c in r:
                row.cell(inline_clean(c))
    pdf.ln(2)


def place_diagram(png, caption):
    iw, ih = Image.open(png).size
    page_bottom = 297 - 18
    avail = page_bottom - pdf.get_y() - 9          # leave room for the caption
    if avail < 125:                                # not enough room -> new page
        pdf.add_page()
        avail = page_bottom - pdf.get_y() - 9
    pdf.set_font(FAMILY, "BI", 9.5); pdf.set_text_color(*GREY)
    pdf.multi_cell(0, 5, clean(caption), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    ratio = min(CW / iw, (avail - 6) / ih)
    w, h = iw * ratio, ih * ratio
    top_y = pdf.get_y()
    pdf.image(png, x=(210 - w) / 2, y=top_y, w=w, h=h)
    pdf.set_y(top_y + h + 5)


def render_markdown(path, diagram_queue):
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if not s:
            i += 1; continue
        if re.match(r"^---+$", s):
            i += 1; continue
        if s.startswith("```"):
            lang = s[3:].strip().lower(); i += 1; buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i]); i += 1
            i += 1
            if lang == "mermaid":
                if diagram_queue:
                    png, cap = diagram_queue.pop(0); place_diagram(png, cap)
            else:
                code_block(buf)
            continue
        if "|" in s and i + 1 < len(lines) and is_sep(lines[i + 1]):
            rows = [[c.strip() for c in s.strip().strip("|").split("|")]]
            i += 2
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")]); i += 1
            table_block(rows); continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            heading(m.group(2), len(m.group(1))); i += 1; continue
        if s.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip()[1:].strip()); i += 1
            quote(buf); continue
        mo = re.match(r"^(\d+)\.\s+(.*)$", s)
        if mo:
            bullet(mo.group(2), ordered=mo.group(1) + "."); i += 1; continue
        mb = re.match(r"^[-*]\s+(.*)$", s)
        if mb:
            bullet(mb.group(1)); i += 1; continue
        buf = [s]; i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if (not nxt or nxt.startswith(("#", ">", "-", "*", "|", "```"))
                    or re.match(r"^\d+\.\s", nxt) or re.match(r"^---+$", nxt)):
                break
            buf.append(nxt); i += 1
        para(" ".join(buf))


pdf.add_page()
render_markdown(PART_A, DIAGRAMS)
pdf.add_page()
render_markdown(PART_B, [])

pdf.output(OUT)
print("PDF written:", OUT, "| pages:", pdf.page_no(), "| font:", FAMILY)
