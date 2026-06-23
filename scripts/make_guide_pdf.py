# -*- coding: utf-8 -*-
"""Generate a simplified business-economics study guide PDF for SliceMatic."""
from fpdf import FPDF

# Colours
DARK = (33, 37, 41)
RED = (200, 60, 50)
GREEN = (40, 120, 70)
GREY = (90, 90, 90)
LIGHT = (245, 245, 245)
BOX = (248, 240, 235)


class PDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GREY)
        self.cell(0, 8, "SliceMatic - Business Economics Made Simple", align="L")
        self.cell(0, 8, "Study Guide", align="R", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GREY)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def clean(s):
    """Replace characters the core fonts can't render."""
    repl = {
        "’": "'", "‘": "'", "“": '"', "”": '"',
        "—": "-", "–": "-", "→": "->", "≈": "~",
        "₹": "Rs.", "×": "x", "…": "...", "•": "-",
        "⚠": "[!]", "\U0001f355": "", "\U0001f4a1": "", "\U0001fab4": "",
        "✓": "-",
    }
    for k, v in repl.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")


pdf = PDF(orientation="P", unit="mm", format="A4")
pdf.set_auto_page_break(auto=True, margin=18)
pdf.set_margins(18, 18, 18)
pdf.add_page()


def h1(txt):
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*DARK)
    pdf.multi_cell(0, 8, clean(txt))
    pdf.set_draw_color(*RED)
    pdf.set_line_width(0.6)
    y = pdf.get_y() + 1
    pdf.line(18, y, 192, y)
    pdf.ln(4)


def para(txt):
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(*DARK)
    pdf.multi_cell(0, 5.6, clean(txt))
    pdf.ln(2)


def bullet(txt):
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(*DARK)
    pdf.set_x(18)
    pdf.cell(5, 5.6, "-")
    pdf.set_x(24)
    pdf.multi_cell(0, 5.6, clean(txt), new_x="LMARGIN", new_y="NEXT")


def callout(txt):
    pdf.ln(1)
    pdf.set_fill_color(*BOX)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(*DARK)
    start_y = pdf.get_y()
    pdf.set_draw_color(*RED)
    pdf.set_line_width(1.2)
    pdf.multi_cell(0, 5.4, clean(txt), border=0, fill=True)
    end_y = pdf.get_y()
    pdf.line(18.5, start_y, 18.5, end_y)
    pdf.ln(2)


def code(lines):
    pdf.ln(1)
    pdf.set_fill_color(*LIGHT)
    pdf.set_font("Courier", "", 9.5)
    pdf.set_text_color(*DARK)
    for ln in lines:
        pdf.cell(0, 5, clean(ln), fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


# ---------- TITLE PAGE ----------
def center(txt, h):
    pdf.set_x(18)
    pdf.multi_cell(0, h, clean(txt), align="C", new_x="LMARGIN", new_y="NEXT")


pdf.ln(20)
pdf.set_font("Helvetica", "B", 26)
pdf.set_text_color(*DARK)
center("Business Economics", 12)
center("Made Simple", 12)
pdf.ln(4)
pdf.set_font("Helvetica", "", 13)
pdf.set_text_color(*RED)
center("A Beginner's Guide using the SliceMatic Model", 8)
pdf.ln(6)
pdf.set_font("Helvetica", "I", 10.5)
pdf.set_text_color(*GREY)
center(
    "Every jargon term - COGS, P&L, EBITDA, contribution margin, break-even and "
    "more - explained step by step in plain language, anchored to real rupee "
    "numbers from the SliceMatic pizza-delivery business.", 6)
pdf.ln(10)
pdf.set_draw_color(*RED)
pdf.set_line_width(0.6)
pdf.line(60, pdf.get_y(), 150, pdf.get_y())
pdf.ln(8)
pdf.set_font("Helvetica", "", 10)
pdf.set_text_color(*DARK)
center("FDE Programme - Stage 1 Companion Notes", 6)

# ---------- 1 ----------
pdf.add_page()
h1("1. The Two Kinds of Costs (the foundation of everything)")
para("Before any fancy term, you only need to understand that a business has two types of costs.")
para("Fixed costs - you pay these no matter what, even if you sell zero pizzas. Rent (Rs.55,000), the chef's salary (Rs.28,000), the loan EMI on the oven (Rs.14,500), and so on. SliceMatic's total fixed cost = Rs.2,02,910 per month. Rent doesn't care whether you sold 10 pizzas or 1,000. It is fixed.")
para("Variable costs - these go up and down with each pizza you sell: the cheese, dough, sauce, the box it ships in, the rider's per-delivery tip. Sell one more pizza, you spend a bit more. Sell zero, you spend zero.")
callout("Analogy: Fixed cost is your gym membership - you pay Rs.2,000/month whether you go 0 times or 30 times. Variable cost is the protein shake you buy each time you actually go.")
para("Almost every other term in the document is built on top of this one split. Get this and you are halfway there.")

# ---------- 2 ----------
h1("2. COGS - Cost of Goods Sold")
para("COGS = what it costs you to make the actual thing you sell. For a pizza shop, that is ingredients + packaging + delivery for one pizza. From the document, an average pizza's COGS = Rs.170:")
code([
    " Pizza base ............ Rs.52",
    " Sauce + seasoning ..... Rs.13",
    " Cheese ................ Rs.38",
    " Toppings .............. Rs.27",
    " Packaging ............. Rs.18",
    " Delivery cost ......... Rs.22",
    " -----------------------------",
    " Total COGS ............ Rs.170",
])
para("COGS is basically the variable cost of one product. It does NOT include rent or the chef's salary - those are fixed and counted separately.")
callout("Simple version: COGS is the cost of the stuff inside and around the pizza, not the cost of running the shop.")

# ---------- 3 ----------
h1("3. Gross Margin - how much is left after making the thing")
para("If you sell a pizza for Rs.420 and it costs Rs.170 to make (COGS), then:")
code([
    " Selling Price - COGS = Gross Profit",
    " Rs.420 - Rs.170 = Rs.250 left over",
])
para("Gross Margin is that leftover expressed as a percentage of the selling price:")
code([" Gross Margin % = 250 / 420 = 59.5%"])
para("It tells you: for every Rs.100 of pizza you sell, how much is left after paying for ingredients? Higher = healthier.")
callout("[!] 'Gross' means rough / before deductions. Gross margin is BEFORE you have paid rent, salaries, marketing. It is an early, optimistic-looking number - do not confuse it with actual profit.")
para("Notice: Cheese Burst has a lower gross margin (51%) because it uses far more cheese (Rs.65 vs Rs.28). Expensive ingredients mean a thinner margin - a real insight you can read straight off the table.")

# ---------- 4 ----------
h1("4. Contribution Margin - the most important idea")
para("Contribution Margin = Selling price - ALL variable costs of one order. It is similar to gross profit, but the name tells you its purpose: each order's leftover money contributes toward paying off the big fixed costs (rent, salaries).")
code([
    " Revenue (one order) ............... Rs.847",
    " - Ingredients ..................... (Rs.148)",
    " - Packaging ....................... (Rs.18)",
    " - Delivery tip to rider ........... (Rs.22)",
    " - Payment gateway fee ............. (Rs.15)",
    " -------------------------------------------",
    " Contribution Margin ............... Rs.644  (76%)",
])
para("So every single order throws Rs.644 into a bucket. That bucket has to fill up to Rs.2,02,910 (the fixed costs) before the shop earns a single rupee of profit.")
callout("Analogy: Fixed costs are a Rs.2,02,910 hole you must fill each month. Each order drops Rs.644 of fill into it. Once the hole is full, every extra order's Rs.644 is pure profit.")

# ---------- 5 ----------
h1("5. Break-Even - the 'not losing money' line")
para("Break-even = the point where you have sold just enough to cover all costs. Profit = exactly zero. Not winning, not losing. The math is simple:")
code([
    " Break-even orders = Fixed Costs / Contribution Margin",
    "                   = 2,02,910 / 644",
    "                   = 315 orders per month",
    "                   = about 11 orders per day",
])
para("So SliceMatic must sell 11 orders a day just to not lose money. Everything above 11 is profit territory. The plan targets 47 orders/day - that is 4.3x the break-even. Sales would have to collapse by 76% before the shop loses money. That cushion is the 'healthy safety margin'.")
callout("This is why break-even is the first thing investors ask about: how bad can it get before you bleed?")

# ---------- 6 ----------
h1("6. P&L - Profit & Loss statement")
para("P&L is simply a top-to-bottom list that starts with money coming in and subtracts costs line by line until you reach profit at the bottom. Also called an income statement. The shape is always:")
code([
    "   Revenue (money in)",
    " - Cost of goods (variable)",
    " - Operating costs (fixed)",
    " --------------------------",
    " = Profit (or loss) at the bottom",
])
para("When someone says 'run it through the P&L' they mean 'subtract all the costs and see what is actually left'. Section 5 of the SliceMatic document IS a P&L.")

# ---------- 7 ----------
h1("7. EBITDA - the scary word that is actually simple")
para("EBITDA = Earnings Before Interest, Taxes, Depreciation, and Amortization. Forget the long name. Read it as: the operating profit of the business - how much it earns from just running, before accounting-y deductions.")
code([
    " Contribution Margin (the bucket) ... Rs.9,03,666/mo",
    " - Fixed Costs ...................... (Rs.2,02,910)",
    " ----------------------------------------------------",
    " Operating Profit (EBITDA) .......... Rs.7,00,756/mo",
])
para("Why exclude those four things? Because they vary based on how the business was financed and accounted for, not how good the actual pizza operation is. Stripping them out lets you compare core business health cleanly.")
bullet("Interest - cost of loans (a financing choice, not operations).")
bullet("Taxes - the government's cut.")
bullet("Depreciation - spreading the cost of physical things (like the oven) over years.")
bullet("Amortization - same idea, but for non-physical things (like software licenses).")
pdf.ln(2)
callout("Quick read: EBITDA = is the day-to-day business itself profitable? SliceMatic's answer: yes, ~Rs.7 lakh/month at 60% capacity. Operating Margin of 58.9% just means EBITDA is 58.9% of revenue.")

# ---------- 8 ----------
h1("8. AOV - Average Order Value")
para("AOV = the average rupee amount a customer spends per order. Total revenue / number of orders. SliceMatic's AOV = Rs.847. One pizza only sells for ~Rs.420, so how is the average Rs.847? Because people order multiple pizzas, premium bases, and extra toppings. Weekends have a higher AOV (Rs.940 vs Rs.792) - people splurge more.")
callout("Why businesses obsess over AOV: raising it even a little (an upsell - 'add garlic bread?') drops almost straight to profit, because fixed costs do not change.")

# ---------- 9 ----------
h1("9. GST and ITC - the money that passes through you")
para("GST (Goods & Services Tax) = a government tax (18% here) added on top of the bill, collected from the customer. The crucial insight: GST is never SliceMatic's money. The shop is just a collector for the government. The customer pays it, the shop holds it briefly, then hands it over. That is why the P&L is calculated 'ex-GST' (excluding GST) - you do not count money that was never yours.")
code([
    " Customer pays Rs.3,594.87",
    "   -> Rs.3,046.50 is the shop's",
    "   -> Rs.548.37 (the 18% GST) belongs to govt",
])
para("ITC (Input Tax Credit) is the clever part. SliceMatic also paid GST when it bought cheese, boxes, the oven, etc. The government lets you subtract the GST you paid from the GST you collected:")
code([
    " GST collected from customers ... ~Rs.1,77,564",
    " - GST you already paid (ITC) ... ~Rs.20,000",
    " -------------------------------------------",
    " Net GST owed to government ..... ~Rs.1,57,564",
])
callout("ITC prevents tax being charged twice on the same thing. You only remit the difference.")

# ---------- 10 ----------
h1("10. Capacity Utilisation - how full is the kitchen?")
para("The kitchen can physically make 80 orders/day (one pizza every 6 min, two ovens). That is 100% capacity. The plan assumes only 60% capacity = 47 orders/day at launch - a deliberately conservative (cautious) assumption, because new shops start slow.")
callout("Whenever you see '60% capacity', read it as: we assume we are only 60% as busy as we could be - and we are still profitable. That is a sign of a robust plan.")

# ---------- 11 ----------
h1("11. Payback Period - when do I get my money back?")
para("The owner spent Rs.15 lakh upfront to open the shop (oven, fit-out, working capital, marketing). The Payback Period = how long until accumulated profits repay that initial Rs.15 lakh. For SliceMatic: ~18 months. In Section 8, the 'Cumulative P&L' column starts deep negative (-14.12 lakh) and slowly climbs back to zero and beyond. The month it crosses zero is payback.")
callout("Investors love a short payback. 18 months for a restaurant is considered solid.")

# ---------- 12 ----------
h1("12. A few smaller terms you will see")
bullet("QSR = Quick Service Restaurant (fast food / quick delivery, like Domino's). SliceMatic's category.")
bullet("GMV = Gross Merchandise Value = total sales value before any costs. The '1.8% of GMV' gateway fee means the payment processor takes 1.8% of everything sold.")
bullet("SLA = Service Level Agreement = a promise to the customer (here, the 30-min delivery guarantee).")
bullet("Lakh (L) = Indian unit = 1,00,000. So Rs.2.1L = Rs.2,10,000.")

# ---------- MAP ----------
h1("How it all fits together (one mental map)")
code([
    " Selling Price (Rs.847 AOV)",
    "  |- minus VARIABLE costs (COGS ~Rs.170)",
    "     -> CONTRIBUTION MARGIN (Rs.644)",
    "        |- many orders fill the bucket",
    "           to cover FIXED costs (Rs.2.03L)",
    "           |- the BREAK-EVEN point (11/day)",
    "              |- everything above = EBITDA (Rs.7L)",
    "                 |- accumulated over months",
    "                    repays the Rs.15L investment",
    "                    |- PAYBACK (~18 months)",
])
para("Read top to bottom, that is the entire story of the business - and that path IS the P&L. The whole reference document is essentially proving 'this shop makes money and pays itself back in 18 months', using these terms as the proof.")
para("Tip for the assignment: Section 9 ('Challenge These Numbers') is where you are actually graded. It asks you to recalculate break-even under new conditions (higher rent, Swiggy commissions, ingredient inflation). Every one of those is just a re-application of the concepts above.")

pdf.output("M:/mouli-projects/pizzaflow/reference/SliceMatic_Business_Economics_Explained.pdf")
print("PDF written.")
